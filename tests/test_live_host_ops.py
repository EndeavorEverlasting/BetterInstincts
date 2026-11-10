"""Offline live-host-ops: chat rules must be contract-backed (P00/P01)."""
from __future__ import annotations

import unittest

from betterinstincts.live_host_ops import assess_interaction_channel


class InteractionChannelTests(unittest.TestCase):
    def test_verified_native_channel_is_preferred_without_granting_input(self):
        result = assess_interaction_channel(native_capability_verified=True, desktop_fallback_opt_in=True)
        self.assertEqual(result['channel'], 'NATIVE_SEMANTIC_API')
        self.assertFalse(result['execute_allowed'])
        self.assertFalse(result['peripheral_changes_allowed'])

    def test_desktop_fallback_requires_explicit_operator_choice(self):
        self.assertIsNone(assess_interaction_channel(native_capability_verified=False)['channel'])
        self.assertEqual(assess_interaction_channel(native_capability_verified=False,
            desktop_fallback_opt_in=True)['channel'], 'DESKTOP_FALLBACK')

from betterinstincts.camera_traverse import assess_edge_creek_regression, load_contract as load_cam
from betterinstincts.live_host_ops import (
    LiveHostOpsError,
    assess_edge_creek_flag,
    assess_unpause_admission,
    assess_world_xy_policy,
    load_contract,
    priority_order,
)


class LiveHostOpsContractTests(unittest.TestCase):
    def test_architecture_and_priority(self):
        cfg = load_contract()
        self.assertEqual(cfg["architecture"]["selected"], "PAUSED_PRODUCTIVITY_BEFORE_TIME_RISK")
        order = priority_order(cfg)
        self.assertEqual(order[0], "KEEP_PAUSED")
        self.assertIn("ORDER_PURCHASE_UPGRADE_PARTS_OR_WORKSTATION_SPAWN", order)
        self.assertLess(
            order.index("ORDER_PURCHASE_UPGRADE_PARTS_OR_WORKSTATION_SPAWN"),
            order.index("UNPAUSE_ONLY_AFTER_QUEUES_SET"),
        )
        self.assertIn("CHAT_ONLY_RULE_WITHOUT_REPO_MUTATION", cfg["forbidden_always"])

    def test_unpause_denied_while_parts_gate_open(self):
        denied = assess_unpause_admission(
            parts_gate_open=True, household_queue_incomplete=False, paused_verified=True
        )
        self.assertFalse(denied["admit"])
        self.assertEqual(denied["gate"], "PAUSED_PRODUCTIVITY_REQUIRED")
        self.assertIn("UNPAUSE", denied["forbid"])

    def test_unpause_allowed_when_queues_done(self):
        ok = assess_unpause_admission(
            parts_gate_open=False, household_queue_incomplete=False, paused_verified=True
        )
        self.assertTrue(ok["admit"])

    def test_edge_creek_flag(self):
        hit = assess_edge_creek_flag(cursor_in_edge_band=True, scenery_tokens=[])
        self.assertTrue(hit["triggered"])
        self.assertEqual(hit["recovery"][0], "SAFE_CURSOR_REST")
        creek = assess_edge_creek_flag(cursor_in_edge_band=False, scenery_tokens=["CANAL"])
        self.assertTrue(creek["triggered"])

    def test_hardcoded_field_xy_denied_without_fresh_visible(self):
        denied = assess_world_xy_policy(
            target_kind="WORKSTATION",
            using_hardcoded_field_xy=True,
            target_visible_in_fresh_capture=False,
        )
        self.assertFalse(denied["admit"])
        self.assertEqual(denied["gate"], "HARDCODED_FIELD_XY_FORBIDDEN")


class EdgeCreekCameraTraverseTests(unittest.TestCase):
    def test_contract_block_present(self):
        cfg = load_cam()
        block = cfg["edge_creek_regression"]
        self.assertEqual(block["id"], "EDGE_MOUSE_PARK_TO_CREEK")
        self.assertIn("SAFE_CURSOR_REST", block["recovery_chord"])
        self.assertIn("SHIFT_ENTER", block["recovery_chord"])

    def test_assess_edge_creek_regression(self):
        r = assess_edge_creek_regression(cursor_in_edge_band=True)
        self.assertTrue(r["triggered"])
        self.assertEqual(r["recovery_chord"][:2], ["SAFE_CURSOR_REST", "SHIFT_ENTER"])
        buy = assess_edge_creek_regression(
            cursor_in_edge_band=False,
            scenery_tokens=["STREET"],
            buy_catalog_open_after_world_click=True,
        )
        self.assertTrue(buy["triggered"])
        self.assertEqual(buy["recovery_chord"][0], "ESC")


if __name__ == "__main__":
    unittest.main()
