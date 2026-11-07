"""Reusable opt-in screen admission for host --execute adapters (issue #35).

Composes control_handoff + host_listener + presence probes. One lease may span
multiple UI steps only when each step re-calls ensure_ready() — admissions are
never transferable. Does not SendInput, touch saves, or install watchers.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator

from betterinstincts.control_handoff import (
    DEFAULT_IDLE_MS,
    HandoffError,
    confirm,
    decide,
    exclusive_screen_owner,
)
from betterinstincts.host_listener import status as listener_status
from betterinstincts.player_presence import PresenceProbe, probe_windows


def require_execute_session(session_id: str | None, process_id: int | None) -> None:
    """Fail closed before any focus/click when --execute lacks session + PID."""
    if not session_id:
        raise HandoffError("HANDOFF_SESSION_REQUIRED")
    if process_id is None or isinstance(process_id, bool) or int(process_id) <= 0:
        raise HandoffError("EXACT_GAME_PROCESS_ID_REQUIRED")


@contextmanager
def admitted_screen_lease(
    process_id: int,
    session_id: str,
    *,
    idle_ms: int = DEFAULT_IDLE_MS,
    focus_fn: Callable[[], object] | None = None,
    probe_fn: Callable[[], PresenceProbe] | None = None,
    lock_root: Path | None = None,
) -> Iterator[Callable[[], dict]]:
    """Hold exclusive screen ownership; yield ensure_ready() for each UI step.

    ensure_ready probes, optionally focuses once, then double-confirms. Callers
    must invoke it immediately before every SendInput / keystroke burst.
    """
    require_execute_session(session_id, process_id)
    probe = probe_fn or (lambda: probe_windows(int(process_id)))
    with exclusive_screen_owner(int(process_id), lock_root=lock_root):
        focused = False

        def ensure_ready() -> dict:
            nonlocal focused
            if listener_status(session_id).get("state") != "ACTIVE":
                raise HandoffError("HOST_HANDOFF_SESSION_INACTIVE")
            preflight = decide(probe(), session_active=True, idle_ms=idle_ms)
            if not preflight["screen_control_allowed"]:
                raise HandoffError("HOST_PAUSED:" + str(preflight["reason"]))
            if focus_fn is not None and not focused:
                focus_fn()
                focused = True
            handoff = confirm(
                probe,
                session_active=listener_status(session_id).get("state") == "ACTIVE",
                idle_ms=idle_ms,
            )
            if not handoff["screen_control_allowed"]:
                raise HandoffError("HOST_PAUSED:" + str(handoff["reason"]))
            if listener_status(session_id).get("state") != "ACTIVE":
                raise HandoffError("HOST_HANDOFF_SESSION_INACTIVE")
            return handoff

        yield ensure_ready
