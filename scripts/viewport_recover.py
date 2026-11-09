#!/usr/bin/env python3
"""Deterministic host logic for Live Mode black PrintWindow viewports.

Default is analyze-only (dry-run). Recovery SendInput requires --execute.
Process restart requires --execute --authorize-restart (never Resume; never
touch user-named saves). RCA/avoidance/ladder: contracts/viewport-black.v1.json

Examples:
  python -m scripts.viewport_recover --image dist/game-host/.../printwindow-after-black.png
  python -m scripts.viewport_recover --capture --process-id 45380
  python -m scripts.viewport_recover --capture --process-id 45380 --session-id SESSION --execute --max-steps 5
  python -m scripts.viewport_recover --capture --process-id 45380 --session-id SESSION --execute --authorize-restart \\
      --run-id bi002-quiz-boot
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

from betterinstincts.viewport import (
    ViewportError,
    analyze_image,
    load_contract,
    predict_risk,
    report_to_dict,
)
from scripts.game_capture import GateError, capture_sims
from scripts.win32_input import right_drag as _right_drag
from scripts.win32_input import send_click
from scripts.win32_input import send_key_chord
from scripts.win32_input import send_wheel as _send_wheel

OUTPUT = ROOT / "dist" / "game-host"

SIM_PORTRAIT = (290, 1020)
# LOCAL_OBSERVED unstick: Build hammer alone → Buy catalog (bi002-quiz-boot 2026-11-07).
# Hotkey-first: prefer F3/F1; HUD coords retained as mouse fallback only.
HUD_BUILD = (1505, 22)
HUD_LIVE_FROM_BUILD = (1585, 35)
HOTKEY_BUILD = ("F3",)
HOTKEY_LIVE = ("F1",)
BUILD_BUY_SETTLE_SEC = 1.6


def _build_buy_recovered(report) -> bool:
    return (
        getattr(report, "classification", None) == "BUILD_BUY_CATALOG_RECOVERY"
        or getattr(report, "state", None) == "VIEWPORT_MODE_BUILD_BUY"
    )


def _send_click(x: int, y: int) -> None:
    send_click(x, y, between_sec=0.04)


def _focus(process_id: int | None) -> dict:
    from scripts import game_host

    return game_host.focus(process_id=process_id)


def _graceful_close_sims(process_id: int) -> dict:
    """Post WM_CLOSE only; never TerminateProcess. Does not touch saves."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    WM_CLOSE = 0x0010
    found: list[int] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def enum_cb(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        if "Sims" not in buf.value:
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if int(pid.value) != int(process_id):
            return True
        found.append(int(hwnd))
        return True

    user32.EnumWindows(enum_cb, 0)
    if not found:
        return {"state": "SIMS_WINDOW_ALREADY_GONE", "process_id": process_id}
    for hwnd in found:
        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
    return {
        "state": "WM_CLOSE_POSTED",
        "process_id": process_id,
        "hwnds": found,
        "forbidden": ["TerminateProcess", "RESUME", "DELETE_SAVE", "TOUCH_USER_SAVE"],
        "proof_ceiling": "CLOSE_POSTED_NOT_CLEAN_EXIT_PROOF",
        "next": "Wait for process exit; then disposable game_host launch — never Resume",
    }


def run_recovery_step(step: str, *, process_id: int | None, authorize_restart: bool,
                      run_id: str | None) -> dict:
    if sys.platform != "win32":
        raise GateError("LOCAL_WINDOWS_GAME_HOST_REQUIRED")
    if step == "FOCUS_RESTORE":
        return {"step": step, "focus": _focus(process_id), "state": "STEP_DISPATCHED"}
    if step == "CAMERA_ZOOM_OUT_AND_PAN":
        _focus(process_id)
        _send_wheel(-18)
        _right_drag(-240, -120)
        _right_drag(180, 80)
        return {"step": step, "state": "STEP_DISPATCHED"}
    if step == "CLICK_ACTIVE_SIM_PORTRAIT_FOLLOW":
        _focus(process_id)
        _send_click(*SIM_PORTRAIT)
        return {"step": step, "click": list(SIM_PORTRAIT), "state": "STEP_DISPATCHED"}
    if step == "ENTER_BUILD_BUY_UNSTICK":
        # Prefer F3 over Build hammer click (hotkey-first interop). Do not chain
        # Live here (can re-black / skip recognition). HUD coords = mouse fallback.
        _focus(process_id)
        send_key_chord(HOTKEY_BUILD)
        time.sleep(BUILD_BUY_SETTLE_SEC)
        return {
            "step": step,
            "channel": "HOTKEY",
            "chord": list(HOTKEY_BUILD),
            "hotkey_id": "MODE_BUILD",
            "mouse_fallback": list(HUD_BUILD),
            "state": "STEP_DISPATCHED",
            "success_classification": "BUILD_BUY_CATALOG_RECOVERY",
            "note": (
                "F3 hotkey-first Build request; mouse fallback HUD (1505,22) unused; "
                "withhold needs clicks; next EXIT_BUILD_BUY_TO_LIVE or Save and Exit"
            ),
            "forbidden_followups": ["NEEDS_OBJECT_CLICK", "RESUME"],
        }
    if step == "EXIT_BUILD_BUY_TO_LIVE":
        _focus(process_id)
        send_key_chord(HOTKEY_LIVE)
        time.sleep(1.2)
        return {
            "step": step,
            "channel": "HOTKEY",
            "chord": list(HOTKEY_LIVE),
            "hotkey_id": "MODE_LIVE",
            "mouse_fallback": list(HUD_LIVE_FROM_BUILD),
            "state": "STEP_DISPATCHED",
            "note": (
                "F1 hotkey-first Live request; mouse fallback people icon unused; "
                "recheck PrintWindow before needs"
            ),
        }
    if step == "TOGGLE_BUILD_THEN_LIVE_CAMERA_RESET":
        # Legacy combined path retained for ladder compatibility; still hotkey-first.
        _focus(process_id)
        send_key_chord(HOTKEY_BUILD)
        time.sleep(BUILD_BUY_SETTLE_SEC)
        send_key_chord(HOTKEY_LIVE)
        return {
            "step": step,
            "channel": "HOTKEY",
            "chords": [list(HOTKEY_BUILD), list(HOTKEY_LIVE)],
            "mouse_fallback": [list(HUD_BUILD), list(HUD_LIVE_FROM_BUILD)],
            "state": "STEP_DISPATCHED",
            "note": (
                "Legacy F3→F1; prefer ENTER_BUILD_BUY_UNSTICK then "
                "EXIT_BUILD_BUY_TO_LIVE. Esc avoided."
            ),
        }
    if step == "RECHECK_PRINTWINDOW_ANALYZE":
        return {"step": step, "state": "DEFER_TO_CALLER_RECAPTURE"}
    if step == "AUTHORIZED_GAME_RESTART":
        if not authorize_restart:
            return {
                "step": step,
                "state": "BLOCKED_RESTART_AUTHORIZATION_REQUIRED",
                "required_flags": ["--execute", "--authorize-restart"],
                "forbidden": ["RESUME", "DELETE_SAVE", "TOUCH_USER_SAVE", "silent_TerminateProcess"],
                "next": (
                    "Re-run with --authorize-restart after lab-save risk accepted; "
                    "then disposable launch + save_guard Play — never Resume"
                ),
            }
        if process_id is None:
            raise GateError("PROCESS_ID_REQUIRED_FOR_RESTART")
        close = _graceful_close_sims(int(process_id))
        return {
            "step": step,
            "state": "RESTART_CLOSE_POSTED",
            "close": close,
            "run_id": run_id,
            "next_commands": [
                "Wait until TS4_x64 exits",
                "python -m scripts.game_host launch --run-id %s --execute  # disposable profile only" % (run_id or "<run-id>"),
                "Load LabLab via save_guard-chosen path only — never Resume, never Richardson",
                "python -m scripts.game_capture --process-id NEWPID --analyze",
            ],
            "proof_ceiling": "CLOSE_POSTED_RELAUNCH_STILL_OPERATOR_OR_HOST_LANE",
        }
    raise GateError("UNKNOWN_RECOVERY_STEP:" + step)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--image", type=Path, default=None)
    p.add_argument("--capture", action="store_true")
    p.add_argument("--process-id", type=int, default=None)
    p.add_argument("--out", type=Path, default=OUTPUT / "viewport-check.png")
    p.add_argument("--execute", action="store_true")
    p.add_argument("--session-id", default=None, help="ACTIVE host_listener session for --execute")
    p.add_argument("--idle-ms", type=int, default=15000)
    p.add_argument("--authorize-restart", action="store_true",
                   help="Permit WM_CLOSE restart gate after camera ladder fails")
    p.add_argument("--run-id", default=None, help="Host run id for restart relaunch notes")
    p.add_argument(
        "--max-steps",
        type=int,
        default=5,
        help="Include ENTER_BUILD_BUY_UNSTICK (step 4). Raise to reach Live exit / restart.",
    )
    p.add_argument("--receipt", type=Path, default=None)
    p.add_argument("--risk-json", type=Path, default=None,
                   help="Optional JSON flags for predict_risk (empty_lot/night/...)")
    args = p.parse_args(argv)

    try:
        cfg = load_contract()
        image_path = args.image
        capture_meta = None
        if args.capture:
            capture_meta = capture_sims(process_id=args.process_id, out=args.out)
            image_path = Path(capture_meta["path"])
            if not image_path.is_absolute():
                image_path = ROOT / image_path
        if image_path is None:
            raise ViewportError("IMAGE_OR_CAPTURE_REQUIRED")
        report = analyze_image(image_path, contract=cfg)
        out: dict = {
            "analyze": report_to_dict(report),
            "image": str(image_path.relative_to(ROOT)) if image_path.is_relative_to(ROOT) else str(image_path),
            "capture": capture_meta,
            "execute": bool(args.execute),
            "authorize_restart": bool(args.authorize_restart),
            "contract": "contracts/viewport-black.v1.json",
            "proof_ceiling": "VIEWPORT_CLASSIFIER_AND_OPTIONAL_INPUT_NOT_LIVE_CERT",
        }
        if args.risk_json is not None:
            risk_path = Path(args.risk_json)
            if risk_path.is_symlink() or not risk_path.is_file() or risk_path.stat().st_size > 16_384:
                raise ViewportError("RISK_JSON_UNSAFE")
            out["risk"] = predict_risk(json.loads(risk_path.read_text(encoding="utf-8")))

        steps_run = []
        if args.execute and report.state == "VIEWPORT_ANOMALY":
            from betterinstincts.control_handoff import HandoffError
            from betterinstincts.screen_admit import admitted_screen_lease, require_execute_session
            try:
                require_execute_session(args.session_id, args.process_id)
            except HandoffError as exc:
                raise GateError(str(exc)) from exc
            max_steps = max(1, min(8, int(args.max_steps)))
            with admitted_screen_lease(
                int(args.process_id),
                str(args.session_id),
                idle_ms=int(args.idle_ms),
                focus_fn=lambda: _focus(args.process_id),
            ) as ensure_ready:
                for step in report.recovery_ladder[:max_steps]:
                    try:
                        ensure_ready()
                    except HandoffError as exc:
                        raise GateError(str(exc)) from exc
                    if step == "RECHECK_PRINTWINDOW_ANALYZE":
                        recheck_path = Path(args.out) if args.out else OUTPUT / "viewport-recheck.png"
                        if not recheck_path.is_absolute():
                            recheck_path = ROOT / recheck_path
                        capture_meta = capture_sims(process_id=args.process_id, out=recheck_path)
                        image_path = ROOT / capture_meta["path"] if not Path(capture_meta["path"]).is_absolute() else Path(capture_meta["path"])
                        report = analyze_image(image_path, contract=cfg)
                        steps_run.append({
                            "step": step,
                            "state": "RECHECKED",
                            "capture": capture_meta,
                            "analyze": report_to_dict(report),
                        })
                        if report.state == "VIEWPORT_OK":
                            out["state"] = "RECOVERY_VIEWPORT_OK"
                            break
                        if _build_buy_recovered(report):
                            out["state"] = "RECOVERY_BUILD_BUY_UNSTUCK"
                            out["next_gate"] = cfg["host_next_gates"]["BUILD_BUY_CATALOG_RECOVERY"]
                            break
                        continue
                    # After Buy unstick, skip legacy combined toggle and Live exit unless
                    # the caller raised max-steps past ENTER and still wants Live.
                    if (
                        step in {"TOGGLE_BUILD_THEN_LIVE_CAMERA_RESET", "EXIT_BUILD_BUY_TO_LIVE"}
                        and _build_buy_recovered(report)
                    ):
                        steps_run.append({
                            "step": step,
                            "state": "SKIPPED_BUILD_BUY_ALREADY_RECOVERED",
                            "note": "Black glitch already unstuck into Buy; withhold auto Live",
                        })
                        out["state"] = "RECOVERY_BUILD_BUY_UNSTUCK"
                        out["next_gate"] = cfg["host_next_gates"]["BUILD_BUY_CATALOG_RECOVERY"]
                        break
                    step_result = run_recovery_step(
                        step,
                        process_id=args.process_id,
                        authorize_restart=bool(args.authorize_restart),
                        run_id=args.run_id,
                    )
                    steps_run.append(step_result)
                    if step_result.get("state") == "BLOCKED_RESTART_AUTHORIZATION_REQUIRED":
                        out["state"] = "BLOCKED_RESTART_AUTHORIZATION_REQUIRED"
                        break
                    if step == "AUTHORIZED_GAME_RESTART":
                        out["state"] = step_result.get("state", "RESTART_CLOSE_POSTED")
                        break
                    # Recapture after camera mutations when capture mode available.
                    if args.capture or args.out:
                        recheck_path = OUTPUT / "viewport-recheck.png"
                        capture_meta = capture_sims(process_id=args.process_id, out=recheck_path)
                        image_path = ROOT / capture_meta["path"] if not Path(capture_meta["path"]).is_absolute() else Path(capture_meta["path"])
                        report = analyze_image(image_path, contract=cfg)
                        steps_run[-1]["recheck"] = report_to_dict(report)
                        if report.state == "VIEWPORT_OK":
                            out["state"] = "RECOVERY_VIEWPORT_OK"
                            break
                        if _build_buy_recovered(report):
                            out["state"] = "RECOVERY_BUILD_BUY_UNSTUCK"
                            out["next_gate"] = cfg["host_next_gates"]["BUILD_BUY_CATALOG_RECOVERY"]
                            # Stop before chaining Live; Buy recovery is the black unstick.
                            break
                else:
                    if out.get("state") is None:
                        if _build_buy_recovered(report):
                            out["state"] = "RECOVERY_BUILD_BUY_UNSTUCK"
                            out["next_gate"] = cfg["host_next_gates"]["BUILD_BUY_CATALOG_RECOVERY"]
                        elif report.state == "VIEWPORT_ANOMALY":
                            out["state"] = "RECOVERY_ATTEMPTED_STILL_ANOMALY"
                            out["next_gate"] = cfg["host_next_gates"]["STILL_BLACK_AFTER_LADDER"]
                        else:
                            out["state"] = "RECOVERY_VIEWPORT_OK"
            out["steps"] = steps_run
            out["session_id"] = args.session_id
            out["analyze_after"] = report_to_dict(report)
        else:
            out["state"] = report.state
            if report.state == "VIEWPORT_ANOMALY" and not args.execute:
                out["dry_run_next"] = (
                    "python -m scripts.viewport_recover --capture --process-id PID "
                    "--session-id SESSION --execute --max-steps 5 "
                    "--out dist/game-host/<run>/viewport-recover.png"
                )
                out["unstick_step"] = "ENTER_BUILD_BUY_UNSTICK"
                out["restart_gate"] = (
                    "If still black after ENTER_BUILD_BUY_UNSTICK: continue ladder or "
                    "add --authorize-restart --run-id <run> (WM_CLOSE only; never Resume)"
                )

        if args.receipt is not None:
            receipt = Path(args.receipt)
            receipt = receipt if receipt.is_absolute() else ROOT / receipt
            receipt = receipt.resolve()
            if not receipt.is_relative_to(OUTPUT.resolve()):
                raise GateError("RECEIPT_OUTSIDE_DIST_GAME_HOST")
            receipt.parent.mkdir(parents=True, exist_ok=True)
            receipt.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            out["receipt"] = str(receipt.relative_to(ROOT))
        print(json.dumps(out, sort_keys=True))
        return 0
    except (ViewportError, GateError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
