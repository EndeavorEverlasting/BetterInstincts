"""Offline camera-safe traverse: edge park fails closed; plans end at SAFE_REST."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from betterinstincts.camera_traverse import (
    CameraTraverseError,
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
