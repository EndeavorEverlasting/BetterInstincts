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
    HandoffError,
    MIN_IDLE_MS,
    decide,
    exclusive_desktop_owner,
    exclusive_live_hud_surface,
    list_busy_live_hud_surfaces,
    live_hud_surface_busy,
)
from betterinstincts.player_presence import PresenceProbe
from betterinstincts.effect_authority import assess_effect

HUD_SURFACE_ALIASES = {
    "BOTTOM_RIGHT_PANEL": "BOTTOM_RIGHT_PANEL",
    "PANEL_SKILLS": "BOTTOM_RIGHT_PANEL",
    "PANEL_CAREER": "BOTTOM_RIGHT_PANEL",
    "PANEL_ASPIRATIONS": "BOTTOM_RIGHT_PANEL",
    "PANEL_RELATIONSHIPS": "BOTTOM_RIGHT_PANEL",
    "PANEL_INVENTORY": "BOTTOM_RIGHT_PANEL",
    "PANEL_SIMOLOGY": "BOTTOM_RIGHT_PANEL",
    "PANEL_NEEDS": "BOTTOM_RIGHT_PANEL",
    "PANEL_CLUBS": "BOTTOM_RIGHT_PANEL",
    "PHONE": "PHONE",
    "PHONE_INTERFACE": "PHONE",
    "live.phone": "PHONE",
    "CHEAT_CONSOLE": "CHEAT_CONSOLE",
    "CONSOLE": "CHEAT_CONSOLE",
}

SURFACE_CLEARABLE_KIND = {
    "BOTTOM_RIGHT_PANEL": "BOTTOM_RIGHT_PANEL_EXPANDED",
    "PHONE": "PHONE_INTERFACE_EXPANDED",
    "CHEAT_CONSOLE": "CHEAT_CONSOLE",
}

DEFAULT_IDLE_MS = 15_000
MAX_QUEUE = 32
MAX_OBSERVATION_SECONDS = 2.0
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


