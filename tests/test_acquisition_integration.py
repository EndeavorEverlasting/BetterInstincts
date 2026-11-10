"""CLI and machine-contract entry points for safe household acquisition routes.

No Sims host, GUI, Windows service, or saved game state is contacted.
"""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from scripts.upgrade_parts_force import main

ROOT = Path(__file__).resolve().parents[1]


class AcquisitionRoutingIntegrationTests(unittest.TestCase):
    def invoke(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(args))
        return code, json.loads(buf.getvalue())

    def test_cli_source_catalog_lists_four_distinct_domains(self):
        code, data = self.invoke("sources")
        self.assertEqual(code, 0)
        sources = {entry["source"] for entry in data["route_catalog"].values()}
        self.assertEqual(sources, {"computer_order", "eco_fabricator",
                                   "insect_farm", "recycler_generator"})
        self.assertFalse(data["execute_allowed"])

    def test_cli_observed_actor_and_mixed_source_planning(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            portraits = root / "portraits.json"
            requests = root / "requests.json"
            portraits.write_text(json.dumps([
                {"slot": 0, "portrait_id": "found-A", "observed": True},
                {"slot": 3, "portrait_id": "found-B", "observed": True}]), encoding="utf-8")
            requests.write_text(json.dumps([
                {"item": "Robot Salvage Parts", "quantity": 2},
                {"item": "Eco-Upgrade Parts", "quantity": 1},
                {"item": "fuel", "quantity": 1},
                {"item": "insect biofuel-filled can", "quantity": 1},
            ]), encoding="utf-8")
            code, data = self.invoke(
                "acquisition", "--portraits", str(portraits),
                "--requests", str(requests),
                "--selected-slots", "3",
                "--packs-observed", "Discover University", "Eco Lifestyle",
            )
            self.assertEqual(code, 0)
            self.assertEqual(data["portraits_selected"], ["found-B"])
            self.assertEqual(len(data["action_classification"]), 4)
            self.assertFalse(data["execute_allowed"])
            self.assertEqual({x["source"] for x in data["requests"]},
                             {"computer_order", "eco_fabricator",
                              "insect_farm", "recycler_generator"})
            self.assertFalse((root / "cert.json").exists())

    def test_cli_menu_next_accepts_two_observed_pages(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            options = root / "options.json"
            seen = root / "seen.json"
            options.write_text(json.dumps(["Other", "More Choices..."]), encoding="utf-8")
            code, first = self.invoke("menu-next", "--options", str(options),
                                      "--goal", "Purchase Upgrade Parts")
            self.assertEqual(code, 0)
            self.assertEqual(first["state"], "MORE_CHOICES_OBSERVED")
            seen.write_text(json.dumps(first["next_history"]), encoding="utf-8")
            options.write_text(json.dumps(["Purchase Upgrade Parts...", "More Choices"]),
                               encoding="utf-8")
            code, second = self.invoke("menu-next", "--options", str(options),
                                       "--goal", "Purchase Upgrade Parts",
                                       "--visited", str(seen))
            self.assertEqual(code, 0)
            self.assertEqual(second["state"], "CHOICE_OBSERVED")
            self.assertFalse(second["execute_allowed"])

    def test_generic_domain_cli_never_invents_visible_items(self):
        with tempfile.TemporaryDirectory() as folder:
            portraits = Path(folder) / "portraits.json"
            portraits.write_text(json.dumps([{"slot": 5, "portrait_id": "live:5",
                                              "observed": True}]), encoding="utf-8")
            code, plan = self.invoke("order-domain", "--portraits", str(portraits),
                                     "--domain", "Custom Purchase Domain",
                                     "--item", "Sought Product",
                                     "--selected-slots", "5")
            self.assertEqual(code, 0)
            self.assertEqual(plan["known_item_availability"], "NOT_PROVEN_UNTIL_VISIBLE")
            self.assertFalse(plan["execute_allowed"])

    def test_semantic_contract_and_horizon_remain_consistent(self):
        graph = json.loads((ROOT / "contracts/ontology.v1.json").read_text(encoding="utf-8"))
        self.assertIn("OBSERVED_MENU_ROUTE", graph["concepts"])
        self.assertIn("ACQUISITION_SOURCE", graph["concepts"])
        self.assertIn("ACTION_EFFECT_CLASS", graph["concepts"])
        terms = {x["term"] for x in graph["invariants"]}
        self.assertIn("MENU_PAGINATION_NEVER_BLIND", terms)
        self.assertIn("ACQUISITION_ACTOR_SOURCE_AND_EFFECT_PROOF", terms)
        horizon = json.loads((ROOT / "plans/horizon.v1.json").read_text(encoding="utf-8"))
        self.assertEqual(horizon["current_gate"], "BI-002")


if __name__ == "__main__":
    unittest.main()
