"""P04 handoff remains executable, player-first and BI-002-bound."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class JudgmentHandoffTests(unittest.TestCase):
    def test_machine_handoff_has_local_game_owner_and_gate(self):
        data = json.loads((ROOT / "plans/active/BI-JUDGMENT-LEARNING-P04.execution.v1.json").read_text())
        self.assertEqual(data["schema"], "betterinstincts.p04-learning-handoff/v1")
        self.assertEqual(data["execution_owner"], "LOCAL_AGENT_RUNTIME")
        self.assertTrue(data["boundaries"]["operator_review_required_for_every_training_label"])
        self.assertTrue(data["boundaries"]["no_automatic_sims_actions_from_learning"])
        self.assertEqual(data["priority"], "BI-002_HUNGER_LIVE_CERT_REMAINS_PARENT")
        self.assertIn("python -m unittest tests.test_judgment_learning tests.test_listener_learning -v",
                      data["convergence"]["first_command"])
        self.assertEqual([x["lane_id"] for x in data["launch_order"]],
                         ["GATE-0", "GAME-1", "LEARN-1", "P08-1", "BI002-1"])
        self.assertEqual(data["launch_order"][3]["status"], "WAITING_GAME_1_AND_LEARN_1")

    def test_human_handoff_and_agent_router_preserve_proof_ceiling(self):
        handoff = (ROOT / "docs/handoff/BI-JUDGMENT-LEARNING-P04-2026-11-07.md").read_text()
        root = (ROOT / "AGENTS.md").read_text()
        for marker in ("P97", "P95", "Trifecta", "P04", "BI-002", "5 vanilla",
                       "operator", "ABSTAIN", "LOCAL_AGENT_RUNTIME"):
            self.assertIn(marker, handoff)
        self.assertIn("BI-JUDGMENT-LEARNING-P04-2026-11-07.md", root)
        self.assertIn("cannot", handoff.lower() + " cannot certify live from ci")


if __name__ == "__main__":
    unittest.main()
