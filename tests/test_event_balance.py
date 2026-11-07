import unittest

from betterinstincts.event_balance import EventBalanceError, evaluate_event_turn, load_contract
from betterinstincts.host_stack import evaluate_turn

SIX_OK = {
    "hunger": 0.6,
    "bladder": 0.45,
    "energy": 0.5,
    "hygiene": 0.7,
    "fun": 0.4,
    "social": 0.8,
}
LIVE_SNAP = {
    "hunger": 0.55,
    "bladder": 0.35,
    "energy": 0.12,
    "hygiene": 0.4,
    "fun": 0.28,
    "social": 0.85,
}


class EventBalanceTests(unittest.TestCase):
    def test_contract_rca_and_stack(self):
        cfg = load_contract()
        self.assertEqual(cfg["rca"]["hypotheses"][0]["id"], "H1_VENUE_OUTDOOR_MEETUP")
        self.assertIn("EVENT_INDOOR_ROUTING", cfg["call_stack"]["order"])
        self.assertIn("HOMEWORK_HOLD_OR_SCHEDULE", cfg["call_stack"]["order"])

    def test_outdoor_social_with_indoor_capacity_optimizes(self):
        report = evaluate_event_turn(
            SIX_OK,
            event_active=True,
            event_goals_incomplete=["be_silly", "drink"],
            outdoor_social_prefix=True,
            indoor_capacity_observed=True,
        )
        self.assertEqual(report["gate"], "EVENT_INDOOR_ROUTING")
        self.assertEqual(report["action"], "CANCEL_OUTDOOR_WALK_SIT_AND_CHAT_HERE")
        self.assertEqual(report["primary_route"], "SIT_AND_CHAT_HERE_INDOOR")
        self.assertEqual(report["preferred_routes"][0], "SIT_AND_CHAT_HERE_INDOOR")
        self.assertIn("OUTDOOR_SOCIAL_DEFAULT_WITH_INDOOR_CAPACITY", report["findings"])
        self.assertIn("GREET_OR_GO_HERE_WITHOUT_SIT_AND_CHAT_GROUNDING", report["findings"])
        self.assertIn("H9_GREET_WITHOUT_SEAT_GROUNDING", report["rca_leading"])

    def test_contract_sit_and_chat_is_primary_route(self):
        cfg = load_contract()
        gate = cfg["call_stack"]["gates"]["EVENT_INDOOR_ROUTING"]
        self.assertEqual(gate["primary_route"], "SIT_AND_CHAT_HERE_INDOOR")
        self.assertEqual(gate["preferred_routes"][0], "SIT_AND_CHAT_HERE_INDOOR")
        self.assertIn("GREET_WITHOUT_SEAT_GROUNDING", gate["forbidden_routes"])

    def test_energy_critical_outranks_event_goals(self):
        report = evaluate_event_turn(
            LIVE_SNAP,
            event_active=True,
            event_goals_incomplete=["friendly_socialize", "be_silly"],
            outdoor_social_prefix=True,
            indoor_capacity_observed=True,
            homework_pending=True,
        )
        self.assertEqual(report["gate"], "SURVIVAL_NEEDS_CRITICAL")
        self.assertIn("energy", report["survival_critical"])

    def test_homework_holds_during_healthy_event(self):
        needs = {**SIX_OK, "energy": 0.7, "fun": 0.6}
        report = evaluate_event_turn(
            needs,
            event_active=True,
            event_goals_incomplete=[],
            homework_pending=True,
        )
        self.assertEqual(report["gate"], "HOMEWORK_HOLD_OR_SCHEDULE")
        self.assertEqual(report["action"], "HOLD_UNTIL_EVENT_ENDS_OR_SURVIVAL_FORCES_HOME")

    def test_event_goals_when_survival_ok(self):
        needs = {**SIX_OK, "energy": 0.7, "fun": 0.25}
        report = evaluate_event_turn(
            needs,
            event_active=True,
            event_goals_incomplete=["drink", "be_silly"],
            outdoor_social_prefix=False,
            indoor_capacity_observed=True,
        )
        self.assertEqual(report["gate"], "EVENT_FUN_VIA_GOALS")

    def test_player_first(self):
        report = evaluate_event_turn(
            LIVE_SNAP,
            event_active=True,
            outdoor_social_prefix=True,
            indoor_capacity_observed=True,
            player_directed=True,
        )
        self.assertEqual(report["gate"], "PLAYER_FIRST_OR_BUSY")

    def test_host_stack_exposes_event_balance(self):
        result = evaluate_turn(
            LIVE_SNAP,
            event_active=True,
            event_goals_incomplete=["friendly_socialize"],
            outdoor_social_prefix=True,
            indoor_capacity_observed=True,
            homework_pending=True,
            viewport={"state": "VIEWPORT_OK"},
        )
        self.assertIn("event_balance", result)
        self.assertEqual(result["event_balance"]["gate"], "SURVIVAL_NEEDS_CRITICAL")
        self.assertEqual(result["next_gate"], "SURVIVAL_NEEDS_BEFORE_EVENT")

    def test_host_stack_indoor_routing_gate(self):
        result = evaluate_turn(
            SIX_OK,
            event_active=True,
            event_goals_incomplete=["be_silly"],
            outdoor_social_prefix=True,
            indoor_capacity_observed=True,
            viewport={"state": "VIEWPORT_OK"},
        )
        self.assertEqual(result["next_gate"], "EVENT_INDOOR_ROUTING")
        self.assertEqual(result["event_balance"]["action"], "CANCEL_OUTDOOR_WALK_SIT_AND_CHAT_HERE")
        self.assertEqual(result["fallback"]["primary_route"], "SIT_AND_CHAT_HERE_INDOOR")
        self.assertEqual(result["fallback"]["preferred_routes"][0], "SIT_AND_CHAT_HERE_INDOOR")

    def test_invalid_needs(self):
        with self.assertRaises(EventBalanceError):
            evaluate_event_turn({"hunger": 1.0})


if __name__ == "__main__":
    unittest.main()
