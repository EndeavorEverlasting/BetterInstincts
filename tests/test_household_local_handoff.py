"""P04 local Windows handoff structure and proof-ceiling guards (offline only)."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "plans/active/BI-HOUSEHOLD-SKILL-LOCAL-P04.dispatch.v1.json"
HANDOFF = ROOT / "docs/handoff/BI-HOUSEHOLD-SKILL-LOCAL-P04-2026-11-09.md"


class HouseholdLocalHandoffTests(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_local_not_launched_and_runtime_partition(self):
        self.assertEqual(self.cfg["schema"], "betterinstincts.p04-local-runtime-handoff/v1")
        self.assertIn("NOT_LAUNCHED", self.cfg["status"])
        self.assertEqual(self.cfg["runtime_partition"]["host"], "LOCAL_AGENT_RUNTIME")
        self.assertIn("SINGLE_SCREEN_OWNER", self.cfg["runtime_partition"]["parallel_execution"])
        self.assertEqual(self.cfg["handoff"], HANDOFF.relative_to(ROOT).as_posix())

    def test_dependencies_are_ordered_and_each_lane_has_real_gate(self):
        lanes = self.cfg["lanes"]
        ids = [row["lane_id"] for row in lanes]
        self.assertEqual(ids, self.cfg["launch_order"])
        self.assertEqual(len(ids), len(set(ids)))
        for index, lane in enumerate(lanes):
            self.assertEqual(lane["execution_environment"], "LOCAL_AGENT_RUNTIME")
            self.assertTrue(lane["launch_action"])
            self.assertTrue(lane["gate"])
            self.assertTrue(lane["receipt"].startswith("dist/game-host/household-skill-cert/"))
            self.assertTrue(all(dep in ids[:index] for dep in lane["dependencies"]))
            if index:
                self.assertIn(ids[index - 1], lane["dependencies"])
            self.assertIn("proof_ceiling", lane)
        self.assertEqual(lanes[0]["mutation_scope"], "READ_ONLY_GIT_AND_PATH_INSPECTION")

    def test_observer_gate_must_precede_any_live_skill_mutation(self):
        ids = self.cfg["launch_order"]
        self.assertLess(ids.index("LOCAL-03-OBSERVER-SAFETY"), ids.index("LOCAL-04-P08-CANARY"))
        self.assertLess(ids.index("LOCAL-04-P08-CANARY"), ids.index("LOCAL-05-P08-REGRESSION"))
        self.assertIn("per-cell", self.cfg["lanes"][3]["launch_action"])
        self.assertIn("DISPATCHED", self.cfg["lanes"][5]["launch_action"])
        raw = HANDOFF.read_text(encoding="utf-8")
        self.assertIn("NO_SKILL_INPUT", raw)
        self.assertIn("Do not run the bulk household", raw)
        self.assertIn("P08_BLOCKED_PER_CELL_SENSOR", raw)

    def test_protection_and_private_artifact_boundary(self):
        invariants = set(self.cfg["global_invariants"])
        for item in ("PLAYER_FIRST", "DISPOSABLE_SAVE_ONLY", "OFFLINE_SIMS_ONLY",
                     "NO_NEW_HOUSEHOLD_MEMBERS", "NO_PARALLEL_GAME_INPUT",
                     "NO_DETACHED_SKILL_WORKER", "NO_GAME_PASS_FROM_CHEAT_TEXT",
                     "NO_UNAPPROVED_CURSOR_USER_RULE_CHANGES"):
            self.assertIn(item, invariants)
        self.assertIn("dist", self.cfg["artifacts_are_local_private"])
        self.assertEqual(self.cfg["canonical_paths"]["canonical_owner"],
                         "contracts/workstation-paths.v1.json")


if __name__ == "__main__":
    unittest.main()
