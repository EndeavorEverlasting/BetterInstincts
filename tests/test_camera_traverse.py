"""Offline camera-safe traverse: edge park fails closed; plans end at SAFE_REST."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from betterinstincts.camera_traverse import (
    CameraTraverseError,
    assess_edge_interaction,
    assess_drift_recovery,
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

    def test_default_edge_band_catches_console_strip_and_hud(self):
        cfg = load_contract()
        self.assertGreaterEqual(int(cfg["defaults"]["edge_band_px"]), 48)
        self.assertTrue(cfg["defaults"].get("post_input_safe_rest"))
        # Cheat-console strip / bottom HUD clicks must classify as edge under default band.
        top = classify_cursor(400, 20, client_width=1920, client_height=1080)
        bottom = classify_cursor(1200, 1060, client_width=1920, client_height=1080)
        self.assertTrue(top["in_edge_band"])
        self.assertTrue(bottom["in_edge_band"])

    def test_interior_is_safe(self):
        hit = classify_cursor(960, 540, client_width=1920, client_height=1080, edge_band_px=12)
        self.assertFalse(hit["in_edge_band"])
        self.assertEqual(hit["zone"], "SAFE_INTERIOR")

    def test_safe_rest_outside_band(self):
        rest = safe_rest_point(client_width=1920, client_height=1080, edge_band_px=12)
        cx, cy = rest["client"]
        again = classify_cursor(cx, cy, client_width=1920, client_height=1080, edge_band_px=12)
        self.assertFalse(again["in_edge_band"])



class EdgeInteractionSemanticsTests(unittest.TestCase):
    """P82 falsifiers: location alone cannot condemn legitimate HUD clicks."""

    def test_client_relative_guard_and_exact_boundary(self):
        cfg = load_contract()
        self.assertEqual(
            cfg["edge_interaction"]["meaning"],
            "CLIENT_RELATIVE_CAMERA_PAN_GUARD_NOT_MONITOR_BEZEL",
        )
        for x, expected in ((0, True), (47, True), (48, False), (1871, False), (1872, True), (1919, True)):
            with self.subTest(x=x):
                result = assess_edge_interaction(x, 540, client_width=1920, client_height=1080)
                self.assertEqual(result["cursor"]["in_edge_band"], expected)
        self.assertTrue(assess_edge_interaction(960, 0)["cursor"]["in_edge_band"])
        self.assertTrue(assess_edge_interaction(960, 1079)["cursor"]["in_edge_band"])

    def test_idle_host_dwell_is_forbidden_and_requires_interior_rest(self):
        result = assess_edge_interaction(4, 500, phase="REST")
        self.assertEqual(result["gate"], "CAMERA_SAFE_REST")
        self.assertEqual(result["state"], "CAMERA_EDGE_DWELL_FORBIDDEN")
        self.assertTrue(result["post_input_safe_rest_required"])
        self.assertEqual(result["safe_rest"]["client"], [960, 540])
        self.assertFalse(result["execute_allowed"])

    def test_attested_hud_edge_click_is_not_idle_parking(self):
        for x, y in ((6, 500), (800, 20), (1900, 100), (800, 1060), (1, 1)):
            with self.subTest(x=x, y=y):
                result = assess_edge_interaction(
                    x, y, phase="TARGETED_CLICK",
                    target_kind="UI_CHROME", target_verified=True,
                )
                self.assertEqual(result["state"], "EDGE_UI_CLICK_TRANSIENT")
                self.assertEqual(result["gate"], "EDGE_UI_CLICK_HOST_ADMISSION")
                self.assertTrue(result["click_geometry_candidate"])
                self.assertTrue(result["post_input_safe_rest_required"])
                self.assertFalse(result["execute_allowed"])

    def test_unknown_or_world_edge_click_stays_unadmitted(self):
        for kind, attested in (("UI_CHROME", False), ("WORLD_OBJECT", True), (None, True)):
            with self.subTest(kind=kind, attested=attested):
                result = assess_edge_interaction(
                    1, 400, phase="TARGETED_CLICK",
                    target_kind=kind, target_verified=attested,
                )
                self.assertEqual(result["gate"], "EDGE_TARGET_REOBSERVE_OR_REFRAME")
                self.assertFalse(result["click_geometry_candidate"])
                self.assertFalse(result["execute_allowed"])
                self.assertTrue(result["post_input_safe_rest_required"])
                self.assertEqual(result["safe_rest"]["zone"], "SAFE_INTERIOR")

    def test_transit_and_navigation_do_not_authorize_idle_edge_hold(self):
        for phase, gate in (
            ("TRANSIT", "TRANSIT_MUST_END_AT_SAFE_REST"),
            ("CAMERA_NAVIGATION", "CAMERA_SAFE_TRAVERSE"),
        ):
            with self.subTest(phase=phase):
                result = assess_edge_interaction(10, 540, phase=phase)
                self.assertEqual(result["gate"], gate)
                self.assertTrue(result["post_input_safe_rest_required"])
                self.assertFalse(result["execute_allowed"])

    def test_player_owned_pointer_is_never_moved_by_policy(self):
        result = assess_edge_interaction(
            2, 540, phase="REST", player_owned=True,
        )
        self.assertEqual(result["gate"], "YIELD_TO_PLAYER")
        self.assertEqual(result["action"], "NO_AGENT_POINTER_MOVEMENT")
        self.assertFalse(result["post_input_safe_rest_required"])

    def test_interior_pointer_is_not_a_pan_risk(self):
        result = assess_edge_interaction(960, 540, phase="REST")
        self.assertEqual(result["state"], "CURSOR_SAFE_INTERIOR")
        self.assertIsNone(result["gate"])

    def test_invalid_or_off_client_input_fails_closed(self):
        for xy in ((-1, 200), (1920, 200), (200, 1080), (True, 4)):
            with self.subTest(xy=xy):
                with self.assertRaises(CameraTraverseError):
                    assess_edge_interaction(*xy)
        for extra in (
            {"phase": "CLICK_UNVERIFIED"},
            {"phase": None},
            {"target_verified": 1},
            {"player_owned": 1},
        ):
            with self.subTest(extra=extra):
                with self.assertRaises(CameraTraverseError):
                    assess_edge_interaction(4, 300, **extra)

    def test_host_stack_preserves_edge_click_admission_not_needs_dispatch(self):
        turn = evaluate_turn(
            SIX, cursor_client_x=800, cursor_client_y=20,
            camera_pointer_context={
                "phase": "TARGETED_CLICK",
                "target_kind": "UI_CHROME",
                "target_verified": True,
            },
        )
        self.assertEqual(turn["next_gate"], "EDGE_UI_CLICK_HOST_ADMISSION")
        self.assertEqual(turn["fallback"]["mechanism"], "CAMERA_EDGE_INTERACTION")
        self.assertFalse(turn["fallback"]["execute_allowed"])
        self.assertEqual(turn["camera_traverse"]["cursor"]["practice"], "EDGE_UI_CLICK_TRANSIENT")

    def test_player_directed_pointer_at_edge_never_forces_agent_rest(self):
        turn = evaluate_turn(
            SIX, player_directed=True, cursor_client_x=1,
            cursor_client_y=500,
        )
        self.assertEqual(turn["next_gate"], "RESPECT_PLAYER_OR_BUSY_STATE")
        self.assertEqual(turn["camera_traverse"]["gate"], "YIELD_TO_PLAYER")
        self.assertIsNone(turn["fallback"])

    def test_host_stack_refuses_spoofed_pointer_context(self):
        with self.assertRaisesRegex(Exception, "CAMERA_POINTER_CONTEXT_REQUIRES_CURSOR"):
            evaluate_turn(SIX, camera_pointer_context={"phase": "TARGETED_CLICK"})
        with self.assertRaisesRegex(Exception, "CAMERA_POINTER_CONTEXT_UNKNOWN_FIELD"):
            evaluate_turn(
                SIX, cursor_client_x=5, cursor_client_y=4,
                camera_pointer_context={"phase": "REST", "unsafe_grant": True},
            )

    def test_host_risk_evaluation_disambiguates_click_vs_dwell(self):
        kw = dict(cursor_client_x=12, cursor_client_y=1050, client_width=1920, client_height=1080)
        dwell = evaluate_cursor_risk(**kw)
        self.assertEqual(dwell["gate"], "CAMERA_SAFE_REST")
        click = evaluate_cursor_risk(
            **kw, interaction_phase="TARGETED_CLICK",
            target_kind="UI_CHROME", target_verified=True,
        )
        self.assertEqual(click["gate"], "EDGE_UI_CLICK_HOST_ADMISSION")
        self.assertFalse(click["execute_allowed"])
        player = evaluate_cursor_risk(**kw, player_owned=True)
        self.assertEqual(player["gate"], "YIELD_TO_PLAYER")

    def test_cli_explicit_click_intent_requires_post_click_rest(self):
        from io import StringIO
        from unittest.mock import patch
        buf = StringIO()
        with patch("sys.stdout", buf):
            code = camera_cli.main([
                "evaluate", "--x", "800", "--y", "20",
                "--phase", "TARGETED_CLICK", "--target-kind", "UI_CHROME",
                "--target-verified",
            ])
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["post_input_safe_rest_required"])
        self.assertFalse(payload["execute_allowed"])


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
        self.assertEqual(out["next_gate"], "CAMERA_LOCK_REOBSERVE_OR_YIELD")
        self.assertEqual(out["fallback"]["mechanism"], "ACTIVE_SIM_CAMERA_LOCK")
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
        self.assertEqual(turn["next_gate"], "EDGE_CREEK_REGRESSION")
        self.assertEqual(turn["fallback"]["mechanism"], "EDGE_MOUSE_PARK_TO_CREEK")
        self.assertIn("EDGE_MOUSE_PARK", turn["fallback"]["forbidden"])
        self.assertIsNotNone(turn["fallback"]["recovery_chord"])

    def test_scan_plan_gate(self):
        turn = evaluate_turn(
            SIX,
            camera_scan_needed=True,
            camera_pan_directions=["E"],
        )
        self.assertEqual(turn["next_gate"], "CAMERA_LOCK_REOBSERVE_OR_YIELD")
        self.assertEqual(turn["fallback"]["mechanism"], "ACTIVE_SIM_CAMERA_LOCK")
        self.assertIsNone(turn["active_sim_camera_lock"]["map_plan"])
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



class CameraDriftRecoveryRegressionTests(unittest.TestCase):
    """Regression: camera can drift while an agent measures pixel targets."""

    def host(self, **overrides):
        from betterinstincts.scenes import load_catalog
        frame = {
            "source": "HOST_CAPTURE", "capture_ref": "capture:recover-1",
            "camera_revision": "camera:9", "camera_displaced": True,
            "camera_reanchor_attempts": 0, "cursor_client": [1917, 400],
            "game_version": load_catalog()["game_version"],
            "capture_quality": "CONTENT_PRESENT", "viewport_state": "NORMAL",
            "mode": "LIVE", "scene_id": "live_mode",
            "player_camera_owned": False, "text_entry_active": False,
            "modal_open": False, "player_queue_owned": False,
            "save_authorized": True,
            "game_clock": {
                "source": "HOST_GAME_CLOCK", "capture_ref": "capture:recover-1",
                "camera_revision": "camera:9",
                "game_version": load_catalog()["game_version"],
                "clock_revision": "clock:12", "speed_state": "PAUSED",
                "pause_indicator_active": True,
                "clock_still_during_sample": True, "pause_origin": "PLAYER",
            },
            "independent_cues": [
                {"source": "visual", "token": "live_hud"},
                {"source": "operator", "token": "live_confirmed"},
            ],
        }
        frame.update(overrides)
        return frame

    def sim(self):
        return {
            **self.host(cursor_client=[960, 540]),
            "active_sim_id": 492, "active_sim_instanced": True,
            "camera_follow_sim_id": None,
        }

    def assess(self, kind="WORLD_OBJECT", **opts):
        return assess_drift_recovery(
            target_kind=kind, capture_ref="capture:recover-1",
            observation=self.host(**opts.pop("host_changes", {})),
            client_width=1920, client_height=1080,
            target_id="A-OK Bloomer" if kind == "WORLD_OBJECT" else None,
            **opts,
        )

    def world(self, **changes):
        frame = {
            "source": "HOST_CAPTURE", "target_id": "A-OK Bloomer",
            "capture_ref": "capture:recover-1", "camera_revision": "camera:9",
            "target_visible": True, "occluded": False,
            "bbox_client": [840, 420, 1020, 600], "framing_attempts": 0,
        }
        frame.update(changes)
        return frame

    def test_edge_cursor_requires_safe_rest_before_any_target_sampling(self):
        result = self.assess(world_target_observation=self.world())
        self.assertEqual(result["gate"], "CAMERA_SAFE_REST")
        self.assertEqual(result["recovery_step"]["kind"], "SAFE_REST")
        self.assertEqual(result["safe_rest"]["client"], [960, 540])
        self.assertFalse(result["world_click_ready"])
        self.assertTrue(result["invalidate_prior_pixels"])

    def test_recenter_active_sim_only_after_cursor_is_safe(self):
        result = self.assess(
            "SIM", sim_camera_observation=self.sim(),
            host_changes={"cursor_client": [960, 540]},
        )
        self.assertEqual(result["gate"], "CAMERA_RECOVERY_REANCHOR")
        self.assertEqual(result["recovery_step"]["command"], "CENTER_ACTIVE_SIM")
        self.assertEqual(result["recovery_step"]["intent"]["effect"]["chord"], ["ENTER"])
        self.assertFalse(result["execute_allowed"])

    def test_recenter_lot_not_sim_for_lost_world_object(self):
        result = self.assess(
            sim_camera_observation=self.sim(),
            host_changes={"cursor_client": [960, 540]},
        )
        self.assertEqual(result["recovery_step"]["command"], "CENTER_CURRENT_LOT")
        self.assertEqual(result["recovery_step"]["intent"]["effect"]["chord"], ["SHIFT", "ENTER"])
        self.assertEqual(result["next_step"], "CAPTURE_NEW_FRAME_AFTER_REANCHOR")

    def test_follow_is_opt_in_game_api_not_unverified_portrait_click(self):
        result = self.assess(
            "SIM", sim_camera_observation=self.sim(), continuous_follow=True,
            host_changes={"cursor_client": [960, 540]},
        )
        self.assertEqual(result["recovery_step"]["command"], "FOLLOW_ACTIVE_SIM")
        self.assertEqual(result["recovery_step"]["intent"]["effect"]["kind"], "GAME_CAMERA_API")
        self.assertIn("UNCALIBRATED_PORTRAIT_RIGHT_CLICK", result["forbidden"])

    def test_world_target_must_match_camera_revision_and_capture(self):
        safe = {"cursor_client": [960, 540], "camera_displaced": False}
        wrong = self.assess(world_target_observation=self.world(camera_revision="camera:old"), host_changes=safe)
        self.assertEqual(wrong["gate"], "CAMERA_RECOVERY_REOBSERVE")
        self.assertFalse(wrong["world_click_ready"])
        ready = self.assess(world_target_observation=self.world(), host_changes=safe)
        self.assertEqual(ready["gate"], "WORLD_TARGET_AWAIT_HOST_ADMISSION")
        self.assertEqual(ready["target_framing"]["click_candidate"], [930, 510])
        self.assertTrue(ready["world_click_ready"])
        self.assertFalse(ready["execute_allowed"])

    def test_post_recenter_missing_direction_never_reanchors_forever(self):
        safe = {"cursor_client": [960, 540], "camera_reanchor_attempts": 1}
        unknown = self.assess(host_changes=safe, sim_camera_observation=self.sim())
        self.assertEqual(unknown["gate"], "CAMERA_RECOVERY_REOBSERVE")
        self.assertEqual(unknown["reason"], "OBSERVED_PAN_DIRECTION_REQUIRED")
        measured = self.assess(host_changes=safe, reframe_directions=("W",))
        self.assertEqual(measured["gate"], "CAMERA_RECOVERY_TRAVERSE")
        self.assertEqual(measured["recovery_step"]["plan"]["steps"][-1]["kind"], "SAFE_REST")
        refused = self.assess(host_changes={**safe, "camera_reanchor_attempts": 2})
        self.assertEqual(refused["gate"], "CAMERA_RECOVERY_MANUAL_REVIEW")

    def test_player_modal_unknown_cursor_and_scene_abstain(self):
        for bad in [
            {"player_camera_owned": True}, {"text_entry_active": True},
            {"modal_open": True}, {"player_queue_owned": True},
            {"save_authorized": False}, {"cursor_client": None},
            {"camera_revision": ""}, {"camera_displaced": None},
            {"scene_id": "main_menu"}, {"game_version": "unknown"},
        ]:
            with self.subTest(change=bad):
                result = self.assess(host_changes=bad, sim_camera_observation=self.sim())
                self.assertNotIn(result["gate"], ("CAMERA_RECOVERY_REANCHOR", "WORLD_TARGET_AWAIT_HOST_ADMISSION"))
                self.assertFalse(result["execute_allowed"])

    def test_host_stack_recovery_outranks_pixel_framing_and_pan(self):
        world = {
            "target_id": "A-OK Bloomer", "observation": self.world(),
            "reframe_directions": ("E",),
        }
        request = {
            "target_kind": "WORLD_OBJECT", "target_id": "A-OK Bloomer",
            "observation": self.host(cursor_client=[960, 540]),
            "world_target_observation": self.world(),
        }
        turn = evaluate_turn(
            SIX, capture_ref="capture:recover-1", client_width=1920,
            client_height=1080, camera_pan_directions=("E",),
            world_target=world, camera_recovery=request,
            sim_camera_observation=self.sim(),
        )
        self.assertEqual(turn["next_gate"], "CAMERA_RECOVERY_REANCHOR")
        self.assertFalse(turn["fallback"]["execute_allowed"])
        self.assertTrue(turn["camera_recovery"]["invalidate_prior_pixels"])

    def test_player_directed_never_dispatches_recovery(self):
        turn = evaluate_turn(
            SIX, capture_ref="capture:recover-1", player_directed=True,
            client_width=1920, client_height=1080,
            camera_recovery={
                "target_kind": "LOT",
                "observation": self.host(cursor_client=[960, 540]),
            },
            sim_camera_observation=self.sim(),
        )
        self.assertEqual(turn["next_gate"], "RESPECT_PLAYER_OR_BUSY_STATE")
        self.assertFalse(turn["fallback"]["execute_allowed"])

    def test_unknown_evidence_never_mints_camera_action(self):
        result = assess_drift_recovery(
            target_kind="SIM", capture_ref="capture:recover-1",
            observation=None, client_width=1920, client_height=1080,
        )
        self.assertEqual(result["gate"], "CAMERA_RECOVERY_REOBSERVE")
        self.assertIsNone(result.get("recovery_step"))


if __name__ == "__main__":
    unittest.main()
