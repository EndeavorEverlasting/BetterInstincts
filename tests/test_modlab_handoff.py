"""P04 re-entry contract: never promote offline Mod Lab proof into game certification."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HandoffContractTests(unittest.TestCase):
    def test_dispatch_retains_active_game_gate_and_explicit_root(self):
        report = json.loads((ROOT / "plans/active/BI-004.dispatch.v1.json").read_text(encoding="utf-8"))
        self.assertEqual(report["schema_version"], "betterinstincts.p04.dispatch.v1")
        self.assertEqual(report["active_game_gate"], "BI-002")
        self.assertTrue(report["requires_operator_selected_mods_root"])
        self.assertIn("--mods-root", report["local_entry_command"])
        self.assertIn("GAME_ACCESS", report["game_lab_state"])
        self.assertEqual(report["game_observations"]["vanilla_trials"], 0)
        self.assertEqual(report["game_observations"]["modified_trials"], 0)
        self.assertIsNone(report["game_observations"]["game_patch"])


if __name__ == "__main__":
    unittest.main()
