"""P04 re-entry contract: never promote offline Mod Lab proof into game certification."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HandoffContractTests(unittest.TestCase):
    def test_dispatch_retains_active_game_gate_and_explicit_root(self):
        report = json.loads((ROOT / "plans/active/BI-MODLAB.dispatch.v1.json").read_text(encoding="utf-8"))
        self.assertEqual(report["schema_version"], "betterinstincts.p04.dispatch.v1")
        self.assertEqual(report["sprint"], "BI-MODLAB")
        self.assertEqual(report["lane"], "tooling")
        self.assertEqual(report["active_game_gate"], "BI-002")
        self.assertEqual(report["horizon_income_gate"], "BI-004")
        self.assertTrue(report["requires_operator_selected_mods_root"])
        self.assertIn("--mods-root", report["local_entry_command"])
        self.assertIn("GAME_ACCESS", report["game_lab_state"])
        self.assertEqual(report["game_observations"]["vanilla_trials"], 0)
        self.assertEqual(report["game_observations"]["modified_trials"], 0)
        self.assertIsNone(report["game_observations"]["game_patch"])

    def test_modlab_sprint_id_does_not_collide_with_horizon_stages(self):
        dispatch = json.loads((ROOT / "plans/active/BI-MODLAB.dispatch.v1.json").read_text(encoding="utf-8"))
        horizon = json.loads((ROOT / "plans/horizon.v1.json").read_text(encoding="utf-8"))
        stage_ids = {stage["id"] for stage in horizon["stages"]}
        self.assertNotIn(dispatch["sprint"], stage_ids)
        self.assertIn("BI-004", stage_ids)
        self.assertEqual(
            next(stage["title"] for stage in horizon["stages"] if stage["id"] == "BI-004"),
            "Steady autonomous income",
        )
        self.assertFalse((ROOT / "plans/active/BI-004.md").exists())
        self.assertFalse((ROOT / "plans/active/BI-004.dispatch.v1.json").exists())
        self.assertTrue((ROOT / "plans/active/BI-MODLAB.md").is_file())


if __name__ == "__main__":
    unittest.main()
