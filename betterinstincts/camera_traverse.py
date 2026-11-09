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



def assess_edge_interaction(
    x: int,
    y: int,
    *,
    phase: str = "REST",
    target_kind: Optional[str] = None,
    target_verified: bool = False,
    player_owned: bool = False,
    client_width: Optional[int] = None,
    client_height: Optional[int] = None,
    edge_band_px: Optional[int] = None,
    cfg: Optional[Mapping[str, object]] = None,
) -> dict:
    """Interpret the camera-trigger edge by *intent*, not coordinates alone.

    A screen edge means the Sims CLIENT viewport camera-pan guard region, not
    the monitor bezel. The 48px default is a conservative avoidance margin,
    not a claim that every pixel activates panning on every Sims build. Native
    UI chrome may overlap it: a brief, verified HUD click is valid, whereas
    leaving an agent-owned cursor there while idle is not.

    This function is advisory. It never sends input or grants a control permit.
    Existing player/scene/save/focus admission and post-click observation remain
    mandatory, and player-owned input is never repositioned by the agent.
    """
    cfg = cfg or load_contract()
    policy = cfg.get("edge_interaction") or {}
    if policy.get("meaning") != "CLIENT_RELATIVE_CAMERA_PAN_GUARD_NOT_MONITOR_BEZEL":
        raise CameraTraverseError("EDGE_SEMANTICS_CONTRACT_MISSING")
    if type(phase) is not str or phase not in set(policy.get("phases") or []):
        raise CameraTraverseError("UNKNOWN_EDGE_INTERACTION_PHASE")
    if type(target_verified) is not bool or type(player_owned) is not bool:
        raise CameraTraverseError("INVALID_EDGE_INTERACTION_EVIDENCE")
    w, h, band = _geom(
        client_width=client_width, client_height=client_height,
        edge_band_px=edge_band_px, cfg=cfg,
    )
    if type(x) is not int or type(y) is not int or not (0 <= x < w and 0 <= y < h):
        raise CameraTraverseError("CURSOR_OUTSIDE_CLIENT")
    cursor = classify_cursor(x, y, client_width=w, client_height=h, edge_band_px=band, cfg=cfg)
    # Raw coordinate classification assumes REST for older callers. A transient
    # edge click must never inherit the misleading EDGE_MOUSE_PARK verdict.
    if cursor["in_edge_band"] and phase != "REST":
        semantic_practice = {
            "TARGETED_CLICK": "EDGE_UI_CLICK_TRANSIENT" if target_kind == "UI_CHROME" and target_verified else "EDGE_CLICK_NOT_ATTESTED",
            "TRANSIT": "EDGE_TRANSIT_TEMPORARY",
            "CAMERA_NAVIGATION": "RIGHT_DRAG_BOUNDED",
        }[phase]
        cursor = {**cursor, "practice": semantic_practice}
    base = {
        "interaction_phase": phase,
        "target_kind": target_kind,
        "cursor": cursor,
        "execute_allowed": False,
        "click_geometry_candidate": False,
        "post_input_safe_rest_required": False,
        "proof_ceiling": PROOF_CEILING,
    }
    if player_owned:
        return {
            **base, "state": "PLAYER_OWNS_POINTER", "gate": "YIELD_TO_PLAYER",
            "action": "NO_AGENT_POINTER_MOVEMENT",
        }
    if not cursor["in_edge_band"]:
        return {
            **base, "state": "CURSOR_SAFE_INTERIOR", "gate": None,
            "action": "NO_CAMERA_ACTION",
        }
    # Any host-owned edge phase needs a terminal interior rest, including
    # a refused click whose unverified target left the mouse near the edge.
    base = {
        **base,
        "safe_rest": safe_rest_point(
            client_width=w, client_height=h, edge_band_px=band, cfg=cfg,
        ),
    }
    if phase == "TARGETED_CLICK":
        if target_kind == "UI_CHROME" and target_verified:
            return {
                **base, "state": "EDGE_UI_CLICK_TRANSIENT",
                "gate": "EDGE_UI_CLICK_HOST_ADMISSION",
                "action": "ONE_ATTESTED_UI_CLICK_THEN_SAFE_REST",
                "click_geometry_candidate": True,
                "post_input_safe_rest_required": True,
                "note": "A legitimate brief HUD click may be at the edge; park interior after release.",
            }
        return {
            **base, "state": "EDGE_CLICK_NOT_ATTESTED",
            "gate": "EDGE_TARGET_REOBSERVE_OR_REFRAME",
            "action": "DO_NOT_CLICK_UNVERIFIED_EDGE_TARGET",
            "post_input_safe_rest_required": True,
        }
    if phase == "TRANSIT":
        return {
            **base, "state": "EDGE_TRANSIT_TEMPORARY",
            "gate": "TRANSIT_MUST_END_AT_SAFE_REST",
            "action": "FINISH_BOUNDED_TRANSIT_THEN_SAFE_REST",
            "post_input_safe_rest_required": True,
        }
    if phase == "CAMERA_NAVIGATION":
        return {
            **base, "state": "EDGE_NAVIGATION_NOT_DWELL",
            "gate": "CAMERA_SAFE_TRAVERSE",
            "action": "USE_BOUNDED_CAMERA_PLAN_WITH_TERMINAL_SAFE_REST",
            "post_input_safe_rest_required": True,
        }
    return {
        **base, "state": "CAMERA_EDGE_DWELL_FORBIDDEN",
        "gate": "CAMERA_SAFE_REST",
        "action": "SAFE_CURSOR_REST",
        "post_input_safe_rest_required": True,
        "safe_rest": safe_rest_point(client_width=w, client_height=h, edge_band_px=band, cfg=cfg),
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
    interaction_phase: str = "REST",
    target_kind: Optional[str] = None,
    target_verified: bool = False,
    player_owned: bool = False,
    cfg: Optional[Mapping[str, object]] = None,
) -> dict:
    """Host gate: distinguish legitimate transient edge clicks from unsafe rest."""
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

    if interaction_phase != "REST" or player_owned:
        return assess_edge_interaction(
            cursor_client_x, cursor_client_y,
            phase=interaction_phase, target_kind=target_kind,
            target_verified=target_verified, player_owned=player_owned,
            client_width=client_width, client_height=client_height,
            edge_band_px=edge_band_px, cfg=cfg,
        )

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



