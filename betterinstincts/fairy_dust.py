"""Plan Fairy Dust acquisition from supplied game observations."""
from __future__ import annotations

import re
from typing import Mapping

from betterinstincts.player_learning import ACTOR, TOKEN

PACK = "Enchanted by Nature"
DAY_MINUTES = 24 * 60
SHAKE = "SHAKE_FOR_FAIRY_DUST"
ASK = "ASK_FOR_FAIRY_DUST"
HOME_USE = ("SLEEP_IN_FAIRY_HOME", "REST_IN_FAIRY_HOME")
OBJECT = re.compile(r"object:[A-Za-z0-9_-]{3,64}")


def _matches(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _count(value):
    return type(value) is int and value >= 0


def _proposal(interaction, allowed, target, capture):
    if (isinstance(interaction, Mapping) and interaction.get("available") is True
            and interaction.get("capture") == capture
            and interaction.get("action") in allowed
            and _matches(TOKEN, interaction.get("opportunity"))):
        return {"action": interaction["action"], "target": target,
                "opportunity": interaction["opportunity"]}
    return None


def plan_fairy_dust(frame, observation, *, attempted_opportunities=()):
    """Return one proposal or a recheck hint for an explicit inventory goal."""
    if observation is None:
        return {"state": "NO_DUST_GOAL"}
    if (not isinstance(observation, Mapping) or observation.get("scope") != frame.scope()
            or observation.get("capture") != frame.capture):
        return {"state": "REOBSERVE_DUST_SCOPE"}
    if observation.get("pack") != PACK:
        return {"state": "DUST_PACK_UNVERIFIED"}
    count, goal = observation.get("dust_count"), observation.get("goal_count")
    if not _count(count) or not _count(goal) or goal == 0:
        return {"state": "DUST_INVENTORY_OR_GOAL_UNVERIFIED"}
    if count >= goal:
        return {"state": "DUST_GOAL_MET"}
    if frame.playing is not True:
        return {"state": "WAIT_FOR_GAME_TIME"}
    if observation.get("needs_safe") is not True:
        return {"state": "NEEDS_FIRST"}

    home = observation.get("home")
    check = target = None
    shake = None
    candidates = []
    if (isinstance(home, Mapping) and _matches(OBJECT, home.get("target"))
            and home.get("on_actor_lot") is True and home.get("accessible") is True):
        target = home["target"]
        shake = home.get("shake")
        candidates.append(_proposal(shake, (SHAKE,), target, frame.capture))
        use = home.get("use")
        if (observation.get("actor_is_fairy") is True and isinstance(use, Mapping)
                and use.get("benefits_current_need") is True):
            candidates.append(_proposal(use, HOME_USE, target, frame.capture))
        check = home.get("last_empty_check_game_minute")

    npc = observation.get("npc")
    if (isinstance(npc, Mapping) and npc.get("npc_fairy") is True
            and npc.get("on_actor_lot") is True and npc.get("accessible") is True
            and _matches(ACTOR, npc.get("target")) and npc["target"] != frame.actor):
        candidates.append(_proposal(npc.get("ask"), (ASK,), npc["target"], frame.capture))

    for proposal in candidates:
        if proposal is not None and proposal["opportunity"] not in attempted_opportunities:
            return {"state": "DUST_PROPOSAL", "proposal": proposal, "before": count}

    # The latest observed empty state determines recheck cadence only.
    minute = observation.get("game_minute")
    check_is_current = _count(check) and _count(minute) and check <= minute < check + DAY_MINUTES
    if (not check_is_current and isinstance(shake, Mapping) and shake.get("capture") == frame.capture
            and shake.get("action") == SHAKE and shake.get("available") is False
            and shake.get("reason") == "NO_FAIRY_DUST" and _count(minute)):
        check = minute
    if _count(check) and _count(minute) and check <= minute < check + DAY_MINUTES:
        return {"state": "WAIT_FOR_HOME_RECHECK", "target": target,
                "recheck_game_minute": check + DAY_MINUTES}
    if any(candidates):
        return {"state": "DUPLICATE_NATIVE_PROPOSAL"}
    return {"state": "REOBSERVE_HOME_OR_FIND_FAIRY"}


def fairy_dust_outcome(frame, attempted, outcome):
    """Reconcile a single native attempt with a distinct inventory observation."""
    proposal = attempted["proposal"]
    if (not isinstance(outcome, Mapping) or attempted["scope"] != frame.scope()
            or frame.observed_at < attempted["observed_at"] or outcome.get("scope") != frame.scope()
            or outcome.get("capture") != frame.capture or frame.capture in attempted["admission_captures"]
            or outcome.get("proposal") != proposal):
        return "NATIVE_DISPATCH_RECONCILIATION"
    count = outcome.get("dust_count")
    attributed = outcome.get("attributed_dust_gain")
    if (not _count(count) or not _count(attributed)
            or count - attempted["before"] != attributed):
        return "NATIVE_DISPATCH_RECONCILIATION"
    if outcome.get("no_effect_verified") is True:
        if outcome.get("completed") is False and attributed == 0:
            return "DUST_NO_EFFECT_OBSERVED"
        return "NATIVE_DISPATCH_RECONCILIATION"
    if outcome.get("completed") is not True:
        return "NATIVE_DISPATCH_RECONCILIATION"
    if attributed:
        return "DUST_GAIN_OBSERVED"
    if proposal["action"] in HOME_USE:
        return "FAIRY_HOME_USED_RECHECK"
    return "DUST_NO_GAIN_OBSERVED"
