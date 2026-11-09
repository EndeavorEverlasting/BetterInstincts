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
    aspiration_prompt: dict | None = None
    balance_condition: dict | None = None
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
            if aspiration_prompt is not None:
                obs["prior_aspiration_state"] = aspiration_prompt
            if balance_condition is not None:
                obs["prior_balance_state"] = balance_condition
            receipt = tick(session_id, obs, presence_probe=probe(raw))
            if receipt["listener_action"] == "YIELD_TO_PLAYER":
                event("YIELD_TO_PLAYER_NO_QUEUE_CANCELLATION")
                reason = "PLAYER_OR_UNKNOWN_PRESENCE"
                break
            mode_context = receipt.get("ui_mode")
            if mode_context is not None and not mode_context["mode_autonomy_allowed"]:
                event(
                    "UI_MODE_REOBSERVATION_REQUIRED_NO_NEW_DISPATCH",
                    mode=mode_context["mode"],
                    panel=mode_context["active_panel"],
                    scene=mode_context["scene_id"],
                )
                reason = "GAME_MODE_NOT_LIVE_REOBSERVE"
                break
            stack = receipt["host_stack"]
            gate = stack["next_gate"]
            garden = stack.get("gardening") or {}
            career = stack.get("career_service") or {}
            aspiration = stack.get("aspiration_service") or {}
            balance = stack.get("balance_service") or {}
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
            if aspiration.get("prompt_held"):
                aspiration_prompt = dict(aspiration)
                event(
                    "ASPIRATION_PROMPT_HELD",
                    microsystem_state=aspiration.get("microsystem_state"),
                    aspiration_gate=aspiration.get("gate"),
                    dialog_choice=aspiration.get("dialog_choice"),
                    pending_phase=(active or {}).get("phase"),
                )
            elif aspiration.get("microsystem_state") in {"COMPLETE", "IDLE"}:
                aspiration_prompt = None
            if balance.get("condition_held"):
                balance_condition = dict(balance)
                event(
                    "BALANCE_CONDITION_HELD",
                    microsystem_state=balance.get("microsystem_state"),
                    balance_gate=balance.get("gate"),
                    balance_level=balance.get("balance_level"),
                    ailment=balance.get("ailment"),
                    pending_phase=(active or {}).get("phase"),
                )
            elif balance.get("microsystem_state") in {"COMPLETE", "IDLE", "RESTORED"}:
                balance_condition = None
            capture = obs.get("capture_ref")
            if not _ref(capture) or capture == seen_capture:
                event("WAIT_FOR_FRESH_CAPTURE")
                continue
            seen_capture = capture
            event("NEEDS_AND_GARDENING_OBSERVED", gate=gate)
            # Aspiration / life-state dialogs outrank gardening while held.
            if aspiration.get("prompt_held") and aspiration.get("dialog_choice") in {
                "CANCEL",
                "OK",
            }:
                event(
                    "ASPIRATION_DIALOG_READY",
                    aspiration_gate=aspiration.get("gate"),
                    dialog_choice=aspiration.get("dialog_choice"),
                    press_ok_allowed=aspiration.get("press_ok_allowed"),
                )
                reason = "ASPIRATION_DIALOG_HANDOFF_REQUIRED"
                break
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
            # After survival recovery, Very Imbalanced / ailment outranks gardening.
            if (
                just_finished_needs
                and active is None
                and balance.get("condition_held")
                and balance.get("gate") in {"READY_HOLISTIC_CURE", "READY_NATUROPATH"}
            ):
                event(
                    "BALANCE_READY_AFTER_NEEDS",
                    balance_gate=balance.get("gate"),
                    microsystem_state=balance.get("microsystem_state"),
                    primary_route=balance.get("primary_route"),
                    ailment=balance.get("ailment"),
                )
                reason = "BALANCE_READY_HANDOFF_REQUIRED"
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
        "aspiration_prompt": aspiration_prompt,
        "balance_condition": balance_condition,
        "dispatch_authorized": False,
        "proof_ceiling": "BOUNDED_CALLBACK_SESSION_NOT_GAMEPLAY_CERTIFICATION",
    }

