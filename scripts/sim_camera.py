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

    admit()  # Must be the real game-side player/scene/save consent/idle gate.
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
