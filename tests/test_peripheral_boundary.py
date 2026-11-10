"""Regression cases for the Sims/Windows peripheral ownership boundary."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.check_peripheral_boundary import inspect_repository, inspect_source

ROOT = Path(__file__).resolve().parents[1]


class PeripheralBoundaryTests(unittest.TestCase):
    def test_deny_known_service_driver_and_preference_controls(self):
        examples = {
            "OS_SERVICE_CONTROL": ["Start-Service bthserv", "sc.exe config bthserv start= auto",
                                   "BluetoothUserService_abc"],
            "OS_PNP_MUTATION": ["pnputil.exe /restart-device USB\\RADIO",
                                "Disable-PnpDevice -InstanceId ID"],
            "OS_PERIPHERAL_PREFERENCE": ["PrintScreenKeyForSnippingEnabled",
                                         "BlockInput(True)"],
        }
        for reason, cases in examples.items():
            for case in cases:
                with self.subTest(case=case):
                    self.assertIn(reason, inspect_source(case))

    def test_allow_game_observation_and_readonly_service_language(self):
        self.assertEqual(inspect_source("passive PrintWindow; Get-Service bthserv; idle probe"), ())

    def test_scan_catches_new_adapter_outside_the_existing_capture_path(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "betterinstincts").mkdir()
            (root / "scripts").mkdir()
            (root / "scripts" / "new_adapter.py").write_text(
                "import subprocess\nsubprocess.run('pnputil.exe /remove-device ID')\n",
                encoding="utf-8",
            )
            self.assertIn(("scripts/new_adapter.py", "OS_PNP_MUTATION"), inspect_repository(root))

    def test_contract_explicitly_denies_windows_repairs(self):
        authority = json.loads((ROOT / "contracts/peripheral-authority.v1.json").read_text(encoding="utf-8"))
        self.assertEqual(authority["unknown_effect"], "DENY_UNTIL_CLASSIFIED")
        for effect in ("OS_BLUETOOTH_SERVICE", "OS_DRIVER_OR_ADAPTER", "OS_INPUT_PREFERENCE"):
            self.assertTrue(authority["effect_classes"][effect]["decision"].startswith("DENY"))

    def test_ontology_graph_owns_windows_peripheral_authority(self):
        graph = json.loads((ROOT / "contracts/ontology.v1.json").read_text(encoding="utf-8"))
        concept = graph["concepts"]["OS_PERIPHERAL_AUTHORITY"]
        self.assertEqual(concept["canonical_owner"], "contracts/peripheral-authority.v1.json")
        self.assertIn({"from": "CONTROL_PERMIT",
                       "predicate": "DOES_NOT_GRANT_OS_REPAIR_AUTHORITY",
                       "to": "OS_PERIPHERAL_AUTHORITY"}, graph["relations"])
        invariants = {x["id"]: x for x in graph["invariants"]}
        self.assertEqual(invariants["BI-ONT-025"]["term"],
                         "GAME_AGENT_MUST_NOT_MUTATE_WINDOWS_PERIPHERALS")

    def test_repository_source_boundary(self):
        self.assertEqual(inspect_repository(ROOT), [], "Game source must not operate Bluetooth/driver/preferences")


if __name__ == "__main__":
    unittest.main()
