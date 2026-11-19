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
from tempfile import TemporaryDirectory
from time import monotonic, sleep
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
                   "scripts/save_catalog.py", "scripts/startup_handoff.py")
PROFILE_SOURCES = ("scripts/instance_settings.py", "betterinstincts/installation_profiles.py",
                   "contracts/installation-profiles.v1.json")
WIN_COMMAND = "py -3 -m scripts.play"
CONTAINER_ENGINES = ("docker", "podman")
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


def startup_plan(*, profile_launch: bool = False) -> dict:
    sources = {}
    names = STARTUP_SOURCES + PROFILE_SOURCES if profile_launch else STARTUP_SOURCES
    for name in names:
        # Universal newlines give the same source identity in Windows and Docker.
        source = (ROOT / name).read_text(encoding="utf-8")
        if name.endswith(".json"):
            json.loads(source)
        else:
            compile(source, name, "exec")
        sources[name] = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return {**PLAN, "sources": sources}


def container_plan(cli: str, progress: Callable[[str], None], *, engine: str,
                   profile_launch: bool = False) -> dict:
    name = {"docker": "Docker", "podman": "Podman"}[engine]
    if engine == "podman":
        try:
            info = subprocess.run(
                [cli, "info", "--format", "{{.Host.OS}}"],
                check=True, capture_output=True, encoding="utf-8", errors="replace", timeout=15,
            )
            if info.stdout.strip() != "linux":
                raise ValueError("Podman did not report a Linux container host")
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            raise PlayBlocked(
                "container_engine", "PODMAN_ENGINE_NOT_READY",
                "Check podman info. On Windows or macOS, inspect podman machine list and "
                "start your configured machine if needed.",
                detail=str(getattr(exc, "stderr", None) or exc)[-1200:].strip(),
            ) from exc

    progress("Preparing the BetterInstincts startup container. The first build may take a minute.")
    image = ("localhost/" if engine == "podman" else "") + "betterinstincts-startup:local"
    try:
        with TemporaryDirectory(prefix="betterinstincts-startup-") as temp:
            context = Path(temp)
            for file in ("Dockerfile", ".dockerignore", *STARTUP_SOURCES, *PROFILE_SOURCES):
                source = ROOT / file
                if not source.is_file() or source.resolve() != source:
                    raise ValueError(f"Startup source must be a regular checkout file: {file}")
                target = context / file
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            subprocess.run(
                [cli, "build", "--tag", image, str(context)],
                check=True, capture_output=True, encoding="utf-8", errors="replace", timeout=600,
            )
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        guidance = ("Start Docker in Linux container mode and check access to Docker Hub, then rerun."
                    if engine == "docker" else "Check the Podman build details and access to Docker Hub, then rerun.")
        raise PlayBlocked(
            "container_build", f"{engine.upper()}_BUILD_FAILED", guidance,
            detail=str(getattr(exc, "stderr", None) or exc)[-1200:].strip(),
        ) from exc

    try:
        expected = startup_plan(profile_launch=profile_launch)
        plan_args = ["--profile-launch"] if profile_launch else []
        result = subprocess.run(
            [cli, "run", "--rm", "--pull=never", "--network=none", "--read-only",
             "--cap-drop=ALL", "--security-opt=no-new-privileges", image, *plan_args],
            check=True, capture_output=True, encoding="utf-8", errors="replace", timeout=30,
        )
        if len(result.stdout) > 4096 or json.loads(result.stdout) != expected:
            raise ValueError("Unexpected startup plan")
    except (OSError, SyntaxError, ValueError, subprocess.SubprocessError) as exc:
        raise PlayBlocked(
            "container_plan", f"{engine.upper()}_STARTUP_PLAN_FAILED",
            f"Check {name} and rerun from the current BetterInstincts checkout.",
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
    selection: dict | None = None, launch_profile: dict | None = None,
    choose_household: bool = False,
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
                                 upgrade_parts=upgrade_parts, selection=selection,
                                 launch_profile=launch_profile, choose_household=choose_household)

    if game["state"] in SUCCESS_MESSAGES:
        return {"status": "ok", "stage": "complete", "toolkit": toolkit, "game": game,
                "next_step": SUCCESS_MESSAGES[game["state"]]}
    reason = game.get("reason", game["state"])
    return {"status": "blocked", "stage": "game_launch", "toolkit": toolkit,
            "game": game, "reason": reason, "next_step": LAUNCH_GUIDANCE.get(
                game["state"] if game["state"] == "GAME_SELECTION_REQUIRED" else reason,
                "Check the game or its launcher for an error before trying again.",
            )}



