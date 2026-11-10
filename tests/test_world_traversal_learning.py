"""Offline world-scene highlight and observed-outcome learning regressions."""
from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path

from betterinstincts.world_traversal_learning import (
    WorldTraversalLearningError, assess_highlight_continuity, empty_model,
    learn_observed_attempts, rank_strategies, evaluate_holdout, load_contract,
)
from betterinstincts.host_stack import evaluate_turn

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT / "tests/fixtures/world-traversal-learning.v1.json").read_text())
SIX = dict.fromkeys(("hunger", "bladder", "energy", "hygiene", "fun", "social"), 0.8)


def frames():
    return copy.deepcopy(FIXTURE["frames"])


def assess(events=None, **kwargs):
    events = events if events is not None else frames()
    return assess_highlight_continuity(
        target_id="plant-17", frames=events,
        capture_ref=events[-1]["capture_ref"], camera_revision="camera:42", **kwargs)


class HighlightTests(unittest.TestCase):
    def test_contract_is_evaluate_only(self):
        cfg = load_contract()
        self.assertFalse(cfg["boundaries"]["execute_allowed_default"])
        self.assertIn("AUTO_RECLICK", cfg["boundaries"]["forbidden"])

    def test_two_fresh_positive_cues_lock_target_but_not_click(self):
        out = assess()
        self.assertEqual(out["state"], "LOCKED")
        self.assertTrue(out["highlight_locked"])
        self.assertFalse(out["execute_allowed"])
        self.assertFalse(out["click_ready"])

    def test_sustained_absence_is_lost(self):
        seq = frames()
        for f in seq:
            for cue in f["highlight_cues"]:
                cue["state"] = "ABSENT"
        self.assertEqual(assess(seq)["state"], "HIGHLIGHT_LOST")

    def test_absent_highlight_has_no_id_and_still_registers_lost(self):
        seq = frames()
        for frame in seq:
            frame["highlight_target_id"] = None
            for cue in frame["highlight_cues"]:
                cue["state"] = "ABSENT"
        result = assess(seq)
        self.assertEqual(result["state"], "HIGHLIGHT_LOST")
        self.assertFalse(result["highlight_locked"])
        self.assertFalse(result["execute_allowed"])

    def test_present_highlight_without_identity_is_unverified(self):
        seq = frames()
        seq[-1]["highlight_target_id"] = None
        self.assertEqual(assess(seq)["state"], "HIGHLIGHT_UNVERIFIED")

    def test_one_frame_flicker_never_succeeds_or_confirms_lost(self):
        seq = frames()
        for cue in seq[-1]["highlight_cues"]:
            cue["state"] = "ABSENT"
        self.assertEqual(assess(seq)["state"], "HIGHLIGHT_TRANSIENT")

    def test_single_frame_yields(self):
        self.assertEqual(assess(frames()[-1:])["state"], "HIGHLIGHT_UNVERIFIED")

    def test_camera_change_cancels_target(self):
        seq = frames()
        seq[-1]["camera_revision"] = "camera:43"
        self.assertEqual(assess(seq)["state"], "CAMERA_CHANGED_REACQUIRE")

    def test_target_identity_change_cancels_target(self):
        seq = frames()
        seq[-1]["highlight_target_id"] = "another-plant"
        self.assertEqual(assess(seq)["state"], "TARGET_IDENTITY_CHANGED")

    def test_pointer_leaves_target_yields_without_false_loss(self):
        seq = frames()
        seq[-1]["pointer_context"] = "AWAY"
        self.assertEqual(assess(seq)["state"], "HIGHLIGHT_NOT_EXPECTED")

    def test_occluded_or_disappeared_targets_cannot_lock(self):
        for key, value, expected in [
            ("occluded", True, "TARGET_OCCLUDED"),
            ("target_visible", False, "TARGET_LOST"),
        ]:
            seq = frames()
            seq[-1][key] = value
            with self.subTest(key=key):
                self.assertEqual(assess(seq)["state"], expected)

    def test_unknown_or_conflicting_cues_abstain(self):
        seq = frames()
        seq[-1]["highlight_cues"][0]["state"] = "ABSENT"
        self.assertEqual(assess(seq)["state"], "HIGHLIGHT_AMBIGUOUS")
        seq = frames()
        seq[-1]["highlight_cues"][0]["confidence"] = 0.1
        self.assertEqual(assess(seq)["state"], "HIGHLIGHT_UNVERIFIED")

    def test_conflicting_box_track_cancels_even_when_highlight_positive(self):
        seq = frames()
        seq[-1]["bbox_client"] = [900, 350, 1000, 480]
        self.assertEqual(assess(seq)["state"], "TARGET_TRACK_DRIFT")

    def test_replays_and_spoofed_sources_rejected(self):
        seq = frames()
        seq[-1]["capture_ref"] = seq[0]["capture_ref"]
        with self.assertRaisesRegex(WorldTraversalLearningError, "REPLAY"):
            assess(seq)
        seq = frames()
        seq[-1]["highlight_cues"][0]["source"] = "CURSOR_AGENT_GUESS"
        with self.assertRaisesRegex(WorldTraversalLearningError, "UNTRUSTED"):
            assess(seq)

    def test_missing_capture_or_low_object_confidence_blocks(self):
        seq = frames()
        seq[-1]["object_confidence"] = 0.2
        self.assertEqual(assess(seq)["state"], "HIGHLIGHT_UNVERIFIED")
        self.assertEqual(
            assess_highlight_continuity(target_id="plant-17", frames=frames(),
                                        capture_ref="capture:stale")["state"],
            "HIGHLIGHT_UNVERIFIED",
        )


