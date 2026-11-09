"""P95 + P82: multiple behavioral input channels share one read-only evaluator."""
import io
import json
import unittest
import uuid
from contextlib import redirect_stdout

from betterinstincts.behavior_input_catalog import (
    BehaviorInputCatalogError, catalog, resolve_hotkey, resolve_cheat,
)
from betterinstincts.hover_learning import (
    EVENT_SCHEMA, HoverLearningError, empty_state, evaluate, observe,
)
from betterinstincts.host_listener import (
    HostListenerError, activate, deactivate, observe_hover,
)
from scripts.host_listener import main

T = 1_800_000_000_000


def event(kind, event_id, at_ms, **values):
    return {"schema": EVENT_SCHEMA, "id": event_id, "at_ms": at_ms,
            "kind": kind, "source": "operator_supplied", **values}


def ingest(state, kind, event_id, when, **fields):
    return observe(state, event(kind, event_id, when, **fields))[0]


class InputCatalogTests(unittest.TestCase):
    def test_uses_existing_mode_catalog_and_cheat_owners(self):
        identities = catalog()
        self.assertIn("MODE_LIVE", identities["hotkeys"]["LIVE"])
        self.assertIn("BACKSPACE_TO_HOUSEHOLD_INVENTORY", identities["hotkeys"]["BUILD"])
        self.assertIn("CHEAT_CONSOLE", identities["hotkeys"]["BUY"])
        self.assertIn("bb_showhiddenobjects", identities["cheats"])
        self.assertIn("bb_showliveeditobjects", identities["cheats"])
        self.assertIn("careers_promote_techguru", identities["cheats"])
        self.assertIn("motherlode", identities["cheats"])
        self.assertIn("money_amount", identities["cheats"])
        self.assertEqual(resolve_hotkey("BUY", "UNDO"), "hotkey:buy:undo")
        self.assertEqual(resolve_cheat("motherlode"), "cheat:motherlode")

    def test_unknown_mode_hotkey_or_console_line_rejected(self):
        with self.assertRaisesRegex(BehaviorInputCatalogError, "HOTKEY_NOT_IN_MODE_CATALOG"):
            resolve_hotkey("LIVE", "BACKSPACE_TO_HOUSEHOLD_INVENTORY")
        with self.assertRaisesRegex(BehaviorInputCatalogError, "HOTKEY_NOT_IN_MODE_CATALOG"):
            resolve_hotkey("UNKNOWN", "MODE_LIVE")
        with self.assertRaisesRegex(BehaviorInputCatalogError, "CHEAT_NOT_IN_CANONICAL_CATALOG"):
            resolve_cheat("motherlode;delete_personal_save")
        with self.assertRaisesRegex(BehaviorInputCatalogError, "CHEAT_NOT_IN_CANONICAL_CATALOG"):
            resolve_cheat("Money 999999")