def profile_startup_selection(
    mode: str, process, bridge, packet: dict, profile: dict, *, context_path: Path, context: dict,
    force: bool, progress: Callable[[str], None],
) -> tuple[str, dict]:
    """Resolve the player choice, wait for handoff, then refresh before using it."""
    from betterinstincts.control_handoff import decide
    from betterinstincts.installation_profiles import set_preferred_household, view
    from betterinstincts.player_presence import probe_windows
    from scripts.instance_settings import choose_launch_household
    from scripts.launch_save_route import startup_household_choices
    from scripts.smart_start import require_same_game_process

    choices = startup_household_choices(mode, process, packet, path=context_path, context=context)
    if not choices:
        raise ValueError("NO_HOUSEHOLD_IN_CURRENT_SAVE_CATALOG")
    remembered = profile["preferred_household_id"]
    if force or (remembered is not None and remembered not in choices) or (
            remembered is None and len(choices) > 1):
        chosen = choose_launch_household(choices)
        if chosen not in choices:
            raise ValueError("HOUSEHOLD_CHOICE_CANCELLED")
    else:
        chosen = remembered or next(iter(choices))

    idle_ms = profile["launch"]["idle_ms"]
    deadline = monotonic() + idle_ms / 1000 + 15
    progress("Waiting for you to finish using the computer before continuing Play.")
    while True:
        require_same_game_process(process)
        presence = decide(probe_windows(process.pid), session_active=True, idle_ms=idle_ms)
        if presence["screen_control_allowed"]:
            break
        if presence["reason"] != "RECENT_HUMAN_INPUT" or monotonic() >= deadline:
            raise ValueError("STARTUP_YIELD_TO_PLAYER:" + presence["reason"])
        sleep(0.5)

    refreshed = bridge.read_save_catalog()
    if (refreshed.get("capture_ref") == packet.get("capture_ref")
            or chosen not in startup_household_choices(
                mode, process, refreshed, path=context_path, context=context)):
        raise ValueError("CURRENT_HOUSEHOLD_CHOICE_REVALIDATION_FAILED")
    if chosen != remembered:
        profile = set_preferred_household(chosen, profile_id=profile["profile_id"],
                                          expected_revision=profile["revision"])
    if view()["revision"] != profile["revision"]:
        raise ValueError("LAUNCH_PREFERENCES_CHANGED")
    return chosen, refreshed


