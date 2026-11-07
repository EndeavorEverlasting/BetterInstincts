import json
import unittest
from pathlib import Path

from betterinstincts.decision_eval import (
    DecisionEvalError,
    get_prompt,
    load_catalog,
    measure_need_deltas,
    recommend,
)
from betterinstincts.host_stack import evaluate_turn

SIX = {n: 0.9 for n in ("hunger", "bladder", "energy", "hygiene", "fun", "social")}
CRITICAL = {**SIX, "energy": 0.08, "hygiene": 0.08, "social": 0.15}


class DecisionEvalTests(unittest.TestCase):
    def test_catalog_loads_and_lists_rock_prompt(self):
        cfg = load_catalog()
        prompt = get_prompt("school.geology.rock_collection", cfg)
        self.assertEqual(prompt["title"], "ROCK COLLECTION")
        self.assertGreaterEqual(len(prompt["options"]), 2)

    def test_critical_needs_prefer_no_stealing(self):
        result = recommend("school.geology.rock_collection", CRITICAL)
        self.assertEqual(result.recommended_option_id, "no_stealing_today")
        self.assertTrue(result.needs_critical)
        ids = [o.option_id for o in result.ranked]
        self.assertLess(ids.index("no_stealing_today"), ids.index("try_to_take_a_rock"))

    def test_join_vs_send_alone_prefers_home_when_flagged(self):
        result = recommend(
            "school.attend.join_or_send_alone",
            CRITICAL,
            prefer_home_control=True,
        )
        self.assertEqual(result.recommended_option_id, "send_alone")

    def test_need_deltas_measure_influence(self):
        before = {**SIX, "hygiene": 0.1, "energy": 0.1}
        after = {**SIX, "hygiene": 0.8, "energy": 0.8}
        report = measure_need_deltas(before, after, host_action="wash_then_sleep")
        self.assertIn("hygiene", report["improved"])
        self.assertIn("energy", report["improved"])
        self.assertTrue(report["net_sum"] > 0)
        self.assertTrue(report["all_green_after"])

    def test_host_stack_decision_outranks_instincts_gate(self):
        out = evaluate_turn(
            CRITICAL,
            available_objects=("toilet", "sink", "phone"),
            prompt_id="school.geology.rock_collection",
            capture_ref="capture:rock-test",
        )
        self.assertEqual(out["next_gate"], "RESOLVE_DECISION_PROMPT")
        self.assertEqual(out["decision"]["recommended_option_id"], "no_stealing_today")
        self.assertEqual(out["instincts"]["next_action"], "wash")

    def test_unknown_prompt_fails_closed(self):
        with self.assertRaises(DecisionEvalError):
            recommend("school.unknown.prompt", SIX)

    def test_cli_script_present(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "decision_eval.py"
        compile(script.read_text(encoding="utf-8"), str(script), "exec")


if __name__ == "__main__":
    unittest.main()
