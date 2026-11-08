"""Enclosure (inside/outside) + story (F1/F2) classification for Build/Buy (P95).

Pure evaluation. Host uses these axes before admitting intelligent placement.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "build-spatial.v1.json"
MAX_BYTES = 48_000
MODEL_SCHEMA = "betterinstincts.lot-environment-model/v1"

ENCLOSURES = frozenset({"INSIDE", "OUTSIDE", "UNKNOWN_ENCLOSURE"})
STORIES = frozenset({"FLOOR_1", "FLOOR_2", "UNKNOWN_STORY"})


class BuildSpatialError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise BuildSpatialError("BUILD_SPATIAL_CONTRACT_UNSAFE")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.build-spatial/v1":
        raise BuildSpatialError("INVALID_BUILD_SPATIAL_SCHEMA")
    if data.get("architecture", {}).get("selected") != "ENCLOSURE_AND_STORY_AXES":
        raise BuildSpatialError("ENCLOSURE_AND_STORY_AXES_REQUIRED")
    if set(data.get("enclosure") or []) != ENCLOSURES:
        raise BuildSpatialError("ENCLOSURE_SET_INVALID")
    if set(data.get("story") or []) != STORIES:
        raise BuildSpatialError("STORY_SET_INVALID")
    forbidden = set(data.get("forbidden") or [])
    if not {
        "TREAT_OUTSIDE_AS_INSIDE",
        "IGNORE_STORY_LEVEL",
        "BUILD_F2_BEFORE_F1",
        "PLACE_WITH_UNKNOWN_AXES",
    }.issubset(forbidden):
        raise BuildSpatialError("CORE_FORBIDDEN_MISSING")
    return data


def normalize_story(raw: object, aliases: Mapping[str, str] | None = None) -> str:
    if raw is None:
        return "UNKNOWN_STORY"
    text = str(raw).strip().upper().replace(" ", "_")
    if text in STORIES:
        return text
    table = aliases if aliases is not None else load_contract().get("story_aliases", {})
    if text in table:
        return str(table[text])
    # Accept FLOOR1 / LEVEL_2 shapes
    compact = text.replace("FLOOR_", "").replace("LEVEL_", "").replace("STORY_", "")
    if compact in table:
        return str(table[compact])
    return "UNKNOWN_STORY"


def enclosure_from_domain(domain: object, mapping: Mapping[str, str] | None = None) -> str:
    key = str(domain or "UNKNOWN_DOMAIN").upper()
    table = mapping if mapping is not None else load_contract().get("domain_to_enclosure", {})
    value = str(table.get(key) or "UNKNOWN_ENCLOSURE")
    return value if value in ENCLOSURES else "UNKNOWN_ENCLOSURE"


def classify_entity(entity: Mapping[str, Any], *, cfg: Mapping[str, Any] | None = None) -> dict:
    """Classify one lot-model entity on enclosure + story axes."""
    contract = cfg if cfg is not None else load_contract()
    domain = str(entity.get("domain") or entity.get("spatial_domain") or "UNKNOWN_DOMAIN").upper()
    enclosure = str(entity.get("enclosure") or "").upper()
    if enclosure not in ENCLOSURES:
        enclosure = enclosure_from_domain(domain, contract.get("domain_to_enclosure"))
    story = normalize_story(
        entity.get("story") or entity.get("floor_level") or entity.get("level"),
        contract.get("story_aliases"),
    )
    # Outdoor never carries indoor story for placement purposes — keep story if attested, else UNKNOWN.
    if enclosure == "OUTSIDE" and story == "UNKNOWN_STORY":
        pass
    return {
        "state": "SPATIAL_CLASSIFIED",
        "enclosure": enclosure,
        "story": story,
        "domain": domain,
        "zone": (str(entity.get("zone")).upper() if entity.get("zone") is not None else None),
        "kind": str(entity.get("kind") or "UNKNOWN_OBJECT"),
        "id": entity.get("id"),
        "gate": "CLASSIFY_ENCLOSURE_AND_STORY",
    }


def classify_placement(
    *,
    enclosure: object,
    story: object,
    domain: object = None,
    cfg: Mapping[str, Any] | None = None,
) -> dict:
    contract = cfg if cfg is not None else load_contract()
    enc = str(enclosure or "").upper()
    if enc not in ENCLOSURES:
        enc = enclosure_from_domain(domain, contract.get("domain_to_enclosure"))
    sty = normalize_story(story, contract.get("story_aliases"))
    return {
        "state": "SPATIAL_CLASSIFIED",
        "enclosure": enc,
        "story": sty,
        "domain": str(domain or "UNKNOWN_DOMAIN").upper(),
        "gate": "CLASSIFY_ENCLOSURE_AND_STORY",
    }


def _entities(model: Mapping[str, Any]) -> dict[str, dict]:
    raw = model.get("entities") or {}
    if not isinstance(raw, dict):
        raise BuildSpatialError("INVALID_MODEL_ENTITIES")
    return {str(k): v for k, v in raw.items() if isinstance(v, dict)}


def inventory_spatial(model: Mapping[str, Any]) -> dict:
    """Partition the lot model into inside/outside and F1/F2 buckets."""
    cfg = load_contract()
    if model.get("schema") != MODEL_SCHEMA:
        raise BuildSpatialError("LOT_MODEL_REQUIRED")
    buckets = {
        "INSIDE": {"FLOOR_1": [], "FLOOR_2": [], "UNKNOWN_STORY": []},
        "OUTSIDE": {"FLOOR_1": [], "FLOOR_2": [], "UNKNOWN_STORY": []},
        "UNKNOWN_ENCLOSURE": {"FLOOR_1": [], "FLOOR_2": [], "UNKNOWN_STORY": []},
    }
    classified = []
    for eid, ent in _entities(model).items():
        row = classify_entity({**ent, "id": eid}, cfg=cfg)
        classified.append(row)
        buckets[row["enclosure"]][row["story"]].append(eid)
    return {
        "state": "SPATIAL_CLASSIFIED",
        "gate": "CLASSIFY_ENCLOSURE_AND_STORY",
        "buckets": buckets,
        "entities": classified,
        "counts": {
            enc: {sty: len(ids) for sty, ids in stories.items()}
            for enc, stories in buckets.items()
        },
        "proof_ceiling": cfg["proof_ceiling"],
    }


def floor_tile_present(model: Mapping[str, Any], *, enclosure: str, story: str) -> bool:
    cfg = load_contract()
    for eid, ent in _entities(model).items():
        if str(ent.get("kind") or "") != "FLOOR_TILE":
            continue
        status = str(ent.get("status") or "PRESENT").upper()
        if status not in {"PRESENT", "PARTIAL"}:
            continue
        row = classify_entity({**ent, "id": eid}, cfg=cfg)
        if row["enclosure"] == enclosure and row["story"] == story:
            return True
    return False


def admit_spatial_placement(
    model: Mapping[str, Any],
    *,
    place_enclosure: object,
    place_story: object,
    place_domain: object = None,
    indoor_required: bool = True,
) -> dict:
    """Fail closed when axes are unknown, outside-as-inside, or F2-before-F1."""
    cfg = load_contract()
    placement = classify_placement(
        enclosure=place_enclosure,
        story=place_story,
        domain=place_domain,
        cfg=cfg,
    )
    enc = placement["enclosure"]
    sty = placement["story"]

    if indoor_required:
        if enc == "OUTSIDE":
            return {
                "state": "SPATIAL_DENY",
                "gate": "OUTSIDE_NOT_INSIDE",
                "violation": "OUTSIDE_AS_INSIDE",
                "placement": placement,
                "execute_allowed": False,
                "proof_ceiling": cfg["proof_ceiling"],
            }
        if enc == "UNKNOWN_ENCLOSURE" or sty == "UNKNOWN_STORY":
            return {
                "state": "SPATIAL_DENY",
                "gate": "CLASSIFY_ENCLOSURE_AND_STORY",
                "violation": "UNKNOWN_SPATIAL_AXES",
                "placement": placement,
                "execute_allowed": False,
                "proof_ceiling": cfg["proof_ceiling"],
            }
        f1 = floor_tile_present(model, enclosure="INSIDE", story="FLOOR_1")
        if sty == "FLOOR_2" and not f1:
            return {
                "state": "SPATIAL_DENY",
                "gate": "BUILD_ORDER_FLOOR1_BEFORE_FLOOR2",
                "violation": "FLOOR2_BEFORE_FLOOR1",
                "placement": placement,
                "floor_1_present": False,
                "execute_allowed": False,
                "proof_ceiling": cfg["proof_ceiling"],
            }
        if sty == "FLOOR_1" and not f1:
            return {
                "state": "SPATIAL_DENY",
                "gate": "BUILD_ORDER_FLOOR1_BEFORE_FLOOR2",
                "violation": "WRONG_STORY",
                "detail": "FLOOR_1 indoor floor missing",
                "placement": placement,
                "execute_allowed": False,
                "proof_ceiling": cfg["proof_ceiling"],
            }
        if sty == "FLOOR_2" and not floor_tile_present(model, enclosure="INSIDE", story="FLOOR_2"):
            return {
                "state": "SPATIAL_DENY",
                "gate": "BUILD_ORDER_FLOOR1_BEFORE_FLOOR2",
                "violation": "WRONG_STORY",
                "detail": "FLOOR_2 indoor floor missing",
                "placement": placement,
                "floor_1_present": True,
                "execute_allowed": False,
                "proof_ceiling": cfg["proof_ceiling"],
            }

    return {
        "state": "SPATIAL_CLASSIFIED",
        "gate": "CLASSIFY_ENCLOSURE_AND_STORY",
        "placement": placement,
        "floor_1_present": floor_tile_present(model, enclosure="INSIDE", story="FLOOR_1"),
        "floor_2_present": floor_tile_present(model, enclosure="INSIDE", story="FLOOR_2"),
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
    }


def build_order_plan(model: Mapping[str, Any]) -> dict:
    """Intelligent build order from classified model gaps."""
    cfg = load_contract()
    if model.get("schema") != MODEL_SCHEMA:
        raise BuildSpatialError("LOT_MODEL_REQUIRED")
    inv = inventory_spatial(model)
    f1 = floor_tile_present(model, enclosure="INSIDE", story="FLOOR_1")
    f2 = floor_tile_present(model, enclosure="INSIDE", story="FLOOR_2")
    entities = _entities(model)
    steps: list[dict] = []

    def _missing(kind: str, enclosure: str, story: str) -> bool:
        for eid, ent in entities.items():
            if str(ent.get("kind") or "") != kind:
                continue
            row = classify_entity({**ent, "id": eid}, cfg=cfg)
            if row["enclosure"] == enclosure and row["story"] == story:
                if str(ent.get("status") or "").upper() in {"MISSING", "ABSENT", "STRIPPED", "PARTIAL"}:
                    return True
        return False

    if not f1 or _missing("FLOOR_TILE", "INSIDE", "FLOOR_1"):
        steps.append({
            "step": "FLOOR_1_STRUCTURE",
            "action": "PLACE_FLOOR_TILES",
            "enclosure": "INSIDE",
            "story": "FLOOR_1",
            "gate": "BUILD_ORDER_FLOOR1_BEFORE_FLOOR2",
        })
    # F1 indoor furniture gaps only after F1 floor
    if f1:
        for kind, action in (
            ("WALL_SEGMENT", "PLACE_WALL_SEGMENTS"),
            ("DINING_TABLE", "PLACE_DINING_SET"),
            ("SLEEP_POD", "PLACE_SLEEP_POD"),
            ("BED", "PLACE_BED"),
            ("APPLIANCE", "RESTORE_KITCHEN_OBJECTS"),
        ):
            if _missing(kind, "INSIDE", "FLOOR_1"):
                steps.append({
                    "step": "FLOOR_1_INDOOR_FURNITURE",
                    "action": action,
                    "enclosure": "INSIDE",
                    "story": "FLOOR_1",
                    "kind": kind,
                    "gate": "CLASSIFY_ENCLOSURE_AND_STORY",
                })
    # F2 only after F1
    wants_f2 = any(
        classify_entity({**ent, "id": eid}, cfg=cfg)["story"] == "FLOOR_2"
        for eid, ent in entities.items()
    ) or any("FLOOR_2" in str(g).upper() or "SECOND" in str(g).upper() for g in (model.get("open_goals") or []))
    if wants_f2:
        if not f1:
            steps.append({
                "step": "FLOOR_1_STRUCTURE",
                "action": "PLACE_FLOOR_TILES",
                "enclosure": "INSIDE",
                "story": "FLOOR_1",
                "gate": "BUILD_ORDER_FLOOR1_BEFORE_FLOOR2",
                "reason": "FLOOR2_BEFORE_FLOOR1_BLOCKED",
            })
        elif not f2 or _missing("FLOOR_TILE", "INSIDE", "FLOOR_2"):
            steps.append({
                "step": "FLOOR_2_STRUCTURE",
                "action": "PLACE_FLOOR_TILES",
                "enclosure": "INSIDE",
                "story": "FLOOR_2",
                "gate": "BUILD_ORDER_FLOOR1_BEFORE_FLOOR2",
            })
        elif f2:
            for kind, action in (
                ("WALL_SEGMENT", "PLACE_WALL_SEGMENTS"),
                ("BED", "PLACE_BED"),
                ("SLEEP_POD", "PLACE_SLEEP_POD"),
            ):
                if _missing(kind, "INSIDE", "FLOOR_2"):
                    steps.append({
                        "step": "FLOOR_2_INDOOR_FURNITURE",
                        "action": action,
                        "enclosure": "INSIDE",
                        "story": "FLOOR_2",
                        "kind": kind,
                        "gate": "CLASSIFY_ENCLOSURE_AND_STORY",
                    })

    outdoor_floaters = [
        eid for eid in inv["buckets"]["OUTSIDE"]["UNKNOWN_STORY"]
        + inv["buckets"]["OUTSIDE"]["FLOOR_1"]
        + inv["buckets"]["OUTSIDE"]["FLOOR_2"]
        if str((_entities(model).get(eid) or {}).get("kind")) == "FLOATER"
    ]
    if outdoor_floaters:
        steps.append({
            "step": "OUTDOOR_LOT_OBJECTS",
            "action": "BACKSPACE_TO_INVENTORY",
            "enclosure": "OUTSIDE",
            "story": "UNKNOWN_STORY",
            "targets": outdoor_floaters[:8],
            "gate": "OUTSIDE_NOT_INSIDE",
        })

    # De-dupe consecutive identical FLOOR_1_STRUCTURE
    deduped: list[dict] = []
    seen = set()
    for step in steps:
        key = (step.get("step"), step.get("action"), step.get("story"), step.get("kind"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(step)

    if not deduped:
        return {
            "state": "BUILD_ORDER_PLAN",
            "gate": "CLASSIFY_ENCLOSURE_AND_STORY",
            "steps": [],
            "primary": None,
            "inventory": inv,
            "reason": "NO_SPATIAL_GAPS",
            "proof_ceiling": cfg["proof_ceiling"],
        }
    return {
        "state": "BUILD_ORDER_PLAN",
        "gate": deduped[0].get("gate") or "BUILD_ORDER_FLOOR1_BEFORE_FLOOR2",
        "steps": deduped,
        "primary": deduped[0],
        "inventory": inv,
        "floor_1_present": f1,
        "floor_2_present": f2,
        "proof_ceiling": cfg["proof_ceiling"],
        "forbidden": list(cfg.get("forbidden") or []),
    }
