"""Offline falsifiers for fixed-UI click ledger + arm→console handoff."""
from __future__ import annotations

import unittest

from betterinstincts.fixed_ui_click_map import (
    FixedUiClickMapError,
    classify_click,
    empty_ledger,
    ensure_seeded_ledger,
    load_contract,
    load_camera_dependent_fridge_seeds,
    load_escape_menu_coords,
    plan_arm_to_console_handoff,
    plan_escape_menu_save,
    plan_skills_burger_expand,
    record_click_attempt,
    resolve_target_xy,
)


class FixedUiClickMapTests(unittest.TestCase):
    def test_contract_pins_fixed_scope_and_handoff(self):
        cfg = load_contract()
        self.assertEqual(cfg["schema"], "betterinstincts.fixed-ui-click-map/v1")
        self.assertFalse(cfg["execute_allowed_default"])
        self.assertIn("MOVING_WORLD_OBJECTS", cfg["scope"]["out"])
        hand = cfg["handoff"]
        self.assertEqual(hand["console_hotkey_id"], "CHEAT_CONSOLE")
        self.assertEqual(hand["console_chord"], ["CTRL", "SHIFT", "C"])
        self.assertIn("live.calendar_icon", cfg["seed_targets_1920x1080"])

    def test_wrong_control_does_not_rewrite_portrait_coords(self):
        ledger = ensure_seeded_ledger(empty_ledger())
        before = list(ledger["targets"]["live.household_portrait_2"]["client_xy"])
        record_click_attempt(
            ledger,
            target_id="live.household_portrait_2",
            client_xy=[300, 1045],
            classification="WRONG_CONTROL",
            observed_control_id="live.calendar_icon",
            note="Intended Olga portrait; opened calendar",
        )
        after = ledger["targets"]["live.household_portrait_2"]["client_xy"]
        self.assertEqual(after, before)
        self.assertEqual(ledger["targets"]["live.household_portrait_2"]["wrong_control_count"], 1)
        self.assertEqual(ledger["attempts"][-1]["classification"], "WRONG_CONTROL")

    def test_hit_attests_coords(self):
        ledger = ensure_seeded_ledger(empty_ledger())
        record_click_attempt(
            ledger,
            target_id="live.household_portrait_2",
            client_xy=[520, 1045],
            classification="HIT",
        )
        row = ledger["targets"]["live.household_portrait_2"]
        self.assertTrue(row["attested"])
        self.assertEqual(row["client_xy"], [520, 1045])
        self.assertEqual(resolve_target_xy(ledger, "live.household_portrait_2")["client_xy"], [520, 1045])

    def test_moving_target_out_of_scope(self):
        ledger = empty_ledger()
        attempt = record_click_attempt(
            ledger,
            target_id="world.servo_body",
            client_xy=[900, 500],
            classification="OUT_OF_SCOPE_MOVING_TARGET",
            moving_target=True,
        )
        self.assertEqual(attempt["classification"], "OUT_OF_SCOPE_MOVING_TARGET")

    def test_classify_wrong_control_by_id(self):
        scored = classify_click(
            intended_xy=[520, 1045],
            observed_xy=[300, 1045],
            intended_target_id="live.household_portrait_2",
            observed_control_id="live.calendar_icon",
        )
        self.assertEqual(scored["classification"], "WRONG_CONTROL")

    def test_top_left_discovery_tabs_and_bl_tray_seeded(self):
        cfg = load_contract()
        seeds = cfg["seed_targets_1920x1080"]
        self.assertEqual(seeds["live.discovery_tab_lifelong_aspirations"]["client_xy"], [26, 34])
        self.assertEqual(seeds["live.discovery_tab_navigating_needs"]["client_xy"], [60, 34])
        self.assertEqual(seeds["live.discovery_tab_you_and_your_phone"]["client_xy"], [99, 34])
        event = seeds["live.discovery_tab_event_context"]
        self.assertEqual(event["client_xy"], [135, 34])
        self.assertEqual(event["status"], "ABSENT_NOW_ESTIMATED_WHEN_PRESENT")
        tabs = cfg["top_left_discovery_tabs_1920x1080"]["targets"]
        self.assertEqual(tabs["lifelong_aspirations"]["status"], "PRESENT")
        self.assertEqual(tabs["event_context_slot"]["status"], "ABSENT_NOW_ESTIMATED_WHEN_PRESENT")
        bl = cfg["bottom_left_utility_tray_1920x1080"]["targets"]
        self.assertEqual(bl["notebook"]["client_xy"], [258, 1055])
        self.assertEqual(bl["phone"]["client_xy"], [282, 1055])
        self.assertEqual(bl["show_calendar"]["client_xy"], [305, 1055])
        tr = cfg["top_right_hud_1920x1080"]["targets"]
        self.assertEqual(tr["build_buy"]["client_xy"], [1504, 22])
        self.assertEqual(tr["manage_worlds"]["client_xy"], [1562, 22])
        self.assertEqual(tr["gallery"]["client_xy"], [1609, 22])
        self.assertEqual(tr["options_ellipsis"]["client_xy"], [1898, 22])
        self.assertIn("cheat_console_collision", cfg["top_right_hud_1920x1080"])
        self.assertNotEqual(
            seeds["live.top_manage_worlds"]["client_xy"],
            seeds["live.top_gallery"]["client_xy"],
        )

    def test_skills_burger_min_max_endpoints(self):
        cfg = load_contract()
        seeds = cfg["seed_targets_1920x1080"]
        self.assertEqual(seeds["live.skills_burger_grip_min"]["client_xy"], [1722, 810])
        self.assertEqual(seeds["live.skills_burger_grip_max"]["client_xy"], [1722, 225])
        self.assertNotEqual(
            seeds["live.skills_burger_grip_min"]["client_xy"],
            seeds["live.skills_burger_grip_max"]["client_xy"],
        )
        burger = cfg["skills_burger_bar_1920x1080"]
        self.assertEqual(burger["endpoints"]["min"]["client_xy"], [1722, 810])
        self.assertEqual(burger["endpoints"]["max"]["client_xy"], [1722, 225])
        self.assertIn("SCROLLBAR_ALONE_AS_FULL_PANEL_READ", burger["not"])
        plan = plan_skills_burger_expand()
        self.assertEqual(plan["open_hotkey"], "L")
        self.assertEqual(plan["drag"]["from_xy"], [1722, 810])
        self.assertEqual(plan["drag"]["to_xy"], [1722, 225])
        self.assertFalse(plan["execute_allowed"])
        self.assertIn("SCROLLBAR_ALONE_AS_FULL_PANEL_READ", plan["forbidden"])

    def test_whim_pin_slots_seeded(self):
        cfg = load_contract()
        seeds = cfg["seed_targets_1920x1080"]
        self.assertEqual(seeds["live.whim_slot_0_bubble"]["client_xy"], [145, 833])
        self.assertEqual(seeds["live.whim_slot_0_pin"]["client_xy"], [170, 847])
        self.assertEqual(seeds["live.whim_slot_1_bubble"]["client_xy"], [203, 827])
        self.assertEqual(seeds["live.whim_slot_1_pin"]["client_xy"], [233, 833])
        self.assertEqual(
            seeds["live.whim_slot_3_shoulder_bubble"]["bubble_shape"],
            "JAGGED_STARBURST_RARE_FOURTH",
        )
        self.assertEqual(seeds["live.whim_slot_3_shoulder_bubble"]["client_xy"], [278, 900])
        self.assertEqual(seeds["live.whim_slot_3_shoulder_pin"]["client_xy"], [308, 906])
        whims = cfg["whims_pin_slots_1920x1080"]
        self.assertEqual(whims["targets"]["slot_0_left"]["pin_xy"], [170, 847])
        self.assertEqual(whims["pin_offset_from_bubble_center_px"], [30, 6])
        self.assertEqual(whims["geometry"]["pin_thumbtack"].split()[0], "Small")
        self.assertIn("CLICK_CONTENT_THUMBNAIL_AS_PIN", whims["not"])
        self.assertIn("PIN_EXECUTE_FROM_SLOT_SEED_ALONE", whims["not"])
        # Pin badge is not the bubble center
        self.assertNotEqual(
            seeds["live.whim_slot_0_bubble"]["client_xy"],
            seeds["live.whim_slot_0_pin"]["client_xy"],
        )

    def test_center_console_seeded(self):
        cfg = load_contract()
        seeds = cfg["seed_targets_1920x1080"]
        self.assertEqual(seeds["live.center_pause"]["client_xy"], [889, 1033])
        self.assertEqual(seeds["live.center_play_1x"]["client_xy"], [920, 1033])
        self.assertEqual(seeds["live.center_fast_2x"]["client_xy"], [952, 1033])
        self.assertEqual(seeds["live.center_ultra_3x"]["client_xy"], [984, 1033])
        self.assertEqual(seeds["live.center_camera_shutter"]["client_xy"], [1040, 1033])
        console = cfg["center_console_1920x1080"]
        self.assertTrue(console["prefer_hotkey_speed"])
        self.assertEqual(console["targets"]["clock_calendar"]["client_xy"], [930, 1065])
        self.assertNotEqual(
            console["targets"]["clock_calendar"]["client_xy"],
            seeds["live.show_calendar"]["client_xy"],
        )
        self.assertIn("PREFER_MOUSE_OVER_SPEED_HOTKEY", console["not"])


    def test_arm_to_console_handoff_plan(self):
        plan = plan_arm_to_console_handoff()
        self.assertEqual(plan["arm"]["step"], "ARM_LIVE_HOTKEYS")
        self.assertEqual(plan["console"]["chord"], ["CTRL", "SHIFT", "C"])
        self.assertTrue(plan["console"]["require_white_strip_observed"])
        self.assertFalse(plan["execute_allowed"])
        self.assertIn("TYPE_WITHOUT_CONSOLE_STRIP", plan["forbidden"])

    def test_resolve_unknown_fails(self):
        with self.assertRaises(FixedUiClickMapError):
            resolve_target_xy(empty_ledger(), "live.does_not_exist")

    def test_escape_menu_save_and_save_as_distinct_with_dialog_policy(self):
        cfg = load_contract()
        self.assertGreaterEqual(cfg["version"], 7)
        coords = load_escape_menu_coords()
        self.assertEqual(coords["menu_options"], (1898, 22))
        self.assertEqual(coords["save"], (960, 420))
        self.assertEqual(coords["save_as"], (960, 422))
        self.assertNotEqual(coords["save"], coords["save_as"])
        dy = abs(coords["save_as"][1] - coords["save"][1])
        self.assertEqual(dy, 2)
        seeds = cfg["seed_targets_1920x1080"]
        self.assertEqual(seeds["live.escape_menu_save"]["client_xy"], [960, 420])
        self.assertEqual(seeds["live.escape_menu_save_as"]["client_xy"], [960, 422])
        plan = plan_escape_menu_save(intent="SAVE_AS")
        self.assertEqual(plan["menu_row"]["client_xy"], [960, 422])
        self.assertTrue(plan["save_vs_save_as_hazard"]["within_default_hit_radius"])
        self.assertIn("DELETE", plan["dialog_forbidden"])
        self.assertIn("OVERWRITE", plan["dialog_forbidden"])
        add_new = plan["save_game_dialog"]["add_new_save"]
        self.assertEqual(add_new.get("client_xy"), [850, 360])
        self.assertEqual(add_new.get("status"), "LIVE_MEASURED_20261110")
        dialog = cfg["escape_menu_1920x1080"]["save_game_dialog_1920x1080"]["targets"]
        self.assertEqual(dialog["add_new_save_ok"]["client_xy"], [957, 603])
        self.assertEqual(dialog["save_game_close_x"]["client_xy"], [1342, 238])
        self.assertIn("USE_MENU_SAVE_FOR_NEW_SLOT", plan["forbidden"])


