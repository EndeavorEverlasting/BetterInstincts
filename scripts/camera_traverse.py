#!/usr/bin/env python3
"""Camera-safe traverse CLI: plan offline; optional admitted execute + SAFE_REST.

Examples:
  python -m scripts.camera_traverse classify --x 5 --y 540
  python -m scripts.camera_traverse plan --dir E --dir N
  python -m scripts.camera_traverse plan --capture-only
  python -m scripts.camera_traverse rest --execute --session-id SID --process-id PID
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from betterinstincts.camera_traverse import (
    CameraTraverseError,
    classify_cursor,
    evaluate_cursor_risk,
    load_contract,
    plan_traverse,
    safe_rest_point,
)



def pause_game_on_admitted_host(*, process_id: int, session_id: str, observe) -> dict:
    """One guarded P key for proven PLAYING Sims. Never toggle from PAUSED.

    observe must be an injected fresh HOST_CAPTURE + HOST_GAME_CLOCK sensor.
    An exact local host must own process/session admission and 15s user-idle
    proof; this method does not start a listener, move a cursor, or auto-resume.
    """
    from betterinstincts.camera_traverse import assess_game_pause
    from betterinstincts.screen_admit import admitted_screen_lease, require_execute_session
    from scripts.win32_input import send_key_chord

    if not callable(observe):
        raise CameraTraverseError("FRESH_GAME_CLOCK_SENSOR_REQUIRED")
    require_execute_session(session_id, process_id)
    with admitted_screen_lease(process_id, session_id) as ensure_ready:
        ensure_ready()
        before = observe()
        if not isinstance(before, dict):
            raise CameraTraverseError("FRESH_GAME_CLOCK_SENSOR_REQUIRED")
        capture = before.get("capture_ref")
        plan = assess_game_pause(capture_ref=capture, observation=before)
        if plan["gate"] == "GAME_PAUSED_FOR_TARGETING":
            return {
                "state": "GAME_ALREADY_PAUSED_NO_INPUT",
                "key_dispatched": False, "pause_verified": True,
                "auto_resume": False,
            }
        if plan["gate"] != "GAME_PAUSE_REQUIRED":
            raise CameraTraverseError("GAME_PAUSE_STATE_NOT_VERIFIED")
        ensure_ready()
        latest = assess_game_pause(capture_ref=capture, observation=observe())
        if (latest["gate"] != "GAME_PAUSE_REQUIRED"
                or latest["clock_revision"] != plan["clock_revision"]
                or latest["camera_revision"] != plan["camera_revision"]):
            raise CameraTraverseError("PAUSE_SOURCE_CHANGED_BEFORE_KEY")
        # P / 0 toggle. Exactly ONE keypress; never retry if acknowledgment
        # is unknown, because a second keypress may unpause the player's game.
        send_key_chord(["P"])
        after = observe()  # New capture expected; never assume successful pause.
        if not isinstance(after, dict) or not isinstance(after.get("capture_ref"), str):
            return {
                "state": "PAUSE_KEY_DISPATCHED_UNVERIFIED",
                "key_dispatched": True, "pause_verified": False,
                "auto_resume": False,
            }
        verified = assess_game_pause(
            capture_ref=after["capture_ref"], observation=after,
        )
        return {
            "state": "PAUSE_VERIFIED" if verified["gate"] == "GAME_PAUSED_FOR_TARGETING" else "PAUSE_KEY_DISPATCHED_UNVERIFIED",
            "key_dispatched": True,
            "pause_verified": verified["paused_verified"] is True,
            "auto_resume": False,
            "new_capture_required_for_target": True,
        }



def _park_cursor(x: int, y: int) -> None:
    from scripts.win32_input import move_cursor

    move_cursor(x, y)


def _execute_plan(
    plan: dict, *, process_id: int, session_id: str, idle_ms: int,
    map_goal=None, observe=None, now_ms=None, portrait_follow=None,
) -> dict:
    """Execute only when a live host proves a bounded target-map lease.

    The ordinary CLI cannot supply a trusted camera sensor and is intentionally
    unable to perform map pans or zooms. The injected host port may do so, and
    must restore the Sim under the SAME admitted control lease in finally.
    """
    from betterinstincts.screen_admit import admitted_screen_lease, require_execute_session
    from scripts.win32_input import right_drag, send_wheel, send_key_chord
    from betterinstincts.active_sim_camera_lock import evaluate_active_sim_camera_lock
    from betterinstincts.sim_camera import CENTER_SIM, plan_sim_camera
    from betterinstincts.portrait_follow import plan_portrait_follow

    camera_motion = any(s["kind"] in ("RIGHT_DRAG_PAN", "WHEEL_ZOOM")
                        for s in plan["steps"])
    initial_sim_id = None
    if camera_motion:
        if not callable(observe) or not isinstance(map_goal, dict):
            raise CameraTraverseError("GOAL_SCOPED_MAP_LEASE_AND_LIVE_SENSOR_REQUIRED")
        before = observe()
        if not isinstance(before, dict):
            raise CameraTraverseError("FRESH_CAMERA_SENSOR_REQUIRED")
        pan_directions = [
            s["direction"] for s in plan["steps"] if s["kind"] == "RIGHT_DRAG_PAN"
        ]
        zoom = sum(s.get("notches", 0) for s in plan["steps"] if s["kind"] == "WHEEL_ZOOM")
        lock = evaluate_active_sim_camera_lock(
            capture_ref=before.get("capture_ref"), observation=before,
            map_requested=True, map_goal=map_goal,
            directions=pan_directions, zoom_notches=zoom, now_ms=now_ms,
        )
        if lock["gate"] != "CAMERA_MAP_LEASE_READY":
            raise CameraTraverseError("CAMERA_MAP_LEASE_REFUSED:" + lock["gate"])
        if lock["map_plan"]["steps"] != plan["steps"]:
            raise CameraTraverseError("CAMERA_PLAN_DIFFERS_FROM_ADMITTED_MAP_LEASE")
        initial_sim_id = lock["sim_id"]

    require_execute_session(session_id, process_id)
    results = []
    restoration = "NOT_NEEDED"
    with admitted_screen_lease(
        int(process_id),
        str(session_id),
        idle_ms=idle_ms,
    ) as ensure_ready:
        try:
            for step in plan["steps"]:
                ensure_ready()
                kind = step["kind"]
                if kind == "CAPTURE_OBSERVE":
                    results.append({"step": kind, "state": "DEFER_TO_GAME_CAPTURE"})
                    continue
                if kind == "RIGHT_DRAG_PAN":
                    rest = plan["safe_rest"]["screen"]
                    right_drag(step["delta"][0], step["delta"][1], x0=rest[0], y0=rest[1])
                    results.append({"step": kind, "state": "STEP_DISPATCHED", "delta": step["delta"]})
                    continue
                if kind == "WHEEL_ZOOM":
                    rest = plan["safe_rest"]["screen"]
                    send_wheel(step["notches"], x=rest[0], y=rest[1])
                    results.append({"step": kind, "state": "STEP_DISPATCHED", "notches": step["notches"]})
                    continue
                if kind == "SAFE_REST":
                    sx, sy = step["screen"]
                    _park_cursor(sx, sy)
                    time.sleep(0.05)
                    results.append({"step": kind, "state": "CURSOR_PARKED", "screen": [sx, sy]})
                    continue
                raise CameraTraverseError("UNKNOWN_STEP_KIND:" + str(kind))
        finally:
            if camera_motion:
                # No unconditional Enter: human input, changed active Sim,
                # modal or lost game focus must be respected even on cleanup.
                restoration = "RESTORE_PENDING_HOST_REVALIDATION"
                try:
                    ensure_ready()
                    after = observe()
                    if not isinstance(after, dict):
                        raise CameraTraverseError("RESTORE_SENSOR_MISSING")
                    center = plan_sim_camera(
                        CENTER_SIM, capture_ref=after.get("capture_ref"),
                        observation=after,
                    )
                    if center.get("sim_id") != initial_sim_id:
                        raise CameraTraverseError("ACTIVE_SIM_CHANGED_DURING_MAP_LEASE")
                    portrait = plan_portrait_follow(
                        capture_ref=after.get("capture_ref"), observation=after,
                    )
                    if center["state"] == "ALREADY_FOLLOWING_SIM":
                        restoration = "ACTIVE_SIM_FOLLOW_ALREADY_OBSERVED"
                    elif (portrait["state"] == "PORTRAIT_FOLLOW_READY_FOR_ADMISSION"
                          and callable(portrait_follow)):
                        # Preferred: verified portrait click under same lease.
                        # The injected callback must use the canonical native
                        # owner and the exactly attested client hitbox.
                        ensure_ready()
                        if portrait_follow(portrait) is not True:
                            raise CameraTraverseError("PORTRAIT_FOLLOW_PORT_NOT_ACKNOWLEDGED")
                        restoration = "PORTRAIT_FOLLOW_DISPATCHED_REOBSERVE_REQUIRED"
                    elif center["state"] == "SIM_CAMERA_READY_FOR_ADMISSION":
                        # One-shot center is merely a fallback, never follow.
                        ensure_ready()
                        send_key_chord(center["effect"]["chord"])
                        restoration = "ENTER_DISPATCHED_REOBSERVE_REQUIRED"
                    else:
                        raise CameraTraverseError("RESTORE_NOT_ADMITTED")
                except Exception:
                    # Never seize the camera from a human to tidy up after an
                    # aborted map action. Next admitted turn must re-anchor.
                    restoration = "RESTORE_PENDING_HOST_REVALIDATION"
                    raise
    return {
        "state": "CAMERA_TRAVERSE_EXECUTED",
        "results": results,
        "restoration": restoration,
        "proof_ceiling": "LOCAL_OBSERVED_CLICK_DISPATCH_NOT_LIVE_CERT",
        "forbidden": list(plan.get("forbidden") or []),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    show = sub.add_parser("show-contract", help="Print machine contract")
    show.set_defaults(handler="show")

    cls = sub.add_parser("classify", help="Classify client cursor vs edge band")
    cls.add_argument("--x", type=int, required=True)
    cls.add_argument("--y", type=int, required=True)
    cls.add_argument("--width", type=int, default=None)
    cls.add_argument("--height", type=int, default=None)
    cls.add_argument("--edge-band", type=int, default=None)
    cls.set_defaults(handler="classify")

    plan_p = sub.add_parser("plan", help="Build camera-safe traverse plan")
    plan_p.add_argument("--dir", action="append", default=[], dest="dirs")
    plan_p.add_argument("--capture-only", action="store_true")
    plan_p.add_argument("--width", type=int, default=None)
    plan_p.add_argument("--height", type=int, default=None)
    plan_p.add_argument("--edge-band", type=int, default=None)
    plan_p.add_argument("--origin-x", type=int, default=0)
    plan_p.add_argument("--origin-y", type=int, default=0)
    plan_p.add_argument("--pan-pixels", type=int, default=None)
    plan_p.add_argument("--zoom", type=int, default=0)
    plan_p.add_argument("--no-capture-first", action="store_true")
    plan_p.add_argument("--execute", action="store_true")
    plan_p.add_argument("--session-id", default="")
    plan_p.add_argument("--process-id", type=int, default=None)
    plan_p.add_argument("--idle-ms", type=int, default=15000)
    plan_p.set_defaults(handler="plan")

    rest = sub.add_parser("rest", help="Park cursor at SAFE_CURSOR_REST")
    rest.add_argument("--width", type=int, default=None)
    rest.add_argument("--height", type=int, default=None)
    rest.add_argument("--edge-band", type=int, default=None)
    rest.add_argument("--origin-x", type=int, default=0)
    rest.add_argument("--origin-y", type=int, default=0)
    rest.add_argument("--execute", action="store_true")
    rest.add_argument("--session-id", default="")
    rest.add_argument("--process-id", type=int, default=None)
    rest.add_argument("--idle-ms", type=int, default=15000)
    rest.set_defaults(handler="rest")

    risk = sub.add_parser("evaluate", help="Evaluate cursor risk / optional scan plan")
    risk.add_argument("--x", type=int, default=None)
    risk.add_argument("--y", type=int, default=None)
    risk.add_argument("--width", type=int, default=None)
    risk.add_argument("--height", type=int, default=None)
    risk.add_argument("--edge-band", type=int, default=None)
    risk.add_argument("--scan-needed", action="store_true")
    risk.add_argument("--dir", action="append", default=[], dest="dirs")
    risk.set_defaults(handler="evaluate")

    args = p.parse_args(argv)
    try:
        if args.handler == "show":
            print(json.dumps(load_contract(), indent=2))
            return 0
        if args.handler == "classify":
            print(
                json.dumps(
                    classify_cursor(
                        args.x,
                        args.y,
                        client_width=args.width,
                        client_height=args.height,
                        edge_band_px=args.edge_band,
                    ),
                    indent=2,
                )
            )
            return 0
        if args.handler == "evaluate":
            print(
                json.dumps(
                    evaluate_cursor_risk(
                        cursor_client_x=args.x,
                        cursor_client_y=args.y,
                        client_width=args.width,
                        client_height=args.height,
                        edge_band_px=args.edge_band,
                        camera_scan_needed=args.scan_needed,
                        directions=args.dirs,
                    ),
                    indent=2,
                )
            )
            return 0
        if args.handler == "rest":
            point = safe_rest_point(
                client_width=args.width,
                client_height=args.height,
                edge_band_px=args.edge_band,
                origin_x=args.origin_x,
                origin_y=args.origin_y,
            )
            out = {
                "state": "CAMERA_SAFE_REST_PLAN",
                "gate": "CAMERA_SAFE_REST",
                "safe_rest": point,
                "execute_allowed": False,
                "proof_ceiling": "OFFLINE_CAMERA_SAFE_TRAVERSE_NOT_LIVE_CAMERA_PROOF",
            }
            if args.execute:
                if not args.session_id or args.process_id is None:
                    raise CameraTraverseError("SESSION_AND_PROCESS_REQUIRED_FOR_EXECUTE")
                from betterinstincts.screen_admit import admitted_screen_lease, require_execute_session

                require_execute_session(args.session_id, args.process_id)
                with admitted_screen_lease(
                    int(args.process_id),
                    str(args.session_id),
                    idle_ms=int(args.idle_ms),
                ) as ensure_ready:
                    ensure_ready()
                    _park_cursor(*point["screen"])
                out["state"] = "CAMERA_SAFE_REST_EXECUTED"
                out["execute_allowed"] = True
                out["proof_ceiling"] = "LOCAL_OBSERVED_CLICK_DISPATCH_NOT_LIVE_CERT"
            print(json.dumps(out, indent=2))
            return 0
        if args.handler == "plan":
            dirs = [] if args.capture_only else list(args.dirs)
            plan = plan_traverse(
                dirs,
                client_width=args.width,
                client_height=args.height,
                edge_band_px=args.edge_band,
                origin_x=args.origin_x,
                origin_y=args.origin_y,
                prefer_capture_first=not args.no_capture_first,
                pan_pixels=args.pan_pixels,
                zoom_notches=args.zoom,
            )
            if args.execute:
                if not args.session_id or args.process_id is None:
                    raise CameraTraverseError("SESSION_AND_PROCESS_REQUIRED_FOR_EXECUTE")
                executed = _execute_plan(
                    plan,
                    process_id=int(args.process_id),
                    session_id=args.session_id,
                    idle_ms=int(args.idle_ms),
                )
                plan = {**plan, **executed, "execute_allowed": True}
            print(json.dumps(plan, indent=2))
            return 0
        raise CameraTraverseError("UNKNOWN_COMMAND")
    except (CameraTraverseError, TypeError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
