"""Offline camera-safe traverse: edge park fails closed; plans end at SAFE_REST."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from betterinstincts.camera_traverse import (
    CameraTraverseError,
    assess_world_target,
    classify_cursor,
    classify_practice,
    evaluate_cursor_risk,
    load_contract,
    plan_traverse,
    safe_rest_point,
)
from betterinstincts.host_stack import evaluate_turn
from scripts import camera_traverse as camera_cli
from scripts import win32_input

ROOT = Path(__file__).resolve().parents[1]
SIX = {
    "hunger": 0.8,
    "bladder": 0.8,
    "energy": 0.8,
    "hygiene": 0.8,
    "fun": 0.8,
    "social": 0.8,
}


class CameraTraverseContractTests(unittest.TestCase):
    def test_contract_selects_camera_safe_traverse(self):
        cfg = load_contract()
        self.assertEqual(cfg["architecture"]["selected"], "CAMERA_SAFE_TRAVERSE")
        self.assertIn("EDGE_MOUSE_PARK", cfg["forbidden"])
        self.assertIn("CONTINUOUS_EDGE_HOLD", cfg["forbidden"])


class CursorZoneTests(unittest.TestCase):
    def test_edge_band_detected(self):
        hit = classify_cursor(3, 540, client_width=1920, client_height=1080, edge_band_px=12)
        self.assertTrue(hit["in_edge_band"])
        self.assertEqual(hit["practice"], "EDGE_MOUSE_PARK")

    def test_interior_is_safe(self):
        hit = classify_cursor(960, 540, client_width=1920, client_height=1080, edge_band_px=12)
        self.assertFalse(hit["in_edge_band"])
        self.assertEqual(hit["zone"], "SAFE_INTERIOR")

    def test_safe_rest_outside_band(self):
        rest = safe_rest_point(client_width=1920, client_height=1080, edge_band_px=12)
        cx, cy = rest["client"]
        again = classify_cursor(cx, cy, client_width=1920, client_height=1080, edge_band_px=12)
        self.assertFalse(again["in_edge_band"])


class PracticeAndPlanTests(unittest.TestCase):
    def test_edge_park_is_bad(self):
        row = classify_practice("EDGE_MOUSE_PARK")
        self.assertEqual(row["verdict"], "BAD_BEHAVIOR")
        self.assertTrue(row["forbidden"])

    def test_plan_terminates_with_safe_rest(self):
        plan = plan_traverse(["E", "N"], client_width=1920, client_height=1080)
        self.assertEqual(plan["steps"][-1]["kind"], "SAFE_REST")
        self.assertEqual(plan["steps"][0]["kind"], "CAPTURE_OBSERVE")
        kinds = [s["kind"] for s in plan["steps"]]
        self.assertIn("RIGHT_DRAG_PAN", kinds)
        self.assertEqual(plan["gate"], "CAMERA_SAFE_TRAVERSE")

    def test_capture_only_gate(self):
        plan = plan_traverse([], prefer_capture_first=True)
        self.assertEqual(plan["gate"], "CAPTURE_BEFORE_EDGE_SCAN")
        self.assertEqual(plan["steps"][-1]["kind"], "SAFE_REST")

    def test_too_many_steps_fail_closed(self):
        with self.assertRaises(CameraTraverseError) as ctx:
            plan_traverse(["E"] * 20)
        self.assertEqual(str(ctx.exception), "TOO_MANY_PAN_STEPS")


class EvaluateRiskTests(unittest.TestCase):
    def test_edge_park_gate(self):
        out = evaluate_cursor_risk(cursor_client_x=2, cursor_client_y=100)
        self.assertEqual(out["gate"], "CAMERA_SAFE_REST")
        self.assertEqual(out["action"], "SAFE_CURSOR_REST")

    def test_scan_without_cursor_still_plans(self):
        out = evaluate_cursor_risk(camera_scan_needed=True, directions=["W"])
        self.assertEqual(out["gate"], "CAMERA_SAFE_TRAVERSE")
        self.assertEqual(out["plan"]["steps"][-1]["kind"], "SAFE_REST")




class CameraFirstWorldTargetTests(unittest.TestCase):
    CAPTURE = "capture:target-frame"

    def observed(self, **changes):
        data = {
            "source": "HOST_CAPTURE",
            "target_id": "A-OK Bloomer",
            "capture_ref": self.CAPTURE,
            "camera_revision": "camera:42",
            "target_visible": True,
            "occluded": False,
            "bbox_client": [840, 420, 1020, 600],
            "framing_attempts": 0,
        }
        data.update(changes)
        return data

    def assess(self, observation=None, **changes):
        return assess_world_target(
            target_id="A-OK Bloomer", capture_ref=self.CAPTURE,
            observation=self.observed() if observation is None else observation,
            client_width=1920, client_height=1080, **changes,
        )

    def test_already_framed_target_is_ready_without_camera_motion(self):
        result = self.assess()
        self.assertTrue(result["click_ready"])
        self.assertFalse(result["execute_allowed"])
        self.assertEqual(result["gate"], "WORLD_TARGET_AWAIT_HOST_ADMISSION")
        self.assertEqual(result["click_candidate"], [930, 510])
        self.assertIsNone(result["camera_plan"])

    def test_missing_or_stale_host_frame_requires_reobservation(self):
        for obs in (
            {},
            self.observed(capture_ref="capture:previous"),
            self.observed(target_id="another-object"),
            self.observed(source="MODEL_GUESS"),
            self.observed(camera_revision=""),
            self.observed(target_visible=None),
            self.observed(bbox_client=None),
        ):
            with self.subTest(observation=obs):
                result = self.assess(observation=obs)
                self.assertFalse(result["click_ready"])
                self.assertEqual(result["gate"], "CAMERA_TARGET_REOBSERVE_REQUIRED")
                self.assertIsNone(result["click_candidate"])

    def test_reframe_before_click_when_target_is_hard_to_hit(self):
        cases = [
            ({"occluded": True}, "TARGET_OCCLUDED"),
            ({"target_visible": False}, "TARGET_NOT_VISIBLE"),
            ({"bbox_client": [0, 400, 80, 500]}, "TARGET_TOO_CLOSE_TO_VIEWPORT_EDGE"),
            ({"bbox_client": [900, 500, 920, 525]}, "TARGET_TOO_SMALL_TO_CLICK_RELIABLY"),
            ({"bbox_client": [-10, 400, 90, 500]}, "TARGET_CLIPPED_OR_OFFSCREEN"),
        ]
        for changes, reason in cases:
            with self.subTest(changes=changes):
                result = self.assess(self.observed(**changes), reframe_directions=("E",))
                self.assertEqual(result["gate"], "CAMERA_TARGET_REFRAME_REQUIRED")
                self.assertEqual(result["reason"], reason)
                self.assertFalse(result["click_ready"])
                self.assertEqual(result["camera_plan"]["steps"][-1]["kind"], "SAFE_REST")
                self.assertIn("RIGHT_DRAG_PAN", [x["kind"] for x in result["camera_plan"]["steps"]])
                self.assertTrue(result["reobserve_after_camera_change"])

    def test_no_host_pan_direction_means_observe_not_blind_scroll(self):
        result = self.assess(self.observed(occluded=True))
        self.assertEqual(result["camera_plan"]["gate"], "CAPTURE_BEFORE_EDGE_SCAN")
        self.assertNotIn("RIGHT_DRAG_PAN", [s["kind"] for s in result["camera_plan"]["steps"]])
        self.assertFalse(result["execute_allowed"])

    def test_attempt_budget_blocks_repeated_camera_thrashing(self):
        result = self.assess(self.observed(occluded=True, framing_attempts=3))
        self.assertEqual(result["gate"], "CAMERA_TARGET_MANUAL_REVIEW")
        self.assertIsNone(result["camera_plan"])
        self.assertFalse(result["click_ready"])

    def test_invalid_geometry_and_unknown_directions_fail_closed(self):
        with self.assertRaisesRegex(CameraTraverseError, "WORLD_CLIENT_GEOMETRY_REQUIRED"):
            assess_world_target(
                target_id="object", capture_ref=self.CAPTURE,
                observation=self.observed(target_id="object"), client_width=None,
                client_height=1080,
            )
        with self.assertRaisesRegex(CameraTraverseError, "UNKNOWN_PAN_DIRECTION"):
            self.assess(self.observed(occluded=True), reframe_directions=("GUESS",))

    def test_host_stack_uses_camera_gate_before_a_world_click(self):
        requested = {"target_id": "A-OK Bloomer", "observation": self.observed(occluded=True), "reframe_directions": ["W"]}
        out = evaluate_turn(
            SIX, capture_ref=self.CAPTURE,
            client_width=1920, client_height=1080, world_target=requested,
        )
        self.assertEqual(out["next_gate"], "CAMERA_TARGET_REFRAME_REQUIRED")
        self.assertEqual(out["fallback"]["mechanism"], "CAMERA_FIRST_WORLD_TARGET")
        self.assertFalse(out["world_target_framing"]["click_ready"])
        self.assertEqual(out["world_target_framing"]["camera_plan"]["steps"][-1]["kind"], "SAFE_REST")

    def test_host_stack_admission_and_player_authority_stay_distinct(self):
        requested = {"target_id": "A-OK Bloomer", "observation": self.observed()}
        ready = evaluate_turn(
            SIX, capture_ref=self.CAPTURE,
            client_width=1920, client_height=1080, world_target=requested,
        )
        self.assertEqual(ready["next_gate"], "WORLD_TARGET_AWAIT_HOST_ADMISSION")
        self.assertFalse(ready["fallback"]["execute_allowed"])
        busy = evaluate_turn(
            SIX, capture_ref=self.CAPTURE, player_directed=True,
            client_width=1920, client_height=1080, world_target=requested,
        )
        self.assertEqual(busy["next_gate"], "RESPECT_PLAYER_OR_BUSY_STATE")

class HostStackIntegrationTests(unittest.TestCase):
    def test_edge_park_outranks_needs(self):
        turn = evaluate_turn(
            SIX,
            cursor_client_x=1,
            cursor_client_y=500,
            client_width=1920,
            client_height=1080,
        )
        self.assertEqual(turn["next_gate"], "CAMERA_SAFE_REST")
        self.assertEqual(turn["fallback"]["mechanism"], "SAFE_CURSOR_REST")
        self.assertIn("EDGE_MOUSE_PARK", turn["fallback"]["forbidden"])

    def test_scan_plan_gate(self):
        turn = evaluate_turn(
            SIX,
            camera_scan_needed=True,
            camera_pan_directions=["E"],
        )
        self.assertEqual(turn["next_gate"], "CAMERA_SAFE_TRAVERSE")
        self.assertEqual(turn["fallback"]["mechanism"], "CAMERA_SAFE_TRAVERSE")
        self.assertEqual(turn["camera_traverse"]["plan"]["steps"][-1]["kind"], "SAFE_REST")


class CliAndPrimitiveTests(unittest.TestCase):
    def test_cli_classify_json(self):
        code = camera_cli.main(["classify", "--x", "4", "--y", "10"])
        self.assertEqual(code, 0)

    def test_cli_plan_ends_safe_rest(self):
        # Capture stdout via subprocess-less path: call plan_traverse through main print.
        from io import StringIO
        import sys

        buf = StringIO()
        old = sys.stdout
        try:
            sys.stdout = buf
            code = camera_cli.main(["plan", "--dir", "S"])
        finally:
            sys.stdout = old
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["steps"][-1]["kind"], "SAFE_REST")

    def test_move_cursor_fails_closed_off_windows(self):
        from unittest.mock import patch

        with patch.object(win32_input.sys, "platform", "linux"):
            with self.assertRaises(win32_input.Win32InputError):
                win32_input.move_cursor(10, 10)


if __name__ == "__main__":
    unittest.main()
