"""P82: camera centering, app-scoped follow, and cooperative host admission."""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import types
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from betterinstincts.host_stack import evaluate_turn
from betterinstincts.player_presence import PresenceProbe
from betterinstincts.scenes import load_catalog
from betterinstincts.sim_camera import (
    CENTER_LOT, CENTER_SIM, FOLLOW_SIM, SimCameraError,
    command_from_app_hotkey, enqueue_sim_camera, plan_sim_camera,
)
from betterinstincts.ui_chrome import load_contract as load_chrome
from betterinstincts.workflow_interop import CooperativeScreenQueue
from scripts.sim_camera import center_on_admitted_host, follow_active_sim_in_game
from scripts.sim_camera import main as camera_cli

SIX = dict.fromkeys(("hunger", "bladder", "energy", "hygiene", "fun", "social"), 0.8)


def observed(**overrides):
    row = {
        "source": "HOST_CAPTURE",
        "capture_ref": "capture:focus-1",
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
        "independent_cues": [
            {"source": "visual", "token": "live_hud"},
            {"source": "operator", "token": "live_confirmed"},
        ],
    }
    row.update(overrides)
    return row


def plan(command, obs=None):
    return plan_sim_camera(
        command, capture_ref="capture:focus-1",
        observation=observed() if obs is None else obs,
    )


class SimCameraPolicyTests(unittest.TestCase):
    def test_native_center_and_lot_are_different(self):
        center = plan(CENTER_SIM)
        lot = plan(CENTER_LOT)
        self.assertEqual(center["effect"]["chord"], ["ENTER"])
        self.assertEqual(lot["effect"]["chord"], ["SHIFT", "ENTER"])
        self.assertEqual(center["effect"]["kind"], "SEND_KEY_CHORD")
        self.assertEqual(lot["effect"]["kind"], "SEND_KEY_CHORD")
        self.assertFalse(center["execute_allowed"])
        self.assertEqual(load_chrome()["modes"]["LIVE"]["hotkeys"][-3]["id"], CENTER_SIM)

    def test_follow_is_game_api_not_a_fake_native_hotkey(self):
        p = plan(FOLLOW_SIM)
        self.assertEqual(p["effect"]["kind"], "GAME_CAMERA_API")
        self.assertTrue(p["effect"]["follow"])
        self.assertEqual(p["effect"]["sim_id"], 492)
        self.assertNotIn("chord", p["effect"])
        self.assertFalse(p["execute_allowed"])
        self.assertFalse(load_chrome()["app_hotkeys"]["follow_active_sim"]["registered_with_os"])

    def test_app_hotkey_requires_explicit_scoped_input(self):
        good = {
            "source": "APP_SCOPED_HOST_HOTKEY", "listener_opt_in": True,
            "mode": "LIVE", "chord": ["CTRL", "ALT", "SHIFT", "F"],
        }
        self.assertEqual(command_from_app_hotkey(good), FOLLOW_SIM)
        for change in (
            {"listener_opt_in": False}, {"mode": "BUILD"}, {"source": "GLOBAL_KEYHOOK"},
            {"chord": ["SHIFT", "ENTER"]},
        ):
            with self.subTest(change=change):
                with self.assertRaisesRegex(ValueError, "HOTKEY_NOT_ADMITTED"):
                    command_from_app_hotkey({**good, **change})

    def test_invalid_scene_dialog_text_entry_and_camera_owner_hold(self):
        for change in (
            {"mode": "BUY"}, {"scene_id": "main_menu"}, {"capture_ref": "old"},
            {"game_version": "wrong"}, {"capture_quality": "BLACK"},
            {"viewport_state": "UNKNOWN"}, {"save_authorized": False},
            {"player_queue_owned": True}, {"text_entry_active": True},
            {"modal_open": True}, {"player_camera_owned": True},
            {"independent_cues": [{"source": "visual", "token": "hint"}]},
            {"camera_revision": ""},
        ):
            with self.subTest(change=change):
                self.assertEqual(plan(FOLLOW_SIM, observed(**change))["state"], "SIM_CAMERA_NOT_READY")

    def test_missing_or_noninstanced_sim_rejected(self):
        for c in ({"active_sim_id": None}, {"active_sim_id": True},
                  {"active_sim_id": 0}, {"active_sim_instanced": False}):
            self.assertEqual(plan(FOLLOW_SIM, observed(**c))["state"], "SIM_CAMERA_NOT_READY")

    def test_already_following_is_no_op(self):
        p = plan(FOLLOW_SIM, observed(camera_follow_sim_id=492))
        self.assertEqual(p["state"], "ALREADY_FOLLOWING_SIM")
        self.assertIsNone(p["effect"])

    def test_host_stack_keeps_viewport_and_player_priority(self):
        turn = evaluate_turn(
            SIX, capture_ref="capture:focus-1",
            sim_camera_command=FOLLOW_SIM, sim_camera_observation=observed(),
        )
        self.assertEqual(turn["next_gate"], "COOPERATIVE_SCREEN_QUEUE_AND_LIVE_HOST")
        self.assertEqual(turn["fallback"]["mechanism"], "SIM_CAMERA_FOCUS_OR_FOLLOW")
        self.assertFalse(turn["fallback"]["execute_allowed"])
        player = evaluate_turn(
            SIX, capture_ref="capture:focus-1", player_directed=True,
            sim_camera_command=FOLLOW_SIM, sim_camera_observation=observed(),
        )
        self.assertEqual(player["next_gate"], "RESPECT_PLAYER_OR_BUSY_STATE")

    def test_unknown_command_and_observation_do_not_dispatch(self):
        with self.assertRaises(SimCameraError):
            plan("FOLLOW_SIM_VIA_ENTER")
        self.assertEqual(
            plan_sim_camera(FOLLOW_SIM, capture_ref="capture:focus-1", observation=None)["gate"],
            "REOBSERVE_OR_YIELD",
        )

    def test_readonly_cli_never_controls_game(self):
        from io import StringIO
        with patch("sys.stdout", new_callable=StringIO) as output:
            status = camera_cli(["--command", FOLLOW_SIM])
        self.assertEqual(status, 0)
        self.assertFalse(json.loads(output.getvalue())["execute_allowed"])


class SimCameraQueueTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.last_input_ms = 0
        self.current = observed()
        self.effects = []

        async def no_delay(_):
            return None

        self.queue = CooperativeScreenQueue(
            lambda: PresenceProbe(False, False, last_input_age_ms=self.last_input_ms),
            lambda: True, lock_root=Path(temp.name), sleep=no_delay,
        )

    async def inspect(self):
        return self.current

    async def key(self, chord):
        self.effects.append(("key", chord))
        return True

    async def follow(self, sim_id):
        self.effects.append(("game_api", sim_id))
        return True

    def enqueue(self, command):
        return enqueue_sim_camera(
            self.queue, work_id="camera-1", command=command,
            capture_ref="capture:focus-1", observe=self.inspect,
            send_chord=self.key, focus_follow=self.follow,
        )

    async def test_human_activity_waits_then_centers_without_mouse(self):
        item = self.enqueue(CENTER_SIM)
        self.assertEqual((await self.queue.run_once())["state"], "WAITING_FOR_USER")
        self.assertEqual(self.effects, [])
        self.last_input_ms = 16000
        self.assertEqual((await self.queue.run_once())["state"], "COMPLETED")
        self.assertEqual(self.effects, [("key", ["ENTER"])])
        self.assertEqual(item["receipt"]["state"], "EFFECT_DISPATCHED_UNVERIFIED")

    async def test_follow_uses_only_game_port(self):
        self.last_input_ms = 16000
        item = self.enqueue(FOLLOW_SIM)
        self.assertEqual((await self.queue.run_once())["state"], "COMPLETED")
        self.assertEqual(self.effects, [("game_api", 492)])
        self.assertEqual(item["receipt"]["effect_kind"], "GAME_CAMERA_API")

    async def test_changed_target_quarantines_without_effect(self):
        self.last_input_ms = 16000
        self.enqueue(FOLLOW_SIM)
        self.current = observed(active_sim_id=497)
        # First independent observation is new; intent cannot safely
        # proceed if the target identity changes between checks.
        async def changing_inspect():
            self.current = observed(active_sim_id=492)
            return self.current
        # Establish an anchored plan, then mutate the Sim before action.
        self.queue.pending.clear()
        calls = 0
        async def swapped():
            nonlocal calls
            calls += 1
            return observed(active_sim_id=492 if calls == 1 else 497)
        enqueue_sim_camera(
            self.queue, work_id="camera-changed", command=FOLLOW_SIM,
            capture_ref="capture:focus-1", observe=swapped,
            focus_follow=self.follow,
        )
        self.assertEqual((await self.queue.run_once())["state"], "NEEDS_RECONCILIATION")
        self.assertEqual(self.effects, [])

    async def test_modal_blocks_and_missing_game_port_rejected(self):
        self.last_input_ms = 16000
        self.current = observed(modal_open=True)
        self.enqueue(CENTER_SIM)
        self.assertEqual((await self.queue.run_once())["state"], "NEEDS_REVALIDATION")
        self.assertEqual(self.effects, [])
        with self.assertRaises(SimCameraError):
            enqueue_sim_camera(
                self.queue, work_id="missing-port", command=FOLLOW_SIM,
                capture_ref="capture:focus-1", observe=self.inspect,
            )

    async def test_failed_game_port_never_falls_back_to_enter(self):
        self.last_input_ms = 16000
        async def refused(_):
            return False
        enqueue_sim_camera(
            self.queue, work_id="refused", command=FOLLOW_SIM,
            capture_ref="capture:focus-1", observe=self.inspect,
            focus_follow=refused, send_chord=self.key,
        )
        self.assertEqual((await self.queue.run_once())["state"], "NEEDS_RECONCILIATION")
        self.assertEqual(self.effects, [])