class LearningTests(unittest.TestCase):
    def test_online_update_ranks_observed_strategy_not_personal_names(self):
        original = empty_model()
        out = learn_observed_attempts(original, FIXTURE["train"])
        self.assertEqual(out["accepted"], 20)
        self.assertEqual(original["contexts"], {})
        rank = rank_strategies(out["model"], [
            FIXTURE["train"][0], FIXTURE["train"][-1],
        ])
        self.assertEqual(rank["state"], "ADVISORY_RANKING")
        self.assertEqual(rank["recommended_context"].split("|")[-1], "ZOOM_HOVER")
        self.assertNotIn("plant-17", json.dumps(out["model"]))
        self.assertFalse(rank["execute_allowed"])

    def test_repeat_in_single_batch_has_one_successful_evidence_unit(self):
        attempt = copy.deepcopy(FIXTURE["train"][0])
        out = learn_observed_attempts(empty_model(), [attempt, copy.deepcopy(attempt)])
        self.assertEqual((out["accepted"], out["abstained"], out["replayed"]), (1, 1, 1))
        self.assertEqual(len(out["model"]["seen_attempts"]), 1)
        self.assertEqual(sum(c["successes"] for c in out["model"]["contexts"].values()), 1)

    def test_repeat_across_snapshots_and_strategy_renaming_abstains(self):
        attempt = copy.deepcopy(FIXTURE["train"][0])
        first = learn_observed_attempts(empty_model(), [attempt])["model"]
        renamed = copy.deepcopy(attempt)
        renamed["strategy"] = "BLIND_OFFSET"
        renamed["after_capture_ref"] = "capture:forged-outcome"
        replay = learn_observed_attempts(first, [renamed, attempt])
        self.assertEqual((replay["accepted"], replay["replayed"]), (0, 2))
        self.assertEqual(replay["model"], first)

    def test_missing_interruption_attestation_is_not_a_label(self):
        attempt = copy.deepcopy(FIXTURE["train"][0])
        del attempt["player_interrupted"]
        self.assertEqual(learn_observed_attempts(empty_model(), [attempt])["accepted"], 0)

    def test_legacy_training_counts_without_replay_ids_fail_closed(self):
        trained = learn_observed_attempts(empty_model(), FIXTURE["train"][:1])["model"]
        del trained["seen_attempts"]
        with self.assertRaisesRegex(WorldTraversalLearningError, "LEGACY_MODEL_MISSING_REPLAY_PROOF"):
            rank_strategies(trained, [FIXTURE["train"][0]])

    def test_replay_history_is_checked_for_corruption_and_budget(self):
        valid = learn_observed_attempts(empty_model(), FIXTURE["train"][:2])["model"]
        invalid = copy.deepcopy(valid)
        invalid["seen_attempts"][0] = "fake"
        with self.assertRaisesRegex(WorldTraversalLearningError, "MODEL_REPLAY_HISTORY_INVALID"):
            rank_strategies(invalid, [FIXTURE["train"][0]])
        invalid = copy.deepcopy(valid)
        invalid["seen_attempts"].pop()
        with self.assertRaisesRegex(WorldTraversalLearningError, "MODEL_REPLAY_HISTORY_COUNT_MISMATCH"):
            rank_strategies(invalid, [FIXTURE["train"][0]])
        cfg = load_contract()
        cfg["learning"]["max_seen_attempts"] = 1
        model = empty_model()
        with self.assertRaisesRegex(WorldTraversalLearningError, "MODEL_REPLAY_HISTORY_BUDGET_EXCEEDED"):
            learn_observed_attempts(model, FIXTURE["train"][:2], cfg=cfg)
        self.assertEqual(model["contexts"], {})

    def test_empty_or_sparse_model_must_abstain(self):
        self.assertEqual(rank_strategies(empty_model(), [FIXTURE["train"][0]])["state"],
                         "ABSTAIN_INSUFFICIENT_LABELS")
        one = learn_observed_attempts(empty_model(), FIXTURE["train"][:1])["model"]
        self.assertEqual(rank_strategies(one, [FIXTURE["train"][0]])["state"],
                         "ABSTAIN_INSUFFICIENT_LABELS")

    def test_claimed_success_without_independent_outcome_cannot_train(self):
        invalid = copy.deepcopy(FIXTURE["train"][0])
        invalid["observed_result"] = "NO_RESPONSE"
        no_receipt = copy.deepcopy(FIXTURE["train"][0])
        no_receipt["evidence_source"] = "CURSOR_AGENT_GUESS"
        interrupted = copy.deepcopy(FIXTURE["train"][0])
        interrupted["player_interrupted"] = True
        wrong_target = copy.deepcopy(FIXTURE["train"][0])
        wrong_target["observed_target_id"] = "other-plant"
        out = learn_observed_attempts(empty_model(),
                                      [invalid, no_receipt, interrupted, wrong_target])
        self.assertEqual((out["accepted"], out["abstained"]), (0, 4))

    def test_holdout_metrics_distinguish_fixture_from_live_accuracy(self):
        trained = learn_observed_attempts(empty_model(), FIXTURE["train"])["model"]
        score = evaluate_holdout(trained, FIXTURE["holdout"])
        self.assertEqual(score["evaluated"], 4)
        self.assertEqual(score["coverage"], 1.0)
        self.assertLess(score["brier"], score["baseline_brier"])
        self.assertFalse(score["execute_allowed"])

    def test_holdout_replays_training_and_itself_abstain(self):
        trained = learn_observed_attempts(empty_model(), FIXTURE["train"])["model"]
        training_example = copy.deepcopy(FIXTURE["train"][0])
        fresh_example = copy.deepcopy(FIXTURE["holdout"][0])
        report = evaluate_holdout(trained, [training_example, fresh_example, copy.deepcopy(fresh_example)])
        self.assertEqual((report["evaluated"], report["abstained"], report["replayed"]), (1, 2, 2))
        self.assertEqual(report["coverage"], round(1 / 3, 6))

    def test_invalid_model_counts_and_unbounded_batch_rejected(self):
        corrupted = empty_model()
        corrupted["contexts"] = {"1|2|3|4|5|6": {"successes": -1, "failures": 1}}
        with self.assertRaisesRegex(WorldTraversalLearningError, "MODEL_COUNT"):
            rank_strategies(corrupted, [FIXTURE["train"][0]])
        with self.assertRaisesRegex(WorldTraversalLearningError, "BUDGET"):
            learn_observed_attempts(empty_model(), FIXTURE["train"] * 10)


