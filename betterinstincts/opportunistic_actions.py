"""Evidence-qualified late homework and target-specific chat whims.

Pure host policy. This module never presses R, clicks Sims, cancels class,
enqueues gameplay, selects saves, or grants a screen/native-effect permit.
"""
from __future__ import annotations

import re
from typing import Mapping, Sequence

from betterinstincts.queue_capacity import evaluate_queue_capacity, QueueCapacityError
from betterinstincts.social_opportunity import lookup_sim_library, SocialOpportunityError
from betterinstincts.teen_homework import _queue_has_homework

CHAT_PATTERN = re.compile(r"^(?:chat|talk) (?:with|to) ([A-Za-z][A-Za-z0-9 '\-]{0,79})$", re.IGNORECASE)
SIM_ID = re.compile(r"^[a-zA-Z0-9:._-]{1,100}$")
REF = re.compile(r"^[a-zA-Z0-9:._-]{3,120}$")
SAFE_INVITE = frozenset({"HUMAN", "KNOWN_SAFE_NON_VAMPIRE"})
HOMEWORK_STATES = frozenset({"before_class", "class_transition", "class_time"})
HOMEWORK_ACTIONS = frozenset({"DO_HOMEWORK", "CONTINUE_HOMEWORK"})
SOCIAL_ACTIONS = frozenset({"CHAT_ON_LOT", "RELATIONSHIP_CHAT", "INVITE_OVER"})
PROOF = "HOST_ADVISORY_ONLY_EXACT_PATCH_EA_LIVE_PROOF_OPEN"


class OpportunisticActionError(ValueError):
    """Untrusted input cannot become a native game-action recommendation."""


def _receipt(gate: str, *, action: str = "NO_ACTION", capture_ref: str,
             next_actions: Sequence[Mapping] = (), **extra: object) -> dict:
    return {
        "schema": "betterinstincts.opportunistic-action-plan/v1",
        "gate": gate,
        "action": action,
        "capture_ref": capture_ref,
        "next_actions": list(next_actions),
        "primary_route": next_actions[0]["id"] if next_actions else None,
        "execute_allowed": False,
        "requires_native_effect_admission": True,
        "proof_ceiling": PROOF,
        **extra,
    }


def _valid_capture(ref: str) -> bool:
    return isinstance(ref, str) and bool(REF.fullmatch(ref))


def plan_school_homework_window(
    observation: Mapping | None, *, capture_ref: str,
    school_phase: str, school_day_active: bool, location_kind: str,
    homework_pending: bool, inventory_has_homework: bool | None,
    queue: Sequence[str], player_directed: bool, already_busy: bool,
    survival_critical: Sequence[str], multitasking: bool | None = None,
) -> dict | None:
    """A proved usable game interaction overrides the old heuristic, not attendance.

    A class in progress is not by itself permission: the local verified
    source must affirm homework can proceed WITHOUT canceling attendance.
    """
    if observation is None:
        return None
    if not isinstance(observation, Mapping):
        raise OpportunisticActionError("HOMEWORK_WINDOW_INVALID")
    allowed = {
        "capture_ref", "game_version", "school_phase", "homework_available",
        "homework_running", "class_attendance_preserved", "observed_actions",
        "source_kind",
    }
    if set(observation) != allowed:
        raise OpportunisticActionError("HOMEWORK_WINDOW_FIELDS_INVALID")
    if (not _valid_capture(capture_ref)
            or observation["capture_ref"] != capture_ref
            or not isinstance(observation["game_version"], str)
            or not re.fullmatch(r"[0-9]+(?:\.[0-9]+){2,5}", observation["game_version"])
            or observation["school_phase"] not in HOMEWORK_STATES
            or observation["school_phase"] != school_phase
            or observation["source_kind"] not in {"GAME_UI_VERIFIED", "EA_NATIVE_VERIFIED"}):
        return _receipt("HOMEWORK_WINDOW_REOBSERVE", capture_ref=capture_ref)
    if (any(type(observation[key]) is not bool for key in (
            "homework_available", "homework_running", "class_attendance_preserved"))
            or not isinstance(observation["observed_actions"], list)
            or len(observation["observed_actions"]) > 4
            or any(x not in HOMEWORK_ACTIONS for x in observation["observed_actions"])):
        raise OpportunisticActionError("HOMEWORK_AFFORDANCE_INVALID")
    if player_directed or already_busy:
        return _receipt("HOMEWORK_WINDOW_PLAYER_FIRST", capture_ref=capture_ref)
    if survival_critical:
        return _receipt("HOMEWORK_WINDOW_SURVIVAL_FIRST",
                        capture_ref=capture_ref, survival_critical=list(survival_critical))
    if (not homework_pending or not school_day_active
            or location_kind != "school" or inventory_has_homework is not True):
        return _receipt("HOMEWORK_WINDOW_CONTEXT_NOT_ADMITTED", capture_ref=capture_ref)
    if not observation["class_attendance_preserved"]:
        return _receipt("HOMEWORK_WINDOW_ATTEND_CLASS_FIRST",
                        capture_ref=capture_ref)
    if observation["homework_running"] and "CONTINUE_HOMEWORK" in observation["observed_actions"]:
        return _receipt(
            "HOMEWORK_WINDOW_CONTINUE", capture_ref=capture_ref,
            action="KEEP_RUNNING_HOMEWORK_AND_PRESERVE_CLASS_ATTENDANCE",
            next_actions=[{
                "id": "CONTINUE_EXISTING_HOMEWORK",
                "steps": ["OBSERVE_HOMEWORK_PROGRESS", "KEEP_CLASS_ATTENDANCE_QUEUED",
                          "CONFIRM_HOMEWORK_COMPLETION", "REOBSERVE_CLASS_STATE"],
            }], school_phase=school_phase,
        )
    if _queue_has_homework(queue):
        return _receipt("HOMEWORK_WINDOW_ALREADY_QUEUED",
                        capture_ref=capture_ref, action="REOBSERVE_HOMEWORK_QUEUE")
    if (not observation["homework_available"]
            or "DO_HOMEWORK" not in observation["observed_actions"]):
        return _receipt("HOMEWORK_WINDOW_AFFORDANCE_MISSING",
                        capture_ref=capture_ref)
    try:
        budget = evaluate_queue_capacity(queue, multitasking=multitasking,
                                         player_directed=player_directed)
    except QueueCapacityError as exc:
        raise OpportunisticActionError(str(exc)) from exc
    if not budget["enqueue_allowed"]:
        return _receipt("HOMEWORK_WINDOW_QUEUE_CAPACITY_HOLD",
                        capture_ref=capture_ref, queue_budget=budget)
    return _receipt(
        "HOMEWORK_WINDOW_READY", capture_ref=capture_ref,
        action="QUEUE_PROVED_LAST_MINUTE_HOMEWORK_KEEP_CLASS",
        next_actions=[{
            "id": "DO_HOMEWORK_OBSERVED_SCHOOL_WINDOW",
            "steps": ["CONFIRM_CURRENT_SIM_SCHOOL_ATTENDANCE",
                      "OPEN_OBSERVED_HOMEWORK_BOOK",
                      "SELECT_OBSERVED_DO_HOMEWORK",
                      "REOBSERVE_HOMEWORK_AND_CLASS_ATTENDANCE"],
            "game_version": observation["game_version"],
            "school_phase": school_phase,
            "observed_source": observation["source_kind"],
        }],
        queue_budget=budget, school_phase=school_phase,
    )


