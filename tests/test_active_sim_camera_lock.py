"""Regression: autonomous Sims camera must never park over an unrelated street."""
from __future__ import annotations

import unittest
from contextlib import contextmanager
from unittest.mock import patch

from betterinstincts.active_sim_camera_lock import evaluate_active_sim_camera_lock
from betterinstincts.host_stack import evaluate_turn
from betterinstincts.scenes import load_catalog
from betterinstincts.camera_traverse import plan_traverse, CameraTraverseError
from scripts.camera_traverse import _execute_plan

SIX = dict.fromkeys(("hunger", "bladder", "energy", "hygiene", "fun", "social"), 0.8)
CAPTURE = "capture:anchor-1"


def observed(**overrides):
    data = {
        "source": "HOST_CAPTURE",
        "capture_ref": CAPTURE,
        "scene_id": "live_mode",
        "mode": "LIVE",
        "game_version": load_catalog()["game_version"],
        "capture_quality": "CONTENT_PRESENT",
        "viewport_state": "NORMAL",
        "save_authorized": True,
        "player_queue_owned": False,
        "text_entry_active": False,
        "modal_open": False,
        "player_camera_owned": False,
        "camera_revision": "camera:1",
        "active_sim_id": 492,
        "active_sim_instanced": True,
        "camera_follow_sim_id": None,
        "camera_centered_sim_id": None,
        "camera_displaced": True,
        "active_goal_id": "goal:find-shelf",
        "map_target_id": "item:a-ok-bloomer",
        "map_goal_source": "HOST_TASK",
        "independent_cues": [
            {"source": "visual", "token": "live_hud"},
            {"source": "operator", "token": "live_confirmed"},
        ],
    }
    data.update(overrides)
    return data


def goal(**changes):
    data = {
        "goal_id": "goal:find-shelf",
        "target_id": "item:a-ok-bloomer",
        "capture_ref": CAPTURE,
        "camera_revision": "camera:1",
        "active_sim_id": 492,
        "issued_at_ms": 100_000,
    }
    data.update(changes)
    return data


def lock(obs=None, **kw):
    return evaluate_active_sim_camera_lock(
        capture_ref=CAPTURE, observation=observed() if obs is None else obs, **kw,
    )


class ActiveSimCameraLockTests(unittest.TestCase):
    def test_camera_is_always_recentered_by_default(self):
        out = lock()
        self.assertEqual(out["gate"], "CAMERA_ACTIVE_SIM_CENTER_REQUIRED")
        self.assertEqual(out["center"]["effect"]["chord"], ["ENTER"])
        self.assertFalse(out["execute_allowed"])
        self.assertNotIn("SHIFT", out["center"]["effect"]["chord"])

    def test_follow_or_verified_center_is_a_stable_lock(self):
        for obs in (
            observed(camera_follow_sim_id=492),
            observed(camera_centered_sim_id=492, camera_displaced=False),
        ):
            with self.subTest(obs=obs.get("camera_follow_sim_id")):
                self.assertEqual(lock(obs)["gate"], "CAMERA_ACTIVE_SIM_LOCKED")

    def test_never_pan_for_a_generic_scan_or_missing_target(self):
        anchored = observed(camera_centered_sim_id=492, camera_displaced=False)
        result = lock(anchored, map_requested=True, directions=("E",))
        self.assertEqual(result["gate"], "CAMERA_MAP_GOAL_REQUIRED")
        self.assertIsNone(result["map_plan"])

    def test_map_exception_needs_verified_goal_and_already_anchored_sim(self):
        candidate = lock(
            observed(camera_centered_sim_id=492, camera_displaced=False),
            map_requested=True, map_goal=goal(), directions=("E",),
            now_ms=105_000,
        )
        self.assertEqual(candidate["gate"], "CAMERA_MAP_LEASE_READY")
        self.assertEqual(candidate["restore"]["chord"], ["ENTER"])
        self.assertTrue(candidate["restore"]["required_in_finally"])
        self.assertEqual(candidate["map_plan"]["steps"][-1]["kind"], "SAFE_REST")
        self.assertFalse(candidate["execute_allowed"])
        not_anchored = lock(
            map_requested=True, map_goal=goal(), directions=("E",), now_ms=105_000,
        )
        self.assertEqual(not_anchored["gate"], "CAMERA_ACTIVE_SIM_CENTER_REQUIRED")
        self.assertIsNone(not_anchored["map_plan"])

    def test_stale_mismatched_or_uncorroborated_goals_never_pan(self):
        anchored = observed(camera_follow_sim_id=492)
        cases = [
            (goal(goal_id="other"), 105_000, anchored),
            (goal(camera_revision="stale"), 105_000, anchored),
            (goal(active_sim_id=True), 105_000, anchored),
            (goal(issued_at_ms=0), 105_000, anchored),
            (goal(), 130_001, anchored),
            (goal(), None, anchored),
            (goal(), 105_000, observed(camera_follow_sim_id=492, map_goal_source="AGENT_GUESS")),
            (goal(), 105_000, observed(camera_follow_sim_id=492, player_camera_owned=True)),
            (goal(), 105_000, observed(camera_follow_sim_id=492, text_entry_active=True)),
        ]
        for lease, now, scene in cases:
            with self.subTest(lease=lease, now=now, scene=scene.get("map_goal_source")):
                result = lock(scene, map_requested=True, map_goal=lease, directions=("N",), now_ms=now)
                self.assertNotEqual(result["gate"], "CAMERA_MAP_LEASE_READY")
                self.assertIsNone(result["map_plan"])

    def test_host_stack_stops_street_pan_until_named_goal(self):
        blocked = evaluate_turn(
            SIX, capture_ref=CAPTURE, camera_scan_needed=True,
            camera_pan_directions=("E",), sim_camera_observation=observed(
                camera_centered_sim_id=492, camera_displaced=False,
            ),
        )
        self.assertEqual(blocked["next_gate"], "CAMERA_MAP_GOAL_REQUIRED")
        self.assertEqual(blocked["fallback"]["mechanism"], "ACTIVE_SIM_CAMERA_LOCK")
        self.assertFalse(blocked["fallback"]["execute_allowed"])
        leased = evaluate_turn(
            SIX, capture_ref=CAPTURE, camera_scan_needed=True,
            camera_pan_directions=("E",), sim_camera_observation=observed(
                camera_centered_sim_id=492, camera_displaced=False,
            ),
            camera_map_goal=goal(), camera_clock_ms=105_000,
        )
        self.assertEqual(leased["next_gate"], "CAMERA_MAP_LEASE_READY")
        self.assertFalse(leased["fallback"]["execute_allowed"])

    def test_host_stack_auto_recenter_when_sensor_provided(self):
        turn = evaluate_turn(SIX, capture_ref=CAPTURE, sim_camera_observation=observed())
        self.assertEqual(turn["next_gate"], "CAMERA_ACTIVE_SIM_CENTER_REQUIRED")
        self.assertEqual(turn["active_sim_camera_lock"]["sim_id"], 492)
        player = evaluate_turn(
            SIX, capture_ref=CAPTURE, player_directed=True,
            sim_camera_observation=observed(player_camera_owned=True),
        )
        self.assertEqual(player["next_gate"], "RESPECT_PLAYER_OR_BUSY_STATE")


