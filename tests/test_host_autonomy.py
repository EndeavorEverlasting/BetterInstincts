import json
import tempfile
import unittest
from pathlib import Path

from betterinstincts.behavior_eval import evaluate_queue
from betterinstincts.glossary import define, load_glossary
from betterinstincts.host_automate import plan_automation
from betterinstincts.host_listener import activate, deactivate, tick
from betterinstincts.host_stack import evaluate_turn
from betterinstincts.needs_force import plan_force
from betterinstincts.player_presence import PresenceProbe, classify

SIX = {
    "hunger": 0.9, "bladder": 0.9, "energy": 0.9,
    "hygiene": 0.9, "fun": 0.9, "social": 0.9,
}
CRITICAL = {
    "hunger": 0.05, "bladder": 0.9, "energy": 0.05,
    "hygiene": 0.9, "fun": 0.2, "social": 0.2,
}


class HostAutonomyTests(unittest.TestCase):
    def test_glossary_required_terms(self):
        cfg = load_glossary()
        self.assertIn("IN_FRAME_WALK_THRASH", cfg["terms"])
        self.assertIn("HOST_MAY_AUTOMATE", cfg["terms"])
        self.assertIn("manage worlds", define("MAP_TRAVEL").lower())

    def test_fluff_under_critical_is_optimize(self):
        out = evaluate_queue(CRITICAL, ["read"], objects_on_current_lot=False, location_kind="school")
        self.assertEqual(out["clarity"]["verdict"], "BAD_BEHAVIOR")
        self.assertEqual(out["clarity"]["disposition"], "OPTIMIZE")
        self.assertIn("IN_FRAME_WALK_THRASH", out["clarity"]["forbidden_routes"])

    def test_player_directed_emulate_only(self):
        out = evaluate_queue(CRITICAL, ["read"], player_directed=True)
        self.assertEqual(out["clarity"]["disposition"], "EMULATE")
        self.assertFalse(out["clarity"]["optimize_allowed"])

    def test_needs_force_prefers_map_travel_off_lot(self):
        plan = plan_force(location_kind="school", objects_on_current_lot=False, disposition="OPTIMIZE")
        self.assertEqual(plan["route"], "MAP_TRAVEL")
        self.assertIn("open_manage_worlds", [s["id"] for s in plan["steps"]])
        self.assertIn("IN_FRAME_WALK_THRASH", plan["forbidden"])

    def test_presence_yields_when_on_canvas(self):
        presence = classify(
            PresenceProbe(foreground_is_sims=True, cursor_in_client=True),
            session_active=True,
        )
        self.assertEqual(presence["state"], "PLAYER_PLAYING")
        self.assertEqual(presence["host"], "YIELD_TO_PLAYER")

    def test_presence_allows_host_when_off_canvas(self):
        presence = classify(
            PresenceProbe(foreground_is_sims=False, cursor_in_client=False),
            session_active=True,
        )
        self.assertEqual(presence["state"], "HOST_MAY_AUTOMATE")

    def test_automate_yields_to_player(self):
        out = plan_automation(
            {"schema": "betterinstincts.host-listener.observation/v1",
             "needs": CRITICAL, "queue": ["read"], "location_kind": "school",
             "objects_on_current_lot": False, "capture_ref": "capture:t"},
            PresenceProbe(True, True),
            session_active=True,
        )
        self.assertEqual(out["state"], "YIELD_TO_PLAYER")

    def test_automate_plans_map_travel_when_idle(self):
        out = plan_automation(
            {"needs": CRITICAL, "queue": ["read", "walk"], "location_kind": "school",
             "objects_on_current_lot": False, "capture_ref": "capture:t",
             "available_objects": ()},
            PresenceProbe(False, False, last_input_age_ms=9000),
            session_active=True,
        )
        self.assertEqual(out["state"], "HOST_AUTOMATION_PLANNED")
        self.assertEqual(out["needs_force_plan"]["route"], "MAP_TRAVEL")
        self.assertEqual(out["host_stack"]["next_gate"], "MAP_TRAVEL_HOME_FIRST")

    def test_host_stack_map_gate_with_queue(self):
        out = evaluate_turn(
            CRITICAL,
            location_kind="school",
            objects_on_current_lot=False,
            queue=["read"],
        )
        self.assertEqual(out["next_gate"], "MAP_TRAVEL_HOME_FIRST")
        self.assertEqual(out["fallback"]["mechanism"], "MAP_TRAVEL_HOME_FIRST")

    def test_listener_tick_yield_and_optimize(self):
        # Use unique session under dist; clean via deactivate.
        sid = "testautonomy01"
        activate(sid, note="unit")
        try:
            yield_receipt = tick(
                sid,
                {
                    "schema": "betterinstincts.host-listener.observation/v1",
                    "needs": CRITICAL,
                    "queue": ["read"],
                    "location_kind": "school",
                    "objects_on_current_lot": False,
                    "capture_ref": "capture:unit",
                },
                presence_probe=PresenceProbe(True, True),
            )
            self.assertEqual(yield_receipt["listener_action"], "YIELD_TO_PLAYER")
            opt = tick(
                sid,
                {
                    "schema": "betterinstincts.host-listener.observation/v1",
                    "needs": CRITICAL,
                    "queue": ["read"],
                    "location_kind": "school",
                    "objects_on_current_lot": False,
                    "capture_ref": "capture:unit2",
                    "available_objects": (),
                },
                presence_probe=PresenceProbe(False, False, last_input_age_ms=9000),
            )
            self.assertEqual(opt["listener_action"], "RECORD_OPTIMIZATION_PLAN")
            self.assertEqual(opt["needs_force_plan"]["route"], "MAP_TRAVEL")
        finally:
            deactivate(sid)


if __name__ == "__main__":
    unittest.main()