# Opportunity surveying is the same opt-in asynchronous host lifecycle as the
# gardening/needs coordinator, but it never substitutes its goal ownership.
# A player-active observation remains useful; only screen effects yield.
async def run_opportunity_survey_session(
    session_id: str,
    actor_ref: str,
    *,
    observe: Observe,
    probe: Probe,
    max_turns: int = 16,
    interval_seconds: float = 1.0,
    observation_timeout_seconds: float = 15.0,
    on_receipt: Callable[[dict], Awaitable[None]] | None = None,
    exploration_queue: object | None = None,
    navigate: Callable[[dict, Callable[[], Awaitable[None]]], Awaitable[None]] | None = None,
    observe_fresh: Observe | None = None,
) -> dict:
    """Bounded asynchronous survey, including ticks when the human is playing.

    Existing host_listener.tick owns all census/presence/receipt work. Optional
    navigation uses a caller-owned CooperativeScreenQueue and double-probed
    checkpoint, never a raw cursor loop. No callback ports means no game input.
    """
    from betterinstincts.workflow_interop import CooperativeScreenQueue

    cfg = load_contract()
    bounds = cfg["bounds"]
    if not _ref(actor_ref) or type(max_turns) is not int or not 1 <= max_turns <= bounds["max_ticks_per_session"]:
        raise HostTandemError("SURVEY_ACTOR_OR_TURNS_INVALID")
    if not _bounded(interval_seconds, bounds["min_tick_interval_sec"], bounds["max_tick_interval_sec"]):
        raise HostTandemError("SURVEY_POLL_INTERVAL_INVALID")
    if not _bounded(observation_timeout_seconds, 1, cfg["async_session"]["observation_timeout_max_seconds"]):
        raise HostTandemError("SURVEY_OBSERVATION_TIMEOUT_INVALID")
    if (exploration_queue is None) != (navigate is None) or (
        exploration_queue is not None and (
            not isinstance(exploration_queue, CooperativeScreenQueue)
            or not callable(observe_fresh)
        )
    ):
        raise HostTandemError("SURVEY_EXPLORATION_PORTS_MUST_BE_COMPLETE")
    meta = status(session_id)
    if meta["state"] != "ACTIVE":
        raise HostTandemError("EXPLICIT_ACTIVE_SESSION_REQUIRED")
    remaining = int(meta["max_ticks"]) - int(meta["ticks"])
    if remaining <= 0:
        raise HostTandemError("SURVEY_SESSION_EXHAUSTED")
    events: deque[dict] = deque(maxlen=cfg["async_session"]["max_events_in_memory"])
    seen_capture = set()
    turns = 0
    receipts = 0
    for turn in range(1, min(max_turns, remaining) + 1):
        turns = turn
        if turn > 1:
            await asyncio.sleep(interval_seconds)
        try:
            raw = await asyncio.wait_for(observe(), observation_timeout_seconds)
        except asyncio.TimeoutError:
            events.append({"event": "OBSERVATION_TIMEOUT", "turn": turn})
            break
        if not isinstance(raw, Mapping) or raw.get("actor_ref") != actor_ref:
            events.append({"event": "ACTOR_CHANGED_OR_UNKNOWN", "turn": turn})
            break
        snapshot = dict(raw)
        capture = snapshot.get("capture_ref")
        if not _ref(capture) or capture in seen_capture:
            events.append({"event": "REOBSERVE_CAPTURE_REQUIRED", "turn": turn})
            continue
        seen_capture.add(capture)
        result = tick(session_id, snapshot, presence_probe=probe(raw))
        receipts += 1
        survey = result["opportunity_survey"]
        events.append({
            "event": "PASSIVE_SURVEY_RECORDED", "turn": turn,
            "capture_ref": capture, "room_count": survey["room_count"],
            "opportunities": len(survey["candidates"]),
            "player_yield": result["listener_action"] == "YIELD_TO_PLAYER",
            "exploration_gate": survey["exploration_gate"],
        })
        if on_receipt is not None:
            await on_receipt(result)
        # Input is possible only when the operator deliberately supplies a
        # validated adapter *and* a screen-owned queue. Never auto-create one.
        if exploration_queue is not None:
            if survey["exploration_gate"] == "IDLE_EXPLORATION_CANDIDATE":
                enqueued = queue_idle_exploration(
                    survey, actor_ref=actor_ref,
                    screen_queue=exploration_queue,
                    observe_fresh=observe_fresh,
                    navigate=navigate,
                )
                events.append({"event": enqueued["state"], "turn": turn,
                               "work_id": enqueued.get("work_id")})
            if exploration_queue.pending:
                outcome = await exploration_queue.run_once()
                events.append({"event": "IDLE_EXPLORATION_" + str(outcome["state"]),
                               "turn": turn})
    return {
        "state": "BOUNDED_SURVEY_COMPLETED",
        "actor_ref": actor_ref, "turns": turns,
        "survey_receipts": receipts, "events": list(events),
        "pending_exploration": (
            len(exploration_queue.pending) if exploration_queue is not None else 0
        ),
        "control_permit": None, "execute_allowed": False,
        "proof_ceiling": "ASYNC_SURVEY_CALLBACK_TEST_NOT_LIVE_GAME_CERTIFICATION",
    }


