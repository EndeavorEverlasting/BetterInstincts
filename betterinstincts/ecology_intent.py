"""PS-0241: capture-bound, per-Sim ecology intent reducer.

Policy only: an installed, version-proven EA-native adapter must supply observations,
validate the exact event/queue API and perform any game effect. No desktop input,
timer thread, save write, or claim of an active Sims mod lives in this module.
"""
from __future__ import annotations

import copy
import math
from collections.abc import Mapping

from betterinstincts.ecology_forecast import compare_duration_models
from betterinstincts.need_service_base import SIX, threshold_pair

SCHEMA = "betterinstincts.ecology-intent/v1"
OBSERVATION = "betterinstincts.ecology-observation/v1"
NEEDS = SIX
STEPS = ("PICKUP", "FERTILIZE")
MAX_AGE_SECONDS = 60
MAX_QUEUE = 16
MAX_SIMS = 32
WORK_RESERVE_MINUTES = 30.0
TIME_SAFETY_MULTIPLIER = 1.25


class EcologyIntentError(ValueError):
    pass


def _ref(value: object) -> bool:
    return (
        isinstance(value, str) and 1 <= len(value) <= 120
        and all(c.isalnum() or c in "_:.-" for c in value)
    )


def _num(value: object, low: float = 0, high: float = 1_000_000) -> bool:
    return type(value) in (float, int) and math.isfinite(value) and low <= value <= high


def new_ecology_intent(
    *, game_build: str, household_ref: str, sim_ref: str,
    lot_ref: str, plant_ref: str, item_ref: str, goal_ref: str,
) -> dict:
    """A serializable intent for one exact Sim; never a UI portrait index."""
    identities = locals()
    if not all(_ref(value) for value in identities.values()):
        raise EcologyIntentError("ECOLOGY_IDENTITY_INVALID")
    return {
        "schema": SCHEMA,
        **identities,
        "step": "PICKUP",
        "revision": 0,
        "last_capture_ref": None,
        "last_sequence": -1,
        "last_inventory_count": None,
        "awaiting": None,
        "awaiting_capture_ref": None,
        "awaiting_item_count": None,
        "dispatch_status": "NONE",
        "awaiting_queue_ref": None,
        "verified_steps": [],
        "plan": [
            {"step": "PICKUP", "target_ref": item_ref},
            {"step": "FERTILIZE", "target_ref": plant_ref},
        ],
    }


def _validate_intent(intent: Mapping) -> None:
    if not isinstance(intent, Mapping) or intent.get("schema") != SCHEMA:
        raise EcologyIntentError("ECOLOGY_INTENT_SCHEMA")
    if not all(_ref(intent.get(key)) for key in (
        "game_build", "household_ref", "sim_ref", "lot_ref",
        "plant_ref", "item_ref", "goal_ref",
    )):
        raise EcologyIntentError("ECOLOGY_INTENT_IDENTITY")
    if (intent.get("step") not in (*STEPS, "DONE")
            or type(intent.get("revision")) is not int
            or intent["revision"] < 0
            or type(intent.get("last_sequence")) is not int
            or intent["last_sequence"] < -1
            or (intent.get("last_capture_ref") is not None
                and not _ref(intent["last_capture_ref"]))
            or (intent.get("last_inventory_count") is not None
                and (type(intent["last_inventory_count"]) is not int
                     or intent["last_inventory_count"] < 0))
            or intent.get("awaiting") not in (None, "PICKUP", "FERTILIZE")
            or intent.get("dispatch_status") not in ("NONE", "PROPOSED", "QUEUED")
            or (intent.get("awaiting_queue_ref") is not None
                and not _ref(intent["awaiting_queue_ref"]))
            or (intent["awaiting"] is None
                and (intent["dispatch_status"] != "NONE" or intent["awaiting_queue_ref"] is not None))
            or (intent["awaiting"] is not None and
                (intent["dispatch_status"] == "NONE"
                 or (intent["dispatch_status"] == "PROPOSED" and intent["awaiting_queue_ref"] is not None)
                 or (intent["dispatch_status"] == "QUEUED" and not _ref(intent["awaiting_queue_ref"]))))
            or (intent["awaiting"] is None and
                (intent.get("awaiting_capture_ref") is not None
                 or intent.get("awaiting_item_count") is not None))
            or (intent["awaiting"] is not None and
                (not _ref(intent.get("awaiting_capture_ref"))
                 or type(intent.get("awaiting_item_count")) is not int
                 or intent["awaiting_item_count"] < 0))
            or not isinstance(intent.get("verified_steps"), list)
            or any(step not in STEPS for step in intent["verified_steps"])
            or len(intent["verified_steps"]) > 2
            or intent.get("plan") != [
                {"step": "PICKUP", "target_ref": intent["item_ref"]},
                {"step": "FERTILIZE", "target_ref": intent["plant_ref"]},
            ]):
        raise EcologyIntentError("ECOLOGY_INTENT_STATE")


