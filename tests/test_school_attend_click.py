"""P62 falsifiers for the 2026-11-09 Send Alone -> JOIN misclick regression."""
from __future__ import annotations

import contextlib
import io
import json
import unittest

from betterinstincts.decision_eval import get_prompt
from betterinstincts.school_attend_click import (
    FAIL_STATE,
    PASS_STATE,
    SchoolAttendClickError,
    load_hit_targets,
    plan_send_alone_click,
    resolve_layout,
    score_option_hit,
    verify_post_click,
)
from scripts import school_attend_click as cli

LEGACY = (960, 600)
GOOD_HOME = {
    "lot_kind": "home",
    "school_hud_visible": False,
    "dialog_present": False,
    "text_cues": ["Bargain Bend"],
    "source": "PRINTWINDOW",
    "age_s": 4,
}


class HitTargetContractTests(unittest.TestCase):
    def test_legacy_point_is_recorded_superseded_forbidden(self):
        cfg = load_hit_targets()
        self.assertEqual(cfg["legacy"]["send_alone_screen_xy"], [960, 600])
        self.assertIn("SUPERSEDED", cfg["legacy"]["status"])
        self.assertIn("FORBIDDEN", cfg["legacy"]["status"])
        self.assertEqual(cfg["legacy"]["actual_hit"], "join")
        self.assertIs(cfg["execute_allowed_default"], False)

    def test_join_above_send_alone_and_relative_layout(self):
        cfg = load_hit_targets()
        self.assertEqual(cfg["layout_model"]["order_top_to_bottom"], ["join", "send_alone"])
        layout = resolve_layout(cfg=cfg)
        self.assertEqual(layout["send_alone_y"], layout["join_y"] + cfg["layout_model"]["gap_px"])
        self.assertGreater(layout["send_alone_box"][1], layout["join_box"][3])
        measured = resolve_layout(cfg=cfg, measured_join_y=520)
        self.assertEqual(measured["send_alone_y"], 520 + cfg["layout_model"]["gap_px"])
        self.assertGreater(measured["send_alone_box"][1], measured["join_box"][3])

    def test_option_tags_unchanged(self):
        ids = [o["option_id"] for o in get_prompt("school.attend.join_or_send_alone")["options"]]
        self.assertEqual(ids, ["join", "send_alone"])


class ScoreOptionHitTests(unittest.TestCase):
    def setUp(self):
        layout = resolve_layout()
        self.join_box, self.send_box = layout["join_box"], layout["send_alone_box"]
        self.layout = layout

    def test_legacy_960_600_is_join_hit_and_send_alone_miss(self):
        score = score_option_hit("send_alone", LEGACY, self.join_box, self.send_box)
        self.assertEqual(score["hit_option"], "join")
        self.assertTrue(score["join_hit"])
        self.assertFalse(score["send_alone_hit"])
        self.assertFalse(score["intended_hit"])
        self.assertTrue(score["join_misclick_suspected"])
        self.assertEqual(score["verdict"], "WRONG_OPTION_HIT")
        self.assertIs(score["auto_reclick_allowed"], False)

    def test_send_alone_center_hits_with_click_error_thresholds(self):
        score = score_option_hit("send_alone", self.layout["send_alone_center"], self.join_box, self.send_box)
        self.assertEqual(score["verdict"], "INTENDED_OPTION_HIT")
        self.assertEqual(score["classification"], "HIT")
        self.assertEqual(score["error_px"]["euclidean"], 0.0)

    def test_between_pills_misses_both(self):
        gap_y = (self.join_box[3] + self.send_box[1]) // 2
        score = score_option_hit("send_alone", (960, gap_y), self.join_box, self.send_box)
        self.assertEqual(score["hit_option"], "none")
        self.assertEqual(score["verdict"], "MISS_BOTH_PILLS")

    def test_overlapping_boxes_rejected(self):
        with self.assertRaises(SchoolAttendClickError):
            score_option_hit("send_alone", LEGACY, (0, 0, 100, 100), (0, 90, 100, 190))