def complete_play(
    mode: str, game: dict, toolkit: dict, context_path: Path | None,
    receipt_path: Path, receipt: dict, progress: Callable[[str], None],
    *, upgrade_parts: bool = False, selection: dict | None = None,
    launch_profile: dict | None = None, choose_household: bool = False,
) -> dict:
    from scripts.game_host import navigate_startup_save, profile
    from scripts.launch_receipt import gap, write_result
    from scripts.launch_save_route import load_context, route_mode
    from scripts.save_catalog import read_catalog
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
        try:
            context_keys = load_context(context_path).keys() if context_path is not None else ()
        except (ValueError, OSError):
            context_keys = ()
        if upgrade_parts and "native_startup" not in context_keys:
            return pending("existing_game", "EXISTING_SESSION_PRESERVED",
                           "Keep this session. Use the exact-build menu observer to admit an open main menu.",
                           "scripts/play.py", actor="repository")
        semantic = bool({"save_catalog", "selection", "native_startup"}.intersection(context_keys))
        if not semantic and not selection and not launch_profile:
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
        if launch_profile:
            return pending("save_context", "PROFILE_STARTUP_BINDING_REQUIRED",
                           f"Keep this game open. Configure the private startup/{mode}.json binding.",
                           "scripts/startup_handoff.py", actor="repository")
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
    startup_bridge = None
    try:
        startup_context = load_context(context_path)
        if launch_profile and "native_startup" not in startup_context:
            raise ValueError("PROFILE_STARTUP_BINDING_REQUIRED")
        if "native_startup" in startup_context:
            from scripts.startup_handoff import StartupBridge

            if (startup_context.get("schema") != "betterinstincts.startup-save-context/v1"
                    or startup_context.get("startup_mode") != mode
                    or startup_context.get("game_version") != process.game_version):
                raise ValueError("NATIVE_STARTUP_CONTEXT_MODE_OR_BUILD_UNVERIFIED")
            startup_bridge = StartupBridge(context_path, startup_context, process)
            result["startup_binding"] = {"scope": startup_bridge.scope, "sha256": startup_bridge.digest}
            write_result(receipt_path, {**receipt, **result, "stage": "startup_catalog"})
            route_options["save_catalog"] = (startup_bridge.read_save_catalog(catalog_only=True)
                                             if upgrade_parts else startup_bridge.read_save_catalog())
            if launch_profile:
                household, packet = profile_startup_selection(
                    mode, process, startup_bridge, route_options["save_catalog"], launch_profile,
                    context_path=context_path, context=startup_context,
                    force=choose_household, progress=progress,
                )
                # The player's verified ID replaces any older household name in
                # the private context. Title and roster constraints still apply.
                route_options.update(save_catalog=packet,
                                     selection={"household_id": household, "household_name": None})
    except (OSError, ValueError) as exc:
        if launch_profile and str(exc) == "HOUSEHOLD_CHOICE_CANCELLED":
            return pending("startup_catalog", str(exc),
                           "Sims stays open. Use BetterInstincts Play again when you are ready to choose.",
                           "scripts/instance_settings.py")
        if launch_profile and str(exc) == "PROFILE_STARTUP_BINDING_REQUIRED":
            return pending("save_context", str(exc),
                           f"Keep this game open. Configure the private startup/{mode}.json binding.",
                           "scripts/startup_handoff.py", actor="repository")
        return pending("startup_catalog", str(exc),
                       "Check the current Sims session and exact-build startup observation.",
                       "scripts/startup_handoff.py", actor="repository")
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
    catalog = route_options.get("save_catalog", startup_context.get("save_catalog"))
    catalog_capture = catalog["capture_ref"] if route.get("semantic_catalog") else None

    def checkpoint(step: str) -> None:
        result["automatic_steps"].append(step)
        write_result(receipt_path, {**receipt, **result, "stage": dispatch_stage})

    def native_load_checkpoint(report: dict) -> None:
        result["native_save_load"] = report
        write_result(receipt_path, {**receipt, **result, "stage": dispatch_stage})

    native_load = None
    try:
        context = load_context(context_path)
        if (startup_bridge is not None or catalog_capture is not None) and context != startup_context:
            raise ValueError("NATIVE_STARTUP_CONTEXT_CHANGED")
        bridge = None
        if (launch_profile and startup_bridge
                and "load_selected_save" in startup_bridge.supported_operations):
            from scripts.startup_handoff import dispatch_profile_save

            result["startup_binding"]["catalog_capture"] = catalog_capture
            native_load = dispatch_profile_save(
                startup_bridge, process, route, catalog, launch_profile["launch"]["idle_ms"], native_load_checkpoint)
        else:
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
                if catalog_capture is not None:
                    result["restock_binding"] = {"scope": bridge.scope, "sha256": bridge.digest,
                                                 "catalog_capture": catalog_capture}
                listener = save_navigation_listener()
            elif startup_bridge is not None:
                from scripts.lab_upgrade_parts import save_navigation_listener

                listener = save_navigation_listener("native-startup-launch", note="Opt-in native startup")
            if startup_bridge is not None:
                result["startup_binding"]["catalog_capture"] = catalog_capture
            if startup_bridge is not None or catalog_capture is not None:
                write_result(receipt_path, {**receipt, **result, "stage": dispatch_stage})
            require_same_game_process(process)
            title = route.get("candidate_save_name")
            progress(f"Opening {title}." if title else "Opening the oldest eligible disposable save.")
            with listener as session_id:
                if catalog_capture is not None:
                    read_catalog(process, catalog)
                navigate_startup_save(cfg, process, run_id=route["successor_run_id"],
                                      session_id=session_id, checkpoint=checkpoint,
                                      **({"idle_ms": launch_profile["launch"]["idle_ms"]} if launch_profile else {}),
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
    if not upgrade_parts and startup_bridge is not None:
        from scripts.startup_handoff import continue_startup

        def startup_checkpoint(report):
            result["startup_handoff"] = report
            if report.get("save_readback"):
                result["save_state"] = "SELECTED_SAVE_OBSERVED"
                if native_load:
                    result["native_save_load"].update(state="OBSERVED", capture=report["save_readback"])
            write_result(receipt_path, {**receipt, **result, "stage": "startup_handoff"})

        try:
            continue_startup(startup_bridge, route, catalog_capture, startup_checkpoint,
                             **({"profile_idle_ms": launch_profile["launch"]["idle_ms"],
                                 "expected_load_command": native_load}
                                if launch_profile else {}))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return pending("startup_handoff", str(exc),
                           "Reconcile the current save, household or responder using this launch receipt.",
                           "scripts/startup_handoff.py", actor="repository")
        return {**result, "status": "ok", "stage": "complete",
                "next_step": "The active household is in Live Mode and BetterInstincts is responding.",
                "automation_gaps": []}
    if bridge is not None:
        from scripts.lab_upgrade_parts import run_restock

        def restock_checkpoint(report):
            result["restock"] = report
            if report.get("save_readback"):
                result["save_state"] = "DEV_SAVE_MAP_OBSERVED"
            write_result(receipt_path, {**receipt, **result, "stage": "lab_upgrade_parts"})

        try:
            progress("Restocking upgrade parts for each available Sim.")
            report = run_restock(bridge, restock_checkpoint, expected_slot=route.get("candidate_slot"),
                                 expected_roster=route.get("household_member_ids", ()),
                                 catalog_capture=catalog_capture)
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
    mode.add_argument("--plan", action="store_true", help="Check only the portable startup container")
    mode.add_argument("--game-exe", type=Path, help="Choose an installed Sims executable")
    mode.add_argument("--emit-plan", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--container-engine", choices=CONTAINER_ENGINES,
                        help="Select a CLI explicitly (default: Docker if present, otherwise Podman)")
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
    parser.add_argument("--profile-launch", action="store_true",
                        help="Use the current BetterInstincts profile and household picker")
    parser.add_argument("--choose-household", action="store_true",
                        help="Choose a different household from the current game catalog")
    parser.add_argument("--checkout-head", help=argparse.SUPPRESS)
    parser.add_argument("--json", action="store_true", help="Return one JSON result without prompts")
    args = parser.parse_args(argv)
    if args.container_engine and (args.native_start or args.emit_plan):
        parser.error("--container-engine requires a container-backed Play command")
    if args.mode == "prod":
        args.mode = "production"
    selection = {key: value for key, value in (
        ("household_name", args.household), ("household_id", args.household_id),
        ("expected_save_name", args.save_name),
        ("minimum_members", args.minimum_household_members), ("required_members", args.household_member),
    ) if value is not None}
    if args.choose_household and not args.profile_launch:
        parser.error("--choose-household requires --profile-launch")
    if args.choose_household and (args.plan or args.emit_plan):
        parser.error("--choose-household is for playing on the Windows host")
    if args.profile_launch and (args.mode or selection or args.upgrade_parts):
        parser.error("--profile-launch owns mode and household selection")
    if args.upgrade_parts:
        if args.mode == "production" or args.plan or args.emit_plan:
            parser.error("--upgrade-parts requires the Windows dev play route")
        args.mode = "dev"
    if selection and (args.mode != "dev" or not args.save_context):
        parser.error("household and save-name choices require dev mode and --save-context")
    if args.save_context and (args.plan or args.emit_plan):
        parser.error("--save-context is for playing on the Windows host")
    if (args.mode or args.native_start) and args.plan:
        parser.error("--mode is for playing on the Windows host")
    if args.checkout_head and not re.fullmatch(r"[a-f0-9]{40}", args.checkout_head):
        parser.error("invalid verified checkout SHA")
    if args.emit_plan:
        print(json.dumps(startup_plan(profile_launch=args.profile_launch)))
        return 0
    if not args.plan:
        args.mode = args.mode or "production"

    def progress(message: str) -> None:
        if not args.json:
            print(message, flush=True)

    progress("Welcome to BetterInstincts.")
    receipt_path, receipt, launch_profile = None, None, None
    container_engine = None
    try:
        if not args.plan and sys.platform != "win32":
            command = ("Start-BetterInstincts.cmd --upgrade-parts" if args.upgrade_parts else
                       "Start-BetterInstincts.cmd" if args.profile_launch else WIN_COMMAND)
            next_step = ("Rerun this Play command with the same options on the Windows Sims host."
                         if selection or args.save_context else f"Run {command} on the PC with The Sims 4.")
            raise PlayBlocked("host", "WINDOWS_GAME_HOST_REQUIRED", next_step)
        if args.profile_launch and not args.plan:
            from betterinstincts.installation_profiles import view

            launch_profile = view()
            args.mode = launch_profile["launch"]["mode"]
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
            elif (launch_profile or args.mode == "production") and args.save_context is None:
                runtime = paths()["locks"].parent
                configured = runtime / "startup" / (args.mode + ".json")
                if configured.is_file() or configured.is_symlink():
                    args.save_context = configured
                elif launch_profile and args.mode == "dev":
                    existing_lab = runtime / "lab-upgrade-parts" / "startup.json"
                    if existing_lab.is_file() or existing_lab.is_symlink():
                        args.save_context = existing_lab
            if args.checkout_head:
                receipt["checkout_head"] = args.checkout_head
            if args.checkout_head or args.upgrade_parts:
                write_result(receipt_path, receipt)
        if not args.native_start:
            container_engine = args.container_engine or "docker"
            cli = shutil.which(container_engine)
            if cli is None and args.container_engine is None:
                cli = shutil.which("podman")
                if cli is not None:
                    container_engine = "podman"
            if cli is None:
                if container_engine == "podman":
                    raise PlayBlocked("container_engine", "PODMAN_NOT_FOUND",
                                      "Install the Podman CLI for this host architecture and reopen the terminal.")
                guidance = ("Install Docker and reopen the terminal." if args.container_engine else
                            "Install Docker or the Podman CLI and reopen the terminal.")
                raise PlayBlocked("container_build", "DOCKER_NOT_FOUND", guidance)
            plan = container_plan(cli, progress, engine=container_engine, profile_launch=args.profile_launch)
        if args.plan:
            command = f"{WIN_COMMAND} --profile-launch" if args.profile_launch else WIN_COMMAND
            result = {"status": "ok", "stage": "container_plan", "plan": plan,
                      "next_step": f"Startup container is ready. On your Sims PC, run {command}."}
        else:
            result = play_on_windows(args.game_exe, progress, mode=args.mode, receipt=receipt,
                                     save_context=args.save_context, receipt_path=receipt_path, checkout=ROOT,
                                     **({"upgrade_parts": True} if args.upgrade_parts else {}),
                                     **({"launch_profile": launch_profile, "choose_household": args.choose_household}
                                        if launch_profile else {}),
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

    if container_engine is not None:
        result["container_engine"] = container_engine
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
