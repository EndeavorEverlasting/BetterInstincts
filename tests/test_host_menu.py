import unittest

from betterinstincts.host_menu import HostMenuError, load_contract, plan_journey
from betterinstincts.menu_blockers import blockers, plan_dismiss
from betterinstincts.scenes import load_catalog


class HostMenuTests(unittest.TestCase):
    def test_contract_reboot_journey(self):
        cfg = load_contract()
        self.assertEqual(cfg["reboot_journey"][1], "dismiss_memory_boost")
        self.assertIn("RESUME", cfg["forbidden_always"])
        plan = plan_journey("reboot")
        self.assertEqual(plan["state"], "HOST_MENU_JOURNEY_PLANNED")
        self.assertEqual(plan["steps"][1]["click"], [1427, 188])
        self.assertEqual(plan["steps"][2]["gate"], "OPEN_LOAD_GAME")
        self.assertEqual(plan["steps"][3]["gate"], "PLAY_LAB_DISPOSABLE")
        self.assertEqual(plan["steps"][4]["gate"], "SELECT_LABLAB_LOT")
        self.assertEqual(plan["steps"][5]["gate"], "CONFIRM_PLAY_LABLAB_LOT")

    def test_from_step_skips_prefix(self):
        plan = plan_journey("reboot", from_step="confirm_play_lablab_lot")
        self.assertEqual([s["id"] for s in plan["steps"]], ["confirm_play_lablab_lot"])

    def test_memory_boost_blocker_catalog(self):
        rows = blockers()
        self.assertEqual(rows[0]["id"], "memory_boost_on")
        plan = plan_dismiss(None)
        self.assertEqual(plan["steps"][0]["step"], "DISMISS_MEMORY_BOOST")

    def test_scene_catalog_includes_memory_boost(self):
        catalog = load_catalog()
        ids = {s["id"] for s in catalog["scenes"]}
        self.assertIn("memory_boost_modal", ids)
        scene = next(s for s in catalog["scenes"] if s["id"] == "memory_boost_modal")
        self.assertEqual(scene["evidence_state"], "LOCAL_OBSERVED")

    def test_unknown_journey_fails_closed(self):
        with self.assertRaises(HostMenuError):
            plan_journey("career")


if __name__ == "__main__":
    unittest.main()
