import unittest

from betterinstincts.progression_eval import (
    evaluate_case,
    evaluate_repo,
    evaluate_suite,
    load_contract,
    read_cases,
    ProgressionEvalError,
)


class ProgressionEvalTests(unittest.TestCase):
    def test_contract_loads(self):
        contract = load_contract()
        self.assertEqual(len(contract["vision_dimensions"]), 11)
        self.assertIn("scripts.progression_eval", contract["ci_required_substrings"])

    def test_all_fixture_expectations(self):
        result = evaluate_suite(read_cases())
        self.assertEqual(result["mismatches"], [], msg=result["mismatches"])
        self.assertGreaterEqual(result["total"], 10)

    def test_repo_floor_zero_product_high_scaffolding(self):
        report = evaluate_repo()
        self.assertEqual(report["verdict"], "SCAFFOLDING_AHEAD_OF_GAME")
        self.assertEqual(report["rates"]["product_progression_rate"], 0.0)
        self.assertGreater(report["rates"]["scaffolding_rate"], 0.8)
        self.assertGreater(report["rates"]["ci_game_gap"], 0.5)
        self.assertEqual(report["proof_ceiling"], "OFFLINE_REPO_METRICS_NOT_GAME_CERTIFICATION")
        self.assertEqual(report["current_gate"], "BI-002")

    def test_vision_dimensions_present(self):
        report = evaluate_repo()
        self.assertEqual(report["vision"]["missing_ids"], [])
        self.assertEqual(report["vision"]["rate"], 1.0)

    def test_promotion_fails_closed(self):
        case = next(c for c in read_cases()["cases"] if c["case_id"] == "promote_ci_as_certified")
        report = evaluate_case(case)
        self.assertEqual(report["verdict"], "BLOCKED")
        self.assertIn("PROMOTE_OFFLINE_CI_AS_GAME_CERTIFIED", report["blocked_by"])

    def test_partial_overlay_rate(self):
        case = next(c for c in read_cases()["cases"] if c["case_id"] == "partial_hunger_certified_overlay")
        report = evaluate_case(case)
        self.assertEqual(report["rates"]["product_progression_rate"], 0.1)
        self.assertTrue(report["product"]["hunger_trials"]["bi002_gate_closed"])

    def test_duplicate_case_ids_rejected(self):
        case = read_cases()["cases"][0]
        with self.assertRaises(ProgressionEvalError):
            evaluate_suite({"schema": "betterinstincts.progression-eval-suite/v1", "cases": [case, case]})


if __name__ == "__main__":
    unittest.main()
