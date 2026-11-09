"""Read-only routing for Sims 4 top-left Discovery Quest HUD.

Scoring Simoleons and Navigating Needs retain their established domain owners.
You and Your Phone requires exact visible quest goals and phone affordances;
never auto-sends a message, buys, travels, calls, or clicks a guessed menu.
"""
from __future__ import annotations

import math
import time
from collections.abc import Mapping

from betterinstincts.navigating_needs import plan_navigating_needs
from betterinstincts.scenario_goals import plan_scenario_goals

SCHEMA = "betterinstincts.discovery-hud/v1"
QUESTS = {
    "Scoring Simoleons": "scoring_simoleons",
    "Navigating Needs": "navigating_needs",
    "You and Your Phone": "you_and_your_phone",
    "Skillful Sims": "skillful_sims",
    "Lifelong Aspirations": "lifelong_aspirations",
    "Always on the Move": "always_on_the_move",
}
MAX_GOALS = 12
MAX_MENU = 24


class DiscoveryHudError(ValueError):
    pass


def _ref(value: object) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= 120 and all(
        c.isalnum() or c in "_:.-" for c in value
    )


def evaluate_discovery_hud(
    observation: Mapping, *, capture_ref: str,
    needs: Mapping[str, float] | None = None, now: float | None = None,
) -> dict:
    if not isinstance(observation, Mapping) or observation.get("schema") != SCHEMA:
        raise DiscoveryHudError("DISCOVERY_HUD_SCHEMA_INVALID")
    if not _ref(observation.get("sim_ref")):
        raise DiscoveryHudError("DISCOVERY_SIM_INVALID")
    raw = observation.get("quest_label")
    if not isinstance(raw, str) or len(raw) > 120:
        raise DiscoveryHudError("DISCOVERY_QUEST_LABEL_INVALID")
    quest = QUESTS.get(raw.strip())
    result = {
        "schema": "betterinstincts.discovery-hud-result/v1",
        "sim_ref": observation["sim_ref"], "capture_ref": capture_ref,
        "quest": quest, "state": "INSPECT_QUEST_PANEL", "domain_plan": None,
        "next_action": None, "execute_allowed": False, "control_permit": None,
        "proof_ceiling": "OFFLINE_DISCOVERY_ROUTING_NOT_GAME_HUD_PROOF",
    }

    def finish(state: str) -> dict:
        result["state"] = state
        return result

    goals = observation.get("incomplete_goals", [])
    queue = observation.get("queue_labels", [])
    phone = observation.get("phone_actions", [])
    if (not isinstance(goals, list) or len(goals) > MAX_GOALS
            or any(not isinstance(x, str) or not x.strip() or len(x) > 120 for x in goals)
            or not isinstance(queue, list) or len(queue) > 24
            or any(not isinstance(x, str) or len(x) > 120 for x in queue)
            or not isinstance(phone, list) or len(phone) > MAX_MENU):
        raise DiscoveryHudError("DISCOVERY_HUD_INPUT_INVALID")
    timestamp = observation.get("observed_at_unix")
    instant = time.time() if now is None else now
    if (type(timestamp) not in (int, float) or not math.isfinite(timestamp)
            or type(instant) not in (int, float) or not math.isfinite(instant)
            or not 0 <= instant - timestamp <= 180
            or observation.get("capture_ref") != capture_ref
            or observation.get("source") != "DISCOVERY_QUEST"
            or observation.get("mode") != "LIVE"
            or observation.get("panel_verified") is not True
            or observation.get("scene_verified") is not True
            or observation.get("selection_verified") is not True
            or observation.get("selected_sim_ref") != observation["sim_ref"]
            or not _ref(observation.get("panel_proof_ref"))
            or not _ref(observation.get("scene_proof_ref"))
            or not _ref(observation.get("selection_proof_ref"))):
        return finish("REOBSERVE_TOP_LEFT_PANEL")
    if quest is None:
        return finish("UNRECOGNIZED_DISCOVERY_QUEST")
    if observation.get("player_active") is True:
        return finish("PLAYER_FIRST")
    if not goals:
        return finish("NO_INCOMPLETE_QUEST_GOALS")
    if quest == "navigating_needs":
        if needs is None:
            return finish("INSPECT_NEEDS_FOR_QUEST")
        plan = plan_navigating_needs(goals, needs, queue=queue, capture_ref=capture_ref)
        result["domain_plan"] = plan
        return finish("ROUTE_EXISTING_NAVIGATING_NEEDS")
    if quest == "scoring_simoleons":
        plan = plan_scenario_goals(goals, queue=queue, capture_ref=capture_ref)
        result["domain_plan"] = plan
        return finish("ROUTE_EXISTING_SCORING_SIMOLEONS")
    if quest == "you_and_your_phone":
        # No assumption about exact phone quest steps. An observed enabled
        # affordance must cite a matching specific incomplete goal/action.
        for goal in goals:
            for action in phone:
                if not isinstance(action, Mapping):
                    raise DiscoveryHudError("PHONE_ACTION_NOT_OBJECT")
                if (action.get("goal_label") == goal
                        and action.get("available") is True
                        and action.get("capture_ref") == capture_ref
                        and action.get("sim_ref") == observation["sim_ref"]
                        and _ref(action.get("action_id"))
                        and _ref(action.get("menu_observation_ref"))):
                    result["next_action"] = {
                        "action_id": action["action_id"],
                        "goal_label": goal,
                        "menu_observation_ref": action["menu_observation_ref"],
                        "requires": ["FRESH_PHONE_MENU", "EXACT_SIM",
                                     "INDEPENDENT_SCREEN_ADMIT", "EXPLICIT_ACTION_CONSENT"],
                    }
                    return finish("PHONE_GOAL_AFFORDANCE_CANDIDATE")
        return finish("INSPECT_PHONE_AFFORDANCES")
    return finish("KNOWN_DISCOVERY_QUEST_NEEDS_OWN_MICROSYSTEM")
