"""Rank independent domain proposals against one observed household queue snapshot."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping

from betterinstincts.player_learning import ACTOR, TOKEN
from betterinstincts.portrait_handoff import Selection

SCHEMA = "betterinstincts.microsystem-handoff/v1"
PRIORITY = ("NEEDS", "CAREER", "CONTINGENCIES", "SKILLS")
MAX_MEMBERS = 16
MAX_QUEUE = 16
MAX_OPTIONS = 16
PORTS = ("read_microsystem_handoff", "submit_microsystem_if_current", "read_microsystem_outcome")


@dataclass(frozen=True)
class QueueDecision:
    actor: str
    domain: str
    work: str
    proposal: str
    queue_ref: str
    before_slot: str | None
    selection: Selection | None = None

    def identity(self, frame):
        return (frame.scope()[:3] + (self.actor,), "MICROSYSTEM", frame.save_ref, self.work)


def _token(value, pattern=TOKEN):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _positive(value, limit):
    return type(value) in (int, float) and 0 < value <= limit and isfinite(value)


def _queue(frame, member):
    rows = member.get("queue")
    free = member.get("slots_free")
    if (member.get("capture") != frame.capture or member.get("player_queue") is not False
            or member.get("queue_verified") is not True or not _token(member.get("queue_ref"))
            or not isinstance(rows, (list, tuple)) or len(rows) > MAX_QUEUE
            or type(free) is not int or not 0 <= free <= MAX_QUEUE - len(rows)):
        return "QUEUE_UNQUALIFIED"
    slots = set()
    for index, row in enumerate(rows):
        if (not isinstance(row, Mapping) or not _token(row.get("slot"))
                or row["slot"] in slots or row.get("origin") not in ("SIM_AUTONOMY", "BETTERINSTINCTS")
                or row.get("state") not in ("PENDING", "RUNNING")
                or (row["state"] == "RUNNING" and index != 0)
                or not _token(row.get("work"))
                or (row.get("origin") == "BETTERINSTINCTS" and row.get("domain") not in PRIORITY)):
            return "QUEUE_UNQUALIFIED"
        slots.add(row["slot"])
    return "QUEUE_READY" if free else "QUEUE_FULL"


def _next_for_member(frame, actor, member, roster, attempted):
    if not isinstance(member, Mapping) or member.get("available") is not True:
        return "PORTRAIT_UNAVAILABLE", None
    gate = _queue(frame, member)
    if gate != "QUEUE_READY":
        return gate, None
    lanes = member.get("lanes")
    if not isinstance(lanes, Mapping):
        return "LANE_REOBSERVE", None
    rows = member["queue"]
    covered = {row["work"] for row in rows}
    for tier, domain in enumerate(PRIORITY):
        lane = lanes.get(domain)
        if not isinstance(lane, Mapping) or lane.get("capture") != frame.capture:
            return "LANE_REOBSERVE", None
        state = lane.get("state")
        if state == "CLEAR":
            continue
        # Block this portrait if the higher tier is undecided. Other portraits
        # have their own evidence and can still make progress this callback.
        if state != "READY":
            return "LANE_WAITING", None
        options = lane.get("options")
        if not isinstance(options, (list, tuple)) or not 1 <= len(options) <= MAX_OPTIONS:
            return "LANE_REOBSERVE", None
        candidates = []
        seen = set()
        before_slot = None
        # Insertion can pass only a contiguous suffix of our lower-priority
        # pending actions. Running and vanilla interactions keep their places.
        for row in reversed(rows):
            if (row["origin"] != "BETTERINSTINCTS" or row["state"] != "PENDING"
                    or PRIORITY.index(row["domain"]) <= tier):
                break
            before_slot = row["slot"]
        for option in options:
            if (not isinstance(option, Mapping) or not _token(option.get("work"))
                    or not _token(option.get("proposal"))
                    or option["work"] in seen
                    or not _positive(option.get("urgency"), 1)
                    or not _positive(option.get("benefit"), 1)
                    or not _positive(option.get("minutes"), 1440)
                    or option["minutes"] < 1):
                return "LANE_REOBSERVE", None
            seen.add(option["work"])
            if option["work"] in covered:
                continue
            selection = None
            if actor != frame.actor:
                selection = Selection(frame.save_ref, tuple(roster), option["work"],
                                      "MICROSYSTEM", frame.actor, actor)
                if selection.identity(frame) in attempted:
                    continue
            decision = QueueDecision(actor, domain, option["work"], option["proposal"],
                                     member["queue_ref"], before_slot, selection)
            if decision.identity(frame) in attempted:
                continue
            rate = option["urgency"] * option["benefit"] / option["minutes"]
            candidates.append((-rate, option["work"], decision))
        if candidates:
            negative_rate, _, winner = min(candidates, key=lambda entry: entry[:2])
            return "CANDIDATE", (tier, negative_rate, winner)
        if not seen <= covered:
            return "WORK_ALREADY_ATTEMPTED", None
        # A known queued action covers this work. Re-evaluate the next tier.
    return "NO_OPEN_WORK", None


def decide(frame, packet, *, attempted=()):
    """Return one ranked queue or portrait decision and per-portrait dispositions."""
    if (not isinstance(packet, Mapping) or packet.get("schema") != SCHEMA
            or not _token(frame.save_ref) or any(packet.get(key) != value for key, value in (
                ("game_build", frame.game_build), ("run", frame.run), ("save", frame.save_ref),
                ("household", frame.household), ("capture", frame.capture), ("selected", frame.actor),
            ))):
        return "MICROSYSTEM_SCOPE_UNQUALIFIED", None, {}
    roster = packet.get("roster")
    members = packet.get("members")
    if (not isinstance(roster, (list, tuple)) or not 1 <= len(roster) <= MAX_MEMBERS
            or not all(_token(actor, ACTOR) for actor in roster) or len(set(roster)) != len(roster)
            or frame.actor not in roster or not isinstance(members, Mapping)
            or not set(members) <= set(roster)):
        return "MICROSYSTEM_ROSTER_UNQUALIFIED", None, {}
    dispositions = {}
    options = []
    index = roster.index(frame.actor)
    for offset, actor in enumerate(roster[index:] + roster[:index]):
        if actor != frame.actor and packet.get("safe_to_leave") is not True:
            dispositions[actor] = "CURRENT_PORTRAIT_HELD"
            continue
        state, candidate = _next_for_member(frame, actor, members.get(actor), roster, attempted)
        dispositions[actor] = state
        if candidate is not None:
            tier, negative_rate, decision = candidate
            options.append((tier, negative_rate, offset, decision))
    if not options:
        return "MICROSYSTEM_NO_ADMISSIBLE_WORK", None, dispositions
    _, _, _, best = min(options, key=lambda entry: entry[:3])
    return "MICROSYSTEM_READY", best, dispositions


def outcome_state(decision, *, capture, request, outcome):
    """Correlate the native request and independent queue or effect readback."""
    waiting = "MICROSYSTEM_QUEUE_RECONCILIATION"
    if not isinstance(outcome, Mapping) or any(
        outcome.get(key) != value for key, value in (
            ("capture", capture), ("request_capture", request), ("actor", decision.actor),
            ("work", decision.work), ("proposal", decision.proposal),
        )
    ) or not _token(outcome.get("readback_ref")):
        return waiting
    state = outcome.get("status")
    if state == "QUEUED" and _token(outcome.get("slot")):
        return "MICROSYSTEM_QUEUE_CONFIRMED"
    if state == "COMPLETED" and _token(outcome.get("effect_ref")):
        return "MICROSYSTEM_EFFECT_CONFIRMED"
    if state == "NO_EFFECT":
        return "MICROSYSTEM_QUEUE_NO_EFFECT"
    return waiting
