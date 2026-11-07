import unittest
from betterinstincts.host_eval import read_cases, evaluate_case, evaluate_suite, HostEvalError
from betterinstincts.host_stack import evaluate_turn

SIX = {k: .9 for k in ("hunger", "bladder", "energy", "hygiene", "fun", "social")}


class HostEvalTests(unittest.TestCase):
    def test_all_fixture_expectations(self):
        result = evaluate_suite(read_cases())
        self.assertEqual(result["mismatches"], [])
        self.assertGreaterEqual(result["total"], 14)

    def test_black_regression_fails_closed(self):
        case = next(c for c in read_cases()["cases"] if c["case_id"] == "black_viewport")
        result = evaluate_case(case)
        self.assertIn("BLACK_VIEWPORT_STILL_ACTIVE", result["blocked_by"])

    def test_six_whims_and_skill_deltas(self):
        case = next(c for c in read_cases()["cases"] if c["case_id"] == "six_whims_skill_delta")
        result = evaluate_case(case)
        self.assertEqual(result["whims"]["count"], 6)
        self.assertEqual(result["skills"]["deltas"]["cooking"], 1)
        self.assertEqual(evaluate_case(read_cases()["cases"][0])["whims"]["state"], "SENSOR_NOT_SUPPLIED")

    def test_invalid_need_measurement_rejected(self):
        case = read_cases()["cases"][0]
        case["needs"]["after"]["hunger"] = "green"
        with self.assertRaises(HostEvalError):
            evaluate_case(case)

    def test_duplicate_case_ids_rejected(self):
        case = read_cases()["cases"][0]
        with self.assertRaises(HostEvalError):
            evaluate_suite({"cases": [case, case]})

    def test_host_guard_against_player_busy_absent(self):
        for flag in ("player_directed", "already_busy", "sim_absent"):
            with self.subTest(flag=flag):
                result = evaluate_turn(SIX, **{flag: True})
                self.assertNotIn(result["next_gate"], ("LAB_SAVE_AS_BI_CONT_WHEN_AUTHORIZED", "EXECUTE_INSTINCTS_PLAN"))
                self.assertIsNone(result["instincts"]["next_action"])
                self.assertEqual(result["instincts"]["save_recommendation"]["state"], "HOLD_SAVE")

    def test_unknown_viewport_abstains(self):
        result = evaluate_turn(SIX, viewport={"state": "UNKNOWN"})
        self.assertEqual(result["next_gate"], "VERIFY_VIEWPORT_BEFORE_ACTION")


if __name__ == "__main__":
    unittest.main()
