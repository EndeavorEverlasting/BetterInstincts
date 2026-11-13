"""P82 falsifiers: deterministic zero-first scan and smooth one-gesture candidate."""
from __future__ import annotations

import os
import subprocess
import sys
import unittest

from betterinstincts.observation_sweep import (
    ObservationSweepError, plan_observation_sweep,
)


def baseline(**extra):
    return dict(
        camera_revision="camera7", capture_revision="camera7", floor_id="FLOOR_1",
        required_objects=["shelf", "fridge"], observed_objects=["fridge"],
        candidate_views=[
            dict(view_id="right", floor_id="FLOOR_1", camera_revision="camera7",
                 source="OPERATOR_VERIFIED", evidence_refs=["c1", "c2"],
                 evidence_source_classes=["HOST_CAPTURE", "OPERATOR_REVIEW"],
                 visible_objects=["shelf"], pan_delta_px=[120, 30]),
            dict(view_id="left", floor_id="FLOOR_1", camera_revision="camera7",
                 source="HOST_CALIBRATED", evidence_refs=["c3", "c4"],
                 evidence_source_classes=["HOST_CAPTURE", "EA_FILE"],
                 visible_objects=["shelf"], pan_delta_px=[-180, 20]),
        ],
        viewport_px=(1920, 1080), edge_band_px=48,
        motion_opt_in=True,
        **extra,
    )


