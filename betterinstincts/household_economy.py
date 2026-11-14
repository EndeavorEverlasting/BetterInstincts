"""Human-first, read-only cooperative household responsibility allocation.

The existing domain policies own needs, wellbeing, money, skills, career,
upkeep and game-native effects. This planner only assigns *observed available*
work to one safely eligible actor at a time. No background jobs, Sims queue
mutation, estimated income, player input, or profile/save writes.
"""
from __future__ import annotations

import math
import re
from collections.abc import Mapping
from typing import Any

from betterinstincts.household_judgment import require_fixed_roster, HouseholdJudgmentError
from betterinstincts.mechanics_registry import load_registry, MechanicsRegistryError
from betterinstincts.queue_capacity import evaluate_queue_capacity, QueueCapacityError
from betterinstincts.career_service import evaluate_work_shift_tone, CareerServiceError

SCHEMA = "betterinstincts.household-economy.observation/v1"
SIX = frozenset(("hunger", "bladder", "energy", "hygiene", "fun", "social"))
SERVO_NEEDS = frozenset(("charge", "durability", "fun", "social"))
RECOVERING_OR_ABSENT = frozenset(("ASLEEP", "RECHARGING", "AWAY"))
ACTIVITIES = RECOVERING_OR_ABSENT | {"AWAKE", "UNKNOWN", "AT_WORK"}
REF = re.compile(r"^[A-Za-z0-9:_./-]{3,180}$")
MOODS = frozenset(("HAPPY", "STABLE", "STRAINED", "UNKNOWN"))
TEMPERAMENTS = frozenset(("BALANCED", "IRRITABLE", "UNKNOWN"))
KINDS = frozenset(("OBLIGATION", "UPKEEP", "YIELD"))
PROOF = "OFFLINE_COOPERATIVE_ALLOCATIONS_NOT_NATIVE_SIM_EXECUTION"


class HouseholdEconomyError(ValueError):
    pass


def _ref(value: object) -> bool:
    return isinstance(value, str) and bool(REF.fullmatch(value))


