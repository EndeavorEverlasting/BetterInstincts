"""Explicit, bounded human-to-host screen-control arbitration (P95).

Pure policy; no hooks, polling loops, inputs, paths, or game access.
Windows adapters provide independent, fresh probes at the action boundary.
"""
from __future__ import annotations

from typing import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
import os
import time

from betterinstincts.player_presence import PresenceProbe

DEFAULT_IDLE_MS = 8000
MIN_IDLE_MS = 1000
MAX_IDLE_MS = 120000
CONFIRM_INTERVAL_SEC = 0.20


class HandoffError(ValueError):
    pass


def decide(
    probe: PresenceProbe,
    *,
    session_active: bool,
    idle_ms: int = DEFAULT_IDLE_MS,
) -> dict:
    """Classify one presence snapshot; idle requires trustworthy input age.

    A stationary cursor on Sims is not perpetual evidence of human activity.
    Conversely, recent input *anywhere* on the desktop blocks screen takeover.
    Explicit operator playing or player-directed queue always wins.
    """
    if isinstance(idle_ms, bool) or not isinstance(idle_ms, int) or not MIN_IDLE_MS <= idle_ms <= MAX_IDLE_MS:
        raise HandoffError("IDLE_THRESHOLD_OUT_OF_RANGE")
    reason = None
    if not session_active:
        reason = "SESSION_INACTIVE"
    elif not isinstance(probe, PresenceProbe) or not probe.probe_ok:
        reason = "PRESENCE_UNKNOWN"
    elif probe.operator_declared_playing or probe.player_directed_queue:
        reason = "PLAYER_OVERRIDE"
    elif (
        isinstance(probe.last_input_age_ms, bool)
        or not isinstance(probe.last_input_age_ms, int)
        or probe.last_input_age_ms < 0
    ):
        reason = "INPUT_AGE_UNKNOWN"
    elif probe.last_input_age_ms < idle_ms:
        reason = "RECENT_HUMAN_INPUT"
    return {
        "state": "HOST_READY" if reason is None else "PAUSED_FOR_PLAYER",
        "owner": "HOST" if reason is None else "HUMAN",
        "reason": reason or "IDLE_CONFIRMED",
        "idle_ms": idle_ms,
        "screen_control_allowed": reason is None,
        "proof_ceiling": "PROBE_ONLY_NOT_GAME_CONTROL_OR_CERTIFICATION",
    }


def confirm(
    probe_fn: Callable[[], PresenceProbe],
    *,
    session_active: bool,
    idle_ms: int = DEFAULT_IDLE_MS,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> dict:
    """Two fresh samples before *one* screen action; fail closed on any change.

    This is a one-action admission check, never a transferable lease. The
    caller must recheck before subsequent actions, including after SendInput.
    """
    try:
        first = decide(probe_fn(), session_active=session_active, idle_ms=idle_ms)
        if not first["screen_control_allowed"]:
            return {**first, "samples_checked": 1}
        sleep_fn(CONFIRM_INTERVAL_SEC)
        second = decide(probe_fn(), session_active=session_active, idle_ms=idle_ms)
    except (Exception) as exc:
        # Sensor failures must never grant a control token.
        if isinstance(exc, HandoffError) and str(exc) == "IDLE_THRESHOLD_OUT_OF_RANGE":
            raise
        return {
            "state": "PAUSED_FOR_PLAYER",
            "owner": "HUMAN",
            "reason": "PROBE_FAILED",
            "idle_ms": idle_ms,
            "screen_control_allowed": False,
            "samples_checked": 0,
            "proof_ceiling": "PROBE_ONLY_NOT_GAME_CONTROL_OR_CERTIFICATION",
        }
    return {**second, "samples_checked": 2}


def as_presence(handoff: dict) -> dict:
    """Project one canonical arbiter result into existing listener vocabulary."""
    ready = handoff["screen_control_allowed"]
    reason = handoff["reason"]
    return {
        "state": (
            "HOST_MAY_AUTOMATE" if ready else
            "PLAYER_PLAYING" if reason in {"PLAYER_OVERRIDE", "RECENT_HUMAN_INPUT"}
            else "UNKNOWN_PRESENCE"
        ),
        "host": "EVALUATE_AND_OPTIONAL_EXECUTE" if ready else "YIELD_TO_PLAYER",
        "reason": reason,
        "idle_ms": handoff["idle_ms"],
        "proof_ceiling": handoff["proof_ceiling"],
    }


ROOT = Path(__file__).resolve().parents[1]
LOCK_ROOT = ROOT / "dist" / "host-listener"


def _lock_dir(lock_root: Path | None = None) -> Path:
    root = Path(lock_root) if lock_root is not None else LOCK_ROOT
    if root.is_symlink():
        raise HandoffError("SCREEN_LOCK_ROOT_UNSAFE")
    return root


@contextmanager
def _named_screen_lock(filename: str, *, lock_root: Path | None = None) -> Iterator[None]:
    root = _lock_dir(lock_root)
    root.mkdir(parents=True, exist_ok=True)
    lock = root / filename
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(lock, flags, 0o600)
    except FileExistsError as exc:
        raise HandoffError("SCREEN_OWNER_BUSY") from exc
    try:
        owner_inode = os.fstat(fd).st_ino
        yield
    finally:
        try:
            os.close(fd)
        finally:
            try:
                if lock.is_file() and not lock.is_symlink() and lock.stat().st_ino == owner_inode:
                    lock.unlink()
            except OSError:
                pass


@contextmanager
def exclusive_desktop_owner(*, lock_root: Path | None = None) -> Iterator[None]:
    """One desktop input writer shared by Playwright and all adopted Sims scripts.

    Stale/foreign locks fail closed. No age expiry or automatic lock theft.
    """
    with _named_screen_lock("desktop-shared.lock", lock_root=lock_root):
        yield


def desktop_owner_busy(*, lock_root: Path | None = None) -> bool:
    lock = _lock_dir(lock_root) / "desktop-shared.lock"
    return lock.exists() or lock.is_symlink()


@contextmanager
def exclusive_screen_owner(
    process_id: int,
    *,
    lock_root: Path | None = None,
) -> Iterator[None]:
    """The per-game-process mutex also participates in desktop-wide input.

    The desktop lock must be acquired first to avoid opposing lock ordering
    between cooperating Sims executors and Playwright agents.
    """
    if isinstance(process_id, bool) or not isinstance(process_id, int) or process_id <= 0:
        raise HandoffError("EXACT_GAME_PROCESS_ID_REQUIRED")
    with exclusive_desktop_owner(lock_root=lock_root):
        with _named_screen_lock("screen-" + str(process_id) + ".lock", lock_root=lock_root):
            yield


def screen_owner_busy(process_id: int, *, lock_root: Path | None = None) -> bool:
    """Advisory status for read-only agents; exclusive_screen_owner is authority."""
    if isinstance(process_id, bool) or not isinstance(process_id, int) or process_id <= 0:
        raise HandoffError("EXACT_GAME_PROCESS_ID_REQUIRED")
    root = _lock_dir(lock_root)
    lock = root / ("screen-" + str(process_id) + ".lock")
    return desktop_owner_busy(lock_root=lock_root) or lock.exists() or lock.is_symlink()
