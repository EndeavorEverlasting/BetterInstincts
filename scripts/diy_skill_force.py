#!/usr/bin/env python3
"""Deterministic DIY / household skill-force via Sims cheat console.

Order (durable — do not skip):
  soft-focus → Ctrl+Shift+C → testingcheats enabled true →
  stats.set_skill_level <stat> <N> × skills (Cooking/Fitness/NaturalLiving last) →
  ACCEPT_OFFERED_REWARD_TRAIT (Enter + OK hotspot; never Cancel)

Household: --members N (observed portrait count) → skill-round-robin:
    for each skill, Space across every portrait and set that one skill, then the
    next skill (completion ledger skips already-maxed cells). --detach returns a
    worker receipt (opt-in, never autorun). Bootstrap: python bootstrap.py
    household-skills -- --members N ...

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
    completed_skill_ids_for_member,
    completion_member_key,
    default_completion_ledger_path,
    empty_completion_ledger,
    load_completion_ledger,
    plan_household_skill_force,
    plan_skill_force,
    record_skill_dispatched,
    save_completion_ledger,
    skills_panel_observation_policy,
    steps_to_commands,
)

OUTPUT = ROOT / "dist" / "game-host"


class GateError(ValueError):
    pass


def _cursor_pos() -> tuple[int, int] | None:
    """Screen cursor position, or None if unavailable."""
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    pt = POINT()
    if not ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
        return None
    return int(pt.x), int(pt.y)


def _wait_for_input_idle(
    process_id: int,
    *,
    idle_ms: int,
    timeout_sec: float = 600.0,
    poll_sec: float = 0.5,
    progress_path: Path | None = None,
) -> dict:
    """Poll until trusted idle for skill-force admit.

    Only trustworthy OS last-input age >= idle_ms permits continuation.
    A stationary mouse during typing or dictation is NOT idle, even when
    synthetic tools repeatedly reset GetLastInputInfo. Detached workers may
    wait longer but must never substitute cursor stability for input evidence.
    """
    from betterinstincts.player_presence import probe_windows

    need = int(idle_ms)
    deadline = time.monotonic() + max(1.0, float(timeout_sec))
    max_age = 0
    samples = 0
    last_progress = 0.0
    stable_origin = _cursor_pos()
    stable_since = time.monotonic()
    while True:
        probe = probe_windows(int(process_id))
        age = probe.last_input_age_ms
        samples += 1
        pos = _cursor_pos()
        now = time.monotonic()
        if pos is None or stable_origin is None or pos != stable_origin:
            stable_origin = pos
            stable_since = now
        cursor_stable_ms = int(max(0.0, (now - stable_since) * 1000.0))
        if type(age) is int and age >= 0 and probe.probe_ok:
            max_age = max(max_age, age)
            if (
                age >= need
                and not probe.operator_declared_playing
                and not probe.player_directed_queue
                and not probe.operator_busy
            ):
                return {
                    "state": "INPUT_IDLE_READY",
                    "reason": "LAST_INPUT_AGE",
                    "last_input_age_ms": age,
                    "idle_ms": need,
                    "max_age_ms": max_age,
                    "cursor_stable_ms": cursor_stable_ms,
                    "samples": samples,
                }
        if progress_path is not None and (now - last_progress) >= 10.0:
            last_progress = now
            try:
                progress_path.write_text(
                    json.dumps(
                        {
                            "state": "WAITING_INPUT_IDLE",
                            "last_input_age_ms": age,
                            "max_age_ms": max_age,
                            "cursor_stable_ms": cursor_stable_ms,
                            "need_idle_ms": need,
                            "samples": samples,
                            "remaining_timeout_sec": max(0.0, deadline - now),
                        },
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n",
                    encoding="utf-8",
                )
            except OSError:
                pass
        if now >= deadline:
            raise GateError(
                "CONTINUOUS_INPUT_BLOCKING_ADMIT:"
                f"max_age_ms={max_age};cursor_stable_ms={cursor_stable_ms};"
                f"need_idle_ms={need};"
                "stop_mouse_motion_sidecars_then_retry"
            )
        time.sleep(poll_sec)


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
    # Speed keys must hit Live HUD. Caller must close the cheat console first
    # (see _execute_plan); if console is open, '1'/'0' become console text.
    from scripts.win32_input import send_click

    send_click(960, 400, between_sec=0.04)
    time.sleep(0.15)
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
    """Never dispatch unverified Enter/OK presses into arbitrary dialogs.

    Skill upgrades can surface preference Yes/No, occult, unrelated rewards,
    or no dialog at all. A fresh observation must reach its owning one-step
    adapter before UI input is authorized.
    """
    if step.get("never_press_cancel") is False:
        raise GateError("REWARD_TRAIT_CANCEL_FORBIDDEN")
    return {
        "step": "ACCEPT_OFFERED_REWARD_TRAIT",
        "state": "NEEDS_DIALOG_IDENTIFICATION",
        "actions": [],
        "never_press_cancel": True,
        "next": "REOBSERVE_AND_CLASSIFY_REWARD_OR_PREFERENCE_PROMPT",
        "proof_ceiling": "NO_REWARD_DIALOG_INPUT_DISPATCHED",
    }


def _execute_plan(
    plan: dict,
    *,
    process_id: int | None,
    close_console: bool = False,
    session_id: str | None = None,
    idle_ms: int = 15000,
    wait_idle_timeout_sec: float = 600.0,
    wait_idle_progress_path: Path | None = None,
    verify_skills_panel: bool = False,
    verify_play_seconds: int | None = None,
    completion_ledger_path: Path | None = None,
    member_key: str | None = None,
    member_index: int = 0,
) -> dict:
    """Mode-agnostic skill force: no F1, no Esc spam — tandem with Build/Live/Buy."""
    if sys.platform != "win32":
        raise GateError("LOCAL_WINDOWS_GAME_HOST_REQUIRED")
    if plan.get("skip_dispatch") or plan.get("state") == "SKILL_FORCE_MEMBER_ALREADY_MAXED":
        return {
            "state": "SKILL_FORCE_MEMBER_ALREADY_MAXED",
            "skipped": True,
            "member_key": member_key,
            "member_index": member_index,
            "skipped_skill_ids": list(plan.get("skipped_skill_ids") or []),
            "commands": [],
            "safe_cursor_rest": _park_safe_cursor_rest(),
            "proof_ceiling": plan.get("proof_ceiling"),
            "pass_claim": "FORBIDDEN_UNTIL_SKILLS_PANEL_LOCAL_OBSERVED",
            "note": "Completion ledger: nothing left to type for this member",
        }
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
    idle_wait = _wait_for_input_idle(
        int(process_id),
        idle_ms=idle_ms,
        timeout_sec=float(wait_idle_timeout_sec),
        progress_path=wait_idle_progress_path,
    )
    from betterinstincts.player_presence import probe_windows

    # Never falsify last_input_age_ms. The old stationary-pointer fallback
    # could seize the keyboard from a human using dictation or typing.
    def _admit_probe():
        return probe_windows(int(process_id))

    with admitted_screen_lease(
        int(process_id),
        str(session_id),
        idle_ms=idle_ms,
        focus_fn=lambda: _focus(process_id),
        probe_fn=_admit_probe,
    ) as ensure_ready:
        try:
            handoff = ensure_ready()
        except HandoffError as exc:
            raise GateError(str(exc)) from exc
        handoff = {**handoff, "idle_wait": idle_wait}
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
                if completion_ledger_path is not None:
                    mkey = member_key or completion_member_key(
                        session_id, int(member_index)
                    )
                    ledger = load_completion_ledger(completion_ledger_path)
                    record_skill_dispatched(
                        ledger,
                        member_key=mkey,
                        skill_id=str(step.get("skill_id") or ""),
                        skill_stat=str(step.get("skill_stat") or ""),
                        level=int(step.get("level") or plan.get("level") or 10),
                        evidence="HOST_CHEAT_TYPED",
                    )
                    save_completion_ledger(ledger, completion_ledger_path)
                continue
            if name == "ACCEPT_OFFERED_REWARD_TRAIT" and step.get("required"):
                reward_accepts.append(_accept_offered_reward_trait(step, hwnd=hwnd))
                # Do not blind-ENTER: this might be a like/dislike or occult
                # dialog. Never claim a reward acceptance from these steps.
                continue
        if close_console or verify_skills_panel:
            # Never Esc-close: Esc opens pause MENU and breaks household traverse.
            _toggle_cheat_console()
            time.sleep(0.25)
        panel_verify = None
        if verify_skills_panel:
            panel_verify = _play_brief_observe_repause(play_seconds=verify_play_seconds)
    cursor_rest = _park_safe_cursor_rest()
    return {
        "state": "DIY_SKILL_FORCE_DISPATCHED",
        "commands": dispatched,
        "safe_cursor_rest": cursor_rest,
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
        # Fail-closed: console text / reward toasts / level-up overlays are NOT PASS.
        "pass_claim": "FORBIDDEN_UNTIL_SKILLS_PANEL_LOCAL_OBSERVED",
        "console_text_is_not_pass": True,
        "level_up_toast_is_not_pass": True,
        "panel_proof_status": (
            "PLAY_BRIEF_RAN_PANEL_STILL_REQUIRES_OPERATOR_OR_AGENT_READ"
            if panel_verify
            else "UNPROVEN_STALE_NO_PLAY_BRIEF"
        ),
        "next": (
            "Open Skills panel and LOCAL_OBSERVE max levels after PLAY_BRIEF_OBSERVE_REPAUSE; "
            "do not claim PASS from console text or level-up toasts"
            if panel_verify
            else "Dispatch done while paused; panel still UNPROVEN_STALE until play-brief + Skills panel read"
        ),
    }


def _toggle_cheat_console() -> dict:
    """Open/close cheat console via Ctrl+Shift+C.

    Prefer this over Escape: Esc while Live often opens the pause MENU and
    blocks household Space-traverse / skill typing.

    Use send_key_chord so modifiers stay held for the C tap. A bare
    send_vk/tap_vk sequence can drop SHIFT and fire screenshot (C) instead.
    """
    from scripts.win32_input import send_key_chord

    send_key_chord(["CTRL", "SHIFT", "C"], down_sec=0.06, after_sec=0.35)
    time.sleep(0.15)
    return {
        "step": "TOGGLE_CHEAT_CONSOLE",
        "chord": "Ctrl+Shift+C",
        "chord_owner": "scripts.win32_input.send_key_chord",
    }


def _refocus_cheat_console() -> None:
    """Click the top console strip so Enter submits the cheat line.

    Click may touch the top HUD, then win32_input parks SAFE_CURSOR_REST so
    the cursor is not left in the viewport edge pan band.
    """
    from scripts.win32_input import send_click

    send_click(400, 20, between_sec=0.04, safe_rest_after=True)
    time.sleep(0.12)


def _park_safe_cursor_rest() -> dict:
    """Mandatory interior park after skill-force mouse work."""
    from scripts.win32_input import park_safe_cursor_rest

    return park_safe_cursor_rest()


def _type_cheat_line(cmd: str) -> None:
    """Type one cheat and submit with embedded newline via type_text.

    Live cert (P83): computer_type newlines do not submit Sims console lines.
    Durable path: refocus strip → type_text(cmd + '\\n') so keybd_event Enter
    is part of the same typing owner (proven LOCAL_OBSERVED on Servo level-ups).
    """
    from scripts.win32_input import type_text

    _refocus_cheat_console()
    line = str(cmd).rstrip("\r\n")
    type_text(line + "\n")
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
    wait_idle_timeout_sec: float = 600.0,
    verify_skills_panel: bool = False,
    verify_play_seconds: int | None = None,
    completion_ledger_path: Path | None = None,
    redo: bool = False,
) -> dict:
    """Skill-round-robin: one skill × every portrait, then the next skill."""
    ledger_path = (
        Path(completion_ledger_path)
        if completion_ledger_path is not None
        else default_completion_ledger_path()
    )
    units = list(household_plan.get("dispatch_units") or [])
    if not units:
        # Legacy / empty plans: synthesize round-robin from member_plans + skills.
        skills = [str(s.get("id")) for s in (household_plan.get("skills") or []) if s.get("id")]
        for sid in skills:
            for slot in household_plan.get("member_plans") or []:
                units.append(
                    {
                        "skill_id": sid,
                        "member_index": int(slot.get("member_index") or 0),
                        "member_key": slot.get("member_key"),
                        "skip_dispatch": sid
                        in set(slot.get("skipped_skill_ids") or []),
                        "select_before": {"required": True} if units else None,
                    }
                )

    cell_results: list[dict] = []
    dispatched_cells = 0
    skipped_cells = 0
    first_admit = True
    first_unit = True
    target = int(household_plan.get("level") or 10)
    for unit in units:
        index = int(unit.get("member_index") or 0)
        mkey = str(unit.get("member_key") or completion_member_key(session_id, index))
        skill_id = str(unit.get("skill_id") or "").strip().lower()
        select_before = unit.get("select_before")
        if not first_unit and (
            isinstance(select_before, dict)
            or int(household_plan.get("household_members") or 1) > 1
        ):
            # Close console with Ctrl+Shift+C — never Esc (MENU collision).
            _toggle_cheat_console()
            time.sleep(0.25)
            select_report = _select_next_household_member()
        else:
            select_report = {"step": "KEEP_CURRENT_SELECTION", "member_index": index}
        first_unit = False

        # Re-check ledger at execute time so mid-run / restarted workers skip done work.
        omit: list[str] = []
        if not redo:
            ledger = load_completion_ledger(ledger_path)
            omit = sorted(
                completed_skill_ids_for_member(ledger, mkey, target_level=target)
            )
        if (
            bool(unit.get("skip_dispatch"))
            or (skill_id and skill_id in omit)
            or not skill_id
        ):
            skipped_cells += 1
            cell_results.append(
                {
                    "member_index": index,
                    "member_key": mkey,
                    "skill_id": skill_id,
                    "select": select_report,
                    "skipped": True,
                    "reason": "SKILL_ALREADY_MAXED_FOR_MEMBER",
                    "live": {
                        "state": "SKILL_FORCE_MEMBER_ALREADY_MAXED",
                        "commands": [],
                    },
                }
            )
            continue

        live_plan = plan_skill_force(
            skill_ids=[skill_id],
            bundle=None,
            level=household_plan.get("level"),
            game_mode=str(household_plan.get("game_mode") or "unknown"),
            accept_reward_dialogs=household_plan.get("accept_reward_dialogs"),
        )
        if live_plan.get("skip_dispatch") or live_plan.get("state") == (
            "SKILL_FORCE_MEMBER_ALREADY_MAXED"
        ):
            skipped_cells += 1
            cell_results.append(
                {
                    "member_index": index,
                    "member_key": mkey,
                    "skill_id": skill_id,
                    "select": select_report,
                    "skipped": True,
                    "reason": "SKILL_ALREADY_MAXED_FOR_MEMBER",
                    "live": {
                        "state": "SKILL_FORCE_MEMBER_ALREADY_MAXED",
                        "commands": [],
                    },
                }
            )
            continue

        live = _execute_plan(
            live_plan,
            process_id=process_id,
            close_console=True,
            session_id=session_id,
            idle_ms=idle_ms,
            # First real dispatch waits the long quiet window; later ones are shorter.
            wait_idle_timeout_sec=(
                float(wait_idle_timeout_sec)
                if first_admit
                else min(60.0, float(wait_idle_timeout_sec))
            ),
            verify_skills_panel=verify_skills_panel,
            verify_play_seconds=verify_play_seconds,
            completion_ledger_path=ledger_path,
            member_key=mkey,
            member_index=index,
        )
        first_admit = False
        dispatched_cells += 1
        cell_results.append(
            {
                "member_index": index,
                "member_key": mkey,
                "skill_id": skill_id,
                "select": select_report,
                "skipped": False,
                "live": live,
            }
        )
    state = (
        "HOUSEHOLD_SKILL_FORCE_ALL_MEMBERS_ALREADY_MAXED"
        if dispatched_cells == 0
        else "HOUSEHOLD_SKILL_FORCE_DISPATCHED"
    )
    cursor_rest = _park_safe_cursor_rest()
    return {
        "state": state,
        "dispatch_order": household_plan.get("dispatch_order") or "skill_round_robin",
        "household_members": household_plan.get("household_members"),
        "cells_dispatched": dispatched_cells,
        "cells_skipped_already_maxed": skipped_cells,
        "members_dispatched": len(
            {c["member_index"] for c in cell_results if not c.get("skipped")}
        ),
        "required_residual_skills": household_plan.get("required_residual_skills"),
        "completion_ledger": str(ledger_path),
        "cells": cell_results,
        "close_console_before_space": "CTRL_SHIFT_C_TOGGLE",
        "safe_cursor_rest": cursor_rest,
        "proof_ceiling": household_plan.get("proof_ceiling"),
        "not_bi005": True,
        "pass_claim": "FORBIDDEN_UNTIL_SKILLS_PANEL_LOCAL_OBSERVED",
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
    ap.add_argument(
        "--wait-idle-timeout-sec",
        type=float,
        default=600.0,
        help="Max seconds to wait for OS input idle before admit (detached agents reuse this)",
    )
    ap.add_argument("--receipt", type=Path, default=None)
    ap.add_argument(
        "--completion-ledger",
        type=Path,
        default=None,
        help="Durable per-member skill completion JSON (default dist/game-host/diy-skill-force-completion.json)",
    )
    ap.add_argument(
        "--redo",
        action="store_true",
        help="Ignore completion ledger and re-dispatch all requested skills",
    )


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
        help="Exact observed Live household portrait count (N = whatever the household is)",
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
            ledger_path = (
                Path(args.completion_ledger)
                if getattr(args, "completion_ledger", None)
                else default_completion_ledger_path()
            )
            if not ledger_path.is_absolute():
                ledger_path = ROOT / ledger_path
            ledger = (
                empty_completion_ledger()
                if getattr(args, "redo", False)
                else load_completion_ledger(ledger_path)
            )
            plan = plan_household_skill_force(
                members=int(args.members),
                skill_ids=skill_ids,
                bundle=bundle,
                level=args.level,
                game_mode=args.game_mode,
                accept_reward_dialogs=accept,
                session_id=getattr(args, "session_id", None),
                completion_ledger=ledger,
                redo=bool(getattr(args, "redo", False)),
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
                if getattr(args, "wait_idle_timeout_sec", None) is not None:
                    child_argv.extend(
                        ["--wait-idle-timeout-sec", str(float(args.wait_idle_timeout_sec))]
                    )
                child_argv.extend(["--completion-ledger", str(ledger_path)])
                if getattr(args, "redo", False):
                    child_argv.append("--redo")
                result = _detach_household_worker(child_argv, receipt=Path(receipt))
                result["plan"] = {
                    "state": plan["state"],
                    "household_members": plan["household_members"],
                    "members_needing_work": plan.get("members_needing_work"),
                    "required_residual_skills": plan.get("required_residual_skills"),
                    "bundle": plan.get("bundle"),
                }
                result["completion_ledger"] = str(ledger_path.relative_to(ROOT)) if ledger_path.is_relative_to(ROOT) else str(ledger_path)
                result["detached"] = True
                result["execute"] = True
            elif args.execute:
                result["live"] = _execute_household(
                    plan,
                    process_id=args.process_id,
                    session_id=args.session_id,
                    idle_ms=int(args.idle_ms),
                    wait_idle_timeout_sec=float(args.wait_idle_timeout_sec),
                    verify_skills_panel=bool(args.verify_skills_panel),
                    verify_play_seconds=args.verify_play_seconds,
                    completion_ledger_path=ledger_path,
                    redo=bool(getattr(args, "redo", False)),
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
            ledger_path = (
                Path(args.completion_ledger)
                if getattr(args, "completion_ledger", None)
                else default_completion_ledger_path()
            )
            if not ledger_path.is_absolute():
                ledger_path = ROOT / ledger_path
            omit: list[str] = []
            if args.command == "level" and not getattr(args, "redo", False):
                mkey = completion_member_key(getattr(args, "session_id", None), 0)
                omit = sorted(
                    completed_skill_ids_for_member(
                        load_completion_ledger(ledger_path),
                        mkey,
                        target_level=int(args.level or 10),
                    )
                )
            plan = plan_skill_force(
                skill_ids=skill_ids,
                bundle=bundle,
                level=args.level,
                game_mode=args.game_mode,
                accept_reward_dialogs=accept,
                omit_skill_ids=omit,
            )
            result = {"plan": plan, "execute": False}
            if args.command == "level" and args.execute:
                result["live"] = _execute_plan(
                    plan,
                    process_id=args.process_id,
                    close_console=bool(args.close_console),
                    session_id=args.session_id,
                    idle_ms=int(args.idle_ms),
                    wait_idle_timeout_sec=float(args.wait_idle_timeout_sec),
                    verify_skills_panel=bool(args.verify_skills_panel),
                    verify_play_seconds=args.verify_play_seconds,
                    completion_ledger_path=ledger_path,
                    member_key=completion_member_key(args.session_id, 0),
                    member_index=0,
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
