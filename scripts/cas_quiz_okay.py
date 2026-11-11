#!/usr/bin/env python3
"""Detached CAS story-quiz 'Okay!' clicker for disposable lab boots.

Run OUTSIDE an active Cursor computer-control overlay. Overlay-owned SendInput
often never reaches The Sims 4 UI even when PrintWindow still shows the quiz.
This script restores the Sims HWND, clicks the offline-calibrated Okay! control,
and exits. Prefer the story quiz over manual trait picking for disposable fills.
"""
from __future__ import annotations

import argparse
import json
import sys

from betterinstincts.legacy_screen_boundary import deny_unadopted_live_effect
import time


OKAY_CLICK = (1271, 257)  # offline-calibrated from PrintWindow CAS quiz bitmap


def click_okay(
    process_id: int | None,
    delay_s: float,
    point: tuple[int, int] | None = None,
) -> dict:
    """Detached SendInput click; `point` defaults to the CAS Okay! control.

    Other callers (scripts.school_attend_click) pass an explicit, gated point so
    there is one native click owner. The result is dispatch-only proof.
    """
    deny_unadopted_live_effect("scripts/cas_quiz_okay.py")
    click_point = OKAY_CLICK if point is None else (int(point[0]), int(point[1]))
    if sys.platform != "win32":
        raise RuntimeError("LOCAL_WINDOWS_GAME_HOST_REQUIRED")
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    WM_SYSCOMMAND, SC_RESTORE = 0x0112, 0xF120
    ABS, MOVE, LEFTDOWN, LEFTUP = 0x8000, 0x0001, 0x0002, 0x0004

    class RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                    ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                    ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

    class INPUT(ctypes.Structure):
        class _I(ctypes.Union):
            _fields_ = [("mi", MOUSEINPUT)]
        _anonymous_ = ("i",)
        _fields_ = [("type", wintypes.DWORD), ("i", _I)]

    found: list[tuple[int, int]] = []

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
        if process_id is not None and int(pid.value) != int(process_id):
            return True
        found.append((int(hwnd), int(pid.value)))
        return True

    if delay_s > 0:
        time.sleep(delay_s)
    user32.EnumWindows(enum_cb, 0)
    if not found:
        raise RuntimeError("SIMS_WINDOW_NOT_FOUND")
    hwnd, pid = found[0]
    user32.PostMessageW(hwnd, WM_SYSCOMMAND, SC_RESTORE, 0)
    time.sleep(0.2)
    user32.ShowWindow(hwnd, 9)
    fg = user32.GetForegroundWindow()
    pid_fg = wintypes.DWORD()
    tid_fg = user32.GetWindowThreadProcessId(fg, ctypes.byref(pid_fg))
    pid_tg = wintypes.DWORD()
    tid_tg = user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid_tg))
    user32.AttachThreadInput(tid_fg, tid_tg, True)
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    user32.AttachThreadInput(tid_fg, tid_tg, False)
    time.sleep(0.4)

    sx = user32.GetSystemMetrics(0)
    sy = user32.GetSystemMetrics(1)
    x, y = click_point
    ax = int(x * 65535 / (sx - 1))
    ay = int(y * 65535 / (sy - 1))

    def send(flags: int, dx: int = 0, dy: int = 0) -> None:
        inp = INPUT(type=0, mi=MOUSEINPUT(dx, dy, 0, flags, 0, None))
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    send(MOVE | ABS, ax, ay)
    time.sleep(0.05)
    send(LEFTDOWN | ABS, ax, ay)
    time.sleep(0.1)
    send(LEFTUP | ABS, ax, ay)
    return {
        "state": "OKAY_CLICK_DISPATCHED",
        "process_id": pid,
        "hwnd": hwnd,
        "click": list(click_point),
        "iconic_after": bool(user32.IsIconic(hwnd)),
        "proof_ceiling": "CLICK_DISPATCH_ONLY_VERIFY_WITH_PRINTWINDOW",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--process-id", type=int, default=None)
    parser.add_argument("--delay-seconds", type=float, default=0.0)
    args = parser.parse_args(argv)
    try:
        result = click_okay(args.process_id, args.delay_seconds)
    except (RuntimeError, OSError, ValueError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
