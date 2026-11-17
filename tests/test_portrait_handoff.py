"""Native callback and workflow tests using semantic frames, without Sims input."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from betterinstincts.installed_player_runtime import Frame, MANIFEST, start_installed
from betterinstincts.portrait_handoff import choose_selection

BUILD = "1.121.361.1020"
ANNA, BEA, CAM = "sim:anna", "sim:bea", "sim:cam"
ROSTER = (ANNA, BEA, CAM)


def frame(seq, actor=ANNA, **overrides):
    return replace(Frame(BUILD, "game-run", "house-one", actor, True, True,
                         True, False, False, True, 3, 10 + seq / 100, 6,
                         f"capture:frame-{seq}"), **overrides)


def packet(current, purpose, states=("COVERED", "READY", "READY"), **overrides):
    return {
        "capture": current.capture, "household": current.household, "selected": current.actor,
        "save": "lab-save", "roster": ROSTER, "goal": "goal-one",
        "purpose": purpose, "members": dict(zip(ROSTER, states)), "safe_to_leave": True,
        **overrides,
    }


class PortraitPolicyTests(unittest.TestCase):
    def test_needs_use_only_uncovered_actions_then_rotate_by_urgency(self):
        current = frame(1)
        data = packet(current, "NEEDS", urgency={BEA: 1, CAM: 3})
        self.assertEqual(choose_selection(current, data)[1].target, CAM)
        data["urgency"][BEA] = 3
        self.assertEqual(choose_selection(current, data)[1].target, BEA)
        data["members"][ANNA] = "READY"
        data["urgency"][ANNA] = 1
        self.assertEqual(choose_selection(current, data), ("PORTRAIT_ALREADY_SELECTED", None))
        data["members"][ANNA] = "WAITING"
        del data["urgency"][ANNA]
        self.assertEqual(choose_selection(current, data), ("PORTRAIT_CURRENT_REVIEW_PENDING", None))

    def test_purchase_stays_at_actor_until_receipt_and_wraps(self):
        current = frame(1, CAM, playing=False)
        states = ("READY", "READY", "READY")
        self.assertEqual(choose_selection(current, packet(current, "UPGRADE_PARTS", states)),
                         ("PORTRAIT_ALREADY_SELECTED", None))
        covered = ("READY", "READY", "COVERED")
        self.assertEqual(choose_selection(current, packet(current, "UPGRADE_PARTS", covered,
                         safe_to_leave=False)), ("PORTRAIT_CURRENT_EFFECT_PENDING", None))
        self.assertEqual(choose_selection(current, packet(current, "UPGRADE_PARTS", covered))[1].target,
                         ANNA)
        self.assertEqual(choose_selection(current, packet(current, "UPGRADE_PARTS",
                         ("READY", "READY", "WAITING"))), ("PORTRAIT_CURRENT_REVIEW_PENDING", None))

    def test_skill_order_waits_for_earlier_member_and_skips_only_observed_ineligibility(self):
        current = frame(1, CAM)
        waiting = ("COVERED", "WAITING", "READY")
        self.assertEqual(choose_selection(current, packet(current, "SKILL", waiting)),
                         ("PORTRAIT_EARLIER_SKILL_PENDING", None))
        self.assertEqual(choose_selection(current, packet(current, "SKILL"))[1].target, BEA)
        unavailable = ("UNAVAILABLE", "COVERED", "READY")
        self.assertEqual(choose_selection(current, packet(current, "SKILL", unavailable)),
                         ("PORTRAIT_ALREADY_SELECTED", None))

    def test_only_targeted_ready_members_and_exact_evidence_are_accepted(self):
        current = frame(1)
        self.assertEqual(choose_selection(current, packet(current, "TARGET", target=CAM))[1].target, CAM)
        for overrides in (
            {"capture": "capture:old"}, {"roster": (ANNA, BEA, BEA)}, {"save": None},
            {"selected": CAM}, {"household": "house-two"}, {"members": {ANNA: "READY"}},
            {"members": {ANNA: "COVERED", BEA: "UNVERIFIED", CAM: "READY"}}
        ):
            with self.subTest(overrides=overrides):
                self.assertEqual(choose_selection(current, packet(current, "TARGET", target=CAM, **overrides)),
                                 ("PORTRAIT_EVIDENCE_UNQUALIFIED", None))
        self.assertEqual(choose_selection(current, packet(current, "TARGET", target="sim:other")),
                         ("PORTRAIT_TARGET_UNAVAILABLE", None))


class InstalledPortraitTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "Mods" / "BetterInstincts"
        self.root.mkdir(parents=True)
        self.manifest = {
            "schema": "betterinstincts.native-ecology-ownership/v1",
            "game_build": BUILD, "installed_player_runtime": True,
            "installed_portrait_handoff": True,
        }
        self.adapter = Mock(game_build=BUILD)
        self.adapter.register.return_value = True
        self.adapter.analyze.return_value = ({}, None, {})
        self.adapter.submit.return_value = "QUEUED"
        self.adapter.read_portrait_handoff.side_effect = lambda f: packet(f, "SKILL")
        self.adapter.read_portrait_outcome.side_effect = self.outcome

    def start(self):
        (self.root / MANIFEST).write_text(json.dumps(self.manifest))
        return start_installed(self.adapter, exact_build=BUILD, owned_dir=self.root,
                               clock=lambda: 10.9, learning_opt_in=True)

    def outcome(self, attempt, current, **overrides):
        return {"status": "APPLIED", "capture": current.capture, "save": attempt.selection.save,
                "roster": ROSTER, "request_capture": attempt.submit_capture,
                "target": attempt.selection.target, **overrides}

    def cycle(self, runtime, *frames):
        self.adapter.frame.side_effect = list(frames)
        return runtime.cycle()

    def test_each_workflow_submits_once_and_resumes_on_a_third_recipient_observation(self):
        for purpose, action in (("UPGRADE_PARTS", "purchase"), ("SKILL", "train"), ("NEEDS", "care")):
            with self.subTest(purpose=purpose):
                self.adapter.reset_mock()
                self.adapter.analyze.return_value = ({}, None, {})
                self.adapter.read_portrait_handoff.side_effect = (
                    lambda current: packet(current, purpose, urgency={BEA: 3, CAM: 1}))
                runtime = self.start()
                paused = purpose == "UPGRADE_PARTS"
                self.assertEqual(self.cycle(runtime, frame(1, playing=not paused),
                                            frame(2, playing=not paused)),
                                 "PORTRAIT_SWITCH_AWAITING_READBACK")
                attempt, submitted_frame = self.adapter.submit_portrait_if_current.call_args.args
                self.assertEqual((attempt.selection.source, attempt.selection.target), (ANNA, BEA))
                self.assertEqual(submitted_frame.capture, attempt.submit_capture)
                self.adapter.analyze.return_value = ({action: "domain-effect"}, None, {})
                self.assertEqual(self.cycle(runtime, frame(3, BEA)), "PORTRAIT_SWITCH_CONFIRMED")
                self.assertEqual(self.cycle(runtime, frame(3, BEA)), "PORTRAIT_SELECTION_REOBSERVE")
                self.assertEqual(self.cycle(runtime, frame(4, BEA), frame(5, BEA)), "QUEUED")
                self.adapter.submit_portrait_if_current.assert_called_once()
                self.adapter.submit.assert_called_once_with("domain-effect", frame(5, BEA))

    def test_failed_submit_has_to_reconcile_and_never_replays_same_goal(self):
        runtime = self.start()
        self.adapter.submit_portrait_if_current.side_effect = RuntimeError("unknown EA result")
        self.assertEqual(self.cycle(runtime, frame(1), frame(2)), "PORTRAIT_SWITCH_RECONCILE")
        self.assertEqual(self.cycle(runtime, frame(3)), "PORTRAIT_SWITCH_RECONCILE")
        self.adapter.read_portrait_outcome.side_effect = (
            lambda attempt, current: self.outcome(attempt, current, status="NO_EFFECT"))
        self.assertEqual(self.cycle(runtime, frame(4)), "PORTRAIT_SWITCH_NO_EFFECT")
        self.assertEqual(self.cycle(runtime, frame(5), frame(6)), "DUPLICATE_PORTRAIT_PROPOSAL")
        self.adapter.submit_portrait_if_current.assert_called_once()
        self.adapter.submit.assert_not_called()

    def test_reconciliation_rejects_reused_capture_wrong_roster_save_and_receipt(self):
        runtime = self.start()
        self.cycle(runtime, frame(1), frame(2))
        self.assertEqual(self.cycle(runtime, frame(2, BEA)), "PORTRAIT_SWITCH_RECONCILE")
        invalid = ({"roster": (CAM, ANNA, BEA)}, {"save": "new-save"}, {"target": CAM},
                   {"request_capture": "capture:wrong"}, {"status": "QUEUED"})
        for seq, bad in enumerate(invalid, 3):
            self.adapter.read_portrait_outcome.side_effect = (
                lambda attempt, current: self.outcome(attempt, current, **bad))
            self.assertEqual(self.cycle(runtime, frame(seq, BEA)), "PORTRAIT_SWITCH_RECONCILE")
        self.adapter.read_portrait_outcome.side_effect = self.outcome
        self.assertEqual(self.cycle(runtime, frame(9, BEA)), "PORTRAIT_SWITCH_CONFIRMED")
        self.assertEqual(self.cycle(runtime, frame(10, ANNA)), "PORTRAIT_SELECTION_REOBSERVE")
        self.adapter.submit.assert_not_called()

    def test_player_can_preempt_on_either_side_of_native_submit(self):
        runtime = self.start()
        self.assertEqual(self.cycle(runtime, frame(1), frame(2, input_generation=4)),
                         "YIELD_TO_PLAYER")
        self.adapter.submit_portrait_if_current.assert_not_called()
        self.cycle(runtime, frame(3), frame(4))
        self.assertEqual(self.cycle(runtime, frame(5, CAM, input_generation=4, player_active=True)),
                         "PORTRAIT_SWITCH_SUPERSEDED")
        self.assertEqual(self.cycle(runtime, frame(6, CAM, input_generation=4, player_active=True)),
                         "YIELD_TO_PLAYER")
        self.adapter.submit_portrait_if_current.assert_called_once()
        self.adapter.submit.assert_not_called()

    def test_new_higher_priority_plan_and_changed_target_cancel_pre_submit(self):
        runtime = self.start()
        self.adapter.analyze.side_effect = [({}, None, {}), ({"needs": "help-first"}, None, {})]
        self.assertEqual(self.cycle(runtime, frame(1), frame(2)), "PORTRAIT_SELECTION_REOBSERVE")
        self.adapter.analyze.side_effect = None
        self.adapter.read_portrait_handoff.side_effect = [
            packet(frame(3), "SKILL"),
            packet(frame(4), "SKILL", ("COVERED", "COVERED", "READY")),
        ]
        self.assertEqual(self.cycle(runtime, frame(3), frame(4)), "PORTRAIT_SELECTION_REOBSERVE")
        self.adapter.submit_portrait_if_current.assert_not_called()

    def test_exact_build_player_and_opt_in_gates_precede_portrait_read(self):
        runtime = self.start()
        for changes in ({"player_queue": True}, {"player_active": True}, {"activity_trusted": False}):
            self.assertEqual(self.cycle(runtime, frame(1, **changes)), "YIELD_TO_PLAYER")
        self.assertEqual(self.cycle(runtime, frame(1, save_admitted=False)), "NATIVE_FRAME_UNQUALIFIED")
        self.adapter.read_portrait_handoff.assert_not_called()
        self.adapter.read_portrait_outcome = None
        with self.assertRaisesRegex(ValueError, "NATIVE_PORTRAIT_HANDOFF_PORTS_REQUIRED"):
            self.start()
        self.manifest.pop("installed_portrait_handoff")
        legacy = self.start()
        self.assertEqual(self.cycle(legacy, frame(1)), "NO_NATIVE_PROPOSAL")
        self.adapter.read_portrait_handoff.assert_not_called()