@dataclass(frozen=True)
class PassiveObservation:
    """Explicit trusted read-only work. Never an input/OS mutation adapter."""
    work_id: str
    validate: Validate
    observe: Callable[[], Awaitable[Any]]


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
        self.pending_observations: deque[PassiveObservation] = deque()
        self.completed: list[str] = []
        self.needs_review: set[str] = set()
        self.suspended: dict[str, QueuedStep | PassiveObservation] = {}
        self.events: deque[dict[str, str]] = deque(maxlen=128)
        self._running = False

    def enqueue(self, step: QueuedStep) -> None:
        if not isinstance(step, QueuedStep) or not isinstance(step.work_id, str) or not IDENTIFIER.fullmatch(step.work_id):
            raise ValueError("INVALID_WORK_ID")
        if not callable(step.action) or not callable(step.validate):
            raise ValueError("CALLBACKS_REQUIRED")
        if step.work_id in self.completed or step.work_id in self.needs_review or any(
            p.work_id == step.work_id for p in self.pending
        ) or any(p.work_id == step.work_id for p in self.pending_observations):
            raise ValueError("WORK_ID_ALREADY_REGISTERED")
        if len(self.pending) + len(self.pending_observations) + len(self.suspended) >= MAX_QUEUE:
            raise ValueError("QUEUE_FULL")
        self.pending.append(step)
        self._event("ENQUEUED", step.work_id)

    def enqueue_effect(self, work_id: str, validate: Validate,
                       effect: Callable[[], Awaitable[Any]]) -> None:
        """Preferred adapter API: one effect with a mandatory fresh checkpoint.

        Native game/mod/CLI effects use the same human-first gate as desktop
        input. The effect must be atomic and bounded; split sequences into
        separate work items. This cannot preempt an already executing call.
        """
        if not callable(effect):
            raise ValueError("CALLBACKS_REQUIRED")

        async def action(checkpoint: Checkpoint) -> Any:
            await checkpoint()
            return await effect()

        self.enqueue(QueuedStep(work_id, validate, action))


    def enqueue_observation(self, work_id: str, validate: Validate,
                            observe: Callable[[], Awaitable[Any]]) -> None:
        """Queue trusted, bounded, read-only observation without screen ownership.

        Never pass game mutation, Playwright, mouse, keyboard, Windows settings,
        focus changing capture, or arbitrary external/third-party callbacks.
        Callbacks are reviewed code, not sandboxed by their Python type.
        """
        if not isinstance(work_id, str) or not IDENTIFIER.fullmatch(work_id):
            raise ValueError("INVALID_WORK_ID")
        if not callable(validate) or not callable(observe):
            raise ValueError("CALLBACKS_REQUIRED")
        if work_id in self.completed or work_id in self.needs_review or any(
            x.work_id == work_id for x in self.pending
        ) or any(x.work_id == work_id for x in self.pending_observations):
            raise ValueError("WORK_ID_ALREADY_REGISTERED")
        if len(self.pending) + len(self.pending_observations) + len(self.suspended) >= MAX_QUEUE:
            raise ValueError("QUEUE_FULL")
        self.pending_observations.append(PassiveObservation(work_id, validate, observe))
        self._event("ENQUEUED_OBSERVATION", work_id)

    async def _run_observation_once(self) -> dict[str, str | int]:
        """One read-only observation can run even while a human uses the mouse.

        It is independent of UI input and does not acquire a desktop lock.
        An exception/timeout quarantines work; no blind retry or replay.
        """
        item = self.pending_observations[0]
        decision = assess_effect("PASSIVE_OBSERVATION", session_active=bool(self.session_active()))
        if not decision["execute_allowed"]:
            return {"state": "WAITING_FOR_USER", "pending": len(self.pending) + len(self.pending_observations)}
        self._running = True
        try:
            valid = await asyncio.wait_for(item.validate(), timeout=MAX_OBSERVATION_SECONDS)
            if valid is not True:
                self._suspend_observation(item, "NEEDS_REVALIDATION")
                return {"state": "NEEDS_REVALIDATION", "pending": len(self.pending) + len(self.pending_observations)}
            if not self.session_active():
                return {"state": "WAITING_FOR_USER", "pending": len(self.pending) + len(self.pending_observations)}
            await asyncio.wait_for(item.observe(), timeout=MAX_OBSERVATION_SECONDS)
            self.pending_observations.popleft()
            self.completed.append(item.work_id)
            self._event("COMPLETED_OBSERVATION", item.work_id)
            return {"state": "COMPLETED", "pending": len(self.pending) + len(self.pending_observations),
                    "effect_class": "PASSIVE_OBSERVATION"}
        except Exception as exc:
            self._suspend_observation(item, "NEEDS_RECONCILIATION")
            return {"state": "NEEDS_RECONCILIATION", "pending": len(self.pending) + len(self.pending_observations),
                    "error_type": type(exc).__name__}
        finally:
            self._running = False

    def _suspend_observation(self, item: PassiveObservation, state: str) -> None:
        self.pending_observations.popleft()
        self.needs_review.add(item.work_id)
        self.suspended[item.work_id] = item
        self._event(state, item.work_id)

    def _suspend(self, item: QueuedStep, state: str) -> None:
        self.needs_review.add(item.work_id)
        self.suspended[item.work_id] = item
        self.pending.popleft()
        self._event(state, item.work_id)

    def reconcile(self, work_id: str, *, outcome_observed: bool,
                  completed: bool = False, remainder: QueuedStep | None = None) -> None:
        """Resolve observed partial work; never replay the original callback.

        The adapter supplies either confirmed completion or a freshly rebuilt
        remainder with the same intent ID. Requeued work still passes ordinary
        scene validation, exclusive ownership and two fresh idle probes.
        """
        if work_id not in self.suspended:
            raise ValueError("SUSPENDED_WORK_NOT_FOUND")
        if outcome_observed is not True:
            raise ValueError("OBSERVED_OUTCOME_REQUIRED")
        if completed is True and remainder is None:
            self.completed.append(work_id)
            self._event("COMPLETED", work_id)
        elif completed is False and isinstance(remainder, QueuedStep):
            if remainder.work_id != work_id or not callable(remainder.validate) or not callable(remainder.action):
                raise ValueError("INVALID_REMAINDER")
            self.pending.appendleft(remainder)
            self._event("REVALIDATION_QUEUED", work_id)
        else:
            raise ValueError("CONFIRM_COMPLETION_OR_SUPPLY_REMAINDER")
        del self.suspended[work_id]
        self.needs_review.remove(work_id)

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
            return {"state": "BUSY", "pending": len(self.pending) + len(self.pending_observations)}
        # Observation is a disjoint, reviewed read-only lane. It may complete
        # while a screen-effect queue is waiting for physical human inactivity.
        if self.pending_observations:
            return await self._run_observation_once()
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
                        self._suspend(item, "NEEDS_REVALIDATION")
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
                self._suspend(item, "NEEDS_RECONCILIATION")
                return {"state": "NEEDS_RECONCILIATION", "pending": len(self.pending)}
            self._event("WAITING_FOR_USER", item.work_id)
            return {"state": "WAITING_FOR_USER", "pending": len(self.pending)}
        except Exception as exc:
            # Unknown outcome must NOT be automatically replayed: a click may
            # have completed before an adapter error or post-action human input.
            self._suspend(item, "NEEDS_RECONCILIATION")
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
            if last["state"] == "COMPLETED" and not self.pending and not self.pending_observations:
                return last
            if last["state"].startswith("WAITING"):
                await self.sleep(self.poll_seconds)
        return {"state": "WAIT_BUDGET_REACHED", "pending": len(self.pending)}


