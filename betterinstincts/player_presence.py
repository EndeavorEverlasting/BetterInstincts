"""Classify whether the operator is playing on the Sims canvas.

Pure policy over an injectable probe. Fail closed to YIELD_TO_PLAYER.
Never installs a global mouse hook. Never SendInputs.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Optional

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "player-presence.v1.json"
MAX_BYTES = 32_000


class PlayerPresenceError(ValueError):
    pass


@dataclass(frozen=True)
class PresenceProbe:
    """Snapshot from OS adapters or test fakes."""

    foreground_is_sims: bool
    cursor_in_client: bool
    last_input_age_ms: Optional[int] = None
    operator_declared_playing: bool = False
    player_directed_queue: bool = False
    probe_ok: bool = True


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise PlayerPresenceError("PLAYER_PRESENCE_CONTRACT_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.player-presence/v1":
        raise PlayerPresenceError("BAD_PLAYER_PRESENCE_SCHEMA")
    if "SENDINPUT_WHILE_PLAYER_PLAYING" not in set(cfg.get("forbidden", [])):
        raise PlayerPresenceError("MUST_FORBID_SENDINPUT_WHILE_PLAYING")
    return cfg


def classify(
    probe: PresenceProbe,
    *,
    session_active: bool = False,
    grace_ms: Optional[int] = None,
) -> dict:
    cfg = load_contract()
    grace = int(grace_ms if grace_ms is not None else cfg.get("grace_ms_default", 2500))
    if not probe.probe_ok:
        return {
            "state": "UNKNOWN_PRESENCE",
            "host": "YIELD_TO_PLAYER",
            "reason": "PROBE_FAILED",
            "session_active": bool(session_active),
            "proof_ceiling": cfg.get("proof_ceiling"),
        }

    on_canvas = bool(probe.foreground_is_sims and probe.cursor_in_client)
    recent_input = (
        probe.last_input_age_ms is not None
        and probe.foreground_is_sims
        and 0 <= int(probe.last_input_age_ms) <= grace
    )
    playing = bool(
        on_canvas
        or recent_input
        or probe.operator_declared_playing
        or probe.player_directed_queue
    )
    if playing:
        return {
            "state": "PLAYER_PLAYING",
            "host": "YIELD_TO_PLAYER",
            "reason": "PLAYER_ACTIVE",
            "on_canvas": on_canvas,
            "recent_input": recent_input,
            "session_active": bool(session_active),
            "proof_ceiling": cfg.get("proof_ceiling"),
        }
    if not session_active:
        return {
            "state": "UNKNOWN_PRESENCE",
            "host": "YIELD_TO_PLAYER",
            "reason": "SESSION_INACTIVE",
            "on_canvas": on_canvas,
            "session_active": False,
            "proof_ceiling": cfg.get("proof_ceiling"),
        }
    return {
        "state": "HOST_MAY_AUTOMATE",
        "host": "EVALUATE_AND_OPTIONAL_EXECUTE",
        "reason": "PLAYER_NOT_PLAYING_SESSION_ACTIVE",
        "on_canvas": False,
        "session_active": True,
        "proof_ceiling": cfg.get("proof_ceiling"),
    }


def probe_windows(process_id: Optional[int] = None) -> PresenceProbe:
    """Best-effort Win32 probe. Fail closed if anything is ambiguous."""
    import sys

    if sys.platform != "win32":
        return PresenceProbe(
            foreground_is_sims=False,
            cursor_in_client=False,
            probe_ok=False,
        )
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    fg = user32.GetForegroundWindow()
    if not fg:
        return PresenceProbe(False, False, probe_ok=False)
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(fg, ctypes.byref(pid))
    length = user32.GetWindowTextLengthW(fg)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(fg, buf, length + 1)
    title = buf.value or ""
    is_sims = "Sims" in title
    if process_id is not None and int(pid.value) != int(process_id):
        # FG belongs to another process — treat as not on Sims canvas.
        is_sims = False
    rect = wintypes.RECT()
    if not user32.GetClientRect(fg, ctypes.byref(rect)):
        return PresenceProbe(is_sims, False, probe_ok=False)
    pt = wintypes.POINT()
    if not user32.GetCursorPos(ctypes.byref(pt)):
        return PresenceProbe(is_sims, False, probe_ok=False)
    # Map screen cursor into client coords of FG window.
    if not user32.ScreenToClient(fg, ctypes.byref(pt)):
        return PresenceProbe(is_sims, False, probe_ok=False)
    in_client = (
        rect.left <= pt.x <= rect.right and rect.top <= pt.y <= rect.bottom
    )
    last_input_age = None
    try:
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            tick = ctypes.windll.kernel32.GetTickCount()
            last_input_age = int(tick - info.dwTime) & 0xFFFFFFFF
    except Exception:
        last_input_age = None
    return PresenceProbe(
        foreground_is_sims=bool(is_sims),
        cursor_in_client=bool(in_client and is_sims),
        last_input_age_ms=last_input_age,
        probe_ok=True,
    )


ProbeFn = Callable[[], PresenceProbe]
