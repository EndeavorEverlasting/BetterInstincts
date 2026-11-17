"""Select one verified household member through the installed native adapter."""
from __future__ import annotations

from dataclasses import dataclass
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
            or not _matches(TOKEN, packet.get("save")) or not _matches(TOKEN, packet.get("goal"))):
        return "PORTRAIT_EVIDENCE_UNQUALIFIED", None
    roster = _roster(packet.get("roster"))
    members = packet.get("members")
    purpose = packet.get("purpose")
    if (frame.actor not in roster or not isinstance(members, Mapping) or set(members) != set(roster)
            or purpose not in ("NEEDS", "SKILL", "UPGRADE_PARTS", "TARGET")
            or not all(state in STATES for state in members.values())):
        return "PORTRAIT_EVIDENCE_UNQUALIFIED", None
    if packet.get("safe_to_leave") is not True:
        return "PORTRAIT_CURRENT_EFFECT_PENDING", None

    index = roster.index(frame.actor)
    rotation = roster[index:] + roster[:index]
    if purpose == "TARGET":
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
    return "PORTRAIT_SWITCH_READY", Selection(packet["save"], roster, packet["goal"],
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