def assess_game_pause(
    *,
    capture_ref: str,
    observation: Optional[Mapping[str, object]],
    cfg: Optional[Mapping[str, object]] = None,
) -> dict:
    """Verify Live time is actually frozen before screen target sampling.

    Sims P / 0 are *toggles*, not idempotent pause commands. Never recommend
    pressing P unless an independently observed playing clock agrees with the
    HUD indicator. This only plans; it never sends a key or resumes the game.
    Pausing Sims time does not freeze mouse/camera movement or stale UI panels.
    """
    cfg = cfg or load_contract()
    policy = cfg.get("drift_recovery", {}).get("gameplay_pause") or {}
    if (policy.get("pause_before_live_pixel_targeting") is not True
            or policy.get("toggle_key") != ["P"]
            or policy.get("auto_resume") is not False):
        raise CameraTraverseError("GAME_PAUSE_POLICY_UNSAFE")
    if not isinstance(capture_ref, str) or not 1 <= len(capture_ref) <= 128:
        raise CameraTraverseError("GAME_PAUSE_CAPTURE_INVALID")
    base = {
        "paused_verified": False, "execute_allowed": False,
        "capture_ref": capture_ref, "auto_resume_allowed": False,
        "proof_ceiling": PROOF_CEILING,
        "forbidden": ["BLIND_PAUSE_TOGGLE", "AUTO_RESUME", "REUSE_PRE_PAUSE_PIXELS"],
    }

    def hold(reason: str) -> dict:
        return {**base, "gate": "GAME_PAUSE_REOBSERVE",
                "reason": reason, "state": "GAME_PAUSE_UNVERIFIED"}

    if not isinstance(observation, Mapping):
        return hold("HOST_CLOCK_OBSERVATION_MISSING")
    if (observation.get("source") != "HOST_CAPTURE"
            or observation.get("capture_ref") != capture_ref
            or observation.get("mode") != "LIVE"
            or observation.get("scene_id") != "live_mode"
            or observation.get("capture_quality") != "CONTENT_PRESENT"
            or observation.get("viewport_state") != "NORMAL"):
        return hold("GAME_PAUSE_LIVE_SCENE_UNVERIFIED")
    from betterinstincts.scenes import load_catalog
    version = load_catalog()["game_version"]
    if observation.get("game_version") != version:
        return hold("GAME_PAUSE_GAME_PATCH_UNVERIFIED")
    if any(observation.get(key) is not value for key, value in (
        ("player_camera_owned", False), ("player_queue_owned", False),
        ("modal_open", False), ("text_entry_active", False),
        ("save_authorized", True),
    )):
        return hold("GAME_PAUSE_PLAYER_OR_INPUT_OWNED")
    cues = observation.get("independent_cues")
    if (not isinstance(cues, list) or len(cues) != 2
            or {c.get("source") for c in cues if isinstance(c, Mapping)}
                != {"visual", "operator"}
            or not all(isinstance(c, Mapping)
                       and isinstance(c.get("token"), str)
                       and 1 <= len(c["token"]) <= 80 for c in cues)):
        return hold("GAME_PAUSE_INDEPENDENT_SCENE_CUES_MISSING")
    camera_revision = observation.get("camera_revision")
    if not isinstance(camera_revision, str) or not 1 <= len(camera_revision) <= 80:
        return hold("GAME_PAUSE_CAMERA_REVISION_UNVERIFIED")
    clock = observation.get("game_clock")
    if not isinstance(clock, Mapping):
        return hold("GAME_CLOCK_SENSOR_MISSING")
    if (clock.get("source") != "HOST_GAME_CLOCK"
            or clock.get("capture_ref") != capture_ref
            or clock.get("camera_revision") != camera_revision
            or clock.get("game_version") != version):
        return hold("GAME_CLOCK_STALE_OR_UNTRUSTED")
    clock_revision = clock.get("clock_revision")
    if not isinstance(clock_revision, str) or not 1 <= len(clock_revision) <= 80:
        return hold("GAME_CLOCK_REVISION_UNVERIFIED")
    state = clock.get("speed_state")
    indicator = clock.get("pause_indicator_active")
    still = clock.get("clock_still_during_sample")
    if type(indicator) is not bool or type(still) is not bool:
        return hold("GAME_CLOCK_PAUSE_EVIDENCE_UNKNOWN")
    if state == "PAUSED" and indicator and still:
        return {
            **base, "gate": "GAME_PAUSED_FOR_TARGETING",
            "state": "GAME_PAUSED_CONFIRMED", "paused_verified": True,
            "camera_revision": camera_revision, "clock_revision": clock_revision,
            "pause_origin": clock.get("pause_origin") if clock.get("pause_origin") in {"PLAYER", "AGENT"} else "UNKNOWN",
            "key": None,
        }
    if state == "PLAYING" and not indicator and not still:
        return {
            **base, "gate": "GAME_PAUSE_REQUIRED",
            "state": "GAME_PLAYING_CONFIRMED",
            "camera_revision": camera_revision, "clock_revision": clock_revision,
            "key": list(policy["toggle_key"]),
            "next_step": "RECAPTURE_AND_VERIFY_GAME_PAUSED",
        }
    return hold("GAME_CLOCK_CONFLICTING_PAUSE_INDICATORS")



