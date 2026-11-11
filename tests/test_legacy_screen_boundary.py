"""Moonwake closers: unadopted Win32 entrypoints cannot send input.

Tests deliberately run on a non-Windows CI host without any mouse, keyboard,
Bluetooth, Sims, game saves or running foreground process.
"""
from __future__ import annotations

import contextlib
import io
import unittest
from unittest.mock import MagicMock, patch

from betterinstincts.legacy_screen_boundary import (
    UnadoptedLiveEffectError,
    deny_unadopted_live_effect,
)
from scripts import (
    cas_finish_disposable,
    cas_household_check,
    cas_place_live,
    cas_quiz_okay,
    host_menu,
    school_attend_click,
)


class LegacyInputBoundaryTests(unittest.TestCase):
    def test_no_agent_flag_or_path_can_authorize_unadopted_input(self):
        for identity in (
            "scripts/host_menu.py",
            "scripts/cas_quiz_okay.py",
            "scripts/school_attend_click.py",
        ):
            with self.subTest(identity=identity):
                with self.assertRaisesRegex(
                    UnadoptedLiveEffectError, "UNADOPTED_LEGACY_INPUT_DENIED"
                ):
                    deny_unadopted_live_effect(identity)
        with self.assertRaisesRegex(
            UnadoptedLiveEffectError, "UNCLASSIFIED_LEGACY_ADAPTER_DENIED"
        ):
            deny_unadopted_live_effect("../untrusted.py")

    def test_all_four_cas_raw_entrypoints_deny_before_host_api(self):
        invocations = (
            ("quiz", lambda: cas_quiz_okay.click_okay(None, 0.0)),
            ("household", lambda: cas_household_check.click_household_check(None, 0.0)),
            ("finish", lambda: cas_finish_disposable.finish_cas(
                None, None, "Test", "Subject"
            )),
            ("place", lambda: cas_place_live._click(0, 123, 456)),
        )
        for name, invoke in invocations:
            with self.subTest(name=name):
                with self.assertRaisesRegex(
                    UnadoptedLiveEffectError, "UNADOPTED_LEGACY_INPUT_DENIED"
                ):
                    invoke()

    def test_host_menu_still_plans_but_cannot_focus_or_click(self):
        result = host_menu.run_journey(
            journey="reboot", process_id=1234, execute=False,
            from_step=None, from_scene="select_sim_to_play",
            run_id="closeout-offline", settle_sec=0.0,
        )
        self.assertEqual(result["state"], "DRY_RUN")
        focus = MagicMock()
        click = MagicMock()
        with patch.object(host_menu, "_focus", focus), patch.object(
            host_menu, "_send_click", click
        ):
            with self.assertRaisesRegex(
                UnadoptedLiveEffectError,
                "UNADOPTED_LEGACY_INPUT_DENIED:scripts/host_menu.py",
            ):
                host_menu.run_journey(
                    journey="reboot", process_id=1234, execute=True,
                    from_step=None, from_scene="select_sim_to_play",
                    run_id="closeout-offline", settle_sec=0.0,
                )
        focus.assert_not_called()
        click.assert_not_called()

    def test_legacy_cli_returns_json_block_without_leaking_traceback(self):
        import json
        for name, invoke in (
            ("host", lambda: host_menu.main([
                "run", "--from-scene", "select_sim_to_play",
                "--process-id", "1234", "--execute",
            ])),
            ("cas_place", lambda: cas_place_live.main(["--execute"])),
        ):
            with self.subTest(name=name):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = invoke()
                self.assertEqual(code, 2)
                result = json.loads(out.getvalue())
                self.assertEqual(result["state"], "BLOCKED")
                self.assertIn("UNADOPTED_LEGACY_INPUT_DENIED", result["reason"])

    def test_school_click_injection_cannot_bypass_runtime_denial(self):
        callback = MagicMock(return_value={"state": "CLICK_DISPATCHED"})
        argv = [
            "plan", "--execute", "--operator-screen-released",
            "--measured-join-y", "560", "--calibration-source",
            "PRINTWINDOW_MEASURED", "--dialog-observed",
        ]
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = school_attend_click.main(argv, dispatch=callback)
        self.assertEqual(code, 2)
        self.assertIn("UNADOPTED_LEGACY_INPUT_DENIED", err.getvalue())
        self.assertEqual(out.getvalue(), "")
        callback.assert_not_called()

    def test_school_read_only_plan_keeps_order_and_no_dispatch(self):
        callback = MagicMock()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = school_attend_click.main(["plan"], dispatch=callback)
        self.assertEqual(code, 0)
        callback.assert_not_called()
        self.assertIn("ready_to_execute", out.getvalue())


if __name__ == "__main__":
    unittest.main()
