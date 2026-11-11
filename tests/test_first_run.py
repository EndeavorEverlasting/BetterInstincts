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
