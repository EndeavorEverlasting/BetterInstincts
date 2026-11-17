"""Installed callback lifecycle with a deterministic clock and semantic frames."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from betterinstincts.installed_player_runtime import Frame, MANIFEST, start_installed
from tests.test_activity_chain import row, route, snapshot

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
                             False, False, True, 3, 10, 5, "capture:frame-one",
                             save_ref="lab-save"), **kwargs)

    def event(self, kind, seq, **kwargs):
        return {"kind": kind, "sequence": seq, "run": "game-run", "household": "house-one",
                "platform": "windows", **kwargs}

    def test_restock_holds_native_decisions_until_released_and_rechecks_before_submit(self):
        self.start()
        callback = self.adapter.register.call_args.kwargs["cycle"]
        self.adapter.frame.side_effect = [
            self.frame(restock_has_control=True),
            self.frame(restock_has_control=None),
            self.frame(), self.frame(capture="capture:second", restock_has_control=True),
            self.frame(), self.frame(capture="capture:third"),
        ]
        self.assertEqual(callback(), "RESTOCK_CONTROL_HELD_OR_UNVERIFIED")
        self.assertEqual(callback(), "RESTOCK_CONTROL_HELD_OR_UNVERIFIED")
        self.adapter.analyze.assert_not_called()
        self.assertEqual(callback(), "YIELD_TO_PLAYER")
        self.adapter.submit.assert_not_called()
        self.assertEqual(callback(), "QUEUED")
        self.adapter.submit.assert_called_once()

    def enable_activity_chain(self):
        data = json.loads(self.manifest.read_text())
        self.manifest.write_text(json.dumps({**data, "installed_activity_chain": True}))
        self.adapter.analyze.return_value = ({}, None, NEEDS)
        self.adapter.read_activity_chain.side_effect = self.activity_packet
        return self.start()

    def activity_packet(self, frame, **observed):
        return {
            "game_build": frame.game_build, "run": frame.run,
            "save_ref": "lab-save", "goal_ref": "career-artifact",
            "snapshot": snapshot(
                sim_ref=frame.actor, household_ref=frame.household, capture_ref=frame.capture,
                mode="PLAY" if frame.playing else "PLANNING", **observed,
            ),
            "steps": [
                row("buy", "home", domain="purchase", cost=15),
                row("transfer", "home", ["buy"], domain="inventory"),
                row("craft", "station", ["transfer"], domain="career"),
            ],
            "routes": [{**route("home", "station", "WALK", 12), "capture_ref": frame.capture}],
            "proposals": {
                ("ACTIVITY", "buy"): {"evidence_ref": "e:buy", "proposal_ref": "buy-material"},
                ("ACTIVITY", "transfer"): {"evidence_ref": "e:transfer", "proposal_ref": "move-material"},
                ("TRAVEL", "craft", "WALK", "home", "station"): {
                    "evidence_ref": "e:WALK", "proposal_ref": "walk-to-workstation",
                },
                ("ACTIVITY", "craft"): {"evidence_ref": "e:craft", "proposal_ref": "craft-artifact"},
            },
        }

    def test_activity_chain_stages_while_paused_then_submits_at_most_one_action(self):
        runtime = self.enable_activity_chain()
        callback = self.adapter.register.call_args.kwargs["cycle"]
        self.adapter.frame.side_effect = [
            self.frame(playing=False), self.frame(capture="capture:play"),
            self.frame(capture="capture:fresh"),
        ]
        self.assertEqual(callback(), "PLAN_STAGED")
        self.assertEqual([step["kind"] for step in runtime.activity_plan["steps"]],
                         ["ACTIVITY", "ACTIVITY", "TRAVEL", "ACTIVITY"])
        self.adapter.submit.assert_not_called()
        self.assertEqual(callback(), "QUEUED")
        self.adapter.submit.assert_called_once_with(
            "buy-material", self.frame(capture="capture:fresh"))

    def test_activity_chain_rechecks_time_then_holds_uncertain_submission(self):
        runtime = self.enable_activity_chain()
        first = self.frame()
        fresh = self.frame(capture="capture:second")
        third = self.frame(capture="capture:third")
        self.adapter.frame.side_effect = [first, fresh, first, fresh, fresh, third]
        self.adapter.read_activity_chain.side_effect = [
            self.activity_packet(first), self.activity_packet(fresh, minutes_until_work=15),
            self.activity_packet(first), self.activity_packet(fresh),
        ]
        self.assertEqual(runtime.cycle(), "ACTIVITY_REOBSERVE_FIRST_ACTION")
        self.adapter.submit.assert_not_called()
        self.adapter.submit.side_effect = RuntimeError("lost ACK")
        self.assertEqual(runtime.cycle(), "NATIVE_DISPATCH_RECONCILIATION")
        self.assertEqual(runtime.cycle(), "NATIVE_DISPATCH_RECONCILIATION")
        self.adapter.reconcile.assert_not_called()
        self.assertEqual(runtime.cycle(), "NATIVE_DISPATCH_RECONCILIATION")
        self.adapter.reconcile.assert_called_once()
        self.adapter.submit.assert_called_once()

    def test_activity_chain_reconciles_each_effect_until_artifact_is_observed(self):
        runtime = self.enable_activity_chain()
        self.adapter.reconcile.return_value = True
        steps_done = []
        location = "home"

        def qualified_packet(frame):
            completion = [
                {"step_id": sid, "outcome_ref": "outcome:" + sid,
                 "outcome_capture_ref": outcome, "still_valid": True,
                 "revalidated_capture_ref": frame.capture}
                for sid, outcome in steps_done
            ]
            return self.activity_packet(frame, completed=completion, location=location)

        self.adapter.read_activity_chain.side_effect = qualified_packet
        for step, proposal in [("buy", "buy-material"), ("transfer", "move-material"),
                               (None, "walk-to-workstation"), ("craft", "craft-artifact")]:
            with self.subTest(step=step):
                first = self.frame(capture=f"capture:{proposal}-first")
                second = self.frame(capture=f"capture:{proposal}-second")
                self.adapter.frame.side_effect = [first, second]
                self.assertEqual(runtime.cycle(), "QUEUED")
                self.adapter.submit.assert_called_with(proposal, second)
                if step:
                    steps_done.append((step, f"capture:{proposal}-outcome"))
                else:
                    location = "station"
        self.adapter.frame.side_effect = [self.frame(capture="capture:verified-artifact")]
        self.assertEqual(runtime.cycle(), "CHAIN_COMPLETED")
        self.assertEqual(self.adapter.submit.call_count, 4)
        self.assertEqual(self.adapter.reconcile.call_count, 4)

    def test_activity_chain_defers_to_existing_domain_and_player_changes(self):
        runtime = self.enable_activity_chain()
        first = self.frame()
        fresh = self.frame(capture="capture:next")
        self.adapter.frame.side_effect = [first, fresh, first, replace(fresh, input_generation=4)]
        self.adapter.analyze.side_effect = [
            ({}, None, NEEDS), ({"urgent": "native-urgent"}, None, NEEDS), ({}, None, NEEDS),
        ]
        self.assertEqual(runtime.cycle(), "ACTIVITY_REOBSERVE_DOMAIN_PRIORITY")
        self.assertEqual(runtime.cycle(), "YIELD_TO_PLAYER")
        self.adapter.submit.assert_not_called()

    def test_activity_chain_refuses_rebound_proposal_replay_and_stale_completion(self):
        runtime = self.enable_activity_chain()
        first = self.frame()
        fresh = self.frame(capture="capture:fresh")
        third = self.frame(capture="capture:third")
        fourth = self.frame(capture="capture:fourth")
        self.adapter.reconcile.return_value = True
        self.adapter.frame.side_effect = [first, fresh, third, fourth, third]
        moved = []
        for frame in (third, fourth):
            packet = self.activity_packet(frame, location="other-room")
            packet["steps"][0]["location"] = packet["steps"][1]["location"] = "other-room"
            packet["routes"][0]["from"] = "other-room"
            packet["proposals"][("ACTIVITY", "buy")]["proposal_ref"] = "different-id"
            moved.append(packet)
        self.adapter.read_activity_chain.side_effect = [
            self.activity_packet(first), self.activity_packet(fresh),
            *moved,
            self.activity_packet(third, completed=[{"step_id": "buy", "outcome_ref": "outcome:buy",
                                                    "outcome_capture_ref": "capture:old"}]),
        ]
        self.assertEqual(runtime.cycle(), "QUEUED")
        self.assertEqual(runtime.cycle(), "DUPLICATE_NATIVE_PROPOSAL")
        self.assertEqual(runtime.cycle(), "REVALIDATE_PREVIOUS_COMPLETIONS")
        self.adapter.submit.assert_called_once()

    def test_activity_chain_and_regular_dispatch_share_proposal_deduplication(self):
        runtime = self.enable_activity_chain()
        self.adapter.reconcile.return_value = True
        self.adapter.frame.side_effect = [
            self.frame(), self.frame(capture="capture:fresh"),
            self.frame(capture="capture:readback"), self.frame(capture="capture:next"),
        ]
        self.assertEqual(runtime.cycle(), "QUEUED")
        self.adapter.analyze.return_value = ({"purchase": "buy-material"}, None, NEEDS)
        self.assertEqual(runtime.cycle(), "DUPLICATE_NATIVE_PROPOSAL")
        self.adapter.submit.assert_called_once()

    def test_activity_settlement_keeps_original_actor_after_portrait_change(self):
        runtime = self.enable_activity_chain()
        first = self.frame()
        changed = self.frame(actor="sim:sim-two", capture="capture:changed")
        self.adapter.reconcile.return_value = True
        self.adapter.frame.side_effect = [
            first, self.frame(capture="capture:fresh"), changed, replace(changed, capture="capture:next"),
        ]
        self.assertEqual(runtime.cycle(), "QUEUED")
        self.adapter.analyze.return_value = ({"urgent": "native-urgent"}, None, NEEDS)
        self.assertEqual(runtime.cycle(), "QUEUED")
        self.adapter.reconcile.assert_called_once_with((first.scope(), "buy-material"), changed)
        self.assertEqual([call.args[0] for call in self.adapter.submit.call_args_list],
                         ["buy-material", "native-urgent"])

    def test_activity_binding_is_specific_to_the_step_and_observed_save(self):
        runtime = self.enable_activity_chain()
        first = self.frame()
        packet = self.activity_packet(first)
        del packet["proposals"][("ACTIVITY", "buy")]
        packet["proposals"][("ACTIVITY", "transfer")]["evidence_ref"] = "e:buy"
        self.adapter.frame.return_value = first
        self.adapter.read_activity_chain.side_effect = [packet, {**packet, "save_ref": "other-save"}]
        self.assertEqual(runtime.cycle(), "ACTIVITY_ACTION_UNBOUND")
        self.assertEqual(runtime.cycle(), "ACTIVITY_SCOPE_UNQUALIFIED")
        self.adapter.submit.assert_not_called()

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
