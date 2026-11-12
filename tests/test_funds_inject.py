"""P82 offline falsifiers for the P95 exact-funds host call stack.

These tests never perform screen input or certify installed Sims gameplay.
"""
import json
import math
import unittest
from contextlib import contextmanager, redirect_stdout
from io import StringIO
from tempfile import TemporaryDirectory
from unittest.mock import patch
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
        self.assertEqual(cfg["version"], 5)

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
        self.assertEqual(raw["version"], 5)
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


    def test_fallback_selection_is_order_independent(self):
        cfg = load_contract()
        # JSON object order is not a priority rule. kaching first must not win.
        cfg["observed_noop_recovery"]["additive_commands"] = {
            "kaching": 1000, "motherlode": 50000,
        }
        prior = plan_inject(amount=100_000, funds_observed=38, game_mode="live")
        plan = plan_funds_recovery(
            prior_plan=prior, funds_after=38,
            prior_dispatch_ref="dispatch:exact-example-1",
            evidence_ref="hud:post-exact-1", confirmed_noop=True, cfg=cfg,
        )
        self.assertEqual(plan["recovery_command"], "motherlode")
        self.assertEqual(steps_to_commands(plan), ["testingcheats true", "motherlode"])

    @staticmethod
    @contextmanager
    def _admitted_host_lease(*_args, **_kwargs):
        yield lambda: {"screen_control_allowed": True,
                       "foreground_process": {"is_sims": True}}

    def test_recovery_rejects_chord_before_any_input(self):
        from scripts import funds_inject as host
        plan = self._noop_recovery()
        with patch.object(host.sys, "platform", "win32"), \
             patch.object(host, "_open_console_chord") as chord, \
             patch.object(host, "_type_text") as typed:
            with self.assertRaisesRegex(host.GateError, "RECOVERY_REQUIRES_READY_CONSOLE_NO_TOGGLE"):
                host._execute_plan(plan, process_id=123, session_id="session",
                                   console_open_method="chord", console_ready=False)
            chord.assert_not_called()
            typed.assert_not_called()

    def test_host_identity_behavior_denies_wrong_pid_and_executable(self):
        from betterinstincts.player_presence import PresenceProbe
        from scripts import funds_inject as host
        plan = self._noop_recovery()
        for seen_pid, executable in ((999, "TS4_x64.exe"),
                                     (123, "notepad.exe")):
            probe = PresenceProbe(
                foreground_is_sims=True, cursor_in_client=True,
                probe_ok=True, last_input_age_ms=25_000,
                foreground_process_id=seen_pid,
                foreground_process_name=executable,
            )
            with self.subTest(pid=seen_pid, executable=executable), \
                 patch.object(host.sys, "platform", "win32"), \
                 patch("betterinstincts.screen_admit.admitted_screen_lease",
                       self._admitted_host_lease), \
                 patch("betterinstincts.host_listener.status",
                       return_value={"state": "ACTIVE"}), \
                 patch("betterinstincts.player_presence.probe_windows",
                       return_value=probe), \
                 patch.object(host, "_type_text") as typed, \
                 patch.object(host, "_tap") as enter, \
                 patch.object(host, "_open_console_chord") as chord:
                with self.assertRaisesRegex(host.GateError, "GAME_FOREGROUND_OR_SESSION_LOST"):
                    host._execute_plan(
                        plan, process_id=123, session_id="session",
                        console_open_method="operator-ready", console_ready=True,
                    )
                typed.assert_not_called()
                enter.assert_not_called()
                chord.assert_not_called()

    def test_operator_ready_dispatch_skips_focus_chord_and_binds_pid(self):
        from betterinstincts.player_presence import PresenceProbe
        from scripts import funds_inject as host
        probe = PresenceProbe(
            foreground_is_sims=True, cursor_in_client=True,
            probe_ok=True, last_input_age_ms=25_000,
            foreground_process_id=123, foreground_process_name="TS4_x64.exe",
        )
        plan = self._noop_recovery()
        observed_lease = {}
        @contextmanager
        def inspect_lease(*args, **kwargs):
            observed_lease.update(kwargs)
            yield lambda: {"screen_control_allowed": True,
                           "foreground_process": {"is_sims": True}}
        with patch.object(host.sys, "platform", "win32"), \
             patch("betterinstincts.screen_admit.admitted_screen_lease",
                   inspect_lease), \
             patch("betterinstincts.host_listener.status",
                   return_value={"state": "ACTIVE"}), \
             patch("betterinstincts.player_presence.probe_windows",
                   return_value=probe), \
             patch.object(host, "_type_text") as typed, \
             patch.object(host, "_tap") as enter, \
             patch.object(host, "_open_console_chord") as chord, \
             patch.object(host.time, "sleep", return_value=None):
            result = host._execute_plan(
                plan, process_id=123, session_id="session",
                console_open_method="operator-ready", console_ready=True,
                before_input=lambda: "dist/game-host/funds-recovery-claims/claimed.json",
            )
            self.assertEqual(result["process_id"], 123)
            self.assertEqual(result["commands"], ["testingcheats true", "motherlode"])
            self.assertEqual(typed.call_count, 2)
            self.assertEqual(enter.call_count, 2)
            self.assertEqual(result["open_console"], "OPERATOR_ATTESTED_READY_CONSOLE")
            self.assertEqual(result["recovery_claim"],
                             "dist/game-host/funds-recovery-claims/claimed.json")
            self.assertIsNone(observed_lease["focus_fn"])
            chord.assert_not_called()


    def test_unexpected_adapter_failure_after_input_is_unknown_not_blocked(self):
        from betterinstincts.player_presence import PresenceProbe
        from scripts import funds_inject as host
        probe = PresenceProbe(
            foreground_is_sims=True, cursor_in_client=True,
            probe_ok=True, last_input_age_ms=30_000,
            foreground_process_id=123, foreground_process_name="TS4_x64.exe",
        )
        plan = self._noop_recovery()
        with patch.object(host.sys, "platform", "win32"), \
             patch("betterinstincts.screen_admit.admitted_screen_lease",
                   self._admitted_host_lease), \
             patch("betterinstincts.host_listener.status",
                   return_value={"state": "ACTIVE"}), \
             patch("betterinstincts.player_presence.probe_windows",
                   return_value=probe), \
             patch.object(host, "_type_text",
                          side_effect=[None, RuntimeError("input-broken")]), \
             patch.object(host, "_tap"), \
             patch.object(host.time, "sleep", return_value=None):
            with self.assertRaises(host.DispatchUncertain) as caught:
                host._execute_plan(
                    plan, process_id=123, session_id="session",
                    console_open_method="operator-ready", console_ready=True,
                )
            self.assertEqual(caught.exception.commands_sent, ["testingcheats true"])
            self.assertIn("INPUT_EFFECT_MAY_HAVE_OCCURRED", str(caught.exception))

    def test_real_receipt_binding_and_single_use_claim(self):
        from scripts import funds_inject as host
        prior = plan_inject(amount=1_000_000, funds_observed=38, game_mode="live")
        dispatch = "dispatch:" + "a" * 32
        plan = plan_funds_recovery(
            prior_plan=prior, funds_after=38,
            prior_dispatch_ref=dispatch, evidence_ref="hud:post-exact",
            confirmed_noop=True,
        )
        with TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(host, "ROOT", root), \
                 patch.object(host, "OUTPUT", root / "dist" / "game-host"):
                filepath = host._reserve_receipt(
                    Path("dist/game-host/exact-001.json"), execute=True,
                )
                expected_live = {
                    "state": "FUNDS_INJECT_DISPATCHED_NOT_VERIFIED",
                    "dispatch_ref": dispatch,
                    "commands": ["testingcheats true", "money 1000000"],
                    "target_funds": 1_000_000,
                    "funds_before_reported": 38,
                    "game_mode": "live",
                    "process_id": 123,
                    "session_id": "session",
                }
                host._write_receipt(filepath, {"execute": True, "live": expected_live})
                self.assertEqual(
                    host._require_exact_predecessor(
                        filepath, plan, process_id=123, session_id="session"),
                    expected_live,
                )
                for wrong_pid, wrong_session in ((999, "session"), (123, "foreign")):
                    with self.assertRaisesRegex(host.GateError, "PRIOR_EXACT_DISPATCH_MISMATCH"):
                        host._require_exact_predecessor(
                            filepath, plan, process_id=wrong_pid,
                            session_id=wrong_session,
                        )
                plan["prior_dispatch_ref"] = "dispatch:" + "b" * 32
                with self.assertRaisesRegex(host.GateError, "PRIOR_EXACT_DISPATCH_MISMATCH"):
                    host._require_exact_predecessor(
                        filepath, plan, process_id=123, session_id="session")
                claim = host._claim_recovery_once(dispatch)
                self.assertIn("funds-recovery-claims", claim)
                with self.assertRaisesRegex(host.GateError, "RECOVERY_ALREADY_CLAIMED_NO_REPLAY"):
                    host._claim_recovery_once(dispatch)

    def test_receipt_preflight_denies_bad_or_existing_path(self):
        from scripts import funds_inject as host
        with TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(host, "ROOT", root), \
                 patch.object(host, "OUTPUT", root / "dist" / "game-host"):
                with self.assertRaisesRegex(host.GateError, "RECEIPT_OUTSIDE_DIST_GAME_HOST"):
                    host._reserve_receipt(root / "not-ours.json", execute=True)
                owned = host._reserve_receipt(
                    Path("dist/game-host/unique.json"), execute=True)
                self.assertTrue(owned.exists())
                with self.assertRaisesRegex(host.GateError, "FUNDS_RECEIPT_ALREADY_EXISTS"):
                    host._reserve_receipt(
                        Path("dist/game-host/unique.json"), execute=True)
                auto = host._reserve_receipt(None, execute=True)
                self.assertTrue(auto.exists())
                self.assertTrue(auto.is_relative_to(host.OUTPUT))
                unfinished = json.loads(auto.read_text(encoding="utf-8"))
                self.assertEqual(
                    unfinished["state"], "PREPARED_EFFECT_OUTCOME_UNKNOWN_IF_UNFINALIZED"
                )
                self.assertEqual(
                    unfinished["next_gate"], "RECONCILE_GAME_HUD_BEFORE_ANY_RETRY"
                )

    def test_post_dispatch_receipt_failure_preserves_live_receipt_in_stdout(self):
        from scripts import funds_inject as host
        with TemporaryDirectory() as temp:
            root = Path(temp)
            live = {
                "state": "FUNDS_INJECT_DISPATCHED_NOT_VERIFIED",
                "dispatch_ref": "dispatch:" + "a" * 32,
            }
            output = StringIO()
            with patch.object(host, "ROOT", root), \
                 patch.object(host, "OUTPUT", root / "dist" / "game-host"), \
                 patch.object(host, "_execute_plan", return_value=live), \
                 patch.object(host, "_write_receipt",
                              side_effect=OSError("test-disk-full")), \
                 redirect_stdout(output):
                code = host.main([
                    "inject", "--amount", "100000", "--funds", "38",
                    "--game-mode", "live", "--execute",
                    "--process-id", "123", "--session-id", "session",
                ])
            result = json.loads(output.getvalue())
            self.assertEqual(code, 3)
            self.assertEqual(result["live"]["dispatch_ref"], live["dispatch_ref"])
            self.assertEqual(result["persistence_state"],
                             "RECEIPT_WRITE_FAILED_RECONCILE_NO_REPLAY")
            self.assertIn("receipt", result)

    def test_execution_needs_bound_prior_receipt_even_with_fake_valid_ref(self):
        from scripts import funds_inject as host
        with TemporaryDirectory() as temp:
            root = Path(temp)
            output = StringIO()
            with patch.object(host, "ROOT", root), \
                 patch.object(host, "OUTPUT", root / "dist" / "game-host"), \
                 patch.object(host, "_execute_plan") as dispatch, \
                 redirect_stdout(output):
                code = host.main([
                    "recover", "--amount", "100000", "--funds-before", "38",
                    "--funds-after", "38", "--game-mode", "live",
                    "--prior-dispatch-ref", "dispatch:" + "f" * 32,
                    "--evidence-ref", "hud:post-exact", "--confirmed-noop",
                    "--console-open-method", "operator-ready", "--console-ready",
                    "--execute", "--process-id", "123", "--session-id", "session",
                ])
                dispatch.assert_not_called()
            self.assertEqual(code, 2)
            self.assertIn("PRIOR_EXACT_DISPATCH_RECEIPT_REQUIRED", output.getvalue())

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
