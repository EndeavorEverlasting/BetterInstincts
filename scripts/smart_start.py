#!/usr/bin/env python3
"""Bounded unattended Sims 4 startup, not an automatic user-save controller.

The player's deliberate invocation of the launcher is the only launch request.
Process enumeration is read-only. A new or existing process is never evidence
that a particular save, menu, household, or Live Mode has been reached.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path
import subprocess
import sys
from typing import Callable

from betterinstincts.first_run import (
    FirstRunError, discover_game_installs, launch_game, select_game,
)

SIMGAME_NAMES = frozenset({"ts4_x64.exe", "ts4.exe"})
MAX_TASKLIST_CHARS = 1_000_000
MAX_PROCESS_ROWS = 8192


def read_sims_processes(
    runner: Callable[..., object] = subprocess.run,
) -> dict[int, str]:
    """Return observed Sims basename/PID pairs; never scan drives or save data.

    Fail closed on an untrustworthy Windows process inventory rather than
    risk launching a second instance or attaching to the wrong process.
    """
    if sys.platform != "win32":
        raise FirstRunError("LOCAL_WINDOWS_GAME_HOST_REQUIRED")
    try:
        result = runner(
            ["tasklist", "/FO", "CSV", "/NH"], capture_output=True,
            text=True, check=True, timeout=8,
        )
        output = result.stdout
        if not isinstance(output, str) or not output or len(output) > MAX_TASKLIST_CHARS:
            raise FirstRunError("PROCESS_INVENTORY_UNAVAILABLE_OR_TOO_LARGE")
        rows = list(csv.reader(io.StringIO(output)))
        if not rows or len(rows) > MAX_PROCESS_ROWS:
            raise FirstRunError("PROCESS_INVENTORY_UNAVAILABLE_OR_TOO_LARGE")
        found: dict[int, str] = {}
        for row in rows:
            if not row or row[0].casefold() not in SIMGAME_NAMES:
                continue
            if len(row) < 2 or not row[1].strip().isdecimal():
                raise FirstRunError("SIMS_PROCESS_ID_UNTRUSTWORTHY")
            pid = int(row[1].strip())
            if pid <= 0 or pid in found:
                raise FirstRunError("SIMS_PROCESS_ID_UNTRUSTWORTHY")
            found[pid] = row[0]
        return found
    except (OSError, UnicodeError, subprocess.SubprocessError, csv.Error) as exc:
        raise FirstRunError("PROCESS_INVENTORY_UNAVAILABLE") from exc


def auto_start(
    *,
    process_reader: Callable[[], dict[int, str]] = read_sims_processes,
    discoverer: Callable[[], list[Path]] = discover_game_installs,
    launcher: Callable[..., dict] = launch_game,
) -> dict:
    """Launch only for one proven install and no already-running Sims process.

    User-save selection remains explicitly outside automatic authority.
    A process ID from Popen is a dispatch receipt; tasklist may find a
    distinct game PID when EA/Steam launchers hand off the child.
    """
    if sys.platform != "win32":
        raise FirstRunError("LOCAL_WINDOWS_GAME_HOST_REQUIRED")
    before = process_reader()
    if not isinstance(before, dict) or any(
        type(pid) is not int or pid <= 0 or name.casefold() not in SIMGAME_NAMES
        for pid, name in before.items()
        if isinstance(name, str)
    ) or any(not isinstance(name, str) for name in before.values()):
        raise FirstRunError("INVALID_PROCESS_INVENTORY")
    if len(before) > 1:
        return {
            "state": "BLOCKED_MULTIPLE_ACTIVE_GAMES",
            "observed_process_ids": sorted(before),
            "automatic_input": False,
            "save_selection": "PLAYER_ONLY_NO_AUTOMATIC_RESUME",
            "proof_ceiling": "PROCESS_NAMES_ONLY_NO_GAME_SCENE_PROOF",
        }
    if len(before) == 1:
        return {
            "state": "GAME_ALREADY_RUNNING_NO_DUPLICATE_LAUNCH",
            "observed_process_id": next(iter(before)),
            "automatic_input": False,
            "save_selection": "PLAYER_ONLY_NO_AUTOMATIC_RESUME",
            "menu_state": "NOT_OBSERVED",
            "proof_ceiling": "PROCESS_NAME_ONLY_NOT_GAME_OR_SAVE_CERTIFIED",
        }
    try:
        target = select_game(discoverer())
    except FirstRunError as exc:
        if str(exc) not in {
            "SIMS4_NOT_FOUND_SELECT_INSTALLED_EXE",
            "MULTIPLE_SIMS4_INSTALLATIONS_SELECT_ONE",
        }:
            raise
        return {
            "state": "GAME_SELECTION_REQUIRED",
            "reason": str(exc),
            "automatic_input": False,
            "save_selection": "PLAYER_ONLY_NO_AUTOMATIC_RESUME",
            "proof_ceiling": "NO_GAME_LAUNCHED",
        }
    # Recheck after path selection: a concurrently started game wins.
    if process_reader():
        raise FirstRunError("SIMS_STARTED_DURING_PREFLIGHT_NO_DUPLICATE_LAUNCH")
    dispatched = launcher(target, user_clicked_launch=True)
    if dispatched.get("state") != "GAME_LAUNCH_DISPATCHED_NOT_LIVE_MODE":
        raise FirstRunError("GAME_DISPATCH_RESULT_UNTRUSTWORTHY")
    # Read-only post-dispatch snapshot; no guesses from the launcher PID.
    try:
        after = process_reader()
    except FirstRunError:
        after = {}
    observed = sorted(after)
    return {
        "state": "GAME_LAUNCH_DISPATCHED_SAVE_HANDOFF",
        "game_executable": str(target),
        "dispatch_process_id": dispatched.get("process_id"),
        "observed_game_process_id": observed[0] if len(observed) == 1 else None,
        "observed_process_count": len(observed),
        "menu_state": "NOT_OBSERVED",
        "automatic_input": False,
        "save_selection": "PLAYER_ONLY_NO_AUTOMATIC_RESUME",
        "next_step": "The Sims 4 owns loading; choose and verify the save in the game.",
        "proof_ceiling": "PROCESS_DISPATCH_AND_OPTIONAL_NAME_ONLY_NOT_SAVE_OR_LIVE_MODE",
    }
