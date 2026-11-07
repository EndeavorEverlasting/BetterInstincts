#!/usr/bin/env python3
"""Click the CAS household-save modal checkmark (Library + begin playing).

Run outside an active Cursor computer-control overlay. Calibrated against
PrintWindow evidence for the LABLAB / disposable household dialog at 1920x1080.
"""
from __future__ import annotations

import argparse
import json
import sys
import time


# White circular check on the household modal (PrintWindow-calibrated).
HOUSEHOLD_CHECK = (1230, 788)  # deep-blue check (not the white glyph above it)


def click_household_check(process_id: int | None, delay_s: float) -> dict:
    if sys.platform != "win32":
        raise RuntimeError("LOCAL_WINDOWS_GAME_HOST_REQUIRED")
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    WM_SYSCOMMAND, SC_RESTORE = 0x0112, 0xF120
    ABS, MOVE, LEFTDOWN, LEFTUP = 0x8000, 0x0001, 0x0002, 0x0004

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", ctypes.c_long),
            ("dy", ctypes.c_long),
            ("mouseData", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

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
    time.sleep(0.5)

    sx = user32.GetSystemMetrics(0)
    sy = user32.GetSystemMetrics(1)
    x, y = HOUSEHOLD_CHECK
    user32.SetCursorPos(x, y)
    time.sleep(0.15)
    ax = int(x * 65535 / (sx - 1))
    ay = int(y * 65535 / (sy - 1))

    def send(flags: int, dx: int = 0, dy: int = 0) -> None:
        inp = INPUT(type=0, mi=MOUSEINPUT(dx, dy, 0, flags, 0, None))
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    send(MOVE | ABS, ax, ay)
    time.sleep(0.08)
    send(LEFTDOWN | ABS, ax, ay)
    time.sleep(0.2)
    send(LEFTUP | ABS, ax, ay)
    return {
        "state": "HOUSEHOLD_CHECK_DISPATCHED",
        "process_id": pid,
        "hwnd": hwnd,
        "click": list(HOUSEHOLD_CHECK),
        "proof_ceiling": "CLICK_DISPATCH_ONLY_VERIFY_WITH_PRINTWINDOW",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--process-id", type=int, default=None)
    parser.add_argument("--delay-seconds", type=float, default=0.0)
    args = parser.parse_args(argv)
    try:
        result = click_household_check(args.process_id, args.delay_seconds)
    except (RuntimeError, OSError, ValueError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
