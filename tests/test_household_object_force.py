"""Offline coverage for the durable household useful-item force catalog."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from betterinstincts.household_object_force import (
    HouseholdObjectForceError,
    catalog_summary,
    elementary_unlock_steps,
    load_contract,
    plan_force,
    reject_forbidden_console,
    steps_to_commands,
    useful_item_catalog,
)


class HouseholdObjectForceTests(unittest.TestCase):
    def test_contract_invariants(self):
        cfg = load_contract()
        self.assertEqual(cfg["elementary_unlock"]["show_hidden_objects"], "bb.showhiddenobjects")
        self.assertFalse(cfg["optional_catalog_ux"]["required"])
        self.assertTrue(cfg["optional_catalog_ux"]["never_replaces_elementary_unlock"])
        self.assertGreaterEqual(len(cfg["useful_item_catalog"]), 6)
        self.assertIn("SUBSTITUTE_BBB_FOR_SHOW_HIDDEN_OBJECTS", cfg["forbidden_always"])

    def test_catalog_includes_operator_list(self):
        ids = {r["id"] for r in useful_item_catalog(include_optional=True)}
        for needed in (
            "out_of_this_world_desktop",
            "cruelty_free_meat_wall",
            "ufo_bed",
            "captain_sigma_statue",
            "positronic_pro",
            "eco_matic_smog_vacuum",
            "hydroponic_planter",
        ):
            self.assertIn(needed, ids)

    def test_elementary_unlock_commands(self):
        steps = elementary_unlock_steps()
        cmds = [s["command"] for s in steps if "command" in s]
        self.assertEqual(cmds, ["testingcheats true", "bb.showhiddenobjects"])

    def test_catalog_path_requires_elementary_unlock(self):
        with self.assertRaises(HouseholdObjectForceError) as ctx:
            plan_force(item_ids="eco_matic_smog_vacuum", skip_elementary_unlock=True)
        self.assertIn("ELEMENTARY_UNLOCK_REQUIRED", str(ctx.exception))

    def test_bbb_cannot_substitute_unlock(self):
        with self.assertRaises(HouseholdObjectForceError) as ctx:
            plan_force(item_ids="hydroponic_planter", substitute_bbb_for_unlock=True)
        self.assertIn("SUBSTITUTE_BBB_FOR_SHOW_HIDDEN_OBJECTS", str(ctx.exception))

    def test_plan_all_applies_elementary_once_for_catalog_items(self):
        plan = plan_force(item_ids="all")
        self.assertTrue(plan["elementary_unlock_applied"])
        self.assertFalse(plan["execute_allowed"])
        cmds = steps_to_commands(plan)
        self.assertEqual(cmds[0], "testingcheats true")
        self.assertEqual(cmds[1], "bb.showhiddenobjects")
        self.assertIn("careers.promote techguru", cmds)
        self.assertIn("careers.promote astronaut", cmds)
        self.assertNotIn("gsi_create_obj", " ".join(cmds))
        self.assertEqual(cmds.count("bb.showhiddenobjects"), 1)

    def test_career_only_skips_elementary_unlock(self):
        plan = plan_force(item_ids="ufo_bed,captain_sigma_statue")
        self.assertFalse(plan["elementary_unlock_applied"])
        cmds = steps_to_commands(plan)
        self.assertNotIn("bb.showhiddenobjects", cmds)
        self.assertTrue(all(c.startswith("careers.promote") for c in cmds))

    def test_forbidden_console_forms(self):
        with self.assertRaises(HouseholdObjectForceError):
            reject_forbidden_console("bb.showhiddenobjects / buydebug")
        with self.assertRaises(HouseholdObjectForceError):
            reject_forbidden_console("buydebug")
        with self.assertRaises(HouseholdObjectForceError):
            reject_forbidden_console("objects.gsi_create_obj 0x5B8D")

    def test_player_directed_yields(self):
        plan = plan_force(item_ids="all", player_directed=True)
        self.assertEqual(plan["state"], "YIELD_TO_PLAYER")
        self.assertEqual(plan["steps"], [])

    def test_catalog_summary_and_cli_compile(self):
        summary = catalog_summary()
        self.assertGreaterEqual(summary["count"], 6)
        self.assertEqual(summary["elementary_unlock"], "bb.showhiddenobjects")
        script = Path(__file__).resolve().parents[1] / "scripts" / "household_object_force.py"
        compile(script.read_text(encoding="utf-8"), str(script), "exec")
        raw = json.loads(
            (Path(__file__).resolve().parents[1] / "contracts" / "household-object-force.v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(raw["version"], 1)


if __name__ == "__main__":
    unittest.main()
