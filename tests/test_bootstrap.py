"""P92 canonical path, reversible clone lifecycle, and uninstall safety."""
import json
import shutil
import subprocess
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
             patch.object(bootstrap, "_pristine", return_value=True), \
             patch.object(bootstrap, "_clone_signature", return_value={
                 "head": "a" * 40, "branch": "main", "refs_sha256": "b" * 64,
                 "reflog_sha256": "c" * 64, "git_config_sha256": "d" * 64,
                 "git_auxiliary_sha256": "e" * 64,
             }):
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
             patch.object(bootstrap, "_pristine", return_value=False), \
             patch.object(bootstrap, "_clone_signature", return_value={"head": "a" * 40}):
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


    def test_no_arg_and_gui_cli_open_local_window_not_mutate_directly(self):
        with patch.object(bootstrap, "_gui", return_value=0) as gui, \
             patch.object(bootstrap, "install") as installed, \
             patch.object(bootstrap, "uninstall") as removed:
            self.assertEqual(bootstrap.main([]), 0)
            self.assertEqual(bootstrap.main(["gui"]), 0)
        self.assertEqual(gui.call_count, 2)
        installed.assert_not_called()
        removed.assert_not_called()

    def test_gui_cancel_uninstall_requires_click_and_approval(self):
        import sys
        import types

        commands = {}
        class Widget:
            def __init__(self, *args, **kwargs):
                if "text" in kwargs and "command" in kwargs:
                    commands[kwargs["text"]] = kwargs["command"]
            def pack(self, *args, **kwargs):
                return None
        class Root(Widget):
            def title(self, *args):
                return None
            def geometry(self, *args):
                return None
            def resizable(self, *args):
                return None
            def mainloop(self):
                commands["Uninstall"]()
        class StringVar:
            def __init__(self, value):
                self.value = value
            def set(self, value):
                self.value = value
        gui = types.ModuleType("tkinter")
        gui.TclError = RuntimeError
        gui.Tk = Root
        gui.Frame = gui.Label = gui.Button = Widget
        gui.StringVar = StringVar
        msg = types.ModuleType("tkinter.messagebox")
        approvals = []
        def deny(*args, **kwargs):
            approvals.append(args)
            return False
        msg.askyesno = deny
        msg.showinfo = lambda *a, **k: self.fail("no informational dialog after cancelled uninstall")
        msg.showerror = lambda *a, **k: self.fail("no error dialog after cancelled uninstall")
        gui.messagebox = msg
        with patch.dict(sys.modules, {"tkinter": gui, "tkinter.messagebox": msg}), \
             patch.object(bootstrap, "paths", side_effect=AssertionError("NO_PATH_LOOKUP")):
            self.assertEqual(bootstrap._gui(), 0)
        self.assertEqual(len(approvals), 1)


    def _git(self, *args, cwd=None):
        return subprocess.run(
            ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
        ).stdout.strip()

    @unittest.skipUnless(shutil.which("git"), "Git CLI required")
    def _make_local_remote(self):
        bare = self.home / "fixture-remote.git"
        seed = self.home / "fixture-seed"
        self._git("init", "--bare", "--initial-branch=main", str(bare))
        self._git("init", "--initial-branch=main", str(seed))
        (seed / "README.md").write_text("seed\\n", encoding="utf-8")
        self._git("add", "README.md", cwd=seed)
        self._git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                  "commit", "-m", "seed", cwd=seed)
        self._git("remote", "add", "origin", str(bare), cwd=seed)
        self._git("push", "-u", "origin", "main", cwd=seed)
        return bare

    def test_profile_shared_lock_root_is_not_inside_clone(self):
        for loc in (
            self.location,
            bootstrap.paths(home=self.home, platform="win32", environment={
                "LOCALAPPDATA": str(self.home / "LocalAppData")
            }),
        ):
            self.assertEqual(loc["locks"], loc["use"].parent / "runtime" / "locks")
            self.assertNotIn(str(loc["development"]), str(loc["locks"]))

    @unittest.skipUnless(shutil.which("git"), "Git CLI required")
    def test_actual_clean_clone_is_removed_and_empty_runtime_paths_pruned(self):
        bare = self._make_local_remote()
        with patch.object(bootstrap, "REPOSITORY", str(bare)), \
             patch.object(bootstrap, "ALLOWED_ORIGINS", {str(bare)}):
            receipt = bootstrap.install(self.location, platform="linux")
            self.assertTrue(receipt["created_checkout"])
            self.assertTrue(bootstrap._pristine(self.location["development"]))
            self.location["locks"].mkdir(parents=True, mode=0o700)
            removed = bootstrap.uninstall(self.location, platform="linux")
        self.assertTrue(removed["checkout_removed"])
        self.assertFalse(self.location["development"].exists())
        self.assertFalse(self.location["locks"].exists())
        self.assertFalse(self.location["use"].exists())

    @unittest.skipUnless(shutil.which("git"), "Git CLI required")
    def test_clean_checkout_with_unpushed_commit_is_never_deleted(self):
        bare = self._make_local_remote()
        dev = self.location["development"]
        with patch.object(bootstrap, "REPOSITORY", str(bare)), \
             patch.object(bootstrap, "ALLOWED_ORIGINS", {str(bare)}):
            bootstrap.install(self.location, platform="linux")
            (dev / "README.md").write_text("new local commit\\n", encoding="utf-8")
            self._git("add", "README.md", cwd=dev)
            self._git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                      "commit", "-m", "unpublished work", cwd=dev)
            self.assertTrue(bootstrap._pristine(dev))
            removed = bootstrap.uninstall(self.location, platform="linux")
        self.assertFalse(removed["checkout_removed"])
        self.assertEqual(removed["checkout_preserved_reason"], "MODIFIED_OR_UNVERIFIED_GIT_HISTORY")
        self.assertTrue((dev / ".git").exists())
        self.assertFalse(self.location["use"].exists())

    @unittest.skipUnless(shutil.which("git"), "Git CLI required")
    def test_clean_main_with_extra_local_branch_is_preserved(self):
        bare = self._make_local_remote()
        dev = self.location["development"]
        with patch.object(bootstrap, "REPOSITORY", str(bare)), \
             patch.object(bootstrap, "ALLOWED_ORIGINS", {str(bare)}):
            bootstrap.install(self.location, platform="linux")
            self._git("branch", "operator-branch", cwd=dev)
            self.assertTrue(bootstrap._pristine(dev))
            removed = bootstrap.uninstall(self.location, platform="linux")
        self.assertFalse(removed["checkout_removed"])
        self.assertTrue(dev.is_dir())

    @unittest.skipUnless(shutil.which("git"), "Git CLI required")
    def test_git_config_mutation_is_preserved_even_if_worktree_clean(self):
        bare = self._make_local_remote()
        dev = self.location["development"]
        with patch.object(bootstrap, "REPOSITORY", str(bare)), \
             patch.object(bootstrap, "ALLOWED_ORIGINS", {str(bare)}):
            bootstrap.install(self.location, platform="linux")
            self._git("config", "--local", "user.name", "Operator", cwd=dev)
            self.assertTrue(bootstrap._pristine(dev))
            removed = bootstrap.uninstall(self.location, platform="linux")
        self.assertFalse(removed["checkout_removed"])
        self.assertTrue(dev.is_dir())

    @unittest.skipUnless(shutil.which("git"), "Git CLI required")
    def test_clean_checkout_with_custom_git_hook_is_preserved(self):
        bare = self._make_local_remote()
        dev = self.location["development"]
        with patch.object(bootstrap, "REPOSITORY", str(bare)), \
             patch.object(bootstrap, "ALLOWED_ORIGINS", {str(bare)}):
            bootstrap.install(self.location, platform="linux")
            hooks = dev / ".git" / "hooks"
            hooks.mkdir(exist_ok=True)
            (hooks / "pre-commit").write_text("# operator customization\\n", encoding="utf-8")
            self.assertTrue(bootstrap._pristine(dev))
            removed = bootstrap.uninstall(self.location, platform="linux")
        self.assertFalse(removed["checkout_removed"])
        self.assertTrue((hooks / "pre-commit").exists())

    @unittest.skipUnless(shutil.which("git"), "Git CLI required")
    def test_legacy_manifest_lacks_delete_permission(self):
        bare = self._make_local_remote()
        dev = self.location["development"]
        with patch.object(bootstrap, "REPOSITORY", str(bare)), \
             patch.object(bootstrap, "ALLOWED_ORIGINS", {str(bare)}):
            bootstrap.install(self.location, platform="linux")
            manifest = self.location["use"] / bootstrap.MANIFEST
            data = json.loads(manifest.read_text())
            data.pop("clone_signature")
            manifest.write_text(json.dumps(data), encoding="utf-8")
            removed = bootstrap.uninstall(self.location, platform="linux")
        self.assertFalse(removed["checkout_removed"])
        self.assertTrue(dev.is_dir())

    @unittest.skipUnless(shutil.which("git"), "Git CLI required")
    def test_runtime_lock_blocks_uninstall_without_partial_deletion(self):
        bare = self._make_local_remote()
        with patch.object(bootstrap, "REPOSITORY", str(bare)), \
             patch.object(bootstrap, "ALLOWED_ORIGINS", {str(bare)}):
            bootstrap.install(self.location, platform="linux")
            lock = self.location["locks"] / "desktop-shared.lock"
            lock.parent.mkdir(parents=True, mode=0o700)
            lock.write_text("busy", encoding="utf-8")
            with self.assertRaisesRegex(bootstrap.BootstrapError, "RUNTIME_LOCK_BUSY"):
                bootstrap.uninstall(self.location, platform="linux")
            self.assertTrue((self.location["use"] / bootstrap.MANIFEST).exists())
            lock.unlink()
            removed = bootstrap.uninstall(self.location, platform="linux")
        self.assertTrue(removed["checkout_removed"])
        self.assertFalse(lock.parent.exists())


if __name__ == "__main__":
    unittest.main()
