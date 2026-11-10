#!/usr/bin/env python3
"""Calibrated PrintWindow/SendInput coords: Seasons → Willow Creek → lot → Live.

Observed on borderless 1920x1080 for disposable LabLab (BI_LAB_DISPOSABLE_01).
Does not touch personal saves. Prefer story quiz for CAS when available; this
script covers post-CAS placement only. Default is dry-run (prints steps).

Prefer an empty green outline lot on first placement (objective for disposable
lab boots). LOT_STREAMLET is a vacant furnished starter used only as fallback
when empty-lot clicks fail PrintWindow verification.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from betterinstincts.fixed_ui_click_map import load_escape_menu_coords

# Offline-calibrated against PrintWindow bitmaps (1920x1080 borderless).
SEASON_SUMMER = (850, 520)
SEASON_CONTINUE = (1877, 1058)  # green check lower edge; not Cancel X
WORLD_WILLOW_CREEK = (234, 300)  # first residential circular tile
LOT_EMPTY_WILLOW = (1560, 670)  # vacant green outline (no house) — prefer this
LOT_BARGAIN_BEND = (1400, 840)  # Willow Creek empty 30x20 (~§2k); tip-verified in move mode
LOT_STREAMLET = (1122, 799)  # vacant furnished starter fallback (~§15k)
HUD_MANAGE_WORLDS = (1558, 22)  # Live top-right pin (Gallery is ~1608)
LOT_MOVE_HOUSEHOLD = (1692, 1000)  # expanded lot-action truck (after Streamlet selected)
MOVE_TRUCK = (1840, 1017)  # confirm destination truck (move mode)
MOVE_CONFIRM = (1240, 740)  # blue check on "household is moving" modal
_ESCAPE_MENU = load_escape_menu_coords()
MENU_OPTIONS = _ESCAPE_MENU["menu_options"]  # live.top_options @ y≈22
MENU_MANAGE_WORLDS = (960, 713)  # Options MENU row; click blue text
MENU_SAVE_AND_GO_MW = (960, 556)  # Save and Go to Manage Worlds (not question ~y492)
MENU_SAVE = _ESCAPE_MENU["save"]  # contracts/fixed-ui-click-map escape_menu_1920x1080
MENU_SAVE_AS = _ESCAPE_MENU["save_as"]  # 2px below Save — use distinct target_id
MENU_X = (1085, 330)
LAB_SAVE_ROW = (720, 550)  # LabLab / My Saved Game 3 thumbnail
LAB_SAVE_PILL = (1225, 500)  # row Save (above Delete)
LAB_OVERWRITE_CHECK = (1094, 589)
PHONE_HUD = (290, 1060)  # smartphone between notebook and calendar
PHONE_HOUSEHOLD = (275, 840)  # middle-row blue house (not Social Bunny ~y=760)
PHONE_REAL_ESTATE = (280, 780)  # house app on phone home grid (approx)
HUD_BUILD_MODE = (1505, 22)  # Live → Build hammer
HUD_LIVE_FROM_BUILD = (1585, 35)  # Build → Live people icon (Esc opens MENU — avoid)
NEEDS_PANEL = (1822, 1062)  # Live Needs icon (not Simology ~1779)
FRIDGE_CATALOG = (480, 940)  # first fridge after Kitchen illustration click
FRIDGE_PLACE = (1100, 250)  # inland Bargain Bend (avoid sidewalk ~y520+)
KITCHEN_ROOM = (100, 907)  # Objects-by-Room stove icon (approx; prefer green detect)

STEPS = (
    ("season_summer", SEASON_SUMMER),
    ("season_continue", SEASON_CONTINUE),
    ("world_willow_creek", WORLD_WILLOW_CREEK),
    ("lot_empty_willow", LOT_EMPTY_WILLOW),
    ("move_truck", MOVE_TRUCK),
    ("move_confirm", MOVE_CONFIRM),
)


def _click(hwnd: int, x: int, y: int) -> None:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    ABS, MOVE, LD, LU = 0x8000, 1, 2, 4

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
    time.sleep(0.35)
    sx = user32.GetSystemMetrics(0)
    sy = user32.GetSystemMetrics(1)
    ax = int(x * 65535 / (sx - 1))
    ay = int(y * 65535 / (sy - 1))

    def send(flags: int, dx: int = 0, dy: int = 0) -> None:
        inp = INPUT(type=0, mi=MOUSEINPUT(dx, dy, 0, flags, 0, None))
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    user32.SetCursorPos(x, y)
    time.sleep(0.08)
    send(MOVE | ABS, ax, ay)
    time.sleep(0.05)
    send(LD | ABS, ax, ay)
    time.sleep(0.2)
    send(LU | ABS, ax, ay)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true",
                        help="Actually click (default: print calibrated steps only)")
    parser.add_argument("--process-id", type=int, default=None)
    parser.add_argument("--delay", type=float, default=3.0)
    args = parser.parse_args(argv)
    payload = {
        "schema": "betterinstincts.cas-place-live/v1",
        "resolution": "1920x1080",
        "proof_ceiling": "CALIBRATED_COORDS_NOT_LIVE_CERTIFICATION",
        "steps": [{"name": n, "xy": list(xy)} for n, xy in STEPS],
        "menu": {"save": list(MENU_SAVE), "save_as": list(MENU_SAVE_AS),
                 "close_x": list(MENU_X)},
    }
    if not args.execute:
        print(json.dumps(payload, sort_keys=True))
        return 0
    if sys.platform != "win32":
        print(json.dumps({"state": "BLOCKED", "reason": "WINDOWS_REQUIRED"}, sort_keys=True))
        return 2
    from scripts.cas_finish_disposable import find_sims_hwnd

    hwnd, pid = find_sims_hwnd(args.process_id)
    for name, (x, y) in STEPS:
        _click(hwnd, x, y)
        time.sleep(args.delay)
        print(json.dumps({"clicked": name, "xy": [x, y], "process_id": pid},
                         sort_keys=True))
    print(json.dumps({"state": "PLACE_CLICKS_DISPATCHED",
                      "proof_ceiling": "CLICK_DISPATCH_ONLY_VERIFY_WITH_PRINTWINDOW",
                      "next": "game_host manual-cas-complete then confirm"},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