class MultiChannelBehaviorTests(unittest.TestCase):
    def test_hotkey_and_cheat_follow_same_outcome_receipt_chain(self):
        st = empty_state()
        st = ingest(st, "hotkey_action", "key_001", T,
                    mode="BUY", hotkey_id="UNDO",
                    interaction_ref="interaction:undo1")
        st = ingest(st, "outcome", "out_001", T + 20,
                    interaction_ref="interaction:undo1",
                    outcome="helpful", evidence_ref="capture:undo1",
                    operator_reviewed=True)
        st = ingest(st, "cheat_action", "cheat_001", T + 50,
                    cheat_id="motherlode", interaction_ref="interaction:funds1")
        st = ingest(st, "outcome", "out_002", T + 80,
                    interaction_ref="interaction:funds1",
                    outcome="helpful", evidence_ref="capture:funds1",
                    operator_reviewed=False)
        result = evaluate(st, now_ms=T + 100)
        rows = result["windows"]["180"]["patterns"]
        self.assertEqual(len(rows), 2)
        by_channel = {r["channel"]: r for r in rows}
        self.assertEqual(by_channel["hotkey"]["action_ref"], "hotkey:buy:undo")
        self.assertEqual(by_channel["hotkey"]["reviewed_helpful"], 1)
        self.assertEqual(by_channel["cheat"]["action_ref"], "cheat:motherlode")
        self.assertEqual(by_channel["cheat"]["pending_review_or_outcome"], 1)
        self.assertEqual(by_channel["cheat"]["reviewed_helpful"], 0)
        self.assertEqual(result["windows"]["180"]["hotkey_action_observations"], 1)
        self.assertEqual(result["windows"]["180"]["cheat_action_observations"], 1)
        self.assertEqual(result["windows"]["180"]["action_observations"], 2)
        self.assertFalse(result["execute_clicks"])
        self.assertFalse(result["automatically_trained"])
        self.assertIsNone(result["control_permit"])

    def test_all_three_channels_isolate_patterns_and_avoid_double_counting(self):
        st = ingest(empty_state(), "tooltip_visible", "tip_001", T,
                    target_ref="object:tv", tooltip_ref="tip:watch")
        st = ingest(st, "action", "action_001", T + 1,
                    target_ref="object:tv", interaction_ref="interaction:tv1",
                    action_ref="action:watch")
        st = ingest(st, "hotkey_action", "key_001", T + 2, mode="LIVE",
                    hotkey_id="MODE_LIVE", interaction_ref="interaction:mode1")
        st = ingest(st, "cheat_action", "cheat_001", T + 3,
                    cheat_id="bb_showhiddenobjects", interaction_ref="interaction:debug1")
        st = ingest(st, "outcome", "out_001", T + 4,
                    interaction_ref="interaction:mode1", outcome="harmful",
                    evidence_ref="capture:wrong_mode",
                    operator_reviewed=True)
        result = evaluate(st, now_ms=T + 10)
        w = result["windows"]["180"]
        self.assertEqual(len(w["patterns"]), 3)
        self.assertEqual(set(row["channel"] for row in w["patterns"]),
                         {"tooltip", "hotkey", "cheat"})
        self.assertEqual(w["action_observations"], 3)
        self.assertEqual(w["tooltip_appearances"], 1)
        self.assertEqual(sum(p["reviewed_harmful"] for p in w["patterns"]), 1)
        self.assertEqual(sum(p["attempts"] for p in w["patterns"]), 3)

    def test_long_window_and_review_eligibility_are_shared_by_cheat(self):
        st = empty_state()
        for i in range(3):
            at = T + i * 10000
            st = ingest(st, "cheat_action", f"cheat_{i:03d}", at,
                        cheat_id="motherlode",
                        interaction_ref=f"interaction:funds{i}")
            st = ingest(st, "outcome", f"proof_{i:03d}", at + 100,
                        interaction_ref=f"interaction:funds{i}",
                        outcome="helpful", evidence_ref=f"capture:funds{i}",
                        operator_reviewed=True)
        r = evaluate(st, now_ms=T + 40000)
        self.assertEqual(set(r["windows"]), {"180", "300", "600", "1800", "3600"})
        row = r["windows"]["180"]["patterns"][0]
        self.assertEqual(row["channel"], "cheat")
        self.assertEqual(row["reviewed_success_rate"], 1.0)
        self.assertTrue(row["learning_eligible"])
        self.assertFalse(r["automatically_trained"])

    def test_hotkey_request_does_not_claim_mode_or_cheat_effect(self):
        st = ingest(empty_state(), "hotkey_action", "key_001", T,
                    mode="BUILD", hotkey_id="MODE_BUILD",
                    interaction_ref="interaction:build")
        p = evaluate(st, now_ms=T + 1)["windows"]["180"]["patterns"][0]
        self.assertEqual(p["pending_review_or_outcome"], 1)
        self.assertIsNone(p["reviewed_success_rate"])
        self.assertFalse(p["learning_eligible"])

    def test_reject_raw_keys_commands_params_and_forged_derived_action_ref(self):
        base = event("hotkey_action", "key_001", T, mode="LIVE",
                     hotkey_id="MODE_LIVE",
                     interaction_ref="interaction:mode")
        for field, value in (
            ("key_sequence", "CTRL+SHIFT+C"),
            ("typed_command", "Money 100000"),
            ("action_ref", "hotkey:live:mode_live"),
            ("amount", 100000),
        ):
            with self.subTest(field=field), self.assertRaisesRegex(
                    HoverLearningError, "UNEXPECTED_HOVER_EVENT_FIELDS|EVENT_FIELDS_NOT_KIND_SCOPED"):
                observe(empty_state(), {**base, field: value})
        with self.assertRaisesRegex(HoverLearningError, "UNRECOGNIZED_INPUT_CHANNEL"):
            ingest(empty_state(), "hotkey_action", "key_002", T,
                   mode="LIVE", hotkey_id="UNDO", interaction_ref="interaction:undo")
        with self.assertRaisesRegex(HoverLearningError, "UNRECOGNIZED_INPUT_CHANNEL"):
            ingest(empty_state(), "cheat_action", "cheat_002", T,
                   cheat_id="motherlode_money_1000",
                   interaction_ref="interaction:invalid")

    def test_reject_duplicate_interactions_and_outcomes_across_channels(self):
        st = ingest(empty_state(), "hotkey_action", "key_001", T, mode="LIVE",
                    hotkey_id="MODE_LIVE", interaction_ref="interaction:shared")
        with self.assertRaisesRegex(HoverLearningError, "DUPLICATE_INTERACTION_REF"):
            ingest(st, "cheat_action", "cheat_001", T + 10,
                   cheat_id="motherlode", interaction_ref="interaction:shared")
        st = ingest(st, "outcome", "out_001", T + 20,
                    interaction_ref="interaction:shared", outcome="helpful",
                    evidence_ref="capture:proof", operator_reviewed=True)
        with self.assertRaisesRegex(HoverLearningError, "DUPLICATE_INTERACTION_OUTCOME"):
            ingest(st, "outcome", "out_002", T + 21,
                   interaction_ref="interaction:shared", outcome="helpful",
                   evidence_ref="capture:proofagain", operator_reviewed=True)

    def test_mixed_channels_window_expiry_and_time_regression(self):
        st = ingest(empty_state(), "hotkey_action", "key_001", T,
                    mode="LIVE", hotkey_id="MODE_LIVE",
                    interaction_ref="interaction:mode")
        st = ingest(st, "cheat_action", "cheat_001", T + 240000,
                    cheat_id="bb_showhiddenobjects",
                    interaction_ref="interaction:debug")
        r = evaluate(st, now_ms=T + 240000)["windows"]
        self.assertEqual([r[str(sec)]["action_observations"]
                          for sec in (180, 300, 600, 1800, 3600)], [1, 2, 2, 2, 2])
        with self.assertRaisesRegex(HoverLearningError, "HOVER_TIME_REGRESSION"):
            ingest(st, "cheat_action", "cheat_002", T + 1,
                   cheat_id="motherlode", interaction_ref="interaction:replay")

    def test_state_tampering_with_catalog_action_ref_rejected(self):
        st = ingest(empty_state(), "cheat_action", "cheat_001", T,
                    cheat_id="motherlode", interaction_ref="interaction:funds")
        st["events"][0]["action_ref"] = "cheat:unrelated"
        with self.assertRaisesRegex(HoverLearningError, "CORRUPT_HOVER_HISTORY"):
            evaluate(st, now_ms=T + 1)


class BehaviorListenerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.sid = "input_test_" + uuid.uuid4().hex[:16]
        activate(self.sid)

    def tearDown(self):
        deactivate(self.sid)

    def test_active_opt_in_listener_roundtrip_and_cli_catalog(self):
        ev = event("hotkey_action", "key_001", T, mode="LIVE",
                   hotkey_id="CHEAT_CONSOLE",
                   interaction_ref="interaction:console")
        with self.assertRaisesRegex(HostListenerError, "EXPLICIT_HOVER_OPT_IN_REQUIRED"):
            observe_hover(self.sid, ev)
        first = observe_hover(self.sid, ev, explicit_opt_in=True)
        self.assertEqual(first["evaluation"]["windows"]["180"]["hotkey_action_observations"], 1)
        second = observe_hover(self.sid, event(
            "cheat_action", "cheat_001", T + 100,
            cheat_id="bb_showhiddenobjects",
            interaction_ref="interaction:debug"), explicit_opt_in=True)
        self.assertEqual(second["evaluation"]["windows"]["180"]["cheat_action_observations"], 1)
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["behavior-catalog"])
        self.assertEqual(code, 0)
        result = json.loads(buf.getvalue())
        self.assertIn("motherlode", result["cheats"])
        self.assertNotIn("Money 100000", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
