#!/usr/bin/env python3
"""BetterInstincts portable clone/install/doctor/uninstall (stdlib only).

Download THIS file from the repository main page, inspect it, then run it.
No pip, PATH, registry, task scheduler, system services, game files or saves.
An uninstall removes only manifest-proved app-owned files and, when safe, the
pristine canonical checkout created by this bootstrapper.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

REPOSITORY = "https://github.com/EndeavorEverlasting/BetterInstincts.git"
ALLOWED_ORIGINS = {REPOSITORY, "git@github.com:EndeavorEverlasting/BetterInstincts.git"}
SCHEMA = "betterinstincts.install-manifest/v1"
LAUNCHER_HEADER = "# BetterInstincts managed launcher"
MANIFEST = "install-manifest.json"
DESKTOP_LOCK_FILENAME = "desktop-shared.lock"


class BootstrapError(ValueError):
    pass


def paths(*, home: Path | None = None, platform: str | None = None,
          environment: dict[str, str] | None = None) -> dict[str, Path]:
    """One machine/profile-aware owner; no hard-coded usernames or fallbacks."""
    home = Path.home() if home is None else Path(home)
    platform = sys.platform if platform is None else platform
    env = os.environ if environment is None else environment
    if not home.is_absolute():
        raise BootstrapError("HOME_NOT_ABSOLUTE")
    dev = home / "dev" / "BetterInstincts"
    worktrees = home / "dev" / ".worktrees" / "BetterInstincts"
    if platform == "win32":
        root = env.get("LOCALAPPDATA")
        if not root or not Path(root).is_absolute():
            raise BootstrapError("LOCALAPPDATA_REQUIRED")
        use = Path(root) / "BetterInstincts" / "app"
    elif platform.startswith("linux"):
        root = Path(env.get("XDG_DATA_HOME", str(home / ".local" / "share")))
        if not root.is_absolute():
            raise BootstrapError("XDG_DATA_HOME_NOT_ABSOLUTE")
        use = root / "betterinstincts" / "app"
    else:
        raise BootstrapError("UNSUPPORTED_OS")
    return {"development": dev, "use": use, "worktrees": worktrees,
            "locks": use.parent / "runtime" / "locks"}


def _run(*args: str, cwd: Path | None = None) -> str:
    p = subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)
    return p.stdout.strip()


def _origin_ok(checkout: Path) -> bool:
    try:
        return (checkout / ".git").is_dir() and _run("git", "remote", "get-url", "origin", cwd=checkout) in ALLOWED_ORIGINS
    except (OSError, subprocess.CalledProcessError):
        return False


def _pristine(checkout: Path) -> bool:
    """Reject dirty, untracked, ignored, and tampered checkouts before deletion."""
    if checkout.is_symlink() or not _origin_ok(checkout):
        return False
    try:
        return _run("git", "status", "--porcelain", "--untracked-files=all", "--ignored", cwd=checkout) == ""
    except (OSError, subprocess.CalledProcessError):
        return False


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()



def _git_auxiliary_sha256(git_dir: Path) -> str:
    """Guard user hooks, info/exclude and other Git-private custom files.

    Object packs/refs/reflogs/index/config have separate provenance checks.
    Reject symlinked custom Git files; never follow them during deletion proof.
    """
    ignored = {
        "objects", "refs", "logs", "index", "packed-refs",
        "FETCH_HEAD", "ORIG_HEAD", "HEAD", "config",
    }
    digest = hashlib.sha256()
    for child in sorted(git_dir.iterdir(), key=lambda p: p.name):
        if child.name in ignored:
            continue
        nodes = [child]
        if child.is_dir() and not child.is_symlink():
            nodes.extend(sorted(child.rglob("*"), key=lambda p: p.as_posix()))
        for node in nodes:
            if node.is_symlink():
                raise BootstrapError("CLONE_GIT_AUXILIARY_SYMLINK_UNSAFE")
            name = node.relative_to(git_dir).as_posix()
            digest.update(name.encode("utf-8") + b"\\0")
            if node.is_file():
                with node.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
    return digest.hexdigest()


def _clone_signature(checkout: Path) -> dict[str, str]:
    """Identity of installer-created checkout, including independent Git work.

    Status --porcelain alone misses clean local commits, branches and stashes.
    Store this immediately after clone, and require exact equality at removal.
    A later fetch or local Git metadata change safely prevents auto-removal.
    """
    git_dir = checkout / ".git"
    config = git_dir / "config"
    if git_dir.is_symlink() or not git_dir.is_dir() or config.is_symlink() or not config.is_file():
        raise BootstrapError("CLONE_GIT_IDENTITY_UNSAFE")
    return {
        "head": _run("git", "rev-parse", "--verify", "HEAD", cwd=checkout),
        "branch": _run("git", "symbolic-ref", "--quiet", "--short", "HEAD", cwd=checkout),
        "refs_sha256": _sha(_run("git", "show-ref", "--head", cwd=checkout)),
        "reflog_sha256": _sha(_run(
            "git", "reflog", "show", "--all", "--format=%H %gD", cwd=checkout
        )),
        "git_config_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
        "git_auxiliary_sha256": _git_auxiliary_sha256(git_dir),
        "worktrees_sha256": _sha(_run("git", "worktree", "list", "--porcelain", cwd=checkout)),
    }


def _clone_still_original(checkout: Path, signature: object) -> bool:
    """Legacy manifests and unverifiable copies are NEVER deletion grants."""
    if not isinstance(signature, dict) or set(signature) != {
        "head", "branch", "refs_sha256", "reflog_sha256", "git_config_sha256",
        "git_auxiliary_sha256", "worktrees_sha256"
    } or not all(isinstance(value, str) and value for value in signature.values()):
        return False
    try:
        return _clone_signature(checkout) == signature
    except (BootstrapError, OSError, subprocess.CalledProcessError):
        return False


def _sole_linked_worktree(checkout: Path) -> bool:
    """Never remove main Git metadata while another linked worktree uses it."""
    try:
        rows = _run("git", "worktree", "list", "--porcelain", cwd=checkout)
        return sum(line.startswith("worktree ") for line in rows.splitlines()) == 1
    except (OSError, subprocess.CalledProcessError):
        return False


@contextmanager
def _exclusive_uninstall_lease(location: dict[str, Path]):
    """Reserve the very same desktop lock as every cooperating UI executor.

    Check-then-delete without an O_EXCL reservation races a newly started
    Playwright or Sims host. Hold this lock through checkout removal.
    """
    _check_runtime_locks(location)
    root = location["locks"]
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    _check_runtime_locks(location)
    if os.name != "nt":
        info = root.stat()
        if info.st_uid != os.getuid() or (info.st_mode & 0o077):
            raise BootstrapError("RUNTIME_LOCK_ROOT_UNSAFE")
    lock = root / DESKTOP_LOCK_FILENAME
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(lock, flags, 0o600)
    except FileExistsError as exc:
        raise BootstrapError("RUNTIME_LOCK_BUSY_OR_STALE_PRESERVE") from exc
    try:
        inode = os.fstat(fd).st_ino
        yield
    finally:
        try:
            os.close(fd)
        finally:
            try:
                if lock.is_file() and not lock.is_symlink() and lock.stat().st_ino == inode:
                    lock.unlink()
            except OSError:
                pass


def _check_runtime_locks(location: dict[str, Path]) -> None:
    """Refuse uninstall while a cooperating host still owns desktop control."""
    lock = location["locks"]
    for directory in (location["use"].parent, lock.parent, lock):
        if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
            raise BootstrapError("RUNTIME_LOCK_PATH_UNSAFE")
    if lock.is_dir() and any(lock.iterdir()):
        raise BootstrapError("RUNTIME_LOCK_BUSY_OR_STALE_PRESERVE")


def _prune_empty_runtime_paths(location: dict[str, Path]) -> str:
    """Remove only empty BetterInstincts runtime dirs; never unlink lockfiles."""
    for directory in (location["locks"], location["locks"].parent, location["use"].parent):
        if directory.is_symlink():
            raise BootstrapError("RUNTIME_LOCK_PATH_UNSAFE")
        if directory.is_dir():
            try:
                directory.rmdir()
            except OSError:
                return "RUNTIME_PATH_NONEMPTY_PRESERVED"
    return "EMPTY_RUNTIME_PATHS_REMOVED"



def _launcher(checkout: Path, *, platform: str) -> tuple[str, str]:
    if platform == "win32":
        # Use cmd quote escaping only for platform-derived canonical paths.
        interpreter = str(Path(sys.executable))
        if any(x in interpreter + str(checkout) for x in '\r\n"%'):
            raise BootstrapError("UNSAFE_WINDOWS_LAUNCHER_PATH")
        return "betterinstincts.cmd", (
            "@echo off\r\nrem BetterInstincts managed launcher\r\n"
            + 'cd /d "' + str(checkout) + '"\r\n'
            + '"' + interpreter + '" -m scripts.host_listener %*\r\n'
        )
    interpreter = shlex.quote(sys.executable)
    return "betterinstincts", (
        "#!/bin/sh\n" + LAUNCHER_HEADER + "\n"
        + "cd " + shlex.quote(str(checkout)) + " || exit 2\n"
        + "exec " + interpreter + " -m scripts.host_listener \"$@\"\n"
    )


def _validated_manifest(use: Path, dev: Path, platform: str) -> tuple[Path, dict] | None:
    if use.is_symlink():
        raise BootstrapError("SYMLINK_INSTALL_ROOT_REFUSED")
    path = use / MANIFEST
    if not path.exists():
        return None
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 8192:
        raise BootstrapError("MANIFEST_UNSAFE")
    data = json.loads(path.read_text(encoding="utf-8"))
    name = "betterinstincts.cmd" if platform == "win32" else "betterinstincts"
    if (data.get("schema") != SCHEMA or data.get("repository") != REPOSITORY
            or data.get("checkout") != str(dev) or data.get("use") != str(use)
            or data.get("launcher") != name or type(data.get("created_checkout")) is not bool
            or not isinstance(data.get("launcher_sha256"), str)
            or len(data["launcher_sha256"]) != 64):
        raise BootstrapError("MANIFEST_IDENTITY_MISMATCH")
    return path, data


def install(location: dict[str, Path], *, platform: str | None = None) -> dict:
    platform = sys.platform if platform is None else platform
    dev, use = location["development"], location["use"]
    if dev.is_symlink() or use.is_symlink():
        raise BootstrapError("SYMLINK_LOCATION_REFUSED")
    existing = _validated_manifest(use, dev, platform)
    if existing is not None:
        _, data = existing
        name = use / data["launcher"]
        if name.is_symlink() or not name.is_file() or _sha(name.read_text(encoding="utf-8")) != data["launcher_sha256"]:
            raise BootstrapError("INSTALLED_LAUNCHER_DRIFT")
        return {"state": "ALREADY_INSTALLED", "checkout": str(dev), "use": str(use)}
    if use.exists() and any(use.iterdir()):
        raise BootstrapError("NONEMPTY_UNOWNED_INSTALL_DIRECTORY")
    created = False
    created_dev_parent = False
    if dev.exists():
        if not _origin_ok(dev):
            raise BootstrapError("CANONICAL_CHECKOUT_CONFLICT_PRESERVE")
    else:
        created_dev_parent = not dev.parent.exists()
        dev.parent.mkdir(parents=True, exist_ok=True)
        _run("git", "clone", "--", REPOSITORY, str(dev))
        created = True
        if not _origin_ok(dev):
            raise BootstrapError("CLONE_ORIGIN_UNVERIFIED")
    signature = _clone_signature(dev) if created else None
    launcher_name, content = _launcher(dev, platform=platform)
    use.mkdir(parents=True, exist_ok=True)
    target = use / launcher_name
    if target.exists() or target.is_symlink():
        raise BootstrapError("UNOWNED_LAUNCHER_CONFLICT")
    target.write_text(content, encoding="utf-8", newline="")
    if platform != "win32":
        target.chmod(0o700)
    data = {
        "schema": SCHEMA, "repository": REPOSITORY, "checkout": str(dev),
        "use": str(use), "launcher": launcher_name, "launcher_sha256": _sha(content),
        "created_checkout": created, "created_dev_parent": created_dev_parent,
        "profile": platform, "clone_signature": signature,
    }
    (use / MANIFEST).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return {"state": "INSTALLED", "checkout": str(dev), "use": str(use),
            "launcher": str(target), "created_checkout": created}


def uninstall(location: dict[str, Path], *, platform: str | None = None) -> dict:
    platform = sys.platform if platform is None else platform
    dev, use = location["development"], location["use"]
    existing = _validated_manifest(use, dev, platform)
    if existing is None:
        _check_runtime_locks(location)
        cleanup = _prune_empty_runtime_paths(location)
        return {"state": "NOT_INSTALLED", "checkout": str(dev), "runtime_cleanup": cleanup}
    manifest_file, data = existing
    target = use / data["launcher"]
    if target.is_symlink() or not target.is_file() or _sha(target.read_text(encoding="utf-8")) != data["launcher_sha256"]:
        raise BootstrapError("LAUNCHER_CHANGED_PRESERVE")
    if {p.name for p in use.iterdir()} != {MANIFEST, data["launcher"]}:
        raise BootstrapError("UNOWNED_INSTALL_FILES_PRESERVE")

    # Reservation is acquired atomically against all participating agents.
    # The entire destructive section runs while new screen actions are denied.
    with _exclusive_uninstall_lease(location):
        can_remove_clone = bool(
            data["created_checkout"] and _pristine(dev)
            and _sole_linked_worktree(dev)
            and _clone_still_original(dev, data.get("clone_signature"))
        )
        target.unlink()
        manifest_file.unlink()
        use.rmdir()
        dev_parent_removed = False
        if can_remove_clone:
            shutil.rmtree(dev)
            if data.get("created_dev_parent") is True and not dev.parent.is_symlink():
                try:
                    dev.parent.rmdir()
                    dev_parent_removed = True
                except OSError:
                    pass

    # Release our lease before removing its now-empty runtime directory.
    # A new agent's intervening lock makes rmdir fail rather than erase it.
    cleanup = _prune_empty_runtime_paths(location)
    return {"state": "UNINSTALLED", "managed_files_removed": 2,
            "checkout_removed": can_remove_clone, "dev_parent_removed": dev_parent_removed,
            "runtime_cleanup": cleanup,
            "checkout_preserved_reason": None if can_remove_clone else
            ("PREEXISTING_CHECKOUT" if not data["created_checkout"] else
             "MODIFIED_OR_UNVERIFIED_GIT_HISTORY")}



def _gui() -> int:
    """Explicitly clicked local installer. Opening never changes the workstation."""
    try:
        import tkinter as tk
        from tkinter import messagebox
    except ImportError as exc:
        raise BootstrapError("TKINTER_UNAVAILABLE_USE_CLI") from exc
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        raise BootstrapError("GRAPHICAL_DESKTOP_UNAVAILABLE_USE_CLI") from exc
    root.title("BetterInstincts · Installation")
    root.geometry("700x345")
    root.resizable(False, False)
    frame = tk.Frame(root, padx=22, pady=18)
    frame.pack(fill="both", expand=True)
    tk.Label(frame, text="BetterInstincts", font=("Arial", 18, "bold")).pack(anchor="w")
    tk.Label(
        frame,
        text="Local offline toolkit · no Sims game files or services are installed",
        wraplength=488, justify="left",
    ).pack(anchor="w", pady=(5, 10))
    status_text = tk.StringVar(value="No changes made. Choose an action.")
    tk.Label(frame, textvariable=status_text, justify="left", anchor="w", wraplength=488).pack(
        fill="x", pady=(0, 10)
    )

    def handle(command: str) -> None:
        if command == "uninstall" and not messagebox.askyesno(
            "Confirm uninstall",
            "Remove verified BetterInstincts-owned launcher and manifest?\n"
            "A pristine checkout created by this installer may also be removed.\n"
            "Pre-existing or modified checkouts and Sims saves are preserved.",
            parent=root,
        ):
            status_text.set("Uninstall cancelled. No changes made.")
            return
        try:
            location = paths()
            if command == "doctor":
                installed = _validated_manifest(location["use"], location["development"], sys.platform)
                result = {
                    "state": "INSTALLED" if installed else "NOT_INSTALLED",
                    **{key: str(value) for key, value in location.items()},
                }
            elif command == "install":
                result = install(location)
            else:
                result = uninstall(location)
            status_text.set(result["state"] + ": " + str(result.get("use", result.get("checkout", ""))))
            messagebox.showinfo("BetterInstincts", json.dumps(result, indent=2), parent=root)
        except (BootstrapError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
            status_text.set("BLOCKED_PRESERVE: " + str(exc))
            messagebox.showerror("BetterInstincts", str(exc), parent=root)

    buttons = tk.Frame(frame)
    buttons.pack(anchor="w", pady=(5, 0))
    tk.Button(buttons, text="Inspect paths", command=lambda: handle("doctor"), width=15).pack(
        side="left", padx=(0, 8)
    )
    tk.Button(buttons, text="Install", command=lambda: handle("install"), width=12).pack(
        side="left", padx=(0, 8)
    )
    tk.Button(buttons, text="Uninstall", command=lambda: handle("uninstall"), width=12).pack(
        side="left"
    )
    def open_settings() -> None:
        """Launch the explicit local settings UI from the verified checkout."""
        try:
            location = paths()
            checkout = location["development"]
            if not (checkout / "scripts" / "instance_settings.py").is_file():
                raise BootstrapError("SETTINGS_MODULE_NOT_INSTALLED_OR_CHECKOUT_STALE")
            subprocess.Popen([sys.executable, "-m", "scripts.instance_settings", "gui"],
                             cwd=checkout, close_fds=True)
            status_text.set("Local settings window opened. Preferences remain user-owned.")
        except (BootstrapError, OSError) as exc:
            status_text.set("SETTINGS_UNAVAILABLE: " + str(exc))
            messagebox.showerror("BetterInstincts", str(exc), parent=root)

    tk.Button(buttons, text="Preferences", command=open_settings, width=14).pack(
        side="left", padx=(8, 0)
    )

    def show_household_skills_recipe() -> None:
        """Show the opt-in skill bootstrap recipe only — never executes cheats."""
        recipe = household_skills_recipe()
        status_text.set("Household skill recipe shown. No cheats executed.")
        messagebox.showinfo(
            "BetterInstincts · Household skills",
            json.dumps(recipe, indent=2),
            parent=root,
        )

    tk.Button(
        buttons,
        text="Skill bootstrap…",
        command=show_household_skills_recipe,
        width=16,
    ).pack(side="left", padx=(8, 0))
    def open_game() -> None:
        """Open the opt-in Sims chooser; installation itself is not launch consent."""
        try:
            location = paths()
            if _validated_manifest(location["use"], location["development"], sys.platform) is None:
                raise BootstrapError("INSTALL_TOOLKIT_BEFORE_PLAY")
            checkout = location["development"]
            if not (checkout / "scripts" / "first_run.py").is_file():
                raise BootstrapError("FIRST_RUN_MODULE_NOT_INSTALLED_OR_CHECKOUT_STALE")
            subprocess.Popen(
                [sys.executable, "-m", "scripts.first_run", "gui"],
                cwd=checkout, close_fds=True,
            )
            status_text.set("Sims 4 chooser opened. No game launched without your click.")
        except (BootstrapError, OSError, json.JSONDecodeError) as exc:
            status_text.set("GAME_CHOOSER_UNAVAILABLE: " + str(exc))
            messagebox.showerror("BetterInstincts", str(exc), parent=root)

    tk.Button(
        frame, text="Play The Sims 4…", command=open_game, width=23,
    ).pack(anchor="w", pady=(12, 0))
    root.mainloop()
    return 0


def household_skills_recipe(*, members: str = "N") -> dict[str, object]:
    """Read-only skill-round-robin recipe; never imply game certification."""
    return {
        "state": "HOUSEHOLD_SKILLS_BOOTSTRAP_RECIPE",
        "dispatch_order": "skill_round_robin",
        "proof_ceiling": "PLAN_ONLY_NOT_LOCAL_GAME_PROOF",
        "note": (
            "Inspect existing canonical checkout and update by safe fast-forward "
            "before local install. Observe the original Live roster N. The default "
            "recipe is plan-only; do not issue --execute or --detach from bootstrap. "
            "P08 requires a disposable game save, exact patch, verified selected "
            "portrait, offline-only operation and Skills-panel observation. "
            "Adding Sims/Servos, EA Connect/Gallery/Store, unsafe saves and "
            "concurrent game-input agents are forbidden."
        ),
        "owner": "docs/handoff/BI-HOUSEHOLD-SKILL-LOCAL-P04-2026-11-09.md",
        "cli": (
            "python -m scripts.diy_skill_force household --members "
            + str(members)
            + " --skill handiness"
        ),
        "bootstrap_forward": (
            "python bootstrap.py household-skills -- --members "
            + str(members)
            + " --skill handiness"
        ),
        "next_gate": "P04_LOCAL_AGENT_PREFLIGHT_THEN_P08_DISPOSABLE_LIVE_CANARY",
    }


def run_household_skills(
    location: dict[str, Path],
    diy_argv: list[str],
) -> dict[str, object]:
    """Forward explicit household skill-force args into the verified checkout.

    Requires `--members` in diy_argv. Does not invent N. Does not run on install.
    """
    if "--members" not in diy_argv:
        raise BootstrapError("HOUSEHOLD_SKILLS_REQUIRES_OBSERVED_MEMBERS")
    checkout = location["development"]
    module = checkout / "scripts" / "diy_skill_force.py"
    if module.is_symlink() or not module.is_file():
        raise BootstrapError("DIY_SKILL_FORCE_NOT_INSTALLED_OR_CHECKOUT_STALE")
    cmd = [sys.executable, "-m", "scripts.diy_skill_force", "household", *diy_argv]
    completed = subprocess.run(
        cmd,
        cwd=str(checkout),
        capture_output=True,
        text=True,
        check=False,
    )
    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    payload: object
    try:
        payload = json.loads(stdout) if stdout else {"state": "EMPTY_STDOUT"}
    except json.JSONDecodeError:
        payload = {"state": "NON_JSON_STDOUT", "stdout": stdout[-4000:]}
    return {
        "state": "HOUSEHOLD_SKILLS_FORWARDED",
        "dispatch_order": "skill_round_robin",
        "exit_code": int(completed.returncode),
        "command": cmd,
        "checkout": str(checkout),
        "result": payload,
        "stderr_tail": stderr[-2000:] if stderr else "",
        "never_autorun": True,
    }


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    # Opt-in lab forwarder: everything after `--` goes to diy_skill_force household.
    if raw and raw[0] == "household-skills":
        try:
            location = paths()
            if len(raw) == 1 or (len(raw) == 2 and raw[1] == "--recipe"):
                print(json.dumps(household_skills_recipe(), sort_keys=True))
                return 0
            diy_argv = raw[1:]
            if diy_argv and diy_argv[0] == "--":
                diy_argv = diy_argv[1:]
            report = run_household_skills(location, diy_argv)
            print(json.dumps(report, sort_keys=True))
            return 0 if int(report.get("exit_code") or 0) == 0 else 2
        except (BootstrapError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
            print(json.dumps({"state": "BLOCKED_PRESERVE", "reason": str(exc)}, sort_keys=True))
            return 2

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        nargs="?",
        default="gui",
        choices=["install", "uninstall", "doctor", "gui", "household-skills"],
    )
    args = parser.parse_args(raw)
    try:
        if args.command == "gui":
            return _gui()
        if args.command == "household-skills":
            print(json.dumps(household_skills_recipe(), sort_keys=True))
            return 0
        location = paths()
        if args.command == "doctor":
            existing = _validated_manifest(location["use"], location["development"], sys.platform)
            report = {"state": "INSTALLED" if existing else "NOT_INSTALLED",
                      **{k: str(v) for k, v in location.items()}}
        elif args.command == "install":
            report = install(location)
        else:
            report = uninstall(location)
        print(json.dumps(report, sort_keys=True))
        return 0
    except (BootstrapError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(json.dumps({"state": "BLOCKED_PRESERVE", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
