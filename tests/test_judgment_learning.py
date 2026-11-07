"""Trifecta regression suite: reviewed Markov learner, abstention and safe CLI."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout
from io import StringIO

from betterinstincts.judgment_learning import (
    EXAMPLE_SCHEMA, QUERY_SCHEMA, JudgmentLearningError,
    learn, recommend, prequential_evaluate,
)
from scripts import judgment_learning as learning_cli

PATCH = "1.121.361.1020"
CONTEXT = {
    "scenario": "event_social", "need_state": "stable",
    "scene": "event", "previous_action": "socialize", "style": "social",
}


def example(index, action="sit_and_chat_here", outcome="helpful", context=None):
    return {
        "schema": EXAMPLE_SCHEMA, "game_version": PATCH, "platform": "windows",
        "context": dict(context or CONTEXT), "action": action,
        "outcome": outcome, "operator_reviewed": True, "opt_in": True,
        "observation_ref": f"capture:reviewed_{index:03d}",
    }


def query(context=None, **kwargs):
    base = {
        "schema": QUERY_SCHEMA, "game_version": PATCH, "platform": "windows",
        "context": dict(context or CONTEXT),
        "available_actions": ["socialize", "sit_and_chat_here", "rest"],
        "player_directed": False, "player_active": False, "scene_verified": True,
    }
    return {**base, **kwargs}


def trained(events):
    return learn(events, game_version=PATCH, platform="windows")


class JudgmentLearningTests(unittest.TestCase):
    def test_three_reviewed_examples_unlock_advice_not_execution(self):
        model = trained([example(i) for i in range(3)])
        result = recommend(model, query())
        self.assertEqual(result["state"], "ADVISORY_ONLY")
        self.assertEqual(result["suggested_action"], "sit_and_chat_here")
        self.assertFalse(result["execute_clicks"])
        self.assertEqual(result["support"], 3)

    def test_sparse_or_harmful_evidence_abstains(self):
        for events in ([example(0), example(1)],
                       [example(i, outcome="harmful") for i in range(4)],
                       [example(i, outcome="helpful" if i < 3 else "harmful") for i in range(5)]):
            with self.subTest(size=len(events)):
                self.assertEqual(recommend(trained(events), query())["state"], "ABSTAIN")

    def test_player_direction_and_activity_always_outrank_model(self):
        model = trained([example(i) for i in range(4)])
        for flag in ("player_active", "player_directed"):
            self.assertEqual(recommend(model, query(**{flag: True}))["reason"], "PLAYER_FIRST")

    def test_unverified_scene_and_unavailable_action_abstain(self):
        model = trained([example(i) for i in range(4)])
        self.assertEqual(recommend(model, query(scene_verified=False))["reason"], "SCENE_UNVERIFIED")
        self.assertEqual(recommend(model, query(available_actions=["rest"]))["state"], "ABSTAIN")

    def test_exact_patch_separation(self):
        model = trained([example(i) for i in range(3)])
        self.assertEqual(recommend(model, query(game_version="1.129.100.1000"))["reason"],
                         "PATCH_PROFILE_MISMATCH")
        with self.assertRaisesRegex(JudgmentLearningError, "PATCH_PROFILE_MISMATCH"):
            learn([example(99)], game_version="1.129.100.1000", platform="windows")

    def test_context_and_transition_conditioning_preserve_diversity(self):
        alternate = {**CONTEXT, "previous_action": "rest", "style": "solitary"}
        events = [example(i) for i in range(3)] + [
            example(i + 3, action="rest", context=alternate) for i in range(3)
        ]
        model = trained(events)
        self.assertEqual(recommend(model, query())["suggested_action"], "sit_and_chat_here")
        self.assertEqual(recommend(model, query(alternate))["suggested_action"], "rest")
        other = {**CONTEXT, "previous_action": "none"}
        self.assertEqual(recommend(model, query(other))["state"], "ABSTAIN")

    def test_tied_preferences_fail_closed_rather_than_choose_robotically(self):
        model = trained([example(i) for i in range(3)] +
                        [example(i + 3, action="socialize") for i in range(3)])
        self.assertEqual(recommend(model, query())["reason"], "AMBIGUOUS_PLAYER_PREFERENCE")

    def test_duplicate_and_unreviewed_events_rejected(self):
        with self.assertRaisesRegex(JudgmentLearningError, "DUPLICATE_OBSERVATION_IN_BATCH"):
            trained([example(1), example(1)])
        for bad in (
            {**example(1), "operator_reviewed": False},
            {**example(1), "opt_in": False},
            {**example(1), "user_name": "do-not-store"},
            {**example(1), "observation_ref": "C:/Users/private/save"},
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(JudgmentLearningError):
                    trained([bad])

    def test_incremental_learning_is_patch_scoped_and_bounded(self):
        old = trained([example(i) for i in range(2)])
        newer = learn([example(3)], game_version=PATCH, platform="windows", prior=old)
        self.assertEqual(recommend(newer, query())["state"], "ADVISORY_ONLY")
        with self.assertRaisesRegex(JudgmentLearningError, "PATCH_PROFILE_MISMATCH"):
            learn([example(4)], game_version="1.129.100.1000",
                  platform="windows", prior=old)

    def test_prequential_predicts_before_learning_no_leakage(self):
        result = prequential_evaluate([example(i) for i in range(4)],
                                      game_version=PATCH, platform="windows")
        self.assertEqual(result["reviewed_examples"], 4)
        self.assertEqual(result["suggestions_issued"], 1)
        self.assertEqual(result["correct_helpful_actions"], 1)
        self.assertEqual(result["coverage"], 0.25)
        self.assertEqual(result["precision_when_issued"], 1.0)

    def test_cli_explicit_consent_and_dist_guard(self):
        with patch.object(learning_cli, "OUTPUT", Path(tempfile.gettempdir()) / "bi-test-private"):
            out = StringIO()
            with redirect_stdout(out):
                exit_code = learning_cli.main([
                    "train", "--reviewed-examples", "/etc/passwd", "--game-version", PATCH,
                    "--platform", "windows", "--model-out", "/tmp/out.json",
                ])
            self.assertEqual(exit_code, 2)
            self.assertEqual(json.loads(out.getvalue())["reason"], "EXPLICIT_OPT_IN_REQUIRED")
            out = StringIO()
            with redirect_stdout(out):
                exit_code = learning_cli.main([
                    "train", "--reviewed-examples", "/etc/passwd", "--game-version", PATCH,
                    "--platform", "windows", "--model-out", "/tmp/out.json",
                    "--explicit-opt-in",
                ])
            self.assertEqual(exit_code, 2)
            self.assertEqual(json.loads(out.getvalue())["reason"], "LEARNING_PATH_OUTSIDE_DIST")

    def test_cli_end_to_end_bounded_local_artifact(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "dist" / "judgment-learning"
            root.mkdir(parents=True)
            events = root / "reviewed.json"
            events.write_text(json.dumps([example(i) for i in range(4)]), encoding="utf-8")
            with patch.object(learning_cli, "ROOT", Path(folder)), patch.object(learning_cli, "OUTPUT", root):
                out = StringIO()
                with redirect_stdout(out):
                    code = learning_cli.main([
                        "train", "--reviewed-examples", events.as_posix(), "--game-version", PATCH,
                        "--platform", "windows", "--model-out", (root / "model.json").as_posix(),
                        "--explicit-opt-in", "--evaluation-out", (root / "eval.json").as_posix(),
                    ])
                self.assertEqual(code, 0, out.getvalue())
                model = json.loads((root / "model.json").read_text())
                self.assertEqual(recommend(model, query())["state"], "ADVISORY_ONLY")
                self.assertNotIn("observation_ref", json.dumps(model))
                self.assertNotIn("user_name", json.dumps(model))


if __name__ == "__main__":
    unittest.main()