def plan_targeted_chat_whim(
    whims: Sequence[str], sim_library: Sequence[Mapping], *,
    capture_ref: str, queue: Sequence[str] = (),
    queued_social_targets: Sequence[Mapping] = (),
    player_directed: bool = False, already_busy: bool = False,
    survival_critical: Sequence[str] = (),
    multitasking: bool | None = None,
) -> dict | None:
    """Target-specific whim→on-lot/R Relationships, never arbitrary Sim chat."""
    if not isinstance(whims, (list, tuple)) or not isinstance(sim_library, (list, tuple)):
        raise OpportunisticActionError("CHAT_WHIM_INPUT_INVALID")
    matches = []
    for raw in whims:
        if not isinstance(raw, str) or len(raw) > 120:
            raise OpportunisticActionError("CHAT_WHIM_LABEL_INVALID")
        found = CHAT_PATTERN.fullmatch(raw.strip())
        if found:
            matches.append(found.group(1).strip())
    if not matches:
        return None
    if len(matches) > 1:
        # One-target-at-a-time scheduler; cannot choose competing wishes.
        return _receipt("CHAT_WHIM_MULTIPLE_TARGETS_REVIEW", capture_ref=capture_ref)
    target = matches[0]
    if player_directed or already_busy:
        return _receipt("CHAT_WHIM_PLAYER_FIRST", capture_ref=capture_ref,
                        target_name=target)
    if survival_critical:
        return _receipt("CHAT_WHIM_SURVIVAL_FIRST", capture_ref=capture_ref,
                        target_name=target)
    if not _valid_capture(capture_ref):
        raise OpportunisticActionError("CHAT_CAPTURE_REF_INVALID")
    try:
        lookup = lookup_sim_library(target, sim_library)
    except SocialOpportunityError as exc:
        raise OpportunisticActionError(str(exc)) from exc
    if not lookup["unique"]:
        return _receipt(
            "CHAT_WHIM_TARGET_LOOKUP_REQUIRED", capture_ref=capture_ref,
            target_name=target, lookup_state=lookup["state"],
            next_actions=[{
                "id": "OPEN_RELATIONSHIPS_FOR_EXACT_TARGET",
                "steps": ["PRESS_R_AFTER_INDEPENDENT_HOST_ADMISSION",
                          "LOCATE_EXACT_RELATIONSHIP_NAME",
                          "RECAPTURE_UNIQUE_SIM_ID_AND_ACTIONS"],
            }],
        )
    rec = lookup["record"]
    # Do not treat a matched name as a scene / target or an action permit.
    rows = [
        row for row in sim_library
        if isinstance(row, Mapping)
        and str(row.get("name") or row.get("sim_name") or "").casefold().strip()
        == rec["name"].casefold().strip()
    ]
    if len(rows) != 1:
        return _receipt("CHAT_WHIM_TARGET_REOBSERVE", capture_ref=capture_ref)
    row = rows[0]
    sim_id = row.get("sim_id")
    actions = row.get("observed_actions")
    if (not isinstance(sim_id, str) or not SIM_ID.fullmatch(sim_id)
            or row.get("capture_ref") != capture_ref
            or type(row.get("on_lot")) is not bool
            or not isinstance(actions, list) or len(actions) > 5
            or any(action not in SOCIAL_ACTIONS for action in actions)):
        return _receipt("CHAT_WHIM_TARGET_REOBSERVE",
                        capture_ref=capture_ref, target_name=target)
    for item in queued_social_targets:
        if not isinstance(item, Mapping) or set(item) != {
            "sim_id", "action_kind", "capture_ref",
        }:
            raise OpportunisticActionError("CHAT_QUEUE_ENTRY_UNVERIFIED")
        if item["capture_ref"] != capture_ref:
            return _receipt("CHAT_WHIM_QUEUE_REOBSERVE",
                            capture_ref=capture_ref, target_sim_id=sim_id)
        if item["sim_id"] == sim_id and item["action_kind"] == "CHAT":
            return _receipt("CHAT_WHIM_ALREADY_QUEUED",
                            capture_ref=capture_ref, target_sim_id=sim_id,
                            action="REOBSERVE_TARGETED_CHAT_PROGRESS")
    if any(re.search(r"\b(?:chat|talk)\b", str(item), re.I) for item in queue) and not queued_social_targets:
        return _receipt("CHAT_WHIM_QUEUE_REOBSERVE",
                        capture_ref=capture_ref, target_sim_id=sim_id)
    try:
        budget = evaluate_queue_capacity(queue, multitasking=multitasking,
                                         player_directed=player_directed)
    except QueueCapacityError as exc:
        raise OpportunisticActionError(str(exc)) from exc
    if not budget["enqueue_allowed"]:
        return _receipt("CHAT_WHIM_QUEUE_CAPACITY_HOLD",
                        capture_ref=capture_ref, target_sim_id=sim_id,
                        queue_budget=budget)
    base = {"target_sim_id": sim_id, "target_name": rec["name"]}
    if row["on_lot"] and "CHAT_ON_LOT" in actions:
        return _receipt("CHAT_WHIM_ON_LOT_READY", capture_ref=capture_ref,
                        action="PLAN_EXACT_ON_LOT_CHAT",
                        next_actions=[{"id": "CHAT_WITH_OBSERVED_ON_LOT_SIM",
                                       "steps": ["VERIFY_SELECTED_SIM",
                                                 "LOCATE_EXACT_ON_LOT_SIM",
                                                 "CHOOSE_OBSERVED_CHAT",
                                                 "REOBSERVE_TARGETED_QUEUE"]}],
                        queue_budget=budget, **base)
    if "RELATIONSHIP_CHAT" in actions:
        return _receipt("CHAT_WHIM_RELATIONSHIP_READY", capture_ref=capture_ref,
                        action="PLAN_R_RELATIONSHIP_CHAT",
                        next_actions=[{"id": "R_RELATIONSHIPS_EXACT_SIM_CHAT",
                                       "steps": ["PRESS_R_AFTER_INDEPENDENT_HOST_ADMISSION",
                                                 "VERIFY_EXACT_SIM_RELATIONSHIP_CARD",
                                                 "CHOOSE_OBSERVED_CHAT",
                                                 "REOBSERVE_TARGETED_QUEUE"]}],
                        queue_budget=budget, **base)
    if (not row["on_lot"] and "INVITE_OVER" in actions
            and rec["occult_status"] in SAFE_INVITE):
        return _receipt("CHAT_WHIM_INVITE_REVIEW", capture_ref=capture_ref,
                        action="REVIEW_SAFE_INVITE_THEN_CHAT",
                        next_actions=[{"id": "R_RELATIONSHIPS_INVITE_REVIEW",
                                       "steps": ["PRESS_R_AFTER_INDEPENDENT_HOST_ADMISSION",
                                                 "VERIFY_EXACT_SIM_RELATIONSHIP_CARD",
                                                 "RECHECK_OCCULT_AND_INVITE_PERMISSION",
                                                 "REOBSERVE_ARRIVAL_ON_LOT",
                                                 "CHOOSE_CHAT_IF_OBSERVED"]}],
                        queue_budget=budget, **base)
    return _receipt("CHAT_WHIM_AFFORDANCE_UNKNOWN",
                    capture_ref=capture_ref, target_name=target,
                    target_sim_id=sim_id,
                    action="REOBSERVE_RELATIONSHIP_ACTIONS")
