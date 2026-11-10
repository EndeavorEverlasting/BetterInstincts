"""Capture-bound spatial perception for the Sims host (P95 + P67/P62).

Consumes detections, not an IDE/browser API. A 2-D overlap never proves
physical support, room membership, or a safe game click. No SendInput or IO.
"""
from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

from betterinstincts.scenes import classify, load_catalog

SCHEMA = "betterinstincts.spatial-perception.frame/v1"
REPORT_SCHEMA = "betterinstincts.spatial-perception.report/v1"
TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")
MAX_OBJECTS = 48
MAX_CONTACTS = 96
MIN_CONFIDENCE = 0.70
PROOF = "OFFLINE_SUPPLIED_DETECTIONS_NOT_PIXEL_RECOGNITION_OR_LIVE_GAME_CERT"

# Structural categories are intentionally not synonyms. A gate is a passage,
# a wall is an enclosure, and a fence is neither proof of house interior.
KINDS = frozenset({
    "PLANT", "PLANTER", "HYDROPONIC_PLANTER", "CHAIR", "DESK", "COUNTER",
    "LAPTOP", "COMPUTER", "DEVICE", "WALL", "FENCE", "GATE", "DOOR",
    "WINDOW", "WALL_MOUNT", "TOILET_PAPER", "BROOM", "APPLIANCE",
    "FLOOR", "ROOF", "UNKNOWN",
})
CONTACTS = {
    ("PLANT", "PLANTER"): "GROWS_IN",
    ("PLANT", "HYDROPONIC_PLANTER"): "GROWS_IN",
    ("LAPTOP", "DESK"): "RESTS_ON",
    ("LAPTOP", "COUNTER"): "RESTS_ON",
    ("COMPUTER", "DESK"): "RESTS_ON",
    ("DEVICE", "COUNTER"): "RESTS_ON",
    ("DEVICE", "DESK"): "RESTS_ON",
    ("CHAIR", "DESK"): "SEATED_AT",
    ("CHAIR", "COUNTER"): "SEATED_AT",
    ("TOILET_PAPER", "WALL"): "ATTACHED_TO",
    ("WALL_MOUNT", "WALL"): "ATTACHED_TO",
    ("BROOM", "WALL"): "ADJACENT_TO",
}
SOURCES = frozenset({"HOST_CV", "GAME_MODEL", "OPERATOR_REVIEW"})
GEOMETRY_SOURCES = frozenset({"EA_SAVE_GEOMETRY", "OPERATOR_REVIEW"})


class SpatialPerceptionError(ValueError):
    """Malformed or untrusted observations; never extrapolate controls."""


def _token(value: object) -> bool:
    return isinstance(value, str) and TOKEN.fullmatch(value) is not None


def _box(value: object, width: int, height: int) -> tuple[int, int, int, int]:
    if (not isinstance(value, (list, tuple)) or len(value) != 4
            or any(type(n) is not int for n in value)):
        raise SpatialPerceptionError("OBJECT_BBOX_INVALID")
    x0, y0, x1, y1 = value
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise SpatialPerceptionError("OBJECT_BBOX_OUT_OF_FRAME")
    return x0, y0, x1, y1


def _overlap(a: Sequence[int], b: Sequence[int]) -> float:
    w = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    h = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return (w * h) / min((a[2]-a[0]) * (a[3]-a[1]),
                         (b[2]-b[0]) * (b[3]-b[1]))


def _polygon(raw: object, width: int, height: int) -> list[tuple[int, int]]:
    if (not isinstance(raw, list) or not 3 <= len(raw) <= 32):
        raise SpatialPerceptionError("REGION_POLYGON_INVALID")
    points = []
    for p in raw:
        if (not isinstance(p, (list, tuple)) or len(p) != 2
                or any(type(n) is not int for n in p)
                or not 0 <= p[0] <= width or not 0 <= p[1] <= height):
            raise SpatialPerceptionError("REGION_POLYGON_INVALID")
        points.append((p[0], p[1]))
    if len(set(points)) < 3:
        raise SpatialPerceptionError("REGION_POLYGON_DEGENERATE")
    twice_area = sum(
        x * points[(i+1) % len(points)][1] -
        points[(i+1) % len(points)][0] * y
        for i, (x, y) in enumerate(points)
    )
    if twice_area == 0:
        raise SpatialPerceptionError("REGION_POLYGON_DEGENERATE")
    return points


def _contains(poly: Sequence[tuple[int, int]], point: tuple[float, float]) -> bool:
    """Ray casting with boundary inclusion (edge touch is inside)."""
    px, py = point
    inside = False
    for i, (ax, ay) in enumerate(poly):
        bx, by = poly[(i+1) % len(poly)]
        cross = (px-ax)*(by-ay) - (py-ay)*(bx-ax)
        if abs(cross) < 1e-7 and min(ax, bx) <= px <= max(ax, bx) and min(ay, by) <= py <= max(ay, by):
            return True
        if (ay > py) != (by > py):
            ix = ax + (py-ay)*(bx-ax)/(by-ay)
            if px < ix:
                inside = not inside
    return inside


