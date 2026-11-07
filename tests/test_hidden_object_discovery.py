"""Offline-only coverage for the opt-in hidden-object host planner."""
from __future__ import annotations

import unittest

from betterinstincts.hidden_object_discovery import (
    DiscoveryError, load_contract, plan_discovery, review_catalog_entry,
)


def approved(**overrides):
    base = {
        "exact_game_build": "1.121.361.1020",
        "platform": "windows",
        "scene_id": "live_mode",
        "visual_cue_ref": "capture:sample-scene",
        "operator_cue_ref": "operator:review",
        "capture_quality": "CONTENT_PRESENT",
        "viewport": "NORMAL",
        "save_attestation": "OPERATOR_ATTESTED_DISPOSABLE_LAB",
        "player_explicit_opt_in": True,
        "player_idle": True,
        "host_control_lease": "HOST_EXCLUSIVE",
        "game_paused": True,
    }
    base.update(overrides)
    return base


class HiddenObjectDiscoveryTests(unittest.TestCase):
    def test_contract_loads_without_execution(self):
        c = load_contract()
        self.assertEqual(c["host_execution"], "NEVER_FROM_THIS_MODULE")
        self.assertEqual(c["search_contract"]["primary"], "debug")

    def test_exact_requested_console_order_and_opt_in_live_edit(self):
        base = plan_discovery(approved(), target="toothbrush", category="clutter")
        self.assertEqual(base["console_lines"], ["testingcheats true", "bb.showhiddenobjects"])
        self.assertFalse(base["dispatch_authorized"])
        self.assertNotIn("bb.showliveeditobjects", base["console_lines"])
        self.assertEqual(base["steps"][0]["step_id"], "OPEN_CONSOLE")
        self.assertEqual(base["steps"][-1]["step_id"], "PLACEMENT_SEPARATE_APPROVAL")
        self.assertEqual(base["item_availability"], "UNKNOWN_UNTIL_OBSERVED")
        self.assertEqual(base["free_item_claim"], "UNKNOWN_UNTIL_PRICE_OBSERVED")
        live = plan_discovery(approved(), category="world", include_live_edit=True)
        self.assertEqual(live["console_lines"], [
            "testingcheats true", "bb.showhiddenobjects", "bb.showliveeditobjects",
        ])
        self.assertFalse(live["host_executes"])
        self.assertTrue(all(x["manual_only"] for x in live["steps"]))

    def test_missing_guard_individually_abstains(self):
        overrides = [
            {"exact_game_build": "latest"}, {"exact_game_build": ""},
            {"scene_id": "main_menu"}, {"scene_id": "live_viewport_black"},
            {"visual_cue_ref": ""}, {"operator_cue_ref": None},
            {"viewport": "BLACK"}, {"capture_quality": "EMPTY"},
            {"save_attestation": "NAMED_BI_TMP_ONLY"}, {"player_explicit_opt_in": False},
            {"player_idle": False}, {"host_control_lease": "NONE"},
            {"game_paused": False}, {"platform": "unknown"},
        ]
        for change in overrides:
            with self.subTest(change=change):
                res = plan_discovery(approved(**change))
                self.assertEqual(res["state"], "ABSTAIN")
                self.assertEqual(res["steps"], [])

    def test_console_achievement_acknowledgment(self):
        res = plan_discovery(approved(platform="playstation"))
        self.assertIn("CONSOLE_ACHIEVEMENT_ACK_REQUIRED", res["reasons"])
        yes = plan_discovery(approved(platform="playstation", acknowledge_testingcheats_trophy_risk=True))
        self.assertEqual(yes["state"], "DISCOVERY_PLAN_READY_NOT_AUTHORIZED")
        self.assertEqual(yes["steps"][0]["chord"], ["L1", "R1", "L2", "R2"])

    def test_queries_never_become_commands(self):
        for query in ["bb.showhiddenobjects / buydebug", "door\nF1", "testingcheats",
                      "buydebug", "", "A" * 65, "crystal; motherlode"]:
            with self.subTest(query=query):
                with self.assertRaises(DiscoveryError):
                    plan_discovery(approved(), target=query)
        with self.assertRaises(DiscoveryError):
            plan_discovery(approved(), category="unrestricted")
        with self.assertRaises(DiscoveryError):
            plan_discovery(approved(), include_live_edit="yes")

    def test_catalog_price_not_assumed_free(self):
        observed = dict(operator_reviewed=True, result_visible=True,
                        capture_ref="capture:one", item_label="Light")
        no_price = review_catalog_entry(observed)
        self.assertEqual(no_price["state"], "OBSERVED_PRICE_UNKNOWN")
        self.assertIsNone(no_price["free"])
        free = review_catalog_entry({**observed, "price_simoleons": 0})
        self.assertEqual(free["state"], "OBSERVED_FREE_ITEM")
        self.assertIs(free["free"], True)
        priced = review_catalog_entry({**observed, "price_simoleons": 15})
        self.assertEqual(priced["state"], "OBSERVED_PRICED_ITEM")
        self.assertIs(priced["free"], False)
        bad_price = review_catalog_entry({**observed, "price_simoleons": True})
        self.assertEqual(bad_price["state"], "OBSERVED_PRICE_UNKNOWN")
        missing_review = review_catalog_entry({**observed, "operator_reviewed": False, "price_simoleons": 0})
        self.assertEqual(missing_review["state"], "ENTRY_NOT_VERIFIED")

    def test_input_not_mutated(self):
        observation = approved()
        before = dict(observation)
        plan_discovery(observation, category="lighting")
        self.assertEqual(observation, before)


if __name__ == "__main__":
    unittest.main()
