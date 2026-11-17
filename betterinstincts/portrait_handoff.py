"""Select one verified household member through the installed native adapter."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping

from betterinstincts.player_learning import ACTOR, TOKEN

PORTS = ("read_portrait_handoff", "submit_portrait_if_current", "read_portrait_outcome")
STATES = ("READY", "COVERED", "UNAVAILABLE", "WAITING")


def _matches(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _roster(items):
    if (isinstance(items, (list, tuple)) and 1 <= len(items) <= 16
            and all(_matches(ACTOR, item) for item in items)
            and len(set(items)) == len(items)):
        return tuple(items)
    return ()


def _income_target(frame, packet, roster):
    """Resolve a winning host turn using the adapter's observed identity binding."""
    turn = packet.get("income_turn")
    if (not isinstance(turn, Mapping)
            or turn.get("state") != "HOST_TURN_EVALUATED"
            or turn.get("capture_ref") != frame.capture
            or turn.get("next_gate") != "HOUSEHOLD_INCOME_PORTRAIT_READY"):
        return None, None
    report = turn.get("fallback")
    members = packet.get("income_member_keys")
    if (not isinstance(report, Mapping)
            or report.get("owner") != "betterinstincts/household_income.py"
            or report.get("state") != turn["next_gate"]
            or report.get("goal_id") != "household-earned-income"
            or report.get("capture_ref") != frame.capture
            or report.get("game_build") != frame.game_build
            or report.get("save_ref") != packet["save"]
            or report.get("scope_id") is None
            or report["scope_id"] != packet.get("income_scope_id")
            or report.get("execute_allowed") is not False
            or not isinstance(members, list) or len(members) != len(roster)
            or any(not isinstance(key, str) or not key or len(key) > 160 for key in members)
            or len(set(members)) != len(members)
            or members != report.get("member_keys")):
        return None, None
    step = report.get("next")
    if (not isinstance(step, Mapping) or step.get("capture_ref") != frame.capture
            or step.get("action") != "SELECT_PORTRAIT_THEN_REOBSERVE_ACTOR_AND_NEEDS"
            or step.get("from_member_key") != members[roster.index(frame.actor)]
            or step.get("to_member_key") not in members
            or step.get("execute_allowed") is not False
            or step.get("new_capture_required") is not True):
        return None, None
    task = step.get("task_ref")
    if not isinstance(task, str) or not 3 <= len(task) <= 160 or not task.isascii():
        return None, None
    target = roster[members.index(step["to_member_key"])]
    # Deduplicate this work unit across captures while allowing a later task
    # to select the same Sim again under the same household goal.
    return target, sha256(task.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Selection:
    save: str
    roster: tuple
    goal: str
    purpose: str
    source: str
    target: str


def choose_selection(frame, packet):
    """Resolve domain-owned readiness in the exact current household roster."""
    if packet is None:
        return "NO_PORTRAIT_GOAL", None
    if (not isinstance(packet, Mapping) or packet.get("capture") != frame.capture
            or packet.get("household") != frame.household or packet.get("selected") != frame.actor
            or not _matches(TOKEN, packet.get("save"))):
        return "PORTRAIT_EVIDENCE_UNQUALIFIED", None
    roster = _roster(packet.get("roster"))
    members = packet.get("members")
    purpose = packet.get("purpose")
    goal = packet.get("goal")
    if (frame.actor not in roster or not isinstance(members, Mapping) or set(members) != set(roster)
            or purpose not in ("NEEDS", "SKILL", "UPGRADE_PARTS", "TARGET", "INCOME")
            or (purpose != "INCOME" and not _matches(TOKEN, goal))
            or not all(state in STATES for state in members.values())):
        return "PORTRAIT_EVIDENCE_UNQUALIFIED", None
    if packet.get("safe_to_leave") is not True:
        return "PORTRAIT_CURRENT_EFFECT_PENDING", None

    index = roster.index(frame.actor)
    rotation = roster[index:] + roster[:index]
    if purpose == "INCOME":
        target, goal = _income_target(frame, packet, roster)
        if target is None:
            return "PORTRAIT_EVIDENCE_UNQUALIFIED", None
        if members[target] != "READY":
            return "PORTRAIT_TARGET_UNAVAILABLE", None
    elif purpose == "TARGET":
        target = packet.get("target")
        if not _matches(ACTOR, target) or members.get(target) != "READY":
            return "PORTRAIT_TARGET_UNAVAILABLE", None
    elif purpose == "SKILL":
        # Finish this skill across the stable roster before advancing the owner.
        target = next((actor for actor in roster if members[actor] in ("READY", "WAITING")), None)
        if target is not None and members[target] == "WAITING":
            return "PORTRAIT_EARLIER_SKILL_PENDING", None
    else:
        if members[frame.actor] == "WAITING":
            return "PORTRAIT_CURRENT_REVIEW_PENDING", None
        ready = [actor for actor in rotation if members[actor] == "READY"]
        if purpose == "NEEDS":
            urgency = packet.get("urgency")
            if (not isinstance(urgency, Mapping) or set(urgency) != set(ready)
                    or any(type(rank) is not int or not 1 <= rank <= 3 for rank in urgency.values())):
                return "PORTRAIT_EVIDENCE_UNQUALIFIED", None
            if ready and ready[0] != frame.actor:
                # max preserves the observed circular order for equal urgency.
                ready = [max(ready, key=urgency.__getitem__)]
        target = ready[0] if ready else None
    if target is None:
        return "NO_ELIGIBLE_PORTRAIT", None
    if target == frame.actor:
        return "PORTRAIT_ALREADY_SELECTED", None
    return "PORTRAIT_SWITCH_READY", Selection(packet["save"], roster, goal,
                                              purpose, frame.actor, target)


@dataclass(frozen=True)
class Attempt:
    selection: Selection
    run: str
    household: str
    generation: int
    initial_capture: str
    submit_capture: str
    observed_at: float


def outcome_state(frame, attempt, outcome):
    """Require a correlated native receipt and independent selected-Sim readback."""
    selection = attempt.selection
    if (not isinstance(outcome, Mapping) or frame.run != attempt.run
            or frame.household != attempt.household
            or type(frame.input_generation) is not int
            or frame.input_generation < attempt.generation
            or frame.capture in (attempt.initial_capture, attempt.submit_capture)
            or frame.observed_at <= attempt.observed_at
            or outcome.get("capture") != frame.capture or outcome.get("save") != selection.save
            or _roster(outcome.get("roster")) != selection.roster
            or outcome.get("request_capture") != attempt.submit_capture
            or outcome.get("target") != selection.target):
        return "PORTRAIT_SWITCH_RECONCILE"
    state = outcome.get("status")
    if state not in ("APPLIED", "NO_EFFECT"):
        return "PORTRAIT_SWITCH_RECONCILE"
    expected = selection.target if state == "APPLIED" else selection.source
    if frame.input_generation != attempt.generation and frame.actor in selection.roster:
        return "PORTRAIT_SWITCH_SUPERSEDED"
    if frame.actor != expected:
        return "PORTRAIT_SWITCH_RECONCILE"
    return "PORTRAIT_SWITCH_CONFIRMED" if state == "APPLIED" else "PORTRAIT_SWITCH_NO_EFFECT"
