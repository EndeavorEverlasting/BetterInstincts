import json
import unittest
from pathlib import Path

from betterinstincts.upgrade_parts_force import (
    UpgradePartsForceError,
    catalog_snapshot,
    how_to_buy,
    load_contract,
    plan_parts_force,
    resolve_part,
    steps_to_operator_checklist,
)


class UpgradePartsForceTests(unittest.TestCase):
    def test_contract_architecture_and_forbidden(self):
        cfg = load_contract()
        self.assertEqual(cfg["architecture"]["selected"], "UPGRADE_PARTS_FORCE")
        self.assertIn("gsi_create_obj", cfg["forbidden"])
        self.assertIn("computer", cfg["paths"])
        self.assertIn("spawn", cfg["paths"])
        self.assertEqual(cfg["quantity"]["tune_up_observed_minimum"], 4)

    def test_catalog_includes_robot_salvage(self):
        snap = catalog_snapshot()
        ids = {row["id"] for row in snap["parts"]}
        self.assertIn("robot_salvage_parts", ids)
        self.assertFalse(snap["execute_allowed"])
        self.assertIn("gsi_create_obj", snap["forbidden"])

    def test_how_to_buy_names_computer_order_path(self):
        guide = how_to_buy("robot_salvage_parts")
        blob = " ".join(guide["steps"]) + " " + str(guide["summary"])
        self.assertIn("Purchase Upgrade Parts", blob)
        self.assertIn("Order", blob)
        self.assertEqual(guide["tune_up_units_observed"], 4)
        self.assertFalse(guide["execute_allowed"])

    def test_synonym_resolves_gardener_bot_parts(self):
        part = resolve_part("gardener bot parts")
        self.assertEqual(part["id"], "robot_salvage_parts")
        self.assertEqual(part["resolved_via"], "synonym")

    def test_computer_spam_plan_repeats_for_quantity(self):
        plan = plan_parts_force(
            part_id="robot_salvage_parts",
            quantity=4,
            path="computer",
            game_mode="live",
        )
        self.assertEqual(plan["state"], "UPGRADE_PARTS_FORCE_PLAN_READY")
        self.assertEqual(plan["quantity"], 4)
        self.assertEqual(plan["purchase_units_planned"], 4)
        self.assertFalse(plan["execute_allowed"])
        self.assertTrue(plan["not_bi002"])
        ops = [s["op"] for s in plan["steps"]]
        self.assertIn("PIE_MENU", ops)
        self.assertIn("SELECT_PART", ops)
        self.assertIn("REPEAT_PURCHASE", ops)
        repeat = next(s for s in plan["steps"] if s["op"] == "REPEAT_PURCHASE")
        self.assertEqual(repeat["times"], 3)
        select = next(s for s in plan["steps"] if s["op"] == "SELECT_PART")
        self.assertEqual(select["display_name"], "Robot Salvage Parts")

    def test_default_quantity_is_twenty(self):
        plan = plan_parts_force(part_id="robot_salvage_parts", path="computer")
        self.assertEqual(plan["quantity"], 20)
        repeat = next(s for s in plan["steps"] if s["op"] == "REPEAT_PURCHASE")
        self.assertEqual(repeat["times"], 19)

    def test_spawn_path_requires_testingcheats_first(self):
        plan = plan_parts_force(
            part_id="robot_salvage_parts",
            path="spawn",
            quantity=20,
            game_mode="live",
        )
        self.assertTrue(plan["requires_testingcheats"])
        cmds = [s.get("command") for s in plan["steps"] if s.get("op") == "TYPE_COMMAND"]
        self.assertEqual(cmds[0], "testingcheats enabled true")
        ops = [s["op"] for s in plan["steps"]]
        self.assertIn("SHIFT_CLICK_OBJECT", ops)
        self.assertIn("Spawn Crafting Supplies", [s.get("choice") for s in plan["steps"]])

    def test_computer_path_rejects_non_live(self):
        with self.assertRaises(UpgradePartsForceError) as ctx:
            plan_parts_force(path="computer", game_mode="build")
        self.assertIn("COMPUTER_PURCHASE_REQUIRES_LIVE", str(ctx.exception))

    def test_unknown_part_fails_closed(self):
        with self.assertRaises(UpgradePartsForceError) as ctx:
            plan_parts_force(part_id="moon_rock_widgets")
        self.assertIn("UNKNOWN_UPGRADE_PART", str(ctx.exception))

    def test_invalid_quantity_fails_closed(self):
        with self.assertRaises(UpgradePartsForceError):
            plan_parts_force(quantity=0)
        with self.assertRaises(UpgradePartsForceError):
            plan_parts_force(quantity=100)

    def test_player_directed_yields(self):
        plan = plan_parts_force(player_directed=True)
        self.assertEqual(plan["state"], "YIELD_TO_PLAYER")
        self.assertEqual(plan["steps"], [])
        self.assertFalse(plan["execute_allowed"])

    def test_checklist_mentions_order_menu(self):
        plan = plan_parts_force(quantity=4, path="computer")
        lines = steps_to_operator_checklist(plan)
        blob = " | ".join(lines)
        self.assertIn("Order", blob)
        self.assertIn("Purchase Upgrade Parts", blob)
        self.assertIn("Robot Salvage Parts", blob)

    def test_cli_script_compiles(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "upgrade_parts_force.py"
        compile(script.read_text(encoding="utf-8"), str(script), "exec")

    def test_contract_json_roundtrip(self):
        raw = json.loads(
            (Path(__file__).resolve().parents[1] / "contracts" / "upgrade-parts-force.v1.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(raw["schema"], "betterinstincts.upgrade-parts-force/v1")


if __name__ == "__main__":
    unittest.main()
