#!/usr/bin/env python3
"""Capture a Sims window via PrintWindow without desktop screenshots.

Desktop / Playwright / computer-use screenshots minimize The Sims 4 (same class of
focus/capture conflict as Signal). PrintWindow reads the HWND client bitmap and
does not use desktop duplication, so the game can stay restored and focused.
This is still NOT Live Mode proof and NOT a vision classifier.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist" / "game-host"


class GateError(ValueError):
    """Capture gate; never interpreted as gameplay success."""


def capture_sims(*, process_id: int | None, out: Path) -> dict:
    if sys.platform != "win32":
        raise GateError("LOCAL_WINDOWS_GAME_HOST_REQUIRED")
    import ctypes
    from ctypes import wintypes
    from PIL import Image

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    WM_SYSCOMMAND, SC_RESTORE = 0x0112, 0xF120
    PW_RENDERFULLCONTENT = 2

    class RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                    ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

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
        raise GateError("SIMS_WINDOW_NOT_FOUND")
    if len(found) > 1 and process_id is None:
        raise GateError("AMBIGUOUS_SIMS_WINDOW_REQUIRE_PROCESS_ID")
    hwnd, pid = found[0]
    user32.PostMessageW(hwnd, WM_SYSCOMMAND, SC_RESTORE, 0)
    user32.ShowWindow(hwnd, 9)
    user32.AllowSetForegroundWindow(-1)
    user32.SetForegroundWindow(hwnd)

    rc = RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rc))
    width, height = rc.right - rc.left, rc.bottom - rc.top
    if width < 64 or height < 64 or width * height > 16_000_000:
        raise GateError("INVALID_CLIENT_SIZE")
    dest = out.resolve()
    if not dest.is_relative_to((OUTPUT).resolve()) and not dest.is_relative_to(ROOT.resolve()):
        # Prefer ignored dist/, but allow explicit relative paths under the repo.
        raise GateError("CAPTURE_PATH_OUTSIDE_REPO")
    dest.parent.mkdir(parents=True, exist_ok=True)

    hdc = user32.GetDC(hwnd)
    mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, width, height)
    old = gdi32.SelectObject(mem, bmp)
    ok = user32.PrintWindow(hwnd, mem, PW_RENDERFULLCONTENT)
    if not ok:
        gdi32.SelectObject(mem, old)
        gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(mem)
        user32.ReleaseDC(hwnd, hdc)
        raise GateError("PRINTWINDOW_FAILED")

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long),
                    ("biHeight", ctypes.c_long), ("biPlanes", wintypes.WORD),
                    ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                    ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD),
                    ("biClrImportant", wintypes.DWORD)]

    header = BITMAPINFOHEADER()
    header.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    header.biWidth = width
    header.biHeight = -height
    header.biPlanes = 1
    header.biBitCount = 32
    buf = ctypes.create_string_buffer(width * height * 4)
    gdi32.GetDIBits(mem, bmp, 0, height, buf, ctypes.byref(header), 0)
    gdi32.SelectObject(mem, old)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(hwnd, hdc)

    image = Image.frombuffer("RGBX", (width, height), buf, "raw", "BGRX", 0, 1).convert("RGB")
    image.save(dest)
    return {
        "state": "PRINTWINDOW_CAPTURED",
        "process_id": pid,
        "hwnd": hwnd,
        "width": width,
        "height": height,
        "path": str(dest.relative_to(ROOT)) if dest.is_relative_to(ROOT) else str(dest),
        "iconic_after": bool(user32.IsIconic(hwnd)),
        "proof_ceiling": "WINDOW_BITMAP_ONLY_NOT_LIVE_MODE_OR_INPUT_PROOF",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--process-id", type=int, default=None)
    parser.add_argument("--out", type=Path, default=OUTPUT / "printwindow-latest.png")
    args = parser.parse_args(argv)
    try:
        result = capture_sims(process_id=args.process_id, out=args.out)
    except (GateError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