class PlanTests(unittest.TestCase):
    def test_default_plan_is_provisional_and_never_ready_or_executable(self):
        plan = plan_send_alone_click()
        self.assertFalse(plan["ready_to_execute"])
        self.assertIs(plan["execute_allowed"], False)
        self.assertIn("LAYOUT_PROVISIONAL_UNCALIBRATED", plan["blockers"])
        self.assertIn("PRE_CLICK_DIALOG_OBSERVATION_REQUIRED", plan["blockers"])
        self.assertGreater(plan["target_xy"][1], plan["layout"]["join_box"][3])
        self.assertNotEqual(plan["target_xy"], list(LEGACY))
        self.assertEqual(plan["legacy_forbidden_point"]["status"], "SUPERSEDED / FORBIDDEN")

    def test_legacy_point_candidate_is_refused(self):
        plan = plan_send_alone_click(
            measured_join_y=560, calibration_source="PRINTWINDOW_MEASURED",
            dialog_observed=True, candidate_xy=LEGACY,
        )
        self.assertFalse(plan["ready_to_execute"])
        self.assertIn("SUPERSEDED_FORBIDDEN_POINT", plan["blockers"])

    def test_candidate_inside_join_box_is_refused(self):
        plan = plan_send_alone_click(
            measured_join_y=600, calibration_source="OPERATOR_MEASURED",
            dialog_observed=True, candidate_xy=(960, 610),
        )
        self.assertFalse(plan["ready_to_execute"])
        self.assertIn("TARGET_INSIDE_JOIN_BOX", plan["blockers"])
        self.assertIn("SEND_ALONE_NOT_STRICTLY_BELOW_JOIN", plan["blockers"])

    def test_computer_use_overlay_executor_forbidden(self):
        for name in ("computer_use_overlay", "cursor_computer_use", "Computer-Use"):
            plan = plan_send_alone_click(
                executor=name, measured_join_y=560,
                calibration_source="PRINTWINDOW_MEASURED", dialog_observed=True,
            )
            self.assertFalse(plan["ready_to_execute"], name)
            self.assertIn("COMPUTER_USE_OVERLAY_EXECUTOR_FORBIDDEN", plan["blockers"])
        self.assertIn("computer_use_overlay", plan["executor"]["forbidden"])

    def test_unknown_executor_blocked(self):
        plan = plan_send_alone_click(
            executor="pyautogui", measured_join_y=560,
            calibration_source="PRINTWINDOW_MEASURED", dialog_observed=True,
        )
        self.assertFalse(plan["ready_to_execute"])

    def test_measured_observed_native_plan_is_ready_but_still_not_executed(self):
        plan = plan_send_alone_click(
            measured_join_y=560, calibration_source="PRINTWINDOW_MEASURED",
            dialog_observed=True, execute=True,
        )
        self.assertTrue(plan["ready_to_execute"], plan["blockers"])
        self.assertEqual(plan["layout_status"], "MEASURED")
        self.assertIs(plan["execute_allowed"], False)
        self.assertEqual(plan["target_xy"], [960, 560 + 56])
        self.assertTrue(plan["score_vs_layout"]["intended_hit"])

    def test_measured_without_source_is_blocked(self):
        plan = plan_send_alone_click(measured_join_y=560, dialog_observed=True)
        self.assertIn("CALIBRATION_SOURCE_REQUIRED", plan["blockers"])
        self.assertFalse(plan["ready_to_execute"])


class VerifyPostClickTests(unittest.TestCase):
    def test_school_lot_is_join_misclick_confirmed(self):
        result = verify_post_click({**GOOD_HOME, "lot_kind": "school"})
        self.assertEqual(result["state"], FAIL_STATE)
        self.assertFalse(result["passed"])
        self.assertTrue(result["fail_closed"])

    def test_school_day_ends_cue_is_join_misclick_even_if_lot_claims_home(self):
        result = verify_post_click({**GOOD_HOME, "text_cues": ["School Day ends 3:00 PM"]})
        self.assertEqual(result["state"], FAIL_STATE)
        self.assertIn("school day ends", result["school_cues"])

    def test_school_hud_visible_is_join_misclick(self):
        result = verify_post_click({**GOOD_HOME, "school_hud_visible": True})
        self.assertEqual(result["state"], FAIL_STATE)

    def test_home_dialog_gone_hud_absent_fresh_source_verifies(self):
        result = verify_post_click(GOOD_HOME)
        self.assertEqual(result["state"], PASS_STATE)
        self.assertTrue(result["passed"])
        self.assertIs(result["execute_allowed"], False)
        self.assertIn("NOT_GAME_CERTIFIED", result["next"])

    def test_dialog_still_present_does_not_verify(self):
        result = verify_post_click({**GOOD_HOME, "dialog_present": True})
        self.assertFalse(result["passed"])
        self.assertEqual(result["state"], "SEND_ALONE_UNVERIFIED")
        self.assertIn("DIALOG_GONE_NOT_OBSERVED", result["reasons"])

    def test_unknown_lot_or_unobserved_fields_do_not_verify(self):
        self.assertFalse(verify_post_click({**GOOD_HOME, "lot_kind": "unknown"})["passed"])
        bare = {"source": "PRINTWINDOW", "age_s": 1}
        result = verify_post_click(bare)
        self.assertFalse(result["passed"])
        self.assertIn("SCHOOL_HUD_ABSENCE_NOT_OBSERVED", result["reasons"])

    def test_stale_or_untrusted_observation_does_not_verify(self):
        self.assertFalse(verify_post_click({**GOOD_HOME, "age_s": 600})["passed"])
        self.assertFalse(verify_post_click({**GOOD_HOME, "age_s": None})["passed"])
        self.assertFalse(verify_post_click({**GOOD_HOME, "source": "AGENT_INTENT"})["passed"])
        self.assertFalse(verify_post_click({**GOOD_HOME, "source": None})["passed"])

    def test_intent_alone_never_verifies(self):
        self.assertFalse(verify_post_click({"intended": "send_alone"})["passed"])