class HostStackGateTests(unittest.TestCase):
    def _host_target(self, seq):
        observation = {
            "source": "HOST_CAPTURE", "target_id": "plant-17",
            "capture_ref": "capture:2", "camera_revision": "camera:42",
            "target_visible": True, "occluded": False,
            "bbox_client": [620, 360, 720, 490], "framing_attempts": 0,
        }
        return evaluate_turn(
            SIX, capture_ref="capture:2", client_width=1920, client_height=1080,
            world_target={"target_id": "plant-17", "observation": observation,
                          "highlight_frames": seq},
        )

    def test_highlight_lock_still_needs_independent_host_admission(self):
        out = self._host_target(frames())
        self.assertEqual(out["world_target_framing"]["highlight_tracking"]["state"], "LOCKED")
        self.assertEqual(out["next_gate"], "WORLD_TARGET_AWAIT_HOST_ADMISSION")
        self.assertFalse(out["fallback"]["execute_allowed"])

    def test_highlight_lost_with_missing_id_revokes_world_candidate(self):
        seq = frames()
        for frame in seq:
            frame["highlight_target_id"] = None
            for cue in frame["highlight_cues"]:
                cue["state"] = "ABSENT"
        out = self._host_target(seq)
        self.assertEqual(out["world_target_framing"]["highlight_tracking"]["state"], "HIGHLIGHT_LOST")
        self.assertEqual(out["next_gate"], "WORLD_HIGHLIGHT_REACQUIRE_REQUIRED")
        self.assertIsNone(out["world_target_framing"]["click_candidate"])
        self.assertFalse(out["world_target_framing"]["click_ready"])

    def test_highlight_lost_blocks_otherwise_framed_world_target(self):
        seq = frames()
        for f in seq:
            for cue in f["highlight_cues"]:
                cue["state"] = "ABSENT"
        out = self._host_target(seq)
        self.assertEqual(out["world_target_framing"]["highlight_tracking"]["state"], "HIGHLIGHT_LOST")
        self.assertEqual(out["next_gate"], "WORLD_HIGHLIGHT_REACQUIRE_REQUIRED")
        self.assertIsNone(out["world_target_framing"]["click_candidate"])
        self.assertFalse(out["world_target_framing"]["click_ready"])

    def test_player_takeover_outranks_valid_highlight(self):
        # No effect is admitted even when the highlight is confidently tracked.
        observation = {
            "source": "HOST_CAPTURE", "target_id": "plant-17",
            "capture_ref": "capture:2", "camera_revision": "camera:42",
            "target_visible": True, "occluded": False,
            "bbox_client": [620, 360, 720, 490],
        }
        out = evaluate_turn(SIX, capture_ref="capture:2", client_width=1920,
                            client_height=1080, player_directed=True,
                            world_target={"target_id":"plant-17", "observation":observation,
                                          "highlight_frames":frames()})
        self.assertEqual(out["next_gate"], "RESPECT_PLAYER_OR_BUSY_STATE")
