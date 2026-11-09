#!/usr/bin/env python3
"""Shared Win32 mouse + keyboard SendInput primitives for host UI scripts.

One ownership surface for left-click / wheel / right-drag / cursor park /
key chords / unicode typing. Prefer catalogued hotkeys over mouse clicks when
an equivalent exists (see contracts/ui-chrome.v1.json input_preference).
Callers still own session gates, scene checks, and --execute policy. Does not
probe player presence, take focus, or touch saves. Windows-only at call time.
No global keyhook or keylogger.
"""
from __future__ import annotations

import sys
import time
from typing import Sequence


class Win32InputError(RuntimeError):
    pass


# Virtual-key aliases used by ui-chrome / funds / viewport hotkey plans.
_VK_ALIASES: dict[str, int] = {
    "BACKSPACE": 0x08,
    "TAB": 0x09,
    "ENTER": 0x0D,
    "RETURN": 0x0D,
    "SHIFT": 0x10,
    "CTRL": 0x11,
    "CONTROL": 0x11,
    "ALT": 0x12,
    "ESC": 0x1B,
    "ESCAPE": 0x1B,
    "SPACE": 0x20,
    "PAGEUP": 0x21,
    "PAGEDOWN": 0x22,
    "F1": 0x70,
    "F2": 0x71,
    "F3": 0x72,
    "F4": 0x73,
    "F5": 0x74,
}


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


def _keyboard_input_types():
    import ctypes
    from ctypes import wintypes

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
            _fields_ = [("ki", KEYBDINPUT)]

        _anonymous_ = ("i",)
        _fields_ = [("type", wintypes.DWORD), ("i", _I)]

    return ctypes, KEYBDINPUT, INPUT


def resolve_vk(token: str | int) -> int:
    """Map a chord token or raw VK integer to a virtual-key code."""
    if isinstance(token, int):
        if not (1 <= token <= 0xFE):
            raise Win32InputError("VK_OUT_OF_RANGE")
        return token
    name = str(token).strip().upper()
    if not name:
        raise Win32InputError("EMPTY_VK_TOKEN")
    if name in _VK_ALIASES:
        return _VK_ALIASES[name]
    if len(name) == 1 and "A" <= name <= "Z":
        return ord(name)
    if len(name) == 1 and "0" <= name <= "9":
        return ord(name)
    raise Win32InputError("UNKNOWN_VK_TOKEN:" + name)


def send_vk(vk: int, *, up: bool = False) -> None:
    """Press or release one virtual key via SendInput (no hooks)."""
    _require_win32()
    ctypes, KEYBDINPUT, INPUT = _keyboard_input_types()
    user32 = ctypes.windll.user32
    KEYEVENTF_KEYUP = 0x0002
    flags = KEYEVENTF_KEYUP if up else 0
    inp = INPUT(type=1)
    inp.ki = KEYBDINPUT(int(vk) & 0xFFFF, 0, flags, 0, None)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def tap_vk(vk: int, *, down_sec: float = 0.04, after_sec: float = 0.05) -> None:
    """Tap one virtual key (down then up)."""
    send_vk(int(vk), up=False)
    time.sleep(down_sec)
    send_vk(int(vk), up=True)
    time.sleep(after_sec)


def send_key_chord(
    chord: Sequence[str | int],
    *,
    down_sec: float = 0.04,
    after_sec: float = 0.05,
) -> None:
    """Send a modifier+key chord without moving the mouse.

    Preferred cooperative channel when a catalogued hotkey exists. Still
    requires caller-owned idle/session admission before invocation.
    """
    _require_win32()
    tokens = [resolve_vk(part) for part in chord]
    if not tokens:
        raise Win32InputError("EMPTY_KEY_CHORD")
    for vk in tokens:
        send_vk(vk, up=False)
        time.sleep(0.01)
    time.sleep(down_sec)
    for vk in reversed(tokens):
        send_vk(vk, up=True)
        time.sleep(0.01)
    time.sleep(after_sec)


def type_unicode(text: str, *, per_char_sec: float = 0.015) -> None:
    """Type unicode text via KEYEVENTF_UNICODE (no clipboard).

    Prefer type_text() for Sims cheat console — KEYEVENTF_UNICODE is a
    silent miss on some TS4 hosts while VK/scancode typing is accepted.
    """
    _require_win32()
    if not isinstance(text, str):
        raise Win32InputError("TYPE_TEXT_MUST_BE_STR")
    ctypes, KEYBDINPUT, INPUT = _keyboard_input_types()
    user32 = ctypes.windll.user32
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004
    for ch in text:
        down = INPUT(type=1)
        down.ki = KEYBDINPUT(0, ord(ch), KEYEVENTF_UNICODE, 0, None)
        user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(INPUT))
        up = INPUT(type=1)
        up.ki = KEYBDINPUT(0, ord(ch), KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, None)
        user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(INPUT))
        time.sleep(per_char_sec)


