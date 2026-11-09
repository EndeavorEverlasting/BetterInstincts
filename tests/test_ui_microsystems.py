"""P82/P95: semantic Sims panels share one independently admitted native clicker."""
import tempfile
import unittest
from pathlib import Path

from betterinstincts.player_presence import PresenceProbe
from betterinstincts.screen_atlas import (
    ScreenAtlasError, enqueue_native_game_click, inventory as atlas_inventory,
    resolved_calibration,
)
from betterinstincts.ui_microsystems import (
    UIMicrosystemError, inventory, load_contract, resolve_action,
)
from betterinstincts.workflow_interop import CooperativeScreenQueue

PATCH = "1.121.361.1020"


def panel_calibration(**updates):
    data = {
        "panel_id": "career",
        "target_id": "career.inspect_schedule",
        "mode": "LIVE",
        "profile": "1920x1080",
        "game_version": PATCH,
        "client_width": 1920,
        "client_height": 1080,
        "hitbox": [100, 200, 160, 240],
        "x": 130,
        "y": 220,
        "ui_layout_revision": "layout-42",
        "selected_sim_revision": "sim-rev-7",
        "evidence_ref": "attested-career-screen-001",
        "status": "OPERATOR_VERIFIED_EXACT_BUILD",
    }
    data.update(updates)
    return data


def panel_observation(**updates):
    data = {
        "process_id": 4321,
        "focused_process_id": 4321,
        "session_id": "game-session-1",
        "host_admitted": True,
        "client_origin_x": 30,
        "client_origin_y": 40,
        "target_id": "career.inspect_schedule",
        "mode": "LIVE",
        "scene_id": "live_mode",
        "profile": "1920x1080",
        "game_version": PATCH,
        "client_width": 1920,
        "client_height": 1080,
        "capture_quality": "CONTENT_PRESENT",
        "viewport_state": "NORMAL",
        "target_visible": True,
        "save_authorized": True,
        "player_queue_owned": False,
        "independent_cues": [
            {"source": "visual", "token": "live_scene_observed"},
            {"source": "operator", "token": "live_scene_confirmed"},
        ],
        "panel_id": "career",
        "panel_visible": True,
        "panel_hitbox": [100, 200, 160, 240],
        "ui_layout_revision": "layout-42",
        "selected_sim_revision": "sim-rev-7",
        "panel_obscured": False,
        "panel_animation_stable": True,
        "target_enabled": True,
        "panel_cues": [
            {"source": "visual", "token": "panel:live_career"},
            {"source": "operator", "token": "career_visible"},
        ],
    }
    data.update(updates)
    return data


