"""Set up BetterInstincts and open your installed copy of The Sims 4."""
from __future__ import annotations

import argparse
from contextlib import contextmanager, nullcontext
from dataclasses import asdict
import hashlib
import json
import re
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
                   "scripts/smart_start.py", "betterinstincts/first_run.py",
                   "scripts/game_host.py", "scripts/launch_save_route.py", "scripts/launch_receipt.py",
                   "scripts/lab_upgrade_parts.py", "scripts/save_candidate_priority.py",
                   "scripts/save_catalog.py")
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


class PlayBlocked(ValueError):
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
        if len(result.stdout) > 4096 or json.loads(result.stdout) != expected:
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


def play_on_windows(
    game_exe: Path | None, progress: Callable[[str], None], *,
    mode: str | None = None, save_context: Path | None = None, receipt_path: Path | None = None,
    receipt: dict | None = None, checkout: Path | None = None, upgrade_parts: bool = False,
    selection: dict | None = None,
) -> dict:
    from bootstrap import install, paths
    from scripts.first_run import requested_start

    with windows_startup_lock():
        if checkout is not None:
            progress("Using this BetterInstincts checkout.")
            toolkit = {"state": "EXISTING_CHECKOUT", "checkout": str(checkout)}
        else:
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
            game = requested_start(game_exe, identify_process=True) if mode else requested_start(game_exe)
        except (OSError, ValueError) as exc:
            game = {"state": "GAME_LAUNCH_BLOCKED", "reason": str(exc)}

        if mode is not None:
            return complete_play(mode, game, toolkit, save_context, receipt_path, receipt, progress,
                                 upgrade_parts=upgrade_parts, selection=selection)

    if game["state"] in SUCCESS_MESSAGES:
        return {"status": "ok", "stage": "complete", "toolkit": toolkit, "game": game,
                "next_step": SUCCESS_MESSAGES[game["state"]]}
    reason = game.get("reason", game["state"])
    return {"status": "blocked", "stage": "game_launch", "toolkit": toolkit,
            "game": game, "reason": reason, "next_step": LAUNCH_GUIDANCE.get(
                game["state"] if game["state"] == "GAME_SELECTION_REQUIRED" else reason,
                "Check the game or its launcher for an error before trying again.",
            )}



