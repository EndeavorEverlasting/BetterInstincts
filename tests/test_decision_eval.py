import json
import unittest
from pathlib import Path

from betterinstincts.decision_eval import (
    DecisionEvalError,
    _forced_option,
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

    def test_host_work_makes_send_alone_mandatory_even_with_green_needs(self):
        result = recommend("school.attend.join_or_send_alone", SIX, host_work_active=True)
        self.assertEqual(result.recommended_option_id, "send_alone")
        flagged = recommend("school.attend.join_or_send_alone", SIX, flags=("host_work_active",))
        self.assertEqual(flagged.recommended_option_id, "send_alone")
        self.assertIn("host_work_active", get_prompt("school.attend.join_or_send_alone")["force_send_alone_when"])

    def test_cas_continue_needs_consent_otherwise_escape_cancel(self):
        pid = "cas.servo.create_continue_vs_escape_cancel"
        self.assertEqual(recommend(pid, SIX).recommended_option_id, "escape_cancel")
        # No consent flag -> catalog hard gate fires; with consent it does not.
        prompt = get_prompt(pid)
        self.assertEqual(_forced_option(prompt, set()), "escape_cancel")
        self.assertIsNone(_forced_option(prompt, {"new_servo_consent"}))
        # Even with consent, an explicit Escape-cancel request wins.
        forced = recommend(pid, SIX, flags=("new_servo_consent", "escape_cancel_requested"))
        self.assertEqual(forced.recommended_option_id, "escape_cancel")
        # Escape-cancel requested without consent also cancels.
        self.assertEqual(
            recommend(pid, SIX, flags=("escape_cancel_requested",)).recommended_option_id,
            "escape_cancel",
        )

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
