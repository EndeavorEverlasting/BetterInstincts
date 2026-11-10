"""Offline falsifiers for fixed-UI click ledger + arm→console handoff."""
from __future__ import annotations

import unittest

from betterinstincts.fixed_ui_click_map import (
    FixedUiClickMapError,
    classify_click,
    empty_ledger,
    ensure_seeded_ledger,
    load_contract,
    plan_arm_to_console_handoff,
    record_click_attempt,
    resolve_target_xy,
)


class FixedUiClickMapTests(unittest.TestCase):
    def test_contract_pins_fixed_scope_and_handoff(self):
        cfg = load_contract()
        self.assertEqual(cfg["schema"], "betterinstincts.fixed-ui-click-map/v1")
        self.assertFalse(cfg["execute_allowed_default"])
        self.assertIn("MOVING_WORLD_OBJECTS", cfg["scope"]["out"])
        hand = cfg["handoff"]
        self.assertEqual(hand["console_hotkey_id"], "CHEAT_CONSOLE")
        self.assertEqual(hand["console_chord"], ["CTRL", "SHIFT", "C"])
        self.assertIn("live.calendar_icon", cfg["seed_targets_1920x1080"])

    def test_wrong_control_does_not_rewrite_portrait_coords(self):
        ledger = ensure_seeded_ledger(empty_ledger())
        before = list(ledger["targets"]["live.household_portrait_2"]["client_xy"])
        record_click_attempt(
            ledger,
            target_id="live.household_portrait_2",
            client_xy=[300, 1045],
            classification="WRONG_CONTROL",
            observed_control_id="live.calendar_icon",
            note="Intended Olga portrait; opened calendar",
        )
        after = ledger["targets"]["live.household_portrait_2"]["client_xy"]
        self.assertEqual(after, before)
        self.assertEqual(ledger["targets"]["live.household_portrait_2"]["wrong_control_count"], 1)
        self.assertEqual(ledger["attempts"][-1]["classification"], "WRONG_CONTROL")

    def test_hit_attests_coords(self):
        ledger = ensure_seeded_ledger(empty_ledger())
        record_click_attempt(
            ledger,
            target_id="live.household_portrait_2",
            client_xy=[520, 1045],
            classification="HIT",
        )
        row = ledger["targets"]["live.household_portrait_2"]
        self.assertTrue(row["attested"])
        self.assertEqual(row["client_xy"], [520, 1045])
        self.assertEqual(resolve_target_xy(ledger, "live.household_portrait_2")["client_xy"], [520, 1045])

    def test_moving_target_out_of_scope(self):
        ledger = empty_ledger()
        attempt = record_click_attempt(
            ledger,
            target_id="world.servo_body",
            client_xy=[900, 500],
            classification="OUT_OF_SCOPE_MOVING_TARGET",
            moving_target=True,
        )
        self.assertEqual(attempt["classification"], "OUT_OF_SCOPE_MOVING_TARGET")

    def test_classify_wrong_control_by_id(self):
        scored = classify_click(
            intended_xy=[520, 1045],
            observed_xy=[300, 1045],
            intended_target_id="live.household_portrait_2",
            observed_control_id="live.calendar_icon",
        )
        self.assertEqual(scored["classification"], "WRONG_CONTROL")

    def test_arm_to_console_handoff_plan(self):
        plan = plan_arm_to_console_handoff()
        self.assertEqual(plan["arm"]["step"], "ARM_LIVE_HOTKEYS")
        self.assertEqual(plan["console"]["chord"], ["CTRL", "SHIFT", "C"])
        self.assertTrue(plan["console"]["require_white_strip_observed"])
        self.assertFalse(plan["execute_allowed"])
        self.assertIn("TYPE_WITHOUT_CONSOLE_STRIP", plan["forbidden"])

    def test_resolve_unknown_fails(self):
        with self.assertRaises(FixedUiClickMapError):
            resolve_target_xy(empty_ledger(), "live.does_not_exist")


if __name__ == "__main__":
    unittest.main()
