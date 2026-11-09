import unittest

from betterinstincts.host_listener import activate, deactivate, tick
from betterinstincts.host_stack import evaluate_turn
from betterinstincts.player_presence import PresenceProbe
from betterinstincts.scenario_goals import (
    ScenarioGoalsError,
    evaluate_scenario_turn,
    load_contract,
    plan_scenario_goals,
    resolve_goal_id,
)

SIX_OK = {
    "hunger": 0.6,
    "bladder": 0.45,
    "energy": 0.7,
    "hygiene": 0.7,
    "fun": 0.25,
    "social": 0.8,
}
CRITICAL = {
    "hunger": 0.05,
    "bladder": 0.9,
    "energy": 0.9,
    "hygiene": 0.9,
    "fun": 0.2,
    "social": 0.2,
}


class ScenarioGoalsTests(unittest.TestCase):
    def test_contract_scoring_priority(self):
        cfg = load_contract()
        self.assertEqual(cfg["default_profile"], "scoring_simoleons")
        self.assertEqual(
            cfg["profiles"]["scoring_simoleons"]["goal_priority"],
            ["earn_simoleons", "craft_object", "get_career"],
        )
        self.assertTrue(cfg["goals"]["get_career"]["horizon_deferred"])
        self.assertIn("SCENARIO_GOAL_PROGRESS", cfg["call_stack_gates"])
        self.assertIn("SCENARIO_CAREER_DEFERRED", cfg["call_stack_gates"])
        self.assertEqual(resolve_goal_id("Get a career"), "get_career")
        self.assertEqual(resolve_goal_id("Earn § 250"), "earn_simoleons")
        self.assertEqual(resolve_goal_id("Craft an Object"), "craft_object")

    def test_earn_over_career(self):
        plan = plan_scenario_goals(
            ["Get a career", "Earn § 250"],
            allow_career=False,
        )
        self.assertEqual(plan["next_goal"], "earn_simoleons")
        self.assertEqual(plan["primary_route"], "PAINT_AND_SELL")
        self.assertTrue(plan["career_horizon_blocked"])
        report = evaluate_scenario_turn(
            SIX_OK,
            scenario_active=True,
            scenario_goals_incomplete=["Get a career", "Earn § 250"],
        )
        self.assertEqual(report["gate"], "SCENARIO_GOAL_PROGRESS")
        self.assertEqual(report["goal_plan"]["next_goal"], "earn_simoleons")

    def test_career_deferred_horizon(self):
        report = evaluate_scenario_turn(
            SIX_OK,
            scenario_active=True,
            scenario_goals_incomplete=["Get a career"],
            allow_career=False,
        )
        self.assertEqual(report["gate"], "SCENARIO_CAREER_DEFERRED")
        self.assertIn("CAREER_DEFERRED_HORIZON", report["findings"])
        plan = plan_scenario_goals(["Get a career"], allow_career=True, needs_game_certified=True)
        self.assertIsNone(plan["next_goal"])
        plan_ok = plan_scenario_goals(
            ["Get a career"],
            allow_career=True,
            needs_game_certified=True,
            income_game_observed=True,
        )
        self.assertEqual(plan_ok["next_goal"], "get_career")

    def test_survival_and_school_outrank(self):
        surv = evaluate_scenario_turn(
            CRITICAL,
            scenario_active=True,
            scenario_goals_incomplete=["Earn § 250"],
        )
        self.assertEqual(surv["gate"], "SURVIVAL_NEEDS_CRITICAL")
        school = evaluate_scenario_turn(
            SIX_OK,
            scenario_active=True,
            scenario_goals_incomplete=["Earn § 250"],
            school_day_active=True,
        )
        self.assertEqual(school["gate"], "SCHOOL_DAY_OUTRANKS_SCENARIO")

    def test_host_stack_scenario_gate(self):
        result = evaluate_turn(
            SIX_OK,
            scenario_active=True,
            scenario_goals_incomplete=["Earn § 250", "Craft an Object"],
            viewport={"state": "VIEWPORT_OK"},
        )
        self.assertEqual(result["next_gate"], "SCENARIO_GOAL_PROGRESS")
        self.assertIsNotNone(result["scenario"])
        self.assertEqual(result["fallback"]["next_goal"], "earn_simoleons")

    def test_host_stack_school_before_scenario(self):
        result = evaluate_turn(
            SIX_OK,
            scenario_active=True,
            scenario_goals_incomplete=["Earn § 250"],
            school_day_active=True,
            school_goals_incomplete=["study_for_exams"],
            school_phase="morning_free_time",
            location_kind="school",
            viewport={"state": "VIEWPORT_OK"},
        )
        self.assertEqual(result["next_gate"], "SCHOOL_DAY_GOAL_PROGRESS")
        self.assertIsNotNone(result["scenario"])
        self.assertEqual(result["scenario"]["gate"], "SCHOOL_DAY_OUTRANKS_SCENARIO")

    def test_listener_tick_passes_scenario_fields(self):
        sid = "testscenario01"
        activate(sid, note="unit")
        try:
            receipt = tick(
                sid,
                {
                    "schema": "betterinstincts.host-listener.observation/v1",
                    "needs": SIX_OK,
                    "queue": [],
                    "location_kind": "home",
                    "objects_on_current_lot": True,
                    "capture_ref": "capture:scenario-listener",
                    "scenario_active": True,
                    "scenario_goals_incomplete": ["Earn § 250"],
                    "scenario_profile": "scoring_simoleons",
                    "emotion": "FINE",
                    "moodlets": [],
                    "traits": [],
                    "whims": [],
                },
                presence_probe=PresenceProbe(False, False, last_input_age_ms=19000),
            )
            stack = receipt["host_stack"]
            self.assertEqual(stack["next_gate"], "SCENARIO_GOAL_PROGRESS")
            self.assertIsNotNone(stack.get("scenario"))
        finally:
            deactivate(sid)

    def test_unknown_profile_fails_closed(self):
        with self.assertRaises(ScenarioGoalsError):
            plan_scenario_goals(["Earn § 250"], scenario_profile="unknown_mystery_profile")


if __name__ == "__main__":
    unittest.main()
