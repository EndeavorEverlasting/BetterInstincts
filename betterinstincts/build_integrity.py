"""Structure-first Build/Buy spatial integrity (P95).

Denies outdoor-as-indoor, place-without-floor, nesting, and unguarded
structure/aesthetic destruction. Pure evaluation — no SendInput.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "build-integrity.v1.json"
MAX_BYTES = 64_000
MODEL_SCHEMA = "betterinstincts.lot-environment-model/v1"

INDOOR_DOMAINS = frozenset({"INDOOR_FLOOR"})
OUTDOOR_DOMAINS = frozenset({"OUTDOOR_LOT"})
STRUCTURE_KINDS = frozenset({
    "FLOOR_TILE", "WALL_SEGMENT", "DOOR", "WINDOW", "ROOF_PIECE",
})
PROTECTED_FURNITURE = frozenset({
    "DINING_TABLE", "DINING_CHAIR", "BED", "SLEEP_POD", "APPLIANCE",
    "COUNTER", "CABINET",
})


class BuildIntegrityError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise BuildIntegrityError("BUILD_INTEGRITY_CONTRACT_UNSAFE")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.build-integrity/v1":
        raise BuildIntegrityError("INVALID_BUILD_INTEGRITY_SCHEMA")
    if data.get("architecture", {}).get("selected") != "STRUCTURE_FIRST_SPATIAL_ADMISSION":
        raise BuildIntegrityError("STRUCTURE_FIRST_REQUIRED")
    forbidden = set(data.get("forbidden", []))
    if not {
        "TREAT_OUTDOOR_AS_INDOOR",
        "PLACE_INDOOR_ON_GRASS",
        "NEST_OBJECTS",
        "DELETE_FLOOR_WITHOUT_RESTORE_GOAL",
        "STRIP_KITCHEN_AESTHETIC",
    }.issubset(forbidden):
        raise BuildIntegrityError("CORE_FORBIDDEN_MISSING")
    return data


def _goals(model: Mapping[str, Any]) -> set[str]:
    return {str(g).upper() for g in (model.get("open_goals") or [])}


def _entities(model: Mapping[str, Any]) -> dict[str, dict]:
    raw = model.get("entities") or {}
    if not isinstance(raw, dict):
        raise BuildIntegrityError("INVALID_MODEL_ENTITIES")
    out: dict[str, dict] = {}
    for key, val in raw.items():
        if isinstance(val, dict):
            out[str(key)] = val
    return out


def _domain_of(entity: Mapping[str, Any]) -> str:
    domain = str(entity.get("domain") or entity.get("spatial_domain") or "UNKNOWN_DOMAIN")
    return domain.upper()


def _zone_of(entity: Mapping[str, Any]) -> Optional[str]:
    zone = entity.get("zone")
    if zone is None:
        return None
    return str(zone).upper()


def indoor_floor_present(model: Mapping[str, Any]) -> bool:
    for ent in _entities(model).values():
        kind = str(ent.get("kind") or "")
        status = str(ent.get("status") or "PRESENT").upper()
        if kind == "FLOOR_TILE" and status in {"PRESENT", "PARTIAL"} and _domain_of(ent) in INDOOR_DOMAINS:
            return True
        if kind == "ROOM_ZONE" and _domain_of(ent) in INDOOR_DOMAINS and status == "PRESENT":
            # Room zone alone is insufficient without floor — still False
            continue
    return False


def _class_for_kind(kind: str, cfg: Mapping[str, Any]) -> str:
    classes = cfg.get("object_classes") or {}
    for cls_name, kinds in classes.items():
        if kind in kinds:
            return str(cls_name)
    if kind in STRUCTURE_KINDS:
        return "STRUCTURE"
    return "OUTDOOR_OK"


def _has_save_as(model: Mapping[str, Any]) -> bool:
    att = model.get("save_as_attestation") or {}
    return bool(isinstance(att, dict) and att.get("operator_confirmed") is True)


def _restore_goal_ok(model: Mapping[str, Any], cfg: Mapping[str, Any]) -> bool:
    needed = {str(g).upper() for g in cfg.get("required_goals_for_structure_mutate") or []}
    return bool(_goals(model) & needed)


def evaluate_integrity(
    model: Mapping[str, Any],
    *,
    action: str,
    targets: Sequence[str] = (),
    place_kind: Optional[str] = None,
    place_domain: Optional[str] = None,
    nest_risk: bool = False,
    strips_zone: Optional[str] = None,
) -> dict:
    """Admit or deny one Build/Buy mutation under structure-first spatial rules."""
    cfg = load_contract()
    if model.get("schema") != MODEL_SCHEMA:
        raise BuildIntegrityError("LOT_MODEL_REQUIRED")
    action_u = str(action).upper()
    target_list = [str(t) for t in targets if str(t).strip()]
    entities = _entities(model)
    floor_ok = indoor_floor_present(model)
    place_domain_u = (place_domain or "UNKNOWN_DOMAIN").upper()
    kind = place_kind
    if kind is None and target_list and target_list[0] in entities:
        kind = str(entities[target_list[0]].get("kind") or "UNKNOWN_OBJECT")
    kind = str(kind or "UNKNOWN_OBJECT")
    obj_class = _class_for_kind(kind, cfg)

    # Structural delete / sledge / bulk
    if action_u in {
        "SLEDGE",
        "BACKSPACE_TO_INVENTORY",
        "BULK_INVENTORY_SWEEP",
        "MULTI_OBJECT_REARRANGE",
        "WALL_ROOM_TOOL",
        "MOVE_HOUSE_OR_ROOM",
    }:
        touching_structure = False
        touching_protected = False
        touching_zone = None
        for tid in target_list:
            ent = entities.get(tid) or {}
            ekind = str(ent.get("kind") or "")
            if ekind in STRUCTURE_KINDS or obj_class == "STRUCTURE":
                touching_structure = True
            if ekind in PROTECTED_FURNITURE or _zone_of(ent) in set(cfg.get("protected_zones") or []):
                touching_protected = True
                touching_zone = _zone_of(ent)
        if action_u == "BULK_INVENTORY_SWEEP":
            return _deny(
                "BULK_SWEEP_STRUCTURE",
                gate="BUILD_INTEGRITY_ADMIT",
                detail="Bulk sweeps are forbidden; target typed entities only",
                floor_ok=floor_ok,
            )
        if touching_structure or kind in STRUCTURE_KINDS:
            if not _restore_goal_ok(model, cfg):
                return _deny(
                    "STRUCTURE_DELETE_UNGUARDED",
                    gate="STRUCTURE_RESTORE_REQUIRED",
                    detail="FLOOR/WALL mutate needs RESTORE_* goal",
                    floor_ok=floor_ok,
                )
            if not _has_save_as(model):
                return _deny(
                    "STRUCTURE_DELETE_UNGUARDED",
                    gate="STRUCTURE_RESTORE_REQUIRED",
                    detail="STRUCTURE mutate needs Save As attestation",
                    floor_ok=floor_ok,
                )
        if touching_protected and strips_zone:
            zone = str(strips_zone).upper()
            if zone in set(cfg.get("protected_zones") or []) and not _restore_goal_ok(model, cfg):
                return _deny(
                    "AESTHETIC_ZONE_DESTRUCT",
                    gate="PROTECT_AESTHETIC_ZONES",
                    detail=f"Stripping {zone} requires RESTORE_* goal",
                    floor_ok=floor_ok,
                    zone=zone,
                )
        if touching_protected and touching_zone and not _restore_goal_ok(model, cfg):
            # Removing kitchen/dining/bed furniture without restore goal
            if action_u in {"SLEDGE", "BACKSPACE_TO_INVENTORY"} and kind in PROTECTED_FURNITURE:
                return _deny(
                    "AESTHETIC_ZONE_DESTRUCT",
                    gate="PROTECT_AESTHETIC_ZONES",
                    detail=f"Protected furniture {kind} needs RESTORE_* goal",
                    floor_ok=floor_ok,
                    zone=touching_zone,
                )

    # Placement / move
    if action_u in {
        "PLACE_FROM_CATALOG",
        "PLACE_FROM_INVENTORY",
        "EYEDROPPER_PLACE",
        "HAND_MOVE",
    }:
        if place_domain_u == "UNKNOWN_DOMAIN" and not target_list:
            return _deny(
                "MISSING_SPATIAL_CLAIM",
                gate="SPATIAL_CLAIMS_REQUIRED",
                detail="place_domain required when placing",
                floor_ok=floor_ok,
            )
        if obj_class == "INDOOR_FLOOR_REQUIRED" or kind in PROTECTED_FURNITURE:
            if place_domain_u in OUTDOOR_DOMAINS:
                return _deny(
                    "OUTDOOR_AS_INDOOR",
                    gate="INDOOR_DOMAIN_REQUIRED",
                    detail="Indoor object cannot place on OUTDOOR_LOT/grass",
                    floor_ok=floor_ok,
                )
            if not floor_ok:
                return _deny(
                    "PLACE_WITHOUT_FLOOR",
                    gate="RESTORE_FLOOR_BEFORE_FURNITURE",
                    detail="Restore INDOOR_FLOOR before placing indoor furniture",
                    floor_ok=False,
                )
            if place_domain_u not in INDOOR_DOMAINS and place_domain_u != "UNKNOWN_DOMAIN":
                return _deny(
                    "OUTDOOR_AS_INDOOR",
                    gate="INDOOR_DOMAIN_REQUIRED",
                    detail=f"domain {place_domain_u} invalid for indoor furniture",
                    floor_ok=floor_ok,
                )
            if place_domain_u == "UNKNOWN_DOMAIN":
                return _deny(
                    "MISSING_SPATIAL_CLAIM",
                    gate="SPATIAL_CLAIMS_REQUIRED",
                    detail="Indoor place requires domain=INDOOR_FLOOR claim",
                    floor_ok=floor_ok,
                )
        if nest_risk:
            return _deny(
                "NESTED_OBJECTS",
                gate="NO_NESTING",
                detail="Placement would nest/stack inside another object",
                floor_ok=floor_ok,
            )

    return {
        "state": "INTEGRITY_ADMIT",
        "gate": "BUILD_INTEGRITY_ADMIT",
        "action": action_u,
        "kind": kind,
        "object_class": obj_class,
        "place_domain": place_domain_u,
        "indoor_floor_present": floor_ok,
        "targets": target_list,
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
        "forbidden": list(cfg.get("forbidden") or []),
    }


def _deny(violation: str, *, gate: str, detail: str, floor_ok: bool, zone: Optional[str] = None) -> dict:
    cfg = load_contract()
    out = {
        "state": "INTEGRITY_DENY",
        "gate": gate,
        "violation": violation,
        "detail": detail,
        "indoor_floor_present": floor_ok,
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
        "forbidden": list(cfg.get("forbidden") or []),
        "next": "OBSERVE_DOMAINS_AND_RESTORE_STRUCTURE_INTO_SAME_MODEL",
    }
    if zone:
        out["zone"] = zone
    return out


def structure_restore_plan(model: Mapping[str, Any]) -> dict:
    """Ordered restore plan from accumulated damage claims — never blank-slate."""
    cfg = load_contract()
    entities = _entities(model)
    missing_floor = not indoor_floor_present(model)
    missing_walls = any(
        str(e.get("kind")) == "WALL_SEGMENT" and str(e.get("status") or "").upper() in {"MISSING", "PARTIAL", "ABSENT"}
        for e in entities.values()
    ) or any("WALL" in g for g in _goals(model))
    missing_kitchen = any(
        _zone_of(e) == "KITCHEN" and str(e.get("status") or "").upper() in {"MISSING", "STRIPPED", "ABSENT"}
        for e in entities.values()
    ) or "RESTORE_KITCHEN" in _goals(model)
    # Whole dining set restore only when the table is gone; empty chair slots
    # are ordinary furniture placement after structure is intact.
    missing_dining = any(
        str(e.get("kind")) == "DINING_TABLE"
        and str(e.get("status") or "").upper() in {"MISSING", "ABSENT"}
        for e in entities.values()
    )
    missing_bed = any(
        str(e.get("kind")) in {"BED", "SLEEP_POD"}
        and str(e.get("status") or "").upper() in {"MISSING", "ABSENT"}
        for e in entities.values()
    )
    steps = []
    if missing_floor:
        steps.append({"step": "RESTORE_FLOOR", "gate": "RESTORE_FLOOR_BEFORE_FURNITURE", "action": "PLACE_FLOOR_TILES"})
    if missing_walls:
        steps.append({"step": "RESTORE_WALLS", "gate": "STRUCTURE_RESTORE_REQUIRED", "action": "PLACE_WALL_SEGMENTS"})
    if missing_kitchen:
        steps.append({"step": "RESTORE_KITCHEN", "gate": "PROTECT_AESTHETIC_ZONES", "action": "RESTORE_KITCHEN_OBJECTS"})
    if missing_dining:
        steps.append({"step": "RESTORE_DINING", "gate": "PROTECT_AESTHETIC_ZONES", "action": "PLACE_DINING_SET"})
    if missing_bed:
        steps.append({"step": "RESTORE_BED_OR_SLEEP_POD", "gate": "PROTECT_AESTHETIC_ZONES", "action": "PLACE_SLEEP_POD"})
    if not steps:
        return {
            "state": "INTEGRITY_ADMIT",
            "gate": "BUILD_INTEGRITY_ADMIT",
            "steps": [],
            "reason": "NO_STRUCTURE_GAPS_IN_MODEL",
            "proof_ceiling": cfg["proof_ceiling"],
        }
    return {
        "state": "STRUCTURE_RESTORE_REQUIRED",
        "gate": "RESTORE_FLOOR_BEFORE_FURNITURE" if missing_floor else "STRUCTURE_RESTORE_REQUIRED",
        "steps": steps,
        "primary": steps[0],
        "indoor_floor_present": not missing_floor,
        "proof_ceiling": cfg["proof_ceiling"],
        "forbidden": ["PLACE_INDOOR_ON_GRASS", "TREAT_OUTDOOR_AS_INDOOR", "CLAIM_FIXED_WITHOUT_INTEGRITY_PASS"],
    }
