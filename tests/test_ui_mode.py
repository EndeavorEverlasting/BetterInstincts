"""P82 mode-context falsifiers and P07 listener / asynchronous dispatch integration."""
from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from betterinstincts.host_listener import activate, tick
from betterinstincts.host_tandem import run_tandem_session
from betterinstincts.player_presence import PresenceProbe
from betterinstincts.ui_mode import UIModeError, evaluate_mode

VERSION = "1.121.361.1020"
CUES = {
    "LIVE": [
        {"source": "visual", "token": "live:sim_portraits_and_needs"},
        {"source": "operator", "token": "live_controls_visible"},
    ],
    "BUY": [
        {"source": "visual", "token": "mode:buy_catalog_active"},
        {"source": "operator", "token": "buy_tools_visible"},
    ],
    "BUILD": [
        {"source": "visual", "token": "mode:build_structural_tools"},
        {"source": "operator", "token": "build_tools_visible"},
    ],
}
NEEDS = {x: .8 for x in ("hunger", "bladder", "energy", "hygiene", "fun", "social")}


def observation(mode: str) -> dict:
    return {
        "schema": "betterinstincts.host-listener.observation/v1",
        "actor_ref": "sim:test",
        "game_version": VERSION,
        "mode_observations": CUES[mode],
        "needs": dict(NEEDS), "queue": [],
        "available_objects": ["bed"], "location_kind": "home",
        "capture_ref": "capture:ui-mode-context",
        "viewport": {"state": "VIEWPORT_OK"},
        "active_story": "FLOOR_1",
    }


def idle(_raw=None):
    return PresenceProbe(
        foreground_is_sims=True, cursor_in_client=False,
        last_input_age_ms=60_000, probe_ok=True,
    )


class ModeClassificationTests(unittest.TestCase):
    def test_three_modes_and_shortcuts_are_not_evidence(self):
        for mode in ("LIVE", "BUY", "BUILD"):
            with self.subTest(mode=mode):
                actual = evaluate_mode(
                    game_version=VERSION, mode_observations=CUES[mode],
                    shortcut_hint={"LIVE": "F1", "BUY": "F2", "BUILD": "F3"}[mode],
                )
                self.assertEqual(actual["mode"], mode)
                self.assertEqual(actual["state"], "MODE_CANDIDATE")
                self.assertFalse(actual["shortcut_is_evidence"])
                self.assertFalse(actual["execute_allowed"])

    def test_hotkey_alone_or_conflicting_cues_cannot_confirm(self):
        hotkey = evaluate_mode(game_version=VERSION, mode_observations=[], shortcut_hint="F3")
        self.assertEqual(hotkey["mode"], "UNKNOWN")
        conflict = evaluate_mode(
            game_version=VERSION, mode_observations=CUES["BUY"] + CUES["BUILD"]
        )
        self.assertEqual(conflict["mode"], "UNKNOWN")
        self.assertEqual(conflict["state"], "MODE_UNVERIFIED")

    def test_unknown_patch_and_old_ambiguous_build_buy_fail_closed(self):
        stale = evaluate_mode(game_version="1.0.0.0", mode_observations=CUES["BUY"])
        self.assertEqual(stale["state"], "UNKNOWN_PATCH")
        legacy = evaluate_mode(game_version=VERSION, mode_observations=[
            {"source": "visual", "token": "build:catalog_and_grid"},
            {"source": "operator", "token": "build_controls_visible"},
        ])
        self.assertEqual(legacy["mode"], "UNKNOWN")

    def test_panel_context_requires_both_independent_cues(self):
        panel = [
            {"source": "visual", "token": "panel:build_walls"},
            {"source": "operator", "token": "wall_tools_visible"},
        ]
        result = evaluate_mode(
            game_version=VERSION, mode_observations=CUES["BUILD"],
            panel_observations=panel,
        )
        self.assertEqual(result["active_panel"], "wall_tools")
        self.assertIn("floor_controls", result["available_panels"])
        partial = evaluate_mode(
            game_version=VERSION, mode_observations=CUES["BUILD"],
            panel_observations=panel[:1],
        )
        self.assertEqual(partial["active_panel"], "unknown")

    def test_bad_panel_and_shortcut_inputs_rejected(self):
        with self.assertRaises(UIModeError):
            evaluate_mode(
                game_version=VERSION, mode_observations=CUES["BUILD"],
                panel_observations=[{"source": "model", "token": "invented"}],
            )
        with self.assertRaises(UIModeError):
            evaluate_mode(game_version=VERSION, mode_observations=[], shortcut_hint="F8")


class ListenerModeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name).resolve()
        self.p1 = patch("betterinstincts.host_listener.ROOT", root)
        self.p2 = patch("betterinstincts.host_listener.OUTPUT", root / "dist/host-listener")
        self.p1.start()
        self.p2.start()
        self.sid = "mode-context"
        activate(self.sid)

    def tearDown(self):
        self.p2.stop()
        self.p1.stop()
        self.temporary.cleanup()

    def test_buy_build_context_only_and_floor_census(self):
        for mode in ("BUY", "BUILD"):
            with self.subTest(mode=mode):
                receipt = tick(self.sid, observation(mode), presence_probe=idle())
                self.assertEqual(receipt["ui_mode"]["mode"], mode)
                self.assertEqual(receipt["listener_action"], "MODE_CONTEXT_ONLY")
                self.assertNotIn("host_stack", receipt)
                self.assertEqual(receipt["build_floor_activity"]["state"], "BUILD_FLOOR_ACTIVITY_EVALUATED")
                self.assertFalse(receipt["execute_clicks"])

    def test_live_mode_retains_existing_live_stack(self):
        receipt = tick(self.sid, observation("LIVE"), presence_probe=idle())
        self.assertEqual(receipt["ui_mode"]["mode"], "LIVE")
        self.assertIn("host_stack", receipt)
        self.assertFalse(receipt["execute_clicks"])

    def test_unknown_mode_shortcut_and_conflicting_legacy_flag_hold(self):
        raw = observation("BUILD")
        raw["mode_observations"] = []
        raw["shortcut_hint"] = "F3"
        receipt = tick(self.sid, raw, presence_probe=idle())
        self.assertEqual(receipt["listener_action"], "MODE_UNVERIFIED")
        conflict = {**observation("BUILD"), "build_or_buy_mode": False}
        receipt = tick(self.sid, conflict, presence_probe=idle())
        self.assertEqual(receipt["ui_mode"]["reason"], "LEGACY_MODE_CONFLICT")
        self.assertNotIn("host_stack", receipt)

    def test_player_first_even_during_build(self):
        player = PresenceProbe(
            foreground_is_sims=True, cursor_in_client=True,
            last_input_age_ms=0, probe_ok=True,
        )
        receipt = tick(self.sid, observation("BUILD"), presence_probe=player)
        self.assertEqual(receipt["listener_action"], "YIELD_TO_PLAYER")
        self.assertFalse(receipt["execute_clicks"])


class AsyncModeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name).resolve()
        self.p1 = patch("betterinstincts.host_listener.ROOT", root)
        self.p2 = patch("betterinstincts.host_listener.OUTPUT", root / "dist/host-listener")
        self.p1.start()
        self.p2.start()
        activate("mode-async")

    def tearDown(self):
        self.p2.stop()
        self.p1.stop()
        self.temporary.cleanup()

    async def test_buy_mode_stops_async_dispatch_without_player_queue_cancel(self):
        dispatches, interruptions = [], []

        async def observe():
            await asyncio.sleep(0)
            return observation("BUY")

        async def execute(*args):
            dispatches.append(args)
            return {"state": "OUTCOME_OBSERVED"}

        async def interrupt(*args):
            interruptions.append(args)
            return {"state": "HOST_ACTION_INTERRUPTED"}

        result = await run_tandem_session(
            "mode-async", "sim:test", observe=observe, execute=execute,
            interrupt_owned=interrupt, probe=idle, max_turns=1,
        )
        self.assertEqual(result["state"], "GAME_MODE_NOT_LIVE_REOBSERVE")
        self.assertEqual(dispatches, [])
        self.assertEqual(interruptions, [])
        self.assertIn(
            "UI_MODE_REOBSERVATION_REQUIRED_NO_NEW_DISPATCH",
            [event["event"] for event in result["events"]],
        )


if __name__ == "__main__":
    unittest.main()
