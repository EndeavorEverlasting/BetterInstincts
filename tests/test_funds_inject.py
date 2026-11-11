"""P82 offline falsifiers for the P95 exact-funds host call stack.

These tests never perform screen input or certify installed Sims gameplay.
"""
import json
import math
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
    verify_funds_outcome,
)


class FundsInjectTests(unittest.TestCase):
    def test_contract_ea_exact_money_first(self):
        cfg = load_contract()
        seq = cfg["inject_sequence"]
        self.assertTrue(seq["mode_agnostic"])
        self.assertTrue(seq["never_force_mode_switch"])
        self.assertFalse(seq["require_live_mode"])
        self.assertEqual(seq["activate_testing_cheats"], "testingcheats true")
        self.assertEqual(seq["set_funds_template"], "money {amount}")
        self.assertEqual(seq["open_console_chord"], ["CTRL", "SHIFT", "C"])
        self.assertFalse(seq["auto_fallback"])
        self.assertEqual(seq["max_household_funds"], 9_999_999)
        self.assertEqual(cfg["version"], 3)

    def test_subsidy_triggers_only_below_threshold(self):
        self.assertTrue(needs_subsidy_prompt(38))
        self.assertTrue(needs_subsidy_prompt(99))
        self.assertFalse(needs_subsidy_prompt(100))
        self.assertFalse(needs_subsidy_prompt(1_000_000))

    def test_prompt_copy_matches_operator_voice(self):
        prompt = subsidy_prompt()
        self.assertEqual(prompt["title"], "HOUSEHOLD NOTICE")
        self.assertIn("decisions were made", prompt["body"])
        self.assertIn("Simolean federal bank", prompt["body"])

    def test_accept_in_build_mode_no_live_force(self):
        gate = evaluate_subsidy_gate(38, choice="accept_subsidy", game_mode="build")
        self.assertEqual(gate["state"], "SUBSIDY_ACCEPTED")
        plan = gate["inject"]
        self.assertEqual(plan["state"], "FUNDS_INJECT_PLAN_READY")
        steps = [s["step"] for s in plan["steps"]]
        self.assertNotIn("ENSURE_LIVE_MODE", steps)
        self.assertIn("PRESERVE_OPERATOR_MODE", steps)
        self.assertEqual(plan["steps"][2]["chord_label"], "Ctrl+Shift+C")
        self.assertEqual(steps_to_commands(plan), ["testingcheats true", "money 1000000"])
        self.assertEqual(plan["motherlode_count"], 0)

    def test_modes_plan_without_portrait_identity(self):
        for mode in ("live", "build", "buy", "unknown"):
            plan = plan_inject(amount=100000, funds_observed=1, game_mode=mode)
            self.assertEqual(plan["game_mode"], mode)
            self.assertNotIn("ENSURE_LIVE_MODE", [s["step"] for s in plan["steps"]])
            self.assertEqual(steps_to_commands(plan), ["testingcheats true", "money 100000"])
            self.assertNotIn("sim_id", plan)
            self.assertNotIn("motherlode", steps_to_commands(plan))

    def test_observation_required_before_exact_money(self):
        plan = plan_inject(amount=1_000_000, game_mode="live")
        self.assertEqual(plan["state"], "FUNDS_OBSERVATION_REQUIRED")
        self.assertEqual(plan["next_gate"], "OBSERVE_ACTIVE_HOUSEHOLD_FUNDS")
        self.assertEqual(plan["steps"], [])
        with self.assertRaisesRegex(FundsInjectError, "FUNDS_PLAN_NOT_EXECUTABLE"):
            steps_to_commands(plan)

    def test_already_richer_never_reduces_funds(self):
        plan = plan_inject(amount=1000, funds_observed=1001, game_mode="buy")
        self.assertEqual(plan["state"], "TARGET_ALREADY_MET")
        self.assertEqual(plan["remaining"], 0)
        self.assertEqual(plan["steps"], [])
        with self.assertRaises(FundsInjectError):
            steps_to_commands(plan)
        equal = plan_inject(amount=1000, funds_observed=1000)
        self.assertEqual(equal["state"], "TARGET_ALREADY_MET")

    def test_one_exact_command_even_from_non_round_balance(self):
        plan = plan_inject(amount=1_000_000, funds_observed=50038, game_mode="build")
        self.assertEqual(plan["remaining"], 949962)
        self.assertEqual(plan["motherlode_count"], 0)
        self.assertEqual(steps_to_commands(plan), ["testingcheats true", "money 1000000"])

    def test_amount_and_observation_bounds(self):
        bad = [-1, 0, 100.1, float("nan"), float("inf"), True, "123", 10_000_000]
        for target in bad:
            with self.subTest(target=target), self.assertRaises(FundsInjectError):
                plan_inject(amount=target, funds_observed=0)
        for observed in [-1, 1.1, float("nan"), float("inf"), False, "20", 10_000_000]:
            with self.subTest(observed=observed), self.assertRaises(FundsInjectError):
                plan_inject(amount=100, funds_observed=observed)
        self.assertEqual(
            steps_to_commands(plan_inject(amount=9_999_999, funds_observed=0)),
            ["testingcheats true", "money 9999999"],
        )

    def test_tampered_plan_cannot_dispatch_motherlode(self):
        plan = plan_inject(amount=100000, funds_observed=1)
        plan["steps"].append({"step": "ADD_FUNDS_CHUNK", "command": "motherlode"})
        with self.assertRaisesRegex(FundsInjectError, "FUNDS_COMMAND_STACK_UNSAFE"):
            steps_to_commands(plan)

    def test_player_priority_and_subsidy_decline(self):
        self.assertEqual(plan_inject(player_directed=True)["state"], "YIELD_TO_PLAYER")
        self.assertEqual(
            evaluate_subsidy_gate(38, player_directed=True)["state"],
            "YIELD_TO_PLAYER",
        )
        self.assertEqual(
            evaluate_subsidy_gate(38, choice="decline_subsidy")["state"],
            "SUBSIDY_DECLINED",
        )
        with self.assertRaises(FundsInjectError):
            evaluate_subsidy_gate(38, choice="maybe")

    def test_post_command_observation_requires_evidence(self):
        plan = plan_inject(amount=100000, funds_observed=10)
        unproven = verify_funds_outcome(plan, funds_after=100000)
        self.assertEqual(unproven["state"], "FUNDS_NOT_VERIFIED")
        self.assertFalse(unproven["auto_retry"])
        failed = verify_funds_outcome(plan, funds_after=90000, evidence_ref="sample-1")
        self.assertEqual(failed["state"], "FUNDS_NOT_VERIFIED")
        self.assertEqual(failed["next_gate"], "RECHECK_UI_WITH_PLAYER")
        attested = verify_funds_outcome(plan, funds_after=100000, evidence_ref="lab-hud-1")
        self.assertEqual(attested["state"], "TARGET_ATTESTED_BY_EXTERNAL_OBSERVATION")
        self.assertEqual(attested["next_gate"], "CONTINUE_HOST")
        self.assertIn("NOT_GAME_CERTIFICATION", attested["proof_ceiling"])

    def test_cli_source_has_no_blind_click_or_duplicate_cheats(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "funds_inject.py"
        source = script.read_text(encoding="utf-8")
        compile(source, str(script), "exec")
        self.assertNotIn("_click(250, 16)", source)
        self.assertNotIn("run_cmds.insert", source)
        self.assertIn("finally:", source)
        self.assertIn("CLOSE_CONSOLE_REQUIRES_SEPARATE_LOCAL_CERTIFICATION", source)
        self.assertIn("EXPLICIT_GAME_MODE_REQUIRED", source)

    def test_contract_json_roundtrip(self):
        raw = json.loads(
            (Path(__file__).resolve().parents[1] / "contracts" / "host-funds.v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(raw["version"], 3)
        self.assertFalse(raw["inject_sequence"]["auto_fallback"])
        self.assertEqual(raw["subsidy"]["boost_to"], 1000000)


if __name__ == "__main__":
    unittest.main()