def _num(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1


def _need_state(row: Mapping, *, solo: bool, yield_work: bool) -> str:
    if row["mood"] not in {"HAPPY", "STABLE"} or row["temperament"] != "BALANCED":
        return "EMOTIONAL_RECOVERY_FIRST"
    needs = row["needs"]
    # One Sim must have substantially more breathing room; collective tasks
    # may be shared but never at the price of a fragile individual's welfare.
    minimum = 0.8 if solo and yield_work else 0.65 if solo else 0.7 if yield_work else 0.45
    social_fun = 0.8 if solo and yield_work else 0.65 if solo else 0.75 if yield_work else 0.55
    if min(needs.values()) < minimum or needs["fun"] < social_fun or needs["social"] < social_fun:
        return "PERSONAL_NEEDS_OR_LEISURE_FIRST"
    return "WELFARE_RESERVE_MET"


def _scope(data: Mapping, members: list[dict]) -> tuple[str, list[str]]:
    scope = data.get("scope")
    if (not isinstance(scope, Mapping) or scope.get("schema") != "betterinstincts.household-scope/v1"
            or not _ref(scope.get("scope_id")) or
            not _ref(scope.get("roster_fingerprint"))
            or scope.get("execution_permit") is not None
            or type(scope.get("member_count")) is not int
            or not isinstance(scope.get("member_keys"), list)):
        raise HouseholdEconomyError("OPAQUE_VERIFIED_HOUSEHOLD_SCOPE_REQUIRED")
    ids = scope["member_keys"]
    if scope["member_count"] != len(members) or len(ids) != len(members):
        raise HouseholdEconomyError("HOUSEHOLD_MEMBERS_SCOPE_MISMATCH")
    try:
        require_fixed_roster(ids, [row["member_key"] for row in members])
    except (HouseholdJudgmentError, KeyError, TypeError) as exc:
        raise HouseholdEconomyError("ROSTER_CHANGED_STOP_RECONCILE") from exc
    if (data.get("roster_verified") is not True
            or data.get("observed_roster_fingerprint") != scope["roster_fingerprint"]):
        raise HouseholdEconomyError("ROSTER_EVIDENCE_MISSING_OR_CHANGED")
    return scope["scope_id"], ids


def _validate(raw: Mapping, mechanics: Mapping) -> tuple[list[dict], list[dict], list[dict], str]:
    if not isinstance(raw, Mapping) or raw.get("schema") != SCHEMA:
        raise HouseholdEconomyError("HOUSEHOLD_ECONOMY_SCHEMA_REQUIRED")
    if (not _ref(raw.get("capture_ref"))
            or not isinstance(raw.get("members"), list)
            or not 1 <= len(raw["members"]) <= 16
            or not isinstance(raw.get("tasks"), list)
            or len(raw["tasks"]) > 48):
        raise HouseholdEconomyError("BOUNDED_SNAPSHOT_REQUIRED")
    if raw.get("player_active") is not False or type(raw.get("player_active")) is not bool:
        raise HouseholdEconomyError("PLAYER_PRESENCE_NOT_CLEARED")
    members = raw["members"]
    scope_id, member_keys = _scope(raw, members)
    if "selected_member_key" in raw and raw["selected_member_key"] not in member_keys:
        raise HouseholdEconomyError("SELECTED_MEMBER_OUTSIDE_VERIFIED_ROSTER")
    # A completed needs-review is an independently observed caller event, not
    # elapsed time, a prior agent assertion, or a reason to scroll forever.
    review = raw.get("attention_review")
    if review is not None:
        if (not isinstance(review, Mapping)
                or set(review) != {"member_key", "capture_ref", "proof_ref", "state"}
                or review["member_key"] != raw.get("selected_member_key")
                or review["capture_ref"] != raw["capture_ref"]
                or not _ref(review["proof_ref"])
                or review["state"] != "VERIFIED_COMPLETE"):
            raise HouseholdEconomyError("ATTENTION_REVIEW_PROOF_INVALID")
    catalog = {row["id"]: row for row in mechanics["mechanics"]}
    seen_tasks: set[str] = set()
    seen_resources: set[str] = set()
    reservations = raw.get("reserved_resources")
    if (not isinstance(reservations, list) or len(reservations) > 48
            or any(not _ref(x) for x in reservations)
            or len(set(reservations)) != len(reservations)):
        raise HouseholdEconomyError("RESERVED_RESOURCES_INVALID")
    failures = raw.get("failed_tasks", [])
    if (not isinstance(failures, list) or len(failures) > 48
            or any(not isinstance(x, Mapping) or set(x) != {
                "task_ref", "proof_ref", "capture_ref", "outcome",
            } for x in failures)):
        raise HouseholdEconomyError("TASK_OUTCOMES_INVALID")
    proofs: set[str] = set()
    failed: set[str] = set()
    for item in failures:
        if (not _ref(item["task_ref"]) or not _ref(item["proof_ref"])
                or item["proof_ref"] in proofs
                or item["capture_ref"] != raw["capture_ref"]
                or item["outcome"] not in {"FAILED", "UNAVAILABLE"}):
            raise HouseholdEconomyError("UNVERIFIED_OR_REPLAYED_TASK_OUTCOME")
        proofs.add(item["proof_ref"])
        failed.add(item["task_ref"])
    for member in members:
        if (not isinstance(member, Mapping) or not _ref(member.get("member_key"))
                or member.get("mood") not in MOODS
                or member.get("temperament") not in TEMPERAMENTS
                or member.get("capture_ref") != raw["capture_ref"]
                or not isinstance(member.get("needs"), Mapping)
                or member.get("sim_kind", "HUMAN") not in ("HUMAN", "SERVO")
                or set(member["needs"]) != (SERVO_NEEDS if member.get("sim_kind") == "SERVO" else SIX)
                or not all(_num(x) for x in member["needs"].values())):
            raise HouseholdEconomyError("MEMBER_WELLBEING_OBSERVATION_INVALID")
        activity = member.get("activity", "UNKNOWN")
        if not isinstance(activity, str) or activity not in ACTIVITIES:
            raise HouseholdEconomyError("MEMBER_ACTIVITY_INVALID")
        if any(type(member.get(key)) is not bool for key in (
            "player_reserved", "busy", "available", "queue_verified",
        )):
            raise HouseholdEconomyError("MEMBER_STATUS_FLAGS_INVALID")
        if (not isinstance(member.get("queue"), list)
                or member.get("multitasking") is not None and type(member["multitasking"]) is not bool
                or type(member.get("recent_workload")) is not int
                or not 0 <= member["recent_workload"] <= 8):
            raise HouseholdEconomyError("MEMBER_QUEUE_OR_WORKLOAD_INVALID")
        if (not isinstance(member.get("skills"), Mapping)
                or not isinstance(member.get("likes"), list)
                or not isinstance(member.get("dislikes"), list)
                or len(member["likes"]) > 32 or len(member["dislikes"]) > 32):
            raise HouseholdEconomyError("MEMBER_SKILLS_OR_PREFERENCES_INVALID")
        for field in ("likes", "dislikes"):
            if (any(x not in catalog for x in member[field])
                    or len(set(member[field])) != len(member[field])):
                raise HouseholdEconomyError("MEMBER_MECHANIC_PREFERENCES_INVALID")
        for mech, skill in member["skills"].items():
            if (mech not in catalog or not isinstance(skill, Mapping)
                    or set(skill) != {"level", "verified"}
                    or type(skill["verified"]) is not bool
                    or (skill["verified"] and (type(skill["level"]) is not int
                                                 or not 0 <= skill["level"] <= 10))
                    or (not skill["verified"] and skill["level"] is not None)):
                raise HouseholdEconomyError("UNVERIFIED_MEMBER_SKILLS_INVALID")
    if review is not None:
        reviewed = next(row for row in members
                        if row["member_key"] == review["member_key"])
        if (reviewed.get("activity") != "AWAKE" or reviewed["player_reserved"]
                or not reviewed["queue_verified"]):
            raise HouseholdEconomyError("ATTENTION_REVIEW_ACTOR_NOT_VERIFIED_AVAILABLE")
    tasks = raw["tasks"]
    for task in tasks:
        if (not isinstance(task, Mapping) or set(task) != {
                "task_ref", "mechanic_id", "kind", "priority", "resource_ref",
                "required_skill", "min_skill_level", "eligible_member_keys",
                "observed_available", "player_owned", "capture_ref",
        }):
            raise HouseholdEconomyError("TASK_RECORD_SCHEMA_INVALID")
        ident, mech = task["task_ref"], task["mechanic_id"]
        if (not _ref(ident) or ident in seen_tasks or mech not in catalog
                or task["kind"] not in KINDS or type(task["priority"]) is not int
                or not 1 <= task["priority"] <= 3
                or task["capture_ref"] != raw["capture_ref"]
                or type(task["observed_available"]) is not bool
                or type(task["player_owned"]) is not bool
                or not isinstance(task["eligible_member_keys"], list)
                or not task["eligible_member_keys"]
                or len(task["eligible_member_keys"]) > 16
                or set(task["eligible_member_keys"]) - set(member_keys)
                or len(set(task["eligible_member_keys"])) != len(task["eligible_member_keys"])):
            raise HouseholdEconomyError("TASK_IDENTITY_OR_AVAILABILITY_INVALID")
        seen_tasks.add(ident)
        resource = task["resource_ref"]
        if resource is not None and not _ref(resource):
            raise HouseholdEconomyError("TASK_RESOURCE_INVALID")
        if task["required_skill"] is not None and task["required_skill"] not in catalog:
            raise HouseholdEconomyError("UNKNOWN_REQUIRED_SKILL")
        if (type(task["min_skill_level"]) is not int
                or not 0 <= task["min_skill_level"] <= 10
                or (task["required_skill"] is None and task["min_skill_level"])):
            raise HouseholdEconomyError("SKILL_MINIMUM_INVALID")
        if resource is not None:
            seen_resources.add(resource)
    if failed - seen_tasks:
        raise HouseholdEconomyError("FAILED_TASK_NOT_IN_CURRENT_SCOPE")
    return members, tasks, failures, scope_id


def _choose_member(task: Mapping, members: list[dict], allocated: set[str],
                   *, solo: bool, verified_awake_required: bool) -> tuple[dict | None, str]:
    eligible = []
    for row in members:
        key = row["member_key"]
        if key not in task["eligible_member_keys"] or key in allocated:
            continue
        activity = row.get("activity", "UNKNOWN")
        if activity in RECOVERING_OR_ABSENT or activity == "AT_WORK" or (verified_awake_required and activity != "AWAKE"):
            continue
        if (row["player_reserved"] or row["busy"] or not row["available"]
                or not row["queue_verified"]):
            continue
        if task["mechanic_id"] in row["dislikes"]:
            continue
        if _need_state(row, solo=solo, yield_work=task["kind"] == "YIELD") != "WELFARE_RESERVE_MET":
            continue
        skill_id = task["required_skill"]
        skill = row["skills"].get(skill_id) if skill_id else None
        if skill_id and (not isinstance(skill, Mapping) or skill["verified"] is not True
                          or skill["level"] < task["min_skill_level"]):
            continue
        budget = evaluate_queue_capacity(row["queue"],
                                         multitasking=row["multitasking"])
        if not budget["enqueue_allowed"]:
            continue
        score = (
            1 if task["mechanic_id"] in row["likes"] else 0,
            skill["level"] if skill is not None else 0,
            -row["recent_workload"],
            -len(row["queue"]),
        )
        eligible.append((score, key, row))
    if not eligible:
        return None, "NO_VERIFIED_WELL_MEMBER_WITH_CAPACITY"
    # Stable tie resolution. Do not fabricate utility or expected money.
    eligible.sort(key=lambda triple: (tuple(-v for v in triple[0]), triple[1]))
    return eligible[0][2], "MATCHED_VERIFIED_PREFERENCES_SKILLS_AND_FAIRNESS"


def _next_awake_portrait(members: list[dict], selected_key: str) -> dict | None:
    """One verified next portrait in the fixed ordered roster; never self-select.

    Observation eligibility is independent of the income/chores welfare floor:
    an awake Sim with *critical needs* must still be selected for care.
    """
    start = next(i for i, row in enumerate(members)
                 if row["member_key"] == selected_key)
    for offset in range(1, len(members)):
        candidate = members[(start + offset) % len(members)]
        if (candidate.get("activity") == "AWAKE"
                and not candidate["player_reserved"]
                and candidate["queue_verified"]):
            return candidate
    return None


def evaluate_household_economy(observation: Mapping) -> dict:
    """One bounded allocation cycle for a bound roster and fresh capture.

    Caller may pass candidates produced by existing need, upkeep, career,
    gardening, social and budgeting owners. This module cannot invent tasks.
    """
    try:
        mechanics = load_registry()
    except MechanicsRegistryError as exc:
        raise HouseholdEconomyError(str(exc)) from exc
    members, tasks, failures, scope_id = _validate(observation, mechanics)
    catalog = {row["id"]: row for row in mechanics["mechanics"]}
    solo = len(members) == 1
    selected = next((row for row in members
                     if row["member_key"] == observation.get("selected_member_key")), None)
    # One exact current-shift observation is required before advising a tone
    # or releasing attention. A departing Sim is not proof of being at work.
    work_tone = None
    shift = observation.get("work_shift")
    if shift is not None:
        if selected is None or selected.get("activity") != "AT_WORK":
            raise HouseholdEconomyError("WORK_SHIFT_SELECTED_ACTOR_NOT_AT_WORK")
        try:
            work_tone = evaluate_work_shift_tone(
                shift, member_key=selected["member_key"],
                capture_ref=observation["capture_ref"],
                wellbeing_ready=(
                    _need_state(selected, solo=solo, yield_work=True)
                    == "WELFARE_RESERVE_MET"
                ),
                player_reserved=selected["player_reserved"],
            )
        except (CareerServiceError, TypeError, KeyError) as exc:
            raise HouseholdEconomyError("WORK_SHIFT_EVIDENCE_INVALID:" + str(exc)) from exc
    handoff_from = None
    handoff_cause = None
    if selected is not None and not selected["player_reserved"]:
        if selected.get("activity") in RECOVERING_OR_ABSENT:
            handoff_from = selected["member_key"]
            handoff_cause = "SELECTED_MEMBER_RECOVERING_OR_AWAY"
        elif (observation.get("attention_review") is not None
              and selected.get("activity") == "AWAKE"):
            handoff_from = selected["member_key"]
            handoff_cause = "SELECTED_MEMBER_NEEDS_REVIEW_VERIFIED_COMPLETE"
        elif (selected.get("activity") == "AT_WORK"
              and work_tone is not None and work_tone["handoff_ready"]):
            handoff_from = selected["member_key"]
            handoff_cause = "SELECTED_MEMBER_AT_RABBIT_HOLE_WORK"
    allocated: set[str] = set()
    reserved = set(observation["reserved_resources"])
    failed = {row["task_ref"] for row in failures}
    allocations: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    # Obligations first; uncertain money-yield never outranks lived welfare.
    for task in sorted(tasks, key=lambda t: (t["priority"], {"OBLIGATION": 0,
                       "UPKEEP": 1, "YIELD": 2}[t["kind"]], t["task_ref"])):
        ident = task["task_ref"]
        mechanic = catalog[task["mechanic_id"]]
        if ident in failed:
            reason = "FAILED_ACTION_HOLD_REPLAN_WITH_NEW_EVIDENCE"
        elif task["player_owned"]:
            reason = "PLAYER_OWNED_TASK_PROTECTED"
        elif not task["observed_available"]:
            reason = "GAME_MECHANIC_AFFORDANCE_UNOBSERVED"
        elif mechanic["evidence_state"] != "SOURCE_PRESENT":
            reason = "UNCOVERED_MECHANIC_DISCOVERY_REQUIRED"
        elif task["resource_ref"] is not None and task["resource_ref"] in reserved:
            reason = "SHARED_RESOURCE_ALREADY_CLAIMED"
        else:
            actor, reason = _choose_member(
                task, members, allocated, solo=solo,
                verified_awake_required=handoff_from is not None,
            )
            if actor is not None:
                allocated.add(actor["member_key"])
                if task["resource_ref"] is not None:
                    reserved.add(task["resource_ref"])
                allocations.append({
                    "task_ref": ident,
                    "mechanic_id": task["mechanic_id"],
                    "member_key": actor["member_key"],
                    "kind": task["kind"],
                    "resource_ref": task["resource_ref"],
                    "selection_basis": reason,
                    "action": "REVALIDATE_NATIVE_AFFORDANCE_BEFORE_ONE_EFFECT",
                    "execute_allowed": False,
                })
                continue
        deferred.append({"task_ref": ident, "mechanic_id": task["mechanic_id"],
                         "reason": reason, "retain_goal": True})
    personal = [{
        "member_key": row["member_key"],
        "wellbeing_gate": _need_state(row, solo=solo, yield_work=False),
        "discretionary_yield_gate": _need_state(row, solo=solo, yield_work=True),
    } for row in members]
    handoff = None
    if handoff_from is not None:
        # Unlike chores, household attention needs no task to justify a move.
        # The portrait order itself is the stable tie-breaker, not money yield.
        successor = _next_awake_portrait(members, handoff_from)
        if successor is not None:
            queued_task = next(
                (row["task_ref"] for row in allocations
                 if row["member_key"] == successor["member_key"]), None
            )
            handoff = {
                "from_member_key": handoff_from,
                "to_member_key": successor["member_key"],
                "task_ref": queued_task,
                "capture_ref": observation["capture_ref"],
                "reason": handoff_cause,
                "need_keys": sorted(successor["needs"]),
                "action": "SELECT_PORTRAIT_THEN_REOBSERVE_ACTOR_AND_NEEDS",
                "new_capture_required": True,
                "execute_allowed": False,
            }
    return {
        "schema": "betterinstincts.household-economy-plan/v1",
        "portrait_handoff": handoff,
        "work_tone": work_tone,
        "scope_id": scope_id,
        "capture_ref": observation["capture_ref"],
        "mode": "SOLO_WELLBEING_FIRST" if solo else "COOPERATIVE_HOUSEHOLD",
        "gate": ("SOLO_WELLBEING_FIRST" if solo and not allocations else
                 "COOPERATIVE_ALLOCATION_READY" if allocations and not solo else
                 "SOLO_RESPONSIBILITY_READY" if allocations else
                 "HOUSEHOLD_REOBSERVE_OR_WELLBEING_FIRST"),
        "personal_wellbeing": personal,
        "allocations": allocations,
        "deferred": deferred,
        "assigned_count": len(allocations),
        "workload_claims": sorted(allocated),
        "execute_allowed": False,
        "estimated_income": None,
        "expected_game_yield": None,
        "proof_ceiling": PROOF,
    }