class CameraDependentFridgeSeedTests(unittest.TestCase):
    def test_wide_and_zoomed_fridge_coords_are_not_equivalent(self):
        cfg = load_contract()
        seeds = load_camera_dependent_fridge_seeds(cfg=cfg)
        hit = seeds["hit_zoomed"]["client_xy"]
        stale = seeds["stale_wide"]["client_xy"]
        self.assertEqual(hit, (500, 560))
        self.assertEqual(stale, (465, 595))
        self.assertEqual(seeds["hit_zoomed"]["camera_state"], "ZOOMED_IN_RECENTERED")
        self.assertEqual(seeds["stale_wide"]["camera_state"], "WIDE_NEIGHBORHOOD_ZOOM")
        radius = cfg["thresholds_px"]["hit_radius"]
        dist = ((hit[0] - stale[0]) ** 2 + (hit[1] - stale[1]) ** 2) ** 0.5
        self.assertGreater(dist, radius)
        scored = classify_click(intended_xy=hit, observed_xy=stale, cfg=cfg)
        self.assertNotEqual(scored["classification"], "HIT")

    def test_zoom_precondition_is_z_or_wheel_never_rmb(self):
        pre = load_camera_dependent_fridge_seeds()["zoom_precondition"]
        self.assertEqual(pre["required"], "ZOOMED_IN_RECENTERED")
        self.assertEqual(pre["actuator"], ["KEY_Z", "MOUSE_WHEEL"])
        self.assertIn("RIGHT_CLICK", pre["forbidden_actuator"])
        self.assertEqual(pre["recenter"], "ENTER_CENTER_ACTIVE_SIM")

    def test_camera_dependent_seeds_not_ingested_as_fixed_hud(self):
        cfg = load_contract()
        block = cfg["camera_dependent_seeds_1920x1080"]
        self.assertFalse(block["ingest_into_fixed_ledger"])
        self.assertIn("USE_HIT_XY_WITHOUT_ZOOM_PRECONDITION", block["forbidden"])
        self.assertIn("CAMERA_DEPENDENT_WORLD_PIXELS", cfg["scope"]["out"])
        ledger = ensure_seeded_ledger(empty_ledger(), cfg=cfg)
        for tid in ledger["targets"]:
            self.assertFalse(tid.startswith("world.fridge"), tid)
        self.assertEqual(cfg["seed_targets_1920x1080"]["live.calendar_close_x"]["client_xy"], [1445, 255])


if __name__ == "__main__":
    unittest.main()
