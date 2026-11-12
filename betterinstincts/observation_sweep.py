"""Deterministic, zero-first semantic camera reassessment (offline advisory).

No mouse input, synthetic visual inference, Sims state mutation, OS ownership,
auto-discovery or background loop. A host must independently admit any gesture.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:+-]{0,95}$")
SOURCES = frozenset({"EA_LOT_GEOMETRY", "HOST_CALIBRATED", "OPERATOR_VERIFIED"})
PROOF = "OFFLINE_CONTINUOUS_SURVEY_PROPOSAL_NOT_LIVE_CAMERA_CERT"


class ObservationSweepError(ValueError):
    """Reject ambiguous geometry and unsafe inputs without returning control."""


def _id(value: object, label: str) -> str:
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ObservationSweepError("INVALID_" + label)
    return value


def _ids(value: object, label: str, *, limit: int = 64) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or len(value) > limit:
        raise ObservationSweepError("INVALID_" + label)
    result = tuple(_id(item, label) for item in value)
    if len(set(result)) != len(result):
        raise ObservationSweepError("DUPLICATE_" + label)
    return result


def _point(value: object, label: str) -> tuple[int, int]:
    if (not isinstance(value, (list, tuple)) or len(value) != 2
            or any(type(n) is not int for n in value)):
        raise ObservationSweepError("INVALID_" + label)
    return value[0], value[1]


def _result(state: str, *, missing: Sequence[str], **extra: object) -> dict:
    return {
        "schema": "betterinstincts.observation-sweep.plan/v1",
        "state": state,
        "missing_objects": list(missing),
        "gesture_count": 0,
        "movement_policy": "REUSE_OR_STATIONARY_CAPTURE_BEFORE_SINGLE_CONTINUOUS_GESTURE",
        "execute_allowed": False,
        "control_permit": None,
        "proof_ceiling": PROOF,
        **extra,
    }


def plan_observation_sweep(
    *,
    camera_revision: str,
    capture_revision: str,
    floor_id: str,
    required_objects: Sequence[str],
    observed_objects: Sequence[str],
    candidate_views: Sequence[Mapping[str, object]],
    viewport_px: Sequence[int] = (1920, 1080),
    edge_band_px: int = 48,
    previous_view_id: str | None = None,
    player_active: bool = False,
) -> dict:
    """Propose at most ONE smooth camera gesture when grounded novelty warrants it.

    Candidate fields: view_id, floor_id, camera_revision, source,
    evidence_refs (two distinct attested refs), visible_objects, pan_delta_px.
    These are supplied by a separately admitted sensor or EA geometry
    extractor, never inferred from this planner or a screenshot alone.
    """
    rev = _id(camera_revision, "CAMERA_REVISION")
    capture = _id(capture_revision, "CAPTURE_REVISION")
    floor = _id(floor_id, "FLOOR_ID")
    required = _ids(required_objects, "REQUIRED_OBJECTS")
    observed = _ids(observed_objects, "OBSERVED_OBJECTS")
    if not isinstance(candidate_views, (list, tuple)) or len(candidate_views) > 32:
        raise ObservationSweepError("INVALID_CANDIDATE_VIEWS")
    w, h = _point(viewport_px, "VIEWPORT")
    if not (320 <= w <= 7680 and 240 <= h <= 4320):
        raise ObservationSweepError("UNSUPPORTED_VIEWPORT")
    if type(edge_band_px) is not int or not (8 <= edge_band_px < min(w, h) // 4):
        raise ObservationSweepError("INVALID_EDGE_BAND")
    if type(player_active) is not bool:
        raise ObservationSweepError("INVALID_PLAYER_ACTIVE")
    previous = _id(previous_view_id, "PREVIOUS_VIEW_ID") if previous_view_id is not None else None
    missing = tuple(sorted(set(required) - set(observed)))
    if player_active:
        return _result("YIELD_TO_PLAYER", missing=missing, next_gate="PLAYER_RELEASES_CONTROL")
    if rev != capture:
        return _result("HOLD_STALE_CAMERA", missing=missing, next_gate="FRESH_STATIONARY_CAPTURE")
    if not missing:
        return _result("REUSE_OBSERVED_COVERAGE", missing=missing, next_gate="NONE",
                       camera_revision=rev)

    start = (w // 2, h // 2)
    accepted = []
    seen_views: set[str] = set()
    for item in candidate_views:
        if not isinstance(item, Mapping):
            raise ObservationSweepError("INVALID_CANDIDATE_VIEW")
        vid = _id(item.get("view_id"), "VIEW_ID")
        if vid in seen_views:
            raise ObservationSweepError("DUPLICATE_VIEW_ID")
        seen_views.add(vid)
        source = item.get("source")
        if source not in SOURCES:
            raise ObservationSweepError("UNREVIEWED_VIEW_SOURCE")
        if item.get("floor_id") != floor or item.get("camera_revision") != rev:
            continue
        refs = _ids(item.get("evidence_refs"), "EVIDENCE_REFS", limit=8)
        if len(refs) < 2:
            continue
        coverage = set(_ids(item.get("visible_objects"), "VISIBLE_OBJECTS"))
        novel = sorted(coverage.intersection(missing))
        if not novel or vid == previous:
            continue
        dx, dy = _point(item.get("pan_delta_px"), "PAN_DELTA")
        # A large excursion, a stay-on-spot scan, or a screen-edge touch is
        # not silently converted into a multi-hop path or a blind click.
        if abs(dx) > min(240, w // 4) or abs(dy) > min(240, h // 4):
            continue
        end = (start[0] + dx, start[1] + dy)
        if not (edge_band_px <= end[0] < w - edge_band_px
                and edge_band_px <= end[1] < h - edge_band_px):
            continue
        accepted.append((len(novel), dx * dx + dy * dy, vid, dx, dy, novel, source))
    if not accepted:
        return _result("CAPTURE_IN_PLACE", missing=missing,
                       next_gate="REQUEST_NEW_INDEPENDENT_GEOMETRY_OR_CAPTURE",
                       camera_revision=rev, safe_rest_client=list(start))
    # Stable over filesystem ordering, set iteration, candidate arrival and host OS.
    accepted.sort(key=lambda x: (-x[0], x[1], x[2]))
    _, _, vid, dx, dy, novel, source = accepted[0]
    if dx == 0 and dy == 0:
        return _result("CAPTURE_IN_PLACE", missing=missing,
                       next_gate="OBSERVE_CURRENT_VIEW", selected_view_id=vid,
                       safe_rest_client=list(start))
    # One bounded, ease-in/ease-out drag. No chained compass pans, reversals,
    # overshoot, speed guesswork or 2-4 disjoint "arm" gestures.
    waypoints: list[list[int]] = []
    for i in range(13):
        t = i / 12
        eased = t * t * (3 - 2 * t)
        xy = [start[0] + round(dx * eased), start[1] + round(dy * eased)]
        if not waypoints or waypoints[-1] != xy:
            waypoints.append(xy)
    result = _result(
        "ONE_CONTINUOUS_VIEW_PROPOSAL", missing=missing,
        next_gate="HOST_RECHECK_PLAYER_SCENE_SAVE_LOT_BEFORE_AND_AFTER_CAPTURE",
        camera_revision=rev, selected_view_id=vid, predicted_novel_objects=novel,
        source=source, gesture_kind="RIGHT_DRAG_CONTINUOUS_CANDIDATE",
        trajectory_client=waypoints, safe_rest_client=list(start),
        requires_fresh_post_motion_capture=True, repeated_motion_allowed=False,
    )
    result["gesture_count"] = 1
    return result
