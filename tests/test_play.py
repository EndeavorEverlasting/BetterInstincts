"""Container/host startup handshake and first-failure routing."""
from contextlib import nullcontext, redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import bootstrap
from scripts import first_run, play


class PlayTests(unittest.TestCase):
    def invoke(self, args, platform="win32"):
        stdout, stderr = StringIO(), StringIO()
        with patch.object(play.sys, "platform", platform), redirect_stdout(stdout), redirect_stderr(stderr):
            code = play.main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_non_windows_reports_host_before_touching_docker(self):
        with patch.object(play.shutil, "which") as which:
            code, text, stderr = self.invoke(["--json"], "linux")
        self.assertEqual((code, stderr), (2, ""))
        self.assertEqual(json.loads(text)["reason"], "WINDOWS_GAME_HOST_REQUIRED")
        which.assert_not_called()

    def test_plan_works_without_windows_or_git_and_never_calls_host(self):
        plan = play.startup_plan()
        with patch.object(play.shutil, "which", return_value="docker") as which, \
             patch.object(play, "docker_plan", return_value=plan), \
             patch.object(play, "play_on_windows") as host:
            code, text, stderr = self.invoke(["--plan", "--json"], "linux")
        self.assertEqual((code, stderr), (0, ""))
        self.assertEqual(json.loads(text)["plan"], plan)
        which.assert_called_once_with("docker")
        host.assert_not_called()

    def test_missing_docker_returns_actionable_error_before_install(self):
        with patch.object(play.shutil, "which", return_value=None), \
             patch.object(play, "play_on_windows") as host:
            code, text, stderr = self.invoke(["--json"])
        self.assertEqual((code, stderr), (2, ""))
        receipt = json.loads(text)
        self.assertEqual((receipt["stage"], receipt["reason"]), ("container_build", "DOCKER_NOT_FOUND"))
        self.assertIn("Docker", receipt["next_step"])
        host.assert_not_called()

    def test_startup_receipt_contains_source_identity_and_runs_without_host_access(self):
        expected = play.startup_plan()
        image = "betterinstincts-startup:local"
        commands = []

        def docker(command, **kwargs):
            self.assertTrue(kwargs["check"])
            commands.append(command)
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(expected))

        with patch.object(play.subprocess, "run", side_effect=docker):
            self.assertEqual(play.docker_plan("docker", Mock()), expected)
        self.assertEqual(commands[0], ["docker", "build", "--tag", image, str(play.ROOT)])
        self.assertEqual(commands[1], ["docker", "run", "--rm", "--pull=never", "--network=none",
                                       "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges",
                                       image])
        self.assertEqual(set(expected["sources"]), set(play.STARTUP_SOURCES))

    def test_altered_container_plan_never_reaches_host(self):
        def docker(command, **kwargs):
            wrong = play.startup_plan()
            wrong["sources"]["scripts/first_run.py"] = "0" * 64
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(wrong))

        with patch.object(play.shutil, "which", side_effect=lambda name: name), \
             patch.object(play.subprocess, "run", side_effect=docker), \
             patch.object(play, "play_on_windows") as host:
            code, text, _ = self.invoke(["--json"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(text)["reason"], "DOCKER_STARTUP_PLAN_FAILED")
        host.assert_not_called()

    def test_install_failure_stops_before_game_launch(self):
        with patch.object(play, "windows_startup_lock", return_value=nullcontext()), \
             patch.object(bootstrap, "paths", return_value={}), \
             patch.object(bootstrap, "install", side_effect=bootstrap.BootstrapError("conflict")), \
             patch.object(first_run, "requested_start") as start:
            with self.assertRaises(play.PlayBlocked) as raised:
                play.play_on_windows(None, Mock())
        self.assertEqual(raised.exception.step, "toolkit_install")
        start.assert_not_called()

    def test_existing_game_remains_open_after_real_manifest_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            location = bootstrap.paths(home=Path(tmp), platform="win32", environment={"LOCALAPPDATA": tmp})
            location["development"].mkdir(parents=True)
            with patch.object(bootstrap, "_origin_ok", return_value=True), \
                 patch.object(bootstrap, "paths", return_value=location), \
                 patch.object(play, "windows_startup_lock", side_effect=nullcontext), \
                 patch.object(first_run, "auto_start",
                              return_value={"state": "GAME_ALREADY_RUNNING_NO_DUPLICATE_LAUNCH"}):
                self.assertEqual(play.play_on_windows(None, Mock())["toolkit"]["state"], "INSTALLED")
                result = play.play_on_windows(None, Mock())
            self.assertEqual(result["toolkit"]["state"], "ALREADY_INSTALLED")
            self.assertEqual(result["game"]["state"], "GAME_ALREADY_RUNNING_NO_DUPLICATE_LAUNCH")
            self.assertEqual(result["status"], "ok")

    def test_default_cli_runs_container_then_game_and_prints_welcome(self):
        with patch.object(play.shutil, "which", side_effect=lambda name: name), \
             patch.object(play, "docker_plan", return_value=play.startup_plan()) as container, \
             patch.object(play, "play_on_windows",
                          return_value={"status": "ok", "next_step": "Launch requested."}) as host:
            code, text, stderr = self.invoke([])
        self.assertEqual((code, stderr), (0, ""))
        self.assertEqual(text.splitlines(), ["Welcome to BetterInstincts.", "Launch requested."])
        container.assert_called_once()
        self.assertIsNone(host.call_args.args[0])

    def test_selected_exe_uses_existing_admission_and_reports_ambiguity(self):
        with patch.object(play, "windows_startup_lock", return_value=nullcontext()), \
             patch.object(bootstrap, "paths", return_value={}), \
             patch.object(bootstrap, "install", return_value={"state": "ALREADY_INSTALLED"}), \
             patch.object(first_run, "auto_start", return_value={
                 "state": "GAME_SELECTION_REQUIRED", "reason": "MULTIPLE_SIMS4_INSTALLATIONS_SELECT_ONE",
             }) as start:
            target = Path("Game/Bin/TS4_x64.exe")
            result = play.play_on_windows(target, Mock())
        self.assertEqual(result["stage"], "game_launch")
        self.assertIn("--game-exe", result["next_step"])
        self.assertIn("discoverer", start.call_args.kwargs)
