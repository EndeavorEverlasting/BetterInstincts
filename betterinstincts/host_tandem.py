"""Bounded async observation while one host-owned Sim interaction is pending.

The existing listener owns evaluation, presence and tick persistence. Callback
ports own genuine observation, separately admitted input and outcome observation.
This module owns only the in-flight action lifecycle, never a new goal registry.
No threads, game hooks, autorun or input implementation.
"""
from __future__ import annotations

import asyncio
import math
from collections import deque
from collections.abc import Awaitable, Callable, Mapping

from betterinstincts.host_listener import load_contract, status, tick
from betterinstincts.player_presence import PresenceProbe

Observe = Callable[[], Awaitable[Mapping]]
Execute = Callable[[dict, Mapping], Awaitable[Mapping]]
Probe = Callable[[Mapping], PresenceProbe | None]


class HostTandemError(ValueError):
    pass


def _bounded(value: float, low: float, high: float) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


def _ref(value: object) -> bool:
    return (isinstance(value, str) and bool(value.strip()) and len(value) <= 160
            and all(ord(char) >= 32 for char in value))


async def _stop_observing(task: asyncio.Task | None) -> None:
    # Callback cancellation stops its control/observation continuation. It MUST
    # NOT translate into cancelling a player's Sim interaction.
    if task is not None:
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def run_tandem_session(
    session_id: str,
    actor_ref: str,
    *,
    observe: Observe,
    execute: Execute,
    interrupt_owned: Execute,
    probe: Probe,
    max_turns: int | None = None,
    interval_seconds: float | None = None,
    observation_timeout_seconds: float | None = None,
    action_timeout_seconds: float | None = None,
) -> dict:
    """Monitor needs independently of a pending gardening outcome.

    execute starts one interaction then awaits its actual outcome. observe keeps
    running meanwhile. interrupt_owned must verify the exact action is still
    host-owned in the fresh snapshot and independently admit cancellation/input.
    No input is authorized by this coordinator or its receipt.
    """
    cfg = load_contract()
    bounds, async_cfg = cfg["bounds"], cfg["async_session"]
    max_turns = bounds["max_ticks_per_session"] if max_turns is None else max_turns
    interval_seconds = bounds["min_tick_interval_sec"] if interval_seconds is None else interval_seconds
    observation_timeout_seconds = (async_cfg["observation_timeout_default_seconds"]
                                   if observation_timeout_seconds is None else observation_timeout_seconds)
    action_timeout_seconds = (async_cfg["action_timeout_default_seconds"]
                              if action_timeout_seconds is None else action_timeout_seconds)
    if not _ref(actor_ref) or type(max_turns) is not int or not 1 <= max_turns <= bounds["max_ticks_per_session"]:
        raise HostTandemError("ACTOR_OR_TURN_BOUND_INVALID")
    if not (
        _bounded(interval_seconds, bounds["min_tick_interval_sec"], bounds["max_tick_interval_sec"])
        and _bounded(observation_timeout_seconds, 1, async_cfg["observation_timeout_max_seconds"])
        and _bounded(action_timeout_seconds, 1, async_cfg["action_timeout_max_seconds"])
    ):
        raise HostTandemError("SESSION_TIME_BOUND_INVALID")
    meta = status(session_id)
    if meta["state"] != "ACTIVE":
        raise HostTandemError("EXPLICIT_ACTIVE_SESSION_REQUIRED")
    remaining = int(meta["max_ticks"]) - int(meta["ticks"])
    if remaining <= 0:
        raise HostTandemError("SESSION_TICK_BUDGET_EXHAUSTED")

    events: deque[dict] = deque(maxlen=async_cfg["max_events_in_memory"])
    active: dict | None = None
    task: asyncio.Task | None = None
    seen_capture: str | None = None
    turns = 0
    reason = "TURN_BUDGET_REACHED"
    last_need_completed: dict | None = None
    career_obligation: dict | None = None
    just_finished_needs = False

    def event(kind: str, **fields) -> None:
        events.append({"event": kind, "turn": turns, **fields})

    try:
        for turns in range(1, min(max_turns, remaining) + 1):
            if turns > 1:
                await asyncio.sleep(interval_seconds)
            try:
                raw = await asyncio.wait_for(observe(), observation_timeout_seconds)
            except asyncio.TimeoutError:
                reason = "OBSERVATION_TIMEOUT_REOBSERVE"
                break
            if not isinstance(raw, Mapping) or raw.get("actor_ref") != actor_ref:
                reason = "ACTOR_IDENTITY_CHANGED_OR_UNKNOWN"
                break
            obs = dict(raw)
            if task is not None and task.done():
                try:
                    outcome = task.result()
                except Exception as exc:
                    event("ACTION_FAILED", error=type(exc).__name__)
                    reason = "ACTION_FAILED_REOBSERVE"
                    break
                if not (
                    isinstance(outcome, Mapping)
                    and outcome.get("state") == "OUTCOME_OBSERVED"
                    and outcome.get("action_ref") == active["action_ref"]
                    and outcome.get("actor_ref") == actor_ref
                    and _ref(outcome.get("observation_ref"))
                ):
                    event("ACTION_OUTCOME_UNPROVEN", action_ref=active["action_ref"])
                    reason = "OUTCOME_UNPROVEN_REOBSERVE"
                    break
                event("ACTION_OUTCOME_OBSERVED", action_ref=active["action_ref"],
                      phase=active["phase"], observation_ref=outcome["observation_ref"])
                if active["phase"] == "NEEDS":
                    last_need_completed = dict(active)
                    just_finished_needs = True
                active, task = None, None
            owned = bool(
                active and obs.get("host_activity_ref") == active["action_ref"]
                and obs.get("host_activity_owner") == "HOST"
            )
            # Gardening owned by this session is not a global busy lock on the
            # needs evaluator. Unknown/player activities retain the normal gate.
            if owned:
                obs["already_busy"] = False
            if career_obligation is not None:
                obs["prior_career_state"] = career_obligation
            receipt = tick(session_id, obs, presence_probe=probe(raw))
            if receipt["listener_action"] == "YIELD_TO_PLAYER":
                event("YIELD_TO_PLAYER_NO_QUEUE_CANCELLATION")
                reason = "PLAYER_OR_UNKNOWN_PRESENCE"
                break
            stack = receipt["host_stack"]
            gate = stack["next_gate"]
            garden = stack.get("gardening") or {}
            career = stack.get("career_service") or {}
            if career.get("obligation_held"):
                career_obligation = dict(career)
                event(
                    "CAREER_OBLIGATION_HELD",
                    microsystem_state=career.get("microsystem_state"),
                    career_gate=career.get("gate"),
                    pending_phase=(active or {}).get("phase"),
                )
            elif career.get("microsystem_state") in {"COMPLETE", "IDLE"}:
                career_obligation = None
            capture = obs.get("capture_ref")
            if not _ref(capture) or capture == seen_capture:
                event("WAIT_FOR_FRESH_CAPTURE")
                continue
            seen_capture = capture
            event("NEEDS_AND_GARDENING_OBSERVED", gate=gate)
            # After survival recovery, held career duty outranks gardening resume.
            if (
                just_finished_needs
                and active is None
                and career.get("obligation_held")
                and career.get("microsystem_state") in {"READY", "TRACKING"}
            ):
                event(
                    "CAREER_READY_AFTER_NEEDS",
                    career_gate=career.get("gate"),
                    microsystem_state=career.get("microsystem_state"),
                    primary_route=career.get("primary_route"),
                )
                reason = "CAREER_READY_HANDOFF_REQUIRED"
                break
            just_finished_needs = False
            duty = garden.get("gate") == "GARDEN_RESPONSIBILITY_FIRST"
            if gate not in {"GARDEN_RECOVER_NEEDS", "GARDEN_ACTION_READY"} and not duty:
                continue
            phase = "RESPONSIBILITY" if duty else (
                "NEEDS" if gate == "GARDEN_RECOVER_NEEDS" else "GARDENING"
            )
            if active is not None:
                if active["phase"] != "GARDENING" or phase not in {"NEEDS", "RESPONSIBILITY"}:
                    continue
                if not owned:
                    event("OWNERSHIP_REVALIDATION_REQUIRED")
                    continue
                try:
                    stopped = await asyncio.wait_for(
                        interrupt_owned(dict(active), raw), observation_timeout_seconds
                    )
                except asyncio.TimeoutError:
                    reason = "INTERRUPTION_TIMEOUT_REOBSERVE"
                    break
                if not (
                    isinstance(stopped, Mapping)
                    and stopped.get("state") == "HOST_ACTION_INTERRUPTED"
                    and stopped.get("action_ref") == active["action_ref"]
                    and stopped.get("actor_ref") == actor_ref
                    and stopped.get("capture_ref") == capture
                ):
                    event("INTERRUPTION_UNPROVEN_NO_NEW_ACTION")
                    continue
                event("GARDENING_SUSPENDED_FOR_" + phase, action_ref=active["action_ref"])
                await _stop_observing(task)
                active, task = None, None
            if duty:
                reason = "RESPONSIBILITY_HANDOFF_REQUIRED"
                break
            actions = garden.get("next_actions") or []
            if len(actions) != 1:
                continue
            need = (stack.get("need_services") or {}).get("primary_need") if phase == "NEEDS" else None
            if (
                last_need_completed and phase == "NEEDS"
                and actions[0]["action_id"] == last_need_completed["action_id"]
                and need == last_need_completed["need_id"]
                and obs["needs"][need] <= last_need_completed["baseline_need"]
            ):
                # A finished sleep/meal interaction with no observed recovery
                # is not permission for an endless repeat of the same remedy.
                event("NEED_RECOVERY_REVALIDATION_REQUIRED", need=need)
                continue
            active = {
                **actions[0], "phase": phase, "actor_ref": actor_ref,
                "action_ref": f"{session_id}:{receipt['tick']}", "owner": "HOST",
                "need_id": need, "baseline_need": obs["needs"].get(need),
            }
            task = asyncio.create_task(asyncio.wait_for(
                execute(dict(active), raw), action_timeout_seconds
            ))
            event("ACTION_STARTED", action_id=active["action_id"], phase=phase,
                  action_ref=active["action_ref"])
    finally:
        await _stop_observing(task)

    return {
        "state": reason, "actor_ref": actor_ref, "turns": turns,
        "events": list(events), "pending_action": active,
        "gardening_goal": "PRESERVED_REQUIRES_FRESH_REVALIDATION",
        "career_obligation": career_obligation,
        "dispatch_authorized": False,
        "proof_ceiling": "BOUNDED_CALLBACK_SESSION_NOT_GAMEPLAY_CERTIFICATION",
    }