def assess_drift_recovery(
    *,
    target_kind: str,
    capture_ref: str,
    observation: Optional[Mapping[str, object]],
    client_width: int,
    client_height: int,
    target_id: Optional[str] = None,
    world_target_observation: Optional[Mapping[str, object]] = None,
    reframe_directions: Sequence[str] = (),
    sim_camera_observation: Optional[Mapping[str, object]] = None,
    continuous_follow: bool = False,
    cfg: Optional[Mapping[str, object]] = None,
) -> dict:
    """P95: recover a stable camera *before* inspecting pixels or issuing clicks.

    Only returns advice. A new capture after rest/centering/traversal is
    mandatory. Actual input remains the responsibility of the admitted host.
    """
    cfg = cfg or load_contract()
    policy = cfg.get("drift_recovery")
    if not isinstance(policy, dict) or policy.get("safe_rest_before_pixel_targeting") is not True:
        raise CameraTraverseError("DRIFT_RECOVERY_CONTRACT_MISSING")
    if target_kind not in {"SIM", "LOT", "WORLD_OBJECT"}:
        raise CameraTraverseError("UNKNOWN_RECOVERY_TARGET_KIND")
    if type(continuous_follow) is not bool:
        raise CameraTraverseError("INVALID_CONTINUOUS_FOLLOW_REQUEST")
    if continuous_follow and target_kind != "SIM":
        raise CameraTraverseError("FOLLOW_ONLY_FOR_SIM")
    if not isinstance(capture_ref, str) or not 1 <= len(capture_ref) <= 128:
        raise CameraTraverseError("RECOVERY_CAPTURE_REF_INVALID")
    if type(client_width) is not int or type(client_height) is not int:
        raise CameraTraverseError("RECOVERY_DIMENSIONS_REQUIRED")
    w, h, band = _geom(client_width=client_width, client_height=client_height, edge_band_px=None, cfg=cfg)
    rest = safe_rest_point(client_width=w, client_height=h, cfg=cfg)
    max_attempts = policy.get("max_camera_reanchor_attempts")
    if type(max_attempts) is not int or not 1 <= max_attempts <= 3:
        raise CameraTraverseError("RECOVERY_REANCHOR_BUDGET_UNSAFE")
    if target_kind == "WORLD_OBJECT" and (
        not isinstance(target_id, str) or not 1 <= len(target_id) <= 96
    ):
        raise CameraTraverseError("RECOVERY_WORLD_TARGET_REQUIRED")

    base = {
        "state": "CAMERA_RECOVERY_BLOCKED",
        "gate": "CAMERA_RECOVERY_REOBSERVE",
        "target_kind": target_kind,
        "capture_ref": capture_ref,
        "safe_rest": rest,
        "execute_allowed": False,
        "world_click_ready": False,
        "invalidate_prior_pixels": True,
        "proof_ceiling": PROOF_CEILING,
        "forbidden": [
            "BLIND_WORLD_CLICK", "REUSE_PRE_PAN_TARGET_COORDINATES",
            "AUTO_RECLICK", "UNBOUNDED_TARGET_REFRAME",
            "UNCALIBRATED_PORTRAIT_RIGHT_CLICK",
        ],
    }

    def hold(gate: str, reason: str, **extra: object) -> dict:
        return {**base, "gate": gate, "reason": reason, **extra}

    if not isinstance(observation, Mapping):
        return hold("CAMERA_RECOVERY_REOBSERVE", "RECOVERY_HOST_CAPTURE_MISSING")
    if len(str(dict(observation))) > 8192:
        raise CameraTraverseError("RECOVERY_OBSERVATION_TOO_LARGE")
    if observation.get("source") != "HOST_CAPTURE" or observation.get("capture_ref") != capture_ref:
        return hold("CAMERA_RECOVERY_REOBSERVE", "STALE_OR_UNTRUSTED_RECOVERY_CAPTURE")
    revision = observation.get("camera_revision")
    if not isinstance(revision, str) or not 1 <= len(revision) <= 80:
        return hold("CAMERA_RECOVERY_REOBSERVE", "CAMERA_REVISION_UNVERIFIED")
    from betterinstincts.scenes import load_catalog
    modes = {"LIVE": "live_mode", "BUY": "buy_mode", "BUILD": "build_mode"}
    mode = observation.get("mode")
    if (observation.get("game_version") != load_catalog()["game_version"]
            or observation.get("capture_quality") != "CONTENT_PRESENT"
            or observation.get("viewport_state") != "NORMAL"
            or mode not in modes
            or observation.get("scene_id") != modes.get(mode)
            or (target_kind != "WORLD_OBJECT" and mode != "LIVE")):
        return hold("CAMERA_RECOVERY_REOBSERVE", "EXACT_BUILD_OR_SCENE_UNVERIFIED")
    cues = observation.get("independent_cues")
    if (not isinstance(cues, list) or len(cues) != 2
            or {c.get("source") for c in cues if isinstance(c, Mapping)} != {"visual", "operator"}
            or not all(isinstance(c, Mapping) and isinstance(c.get("token"), str)
                       and 1 <= len(c["token"]) <= 80 for c in cues)):
        return hold("CAMERA_RECOVERY_REOBSERVE", "INDEPENDENT_SCENE_CUES_MISSING")
    if any(observation.get(key) is not value for key, value in (
        ("player_camera_owned", False), ("text_entry_active", False),
        ("modal_open", False), ("player_queue_owned", False),
        ("save_authorized", True),
    )):
        return hold("CAMERA_RECOVERY_YIELD_TO_PLAYER", "PLAYER_OR_SCENE_AUTHORITY_UNVERIFIED")
    displaced = observation.get("camera_displaced")
    if type(displaced) is not bool:
        return hold("CAMERA_RECOVERY_REOBSERVE", "CAMERA_DRIFT_STATE_UNKNOWN")
    attempts = observation.get("camera_reanchor_attempts")
    if type(attempts) is not int or attempts < 0:
        return hold("CAMERA_RECOVERY_REOBSERVE", "CAMERA_REANCHOR_COUNT_UNKNOWN")
    cursor = observation.get("cursor_client")
    if not isinstance(cursor, (list, tuple)) or len(cursor) != 2 or any(type(n) is not int for n in cursor):
        return hold("CAMERA_RECOVERY_REOBSERVE", "CURSOR_POSITION_UNKNOWN")
    if not (0 <= cursor[0] < w and 0 <= cursor[1] < h):
        return hold("CAMERA_RECOVERY_REOBSERVE", "CURSOR_OUTSIDE_CLIENT")
    if classify_cursor(cursor[0], cursor[1], client_width=w, client_height=h, cfg=cfg)["in_edge_band"]:
        return hold(
            "CAMERA_SAFE_REST", "CURSOR_EDGE_PANNING",
            recovery_step={"kind": "SAFE_REST", "client": rest["client"]},
            next_step="CAPTURE_NEW_FRAME_AFTER_CURSOR_REST",
        )
    # Freeze simulation time *after* safely moving the cursor off the edge.
    # Pause does not freeze the camera, so the existing reanchor and target
    # revision checks remain necessary after the fresh paused capture.
    time_pause = None
    if mode == "LIVE":
        time_pause = assess_game_pause(
            capture_ref=capture_ref, observation=observation, cfg=cfg,
        )
        if time_pause["paused_verified"] is not True:
            return hold(
                time_pause["gate"],
                "PAUSE_BEFORE_LIVE_CAMERA_OR_PIXEL_TARGET",
                recovery_step={
                    "kind": "PAUSE_GAME_IF_PLAYING",
                    "chord": time_pause.get("key"),
                } if time_pause["gate"] == "GAME_PAUSE_REQUIRED" else None,
                game_pause=time_pause,
                next_step="RECAPTURE_AND_VERIFY_PAUSED_SCENE",
            )
    if displaced:
        if attempts >= max_attempts:
            return hold("CAMERA_RECOVERY_MANUAL_REVIEW", "REANCHOR_BUDGET_EXHAUSTED")
        if attempts and target_kind == "WORLD_OBJECT":
            # After one lot reanchor, no further guessed keyboard recenter.
            # Either traverse by observed direction or capture for guidance.
            if not reframe_directions:
                return hold("CAMERA_RECOVERY_REOBSERVE", "OBSERVED_PAN_DIRECTION_REQUIRED")
            camera = plan_traverse(reframe_directions, client_width=w, client_height=h, cfg=cfg)
            return hold(
                "CAMERA_RECOVERY_TRAVERSE", "LOT_REANCHORED_TARGET_STILL_OUT_OF_FRAME",
                recovery_step={"kind": "BOUNDED_TRAVERSE", "plan": camera},
                next_step="CAPTURE_NEW_FRAME_AND_REDETECT_OBJECT",
            )
        from betterinstincts.sim_camera import CENTER_LOT, CENTER_SIM, FOLLOW_SIM, plan_sim_camera
        command = CENTER_LOT if target_kind != "SIM" else FOLLOW_SIM if continuous_follow else CENTER_SIM
        sim_plan = plan_sim_camera(
            command, capture_ref=capture_ref, observation=sim_camera_observation,
        )
        if sim_plan["state"] == "ALREADY_FOLLOWING_SIM":
            return hold("CAMERA_RECOVERY_REOBSERVE", "ALREADY_FOLLOWING_SIM_REOBSERVE")
        if sim_plan["state"] != "SIM_CAMERA_READY_FOR_ADMISSION":
            return hold("CAMERA_RECOVERY_REOBSERVE", "NATIVE_CAMERA_REANCHOR_NOT_READY", camera_intent=sim_plan)
        return hold(
            "CAMERA_RECOVERY_REANCHOR", "CAMERA_DISPLACED",
            recovery_step={"kind": "SIM_CAMERA_INTENT", "command": command, "intent": sim_plan},
            next_step="CAPTURE_NEW_FRAME_AFTER_REANCHOR",
        )
    if target_kind != "WORLD_OBJECT":
        return {
            **base, "state": "CAMERA_STABLE",
            "gate": "CAMERA_RECOVERY_STABLE",
            "reason": "INTERIOR_CURSOR_AND_STABLE_CAMERA",
            "invalidate_prior_pixels": False,
            "camera_revision": revision,
            "game_pause": time_pause,
        }
    if not isinstance(world_target_observation, Mapping):
        return hold("CAMERA_RECOVERY_REOBSERVE", "WORLD_TARGET_CAPTURE_MISSING")
    if world_target_observation.get("camera_revision") != revision:
        return hold("CAMERA_RECOVERY_REOBSERVE", "WORLD_TARGET_FROM_DIFFERENT_CAMERA")
    framed = assess_world_target(
        target_id=target_id, capture_ref=capture_ref,
        observation=world_target_observation, client_width=w, client_height=h,
        reframe_directions=reframe_directions, cfg=cfg,
    )
    if not framed["click_ready"]:
        return hold(
            framed["gate"], framed["reason"], target_framing=framed,
            recovery_step={"kind": "BOUNDED_TRAVERSE", "plan": framed["camera_plan"]}
            if framed.get("camera_plan") else None,
            next_step="CAPTURE_NEW_FRAME_AND_REDETECT_OBJECT",
        )
    return {
        **base, "state": "CAMERA_STABLE_TARGET_FRAMED",
        "gate": "WORLD_TARGET_AWAIT_HOST_ADMISSION",
        "reason": "CURSOR_SAFE_CURRENT_CAMERA_AND_TARGET_FRAMED",
        "world_click_ready": True,
        "invalidate_prior_pixels": False,
        "camera_revision": revision,
        "game_pause": time_pause,
        "clock_revision": time_pause["clock_revision"] if time_pause else None,
        "target_framing": framed,
    }
