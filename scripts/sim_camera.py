#!/usr/bin/env python3
"""Sim camera code ports; no background listener, game launch, or mouse effects.

Desktop center path uses the existing admitted Win32 keyboard owner.
The optional follow port MUST run inside the Sims game Python runtime with an
installed, compatible Sims4CommunityLib; it cannot operate from a desktop CLI.
"""
from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Mapping
from typing import Any

from betterinstincts.sim_camera import (
    CENTER_SIM, CENTER_LOT, FOLLOW_SIM, SimCameraError,
    plan_sim_camera,
)


def center_on_admitted_host(
    command: str, *, session_id: str, process_id: int,
    observe: Callable[[], Mapping[str, Any]],
) -> dict:
    """Dispatch *one* Enter or Shift+Enter, never touch the mouse.

    Local caller must supply a real host sensor (not a stored observation).
    The host lease independently enforces active session, exact PID, focus and
    15s human idle, checked again immediately before the key is sent.
    """
    if command not in (CENTER_SIM, CENTER_LOT) or not callable(observe):
        raise SimCameraError("HOST_CENTER_PORT_INVALID")
    from betterinstincts.screen_admit import admitted_screen_lease
    from scripts.win32_input import send_key_chord

    with admitted_screen_lease(process_id, session_id) as ensure_ready:
        ensure_ready()
        initial = observe()
        if not isinstance(initial, Mapping):
            raise SimCameraError("FRESH_HOST_CAMERA_SENSOR_REQUIRED")
        capture_ref = initial.get("capture_ref")
        plan = plan_sim_camera(command, capture_ref=capture_ref, observation=initial)
        if plan["state"] != "SIM_CAMERA_READY_FOR_ADMISSION":
            raise SimCameraError("CAMERA_CENTER_NOT_ADMITTED:" + plan["reason"])
        ensure_ready()
        latest = plan_sim_camera(command, capture_ref=capture_ref, observation=observe())
        if latest["state"] != plan["state"] or latest["camera_revision"] != plan["camera_revision"] or latest["sim_id"] != plan["sim_id"]:
            raise SimCameraError("CAMERA_CENTER_CHANGED_BEFORE_KEY")
        send_key_chord(plan["effect"]["chord"])
    return {
        "state": "KEY_DISPATCHED_UNVERIFIED",
        "command": command,
        "chord": plan["effect"]["chord"],
        "cursor_moved": False,
        "game_effect_observed": False,
    }



def follow_active_portrait_on_admitted_host(
    *, session_id: str, process_id: int,
    observe: Callable[[], Mapping[str, Any]],
) -> dict:
    """Right-click ONE attested active-Sim portrait on the admitted game PID.

    Uses the existing Windows input owner. This is the preferred desktop path
    over one-shot Enter; successful input alone is not follow proof.
    """
    from betterinstincts.portrait_follow import plan_portrait_follow
    from betterinstincts.screen_atlas import _native_owner
    from betterinstincts.screen_admit import admitted_screen_lease
    from scripts.win32_input import send_right_click, park_safe_cursor_rest

    if not callable(observe):
        raise SimCameraError("PORTRAIT_HOST_SENSOR_REQUIRED")
    with admitted_screen_lease(process_id, session_id) as ensure_ready:
        ensure_ready()
        before = observe()
        if not _native_owner(before, process_id, session_id):
            raise SimCameraError("PORTRAIT_HOST_PID_SESSION_NOT_ATTESTED")
        capture = before.get("capture_ref")
        initial = plan_portrait_follow(capture_ref=capture, observation=before)
        if initial["state"] != "PORTRAIT_FOLLOW_READY_FOR_ADMISSION":
            raise SimCameraError("ACTIVE_SIM_PORTRAIT_UNVERIFIED:" + initial["state"])
        ensure_ready()
        latest_obs = observe()
        if not _native_owner(latest_obs, process_id, session_id):
            raise SimCameraError("PORTRAIT_OWNER_CHANGED")
        latest = plan_portrait_follow(capture_ref=capture, observation=latest_obs)
        keys = (
            "sim_id", "capture_ref", "camera_revision", "portrait_revision",
            "ui_layout_revision", "selected_sim_revision", "hitbox",
        )
        if (latest["state"] != initial["state"]
                or any(latest.get(k) != initial.get(k) for k in keys)
                or (latest_obs["client_origin_x"], latest_obs["client_origin_y"]) != (
                    before["client_origin_x"], before["client_origin_y"])):
            raise SimCameraError("PORTRAIT_CHANGED_BEFORE_RIGHT_CLICK")
        origin = (latest_obs["client_origin_x"], latest_obs["client_origin_y"])
        x, y = initial["effect"]["client"]
        send_right_click(origin[0]+x, origin[1]+y, safe_rest_after=False)
        # Avoid stealing the mouse back from a player who interrupted.
        ensure_ready()
        park_safe_cursor_rest(
            origin_x=origin[0], origin_y=origin[1],
            client_width=initial["client_width"], client_height=initial["client_height"],
        )
        post = observe()
    observed = (
        isinstance(post, Mapping)
        and post.get("source") == "HOST_CAPTURE"
        and post.get("camera_follow_sim_id") == initial["sim_id"]
        and post.get("active_sim_id") == initial["sim_id"]
    )
    return {
        "state": "FOLLOW_OBSERVED" if observed else "PORTRAIT_RIGHT_CLICK_DISPATCHED_UNVERIFIED",
        "target_sim_id": initial["sim_id"],
        "camera_follow_observed": observed,
        "cursor_parked_after": True,
        "game_input": "RIGHT_CLICK_ACTIVE_SIM_PORTRAIT",
        "keyboard_center_used": False,
    }


