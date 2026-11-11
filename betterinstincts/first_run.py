"""Read-only Sims 4 discovery and opt-in game launch for the first-run journey.

Never scan Documents, enumerate Sims saves, choose a save automatically, touch
Windows settings, intercept inputs, or launch without a direct player request.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Callable, Mapping

GAME_NAMES = ("TS4_x64.exe", "TS4.exe")
MAX_VDF_BYTES = 65_536
GOALS = {
    "balanced": {
        "aspiration": "Choose an aspiration that reflects your Sim's own interests",
        "traits": ("Cheerful", "Self-Assured", "Good"),
        "reason": "Flexible example only; a varied household is usually more interesting than a universal build.",
    },
    "career": {
        "aspiration": "Fortune / Fabulously Wealthy",
        "traits": ("Ambitious", "Self-Assured", "Outgoing"),
        "reason": "A career-oriented starting suggestion, not a guarantee of faster promotions.",
    },
    "creative": {
        "aspiration": "Creativity / Bestselling Author",
        "traits": ("Creative", "Bookworm", "Loner"),
        "reason": "Good starting points for an independent creative Sim.",
    },
    "social": {
        "aspiration": "Popularity / Friend of the World",
        "traits": ("Outgoing", "Cheerful", "Good"),
        "reason": "A social playstyle starting point, not mandatory choices.",
    },
}
MODES = ("existing", "new")


class FirstRunError(ValueError):
    """An unattended action cannot meet the provenance or consent gate."""


def _candidate(exe: Path) -> bool:
    """Accept only recognizable Sims executables in the game's Bin directory."""
    return (
        exe.name.lower() in {name.lower() for name in GAME_NAMES}
        and exe.parent.name.lower() == "bin"
        and exe.parent.parent.name.lower() == "game"
        and exe.is_file()
        and not exe.is_symlink()
    )


def validate_game_exe(path: str | Path) -> Path:
    target = Path(path).expanduser()
    if not _candidate(target):
        raise FirstRunError("EXPECTED_INSTALLED_SIMS4_GAME_BIN_EXECUTABLE")
    return target.resolve(strict=True)


def _steam_libraries(steam: Path) -> list[Path]:
    """Only parse the bounded Steam metadata file, never walk user drives."""
    library = steam / "steamapps" / "libraryfolders.vdf"
    if not library.is_file() or library.is_symlink():
        return []
    try:
        if library.stat().st_size > MAX_VDF_BYTES:
            return []
        content = library.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return []
    # Steam stores backslash-escaped Windows paths in VDF strings.
    roots = []
    for raw in re.findall(r'"path"\s+"([^"]+)"', content, re.IGNORECASE):
        value = raw.replace("\\\\", "\\")
        if value and not any(c in value for c in ('\x00', '\r', '\n')):
            roots.append(Path(value))
    return roots


def discover_game_installs(environment: Mapping[str, str] | None = None) -> list[Path]:
    """Bounded, read-only EA/Steam/Epic defaults; no scans of saves or profiles."""
    env = os.environ if environment is None else environment
    pf = env.get("ProgramFiles") or env.get("PROGRAMFILES")
    pfx = env.get("ProgramFiles(x86)") or env.get("PROGRAMFILES(X86)")
    bases = list(dict.fromkeys(Path(x) for x in (pf, pfx) if x))
    game_dirs: list[Path] = []
    for base in bases:
        game_dirs += [
            base / "EA Games" / "The Sims 4",
            base / "Electronic Arts" / "The Sims 4",
            base / "Origin Games" / "The Sims 4",
            base / "Epic Games" / "The Sims 4",
            base / "Steam" / "steamapps" / "common" / "The Sims 4",
        ]
        for library_root in _steam_libraries(base / "Steam"):
            game_dirs.append(library_root / "steamapps" / "common" / "The Sims 4")
    found: dict[str, Path] = {}
    for game_dir in game_dirs:
        for name in GAME_NAMES:
            candidate = game_dir / "Game" / "Bin" / name
            if _candidate(candidate):
                resolved = candidate.resolve(strict=True)
                found.setdefault(str(resolved).casefold(), resolved)
    return list(found.values())


def select_game(installs: list[Path], selected: str | Path | None = None) -> Path:
    if selected is not None:
        return validate_game_exe(selected)
    if not installs:
        raise FirstRunError("SIMS4_NOT_FOUND_SELECT_INSTALLED_EXE")
    if len(installs) > 1:
        raise FirstRunError("MULTIPLE_SIMS4_INSTALLATIONS_SELECT_ONE")
    return validate_game_exe(installs[0])


def plan_journey(mode: str, goal: str = "balanced") -> dict[str, object]:
    if mode not in MODES:
        raise FirstRunError("CHOOSE_EXISTING_OR_NEW")
    if goal not in GOALS:
        raise FirstRunError("UNKNOWN_CAS_GOAL")
    if mode == "existing":
        return {
            "state": "PLAYER_SAVE_SELECTION_REQUIRED",
            "mode": mode,
            "next_step": "In The Sims 4, choose Load Game, review the slot, and press Play.",
            "save_selection": "PLAYER_ONLY_NO_AUTOMATIC_RESUME",
            "automatic_input": False,
            "gameplay_proved": False,
        }
    return {
        "state": "PLAYER_CREATE_A_SIM_REQUIRED",
        "mode": mode,
        "next_step": "In The Sims 4 choose New Game; create/place your Sim before Live Mode.",
        "cas_advice": {"goal": goal, **GOALS[goal]},
        "cas_changes_applied": False,
        "automatic_input": False,
        "gameplay_proved": False,
    }


def launch_game(
    executable: str | Path, *,
    user_clicked_launch: bool,
    popen: Callable[..., object] = subprocess.Popen,
) -> dict[str, object]:
    if sys.platform != "win32":
        raise FirstRunError("LOCAL_WINDOWS_GAME_HOST_REQUIRED")
    if user_clicked_launch is not True:
        raise FirstRunError("EXPLICIT_GAME_LAUNCH_CONSENT_REQUIRED")
    target = validate_game_exe(executable)
    # Direct file dispatch only. Never use shell=True or manipulate EA/Steam login.
    child = popen([str(target)], cwd=str(target.parent), close_fds=True)
    return {
        "state": "GAME_LAUNCH_DISPATCHED_NOT_LIVE_MODE",
        "path": str(target),
        "process_id": getattr(child, "pid", None),
        "proof_ceiling": "PROCESS_DISPATCH_ONLY_NOT_GAMEPLAY_OR_SAVE_LOAD",
    }
