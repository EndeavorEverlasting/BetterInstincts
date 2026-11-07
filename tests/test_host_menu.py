import unittest

from betterinstincts.host_menu import (
    HostMenuError,
    load_contract,
    plan_from_scene,
    plan_journey,
    resolve_scene,
)
from betterinstincts.menu_blockers import blockers, plan_dismiss
from betterinstincts.scenes import load_catalog


class HostMenuTests(unittest.TestCase):
    def test_contract_reboot_journey(self):
        cfg = load_contract()
        self.assertEqual(cfg["reboot_journey"][1], "dismiss_memory_boost")
        self.assertIn("RESUME", cfg["forbidden_always"])
        self.assertIn("select_sim_to_play", cfg["scenes"])
        self.assertEqual(
            cfg["scenes"]["manage_worlds_or_map"]["substeps"],
            ["select_lablab_domicile"],
        )
        self.assertEqual(
            cfg["scenes"]["select_sim_to_play"]["substeps"],
            ["select_charlee_profile", "confirm_play_after_sim"],
        )
        plan = plan_journey("reboot")
        self.assertEqual(plan["state"], "HOST_MENU_JOURNEY_PLANNED")
        self.assertEqual(plan["steps"][1]["click"], [1427, 188])
        self.assertEqual(plan["steps"][2]["gate"], "OPEN_LOAD_GAME")
        self.assertEqual(plan["steps"][3]["gate"], "PLAY_LAB_DISPOSABLE")
        self.assertEqual(plan["steps"][4]["gate"], "SELECT_LABLAB_DOMICILE")
        self.assertEqual(plan["steps"][5]["gate"], "CONFIRM_PLAY_LABLAB_LOT")
        self.assertEqual(plan["steps"][6]["gate"], "SELECT_HOUSEHOLD_PROFILE")
        self.assertEqual(plan["steps"][6]["click"], [838, 392])
        self.assertEqual(plan["steps"][7]["gate"], "CONFIRM_PLAY_AFTER_SIM")

    def test_from_step_skips_prefix(self):
        plan = plan_journey("reboot", from_step="confirm_play_lablab_lot")
        self.assertEqual(
            [s["id"] for s in plan["steps"]],
            ["confirm_play_lablab_lot", "select_charlee_profile", "confirm_play_after_sim"],
        )

    def test_from_scene_select_sim_resumes_profile_substeps(self):
        plan = plan_from_scene("select_sim_to_play")
        self.assertEqual(plan["from_scene"], "select_sim_to_play")
        self.assertEqual(
            [s["id"] for s in plan["steps"]],
            ["select_charlee_profile", "confirm_play_after_sim"],
        )
        self.assertEqual(
            plan["remaining_substeps"],
            ["select_charlee_profile", "confirm_play_after_sim"],
        )

    def test_from_scene_map_resumes_domicile_substeps(self):
        plan = plan_from_scene("neighborhood_map")
        self.assertEqual(plan["from_scene"], "manage_worlds_or_map")
        self.assertEqual(plan["steps"][0]["id"], "select_lablab_domicile")
        self.assertEqual(plan["steps"][-1]["id"], "confirm_play_after_sim")

    def test_from_scene_live_is_terminal(self):
        plan = plan_from_scene("live")
        self.assertEqual(plan["state"], "HOST_MENU_ALREADY_AT_TERMINAL")
        self.assertEqual(plan["steps"], [])

    def test_scene_alias_resolution(self):
        self.assertEqual(resolve_scene("lot_details"), "lablab_lot_selected")
        self.assertEqual(resolve_scene("select_sim"), "select_sim_to_play")
        with self.assertRaises(HostMenuError):
            resolve_scene("richardson_save")

    def test_memory_boost_blocker_catalog(self):
        rows = blockers()
        self.assertEqual(rows[0]["id"], "memory_boost_on")
        plan = plan_dismiss(None)
        self.assertEqual(plan["steps"][0]["step"], "DISMISS_MEMORY_BOOST")

    def test_scene_catalog_includes_memory_boost_and_select_sim(self):
        catalog = load_catalog()
        ids = {s["id"] for s in catalog["scenes"]}
        self.assertIn("memory_boost_modal", ids)
        self.assertIn("select_sim_to_play", ids)
        scene = next(s for s in catalog["scenes"] if s["id"] == "select_sim_to_play")
        self.assertEqual(scene["evidence_state"], "LOCAL_OBSERVED")

    def test_unknown_journey_fails_closed(self):
        with self.assertRaises(HostMenuError):
            plan_journey("career")


if __name__ == "__main__":
    unittest.main()
