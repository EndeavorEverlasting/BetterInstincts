#!/usr/bin/env python3
"""Finish a disposable CAS Sim via SendInput + PrintWindow (no desktop capture).

Calibrated for borderless 1920x1080: Athletic flyout -> Bodybuilder, trait dice,
unicode name, checkmark. Prefer story quiz when its dialog is already visible
(see cas_quiz_okay.py). Does not touch personal saves.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


# Offline-calibrated against PrintWindow bitmaps (1920x1080 borderless).
ASPIRATION_HEX = (100, 170)
ATHLETIC = (189, 335)
BODYBUILDER = (204, 315)  # flexed-arm flyout above Athletic
TRAIT_DICE = (291, 155)
NAME_BUBBLE = (140, 48)
NAME_FIELD = (160, 80)
CHECKMARK = (1845, 1005)
MENU_X = (1085, 330)


def _win_api():
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    ABS, MOVE, LD, LU = 0x8000, 1, 2, 4
    KEYEVENTF_UNICODE, KEYEVENTF_KEYUP = 4, 2

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", ctypes.c_long),
            ("dy", ctypes.c_long),
            ("mouseData", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class INPUT(ctypes.Structure):
        class _I(ctypes.Union):
            _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]

        _anonymous_ = ("i",)
        _fields_ = [("type", wintypes.DWORD), ("i", _I)]

    return ctypes, wintypes, user32, ABS, MOVE, LD, LU, KEYEVENTF_UNICODE, KEYEVENTF_KEYUP, MOUSEINPUT, KEYBDINPUT, INPUT


def find_sims_hwnd(process_id: int | None) -> tuple[int, int]:
    ctypes, wintypes, user32, *_rest = _win_api()
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

    user32.EnumWindows(enum_cb, 0)
    if not found:
        raise RuntimeError("SIMS_WINDOW_NOT_FOUND")
    return found[0]


def finish_cas(process_id: int | None, out_dir: Path, first: str, last: str) -> dict:
    if sys.platform != "win32":
        raise RuntimeError("LOCAL_WINDOWS_GAME_HOST_REQUIRED")
    from scripts.game_capture import capture_sims

    ctypes, wintypes, user32, ABS, MOVE, LD, LU, KEYEVENTF_UNICODE, KEYEVENTF_KEYUP, MOUSEINPUT, KEYBDINPUT, INPUT = _win_api()
    hwnd, pid = find_sims_hwnd(process_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    def restore() -> None:
        user32.PostMessageW(hwnd, 0x0112, 0xF120, 0)
        user32.ShowWindow(hwnd, 9)
        fg = user32.GetForegroundWindow()
        pfg = wintypes.DWORD()
        tfg = user32.GetWindowThreadProcessId(fg, ctypes.byref(pfg))
        ptg = wintypes.DWORD()
        ttg = user32.GetWindowThreadProcessId(hwnd, ctypes.byref(ptg))
        user32.AttachThreadInput(tfg, ttg, True)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.AttachThreadInput(tfg, ttg, False)
        time.sleep(0.3)

    def click(x: int, y: int) -> None:
        sx = user32.GetSystemMetrics(0)
        sy = user32.GetSystemMetrics(1)
        ax = int(x * 65535 / (sx - 1))
        ay = int(y * 65535 / (sy - 1))

        def send(flags: int, dx: int = 0, dy: int = 0) -> None:
            inp = INPUT(type=0)
            inp.mi = MOUSEINPUT(dx, dy, 0, flags, 0, None)
            user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

        send(MOVE | ABS, ax, ay)
        time.sleep(0.05)
        send(LD | ABS, ax, ay)
        time.sleep(0.1)
        send(LU | ABS, ax, ay)

    def tap(vk: int) -> None:
        d = INPUT(type=1)
        d.ki = KEYBDINPUT(vk, 0, 0, 0, None)
        u = INPUT(type=1)
        u.ki = KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP, 0, None)
        user32.SendInput(1, ctypes.byref(d), ctypes.sizeof(INPUT))
        time.sleep(0.03)
        user32.SendInput(1, ctypes.byref(u), ctypes.sizeof(INPUT))

    def type_unicode(text: str) -> None:
        for ch in text:
            code = ord(ch)
            d = INPUT(type=1)
            d.ki = KEYBDINPUT(0, code, KEYEVENTF_UNICODE, 0, None)
            u = INPUT(type=1)
            u.ki = KEYBDINPUT(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, None)
            user32.SendInput(1, ctypes.byref(d), ctypes.sizeof(INPUT))
            time.sleep(0.02)
            user32.SendInput(1, ctypes.byref(u), ctypes.sizeof(INPUT))
            time.sleep(0.03)

    def snap(name: str) -> Path:
        path = out_dir / name
        capture_sims(process_id=pid, out=path)
        return path

    restore()
    click(*MENU_X)
    time.sleep(0.4)
    snap("cas_finish_00.png")

    restore()
    click(*ASPIRATION_HEX)
    time.sleep(1.2)
    restore()
    click(*ATHLETIC)
    time.sleep(1.0)
    restore()
    click(*BODYBUILDER)
    time.sleep(1.2)
    snap("cas_finish_asp.png")

    restore()
    click(*TRAIT_DICE)
    time.sleep(1.0)
    snap("cas_finish_traits.png")

    restore()
    click(*NAME_BUBBLE)
    time.sleep(0.7)
    restore()
    click(*NAME_FIELD)
    time.sleep(0.15)
    for _ in range(24):
        tap(0x08)
        time.sleep(0.008)
    type_unicode(first)
    time.sleep(0.1)
    tap(0x09)
    time.sleep(0.1)
    type_unicode(last)
    tap(0x0D)
    time.sleep(0.5)
    snap("cas_finish_named.png")

    restore()
    click(*CHECKMARK)
    time.sleep(3.0)
    after = snap("cas_finish_after_check.png")

    return {
        "state": "CAS_FINISH_DISPATCHED",
        "process_id": pid,
        "hwnd": hwnd,
        "after_check": str(after),
        "proof_ceiling": "CLICK_DISPATCH_ONLY_VERIFY_WITH_PRINTWINDOW",
        "name": f"{first} {last}",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--process-id", type=int, default=None)
    parser.add_argument("--out-dir", type=Path, default=Path("dist/game-host"))
    parser.add_argument("--first", default="BILab")
    parser.add_argument("--last", default="One")
    args = parser.parse_args(argv)
    try:
        result = finish_cas(args.process_id, args.out_dir, args.first, args.last)
    except (RuntimeError, OSError, ValueError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
