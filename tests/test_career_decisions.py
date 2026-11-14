"""P82 synthetic adversarial tests of the career-event chance-card microsystem.

All observations and probabilities are fabricated *test fixtures*, not
measured EA tuning. The module must never claim a native effect or click.
"""
import copy
import json
import unittest

from betterinstincts.career_decisions import (
    evaluate_career_event, reconcile_career_event, load_contract,
)
from betterinstincts.career_service import (
    evaluate_career_event_turn, reconcile_career_event_turn,
    evaluate_work_shift_tone,
)
from betterinstincts.glossary import define


def choice(rid, effects, *, lose=False, irreversible=False, probability=10000,
           second=None):
    outcomes = [{
        "probability_bps": probability,
        "effect_source_ref": "tuning:career-option-observed",
        "job_lost": lose, "irreversible": irreversible,
        "effects": effects,
    }]
    if second is not None:
        outcomes.append({
            "probability_bps": 10000 - probability,
            "effect_source_ref": "tuning:career-option-other",
            "job_lost": False, "irreversible": False, "effects": second,
        })
    return {
        "response_id": rid, "option_ref": "option:" + str(rid),
        "effect_basis_ref": "ea:career-tuning:" + str(rid),
        "outcomes": outcomes,
    }


def event(**overrides):
    data = {
        "schema": "betterinstincts.career-event.observation/v1",
        "source": "EA_NATIVE", "read_origin": "RUNNING_GAME_MEMORY",
        "stage": "CHOICE", "event_kind": "CAREER_CHANCE_CARD",
        "game_build": "1.121.361.1020", "dialog_tuning_id": 654321,
        "event_ref": "career:event-one", "event_revision": "rev:one",
        "native_hook_ref": "hook:career-offer", "capture_ref": "capture:career-one",
        "captured_at_epoch_ms": 100000,
        "recipient_sim_id": "1002001", "selected_sim_id": "1002002",
        "household_id": "99999", "career_id": "career:scientist",
        "shift_ref": "shift:one", "career_level": 4,
        "career_mode": "RABBIT_HOLE", "player_directed": False,
        "player_queue_reserved": False, "options_complete": True,
        "response_ids": [8, 2],
        "options": [
            choice(8, {"performance": 4, "simoleons": 100}),
            choice(2, {"performance": -5, "mood": -10}),
        ],
    }
    data.update(overrides)
    return data


def plan(case=None, **kw):
    return evaluate_career_event(
        event() if case is None else case, now_epoch_ms=kw.pop("now_epoch_ms", 100100),
        autonomy_enabled=kw.pop("autonomy_enabled", True),
        player_active=kw.pop("player_active", False), **kw,
    )


