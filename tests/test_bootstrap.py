"""P92 canonical path, reversible clone lifecycle, and uninstall safety."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bootstrap


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.location = bootstrap.paths(home=self.home, platform="linux", environment={})

    def test_profiles_have_distinct_portable_dev_use_worktree_roots(self):
        loc = self.location
        self.assertEqual(loc["development"], self.home / "dev" / "BetterInstincts")
        self.assertNotEqual(loc["development"], loc["use"])
        self.assertNotEqual(loc["worktrees"], loc["use"])
        win = bootstrap.paths(home=self.home, platform="win32",
                              environment={"LOCALAPPDATA": str(self.home / "LocalAppData")})
        self.assertEqual(win["use"], self.home / "LocalAppData" / "BetterInstincts" / "app")
        with self.assertRaisesRegex(bootstrap.BootstrapError, "LOCALAPPDATA_REQUIRED"):
            bootstrap.paths(home=self.home, platform="win32", environment={})

    def test_existing_checkout_never_removed(self):
        dev = self.location["development"]
        dev.mkdir(parents=True)
        (dev / "sentinel.txt").write_text("operator work")
        with patch.object(bootstrap, "_origin_ok", return_value=True):
            installed = bootstrap.install(self.location, platform="linux")
            self.assertEqual(installed["state"], "INSTALLED")
            self.assertEqual(bootstrap.install(self.location, platform="linux")["state"], "ALREADY_INSTALLED")
            removed = bootstrap.uninstall(self.location, platform="linux")
        self.assertFalse(removed["checkout_removed"])
        self.assertEqual((dev / "sentinel.txt").read_text(), "operator work")
        self.assertFalse(self.location["use"].exists())

    def test_new_clean_clone_is_removed_with_managed_launcher(self):
        dev = self.location["development"]
        def fake_run(*args, **kwargs):
            if args[:2] == ("git", "clone"):
                (dev / ".git").mkdir(parents=True)
            return ""
        with patch.object(bootstrap, "_run", side_effect=fake_run), \
             patch.object(bootstrap, "_origin_ok", return_value=True), \
             patch.object(bootstrap, "_pristine", return_value=True):
            installed = bootstrap.install(self.location, platform="linux")
            self.assertTrue(installed["created_checkout"])
            launcher = Path(installed["launcher"])
            self.assertTrue(launcher.read_text().startswith("#!/bin/sh"))
            removed = bootstrap.uninstall(self.location, platform="linux")
        self.assertTrue(removed["checkout_removed"])
        self.assertFalse(dev.exists())
        self.assertFalse(self.location["use"].exists())

    def test_managed_clone_with_untracked_data_is_preserved(self):
        dev = self.location["development"]
        def fake_run(*args, **kwargs):
            if args[:2] == ("git", "clone"):
                (dev / ".git").mkdir(parents=True)
            return ""
        with patch.object(bootstrap, "_run", side_effect=fake_run), \
             patch.object(bootstrap, "_origin_ok", return_value=True), \
             patch.object(bootstrap, "_pristine", return_value=False):
            bootstrap.install(self.location, platform="linux")
            removed = bootstrap.uninstall(self.location, platform="linux")
        self.assertFalse(removed["checkout_removed"])
        self.assertTrue(dev.exists())

    def test_launcher_tamper_fails_closed_with_install_preserved(self):
        dev = self.location["development"]
        dev.mkdir(parents=True)
        with patch.object(bootstrap, "_origin_ok", return_value=True):
            installed = bootstrap.install(self.location, platform="linux")
            Path(installed["launcher"]).write_text("unowned change")
            with self.assertRaisesRegex(bootstrap.BootstrapError, "LAUNCHER_CHANGED"):
                bootstrap.uninstall(self.location, platform="linux")
        self.assertTrue((self.location["use"] / bootstrap.MANIFEST).exists())

    def test_unowned_extra_install_file_is_never_deleted(self):
        dev = self.location["development"]
        dev.mkdir(parents=True)
        with patch.object(bootstrap, "_origin_ok", return_value=True):
            bootstrap.install(self.location, platform="linux")
            (self.location["use"] / "my-data.txt").write_text("preserve")
            with self.assertRaisesRegex(bootstrap.BootstrapError, "UNOWNED_INSTALL_FILES"):
                bootstrap.uninstall(self.location, platform="linux")
        self.assertEqual((self.location["use"] / "my-data.txt").read_text(), "preserve")

    def test_manifest_identity_tamper_blocks_cleanup(self):
        dev = self.location["development"]
        dev.mkdir(parents=True)
        with patch.object(bootstrap, "_origin_ok", return_value=True):
            bootstrap.install(self.location, platform="linux")
            path = self.location["use"] / bootstrap.MANIFEST
            payload = json.loads(path.read_text())
            payload["checkout"] = str(self.home)
            path.write_text(json.dumps(payload))
            with self.assertRaisesRegex(bootstrap.BootstrapError, "MANIFEST_IDENTITY"):
                bootstrap.uninstall(self.location, platform="linux")


if __name__ == "__main__":
    unittest.main()