def _regions(frame: Mapping, width: int, height: int) -> dict:
    raw = frame.get("regions")
    if raw is None:
        return {}
    if not isinstance(raw, Mapping) or set(raw) - {"lot", "house"}:
        raise SpatialPerceptionError("REGIONS_INVALID")
    out = {}
    for name in ("lot", "house"):
        if name not in raw:
            continue
        item = raw[name]
        if (not isinstance(item, Mapping)
                or item.get("source") not in GEOMETRY_SOURCES
                or item.get("camera_revision") != frame["camera_revision"]
                or not _token(item.get("evidence_ref"))):
            raise SpatialPerceptionError("REGION_PROVENANCE_OR_CAMERA_STALE")
        out[name] = _polygon(item.get("polygon"), width, height)
    if "house" in out and "lot" not in out:
        raise SpatialPerceptionError("HOUSE_WITHOUT_LOT_GEOMETRY")
    if "house" in out and any(not _contains(out["lot"], p) for p in out["house"]):
        raise SpatialPerceptionError("HOUSE_POLYGON_OUTSIDE_LOT")
    return out


def _zone(obj: Mapping, regions: Mapping, off_lot: bool) -> str:
    if off_lot:
        return "OFF_ACTIVE_LOT"
    if not regions:
        return "UNVERIFIED"
    b = obj["bbox"]
    c = ((b[0]+b[2])/2, (b[1]+b[3])/2)
    if not _contains(regions["lot"], c):
        return "OUTSIDE_ACTIVE_LOT"
    if "house" not in regions:
        return "ON_LOT_HOUSE_UNKNOWN"
    return "HOUSE_FOOTPRINT" if _contains(regions["house"], c) else "YARD_OR_OPEN_LOT"