class CareerChanceCardTests(unittest.TestCase):
    def test_known_unique_benefit_is_autonomous_recommendation_not_click(self):
        value = plan()
        self.assertEqual(value["state"], "RECOMMENDED_NATIVE_CHOICE")
        self.assertEqual(value["recommended_response_id"], 8)
        self.assertEqual(value["recipient_sim_id"], "1002001")
        self.assertEqual(value["selected_sim_id"], "1002002")
        self.assertGreater(value["score_margin"], 0)
        self.assertFalse(value["execute_allowed"])
        self.assertIsNone(value["control_permit"])
        self.assertIn("OFFLINE", value["proof_ceiling"])
        self.assertEqual(evaluate_career_event_turn(
            event(), now_epoch_ms=100100, autonomy_enabled=True,
            player_active=False)["recommended_response_id"], 8)

    def test_real_choice_ids_never_invented_from_list_position(self):
        swapped = event(response_ids=[2, 8])
        decision = plan(swapped)
        self.assertEqual(decision["recommended_response_id"], 8)
        self.assertEqual(decision["event_ref"], "career:event-one")

    def test_probabilistic_risk_can_beat_large_unreliable_gain(self):
        risky = choice(8, {"performance": 10}, probability=5000,
                       second={"performance": -10})
        reliable = choice(2, {"performance": 2})
        decision = plan(event(options=[risky, reliable]))
        self.assertEqual(decision["recommended_response_id"], 2)

    def test_both_negative_options_choose_lesser_evidenced_harm_when_required(self):
        value = plan(event(options=[
            choice(8, {"performance": -1}),
            choice(2, {"performance": -20}),
        ]))
        self.assertEqual(value["recommended_response_id"], 8)

    def test_irreversible_job_risk_denies_unapproved_choice(self):
        val = plan(event(options=[
            choice(8, {"performance": 100}, lose=True),
            choice(2, {"performance": 1}),
        ]))
        self.assertEqual(val["state"], "HOLD")
        self.assertEqual(val["reason"], "CAREER_IRREVERSIBLE_RISK_HOLD")
        other = plan(event(options=[
            choice(8, {"performance": 100}, irreversible=True),
            choice(2, {"performance": 1}),
        ]))
        self.assertEqual(other["state"], "HOLD")

    def test_player_autonomy_and_queue_override(self):
        for item, opts in [
            (event(), {"player_active": True}),
            (event(), {"autonomy_enabled": False}),
            (event(player_directed=True), {}),
            (event(player_queue_reserved=True), {}),
        ]:
            with self.subTest(item=item, opts=opts):
                result = plan(item, **opts)
                self.assertEqual(result["state"], "HOLD")
                self.assertFalse(result["execute_allowed"])

    def test_source_incomplete_and_wrong_event_hold(self):
        cases = [
            ({"source": "DISK_SAVE"}, "COMPLETE_NATIVE_CAREER_CHOICE_REQUIRED"),
            ({"event_kind": "SIM_PREFERENCE"}, "COMPLETE_NATIVE_CAREER_CHOICE_REQUIRED"),
            ({"options_complete": False}, "COMPLETE_NATIVE_CAREER_CHOICE_REQUIRED"),
            ({"stage": "OUTCOME"}, "COMPLETE_NATIVE_CAREER_CHOICE_REQUIRED"),
            ({"career_mode": "UNKNOWN"}, "CAREER_MODE_NOT_SOURCE_VERIFIED"),
            ({"career_mode": "ACTIVE_CAREER"}, None),
            ({"dialog_tuning_id": True}, "CAREER_EVENT_IDENTITY_OR_SOURCE_INVALID"),
            ({"recipient_sim_id": "1002000.0"}, "CAREER_EVENT_IDENTITY_OR_SOURCE_INVALID"),
            ({"selected_sim_id": "bad"}, "CAREER_SELECTED_PORTRAIT_INVALID"),
            ({"capture_ref": ""}, "CAREER_EVENT_IDENTITY_OR_SOURCE_INVALID"),
            ({"response_ids": [8]}, "COMPLETE_CAREER_RESPONSE_IDS_REQUIRED"),
            ({"response_ids": [8, 8]}, "COMPLETE_CAREER_RESPONSE_IDS_REQUIRED"),
            ({"response_ids": [8, 9]}, "CAREER_RESPONSE_OPTION_SET_MISMATCH"),
        ]
        for update, expected in cases:
            with self.subTest(update=update):
                value = plan(event(**update))
                self.assertEqual(value["reason"], expected)
        self.assertEqual(plan(event(captured_at_epoch_ms=95000),
                              now_epoch_ms=100100)["reason"], "CAREER_CHOICE_CAPTURE_STALE")
        self.assertEqual(plan(event(captured_at_epoch_ms=100110),
                              now_epoch_ms=100100)["reason"], "CAREER_CHOICE_CAPTURE_STALE")

    def test_missing_or_invalid_effect_probability_holds(self):
        for variation in [
            lambda x: x["outcomes"][0].update(probability_bps=9999),
            lambda x: x["outcomes"][0].update(probability_bps=True),
            lambda x: x["outcomes"][0].update(effects={"performance": float("nan")}),
            lambda x: x["outcomes"][0].update(effects={"unknown_trait": 10}),
            lambda x: x["outcomes"][0].update(effects={"simoleons": 1000000}),
            lambda x: x["outcomes"][0].update(effect_source_ref=""),
            lambda x: x["outcomes"][0].pop("job_lost"),
            lambda x: x["outcomes"][0].update(irreversible="unknown"),
        ]:
            with self.subTest(variation=variation):
                options = copy.deepcopy(event()["options"])
                variation(options[0])
                got = plan(event(options=options))
                self.assertEqual(got["state"], "HOLD")

    def test_tie_and_same_outcome_do_not_fake_optimum(self):
        got = plan(event(options=[
            choice(8, {"performance": 1}),
            choice(2, {"performance": 1}),
        ]))
        self.assertEqual(got["reason"], "CAREER_CHOICE_UTILITY_TIE_OR_WEAK_MARGIN")

    def test_duplicate_or_pending_response_never_replayed(self):
        for state in ("INPUT_DISPATCHED", "OUTCOME_UNKNOWN", "NATIVE_ACK"):
            got = plan(previously_responded={
                "event_ref": "career:event-one",
                "event_revision": "rev:one", "status": state,
            })
            self.assertEqual(got["reason"], "CAREER_EVENT_ALREADY_ACTED_OR_UNCERTAIN")
        self.assertEqual(plan(previously_responded="bad")["state"], "HOLD")

    def test_response_and_resumed_activity_need_disjoint_captures(self):
        decision = plan()
        response = {
            "source": "EA_NATIVE", "event_ref": decision["event_ref"],
            "event_revision": decision["event_revision"],
            "recipient_sim_id": "1002001",
            "response_id": 8, "accepted": True,
            "capture_ref": "capture:after-response",
        }
        activity = {
            "source": "EA_NATIVE", "event_ref": decision["event_ref"],
            "recipient_sim_id": "1002001", "resumed": True,
            "capture_ref": "capture:after-activity",
            "activity_ref": "sim-queue:ongoing",
        }
        self.assertEqual(reconcile_career_event_turn(
            decision, response, activity=activity)["state"],
            "RESPONSE_AND_RESUMPTION_SHAPE_MATCH")
        self.assertEqual(reconcile_career_event(
            decision, response, activity=None)["state"], "UNVERIFIED")
        for change in [
            {"capture_ref": decision["capture_ref"]},
            {"response_id": 2},
            {"recipient_sim_id": "1002002"},
            {"accepted": False},
        ]:
            with self.subTest(change=change):
                self.assertEqual(reconcile_career_event(
                    decision, {**response, **change}, activity=activity)["state"],
                    "UNVERIFIED")
        for change in [
            {"capture_ref": response["capture_ref"]},
            {"capture_ref": decision["capture_ref"]},
            {"resumed": False},
            {"recipient_sim_id": "1002002"},
        ]:
            with self.subTest(change=change):
                self.assertEqual(reconcile_career_event(
                    decision, response, activity={**activity, **change})["state"],
                    "UNVERIFIED")

    def test_does_not_change_work_hard_or_teen_homework_owner(self):
        shift = {
            "schema": "betterinstincts.work-shift.observation/v1",
            "member_key": "sim:one", "capture_ref": "capture:work",
            "shift_ref": "shift:one", "state": "AT_WORK",
            "work_mode": "RABBIT_HOLE", "promotion_requirements": "MET",
            "daily_task": "COMPLETE", "performance": "BELOW_TARGET",
            "current_tone": "NORMAL", "tone_owner": "GAME",
            "work_hard_available": True,
        }
        tone = evaluate_work_shift_tone(
            shift, member_key="sim:one", capture_ref="capture:work",
            wellbeing_ready=True, player_reserved=False)
        self.assertEqual(tone["gate"], "WORK_HARD_ADMISSION_REQUIRED")
        self.assertFalse(tone["execute_allowed"])

    def test_progressive_glossary_is_lazy_and_owner_grounded(self):
        contract = load_contract()
        self.assertEqual(contract["owners"]["entrypoint"],
                         "betterinstincts/career_service.py#evaluate_career_event_turn")
        self.assertIn("Career", define("CAREER_EVENT_CHOICE"))
        self.assertIn("J", define("CAREER_PANEL_J"))
        self.assertIn("Work Hard", define("CAREER_WORK_TONE"))

    def test_contract_and_bounds_are_constant(self):
        cfg = load_contract()
        self.assertEqual(cfg["event_kind"], "CAREER_CHANCE_CARD")
        self.assertEqual(cfg["probability_scale"], 10000)
        self.assertEqual(cfg["scoring"]["max_termination_probability_bps"], 0)
        self.assertFalse(cfg["scoring"]["allow_irreversible_outcome"])


if __name__ == "__main__":
    unittest.main()
