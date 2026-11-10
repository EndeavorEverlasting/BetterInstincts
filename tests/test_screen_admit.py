"""Offline regressions for issue #35 screen_admit adapter barrier."""
from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from betterinstincts.control_handoff import HandoffError
from betterinstincts.player_presence import PresenceProbe
from betterinstincts.screen_admit import admitted_screen_lease, require_execute_session
from scripts import funds_inject, menu_blockers, viewport_recover


def probe(age=20000, **kwargs):
    return PresenceProbe(
        foreground_is_sims=kwargs.pop("foreground_is_sims", True),
        cursor_in_client=kwargs.pop("cursor_in_client", True),
        last_input_age_ms=age,
        **kwargs,
    )


class ScreenAdmitUnitTests(unittest.TestCase):
    def setUp(self):
        self._lock_tmp = TemporaryDirectory()
        self._lock_patch = patch(
            "betterinstincts.control_handoff.LOCK_ROOT",
            Path(self._lock_tmp.name),
        )
        self._lock_patch.start()

    def tearDown(self):
        self._lock_patch.stop()
        self._lock_tmp.cleanup()

    def test_require_session_and_pid(self):
        with self.assertRaisesRegex(HandoffError, "HANDOFF_SESSION_REQUIRED"):
            require_execute_session(None, 42)
        with self.assertRaisesRegex(HandoffError, "EXACT_GAME_PROCESS_ID_REQUIRED"):
            require_execute_session("unit", None)
        with self.assertRaisesRegex(HandoffError, "EXACT_GAME_PROCESS_ID_REQUIRED"):
            require_execute_session("unit", 0)

    def test_lease_reconfirms_before_each_step_and_focuses_once(self):
        focus = MagicMock()
        # First ensure_ready: 2 pre-focus + 2 post-focus samples; next: 2.
        samples = iter([
            probe(19000), probe(19100), probe(19200),
            probe(19300), probe(19400), probe(19500),
        ])
        with (
            patch("betterinstincts.screen_admit.listener_status", return_value={"state": "ACTIVE"}),
            patch("betterinstincts.screen_admit.probe_windows", side_effect=lambda *_: next(samples)),
            patch("betterinstincts.control_handoff.time.sleep"),
        ):
            with admitted_screen_lease(4242, "unit-test", focus_fn=focus) as ensure_ready:
                first = ensure_ready()
                second = ensure_ready()
        self.assertTrue(first["screen_control_allowed"])
        self.assertTrue(second["screen_control_allowed"])
        focus.assert_called_once()

    def test_inactive_session_blocks_without_focus(self):
        focus = MagicMock()
        with (
            patch("betterinstincts.screen_admit.listener_status", return_value={"state": "INACTIVE"}),
            patch("betterinstincts.screen_admit.probe_windows", return_value=probe(20000)),
        ):
            with admitted_screen_lease(4242, "unit-test", focus_fn=focus) as ensure_ready:
                with self.assertRaisesRegex(HandoffError, "HOST_HANDOFF_SESSION_INACTIVE"):
                    ensure_ready()
        focus.assert_not_called()

    def test_player_input_blocks_without_focus(self):
        focus = MagicMock()
        with (
            patch("betterinstincts.screen_admit.listener_status", return_value={"state": "ACTIVE"}),
            patch("betterinstincts.screen_admit.probe_windows", return_value=probe(0)),
        ):
            with admitted_screen_lease(4242, "unit-test", focus_fn=focus) as ensure_ready:
                with self.assertRaisesRegex(HandoffError, "HOST_PAUSED:RECENT_HUMAN_INPUT"):
                    ensure_ready()
        focus.assert_not_called()



    def test_user_input_during_pre_focus_second_probe_never_steals_focus(self):
        focus = MagicMock()
        samples = iter([probe(20000), probe(0)])
        with (
            patch("betterinstincts.screen_admit.listener_status", return_value={"state": "ACTIVE"}),
            patch("betterinstincts.screen_admit.probe_windows", side_effect=lambda *_: next(samples)),
            patch("betterinstincts.control_handoff.time.sleep"),
        ):
            with admitted_screen_lease(4242, "unit-test", focus_fn=focus) as ensure_ready:
                with self.assertRaisesRegex(HandoffError, "HOST_PAUSED:RECENT_HUMAN_INPUT"):
                    ensure_ready()
        focus.assert_not_called()

    def test_input_after_focus_blocks_game_effect_admission(self):
        focus = MagicMock()
        samples = iter([probe(20000), probe(20000), probe(0)])
        with (
            patch("betterinstincts.screen_admit.listener_status", return_value={"state": "ACTIVE"}),
            patch("betterinstincts.screen_admit.probe_windows", side_effect=lambda *_: next(samples)),
            patch("betterinstincts.control_handoff.time.sleep"),
        ):
            with admitted_screen_lease(4242, "unit-test", focus_fn=focus) as ensure_ready:
                with self.assertRaisesRegex(HandoffError, "HOST_PAUSED:RECENT_HUMAN_INPUT"):
                    ensure_ready()
        focus.assert_called_once()

    def test_no_input_if_focus_did_not_reach_sims(self):
        focus = MagicMock()
        with (
            patch("betterinstincts.screen_admit.listener_status", return_value={"state": "ACTIVE"}),
            patch("betterinstincts.screen_admit.probe_windows", return_value=probe(20000, foreground_is_sims=False)),
            patch("betterinstincts.control_handoff.time.sleep"),
        ):
            with admitted_screen_lease(4242, "unit-test", focus_fn=focus) as ensure_ready:
                with self.assertRaisesRegex(HandoffError, "SIMS_FOREGROUND_UNVERIFIED"):
                    ensure_ready()
        focus.assert_called_once()

    def test_foreground_reclaimed_between_steps_requires_reborrow(self):
        focus = MagicMock()
        samples = iter([
            probe(20000, foreground_is_sims=False),
            probe(20000, foreground_is_sims=False),
            probe(20000), probe(20000),
            probe(20000, foreground_is_sims=False),
            probe(20000, foreground_is_sims=False),
            probe(20000), probe(20000),
        ])
        with (
            patch("betterinstincts.screen_admit.listener_status", return_value={"state": "ACTIVE"}),
            patch("betterinstincts.screen_admit.probe_windows", side_effect=lambda *_: next(samples)),
            patch("betterinstincts.control_handoff.time.sleep"),
        ):
            with admitted_screen_lease(4242, "unit-test", focus_fn=focus) as ensure_ready:
                self.assertTrue(ensure_ready()["screen_control_allowed"])
                self.assertTrue(ensure_ready()["screen_control_allowed"])
        self.assertEqual(focus.call_count, 2)

