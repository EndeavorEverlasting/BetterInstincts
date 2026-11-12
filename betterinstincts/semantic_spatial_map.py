"""Sparse semantic 3D map and camera-local relocalization for Sims world objects.

The Y axis means world elevation; viewport client XY is a different coordinate
system. No single screenshot is taken as proof of height or metric 3D pose.
This module has no screenshot adapter, input hooks, persistence or game effects.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "semantic-spatial-map.v1.json"
PROOF = "OFFLINE_SEMANTIC_3D_AND_AFFINE_CAMERA_PROJECTION_NOT_LIVE_SLAM_OR_CLICK_CERT"


class SemanticSpatialError(ValueError):
    """Invalid evidence, inconsistent geometry or unsuitable calibration."""


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32_768:
        raise SemanticSpatialError("UNSAFE_SPATIAL_CONTRACT")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.semantic-spatial-map/v1":
        raise SemanticSpatialError("INVALID_SPATIAL_SCHEMA")
    if cfg.get("execute_allowed_default") is not False:
        raise SemanticSpatialError("EXECUTION_AUTHORITY_FORBIDDEN")
    return cfg


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise SemanticSpatialError("INVALID_" + field)
    return value.strip()


def _vector(value: object, width: int, field: str) -> tuple[float, ...]:
    if not isinstance(value, (list, tuple)) or len(value) != width:
        raise SemanticSpatialError("INVALID_" + field)
    if any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 100000 for v in value):
        raise SemanticSpatialError("INVALID_" + field)
    return tuple(float(v) for v in value)


def _bounds(item: Mapping[str, object]) -> tuple[tuple[float, ...], tuple[float, ...]]:
    center = item["center"]
    size = item["size"]
    return (tuple(c - s / 2 for c, s in zip(center, size)),
            tuple(c + s / 2 for c, s in zip(center, size)))


def _overlap(lo1: float, hi1: float, lo2: float, hi2: float, tolerance: float = 0.0) -> bool:
    return min(hi1, hi2) + tolerance >= max(lo1, lo2)


def _validate_relation(child: dict, parent: dict, relation: str, tolerance: float) -> None:
    if child["floor_id"] != parent["floor_id"]:
        raise SemanticSpatialError("CROSS_FLOOR_RELATION_UNPROVEN")
    if child["center"] is None or parent["center"] is None:
        raise SemanticSpatialError("RELATION_REQUIRES_3D_POSES")
    (cl, ch), (pl, ph) = _bounds(child), _bounds(parent)
    planar_overlap = (_overlap(cl[0], ch[0], pl[0], ph[0], tolerance) and
                      _overlap(cl[2], ch[2], pl[2], ph[2], tolerance))
    if relation == "ON_TOP_OF":
        if not planar_overlap or abs(cl[1] - ph[1]) > tolerance:
            raise SemanticSpatialError("SUPPORT_GEOMETRY_CONFLICT")
    elif relation == "INSIDE":
        if any(cl[i] < pl[i] - tolerance or ch[i] > ph[i] + tolerance for i in range(3)):
            raise SemanticSpatialError("CONTAINMENT_GEOMETRY_CONFLICT")
    elif relation == "BESIDE":
        x_gap = max(pl[0] - ch[0], cl[0] - ph[0], 0)
        z_gap = max(pl[2] - ch[2], cl[2] - ph[2], 0)
        if not _overlap(cl[1], ch[1], pl[1], ph[1]) or (x_gap == 0 and z_gap == 0) or math.hypot(x_gap, z_gap) > 1.0:
            raise SemanticSpatialError("BESIDE_GEOMETRY_CONFLICT")
    elif relation == "WALL_MOUNTED_TO":
        if parent["category"] != "WALL" or not planar_overlap or cl[1] < pl[1] - tolerance or ch[1] > ph[1] + tolerance:
            raise SemanticSpatialError("WALL_MOUNT_GEOMETRY_CONFLICT")
    else:
        raise SemanticSpatialError("UNKNOWN_SPATIAL_RELATION")


def compile_spatial_map(
    *,
    lot_id: str,
    game_build: str,
    observations: Sequence[Mapping[str, object]],
    relations: Sequence[Mapping[str, object]] = (),
    cfg: Mapping[str, object] | None = None,
) -> dict:
    """Validate supplied world poses; never manufacture depth from screen pixels.

    world geometry is admitted from explicit EA read-only extraction or a
    separately calibrated multiview source, not an agent guess or lone image.
    """
    cfg = dict(cfg or load_contract())
    lot = _text(lot_id, "LOT_ID")
    build = _text(game_build, "GAME_BUILD")
    limit = int(cfg["limits"]["max_objects"])
    if not isinstance(observations, (list, tuple)) or len(observations) > limit:
        raise SemanticSpatialError("OBJECT_BUDGET_EXCEEDED")
    objects: dict[str, dict] = {}
    for raw in observations:
        if not isinstance(raw, Mapping):
            raise SemanticSpatialError("INVALID_OBJECT_OBSERVATION")
        oid = _text(raw.get("object_id"), "OBJECT_ID")
        if oid in objects:
            raise SemanticSpatialError("DUPLICATE_OBJECT_ID")
        floor = _text(raw.get("floor_id"), "FLOOR_ID")
        if not (floor == "OUTSIDE" or floor.startswith("FLOOR_") or floor.startswith("BASEMENT_")):
            raise SemanticSpatialError("UNKNOWN_FLOOR")
        category = _text(raw.get("category"), "CATEGORY").upper()
        if not category.replace("_", "").isalnum():
            raise SemanticSpatialError("INVALID_CATEGORY")
        identity = str(raw.get("identity_source") or "UNVERIFIED")
        confidence = raw.get("category_confidence")
        if type(confidence) not in (int, float) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise SemanticSpatialError("INVALID_CLASS_CONFIDENCE")
        if identity not in cfg["evidence"]["identity_sources"] or confidence < cfg["limits"]["min_category_confidence"]:
            category = "UNKNOWN_OBJECT"
        pose_source = str(raw.get("pose_source") or "NONE")
        if pose_source not in cfg["evidence"]["pose_sources"]:
            raise SemanticSpatialError("UNTRUSTED_POSE_SOURCE")
        center = size = None
        pose_refs = raw.get("pose_refs") or []
        if pose_source != "NONE":
            center = _vector(raw.get("world_center_xyz"), 3, "WORLD_CENTER")
            size = _vector(raw.get("world_size_xyz"), 3, "WORLD_SIZE")
            if any(s <= 0 or s > 100 for s in size):
                raise SemanticSpatialError("WORLD_SIZE_OUT_OF_BOUNDS")
            if not isinstance(pose_refs, (list, tuple)) or not all(isinstance(p, str) and p.strip() for p in pose_refs):
                raise SemanticSpatialError("POSE_REFS_REQUIRED")
            if pose_source == "EA_READ_ONLY" and len(pose_refs) < 1:
                raise SemanticSpatialError("EA_POSE_PROVENANCE_REQUIRED")
            if pose_source == "CALIBRATED_MULTIVIEW" and len(set(pose_refs)) < 2:
                raise SemanticSpatialError("MULTIVIEW_POSE_REFS_REQUIRED")
            if raw.get("pose_build") != build:
                raise SemanticSpatialError("STALE_GAME_BUILD_POSE")
        elif raw.get("world_center_xyz") is not None or raw.get("world_size_xyz") is not None:
            raise SemanticSpatialError("UNSUPPORTED_3D_FROM_2D")
        objects[oid] = {
            "object_id": oid, "category": category, "floor_id": floor,
            "center": center, "size": size, "pose_source": pose_source,
            "pose_refs": list(pose_refs), "vertical_adjustable": raw.get("vertical_adjustable") is True,
        }

    if not isinstance(relations, (list, tuple)) or len(relations) > cfg["limits"]["max_relations"]:
        raise SemanticSpatialError("RELATION_BUDGET_EXCEEDED")
    links = []
    for raw in relations:
        if not isinstance(raw, Mapping):
            raise SemanticSpatialError("INVALID_RELATION")
        child_id = _text(raw.get("child_id"), "CHILD_ID")
        parent_id = _text(raw.get("parent_id"), "PARENT_ID")
        relation = _text(raw.get("relation"), "RELATION")
        if child_id == parent_id or child_id not in objects or parent_id not in objects:
            raise SemanticSpatialError("RELATION_ENDPOINT_INVALID")
        if raw.get("evidence_source") not in cfg["evidence"]["relation_sources"] or not raw.get("evidence_ref"):
            raise SemanticSpatialError("RELATION_SOURCE_UNPROVEN")
        _validate_relation(objects[child_id], objects[parent_id], relation, cfg["limits"]["geometry_tolerance_world"])
        links.append({"child_id": child_id, "parent_id": parent_id,
                      "relation": relation, "evidence_source": raw["evidence_source"],
                      "evidence_ref": str(raw["evidence_ref"])})
    # Structural containment/support cycles are nonsensical even if bounding boxes overlap.
    parents = {oid: [] for oid in objects}
    for edge in links:
        if edge["relation"] in {"ON_TOP_OF", "INSIDE", "WALL_MOUNTED_TO"}:
            parents[edge["child_id"]].append(edge["parent_id"])
    def visit(node: str, path: set[str]) -> None:
        if node in path:
            raise SemanticSpatialError("RELATION_CYCLE")
        for parent in parents[node]:
            visit(parent, path | {node})
    for oid in parents:
        visit(oid, set())
    return {"schema": "betterinstincts.semantic-spatial-map-doc/v1", "lot_id": lot,
            "game_build": build, "objects": objects, "relations": links,
            "execute_allowed": False, "proof_ceiling": PROOF}


def _solve(matrix: list[list[float]], values: list[float]) -> tuple[float, ...]:
    n = len(values)
    augmented = [list(row) + [val] for row, val in zip(matrix, values)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(augmented[r][col]))
        if abs(augmented[pivot][col]) < 1e-8:
            raise SemanticSpatialError("CAMERA_LANDMARKS_DEGENERATE")
        augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        scale = augmented[col][col]
        for j in range(col, n + 1):
            augmented[col][j] /= scale
        for row in range(n):
            if row == col:
                continue
            factor = augmented[row][col]
            for j in range(col, n + 1):
                augmented[row][j] -= factor * augmented[col][j]
    return tuple(augmented[i][-1] for i in range(n))


def calibrate_camera(
    spatial_map: Mapping[str, object],
    *,
    camera_revision: str,
    landmarks: Sequence[Mapping[str, object]],
    cfg: Mapping[str, object] | None = None,
) -> dict:
    """Fit a LOCAL 3D affine camera projection with rank/residual checks.

    This is a measured orthographic approximation, not optical flow, inertial
    odometry, depth reconstruction, or a global perspective camera solution.
    """
    cfg = dict(cfg or load_contract())
    camera = _text(camera_revision, "CAMERA_REVISION")
    if not isinstance(landmarks, (list, tuple)) or not 5 <= len(landmarks) <= cfg["limits"]["max_landmarks"]:
        raise SemanticSpatialError("CAMERA_REQUIRES_FIVE_LANDMARKS")
    seen = set()
    refs = set()
    axes = []
    screen = []
    for mark in landmarks:
        oid = _text(mark.get("object_id"), "LANDMARK_OBJECT_ID")
        if oid in seen or oid not in spatial_map["objects"]:
            raise SemanticSpatialError("DUPLICATE_OR_UNKNOWN_LANDMARK")
        seen.add(oid)
        item = spatial_map["objects"][oid]
        if item["center"] is None:
            raise SemanticSpatialError("LANDMARK_3D_UNPROVEN")
        if mark.get("camera_revision") != camera:
            raise SemanticSpatialError("CAMERA_REVISION_MISMATCH")
        capture = _text(mark.get("capture_ref"), "CAPTURE_REF")
        refs.add(capture)
        if mark.get("source") not in cfg["evidence"]["landmark_sources"]:
            raise SemanticSpatialError("LANDMARK_SOURCE_UNTRUSTED")
        xy = _vector(mark.get("client_xy"), 2, "LANDMARK_CLIENT_XY")
        axes.append(list(item["center"]) + [1.0])
        screen.append(xy)
    if len(refs) < 2:
        raise SemanticSpatialError("LANDMARKS_REQUIRE_DISTINCT_FRAMES")
    n = 4
    normal = [[sum(a[i] * a[j] for a in axes) for j in range(n)] for i in range(n)]
    coeffs = [_solve(normal, [sum(a[i] * xy[k] for a, xy in zip(axes, screen)) for i in range(n)]) for k in range(2)]
    residuals = [math.dist((sum(v * c for v, c in zip(row, coeffs[0])),
                            sum(v * c for v, c in zip(row, coeffs[1]))), xy)
                 for row, xy in zip(axes, screen)]
    rms = math.sqrt(sum(r * r for r in residuals) / len(residuals))
    max_error = max(residuals)
    if max_error > cfg["limits"]["max_projection_error_px"] or rms > cfg["limits"]["max_rms_error_px"]:
        raise SemanticSpatialError("CAMERA_REPROJECTION_UNSTABLE")
    return {"schema": "betterinstincts.semantic-camera-local/v1", "camera_revision": camera,
            "map_fingerprint": _map_fingerprint(spatial_map),
            "capture_refs": sorted(refs), "latest_capture_ref": _text(landmarks[-1]["capture_ref"], "CAPTURE_REF"),
            "coefficients": [list(coeffs[0]), list(coeffs[1])],
            "rms_error_px": round(rms, 6), "max_error_px": round(max_error, 6),
            "landmark_count": len(landmarks), "execute_allowed": False,
            "proof_ceiling": PROOF}


def _map_fingerprint(spatial_map: Mapping[str, object]) -> str:
    """Bind each camera solution to a particular lot/build/geometry snapshot."""
    snapshot = {key: spatial_map.get(key) for key in ("schema", "lot_id", "game_build", "objects", "relations")}
    payload = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def plan_spatial_target(
    spatial_map: Mapping[str, object], calibration: Mapping[str, object] | None,
    *,
    object_id: str, requested_floor: str,
    camera_revision: str, capture_ref: str,
    visibility: Mapping[str, object] | None = None,
) -> dict:
    """Advisory targeting only. An image position is never a click permit."""
    base = {"object_id": object_id, "execute_allowed": False,
            "click_permit": None, "proof_ceiling": PROOF}
    def decline(reason: str, next_gate: str) -> dict:
        return {**base, "state": "ABSTAIN", "reason": reason, "next_gate": next_gate,
                "suggested_client_xy": None}
    obj = spatial_map.get("objects", {}).get(object_id)
    if obj is None:
        return decline("OBJECT_NOT_MAPPED", "DISCOVER_OBJECT")
    if obj["floor_id"] != requested_floor:
        return decline("FLOOR_NOT_ACTIVE", "CHANGE_FLOOR_THEN_REOBSERVE")
    if obj["center"] is None:
        return decline("METRIC_3D_UNPROVEN", "EA_GEOMETRY_OR_CALIBRATED_MULTIVIEW")
    if calibration is None or calibration.get("camera_revision") != camera_revision:
        return decline("STALE_OR_MISSING_CAMERA", "RELOCALIZE_FROM_FRESH_LANDMARKS")
    if calibration.get("map_fingerprint") != _map_fingerprint(spatial_map):
        return decline("STALE_OBJECT_MAP", "REBUILD_SPATIAL_MAP_AND_RELOCALIZE")
    if capture_ref != calibration.get("latest_capture_ref"):
        return decline("STALE_CAPTURE", "RELOCALIZE_FROM_FRESH_LANDMARKS")
    if not isinstance(visibility, Mapping) or visibility.get("object_id") != object_id or visibility.get("capture_ref") != capture_ref or visibility.get("camera_revision") != camera_revision:
        return decline("TARGET_VISIBILITY_UNVERIFIED", "FRESH_TARGET_OBSERVATION")
    if visibility.get("occluded") is True or visibility.get("visible") is not True:
        parent = [r for r in spatial_map.get("relations", []) if r["child_id"] == object_id and r["relation"] == "INSIDE"]
        return decline("TARGET_OCCLUDED", "OPEN_CONTAINER_THEN_REOBSERVE" if parent else "CHANGE_VIEW_THEN_REOBSERVE")
    if visibility.get("ambiguous") is True or visibility.get("target_identity_confirmed") is not True:
        return decline("TARGET_IDENTITY_AMBIGUOUS", "HIGHLIGHT_AND_TARGET_REACQUISITION")
    coeffs = calibration.get("coefficients")
    if (not isinstance(coeffs, list) or len(coeffs) != 2
            or any(not isinstance(row, list) or len(row) != 4 for row in coeffs)):
        return decline("INVALID_CAMERA_MODEL", "RELOCALIZE_FROM_FRESH_LANDMARKS")
    vector = list(obj["center"]) + [1.0]
    xy = [sum(float(c) * v for c, v in zip(row, vector)) for row in coeffs]
    if not all(math.isfinite(n) for n in xy):
        return decline("NONFINITE_PROJECTION", "RELOCALIZE_FROM_FRESH_LANDMARKS")
    bbox = visibility.get("bbox_client")
    try:
        rect = _vector(bbox, 4, "TARGET_BBOX")
    except SemanticSpatialError:
        return decline("TARGET_BBOX_UNVERIFIED", "FRESH_TARGET_OBSERVATION")
    if not (rect[0] < rect[2] and rect[1] < rect[3]):
        return decline("TARGET_BBOX_UNVERIFIED", "FRESH_TARGET_OBSERVATION")
    margin = 8.0 + float(calibration["max_error_px"])
    if not (rect[0] - margin <= xy[0] <= rect[2] + margin and
            rect[1] - margin <= xy[1] <= rect[3] + margin):
        return decline("PROJECTED_POINT_OUTSIDE_TARGET", "RELOCALIZE_AND_REOBSERVE")
    return {**base, "state": "FRAMING_CANDIDATE", "suggested_client_xy": [round(xy[0], 3), round(xy[1], 3)],
            "floor_id": requested_floor, "camera_revision": camera_revision, "capture_ref": capture_ref,
            "requires": ["WORLD_HIGHLIGHT_CONTINUITY", "LOT_BOUNDARY", "SCENE_AND_SAVE_GUARDS",
                         "PLAYER_AND_FOCUS_ADMISSION", "ONE_EFFECT_HOST_PERMIT"],
            "note": "Candidate pixels are not permission to click; apply existing screen_admit independently."}
