"""Library-save-before-room-mutate admission (P95).

Preserves operator human judgment: before changing a room or building
structure, require an attested Sims My Library building save. Distinct from
game Save As. Pure evaluation / model attestation — no SendInput, no
Documents-folder writes.
"""
from __future__ import annotations

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
    if not {
        "MUTATE_ROOM_WITHOUT_LIBRARY_SAVE",
        "TREAT_SAVE_AS_AS_LIBRARY_CHECKPOINT",
        "SLEDGE_WALLS_WITHOUT_LIBRARY_SAVE",
    }.issubset(forbidden):
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


def is_room_mutation(
    model: Mapping[str, Any],
    action: str,
    *,
    targets: Sequence[str] | None = None,
    place_kind: str | None = None,
    contract: Mapping[str, Any] | None = None,
) -> bool:
    """True when the action changes room envelope / structure (not outdoor floaters)."""
    cfg = contract if contract is not None else load_contract()
    act = str(action or "").upper()
    if act in {str(x).upper() for x in cfg.get("exempt_actions") or []}:
        return False
    if act == "SAVE_TO_LIBRARY":
        return False
    if act in room_mutating_actions(cfg):
        return True
    kinds = room_mutating_target_kinds(cfg)
    if place_kind and str(place_kind).upper() in kinds:
        return True
    entities = _entities(model)
    for tid in targets or []:
        ent = entities.get(str(tid)) or {}
        if str(ent.get("kind") or "").upper() in kinds:
            return True
        if str(ent.get("domain") or "").upper() in {"WALL", "INDOOR_FLOOR"} and act in {
            "SLEDGE", "HAND_MOVE", "EYEDROPPER_PLACE", "PLACE_FROM_CATALOG", "PLACE_FROM_INVENTORY"
        }:
            # HAND_MOVE of wall/floor is room mutation even if kind tagging drifted.
            if act in {"SLEDGE", "HAND_MOVE"}:
                return True
    return False


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
        "reason": "FRESH_LIBRARY_CHECKPOINT",
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
    building_id: str | None = None,
) -> dict:
    """Admit or deny based on library-save-before-room-mutate."""
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
    if not is_room_mutation(
        model, act, targets=targets, place_kind=place_kind, contract=cfg
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
    if not freshness.get("fresh"):
        return {
            "state": "LIBRARY_DENY",
            "gate": "LIBRARY_CHECKPOINT_REQUIRED",
            "action": act,
            "library_required": True,
            "violation": freshness.get("violation") or "MUTATE_ROOM_WITHOUT_LIBRARY_SAVE",
            "detail": freshness.get("reason"),
            "freshness": freshness,
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
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
    }


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
    restore_goals = any(g.startswith("RESTORE_") for g in goals)
    if not structure_targets and not restore_goals:
        return None
    building_id = str(model.get("lot_id") or "building.unknown")
    return {
        "state": "LIBRARY_SAVE_REQUIRED",
        "gate": "LIBRARY_CHECKPOINT_REQUIRED",
        "action": "SAVE_TO_LIBRARY",
        "reason": "SAVE_BUILDING_TO_LIBRARY_BEFORE_ROOM_MUTATE",
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
