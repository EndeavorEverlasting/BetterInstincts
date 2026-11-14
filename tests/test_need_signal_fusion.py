"""P82 falsifiers: independent live-state feeds, health reset and Servo trends."""
from __future__ import annotations

import copy
import time
import unittest

from betterinstincts.need_signal_fusion import (
    NeedSignalError, evaluate_need_signals,
)

NOW = 2000.0
BUILD = "1.121.361.1020"
SIM = "sim:servo-1"


def native(*, stamp=NOW, sample="native:1", **changes):
    row = {
        "source": "EA_NATIVE", "status": "READY", "source_ref": "source:ea-hook",
        "sample_ref": sample, "capture_ref": "capture:native", "sim_ref": SIM,
        "game_build": BUILD, "profile": "servo", "observed_at_unix": stamp,
        "probe_passed": True, "scene_verified": True,
        "native_hook_ref": "ea:runtime:motive-observer",
        "native_read_verified": True,
        "needs": {
            "social": {"level": .69, "direction": "DOWN",
                       "rate_per_sim_minute": -.004,
                       "rate_proof_ref": "ea:sample:delta"},
            "charge": {"level": .48, "direction": "DOWN"},
        },
    }
    row.update(changes)
    return row


def hud(*, stamp=NOW, sample="hud:1", **changes):
    row = {
        "source": "HUD_CV", "status": "READY", "source_ref": "source:cv-calibration",
        "sample_ref": sample, "capture_ref": "capture:hud", "sim_ref": SIM,
        "game_build": BUILD, "profile": "servo", "observed_at_unix": stamp,
        "probe_passed": True, "scene_verified": True,
        "calibration_ref": "calibration:needs-panel",
        "calibration_verified": True,
        "needs": {
            "fun": {"level": .92, "direction": "FLAT"},
            "social": {"level": .69, "direction": "DOWN", "arrow_count": 3,
                       "arrow_proof_ref": "cue:three-red-down"},
            "durability": {"level": .75, "direction": "FLAT"},
            "charge": {"level": .48, "direction": "DOWN", "arrow_count": 1,
                       "arrow_proof_ref": "cue:charge-down"},
        },
    }
    row.update(changes)
    return row


def snapshot(feeds=None, *, profile="servo", paused=True, **changes):
    row = {
        "schema": "betterinstincts.need-signal-fusion/v1",
        "profile": profile, "sim_ref": SIM, "game_build": BUILD,
        "capture_ref": "capture:host", "game_paused": paused,
        "player_active": False, "feeds": [native(), hud()] if feeds is None else feeds,
        "moodlet_observation": {
            "source_ref": "operator:emotion-note", "capture_ref": "capture:host",
            "emotion": "FINE", "moodlets": [],
        },
    }
    row.update(changes)
    return row


def eval_need(obs=None, **kwargs):
    return evaluate_need_signals(snapshot() if obs is None else obs, now=NOW, **kwargs)


