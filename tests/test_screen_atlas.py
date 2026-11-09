"""Offline proof: live-calibrated action atlas yields and parks safely."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from betterinstincts.player_presence import PresenceProbe
from betterinstincts.screen_atlas import (
    ScreenAtlasError, enqueue_game_click, enqueue_native_game_click, inventory, load_atlas,
    resolved_calibration,
)
from betterinstincts.workflow_interop import CooperativeScreenQueue
from scripts.screen_atlas import main as atlas_cli

PATCH = "1.121.361.1020"


def calibration(**changes):
    data = {
        "target_id": "catalog.search_field", "mode": "BUILD",
        "profile": "1920x1080", "game_version": PATCH,
        "client_width": 1920, "client_height": 1080,
        "x": 125, "y": 866, "status": "OPERATOR_VERIFIED_EXACT_BUILD",
        "evidence_ref": "p08-observed-build-search",
    }
    data.update(changes)
    return data


def observation(**changes):
    data = {
        "target_id": "catalog.search_field", "mode": "BUILD",
        "scene_id": "build_mode", "profile": "1920x1080",
        "game_version": PATCH, "client_width": 1920, "client_height": 1080,
        "capture_quality": "CONTENT_PRESENT", "viewport_state": "NORMAL",
        "target_visible": True, "save_authorized": True, "player_queue_owned": False,
        "independent_cues": [
            {"source": "visual", "token": "observed_build_chrome"},
            {"source": "operator", "token": "confirmed_build_mode"},
        ],
    }
    data.update(changes)
    return data


class AtlasInventoryTests(unittest.TestCase):
    def test_uses_authoritative_hotkeys_targets_and_console(self):
        out = inventory()
        self.assertEqual(out["exact_game_version"], PATCH)
        self.assertEqual(set(out["modes"]), {"LIVE", "BUY", "BUILD"})
        hotkeys = {r["id"] for r in out["modes"]["BUILD"]["hotkeys"]}
        self.assertIn("MODE_BUILD", hotkeys)
        self.assertIn("BACKSPACE_TO_HOUSEHOLD_INVENTORY", hotkeys)
        self.assertIn("catalog.search_field", out["modes"]["BUILD"]["targets"])
        self.assertIn("bb.showhiddenobjects", [r["line"] for r in out["console"]["ordered_commands"]])
        self.assertTrue(all(r["execute_allowed"] is False for r in out["console"]["ordered_commands"]))
        self.assertFalse(out["execute_allowed"])
        screens = {x["scene_id"]: x for x in out["screen_maps"]}
        self.assertEqual(set(screens), set(out["scenes"]))
        self.assertIn("open_load_game", [x["id"] for x in screens["main_menu"]["menu_clicks"]])
        self.assertIn("catalog.search_field", screens["build_mode"]["target_ids"])
        self.assertTrue(screens["unknown"]["unmapped"])
        self.assertTrue(all(not x["execute_allowed"] for screen in screens.values()
                            for x in screen["menu_clicks"]))

    def test_requires_exact_version_and_explicit_attestation(self):
        for changes, reason in [
            ({"status": "CANDIDATE_UNVERIFIED"}, "VERIFIED_CALIBRATION_REQUIRED"),
            ({"game_version": "1.0.0.0"}, "UNKNOWN_GAME_PATCH"),
            ({"client_width": 1600}, "PROFILE_GEOMETRY_MISMATCH"),
            ({"mode": "LIVE"}, "TARGET_NOT_IN_MODE"),
            ({"x": 1920}, "TARGET_PIXEL_OUT_OF_BOUNDS"),
            ({"evidence_ref": "bad/path"}, "VERIFIED_CALIBRATION_REQUIRED"),
            ({"profile": "4k"}, "UNKNOWN_PROFILE"),
        ]:
            with self.subTest(changes=changes):
                with self.assertRaisesRegex((ScreenAtlasError, ValueError), reason):
                    resolved_calibration(calibration(**changes))

    def test_rest_inside_interior_and_atlas_has_gate(self):
        out = resolved_calibration(calibration())
        self.assertEqual(out["click"], [125, 866])
        self.assertEqual(out["safe_rest"], [960, 540])
        self.assertFalse(out["execute_allowed"])
        self.assertTrue(load_atlas()["mouse"]["rest_requires_fresh_presence_checkpoint"])

    def test_cli_is_inspection_only(self):
        self.assertEqual(atlas_cli(["target", "--mode", "BUILD", "--id", "catalog.search_field"]), 0)
        self.assertEqual(atlas_cli(["target", "--mode", "LIVE", "--id", "catalog.search_field"]), 1)


class FakeMouse:
    def __init__(self):
        self.effects = []
        self.after_click = None

    async def click(self, x, y):
        self.effects.append(("click", x, y))
        if self.after_click:
            self.after_click()

    async def move(self, x, y):
        self.effects.append(("rest", x, y))


class FakePage:
    def __init__(self):
        self.mouse = FakeMouse()
        self.closed = False

    def is_closed(self):
        return self.closed


class CooperativeAtlasTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.age = 0
        self.page = FakePage()
        self.current = observation()

        async def no_delay(seconds):
            pass

        self.queue = CooperativeScreenQueue(
            lambda: PresenceProbe(False, False, last_input_age_ms=self.age),
            lambda: True,
            lock_root=Path(self.tmp.name),
            sleep=no_delay,
        )

    async def observed(self):
        return self.current

    def enqueue(self, work_id="click"):
        return enqueue_game_click(
            self.queue, work_id=work_id, page=self.page,
            calibration=calibration(), observe=self.observed,
        )

    async def test_no_click_or_park_while_player_active_then_safe_rest(self):
        plan = self.enqueue()
        self.assertFalse(plan["execute_allowed"])
        self.assertEqual((await self.queue.run_once())["state"], "WAITING_FOR_USER")
        self.assertEqual(self.page.mouse.effects, [])
        self.age = 16000
        self.assertEqual((await self.queue.run_once())["state"], "COMPLETED")
        self.assertEqual(self.page.mouse.effects, [("click", 125, 866), ("rest", 960, 540)])

    async def test_scene_ambiguity_and_wrong_geometry_are_quarantined(self):
        for bad in [{"scene_id": "buy_mode"}, {"client_width": 1600},
                    {"target_visible": False}, {"player_queue_owned": True},
                    {"independent_cues": [{"source": "visual", "token": "looks_build"}]},
                    {"capture_quality": "BLACK"}]:
            with self.subTest(bad=bad):
                self.current = observation(**bad)
                self.age = 16000
                self.page.mouse.effects.clear()
                self.queue.pending.clear()
                self.queue.needs_review.clear()
                self.enqueue(work_id="attempt")
                self.assertEqual((await self.queue.run_once())["state"], "NEEDS_REVALIDATION")
                self.assertEqual(self.page.mouse.effects, [])

    async def test_human_interrupts_after_click_and_park_yields(self):
        self.age = 16000
        self.page.mouse.after_click = lambda: setattr(self, "age", 0)
        self.enqueue()
        out = await self.queue.run_once()
        self.assertEqual(out["state"], "NEEDS_RECONCILIATION")
        self.assertEqual(self.page.mouse.effects, [("click", 125, 866)])
        self.assertIn("click", self.queue.needs_review)

    async def test_unrelated_browser_page_fails_closed(self):
        self.page.closed = True
        self.age = 16000
        self.enqueue()
        self.assertEqual((await self.queue.run_once())["state"], "NEEDS_REVALIDATION")
        self.assertEqual(self.page.mouse.effects, [])



class NativeGameScreenAtlasTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.age = 16000
        self.effects = []
        self.current = observation(
            process_id=4521, focused_process_id=4521, session_id="lab-session",
            host_admitted=True, client_origin_x=100, client_origin_y=50,
        )

        async def no_delay(seconds):
            pass

        self.queue = CooperativeScreenQueue(
            lambda: PresenceProbe(False, False, last_input_age_ms=self.age),
            lambda: True,
            lock_root=Path(self.tmp.name),
            sleep=no_delay,
        )

    async def observed(self):
        return self.current

    async def click(self, x, y):
        self.effects.append(("click", x, y))

    async def move(self, x, y):
        self.effects.append(("rest", x, y))

    def enqueue(self):
        return enqueue_native_game_click(
            self.queue, work_id="native-click", calibration=calibration(),
            observe=self.observed, process_id=4521, session_id="lab-session",
            click_screen=self.click, move_screen=self.move,
        )

    async def test_native_client_to_screen_conversion_and_safe_rest(self):
        self.enqueue()
        self.assertEqual((await self.queue.run_once())["state"], "COMPLETED")
        self.assertEqual(self.effects, [("click", 225, 916), ("rest", 1060, 590)])

    async def test_wrong_pid_or_stale_scene_never_click(self):
        for bad in [{"focused_process_id": 999}, {"host_admitted": False},
                    {"client_origin_x": None}, {"scene_id": "buy_mode"},
                    {"session_id": "other-session"}]:
            with self.subTest(bad=bad):
                self.current = observation(
                    process_id=4521, focused_process_id=4521,
                    session_id="lab-session", host_admitted=True,
                    client_origin_x=100, client_origin_y=50, **{},
                )
                self.current.update(bad)
                self.queue.pending.clear()
                self.queue.needs_review.clear()
                self.enqueue()
                self.assertEqual((await self.queue.run_once())["state"], "NEEDS_REVALIDATION")
                self.assertEqual(self.effects, [])

    async def test_native_after_click_human_takeover_yields_without_rest(self):
        async def interrupted_click(x, y):
            self.effects.append(("click", x, y))
            self.age = 0

        enqueue_native_game_click(
            self.queue, work_id="native-interrupted",
            calibration=calibration(), observe=self.observed,
            process_id=4521, session_id="lab-session",
            click_screen=interrupted_click, move_screen=self.move,
        )
        self.assertEqual((await self.queue.run_once())["state"], "NEEDS_RECONCILIATION")
        self.assertEqual(self.effects, [("click", 225, 916)])

    async def test_native_window_move_after_click_quarantines(self):
        async def moved_click(x, y):
            self.effects.append(("click", x, y))
            self.current = dict(self.current, client_origin_x=120)

        enqueue_native_game_click(
            self.queue, work_id="window-moved",
            calibration=calibration(), observe=self.observed,
            process_id=4521, session_id="lab-session",
            click_screen=moved_click, move_screen=self.move,
        )
        self.assertEqual((await self.queue.run_once())["state"], "NEEDS_RECONCILIATION")
        self.assertEqual(self.effects, [("click", 225, 916)])


if __name__ == "__main__":
    unittest.main()
