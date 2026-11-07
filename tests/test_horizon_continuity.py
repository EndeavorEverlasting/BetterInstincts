import unittest

from betterinstincts.horizon_continuity import ContinuityError, load_continuity, validate
from betterinstincts.funds_inject import load_contract as load_funds


class HorizonContinuityTests(unittest.TestCase):
    def test_continuity_contract_passes(self):
        report = validate()
        self.assertEqual(report["state"], "PASS")
        self.assertEqual(report["selected_investigation"], "BI-002 GAME-1")
        self.assertIn("FUNDS_PREFERRED_NON_MOTHERLODE", report["open_items"])

    def test_parent_prompt_stack_complete(self):
        prompts = load_continuity()["parent_prompts"]
        self.assertIn("community-native", prompts["north_star"])
        self.assertEqual(len(prompts["non_negotiables"]), 5)
        self.assertIn("continuity_opener", prompts)
        self.assertIn("CHANGED | PROVED | NEXT", prompts["continuity_opener"])

    def test_funds_preferred_path_open_interim_motherlode(self):
        funds = load_funds()
        seq = funds["inject_sequence"]
        self.assertEqual(seq["preferred_path_status"], "OPEN")
        self.assertEqual(seq["preferred_path_id"], "FUNDS_PREFERRED_NON_MOTHERLODE")
        self.assertEqual(seq["durable_additive_command"], "motherlode")

    def test_corrupt_selection_fails(self):
        data = load_continuity()
        data["selected_investigation"]["name"] = "WRONG"
        with self.assertRaises(ContinuityError):
            validate(data)


if __name__ == "__main__":
    unittest.main()