def follow_active_sim_in_game(
    expected_sim_id: int, *,
    admit: Callable[[], object],
    observe: Callable[[], Mapping[str, Any]],
) -> dict:
    """Optional in-game camera.follow call; does NOT run from external Python.

    A host-integrated Sims extension must invoke this only after its approved
    game-side screen-control admission, and supply a fresh game observation.
    No S4CL files are bundled or auto-installed; no global hotkey is installed.
    """
    if type(expected_sim_id) is not int or expected_sim_id <= 0 or not callable(admit) or not callable(observe):
        raise SimCameraError("IN_GAME_FOLLOW_ADMISSION_REQUIRED")
    before = observe()
    if not isinstance(before, Mapping):
        raise SimCameraError("IN_GAME_OBSERVATION_REQUIRED")
    initial = plan_sim_camera(
        FOLLOW_SIM, capture_ref=before.get("capture_ref"), observation=before,
    )
    if initial["state"] != "SIM_CAMERA_READY_FOR_ADMISSION" or initial["sim_id"] != expected_sim_id:
        raise SimCameraError("ACTIVE_SIM_FOLLOW_NOT_READY")

    try:
        from sims4communitylib.utils.misc.common_camera_utils import CommonCameraUtils
        from sims4communitylib.utils.sims.common_sim_utils import CommonSimUtils
    except ImportError as exc:
        raise SimCameraError("COMPATIBLE_S4CL_GAME_RUNTIME_REQUIRED") from exc
    info = CommonSimUtils.get_active_sim_info()
    if info is None or CommonSimUtils.get_sim_id(info) != expected_sim_id:
        raise SimCameraError("GAME_ACTIVE_SIM_CHANGED")
    if CommonSimUtils.get_sim_instance(info) is None:
        raise SimCameraError("SIM_NOT_INSTANCED_IN_LOADED_ZONE")

    if admit() is not True:  # Real game-side player/scene/save consent/idle gate.
        raise SimCameraError("IN_GAME_ADMISSION_NOT_GRANTED")
    if CommonSimUtils.get_active_sim_info() is not info or CommonSimUtils.get_sim_instance(info) is None:
        raise SimCameraError("GAME_ACTIVE_SIM_CHANGED_AFTER_ADMISSION")
    latest = plan_sim_camera(FOLLOW_SIM, capture_ref=initial["capture_ref"], observation=observe())
    if (
        latest["state"] != "SIM_CAMERA_READY_FOR_ADMISSION"
        or latest["sim_id"] != expected_sim_id
        or latest["camera_revision"] != initial["camera_revision"]
    ):
        raise SimCameraError("CAMERA_OR_SIM_CHANGED_BEFORE_FOLLOW")
    CommonCameraUtils.start_focus_on_sim(info, follow=True)
    return {
        "state": "FOLLOW_API_DISPATCHED_UNVERIFIED",
        "target_sim_id": expected_sim_id,
        "camera_follow_observed": False,
        "cursor_moved": False,
    }


def main(argv=None) -> int:
    """Read-only CLI; live host adapters are opt-in Python callables, not CLI flags."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command", choices=[CENTER_SIM, CENTER_LOT, FOLLOW_SIM], required=True)
    parser.add_argument("--capture-ref", default="capture:missing")
    parser.add_argument("--observation-json", default=None, help="Optional bounded host observation JSON; no file reads")
    args = parser.parse_args(argv)
    try:
        observation = json.loads(args.observation_json) if args.observation_json else None
        result = plan_sim_camera(args.command, capture_ref=args.capture_ref, observation=observation)
    except (ValueError, TypeError, SimCameraError) as exc:
        print(json.dumps({"state": "REFUSED", "reason": str(exc)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
