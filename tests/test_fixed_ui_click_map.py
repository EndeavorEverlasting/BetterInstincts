"""Offline falsifiers for fixed-UI click ledger + arm→console handoff."""
from __future__ import annotations

import unittest

from betterinstincts.fixed_ui_click_map import (
    FixedUiClickMapError,
    classify_click,
    empty_ledger,
    ensure_seeded_ledger,
    is_forbidden_target,
    load_contract,
    load_inventory_multiselect_coords,
    load_camera_dependent_fridge_seeds,
    load_escape_menu_coords,
    load_load_play_recovery_coords,
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
        self.assertEqual(cfg["seed_targets_1920x1080"]["live.notebook_close_x"]["client_xy"], [1338, 276])
        self.assertGreaterEqual(cfg["version"], 10)


class InventoryMultiselectTests(unittest.TestCase):
    def test_multiselect_and_sell_coords(self):
        cfg = load_contract()
        self.assertGreaterEqual(cfg["version"], 11)
        coords = load_inventory_multiselect_coords(cfg=cfg)
        self.assertEqual(coords["multiselect_toggle"], (1878, 791))
        self.assertNotEqual(coords["multiselect_toggle"], (1880, 735))
        self.assertEqual(coords["sell_button"], (1915, 925))
        seeds = cfg["seed_targets_1920x1080"]
        toggle = seeds["live.inventory_multiselect_toggle"]
        self.assertEqual(toggle["client_xy"], [1878, 791])
        self.assertEqual(toggle["prior_xy_wrong"], [1880, 735])
        self.assertEqual(toggle["panel_scope"], "HOUSEHOLD")
        self.assertIn("1846-1911", toggle["measured_evidence"]["on_state"])
        self.assertIn("1878, 793", toggle["measured_evidence"]["off_state"])
        # ON switch bbox 1846-1911 x 784-799 contains the click point.
        self.assertTrue(1846 <= coords["multiselect_toggle"][0] <= 1911)
        self.assertTrue(784 <= coords["multiselect_toggle"][1] <= 799)
        hvp = cfg["inventory_multiselect_1920x1080"]["household_vs_personal"]
        self.assertFalse(hvp["household_panel"]["eat_supported"])
        self.assertEqual(hvp["personal_panel"]["target_id"], "live.panel_inventory")
        self.assertIn("EAT_FROM_HOUSEHOLD_MULTISELECT", cfg["inventory_multiselect_1920x1080"]["forbidden"])
        self.assertEqual(seeds["live.inventory_sell_button"]["status"], "FORBIDDEN_DENY")
        self.assertEqual(seeds["live.inventory_sell_button"]["action"], "deny")
        near = cfg["thresholds_px"]["near_miss_radius"]
        dx = coords["sell_button"][0] - coords["multiselect_toggle"][0]
        dy = coords["sell_button"][1] - coords["multiselect_toggle"][1]
        self.assertGreater((dx * dx + dy * dy) ** 0.5, near)
        self.assertIn("CLICK_INVENTORY_SELL_BUTTON", cfg["inventory_multiselect_1920x1080"]["forbidden"])

    def test_prior_inventory_and_needs_tray_entries_unchanged(self):
        seeds = load_contract()["seed_targets_1920x1080"]
        # v12 corrected tray glyph; prior_xy_wrong [1757,1045] remains on the seed.
        self.assertEqual(seeds["live.panel_inventory"]["client_xy"], [1750, 1058])
        self.assertEqual(seeds["live.panel_inventory"]["prior_xy_wrong"], [1757, 1045])
        self.assertEqual(seeds["live.panel_inventory"]["panel_id"], "personal_inventory")
        self.assertEqual(seeds["live.panel_inventory"]["hotkey"], "I")
        self.assertEqual(seeds["live.panel_needs"]["client_xy"], [1820, 1045])

    def test_sell_cannot_be_attested_hit_or_resolved_as_clickable(self):
        ledger = ensure_seeded_ledger(empty_ledger())
        self.assertTrue(is_forbidden_target("live.inventory_sell_button"))
        self.assertFalse(is_forbidden_target("live.inventory_multiselect_toggle"))
        with self.assertRaises(FixedUiClickMapError):
            record_click_attempt(
                ledger,
                target_id="live.inventory_sell_button",
                client_xy=[1915, 925],
                classification="HIT",
            )
        self.assertFalse(ledger["targets"]["live.inventory_sell_button"]["attested"])
        self.assertEqual(ledger["targets"]["live.inventory_sell_button"]["hit_count"], 0)
        self.assertTrue(resolve_target_xy(ledger, "live.inventory_sell_button")["denied"])
        self.assertFalse(resolve_target_xy(ledger, "live.inventory_multiselect_toggle")["denied"])

    def test_multiselect_toggle_can_attest_hit(self):
        ledger = ensure_seeded_ledger(empty_ledger())
        record_click_attempt(
            ledger,
            target_id="live.inventory_multiselect_toggle",
            client_xy=[1878, 791],
            classification="HIT",
        )
        self.assertTrue(ledger["targets"]["live.inventory_multiselect_toggle"]["attested"])


class LoadPlayRecoveryCoordTests(unittest.TestCase):
    def test_load_play_recovery_measured_coords(self):
        cfg = load_contract()
        self.assertGreaterEqual(cfg["version"], 10)
        coords = load_load_play_recovery_coords(cfg=cfg)
        self.assertEqual(coords["main_menu_load_game"], (220, 590))
        self.assertEqual(coords["load_game_play_slot_6"], (1257, 353))
        self.assertEqual(coords["cas_cancel_x"], (1838, 1048))
        self.assertEqual(coords["exit_create_a_sim"], (960, 567))
        self.assertEqual(coords["willow_creek_world"], (120, 320))
        self.assertEqual(coords["lablab_lot_house"], (1456, 850))
        self.assertEqual(coords["manage_worlds_play"], (1811, 1033))
        self.assertEqual(coords["forbidden_blue_person"], (1883, 1040))
        block = cfg["load_play_recovery_1920x1080"]
        self.assertIn("camera_dependent", block["camera_dependent_note"].lower())
        self.assertGreaterEqual(
            block["hazards"]["load_game_delete_avoid_y_min"],
            coords["load_game_play_slot_6"][1],
        )
        seeds = cfg["seed_targets_1920x1080"]
        self.assertEqual(seeds["host.cas_cancel_x"]["prior_xy_stale"], [1830, 1050])
        self.assertEqual(seeds["host.forbidden_create_new_household"]["status"], "FORBIDDEN_DENY")

    def test_fridge_seeds_still_separate_from_load_play_block(self):
        cfg = load_contract()
        self.assertIn("camera_dependent_seeds_1920x1080", cfg)
        self.assertIn("load_play_recovery_1920x1080", cfg)
        self.assertIn(
            "MERGE_CAMERA_DEPENDENT_FRIDGE_INTO_THIS_BLOCK",
            cfg["load_play_recovery_1920x1080"]["not"],
        )
        self.assertFalse(cfg["camera_dependent_seeds_1920x1080"]["ingest_into_fixed_ledger"])


class ManageWorldsTravelPartyCancelTests(unittest.TestCase):
    def test_travel_party_cancel_x_live_measured(self):
        cfg = load_contract()
        self.assertGreaterEqual(cfg["version"], 15)
        seeds = cfg["seed_targets_1920x1080"]
        cancel = seeds["host.manage_worlds_travel_party_cancel_x"]
        self.assertEqual(cancel["client_xy"], [1055, 22])
        self.assertEqual(cancel["prior_xy_computer_use_scale"], [1055, 33])
        self.assertEqual(cancel["canvas_1456x840_xy"], [800, 25])
        self.assertEqual(cancel["status"], "PRINTWINDOW_REMEASURED_20261110")
        self.assertIn("manage_worlds.travel_party_cancel_x", cancel["aliases"])
        self.assertEqual(cancel["text_miss_canvas_1456x840_xy"], [556, 34])
        self.assertEqual(cancel["icon_order_after_lablab_text"], ["cancel_x", "footprint", "crown"])
        self.assertEqual(
            seeds["host.forbidden_manage_worlds_travel_party_footprint"]["client_xy"],
            [1090, 22],
        )
        self.assertEqual(
            seeds["host.forbidden_manage_worlds_travel_party_crown"]["client_xy"],
            [1131, 22],
        )
        self.assertEqual(
            seeds["host.forbidden_manage_worlds_travel_party_footprint"]["status"],
            "FORBIDDEN_DENY",
        )
        self.assertEqual(
            seeds["host.forbidden_manage_worlds_travel_party_crown"]["status"],
            "FORBIDDEN_DENY",
        )
        self.assertTrue(is_forbidden_target("host.forbidden_manage_worlds_travel_party_footprint"))
        self.assertTrue(is_forbidden_target("host.forbidden_manage_worlds_travel_party_crown"))
        self.assertFalse(is_forbidden_target("host.manage_worlds_travel_party_cancel_x"))
        block = cfg["manage_worlds_travel_party_1920x1080"]
        self.assertEqual(block["targets"]["travel_party_cancel_x"]["client_xy"], [1055, 22])
        self.assertEqual(block["alias_key"], "manage_worlds.travel_party_cancel_x")
        self.assertIn("CLICK_TRAVEL_PARTY_FOOTPRINT_AS_CANCEL", block["forbidden"])
        self.assertIn("EXPECT_ESC_TO_CANCEL_TRAVEL", block["forbidden"])
        # Text miss must not score as HIT against cancel X.
        miss = cancel["text_miss_client_xy"]
        scored = classify_click(
            intended_xy=cancel["client_xy"],
            observed_xy=miss,
            cfg=cfg,
        )
        self.assertNotEqual(scored["classification"], "HIT")

    def test_switch_control_chip_trap_annotated(self):
        cfg = load_contract()
        seeds = cfg["seed_targets_1920x1080"]
        chip = seeds["live.switch_control_chip"]
        self.assertEqual(chip["status"], "TRAP_ANNOTATED_NOT_HIT_CERTIFIED")
        self.assertEqual(chip["proved_miss_xy"], [455, 900])
        self.assertEqual(chip["click"], "PILL_TEXT")
        self.assertIn("EMPTY_STREET_HIGH_ABOVE_PORTRAIT_STRIP", chip["forbidden"])
        self.assertIn("LIGHTNING_ICON_ALONE_IF_OPENS_TRAVEL", chip["forbidden"])
        charlee = seeds["live.household_portrait_3"]
        self.assertEqual(charlee["magenta_bbox_printwindow"]["x"], [431, 480])
        self.assertEqual(charlee["face_hover_approx"], [455, 1035])
        block = cfg["manage_worlds_travel_party_1920x1080"]
        self.assertEqual(block["switch_control_trap"]["proved_miss_xy"], [455, 900])
        self.assertIn("SWITCH_CONTROL_EMPTY_STREET_ABOVE_STRIP", block["forbidden"])


if __name__ == "__main__":
    unittest.main()