def _time_window(observation: Mapping) -> tuple[float | None, str]:
    if not _ref(observation.get("needs_proof_ref")):
        return None, "NEEDS_PROOF_MISSING"
    needs = observation.get("needs")
    if not isinstance(needs, Mapping) or set(needs) != NEEDS:
        return None, "NEEDS_UNVERIFIED"
    # Reuse the shared proactive needs threshold, not a private ecology constant.
    _, need_floor = threshold_pair()
    until_floor = 1_000_000.0
    for name in NEEDS:
        row = needs[name]
        if not isinstance(row, Mapping):
            return None, "NEEDS_UNVERIFIED"
        value, decay = row.get("value"), row.get("decay_per_sim_minute")
        if not _num(value, 0, 1) or not _num(decay, 0, 1):
            return None, "NEEDS_UNVERIFIED"
        if value <= need_floor:
            return 0.0, "CRITICAL_NEED"
        if decay > 0:
            until_floor = min(until_floor, (value - need_floor) / decay)

    if not _ref(observation.get("work_proof_ref")):
        return None, "WORK_DEADLINE_UNVERIFIED"
    work = observation.get("minutes_until_work")
    if work is None and observation.get("no_upcoming_work") is True:
        work_window = 1_000_000.0
    elif _num(work):
        work_window = max(0.0, float(work) - WORK_RESERVE_MINUTES)
    else:
        return None, "WORK_DEADLINE_UNVERIFIED"
    return min(until_floor, work_window), "WINDOW_VERIFIED"


def _queue_gate(observation: Mapping, action: str, target: str) -> str | None:
    queue = observation.get("queue")
    if observation.get("queue_verified") is not True or not isinstance(queue, list):
        return "QUEUE_UNVERIFIED"
    if len(queue) > MAX_QUEUE:
        return "QUEUE_OVERSIZED_REOBSERVE"
    for row in queue:
        if (not isinstance(row, Mapping)
                or row.get("capture_ref") != observation.get("capture_ref")
                or row.get("sim_ref") != observation.get("sim_ref")
                or not _ref(row.get("action_id"))
                or not _ref(row.get("target_ref"))
                or row.get("origin") not in {"PLAYER", "HOST", "SIM_AUTONOMY", "UNKNOWN"}
                or row.get("state") not in {"RUNNING", "PENDING"}):
            return "QUEUE_UNVERIFIED"
        if row["origin"] != "UNKNOWN" and not _ref(row.get("origin_proof_ref")):
            return "QUEUE_ORIGIN_UNVERIFIED"
        if row["origin"] == "PLAYER":
            return "PLAYER_QUEUE_FIRST"
        if row["origin"] == "UNKNOWN":
            return "QUEUE_ORIGIN_UNVERIFIED"
        if row["action_id"] == action and row["target_ref"] == target:
            return "TASK_ALREADY_QUEUED"
    if any(row["origin"] == "SIM_AUTONOMY" for row in queue):
        return "AUTONOMY_INTERRUPTED_RECONCILE"
    if queue:
        return "OTHER_VERIFIED_WORK"
    return None


def _outcome_verified(
    outcome: object, *, step: str, intent: Mapping, observation: Mapping,
) -> bool:
    if not isinstance(outcome, Mapping) or outcome.get("step") != step:
        return False
    if (outcome.get("status") != "SUCCEEDED"
            or outcome.get("sim_ref") != intent["sim_ref"]
            or outcome.get("target_ref") != (
                intent["item_ref"] if step == "PICKUP" else intent["plant_ref"])
            or outcome.get("before_capture_ref") != intent["awaiting_capture_ref"]
            or outcome.get("after_capture_ref") != observation["capture_ref"]
            or not _ref(outcome.get("proof_ref"))
            or not _ref(outcome.get("native_action_ref"))
            or outcome.get("native_queue_ref") != intent["awaiting_queue_ref"]):
        return False
    before, after = outcome.get("before_item_count"), outcome.get("after_item_count")
    if (type(before) is not int or type(after) is not int or before < 0
            or after < 0 or before != intent["awaiting_item_count"]
            or after != observation["inventory_count"]):
        return False
    if step == "PICKUP":
        return after > before
    return (before > after and outcome.get("before_plant_state") == "DEPLETED"
            and outcome.get("after_plant_state") == "GOOD"
            and observation.get("plant_state") == "GOOD")


