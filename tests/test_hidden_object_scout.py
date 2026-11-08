"""Deterministic multi-hour scout tests. No Windows process, camera or SendInput."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from betterinstincts.hidden_object_discovery import p04_guide
from betterinstincts.hidden_object_scout import (
    ScoutError, change_mode, load_goal, next_search, record_batch, start, status,
)


def initial_receipt():
    return {
        "schema": "betterinstincts.hidden-object-discovery-receipt/v1",
        "exact_game_build": "1.121.361.1020",
        "platform": "windows", "save_ref": "save:lab-one",
        "save_attestation": "OPERATOR_ATTESTED_DISPOSABLE_LAB",
        "player_explicit_opt_in": True, "player_idle": True,
        "host_control_lease": "HOST_EXCLUSIVE", "game_paused": True,
        "capture_quality": "CONTENT_PRESENT", "viewport": "NORMAL",
        "final_scene_id": "build_buy", "live_edit_requested": False,
        "game_speed_unchanged": True, "player_queue_unchanged": True,
        "scene_cues": {"visual_ref": "capture:setup", "operator_ref": "operator:ack"},
        "steps": [
            {
                "step_id": x["step_id"], "observed_gate": x["proof_gate"],
                "control_permit_ref": "permit:" + str(i),
                "observation_ref": "capture:setup-" + str(i), "outcome": "OBSERVED",
            }
            for i, x in enumerate(p04_guide()["steps"])
        ],
        "catalog_entries": [
            {"operator_reviewed": True, "result_visible": True,
             "capture_ref": "capture:p04-item", "item_label": "P04 initial example",
             "price_simoleons": 12}
        ],
    }


def current(at, **kwargs):
    observation = {
        "exact_game_build": "1.121.361.1020", "platform": "windows",
        "save_ref": "save:lab-one", "scene_id": "build_buy",
        "visual_cue_ref": "capture:current-" + str(at),
        "operator_cue_ref": "operator:current-" + str(at),
        "observed_at_unix": at,
        "capture_quality": "CONTENT_PRESENT", "viewport": "NORMAL",
        "save_attestation": "OPERATOR_ATTESTED_DISPOSABLE_LAB",
        "player_explicit_opt_in": True, "player_idle": True,
        "host_control_lease": "HOST_EXCLUSIVE", "game_paused": True,
    }
    observation.update(kwargs)
    return observation


def batch(plan, *, number=1, label="Toothbrush", reviewed=False,
          price=None, no_match=False):
    items = [] if no_match else [{
        "item_label": label, "pack_name": "Base",
        "capture_ref": "capture:item-" + str(number),
        "operator_reviewed": reviewed, "result_visible": True,
    }]
    if items and reviewed:
        items[0]["price_simoleons"] = price
    return {
        "batch_id": plan["batch_id"],
        "category": plan["category"], "search_term": plan["search_term"],
        "search_capture_ref": "capture:search-" + str(number),
        "result_state": "NO_MATCH" if no_match else "ITEMS_CAPTURED",
        "items": items,
    }


class LongRunScoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch("betterinstincts.hidden_object_scout.STATE_ROOT", Path(self.tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.initial = initial_receipt()

    def test_contract_defaults_are_bounded_four_hours_and_no_daemon(self):
        cfg = load_goal()
        self.assertEqual(cfg["objectives"]["default_duration_minutes"], 240)
        self.assertEqual(cfg["objectives"]["target_unique_candidates"], 40)
        self.assertLessEqual(cfg["objectives"]["max_batches"], 100)
        self.assertEqual(cfg["engine"], "SCOPED_READ_ONLY_CHECKPOINTS_NO_GAME_INPUT")
        self.assertIn("no_SendInput", cfg["regression_safety"])
        self.assertIn("no_scheduled_task", cfg["regression_safety"])

    def test_session_start_is_opt_in_and_safe(self):
        info = start("lab-scout", now=1000)
        self.assertEqual(info["state"], "ACTIVE")
        self.assertEqual(info["remaining_seconds"], 14400)
        self.assertEqual(info["metrics"]["completed_batches"], 0)
        self.assertIsNone(info["pinned_build"])
        with self.assertRaisesRegex(ScoutError, "SCOUT_SESSION_ALREADY_EXISTS"):
            start("lab-scout", now=1000)
        for bad in ("../escape", "/etc/passwd", "", "a" * 65):
            with self.subTest(bad=bad):
                with self.assertRaises(ScoutError):
                    start(bad, now=1000)
        with self.assertRaisesRegex(ScoutError, "INVALID_MISSION_DURATION"):
            start("too-long", minutes=900, now=1000)

    def test_every_next_requires_actual_current_host_evidence(self):
        start("scout", now=1000)
        good = next_search("scout", current(1000), self.initial, now=1000)
        self.assertEqual(good["state"], "SCOUT_SEARCH_PROPOSED_NOT_AUTHORIZED")
        self.assertFalse(good["host_action_authorized"])
        self.assertFalse(good["repeat_cheat_console_setup"])
        self.assertEqual(good["category"], "clutter")
        self.assertEqual(good["search_term"], "debug")
        self.assertEqual(good["max_items"], 12)
        self.assertEqual(next_search("scout", current(1000), self.initial, now=1000)["batch_id"], good["batch_id"])
        for overrides in [
            {"exact_game_build": "1.121.361.1021"},
            {"save_ref": "save:someone-else"}, {"game_paused": False},
            {"host_control_lease": None}, {"player_idle": False},
            {"scene_id": "live_viewport_black"}, {"capture_quality": "BLACK"},
            {"visual_cue_ref": ""}, {"player_explicit_opt_in": False},
        ]:
            with self.subTest(overrides=overrides):
                result = next_search("scout", current(1000, **overrides), self.initial, now=1000)
                self.assertEqual(result["state"], "ABSTAIN")
                self.assertIsNone(result["next_action"])
        self.assertEqual(next_search("scout", current(1000), self.initial, now=1250)["state"], "ABSTAIN")
        wrong_setup = dict(self.initial)
        wrong_setup["steps"] = []
        self.assertIn("P04_SETUP_RECEIPT_INCOMPLETE",
                      next_search("scout", current(1000), wrong_setup, now=1000)["problems"])

    def test_multi_batch_rotation_checkpoint_and_idempotence(self):
        start("scout", now=1000)
        initial = next_search("scout", current(1000), self.initial, now=1000)
        first = batch(initial, number=1, reviewed=False)
        result = record_batch("scout", first, current(1000), self.initial, now=1000)
        self.assertEqual(result["new_unique"], 1)
        self.assertEqual(result["metrics"]["pending_review"], 1)
        self.assertEqual(result["metrics"]["reviewed_free"], 0)
        same = record_batch("scout", first, current(1000), self.initial, now=1001)
        self.assertEqual(same["state"], "BATCH_ALREADY_RECORDED")
        with self.assertRaisesRegex(ScoutError, "BATCH_RETRY_CONFLICT"):
            record_batch("scout", {**first, "search_capture_ref": "capture:modified"}, current(1000),
                         self.initial, now=1001)
        self.assertEqual(next_search("scout", current(1001), self.initial, now=1001)["state"], "COOLDOWN")
        second = next_search("scout", current(1020), self.initial, now=1020)
        self.assertEqual(second["category"], "collectibles")
        duplicate = batch(second, number=2, label="Toothbrush", reviewed=True, price=0)
        result2 = record_batch("scout", duplicate, current(1020), self.initial, now=1020)
        self.assertEqual(result2["new_unique"], 0)
        self.assertEqual(result2["promoted_reviews"], 1)
        self.assertEqual(result2["metrics"]["reviewed_free"], 1)
        self.assertEqual(result2["metrics"]["unique_candidates"], 1)
        third = next_search("scout", current(1040), self.initial, now=1040)
        self.assertEqual(third["category"], "landscape")
        result3 = record_batch("scout", batch(third, number=3, no_match=True),
                               current(1040), self.initial, now=1040)
        self.assertEqual(result3["metrics"]["completed_batches"], 3)
        self.assertEqual(result3["metrics"]["zero_new_streak"], 1)
        self.assertEqual(status("scout", now=1040)["pinned_save_ref"], "save:lab-one")

    def test_unreviewed_price_is_never_free_or_accepted(self):
        start("scout", now=1000)
        plan = next_search("scout", current(1000), self.initial, now=1000)
        unsafe = batch(plan, number=4, reviewed=False)
        unsafe["items"][0]["price_simoleons"] = 0
        with self.assertRaisesRegex(ScoutError, "UNREVIEWED_PRICE_MUST_NOT_BE_PROMOTED"):
            record_batch("scout", unsafe, current(1000), self.initial, now=1000)
        self.assertEqual(status("scout", now=1000)["metrics"]["completed_batches"], 0)
        safe = batch(plan, number=4, reviewed=True, price=25)
        recorded = record_batch("scout", safe, current(1000), self.initial, now=1000)
        self.assertEqual(recorded["metrics"]["reviewed_priced"], 1)
        self.assertEqual(recorded["metrics"]["reviewed_free"], 0)

    def test_wrong_batch_and_duplicate_refs_fail_without_state_mutation(self):
        start("scout", now=1000)
        plan = next_search("scout", current(1000), self.initial, now=1000)
        wrong = batch(plan, number=5)
        wrong["batch_id"] = "arbitrary"
        with self.assertRaisesRegex(ScoutError, "BATCH_ID_OR_SEARCH_MISMATCH"):
            record_batch("scout", wrong, current(1000), self.initial, now=1000)
        same_capture = batch(plan, number=5)
        same_capture["items"][0]["capture_ref"] = same_capture["search_capture_ref"]
        with self.assertRaisesRegex(ScoutError, "BATCH_CAPTURE_COLLISION"):
            record_batch("scout", same_capture, current(1000), self.initial, now=1000)
        self.assertEqual(status("scout", now=1000)["metrics"]["completed_batches"], 0)

    def test_pause_resume_stop_and_deadline(self):
        start("scout", minutes=30, now=1000)
        self.assertEqual(change_mode("scout", "pause", now=1200)["state"], "PAUSED")
        self.assertEqual(next_search("scout", current(1200), self.initial, now=1200)["state"], "PAUSED")
        info = change_mode("scout", "resume", now=1300)
        self.assertEqual(info["remaining_seconds"], 1600)
        self.assertEqual(status("scout", now=2900)["state"], "TIMEBOX_EXPIRED")
        self.assertEqual(change_mode("scout", "stop", now=2900)["state"], "STOPPED")
        with self.assertRaisesRegex(ScoutError, "MISSION_NOT_PAUSED"):
            change_mode("scout", "resume", now=3000)

    def test_invalid_setup_or_scope_never_grants_game_control(self):
        start("scout", now=1000)
        bad = dict(self.initial, save_ref="save:other")
        self.assertEqual(next_search("scout", current(1000), bad, now=1000)["state"], "ABSTAIN")
        self.assertFalse(next_search("scout", current(1000), self.initial, now=1000)["host_action_authorized"])

    def test_cli_compiles(self):
        source = Path(__file__).resolve().parents[1] / "scripts" / "hidden_object_scout.py"
        compile(source.read_text(encoding="utf-8"), str(source), "exec")


if __name__ == "__main__":
    unittest.main()