class ObservationSweepTests(unittest.TestCase):
    def test_one_stable_monotone_trajectory_not_compass_jitter(self):
        plan = plan_observation_sweep(**baseline())
        self.assertEqual(plan["state"], "ONE_CONTINUOUS_VIEW_PROPOSAL")
        self.assertEqual(plan["selected_view_id"], "right")
        self.assertEqual(plan["gesture_count"], 1)
        self.assertEqual(plan["trajectory_profile"], "MINIMUM_JERK_QUINTIC_C2")
        self.assertFalse(plan["execute_allowed"])
        pts = plan["trajectory_client"]
        self.assertGreaterEqual(len(pts), 7)
        self.assertEqual(pts[0], [960, 540])
        self.assertEqual(pts[-1], [1080, 570])
        self.assertTrue(all(a[0] <= b[0] and a[1] <= b[1] for a, b in zip(pts, pts[1:])))
        self.assertEqual(plan, plan_observation_sweep(**baseline()))

    def test_order_independent_candidate_selection(self):
        one = baseline()
        other = baseline()
        other["candidate_views"].reverse()
        other["required_objects"].reverse()
        self.assertEqual(plan_observation_sweep(**one), plan_observation_sweep(**other))

    def test_no_move_when_coverage_complete_or_camera_stale(self):
        kw = baseline()
        kw["observed_objects"] = ["shelf", "fridge"]
        self.assertEqual(plan_observation_sweep(**kw)["state"], "REUSE_OBSERVED_COVERAGE")
        kw = baseline()
        kw["capture_revision"] = "older"
        result = plan_observation_sweep(**kw)
        self.assertEqual(result["state"], "HOLD_STALE_CAMERA")
        self.assertEqual(result["gesture_count"], 0)

    def test_no_oscillation_or_unproven_view(self):
        kw = baseline()
        kw["previous_view_id"] = "right"
        self.assertEqual(plan_observation_sweep(**kw)["selected_view_id"], "left")
        kw["previous_view_id"] = "left"
        kw["candidate_views"] = kw["candidate_views"][1:]
        self.assertEqual(plan_observation_sweep(**kw)["state"], "CAPTURE_IN_PLACE")
        kw = baseline()
        kw["candidate_views"][0]["evidence_refs"] = ["same"]
        self.assertEqual(plan_observation_sweep(**kw)["selected_view_id"], "left")

    def test_player_and_unsafe_inputs_never_get_motion(self):
        kw = baseline()
        kw["player_active"] = True
        self.assertEqual(plan_observation_sweep(**kw)["state"], "YIELD_TO_PLAYER")
        invalid = [
            ("camera_revision", "../bad"), ("viewport_px", [200, 100]),
            ("edge_band_px", 400), ("player_active", 1),
        ]
        for key, value in invalid:
            with self.subTest(key=key):
                data = baseline()
                data[key] = value
                with self.assertRaises(ObservationSweepError):
                    plan_observation_sweep(**data)

    def test_floor_mismatch_and_no_novelty_capture_in_place(self):
        kw = baseline()
        for view in kw["candidate_views"]:
            view["floor_id"] = "FLOOR_2"
        self.assertEqual(plan_observation_sweep(**kw)["state"], "CAPTURE_IN_PLACE")
        kw = baseline()
        for view in kw["candidate_views"]:
            view["visible_objects"] = ["fridge"]
        self.assertEqual(plan_observation_sweep(**kw)["gesture_count"], 0)

    def test_room_mapper_exposes_advisory_survey_without_actuator(self):
        from betterinstincts.room_map_traverse import plan_room_map_traverse
        room = plan_room_map_traverse(goal_id="inspect", target_kind="ROBOTICS_WORKSTATION")
        self.assertEqual(room["reassessment"]["state"], "CAPTURE_IN_PLACE")
        self.assertFalse(room["reassessment"]["execute_allowed"])
        room = plan_room_map_traverse(goal_id="inspect", target_kind="ROBOTICS_WORKSTATION",
                                      survey=baseline())
        self.assertEqual(room["reassessment"]["gesture_count"], 1)
        self.assertEqual(room["scan_priority"], "EA_EVIDENCE_THEN_STATIONARY_CAPTURE_THEN_ONE_SMOOTH_GESTURE")

    def test_opt_in_denied_by_default_and_pending_capture_blocks_motion(self):
        data = baseline()
        data["motion_opt_in"] = False
        no_consent = plan_observation_sweep(**data)
        self.assertEqual(no_consent["state"], "HOLD_MOTION_PROPOSAL_NOT_OPTED_IN")
        self.assertEqual(no_consent["gesture_count"], 0)
        self.assertFalse(no_consent["execute_allowed"])
        data = baseline()
        data["pending_view_id"] = "right"
        pending = plan_observation_sweep(**data)
        self.assertEqual(pending["state"], "AWAIT_POST_MOTION_OBSERVATION")
        self.assertEqual(pending["gesture_count"], 0)
        self.assertFalse(pending["execute_allowed"])

    def test_recent_visited_views_cannot_cycle_back_and_forth(self):
        data = baseline()
        data["recent_view_ids"] = ("left", "right")
        result = plan_observation_sweep(**data)
        self.assertEqual(result["state"], "CAPTURE_IN_PLACE")
        self.assertEqual(result["gesture_count"], 0)
        data["recent_view_ids"] = ("left",)
        self.assertEqual(plan_observation_sweep(**data)["selected_view_id"], "right")
        data["recent_view_ids"] = tuple("v" + str(i) for i in range(9))
        with self.assertRaisesRegex(ObservationSweepError, "INVALID_RECENT_VIEW_IDS"):
            plan_observation_sweep(**data)

    def test_distinct_evidence_classes_are_required_for_motion(self):
        data = baseline()
        data["candidate_views"][0].pop("evidence_source_classes")
        result = plan_observation_sweep(**data)
        self.assertEqual(result["selected_view_id"], "left")
        data = baseline()
        data["candidate_views"][0]["evidence_source_classes"] = ["HOST_CAPTURE", "HOST_CAPTURE"]
        with self.assertRaisesRegex(ObservationSweepError, "DUPLICATE_EVIDENCE_SOURCE_CLASSES"):
            plan_observation_sweep(**data)
        data = baseline()
        for view in data["candidate_views"]:
            view["evidence_source_classes"] = ["UNTRUSTED", "HOST_CAPTURE"]
        self.assertEqual(plan_observation_sweep(**data)["gesture_count"], 0)

    def test_quintic_endpoints_have_zero_first_and_second_derivatives(self):
        # Analytical derivative of 10*t**3 - 15*t**4 + 6*t**5.
        d1 = lambda t: 30 * t * t * (1 - t) ** 2
        d2 = lambda t: 60 * t * (1 - t) * (1 - 2 * t)
        for t in (0.0, 1.0):
            self.assertEqual(d1(t), 0.0)
            self.assertEqual(d2(t), 0.0)
        plan = plan_observation_sweep(**baseline())
        self.assertEqual(plan["trajectory_profile"], "MINIMUM_JERK_QUINTIC_C2")
        self.assertLessEqual(len(plan["trajectory_client"]), 13)
        self.assertTrue(all(a[0] <= b[0] for a, b in zip(
            plan["trajectory_client"], plan["trajectory_client"][1:])))

    def test_small_camera_nudge_has_no_motion_benefit(self):
        data = baseline()
        for view in data["candidate_views"]:
            view["pan_delta_px"] = [1, 1]
        self.assertEqual(plan_observation_sweep(**data)["state"], "CAPTURE_IN_PLACE")

    def test_invalid_bool_opt_in_fails_closed(self):
        data = baseline()
        data["motion_opt_in"] = 1
        with self.assertRaisesRegex(ObservationSweepError, "INVALID_MOTION_OPT_IN"):
            plan_observation_sweep(**data)


if __name__ == "__main__":
    unittest.main()
