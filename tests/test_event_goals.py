import unittest

from betterinstincts.event_balance import evaluate_event_turn
from betterinstincts.event_goals import (
    EventGoalsError,
    load_contract,
    plan_event_goals,
    resolve_goal_id,
)
from betterinstincts.host_stack import evaluate_turn

SIX_OK = {
    "hunger": 0.6,
    "bladder": 0.45,
    "energy": 0.7,
    "hygiene": 0.7,
    "fun": 0.25,
    "social": 0.8,
}


class EventGoalsTests(unittest.TestCase):
    def test_contract_lounge_priority(self):
        cfg = load_contract()
        self.assertEqual(cfg["default_profile"], "lounge_party")
        self.assertIn("drink", cfg["goals"])
        self.assertEqual(
            cfg["profiles"]["lounge_party"]["goal_priority"][0],
            "drink",
        )

    def test_alias_resolution(self):
        self.assertEqual(resolve_goal_id("Be Silly"), "be_silly")
        self.assertEqual(resolve_goal_id("friendly_greet_or_socialize"), "friendly_socialize")
        self.assertEqual(resolve_goal_id("Tell a Joke"), "tell_jokes")
        self.assertIsNone(resolve_goal_id("woohoo_mystery"))

    def test_plan_prioritizes_drink_with_concrete_actions(self):
        plan = plan_event_goals(
            ["be_silly", "drink", "talk about food"],
            event_profile="lounge_party",
            queue=["Friendly Greet"],
        )
        self.assertEqual(plan["next_goal"], "drink")
        self.assertEqual(plan["primary_route"], "ORDER_DRINK_FROM_BAR")
        self.assertTrue(plan["next_actions"])
        self.assertIn("QUEUE_DOES_NOT_SATISFY_EVENT_GOALS", plan["findings"])
        self.assertEqual(plan["goals_incomplete"][0], "drink")

    def test_queue_match_covers_joke_goal(self):
        plan = plan_event_goals(
            ["tell_jokes", "drink"],
            queue=["Tell a Joke"],
        )
        self.assertIn("tell_jokes", plan["goals_covered_by_queue"])
        self.assertEqual(plan["next_goal"], "drink")

    def test_outdoor_prefix_grounds_before_goal(self):
        plan = plan_event_goals(
            ["be_silly"],
            outdoor_social_prefix=True,
        )
        self.assertEqual(plan["primary_route"], "SIT_AND_CHAT_HERE_INDOOR")
        self.assertIn("SPAM_OUTDOOR_GREET_HOPING_GOALS_TICK", plan["findings"])

    def test_event_balance_attaches_goal_plan(self):
        report = evaluate_event_turn(
            SIX_OK,
            event_active=True,
            event_goals_incomplete=["drink", "be_silly"],
            outdoor_social_prefix=False,
            indoor_capacity_observed=True,
            queue=["Chat"],
        )
        self.assertEqual(report["gate"], "EVENT_FUN_VIA_GOALS")
        self.assertIsNotNone(report["goal_plan"])
        self.assertEqual(report["goal_plan"]["next_goal"], "drink")
        self.assertEqual(report["preferred_routes"][0], "ORDER_DRINK_FROM_BAR")

    def test_host_stack_exposes_next_actions(self):
        result = evaluate_turn(
            SIX_OK,
            event_active=True,
            event_goals_incomplete=["tell_jokes", "friendly_socialize"],
            outdoor_social_prefix=False,
            viewport={"state": "VIEWPORT_OK"},
        )
        self.assertEqual(result["next_gate"], "EVENT_FUN_VIA_GOALS")
        self.assertEqual(result["fallback"]["next_goal"], "tell_jokes")
        self.assertTrue(result["fallback"]["next_actions"])
        self.assertEqual(result["fallback"]["next_actions"][0]["id"], "TELL_A_JOKE")

    def test_unknown_profile_fails_closed(self):
        with self.assertRaises(EventGoalsError):
            plan_event_goals(["drink"], event_profile="career_award_gala")


if __name__ == "__main__":
    unittest.main()
