"""Installed callback lifecycle with a deterministic clock and semantic frames."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from betterinstincts.installed_player_runtime import Frame, MANIFEST, start_installed

BUILD = "1.121.361.1020"
NEEDS = dict.fromkeys(("hunger", "bladder", "energy", "hygiene", "fun", "social"), 0.8)
CONTEXT = {"scenario": "event_social", "style": "social", "previous_action": "socialize",
           "available_actions": ["socialize", "sit_and_chat_here"]}


class InstalledRuntimeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "Mods" / "BetterInstincts"
        self.root.mkdir(parents=True)
        self.manifest = self.root / MANIFEST
        self.manifest.write_text(json.dumps({
            "schema": "betterinstincts.native-ecology-ownership/v1",
            "game_build": BUILD, "installed_player_runtime": True,
        }))
        self.clock = Mock(return_value=10)
        self.adapter = Mock(game_build=BUILD)
        self.adapter.register = Mock(return_value=True)
        self.adapter.analyze = Mock(return_value=({"socialize": "baseline-id",
                                                    "sit_and_chat_here": "learned-id"}, None, NEEDS))
        self.adapter.submit = Mock(return_value="QUEUED")
        self.adapter.reconcile = Mock(return_value=False)

    def start(self, opt_in=True):
        return start_installed(self.adapter, exact_build=BUILD, owned_dir=self.root,
                               learning_opt_in=opt_in, clock=self.clock)

    def frame(self, **kwargs):
        return replace(Frame(BUILD, "game-run", "house-one", "sim:sim-one", True, True, True,
                             False, False, True, 3, 10, 5, "capture:frame-one"), **kwargs)

    def event(self, kind, seq, **kwargs):
        return {"kind": kind, "sequence": seq, "run": "game-run", "household": "house-one",
                "platform": "windows", **kwargs}

    def test_installed_manifest_without_successful_registration_is_not_running(self):
        self.assertIsNone(self.start(opt_in=False))
        self.adapter.register.assert_not_called()
        self.adapter.register.return_value = False
        with self.assertRaisesRegex(ValueError, "REGISTRATION_UNVERIFIED"):
            self.start()
        self.adapter.submit.assert_not_called()

    def test_exact_five_seconds_and_fresh_scope_recheck(self):
        runtime = self.start()
        self.adapter.frame.side_effect = [
            self.frame(idle_seconds=4.999),
            self.frame(), self.frame(capture="capture:frame-two"),
        ]
        self.assertEqual(runtime.cycle(), "YIELD_TO_PLAYER")
        self.adapter.analyze.assert_called_once()
        self.adapter.submit.assert_not_called()
        self.assertEqual(runtime.cycle(), "QUEUED")
        self.adapter.submit.assert_called_once()

    def test_input_during_analysis_invalidates_even_when_second_probe_is_idle(self):
        runtime = self.start()
        self.adapter.frame.side_effect = [
            self.frame(), self.frame(capture="capture:frame-two", input_generation=4),
        ]
        self.assertEqual(runtime.cycle(), "YIELD_TO_PLAYER")
        self.adapter.submit.assert_not_called()

    def test_foreground_scope_and_player_queue_must_stay_eligible(self):
        runtime = self.start()
        for changed in ({"actor": "sim:sim-two"}, {"player_queue": True},
                        {"player_active": True}, {"activity_trusted": False}, {"observed_at": 8}, {"playing": False},
                        {"save_admitted": False}, {"run": "another-run"}):
            self.adapter.frame.side_effect = [
                self.frame(), self.frame(capture="capture:frame-two", **changed),
            ]
            self.assertEqual(runtime.cycle(), "YIELD_TO_PLAYER", changed)
        self.adapter.submit.assert_not_called()

    def test_learning_while_yielded_changes_idle_ranking(self):
        self.start()
        callback = self.adapter.register.call_args.kwargs["observe"]
        for index in range(3):
            picked = self.frame(player_active=True, capture=f"capture:choice-{index}")
            choice = self.event("choice", 2 * index, **CONTEXT, owner="PLAYER",
                                action="sit_and_chat_here", interaction=f"choice-{index}")
            self.assertEqual(callback(picked, choice, NEEDS)["state"], "PLAYER_CHOICE_PENDING")
            completed = self.frame(player_active=True, capture=f"capture:outcome-{index}")
            outcome = self.event("outcome", 2 * index + 1, completed=True, goal_delta=0.2,
                                 effect_capture=f"capture:effect-{index}", interaction=f"choice-{index}")
            self.assertEqual(callback(completed, outcome, NEEDS)["state"], "PLAYER_OUTCOME_HELPFUL")
        self.adapter.submit.assert_not_called()
        # A new registered session reads the same local evidence.
        runtime = self.start()
        self.adapter.analyze.return_value = (
            {"socialize": "baseline-id", "sit_and_chat_here": "learned-id"},
            self.event("query", 10, **CONTEXT), NEEDS,
        )
        self.adapter.frame.side_effect = [self.frame(), self.frame(capture="capture:frame-two")]
        self.assertEqual(runtime.cycle(), "QUEUED")
        self.assertEqual(self.adapter.submit.call_args.args[0], "learned-id")

    def test_uncertain_submit_stays_in_reconciliation_without_repeating(self):
        runtime = self.start()
        self.adapter.submit.side_effect = RuntimeError("lost ACK")
        self.adapter.frame.side_effect = [
            self.frame(), self.frame(capture="capture:frame-two"),
            self.frame(player_active=True), self.frame(),
        ]
        for _ in range(3):
            self.assertEqual(runtime.cycle(), "NATIVE_DISPATCH_RECONCILIATION")
        self.adapter.submit.assert_called_once()
        self.assertEqual(self.adapter.reconcile.call_count, 2)

    def test_nonconsecutive_proposal_cannot_replay(self):
        runtime = self.start()
        self.adapter.reconcile.return_value = True
        for proposal, expected in (("action-one", "QUEUED"), ("action-two", "QUEUED"),
                                   ("action-one", "DUPLICATE_NATIVE_PROPOSAL")):
            self.adapter.analyze.return_value = ({"socialize": proposal}, None, NEEDS)
            self.adapter.frame.side_effect = [self.frame(), self.frame(capture="capture:frame-two")]
            self.assertEqual(runtime.cycle(), expected)
        self.assertEqual(self.adapter.submit.call_count, 2)

    def test_claimed_success_without_fresh_player_signal_never_dispatches(self):
        runtime = self.start()
        self.adapter.frame.return_value = self.frame(activity_trusted=False)
        self.assertEqual(runtime.cycle(), "YIELD_TO_PLAYER")
        self.adapter.analyze.assert_called_once()
        self.adapter.submit.assert_not_called()