def reconcile_ecology_intent(intent: Mapping, observation: Mapping, *, now: float) -> dict:
    """Consume one newer observation, retain goal and return at most one proposal.

    No dispatch permission is emitted. The native adapter must independently
    admit the exact game effect and log its actual queue/outcome, not blindly
    interpret a proposed action as completion.
    """
    _validate_intent(intent)
    if not isinstance(observation, Mapping) or observation.get("schema") != OBSERVATION:
        raise EcologyIntentError("ECOLOGY_OBSERVATION_SCHEMA")
    if not _num(now, 0, 10_000_000_000):
        raise EcologyIntentError("ECOLOGY_CLOCK_INVALID")
    state = copy.deepcopy(dict(intent))
    result = {
        "schema": "betterinstincts.ecology-decision/v1",
        "intent": state, "gate": "REOBSERVE",
        "proposal": None, "mode": "UNKNOWN", "execute_allowed": False,
        "cancel_allowed": False,
        "proof_ceiling": "OFFLINE_INTENT_ONLY_NOT_INSTALLED_EA_RUNTIME",
    }

    def finish(gate: str, *, proposal: dict | None = None, mode: str = "UNKNOWN") -> dict:
        remaining = [] if state["step"] == "DONE" else state["plan"][
            0 if state["step"] == "PICKUP" else 1:
        ]
        result.update(gate=gate, proposal=proposal, mode=mode, remaining_steps=remaining)
        return result

    if any(observation.get(key) != intent[key] for key in (
        "game_build", "household_ref", "sim_ref", "lot_ref", "plant_ref", "item_ref"
    )):
        return finish("ECOLOGY_SCOPE_MISMATCH")
    seq = observation.get("sequence")
    capture = observation.get("capture_ref")
    stamp = observation.get("observed_at_unix")
    if (type(seq) is not int or seq <= intent["last_sequence"]
            or not _ref(capture) or capture == intent["last_capture_ref"]
            or not _num(stamp, 0, 10_000_000_000)
            or not 0 <= now - stamp <= MAX_AGE_SECONDS):
        return finish("ECOLOGY_STALE_OR_REPLAY")
    if (observation.get("scene") != "LIVE"
            or observation.get("mode_verified") is not True
            or type(observation.get("paused")) is not bool
            or observation.get("inventory_verified") is not True
            or not _ref(observation.get("inventory_proof_ref"))
            or type(observation.get("inventory_count")) is not int
            or not 0 <= observation["inventory_count"] <= 1_000_000):
        return finish("ECOLOGY_REOBSERVE_LIVE_STATE")

    paused = observation["paused"]
    mode = "PLANNING" if paused else "PLAY"
    previous_capture = state["last_capture_ref"]
    if (state["awaiting"] is not None and state["dispatch_status"] == "QUEUED"
            and previous_capture is not None):
        if _outcome_verified(
            observation.get("outcome"), step=state["awaiting"],
            intent=state, observation=observation,
        ):
            completed = state["awaiting"]
            state["verified_steps"].append(completed)
            state["step"] = "FERTILIZE" if completed == "PICKUP" else "DONE"
            state["awaiting"] = None
            state["awaiting_capture_ref"] = None
            state["awaiting_item_count"] = None
            state["dispatch_status"] = "NONE"
            state["awaiting_queue_ref"] = None

    # An independently witnessed native cancellation can release a pending
    # proposal. An absent/unknown queue entry alone never licenses replay.
    interruption = observation.get("interruption")
    if (state["awaiting"] is not None and state["dispatch_status"] == "QUEUED"
            and isinstance(interruption, Mapping)):
        if (interruption.get("step") == state["awaiting"]
                and interruption.get("status") == "NATIVE_INTERRUPTED"
                and interruption.get("cause") == "SIM_AUTONOMY"
                and interruption.get("before_capture_ref") == state["awaiting_capture_ref"]
                and interruption.get("after_capture_ref") == capture
                and _ref(interruption.get("proof_ref"))
                and interruption.get("native_queue_ref") == state["awaiting_queue_ref"]):
            state["awaiting"] = None
            state["awaiting_capture_ref"] = None
            state["awaiting_item_count"] = None
            state["dispatch_status"] = "NONE"
            state["awaiting_queue_ref"] = None

    # If we already own inventory at goal admission, pickup is unnecessary.
    if previous_capture is None and state["step"] == "PICKUP" and observation["inventory_count"] > 0:
        state["step"] = "FERTILIZE"
    state.update(
        last_sequence=seq, last_capture_ref=capture,
        last_inventory_count=observation["inventory_count"],
        revision=state["revision"] + 1,
    )
    if state["step"] == "DONE":
        return finish("ECOLOGY_VERIFIED_COMPLETE", mode=mode)

    # Persist intent during user control and non-live autonomy without modifying queue.
    if observation.get("player_active") is not False:
        return finish("ECOLOGY_PLAYER_FIRST", mode=mode)
    if state["awaiting"] is not None:
        next_action = state["awaiting"]
        next_target = state["item_ref"] if next_action == "PICKUP" else state["plant_ref"]
        queue_gate = _queue_gate(observation, next_action, next_target)
        if queue_gate in {"PLAYER_QUEUE_FIRST", "QUEUE_ORIGIN_UNVERIFIED"}:
            return finish(queue_gate, mode=mode)
        if state["dispatch_status"] == "PROPOSED":
            return finish("ECOLOGY_AWAIT_NATIVE_DISPATCH_ACK", mode=mode)
        if queue_gate == "TASK_ALREADY_QUEUED":
            return finish("ECOLOGY_WAIT_FOR_QUEUED_STEP", mode=mode)
        return finish("ECOLOGY_AWAIT_INDEPENDENT_OUTCOME", mode=mode)

    action = state["step"]
    target = state["item_ref"] if action == "PICKUP" else state["plant_ref"]
    queue_gate = _queue_gate(observation, action, target)
    if queue_gate:
        return finish(queue_gate, mode=mode)
    if action == "PICKUP":
        if observation["inventory_count"] > 0:
            return finish("ECOLOGY_RECONCILE_INVENTORY_GAIN", mode=mode)
        if (observation.get("ground_stock_verified") is not True
                or not _ref(observation.get("ground_stock_proof_ref"))
                or type(observation.get("ground_stock_count")) is not int
                or observation["ground_stock_count"] < 1):
            return finish("ECOLOGY_SUPPLY_UNVERIFIED", mode=mode)
    elif observation["inventory_count"] < 1:
        return finish("ECOLOGY_PERSONAL_STOCK_REQUIRED", mode=mode)
    elif (observation.get("plant_verified") is not True
          or not _ref(observation.get("plant_proof_ref"))
          or observation.get("plant_state") != "DEPLETED"):
        return finish("ECOLOGY_PLANT_ELIGIBILITY_UNVERIFIED", mode=mode)

    available, window_gate = _time_window(observation)
    if available is None:
        return finish(window_gate, mode=mode)
    if available == 0:
        return finish("ECOLOGY_NEED_OR_WORK_FIRST", mode=mode)
    upper_pickup = observation.get("pickup_upper_sim_minutes")
    upper_fertilize = observation.get("fertilize_upper_sim_minutes")
    if (not _num(upper_pickup, 0.01, 500)
            or not _num(upper_fertilize, 0.01, 500)
            or not _ref(observation.get("timing_proof_ref"))):
        return finish("ECOLOGY_TIMING_UNVERIFIED", mode=mode)
    upper = {"PICKUP": float(upper_pickup), "FERTILIZE": float(upper_fertilize)}
    training = observation.get("duration_training")
    if training is not None:
        if not isinstance(training, Mapping):
            return finish("ECOLOGY_TIMING_SOURCE_UNVERIFIED", mode=mode)
        if not _num(observation.get("duration_context"), 0, 1):
            return finish("ECOLOGY_TIMING_SOURCE_UNVERIFIED", mode=mode)
        result["forecast_models"] = {}
        for step in STEPS:
            rows = training.get(step, [])
            model = compare_duration_models(
                rows, game_build=state["game_build"], action_id=step,
                context=observation["duration_context"],
                baseline_upper_sim_minutes=upper[step],
            )
            result["forecast_models"][step] = model
            upper[step] = model["selected_upper_sim_minutes"]
    remaining = upper["FERTILIZE"] + (upper["PICKUP"] if action == "PICKUP" else 0)
    required = remaining * TIME_SAFETY_MULTIPLIER
    if available <= required:
        return finish("ECOLOGY_DEFER_FOR_NEEDS_OR_WORK", mode=mode)

    proposal = {
        "step": action, "action_id": action, "sim_ref": state["sim_ref"],
        "target_ref": target, "capture_ref": capture,
        "available_sim_minutes": round(available, 4),
        "required_upper_sim_minutes": round(required, 4),
        "requires": [
            "NATIVE_EXACT_PATCH_HOOK",
            "NATIVE_PLAYER_AND_QUEUE_REVALIDATION",
            "OBSERVE_INDEPENDENT_OUTCOME_BEFORE_NEXT_STEP",
        ],
    }
    if paused:
        return finish("ECOLOGY_PLANNED_WHILE_PAUSED", proposal=proposal, mode=mode)
    # A suggestion offered in Play is only a pending intent. Native dispatch
    # must run under separately version-pinned and game-certified authority.
    state["awaiting"] = action
    state["awaiting_capture_ref"] = capture
    state["awaiting_item_count"] = observation["inventory_count"]
    state["dispatch_status"] = "PROPOSED"
    return finish("ECOLOGY_PLAY_STEP_PROPOSED", proposal=proposal, mode=mode)



