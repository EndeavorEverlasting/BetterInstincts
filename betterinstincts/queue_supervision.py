"""Bounded, evidence-first household queue and activity-duration supervision.

Pure game-native POLICY_ONLY port. The caller supplies attested EA observations;
this module never reads the HUD, sends input, cancels, enqueues or persists logs.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from statistics import median

from betterinstincts.need_service_base import SIX, threshold_pair
from betterinstincts.queue_capacity import evaluate_queue_capacity

SCHEMA = "betterinstincts.queue-supervision/v1"
RESULT_SCHEMA = "betterinstincts.queue-supervision-result/v1"
FACTORS = ("moodlet", "temperament", "balance", "trait")
MAX_SIMS = 32
MAX_QUEUE = 16
MAX_SAMPLES = 12
MAX_CAPTURE_AGE = 180
MIN_SWITCH_GAP = 90.0  # ACTIVE_SIM_SECONDS; provisional anti-oscillation guard


class QueueSupervisionError(ValueError):
    pass


def _ref(value: object) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= 120 and all(
        c.isalnum() or c in "_.:-" for c in value
    )


def _number(value: object, low: float, high: float) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise QueueSupervisionError("INVALID_CALIBRATED_NUMBER")
    return float(value)


def _duration_profile(activity: Mapping | None) -> dict:
    """Use independent, same-action completion evidence; no invented EA speeds."""
    result = {
        "state": "NO_ACTIVE_ACTIVITY",
        "predicted_seconds": None,
        "remaining_seconds": None,
        "elapsed_seconds": None,
        "sample_count": 0,
        "learned_ratio": None,
        "verified_factors": [],
        "unknown_factors": list(FACTORS),
        "reliable_for_preemption": False,
        "suspected_stall": False,
    }
    if activity is None:
        return result
    if not isinstance(activity, Mapping):
        raise QueueSupervisionError("ACTIVITY_INVALID")
    if activity.get("clock_basis") != "ACTIVE_SIM_SECONDS":
        result["state"] = "CLOCK_BASIS_UNVERIFIED"
        return result
    base = _number(activity.get("base_seconds"), 1, 86400)
    elapsed = _number(activity.get("elapsed_seconds"), 0, 172800)
    if not _ref(activity.get("base_proof_ref")) or not _ref(activity.get("elapsed_proof_ref")):
        result["state"] = "ACTIVITY_TIMING_UNVERIFIED"
        return result
    result["elapsed_seconds"] = elapsed
    factors = activity.get("factors")
    if not isinstance(factors, Mapping) or set(factors) - set(FACTORS):
        raise QueueSupervisionError("DURATION_FACTORS_INVALID")
    prediction = base
    verified = []
    unknown = []
    for label in FACTORS:
        row = factors.get(label)
        if row is None:
            unknown.append(label)
            continue
        if not isinstance(row, Mapping):
            raise QueueSupervisionError("DURATION_FACTOR_INVALID")
        multiplier = _number(row.get("multiplier"), 0.5, 2.0)
        if not _ref(row.get("proof_ref")):
            unknown.append(label)
            continue  # unproven factors must not influence cancellation
        prediction *= multiplier
        verified.append(label)
    samples = activity.get("completed_samples", [])
    if not isinstance(samples, list) or len(samples) > MAX_SAMPLES:
        raise QueueSupervisionError("DURATION_HISTORY_INVALID")
    ratios = []
    seen = set()
    action_id = activity.get("action_id")
    game_build = activity.get("game_build")
    if not _ref(action_id) or not _ref(game_build):
        raise QueueSupervisionError("DURATION_IDENTITY_INVALID")
    for sample in samples:
        if not isinstance(sample, Mapping):
            raise QueueSupervisionError("DURATION_SAMPLE_INVALID")
        sample_ref = sample.get("sample_ref")
        if (not _ref(sample_ref) or sample_ref in seen
                or not _ref(sample.get("outcome_proof_ref"))
                or sample.get("action_id") != action_id
                or sample.get("game_build") != game_build):
            raise QueueSupervisionError("DURATION_SAMPLE_REPLAY_OR_SCOPE")
        seen.add(sample_ref)
        actual = _number(sample.get("active_seconds"), 1, 86400)
        expected = _number(sample.get("modeled_seconds"), 1, 86400)
        ratios.append(min(2.0, max(0.5, actual / expected)))
    correction = median(ratios) if ratios else 1.0
    predicted = min(86400.0, max(1.0, prediction * correction))
    result.update(
        state="DURATION_ESTIMATED" if not unknown else "DURATION_PARTIALLY_OBSERVED",
        predicted_seconds=round(predicted, 3),
        remaining_seconds=round(max(0.0, predicted - elapsed), 3),
        sample_count=len(ratios),
        learned_ratio=round(correction, 4) if ratios else None,
        verified_factors=verified,
        unknown_factors=unknown,
        reliable_for_preemption=not unknown and len(ratios) >= 2,
    )
    progress = activity.get("progress_state", "UNKNOWN")
    if progress not in {"UNKNOWN", "ADVANCING", "STALLED"}:
        raise QueueSupervisionError("ACTIVITY_PROGRESS_INVALID")
    result["suspected_stall"] = bool(
        result["reliable_for_preemption"]
        and progress == "STALLED" and _ref(activity.get("progress_proof_ref"))
        and elapsed > max(predicted * 1.75, predicted + 30.0)
    )
    return result


def _queue_rows(queue: object, *, capture_ref: str, sim_ref: str) -> list[Mapping]:
    if not isinstance(queue, list):
        raise QueueSupervisionError("QUEUE_NOT_A_LIST")
    if len(queue) > MAX_QUEUE:
        return []  # oversized/untrustworthy queue is held before inspection
    seen = set()
    running = 0
    for row in queue:
        if not isinstance(row, Mapping) or not all(
            _ref(row.get(k)) for k in ("action_id", "queue_slot_ref", "origin_proof_ref")
        ):
            raise QueueSupervisionError("QUEUE_ROW_UNTRUSTWORTHY")
        if (row.get("capture_ref") != capture_ref or row.get("sim_ref") != sim_ref
                or row["queue_slot_ref"] in seen):
            raise QueueSupervisionError("QUEUE_IDENTITY_OR_REPLAY")
        seen.add(row["queue_slot_ref"])
        if row.get("queue_state") not in {"RUNNING", "PENDING"}:
            raise QueueSupervisionError("QUEUE_STATE_UNKNOWN")
        running += row["queue_state"] == "RUNNING"
        if running > 1 or row.get("origin") not in {"PLAYER", "HOST", "SIM_AUTONOMY", "UNKNOWN"}:
            raise QueueSupervisionError("QUEUE_ORIGIN_OR_RUNNING_INVALID")
        if row.get("semantic_key") is not None and not _ref(row["semantic_key"]):
            raise QueueSupervisionError("QUEUE_SEMANTIC_INVALID")
        if row.get("conflict_group") is not None and not _ref(row["conflict_group"]):
            raise QueueSupervisionError("QUEUE_CONFLICT_INVALID")
        if row.get("serves_need") is not None and row["serves_need"] not in SIX:
            raise QueueSupervisionError("QUEUE_SERVES_NEED_INVALID")
    return queue


def _candidate(row: Mapping, reason: str, capture_ref: str, sim_ref: str) -> dict | None:
    if (row.get("queue_state") not in {"RUNNING", "PENDING"}
            or row.get("origin") != "SIM_AUTONOMY"
            or not _ref(row.get("origin_proof_ref"))
            or row.get("protected_goal") is not False
            or not _ref(row.get("goal_proof_ref"))):
        return None
    return {
        "sim_ref": sim_ref,
        "queue_slot_ref": row["queue_slot_ref"],
        "action_id": row["action_id"],
        "reason": reason,
        "capture_ref": capture_ref,
        "origin_proof_ref": row["origin_proof_ref"],
        "goal_proof_ref": row["goal_proof_ref"],
        "requires": [
            "EXACT_GAME_PATCH_AND_NATIVE_SLOT",
            "FRESH_QUEUE_AND_SIM",
            "RECHECK_PLAYER_AND_GOAL_CONTROL",
            "INDEPENDENT_NATIVE_EFFECT_ADMISSION",
            "OBSERVE_EFFECT_BEFORE_REPLAN",
        ],
    }


def _queue_conflict(queue: list[Mapping]) -> tuple[Mapping, str] | None:
    for i, later in enumerate(queue):
        if later.get("queue_state") != "PENDING":
            continue
        for prior in queue[:i]:
            if (
                _ref(later.get("semantic_key"))
                and later.get("semantic_key") == prior.get("semantic_key")
                and _ref(later.get("semantic_proof_ref"))
                and _ref(prior.get("semantic_proof_ref"))
            ):
                return later, "DUPLICATE_SEMANTIC_ACTION"
            if (
                _ref(later.get("conflict_group"))
                and later.get("conflict_group") == prior.get("conflict_group")
                and _ref(later.get("conflict_outcome"))
                and _ref(prior.get("conflict_outcome"))
                and later["conflict_outcome"] != prior["conflict_outcome"]
                and _ref(later.get("conflict_proof_ref"))
                and _ref(prior.get("conflict_proof_ref"))
            ):
                return later, "MUTUALLY_EXCLUSIVE_OUTCOME"
    return None


def _urgent_need(row: Mapping, duration: Mapping) -> tuple[str | None, str | None]:
    needs = row.get("needs")
    if not isinstance(needs, Mapping) or set(needs) != SIX or not _ref(row.get("needs_proof_ref")):
        return None, None
    normalized = {name: _number(value, 0, 1) for name, value in needs.items()}
    urgent, proactive = threshold_pair()
    hard = sorted((v, n) for n, v in normalized.items() if v < urgent)
    if hard:
        return hard[0][1], "OBSERVED_CRITICAL_NEED"
    if not duration["reliable_for_preemption"]:
        return None, None
    decay = row.get("need_decay_per_active_second")
    if not isinstance(decay, Mapping) or set(decay) - SIX or not _ref(row.get("decay_proof_ref")):
        return None, None
    remaining = duration["remaining_seconds"]
    candidates = []
    for need, rate in decay.items():
        rate = _number(rate, 0, 1)
        if rate > 0 and urgent <= normalized[need] < proactive:
            ttc = (normalized[need] - urgent) / rate
            if ttc < 0.75 * remaining:
                candidates.append((ttc, normalized[need], need))
    if candidates:
        best = min(candidates)
        return best[2], "FORECAST_CRITICAL_BEFORE_COMPLETION"
    return None, None


def evaluate_queue_supervision(
    observation: Mapping, *,
    household_ref: str,
    game_build: str,
    capture_ref: str,
    sims: list[Mapping],
    player_active: object,
    observed_at_unix: object,
    now: float,
) -> dict:
    """One bounded policy pass for existing native household Sim/queue identities."""
    if not isinstance(observation, Mapping) or observation.get("schema") != SCHEMA:
        raise QueueSupervisionError("QUEUE_SUPERVISION_SCHEMA_INVALID")
    if (observation.get("household_ref") != household_ref
            or observation.get("game_build") != game_build
            or observation.get("capture_ref") != capture_ref):
        raise QueueSupervisionError("QUEUE_SUPERVISION_CONTEXT_MISMATCH")
    records = observation.get("sims")
    if not isinstance(records, list) or not 1 <= len(records) <= MAX_SIMS:
        raise QueueSupervisionError("QUEUE_SUPERVISION_BOUNDS")
    native_by_id = {sim["sim_ref"]: sim for sim in sims}
    if (
        any(not isinstance(r, Mapping) or not _ref(r.get("sim_ref")) for r in records)
        or len(records) != len(native_by_id)
        or len({r["sim_ref"] for r in records}) != len(records)
        or {r["sim_ref"] for r in records} != set(native_by_id)
    ):
        raise QueueSupervisionError("QUEUE_SUPERVISION_SIM_SCOPE_MISMATCH")
    fresh = (
        type(now) in (float, int) and type(observed_at_unix) in (float, int)
        and math.isfinite(now) and math.isfinite(observed_at_unix)
        and 0 <= now - observed_at_unix <= MAX_CAPTURE_AGE
    )
    decisions = []
    for row in records:
        sim_id = row["sim_ref"]
        native = native_by_id[sim_id]
        queue = native.get("queue", [])
        decision = {
            "sim_ref": sim_id, "gate": "REOBSERVE_QUEUE",
            "queue_budget": None, "duration": None,
            "priority_need": None, "cancel_candidate": None,
            "enqueue_allowed": False, "cancel_allowed": False,
            "desktop_input_allowed": False, "max_new_actions": 0,
        }
        decisions.append(decision)
        if not fresh or row.get("capture_ref") != capture_ref or native.get("capture_ref") != capture_ref:
            continue
        if (player_active is not False or native.get("player_command_present") is not False
                or native.get("player_owned") is not False):
            decision["gate"] = "PLAYER_OR_UNKNOWN_OWNER_PROTECTED"
            continue
        if native.get("queue_verified") is not True or row.get("queue_verified") is not True:
            continue
        if not isinstance(queue, list) or len(queue) > MAX_QUEUE:
            decision["gate"] = "QUEUE_OBSERVATION_TOO_LARGE"
            continue
        verified_queue = _queue_rows(queue, capture_ref=capture_ref, sim_ref=sim_id)
        budget = evaluate_queue_capacity(
            [act["action_id"] for act in verified_queue],
            multitasking=row.get("multitasking"),
            player_directed=False,
            rejected_last_enqueue=row.get("rejected_last_enqueue", False),
        )
        decision["queue_budget"] = budget
        if any(action["origin"] != "SIM_AUTONOMY" for action in verified_queue):
            decision["gate"] = "PLAYER_OR_UNKNOWN_QUEUE_PROTECTED"
            continue
        if row.get("policy_opt_in") is not True or native.get("policy_opt_in") is not True:
            decision["gate"] = "POLICY_OPT_IN_REQUIRED"
            continue
        activity = row.get("active_activity")
        duration = _duration_profile(activity)
        decision["duration"] = duration
        running = [act for act in verified_queue if act["queue_state"] == "RUNNING"]
        if activity is not None and (
            len(running) != 1 or activity.get("queue_slot_ref") != running[0]["queue_slot_ref"]
            or activity.get("action_id") != running[0]["action_id"]
            or activity.get("game_build") != game_build
        ):
            decision["gate"] = "REOBSERVE_ACTIVITY"
            continue
        if activity is not None and activity.get("paused") is not False:
            decision["gate"] = "PAUSED_OR_UNKNOWN_CLOCK"
            continue
        need, reason = _urgent_need(row, duration)
        if need:
            decision["priority_need"] = need
            if running:
                current = running[0]
                if (current.get("serves_need") == need and _ref(current.get("serve_proof_ref"))):
                    decision["gate"] = "CURRENT_ACTIVITY_SERVES_PRIORITY_NEED"
                    continue
                if not _ref(current.get("serve_proof_ref")):
                    decision["gate"] = "CURRENT_ACTIVITY_PURPOSE_UNKNOWN"
                    continue
                if row.get("switch_history_verified") is not True:
                    decision["gate"] = "SWITCH_HISTORY_UNVERIFIED"
                    continue
                last = row.get("last_switch_active_second")
                if last is not None:
                    instant = _number(row.get("active_clock_second"), 0, 1e12)
                    previous = _number(last, 0, 1e12)
                    if instant < previous or instant - previous < MIN_SWITCH_GAP:
                        decision["gate"] = "SWITCH_COOLDOWN"
                        continue
                candidate = _candidate(current, reason, capture_ref, sim_id)
                if candidate:
                    candidate["priority_need"] = need
                    decision.update(gate="REPLAN_HIGHER_PRIORITY_NEED", cancel_candidate=candidate)
                    continue
                decision["gate"] = "CURRENT_ACTION_PROTECTED"
                continue
            decision["gate"] = "NEED_REPLAN_NO_RUNNING_ACTION"
            continue
        conflict = _queue_conflict(verified_queue)
        if conflict:
            target, cause = conflict
            candidate = _candidate(target, cause, capture_ref, sim_id)
            if candidate:
                decision.update(gate="QUEUE_CONFLICT_CANDIDATE", cancel_candidate=candidate)
            else:
                decision["gate"] = "CONFLICT_ACTION_PROTECTED"
        elif duration["suspected_stall"]:
            decision["gate"] = "STALLED_ACTIVITY_REOBSERVE"
        elif budget["enqueue_allowed"]:
            # Headroom is not evidence that adding more work is coherent.
            # Require source-attested semantics on every existing action;
            # even a clean queue may only propose ONE addition per capture.
            if any(
                not _ref(a.get("semantic_key"))
                or not _ref(a.get("semantic_proof_ref"))
                for a in verified_queue
            ):
                decision["gate"] = "QUEUE_SEMANTICS_UNKNOWN"
            else:
                decision["gate"] = "QUEUE_CAPACITY_AVAILABLE_ADVISORY"
                decision["max_new_actions"] = 1
        else:
            decision["gate"] = budget["gate"]
    return {
        "schema": RESULT_SCHEMA, "household_ref": household_ref,
        "game_build": game_build, "capture_ref": capture_ref,
        "decisions": decisions,
        "cancel_allowed": False, "enqueue_allowed": False,
        "desktop_input_allowed": False,
        "proof_ceiling": "OFFLINE_QUEUE_POLICY_NOT_EA_HOOK_OR_IN_GAME_EFFECT",
    }
