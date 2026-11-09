#!/usr/bin/env python3
"""BetterInstincts portable clone/install/doctor/uninstall (stdlib only).

Download THIS file from the repository main page, inspect it, then run it.
No pip, PATH, registry, task scheduler, system services, game files or saves.
An uninstall removes only manifest-proved app-owned files and, when safe, the
pristine canonical checkout created by this bootstrapper.
"""
from __future__ import annotations

import argparse
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
    }


def _clone_still_original(checkout: Path, signature: object) -> bool:
    """Legacy manifests and unverifiable copies are NEVER deletion grants."""
    if not isinstance(signature, dict) or set(signature) != {
        "head", "branch", "refs_sha256", "reflog_sha256", "git_config_sha256",
        "git_auxiliary_sha256"
    } or not all(isinstance(value, str) and value for value in signature.values()):
        return False
    try:
        return _clone_signature(checkout) == signature
    except (BootstrapError, OSError, subprocess.CalledProcessError):
        return False


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
    if dev.exists():
        if not _origin_ok(dev):
            raise BootstrapError("CANONICAL_CHECKOUT_CONFLICT_PRESERVE")
    else:
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
        "created_checkout": created, "profile": platform, "clone_signature": signature,
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
    # First validate the exact managed files; avoid partial cleanup on extras.
    if {p.name for p in use.iterdir()} != {MANIFEST, data["launcher"]}:
        raise BootstrapError("UNOWNED_INSTALL_FILES_PRESERVE")
    _check_runtime_locks(location)
    # The manifest's created_checkout flag is insufficient: clean Git trees may
    # contain unique unpublished commits/branches/stashes or modified Git config.
    can_remove_clone = bool(
        data["created_checkout"] and _pristine(dev)
        and _clone_still_original(dev, data.get("clone_signature"))
    )
    target.unlink()
    manifest_file.unlink()
    use.rmdir()
    if can_remove_clone:
        shutil.rmtree(dev)
    cleanup = _prune_empty_runtime_paths(location)
    return {"state": "UNINSTALLED", "managed_files_removed": 2,
            "checkout_removed": can_remove_clone, "runtime_cleanup": cleanup,
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
    root.geometry("540x280")
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
    root.mainloop()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", default="gui", choices=["install", "uninstall", "doctor", "gui"])
    args = parser.parse_args(argv)
    try:
        if args.command == "gui":
            return _gui()
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
