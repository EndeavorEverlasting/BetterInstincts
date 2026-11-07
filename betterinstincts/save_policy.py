"""Fail-closed Sims 4 save identity policy; no save directory access or writes."""
from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
POLICY_FILE = ROOT / "contracts" / "save-policy.v1.json"
MANIFEST_SCHEMA = "betterinstincts.save-register/v1"
MAX_REGISTRY_BYTES = 65_536
SAVE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{3,119}$")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,49}$")
REF_RE = re.compile(r"^capture:[A-Za-z0-9_.:-]{3,100}$")
PATCH_RE = re.compile(r"^\d+\.\d+\.\d+\.\d+$")


class SavePolicyError(ValueError):
    pass


def load_policy(path: Path = POLICY_FILE) -> dict:
    path = Path(path)
    if path.is_symlink() or path.stat().st_size > 24_000:
        raise SavePolicyError("SAVE_POLICY_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    classes = cfg.get("labels", {})
    if cfg.get("schema") != "betterinstincts.save-policy/v1" or cfg.get("default_classification") != "UNKNOWN_PROTECTED":
        raise SavePolicyError("SAVE_POLICY_CANNOT_DOWNGRADE_UNKNOWN")
    if set(classes) != {"LAB_DISPOSABLE", "LAB_CONTINUATION", "USER_PROTECTED", "UNKNOWN_PROTECTED"}:
        raise SavePolicyError("SAVE_POLICY_CLASSES_INVALID")
    forbidden = set(cfg.get("always_denied", []))
    if not {"DELETE", "OVERWRITE", "RESUME", "AUTO_SELECT", "MIGRATE", "MODIFY_GAME_SAVE", "LOAD_USER_SAVE"}.issubset(forbidden):
        raise SavePolicyError("SAVE_POLICY_DESTRUCTIVE_ACTIONS_NOT_FORBIDDEN")
    for label in ("LAB_DISPOSABLE", "LAB_CONTINUATION"):
        entry = classes[label]
        if entry.get("permitted_intents") != ["SELECT_FOR_PLAY"] or entry.get("requires_origin") != "LAB_CREATED" or entry.get("requires_capture_and_run_binding") is not True:
            raise SavePolicyError("SAVE_POLICY_LAB_REQUIREMENTS_WEAKENED")
    for label in ("USER_PROTECTED", "UNKNOWN_PROTECTED"):
        if classes[label].get("permitted_intents") != []:
            raise SavePolicyError("PROTECTED_SAVE_MUST_NOT_BE_AUTOMATED")
    return cfg


def load_registry(path: Path) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_REGISTRY_BYTES:
        raise SavePolicyError("SAVE_REGISTRY_MISSING_OR_UNSAFE")
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SavePolicyError("INVALID_SAVE_REGISTRY_JSON") from exc
    if not isinstance(result, dict) or result.get("schema") != MANIFEST_SCHEMA or not isinstance(result.get("entries"), list) or len(result["entries"]) > 150:
        raise SavePolicyError("INVALID_SAVE_REGISTRY_SCHEMA")
    return result


def decide(registry: dict, *, save_id: str, run_id: str, alias: str,
           game_version: str, capture_ref: str, intent: str = "SELECT_FOR_PLAY",
           policy: dict | None = None) -> dict:
    """Names suggest classes; only one bound lab-origin record authorizes selection.

    A lab-origin record is operator attestation, NOT independent proof of creation.
    No save may be deleted/overwritten by this API, regardless of classification.
    """
    rules = policy if policy is not None else load_policy()
    if not isinstance(registry, dict) or registry.get("schema") != MANIFEST_SCHEMA or not isinstance(registry.get("entries"), list) or len(registry["entries"]) > 150:
        raise SavePolicyError("INVALID_SAVE_REGISTRY_SCHEMA")
    if not all(isinstance(x, str) for x in (save_id, run_id, alias, game_version, capture_ref)):
        raise SavePolicyError("INVALID_SAVE_IDENTITY_FIELDS")
    if not SAVE_ID_RE.fullmatch(save_id) or not RUN_ID_RE.fullmatch(run_id) or not PATCH_RE.fullmatch(game_version) or not REF_RE.fullmatch(capture_ref) or len(alias) > 90:
        raise SavePolicyError("INVALID_SAVE_IDENTITY_FIELDS")
    if intent not in {"SELECT_FOR_PLAY", "INSPECT", "DELETE", "OVERWRITE", "RESUME", "MIGRATE", "AUTO_SELECT"}:
        raise SavePolicyError("UNKNOWN_SAVE_INTENT")
    matches = [r for r in registry["entries"] if isinstance(r, dict) and (r.get("save_id") == save_id or r.get("alias") == alias)]
    safe = {"state": "DENIED", "classification": "UNKNOWN_PROTECTED",
            "reason": "NO_UNIQUE_LAB_PROVENANCE", "proof_ceiling": "NO_GAME_SAVE_INSPECTED"}
    if len(matches) != 1:
        safe["reason"] = "SAVE_IDENTITY_AMBIGUOUS" if matches else "UNREGISTERED_SAVE_PROTECTED"
        return safe
    record = matches[0]
    kind = record.get("classification")
    if kind in {"USER_PROTECTED", "UNKNOWN_PROTECTED"}:
        return {**safe, "classification": kind, "reason": "USER_OR_UNKNOWN_SAVE_PROTECTED"}
    if kind not in {"LAB_DISPOSABLE", "LAB_CONTINUATION"}:
        return {**safe, "reason": "INVALID_OR_UNRECOGNIZED_CLASSIFICATION"}
    expected = rules["labels"][kind]
    if not re.fullmatch(expected["hint_pattern"], alias) or record.get("alias") != alias:
        return {**safe, "reason": "LAB_NAMING_INCONSISTENT"}
    # Never promote a user-created save even if it happens to match a lab-style alias.
    if record.get("origin") != "LAB_CREATED" or record.get("lab_origin_confirmed") is not True:
        return {**safe, "reason": "LAB_ORIGIN_UNPROVEN"}
    if (record.get("save_id") != save_id or record.get("authorized_run_id") != run_id
            or record.get("capture_ref") != capture_ref or record.get("game_version") != game_version
            or record.get("operator_confirmed") is not True
            or not RUN_ID_RE.fullmatch(str(record.get("creation_run_id", "")))):
        return {**safe, "reason": "SAVE_BINDING_OR_OPERATOR_CONFIRMATION_MISSING"}
    if intent not in expected["permitted_intents"]:
        return {**safe, "classification": kind, "reason": "INTENT_NOT_PERMITTED"}
    return {"state": "OPERATOR_ATTESTED_SELECTION_ONLY", "classification": kind,
            "reason": "LAB_IDENTITY_BOUND_TO_CURRENT_RUN_AND_CAPTURE",
            "proof_ceiling": "OPERATOR_ATTESTED_NOT_INDEPENDENTLY_PROVEN_SAVE_ORIGIN"}


def selected_save_guard(cfg: dict, run_id: str) -> dict:
    """Authorize only an explicitly supplied same-folder lab manifest for a chosen slot."""
    path = Path(str(cfg.get("_profile_path", "")))
    name = cfg.get("save_registry")
    if not isinstance(name, str) or Path(name).name != name or not name.endswith(".json"):
        raise SavePolicyError("CHOSEN_SAVE_REQUIRES_LOCAL_REGISTRY")
    if not path.is_absolute() or not path.is_file():
        raise SavePolicyError("EXPLICIT_PROFILE_REQUIRED")
    registry_path = path.parent / name
    if registry_path.is_symlink():
        raise SavePolicyError("SYMLINK_SAVE_REGISTRY_FORBIDDEN")
    record = load_registry(registry_path)
    decision = decide(record, save_id=cfg.get("selected_save_id"),
                      run_id=run_id, alias=cfg.get("save_alias"),
                      game_version=cfg.get("game_version"),
                      capture_ref=cfg.get("selected_save_capture_ref"))
    if decision["state"] != "OPERATOR_ATTESTED_SELECTION_ONLY":
        raise SavePolicyError("CHOSEN_SAVE_PROTECTED:" + decision["reason"])
    return decision