def type_text(text: str, *, per_char_sec: float = 0.02) -> None:
    """Type ASCII/cheat-console text via VkKeyScan + keybd_event.

    Sims 4's DirectInput cheat box often ignores KEYEVENTF_UNICODE and can
    also miss SendInput VK injection on some hosts; keybd_event matches the
    path that computer-use typing successfully reaches for motherlode/skills.
    """
    _require_win32()
    if not isinstance(text, str):
        raise Win32InputError("TYPE_TEXT_MUST_BE_STR")
    import ctypes

    user32 = ctypes.windll.user32
    KEYEVENTF_KEYUP = 0x0002
    VK_SHIFT = 0x10
    for ch in text:
        if ch == "\n":
            user32.keybd_event(0x0D, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(0x0D, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(per_char_sec)
            continue
        if ch == "\t":
            user32.keybd_event(0x09, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(0x09, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(per_char_sec)
            continue
        scanned = int(user32.VkKeyScanW(ord(ch)))
        if scanned == -1 or scanned == 0xFFFF:
            type_unicode(ch, per_char_sec=per_char_sec)
            continue
        vk = scanned & 0xFF
        shift = bool(scanned & 0x100)
        if shift:
            user32.keybd_event(VK_SHIFT, 0, 0, 0)
        user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.012)
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        if shift:
            user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(per_char_sec)


def park_safe_cursor_rest(
    *,
    origin_x: int = 0,
    origin_y: int = 0,
    client_width: int | None = None,
    client_height: int | None = None,
    settle_sec: float = 0.05,
) -> dict:
    """Move the cursor to SAFE_CURSOR_REST (client interior; outside edge band).

    Canonical post-input park so Sims edge-pan stops. Reuses camera_traverse
    geometry — do not invent a second rest point in callers.
    """
    _require_win32()
    from betterinstincts.camera_traverse import safe_rest_point

    rest = safe_rest_point(
        origin_x=int(origin_x),
        origin_y=int(origin_y),
        client_width=client_width,
        client_height=client_height,
    )
    sx, sy = int(rest["screen"][0]), int(rest["screen"][1])
    move_cursor(sx, sy, settle_sec=settle_sec, allow_edge=True)
    return {
        "state": "SAFE_CURSOR_REST",
        "screen": [sx, sy],
        "client": list(rest["client"]),
        "edge_band_px": rest.get("edge_band_px"),
    }


def move_cursor(
    x: int,
    y: int,
    *,
    settle_sec: float = 0.05,
    allow_edge: bool = False,
) -> None:
    """Park the cursor at absolute screen coordinates without clicking.

    Used by camera-safe traverse to leave SAFE_CURSOR_REST outside the edge
    pan band so the Sims camera stops drifting after a host step.
    Refuses EDGE_MOUSE_PARK unless allow_edge=True (internal rest helper).
    """
    _require_win32()
    import ctypes

    if not allow_edge:
        from betterinstincts.camera_traverse import classify_cursor, load_contract

        cfg = load_contract()
        d = cfg.get("defaults") or {}
        w = int(d.get("client_width") or 1920)
        h = int(d.get("client_height") or 1080)
        hit = classify_cursor(int(x), int(y), client_width=w, client_height=h, cfg=cfg)
        if hit.get("in_edge_band"):
            park_safe_cursor_rest(settle_sec=settle_sec)
            return
    ctypes.windll.user32.SetCursorPos(int(x), int(y))
    time.sleep(settle_sec)


def _send_mouse_button_click(
    x: int, y: int, *, down_flag: int, up_flag: int,
    settle_sec: float, between_sec: float, safe_rest_after: bool,
) -> None:
    """One canonical Windows mouse click owner; no caller-owned Win32 types."""
    _require_win32()
    ctypes, MOUSEINPUT, INPUT = _mouse_input_types()
    user32 = ctypes.windll.user32
    user32.SetCursorPos(int(x), int(y))
    time.sleep(settle_sec)
    for flag in (down_flag, up_flag):
        inp = INPUT(type=0)
        inp.mi = MOUSEINPUT(0, 0, 0, flag, 0, None)
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        time.sleep(between_sec)
    if safe_rest_after:
        park_safe_cursor_rest(settle_sec=settle_sec)


def send_click(
    x: int,
    y: int,
    *,
    settle_sec: float = 0.05,
    between_sec: float = 0.05,
    safe_rest_after: bool = True,
) -> None:
    """Left click and park interior; caller must own host admission."""
    _send_mouse_button_click(
        x, y, down_flag=2, up_flag=4, settle_sec=settle_sec,
        between_sec=between_sec, safe_rest_after=safe_rest_after,
    )


def send_right_click(
    x: int,
    y: int,
    *,
    settle_sec: float = 0.05,
    between_sec: float = 0.05,
    safe_rest_after: bool = True,
) -> None:
    """Right click exact target; use only through admitted portrait-follow port."""
    _send_mouse_button_click(
        x, y, down_flag=8, up_flag=16, settle_sec=settle_sec,
        between_sec=between_sec, safe_rest_after=safe_rest_after,
    )


def send_wheel(
    notches: int,
    *,
    x: int = 960,
    y: int = 540,
    settle_sec: float = 0.05,
    safe_rest_after: bool = True,
) -> None:
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
    if safe_rest_after:
        park_safe_cursor_rest(settle_sec=settle_sec)


def right_drag(
    dx: int,
    dy: int,
    *,
    x0: int = 960,
    y0: int = 540,
    steps: int = 24,
    settle_sec: float = 0.05,
    safe_rest_after: bool = True,
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
    if safe_rest_after:
        park_safe_cursor_rest(settle_sec=settle_sec)
