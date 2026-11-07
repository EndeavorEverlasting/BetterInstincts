import json
import unittest
from pathlib import Path

from betterinstincts.funds_inject import (
    FundsInjectError,
    evaluate_subsidy_gate,
    load_contract,
    needs_subsidy_prompt,
    plan_inject,
    steps_to_commands,
    subsidy_prompt,
)


class FundsInjectTests(unittest.TestCase):
    def test_contract_mode_agnostic(self):
        cfg = load_contract()
        seq = cfg["inject_sequence"]
        self.assertTrue(seq["mode_agnostic"])
        self.assertTrue(seq["never_force_mode_switch"])
        self.assertFalse(seq["require_live_mode"])
        self.assertEqual(seq["activate_testing_cheats"], "testingcheats enabled true")
        self.assertEqual(seq["open_console_chord"], ["CTRL", "SHIFT", "C"])

    def test_under_100_requires_prompt(self):
        self.assertTrue(needs_subsidy_prompt(38))
        self.assertTrue(needs_subsidy_prompt(99))
        self.assertFalse(needs_subsidy_prompt(100))
        self.assertFalse(needs_subsidy_prompt(1000000))

    def test_prompt_copy_matches_operator_voice(self):
        prompt = subsidy_prompt()
        self.assertEqual(prompt["title"], "HOUSEHOLD NOTICE")
        self.assertIn("decisions were made", prompt["body"])
        self.assertIn("Simolean federal bank", prompt["body"])

    def test_accept_in_build_mode_no_live_force(self):
        gate = evaluate_subsidy_gate(38, choice="accept_subsidy", game_mode="build")
        self.assertEqual(gate["state"], "SUBSIDY_ACCEPTED")
        self.assertEqual(gate["game_mode"], "build")
        plan = gate["inject"]
        self.assertTrue(plan["mode_agnostic"])
        steps = [s["step"] for s in plan["steps"]]
        self.assertNotIn("ENSURE_LIVE_MODE", steps)
        self.assertIn("PRESERVE_OPERATOR_MODE", steps)
        self.assertEqual(plan["steps"][2]["chord_label"], "Ctrl+Shift+C")
        cmds = steps_to_commands(plan)
        self.assertEqual(cmds[0], "testingcheats enabled true")
        self.assertIn("motherlode", cmds)

    def test_live_and_buy_modes_accepted(self):
        for mode in ("live", "buy", "unknown"):
            plan = plan_inject(amount=100000, funds_observed=0, game_mode=mode)
            self.assertEqual(plan["game_mode"], mode)
            self.assertNotIn("ENSURE_LIVE_MODE", [s["step"] for s in plan["steps"]])

    def test_remaining_chunks_when_funds_known(self):
        # Already have ~50k toward 1M → fewer motherlodes than a cold start.
        plan = plan_inject(amount=1000000, funds_observed=50038, game_mode="build")
        self.assertEqual(plan["motherlode_count"], 19)
        cold = plan_inject(amount=1000000, funds_observed=0, game_mode="build")
        self.assertEqual(cold["motherlode_count"], 20)

    def test_decline_holds(self):
        gate = evaluate_subsidy_gate(38, choice="decline_subsidy", game_mode="build")
        self.assertEqual(gate["state"], "SUBSIDY_DECLINED")

    def test_unknown_choice_fails_closed(self):
        with self.assertRaises(FundsInjectError):
            evaluate_subsidy_gate(38, choice="maybe")

    def test_cli_script_compiles(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "funds_inject.py"
        compile(script.read_text(encoding="utf-8"), str(script), "exec")

    def test_contract_json_roundtrip(self):
        raw = json.loads(
            (Path(__file__).resolve().parents[1] / "contracts" / "host-funds.v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(raw["version"], 2)
        self.assertEqual(raw["subsidy"]["boost_to"], 1000000)


if __name__ == "__main__":
    unittest.main()
