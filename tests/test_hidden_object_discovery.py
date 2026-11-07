"""Offline-only coverage for the opt-in hidden-object host planner."""
from __future__ import annotations

import unittest

from betterinstincts.hidden_object_discovery import (
    DiscoveryError, audit_p04_receipt, load_contract, p04_guide,
    plan_discovery, review_catalog_entry,
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



class P04OperatorGuideTests(unittest.TestCase):
    def valid_receipt(self):
        guide = p04_guide()
        return {
            "schema": "betterinstincts.hidden-object-discovery-receipt/v1",
            "exact_game_build": "1.121.361.1020",
            "platform": "windows",
            "save_attestation": "OPERATOR_ATTESTED_DISPOSABLE_LAB",
            "player_explicit_opt_in": True,
            "player_idle": True,
            "host_control_lease": "HOST_EXCLUSIVE",
            "game_paused": True,
            "capture_quality": "CONTENT_PRESENT",
            "viewport": "NORMAL",
            "final_scene_id": "build_buy",
            "live_edit_requested": False,
            "game_speed_unchanged": True,
            "player_queue_unchanged": True,
            "scene_cues": {"visual_ref": "capture:build-buy", "operator_ref": "operator:confirmed"},
            "steps": [
                {
                    "step_id": item["step_id"],
                    "observed_gate": item["proof_gate"],
                    "observation_ref": "capture:step-" + str(i + 1),
                    "control_permit_ref": "host-permit:" + str(i + 1),
                    "outcome": "OBSERVED",
                }
                for i, item in enumerate(guide["steps"])
            ],
            "catalog_entries": [
                {
                    "operator_reviewed": True, "result_visible": True,
                    "capture_ref": "capture:item-001", "item_label": "Some current item",
                    "price_simoleons": 0,
                },
            ],
        }

    def test_p04_guide_always_exposes_five_user_steps_and_platforms(self):
        guide = p04_guide()
        self.assertEqual(guide["state"], "P04_PLAYBOOK_RETRIEVED_NO_GAME_ACTION")
        self.assertEqual([x["step_id"] for x in guide["steps"]], [
            "OPEN_CHEAT_CONSOLE", "ENABLE_CHEATS", "REVEAL_HIDDEN_OBJECTS",
            "ENTER_BUILD_BUY", "SELECT_DEBUG_RESULTS",
        ])
        self.assertEqual([x["number"] for x in guide["steps"]], [1, 2, 3, 4, 5])
        self.assertEqual(guide["console_commands"], ["testingcheats true", "bb.showhiddenobjects"])
        self.assertEqual(guide["optional_live_edit_command"], "bb.showliveeditobjects")
        self.assertEqual(guide["platform_console_chords"]["windows"], ["CTRL", "SHIFT", "C"])
        self.assertEqual(guide["platform_console_chords"]["playstation"], ["L1", "R1", "L2", "R2"])
        self.assertEqual(guide["platform_console_chords"]["xbox"], ["LB", "RB", "LT", "RT"])
        self.assertEqual(guide["steps"][3]["keyboard_shortcut_hint"], "F2 (keyboard; verify current patch)")
        self.assertEqual(guide["steps"][4]["search_term"], "debug")
        self.assertFalse(guide["host_action_authorized"])

    def test_p04_guide_rejects_removed_or_reordered_step(self):
        cfg = load_contract()
        cfg["operator_playbook"]["ordered_steps"][0]["step_id"] = "SKIP_CONSOLE"
        with self.assertRaisesRegex(DiscoveryError, "P04_PLAYBOOK_SEQUENCE_CHANGED"):
            p04_guide(cfg=cfg)

    def test_audit_structurally_complete_not_game_cert(self):
        proof = audit_p04_receipt(self.valid_receipt())
        self.assertEqual(proof["state"], "P04_EVIDENCE_SHAPE_COMPLETE_PENDING_INDEPENDENT_REVIEW")
        self.assertEqual(proof["steps_structurally_checked"], 5)
        self.assertEqual(proof["observed_zero_price_claims_in_receipt"], 1)
        self.assertFalse(proof["live_certified"])
        self.assertFalse(proof["host_action_authorized"])

    def test_audit_rejects_skipped_reordered_or_forged_generic_steps(self):
        edits = [
            lambda r: r["steps"].pop(2),
            lambda r: r["steps"].reverse(),
            lambda r: r["steps"][4].pop("observed_gate"),
            lambda r: r["steps"][3].update(observation_ref=""),
            lambda r: r["steps"][0].update(control_permit_ref=""),
            lambda r: r["steps"][1].update(outcome="ASSUMED"),
            lambda r: r["steps"][1].update(observation_ref="capture:step-1"),
        ]
        for edit in edits:
            with self.subTest(edit=edits.index(edit)):
                receipt = self.valid_receipt()
                edit(receipt)
                self.assertEqual(audit_p04_receipt(receipt)["state"], "P04_EVIDENCE_INCOMPLETE")

    def test_audit_rejects_unsafe_unproven_game_state(self):
        for field, bad in [
            ("exact_game_build", "latest"), ("player_idle", False),
            ("host_control_lease", "NONE"), ("save_attestation", "BI_TMP_NAME_ONLY"),
            ("player_explicit_opt_in", False), ("game_paused", False),
            ("capture_quality", "BLACK"), ("final_scene_id", "live_mode"),
            ("game_speed_unchanged", False), ("player_queue_unchanged", False),
            ("live_edit_requested", None),
        ]:
            with self.subTest(field=field):
                receipt = self.valid_receipt()
                receipt[field] = bad
                self.assertEqual(audit_p04_receipt(receipt)["state"], "P04_EVIDENCE_INCOMPLETE")

    def test_audit_optional_liveedit_and_no_global_free_claim(self):
        receipt = self.valid_receipt()
        receipt["live_edit_requested"] = True
        self.assertIn("OPTIONAL_LIVE_EDIT_UNVERIFIED", audit_p04_receipt(receipt)["problems"])
        receipt["live_edit_observation"] = {
            "observation_ref": "capture:live-edit-step", "outcome": "OBSERVED",
        }
        self.assertEqual(
            audit_p04_receipt(receipt)["state"],
            "P04_EVIDENCE_SHAPE_COMPLETE_PENDING_INDEPENDENT_REVIEW",
        )
        receipt["all_items_free"] = True
        self.assertIn("UNSUPPORTED_GLOBAL_CATALOG_CLAIM", audit_p04_receipt(receipt)["problems"])

    def test_audit_requires_actual_item_review_not_blank_or_false_free(self):
        receipt = self.valid_receipt()
        receipt["catalog_entries"] = []
        self.assertIn("REVIEWED_CATALOG_ENTRIES_REQUIRED", audit_p04_receipt(receipt)["problems"])
        receipt = self.valid_receipt()
        receipt["catalog_entries"][0]["operator_reviewed"] = False
        self.assertIn("CATALOG_ENTRY_UNVERIFIED:1", audit_p04_receipt(receipt)["problems"])
        receipt = self.valid_receipt()
        del receipt["catalog_entries"][0]["price_simoleons"]
        proof = audit_p04_receipt(receipt)
        self.assertEqual(proof["observed_zero_price_claims_in_receipt"], 0)
        self.assertEqual(proof["price_unknown_entries_in_receipt"], 1)

    def test_audit_console_requires_achievement_ack(self):
        receipt = self.valid_receipt()
        receipt["platform"] = "xbox"
        self.assertIn("CONSOLE_ACHIEVEMENT_ACK_MISSING", audit_p04_receipt(receipt)["problems"])
        receipt["acknowledge_testingcheats_trophy_risk"] = True
        self.assertEqual(
            audit_p04_receipt(receipt)["state"],
            "P04_EVIDENCE_SHAPE_COMPLETE_PENDING_INDEPENDENT_REVIEW",
        )




if __name__ == "__main__":
    unittest.main()