class ScopedMapExecutionTests(unittest.TestCase):
    def test_cli_style_unscoped_map_movement_is_rejected_without_input(self):
        steps = plan_traverse(("E",))
        with patch("scripts.win32_input.right_drag") as drag:
            with self.assertRaisesRegex(CameraTraverseError, "GOAL_SCOPED_MAP_LEASE"):
                _execute_plan(steps, process_id=303, session_id="demo", idle_ms=15000)
            drag.assert_not_called()

    def test_injected_host_map_lease_restores_with_enter_not_lot(self):
        effects = []
        seen = observed(camera_centered_sim_id=492, camera_displaced=False)
        @contextmanager
        def fake_lease(*args, **kwargs):
            def ready():
                effects.append("admitted")
            yield ready

        with patch("betterinstincts.screen_admit.require_execute_session"), \
             patch("betterinstincts.screen_admit.admitted_screen_lease", fake_lease), \
             patch("scripts.win32_input.right_drag", lambda *a, **k: effects.append("pan")), \
             patch("scripts.win32_input.send_key_chord", lambda c: effects.append(tuple(c))), \
             patch("scripts.camera_traverse._park_cursor"), \
             patch("scripts.camera_traverse.time.sleep"):
            out = _execute_plan(
                plan_traverse(("E",)), process_id=303, session_id="demo",
                idle_ms=15000, map_goal=goal(), observe=lambda: seen,
                now_ms=105_000,
            )
        self.assertIn("pan", effects)
        self.assertIn(("ENTER",), effects)
        self.assertNotIn(("SHIFT", "ENTER"), effects)
        self.assertEqual(out["restoration"], "ENTER_DISPATCHED_REOBSERVE_REQUIRED")

    def test_human_owned_camera_blocks_map_before_native_input(self):
        owned = observed(camera_follow_sim_id=492, player_camera_owned=True)
        with patch("scripts.win32_input.right_drag") as drag:
            with self.assertRaisesRegex(CameraTraverseError, "CAMERA_MAP_LEASE_REFUSED"):
                _execute_plan(
                    plan_traverse(("E",)), process_id=303, session_id="demo",
                    idle_ms=15000, map_goal=goal(), observe=lambda: owned,
                    now_ms=105_000,
                )
            drag.assert_not_called()


if __name__ == "__main__":
    unittest.main()
