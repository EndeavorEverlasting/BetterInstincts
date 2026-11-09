import unittest

from betterinstincts.host_listener import activate, deactivate, tick
from betterinstincts.host_stack import evaluate_turn
from betterinstincts.player_presence import PresenceProbe
from betterinstincts.teen_homework import (
    TeenHomeworkError,
    evaluate_teen_homework_turn,
    load_contract,
    recovery_plan,
    survival_critical,
)

SIX_OK = {
    "hunger": 0.6,
    "bladder": 0.45,
    "energy": 0.7,
    "hygiene": 0.7,
    "fun": 0.25,
    "social": 0.8,
}
CRITICAL_HOME = {
    "hunger": 0.05,
    "bladder": 0.9,
    "energy": 0.2,
    "hygiene": 0.7,
    "fun": 0.5,
    "social": 0.5,
}


class TeenHomeworkTests(unittest.TestCase):
    def test_contract_schema_and_ladder(self):
        cfg = load_contract()
        self.assertEqual(cfg["schema"], "betterinstincts.teen-homework/v1")
        self.assertEqual(
            cfg["proof_ceiling"],
            "HOST_TEEN_HOMEWORK_CATALOG_NOT_EA_API_NOT_BI006_CERT",
        )
        self.assertEqual(cfg["local_observed"]["capture_ref"], "operator:teen-homework-missing-20261107")
        ladder = recovery_plan(cfg)
        self.assertEqual(ladder[0]["id"], "LOT_SCAN_PUT_HOMEWORK_IN_INVENTORY")
        self.assertEqual(
            recovery_plan(cfg, homework_on_lot=False)[0]["id"],
            "COMPUTER_SCHOOL_DO_HOMEWORK",
        )
        self.assertIn("SURVIVAL_BEFORE_HOMEWORK", cfg["call_stack_gates"])
        self.assertIn("lot_scan", cfg)

    def test_survival_outranks_homework(self):
        report = evaluate_teen_homework_turn(
            CRITICAL_HOME,
            location_kind="home",
            homework_pending=True,
            inventory_has_homework=False,
            queue=["Use Toilet", "Take a Shower"],
        )
        self.assertEqual(report["gate"], "SURVIVAL_BEFORE_HOMEWORK")
        self.assertIn("hunger", report["survival_critical"])
        self.assertIn("energy", report["survival_critical"])

    def test_premises_block(self):
        report = evaluate_teen_homework_turn(
            SIX_OK,
            location_kind="school",
            homework_pending=True,
            inventory_has_homework=False,
            school_day_active=True,
        )
        self.assertEqual(report["gate"], "HOMEWORK_PREMISES_BLOCKED")
        self.assertTrue(report["homework_blocked_on_premises"])

    def test_missing_inventory_recovery_primary_lot_scan(self):
        report = evaluate_teen_homework_turn(
            SIX_OK,
            location_kind="home",
            homework_pending=True,
            inventory_has_homework=False,
        )
        self.assertEqual(report["gate"], "HOMEWORK_INVENTORY_MISSING")
        self.assertEqual(report["primary_route"], "LOT_SCAN_PUT_HOMEWORK_IN_INVENTORY")
        self.assertEqual(report["next_actions"][0]["id"], "LOT_SCAN_PUT_HOMEWORK_IN_INVENTORY")
        self.assertIn("LOT_SCAN_BEFORE_COMPUTER_RECOVERY", report["findings"])

    def test_lot_observed_homework_prefers_put_in_inventory(self):
        report = evaluate_teen_homework_turn(
            SIX_OK,
            location_kind="home",
            homework_pending=True,
            inventory_has_homework=False,
            homework_on_lot=True,
            available_objects=["dining_table", "homework"],
        )
        self.assertEqual(report["primary_route"], "LOT_SCAN_PUT_HOMEWORK_IN_INVENTORY")
        self.assertTrue(report["homework_on_lot"])
        self.assertIn("homework", report["lot_homework_hits"])
        self.assertIn("HOMEWORK_OBSERVED_ON_LOT", report["findings"])

    def test_confirmed_absent_on_lot_skips_lot_scan(self):
        report = evaluate_teen_homework_turn(
            SIX_OK,
            location_kind="home",
            homework_pending=True,
            inventory_has_homework=False,
            homework_on_lot=False,
        )
        self.assertEqual(report["primary_route"], "COMPUTER_SCHOOL_DO_HOMEWORK")
        self.assertNotIn(
            "LOT_SCAN_PUT_HOMEWORK_IN_INVENTORY",
            report["preferred_routes"],
        )

    def test_inventory_present_queues_homework(self):
        report = evaluate_teen_homework_turn(
            SIX_OK,
            location_kind="home",
            homework_pending=True,
            inventory_has_homework=True,
        )
        self.assertEqual(report["gate"], "QUEUE_TEEN_HOMEWORK")
        self.assertIn(report["primary_route"], {"DO_HOMEWORK", "WORK_ON_HOMEWORK"})

    def test_homework_after_needs_queue(self):
        report = evaluate_teen_homework_turn(
            SIX_OK,
            location_kind="home",
            homework_pending=True,
            inventory_has_homework=False,
            queue=["Use Toilet", "Take a Shower"],
        )
        self.assertEqual(report["gate"], "HOMEWORK_AFTER_NEEDS_QUEUE")

    def test_host_stack_survival_gate(self):
        result = evaluate_turn(
            CRITICAL_HOME,
            location_kind="home",
            homework_pending=True,
            inventory_has_homework=False,
            life_stage="teen",
            queue=["Use Toilet", "Take a Shower"],
            viewport={"state": "VIEWPORT_OK"},
        )
        self.assertEqual(result["next_gate"], "SURVIVAL_BEFORE_HOMEWORK")
        self.assertIsNotNone(result.get("teen_homework"))
        self.assertEqual(result["teen_homework"]["gate"], "SURVIVAL_BEFORE_HOMEWORK")

    def test_host_stack_inventory_missing(self):
        result = evaluate_turn(
            SIX_OK,
            location_kind="home",
            homework_pending=True,
            inventory_has_homework=False,
            life_stage="teen",
            viewport={"state": "VIEWPORT_OK"},
        )
        self.assertEqual(result["next_gate"], "HOMEWORK_INVENTORY_MISSING")
        self.assertEqual(
            result["fallback"]["primary_route"],
            "LOT_SCAN_PUT_HOMEWORK_IN_INVENTORY",
        )

    def test_host_stack_lot_object_token(self):
        result = evaluate_turn(
            SIX_OK,
            location_kind="home",
            homework_pending=True,
            inventory_has_homework=False,
            homework_on_lot=None,
            available_objects=["Homework"],
            life_stage="teen",
            viewport={"state": "VIEWPORT_OK"},
        )
        self.assertEqual(result["next_gate"], "HOMEWORK_INVENTORY_MISSING")
        self.assertEqual(
            result["teen_homework"]["primary_route"],
            "LOT_SCAN_PUT_HOMEWORK_IN_INVENTORY",
        )
        self.assertTrue(result["teen_homework"]["homework_on_lot"])

    def test_listener_tick_passes_teen_fields(self):
        sid = "testteenhw01"
        activate(sid, note="unit")
        try:
            receipt = tick(
                sid,
                {
                    "schema": "betterinstincts.host-listener.observation/v1",
                    "needs": SIX_OK,
                    "queue": [],
                    "location_kind": "home",
                    "capture_ref": "capture:teen-listener",
                    "homework_pending": True,
                    "inventory_has_homework": False,
                    "homework_on_lot": True,
                    "available_objects": ["homework"],
                    "life_stage": "teen",
                },
                presence_probe=PresenceProbe(False, False, last_input_age_ms=19000),
            )
            stack = receipt["host_stack"]
            self.assertEqual(stack["next_gate"], "HOMEWORK_INVENTORY_MISSING")
            self.assertIsNotNone(stack.get("teen_homework"))
            self.assertEqual(stack["teen_homework"]["inventory_has_homework"], False)
            self.assertEqual(
                stack["teen_homework"]["primary_route"],
                "LOT_SCAN_PUT_HOMEWORK_IN_INVENTORY",
            )
            self.assertEqual(stack["teen_homework"]["life_stage"], "teen")
            self.assertTrue(stack["teen_homework"]["homework_pending"])
            self.assertTrue(stack["teen_homework"]["homework_on_lot"])
        finally:
            deactivate(sid)

    def test_invalid_needs_fail_closed(self):
        with self.assertRaises(TeenHomeworkError):
            evaluate_teen_homework_turn(
                {"hunger": 0.5},
                homework_pending=True,
            )

    def test_survival_helper_threshold(self):
        self.assertEqual(survival_critical(CRITICAL_HOME), ["energy", "hunger"])


if __name__ == "__main__":
    unittest.main()
