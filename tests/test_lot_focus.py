"""Lot-off-focus recognition (offline policy)."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from betterinstincts.host_stack import evaluate_turn
from betterinstincts.lot_focus import (
    MISS_OFF_LOT,
    OFF_INTENT_VIEW,
    SCENERY_MANAGE_WORLDS,
    SCENERY_ON_LOT,
    SCENERY_STREET_ROOFTOP,
    SCENERY_TRAVELING,
    SCENERY_VIEWPORT,
    assess_lot_focus,
    assess_off_intent_view,
    recovery_for_off_intent_view,
    recovery_for_scenery_focus,
    should_assess_lot_focus,
)
from betterinstincts.scenes import load_catalog, stamp_host_capture_branch, stamp_host_capture_game_version


CAPTURE = "capture:lot-focus-1"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "scenery_focus"
FIXTURE_OBS = FIXTURE_DIR / "observations.v1.json"


def obs(**overrides):
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
        "camera_revision": "camera:lot-1",
        "active_sim_id": 492,
        "active_sim_instanced": True,
        "camera_follow_sim_id": 492,
        "camera_displaced": False,
        "client_width": 1920,
        "client_height": 1080,
        "camera_on_active_household_lot": True,
        "camera_lot_kind": "home",
        "independent_cues": [
            {"source": "visual", "token": "live_hud"},
            {"source": "operator", "token": "live_confirmed"},
        ],
    }
    data.update(overrides)
    return data


SIX = {
    "hunger": 0.8,
    "bladder": 0.8,
    "energy": 0.8,
    "fun": 0.8,
    "hygiene": 0.8,
    "social": 0.8,
}


class LotFocusTests(unittest.TestCase):
    def test_on_lot_when_household_lot_attested(self):
        out = assess_lot_focus(capture_ref=CAPTURE, observation=obs())
        self.assertEqual(out["state"], "ON_LOT")
        self.assertFalse(out["execute_allowed"])
        self.assertIsNone(out.get("restore"))
        self.assertEqual(out["proof_ceiling"], "OFFLINE_LOT_FOCUS_POLICY_NOT_LIVE_CAMERA_CERTIFIED")

    def test_off_lot_street_when_travel_afar_without_goal(self):
        out = assess_lot_focus(
            capture_ref=CAPTURE,
            observation=obs(
                zoom_mode_observed="TRAVEL_AFAR",
                camera_on_active_household_lot=False,
                camera_lot_kind="street",
                live_hud_present=False,
            ),
        )
        self.assertEqual(out["state"], "OFF_LOT_STREET")
        self.assertEqual(out["gate"], "LOT_OFF_FOCUS_RESTORE_REQUIRED")
        self.assertEqual(out["restore_plan"]["command"], "CENTER_ACTIVE_SIM")
        self.assertEqual(out["restore_plan"]["chord"], ["ENTER"])
        self.assertIn("SHIFT_ENTER", out["restore_plan"]["forbid_default"])
        self.assertFalse(out["execute_allowed"])

    def test_unknown_when_cues_insufficient(self):
        out = assess_lot_focus(
            capture_ref=CAPTURE,
            observation={
                "source": "HOST_CAPTURE",
                "capture_ref": CAPTURE,
                "game_version": load_catalog()["game_version"],
            },
        )
        self.assertEqual(out["state"], "UNKNOWN")
        self.assertEqual(out["gate"], "LOT_FOCUS_UNKNOWN")
        self.assertIsNone(out.get("restore"))

    def test_off_lot_from_compound_scenery_tokens_with_live_hud(self):
        """Neighborhood PrintWindow: canal/street labels + low lot fraction.

        Live HUD can still be visible while scenery is clearly off immersion —
        compound tokens like CANAL_LEFT must still force OFF_LOT + Enter restore.
        """
        out = assess_lot_focus(
            capture_ref=CAPTURE,
            observation=obs(
                camera_on_active_household_lot=False,
                camera_lot_kind="neighborhood",
                live_hud_present=True,
                camera_altitude="NEIGHBORHOOD_HIGH",
                lot_fraction_of_frame=0.35,
                scenery_tokens=[
                    "CANAL_LEFT",
                    "STREET_RIGHT",
                    "NEIGHBOR_HOUSES",
                    "STREETLIGHTS",
                    "ACTIVE_LOT_LIT_CENTER",
                ],
            ),
        )
        self.assertEqual(out["state"], "OFF_LOT_STREET")
        self.assertEqual(out["gate"], "LOT_OFF_FOCUS_RESTORE_REQUIRED")
        self.assertEqual(out["restore_plan"]["chord"], ["ENTER"])
        self.assertFalse(out["execute_allowed"])

    # --- ON_LOT vs OFF_LOT vs AMBIGUOUS regression fixtures -----------------

    def assess(self, **overrides):
        return assess_lot_focus(capture_ref=CAPTURE, observation=obs(**overrides))

    def assert_off_lot_enter_only(self, out, state="OFF_LOT_STREET"):
        self.assertEqual(out["classification"], "OFF_LOT")
        self.assertEqual(out["state"], state)
        self.assertEqual(out["gate"], "LOT_OFF_FOCUS_RESTORE_REQUIRED")
        self.assertEqual(out["restore_plan"]["chord"], ["ENTER"])
        self.assertIn("SHIFT_ENTER", out["restore_plan"]["forbid_default"])
        self.assertFalse(out["execute_allowed"])
        effect = out["restore"]["effect"]
        self.assertIsNotNone(effect, out["restore"])
        self.assertEqual(effect["chord"], ["ENTER"])
        self.assertNotIn("SHIFT", effect["chord"])

    def test_on_lot_classification_with_household_interior_cue_only(self):
        out = self.assess(
            live_hud_present=False,
            independent_cues=obs()["independent_cues"],
            scenery_tokens=["KITCHEN_COUNTER", "LIVING_ROOM_SOFA"],
        )
        self.assertEqual(out["classification"], "ON_LOT")
        self.assertTrue(out["household_cues"])

    def test_on_lot_ignores_lone_sidewalk_when_corroborated(self):
        out = self.assess(scenery_tokens=["SIDEWALK_LEFT", "KITCHEN"])
        self.assertEqual(out["state"], "ON_LOT")
        self.assertTrue(out["edge_scenery_ignored"])

    def test_on_lot_household_fixture_water_is_not_canal(self):
        out = self.assess(scenery_tokens=["SINK_WATER", "BATHTUB_WATER", "WATER_COOLER"])
        self.assertEqual(out["state"], "ON_LOT")

    def test_off_lot_neighboring_houses(self):
        out = self.assess(
            camera_on_active_household_lot=False,
            scenery_tokens=["NEIGHBOR_HOUSE_LEFT", "NEIGHBOR_HOUSE_RIGHT"],
        )
        self.assert_off_lot_enter_only(out)

    def test_off_lot_neighboring_house_overrides_on_lot_flag(self):
        out = self.assess(scenery_tokens=["NEIGHBORING_HOUSES"])
        self.assert_off_lot_enter_only(out)
        self.assertEqual(out["conflict"], "ON_LOT_FLAG_CONTRADICTED_BY_SCENERY")

    def test_off_lot_canal_water_only(self):
        out = self.assess(
            camera_on_active_household_lot=False,
            camera_lot_kind="home",
            scenery_tokens=["CANAL_LEFT", "WATER_SURFACE", "DOCK"],
        )
        self.assert_off_lot_enter_only(out, state="OFF_LOT_WATER")

    def test_off_lot_sidewalk_and_streetlamp_dominate(self):
        out = self.assess(scenery_tokens=["SIDEWALK_WIDE", "STREETLAMP_ROW"])
        self.assert_off_lot_enter_only(out)
        self.assertEqual(out["edge_scenery_families"], ["lighting", "sidewalk"])

    def test_off_lot_lone_sidewalk_with_explicit_off_lot_flag(self):
        out = self.assess(camera_on_active_household_lot=False, scenery_tokens=["SIDEWALK"])
        self.assert_off_lot_enter_only(out)

    def test_off_lot_neighborhood_zoom_label_and_altitude(self):
        for kwargs in (
            {"zoom_mode_observed": "NEIGHBORHOOD_ZOOM"},
            {"camera_altitude": "full-zoom-out"},
            {"camera_altitude": "street_topdown"},
            {"lot_fraction_of_frame": 0.2},
        ):
            with self.subTest(kwargs=kwargs):
                self.assert_off_lot_enter_only(self.assess(**kwargs))

    def test_off_lot_travel_afar_with_stale_follow_flag_still_plans_enter(self):
        # camera_follow_sim_id == active_sim_id would make plan_sim_camera say
        # NO_EFFECT; off-lot scenery must outrank the stale follow flag.
        out = self.assess(
            zoom_mode_observed="TRAVEL_AFAR",
            camera_on_active_household_lot=False,
            camera_follow_sim_id=492,
        )
        self.assert_off_lot_enter_only(out)
        self.assertTrue(out["follow_flag_overridden"])

    def test_travel_afar_with_verified_goal_alone_is_not_off_lot(self):
        goal = {
            "goal_id": "travel-1",
            "kind": "LONG_DISTANCE_TRAVEL",
            "source": "HOST_TASK",
            "destination_attested": True,
        }
        out = assess_lot_focus(
            capture_ref=CAPTURE,
            observation=obs(zoom_mode_observed="TRAVEL_AFAR"),
            travel_goal=goal,
        )
        self.assertEqual(out["classification"], "ON_LOT")

    def test_ambiguous_lone_sidewalk_without_corroboration(self):
        out = self.assess(
            live_hud_present=False,
            independent_cues=obs()["independent_cues"],
            scenery_tokens=["SIDEWALK_LEFT"],
        )
        self.assertEqual(out["classification"], "AMBIGUOUS")
        self.assertEqual(out["state"], "UNKNOWN")
        self.assertIsNone(out["restore"])
        self.assertNotIn("restore_plan", out)

    def test_ambiguous_on_lot_flag_without_hud_or_household_cue(self):
        out = self.assess(
            live_hud_present=False,
            independent_cues=obs()["independent_cues"],
        )
        self.assertEqual(out["classification"], "AMBIGUOUS")
        self.assertEqual(out["reason"], "ON_LOT_CLAIM_WITHOUT_LIVE_HUD_OR_HOUSEHOLD_CUE")
        self.assertIsNone(out["restore"])

    def test_ambiguous_unverified_capture_or_build(self):
        out = self.assess(game_version="0.0.0")
        self.assertEqual(out["classification"], "AMBIGUOUS")
        self.assertEqual(out["gate"], "LOT_FOCUS_SCENE_UNVERIFIED")

    def test_off_lot_when_game_version_stamped_from_catalog(self):
        raw = obs(
            camera_on_active_household_lot=False,
            scenery_tokens=["CANAL_LEFT", "NEIGHBOR_HOUSES"],
        )
        del raw["game_version"]
        stamped = stamp_host_capture_game_version(raw)
        self.assertEqual(stamped["game_version"], load_catalog()["game_version"])
        out = assess_lot_focus(capture_ref=CAPTURE, observation=stamped)
        self.assertEqual(out["classification"], "OFF_LOT")
        self.assertEqual(out["state"], "OFF_LOT_STREET")

    def test_host_stack_stamps_missing_game_version_for_lot_focus(self):
        raw = obs(
            zoom_mode_observed="TRAVEL_AFAR",
            camera_on_active_household_lot=False,
            camera_lot_kind="neighborhood",
            live_hud_present=False,
        )
        del raw["game_version"]
        turn = evaluate_turn(
            SIX,
            capture_ref=CAPTURE,
            sim_camera_observation=raw,
        )
        self.assertEqual(turn["lot_focus"]["state"], "OFF_LOT_STREET")
        self.assertEqual(turn["next_gate"], "LOT_OFF_FOCUS_RESTORE_REQUIRED")

    def test_stamp_host_capture_branch_nested_recovery_observation(self):
        inner = {"source": "HOST_CAPTURE", "capture_ref": "capture:recover-1", "camera_lot_kind": "canal"}
        wrapped = stamp_host_capture_branch({"target_kind": "LOT", "observation": inner})
        self.assertEqual(
            wrapped["observation"]["game_version"],
            load_catalog()["game_version"],
        )

    def test_scenery_tokens_are_bounded_and_type_checked(self):
        out = self.assess(scenery_tokens=[None, 5, {"x": 1}] + ["KITCHEN"] * 500)
        self.assertEqual(out["classification"], "ON_LOT")

    def test_host_stack_attaches_lot_focus_from_camera_recovery_observation(self):
        # Only camera_recovery carries the capture (no sim_camera_observation):
        # host_stack must still attach lot_focus and plan Enter.
        version = load_catalog()["game_version"]
        recovery_obs = obs(
            capture_ref="capture:recover-1",
            camera_revision="camera:9",
            camera_displaced=True,
            camera_reanchor_attempts=0,
            cursor_client=[960, 540],
            camera_on_active_household_lot=False,
            scenery_tokens=["CANAL_LEFT", "NEIGHBOR_HOUSES"],
            lot_focus_cues=[{"source": "host", "token": "canal_view"}],
            game_clock={
                "source": "HOST_GAME_CLOCK", "capture_ref": "capture:recover-1",
                "camera_revision": "camera:9", "game_version": version,
                "clock_revision": "clock:12", "speed_state": "PAUSED",
                "pause_indicator_active": True,
                "clock_still_during_sample": True, "pause_origin": "PLAYER",
            },
        )
        turn = evaluate_turn(
            SIX,
            capture_ref="capture:recover-1",
            client_width=1920,
            client_height=1080,
            camera_recovery={"target_kind": "LOT", "observation": recovery_obs},
        )
        lot = turn.get("lot_focus")
        self.assertIsNotNone(lot)
        self.assertEqual(lot["classification"], "OFF_LOT")
        self.assertEqual(lot["restore_plan"]["chord"], ["ENTER"])
        self.assertFalse(lot["execute_allowed"])
    def test_host_stack_ambiguous_does_not_emit_restore_gate(self):
        turn = evaluate_turn(
            SIX,
            capture_ref=CAPTURE,
            sim_camera_observation=obs(
                live_hud_present=False,
                independent_cues=obs()["independent_cues"],
            ),
        )
        self.assertEqual(turn["lot_focus"]["classification"], "AMBIGUOUS")
        self.assertNotEqual(turn["next_gate"], "LOT_OFF_FOCUS_RESTORE_REQUIRED")

    def test_should_assess_on_travel_afar_cue(self):
        self.assertTrue(
            should_assess_lot_focus(observation=obs(zoom_mode_observed="TRAVEL_AFAR"))
        )

    def test_host_stack_emits_lot_focus_off_street(self):
        turn = evaluate_turn(
            SIX,
            capture_ref=CAPTURE,
            sim_camera_observation=obs(
                zoom_mode_observed="TRAVEL_AFAR",
                camera_on_active_household_lot=False,
                camera_lot_kind="neighborhood",
                live_hud_present=False,
            ),
        )
        self.assertIsNotNone(turn.get("lot_focus"))
        self.assertEqual(turn["lot_focus"]["state"], "OFF_LOT_STREET")
        self.assertEqual(turn["lot_focus"]["scenery_focus"], SCENERY_STREET_ROOFTOP)
        self.assertEqual(turn["next_gate"], "LOT_OFF_FOCUS_RESTORE_REQUIRED")
        self.assertEqual(turn["fallback"]["mechanism"], "LOT_OFF_FOCUS_RESTORE")


class SceneryFocusHardeningTests(unittest.TestCase):
    """Operator 2026-11-10: recognize when scenery is no longer in lot focus."""

    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE_OBS.read_text(encoding="utf-8"))
        cls.cases = {row["id"]: row for row in cls.fixture["cases"]}

    def test_fixture_images_present(self):
        for name in (
            "sulani-travel-banner.png",
            "kingdom-x-region.png",
            "travel-dialog-x-crop.png",
            "printwindow-black-synthetic.png",
            "printwindow-white-synthetic.png",
        ):
            self.assertTrue((FIXTURE_DIR / name).is_file(), name)

    def test_fixture_matrix_scenery_focus(self):
        for case_id, expected in (
            ("on_lot_interior_or_yard", SCENERY_ON_LOT),
            ("street_or_rooftop_off_focus", SCENERY_STREET_ROOFTOP),
            ("manage_worlds_map", SCENERY_MANAGE_WORLDS),
            ("traveling_with_banner", SCENERY_TRAVELING),
            ("viewport_black_or_white", SCENERY_VIEWPORT),
        ):
            with self.subTest(case_id=case_id):
                overrides = self.cases[case_id]["observation_overrides"]
                out = assess_lot_focus(capture_ref=CAPTURE, observation=obs(**overrides))
                self.assertEqual(out["scenery_focus"], expected)
                self.assertFalse(out["execute_allowed"])
                self.assertEqual(out["recovery"]["scenery_focus"], expected)

    def test_street_rooftop_recovery_enter_then_shift_enter(self):
        out = assess_lot_focus(
            capture_ref=CAPTURE,
            observation=obs(**self.cases["street_or_rooftop_off_focus"]["observation_overrides"]),
        )
        self.assertEqual(out["state"], "OFF_LOT_STREET")
        self.assertEqual(out["restore_plan"]["chord"], ["ENTER"])
        self.assertEqual(out["restore_plan"]["escalation_chord"], ["SHIFT", "ENTER"])
        self.assertEqual(
            out["recovery"]["escalation"]["chord"],
            ["SHIFT", "ENTER"],
        )
        for banned in ("CROWN", "FOOTPRINT", "SELL", "DELETE_SAVE", "CLICK_VOID"):
            self.assertIn(banned, out["recovery"]["forbidden"])

    def test_traveling_with_banner_cancel_xy_never_crown_footprint(self):
        out = assess_lot_focus(
            capture_ref=CAPTURE,
            observation=obs(**self.cases["traveling_with_banner"]["observation_overrides"]),
        )
        self.assertEqual(out["state"], "TRAVELING_WITH_BANNER")
        self.assertEqual(out["gate"], "TRAVEL_PARTY_CANCEL_REQUIRED")
        primary = out["recovery"]["primary"]
        self.assertEqual(primary["seed"], "host.manage_worlds_travel_party_cancel_x")
        self.assertEqual(primary["client_xy"], [1055, 22])
        self.assertEqual(primary["canvas_1456x840_xy"], [800, 25])
        self.assertEqual(
            primary["secondary_seed"],
            "host.manage_worlds_travel_party_cancel_x_bottom",
        )
        self.assertIsNone(out.get("restore"))
        for banned in (
            "CROWN",
            "FOOTPRINT",
            "SELL",
            "DELETE_SAVE",
            "ESC_AS_TRAVEL_CANCEL",
            "CLICK_WORLD_GLOBE_WHILE_TRAVELING",
            "CLICK_PLAY_OR_LOT_PIN_WHILE_MAPPING",
        ):
            self.assertIn(banned, out["recovery"]["forbidden"])

    def test_manage_worlds_map_not_enter_roam(self):
        out = assess_lot_focus(
            capture_ref=CAPTURE,
            observation=obs(**self.cases["manage_worlds_map"]["observation_overrides"]),
        )
        self.assertEqual(out["state"], "MANAGE_WORLDS_MAP")
        self.assertIsNone(out.get("restore"))
        self.assertIn("ENTER_AS_MAP_ROAM", out["recovery"]["forbidden"])
        self.assertEqual(
            out["recovery"]["if_traveling_with_banner"]["seed"],
            "host.manage_worlds_travel_party_cancel_x",
        )
        self.assertIn("CLICK_WORLD_GLOBE_WHILE_TRAVELING", out["recovery"]["forbidden"])

    def test_viewport_black_or_white_distinct_from_street(self):
        out = assess_lot_focus(
            capture_ref=CAPTURE,
            observation=obs(**self.cases["viewport_black_or_white"]["observation_overrides"]),
        )
        self.assertEqual(out["scenery_focus"], SCENERY_VIEWPORT)
        self.assertEqual(out["state"], "VIEWPORT_BLACK_OR_WHITE")
        self.assertIn("ENTER_AS_SCENERY_RESTORE", out["recovery"]["forbidden"])
        self.assertEqual(out["recovery"]["primary"]["owner"], "betterinstincts/viewport.py")

    def test_viewport_white_flag(self):
        out = assess_lot_focus(
            capture_ref=CAPTURE,
            observation=obs(
                viewport_classification="FULL_CLIENT_WHITE",
                capture_quality="FULL_CLIENT_WHITE",
            ),
        )
        self.assertEqual(out["scenery_focus"], SCENERY_VIEWPORT)

    def test_host_stack_traveling_banner_gate(self):
        turn = evaluate_turn(
            SIX,
            capture_ref=CAPTURE,
            sim_camera_observation=obs(
                **self.cases["traveling_with_banner"]["observation_overrides"]
            ),
        )
        self.assertEqual(turn["lot_focus"]["scenery_focus"], SCENERY_TRAVELING)
        self.assertEqual(turn["next_gate"], "TRAVEL_PARTY_CANCEL_REQUIRED")
        self.assertEqual(turn["fallback"]["mechanism"], "TRAVEL_PARTY_CANCEL")
        self.assertIn("CROWN", turn["fallback"]["forbidden"])

    def test_host_stack_manage_worlds_gate(self):
        turn = evaluate_turn(
            SIX,
            capture_ref=CAPTURE,
            sim_camera_observation=obs(
                **self.cases["manage_worlds_map"]["observation_overrides"]
            ),
        )
        self.assertEqual(turn["lot_focus"]["scenery_focus"], SCENERY_MANAGE_WORLDS)
        self.assertEqual(turn["fallback"]["mechanism"], "MANAGE_WORLDS_FOCUS_RESTORE")

    def test_recovery_helper_covers_all_classes(self):
        for focus in (
            SCENERY_ON_LOT,
            SCENERY_STREET_ROOFTOP,
            SCENERY_MANAGE_WORLDS,
            SCENERY_TRAVELING,
            SCENERY_VIEWPORT,
        ):
            with self.subTest(focus=focus):
                payload = recovery_for_scenery_focus(focus)
                self.assertEqual(payload["scenery_focus"], focus)
                self.assertIn("forbidden", payload)


class OffIntentViewTests(unittest.TestCase):
    def test_buy_after_world_object_click_triggers_miss(self):
        out = assess_off_intent_view(
            intent="WORLD_OBJECT",
            observation={"buy_catalog_open": True, "ui_mode": "buy"},
        )
        self.assertTrue(out["triggered"])
        self.assertEqual(out["flag"], OFF_INTENT_VIEW)
        self.assertEqual(out["classification"], MISS_OFF_LOT)
        self.assertEqual(out["reason"], "BUY_BUILD_AFTER_WORLD_OBJECT_CLICK")
        chords = [step.get("chord") for step in out["recovery"]["order"]]
        self.assertIn(["ESCAPE"], chords)
        self.assertIn(["F1"], chords)
        self.assertIn(["SHIFT", "ENTER"], chords)
        self.assertIn("EXPLORE_BUY_CATALOG", out["forbidden"])
        self.assertIn("HARDCODED_FIELD_XY_AFTER_MISS", out["forbidden"])

    def test_street_asphalt_after_object_click_triggers_miss(self):
        out = assess_off_intent_view(
            observation={
                "intended_world_object_click": True,
                "street_empty_asphalt": True,
                "post_click_view": "empty_asphalt",
            }
        )
        self.assertTrue(out["triggered"])
        self.assertEqual(out["classification"], MISS_OFF_LOT)
        self.assertEqual(out["reason"], "STREET_OR_EMPTY_ASPHALT_AFTER_WORLD_OBJECT_CLICK")
        self.assertEqual(
            out["recovery"]["blocked_if_target_absent"], "BLOCKED_NEED_OPERATOR_FRAME"
        )

    def test_no_intent_does_not_trigger(self):
        out = assess_off_intent_view(observation={"buy_catalog_open": True})
        self.assertFalse(out["triggered"])
        self.assertEqual(out["reason"], "NO_WORLD_OBJECT_CLICK_INTENT")

    def test_on_target_post_click_does_not_trigger(self):
        out = assess_off_intent_view(
            intent="ROBOTICS_WORKSTATION",
            observation={"buy_mode": False, "post_click_view": "object_pie"},
        )
        self.assertFalse(out["triggered"])

    def test_recovery_helper_includes_shift_enter_arm(self):
        rec = recovery_for_off_intent_view(buy_or_build_opened=True)
        self.assertEqual(rec["flag"], OFF_INTENT_VIEW)
        self.assertEqual(rec["classification"], MISS_OFF_LOT)
        self.assertEqual(rec["order"][-2]["chord"], ["SHIFT", "ENTER"])


if __name__ == "__main__":
    unittest.main()
