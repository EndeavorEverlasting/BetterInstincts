#!/usr/bin/env python3
"""Deterministic DIY / household skill-force via Sims cheat console.

Order (durable — do not skip):
  soft-focus → Ctrl+Shift+C → testingcheats enabled true →
  stats.set_skill_level <stat> <N> × skills (Cooking/Fitness/NaturalLiving last) →
  ACCEPT_OFFERED_REWARD_TRAIT (Enter + OK hotspot; never Cancel)

Household: --members N (observed portrait count) → for each member Space-select →
dispatch. --detach returns immediately with a worker receipt (opt-in, never autorun).

Typing owner: scripts.win32_input.type_text (keybd_event). Evaluate-only unless
--execute. Disposable lab only; never edits saves. Not BI-005.

Examples:
  python -m scripts.diy_skill_force catalog
  python -m scripts.diy_skill_force plan --bundle full_unlock
  python -m scripts.diy_skill_force level --bundle full_unlock --execute --process-id PID --session-id ID
  python -m scripts.diy_skill_force household --members 3 --bundle full_unlock
  python -m scripts.diy_skill_force household --members 3 --execute --detach --process-id PID --session-id ID
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from betterinstincts.diy_skill_force import (
    DiySkillForceError,
    catalog_snapshot,
    plan_household_skill_force,
    plan_skill_force,
    skills_panel_observation_policy,
    steps_to_commands,
)

OUTPUT = ROOT / "dist" / "game-host"


class GateError(ValueError):
    pass


def _focus(process_id: int | None, *, click_client: bool = False) -> dict:
    """Soft-focus Sims without stealing Build tools (no center click by default)."""
    import ctypes

    from scripts.game_host import focus

    report = focus(process_id=process_id)
    user32 = ctypes.windll.user32
    hwnd = int(report["hwnd"])
    VK_MENU = 0x12
    user32.keybd_event(VK_MENU, 0, 0, 0)
    user32.keybd_event(VK_MENU, 0, 2, 0)
    fg = user32.GetForegroundWindow()
    tid_fg = user32.GetWindowThreadProcessId(fg, None)
    tid_t = user32.GetWindowThreadProcessId(hwnd, None)
    user32.AttachThreadInput(tid_fg, tid_t, True)
    user32.BringWindowToTop(hwnd)
    user32.AllowSetForegroundWindow(-1)
    user32.SetForegroundWindow(hwnd)
    user32.SetActiveWindow(hwnd)
    user32.AttachThreadInput(tid_fg, tid_t, False)
    # Synthetic Alt unlock counts as last-input; age past interop idle (15s)
    # so screen_admit confirm does not immediately PAUSE_FOR_PLAYER.
    time.sleep(15.25)
    if click_client:
        from ctypes import wintypes

        rect = wintypes.RECT()
        user32.GetClientRect(hwnd, ctypes.byref(rect))
        pt = wintypes.POINT(rect.right // 2, rect.bottom // 2)
        user32.ClientToScreen(hwnd, ctypes.byref(pt))
        from scripts.win32_input import send_click

        send_click(int(pt.x), int(pt.y), between_sec=0.04)
        time.sleep(0.2)
    fg_ok = user32.GetForegroundWindow() == hwnd
    report["foreground_ok"] = fg_ok
    report["soft_focus"] = not click_client
    if not fg_ok:
        raise GateError("SIMS_FOREGROUND_REQUIRED_FOR_CHEAT_CONSOLE")
    return report


def _play_brief_observe_repause(
    *,
    play_seconds: int | None = None,
    play_key: str = "1",
    pause_key: str = "0",
) -> dict:
    """Bounded Live tick for Skills-panel refresh, then always re-pause.

    Robust verify: play 5–10s @ 1x → caller captures/analyzes → pause (0).
    Never leaves sim speed running. Not main-menu Resume.
    """
    from scripts.win32_input import type_text

    policy = skills_panel_observation_policy(purpose="verify")
    seconds = int(play_seconds if play_seconds is not None else policy["play_seconds"])
    seconds = max(int(policy["min_play_seconds"]), min(int(policy["max_play_seconds"]), seconds))
    play = str(play_key or policy["play_key"] or "1")[:1]
    pause = str(pause_key or policy["pause_key"] or "0")[:1]
    # Speed keys are typed into Live HUD (console must be closed).
    type_text(play)
    time.sleep(float(seconds))
    type_text(pause)
    time.sleep(0.35)
    return {
        "step": "PLAY_BRIEF_OBSERVE_REPAUSE",
        "action": "PLAY_BRIEF_OBSERVE_REPAUSE",
        "play_key": play,
        "pause_key": pause,
        "play_seconds": seconds,
        "always_repause": True,
        "panel_status": "FRESH_PANEL_AFTER_PLAY_BRIEF",
        "note": "Capture Skills panel between play and pause; do not leave clock running.",
    }


def _accept_offered_reward_trait(step: dict, *, hwnd: int) -> dict:
    """Confirm offered mastery/reward-trait dialogs. Never Cancel."""
    import ctypes
    from ctypes import wintypes

    from scripts.win32_input import send_click, tap_vk

    if step.get("never_press_cancel") is False:
        raise GateError("REWARD_TRAIT_CANCEL_FORBIDDEN")
    rounds = max(1, int(step.get("max_rounds") or 3))
    fractions = list(step.get("ok_click_client_fractions") or [[0.50, 0.72]])
    user32 = ctypes.windll.user32
    rect = wintypes.RECT()
    user32.GetClientRect(int(hwnd), ctypes.byref(rect))
    actions: list[str] = []
    for _ in range(rounds):
        # Enter is the durable primary confirm for Sims OK dialogs.
        tap_vk(0x0D)
        actions.append("ENTER")
        time.sleep(0.2)
        for frac in fractions:
            if not isinstance(frac, (list, tuple)) or len(frac) != 2:
                continue
            fx, fy = float(frac[0]), float(frac[1])
            pt = wintypes.POINT(
                int(rect.left + (rect.right - rect.left) * fx),
                int(rect.top + (rect.bottom - rect.top) * fy),
            )
            user32.ClientToScreen(int(hwnd), ctypes.byref(pt))
            send_click(int(pt.x), int(pt.y), between_sec=0.04)
            actions.append(f"OK_CLICK_CLIENT:{fx:.2f},{fy:.2f}")
            time.sleep(0.18)
    return {
        "step": "ACCEPT_OFFERED_REWARD_TRAIT",
        "actions": actions,
        "never_press_cancel": True,
    }


def _execute_plan(
    plan: dict,
    *,
    process_id: int | None,
    close_console: bool = False,
    session_id: str | None = None,
    idle_ms: int = 15000,
    verify_skills_panel: bool = False,
    verify_play_seconds: int | None = None,
) -> dict:
    """Mode-agnostic skill force: no F1, no Esc spam — tandem with Build/Live/Buy."""
    if sys.platform != "win32":
        raise GateError("LOCAL_WINDOWS_GAME_HOST_REQUIRED")
    commands = steps_to_commands(plan)
    if commands[0] != "testingcheats enabled true":
        raise GateError("TESTINGCHEATS_ENABLED_TRUE_REQUIRED")
    if any(s.get("step") == "ENSURE_LIVE_MODE" and s.get("required") for s in (plan.get("steps") or [])):
        raise GateError("ENSURE_LIVE_MODE_FORBIDDEN_IN_MODE_AGNOSTIC_STACK")
    from betterinstincts.control_handoff import DEFAULT_IDLE_MS, HandoffError, MIN_IDLE_MS
    from betterinstincts.screen_admit import admitted_screen_lease, require_execute_session

    if isinstance(idle_ms, bool) or not isinstance(idle_ms, int) or idle_ms < MIN_IDLE_MS:
        raise GateError("IDLE_THRESHOLD_OUT_OF_RANGE")
    idle_ms = int(idle_ms if idle_ms else DEFAULT_IDLE_MS)

    try:
        require_execute_session(session_id, process_id)
    except HandoffError as exc:
        raise GateError(str(exc)) from exc
    with admitted_screen_lease(
        int(process_id),
        str(session_id),
        idle_ms=idle_ms,
        focus_fn=lambda: _focus(process_id),
    ) as ensure_ready:
        try:
            handoff = ensure_ready()
        except HandoffError as exc:
            raise GateError(str(exc)) from exc
        focus_report = _focus(process_id)
        hwnd = int(focus_report["hwnd"])
        time.sleep(0.2)
        # Durable console open in whatever mode the operator is in: Ctrl+Shift+C
        _toggle_cheat_console()
        time.sleep(0.15)
        _refocus_cheat_console()
        dispatched: list[str] = []
        reward_accepts: list[dict] = []
        testing_alias_sent = False
        for step in plan.get("steps") or []:
            name = str(step.get("step") or "")
            if name == "ACTIVATE_TESTING_CHEATS":
                cmd = str(step.get("command") or "")
                _type_cheat_line(cmd)
                dispatched.append(cmd)
                alias = step.get("alias")
                if isinstance(alias, str) and alias.strip() and not testing_alias_sent:
                    _type_cheat_line(alias.strip())
                    dispatched.append(alias.strip())
                    testing_alias_sent = True
                continue
            if name == "SET_SKILL_LEVEL":
                cmd = str(step.get("command") or "")
                if not cmd:
                    continue
                _type_cheat_line(cmd)
                dispatched.append(cmd)
                continue
            if name == "ACCEPT_OFFERED_REWARD_TRAIT" and step.get("required"):
                reward_accepts.append(_accept_offered_reward_trait(step, hwnd=hwnd))
                # Re-focus cheat console after OK clicks.
                _refocus_cheat_console()
                continue
        if close_console or verify_skills_panel:
            # Never Esc-close: Esc opens pause MENU and breaks household traverse.
            _toggle_cheat_console()
            time.sleep(0.25)
        panel_verify = None
        if verify_skills_panel:
            panel_verify = _play_brief_observe_repause(play_seconds=verify_play_seconds)
    return {
        "state": "DIY_SKILL_FORCE_DISPATCHED",
        "commands": dispatched,
        "reward_accepts": reward_accepts,
        "accept_reward_dialogs": bool(plan.get("accept_reward_dialogs")),
        "typing_owner": plan.get("typing_owner", "scripts/win32_input.type_text"),
        "open_console": "Ctrl+Shift+C",
        "mode_agnostic": True,
        "forced_live_mode": False,
        "game_mode": plan.get("game_mode", "unknown"),
        "skills": plan.get("skills"),
        "level": plan.get("level"),
        "skills_panel_observation": plan.get("skills_panel_observation"),
        "skills_panel_verify": panel_verify,
        "focus": focus_report,
        "handoff": handoff,
        "session_id": session_id,
        "proof_ceiling": plan.get("proof_ceiling"),
        "not_bi005": True,
        "next": (
            "Skills panel LOCAL_OBSERVED after PLAY_BRIEF_OBSERVE_REPAUSE"
            if panel_verify
            else "Dispatch done while paused; panel still UNPROVEN_STALE until play-brief verify"
        ),
    }


def _toggle_cheat_console() -> dict:
    """Open/close cheat console via Ctrl+Shift+C.

    Prefer this over Escape: Esc while Live often opens the pause MENU and
    blocks household Space-traverse / skill typing.
    """
    from scripts.win32_input import send_vk, tap_vk

    send_vk(0x11)  # CTRL
    send_vk(0x10)  # SHIFT
    tap_vk(0x43)   # C
    send_vk(0x10, up=True)
    send_vk(0x11, up=True)
    time.sleep(0.45)
    return {"step": "TOGGLE_CHEAT_CONSOLE", "chord": "Ctrl+Shift+C"}


def _refocus_cheat_console() -> None:
    """Click the top console strip so Enter submits the cheat line."""
    from scripts.win32_input import send_click

    send_click(250, 16, between_sec=0.04)
    time.sleep(0.12)


def _type_cheat_line(cmd: str) -> None:
    """Type one cheat and submit with Enter (keybd_event), then pause.

    Live cert (P83): computer_type newlines do not submit Sims console lines;
    durable host must use type_text + Enter (or type_text with embedded \\n).
    """
    from scripts.win32_input import tap_vk, type_text

    _refocus_cheat_console()
    type_text(str(cmd))
    time.sleep(0.08)
    tap_vk(0x0D)
    time.sleep(0.45)


def _select_next_household_member() -> dict:
    """EA Space = next household Sim. Console must already be closed."""
    from scripts.win32_input import tap_vk

    # VK_SPACE
    tap_vk(0x20)
    time.sleep(0.55)
    return {"step": "SELECT_NEXT_HOUSEHOLD_SIM", "key": "SPACE"}


def _execute_household(
    household_plan: dict,
    *,
    process_id: int | None,
    session_id: str | None = None,
    idle_ms: int = 15000,
    verify_skills_panel: bool = False,
    verify_play_seconds: int | None = None,
) -> dict:
    """Traverse every member and dispatch the same skill plan on each."""
    member_results: list[dict] = []
    for slot in household_plan.get("member_plans") or []:
        index = int(slot.get("member_index") or 0)
        select = slot.get("select")
        if isinstance(select, dict) and select.get("required"):
            # Close console with Ctrl+Shift+C — never Esc (MENU collision).
            _toggle_cheat_console()
            time.sleep(0.25)
            select_report = _select_next_household_member()
        else:
            select_report = {"step": "KEEP_CURRENT_SELECTION", "member_index": index}
        live = _execute_plan(
            slot["plan"],
            process_id=process_id,
            close_console=True,
            session_id=session_id,
            idle_ms=idle_ms,
            verify_skills_panel=verify_skills_panel,
            verify_play_seconds=verify_play_seconds,
        )
        member_results.append(
            {
                "member_index": index,
                "select": select_report,
                "live": live,
            }
        )
    return {
        "state": "HOUSEHOLD_SKILL_FORCE_DISPATCHED",
        "household_members": household_plan.get("household_members"),
        "required_residual_skills": household_plan.get("required_residual_skills"),
        "members": member_results,
        "close_console_before_space": "CTRL_SHIFT_C_TOGGLE",
        "proof_ceiling": household_plan.get("proof_ceiling"),
        "not_bi005": True,
    }


def _detach_household_worker(argv_tail: list[str], *, receipt: Path) -> dict:
    """Opt-in async worker: return immediately; progress lands in receipt."""
    receipt = receipt.resolve()
    if not receipt.is_relative_to(OUTPUT.resolve()):
        raise GateError("RECEIPT_OUTSIDE_DIST_GAME_HOST")
    receipt.parent.mkdir(parents=True, exist_ok=True)
    log_path = receipt.with_suffix(receipt.suffix + ".log")
    cmd = [sys.executable, "-m", "scripts.diy_skill_force", *argv_tail, "--receipt", str(receipt)]
    creationflags = 0
    close_fds = True
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(
            subprocess, "DETACHED_PROCESS", 0x00000008
        )
        close_fds = False
    log_fh = open(log_path, "w", encoding="utf-8")
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            stdin=subprocess.DEVNULL,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
            close_fds=close_fds,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
    finally:
        log_fh.close()
    meta = {
        "state": "HOUSEHOLD_SKILL_FORCE_DETACHED",
        "worker_pid": int(proc.pid),
        "receipt": str(receipt.relative_to(ROOT)),
        "log": str(log_path.relative_to(ROOT)),
        "command": cmd,
        "note": "Opt-in worker — not autorun. Poll receipt for member progress.",
    }
    receipt.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return meta


def _add_common_execute_flags(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--bundle", default=None, help="Named bundle (default full_unlock when no --skill)")
    ap.add_argument("--skill", action="append", default=[], help="Repeatable skill id")
    ap.add_argument("--level", type=int, default=None)
    ap.add_argument("--game-mode", default="unknown")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--close-console", action="store_true")
    ap.add_argument(
        "--no-accept-reward-dialogs",
        action="store_true",
        help="Skip Enter/OK accept of offered mastery/reward traits",
    )
    ap.add_argument(
        "--verify-skills-panel",
        action="store_true",
        help="After dispatch: play 5–10s @ 1x, then pause (Skills panel refresh)",
    )
    ap.add_argument(
        "--verify-play-seconds",
        type=int,
        default=None,
        help="Bounded play seconds for --verify-skills-panel (5–10)",
    )
    ap.add_argument("--process-id", type=int, default=None)
    ap.add_argument("--session-id", default=None, help="ACTIVE host_listener session for --execute")
    ap.add_argument(
        "--idle-ms",
        type=int,
        default=15000,
        help="Player-idle gate ms (contract floor 15000; below raises IDLE_THRESHOLD_OUT_OF_RANGE)",
    )
    ap.add_argument("--receipt", type=Path, default=None)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("catalog")

    pl = sub.add_parser("plan")
    pl.add_argument("--bundle", default=None, help="Named bundle (default full_unlock when no --skill)")
    pl.add_argument("--skill", action="append", default=[], help="Repeatable skill id")
    pl.add_argument("--level", type=int, default=None)
    pl.add_argument("--game-mode", default="unknown")
    pl.add_argument(
        "--no-accept-reward-dialogs",
        action="store_true",
        help="Skip ACCEPT_OFFERED_REWARD_TRAIT steps",
    )

    lv = sub.add_parser("level")
    _add_common_execute_flags(lv)

    hh = sub.add_parser("household", help="Traverse all household members and skill-force each")
    hh.add_argument(
        "--members",
        type=int,
        required=True,
        help="Exact observed Live household portrait count (1..8)",
    )
    _add_common_execute_flags(hh)
    hh.add_argument(
        "--detach",
        action="store_true",
        help="Opt-in async worker: return immediately; write progress under dist/game-host",
    )

    args = p.parse_args(argv)
    try:
        if args.command == "catalog":
            result = catalog_snapshot()
        elif args.command == "household":
            skill_ids = list(args.skill) or None
            bundle = args.bundle
            if isinstance(bundle, str) and not bundle.strip():
                bundle = None
            if bundle is None and not skill_ids:
                bundle = "full_unlock"
            accept = None if not getattr(args, "no_accept_reward_dialogs", False) else False
            plan = plan_household_skill_force(
                members=int(args.members),
                skill_ids=skill_ids,
                bundle=bundle,
                level=args.level,
                game_mode=args.game_mode,
                accept_reward_dialogs=accept,
            )
            result = {"plan": plan, "execute": False, "detached": False}
            if args.execute and args.detach:
                receipt = args.receipt
                if receipt is None:
                    receipt = OUTPUT / "household-skill-force-async-receipt.json"
                elif not receipt.is_absolute():
                    receipt = ROOT / receipt
                # Child must not detach again.
                child_argv = [
                    "household",
                    "--members",
                    str(int(args.members)),
                    "--bundle",
                    str(bundle or "full_unlock"),
                    "--execute",
                    "--close-console",
                ]
                if args.level is not None:
                    child_argv.extend(["--level", str(args.level)])
                if skill_ids:
                    for sid in skill_ids:
                        child_argv.extend(["--skill", sid])
                if args.no_accept_reward_dialogs:
                    child_argv.append("--no-accept-reward-dialogs")
                if args.verify_skills_panel:
                    child_argv.append("--verify-skills-panel")
                if args.verify_play_seconds is not None:
                    child_argv.extend(["--verify-play-seconds", str(args.verify_play_seconds)])
                if args.process_id is not None:
                    child_argv.extend(["--process-id", str(args.process_id)])
                if args.session_id:
                    child_argv.extend(["--session-id", str(args.session_id)])
                if args.idle_ms:
                    child_argv.extend(["--idle-ms", str(int(args.idle_ms))])
                result = _detach_household_worker(child_argv, receipt=Path(receipt))
                result["plan"] = {
                    "state": plan["state"],
                    "household_members": plan["household_members"],
                    "required_residual_skills": plan.get("required_residual_skills"),
                    "bundle": plan.get("bundle"),
                }
                result["detached"] = True
                result["execute"] = True
            elif args.execute:
                result["live"] = _execute_household(
                    plan,
                    process_id=args.process_id,
                    session_id=args.session_id,
                    idle_ms=int(args.idle_ms),
                    verify_skills_panel=bool(args.verify_skills_panel),
                    verify_play_seconds=args.verify_play_seconds,
                )
                result["execute"] = True
        else:
            skill_ids = list(args.skill) or None
            bundle = args.bundle
            if isinstance(bundle, str) and not bundle.strip():
                bundle = None
            if bundle is None and not skill_ids:
                bundle = "full_unlock"
            accept = None if not getattr(args, "no_accept_reward_dialogs", False) else False
            plan = plan_skill_force(
                skill_ids=skill_ids,
                bundle=bundle,
                level=args.level,
                game_mode=args.game_mode,
                accept_reward_dialogs=accept,
            )
            result = {"plan": plan, "execute": False}
            if args.command == "level" and args.execute:
                result["live"] = _execute_plan(
                    plan,
                    process_id=args.process_id,
                    close_console=bool(args.close_console),
                    session_id=args.session_id,
                    idle_ms=int(args.idle_ms),
                    verify_skills_panel=bool(args.verify_skills_panel),
                    verify_play_seconds=args.verify_play_seconds,
                )
                result["execute"] = True

        receipt = getattr(args, "receipt", None)
        if receipt is not None and not (args.command == "household" and getattr(args, "detach", False)):
            path = receipt if receipt.is_absolute() else ROOT / receipt
            path = path.resolve()
            if not path.is_relative_to(OUTPUT.resolve()):
                raise GateError("RECEIPT_OUTSIDE_DIST_GAME_HOST")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            result["receipt"] = str(path.relative_to(ROOT))

        print(json.dumps(result, sort_keys=True))
        return 0
    except (DiySkillForceError, GateError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