def assess_frame(frame: Mapping[str, Any]) -> dict[str, Any]:
    """Classify supplied detections and qualified relations; *never* admit input.

    Coordinates are camera-revision-bound screen projections, NOT world xyz.
    A caller may provide independently reviewed regions/contacts. A CV box
    alone cannot establish physical nesting, wall attachment or house interior.
    """
    if not isinstance(frame, Mapping) or frame.get("schema") != SCHEMA:
        raise SpatialPerceptionError("FRAME_SCHEMA_INVALID")
    if (frame.get("source") != "HOST_CAPTURE"
            or not _token(frame.get("capture_ref"))
            or not _token(frame.get("camera_revision"))
            or not _token(frame.get("active_lot_id"))
            or not _token(frame.get("observed_lot_id"))):
        raise SpatialPerceptionError("FRAME_PROVENANCE_INCOMPLETE")
    width, height = frame.get("width"), frame.get("height")
    if (type(width) is not int or type(height) is not int or
            not 320 <= width <= 4096 or not 240 <= height <= 4096
            or width * height > 16_000_000):
        raise SpatialPerceptionError("FRAME_DIMENSIONS_INVALID")

    catalog = load_catalog()
    if frame.get("game_version") != catalog["game_version"]:
        return {
            "schema": REPORT_SCHEMA, "state": "UNKNOWN_PATCH",
            "scene_state": "UNVERIFIED", "scene_id": "unknown",
            "objects": [], "relations": [], "conflicts": [],
            "camera_side": "UNVERIFIED", "execute_allowed": False,
            "proof_ceiling": PROOF,
        }

    cues = frame.get("scene_cues", [])
    try:
        scene = classify(catalog, frame["game_version"], cues)
    except (ValueError, TypeError, KeyError) as exc:
        raise SpatialPerceptionError("SCENE_CUES_INVALID") from exc
    scene_ok = (scene["state"] == "CANDIDATE_UNVERIFIED"
                and scene["scene_id"] == frame.get("scene_id"))
    source_objects = frame.get("objects", [])
    if not isinstance(source_objects, list) or len(source_objects) > MAX_OBJECTS:
        raise SpatialPerceptionError("OBJECT_BUDGET_INVALID")
    objects = []
    ids = set()
    for entry in source_objects:
        if not isinstance(entry, Mapping):
            raise SpatialPerceptionError("OBJECT_INVALID")
        obj_id, kind = entry.get("id"), entry.get("kind")
        conf, source = entry.get("confidence"), entry.get("source")
        if (not _token(obj_id) or obj_id in ids or kind not in KINDS
                or source not in SOURCES or not _token(entry.get("evidence_ref"))
                or type(conf) not in (int, float) or not math.isfinite(conf)
                or not 0 <= conf <= 1
                or entry.get("camera_revision") != frame["camera_revision"]):
            raise SpatialPerceptionError("OBJECT_EVIDENCE_INVALID")
        ids.add(obj_id)
        objects.append({
            "id": obj_id, "kind": kind, "bbox": list(_box(entry.get("bbox"), width, height)),
            "confidence": conf, "source": source,
            "evidence_ref": entry["evidence_ref"],
            "classification": "CANDIDATE" if conf >= MIN_CONFIDENCE and kind != "UNKNOWN" else "UNVERIFIED",
        })
    regions = _regions(frame, width, height)
    off_lot = frame["observed_lot_id"] != frame["active_lot_id"]
    # A screen-side label cannot be inferred from left/right pixels after zoom,
    # rotation or camera drift. Require explicit independently anchored basis.
    camera_side = "UNVERIFIED"
    view = frame.get("view")
    if view is not None:
        if (not isinstance(view, Mapping) or
                view.get("camera_revision") != frame["camera_revision"] or
                view.get("source") not in GEOMETRY_SOURCES or
                not _token(view.get("evidence_ref")) or
                view.get("side") not in {"STREET_SIDE", "CREEK_SIDE", "FRONT", "REAR"}):
            raise SpatialPerceptionError("VIEW_ANCHOR_INVALID")
        camera_side = view["side"]

    for obj in objects:
        obj["zone"] = _zone(obj, regions, off_lot) if scene_ok else "UNVERIFIED"
        if not scene_ok:
            obj["classification"] = "UNVERIFIED"

    # Almost-identical screen footprints labelled both WALL and GATE are
    # contradictory: neither may drive enclosure or attachment inference.
    conflicts = []
    ambiguous = set()
    for i, a in enumerate(objects):
        for b in objects[i+1:]:
            if {a["kind"], b["kind"]} == {"WALL", "GATE"} and _overlap(a["bbox"], b["bbox"]) >= 0.60:
                conflicts.append({"ids": sorted([a["id"], b["id"]]), "reason": "WALL_GATE_CONFLICT"})
                ambiguous.update((a["id"], b["id"]))
    for obj in objects:
        if obj["id"] in ambiguous:
            obj["classification"] = "AMBIGUOUS_STRUCTURE"

    source_contacts = frame.get("contacts", [])
    if not isinstance(source_contacts, list) or len(source_contacts) > MAX_CONTACTS:
        raise SpatialPerceptionError("CONTACT_BUDGET_INVALID")
    known = {obj["id"]: obj for obj in objects}
    contacts = {}
    for row in source_contacts:
        if not isinstance(row, Mapping):
            raise SpatialPerceptionError("CONTACT_INVALID")
        child, parent = row.get("child"), row.get("parent")
        if (child not in known or parent not in known or child == parent
                or row.get("source") not in {"GAME_MODEL", "OPERATOR_REVIEW"}
                or row.get("camera_revision") != frame["camera_revision"]
                or not _token(row.get("evidence_ref"))):
            raise SpatialPerceptionError("CONTACT_EVIDENCE_INVALID")
        expected = CONTACTS.get((known[child]["kind"], known[parent]["kind"]))
        if expected is None or row.get("relation") != expected:
            raise SpatialPerceptionError("CONTACT_TYPE_CONFLICT")
        key = (child, parent)
        if key in contacts:
            raise SpatialPerceptionError("CONTACT_DUPLICATE")
        contacts[key] = row

    relations = []
    for i, a in enumerate(objects):
        for b in objects[i+1:]:
            overlap = _overlap(a["bbox"], b["bbox"])
            if overlap > 0:
                relations.append({"from": a["id"], "to": b["id"], "type": "SCREEN_OVERLAP",
                                  "status": "PROJECTED_2D_ONLY", "overlap_fraction": round(overlap, 3)})
    for child in objects:
        for parent in objects:
            if child["id"] == parent["id"]:
                continue
            kind = CONTACTS.get((child["kind"], parent["kind"]))
            if kind is None:
                continue
            attested = (child["id"], parent["id"]) in contacts
            if not attested and _overlap(child["bbox"], parent["bbox"]) <= 0:
                continue
            safe = (scene_ok and not off_lot
                    and child["classification"] == "CANDIDATE"
                    and parent["classification"] == "CANDIDATE")
            relations.append({
                "from": child["id"], "to": parent["id"], "type": kind,
                "status": "SUPPLIED_CONTACT_EVIDENCE" if (attested and safe) else "GEOMETRY_HYPOTHESIS",
                "attested": bool(attested and safe),
            })
    if not scene_ok:
        state = "SCENE_UNVERIFIED"
    elif off_lot:
        state = "OFF_ACTIVE_LOT"
    elif conflicts:
        state = "STRUCTURE_AMBIGUOUS"
    elif not regions:
        state = "TOPOLOGY_UNVERIFIED"
    else:
        state = "CANDIDATE_TOPOLOGY"
    return {
        "schema": REPORT_SCHEMA, "state": state,
        "scene_state": scene["state"] if scene_ok else "UNVERIFIED",
        "scene_id": scene["scene_id"] if scene_ok else "unknown",
        "capture_ref": frame["capture_ref"],
        "camera_revision": frame["camera_revision"], "camera_side": camera_side,
        "active_lot_id": frame["active_lot_id"], "observed_lot_id": frame["observed_lot_id"],
        "objects": objects, "relations": relations, "conflicts": conflicts,
        "execute_allowed": False, "control_permit": None,
        "next_gate": "LIVE_IMAGE_DETECTOR_AND_REVIEWED_LOT_GEOMETRY" if state != "OFF_ACTIVE_LOT" else "RECENTER_AND_REOBSERVE",
        "proof_ceiling": PROOF,
    }