def acknowledge_native_ecology_dispatch(intent: Mapping, receipt: Mapping) -> dict:
    """Reconcile a game-native *queue attestation*, not a plan's intention.

    A Play proposal sets PROPOSED but does not imply that EA queued anything.
    The verified, exact-Sim native adapter must independently attest QUEUED
    before any later outcome can advance the plan. A proven NOT_ENQUEUED
    admission may release intent for a new capture; unknown/ambiguous
    acknowledgements leave intent unchanged. This function performs no effects.
    """
    _validate_intent(intent)
    state = copy.deepcopy(dict(intent))
    result = {
        "schema": "betterinstincts.ecology-dispatch-ack/v1",
        "intent": state, "gate": "ECOLOGY_ACK_REOBSERVE",
        "execute_allowed": False, "cancel_allowed": False,
        "proof_ceiling": "OFFLINE_QUEUE_ATTESTATION_POLICY_NOT_EA_EFFECT",
    }

    if state["awaiting"] is None or state["dispatch_status"] != "PROPOSED":
        return {**result, "gate": "ECOLOGY_ACK_NO_PENDING_PROPOSAL"}
    if not isinstance(receipt, Mapping):
        return result
    if any(receipt.get(key) != state[key] for key in (
        "game_build", "household_ref", "sim_ref", "lot_ref",
    )):
        return {**result, "gate": "ECOLOGY_ACK_SCOPE_MISMATCH"}
    target = state["item_ref"] if state["awaiting"] == "PICKUP" else state["plant_ref"]
    if (receipt.get("step") != state["awaiting"]
            or receipt.get("target_ref") != target
            or receipt.get("proposal_capture_ref") != state["awaiting_capture_ref"]
            or not _ref(receipt.get("queue_capture_ref"))
            or receipt["queue_capture_ref"] == state["awaiting_capture_ref"]
            or receipt.get("queue_verified") is not True
            or not _ref(receipt.get("queue_proof_ref"))
            or not _ref(receipt.get("native_observation_ref"))
            or receipt.get("player_active") is not False):
        return result

    status = receipt.get("status")
    if status == "QUEUED":
        if (receipt.get("queue_origin") != "HOST"
                or not _ref(receipt.get("origin_proof_ref"))
                or not _ref(receipt.get("native_queue_ref"))):
            return result
        state["dispatch_status"] = "QUEUED"
        state["awaiting_queue_ref"] = receipt["native_queue_ref"]
        return {**result, "gate": "ECOLOGY_NATIVE_QUEUE_ATTESTED"}
    if status == "NOT_ENQUEUED":
        if (receipt.get("effect_absent_verified") is not True
                or not _ref(receipt.get("absence_proof_ref"))):
            return result
        state["awaiting"] = None
        state["awaiting_capture_ref"] = None
        state["awaiting_item_count"] = None
        state["dispatch_status"] = "NONE"
        state["awaiting_queue_ref"] = None
        return {**result, "gate": "ECOLOGY_NATIVE_NONENQUEUE_CONFIRMED"}
    return result


def reconcile_household_ecology(
    intents: Mapping[str, Mapping], observations: Mapping[str, Mapping], *, now: float,
) -> dict:
    """Per-identity bounded batch; never rotate portraits or infer a selected Sim."""
    if (not isinstance(intents, Mapping) or not isinstance(observations, Mapping)
            or len(intents) > MAX_SIMS or set(intents) != set(observations)):
        raise EcologyIntentError("ECOLOGY_HOUSEHOLD_SCOPE")
    outputs = {}
    for sim_ref, intent in intents.items():
        if (not _ref(sim_ref) or not isinstance(intent, Mapping)
                or intent.get("sim_ref") != sim_ref
                or not isinstance(observations[sim_ref], Mapping)
                or observations[sim_ref].get("sim_ref") != sim_ref):
            raise EcologyIntentError("ECOLOGY_HOUSEHOLD_IDENTITY")
        outputs[sim_ref] = reconcile_ecology_intent(intent, observations[sim_ref], now=now)
    return outputs