class CliTests(unittest.TestCase):
    def _run(self, argv, dispatch=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(argv, dispatch)
        return code, out.getvalue(), err.getvalue()

    def test_plan_default_is_evaluate_only(self):
        calls = []
        code, out, _ = self._run(["plan"], dispatch=lambda p: calls.append(p) or {})
        self.assertEqual(code, 0)
        self.assertEqual(calls, [])
        self.assertFalse(json.loads(out)["ready_to_execute"])

    def test_execute_refused_without_calibration_and_release(self):
        calls = []
        code, out, _ = self._run(["plan", "--execute"], dispatch=lambda p: calls.append(p) or {})
        self.assertEqual(code, 3)
        self.assertEqual(calls, [])
        refused = json.loads(out)["execute_refused"]
        self.assertIn("OPERATOR_SCREEN_RELEASE_REQUIRED", refused)
        self.assertIn("LAYOUT_PROVISIONAL_UNCALIBRATED", refused)

    def test_execute_refused_when_ready_but_operator_has_screen(self):
        calls = []
        argv = ["plan", "--execute", "--measured-join-y", "560",
                "--calibration-source", "PRINTWINDOW_MEASURED", "--dialog-observed"]
        code, out, _ = self._run(argv, dispatch=lambda p: calls.append(p) or {})
        self.assertEqual(code, 3)
        self.assertEqual(calls, [])
        self.assertEqual(json.loads(out)["execute_refused"], ["OPERATOR_SCREEN_RELEASE_REQUIRED"])

    def test_execute_refused_for_computer_use_executor_even_when_released(self):
        calls = []
        argv = ["plan", "--execute", "--executor", "computer_use_overlay", "--operator-screen-released",
                "--measured-join-y", "560", "--calibration-source", "PRINTWINDOW_MEASURED", "--dialog-observed"]
        code, _, _ = self._run(argv, dispatch=lambda p: calls.append(p) or {})
        self.assertEqual(code, 3)
        self.assertEqual(calls, [])

    def test_gated_execute_dispatches_only_below_join_and_is_not_a_claim(self):
        calls = []
        argv = ["plan", "--execute", "--operator-screen-released", "--measured-join-y", "560",
                "--calibration-source", "OPERATOR_MEASURED", "--dialog-observed"]
        code, out, _ = self._run(argv, dispatch=lambda p: calls.append(p) or {"state": "OKAY_CLICK_DISPATCHED"})
        self.assertEqual(code, 0)
        self.assertEqual(calls, [(960, 616)])
        self.assertNotEqual(calls[0], LEGACY)
        self.assertIn("NOT_A_SEND_ALONE_CLAIM", json.loads(out)["next"])

    def test_verify_exit_codes(self):
        code, out, _ = self._run(["verify", "--lot-kind", "school"])
        self.assertEqual(code, 4)
        self.assertEqual(json.loads(out)["state"], FAIL_STATE)
        code, out, _ = self._run([
            "verify", "--lot-kind", "home", "--no-school-hud", "--no-dialog",
            "--source", "PRINTWINDOW", "--age-seconds", "3",
        ])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["state"], PASS_STATE)


if __name__ == "__main__":
    unittest.main()
