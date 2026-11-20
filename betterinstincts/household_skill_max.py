"""Scope and verify a selected household skill through the optional native port."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from betterinstincts.player_learning import TOKEN
from betterinstincts.portrait_handoff import Selection, _matches, _roster, choose_selection

PORTS = ("read_household_skill", "submit_skill_max_if_current", "read_skill_max_outcome")
SCHEMA = "betterinstincts.household-skill-max/v1"
RECONCILE = "SKILL_MAX_AWAITING_READBACK"
COMPLETE = "HOUSEHOLD_SKILL_MAX_VERIFIED"


@dataclass(frozen=True)
class Turn:
    profile: str
    revision: int
    skill: str
    save: str
    roster: tuple
    actor: str
    level: int
    cap: int
    selection: Selection | None = None

    def identity(self, frame):
        return frame.scope()[:3] + (self.save, "SKILL_MAX", self.skill, self.actor,
                                   self.profile, self.revision)


@dataclass(frozen=True)
class Attempt:
    turn: Turn
    first_capture: str
    dispatch: object


def choose_turn(frame, packet, profile):
    """Use per-Sim native caps and the existing skill-first portrait order."""
    skill = profile["launch"]["household_skill"]
    if (not isinstance(packet, Mapping) or packet.get("schema") != SCHEMA
            or not _matches(TOKEN, frame.save_ref)
            or packet.get("save_kind") != "LAB_DISPOSABLE"
            or any(packet.get(key) != value for key, value in (
                ("game_build", frame.game_build), ("run", frame.run), ("save", frame.save_ref),
                ("household", frame.household), ("capture", frame.capture),
                ("selected", frame.actor), ("skill", skill),
            ))):
        return "SKILL_MAX_EVIDENCE_UNQUALIFIED", None
    roster = _roster(packet.get("roster"))
    members = packet.get("members")
    if (frame.actor not in roster or not isinstance(members, Mapping)
            or set(members) != set(roster)):
        return "SKILL_MAX_EVIDENCE_UNQUALIFIED", None
    states, levels = {}, {}
    for actor in roster:
        row = members[actor]
        if not isinstance(row, Mapping):
            return "SKILL_MAX_EVIDENCE_UNQUALIFIED", None
        if row.get("eligible") is False:
            states[actor] = "UNAVAILABLE"
            continue
        level, cap = row.get("level"), row.get("cap")
        if (row.get("eligible") is not True or type(level) is not int
                or type(cap) is not int or not 0 <= level <= cap <= 100 or cap == 0):
            states[actor] = "WAITING"
            continue
        states[actor] = "COVERED" if level == cap else "READY"
        levels[actor] = (level, cap)
    if "READY" not in states.values() and "WAITING" not in states.values():
        return (COMPLETE if levels else "NO_ELIGIBLE_SKILL_PORTRAITS"), None
    state, selection = choose_selection(frame, {
        **packet, "purpose": "SKILL", "goal": "skill-max-" + skill, "members": states,
    })
    if not selection and state != "PORTRAIT_ALREADY_SELECTED":
        return state, None
    target = selection.target if selection else frame.actor
    if selection:
        selection = replace(selection, purpose="SKILL_MAX")
    return "SKILL_MAX_READY", Turn(profile["profile_id"], profile["revision"], skill,
                                   frame.save_ref, roster, target, *levels[target], selection)


def can_read_outcome(frame, attempt):
    sent, turn = attempt.dispatch, attempt.turn
    return (frame.scope()[:3] == sent.scope()[:3] and frame.save_ref == turn.save
            and type(frame.input_generation) is int and frame.input_generation >= sent.input_generation
            and frame.capture not in (attempt.first_capture, sent.capture)
            and frame.observed_at > sent.observed_at)


def outcome_state(frame, attempt, outcome):
    """An acknowledgement, wrong Sim or stale cap cannot complete a skill turn."""
    sent, turn = attempt.dispatch, attempt.turn
    if (not can_read_outcome(frame, attempt) or not isinstance(outcome, Mapping)
            or _roster(outcome.get("roster")) != turn.roster
            or any(outcome.get(key) != value for key, value in (
                ("capture", frame.capture), ("request_capture", sent.capture), ("save", turn.save),
                ("actor", turn.actor), ("skill", turn.skill), ("cap", turn.cap),
            )) or type(outcome.get("cap")) is not int or type(outcome.get("level")) is not int):
        return RECONCILE
    if outcome.get("status") == "APPLIED" and outcome["level"] == turn.cap:
        return "SKILL_MAX_VERIFIED"
    if outcome.get("status") == "NO_EFFECT" and outcome["level"] == turn.level:
        return "SKILL_MAX_NO_EFFECT"
    return RECONCILE
