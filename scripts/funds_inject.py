#!/usr/bin/env python3
"""Deterministic Live-Mode household funds inject via Sims cheat console.

Order (durable — do not skip):
  F1 Live Mode → Ctrl+Shift+C → testingcheats enabled true → Money N → Esc

Default amount is the federal subsidy boost (1_000_000). Evaluate-only unless
--execute. Disposable lab only; never edits saves.

Examples:
  python -m scripts.funds_inject plan --funds 38
  python -m scripts.funds_inject subsidy --funds 38
  python -m scripts.funds_inject subsidy --funds 38 --choice accept_subsidy --execute --process-id PID
  python -m scripts.funds_inject inject --amount 1000000 --execute --process-id PID
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
)

OUTPUT = ROOT / "dist" / "game-host"


class GateError(ValueError):
    pass


def _focus(process_id: int | None, *, click_client: bool = False) -> dict:
    """Soft-focus Sims without stealing Build tools (no center click by default)."""
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
    # Optional client click — OFF by default so Build wall/room tools stay intact.
    if click_client:
        from ctypes import wintypes

        rect = wintypes.RECT()
        user32.GetClientRect(hwnd, ctypes.byref(rect))
        pt = wintypes.POINT(rect.right // 2, rect.bottom // 2)
        user32.ClientToScreen(hwnd, ctypes.byref(pt))
        _click(int(pt.x), int(pt.y))
        time.sleep(0.2)
    fg_ok = user32.GetForegroundWindow() == hwnd
    report["foreground_ok"] = fg_ok
    report["soft_focus"] = not click_client
    if not fg_ok:
        raise GateError("SIMS_FOREGROUND_REQUIRED_FOR_CHEAT_CONSOLE")
    return report


def _send_vk(vk: int, *, up: bool = False) -> None:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    KEYEVENTF_KEYUP = 0x0002

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class INPUT(ctypes.Structure):
        class _I(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT)]

        _anonymous_ = ("i",)
        _fields_ = [("type", wintypes.DWORD), ("i", _I)]

    flags = KEYEVENTF_KEYUP if up else 0
    inp = INPUT(type=1)
    inp.ki = KEYBDINPUT(vk, 0, flags, 0, None)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def _tap(vk: int) -> None:
    _send_vk(vk, up=False)
    time.sleep(0.04)
    _send_vk(vk, up=True)
    time.sleep(0.05)


def _type_text(text: str) -> None:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class INPUT(ctypes.Structure):
        class _I(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT)]

        _anonymous_ = ("i",)
        _fields_ = [("type", wintypes.DWORD), ("i", _I)]

    for ch in text:
        down = INPUT(type=1)
        down.ki = KEYBDINPUT(0, ord(ch), KEYEVENTF_UNICODE, 0, None)
        user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(INPUT))
        up = INPUT(type=1)
        up.ki = KEYBDINPUT(0, ord(ch), KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, None)
        user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(INPUT))
        time.sleep(0.015)


def _click(x: int, y: int) -> None:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    user32.SetCursorPos(x, y)
    time.sleep(0.05)

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", ctypes.c_long), ("dy", ctypes.c_long),
            ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class INPUT(ctypes.Structure):
        class _I(ctypes.Union):
            _fields_ = [("mi", MOUSEINPUT)]

        _anonymous_ = ("i",)
        _fields_ = [("type", wintypes.DWORD), ("i", _I)]

    for flag in (2, 4):
        inp = INPUT(type=0)
        inp.mi = MOUSEINPUT(0, 0, 0, flag, 0, None)
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        time.sleep(0.04)


def _execute_plan(
    plan: dict,
    *,
    process_id: int | None,
    close_console: bool = False,
) -> dict:
    """Mode-agnostic inject: no F1, no Esc spam — tandem with Build/Live/Buy."""
    if sys.platform != "win32":
        raise GateError("LOCAL_WINDOWS_GAME_HOST_REQUIRED")
    commands = steps_to_commands(plan)
    if commands[0] != "testingcheats enabled true":
        raise GateError("TESTINGCHEATS_ENABLED_TRUE_REQUIRED")
    # Never force Live Mode — operator may be mid-build with new funds.
    if any(s.get("step") == "ENSURE_LIVE_MODE" and s.get("required") for s in (plan.get("steps") or [])):
        raise GateError("ENSURE_LIVE_MODE_FORBIDDEN_IN_MODE_AGNOSTIC_STACK")
    focus_report = _focus(process_id)
    time.sleep(0.2)
    # Durable console open in whatever mode the operator is in: Ctrl+Shift+C
    _send_vk(0x11)  # CTRL
    _send_vk(0x10)  # SHIFT
    _tap(0x43)      # C
    _send_vk(0x10, up=True)
    _send_vk(0x11, up=True)
    time.sleep(0.55)
    _click(250, 16)
    time.sleep(0.2)
    dispatched = []
    run_cmds = list(commands)
    if run_cmds and run_cmds[0] == "testingcheats enabled true":
        run_cmds.insert(1, "testingcheats true")
    for cmd in run_cmds:
        _type_text(cmd)
        _tap(0x0D)
        time.sleep(0.35 if cmd == "motherlode" else 0.45)
        dispatched.append(cmd)
    if close_console:
        _tap(0x1B)
    return {
        "state": "FUNDS_INJECT_DISPATCHED",
        "commands": dispatched,
        "open_console": "Ctrl+Shift+C",
        "mode_agnostic": True,
        "forced_live_mode": False,
        "game_mode": plan.get("game_mode", "unknown"),
        "focus": focus_report,
        "amount": plan.get("amount"),
        "proof_ceiling": plan.get("proof_ceiling"),
        "next": "PrintWindow-confirm household funds; LOCAL_OBSERVED only",
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
    gate.add_argument("--receipt", type=Path, default=None)

    inj = sub.add_parser("inject")
    inj.add_argument("--amount", type=float, default=None)
    inj.add_argument("--funds", type=float, default=None, help="Observed funds for remaining-chunk math")
    inj.add_argument("--game-mode", default="unknown", help="live|build|buy|unknown — never forced")
    inj.add_argument("--execute", action="store_true")
    inj.add_argument("--close-console", action="store_true")
    inj.add_argument("--process-id", type=int, default=None)
    inj.add_argument("--receipt", type=Path, default=None)

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
