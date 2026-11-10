"""Observe candidate whims and harmful autonomous queue actions separately.

Decision only. A cancellation proposal is not a cancellation permit or a
request to alter global Sims autonomy settings. No implicit behavior hooks.
"""
from __future__ import annotations

import math
import time
from collections.abc import Mapping

SCHEMA = "betterinstincts.autonomy-moderation/v1"
EFFECTS = {"RELATIONSHIP_HARM", "ENVIRONMENT_HARM", "BENEFICIAL", "NEUTRAL", "UNKNOWN"}
ORIGINS = {"PLAYER", "HOST", "SIM_AUTONOMY", "UNKNOWN"}
SETTINGS = {"FULL", "OFF", "UNKNOWN"}
MAX_QUEUE, MAX_WHIMS, MAX_AGE = 24, 12, 180
MAX_OUTCOMES, MAX_REPAIRS = 12, 24


class AutonomyModerationError(ValueError):
    pass


def _ref(value: object) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= 120 and all(
        c.isalnum() or c in "_.:-" for c in value
    )


def evaluate_autonomy_moderation(
    observation: Mapping, *, capture_ref: str, now: float | None = None,
) -> dict:
    """Evaluate one currently selected Sim's action queue, never dispatch."""
    if not isinstance(observation, Mapping) or observation.get("schema") != SCHEMA:
        raise AutonomyModerationError("AUTONOMY_SCHEMA_INVALID")
    if not all(_ref(observation.get(k)) for k in ("sim_ref", "goal_ref")):
        raise AutonomyModerationError("AUTONOMY_IDENTITY_INVALID")
    setting = observation.get("autonomy_setting", "UNKNOWN")
    if setting not in SETTINGS:
        raise AutonomyModerationError("AUTONOMY_SETTING_INVALID")
    if observation.get("disable_selected_sim_autonomy") not in (True, False, None):
        raise AutonomyModerationError("AUTONOMY_SELECTED_SETTING_INVALID")
    queue = observation.get("queue", [])
    whims = observation.get("whims", [])
    if not isinstance(queue, list) or len(queue) > MAX_QUEUE:
        raise AutonomyModerationError("AUTONOMY_QUEUE_INVALID")
    if not isinstance(whims, list) or len(whims) > MAX_WHIMS:
        raise AutonomyModerationError("AUTONOMY_WHIMS_INVALID")
    outcomes = observation.get("observed_harm_outcomes", [])
    repairs = observation.get("observed_repair_actions", [])
    if not isinstance(outcomes, list) or len(outcomes) > MAX_OUTCOMES:
        raise AutonomyModerationError("AUTONOMY_HARM_OUTCOMES_INVALID")
    if not isinstance(repairs, list) or len(repairs) > MAX_REPAIRS:
        raise AutonomyModerationError("AUTONOMY_REPAIRS_INVALID")
    result = {
        "schema": "betterinstincts.autonomy-moderation-result/v1",
        "sim_ref": observation["sim_ref"], "capture_ref": capture_ref,
        "observed_autonomy_setting": setting,
        "state": "INSPECT_AUTONOMY_EVIDENCE", "cancel_candidate": None,
        "repair_candidate": None, "positive_whim_candidate": None,
        "execute_allowed": False,
        "cancel_allowed": False, "settings_change_allowed": False,
        "proof_ceiling": "HOST_AUTONOMY_POLICY_ONLY_NOT_GAME_CANCELLATION",
    }
    def finish(state: str) -> dict:
        result["state"] = state
        return result

    timestamp = observation.get("observed_at_unix")
    instant = time.time() if now is None else now
    if (type(timestamp) not in (int, float) or not math.isfinite(timestamp)
            or type(instant) not in (int, float) or not math.isfinite(instant)
            or not 0 <= instant - timestamp <= MAX_AGE
            or observation.get("capture_ref") != capture_ref
            or observation.get("queue_verified") is not True):
        return finish("REOBSERVE_QUEUE")
    if (observation.get("selection_verified") is not True
            or not _ref(observation.get("selection_proof_ref"))
            or observation.get("selected_sim_ref") != observation["sim_ref"]):
        return finish("SIM_NOT_VERIFIED_SELECTED")
    if observation.get("player_active") is True:
        return finish("PLAYER_FIRST")
    if (observation.get("urgent_need") is True
            or observation.get("imminent_obligation") is True):
        return finish("SURVIVAL_OR_OBLIGATION_FIRST")

    positive = None
    for row in whims:
        if not isinstance(row, Mapping) or not _ref(row.get("whim_ref")):
            raise AutonomyModerationError("WHIM_ROW_INVALID")
        if row.get("capture_ref") != capture_ref or row.get("sim_ref") != observation["sim_ref"]:
            return finish("REOBSERVE_WHIMS")
        # Whims are *opportunities*, never intrinsically positive/negative.
        if (positive is None and row.get("benefit") == "BENEFICIAL"
                and _ref(row.get("benefit_proof_ref"))
                and _ref(row.get("action_id"))
                and row.get("available") is True):
            positive = {
                "whim_ref": row["whim_ref"], "action_id": row["action_id"],
                "benefit_proof_ref": row["benefit_proof_ref"],
                "capture_ref": capture_ref,
                "requires": ["FRESH_AFFORDANCE", "ONE_ACTION_PER_TURN", "SCREEN_ADMIT"],
            }

    # Determine one harmful *action*, not a harmful whim. Origin and effect
    # must be supported by independent references. No blind queue cancellation.
    classified = []
    for row in queue:
        if not isinstance(row, Mapping) or not all(_ref(row.get(k)) for k in (
                "action_id", "queue_slot_ref", "capture_ref", "sim_ref")):
            raise AutonomyModerationError("QUEUE_ROW_INVALID")
        if row["capture_ref"] != capture_ref or row["sim_ref"] != observation["sim_ref"]:
            return finish("REOBSERVE_QUEUE")
        origin = row.get("origin", "UNKNOWN")
        effect = row.get("effect", "UNKNOWN")
        if origin not in ORIGINS or effect not in EFFECTS:
            raise AutonomyModerationError("QUEUE_CLASSIFICATION_INVALID")
        if not _ref(row.get("origin_proof_ref")):
            origin = "UNKNOWN"
        if not _ref(row.get("effect_proof_ref")):
            effect = "UNKNOWN"
        classified.append((row, origin, effect))

    if any(origin == "PLAYER" for _, origin, _ in classified):
        return finish("PLAYER_QUEUE_PROTECTED")
    if setting == "OFF" and any(origin == "SIM_AUTONOMY" for _, origin, _ in classified):
        return finish("AUTONOMY_SETTING_QUEUE_CONFLICT")
    for row, origin, effect in classified:
        if (origin == "SIM_AUTONOMY"
                and effect in {"RELATIONSHIP_HARM", "ENVIRONMENT_HARM"}
                and row.get("protect_goal") is not True
                and row.get("action_id") != observation["goal_ref"]):
            if observation.get("cancel_policy_opt_in") is not True:
                return finish("HARMFUL_AUTONOMY_REVIEW_OPT_IN_REQUIRED")
            result["cancel_candidate"] = {
                "queue_slot_ref": row["queue_slot_ref"],
                "action_id": row["action_id"], "effect": effect,
                "origin_proof_ref": row["origin_proof_ref"],
                "effect_proof_ref": row["effect_proof_ref"],
                "capture_ref": capture_ref,
                "requires": ["EXACT_QUEUE_SLOT_CURRENT", "PLAYER_IDLE_LEASE",
                             "INDEPENDENT_SCREEN_ADMIT", "OBSERVE_OUTCOME_BEFORE_RETRY"],
            }
            return finish("HARMFUL_AUTONOMOUS_ACTION_CANDIDATE")
    # A completed harmful effect cannot be undone by canceling a vanished
    # queue entry. Propose one evidence-matched relationship/environment
    # mitigation, without claiming it restores the previous state.
    for outcome in outcomes:
        if not isinstance(outcome, Mapping):
            raise AutonomyModerationError("HARM_OUTCOME_ROW_INVALID")
        if (outcome.get("capture_ref") != capture_ref
                or outcome.get("sim_ref") != observation["sim_ref"]):
            return finish("REOBSERVE_HARM_OUTCOME")
        effect = outcome.get("effect")
        if effect not in {"RELATIONSHIP_HARM", "ENVIRONMENT_HARM"}:
            continue
        if (outcome.get("origin") != "SIM_AUTONOMY"
                or not all(_ref(outcome.get(k)) for k in (
                    "origin_proof_ref", "effect_proof_ref", "outcome_ref", "target_ref"
                ))):
            continue
        for repair in repairs:
            if not isinstance(repair, Mapping):
                raise AutonomyModerationError("REPAIR_ROW_INVALID")
            if (repair.get("capture_ref") != capture_ref
                    or repair.get("sim_ref") != observation["sim_ref"]):
                return finish("REOBSERVE_REPAIR_AFFORDANCES")
            if (repair.get("available") is True
                    and repair.get("effect") == effect
                    and repair.get("target_ref") == outcome["target_ref"]
                    and _ref(repair.get("action_id"))
                    and _ref(repair.get("menu_observation_ref"))):
                if observation.get("repair_policy_opt_in") is not True:
                    return finish("HARM_REPAIR_REVIEW_OPT_IN_REQUIRED")
                result["repair_candidate"] = {
                    "outcome_ref": outcome["outcome_ref"],
                    "effect": effect, "target_ref": outcome["target_ref"],
                    "action_id": repair["action_id"],
                    "menu_observation_ref": repair["menu_observation_ref"],
                    "requires": ["EXACT_ACTOR_AND_TARGET", "FRESH_MENU",
                                 "PLAYER_IDLE_LEASE", "INDEPENDENT_SCREEN_ADMIT",
                                 "OBSERVE_RESULT_NO_AUTOMATIC_RETRY"],
                    "outcome_not_reversed_by_proposal": True,
                }
                return finish("NEGATIVE_EFFECT_REPAIR_CANDIDATE")

    # Optional positive wants are *non-preemptive*: never append to a busy
    # or player-directed queue, and never outrank a still-active goal.
    if positive is not None and not classified and observation.get("goal_pending") is False:
        result["positive_whim_candidate"] = positive
        return finish("POSITIVE_WHIM_QUEUE_CANDIDATE")
    return finish("PRESERVE_QUEUE_OR_GOAL")