class MicrosystemContractTests(unittest.TestCase):
    def test_inventory_has_distinct_menus_without_unsafe_pixel_defaults(self):
        cfg = load_contract()
        rows = inventory(cfg=cfg)["panels"]
        for panel in ("aspirations", "career", "skills", "simology",
                      "personal_inventory", "needs", "household_inventory",
                      "small_business", "skit", "skills_and_needs"):
            self.assertIn(panel, rows)
            self.assertFalse(rows[panel]["execute_allowed"])
        self.assertEqual(rows["skit"]["actions"], [])
        self.assertEqual(rows["skills_and_needs"]["actions"], [])
        self.assertIn("career.inspect_schedule",
                      [f"career.{x}" for x in rows["career"]["actions"]])
        atlas = atlas_inventory()
        self.assertIn("career", atlas["screen_maps"][
            next(i for i, row in enumerate(atlas["screen_maps"])
                 if row["scene_id"] == "live_mode")]["microsystem_ids"])

    def test_targets_are_never_interchangeable_across_panels(self):
        for panel, target, mode, reason in [
            ("unknown", "unknown.inspect", "LIVE", "UNKNOWN_PANEL"),
            ("skit", "skit.inspect", "LIVE", "PANEL_NOT_A_CLICK_SURFACE"),
            ("skills_and_needs", "skills_and_needs.inspect", "LIVE", "PANEL_NOT_A_CLICK_SURFACE"),
            ("career", "career.inspect_schedule", "BUY", "PANEL_WRONG_MODE"),
            ("career", "skills.inspect_skill", "LIVE", "TARGET_NOT_IN_PANEL"),
            ("small_business", "small_business.inspect_staff", "BUY", "PANEL_WRONG_MODE"),
        ]:
            with self.subTest(panel=panel, target=target):
                with self.assertRaisesRegex(UIMicrosystemError, reason):
                    resolve_action(panel, target, mode=mode)

    def test_centered_attested_rectangle_required(self):
        out = resolved_calibration(panel_calibration())
        self.assertEqual(out["click"], [130, 220])
        self.assertEqual(out["panel_id"], "career")
        self.assertEqual(out["panel_cues"]["visual"], "panel:live_career")
        self.assertFalse(out["execute_allowed"])
        for update, reason in [
            ({"status": "CANDIDATE_UNVERIFIED"}, "VERIFIED_CALIBRATION_REQUIRED"),
            ({"game_version": "1.0.0.0"}, "UNKNOWN_GAME_PATCH"),
            ({"x": 150}, "PANEL_CLICK_MUST_BE_HITBOX_CENTER"),
            ({"hitbox": [100, 200, 104, 205], "x": 102, "y": 202}, "PANEL_HITBOX_OUT_OF_BOUNDS"),
            ({"hitbox": [100, 200, 1920, 240], "x": 1010}, "PANEL_HITBOX_OUT_OF_BOUNDS"),
            ({"panel_id": "skills"}, "TARGET_NOT_IN_PANEL"),
            ({"ui_layout_revision": ""}, "PANEL_REVISION_REQUIRED"),
            ({"selected_sim_revision": None}, "PANEL_REVISION_REQUIRED"),
        ]:
            with self.subTest(update=update):
                with self.assertRaisesRegex((ScreenAtlasError, UIMicrosystemError), reason):
                    resolved_calibration(panel_calibration(**update))

    def test_business_panel_requires_pack_attestation(self):
        business = panel_calibration(
            panel_id="small_business",
            target_id="small_business.inspect_staff",
        )
        with self.assertRaisesRegex(UIMicrosystemError, "PANEL_ENTITLEMENT_UNVERIFIED"):
            resolved_calibration(business)
        self.assertEqual(resolved_calibration({
            **business, "entitlement_attested": True,
        })["panel_id"], "small_business")

    def test_legacy_build_catalog_resolves_unchanged(self):
        data = panel_calibration(
            panel_id="career",
            target_id="catalog.search_field",
            mode="BUILD",
        )
        del data["panel_id"]
        self.assertEqual(resolved_calibration(data)["target_id"], "catalog.search_field")


class NativeMicrosystemClickTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.age = 0
        self.current = panel_observation()
        self.effects = []
        self.job_number = 0

        async def no_delay(seconds):
            pass

        self.queue = CooperativeScreenQueue(
            lambda: PresenceProbe(False, False, last_input_age_ms=self.age),
            lambda: True,
            lock_root=Path(self.tmp.name),
            sleep=no_delay,
        )

    async def observe(self):
        return self.current

    async def click(self, x, y):
        self.effects.append(("click", x, y))

    async def move(self, x, y):
        self.effects.append(("rest", x, y))

    def enqueue(self):
        self.job_number += 1
        return enqueue_native_game_click(
            self.queue,
            work_id=f"career-intent-{self.job_number}",
            calibration=panel_calibration(),
            observe=self.observe,
            process_id=4321,
            session_id="game-session-1",
            click_screen=self.click,
            move_screen=self.move,
        )

    async def test_player_idle_queue_and_single_centered_click(self):
        self.enqueue()
        self.assertEqual((await self.queue.run_once())["state"], "WAITING_FOR_USER")
        self.assertEqual(self.effects, [])
        self.age = 16000
        self.assertEqual((await self.queue.run_once())["state"], "COMPLETED")
        self.assertEqual(self.effects, [("click", 160, 260), ("rest", 990, 580)])

    async def test_revalidation_denies_wrong_panel_or_stale_geometry(self):
        for changed in [
            {"panel_id": "skills"},
            {"panel_hitbox": [110, 200, 170, 240]},
            {"ui_layout_revision": "layout-43"},
            {"selected_sim_revision": "sim-rev-8"},
            {"panel_animation_stable": False},
            {"panel_obscured": True},
            {"panel_visible": False},
            {"target_enabled": False},
            {"panel_cues": [{"source": "visual", "token": "panel:live_skills"},
                            {"source": "operator", "token": "career_visible"}]},
            {"focused_process_id": 9999},
        ]:
            with self.subTest(changed=changed):
                self.current = panel_observation(**changed)
                self.age = 16000
                self.enqueue()
                self.assertEqual((await self.queue.run_once())["state"], "NEEDS_REVALIDATION")
                self.assertEqual(self.effects, [])


if __name__ == "__main__":
    unittest.main()
