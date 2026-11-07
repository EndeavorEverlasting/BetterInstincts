import unittest

from betterinstincts.host_listener import activate, deactivate, tick
from betterinstincts.host_stack import evaluate_turn
from betterinstincts.navigating_needs import (
    NavigatingNeedsError,
    evaluate_navigating_needs_turn,
    load_contract,
    order_goals_by_motive_urgency,
    plan_navigating_needs,
    resolve_goal_id,
)
from betterinstincts.player_presence import PresenceProbe

SIX_OK = {
    "hunger": 0.6,
    "bladder": 0.45,
    "energy": 0.7,
    "hygiene": 0.7,
    "fun": 0.25,
    "social": 0.8,
}
HUNGER_CRITICAL = {
    "hunger": 0.05,
    "bladder": 0.9,
    "energy": 0.9,
    "hygiene": 0.9,
    "fun": 0.2,
    "social": 0.2,
}
BLADDER_CRITICAL_FUN_PANEL = {
    "hunger": 0.8,
    "bladder": 0.1,
    "energy": 0.8,
    "hygiene": 0.8,
    "fun": 0.2,
    "social": 0.8,
}


class NavigatingNeedsTests(unittest.TestCase):
    def test_contract_and_aliases(self):
        cfg = load_contract()
        self.assertEqual(cfg["default_profile"], "navigating_needs")
        self.assertEqual(len(cfg["goals"]), 6)
        self.assertIn("NAVIGATING_NEEDS_TANDEM", cfg["call_stack_gates"])
        self.assertEqual(resolve_goal_id("Cook a Meal or Have a Quick Meal"), "cook_or_quick_meal")
        self.assertEqual(resolve_goal_id("Use a toilet"), "use_toilet")
        self.assertEqual(resolve_goal_id("Read a book or watch TV"), "read_or_watch_tv")
        self.assertEqual(cfg["goals"]["cook_or_quick_meal"]["linked_need"], "hunger")

    def test_urgency_orders_hunger_before_fun(self):
        ordered = order_goals_by_motive_urgency(
            ["read_or_watch_tv", "cook_or_quick_meal"],
            HUNGER_CRITICAL,
            fallback_priority=[
                "use_toilet",
                "cook_or_quick_meal",
                "take_nap",
                "shower_or_bath",
                "read_or_watch_tv",
                "socialize",
            ],
        )
        self.assertEqual(ordered[0], "cook_or_quick_meal")
        plan = plan_navigating_needs(
            ["Read a book or watch TV", "Cook a Meal or Have a Quick Meal"],
            HUNGER_CRITICAL,
        )
        self.assertEqual(plan["next_goal"], "cook_or_quick_meal")
        self.assertEqual(plan["next_need"], "hunger")
        self.assertEqual(plan["primary_route"], "QUICK_MEAL_OR_COOK")

    def test_tandem_gate_and_build_yield(self):
        report = evaluate_navigating_needs_turn(
            HUNGER_CRITICAL,
            navigating_needs_active=True,
            navigating_needs_incomplete=[
                "Cook a Meal or Have a Quick Meal",
                "Read a book or watch TV",
            ],
        )
        self.assertEqual(report["gate"], "NAVIGATING_NEEDS_TANDEM")
        self.assertIn("TANDEM_WITH_NAVIGATING_NEEDS_PANEL", report["findings"])
        build = evaluate_navigating_needs_turn(
            HUNGER_CRITICAL,
            navigating_needs_active=True,
            navigating_needs_incomplete=["Cook a Meal or Have a Quick Meal"],
            build_or_buy_mode=True,
        )
        self.assertEqual(build["gate"], "BUILD_OR_BUY_YIELD")

    def test_uncovered_urgent_falls_through(self):
        report = evaluate_navigating_needs_turn(
            BLADDER_CRITICAL_FUN_PANEL,
            navigating_needs_active=True,
            navigating_needs_incomplete=["Read a book or watch TV", "Socialize with another Sim"],
        )
        self.assertEqual(report["gate"], "URGENT_NEED_WITHOUT_PANEL_GOAL")
        self.assertIn("bladder", report["goal_plan"]["uncovered_urgent_motives"])

    def test_school_outranks(self):
        report = evaluate_navigating_needs_turn(
            SIX_OK,
            navigating_needs_active=True,
            navigating_needs_incomplete=["Take a nap"],
            school_day_active=True,
        )
        self.assertEqual(report["gate"], "SCHOOL_DAY_OUTRANKS_NAVIGATING_NEEDS")

    def test_host_stack_tandem_before_scenario(self):
        result = evaluate_turn(
            HUNGER_CRITICAL,
            navigating_needs_active=True,
            navigating_needs_incomplete=["Cook a Meal or Have a Quick Meal"],
            scenario_active=True,
            scenario_goals_incomplete=["Earn § 250"],
            available_objects=("fridge", "toilet", "bed", "shower", "tv", "phone"),
            viewport={"state": "VIEWPORT_OK"},
        )
        self.assertEqual(result["next_gate"], "NAVIGATING_NEEDS_TANDEM")
        self.assertEqual(result["fallback"]["next_goal"], "cook_or_quick_meal")
        self.assertEqual(result["fallback"]["primary_route"], "QUICK_MEAL_OR_COOK")
        self.assertIsNotNone(result["navigating_needs"])

    def test_host_stack_uncovered_urgent_uses_instincts(self):
        result = evaluate_turn(
            BLADDER_CRITICAL_FUN_PANEL,
            navigating_needs_active=True,
            navigating_needs_incomplete=["Read a book or watch TV"],
            available_objects=("fridge", "toilet", "bed", "shower", "tv", "phone"),
            viewport={"state": "VIEWPORT_OK"},
        )
        self.assertEqual(result["next_gate"], "EXECUTE_INSTINCTS_PLAN")
        self.assertEqual(result["navigating_needs"]["gate"], "URGENT_NEED_WITHOUT_PANEL_GOAL")
        self.assertEqual(result["instincts"]["next_need"], "bladder")

    def test_host_stack_build_yield(self):
        result = evaluate_turn(
            HUNGER_CRITICAL,
            navigating_needs_active=True,
            navigating_needs_incomplete=["Cook a Meal or Have a Quick Meal"],
            build_or_buy_mode=True,
            viewport={"state": "VIEWPORT_OK"},
        )
        self.assertEqual(result["next_gate"], "BUILD_OR_BUY_YIELD")
        self.assertEqual(
            result["fallback"]["forbidden"],
            ["FORCE_F1", "NEEDS_OBJECT_CLICK", "RESUME"],
        )

    def test_listener_tick_passes_fields(self):
        sid = "testnavneeds01"
        activate(sid, note="unit")
        try:
            receipt = tick(
                sid,
                {
                    "schema": "betterinstincts.host-listener.observation/v1",
                    "needs": HUNGER_CRITICAL,
                    "queue": [],
                    "location_kind": "home",
                    "objects_on_current_lot": True,
                    "available_objects": ["fridge", "toilet", "bed", "shower", "tv", "phone"],
                    "capture_ref": "capture:navigating-needs-listener",
                    "navigating_needs_active": True,
                    "navigating_needs_incomplete": ["Cook a Meal or Have a Quick Meal"],
                    "emotion": "FINE",
                    "moodlets": [],
                    "traits": [],
                    "whims": [],
                },
                presence_probe=PresenceProbe(False, False, last_input_age_ms=9000),
            )
            stack = receipt["host_stack"]
            self.assertEqual(stack["next_gate"], "NAVIGATING_NEEDS_TANDEM")
            self.assertIsNotNone(stack.get("navigating_needs"))
        finally:
            deactivate(sid)

    def test_unknown_goal_rejected_softly(self):
        plan = plan_navigating_needs(["Totally Fake Goal"], SIX_OK)
        self.assertIn("UNKNOWN_GOAL_LABEL", plan["findings"])
        self.assertEqual(plan["goals_incomplete"], [])
        with self.assertRaises(NavigatingNeedsError):
            plan_navigating_needs(["Use a toilet"], {"hunger": 0.5})


if __name__ == "__main__":
    unittest.main()