class NeedSignalFusionTests(unittest.TestCase):
    def test_paused_servo_three_down_arrows_are_ordinal_not_numeric_3x(self):
        original = snapshot()
        saved = copy.deepcopy(original)
        result = eval_need(original)
        self.assertEqual(original, saved)
        self.assertEqual(set(result["motives"]), {"fun", "social", "durability", "charge"})
        self.assertEqual(result["state"], "DUAL_SOURCE_CORROBORATION")
        self.assertEqual(result["priority"], "PAUSED_RAPID_DECAY_INDICATOR_REVIEW")
        self.assertEqual(result["rapid_declines"], ["social"])
        social = result["motives"]["social"]
        self.assertEqual(social["direction"], "DOWN")
        self.assertEqual(social["hud_arrow_count"], 3)
        self.assertEqual(social["ordinal_rate_tier"], "THREE_DOWN_CHEVRONS")
        self.assertIsNone(social["rate_multiplier_claim"])
        self.assertIsNone(social["native_rate_per_sim_minute"])
        self.assertFalse(social["active_decay_measured"])
        self.assertEqual(result["moodlets"]["emotion"], "FINE")
        self.assertFalse(result["game_input_allowed"])
        self.assertFalse(result["execute_allowed"])

    def test_native_only_provides_true_signed_rate_when_game_running(self):
        result = eval_need(snapshot(feeds=[native()], paused=False))
        self.assertEqual(result["state"], "SINGLE_SOURCE_FALLBACK")
        self.assertEqual(result["motives"]["social"]["native_rate_per_sim_minute"], -.004)
        self.assertEqual(result["motives"]["social"]["direction"], "DOWN")
        self.assertTrue(result["motives"]["social"]["active_decay_measured"])
        self.assertEqual(result["source_health"]["HUD_CV"]["state"], "DOWN")
        self.assertEqual(result["priority"], "MONITOR_DECLINING_NEEDS")

    def test_cv_only_detects_high_priority_without_guessing_slope(self):
        report = eval_need(snapshot(feeds=[hud()], paused=False))
        self.assertEqual(report["state"], "SINGLE_SOURCE_FALLBACK")
        self.assertEqual(report["priority"], "DIAGNOSE_RAPID_NEED_DECLINE")
        self.assertIsNone(report["motives"]["social"]["native_rate_per_sim_minute"])
        self.assertEqual(report["healthy_sources"], ["HUD_CV"])

    def test_wrong_patch_sim_calibration_and_read_only_static_file_denied(self):
        cases = (
            native(game_build="old:build"), native(sim_ref="sim:other"),
            native(native_read_verified=False), native(native_hook_ref=None),
            native(observed_at_unix=NOW - 70),
            hud(game_build="old:build"), hud(calibration_verified=False),
            hud(calibration_ref=None), hud(sim_ref="sim:other"),
            hud(observed_at_unix=NOW + 1),
        )
        for feed in cases:
            with self.subTest(source=feed["source"], changed=feed):
                result = eval_need(snapshot(feeds=[feed]))
                self.assertEqual(result["state"], "SOURCES_UNAVAILABLE")
                self.assertFalse(result["healthy_sources"])
                self.assertIn(result["source_health"][feed["source"]]["state"],
                              {"DOWN", "QUARANTINED"})
        with self.assertRaisesRegex(NeedSignalError, "UNRECOGNIZED_SOURCE"):
            eval_need(snapshot(feeds=[{"source": "EA_FILE"}]))

    def test_conflict_does_not_fabricate_correct_direction(self):
        rising = native(needs={"social": {"level": .72, "direction": "UP",
                    "rate_per_sim_minute": .002, "rate_proof_ref": "ea:positive"}})
        result = eval_need(snapshot(feeds=[rising, hud()], paused=False))
        self.assertEqual(result["priority"], "SOURCE_CONFLICT_REOBSERVE")
        self.assertEqual(result["conflicts"], ["social"])
        self.assertEqual(result["motives"]["social"]["direction"], "CONFLICT")
        self.assertIsNone(result["motives"]["social"]["native_rate_per_sim_minute"])
        self.assertNotIn("social", result["rapid_declines"])

    def test_asynchronous_samples_do_not_claim_corroborated_same_moment(self):
        later = hud(stamp=NOW - 25)
        result = eval_need(snapshot(feeds=[native(), later]))
        self.assertEqual(result["state"], "DUAL_SOURCE_CORROBORATION")
        self.assertEqual(result["motives"]["social"]["ordinal_rate_tier"],
                         "ASYNCHRONOUS_NOT_CORROBORATED")
        self.assertTrue(result["motives"]["social"]["needs_reobservation"])

    def test_one_channel_down_other_still_provides_direction(self):
        missing = {"source": "EA_NATIVE", "status": "DOWN"}
        report = eval_need(snapshot(feeds=[missing, hud()]))
        self.assertEqual(report["state"], "SINGLE_SOURCE_FALLBACK")
        self.assertEqual(report["source_health"]["EA_NATIVE"]["state"], "DOWN")
        self.assertEqual(report["rapid_declines"], ["social"])
        self.assertFalse(report["restart_sensor_allowed"])

    def test_quarantined_channel_requires_new_reset_and_two_distinct_probes(self):
        failure = eval_need(snapshot(feeds=[native(probe_passed=False), hud()]))
        self.assertEqual(failure["source_health"]["EA_NATIVE"]["state"], "QUARANTINED")
        first = eval_need(snapshot(feeds=[
            native(sample="native:reset1",stamp=NOW+1,reset_ref="reset:one",
                   reset_probe_passed=True),
            hud(sample="hud:2",stamp=NOW+1)], game_paused=False),
            prior_health=failure["source_health"], now=NOW+1)
        self.assertEqual(first["source_health"]["EA_NATIVE"]["state"], "RECOVERING")
        self.assertEqual(first["healthy_sources"], ["HUD_CV"])
        second = eval_need(snapshot(feeds=[
            native(sample="native:reset2",stamp=NOW+2,reset_ref="reset:one",
                   reset_probe_passed=True),
            hud(sample="hud:3",stamp=NOW+2)], game_paused=False),
            prior_health=first["source_health"], now=NOW+2)
        self.assertEqual(second["source_health"]["EA_NATIVE"]["state"], "HEALTHY")
        self.assertEqual(second["state"], "DUAL_SOURCE_CORROBORATION")
        self.assertEqual(second["source_health"]["EA_NATIVE"]["consecutive_good"], 2)
        replay = eval_need(snapshot(feeds=[
            native(sample="native:reset2",stamp=NOW+2,reset_ref="reset:one",
                   reset_probe_passed=True)], game_paused=False),
            prior_health=second["source_health"], now=NOW+3)
        self.assertEqual(replay["source_health"]["EA_NATIVE"]["state"], "QUARANTINED")

    def test_reset_flag_alone_cannot_restore_unhealthy_source(self):
        old = eval_need(snapshot(feeds=[hud(calibration_verified=False)]))
        report = eval_need(snapshot(feeds=[hud(reset_ref="reset:hud",
                           calibration_verified=True)], game_paused=False),
                           prior_health=old["source_health"])
        self.assertEqual(report["source_health"]["HUD_CV"]["state"], "QUARANTINED")
        self.assertFalse(report["healthy_sources"])

    def test_positive_emotion_must_not_hide_social_decline(self):
        obs = snapshot(feeds=[hud()],
            moodlet_observation={"source_ref": "mood:source",
                "capture_ref":"capture:host","emotion":"HAPPY","moodlets":["playful"]})
        result = eval_need(obs)
        self.assertEqual(result["moodlets"]["emotion"], "HAPPY")
        self.assertEqual(result["moodlet_guidance"], "DECLINING_NEED_OUTRANKS_POSITIVE_MOOD")
        self.assertIn("social", result["rapid_declines"])
        self.assertEqual(result["moodlets"]["relief"], ["be_silly", "tell_jokes"])

    def test_negative_moodlets_reuse_existing_owner_not_new_decision_engine(self):
        obs = snapshot(feeds=[native()], moodlet_observation={
            "source_ref":"mood:source","capture_ref":"capture:host",
            "emotion":"ANGRY","moodlets":["scared"]})
        result=eval_need(obs)
        self.assertEqual(result["moodlet_guidance"], "REVIEW_NEGATIVE_MOODLET_RELIEF")
        self.assertIn("social", result["moodlets"]["need_pressure"])

    def test_player_first_even_with_rapid_social_decline(self):
        report = eval_need(snapshot(feeds=[hud()], player_active=True))
        self.assertEqual(report["priority"], "PLAYER_FIRST")
        self.assertFalse(report["queue_cancel_allowed"])
        self.assertFalse(report["execute_allowed"])

    def test_unknown_visible_moodlet_is_not_invented(self):
        obs=snapshot(feeds=[hud()], moodlet_observation={
            "source_ref":"mood:source","capture_ref":"capture:host",
            "emotion":"FINE","moodlets":["Cheerful Treat"]})
        result=eval_need(obs)
        self.assertIn("UNKNOWN_MOODLET_LABEL", result["moodlets"]["findings"])

    def test_ordinary_six_and_servo_four_are_separate_catalog_profiles(self):
        raw={key: {"level": .7, "direction":"FLAT"}
             for key in ("hunger","bladder","energy","hygiene","fun","social")}
        std=native(profile="human",needs=raw)
        report=eval_need(snapshot(feeds=[std],profile="human"))
        self.assertEqual(len(report["motives"]),6)
        self.assertNotIn("charge",report["motives"])
        invalid=eval_need(snapshot(feeds=[std],profile="servo"))
        self.assertEqual(invalid["state"],"SOURCES_UNAVAILABLE")

    def test_invalid_inputs_and_fake_numeric_hud_are_not_promoted(self):
        with self.assertRaisesRegex(NeedSignalError,"CONTEXT"):
            eval_need(snapshot(game_paused="yes"))
        with self.assertRaisesRegex(NeedSignalError,"DUPLICATE"):
            eval_need(snapshot(feeds=[hud(), hud()]))
        for row in (
            {"social":{"level": .8,"direction":"DOWN","arrow_count":3}},
            {"social":{"level":float("nan"),"direction":"DOWN","arrow_count":3,
                       "arrow_proof_ref":"cue:down"}},
            {"social":{"level": .8,"direction":"DOWN","arrow_count":4,
                       "arrow_proof_ref":"cue:down"}},
            {"social":{"level": .8,"direction":"DOWN","arrow_count":3,
                       "arrow_proof_ref":"cue:down","rate_per_sim_minute":-.3}},
        ):
            with self.subTest(row=row):
                report=eval_need(snapshot(feeds=[hud(needs=row)]))
                self.assertEqual(report["state"],"SOURCES_UNAVAILABLE")
        with self.assertRaisesRegex(NeedSignalError,"MOODLET_EVIDENCE_INVALID"):
            eval_need(snapshot(moodlet_observation={"source_ref":"x",
                             "capture_ref":"capture:host","moodlets":"Fine"}))


if __name__ == "__main__":
    unittest.main()
