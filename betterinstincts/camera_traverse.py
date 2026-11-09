"""Camera-safe host traversal planner (P95).

Stops agents from parking the mouse in the Sims edge-pan band while they
gather lot data or develop. Pure policy — no SendInput, PrintWindow, or
filesystem side effects. Live adapters live under scripts/.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "camera-traverse.v1.json"
MAX_BYTES = 64_000
PROOF_CEILING = "OFFLINE_CAMERA_SAFE_TRAVERSE_NOT_LIVE_CAMERA_PROOF"


class CameraTraverseError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise CameraTraverseError("CAMERA_TRAVERSE_CONTRACT_UNSAFE")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.camera-traverse/v1":
        raise CameraTraverseError("INVALID_CAMERA_TRAVERSE_SCHEMA")
    if data.get("architecture", {}).get("selected") != "CAMERA_SAFE_TRAVERSE":
        raise CameraTraverseError("CAMERA_SAFE_TRAVERSE_REQUIRED")
    forbidden = set(data.get("forbidden") or [])
    if not {
        "EDGE_MOUSE_PARK",
        "CONTINUOUS_EDGE_HOLD",
        "LEAVE_CURSOR_IN_EDGE_BAND",
        "PLAN_WITHOUT_TERMINAL_SAFE_REST",
    }.issubset(forbidden):
        raise CameraTraverseError("EDGE_PARK_GUARDS_MISSING")
    return data


def _defaults(cfg: Mapping[str, object]) -> dict:
    raw = cfg.get("defaults") or {}
    if not isinstance(raw, dict):
        raise CameraTraverseError("CAMERA_TRAVERSE_DEFAULTS_INVALID")
    return dict(raw)


def _geom(
    *,
    client_width: Optional[int],
    client_height: Optional[int],
    edge_band_px: Optional[int],
    cfg: Mapping[str, object],
) -> tuple[int, int, int]:
    d = _defaults(cfg)
    w = int(client_width if client_width is not None else d["client_width"])
    h = int(client_height if client_height is not None else d["client_height"])
    band = int(edge_band_px if edge_band_px is not None else d["edge_band_px"])
    if w < 64 or h < 64 or w * h > 16_000_000:
        raise CameraTraverseError("INVALID_CLIENT_SIZE")
    if band < 1 or band > min(w, h) // 4:
        raise CameraTraverseError("INVALID_EDGE_BAND")
    return w, h, band


def classify_cursor(
    x: int,
    y: int,
    *,
    client_width: Optional[int] = None,
    client_height: Optional[int] = None,
    edge_band_px: Optional[int] = None,
    cfg: Optional[Mapping[str, object]] = None,
) -> dict:
    """Classify a client-relative cursor against the edge pan band."""
    cfg = cfg or load_contract()
    w, h, band = _geom(
        client_width=client_width,
        client_height=client_height,
        edge_band_px=edge_band_px,
        cfg=cfg,
    )
    if isinstance(x, bool) or isinstance(y, bool) or not isinstance(x, int) or not isinstance(y, int):
        raise CameraTraverseError("INVALID_CURSOR")
    in_edge = x < band or y < band or x >= (w - band) or y >= (h - band)
    zone = "EDGE_BAND" if in_edge else "SAFE_INTERIOR"
    return {
        "zone": zone,
        "in_edge_band": in_edge,
        "cursor": [x, y],
        "client": [w, h],
        "edge_band_px": band,
        "practice": "EDGE_MOUSE_PARK" if in_edge else "SAFE_CURSOR_REST",
        "proof_ceiling": PROOF_CEILING,
    }


def safe_rest_point(
    *,
    client_width: Optional[int] = None,
    client_height: Optional[int] = None,
    edge_band_px: Optional[int] = None,
    origin_x: int = 0,
    origin_y: int = 0,
    cfg: Optional[Mapping[str, object]] = None,
) -> dict:
    """Absolute screen rest point at the client interior center."""
    cfg = cfg or load_contract()
    w, h, band = _geom(
        client_width=client_width,
        client_height=client_height,
        edge_band_px=edge_band_px,
        cfg=cfg,
    )
    d = _defaults(cfg)
    ratio = float(d.get("safe_rest_inset_ratio", 0.5))
    if not (0.2 <= ratio <= 0.8):
        raise CameraTraverseError("INVALID_SAFE_REST_RATIO")
    cx = int(origin_x + w * ratio)
    cy = int(origin_y + h * ratio)
    # Clamp hard away from the edge band.
    cx = max(origin_x + band + 1, min(origin_x + w - band - 1, cx))
    cy = max(origin_y + band + 1, min(origin_y + h - band - 1, cy))
    return {
        "screen": [cx, cy],
        "client": [cx - origin_x, cy - origin_y],
        "zone": "SAFE_INTERIOR",
        "edge_band_px": band,
        "proof_ceiling": PROOF_CEILING,
    }


def classify_practice(practice: str, *, cfg: Optional[Mapping[str, object]] = None) -> dict:
    cfg = cfg or load_contract()
    practices = cfg.get("practices") or {}
    key = str(practice or "").strip().upper()
    if key not in practices:
        raise CameraTraverseError("UNKNOWN_CAMERA_PRACTICE:" + key)
    row = dict(practices[key])
    return {
        "practice": key,
        "verdict": row["verdict"],
        "disposition": row["disposition"],
        "note": row.get("note"),
        "forbidden": key in set(cfg.get("forbidden") or []),
        "proof_ceiling": PROOF_CEILING,
    }


def _direction_delta(token: str, pan_pixels: int, directions: Mapping[str, Sequence[int]]) -> tuple[int, int]:
    key = str(token or "").strip().upper()
    if key not in directions:
        raise CameraTraverseError("UNKNOWN_PAN_DIRECTION:" + key)
    dx, dy = directions[key]
    return int(dx) * int(pan_pixels), int(dy) * int(pan_pixels)


def plan_traverse(
    directions: Sequence[str] = (),
    *,
    client_width: Optional[int] = None,
    client_height: Optional[int] = None,
    edge_band_px: Optional[int] = None,
    origin_x: int = 0,
    origin_y: int = 0,
    prefer_capture_first: Optional[bool] = None,
    pan_pixels: Optional[int] = None,
    zoom_notches: int = 0,
    cfg: Optional[Mapping[str, object]] = None,
) -> dict:
    """Build a bounded camera plan that always terminates at SAFE_REST."""
    cfg = cfg or load_contract()
    d = _defaults(cfg)
    w, h, band = _geom(
        client_width=client_width,
        client_height=client_height,
        edge_band_px=edge_band_px,
        cfg=cfg,
    )
    max_steps = int(d["max_pan_steps"])
    dirs = [str(x).strip().upper() for x in directions if str(x).strip()]
    if len(dirs) > max_steps:
        raise CameraTraverseError("TOO_MANY_PAN_STEPS")
    prefer_capture = (
        bool(d["prefer_capture_first"])
        if prefer_capture_first is None
        else bool(prefer_capture_first)
    )
    pixels = int(pan_pixels if pan_pixels is not None else d["pan_pixels"])
    if pixels < 1 or pixels > max(w, h):
        raise CameraTraverseError("INVALID_PAN_PIXELS")
    if isinstance(zoom_notches, bool) or not isinstance(zoom_notches, int):
        raise CameraTraverseError("INVALID_ZOOM")
    if abs(zoom_notches) > 40:
        raise CameraTraverseError("ZOOM_OUT_OF_BOUNDS")

    rest = safe_rest_point(
        client_width=w,
        client_height=h,
        edge_band_px=band,
        origin_x=origin_x,
        origin_y=origin_y,
        cfg=cfg,
    )
    rest_client = rest["client"]
    steps: list[dict] = []
    if prefer_capture or not dirs:
        steps.append(
            {
                "kind": "CAPTURE_OBSERVE",
                "owner": "scripts/game_capture.py",
                "house_state_action": "CAPTURE_ONLY",
                "note": "Prefer PrintWindow observe before any edge-adjacent pan",
            }
        )
    direction_map = cfg.get("directions") or {}
    for token in dirs:
        dx, dy = _direction_delta(token, pixels, direction_map)
        steps.append(
            {
                "kind": "RIGHT_DRAG_PAN",
                "direction": token,
                "from_client": list(rest_client),
                "delta": [dx, dy],
                "house_state_action": "CAMERA_PAN_ZOOM",
                "forbidden_end_zones": ["EDGE_BAND"],
            }
        )
    if zoom_notches:
        steps.append(
            {
                "kind": "WHEEL_ZOOM",
                "notches": int(zoom_notches),
                "at_client": list(rest_client),
                "house_state_action": "CAMERA_PAN_ZOOM",
            }
        )
    steps.append(
        {
            "kind": "SAFE_REST",
            "screen": list(rest["screen"]),
            "client": list(rest_client),
            "required": True,
            "note": "Mandatory park outside edge band so camera stops drifting",
        }
    )
    if steps[-1]["kind"] != "SAFE_REST":
        raise CameraTraverseError("PLAN_WITHOUT_TERMINAL_SAFE_REST")

    gate = "CAMERA_SAFE_TRAVERSE" if dirs or zoom_notches else "CAPTURE_BEFORE_EDGE_SCAN"
    return {
        "state": "CAMERA_TRAVERSE_PLAN_READY",
        "architecture": "CAMERA_SAFE_TRAVERSE",
        "gate": gate,
        "steps": steps,
        "step_count": len(steps),
        "safe_rest": rest,
        "prefer_capture_first": prefer_capture,
        "forbidden": list(cfg.get("forbidden") or []),
        "execute_allowed": False,
        "command": (
            "python -m scripts.camera_traverse plan "
            + (" ".join(f"--dir {d}" for d in dirs) if dirs else "--capture-only")
        ),
        "proof_ceiling": PROOF_CEILING,
    }



def assess_world_target(
    *,
    target_id: str,
    capture_ref: str,
    observation: Optional[Mapping[str, object]],
    client_width: int,
    client_height: int,
    reframe_directions: Sequence[str] = (),
    cfg: Optional[Mapping[str, object]] = None,
) -> dict:
    """Camera-first world-target gate; no mouse input or automatic pan.

    World targets must be comfortably framed before *proposing* a click.
    Screen-chrome targets are a separate, fixed-coordinate responsibility.
    Every camera move invalidates the old capture and requires a new frame.
    """
    cfg = cfg or load_contract()
    if not isinstance(target_id, str) or not (1 <= len(target_id) <= 96) or not all(
        c.isalnum() or c in " _.:+-" for c in target_id
    ):
        raise CameraTraverseError("WORLD_TARGET_ID_INVALID")
    if not isinstance(capture_ref, str) or not capture_ref or len(capture_ref) > 128:
        raise CameraTraverseError("WORLD_CAPTURE_REF_REQUIRED")
    if type(client_width) is not int or type(client_height) is not int:
        raise CameraTraverseError("WORLD_CLIENT_GEOMETRY_REQUIRED")
    w, h, band = _geom(
        client_width=client_width, client_height=client_height,
        edge_band_px=None, cfg=cfg,
    )
    framing = cfg.get("world_target_framing") or {}
    if not isinstance(framing, dict) or framing.get("camera_before_world_click") is not True:
        raise CameraTraverseError("WORLD_CAMERA_FIRST_CONTRACT_MISSING")
    margin = max(band + 24, int(framing["interior_margin_px"]))
    min_size = int(framing["min_target_extent_px"])
    max_attempts = int(framing["max_reframe_attempts"])
    if margin < band + 1 or margin * 2 >= min(w, h) or min_size < 1 or max_attempts < 1:
        raise CameraTraverseError("WORLD_FRAMING_POLICY_INVALID")

    def block(gate: str, reason: str, *, attempt: int = 0, plan: Optional[dict] = None) -> dict:
        return {
            "state": "WORLD_TARGET_NOT_CLICK_READY",
            "gate": gate,
            "reason": reason,
            "target_id": target_id,
            "capture_ref": capture_ref,
            "framing_attempts": attempt,
            "camera_plan": plan,
            "reobserve_after_camera_change": True,
            "click_candidate": None,
            "click_ready": False,
            "execute_allowed": False,
            "forbidden": [
                "BLIND_WORLD_CLICK", "AUTO_RECLICK",
                "REUSE_PRE_PAN_TARGET_COORDINATES", "EDGE_MOUSE_PARK",
            ],
            "proof_ceiling": PROOF_CEILING,
        }

    if not isinstance(observation, Mapping):
        return block("CAMERA_TARGET_REOBSERVE_REQUIRED", "HOST_TARGET_OBSERVATION_MISSING")
    if len(str(dict(observation))) > 8192:
        raise CameraTraverseError("WORLD_TARGET_OBSERVATION_TOO_LARGE")
    if (
        observation.get("source") != "HOST_CAPTURE"
        or observation.get("target_id") != target_id
        or observation.get("capture_ref") != capture_ref
        or not isinstance(observation.get("camera_revision"), str)
        or not observation["camera_revision"]
    ):
        return block("CAMERA_TARGET_REOBSERVE_REQUIRED", "STALE_OR_UNTRUSTED_TARGET_FRAME")

    attempt = observation.get("framing_attempts", 0)
    if type(attempt) is not int or attempt < 0:
        raise CameraTraverseError("WORLD_FRAMING_ATTEMPTS_INVALID")
    if attempt > max_attempts:
        return block("CAMERA_TARGET_MANUAL_REVIEW", "REFRAME_BUDGET_EXCEEDED", attempt=attempt)
    visible, occluded = observation.get("target_visible"), observation.get("occluded")
    if type(visible) is not bool or type(occluded) is not bool:
        return block("CAMERA_TARGET_REOBSERVE_REQUIRED", "TARGET_VISIBILITY_UNKNOWN", attempt=attempt)

    box = observation.get("bbox_client")
    reason = "TARGET_NOT_VISIBLE" if not visible else "TARGET_OCCLUDED" if occluded else None
    point = None
    if reason is None:
        if not isinstance(box, (list, tuple)) or len(box) != 4 or any(type(v) is not int for v in box):
            return block("CAMERA_TARGET_REOBSERVE_REQUIRED", "TARGET_BOUNDS_UNVERIFIED", attempt=attempt)
        left, top, right, bottom = box
        if not (0 <= left < right <= w and 0 <= top < bottom <= h):
            reason = "TARGET_CLIPPED_OR_OFFSCREEN"
        elif right - left < min_size or bottom - top < min_size:
            reason = "TARGET_TOO_SMALL_TO_CLICK_RELIABLY"
        elif left < margin or top < margin or right > w - margin or bottom > h - margin:
            reason = "TARGET_TOO_CLOSE_TO_VIEWPORT_EDGE"
        else:
            point = [(left + right) // 2, (top + bottom) // 2]

    if reason is None:
        return {
            "state": "WORLD_TARGET_FRAMED",
            "gate": "WORLD_TARGET_AWAIT_HOST_ADMISSION",
            "reason": "TARGET_VISIBLE_CLEAR_AND_IN_INTERIOR",
            "target_id": target_id,
            "capture_ref": capture_ref,
            "camera_revision": observation["camera_revision"],
            "framing_attempts": attempt,
            "click_candidate": point,
            "click_ready": True,
            "execute_allowed": False,
            "camera_plan": None,
            "reobserve_after_camera_change": False,
            "proof_ceiling": PROOF_CEILING,
        }
    if attempt >= max_attempts:
        return block("CAMERA_TARGET_MANUAL_REVIEW", "REFRAME_BUDGET_EXHAUSTED", attempt=attempt)
    # Directions must come from an observed host strategy. No pixel guessed
    # pan loops; if no direction is known, observe again and request guidance.
    plan = plan_traverse(
        reframe_directions,
        client_width=w, client_height=h,
        cfg=cfg,
    )
    return block("CAMERA_TARGET_REFRAME_REQUIRED", reason, attempt=attempt, plan=plan)

def evaluate_cursor_risk(
    *,
    cursor_client_x: Optional[int] = None,
    cursor_client_y: Optional[int] = None,
    client_width: Optional[int] = None,
    client_height: Optional[int] = None,
    edge_band_px: Optional[int] = None,
    camera_scan_needed: bool = False,
    directions: Sequence[str] = (),
    cfg: Optional[Mapping[str, object]] = None,
) -> dict:
    """Host gate helper: edge park outranks needs; otherwise optional traverse plan."""
    cfg = cfg or load_contract()
    if cursor_client_x is None or cursor_client_y is None:
        if not camera_scan_needed and not directions:
            return {
                "state": "CAMERA_CURSOR_UNKNOWN",
                "gate": None,
                "action": "NO_CAMERA_ACTION",
                "sensor": "SENSOR_NOT_SUPPLIED",
                "proof_ceiling": PROOF_CEILING,
            }
        plan = plan_traverse(
            directions,
            client_width=client_width,
            client_height=client_height,
            edge_band_px=edge_band_px,
            cfg=cfg,
        )
        return {
            "state": plan["state"],
            "gate": plan["gate"],
            "action": "CAMERA_SAFE_TRAVERSE",
            "plan": plan,
            "practice": classify_practice("CAPTURE_ONLY", cfg=cfg),
            "proof_ceiling": PROOF_CEILING,
        }

    cursor = classify_cursor(
        int(cursor_client_x),
        int(cursor_client_y),
        client_width=client_width,
        client_height=client_height,
        edge_band_px=edge_band_px,
        cfg=cfg,
    )
    if cursor["in_edge_band"]:
        rest = safe_rest_point(
            client_width=client_width,
            client_height=client_height,
            edge_band_px=edge_band_px,
            cfg=cfg,
        )
        practice = classify_practice("EDGE_MOUSE_PARK", cfg=cfg)
        return {
            "state": "CAMERA_EDGE_PARK_DETECTED",
            "gate": "CAMERA_SAFE_REST",
            "action": "SAFE_CURSOR_REST",
            "cursor": cursor,
            "safe_rest": rest,
            "practice": practice,
            "forbidden": ["LEAVE_CURSOR_IN_EDGE_BAND", "CONTINUOUS_EDGE_HOLD"],
            "proof_ceiling": PROOF_CEILING,
        }

    if camera_scan_needed or directions:
        plan = plan_traverse(
            directions,
            client_width=client_width,
            client_height=client_height,
            edge_band_px=edge_band_px,
            cfg=cfg,
        )
        return {
            "state": plan["state"],
            "gate": plan["gate"],
            "action": "CAMERA_SAFE_TRAVERSE",
            "cursor": cursor,
            "plan": plan,
            "practice": classify_practice("RIGHT_DRAG_BOUNDED", cfg=cfg),
            "proof_ceiling": PROOF_CEILING,
        }

    return {
        "state": "CAMERA_CURSOR_SAFE",
        "gate": None,
        "action": "NO_CAMERA_ACTION",
        "cursor": cursor,
        "practice": classify_practice("SAFE_CURSOR_REST", cfg=cfg),
        "proof_ceiling": PROOF_CEILING,
    }