def complete_play(
    mode: str, game: dict, toolkit: dict, context_path: Path | None,
    receipt_path: Path, receipt: dict, progress: Callable[[str], None],
    *, upgrade_parts: bool = False, selection: dict | None = None,
) -> dict:
    from scripts.game_host import navigate_startup_save, profile
    from scripts.launch_receipt import gap, write_result
    from scripts.launch_save_route import load_context, route_mode
    from scripts.smart_start import observe_launched_process, require_same_game_process

    result = {"toolkit": toolkit, "game": game, "save_state": "NOT_OBSERVED",
              "automatic_steps": []}

    def pending(stage, reason, step, owner, *, actor=None):
        return {**result, "status": "blocked", "stage": stage, "reason": reason,
                "next_step": step, "automation_gaps": [gap(
                    stage, reason, step, owner,
                    actor=actor or ("repository" if upgrade_parts else "human_or_agent"))]}

    state = game["state"]
    if state not in SUCCESS_MESSAGES:
        reason = game.get("reason", state)
        guidance = LAUNCH_GUIDANCE.get(state, LAUNCH_GUIDANCE.get(reason,
                                   "Check the game platform or startup error before trying again."))
        return pending("game_launch", reason, guidance, "scripts/smart_start.py")
    result["launch_state"] = state
    write_result(receipt_path, {**receipt, **result, "stage": "game_process"})
    try:
        process = observe_launched_process(game)
    except (OSError, ValueError) as exc:
        out = pending("game_process", str(exc),
                      "Check whether the game opened or needs platform sign-in, then observe the current instance.",
                      "scripts/smart_start.py")
        if state == "GAME_LAUNCH_DISPATCHED_SAVE_HANDOFF":
            out["automation_gaps"].append(gap(
                "platform_sign_in", "PLATFORM_AUTHENTICATION_IF_REQUESTED",
                "Sign in through EA or Steam if prompted.", "scripts/first_run.py", actor="human",
            ))
        return out
    result["game_process"] = asdict(process)
    result["process_proof"] = "OBSERVED_WINDOWS_PROCESS_ONLY"
    existing_game = state == "GAME_ALREADY_RUNNING_NO_DUPLICATE_LAUNCH"
    if existing_game:
        lab_route = game.get("lab_save_route", {})
        if mode == "dev" and lab_route.get("state") == "PRESERVE_RUNNING_CERTIFICATION_SESSION":
            return pending("certification", "CONTINUE_ACTIVE_CERTIFICATION",
                           "Continue the active certification in the open game.",
                           "scripts/continue_certification.py")
        if upgrade_parts:
            return pending("existing_game", "EXISTING_SESSION_PRESERVED",
                           "The restock launch needs a new admitted game session.",
                           "scripts/play.py", actor="repository")
        try:
            semantic = context_path is not None and bool(
                {"save_catalog", "selection"} & load_context(context_path).keys()
            )
        except (ValueError, OSError):
            semantic = False
        if not semantic and not selection:
            if mode == "production" and context_path is not None:
                result["save_route"] = route_mode(mode, process, context_path)
            return {**result, "status": "ok", "stage": "existing_game",
                    "next_step": "The Sims 4 is already open. BetterInstincts kept your session in place.",
                    "automation_gaps": []}
    if mode == "dev" and game.get("lab_save_route", {}).get("state") in {
        "PRESERVE_RUNNING_CERTIFICATION_SESSION", "CERTIFICATION_PINNED_LAB_SAVE_ADVISORY",
        "HOLD_CERTIFICATION_PIN", "HOLD_CERTIFICATION_REVIEW",
    }:
        return pending("certification", "CONTINUE_ACTIVE_CERTIFICATION",
                       "Finish the existing certification before the oldest-save trial.",
                       "scripts/launch_save_route.py")
    if context_path is None:
        if mode == "production":
            return pending("production_save", "LATEST_SAVE_OBSERVER_AND_LOADER_REQUIRED",
                           "Use Load Game to verify and open your most recently played save.",
                           "scripts/launch_save_route.py")
        return pending("save_context", "STARTUP_SAVE_CONTEXT_REQUIRED",
                       "Supply the private dev context for the oldest eligible disposable save.",
                       "scripts/launch_save_route.py")

    route_options = {"active_map_household": True} if upgrade_parts else {}
    if selection:
        route_options["selection"] = selection
    route = route_mode(mode, process, context_path, **route_options)
    result["save_route"] = route
    selected = route.get("candidate_save_id")
    production_dispatch = mode == "production"
    if production_dispatch and route["state"] != "PRODUCTION_APPROVED_LATEST_CANDIDATE":
        title = route.get("candidate_save_name")
        if route["reason"] == "LATEST_SLOT_REQUIRES_SEPARATE_AUTHORIZATION":
            prompt = f"{title} is the newest save. This slot requires separate authorization to open."
        else:
            prompt = (f"Use Load Game to verify and open {title}." if title
                      else "Use Load Game to verify and open the most recently played save.")
        return pending("production_save", route["reason"], prompt, "scripts/launch_save_route.py")
    if not production_dispatch and route["state"] not in {
        "DEV_OLDEST_DISPOSABLE_CANDIDATE", "STANDARDIZED_OLDEST_DISPOSABLE_ADVISORY",
    }:
        if upgrade_parts:
            return pending("dev_save_candidate", route["reason"],
                           "Recover the local lab registry binding and chronological evidence.",
                           "scripts/launch_save_route.py", actor="repository")
        return pending("dev_save_candidate", route["reason"], "Resolve the disposable save or household evidence.",
                       "scripts/launch_save_route.py")

    dispatch_stage = "production_save_dispatch" if production_dispatch else "dev_save_dispatch"

    def checkpoint(step: str) -> None:
        result["automatic_steps"].append(step)
        write_result(receipt_path, {**receipt, **result, "stage": dispatch_stage})

    try:
        context = load_context(context_path)
        profile_name = context.get("navigation_profile")
        profiles = context.get("navigation_profiles")
        if isinstance(profiles, dict):
            profile_name = profiles.get(selected, profile_name)
        if (not isinstance(profile_name, str) or Path(profile_name).name != profile_name
                or not profile_name.endswith(".json")):
            raise ValueError("CALIBRATED_DEV_PROFILE_REQUIRED")
        p = context_path.parent / profile_name
        if p.is_symlink() or not p.is_file() or p.stat().st_size > 16384:
            raise ValueError("CALIBRATED_DEV_PROFILE_REQUIRED")
        cfg, _ = profile(p, **({"mode": "production"} if production_dispatch else {}))
        cfg["_profile_path"] = str(p.absolute())
        if (cfg.get("selected_save_id") != selected or cfg.get("save_registry") != context.get("registry")
                or cfg.get("game_version") != context.get("game_version")
                or (route.get("semantic_catalog") is True and
                    cfg.get("selected_slot") != route["candidate_slot"])):
            raise ValueError("DEV_PROFILE_DOES_NOT_BIND_OLDEST_CANDIDATE")
        bridge = None
        listener = nullcontext(context.get("session_id"))
        if upgrade_parts:
            from scripts.lab_upgrade_parts import NativeBridge, save_navigation_listener

            try:
                bridge = NativeBridge(context_path, context, process, route)
                bridge.require_capabilities()
            except (OSError, ValueError) as exc:
                return pending("native_restock_binding", str(exc),
                               "Bind the Windows EA observer and commands from the repository handoff.",
                               "scripts/lab_upgrade_parts.py", actor="repository")
            listener = save_navigation_listener()
        require_same_game_process(process)
        title = route.get("candidate_save_name")
        progress(f"Opening {title}." if title else "Opening the oldest eligible disposable save.")
        with listener as session_id:
            navigate_startup_save(cfg, process, run_id=route["successor_run_id"],
                                  session_id=session_id, checkpoint=checkpoint,
                                  **({"mode": "production"} if production_dispatch else {}))
        require_same_game_process(process)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        unchanged = not result["automatic_steps"]
        if unchanged and str(exc) == "DEV_PROFILE_DOES_NOT_BIND_OLDEST_CANDIDATE":
            return pending("dev_calibration", str(exc),
                           "Calibrate the chosen-save adapter for the exact oldest disposable slot.",
                           "scripts/game_host.py")
        return pending(dispatch_stage, str(exc),
                       "Observe the current game and verify its exact save and menu before any further action.",
                       "scripts/game_host.py")

    result["save_state"] = ("PRODUCTION_SAVE_PLAY_DISPATCHED" if production_dispatch
                            else "DEV_SAVE_PLAY_DISPATCHED")
    if bridge is not None:
        from scripts.lab_upgrade_parts import run_restock

        def restock_checkpoint(report):
            result["restock"] = report
            if report.get("save_readback"):
                result["save_state"] = "DEV_SAVE_MAP_OBSERVED"
            write_result(receipt_path, {**receipt, **result, "stage": "lab_upgrade_parts"})

        try:
            progress("Restocking upgrade parts for each available Sim.")
            report = run_restock(bridge, restock_checkpoint)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            if result.get("restock", {}).get("state") in ("RESTOCK_VERIFIED", "NO_AVAILABLE_PORTRAITS"):
                return pending("native_responder_handoff", str(exc),
                               "Reconcile the existing run using the native handoff receipt.",
                               "scripts/lab_upgrade_parts.py", actor="repository")
            return pending("lab_upgrade_parts", str(exc),
                           "Recover the recorded native evidence before a new restock attempt.",
                           "scripts/lab_upgrade_parts.py", actor="repository")
        return {**result, "status": "ok", "stage": "lab_upgrade_parts",
                "next_step": ("Restock verified and native responder decision observed."
                              if report["state"] == "RESTOCK_VERIFIED"
                              else "No portraits were available. Native responder decision observed."),
                "automation_gaps": []}
    return pending("save_readback", "NATIVE_SAVE_READBACK_MISSING",
                   "Verify the selected save and household in the current game.",
                   "scripts/game_host.py")

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true", help="Check the container on any Docker host")
    mode.add_argument("--game-exe", type=Path, help="Choose an installed Sims executable")
    mode.add_argument("--emit-plan", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--mode", choices=("dev", "prod", "production"),
                        help="Choose the oldest disposable lab or latest-played production route")
    parser.add_argument("--upgrade-parts", action="store_true",
                        help="Restock 99 of each computer upgrade part in the oldest eligible lab save")
    parser.add_argument("--save-context", type=Path, help="Private local save and calibration context")
    parser.add_argument("--household", help="Game-visible household name in dev mode")
    parser.add_argument("--household-id", help="Observed household ID if names are ambiguous")
    parser.add_argument("--save-name", help="Expected game-visible title of the oldest dev match")
    parser.add_argument("--minimum-household-members", type=int, help="Minimum roster size in dev mode")
    parser.add_argument("--household-member", action="append", help="Required Sim name, repeatable")
    parser.add_argument("--native-start", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--checkout-head", help=argparse.SUPPRESS)
    parser.add_argument("--json", action="store_true", help="Return one JSON result without prompts")
    args = parser.parse_args(argv)
    if args.mode == "prod":
        args.mode = "production"
    selection = {key: value for key, value in (
        ("household_name", args.household), ("household_id", args.household_id),
        ("expected_save_name", args.save_name),
        ("minimum_members", args.minimum_household_members), ("required_members", args.household_member),
    ) if value is not None}
    if selection and (args.mode != "dev" or not args.save_context or args.upgrade_parts):
        parser.error("household and save-name choices require --mode dev and --save-context")
    if args.upgrade_parts:
        if args.mode == "production" or args.plan or args.emit_plan:
            parser.error("--upgrade-parts requires the Windows dev play route")
        args.mode = "dev"
    if args.save_context and (args.plan or args.emit_plan):
        parser.error("--save-context is for playing on the Windows host")
    if (args.mode or args.native_start) and args.plan:
        parser.error("--mode is for playing on the Windows host")
    if args.checkout_head and not re.fullmatch(r"[a-f0-9]{40}", args.checkout_head):
        parser.error("invalid verified checkout SHA")
    if args.emit_plan:
        print(json.dumps(startup_plan()))
        return 0
    if not args.plan:
        args.mode = args.mode or "production"

    def progress(message: str) -> None:
        if not args.json:
            print(message, flush=True)

    progress("Welcome to BetterInstincts.")
    receipt_path, receipt = None, None
    try:
        if not args.plan and sys.platform != "win32":
            command = "Start-BetterInstincts.cmd --upgrade-parts" if args.upgrade_parts else WIN_COMMAND
            raise PlayBlocked("host", "WINDOWS_GAME_HOST_REQUIRED",
                              f"Run {command} on the PC with The Sims 4.")
        if args.mode:
            from bootstrap import paths
            from scripts.launch_receipt import begin, write_result

            try:
                receipt_path, receipt = begin(args.mode, root=paths()["locks"].parent)
            except (OSError, ValueError) as exc:
                reason = str(exc) if str(exc).startswith("PLAY_RECEIPT_") else "RECEIPT_DIRECTORY_UNAVAILABLE"
                action = ("Archive older launch receipt folders outside play-receipts, then retry."
                          if reason == "PLAY_RECEIPT_STORE_FULL_ARCHIVE_OLDER_RUNS" else
                          "Restore access to the local receipt directory before retrying.")
                raise PlayBlocked("receipt", reason, action) from exc
            if args.upgrade_parts:
                receipt["workflow"] = "OLDEST_LAB_UPGRADE_PARTS"
                if args.save_context is None:
                    args.save_context = paths()["locks"].parent / "lab-upgrade-parts" / "startup.json"
                if args.save_context.is_symlink() or not args.save_context.is_file():
                    raise PlayBlocked("save_context", "LAB_RESTOCK_CONTEXT_UNAVAILABLE",
                                      "Restore the local restock binding documented in the repository handoff.")
            if args.checkout_head:
                receipt["checkout_head"] = args.checkout_head
            if args.checkout_head or args.upgrade_parts:
                write_result(receipt_path, receipt)
        docker = shutil.which("docker")
        if docker is None and not args.native_start:
            raise PlayBlocked("container_build", "DOCKER_NOT_FOUND",
                              "Install or start Docker, then rerun from the BetterInstincts checkout.")
        if not args.native_start:
            plan = docker_plan(docker, progress)
        if args.plan:
            result = {"status": "ok", "stage": "container_plan", "plan": plan,
                      "next_step": f"Startup container is ready. On your Sims PC, run {WIN_COMMAND}."}
        else:
            result = play_on_windows(args.game_exe, progress, mode=args.mode, receipt=receipt,
                                     save_context=args.save_context, receipt_path=receipt_path, checkout=ROOT,
                                     **({"upgrade_parts": True} if args.upgrade_parts else {}),
                                     **({"selection": selection} if selection else {}))
    except (PlayBlocked, OSError, ValueError) as exc:
        if not isinstance(exc, PlayBlocked):
            exc = PlayBlocked("startup", "STARTUP_PREFLIGHT_FAILED",
                              "Check the local BetterInstincts startup details before retrying.",
                              detail=str(exc))
        result = {"status": "blocked", "stage": exc.step, "reason": exc.reason,
                  "next_step": exc.next_step}
        if exc.detail:
            result["detail"] = exc.detail

    if args.mode:
        from scripts.launch_receipt import gap, write_result

        if result["status"] == "blocked" and "automation_gaps" not in result:
            result["automation_gaps"] = [gap(result["stage"], result["reason"], result["next_step"],
                                               "scripts/play.py",
                                               actor="repository" if args.upgrade_parts else "human_or_agent")]
        if receipt_path is not None and receipt is not None:
            result = {**receipt, **result, "receipt": str(receipt_path)}
            try:
                write_result(receipt_path, result)
            except (OSError, ValueError) as exc:
                result["status"] = "blocked"
                result["automation_gaps"].append(gap("receipt", "RECEIPT_WRITE_FAILED",
                                                    "Recover the startup receipt destination.",
                                                    "scripts/launch_receipt.py"))
                result["stage"] = "receipt"
                result["reason"] = "RECEIPT_WRITE_FAILED"
                result["next_step"] = "Recover the local receipt before retrying any game action."
                result["detail"] = str(exc)
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        if result["status"] == "blocked":
            stage = result["stage"].replace("_", " ")
            print(f"Stopped at {stage} ({result['reason']}).", file=sys.stderr)
            if result.get("detail"):
                print(result["detail"], file=sys.stderr)
        print(result["next_step"], file=sys.stdout if result["status"] == "ok" else sys.stderr)
        choices = result.get("save_route", {}).get("household_choices", {})
        if choices:
            labels = sorted(f"{name} ({identity})" for identity, name in choices.items())
            print("Available households:", ", ".join(labels), file=sys.stderr)
        if result.get("receipt"):
            print("Launch receipt:", result["receipt"])
    return 0 if result["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
