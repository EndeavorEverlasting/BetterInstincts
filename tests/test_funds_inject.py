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
    plan_funds_recovery,
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
        self.assertEqual(cfg["version"], 4)

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
        self.assertEqual(raw["version"], 4)
        self.assertFalse(raw["inject_sequence"]["auto_fallback"])
        self.assertEqual(raw["subsidy"]["boost_to"], 1000000)


    def _noop_recovery(self, before=38, target=1_000_000, **opts):
        prior = plan_inject(amount=target, funds_observed=before, game_mode="build")
        defaults = dict(
            prior_plan=prior, funds_after=before,
            evidence_ref="hud:after-exact-1",
            prior_dispatch_ref="dispatch:exact-1",
            confirmed_noop=True,
        )
        defaults.update(opts)
        return plan_funds_recovery(**defaults)

    def test_recovery_is_opt_in_single_non_overshooting_command(self):
        plan = self._noop_recovery()
        self.assertEqual(plan["state"], "FUNDS_RECOVERY_PLAN_READY")
        self.assertEqual(plan["recovery_command"], "motherlode")
        self.assertEqual(plan["planned_delta"], 50_000)
        self.assertEqual(plan["game_mode"], "build")
        self.assertEqual(steps_to_commands(plan), ["testingcheats true", "motherlode"])
        self.assertFalse(plan["auto_retry"])
        self.assertEqual(len([s for s in plan["steps"] if s.get("step") == "ADD_FUNDS_CHUNK"]), 1)

    def test_recovery_kaching_if_motherlode_would_overshoot(self):
        plan = self._noop_recovery(before=100, target=1900)
        self.assertEqual(plan["recovery_command"], "kaching")
        self.assertEqual(plan["planned_delta"], 1000)
        self.assertEqual(steps_to_commands(plan), ["testingcheats true", "kaching"])
        self.assertLessEqual(plan["funds_observed"] + plan["planned_delta"], plan["target_funds"])

    def test_recovery_remainder_under_1000_denies_additive(self):
        plan = self._noop_recovery(before=123, target=999)
        self.assertEqual(plan["state"], "NO_EXACT_ADDITIVE_FALLBACK")
        self.assertEqual(plan["steps"], [])
        with self.assertRaisesRegex(FundsInjectError, "FUNDS_PLAN_NOT_EXECUTABLE"):
            steps_to_commands(plan)

    def test_recovery_requires_distinct_receipts_and_confirmed_settlement(self):
        for opts in (
            {"evidence_ref": ""},
            {"prior_dispatch_ref": ""},
            {"prior_dispatch_ref": "hud:after-exact-1"},
            {"prior_dispatch_ref": "bad ref"},
            {"evidence_ref": "bad ref"},
        ):
            with self.subTest(opts=opts):
                plan = self._noop_recovery(**opts)
                self.assertEqual(plan["state"], "RECOVERY_EVIDENCE_REQUIRED")
                self.assertEqual(plan["steps"], [])
        unconfirmed = self._noop_recovery(confirmed_noop=False)
        self.assertEqual(unconfirmed["state"], "RECOVERY_CONFIRMATION_REQUIRED")
        self.assertFalse(unconfirmed["auto_retry"])
        self.assertEqual(unconfirmed["steps"], [])

    def test_recovery_never_treats_different_balance_as_noop(self):
        increased = self._noop_recovery(funds_after=50_038)
        decreased = self._noop_recovery(funds_after=20)
        for plan in (increased, decreased):
            self.assertEqual(plan["state"], "REPLAN_FROM_NEW_OBSERVATION")
            self.assertEqual(plan["next_gate"], "REPLAN_EXACT_FROM_CURRENT_HUD")
            self.assertEqual(plan["steps"], [])

    def test_recovery_tamper_and_player_preemption_fail_closed(self):
        yielded = self._noop_recovery(player_directed=True)
        self.assertEqual(yielded["state"], "YIELD_TO_PLAYER")
        self.assertEqual(yielded["steps"], [])
        tampered = self._noop_recovery()
        tampered["steps"].append({"step": "ADD_FUNDS_CHUNK", "command": "motherlode"})
        with self.assertRaisesRegex(FundsInjectError, "FUNDS_COMMAND_STACK_UNSAFE"):
            steps_to_commands(tampered)
        wrong_delta = self._noop_recovery()
        wrong_delta["planned_delta"] = 100_000
        with self.assertRaisesRegex(FundsInjectError, "FUNDS_RECOVERY_PLAN_UNSAFE"):
            steps_to_commands(wrong_delta)

    def test_recovery_requires_an_exact_predecessor_not_an_additive_chain(self):
        prior = self._noop_recovery()
        with self.assertRaisesRegex(FundsInjectError, "FUNDS_RECOVERY_PLAN_UNSAFE|FUNDS_COMMAND_STACK_UNSAFE|EXACT_FUNDS_PREDECESSOR_REQUIRED"):
            plan_funds_recovery(
                prior_plan=prior, funds_after=50_038,
                prior_dispatch_ref="dispatch:alternate-1",
                evidence_ref="hud:after-alternate-1", confirmed_noop=True,
            )

    def test_progress_is_not_exact_target_attestation(self):
        plan = self._noop_recovery(before=100, target=100_100)
        outcome = verify_funds_outcome(plan, funds_after=50_100, evidence_ref="hud:after-additive-1")
        self.assertEqual(outcome["state"], "FUNDS_PROGRESS_ATTESTED_BY_EXTERNAL_OBSERVATION")
        self.assertEqual(outcome["next_gate"], "REPLAN_FROM_CURRENT_HUD")
        self.assertFalse(outcome["auto_retry"])
        self.assertIn("NOT_GAME_CERTIFICATION", outcome["proof_ceiling"])

    def test_offline_recovery_cli_and_missing_session_denial(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from scripts.funds_inject import main

        base = [
            "recover", "--amount", "1000000", "--funds-before", "38",
            "--funds-after", "38", "--game-mode", "live",
            "--evidence-ref", "hud:after-exact-1",
            "--prior-dispatch-ref", "dispatch:exact-1", "--confirmed-noop",
        ]
        out = StringIO()
        with redirect_stdout(out):
            code = main(base)
        self.assertEqual(code, 0)
        payload = json.loads(out.getvalue())
        self.assertFalse(payload["execute"])
        self.assertEqual(payload["plan"]["recovery_command"], "motherlode")
        blocked = StringIO()
        with redirect_stdout(blocked):
            code = main(base + ["--execute"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(blocked.getvalue())["state"], "BLOCKED")

    def test_post_effect_unexpected_delta_stops_instead_of_certifying_success(self):
        exact = plan_inject(amount=100_000, funds_observed=38)
        overshot = verify_funds_outcome(exact, funds_after=100_001, evidence_ref="hud:unexpected-exact-1")
        self.assertEqual(overshot["state"], "FUNDS_UNEXPECTED_DELTA")
        self.assertEqual(overshot["next_gate"], "STOP_AND_RECONCILE_UNEXPECTED_FUNDS")
        fallback = self._noop_recovery(before=100, target=100_100)
        for reported in (99, 50_101, 110_000):
            with self.subTest(reported=reported):
                unexpected = verify_funds_outcome(
                    fallback, funds_after=reported, evidence_ref="hud:unexpected-additive-1")
                self.assertEqual(unexpected["state"], "FUNDS_UNEXPECTED_DELTA")
                self.assertFalse(unexpected["auto_retry"])

    def test_recovery_outcome_evidence_must_be_new(self):
        plan = self._noop_recovery(before=100, target=100_100)
        with self.assertRaisesRegex(FundsInjectError, "RECOVERY_HUD_EVIDENCE_MUST_BE_FRESH_AND_DISTINCT"):
            verify_funds_outcome(plan, funds_after=50_100, evidence_ref="hud:after-exact-1")
        with self.assertRaisesRegex(FundsInjectError, "RECOVERY_HUD_EVIDENCE_MUST_BE_FRESH_AND_DISTINCT"):
            verify_funds_outcome(plan, funds_after=50_100, evidence_ref="dispatch:exact-1")

    def test_cli_verify_recovery_reports_progress_not_exact_success(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from scripts.funds_inject import main

        argv = [
            "verify", "--route", "recovery", "--amount", "100100",
            "--funds-before", "100", "--funds-after-exact", "100",
            "--funds-after", "50100", "--no-op-evidence-ref", "hud:after-exact-1",
            "--prior-dispatch-ref", "dispatch:exact-1",
            "--evidence-ref", "hud:after-additive-1", "--confirmed-noop",
        ]
        buf = StringIO()
        with redirect_stdout(buf):
            code = main(argv)
        self.assertEqual(code, 0)
        self.assertEqual(
            json.loads(buf.getvalue())["state"],
            "FUNDS_PROGRESS_ATTESTED_BY_EXTERNAL_OBSERVATION",
        )
        denied = StringIO()
        with redirect_stdout(denied):
            code = main(argv[:argv.index("--funds-after-exact")] + argv[argv.index("--funds-after"):])
        self.assertEqual(code, 2)
        self.assertIn("POST_EXACT_FUNDS_OBSERVATION_REQUIRED", denied.getvalue())

    def test_windows_host_process_identity_and_console_fallback_contract(self):
        cfg = load_contract()
        self.assertTrue(cfg["observed_noop_recovery"]["explicit_opt_in"])
        self.assertTrue(cfg["observed_noop_recovery"]["one_effect_per_invocation"])
        self.assertFalse(cfg["inject_sequence"]["auto_fallback"])
        self.assertEqual(cfg["runtime_compatibility"]["supported_host_executor"], "windows")
        self.assertIn("steam", cfg["runtime_compatibility"]["known_distribution_channels"])
        script = (Path(__file__).resolve().parents[1] / "scripts" / "funds_inject.py").read_text(encoding="utf-8")
        self.assertIn("foreground_process_name", script)
        self.assertIn("OPERATOR_CONSOLE_FOCUS_ATTESTATION_REQUIRED", script)
        self.assertIn("ts4_x64.exe", script)
        self.assertNotIn("SteamLibrary", script)


if __name__ == "__main__":
    unittest.main()
