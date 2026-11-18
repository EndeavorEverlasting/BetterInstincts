"""No OS desktop calls: mocked official Git worktree recovery."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.certification_checkout import CheckoutHold, prepare_checkout

HEAD = "6" * 40
OFFICIAL = "https://github.com/EndeavorEverlasting/BetterInstincts.git"


class FakeGit:
    def __init__(self, source: Path, origin=OFFICIAL):
        self.source, self.origin, self.calls = source, origin, []
        self.dirty = False

    def __call__(self, *args, cwd):
        self.calls.append((args, cwd))
        if args == ("rev-parse", "--show-toplevel"):
            return str(self.source)
        if args == ("remote", "get-url", "origin"):
            return self.origin
        if args[0] == "fetch":
            return ""
        if args == ("rev-parse", "--verify", "refs/remotes/origin/main^{commit}"):
            return HEAD
        if args[:3] == ("worktree", "add", "--detach"):
            target = Path(args[3])
            target.mkdir()
            (target / ".git").write_text("gitdir: original")
            return ""
        if args == ("rev-parse", "--verify", "HEAD"):
            return HEAD
        if args == ("status", "--porcelain", "--untracked-files=all"):
            return " M live.py" if self.dirty else ""
        if args == ("rev-parse", "--git-common-dir"):
            return str(self.source / ".git")
        raise AssertionError(args)


class CheckoutRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.source = base / "source"
        self.source.mkdir()
        (self.source / ".git").mkdir()
        self.worktrees = base / "isolated"

    def test_dirty_original_is_never_reset_or_stashed(self):
        fake = FakeGit(self.source)
        result = prepare_checkout(self.source, self.worktrees, git=fake)
        self.assertTrue(result["created"])
        self.assertEqual(result["checkout_head"], HEAD)
        self.assertEqual(result["effect_admission"], "NOT_GRANTED")
        self.assertFalse(any(args[0][0] in ("reset", "stash", "clean", "merge")
                             for args in fake.calls))
        self.assertTrue((self.source / ".git").is_dir())
        repeated = prepare_checkout(self.source, self.worktrees, git=fake)
        self.assertFalse(repeated["created"])
        self.assertEqual(repeated["checkout"], result["checkout"])

    def test_unofficial_origin_rejected_before_fetch(self):
        fake = FakeGit(self.source, "https://not-official.invalid/git")
        with self.assertRaisesRegex(CheckoutHold, "CHECKOUT_ORIGIN_NOT_VERIFIED"):
            prepare_checkout(self.source, self.worktrees, git=fake)
        self.assertFalse(any(x[0][0] == "fetch" for x in fake.calls))

    def test_dirty_target_is_not_replaced(self):
        fake = FakeGit(self.source)
        prepare_checkout(self.source, self.worktrees, git=fake)
        fake.dirty = True
        with self.assertRaisesRegex(CheckoutHold, "CHECKOUT_WORKTREE_NOT_CLEAN"):
            prepare_checkout(self.source, self.worktrees, git=fake)
        self.assertFalse(any(x[0][0] in ("reset", "clean") for x in fake.calls))

    def test_symlink_source_rejected(self):
        link = Path(self.temp.name) / "link"
        try:
            link.symlink_to(self.source, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        with self.assertRaisesRegex(CheckoutHold, "CHECKOUT_SOURCE_UNSAFE"):
            prepare_checkout(link, self.worktrees, git=FakeGit(self.source))


if __name__ == "__main__":
    unittest.main()
