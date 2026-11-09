"""Library-save-before-room-mutate admission (P95).

Preserves operator human judgment: before changing a room, story, stairs,
floor, wall, or building structure, require an attested Sims My Library
building save. Distinct from game Save As. Includes live-structure preflight
and held-object distractor blocks (Medicine Craftidink). Pure evaluation /
model attestation — no SendInput, no Documents-folder writes.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "build-library-checkpoint.v1.json"
MAX_BYTES = 64_000
MODEL_SCHEMA = "betterinstincts.lot-environment-model/v1"
CAPTURE_RE = re.compile(r"^capture:[A-Za-z0-9_./:-]{3,160}$")
BUILDING_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.:-]{1,79}$")
LIBRARY_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.'-]{2,79}$")

_CORE_FORBIDDEN = frozenset(
    {
        "MUTATE_ROOM_WITHOUT_LIBRARY_SAVE",
        "TREAT_SAVE_AS_AS_LIBRARY_CHECKPOINT",
        "SLEDGE_WALLS_WITHOUT_LIBRARY_SAVE",
        "DELETE_FLOOR2_WITHOUT_LIBRARY_SAVE",
        "STRUCTURE_WHILE_HELD_DISTRACTOR",
        "RAW_INPUT_BYPASS_OF_STRUCTURE_PREFLIGHT",
    }
)

_STRUCTURE_DOMAIN_ACTIONS = frozenset(
    {
        "SLEDGE",
        "HAND_MOVE",
        "DELETE_KEY",
        "DELETE_OBJECT",
        "BACKSPACE_STRUCTURE",
        "REMOVE_FLOOR",
        "REMOVE_FLOOR_TILE",
        "DELETE_STAIRS",
    }
)


class BuildLibraryCheckpointError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise BuildLibraryCheckpointError("BUILD_LIBRARY_CHECKPOINT_CONTRACT_UNSAFE")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.build-library-checkpoint/v1":
        raise BuildLibraryCheckpointError("INVALID_BUILD_LIBRARY_CHECKPOINT_SCHEMA")
    if data.get("architecture", {}).get("selected") != "LIBRARY_SAVE_BEFORE_ROOM_MUTATE":
        raise BuildLibraryCheckpointError("LIBRARY_SAVE_BEFORE_ROOM_MUTATE_REQUIRED")
    forbidden = set(data.get("forbidden", []))
    if not _CORE_FORBIDDEN.issubset(forbidden):
        raise BuildLibraryCheckpointError("CORE_FORBIDDEN_MISSING")
    return data


def _entities(model: Mapping[str, Any]) -> dict[str, dict]:
    raw = model.get("entities") or {}
    if not isinstance(raw, dict):
        raise BuildLibraryCheckpointError("INVALID_MODEL_ENTITIES")
    out: dict[str, dict] = {}
    for key, val in raw.items():
        if isinstance(val, dict):
            out[str(key)] = val
    return out


def room_mutating_target_kinds(contract: Mapping[str, Any] | None = None) -> frozenset[str]:
    cfg = contract if contract is not None else load_contract()
    return frozenset(str(x).upper() for x in cfg.get("room_mutating_target_kinds") or [])


def room_mutating_actions(contract: Mapping[str, Any] | None = None) -> frozenset[str]:
    cfg = contract if contract is not None else load_contract()
    return frozenset(str(x).upper() for x in cfg.get("room_mutating_actions") or [])


def live_structure_effects(contract: Mapping[str, Any] | None = None) -> frozenset[str]:
    cfg = contract if contract is not None else load_contract()
    return frozenset(str(x).upper() for x in cfg.get("live_structure_effects") or [])


def protected_stories(contract: Mapping[str, Any] | None = None) -> frozenset[str]:
    cfg = contract if contract is not None else load_contract()
    return frozenset(str(x).upper() for x in cfg.get("protected_stories") or [])


def _normalize_held(held_object: str | None) -> str:
    return " ".join(str(held_object or "").strip().lower().split())


def held_object_structure_block(
    held_object: str | None,
    *,
    contract: Mapping[str, Any] | None = None,
) -> Optional[dict]:
    """If a held object must cancel-only (never structure thrash), return the block row."""
    cfg = contract if contract is not None else load_contract()
    label = _normalize_held(held_object)
    if not label:
        return None
    for row in cfg.get("held_object_structure_blocks") or []:
        if not isinstance(row, dict):
            continue
        for needle in row.get("match_substrings") or []:
            if str(needle).lower() in label:
                return {
                    "id": row.get("id"),
                    "required_action": row.get("required_action") or "CANCEL_UI_ONLY",
                    "forbid": [str(x).upper() for x in (row.get("forbid") or [])],
                    "operator_correction": row.get("operator_correction"),
                    "held_object": held_object,
                }
    return None


def targets_protected_story(
    model: Mapping[str, Any],
    targets: Sequence[str] | None,
    *,
    place_story: str | None = None,
    contract: Mapping[str, Any] | None = None,
) -> bool:
    stories = protected_stories(contract)
    if place_story and str(place_story).upper() in stories:
        return True
    entities = _entities(model)
    for tid in targets or []:
        ent = entities.get(str(tid)) or {}
        if str(ent.get("story") or "").upper() in stories:
            return True
        kind = str(ent.get("kind") or "").upper()
        if kind in {"STAIR", "STAIRS", "STAIRCASE"}:
            return True
    return False


def is_room_mutation(
    model: Mapping[str, Any],
    action: str,
    *,
    targets: Sequence[str] | None = None,
    place_kind: str | None = None,
    place_story: str | None = None,
    contract: Mapping[str, Any] | None = None,
) -> bool:
    """True when the action changes room envelope / structure / stairs / story."""
    cfg = contract if contract is not None else load_contract()
    act = str(action or "").upper()
    if act in {str(x).upper() for x in cfg.get("exempt_actions") or []}:
        return False
    if act == "SAVE_TO_LIBRARY":
        return False
    # P00/P01: every Buy/Build change requires the whole-lot pre-edit backup.
    # Keep live FLOOR_2 and held-object safety checks below unchanged.
    from betterinstincts.house_state import load_contract as load_house_contract
    if act in {str(x).upper() for x in load_house_contract()["mutating_actions"]}:
        return True
    if act in room_mutating_actions(cfg):
        return True
    kinds = room_mutating_target_kinds(cfg)
    if place_kind and str(place_kind).upper() in kinds:
        return True
    if place_story and str(place_story).upper() in protected_stories(cfg):
        if act in {str(x).upper() for x in cfg.get("protected_story_actions") or []}:
            return True
    entities = _entities(model)
    for tid in targets or []:
        ent = entities.get(str(tid)) or {}
        kind = str(ent.get("kind") or "").upper()
        if kind in kinds:
            return True
        domain = str(ent.get("domain") or "").upper()
        if domain in {"WALL", "INDOOR_FLOOR"} and act in _STRUCTURE_DOMAIN_ACTIONS:
            return True
        if str(ent.get("story") or "").upper() in protected_stories(cfg) and act in {
            str(x).upper() for x in cfg.get("protected_story_actions") or []
        }:
            return True
    return False


def validate_full_lot_manifest(model: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict:
    """Validate an operator-attested, every-story/room scan against current observations.

    This can verify *declared* coverage, not discover a physically unseen floor.
    A capture ref is provenance, not proof a live Gallery save occurred.
    """
    from betterinstincts.room_census import load_contract as census_contract, scan_lot_model

    if not isinstance(manifest, Mapping) or manifest.get("operator_confirmed") is not True:
        raise BuildLibraryCheckpointError("FULL_LOT_MANIFEST_CONFIRMATION_REQUIRED")
    if manifest.get("all_stories_inspected") is not True:
        raise BuildLibraryCheckpointError("ALL_STORIES_NOT_ATTESTED")
    if str(manifest.get("lot_id")) != str(model.get("lot_id")):
        raise BuildLibraryCheckpointError("LOT_MANIFEST_SCOPE_MISMATCH")
    if type(manifest.get("model_revision")) is not int or manifest["model_revision"] != model.get("revision"):
        raise BuildLibraryCheckpointError("LOT_MANIFEST_REVISION_STALE")
    census = scan_lot_model(model)
    if census["unassigned_items"] or census["unverified_claim_count"] or model.get("unknowns"):
        raise BuildLibraryCheckpointError("LOT_MANIFEST_UNCLASSIFIED_OBSERVATIONS")
    floors = manifest.get("floors")
    rooms = manifest.get("rooms")
    if not isinstance(floors, Mapping) or not isinstance(rooms, Mapping) or not floors or not rooms:
        raise BuildLibraryCheckpointError("LOT_MANIFEST_FLOORS_AND_ROOMS_REQUIRED")
    if set(floors) != set(census["floors"]) or set(rooms) != set(census["rooms"]):
        raise BuildLibraryCheckpointError("LOT_MANIFEST_FLOOR_ROOM_COVERAGE_MISMATCH")
    captures = set(model.get("captures") or [])
    taxonomy = census_contract()
    allowed_functions = set(taxonomy["functional_labels"])
    allowed_styles = set(taxonomy["style_labels"])
    for story, floor in floors.items():
        if not isinstance(floor, Mapping) or floor.get("rooms") != census["floors"][story]["rooms"]:
            raise BuildLibraryCheckpointError("LOT_MANIFEST_FLOOR_ROOMS_MISMATCH")
        ref = floor.get("capture_ref")
        if not isinstance(ref, str) or not CAPTURE_RE.fullmatch(ref) or ref not in captures:
            raise BuildLibraryCheckpointError("LOT_MANIFEST_FLOOR_CAPTURE_MISSING")
    for room_id, classification in rooms.items():
        observed = census["rooms"][room_id]
        if observed["room_evidence"] != "STRUCTURE_ATTESTED" or observed["enclosure"] == "UNKNOWN_ENCLOSURE" or observed["enclosure_conflict"]:
            raise BuildLibraryCheckpointError("LOT_MANIFEST_ROOM_STRUCTURE_UNVERIFIED")
        if not isinstance(classification, Mapping):
            raise BuildLibraryCheckpointError("LOT_MANIFEST_ROOM_CLASSIFICATION_MISSING")
        if classification.get("capture_ref") not in captures:
            raise BuildLibraryCheckpointError("LOT_MANIFEST_ROOM_CAPTURE_MISSING")
        functions = classification.get("function_labels")
        styles = classification.get("style_labels")
        if not isinstance(functions, list) or not functions or not set(functions) <= allowed_functions:
            raise BuildLibraryCheckpointError("LOT_MANIFEST_ROOM_FUNCTION_MISSING")
        if not isinstance(styles, list) or not styles or not set(styles) <= allowed_styles:
            raise BuildLibraryCheckpointError("LOT_MANIFEST_ROOM_STYLE_MISSING")
    canonical = {
        "lot_id": model["lot_id"],
        "model_revision": model["revision"],
        "floors": {key: dict(val) for key, val in sorted(floors.items())},
        "rooms": {key: dict(val) for key, val in sorted(rooms.items())},
        "entity_count": len(model.get("entities") or {}),
        "observed_story_count": census["observed_story_count"],
    }
    digest = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {"fingerprint": digest, "floor_count": len(floors), "room_count": len(rooms),
            "model_revision": model["revision"], "manifest": dict(manifest),
            "coverage": "OPERATOR_ATTESTED_ALL_STORIES_AND_ROOMS"}


def _verified_saved_lot_inventory(model: Mapping[str, Any], att: Mapping[str, Any]) -> dict:
    snapshot = att.get("lot_inventory")
    if not isinstance(snapshot, dict):
        return {"fresh": False, "reason": "FULL_LOT_MANIFEST_REQUIRED",
                "violation": "LOT_MUTATION_WITHOUT_COMPLETE_BACKUP"}
    try:
        verified = validate_full_lot_manifest(model, snapshot.get("manifest"))
    except (BuildLibraryCheckpointError, ValueError, TypeError) as exc:
        return {"fresh": False, "reason": str(exc),
                "violation": "LOT_MUTATION_WITHOUT_COMPLETE_BACKUP"}
    if verified["fingerprint"] != snapshot.get("fingerprint"):
        return {"fresh": False, "reason": "LOT_INVENTORY_FINGERPRINT_MISMATCH",
                "violation": "LOT_MUTATION_WITHOUT_COMPLETE_BACKUP"}
    # The host must have *written* the model before admitting a purchase or edit.
    # This is only the host's metadata backup; the My Library save is separately
    # operator-attested, not fabricated by this filesystem readback.
    try:
        from betterinstincts.house_state import load_model, model_path
        path = model_path(str(model["run_id"]), str(model["lot_id"]))
        stored = load_model(path)
        if stored.get("revision") != model.get("revision") or stored.get("entities") != model.get("entities") or stored.get("library_checkpoint") != att:
            raise BuildLibraryCheckpointError("LOT_METADATA_BACKUP_STALE")
    except (OSError, ValueError, KeyError) as exc:
        return {"fresh": False, "reason": str(exc) or "LOT_METADATA_BACKUP_MISSING",
                "violation": "LOT_MUTATION_WITHOUT_COMPLETE_BACKUP"}
    return {"fresh": True, "inventory": verified}


def library_checkpoint_fresh(
    model: Mapping[str, Any],
    *,
    building_id: str | None = None,
) -> dict:
    """Inspect whether the model carries a fresh library save for this revision."""
    if model.get("schema") != MODEL_SCHEMA:
        raise BuildLibraryCheckpointError("INVALID_LOT_MODEL_SCHEMA")
    revision = int(model.get("revision") or 0)
    att = model.get("library_checkpoint")
    if not isinstance(att, dict) or not att.get("library_saved"):
        return {
            "fresh": False,
            "reason": "LIBRARY_SAVE_REQUIRED",
            "violation": "MUTATE_ROOM_WITHOUT_LIBRARY_SAVE",
            "model_revision": revision,
        }
    if int(att.get("model_revision") or -1) != revision:
        return {
            "fresh": False,
            "reason": "STALE_LIBRARY_CHECKPOINT",
            "violation": "STALE_LIBRARY_CHECKPOINT",
            "model_revision": revision,
            "attestation_revision": att.get("model_revision"),
            "library_item_name": att.get("library_item_name"),
        }
    if building_id:
        if not BUILDING_ID_RE.fullmatch(building_id):
            raise BuildLibraryCheckpointError("INVALID_BUILDING_ID")
        if str(att.get("building_id") or "") != building_id:
            return {
                "fresh": False,
                "reason": "BUILDING_SCOPE_MISMATCH",
                "violation": "BUILDING_SCOPE_MISMATCH",
                "model_revision": revision,
                "attested_building_id": att.get("building_id"),
                "requested_building_id": building_id,
            }
    inventory = _verified_saved_lot_inventory(model, att)
    if not inventory["fresh"]:
        return {"fresh": False, "reason": inventory["reason"],
                "violation": inventory["violation"], "model_revision": revision}
    # Save As attestation must never be treated as library checkpoint.
    if att.get("source") == "GAME_SAVE_AS" or att.get("treated_as_save_as"):
        return {
            "fresh": False,
            "reason": "TREAT_SAVE_AS_AS_LIBRARY_CHECKPOINT",
            "violation": "TREAT_SAVE_AS_AS_LIBRARY_CHECKPOINT",
            "model_revision": revision,
        }
    return {
        "fresh": True,
        "reason": "FRESH_LIBRARY_AND_COMPLETE_LOT_BACKUP",
        "lot_inventory": inventory["inventory"],
        "model_revision": revision,
        "building_id": att.get("building_id"),
        "library_item_name": att.get("library_item_name"),
        "capture_ref": att.get("capture_ref"),
    }


def evaluate_library_checkpoint(
    model: Mapping[str, Any],
    action: str,
    *,
    targets: Sequence[str] | None = None,
    place_kind: str | None = None,
    place_story: str | None = None,
    building_id: str | None = None,
    held_object: str | None = None,
) -> dict:
    """Admit or deny based on library-save-before-room-mutate (+ held distractors)."""
    cfg = load_contract()
    if model.get("schema") != MODEL_SCHEMA:
        raise BuildLibraryCheckpointError("INVALID_LOT_MODEL_SCHEMA")
    act = str(action or "").upper()
    if act == "SAVE_TO_LIBRARY":
        return {
            "state": "LIBRARY_SAVE_ACTION",
            "gate": "SAVE_BUILDING_TO_LIBRARY_BEFORE_ROOM_MUTATE",
            "action": act,
            "execute_allowed": False,
            "proof_ceiling": cfg["proof_ceiling"],
            "detail": "SAVE_TO_LIBRARY creates the required checkpoint; it does not consume one",
        }

    block = held_object_structure_block(held_object, contract=cfg)
    if block and act in set(block.get("forbid") or []) | live_structure_effects(cfg):
        return {
            "state": "STRUCTURE_WHILE_HELD_DISTRACTOR",
            "gate": "HELD_DISTRACTOR_CANCEL_ONLY",
            "action": act,
            "library_required": False,
            "violation": "STRUCTURE_WHILE_HELD_DISTRACTOR",
            "detail": block.get("operator_correction"),
            "held_block": block,
            "required_action": block.get("required_action"),
            "execute_allowed": False,
            "forbidden": list(cfg.get("forbidden") or []),
            "proof_ceiling": cfg["proof_ceiling"],
        }

    if not is_room_mutation(
        model,
        act,
        targets=targets,
        place_kind=place_kind,
        place_story=place_story,
        contract=cfg,
    ):
        return {
            "state": "NOT_ROOM_MUTATION",
            "gate": "LIBRARY_CHECKPOINT_REQUIRED",
            "action": act,
            "library_required": False,
            "execute_allowed": False,
            "proof_ceiling": cfg["proof_ceiling"],
        }
    freshness = library_checkpoint_fresh(model, building_id=building_id)
    protected = targets_protected_story(
        model, targets, place_story=place_story, contract=cfg
    )
    if not freshness.get("fresh"):
        violation = freshness.get("violation") or "MUTATE_ROOM_WITHOUT_LIBRARY_SAVE"
        if protected:
            violation = "DELETE_FLOOR2_WITHOUT_LIBRARY_SAVE"
        return {
            "state": "LIBRARY_DENY" if not protected else "PROTECTED_STORY_DENY",
            "gate": (
                "PROTECTED_STORY_REQUIRES_LIBRARY"
                if protected
                else "LIBRARY_CHECKPOINT_REQUIRED"
            ),
            "action": act,
            "library_required": True,
            "violation": violation,
            "detail": freshness.get("reason"),
            "freshness": freshness,
            "protected_story": protected,
            "execute_allowed": False,
            "forbidden": list(cfg.get("forbidden") or []),
            "hint": "Call attest_library_save after observing Build Mode Save to My Library",
            "proof_ceiling": cfg["proof_ceiling"],
        }
    return {
        "state": "LIBRARY_ADMIT",
        "gate": "FRESH_LIBRARY_CHECKPOINT",
        "action": act,
        "library_required": True,
        "freshness": freshness,
        "protected_story": protected,
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
    }


def admit_live_structure_effect(
    model: Mapping[str, Any],
    action: str,
    *,
    targets: Sequence[str] | None = None,
    place_kind: str | None = None,
    place_story: str | None = None,
    building_id: str | None = None,
    held_object: str | None = None,
) -> dict:
    """Mandatory live preflight before any structure SendInput effect.

    Host/computer-use callers must invoke this and stop on any non-admit state.
    Skipping this call is the forbidden RAW_INPUT_BYPASS_OF_STRUCTURE_PREFLIGHT.
    Still execute_allowed=False: gallery write / SendInput remain separate.
    """
    cfg = load_contract()
    act = str(action or "").upper()
    if act not in live_structure_effects(cfg) and not is_room_mutation(
        model,
        act,
        targets=targets,
        place_kind=place_kind,
        place_story=place_story,
        contract=cfg,
    ):
        return {
            "state": "NOT_ROOM_MUTATION",
            "gate": "LIVE_STRUCTURE_PREFLIGHT",
            "action": act,
            "live_structure_effect": False,
            "execute_allowed": False,
            "proof_ceiling": cfg["proof_ceiling"],
        }
    result = evaluate_library_checkpoint(
        model,
        act,
        targets=targets,
        place_kind=place_kind,
        place_story=place_story,
        building_id=building_id,
        held_object=held_object,
    )
    result = dict(result)
    result["gate"] = "LIVE_STRUCTURE_PREFLIGHT"
    result["live_structure_effect"] = True
    result["raw_input_bypass_forbidden"] = True
    if result.get("state") == "LIBRARY_ADMIT":
        result["preflight"] = "ADMIT_STRUCTURE_EFFECT_OFFLINE_ONLY"
    else:
        result["preflight"] = "DENY_STRUCTURE_EFFECT"
    return result


def plan_library_save_if_required(model: Mapping[str, Any]) -> Optional[dict]:
    """If structure/room work is pending without a fresh checkpoint, demand SAVE_TO_LIBRARY.

    Presence of intact floors alone does not block outdoor floater planning; the
    admit_mutation gate still fails closed for SLEDGE / WALL_ROOM_TOOL / etc.
    """
    cfg = load_contract()
    if model.get("schema") != MODEL_SCHEMA:
        raise BuildLibraryCheckpointError("INVALID_LOT_MODEL_SCHEMA")
    freshness = library_checkpoint_fresh(model)
    if freshness.get("fresh"):
        return None
    entities = _entities(model)
    kinds = room_mutating_target_kinds(cfg)
    goals = {str(g).upper() for g in (model.get("open_goals") or [])}
    pending_statuses = {"MISSING", "ABSENT", "DAMAGED", "PARTIAL", "STRIPPED", "EMPTY_SLOT"}
    structure_targets = [
        eid for eid, ent in entities.items()
        if str(ent.get("kind") or "").upper() in kinds
        and str(ent.get("status") or "").upper() in pending_statuses
    ]
    restore_goals = any(
        g.startswith("RESTORE_") or g in {"FLOOR_2", "STAIRS", "STAIR"}
        for g in goals
    )
    if not entities:
        return None
    # P01 host planning: no catalog/inventory purchase or edit before full-lot census.
    building_id = str(model.get("lot_id") or "building.unknown")
    return {
        "state": "LIBRARY_SAVE_REQUIRED",
        "gate": "LIBRARY_CHECKPOINT_REQUIRED",
        "action": "SCAN_ALL_FLOORS_AND_ROOMS" if not isinstance((model.get("library_checkpoint") or {}).get("lot_inventory"), dict) else "SAVE_TO_LIBRARY",
        "reason": "COMPLETE_LOT_INVENTORY_AND_LIBRARY_SAVE_REQUIRED",
        "building_id": building_id,
        "targets": structure_targets[:8],
        "execute_allowed": False,
        "forbidden": list(cfg.get("forbidden") or []),
        "proof_ceiling": cfg["proof_ceiling"],
    }


def validate_attestation_payload(
    *,
    building_id: str,
    library_item_name: str,
    capture_ref: str,
) -> None:
    if not isinstance(building_id, str) or not BUILDING_ID_RE.fullmatch(building_id):
        raise BuildLibraryCheckpointError("INVALID_BUILDING_ID")
    if not isinstance(library_item_name, str) or not LIBRARY_NAME_RE.fullmatch(library_item_name):
        raise BuildLibraryCheckpointError("LIBRARY_NAME_MISSING")
    if not isinstance(capture_ref, str) or not CAPTURE_RE.fullmatch(capture_ref):
        raise BuildLibraryCheckpointError("LIBRARY_CAPTURE_MISSING")
