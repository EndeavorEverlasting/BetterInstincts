"""Read-only, multi-label room/object census of an attested revisioned lot model.

P95: bounded call stack over house_state; P124: no second house model or daemon.
A grouped zone is NOT a geometrically certified room without a ROOM_ZONE claim.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
from typing import Mapping

from betterinstincts.build_spatial import classify_entity, load_contract as load_spatial_contract, normalize_story

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "room-census.v1.json"
MAX_CONTRACT_BYTES = 32_000
FLOOR_PATTERN = re.compile(r"^(?:FLOOR_[1-9][0-9]?|BASEMENT_[1-9][0-9]?)$")
ZONE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_.-]{0,59}$")
SOURCE_SCHEMA = "betterinstincts.lot-environment-model/v1"


class RoomCensusError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_CONTRACT_BYTES:
        raise RoomCensusError("ROOM_CENSUS_CONTRACT_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.room-census/v1":
        raise RoomCensusError("ROOM_CENSUS_SCHEMA_INVALID")
    if cfg.get("architecture") != "READ_ONLY_REVISIONED_ROOM_PROJECTION":
        raise RoomCensusError("ROOM_CENSUS_MUST_REUSE_HOUSE_STATE")
    if not cfg.get("functional_labels") or not cfg.get("style_labels"):
        raise RoomCensusError("ROOM_CENSUS_TAXONOMY_MISSING")
    return cfg


def _story(raw: object) -> str:
    canonical = normalize_story(raw)
    if canonical != "UNKNOWN_STORY":
        return canonical
    value = str(raw or "").strip().upper().replace(" ", "_")
    return value if FLOOR_PATTERN.fullmatch(value) else "UNKNOWN_STORY"


def _enclosure(entity: Mapping, spatial_contract: Mapping) -> str:
    # The existing spatial authority owns the two canonical axes.
    value = classify_entity(entity, cfg=spatial_contract).get("enclosure", "UNKNOWN_ENCLOSURE")
    return value if value in {"INSIDE", "OUTSIDE"} else "UNKNOWN_ENCLOSURE"


def _zone(raw: object) -> str | None:
    value = str(raw or "").strip().upper()
    return value if ZONE_PATTERN.fullmatch(value) else None


def _tags(raw: object, allowed: set[str], cap: int) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, (list, tuple)) or len(raw) > cap:
        raise RoomCensusError("ROOM_STYLE_TAGS_INVALID")
    if any(not isinstance(x, str) for x in raw):
        raise RoomCensusError("ROOM_STYLE_TAGS_INVALID")
    return sorted({x.strip().lower().replace("-", "_").replace(" ", "_")
                   for x in raw if x.strip().lower().replace("-", "_").replace(" ", "_") in allowed})


def _sort_story(value: str) -> tuple[int, int]:
    if value.startswith("BASEMENT_"):
        return (0, -int(value.split("_")[1]))
    if value.startswith("FLOOR_"):
        return (1, int(value.split("_")[1]))
    return (2, 0)


def scan_lot_model(model: Mapping, *, cfg: dict | None = None) -> dict:
    """Inventory every attested story/zone. Never asserts complete lot coverage."""
    cfg = cfg or load_contract()
    if not isinstance(model, Mapping) or model.get("schema") != SOURCE_SCHEMA:
        raise RoomCensusError("LOT_MODEL_REQUIRED")
    revision = model.get("revision")
    if type(revision) is not int or revision < 0:
        raise RoomCensusError("LOT_MODEL_REVISION_INVALID")
    entities = model.get("entities")
    if not isinstance(entities, Mapping) or len(entities) > cfg["bounds"]["max_entities"]:
        raise RoomCensusError("ROOM_CENSUS_ENTITIES_INVALID")
    spatial_contract = load_spatial_contract()  # Once per scan, not once per object.
    max_tags = cfg["bounds"]["max_labels_per_item"]
    styles = set(cfg["style_labels"])
    funcs = set(cfg["functional_labels"])
    groups: dict[tuple[str, str], dict] = {}
    unassigned = []
    floor_names: set[str] = set()
    for key, entity in sorted(entities.items()):
        if not isinstance(key, str) or not isinstance(entity, Mapping):
            raise RoomCensusError("ROOM_CENSUS_ENTITY_INVALID")
        if entity.get("status", "PRESENT") not in {"PRESENT", "OBSERVED"}:
            continue
        story = _story(entity.get("story") or entity.get("floor_level"))
        zone = _zone(entity.get("zone"))
        enclosure = _enclosure(entity, spatial_contract)
        kind = str(entity.get("kind") or "UNKNOWN_OBJECT").upper()
        if story != "UNKNOWN_STORY":
            floor_names.add(story)
        if story == "UNKNOWN_STORY" or zone is None:
            if kind != "SIM":
                unassigned.append({"item_id": key, "reason": "UNKNOWN_STORY" if story == "UNKNOWN_STORY" else "UNKNOWN_ZONE"})
            continue
        pair = (story, zone)
        room = groups.setdefault(pair, {"story": story, "zone": zone, "structure_claims": [],
                                        "items": [], "enclosures": set(), "functions": Counter(), "styles": Counter()})
        if enclosure != "UNKNOWN_ENCLOSURE":
            room["enclosures"].add(enclosure)
        if kind == "ROOM_ZONE":
            room["structure_claims"].append({"id": key, "confidence": entity.get("confidence", "UNKNOWN")})
            continue
        if kind in {"WALL_SEGMENT", "FLOOR_TILE", "ROOF_PIECE", "SIM"}:
            continue
        category = str(entity.get("category") or cfg["kind_to_category"].get(kind, "unknown")).strip().lower().replace("-", "_").replace(" ", "_")
        functional = list(cfg["category_to_functions"].get(category, []))
        # Object-level function tags are explicit observations, not guessed room names.
        functional += _tags(entity.get("function_tags"), funcs, max_tags)
        functional = sorted(set(functional))
        aesthetic = _tags(entity.get("style_tags"), styles, max_tags)
        for t in functional:
            room["functions"][t] += 1
        for t in aesthetic:
            room["styles"][t] += 1
        room["items"].append({"id": key, "label": str(entity.get("label") or key)[:120],
                              "kind": kind, "category": category, "functions": functional,
                              "styles": aesthetic, "confidence": entity.get("confidence", "UNKNOWN")})
    if len(groups) > cfg["bounds"]["max_rooms"]:
        raise RoomCensusError("ROOM_CENSUS_ROOM_LIMIT_EXCEEDED")
    floors: dict[str, dict] = {name: {"story": name, "rooms": [], "item_count": 0}
                               for name in sorted(floor_names, key=_sort_story)}
    rooms: dict[str, dict] = {}
    for (story, zone), data in sorted(groups.items(), key=lambda row: (_sort_story(row[0][0]), row[0][1])):
        structural = any(c["confidence"] in {"OPERATOR_ATTESTED", "LOCAL_OBSERVED", "GAME_CERTIFIED"}
                         for c in data["structure_claims"])
        enclosures = data["enclosures"]
        enclosure = next(iter(enclosures)) if len(enclosures) == 1 else "UNKNOWN_ENCLOSURE"
        room_id = f"{story}:{zone}"
        def ranking(hist: Counter) -> list[dict]:
            return [{"label": name, "item_count": count} for name, count in
                    sorted(hist.items(), key=lambda entry: (-entry[1], entry[0]))]
        row = {"room_id": room_id, "story": story, "zone": zone,
               "room_evidence": "STRUCTURE_ATTESTED" if structural else "ZONE_CANDIDATE",
               "enclosure": enclosure, "enclosure_conflict": len(enclosures) > 1,
               "item_count": len(data["items"]), "items": data["items"],
               "functions": ranking(data["functions"]), "styles": ranking(data["styles"]),
               "function_labels": [x["label"] for x in ranking(data["functions"])],
               "style_labels": [x["label"] for x in ranking(data["styles"])],
               "classification": "MULTI_LABEL_NOT_EXCLUSIVE"}
        rooms[room_id] = row
        floors[story]["rooms"].append(room_id)
        floors[story]["item_count"] += row["item_count"]
    return {"state": "ROOM_CENSUS_EVALUATED", "architecture": cfg["architecture"],
            "lot_id": model.get("lot_id"), "model_revision": revision,
            "floors": floors, "rooms": rooms, "unassigned_items": unassigned,
            "observed_story_count": len(floors), "coverage": "ATTESTED_OBSERVATIONS_ONLY_NOT_COMPLETE_FLOOR_PROOF",
            "execute_allowed": False, "proof_ceiling": cfg["proof_ceiling"]}

def summarize_for_listener(census: Mapping) -> dict:
    """Compact advisory receipt; full item inventory stays in explicit scan result."""
    return {
        "state": census["state"],
        "model_revision": census["model_revision"],
        "observed_story_count": census["observed_story_count"],
        "coverage": census["coverage"],
        "floors": {
            story: {"room_count": len(row["rooms"]), "item_count": row["item_count"]}
            for story, row in census["floors"].items()
        },
        "rooms": [
            {"room_id": r["room_id"], "enclosure": r["enclosure"],
             "room_evidence": r["room_evidence"], "item_count": r["item_count"],
             "function_labels": r["function_labels"], "style_labels": r["style_labels"]}
            for r in census["rooms"].values()
        ][:100],
        "room_count_total": len(census["rooms"]),
        "summary_truncated": len(census["rooms"]) > 100,
        "unassigned_count": len(census["unassigned_items"]),
        "execute_allowed": False,
        "proof_ceiling": census["proof_ceiling"],
    }