class AdapterBarrierTests(unittest.TestCase):
    def setUp(self):
        self._lock_tmp = TemporaryDirectory()
        self._lock_patch = patch(
            "betterinstincts.control_handoff.LOCK_ROOT",
            Path(self._lock_tmp.name),
        )
        self._lock_patch.start()

    def tearDown(self):
        self._lock_patch.stop()
        self._lock_tmp.cleanup()

    def test_menu_blockers_execute_requires_session(self):
        with patch.object(menu_blockers.sys, "platform", "win32"):
            with self.assertRaisesRegex(menu_blockers.GateError, "HANDOFF_SESSION_REQUIRED"):
                menu_blockers.dismiss(process_id=42, execute=True, blocker_ids=None, receipt=None)

    def test_menu_blockers_dry_run_stays_open(self):
        out = menu_blockers.dismiss(process_id=None, execute=False, blocker_ids=None, receipt=None)
        self.assertEqual(out["state"], "DRY_RUN")
        self.assertIn("--session-id", out["next"])

    def test_menu_blockers_execute_admits_then_clicks(self):
        with (
            patch.object(menu_blockers.sys, "platform", "win32"),
            patch("betterinstincts.screen_admit.listener_status", return_value={"state": "ACTIVE"}),
            patch("betterinstincts.screen_admit.probe_windows", return_value=probe(20000)),
            patch("betterinstincts.control_handoff.time.sleep"),
            patch("scripts.menu_blockers._focus"),
            patch("scripts.menu_blockers._send_click") as click,
            patch("scripts.menu_blockers.time.sleep"),
            patch("scripts.menu_blockers.plan_dismiss", return_value={
                "steps": [{
                    "step": "DISMISS_MEMORY_BOOST",
                    "blocker_id": "memory_boost_on",
                    "click": [10, 20],
                    "forbidden": ["RESUME"],
                }],
            }),
        ):
            out = menu_blockers.dismiss(
                process_id=42,
                execute=True,
                blocker_ids=["memory_boost_on"],
                receipt=None,
                session_id="unit-test",
            )
        self.assertEqual(out["state"], "MENU_BLOCKERS_DISMISS_DISPATCHED")
        self.assertEqual(out["session_id"], "unit-test")
        click.assert_called_once_with(10, 20)


    def test_needs_force_aborts_before_focus_on_second_input_probe(self):
        from scripts import needs_force

        mock_plan = {
            "state": "READY", "route": "MAP_TRAVEL",
            "steps": [{"id": "test-click", "execution": "HOST_SENDINPUT", "click": [10, 20]}],
            "forbidden": [],
        }
        samples = iter([probe(20000), probe(0)])
        with (
            patch.object(needs_force.sys, "platform", "win32"),
            patch("scripts.needs_force.plan_force", return_value=mock_plan),
            patch("betterinstincts.screen_admit.listener_status", return_value={"state": "ACTIVE"}),
            patch("betterinstincts.screen_admit.probe_windows", side_effect=lambda *_: next(samples)),
            patch("betterinstincts.control_handoff.time.sleep"),
            patch("scripts.game_host.focus") as focus,
            patch("scripts.needs_force._send_click") as click,
            redirect_stdout(io.StringIO()) as output,
        ):
            code = needs_force.main([
                "run", "--execute", "--process-id", "42", "--session-id", "unit",
                "--step-id", "test-click",
            ])
        self.assertEqual(code, 2)
        self.assertIn("RECENT_HUMAN_INPUT", output.getvalue())
        focus.assert_not_called()
        click.assert_not_called()

    def test_needs_force_rechecks_focus_and_dispatches_only_when_game_is_foreground(self):
        from scripts import needs_force

        mock_plan = {
            "state": "READY", "route": "MAP_TRAVEL",
            "steps": [{"id": "test-click", "execution": "HOST_SENDINPUT", "click": [10, 20]}],
            "forbidden": [],
        }
        samples = iter([
            probe(20000, foreground_is_sims=False),
            probe(20000, foreground_is_sims=False),
            probe(20000), probe(20000),
        ])
        with (
            patch.object(needs_force.sys, "platform", "win32"),
            patch("scripts.needs_force.plan_force", return_value=mock_plan),
            patch("betterinstincts.screen_admit.listener_status", return_value={"state": "ACTIVE"}),
            patch("betterinstincts.screen_admit.probe_windows", side_effect=lambda *_: next(samples)),
            patch("betterinstincts.control_handoff.time.sleep"),
            patch("scripts.game_host.focus") as focus,
            patch("scripts.needs_force._send_click") as click,
            patch("scripts.needs_force.time.sleep"),
            redirect_stdout(io.StringIO()) as output,
        ):
            code = needs_force.main([
                "run", "--execute", "--process-id", "42", "--session-id", "unit",
                "--step-id", "test-click",
            ])
        self.assertEqual(code, 0, output.getvalue())
        self.assertEqual(json.loads(output.getvalue())["state"], "NEEDS_FORCE_DISPATCHED")
        focus.assert_called_once()
        click.assert_called_once_with(10, 20)

    def test_funds_inject_execute_requires_session(self):
        with patch.object(funds_inject.sys, "platform", "win32"), \
             redirect_stdout(io.StringIO()) as output:
            code = funds_inject.main([
                "inject", "--amount", "50", "--execute", "--process-id", "42",
            ])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())["reason"], "HANDOFF_SESSION_REQUIRED")

    def test_viewport_execute_requires_session(self):
        fake_report = MagicMock()
        fake_report.state = "VIEWPORT_ANOMALY"
        fake_report.recovery_ladder = ["RECENTER_CAMERA"]
        with (
            patch.object(viewport_recover.sys, "platform", "win32"),
            patch("scripts.viewport_recover.load_contract", return_value={
                "host_next_gates": {
                    "BUILD_BUY_CATALOG_RECOVERY": "BUY",
                    "STILL_BLACK_AFTER_LADDER": "RESTART",
                },
            }),
            patch("scripts.viewport_recover.analyze_image", return_value=fake_report),
            patch("scripts.viewport_recover.report_to_dict", return_value={"state": "VIEWPORT_ANOMALY"}),
            redirect_stdout(io.StringIO()) as output,
        ):
            code = viewport_recover.main([
                "--image", str(Path(__file__).resolve()),
                "--execute", "--process-id", "42", "--max-steps", "1",
            ])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())["reason"], "HANDOFF_SESSION_REQUIRED")


if __name__ == "__main__":
    unittest.main()
