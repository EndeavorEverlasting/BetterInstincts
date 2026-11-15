"""Set up BetterInstincts and open your installed copy of The Sims 4."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
PLAN = {
    "schema": "betterinstincts.container-play/v1",
    "steps": ["install_toolkit", "start_windows_game"],
}
STARTUP_SOURCES = ("bootstrap.py", "scripts/play.py", "scripts/first_run.py",
                   "scripts/smart_start.py", "betterinstincts/first_run.py")
WIN_COMMAND = "py -3 -m scripts.play"
SUCCESS_MESSAGES = {
    "GAME_LAUNCH_DISPATCHED_SAVE_HANDOFF":
        "The Sims 4 launch was requested. Choose your save or start a new game in Sims.",
    "GAME_ALREADY_RUNNING_NO_DUPLICATE_LAUNCH":
        "The Sims 4 is already open. Continue in your current game.",
}
LAUNCH_GUIDANCE = {
    "GAME_SELECTION_REQUIRED":
        f'Find your installed Game\\Bin\\TS4_x64.exe and rerun {WIN_COMMAND} '
        '--game-exe "C:\\path\\to\\Game\\Bin\\TS4_x64.exe".',
    "BLOCKED_MULTIPLE_ACTIVE_GAMES":
        "Choose which open game to keep. Rerun when only one Sims process remains.",
    "SIMS_STARTED_DURING_PREFLIGHT_NO_DUPLICATE_LAUNCH":
        "The Sims 4 started while the launcher was checking. Continue in that game.",
    "GAME_DISPATCH_RESULT_UNTRUSTWORTHY":
        "Check whether The Sims 4 opened before requesting another launch.",
}


class PlayBlocked(Exception):
    def __init__(self, step: str, reason: str, next_step: str, *, detail: str = ""):
        super().__init__(reason)
        self.step = step
        self.reason = reason
        self.next_step = next_step
        self.detail = detail


def startup_plan() -> dict:
    sources = {}
    for name in STARTUP_SOURCES:
        # Universal newlines give the same source identity in Windows and Docker.
        source = (ROOT / name).read_text(encoding="utf-8")
        compile(source, name, "exec")
        sources[name] = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return {**PLAN, "sources": sources}


def docker_plan(docker: str, progress: Callable[[str], None]) -> dict:
    progress("Preparing the BetterInstincts startup container. The first build may take a minute.")
    image = "betterinstincts-startup:local"
    try:
        subprocess.run(
            [docker, "build", "--tag", image, str(ROOT)],
            check=True, capture_output=True, encoding="utf-8", errors="replace", timeout=600,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise PlayBlocked(
            "container_build", "DOCKER_BUILD_FAILED",
            "Start Docker in Linux container mode and check access to Docker Hub, then rerun.",
            detail=str(getattr(exc, "stderr", None) or exc)[-1200:].strip(),
        ) from exc

    try:
        expected = startup_plan()
        result = subprocess.run(
            [docker, "run", "--rm", "--pull=never", "--network=none", "--read-only",
             "--cap-drop=ALL", "--security-opt=no-new-privileges", image],
            check=True, capture_output=True, encoding="utf-8", errors="replace", timeout=30,
        )
        if len(result.stdout) > 2048 or json.loads(result.stdout) != expected:
            raise ValueError("Unexpected startup plan")
    except (OSError, SyntaxError, ValueError, subprocess.SubprocessError) as exc:
        raise PlayBlocked(
            "container_plan", "DOCKER_STARTUP_PLAN_FAILED",
            "Check Docker and rerun from the current BetterInstincts checkout.",
            detail=str(getattr(exc, "stderr", None) or exc)[-1200:].strip(),
        ) from exc
    return expected


@contextmanager
def windows_startup_lock():
    """Serialize cooperating Play commands in the Windows desktop session."""
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.ReleaseMutex.argtypes = kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.ReleaseMutex.restype = kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.CreateMutexW(None, True, r"Local\BetterInstincts.Play")
    error = ctypes.get_last_error()
    if not handle:
        raise ctypes.WinError(error)
    try:
        if error == 183:  # ERROR_ALREADY_EXISTS: another launcher owns it.
            raise PlayBlocked("toolkit_install", "PLAY_ALREADY_IN_PROGRESS",
                              "Let the open BetterInstincts launcher finish.")
        try:
            yield
        finally:
            kernel.ReleaseMutex(handle)
    finally:
        kernel.CloseHandle(handle)


def play_on_windows(game_exe: Path | None, progress: Callable[[str], None]) -> dict:
    from bootstrap import install, paths
    from scripts.first_run import requested_start

    with windows_startup_lock():
        progress("Setting up your BetterInstincts toolkit.")
        try:
            toolkit = install(paths())
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            raise PlayBlocked(
                "toolkit_install", "TOOLKIT_INSTALL_FAILED",
                "Run py -3 bootstrap.py doctor to inspect the toolkit location.",
                detail=str(exc),
            ) from exc

        progress("Checking for The Sims 4.")
        try:
            game = requested_start(game_exe)
        except (OSError, ValueError) as exc:
            game = {"state": "GAME_LAUNCH_BLOCKED", "reason": str(exc)}

    if game["state"] in SUCCESS_MESSAGES:
        return {"status": "ok", "stage": "complete", "toolkit": toolkit, "game": game,
                "next_step": SUCCESS_MESSAGES[game["state"]]}
    reason = game.get("reason", game["state"])
    return {"status": "blocked", "stage": "game_launch", "toolkit": toolkit,
            "game": game, "reason": reason, "next_step": LAUNCH_GUIDANCE.get(
                game["state"] if game["state"] == "GAME_SELECTION_REQUIRED" else reason,
                "Check the game or its launcher for an error before trying again.",
            )}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true", help="Check the container on any Docker host")
    mode.add_argument("--game-exe", type=Path, help="Choose an installed Sims executable")
    mode.add_argument("--emit-plan", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--json", action="store_true", help="Return one JSON result without prompts")
    args = parser.parse_args(argv)
    if args.emit_plan:
        print(json.dumps(startup_plan()))
        return 0

    def progress(message: str) -> None:
        if not args.json:
            print(message, flush=True)

    progress("Welcome to BetterInstincts.")
    try:
        if not args.plan and sys.platform != "win32":
            raise PlayBlocked("host", "WINDOWS_GAME_HOST_REQUIRED",
                              f"Run {WIN_COMMAND} from the checkout on the PC with The Sims 4.")
        docker = shutil.which("docker")
        if docker is None:
            raise PlayBlocked("container_build", "DOCKER_NOT_FOUND",
                              "Install or start Docker, then rerun from the BetterInstincts checkout.")
        if not args.plan and shutil.which("git") is None:
            raise PlayBlocked("toolkit_install", "GIT_NOT_FOUND",
                              "Install Git for Windows and reopen this terminal, then rerun.")
        plan = docker_plan(docker, progress)
        if args.plan:
            result = {"status": "ok", "stage": "container_plan", "plan": plan,
                      "next_step": f"Startup container is ready. On your Sims PC, run {WIN_COMMAND}."}
        else:
            result = play_on_windows(args.game_exe, progress)
    except (PlayBlocked, OSError) as exc:
        if isinstance(exc, OSError):
            exc = PlayBlocked("toolkit_install", "WINDOWS_STARTUP_LOCK_UNAVAILABLE",
                              "Check whether BetterInstincts is already starting, then rerun.",
                              detail=str(exc))
        result = {"status": "blocked", "stage": exc.step, "reason": exc.reason,
                  "next_step": exc.next_step}
        if exc.detail:
            result["detail"] = exc.detail

    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        if result["status"] == "blocked":
            stage = result["stage"].replace("_", " ")
            print(f"Stopped at {stage} ({result['reason']}).", file=sys.stderr)
            if result.get("detail"):
                print(result["detail"], file=sys.stderr)
        print(result["next_step"], file=sys.stdout if result["status"] == "ok" else sys.stderr)
    return 0 if result["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
