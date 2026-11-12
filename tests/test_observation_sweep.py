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
                 visible_objects=["shelf"], pan_delta_px=[120, 30]),
            dict(view_id="left", floor_id="FLOOR_1", camera_revision="camera7",
                 source="HOST_CALIBRATED", evidence_refs=["c3", "c4"],
                 visible_objects=["shelf"], pan_delta_px=[-180, 20]),
        ],
        viewport_px=(1920, 1080), edge_band_px=48,
        **extra,
    )


class ObservationSweepTests(unittest.TestCase):
    def test_one_stable_monotone_trajectory_not_compass_jitter(self):
        plan = plan_observation_sweep(**baseline())
        self.assertEqual(plan["state"], "ONE_CONTINUOUS_VIEW_PROPOSAL")
        self.assertEqual(plan["selected_view_id"], "right")
        self.assertEqual(plan["gesture_count"], 1)
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

if __name__ == "__main__":
    unittest.main()
