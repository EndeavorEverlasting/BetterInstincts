"""P95 handoff call-stack + Trifecta P08/P82/P07 offline regressions.

No game process, global input hooks, user saves, or host SendInput required.
"""
import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from betterinstincts.control_handoff import HandoffError, as_presence, confirm, decide
from betterinstincts.host_automate import plan_automation
from betterinstincts.player_presence import PresenceProbe
from scripts import needs_force

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
    def test_no_opt_in_session_stays_paused(self):
        result = decide(probe(120000), session_active=False)
        self.assertFalse(result["screen_control_allowed"])
        self.assertEqual(result["reason"], "SESSION_INACTIVE")

    def test_player_on_canvas_recent_input_pauses_immediately(self):
        result = decide(probe(0), session_active=True)
        self.assertEqual(result["state"], "PAUSED_FOR_PLAYER")
        self.assertEqual(as_presence(result)["host"], "YIELD_TO_PLAYER")

    def test_stationary_cursor_does_not_lock_host_forever(self):
        result = decide(probe(10000), session_active=True)
        self.assertTrue(result["screen_control_allowed"])
        self.assertEqual(result["state"], "HOST_READY")

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
        self.assertTrue(decide(probe(3500), session_active=True, idle_ms=3000)["screen_control_allowed"])
        self.assertFalse(decide(probe(3500), session_active=True, idle_ms=5000)["screen_control_allowed"])
        for threshold in (0, 999, 120001, True):
            with self.assertRaises(HandoffError):
                decide(probe(100000), session_active=True, idle_ms=threshold)

    def test_confirm_two_fresh_probes(self):
        samples = iter([probe(9000), probe(9500)])
        result = confirm(lambda: next(samples), session_active=True, sleep_fn=lambda _: None)
        self.assertTrue(result["screen_control_allowed"])
        self.assertEqual(result["samples_checked"], 2)

    def test_confirm_second_probe_player_interrupt_cancels(self):
        samples = iter([probe(9000), probe(0)])
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
        result = plan_automation(OBS, probe(9000), session_active=True)
        self.assertEqual(result["state"], "HOST_AUTOMATION_PLANNED")
        self.assertEqual(result["needs_force_plan"]["route"], "MAP_TRAVEL")
        self.assertFalse(result["execute_clicks"])

    def test_observation_player_direction_overrides_idle_probe(self):
        obs = {**OBS, "player_directed": True}
        result = plan_automation(obs, probe(9000), session_active=True)
        self.assertEqual(result["state"], "YIELD_TO_PLAYER")

    def test_live_click_executor_demands_exact_session_and_one_step(self):
        with patch.object(needs_force.sys, "platform", "win32"):
            with redirect_stdout(io.StringIO()) as output:
                status = needs_force.main(["run", "--execute", "--process-id", "42"])
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(output.getvalue())["reason"], "HANDOFF_SESSION_AND_SINGLE_STEP_REQUIRED")

    def test_live_click_executor_never_batches_steps(self):
        with patch.object(needs_force.sys, "platform", "win32"), \
             patch("betterinstincts.host_listener.status", return_value={"state": "ACTIVE"}), \
             patch("betterinstincts.player_presence.probe_windows", return_value=probe(10000)), \
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
        samples = iter([probe(10000), probe(10000), probe(0)])
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
            patch("betterinstincts.player_presence.probe_windows", return_value=probe(10000)),
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


if __name__ == "__main__":
    unittest.main()
