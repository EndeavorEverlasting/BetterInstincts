"""Operator-launched safe detached checkout for BetterInstincts live certification.

This is a product bootstrap command, NOT an agent Shell permission. The
operator launches Start-BetterInstincts.cmd; the existing desktop hook still
denies unadmitted agent Shell calls. Never reset or stash the original tree.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

from bootstrap import ALLOWED_ORIGINS, paths

ROOT = Path(__file__).resolve().parents[1]
SHA = re.compile(r"^[0-9a-f]{40}$")


class CheckoutHold(ValueError):
    pass


def git_command(*args: str, cwd: Path) -> str:
    try:
        p = subprocess.run(
            ["git", *args], cwd=cwd, check=False, capture_output=True,
            text=True, timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CheckoutHold("CHECKOUT_GIT_UNAVAILABLE") from exc
    if p.returncode:
        raise CheckoutHold("CHECKOUT_GIT_COMMAND_FAILED:" + args[0])
    return p.stdout.strip()


def prepare_checkout(
    source: Path, worktrees: Path, *, git=git_command,
) -> dict:
    """Fetch official main and reuse/create one immutable, clean detached worktree.

    Permitted only from an explicitly launched product runner. Callers must
    separately satisfy Sims player/save/host gates. No profile/save access.
    """
    source, worktrees = Path(source), Path(worktrees)
    if source.is_symlink() or not source.is_dir() or not (source / ".git").exists():
        raise CheckoutHold("CHECKOUT_SOURCE_UNSAFE")
    source = source.resolve(strict=True)
    if (not worktrees.is_absolute() or worktrees.is_symlink()
            or worktrees.parent.is_symlink()):
        raise CheckoutHold("CHECKOUT_TARGET_UNSAFE")
    try:
        observed_root = Path(git("rev-parse", "--show-toplevel", cwd=source)).resolve()
        origin = git("remote", "get-url", "origin", cwd=source)
    except (OSError, ValueError) as exc:
        raise CheckoutHold("CHECKOUT_ORIGIN_NOT_VERIFIED") from exc
    if observed_root != source or origin not in ALLOWED_ORIGINS:
        raise CheckoutHold("CHECKOUT_ORIGIN_NOT_VERIFIED")
    git("fetch", "--no-tags", "origin",
        "refs/heads/main:refs/remotes/origin/main", cwd=source)
    head = git("rev-parse", "--verify", "refs/remotes/origin/main^{commit}", cwd=source)
    if not SHA.fullmatch(head):
        raise CheckoutHold("CHECKOUT_MAIN_SHA_UNVERIFIED")
    if not worktrees.exists():
        worktrees.mkdir(parents=True, exist_ok=False)
    if worktrees.is_symlink() or not worktrees.is_dir():
        raise CheckoutHold("CHECKOUT_TARGET_UNSAFE")
    target = worktrees / ("certification-" + head[:12])
    if target.is_symlink():
        raise CheckoutHold("CHECKOUT_TARGET_UNSAFE")
    created = False
    if not target.exists():
        git("worktree", "add", "--detach", str(target), head, cwd=source)
        created = True
    if not target.is_dir() or not (target / ".git").exists():
        raise CheckoutHold("CHECKOUT_TARGET_UNSAFE")
    actual = git("rev-parse", "--verify", "HEAD", cwd=target)
    dirty = git("status", "--porcelain", "--untracked-files=all", cwd=target)
    # A detached worktree must be linked to this source's same Git object store.
    def common(directory):
        rel = Path(git("rev-parse", "--git-common-dir", cwd=directory))
        return (directory / rel).resolve()
    if actual != head or dirty or common(source) != common(target):
        raise CheckoutHold("CHECKOUT_WORKTREE_NOT_CLEAN_OR_IDENTICAL")
    return {"schema": "betterinstincts.certification-checkout/v1",
            "state": "CLEAN_DETACHED_OFFICIAL_MAIN",
            "checkout_head": head, "checkout": str(target),
            "created": created, "original_preserved": True,
            "effect_admission": "NOT_GRANTED"}


def dispatch_play(result: dict, *, save_context: Path | None = None,
                  save_name: str | None = None,
                  household_members: list[str] | None = None) -> tuple[int, dict]:
    """Only the operator-launched --run-play path dispatches current source."""
    command = [sys.executable, "-m", "scripts.play", "--native-start",
               "--mode", "dev", "--upgrade-parts",
               "--checkout-head", result["checkout_head"], "--json"]
    if save_name is not None or household_members:
        if save_context is None:
            save_context = paths()["locks"].parent / "lab-upgrade-parts" / "startup.json"
    if save_context is not None:
        command += ["--save-context", str(save_context)]
    if save_name is not None:
        command += ["--save-name", save_name]
    if household_members:
        command += ["--minimum-household-members", str(len(household_members))]
        for member in household_members:
            command += ["--household-member", member]
    try:
        p = subprocess.run(command, cwd=result["checkout"], check=False,
                           capture_output=True, text=True, timeout=900)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CheckoutHold("CERTIFICATION_PLAY_DISPATCH_FAILED") from exc
    try:
        play = json.loads(p.stdout)
    except (ValueError, TypeError) as exc:
        raise CheckoutHold("CERTIFICATION_PLAY_RECEIPT_UNAVAILABLE") from exc
    if not isinstance(play, dict) or play.get("status") not in ("blocked", "ok"):
        raise CheckoutHold("CERTIFICATION_PLAY_RECEIPT_INVALID")
    return p.returncode, play


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-play", action="store_true",
                        help="User-launched: start the existing guarded dev restock after checkout verification")
    parser.add_argument("--upgrade-parts", action="store_true",
                        help="Compatibility with the Start-BetterInstincts.cmd restock argument")
    parser.add_argument("--save-context", type=Path)
    parser.add_argument("--save-name")
    parser.add_argument("--household-member", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        result = prepare_checkout(ROOT, paths()["worktrees"])
        envelope = {"status": "prepared", "checkout_recovery": result}
        if args.run_play:
            exit_code, play = dispatch_play(
                result, save_context=args.save_context, save_name=args.save_name,
                household_members=args.household_member)
            envelope.update(status=play["status"], play=play)
            print(json.dumps(envelope, sort_keys=True))
            return 0 if exit_code == 0 and play["status"] == "ok" else 2
        print(json.dumps(envelope, sort_keys=True))
        return 0
    except (CheckoutHold, OSError, ValueError) as exc:
        reason = str(exc)
        if not reason.startswith(("CHECKOUT_", "CERTIFICATION_")):
            reason = "CHECKOUT_PREPARATION_FAILED"
        print(json.dumps({"schema": "betterinstincts.certification-checkout/v1",
                          "status": "blocked", "stage": "checkout",
                          "reason": reason,
                          "effect_admission": "NOT_GRANTED"}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
