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
    return {"development": dev, "use": use, "worktrees": worktrees}


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
        LAUNCHER_HEADER + "\n#!/bin/sh\n"
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
        "created_checkout": created, "profile": platform,
    }
    (use / MANIFEST).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return {"state": "INSTALLED", "checkout": str(dev), "use": str(use),
            "launcher": str(target), "created_checkout": created}


def uninstall(location: dict[str, Path], *, platform: str | None = None) -> dict:
    platform = sys.platform if platform is None else platform
    dev, use = location["development"], location["use"]
    existing = _validated_manifest(use, dev, platform)
    if existing is None:
        return {"state": "NOT_INSTALLED", "checkout": str(dev)}
    manifest_file, data = existing
    target = use / data["launcher"]
    if target.is_symlink() or not target.is_file() or _sha(target.read_text(encoding="utf-8")) != data["launcher_sha256"]:
        raise BootstrapError("LAUNCHER_CHANGED_PRESERVE")
    # First validate the exact managed files; avoid partial cleanup on extras.
    if {p.name for p in use.iterdir()} != {MANIFEST, data["launcher"]}:
        raise BootstrapError("UNOWNED_INSTALL_FILES_PRESERVE")
    can_remove_clone = data["created_checkout"] and _pristine(dev)
    target.unlink()
    manifest_file.unlink()
    use.rmdir()
    if can_remove_clone:
        # This is an exact canonical checkout created by THIS installer, and
        # pristine including ignored/untracked data; never delete another clone.
        shutil.rmtree(dev)
    return {"state": "UNINSTALLED", "managed_files_removed": 2,
            "checkout_removed": can_remove_clone,
            "checkout_preserved_reason": None if can_remove_clone else "PREEXISTING_OR_MODIFIED_CHECKOUT"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["install", "uninstall", "doctor"])
    args = parser.parse_args(argv)
    try:
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
