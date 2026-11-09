"""Cooperative, opt-in desktop workflow waiter for host and browser adapters.

The queue retains executable callbacks IN MEMORY while the agent process lives.
No hook, cron, daemon, key capture, scheduler installation, or automatic replay.
Every participating Playwright/Sims side effect MUST await the supplied checkpoint
immediately before it occurs; this API cannot control unrelated agent processes.
"""
from __future__ import annotations

import asyncio
import re
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from betterinstincts.control_handoff import (
    HandoffError, MIN_IDLE_MS, decide, exclusive_desktop_owner,
)
from betterinstincts.player_presence import PresenceProbe

DEFAULT_IDLE_MS = 15_000
MAX_QUEUE = 32
CONFIRM_GAP_SECONDS = 0.20
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")
Checkpoint = Callable[[], Awaitable[None]]
Action = Callable[[Checkpoint], Awaitable[Any]]
Validate = Callable[[], Awaitable[bool]]


class DeferredForHuman(Exception):
    """Trusted idle not yet proved; keep work in the queue."""


@dataclass(frozen=True)
class QueuedStep:
    work_id: str
    validate: Validate
    action: Action


class CooperativeScreenQueue:
    """One small, single-agent in-memory queue; cross-agent desktop lock.

    This is an explicit session, never background-autostart. Caller owns the
    trustworthy OS idle probe, session lifecycle, and game/browser intent.
    Unknown input age or absent sensor never grants screen control.
    """

    def __init__(
        self,
        probe: Callable[[], PresenceProbe],
        session_active: Callable[[], bool],
        *,
        idle_ms: int = DEFAULT_IDLE_MS,
        poll_seconds: float = 0.5,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        lock_root: Path | None = None,
    ):
        if isinstance(idle_ms, bool) or type(idle_ms) is not int or not MIN_IDLE_MS <= idle_ms <= 120000:
            raise ValueError("IDLE_THRESHOLD_OUT_OF_RANGE")
        if isinstance(poll_seconds, bool) or not isinstance(poll_seconds, (int, float)) or not 0.1 <= poll_seconds <= 5:
            raise ValueError("POLL_INTERVAL_OUT_OF_RANGE")
        self.probe = probe
        self.session_active = session_active
        self.idle_ms = idle_ms
        self.poll_seconds = float(poll_seconds)
        self.sleep = sleep
        self.lock_root = lock_root
        self.pending: deque[QueuedStep] = deque()
        self.completed: list[str] = []
        self.needs_review: set[str] = set()
        self.events: deque[dict[str, str]] = deque(maxlen=128)
        self._running = False

    def enqueue(self, step: QueuedStep) -> None:
        if not isinstance(step, QueuedStep) or not isinstance(step.work_id, str) or not IDENTIFIER.fullmatch(step.work_id):
            raise ValueError("INVALID_WORK_ID")
        if not callable(step.action) or not callable(step.validate):
            raise ValueError("CALLBACKS_REQUIRED")
        if step.work_id in self.completed or step.work_id in self.needs_review or any(
            p.work_id == step.work_id for p in self.pending
        ):
            raise ValueError("WORK_ID_ALREADY_REGISTERED")
        if len(self.pending) >= MAX_QUEUE:
            raise ValueError("QUEUE_FULL")
        self.pending.append(step)
        self._event("ENQUEUED", step.work_id)

    def _event(self, state: str, work_id: str) -> None:
        # Never log callbacks, keystrokes, URLs, player saves, or work payloads.
        self.events.append({"state": state, "work_id": work_id})

    async def checkpoint(self) -> None:
        """Two independent probes; call immediately before EACH UI side effect."""
        try:
            for n in range(2):
                if n:
                    await self.sleep(CONFIRM_GAP_SECONDS)
                result = decide(self.probe(), session_active=bool(self.session_active()), idle_ms=self.idle_ms)
                if not result["screen_control_allowed"]:
                    raise DeferredForHuman(result["reason"])
        except DeferredForHuman:
            raise
        except (HandoffError, Exception) as exc:
            raise DeferredForHuman("PRESENCE_PROBE_FAILED") from exc

    async def run_once(self) -> dict[str, str | int]:
        if self._running:
            return {"state": "BUSY", "pending": len(self.pending)}
        if not self.pending:
            return {"state": "EMPTY", "pending": 0}
        self._running = True
        item = self.pending[0]
        effect_started = False
        try:
            # No focus or browser launch before this check; fail-closed probe.
            await self.checkpoint()
            try:
                with exclusive_desktop_owner(lock_root=self.lock_root):
                    await self.checkpoint()
                    # Scene, save, player queue, document context and target
                    # ownership must be freshly checked by the adapter.
                    valid = await item.validate()
                    if valid is not True:
                        self.needs_review.add(item.work_id)
                        self.pending.popleft()
                        self._event("NEEDS_REVALIDATION", item.work_id)
                        return {"state": "NEEDS_REVALIDATION", "pending": len(self.pending)}
                    await self.checkpoint()
                    # Action is expected to await checkpoint before each
                    # click/type/navigate. Deferral must not consume the job.
                    # A callback may have made an effect. Do not blindly replay
                    # when human activity interrupts a partially run callback.
                    async def effect_checkpoint() -> None:
                        nonlocal effect_started
                        await self.checkpoint()
                        effect_started = True

                    await item.action(effect_checkpoint)
            except HandoffError as exc:
                if str(exc) == "SCREEN_OWNER_BUSY":
                    self._event("WAITING_FOR_AGENT", item.work_id)
                    return {"state": "WAITING_FOR_AGENT", "pending": len(self.pending)}
                raise
            self.pending.popleft()
            self.completed.append(item.work_id)
            self._event("COMPLETED", item.work_id)
            return {"state": "COMPLETED", "pending": len(self.pending)}
        except DeferredForHuman:
            if effect_started:
                self.needs_review.add(item.work_id)
                self.pending.popleft()
                self._event("NEEDS_RECONCILIATION", item.work_id)
                return {"state": "NEEDS_RECONCILIATION", "pending": len(self.pending)}
            self._event("WAITING_FOR_USER", item.work_id)
            return {"state": "WAITING_FOR_USER", "pending": len(self.pending)}
        except Exception as exc:
            # Unknown outcome must NOT be automatically replayed: a click may
            # have completed before an adapter error or post-action human input.
            self.needs_review.add(item.work_id)
            self.pending.popleft()
            self._event("NEEDS_RECONCILIATION", item.work_id)
            return {"state": "NEEDS_RECONCILIATION", "pending": len(self.pending), "error_type": type(exc).__name__}
        finally:
            self._running = False

    async def drain(self, *, max_checks: int = 120) -> dict[str, str | int]:
        """Bounded silent waiter; stopping never drops queued work."""
        if type(max_checks) is not int or not 1 <= max_checks <= 100000:
            raise ValueError("INVALID_CHECK_BUDGET")
        last: dict[str, str | int] = {"state": "EMPTY", "pending": 0}
        for _ in range(max_checks):
            last = await self.run_once()
            if last["state"] in {"EMPTY", "NEEDS_REVALIDATION", "NEEDS_RECONCILIATION", "BUSY"}:
                return last
            if last["state"] == "COMPLETED" and not self.pending:
                return last
            if last["state"].startswith("WAITING"):
                await self.sleep(self.poll_seconds)
        return {"state": "WAIT_BUDGET_REACHED", "pending": len(self.pending)}
