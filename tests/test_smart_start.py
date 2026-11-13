"""Offline negative/positive fixtures for deliberate zero-extra-click launch.

No real Sims executable, EA app, Documents directory or Windows input used.
"""
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from betterinstincts.first_run import FirstRunError
from scripts import smart_start


class SmartStartTests(unittest.TestCase):
    def test_observed_process_inventory_is_bounded_read_only(self):
        runner = Mock(return_value=SimpleNamespace(
            stdout='"System","100","Console","1","5 K"\n"TS4_x64.exe","5412","Console","1","500 K"\n'
        ))
        with patch.object(smart_start.sys, "platform", "win32"):
            self.assertEqual(smart_start.read_sims_processes(runner), {5412: "TS4_x64.exe"})
        runner.assert_called_once_with(
            ["tasklist", "/FO", "CSV", "/NH"], capture_output=True,
            text=True, check=True, timeout=8,
        )

    def test_inventory_fails_closed_on_untrusted_pid_or_system_failure(self):
        with patch.object(smart_start.sys, "platform", "win32"):
            for output in ('"TS4.exe","not-a-pid"\n', '"TS4.exe","0"\n',
                           '"TS4.exe","41"\n"TS4.exe","41"\n', ""):
                with self.subTest(output=output):
                    with self.assertRaises(FirstRunError):
                        smart_start.read_sims_processes(
                            Mock(return_value=SimpleNamespace(stdout=output))
                        )
            with self.assertRaisesRegex(FirstRunError, "PROCESS_INVENTORY_UNAVAILABLE"):
                smart_start.read_sims_processes(
                    Mock(side_effect=subprocess.TimeoutExpired("tasklist", 8))
                )

    def test_single_install_starts_from_double_click_without_another_consent(self):
        launch = Mock(return_value={
            "state": "GAME_LAUNCH_DISPATCHED_NOT_LIVE_MODE", "process_id": 72,
        })
        reader = Mock(side_effect=[{}, {}, {852: "TS4_x64.exe"}])
        chosen = Path("C:/EA Games/The Sims 4/Game/Bin/TS4_x64.exe")
        with patch.object(smart_start.sys, "platform", "win32"), patch.object(
            smart_start, "select_game", return_value=chosen,
        ) as selector:
            result = smart_start.auto_start(
                process_reader=reader, discoverer=lambda: [chosen], launcher=launch
            )
        selector.assert_called_once_with([chosen])
        launch.assert_called_once_with(chosen, user_clicked_launch=True)
        self.assertEqual(result["dispatch_process_id"], 72)
        self.assertEqual(result["observed_game_process_id"], 852)
        self.assertEqual(result["menu_state"], "NOT_OBSERVED")
        self.assertEqual(result["save_selection"], "PLAYER_ONLY_NO_AUTOMATIC_RESUME")
        self.assertFalse(result["automatic_input"])

    def test_existing_process_never_launches_duplicate(self):
        launch = Mock()
        with patch.object(smart_start.sys, "platform", "win32"):
            result = smart_start.auto_start(
                process_reader=lambda: {522: "TS4.exe"},
                discoverer=Mock(side_effect=AssertionError("unneeded discovery")),
                launcher=launch,
            )
        self.assertEqual(result["state"], "GAME_ALREADY_RUNNING_NO_DUPLICATE_LAUNCH")
        self.assertEqual(result["observed_process_id"], 522)
        launch.assert_not_called()

    def test_multiple_active_processes_abstain(self):
        launch = Mock()
        with patch.object(smart_start.sys, "platform", "win32"):
            result = smart_start.auto_start(
                process_reader=lambda: {10: "TS4.exe", 11: "TS4_x64.exe"},
                discoverer=lambda: [], launcher=launch,
            )
        self.assertEqual(result["state"], "BLOCKED_MULTIPLE_ACTIVE_GAMES")
        launch.assert_not_called()

    def test_missing_and_ambiguous_installations_retain_manual_picker(self):
        launch = Mock()
        with patch.object(smart_start.sys, "platform", "win32"):
            for code in ("SIMS4_NOT_FOUND_SELECT_INSTALLED_EXE",
                         "MULTIPLE_SIMS4_INSTALLATIONS_SELECT_ONE"):
                with self.subTest(code=code), patch.object(
                    smart_start, "select_game", side_effect=FirstRunError(code)
                ):
                    result = smart_start.auto_start(
                        process_reader=lambda: {}, discoverer=lambda: [], launcher=launch
                    )
                    self.assertEqual(result["state"], "GAME_SELECTION_REQUIRED")
                    self.assertEqual(result["reason"], code)
        launch.assert_not_called()

    def test_concurrent_game_start_aborts_before_launch(self):
        launch = Mock()
        with patch.object(smart_start.sys, "platform", "win32"), patch.object(
            smart_start, "select_game", return_value=Path("sim.exe")
        ):
            with self.assertRaisesRegex(FirstRunError, "DURING_PREFLIGHT"):
                smart_start.auto_start(
                    process_reader=Mock(side_effect=[{}, {342: "TS4.exe"}]),
                    discoverer=lambda: [Path("sim.exe")], launcher=launch
                )
        launch.assert_not_called()

    def test_linux_and_untrusted_inventory_never_dispatch(self):
        launch = Mock()
        with patch.object(smart_start.sys, "platform", "linux"):
            with self.assertRaisesRegex(FirstRunError, "LOCAL_WINDOWS"):
                smart_start.auto_start(launcher=launch)
        with patch.object(smart_start.sys, "platform", "win32"):
            with self.assertRaisesRegex(FirstRunError, "INVALID_PROCESS"):
                smart_start.auto_start(process_reader=lambda: {"x": "TS4.exe"}, launcher=launch)
        launch.assert_not_called()

    def test_postlaunch_missing_pid_is_not_misreported_as_game_process(self):
        launch = Mock(return_value={
            "state": "GAME_LAUNCH_DISPATCHED_NOT_LIVE_MODE", "process_id": 234
        })
        with patch.object(smart_start.sys, "platform", "win32"), patch.object(
            smart_start, "select_game", return_value=Path("sim.exe")
        ):
            result = smart_start.auto_start(
                process_reader=lambda: {}, discoverer=lambda: [Path("sim.exe")],
                launcher=launch,
            )
        self.assertIsNone(result["observed_game_process_id"])
        self.assertEqual(result["dispatch_process_id"], 234)
        self.assertNotIn("LIVE_CERTIFIED", str(result))


    def test_single_install_with_32_and_64_bit_exes_prefers_x64(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "EA Games" / "The Sims 4" / "Game" / "Bin"
            binary.mkdir(parents=True)
            legacy = binary / "TS4.exe"
            current = binary / "TS4_x64.exe"
            legacy.write_bytes(b"fixture")
            current.write_bytes(b"fixture")
            launch = Mock(return_value={
                "state": "GAME_LAUNCH_DISPATCHED_NOT_LIVE_MODE", "process_id": 132,
            })
            with patch.object(smart_start.sys, "platform", "win32"):
                result = smart_start.auto_start(
                    process_reader=lambda: {}, discoverer=lambda: [legacy, current],
                    launcher=launch,
                )
            launch.assert_called_once_with(current.resolve(), user_clicked_launch=True)
            self.assertEqual(result["state"], "GAME_LAUNCH_DISPATCHED_SAVE_HANDOFF")
            self.assertEqual(result["save_selection"], "PLAYER_ONLY_NO_AUTOMATIC_RESUME")


    def test_unique_install_helper_is_shared_with_manual_chooser(self):
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp) / "EA Games/The Sims 4/Game/Bin"
            bin_dir.mkdir(parents=True)
            x64 = bin_dir / "TS4_x64.exe"
            legacy = bin_dir / "TS4.exe"
            x64.write_bytes(b"x64")
            legacy.write_bytes(b"legacy")
            self.assertEqual(
                smart_start.select_unique_install([legacy, x64]), x64.resolve()
            )
            self.assertEqual(
                smart_start.select_unique_install([x64]), x64.resolve()
            )
            other_dir = Path(tmp) / "Steam/The Sims 4/Game/Bin"
            other_dir.mkdir(parents=True)
            other = other_dir / "TS4_x64.exe"
            other.write_bytes(b"fixture")
            with self.assertRaisesRegex(FirstRunError, "MULTIPLE"):
                smart_start.select_unique_install([x64, other])

    def test_two_distinct_install_directories_are_not_collapsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidates = []
            for name in ("EA Games", "Steam"):
                binary = Path(tmp) / name / "The Sims 4" / "Game" / "Bin"
                binary.mkdir(parents=True)
                exe = binary / "TS4_x64.exe"
                exe.write_bytes(b"fixture")
                candidates.append(exe)
            launch = Mock()
            with patch.object(smart_start.sys, "platform", "win32"):
                result = smart_start.auto_start(
                    process_reader=lambda: {}, discoverer=lambda: candidates,
                    launcher=launch,
                )
            self.assertEqual(result["state"], "GAME_SELECTION_REQUIRED")
            self.assertEqual(result["reason"], "MULTIPLE_SIMS4_INSTALLATIONS_SELECT_ONE")
            launch.assert_not_called()

    def test_malformed_tasklist_must_not_be_interpreted_as_empty_inventory(self):
        with patch.object(smart_start.sys, "platform", "win32"):
            for output in (
                'INFO: No tasks are running which match the specified criteria.\\n',
                '"System","100"\\n',
                '"System","100","Console","1","1 K"\\n"TS4.exe","20"\\n',
                '"TS4.exe","21","Console","1","1 K","extra"\\n',
            ):
                with self.subTest(output=output):
                    with self.assertRaisesRegex(
                        FirstRunError, "PROCESS_INVENTORY_UNTRUSTWORTHY"
                    ):
                        smart_start.read_sims_processes(
                            Mock(return_value=SimpleNamespace(stdout=output))
                        )

    def test_prelaunch_second_snapshot_must_be_well_formed(self):
        launch = Mock()
        with patch.object(smart_start.sys, "platform", "win32"), patch.object(
            smart_start, "select_game", return_value=Path("sim.exe")
        ):
            for second in ([], {"bad": "TS4.exe"}, {1: "not-the-sims.exe"}):
                with self.subTest(second=second):
                    with self.assertRaisesRegex(FirstRunError, "INVALID_PROCESS_INVENTORY"):
                        smart_start.auto_start(
                            process_reader=Mock(side_effect=[{}, second]),
                            discoverer=lambda: [Path("sim.exe")],
                            launcher=launch,
                        )
        launch.assert_not_called()

    def test_postdispatch_invalid_snapshot_withholds_process_proof_without_replay(self):
        launch = Mock(return_value={
            "state": "GAME_LAUNCH_DISPATCHED_NOT_LIVE_MODE", "process_id": 123,
        })
        with patch.object(smart_start.sys, "platform", "win32"), patch.object(
            smart_start, "select_game", return_value=Path("sim.exe")
        ):
            result = smart_start.auto_start(
                process_reader=Mock(side_effect=[{}, {}, {"not-a-pid": "TS4.exe"}]),
                discoverer=lambda: [Path("sim.exe")], launcher=launch,
            )
        launch.assert_called_once()
        self.assertIsNone(result["observed_game_process_id"])
        self.assertEqual(result["observed_process_count"], 0)
        self.assertEqual(result["process_observation_state"],
                         "PROCESS_INVENTORY_UNAVAILABLE_AFTER_DISPATCH")
        self.assertEqual(result["menu_state"], "NOT_OBSERVED")



if __name__ == "__main__":
    unittest.main()
