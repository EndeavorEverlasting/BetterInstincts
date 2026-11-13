"""Offline, synthetic first-run journey checks. No local Sims launch."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from betterinstincts import first_run as first


class FirstRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.pf = self.root / "Program Files"

    def executable(self, relative: str = "EA Games/The Sims 4/Game/Bin/TS4_x64.exe") -> Path:
        path = self.pf / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture")
        return path

    def test_ea_game_found_without_touching_documents_or_saves(self):
        expected = self.executable()
        saves = self.root / "Documents/Electronic Arts/The Sims 4/saves"
        saves.mkdir(parents=True)
        protected = saves / "Slot_00000007.save"
        protected.write_bytes(b"protected")
        found = first.discover_game_installs({"ProgramFiles": str(self.pf)})
        self.assertEqual(found, [expected.resolve()])
        self.assertEqual(protected.read_bytes(), b"protected")

    def test_steam_secondary_library_parsed_without_recursive_drive_scan(self):
        steam = self.pf / "Steam/steamapps/libraryfolders.vdf"
        steam.parent.mkdir(parents=True)
        secondary = self.root / "Steam Library"
        steam.write_text('"libraryfolders" { "1" { "path" "' + str(secondary) + '" } }')
        game = secondary / "steamapps/common/The Sims 4/Game/Bin/TS4_x64.exe"
        game.parent.mkdir(parents=True)
        game.write_bytes(b"fixture")
        found = first.discover_game_installs({"ProgramFiles": str(self.pf)})
        self.assertEqual(found, [game.resolve()])

    def test_manual_path_works_and_foreign_executable_denied(self):
        game = self.executable()
        self.assertEqual(first.select_game([], game), game.resolve())
        stranger = self.pf / "bad.exe"
        stranger.write_bytes(b"fixture")
        with self.assertRaisesRegex(first.FirstRunError, "EXPECTED_INSTALLED"):
            first.select_game([], stranger)

    def test_missing_and_ambiguous_installation_do_not_choose_for_player(self):
        with self.assertRaisesRegex(first.FirstRunError, "NOT_FOUND"):
            first.select_game([])
        self.executable()
        another = self.executable("Steam/steamapps/common/The Sims 4/Game/Bin/TS4_x64.exe")
        with self.assertRaisesRegex(first.FirstRunError, "MULTIPLE"):
            first.select_game(first.discover_game_installs({"ProgramFiles": str(self.pf)}))
        self.assertEqual(first.select_game([], another), another.resolve())

    def test_symlink_executable_rejected(self):
        game = self.executable()
        alias = game.with_name("TS4.exe")
        try:
            alias.symlink_to(game)
        except OSError:
            self.skipTest("Filesystem does not allow symlink")
        with self.assertRaisesRegex(first.FirstRunError, "EXPECTED_INSTALLED"):
            first.validate_game_exe(alias)

    def test_journey_modes_remain_advisory_and_save_safe(self):
        old = first.plan_journey("existing")
        self.assertEqual(old["save_selection"], "PLAYER_ONLY_NO_AUTOMATIC_RESUME")
        self.assertFalse(old["automatic_input"])
        new = first.plan_journey("new", "career")
        self.assertFalse(new["cas_changes_applied"])
        self.assertIn("Fabulously Wealthy", new["cas_advice"]["aspiration"])
        self.assertFalse(new["gameplay_proved"])
        with self.assertRaises(first.FirstRunError):
            first.plan_journey("delete-save")
        with self.assertRaises(first.FirstRunError):
            first.plan_journey("new", "unknown")

    def test_first_session_skill_route_fits_four_goals_without_game_effects(self):
        expected = {
            "balanced": "gardening",
            "career": "charisma",
            "creative": "painting",
            "social": "charisma",
        }
        for goal, top_skill in expected.items():
            with self.subTest(goal=goal):
                route = first.plan_journey("new", goal)["first_session"]
                self.assertEqual(route["ranked_skill_focus"][0]["skill"], top_skill)
                self.assertEqual(len(route["ranked_skill_focus"]), 3)
                self.assertFalse(route["automatic_input"])
                self.assertFalse(route["cas_changes_applied"])
                self.assertFalse(route["skill_levels_granted"])
                self.assertFalse(route["gameplay_proved"])
                self.assertEqual(route, first.recommend_first_session(goal))
                self.assertIn("UNMEASURED", route["proof_ceiling"])

    def test_player_preference_can_change_goal_default_without_cas_mutation(self):
        selected = first.plan_journey(
            "new", "career", preferred_skill="gardening",
        )["first_session"]
        self.assertEqual(selected["ranked_skill_focus"][0]["skill"], "gardening")
        self.assertEqual(selected["context"]["preferred_skill"], "gardening")
        self.assertFalse(selected["skill_levels_granted"])
        self.assertEqual(
            selected,
            first.plan_journey("new", "career", preferred_skill=" Gardening ")["first_session"],
        )

    def test_critical_needs_and_income_pressure_gate_progression(self):
        route = first.recommend_first_session(
            "creative", critical_needs=True, income_pressure=True,
        )
        gates = [row["gate"] for row in route["first_session_decisions"]]
        self.assertEqual(gates[:2], ["PLAYER_CAS_CHOICE", "ALL_SIX_NEEDS_CHECK"])
        self.assertLess(gates.index("CRITICAL_NEEDS_FIRST"), gates.index("PLAYER_CHOSEN_SKILL"))
        self.assertLess(gates.index("FUNDS_BEFORE_PURCHASE"), gates.index("PLAYER_CHOSEN_SKILL"))
        self.assertTrue(route["training_deferred"])
        self.assertIn("Defer", route["first_session_decisions"][-2]["action"])
        self.assertFalse(first.recommend_first_session("creative")["training_deferred"])

    def test_invalid_context_abstains_and_existing_save_remains_player_only(self):
        for kwargs in (
            {"preferred_skill": "untrusted-dlc-skill"},
            {"preferred_skill": ""},
            {"preferred_skill": 123},
            {"critical_needs": "yes"},
            {"income_pressure": 1},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(first.FirstRunError):
                first.recommend_first_session("balanced", **kwargs)
        self.assertEqual(
            first.plan_journey("existing")["save_selection"],
            "PLAYER_ONLY_NO_AUTOMATIC_RESUME",
        )
        self.assertNotIn("first_session", first.plan_journey("existing"))
        self.assertEqual(len(first.SKILL_ROUTES), 7)

    def test_first_session_cli_planning_without_ea_process_or_saves(self):
        import contextlib
        import io
        import json
        from scripts.first_run import main
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = main([
                "plan", "--mode", "new", "--goal", "creative",
                "--preferred-skill", "handiness", "--critical-needs",
                "--income-pressure",
            ])
        self.assertEqual(rc, 0)
        route = json.loads(out.getvalue())["first_session"]
        self.assertEqual(route["ranked_skill_focus"][0]["skill"], "handiness")
        self.assertTrue(route["training_deferred"])
        self.assertFalse(route["automatic_input"])


    def test_gui_default_same_install_exe_pair_prefers_64_bit(self):
        from scripts import first_run as cli
        primary = self.executable()
        legacy = self.executable("EA Games/The Sims 4/Game/Bin/TS4.exe")
        self.assertEqual(
            cli.default_install_selection([legacy, primary]), primary.resolve()
        )
        self.assertIsNone(cli.default_install_selection([]))
        other = self.executable("Other/The Sims 4/Game/Bin/TS4_x64.exe")
        self.assertIsNone(cli.default_install_selection([primary, other]))

    def test_manual_game_admission_refuses_second_launch_and_preserves_save(self):
        from scripts import first_run as cli
        game = self.executable()
        protected = self.root / "Documents/Electronic Arts/The Sims 4/saves/Slot_00000007.save"
        protected.parent.mkdir(parents=True)
        protected.write_bytes(b"protected original save")
        from unittest.mock import Mock
        already_running = Mock(return_value={
            "state": "GAME_ALREADY_RUNNING_NO_DUPLICATE_LAUNCH",
            "observed_process_id": 522,
            "save_selection": "PLAYER_ONLY_NO_AUTOMATIC_RESUME",
        })
        receipt = cli.launch_selected_game(
            game, user_clicked_launch=True, admission=already_running
        )
        self.assertEqual(receipt["state"], "GAME_ALREADY_RUNNING_NO_DUPLICATE_LAUNCH")
        self.assertEqual(
            already_running.call_args.kwargs["discoverer"](), [game.resolve()]
        )
        self.assertEqual(protected.read_bytes(), b"protected original save")

    def test_manual_game_admission_fails_closed_on_unknowns(self):
        from scripts import first_run as cli
        game = self.executable()
        admit = Mock(return_value={"state": "BLOCKED_MULTIPLE_ACTIVE_GAMES"})
        with self.assertRaisesRegex(first.FirstRunError, "CONSENT"):
            cli.launch_selected_game(game, user_clicked_launch=False, admission=admit)
        admit.assert_not_called()
        outsider = self.pf / "unrelated.exe"
        outsider.write_bytes(b"other game")
        with self.assertRaisesRegex(first.FirstRunError, "EXPECTED_INSTALLED"):
            cli.launch_selected_game(outsider, user_clicked_launch=True, admission=admit)
        admit.assert_not_called()
        with self.assertRaisesRegex(first.FirstRunError, "NOT_ADMITTED"):
            cli.launch_selected_game(game, user_clicked_launch=True, admission=admit)
        with self.assertRaisesRegex(first.FirstRunError, "NOT_ADMITTED"):
            cli.launch_selected_game(
                game, user_clicked_launch=True,
                admission=Mock(return_value={"state": "GAME_SELECTION_REQUIRED"}),
            )

    def test_cli_launch_exposes_advisory_and_requires_explicit_consent(self):
        import contextlib
        import io
        import json
        from scripts import first_run as cli
        game = self.executable()
        response = {
            "state": "GAME_ALREADY_RUNNING_NO_DUPLICATE_LAUNCH",
            "save_selection": "PLAYER_ONLY_NO_AUTOMATIC_RESUME",
        }
        for confirmed in (False, True):
            with self.subTest(confirmed=confirmed), patch.object(
                cli, "launch_selected_game",
                return_value=response if confirmed else None,
                side_effect=None if confirmed else first.FirstRunError("EXPLICIT_GAME_LAUNCH_CONSENT_REQUIRED"),
            ) as launch:
                out = io.StringIO()
                args = [
                    "launch", "--game-exe", str(game),
                    "--mode", "new", "--goal", "career",
                    "--preferred-skill", "charisma",
                ]
                if confirmed:
                    args.append("--confirm-launch")
                with contextlib.redirect_stdout(out):
                    result = cli.main(args)
                payload = json.loads(out.getvalue())
                if confirmed:
                    self.assertEqual(result, 0)
                    self.assertEqual(payload["handoff"]["first_session"]["goal"], "career")
                    self.assertFalse(payload["handoff"]["automatic_input"])
                    launch.assert_called_once_with(game, user_clicked_launch=True)
                else:
                    self.assertEqual(result, 2)
                    self.assertEqual(payload["state"], "BLOCKED_PRESERVE")

    def test_no_launch_without_exact_windows_host_and_click(self):
        game = self.executable()
        fake = Mock(return_value=Mock(pid=913))
        with patch.object(first.sys, "platform", "linux"):
            with self.assertRaisesRegex(first.FirstRunError, "WINDOWS"):
                first.launch_game(game, user_clicked_launch=True, popen=fake)
        with patch.object(first.sys, "platform", "win32"):
            with self.assertRaisesRegex(first.FirstRunError, "CONSENT"):
                first.launch_game(game, user_clicked_launch=False, popen=fake)
            result = first.launch_game(game, user_clicked_launch=True, popen=fake)
        fake.assert_called_once_with([str(game.resolve())], cwd=str(game.parent.resolve()), close_fds=True)
        self.assertEqual(result["state"], "GAME_LAUNCH_DISPATCHED_NOT_LIVE_MODE")
        self.assertEqual(result["process_id"], 913)


if __name__ == "__main__":
    unittest.main()