class SimCameraHostPortTests(unittest.TestCase):
    def test_admitted_center_uses_shared_key_owner_and_no_mouse(self):
        effects = []
        @contextmanager
        def fake_lease(process_id, session_id):
            self.assertEqual((process_id, session_id), (303, "demo"))
            def checkpoint():
                effects.append("checkpoint")
            yield checkpoint
        with patch("betterinstincts.screen_admit.admitted_screen_lease", fake_lease), \
                patch("scripts.win32_input.send_key_chord", lambda chord: effects.append(tuple(chord))):
            result = center_on_admitted_host(
                CENTER_LOT, process_id=303, session_id="demo",
                observe=lambda: observed(),
            )
        self.assertEqual(effects, ["checkpoint", "checkpoint", ("SHIFT", "ENTER")])
        self.assertFalse(result["game_effect_observed"])
        self.assertFalse(result["cursor_moved"])

    def test_s4cl_absence_never_substitutes_click(self):
        original_import = __import__
        def missing_s4cl(name, *args, **kwargs):
            if name.startswith("sims4communitylib"):
                raise ImportError("simulated missing mod dependency")
            return original_import(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=missing_s4cl):
            with self.assertRaisesRegex(SimCameraError, "COMPATIBLE_S4CL_GAME_RUNTIME_REQUIRED"):
                follow_active_sim_in_game(
                    492, admit=lambda: True, observe=lambda: observed(),
                )

    def test_in_game_explicit_admission_cannot_be_missing(self):
        with self.assertRaisesRegex(SimCameraError, "IN_GAME_FOLLOW_ADMISSION_REQUIRED"):
            follow_active_sim_in_game(
                492, admit=None, observe=lambda: observed(),
            )

    def test_s4cl_follow_port_accepts_exact_active_sim_only(self):
        packages = {
            k: types.ModuleType(k) for k in (
                "sims4communitylib", "sims4communitylib.utils",
                "sims4communitylib.utils.misc", "sims4communitylib.utils.sims",
                "sims4communitylib.utils.misc.common_camera_utils",
                "sims4communitylib.utils.sims.common_sim_utils",
            )
        }
        info = object()
        invoked = []
        class CommonSimUtils:
            @staticmethod
            def get_active_sim_info():
                return info
            @staticmethod
            def get_sim_id(_):
                return 492
            @staticmethod
            def get_sim_instance(_):
                return object()
        class CommonCameraUtils:
            @staticmethod
            def start_focus_on_sim(_, *, follow):
                invoked.append(follow)
        packages["sims4communitylib.utils.misc.common_camera_utils"].CommonCameraUtils = CommonCameraUtils
        packages["sims4communitylib.utils.sims.common_sim_utils"].CommonSimUtils = CommonSimUtils
        with patch.dict(sys.modules, packages):
            result = follow_active_sim_in_game(
                492, admit=lambda: True, observe=lambda: observed(),
            )
            self.assertEqual(invoked, [True])
            self.assertFalse(result["camera_follow_observed"])
            with self.assertRaisesRegex(SimCameraError, "ACTIVE_SIM_FOLLOW_NOT_READY"):
                follow_active_sim_in_game(
                    493, admit=lambda: True, observe=lambda: observed(),
                )


if __name__ == "__main__":
    unittest.main()
