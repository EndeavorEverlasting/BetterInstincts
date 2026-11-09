#!/usr/bin/env python3
"""One-observed-dialog-step Sims 4 likes/dislikes executor.

Assess -> optional YES/NO -> reobserve the resulting confirmation -> OK.
No image recognition, global hooks, auto-start, or unattended keyboard loop.
Each --execute call is one click under the canonical screen lease. Never
confuse a proposed preference with observed gameplay or a completed choice.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from betterinstincts.preference_prompts import (
    PreferencePromptError, evaluate_offer, plan_stage,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist" / "game-host"
MAX_OBSERVATION_BYTES = 16_384
MAX_CAPTURE_AGE_MS = 5_000


class PreferenceStepError(ValueError):
    pass


def _read_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_OBSERVATION_BYTES:
        raise PreferenceStepError("OBSERVATION_FILE_UNSAFE")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError, OSError) as exc:
        raise PreferenceStepError("OBSERVATION_JSON_INVALID") from exc
    if not isinstance(value, dict):
        raise PreferenceStepError("OBSERVATION_MUST_BE_OBJECT")
    return value


def _receipt_path(path: Path) -> Path:
    target = (path if path.is_absolute() else ROOT / path).resolve()
    root = OUTPUT.resolve()
    if not target.is_relative_to(root) or target == root or target.suffix != ".json":
        raise PreferenceStepError("RECEIPT_OUTSIDE_GAME_HOST")
    if target.exists() or target.is_symlink():
        raise PreferenceStepError("RECEIPT_MUST_BE_NEW")
    return target


def _fresh(observation: dict, *, now_ms: int | None = None) -> None:
    timestamp = observation.get("captured_at_epoch_ms")
    now = int(time.time() * 1000) if now_ms is None else now_ms
    if (type(timestamp) is not int or timestamp <= 0
            or not 0 <= now - timestamp <= MAX_CAPTURE_AGE_MS):
        raise PreferenceStepError("PREFERENCE_CAPTURE_STALE_OR_UNDATED")


def _validate_live_evidence(observation: dict, *, process_id: int) -> None:
    _fresh(observation)
    if (
        observation.get("observed_process_id") != process_id
        or observation.get("sim_selected") is not True
        or observation.get("player_queue_clear") is not True
        or observation.get("save_authorized") is not True
        or observation.get("game_build_confirmed") is not True
    ):
        raise PreferenceStepError("GAME_SIM_SAVE_QUEUE_NOT_OBSERVED")


def _client_target(observation: dict, role: str, *, hwnd: int) -> tuple[int, int]:
    """Convert observed client-local button rectangle to screen center.

    An atlas hotspot is never enough: callers must supply fresh button bounds
    from this exact observation. Never click near a game viewport edge.
    """
    import ctypes
    from ctypes import wintypes

    boxes = observation.get("target_boxes")
    if not isinstance(boxes, dict) or role not in boxes:
        raise PreferenceStepError("VISIBLE_TARGET_BOUNDS_REQUIRED")
    bounds = boxes[role]
    if (not isinstance(bounds, list) or len(bounds) != 4
            or any(type(v) is not int for v in bounds)):
        raise PreferenceStepError("TARGET_BOUNDS_INVALID")
    x1, y1, x2, y2 = bounds
    user32 = ctypes.windll.user32
    rect = wintypes.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        raise PreferenceStepError("GAME_CLIENT_RECT_UNAVAILABLE")
    width, height = rect.right - rect.left, rect.bottom - rect.top
    if not (
        width > 0 and height > 0 and
        0 <= x1 < x2 < width and 0 <= y1 < y2 < height and
        x1 >= 8 and x2 <= width - 8 and y1 >= 8 and y2 <= height - 8
    ):
        raise PreferenceStepError("TARGET_OUTSIDE_SAFE_CLIENT")
    point = wintypes.POINT((x1 + x2) // 2, (y1 + y2) // 2)
    if not user32.ClientToScreen(hwnd, ctypes.byref(point)):
        raise PreferenceStepError("GAME_CLIENT_TO_SCREEN_FAILED")
    return point.x, point.y


def _foreground_game_window(process_id: int) -> int:
    import ctypes
    from ctypes import wintypes
    from betterinstincts.player_presence import probe_windows

    probe = probe_windows(process_id)
    if not (probe.probe_ok and probe.foreground_is_sims and
            probe.foreground_process_id == process_id):
        raise PreferenceStepError("GAME_MUST_ALREADY_BE_FOREGROUND")
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    pid = wintypes.DWORD()
    if not hwnd or not user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid)) or pid.value != process_id:
        raise PreferenceStepError("FOREGROUND_GAME_PID_CHANGED")
    return hwnd


def execute_step(
    observation: dict,
    *,
    stage: str,
    session_id: str,
    process_id: int,
    idle_ms: int,
    receipt_path: Path,
    previous_receipt: dict | None = None,
) -> dict:
    """No takeover from a foreign app, no stale target, no batch of clicks."""
    if sys.platform != "win32":
        raise PreferenceStepError("LOCAL_WINDOWS_GAME_HOST_REQUIRED")
    if type(process_id) is not int or process_id <= 0:
        raise PreferenceStepError("EXACT_GAME_PID_REQUIRED")
    # The plan itself remains independent of screen permission.
    plan = plan_stage(
        observation, stage, automation_opt_in=True,
        previous_receipt=previous_receipt,
        player_directed=observation.get("player_directed") is True,
        known_game_build=observation.get("game_build_confirmed") is True,
    )
    _validate_live_evidence(observation, process_id=process_id)
    from betterinstincts.screen_admit import admitted_screen_lease, require_execute_session
    from betterinstincts.control_handoff import HandoffError
    from scripts.win32_input import send_click

    require_execute_session(session_id, process_id)
    try:
        with admitted_screen_lease(
            process_id, session_id, idle_ms=idle_ms,
            # Never steal focus away from a user's dictation/editor.
            focus_fn=None,
        ) as ensure_ready:
            ensure_ready()
            hwnd = _foreground_game_window(process_id)
            _validate_live_evidence(observation, process_id=process_id)
            x, y = _client_target(observation, plan["target_role"], hwnd=hwnd)
            ensure_ready()  # New input while planning invalidates this step.
            _validate_live_evidence(observation, process_id=process_id)
            _foreground_game_window(process_id)
            send_click(x, y, between_sec=0.04)
    except HandoffError as exc:
        raise PreferenceStepError(str(exc)) from exc
    receipt = {
        "schema": "betterinstincts.preference-step-receipt/v1",
        "state": "INPUT_DISPATCHED",
        "step": stage,
        "sim_ref": plan["sim_ref"],
        "topic_id": plan["topic_id"],
        "offer_kind": plan["offer_kind"],
        "capture_ref": plan["capture_ref"],
        "captured_at_epoch_ms": observation["captured_at_epoch_ms"],
        "session_id": session_id,
        "process_id": process_id,
        "proof_ceiling": "SINGLE_CLICK_DISPATCHED_NOT_PROMPT_ACCEPTED_OR_GAME_CERT",
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    with receipt_path.open("x", encoding="utf-8") as fh:
        json.dump(receipt, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return {**receipt, "receipt": str(receipt_path.relative_to(ROOT))}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observation", type=Path, required=True)
    parser.add_argument("--stage", choices=("YES", "NO", "OK"))
    parser.add_argument("--opt-in", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--session-id")
    parser.add_argument("--process-id", type=int)
    parser.add_argument("--idle-ms", type=int, default=30000)
    parser.add_argument("--previous-receipt", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    try:
        obs = _read_json(args.observation)
        prior = _read_json(args.previous_receipt) if args.previous_receipt else None
        if args.stage is None:
            result = evaluate_offer(
                obs, automation_opt_in=args.opt_in,
                player_directed=obs.get("player_directed") is True,
                known_game_build=obs.get("game_build_confirmed") is True,
            )
        else:
            if not args.opt_in:
                raise PreferenceStepError("EXPLICIT_OPT_IN_REQUIRED")
            result = plan_stage(
                obs, args.stage, automation_opt_in=True,
                previous_receipt=prior,
                player_directed=obs.get("player_directed") is True,
                known_game_build=obs.get("game_build_confirmed") is True,
            )
        if args.execute:
            if not args.opt_in or args.stage is None or not args.session_id or args.process_id is None or not args.receipt:
                raise PreferenceStepError("EXECUTE_REQUIRES_OPT_IN_STAGE_SESSION_PID_RECEIPT")
            result = execute_step(
                obs, stage=args.stage, session_id=args.session_id,
                process_id=args.process_id, idle_ms=args.idle_ms,
                receipt_path=_receipt_path(args.receipt), previous_receipt=prior,
            )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (PreferencePromptError, PreferenceStepError, OSError, TypeError, ValueError) as exc:
        print(json.dumps({"state": "BLOCKED_PRESERVE", "reason": str(exc),
                          "control_permit": None}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