def resolve_live_hud_surface(token: str) -> str:
    """Map panel/phone/console aliases to the exclusive surface id."""
    if not isinstance(token, str) or not token:
        raise ValueError("LIVE_HUD_SURFACE_REQUIRED")
    surface = HUD_SURFACE_ALIASES.get(token) or HUD_SURFACE_ALIASES.get(token.upper())
    if not surface:
        raise ValueError("UNKNOWN_LIVE_HUD_SURFACE")
    return surface


def assess_live_hud_surface_claim(
    surface_token: str,
    *,
    lock_root: Path | None = None,
) -> dict:
    """Decide whether this agent may open a Live HUD surface without fighting a peer.

    Skills (BOTTOM_RIGHT) vs phone are mutually exclusive. Busy peer → WAITING_FOR_AGENT;
    work must be retained, never cancelled. Plans never grant SendInput.
    """
    surface = resolve_live_hud_surface(surface_token)
    busy_others = [
        s for s in list_busy_live_hud_surfaces(lock_root=lock_root) if s != surface
    ]
    this_busy = live_hud_surface_busy(surface, lock_root=lock_root)
    if busy_others:
        return {
            "state": "WAITING_FOR_AGENT",
            "gate": "PEER_HUD_SURFACE_LEASED",
            "surface": surface,
            "peer_surfaces": busy_others,
            "execute_allowed": False,
            "retain_work": True,
            "reason": "LIVE_HUD_MUTUAL_EXCLUSION",
            "note": "Do not open phone while Skills (or another exclusive HUD) is peer-leased.",
        }
    if this_busy:
        return {
            "state": "WAITING_FOR_AGENT",
            "gate": "SAME_HUD_SURFACE_BUSY",
            "surface": surface,
            "execute_allowed": False,
            "retain_work": True,
            "reason": "SCREEN_OWNER_BUSY",
        }
    return {
        "state": "HUD_SURFACE_CLAIM_READY",
        "gate": "LIVE_HUD_SURFACE_AVAILABLE",
        "surface": surface,
        "clearable_kind": SURFACE_CLEARABLE_KIND[surface],
        "execute_allowed": False,
        "claim_helper": "exclusive_live_hud_surface",
        "proof_ceiling": "OFFLINE_HUD_SURFACE_LEASE_POLICY_NOT_LIVE_TWO_AGENT_CERT",
    }


def peer_hud_leases_for_overlay_clear(*, lock_root: Path | None = None) -> list[dict]:
    """Observation fragment: withhold overlay-clear of these peer-leased kinds."""
    out: list[dict] = []
    for surface in list_busy_live_hud_surfaces(lock_root=lock_root):
        out.append(
            {
                "surface": surface,
                "clearable_kind": SURFACE_CLEARABLE_KIND[surface],
                "reason": "PEER_LEASED_HUD_SURFACE",
            }
        )
    return out
