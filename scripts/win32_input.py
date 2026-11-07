#!/usr/bin/env python3
"""Shared Win32 mouse SendInput primitives for host UI scripts.

One ownership surface for left-click / wheel / right-drag. Callers still own
session gates, scene checks, and --execute policy. Does not probe player
presence, take focus, or touch saves. Windows-only at call time.
"""
from __future__ import annotations

import sys
import time


class Win32InputError(RuntimeError):
    pass


def _require_win32() -> None:
    if sys.platform != "win32":
        raise Win32InputError("LOCAL_WINDOWS_GAME_HOST_REQUIRED")


def _mouse_input_types():
    import ctypes
    from ctypes import wintypes

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

    return ctypes, MOUSEINPUT, INPUT


def send_click(
    x: int,
    y: int,
    *,
    settle_sec: float = 0.05,
    between_sec: float = 0.05,
) -> None:
    """Left click at absolute screen coordinates via SetCursorPos + SendInput."""
    _require_win32()
    ctypes, MOUSEINPUT, INPUT = _mouse_input_types()
    user32 = ctypes.windll.user32
    ld, lu = 2, 4
    user32.SetCursorPos(int(x), int(y))
    time.sleep(settle_sec)
    for flag in (ld, lu):
        inp = INPUT(type=0)
        inp.mi = MOUSEINPUT(0, 0, 0, flag, 0, None)
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        time.sleep(between_sec)


def send_wheel(notches: int, *, x: int = 960, y: int = 540, settle_sec: float = 0.05) -> None:
    """Scroll wheel notches at a screen point (negative = toward user)."""
    _require_win32()
    ctypes, MOUSEINPUT, INPUT = _mouse_input_types()
    user32 = ctypes.windll.user32
    wheel = 0x0800
    user32.SetCursorPos(int(x), int(y))
    time.sleep(settle_sec)
    delta = -120 if notches < 0 else 120
    for _ in range(abs(int(notches))):
        inp = INPUT(type=0)
        inp.mi = MOUSEINPUT(0, 0, delta & 0xFFFFFFFF, wheel, 0, None)
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        time.sleep(0.03)


def right_drag(
    dx: int,
    dy: int,
    *,
    x0: int = 960,
    y0: int = 540,
    steps: int = 24,
    settle_sec: float = 0.05,
) -> None:
    """Right-button drag from (x0,y0) by (dx,dy) over a fixed step count."""
    _require_win32()
    ctypes, MOUSEINPUT, INPUT = _mouse_input_types()
    user32 = ctypes.windll.user32
    rd, ru = 8, 16
    user32.SetCursorPos(int(x0), int(y0))
    time.sleep(settle_sec)
    inp = INPUT(type=0)
    inp.mi = MOUSEINPUT(0, 0, 0, rd, 0, None)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
    time.sleep(0.05)
    for i in range(1, int(steps) + 1):
        user32.SetCursorPos(int(x0) + int(dx) * i // int(steps), int(y0) + int(dy) * i // int(steps))
        time.sleep(0.02)
    inp = INPUT(type=0)
    inp.mi = MOUSEINPUT(0, 0, 0, ru, 0, None)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
