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
    result = {
        "schema": "betterinstincts.autonomy-moderation-result/v1",
        "sim_ref": observation["sim_ref"], "capture_ref": capture_ref,
        "observed_autonomy_setting": setting,
        "state": "INSPECT_AUTONOMY_EVIDENCE", "cancel_candidate": None,
        "positive_whim_candidate": None, "execute_allowed": False,
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
    # Optional positive wants are *non-preemptive*: never append to a busy
    # or player-directed queue, and never outrank a still-active goal.
    if positive is not None and not classified and observation.get("goal_pending") is False:
        result["positive_whim_candidate"] = positive
        return finish("POSITIVE_WHIM_QUEUE_CANDIDATE")
    return finish("PRESERVE_QUEUE_OR_GOAL")
