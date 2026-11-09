#!/usr/bin/env python3
"""Deterministic DIY skill-force via Sims cheat console.

Order (durable — do not skip):
  soft-focus → Ctrl+Shift+C → testingcheats enabled true →
  stats.set_skill_level <stat> <N> × skills

Applies to the currently selected Sim/Servo. Evaluate-only unless --execute.
Disposable lab only; never edits saves. Not BI-005 skill-growth certification.

Examples:
  python -m scripts.diy_skill_force catalog
  python -m scripts.diy_skill_force plan --bundle diy_maker
  python -m scripts.diy_skill_force level --bundle diy_maker --level 10
  python -m scripts.diy_skill_force level --bundle diy_maker --execute --process-id PID --session-id ID
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from betterinstincts.diy_skill_force import (
    DiySkillForceError,
    catalog_snapshot,
    plan_skill_force,
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
    time.sleep(0.35)
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


def _execute_plan(
    plan: dict,
    *,
    process_id: int | None,
    close_console: bool = False,
    session_id: str | None = None,
    idle_ms: int = 15000,
) -> dict:
    """Mode-agnostic skill force: no F1, no Esc spam — tandem with Build/Live/Buy."""
    if sys.platform != "win32":
        raise GateError("LOCAL_WINDOWS_GAME_HOST_REQUIRED")
    commands = steps_to_commands(plan)
    if commands[0] != "testingcheats enabled true":
        raise GateError("TESTINGCHEATS_ENABLED_TRUE_REQUIRED")
    if any(s.get("step") == "ENSURE_LIVE_MODE" and s.get("required") for s in (plan.get("steps") or [])):
        raise GateError("ENSURE_LIVE_MODE_FORBIDDEN_IN_MODE_AGNOSTIC_STACK")
    from betterinstincts.control_handoff import HandoffError
    from betterinstincts.screen_admit import admitted_screen_lease, require_execute_session
    from scripts.win32_input import send_vk, tap_vk, type_unicode

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
        focus_report = {"state": "FOCUS_VIA_SCREEN_ADMIT"}
        time.sleep(0.2)
        # Durable console open in whatever mode the operator is in: Ctrl+Shift+C
        send_vk(0x11)  # CTRL
        send_vk(0x10)  # SHIFT
        tap_vk(0x43)   # C
        send_vk(0x10, up=True)
        send_vk(0x11, up=True)
        time.sleep(0.55)
        from scripts.win32_input import send_click

        send_click(250, 16, between_sec=0.04)
        time.sleep(0.2)
        dispatched: list[str] = []
        run_cmds = list(commands)
        if run_cmds and run_cmds[0] == "testingcheats enabled true":
            run_cmds.insert(1, "testingcheats true")
        for cmd in run_cmds:
            type_unicode(cmd)
            tap_vk(0x0D)
            time.sleep(0.45)
            dispatched.append(cmd)
        if close_console:
            tap_vk(0x1B)
    return {
        "state": "DIY_SKILL_FORCE_DISPATCHED",
        "commands": dispatched,
        "open_console": "Ctrl+Shift+C",
        "mode_agnostic": True,
        "forced_live_mode": False,
        "game_mode": plan.get("game_mode", "unknown"),
        "skills": plan.get("skills"),
        "level": plan.get("level"),
        "focus": focus_report,
        "handoff": handoff,
        "session_id": session_id,
        "proof_ceiling": plan.get("proof_ceiling"),
        "not_bi005": True,
        "next": "Open Skills panel on the selected Sim/Servo; LOCAL_OBSERVED only",
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("catalog")

    pl = sub.add_parser("plan")
    pl.add_argument("--bundle", default=None, help="Named bundle (default diy_maker when no --skill)")
    pl.add_argument("--skill", action="append", default=[], help="Repeatable skill id")
    pl.add_argument("--level", type=int, default=None)
    pl.add_argument("--game-mode", default="unknown")

    lv = sub.add_parser("level")
    lv.add_argument("--bundle", default=None, help="Named bundle (default diy_maker when no --skill)")
    lv.add_argument("--skill", action="append", default=[], help="Repeatable skill id")
    lv.add_argument("--level", type=int, default=None)
    lv.add_argument("--game-mode", default="unknown")
    lv.add_argument("--execute", action="store_true")
    lv.add_argument("--close-console", action="store_true")
    lv.add_argument("--process-id", type=int, default=None)
    lv.add_argument("--session-id", default=None, help="ACTIVE host_listener session for --execute")
    lv.add_argument("--idle-ms", type=int, default=15000)
    lv.add_argument("--receipt", type=Path, default=None)

    args = p.parse_args(argv)
    try:
        if args.command == "catalog":
            result = catalog_snapshot()
        else:
            skill_ids = list(args.skill) or None
            bundle = args.bundle
            if isinstance(bundle, str) and not bundle.strip():
                bundle = None
            if bundle is None and not skill_ids:
                bundle = "diy_maker"
            plan = plan_skill_force(
                skill_ids=skill_ids,
                bundle=bundle,
                level=args.level,
                game_mode=args.game_mode,
            )
            result = {"plan": plan, "execute": False}
            if args.command == "level" and args.execute:
                result["live"] = _execute_plan(
                    plan,
                    process_id=args.process_id,
                    close_console=bool(args.close_console),
                    session_id=args.session_id,
                    idle_ms=int(args.idle_ms),
                )
                result["execute"] = True

        receipt = getattr(args, "receipt", None)
        if receipt is not None:
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
