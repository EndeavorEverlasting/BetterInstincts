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
        with (tempfile.TemporaryDirectory() as tmp,
              patch.object(bootstrap, "paths", return_value={"locks": Path(tmp) / "locks"}),
              patch.object(play.sys, "platform", platform),
              redirect_stdout(stdout), redirect_stderr(stderr)):
            code = play.main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_non_windows_reports_host_before_touching_docker(self):
        with patch.object(play.shutil, "which") as which:
            code, text, stderr = self.invoke(["--json"], "linux")
        self.assertEqual((code, stderr), (2, ""))
        self.assertEqual(json.loads(text)["reason"], "WINDOWS_GAME_HOST_REQUIRED")
        which.assert_not_called()

    def test_profile_entrypoint_checks_container_before_using_saved_mode_on_host(self):
        from betterinstincts import installation_profiles

        profile = {"preferred_household_id": "household:fixture",
                   "launch": {"mode": "dev", "idle_ms": 34000, "allow_cheats": False}}
        calls = Mock()
        with (patch.object(installation_profiles, "view", return_value=profile),
              patch.object(play, "play_on_windows", calls.host),
              patch.object(play, "container_plan", calls.container),
              patch.object(play.shutil, "which", return_value="docker")):
            calls.host.return_value = {"status": "ok", "next_step": "Observed fixture."}
            code, _, stderr = self.invoke(["--profile-launch", "--choose-household", "--json"])
        self.assertEqual((code, stderr), (0, ""))
        self.assertEqual([call[0] for call in calls.mock_calls], ["container", "host"])
        self.assertEqual(calls.container.call_args.args[0], "docker")
        self.assertEqual(calls.container.call_args.kwargs, {"engine": "docker", "profile_launch": True})
        self.assertEqual(calls.host.call_args.kwargs["mode"], "dev")
        self.assertIs(calls.host.call_args.kwargs["launch_profile"], profile)
        self.assertIs(calls.host.call_args.kwargs["choose_household"], True)

    def test_profile_entrypoint_can_explicitly_use_native_start(self):
        from betterinstincts import installation_profiles

        profile = {"launch": {"mode": "production"}, "preferred_household_id": None}
        with (patch.object(installation_profiles, "view", return_value=profile),
              patch.object(play.shutil, "which") as which,
              patch.object(play, "play_on_windows",
                           return_value={"status": "ok", "next_step": "Observed fixture."}) as host):
            code, _, stderr = self.invoke(["--profile-launch", "--native-start", "--json"])
        self.assertEqual((code, stderr), (0, ""))
        self.assertIs(host.call_args.kwargs["launch_profile"], profile)
        which.assert_not_called()

    def test_semantic_restock_cli_forwards_dev_selection(self):
        with (tempfile.TemporaryDirectory() as tmp, patch.object(play, "play_on_windows") as host,
              patch.object(play.shutil, "which") as which):
            context = Path(tmp) / "startup.json"
            context.touch()
            host.return_value = {"status": "ok", "stage": "lab_upgrade_parts", "next_step": "verified"}
            code, _, stderr = self.invoke(["--native-start", "--upgrade-parts", "--save-context", str(context),
                                          "--save-name", "Fixture Lab", "--household-member", "Alpha",
                                          "--household-member", "Beta", "--minimum-household-members", "3", "--json"])
        self.assertEqual((code, stderr), (0, ""))
        which.assert_not_called()
        self.assertEqual(host.call_args.kwargs["mode"], "dev")
        self.assertIs(host.call_args.kwargs["upgrade_parts"], True)
        self.assertEqual(host.call_args.kwargs["selection"], {
            "expected_save_name": "Fixture Lab", "required_members": ["Alpha", "Beta"], "minimum_members": 3})

    def test_plan_works_without_windows_or_git_and_never_calls_host(self):
        plan = play.startup_plan()
        with patch.object(play.shutil, "which", return_value="docker") as which, \
             patch.object(play, "container_plan", return_value=plan), \
             patch.object(play, "play_on_windows") as host:
            code, text, stderr = self.invoke(["--plan", "--json"], "linux")
        self.assertEqual((code, stderr), (0, ""))
        self.assertEqual(json.loads(text)["plan"], plan)
        self.assertEqual(json.loads(text)["container_engine"], "docker")
        which.assert_called_once_with("docker")
        host.assert_not_called()

    def test_profile_plan_on_linux_matches_image_emitter_without_reading_local_profile(self):
        from betterinstincts import installation_profiles

        emitted = subprocess.check_output(
            [play.sys.executable, "-I", str(play.ROOT / "scripts/play.py"),
             "--emit-plan", "--profile-launch"], text=True,
        )
        commands = []

        def docker(command, **kwargs):
            commands.append(command)
            return subprocess.CompletedProcess(command, 0, stdout=emitted)

        with (patch.object(installation_profiles, "view") as view,
              patch.object(play.shutil, "which", return_value="docker"),
              patch.object(play.subprocess, "run", side_effect=docker),
              patch.object(play, "play_on_windows") as host):
            code, text, stderr = self.invoke(["--plan", "--profile-launch", "--json"], "linux")
        self.assertEqual((code, stderr), (0, ""))
        result = json.loads(text)
        self.assertEqual(set(result["plan"]["sources"]),
                         set(play.STARTUP_SOURCES + play.PROFILE_SOURCES))
        self.assertIn("--profile-launch", result["next_step"])
        self.assertEqual(commands[1], ["docker", "run", "--rm", "--pull=never", "--network=none",
                                       "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges",
                                       "betterinstincts-startup:local", "--profile-launch"])
        view.assert_not_called()
        host.assert_not_called()

    def test_missing_docker_returns_actionable_error_before_install(self):
        from betterinstincts import installation_profiles

        profile = {"launch": {"mode": "production"}, "preferred_household_id": None}
        for options in ([], ["--profile-launch"]):
            with (self.subTest(options=options),
                  patch.object(installation_profiles, "view", return_value=profile),
                  patch.object(play.shutil, "which", return_value=None),
                  patch.object(play, "play_on_windows") as host):
                code, text, stderr = self.invoke([*options, "--json"])
                self.assertEqual((code, stderr), (2, ""))
                receipt = json.loads(text)
                self.assertEqual((receipt["stage"], receipt["reason"]), ("container_build", "DOCKER_NOT_FOUND"))
                self.assertIn("Docker", receipt["next_step"])
                host.assert_not_called()

    def test_shortcut_has_one_container_backed_profile_command(self):
        shortcut = (play.ROOT / "Start-BetterInstincts.cmd").read_text()
        commands = [line for line in shortcut.splitlines()
                    if "-m scripts.play" in line and "--profile-launch" in line]
        self.assertEqual(len(commands), 1)
        self.assertNotIn("--native-start", commands[0])
        self.assertIn("%CHOOSER_ARG%", commands[0])
        self.assertIn("%CHECKOUT_ARG%", commands[0])

    def test_engines_share_source_identity_and_do_not_receive_the_checkout(self):
        expected = play.startup_plan(profile_launch=True)
        allowed = {"Dockerfile", ".dockerignore", *play.STARTUP_SOURCES, *play.PROFILE_SOURCES}
        for engine in play.CONTAINER_ENGINES:
            with self.subTest(engine=engine):
                commands = []
                image = ("localhost/" if engine == "podman" else "") + "betterinstincts-startup:local"

                def execute(command, **kwargs):
                    self.assertTrue(kwargs["check"])
                    commands.append(command)
                    if command[1] == "info":
                        return subprocess.CompletedProcess(command, 0, stdout="linux\n")
                    if command[1] == "build":
                        context = Path(command[-1])
                        self.assertEqual(command[:-1], [engine, "build", "--tag", image])
                        self.assertNotEqual(context, play.ROOT)
                        self.assertEqual({path.relative_to(context).as_posix()
                                          for path in context.rglob("*") if path.is_file()}, allowed)
                    return subprocess.CompletedProcess(command, 0, stdout=json.dumps(expected))

                with patch.object(play.subprocess, "run", side_effect=execute):
                    self.assertEqual(play.container_plan(engine, Mock(), engine=engine, profile_launch=True), expected)
                self.assertEqual([command[1] for command in commands],
                                 ["info", "build", "run"] if engine == "podman" else ["build", "run"])
                self.assertEqual(commands[-1], [
                    engine, "run", "--rm", "--pull=never", "--network=none", "--read-only",
                    "--cap-drop=ALL", "--security-opt=no-new-privileges", image, "--profile-launch",
                ])

    def test_engine_selection_defaults_and_explicit_selection(self):
        for args, installed, selected, lookups in (
            ([], {"docker", "podman"}, "docker", ["docker"]),
            ([], {"podman"}, "podman", ["docker", "podman"]),
            (["--container-engine", "podman"], {"docker", "podman"}, "podman", ["podman"]),
        ):
            with (self.subTest(args=args, installed=installed),
                  patch.object(play.shutil, "which", side_effect=lambda name: name if name in installed else None) as which,
                  patch.object(play, "container_plan", return_value=play.startup_plan()) as plan,
                  patch.object(play, "play_on_windows") as host):
                code, output, stderr = self.invoke(["--plan", "--json", *args], "linux")
                self.assertEqual((code, stderr, json.loads(output)["container_engine"]), (0, "", selected))
                self.assertEqual([call.args[0] for call in which.call_args_list], lookups)
                plan.assert_called_once_with(selected, unittest.mock.ANY, engine=selected, profile_launch=False)
                host.assert_not_called()

    def test_explicit_missing_podman_does_not_try_docker_or_desktop(self):
        with (patch.object(play.shutil, "which", side_effect=lambda name: "docker" if name == "docker" else None) as which,
              patch.object(play.subprocess, "run") as run,
              patch.object(play, "play_on_windows") as host):
            code, output, _ = self.invoke(["--container-engine", "podman", "--json"])
        self.assertEqual((code, json.loads(output)["reason"]), (2, "PODMAN_NOT_FOUND"))
        which.assert_called_once_with("podman")
        run.assert_not_called()
        host.assert_not_called()

    def test_unavailable_or_non_linux_podman_stops_before_build_and_host(self):
        for response in (
            subprocess.CalledProcessError(1, "podman info", stderr="Machine is stopped"),
            subprocess.CompletedProcess("podman info", 0, stdout="windows\n"),
        ):
            with (self.subTest(response=response),
                  patch.object(play.shutil, "which", side_effect=lambda name: name) as which,
                  patch.object(play.subprocess, "run", side_effect=[response]) as run,
                  patch.object(play, "play_on_windows") as host):
                code, output, _ = self.invoke(["--container-engine", "podman", "--json"])
                result = json.loads(output)
                self.assertEqual((code, result["stage"], result["reason"], result["container_engine"]),
                                 (2, "container_engine", "PODMAN_ENGINE_NOT_READY", "podman"))
                which.assert_called_once_with("podman")
                run.assert_called_once()
                self.assertEqual(run.call_args.args[0], ["podman", "info", "--format", "{{.Host.OS}}"])
                host.assert_not_called()

    def test_running_podman_with_bad_plan_does_not_fall_through_to_docker_or_host(self):
        commands = []

        def podman(command, **kwargs):
            commands.append(command[:2])
            output = "linux\n" if command[1] == "info" else "{}"
            return subprocess.CompletedProcess(command, 0, stdout=output)

        with (patch.object(play.shutil, "which", side_effect=lambda name: name) as which,
              patch.object(play.subprocess, "run", side_effect=podman),
              patch.object(play, "play_on_windows") as host):
            code, output, _ = self.invoke(["--container-engine", "podman", "--json"])
        self.assertEqual((code, json.loads(output)["reason"]), (2, "PODMAN_STARTUP_PLAN_FAILED"))
        self.assertEqual(commands, [["podman", step] for step in ("info", "build", "run")])
        which.assert_called_once_with("podman")
        host.assert_not_called()

    def test_native_start_cannot_also_select_podman(self):
        with (patch.object(play.shutil, "which") as which,
              patch.object(play, "play_on_windows") as host,
              self.assertRaises(SystemExit) as raised):
            self.invoke(["--native-start", "--container-engine", "podman"])
        self.assertEqual(raised.exception.code, 2)
        which.assert_not_called()
        host.assert_not_called()

    def test_docker_context_is_the_exact_startup_source_allowlist(self):
        rules = [line for line in (play.ROOT / ".dockerignore").read_text().splitlines()
                 if line and not line.startswith("#")]
        self.assertEqual(rules[0], "**")
        self.assertCountEqual(rules[1:], ["!Dockerfile", "!.dockerignore",
                                         *(f"!{path}" for path in play.STARTUP_SOURCES + play.PROFILE_SOURCES)])

    def test_profile_plan_mismatch_blocks_the_game_route(self):
        from betterinstincts import installation_profiles

        def docker(command, **kwargs):
            legacy = play.startup_plan()
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(legacy))

        profile = {"launch": {"mode": "production"}, "preferred_household_id": None}
        with (patch.object(installation_profiles, "view", return_value=profile),
              patch.object(play.shutil, "which", return_value="docker"),
              patch.object(play.subprocess, "run", side_effect=docker),
              patch.object(play, "play_on_windows") as host):
            code, text, _ = self.invoke(["--profile-launch", "--json"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(text)["reason"], "DOCKER_STARTUP_PLAN_FAILED")
        host.assert_not_called()

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

    def test_existing_checkout_starts_without_toolkit_install(self):
        with patch.object(play, "windows_startup_lock", return_value=nullcontext()), \
             patch.object(bootstrap, "install") as install, \
             patch.object(first_run, "requested_start",
                          return_value={"state": "GAME_ALREADY_RUNNING_NO_DUPLICATE_LAUNCH"}):
            result = play.play_on_windows(None, Mock(), checkout=play.ROOT)
        install.assert_not_called()
        self.assertEqual(result["toolkit"], {"state": "EXISTING_CHECKOUT",
                                              "checkout": str(play.ROOT)})

    def test_default_cli_runs_container_then_game_and_prints_welcome(self):
        with patch.object(play.shutil, "which", side_effect=lambda name: name), \
             patch.object(play, "container_plan", return_value=play.startup_plan()) as container, \
             patch.object(play, "play_on_windows",
                          return_value={"status": "ok", "next_step": "Launch requested."}) as host:
            code, text, stderr = self.invoke([])
        self.assertEqual((code, stderr), (0, ""))
        self.assertEqual(text.splitlines()[:2], ["Welcome to BetterInstincts.", "Launch requested."])
        self.assertTrue(text.splitlines()[2].startswith("Launch receipt:"))
        self.assertEqual(host.call_args.kwargs["mode"], "production")
        self.assertEqual(host.call_args.kwargs["checkout"], play.ROOT)
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
