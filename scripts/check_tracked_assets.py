#!/usr/bin/env python3
"""Reject accidental tracking of game saves, compiled mods, or private game assets."""
import fnmatch
from pathlib import PurePosixPath
import subprocess
import sys

BLOCKED_EXTENSIONS = ("*.save", "*.save.ver*", "*.package", "*.ts4script")
BLOCKED_DIRS = {"mods", "saves", "tray", "dist", "build"}

def forbidden(paths):
    bad = []
    for filename in paths:
        normal = filename.replace("\\", "/")
        segments = PurePosixPath(normal).parts
        if any(part.lower() in BLOCKED_DIRS for part in segments[:-1]):
            bad.append(filename)
        elif any(fnmatch.fnmatch(segments[-1].lower(), pat) for pat in BLOCKED_EXTENSIONS):
            bad.append(filename)
    return bad

def main():
    outcome = subprocess.run(["git", "ls-files", "-z"], capture_output=True, check=True)
    tracked = [p for p in outcome.stdout.decode("utf-8").split("\0") if p]
    illegal = forbidden(tracked)
    if illegal:
        print("TRACKED_GAME_ASSET_BLOCKED: " + ",".join(illegal), file=sys.stderr)
        return 2
    print("TRACKED_ASSETS_PASS: " + str(len(tracked)) + " tracked files inspected")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
