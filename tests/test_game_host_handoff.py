"""P04 dispatch contract keeps live Sims certification separate from merged code."""
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "plans/active/BI-GAME-HOST.dispatch.v1.json"
HANDOFF = ROOT / "plans/active/BI-GAME-HOST.HANDOFF.md"
RUNBOOK = ROOT / "docs/GAME_HOST.md"


class GameHostDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = json.loads(DISPATCH.read_text(encoding="utf-8"))
        cls.text = HANDOFF.read_text(encoding="utf-8")
        cls.runbook = RUNBOOK.read_text(encoding="utf-8")

    def test_parent_hunger_stays_active_and_uncertified(self):
        self.assertEqual(self.plan["parent"], "BI-002")
        self.assertEqual(self.plan["state"], "ACTIVE_GAME_HOST_UNPROVEN")
        self.assertEqual(self.plan["parent_gate"], "HUNGER_LIVE_CERTIFIED")
        self.assertIn("BLOCKED_LOCAL_GAME_ACCESS", self.text)
        self.assertIn("BI-MODLAB", self.text)
        self.assertIn("income", self.text.lower())

    def test_all_lanes_have_host_not_just_provider(self):
        lane_ids = [lane["lane_id"] for lane in self.plan["lanes"]]
        self.assertEqual(len(lane_ids), len(set(lane_ids)))
        self.assertEqual(
            set(lane_ids),
            {"REPO-IMPLEMENTATION", "CI-REGRESSION", "GAME-BOOT",
             "TUNING-READONLY", "HUNGER-LIVE", "SENSOR-BRIDGE", "MAINTAINER-REVIEW"},
        )
        allowed = {"CURRENT_CHAT_RUNTIME", "LOCAL_AGENT_RUNTIME", "CI_OR_REMOTE_RUNNER",
                   "OPERATOR_OR_PHYSICAL_RUNTIME", "UNKNOWN_RUNTIME"}
        for lane in self.plan["lanes"]:
            with self.subTest(lane=lane["lane_id"]):
                self.assertIn(lane["execution_environment"], allowed)
                for field in ("dependencies", "provider_access", "required_capabilities",
                              "owned_mutation_surfaces", "forbidden_surfaces", "execution_adapter",
                              "launch_action", "expected_artifact", "validation",
                              "convergence_owner", "status", "proof_ceiling", "evidence_inputs"):
                    self.assertIn(field, lane)
                self.assertTrue(set(lane["dependencies"]).issubset(set(lane_ids)))

    def test_disposable_game_local_gate_and_parallelism_are_not_faked(self):
        lanes = {x["lane_id"]: x for x in self.plan["lanes"]}
        self.assertEqual(lanes["GAME-BOOT"]["status"], "WAITING_FOR_LOCAL_GAME")
        self.assertEqual(lanes["TUNING-READONLY"]["status"], "WAITING_FOR_LOCAL_GAME")
        self.assertEqual(lanes["HUNGER-LIVE"]["dependencies"],
                         ["GAME-BOOT", "TUNING-READONLY"])
        self.assertEqual(lanes["MAINTAINER-REVIEW"]["dependencies"], ["HUNGER-LIVE"])
        self.assertEqual(lanes["GAME-BOOT"]["execution_environment"], "LOCAL_AGENT_RUNTIME")
        self.assertEqual(self.plan["parallelism"]["actual_parallel_workers_launched"], 0)
        self.assertFalse(self.plan["parallelism"]["observed_parallelism"])
        self.assertIn("UNPROVEN", self.plan["parallelism"]["status"])
        self.assertIn("NOT_INSTALLED", self.plan["generic_moonwake_dispatch_runner"])

    def test_proven_ci_and_unproven_live_are_distinct(self):
        lanes = {x["lane_id"]: x for x in self.plan["lanes"]}
        self.assertEqual(lanes["REPO-IMPLEMENTATION"]["status"], "MERGED")
        self.assertEqual(lanes["CI-REGRESSION"]["status"], "SUCCESS")
        self.assertEqual(self.plan["ci"]["conclusion"], "success")
        self.assertEqual(lanes["SENSOR-BRIDGE"]["status"], "WAITING")
        self.assertNotEqual(lanes["HUNGER-LIVE"]["status"], "SUCCESS")
        self.assertIn("P08", self.text)
        self.assertIn("P82", self.text)
        self.assertIn("P07", self.text)
        self.assertIn("P04", self.text)

    def test_runbook_keeps_cas_focus_caveat_and_click_ceiling(self):
        # First real boot: minimized windows and focus-steal must not be promoted to Live Mode.
        self.assertIn("CLICK_DISPATCH_ONLY", self.runbook)
        self.assertIn("minimized", self.runbook.lower())
        self.assertIn("Live Mode", self.runbook)
        self.assertIn("never uses Resume", self.runbook)


if __name__ == "__main__":
    unittest.main()
