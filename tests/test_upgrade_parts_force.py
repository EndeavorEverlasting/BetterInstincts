import json
import tempfile
import unittest
from pathlib import Path

from betterinstincts.upgrade_parts_force import (
    UpgradePartsForceError,
    budget_snapshot,
    catalog_snapshot,
    evaluate_diy_parts_cert,
    how_to_buy,
    load_contract,
    plan_household_parts_budget,
    plan_parts_force,
    record_part_observation,
    resolve_part,
    status_cert,
    steps_to_operator_checklist,
)


class UpgradePartsForceTests(unittest.TestCase):
    def test_contract_household_budget_architecture(self):
        cfg = load_contract()
        self.assertEqual(cfg["architecture"]["selected"], "HOUSEHOLD_DIY_PARTS_BUDGET")
        self.assertEqual(cfg["version"], 2)
        self.assertEqual(cfg["household_budget"]["selected"], "PER_SIM_POCKET_STOCK")
        self.assertEqual(cfg["household_budget"]["preferred_acquisition_order"][0], "spawn")
        self.assertIn("phone", cfg["paths"])
        self.assertIn("gsi_create_obj", cfg["forbidden"])

    def test_catalog_diy_kit_covers_core_parts(self):
        snap = catalog_snapshot()
        ids = set(snap["diy_kit_part_ids"])
        for required in (
            "common_upgrade_parts",
            "electronic_upgrade_parts",
            "plumbing_upgrade_parts",
            "kitchen_upgrade_parts",
            "robot_salvage_parts",
            "computer_chip",
            "mechanism",
        ):
            self.assertIn(required, ids)
        self.assertFalse(snap["execute_allowed"])

    def test_budget_snapshot_pocket_destination(self):
        snap = budget_snapshot()
        self.assertEqual(snap["destination"], "sim_pocket_inventory")
        self.assertGreaterEqual(len(snap["parts"]), 7)
        self.assertTrue(all(p["destination"] == "sim_pocket_inventory" for p in snap["parts"]))

    def test_how_to_buy_names_order_path(self):
        guide = how_to_buy("robot_salvage_parts")
        blob = " ".join(guide["steps"]) + " " + str(guide["summary"])
        self.assertIn("Purchase Upgrade Parts", blob)
        self.assertIn("Order", blob)

    def test_synonym_resolves_electronics(self):
        part = resolve_part("electronics")
        self.assertEqual(part["id"], "electronic_upgrade_parts")

    def test_spawn_is_default_for_robot_salvage(self):
        plan = plan_parts_force(part_id="robot_salvage_parts", quantity=20)
        self.assertEqual(plan["path"], "spawn")
        self.assertTrue(plan["requires_testingcheats"])

    def test_phone_path_plan(self):
        plan = plan_parts_force(part_id="kitchen_upgrade_parts", path="phone", quantity=5)
        self.assertEqual(plan["path"], "phone")
        ops = [s["op"] for s in plan["steps"]]
        self.assertIn("OPEN_PHONE", ops)
        self.assertIn("REPEAT_PURCHASE", ops)

    def test_buy_mode_rejected(self):
        with self.assertRaises(UpgradePartsForceError) as ctx:
            plan_parts_force(path="buy_mode")
        self.assertIn("BUY_MODE_NOT_PREFERRED_ACQUISITION", str(ctx.exception))

    def test_household_plan_for_n_members(self):
        plan = plan_household_parts_budget(members=4, path="spawn")
        self.assertEqual(plan["state"], "HOUSEHOLD_DIY_PARTS_BUDGET_PLAN_READY")
        self.assertEqual(plan["household_members"], 4)
        self.assertEqual(len(plan["member_plans"]), 4)
        self.assertEqual(plan["destination"], "sim_pocket_inventory")
        self.assertFalse(plan["execute_allowed"])
        chords = [s for s in plan["steps"] if s.get("op") == "KEY"]
        self.assertEqual(len(chords), 3)  # Space between 4 members
        self.assertIn("robot_salvage_parts", plan["diy_kit_part_ids"])

    def test_household_invalid_n_fails(self):
        with self.assertRaises(UpgradePartsForceError):
            plan_household_parts_budget(members=0)
        with self.assertRaises(UpgradePartsForceError):
            plan_household_parts_budget(members=101)

    def test_cert_all_met_review_required(self):
        kit = catalog_snapshot()["diy_kit_part_ids"]
        observations = []
        for slot in range(2):
            observations.append(
                {
                    "member_slot": slot,
                    "parts": {pid: 20 for pid in kit},
                }
            )
        cert = evaluate_diy_parts_cert(members=2, observations=observations)
        self.assertEqual(cert["aggregate_state"], "ALL_MEMBERS_MET_REVIEW_REQUIRED")
        self.assertFalse(cert["certified"])
        self.assertEqual(cert["members_met"], 2)

    def test_cert_unknown_without_counts(self):
        observations = [{"member_slot": 0, "parts": {}}, {"member_slot": 1, "parts": {}}]
        cert = evaluate_diy_parts_cert(members=2, observations=observations)
        self.assertEqual(cert["aggregate_state"], "UNPROVEN")
        self.assertTrue(all(p["state"] == "UNKNOWN" for m in cert["members"] for p in m["parts"]))

    def test_cert_partial_short(self):
        kit = catalog_snapshot()["diy_kit_part_ids"]
        parts = {pid: 20 for pid in kit}
        parts["robot_salvage_parts"] = 2
        cert = evaluate_diy_parts_cert(
            members=1,
            observations=[{"member_slot": 0, "parts": parts}],
        )
        self.assertEqual(cert["aggregate_state"], "PARTIAL")
        salvage = next(p for p in cert["members"][0]["parts"] if p["part_id"] == "robot_salvage_parts")
        self.assertEqual(salvage["state"], "SHORT")

    def test_record_and_status_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kit = catalog_snapshot()["diy_kit_part_ids"]
            cert = None
            for pid in kit:
                cert = record_part_observation(
                    run_id="lab-n2",
                    member_slot=0,
                    part_id=pid,
                    observed_count=50,
                    members=2,
                    root=root,
                )
                record_part_observation(
                    run_id="lab-n2",
                    member_slot=1,
                    part_id=pid,
                    observed_count=50,
                    members=2,
                    root=root,
                )
            self.assertIsNotNone(cert)
            status = status_cert("lab-n2", root=root)
            self.assertEqual(status["aggregate_state"], "ALL_MEMBERS_MET_REVIEW_REQUIRED")
            self.assertEqual(status["household_members"], 2)

    def test_player_directed_yields(self):
        plan = plan_household_parts_budget(members=3, player_directed=True)
        self.assertEqual(plan["state"], "YIELD_TO_PLAYER")

    def test_checklist_mentions_space_traverse(self):
        plan = plan_household_parts_budget(members=3, path="spawn")
        lines = steps_to_operator_checklist(plan)
        blob = " | ".join(lines)
        self.assertIn("SPACE", blob)
        self.assertIn("Spawn Crafting Supplies", blob)

    def test_cli_script_compiles(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "upgrade_parts_force.py"
        compile(script.read_text(encoding="utf-8"), str(script), "exec")

    def test_contract_json_roundtrip(self):
        raw = json.loads(
            (Path(__file__).resolve().parents[1] / "contracts" / "upgrade-parts-force.v1.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(raw["schema"], "betterinstincts.upgrade-parts-force/v1")
        self.assertEqual(raw["architecture"]["selected"], "HOUSEHOLD_DIY_PARTS_BUDGET")


if __name__ == "__main__":
    unittest.main()
