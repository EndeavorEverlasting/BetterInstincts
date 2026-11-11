#!/usr/bin/env python3
"""Opt-in exact household funds through the existing Sims 4 host input lease.

Command stack: Ctrl+Shift+C -> testingcheats true -> money N -> HUD check.
No portrait click, fixed screen click, mode switch, extra motherlodes, or
automatic retries. The remote/CLI executor reports dispatch, NEVER a proven
balance change. Local P08 disposable game verification remains required.

Examples:
  python -m scripts.funds_inject plan --amount 1000000 --funds 38 --game-mode live
  python -m scripts.funds_inject inject --amount 1000000 --funds 38 --game-mode live
  python -m scripts.funds_inject inject --amount 1000000 --funds 38 --game-mode live --execute --process-id PID --session-id ACTIVE_SESSION
  python -m scripts.funds_inject verify --amount 1000000 --funds-before 38 --funds-after 1000000 --evidence-ref observed-hud-id
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

from betterinstincts.funds_inject import (
    FundsInjectError,
    evaluate_subsidy_gate,
    plan_inject,
    steps_to_commands,
    subsidy_prompt,
    verify_funds_outcome,
)

OUTPUT = ROOT / "dist" / "game-host"


class GateError(ValueError):
    pass


def _focus(process_id: int | None) -> dict:
    """Soft-focus Sims; never click the world or a fixed console pixel."""
    import ctypes

    from scripts.game_host import focus

    report = focus(process_id=process_id)
    user32 = ctypes.windll.user32
    hwnd = int(report["hwnd"])
    # Alt-unlock + AttachThreadInput: background agents often cannot SetForeground alone.
    VK_MENU = 0x12
    user32.keybd_event(VK_MENU, 0, 0, 0)
    user32.keybd_event(VK_MENU, 0, 2, 0)
    fg = user32.GetForegroundWindow()
    tid_fg = user32.GetWindowThreadProcessId(fg, None)
    tid_t = user32.GetWindowThreadProcessId(hwnd, None)
    user32.AttachThreadInput(tid_fg, tid_t, True)
    user32.BringWindowToTop(hwnd)
    user32.AllowSetForegroundWindow(-1)
    user32.SetForegroundWindow(hwnd)
    user32.SetActiveWindow(hwnd)
    user32.AttachThreadInput(tid_fg, tid_t, False)
    time.sleep(0.35)
    fg_ok = user32.GetForegroundWindow() == hwnd
    report["foreground_ok"] = fg_ok
    report["soft_focus"] = True
    if not fg_ok:
        raise GateError("SIMS_FOREGROUND_REQUIRED_FOR_CHEAT_CONSOLE")
    return report


def _send_vk(vk: int, *, up: bool = False) -> None:
    from scripts.win32_input import send_vk

    send_vk(vk, up=up)


def _tap(vk: int) -> None:
    from scripts.win32_input import tap_vk

    tap_vk(vk)


def _type_text(text: str) -> None:
    from scripts.win32_input import type_text

    type_text(text)


def _open_console_chord() -> None:
    """A balanced input chord: release all modifiers even if C fails."""
    ctrl_down = shift_down = False
    try:
        _send_vk(0x11)  # CTRL
        ctrl_down = True
        _send_vk(0x10)  # SHIFT
        shift_down = True
        _tap(0x43)  # C
    finally:
        if shift_down:
            _send_vk(0x10, up=True)
        if ctrl_down:
            _send_vk(0x11, up=True)


def _execute_plan(
    plan: dict,
    *,
    process_id: int | None,
    close_console: bool = False,
    session_id: str | None = None,
    idle_ms: int = 15000,
) -> dict:
    """One bounded exact-money dispatch under explicit human-first admission.

    The permitted input burst must not masquerade as a verified money change.
    GetLastInputInfo sees our own injected keystrokes, so a fresh 15-second
    idle lease between each *synthetic* character would deadlock. The caller
    holds one exclusive desktop/game lease, probes before borrowing focus,
    and checks exact foreground PID and ACTIVE session between commands.
    """
    if sys.platform != "win32":
        raise GateError("LOCAL_WINDOWS_GAME_HOST_REQUIRED")
    commands = steps_to_commands(plan)
    if plan.get("game_mode") not in {"live", "build", "buy"}:
        raise GateError("EXPLICIT_GAME_MODE_REQUIRED")
    if any(s.get("step") == "ENSURE_LIVE_MODE" for s in (plan.get("steps") or [])):
        raise GateError("ENSURE_LIVE_MODE_FORBIDDEN")
    if close_console:
        # Esc's menu/cancellation semantics are under separate local forensics.
        # Do not toggle or spam an unverified key after money dispatch.
        raise GateError("CLOSE_CONSOLE_REQUIRES_SEPARATE_LOCAL_CERTIFICATION")
    from betterinstincts.control_handoff import HandoffError
    from betterinstincts.screen_admit import admitted_screen_lease, require_execute_session
    from betterinstincts.host_listener import status as listener_status
    from betterinstincts.player_presence import probe_windows

    try:
        require_execute_session(session_id, process_id)
    except HandoffError as exc:
        raise GateError(str(exc)) from exc

    def verify_game_focus() -> None:
        observed = probe_windows(int(process_id))
        if (
            not observed.probe_ok
            or not observed.foreground_is_sims
            or observed.foreground_process_id != int(process_id)
            or listener_status(str(session_id)).get("state") != "ACTIVE"
        ):
            raise GateError("GAME_FOREGROUND_OR_SESSION_LOST")

    try:
        with admitted_screen_lease(
            int(process_id),
            str(session_id),
            idle_ms=idle_ms,
            focus_fn=lambda: _focus(process_id),
        ) as ensure_ready:
            handoff = ensure_ready()
            verify_game_focus()
            _open_console_chord()
            time.sleep(0.55)
            dispatched = []
            for cmd in commands:
                verify_game_focus()
                _type_text(cmd)
                _tap(0x0D)  # Enter
                time.sleep(0.40)
                dispatched.append(cmd)
    except HandoffError as exc:
        raise GateError("HOST_CONTROL_NOT_ADMITTED:" + str(exc)) from exc
    return {
        "state": "FUNDS_INJECT_DISPATCHED_NOT_VERIFIED",
        "commands": dispatched,
        "open_console": "Ctrl+Shift+C",
        "mode_agnostic": True,
        "forced_live_mode": False,
        "game_mode": plan.get("game_mode"),
        "handoff": handoff,
        "session_id": session_id,
        "target_funds": plan.get("target_funds"),
        "funds_before_reported": plan.get("funds_observed"),
        "proof_ceiling": "INPUT_DISPATCH_ONLY_NOT_ACCEPTANCE_OR_BALANCE_PROOF",
        "next_gate": "OBSERVE_HOUSEHOLD_FUNDS_UI_THEN_VERIFY_WITH_EVIDENCE",
        "auto_retry": False,
    }


def _show_overlay(prompt: dict) -> str:
    """Sims-styled yes/no card. Returns option_id."""
    import tkinter as tk

    choice: dict[str, str] = {"value": str(prompt.get("default_option_id") or "accept_subsidy")}

    root = tk.Tk()
    root.title("")
    root.attributes("-topmost", True)
    root.resizable(False, False)
    root.configure(bg="#f4efe6")
    # Center-ish over primary display
    w, h = 520, 280
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 3}")
    root.overrideredirect(True)

    frame = tk.Frame(root, bg="#f4efe6", highlightbackground="#2c2c2c", highlightthickness=2)
    frame.pack(fill="both", expand=True, padx=2, pady=2)

    tk.Label(
        frame,
        text=str(prompt.get("title") or "HOUSEHOLD NOTICE"),
        font=("Segoe UI", 14, "bold"),
        fg="#1a1a1a",
        bg="#f4efe6",
    ).pack(pady=(28, 8))
    tk.Label(
        frame,
        text=str(prompt.get("body") or ""),
        font=("Segoe UI", 11),
        fg="#2a2a2a",
        bg="#f4efe6",
        wraplength=440,
        justify="center",
    ).pack(padx=28, pady=8)

    btn_row = tk.Frame(frame, bg="#f4efe6")
    btn_row.pack(pady=24)

    def pick(oid: str) -> None:
        choice["value"] = oid
        root.destroy()

    options = prompt.get("options") or []
    for opt in options:
        oid = str(opt.get("option_id"))
        label = str(opt.get("label") or oid)
        tk.Button(
            btn_row,
            text=label,
            font=("Segoe UI", 10, "bold"),
            width=16,
            relief="solid",
            bd=1,
            bg="#ffffff",
            fg="#1a1a1a",
            activebackground="#e8e0d4",
            command=lambda o=oid: pick(o),
        ).pack(side="left", padx=12)

    root.bind("<Escape>", lambda _e: pick("decline_subsidy"))
    root.mainloop()
    return choice["value"]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    pl = sub.add_parser("plan")
    pl.add_argument("--funds", type=float, default=None)
    pl.add_argument("--amount", type=float, default=None)
    pl.add_argument("--game-mode", default="unknown")

    pr = sub.add_parser("prompt")
    gate = sub.add_parser("subsidy")
    gate.add_argument("--funds", type=float, required=True)
    gate.add_argument("--choice", default=None, help="accept_subsidy | decline_subsidy; omit for prompt UI")
    gate.add_argument("--game-mode", default="unknown", help="live|build|buy|unknown — never forced")
    gate.add_argument("--overlay", action="store_true", help="Show Sims-styled yes/no card")
    gate.add_argument("--execute", action="store_true")
    gate.add_argument("--close-console", action="store_true", help="Optional Esc after inject (off by default)")
    gate.add_argument("--process-id", type=int, default=None)
    gate.add_argument("--session-id", default=None, help="ACTIVE host_listener session for --execute")
    gate.add_argument("--idle-ms", type=int, default=15000)
    gate.add_argument("--receipt", type=Path, default=None)

    inj = sub.add_parser("inject")
    inj.add_argument("--amount", type=float, default=None)
    inj.add_argument("--funds", type=float, default=None, help="Observed funds for remaining-chunk math")
    inj.add_argument("--game-mode", default="unknown", help="live|build|buy|unknown — never forced")
    inj.add_argument("--execute", action="store_true")
    inj.add_argument("--close-console", action="store_true")
    inj.add_argument("--process-id", type=int, default=None)
    inj.add_argument("--session-id", default=None, help="ACTIVE host_listener session for --execute")
    inj.add_argument("--idle-ms", type=int, default=15000)
    inj.add_argument("--receipt", type=Path, default=None)

    verify = sub.add_parser("verify", help="Classify externally observed HUD funds; no game input")
    verify.add_argument("--amount", type=float, required=True)
    verify.add_argument("--funds-before", type=float, required=True)
    verify.add_argument("--funds-after", type=float, required=True)
    verify.add_argument("--evidence-ref", default=None)

    args = p.parse_args(argv)
    try:
        if args.command == "prompt":
            result = subsidy_prompt()
        elif args.command == "plan":
            result = plan_inject(
                amount=args.amount,
                funds_observed=args.funds,
                game_mode=args.game_mode,
            )
        elif args.command == "verify":
            prior_plan = plan_inject(amount=args.amount, funds_observed=args.funds_before)
            result = verify_funds_outcome(
                prior_plan, funds_after=args.funds_after, evidence_ref=args.evidence_ref,
            )
        elif args.command == "subsidy":
            choice = args.choice
            if args.overlay and choice is None:
                choice = _show_overlay(subsidy_prompt())
            result = evaluate_subsidy_gate(
                args.funds,
                choice=choice,
                game_mode=args.game_mode,
            )
            if (
                args.execute
                and result.get("next_gate") == "EXECUTE_FUNDS_INJECT"
                and isinstance(result.get("inject"), dict)
            ):
                live = _execute_plan(
                    result["inject"],
                    process_id=args.process_id,
                    close_console=bool(args.close_console),
                    session_id=args.session_id,
                    idle_ms=int(args.idle_ms),
                )
                result = {**result, "live": live, "execute": True}
            else:
                result = {**result, "execute": False}
        else:
            plan = plan_inject(
                amount=args.amount,
                funds_observed=args.funds,
                game_mode=args.game_mode,
            )
            result = {"plan": plan, "execute": bool(args.execute)}
            if args.execute:
                result["live"] = _execute_plan(
                    plan,
                    process_id=args.process_id,
                    close_console=bool(args.close_console),
                    session_id=args.session_id,
                    idle_ms=int(args.idle_ms),
                )

        receipt = getattr(args, "receipt", None)
        if receipt is not None:
            path = receipt if receipt.is_absolute() else ROOT / receipt
            path = path.resolve()
            if not path.is_relative_to(OUTPUT.resolve()):
                raise GateError("RECEIPT_OUTSIDE_DIST_GAME_HOST")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            result["receipt"] = str(path.relative_to(ROOT))

        print(json.dumps(result, sort_keys=True))
        return 0
    except (FundsInjectError, GateError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