def queue_idle_exploration(
    survey: Mapping,
    *,
    actor_ref: str,
    screen_queue: object,
    observe_fresh: Observe,
    navigate: Callable[[dict, Callable[[], Awaitable[None]]], Awaitable[None]],
) -> dict:
    """Stage one targeted hover/traverse via the existing cooperative screen gate.

    A fresh capture, unchanged patch/lot/revision/actor and scene-backed Live
    mode are required immediately before a real adapter is called.
    """
    import hashlib
    from betterinstincts.workflow_interop import CooperativeScreenQueue, QueuedStep
    from betterinstincts.ui_mode import evaluate_mode, UIModeError
    from betterinstincts.room_census import scan_lot_model, RoomCensusError

    if not isinstance(screen_queue, CooperativeScreenQueue) or not callable(observe_fresh) or not callable(navigate):
        raise HostTandemError("IDLE_EXPLORATION_ADAPTER_INVALID")
    if survey.get("exploration_gate") != "IDLE_EXPLORATION_CANDIDATE":
        return {"state": "IDLE_EXPLORATION_DEFERRED", "execute_allowed": False}
    targets = survey.get("exploration_targets") or []
    if not targets:
        return {"state": "NOTHING_TO_EXPLORE", "execute_allowed": False}
    target = dict(targets[0])
    patch, lot, revision = survey.get("game_version"), survey.get("lot_id"), survey.get("lot_revision")
    if not patch or not lot or type(revision) is not int or not _ref(actor_ref):
        return {"state": "EXPLORATION_PROVENANCE_MISSING", "execute_allowed": False}
    identity = "|".join((patch, lot, str(revision), actor_ref, target["target_ref"]))
    work_id = "survey-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
    if work_id in screen_queue.completed or work_id in screen_queue.needs_review or any(
        item.work_id == work_id for item in screen_queue.pending
    ):
        return {"state": "EXPLORATION_ALREADY_KNOWN_OR_PENDING",
                "work_id": work_id, "execute_allowed": False}

    async def validate() -> bool:
        try:
            snapshot = await observe_fresh()
            if not isinstance(snapshot, Mapping) or any((
                snapshot.get("actor_ref") != actor_ref,
                snapshot.get("active_lot_id") != lot,
                snapshot.get("game_version") != patch,
                snapshot.get("capture_ref") == survey.get("capture_ref"),
                snapshot.get("camera_follow_attested") is not True,
                snapshot.get("operator_declared_playing") is True,
                snapshot.get("player_directed") is True,
                snapshot.get("event_active") is True,
            )):
                return False
            mode = evaluate_mode(
                game_version=patch,
                mode_observations=snapshot.get("mode_observations", []),
                panel_observations=snapshot.get("panel_observations"),
                shortcut_hint=snapshot.get("shortcut_hint"),
            )
            if mode["mode"] != "LIVE" or not mode["mode_autonomy_allowed"]:
                return False
            census = scan_lot_model(snapshot["lot_model"])
            if census["lot_id"] != lot or census["model_revision"] != revision:
                return False
            room = census["rooms"].get(target["room_id"])
            return bool(
                room and room["room_evidence"] == "STRUCTURE_ATTESTED"
                and any("object:" + item["id"] == target["target_ref"]
                        for item in room["items"])
            )
        except (KeyError, TypeError, ValueError, RoomCensusError, UIModeError):
            return False

    async def action(checkpoint: Callable[[], Awaitable[None]]) -> None:
        await checkpoint()
        await navigate(target, checkpoint)

    screen_queue.enqueue(QueuedStep(work_id=work_id, validate=validate, action=action))
    return {"state": "IDLE_EXPLORATION_QUEUED", "work_id": work_id,
            "target_ref": target["target_ref"], "execute_allowed": False}
