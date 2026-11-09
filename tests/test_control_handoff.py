"""P95 handoff call-stack + Trifecta P08/P82/P07 offline regressions.

No game process, global input hooks, user saves, or host SendInput required.
"""
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from betterinstincts.control_handoff import HandoffError, as_presence, confirm, decide, exclusive_screen_owner, screen_owner_busy
from betterinstincts.host_automate import plan_automation
from betterinstincts.player_presence import PresenceProbe
from scripts import needs_force, control_handoff as handoff_cli, host_listener as listener_cli, host_automate as automate_cli

NEEDS = {
    "hunger": 0.05, "bladder": 0.7, "energy": 0.9,
    "hygiene": 0.8, "fun": 0.6, "social": 0.9,
}
OBS = {
    "needs": NEEDS, "queue": ["read"], "location_kind": "school",
    "objects_on_current_lot": False, "capture_ref": "capture:handoff-test",
}


def probe(age=None, **kwargs):
    return PresenceProbe(
        foreground_is_sims=kwargs.pop("foreground_is_sims", True),
        cursor_in_client=kwargs.pop("cursor_in_client", True),
        last_input_age_ms=age,
        **kwargs,
    )


class ControlHandoffTests(unittest.TestCase):
    def setUp(self):
        # Isolate screen locks from leftover dist/host-listener locks on the host.
        self._lock_tmp = TemporaryDirectory()
        self._lock_patch = patch(
            "betterinstincts.control_handoff.LOCK_ROOT",
            Path(self._lock_tmp.name),
        )
        self._lock_patch.start()

    def tearDown(self):
        self._lock_patch.stop()
        self._lock_tmp.cleanup()

    def test_no_opt_in_session_stays_paused(self):
        result = decide(probe(120000), session_active=False)
        self.assertFalse(result["screen_control_allowed"])
        self.assertEqual(result["reason"], "SESSION_INACTIVE")

    def test_player_on_canvas_recent_input_pauses_immediately(self):
        result = decide(probe(0), session_active=True)
        self.assertEqual(result["state"], "PAUSED_FOR_PLAYER")
        self.assertEqual(as_presence(result)["host"], "YIELD_TO_PLAYER")

    def test_stationary_cursor_does_not_lock_host_forever(self):
        result = decide(probe(20000), session_active=True)
        self.assertTrue(result["screen_control_allowed"])
        self.assertEqual(result["state"], "HOST_READY")

    def test_foreground_pid_name_is_ephemeral_not_a_control_grant(self):
        busy = probe(300, foreground_is_sims=False, cursor_in_client=False,
                     foreground_process_id=4321, foreground_process_name="Dictation.exe")
        result = decide(busy, session_active=True, idle_ms=30000)
        self.assertFalse(result["screen_control_allowed"])
        self.assertEqual(result["foreground_process"]["pid"], 4321)
        self.assertEqual(result["foreground_process"]["name"], "Dictation.exe")
        quiet = probe(60000, foreground_is_sims=False, cursor_in_client=False,
                      foreground_process_id=4321, foreground_process_name="Dictation.exe")
        self.assertTrue(decide(quiet, session_active=True, idle_ms=30000)["screen_control_allowed"])
        self.assertFalse(decide(quiet, session_active=True, idle_ms=60001)["screen_control_allowed"])
        self.assertEqual(decide(quiet, session_active=True, idle_ms=60000)["state"], "HOST_READY")

    def test_explicit_dictation_busy_blocks_even_when_clock_says_idle(self):
        value = probe(120000, foreground_process_id=500, operator_busy=True)
        result = decide(value, session_active=True)
        self.assertEqual(result["reason"], "PLAYER_OVERRIDE")
        self.assertFalse(result["screen_control_allowed"])

    def test_other_app_input_also_blocks_takeover(self):
        result = decide(
            probe(150, foreground_is_sims=False, cursor_in_client=False),
            session_active=True,
        )
        self.assertEqual(result["reason"], "RECENT_HUMAN_INPUT")

    def test_missing_stale_or_failed_sensor_fails_closed(self):
        for suspect in (
            probe(None), probe(-1), probe(True),
            probe(100000, probe_ok=False),
        ):
            with self.subTest(probe=suspect):
                self.assertFalse(decide(suspect, session_active=True)["screen_control_allowed"])

    def test_operator_override_and_directed_queue_never_expire(self):
        for suspect in (
            probe(120000, operator_declared_playing=True),
            probe(120000, player_directed_queue=True),
        ):
            self.assertEqual(decide(suspect, session_active=True)["reason"], "PLAYER_OVERRIDE")

    def test_idle_threshold_is_per_use_case_but_bounded(self):
        self.assertTrue(decide(probe(18000), session_active=True, idle_ms=15000)["screen_control_allowed"])
        self.assertFalse(decide(probe(18000), session_active=True, idle_ms=20000)["screen_control_allowed"])
        for threshold in (0, 1000, 14999, 120001, True):
            with self.assertRaises(HandoffError):
                decide(probe(100000), session_active=True, idle_ms=threshold)

    def test_confirm_two_fresh_probes(self):
        samples = iter([probe(19000), probe(19500)])
        result = confirm(lambda: next(samples), session_active=True, sleep_fn=lambda _: None)
        self.assertTrue(result["screen_control_allowed"])
        self.assertEqual(result["samples_checked"], 2)

    def test_confirm_second_probe_player_interrupt_cancels(self):
        samples = iter([probe(19000), probe(0)])
        result = confirm(lambda: next(samples), session_active=True, sleep_fn=lambda _: None)
        self.assertFalse(result["screen_control_allowed"])
        self.assertEqual(result["samples_checked"], 2)

    def test_confirm_probe_exception_cancels(self):
        def failure():
            raise RuntimeError("capture lost")
        result = confirm(failure, session_active=True, sleep_fn=lambda _: None)
        self.assertEqual(result["reason"], "PROBE_FAILED")

    def test_planner_pauses_on_unknown_input(self):
        result = plan_automation(OBS, probe(None), session_active=True)
        self.assertEqual(result["state"], "YIELD_TO_PLAYER")
        self.assertIsNone(result["needs_force_plan"])
        self.assertFalse(result["execute_clicks"])

    def test_planner_resumes_after_idle_but_only_plans(self):
        result = plan_automation(OBS, probe(19000), session_active=True)
        self.assertEqual(result["state"], "HOST_AUTOMATION_PLANNED")
        self.assertEqual(result["needs_force_plan"]["route"], "MAP_TRAVEL")
        self.assertFalse(result["execute_clicks"])

    def test_observation_player_direction_overrides_idle_probe(self):
        obs = {**OBS, "player_directed": True}
        result = plan_automation(obs, probe(19000), session_active=True)
        self.assertEqual(result["state"], "YIELD_TO_PLAYER")

    def test_same_game_process_has_only_one_agent_screen_owner(self):
        process_id = 624286
        with exclusive_screen_owner(process_id):
            self.assertTrue(screen_owner_busy(process_id))
            with self.assertRaisesRegex(HandoffError, "SCREEN_OWNER_BUSY"):
                with exclusive_screen_owner(process_id):
                    pass
        self.assertFalse(screen_owner_busy(process_id))
        # Normal exit releases ownership, and another explicit action can start.
        with exclusive_screen_owner(process_id):
            pass

    def test_cli_explicit_busy_pauses_with_dormant_cursor(self):
        with (
            patch.object(handoff_cli.sys, "platform", "win32"),
            patch("scripts.control_handoff.status", return_value={"state": "ACTIVE"}),
            patch("scripts.control_handoff.probe_windows", return_value=probe(120000)),
            redirect_stdout(io.StringIO()) as output,
        ):
            exit_code = handoff_cli.main([
                "--session-id", "unit-test", "--process-id", "42",
                "--operator-busy",
            ])
        self.assertEqual(exit_code, 3)
        result = json.loads(output.getvalue())
        self.assertEqual(result["reason"], "PLAYER_OVERRIDE")
        self.assertFalse(result["screen_control_allowed"])

    def test_cli_reports_other_agent_as_distinct_owner(self):
        with (
            patch.object(handoff_cli.sys, "platform", "win32"),
            patch("scripts.control_handoff.status", return_value={"state": "ACTIVE"}),
            patch("scripts.control_handoff.probe_windows", return_value=probe(40000)),
            patch("scripts.control_handoff.screen_owner_busy", return_value=True),
            redirect_stdout(io.StringIO()) as output,
        ):
            exit_code = handoff_cli.main([
                "--session-id", "unit-test", "--process-id", "42",
            ])
        self.assertEqual(exit_code, 3)
        self.assertEqual(json.loads(output.getvalue())["state"], "PAUSED_FOR_AGENT")

    def test_live_click_executor_demands_exact_session_and_one_step(self):
        with patch.object(needs_force.sys, "platform", "win32"):
            with redirect_stdout(io.StringIO()) as output:
                status = needs_force.main(["run", "--execute", "--process-id", "42"])
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(output.getvalue())["reason"], "HANDOFF_SESSION_AND_SINGLE_STEP_REQUIRED")

    def test_live_click_executor_never_batches_steps(self):
        with patch.object(needs_force.sys, "platform", "win32"), \
             patch("betterinstincts.host_listener.status", return_value={"state": "ACTIVE"}), \
             patch("betterinstincts.player_presence.probe_windows", return_value=probe(20000)), \
             patch("scripts.game_host.focus"), \
             patch("scripts.needs_force._send_click") as click, \
             patch("scripts.needs_force.time.sleep"), \
             redirect_stdout(io.StringIO()) as output:
            result = needs_force.main([
                "run", "--execute", "--process-id", "42",
                "--session-id", "unit-test", "--step-id", "pause_live",
            ])
        self.assertEqual(result, 0)
        receipt = json.loads(output.getvalue())
        self.assertTrue(receipt["single_step_only"])
        self.assertEqual([row["id"] for row in receipt["steps"]], ["pause_live"])
        click.assert_called_once()

    def test_live_click_executor_stops_after_probe_changes(self):
        samples = iter([probe(20000), probe(20000), probe(0)])
        with patch.object(needs_force.sys, "platform", "win32"), \
             patch("betterinstincts.host_listener.status", return_value={"state": "ACTIVE"}), \
             patch("betterinstincts.player_presence.probe_windows", side_effect=lambda *_: next(samples)), \
             patch("scripts.game_host.focus"), \
             patch("scripts.needs_force._send_click") as click, \
             patch("scripts.needs_force.time.sleep"), \
             redirect_stdout(io.StringIO()) as output:
            result = needs_force.main([
                "run", "--execute", "--process-id", "42",
                "--session-id", "unit-test", "--step-id", "pause_live",
            ])
        self.assertEqual(result, 2)
        self.assertEqual(json.loads(output.getvalue())["reason"], "HOST_PAUSED:RECENT_HUMAN_INPUT")
        click.assert_not_called()


    def test_session_deactivation_before_click_cancels(self):
        states = iter([{"state": "ACTIVE"}, {"state": "ACTIVE"}, {"state": "INACTIVE"}])
        with (
            patch.object(needs_force.sys, "platform", "win32"),
            patch("betterinstincts.host_listener.status", side_effect=lambda _: next(states)),
            patch("betterinstincts.player_presence.probe_windows", return_value=probe(20000)),
            patch("scripts.game_host.focus"),
            patch("scripts.needs_force._send_click") as click,
            patch("scripts.needs_force.time.sleep"),
            redirect_stdout(io.StringIO()) as output,
        ):
            result = needs_force.main([
                "run", "--execute", "--process-id", "42",
                "--session-id", "unit-test", "--step-id", "pause_live",
            ])
        self.assertEqual(result, 2)
        self.assertEqual(json.loads(output.getvalue())["reason"], "HOST_HANDOFF_SESSION_INACTIVE")
        click.assert_not_called()

    def test_bad_receipt_path_rejected_before_any_click(self):
        with (
            patch.object(needs_force.sys, "platform", "win32"),
            patch("scripts.needs_force._send_click") as click,
            redirect_stdout(io.StringIO()) as output,
        ):
            result = needs_force.main([
                "run", "--execute", "--process-id", "42",
                "--session-id", "unit-test", "--step-id", "pause_live",
                "--receipt", "../unowned.json",
            ])
        self.assertEqual(result, 2)
        self.assertEqual(json.loads(output.getvalue())["reason"], "RECEIPT_OUTSIDE_DIST_GAME_HOST")
        click.assert_not_called()


    def test_host_listener_cli_uses_shared_15_second_idle_default(self):
        with TemporaryDirectory() as tmp:
            observation = Path(tmp) / "obs.json"
            observation.write_text("{}", encoding="utf-8")
            with patch("scripts.host_listener.tick", return_value={"state": "TEST"}) as handler, \
                 redirect_stdout(io.StringIO()):
                exit_code = listener_cli.main([
                    "tick", "--session-id", "unit", "--observation", str(observation),
                ])
        self.assertEqual(exit_code, 0)
        self.assertEqual(handler.call_args.kwargs["idle_ms"], 15000)

    def test_host_automate_cli_uses_shared_15_second_idle_default(self):
        with TemporaryDirectory() as tmp:
            observation = Path(tmp) / "obs.json"
            probe_file = Path(tmp) / "probe.json"
            observation.write_text("{}", encoding="utf-8")
            probe_file.write_text(json.dumps({
                "foreground_is_sims": False,
                "cursor_in_client": False,
                "last_input_age_ms": 20000,
                "probe_ok": True,
            }), encoding="utf-8")
            with patch("scripts.host_automate.plan_automation", return_value={"state": "TEST"}) as handler, \
                 redirect_stdout(io.StringIO()):
                exit_code = automate_cli.main([
                    "--observation", str(observation), "--probe-json", str(probe_file),
                    "--session-active",
                ])
            self.assertEqual(exit_code, 0)
            self.assertEqual(handler.call_args.kwargs["idle_ms"], 15000)
            with redirect_stdout(io.StringIO()) as output:
                refused = automate_cli.main([
                    "--observation", str(observation), "--probe-json", str(probe_file),
                    "--session-active", "--idle-ms", "8000",
                ])
        self.assertEqual(refused, 2)
        self.assertIn("IDLE_THRESHOLD_OUT_OF_RANGE", output.getvalue())


if __name__ == "__main__":
    unittest.main()