# Mod-importable, game-native policy seam. The Sims 4 adapter must provide
# attested interaction identities and estimates from the installed build.
# This module never invokes the game's action queue or desktop controls.
NATIVE_SCHEMA = "betterinstincts.native-household-autonomy/v1"
MAX_HOUSEHOLD_SIMS = 32
YIELD_DOMAINS = frozenset({
    "hunger", "bladder", "energy", "hygiene", "fun", "social",
    "career", "income", "skill", "aspiration", "obligation",
    "relationship", "recovery",
})


def _native_yield(row: Mapping) -> float | None:
    """Evidence-qualified, normalized positive utility; unknown is not zero."""
    if not isinstance(row, Mapping) or not _ref(row.get("yield_proof_ref")):
        return None
    values = row.get("yield_by_domain")
    if not isinstance(values, Mapping) or not values or set(values) - YIELD_DOMAINS:
        return None
    if any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1
           for v in values.values()):
        return None
    # Equal weighting is a deterministic baseline, not learned authority.
    return round(sum(values.values()), 6)


def evaluate_native_household_autonomy(
    observation: Mapping, *, now: float | None = None,
) -> dict:
    """Evaluate EVERY supplied household Sim without selected-portrait coupling.

    Suppression and replacement are recommendations for a future version-pinned
    EA-native interaction adapter, never an executed cancellation or enqueue.
    A player command, unknown ownership, missing measurement, or stale capture
    denies intervention. Positive leisure/social yields count as productive.
    """
    if not isinstance(observation, Mapping) or observation.get("schema") != NATIVE_SCHEMA:
        raise AutonomyModerationError("NATIVE_AUTONOMY_SCHEMA_INVALID")
    if not all(_ref(observation.get(k)) for k in ("household_ref", "game_build", "capture_ref")):
        raise AutonomyModerationError("NATIVE_AUTONOMY_IDENTITY_INVALID")
    sims = observation.get("sims")
    if not isinstance(sims, list) or not 1 <= len(sims) <= MAX_HOUSEHOLD_SIMS:
        raise AutonomyModerationError("NATIVE_HOUSEHOLD_BOUNDS_INVALID")
    instant = time.time() if now is None else now
    stamp = observation.get("observed_at_unix")
    fresh = (
        type(stamp) in (int, float) and type(instant) in (int, float)
        and math.isfinite(stamp) and math.isfinite(instant)
        and 0 <= instant - stamp <= MAX_AGE
    )
    result = {
        "schema": "betterinstincts.native-household-autonomy-result/v1",
        "household_ref": observation["household_ref"],
        "capture_ref": observation["capture_ref"],
        "game_build": observation["game_build"],
        "decisions": [],
        "cancel_allowed": False,
        "enqueue_allowed": False,
        "desktop_input_allowed": False,
        "proof_ceiling": "OFFLINE_NATIVE_POLICY_NOT_EA_HOOK_OR_GAME_EFFECT",
    }
    seen = set()
    for sim in sims:
        if not isinstance(sim, Mapping) or not _ref(sim.get("sim_ref")):
            raise AutonomyModerationError("NATIVE_SIM_IDENTITY_INVALID")
        sim_id = sim["sim_ref"]
        if sim_id in seen:
            raise AutonomyModerationError("NATIVE_DUPLICATE_SIM")
        seen.add(sim_id)
        decision = {
            "sim_ref": sim_id, "state": "PRESERVE_UNKNOWN",
            "suppress_candidate": None, "replacement_candidate": None,
        }
        result["decisions"].append(decision)
        if not fresh or sim.get("capture_ref") != observation["capture_ref"]:
            decision["state"] = "REOBSERVE_SIM"
            continue
        if (observation.get("player_active") is not False
                or sim.get("player_command_present") is not False
                or sim.get("player_owned") is not False):
            decision["state"] = "PLAYER_OR_UNKNOWN_OWNER_PROTECTED"
            continue
        if sim.get("queue_verified") is not True:
            decision["state"] = "QUEUE_NOT_VERIFIED"
            continue
        queue = sim.get("queue", [])
        alternatives = sim.get("available_actions", [])
        if (not isinstance(queue, list) or len(queue) > MAX_QUEUE
                or not isinstance(alternatives, list) or len(alternatives) > MAX_REPAIRS):
            raise AutonomyModerationError("NATIVE_ACTION_BOUNDS_INVALID")
        # A protected player action anywhere in this Sim's queue blocks all
        # optimization of that queue. It never depends on the active portrait.
        if any(not isinstance(a, Mapping) or a.get("origin") == "PLAYER"
               or a.get("origin") not in ORIGINS for a in queue):
            decision["state"] = "PLAYER_QUEUE_PROTECTED"
            continue
        active_goal = sim.get("active_goal")
        goal_score = None
        if isinstance(active_goal, Mapping) and active_goal.get("active") is True:
            goal_score = _native_yield(active_goal)
            if not _ref(active_goal.get("action_id")) or goal_score is None:
                decision["state"] = "GOAL_EVIDENCE_UNKNOWN"
                continue
        best = None
        for candidate in alternatives:
            if not isinstance(candidate, Mapping):
                raise AutonomyModerationError("NATIVE_ALTERNATIVE_INVALID")
            score = _native_yield(candidate)
            if (score is not None and score > 0
                    and candidate.get("available") is True
                    and candidate.get("native_affordance_verified") is True
                    and _ref(candidate.get("action_id"))
                    and (best is None or score > best[0])):
                best = (score, candidate)
        for action in queue:
            if not all(_ref(action.get(k)) for k in ("action_id", "queue_slot_ref",
                                                     "origin_proof_ref")):
                decision["state"] = "ACTION_PROVENANCE_UNKNOWN"
                break
            if action["origin"] != "SIM_AUTONOMY":
                continue
            action_score = _native_yield(action)
            if action_score is None:
                decision["state"] = "ACTION_YIELD_UNKNOWN"
                break
            if active_goal is not None and action.get("action_id") == active_goal.get("action_id"):
                continue
            if active_goal is not None and active_goal.get("active") is True:
                # The expected *loss of ongoing goal progress* must be attested.
                if action.get("interrupts_goal") is not True or goal_score is None:
                    continue
                better = goal_score > action_score
                replacement = {"action_id": active_goal["action_id"],
                               "kind": "RESUME_ATTESTED_GOAL"}
            else:
                better = action_score == 0 and best is not None
                replacement = ({"action_id": best[1]["action_id"],
                                "kind": "NATIVE_AFFORDANCE_CANDIDATE"} if best else None)
            if not better or replacement is None:
                continue
            if action.get("effect_proof_ref") is None or not _ref(action["effect_proof_ref"]):
                decision["state"] = "ACTION_EFFECT_UNKNOWN"
                break
            if sim.get("policy_opt_in") is not True:
                decision["state"] = "OPT_IN_REQUIRED"
                break
            decision["state"] = "NATIVE_SUPPRESSION_CANDIDATE"
            decision["suppress_candidate"] = {
                "queue_slot_ref": action["queue_slot_ref"],
                "action_id": action["action_id"],
                "observed_yield": action_score,
                "protected_goal_yield": goal_score,
                "requires": ["EA_NATIVE_QUEUE_IDENTITY", "EXACT_PATCH_ADAPTER",
                             "RECHECK_PLAYER_CONTROL", "RECHECK_GOAL_AND_YIELD",
                             "OBSERVE_EFFECT_BEFORE_NEXT_DECISION"],
            }
            decision["replacement_candidate"] = replacement
            break
        else:
            if decision["state"] == "PRESERVE_UNKNOWN":
                decision["state"] = "PRESERVE_QUEUE_OR_YIELD"
    return result
