#!/usr/bin/env python3
"""Deterministic DIY / household skill-force via Sims cheat console.

Order (durable — do not skip):
  soft-focus → Ctrl+Shift+C → testingcheats enabled true →
  stats.set_skill_level <stat> <N> × skills (Cooking/Fitness/NaturalLiving last) →
  ACCEPT_OFFERED_REWARD_TRAIT (Enter + OK hotspot; never Cancel)

Household: --members N (observed portrait count) → skill-round-robin:
    for each skill, Space across every portrait and set that one skill, then the
    next skill (completion ledger skips already-maxed cells). --detach returns a
    is foreground-only; detached screen workers are denied. Bootstrap: python bootstrap.py
    household-skills -- --members N ...

Typing owner: scripts.win32_input.type_text (keybd_event). Evaluate-only unless
--execute. Disposable lab only; never edits saves. Not BI-005.

Trait safety (2026-11-09 Servo Evil incident): reward dialogs classified Evil/harmful
are never Enter/OK'd (ESCAPE_CANCEL_DIALOG or HOLD). trait-repair plans
`traits.remove_trait trait_Evil` for the selected Sim (evaluate-only). Escape is never
the household-traverse / console close (Ctrl+Shift+C) and never spammed (opens
Travel map / pause MENU); never create/activate a new Servo without operator consent.

Examples:
  python -m scripts.diy_skill_force trait-repair
  python -m scripts.diy_skill_force reward-check --trait trait_Evil
  python -m scripts.diy_skill_force ui-check --action ESCAPE --context household_traverse
  python -m scripts.diy_skill_force catalog
  python -m scripts.diy_skill_force commands --bundle remote_income
  python -m scripts.diy_skill_force skills-inventory-plan --pages 8
  python -m scripts.diy_skill_force plan --bundle full_unlock
  python -m scripts.diy_skill_force level --bundle full_unlock --execute --process-id PID --session-id ID
  python -m scripts.diy_skill_force household --members 3 --bundle full_unlock
  python -m scripts.diy_skill_force household --members 3 --execute --roster-key SIM1 --roster-key SIM2 --roster-key SIM3 --first-portrait-attested --process-id PID --session-id ID
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

from betterinstincts.household_judgment import (
    HouseholdJudgmentError, bind_household_scope, require_fixed_roster,
    require_skill_action,
)
from betterinstincts.installation_profiles import (
    InstallationProfileError, household_ledger_path, view as view_installation_profile,
)
from betterinstincts.diy_skill_force import (
    DiySkillForceError,
    assess_console_type_safety,
    assess_selection_identity,
    catalog_snapshot,
    canonical_skill_commands,
    completed_skill_ids_for_member,
    completion_member_key,
    decide_reward_dialog,
    default_completion_ledger_path,
    empty_completion_ledger,
    evaluate_member_skill_levels,
    evaluate_ui_action,
    gap_targets_from_observed_levels,
    load_completion_ledger,
    member_observed_levels_from_ledger,
    plan_force_gaps_beat,
    plan_household_skill_force,
    plan_skill_force,
    plan_skills_panel_inventory,
    plan_target_sim_skill_algorithm,
    plan_trait_repair,
    record_member_panel_snapshot,
    record_skill_dispatched,
    record_skill_panel_observed,
    resolve_force_gap_commands,
    resolve_skill_ref,
    save_completion_ledger,
    set_household_roster,
    skills_panel_observation_policy,
    steps_to_commands,
    trait_repair_commands,
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


def _snapshot_operator_foreground() -> dict:
    """Remember which app the operator is actually using (YouTube, browser, …)."""
    import ctypes

    user32 = ctypes.windll.user32
    hwnd = int(user32.GetForegroundWindow() or 0)
    return {
        "hwnd": hwnd,
        "step": "SNAPSHOT_OPERATOR_FOREGROUND",
    }


def _restore_operator_foreground(prior_hwnd: int | None, *, sims_hwnd: int | None = None) -> dict:
    """Give the operator their app back after a brief Sims input borrow.

    Interruptibility: never leave the user trapped in Sims after an agent tick.
    If prior was Sims or invalid, no-op restore.
    """
    import ctypes

    user32 = ctypes.windll.user32
    KEYEVENTF_KEYUP = 0x0002
    VK_MENU = 0x12
    prior = int(prior_hwnd or 0)
    sims = int(sims_hwnd or 0)
    if prior <= 0 or not user32.IsWindow(prior):
        return {"step": "RESTORE_OPERATOR_FOREGROUND", "restored": False, "reason": "NO_VALID_PRIOR"}
    if sims and prior == sims:
        return {"step": "RESTORE_OPERATOR_FOREGROUND", "restored": False, "reason": "PRIOR_WAS_SIMS"}
    if user32.GetForegroundWindow() == prior:
        return {"step": "RESTORE_OPERATOR_FOREGROUND", "restored": True, "already": True, "hwnd": prior}
    fg = user32.GetForegroundWindow()
    tid_fg = user32.GetWindowThreadProcessId(fg, None)
    tid_t = user32.GetWindowThreadProcessId(prior, None)
    attached = False
    if tid_fg and tid_t and tid_fg != tid_t:
        attached = bool(user32.AttachThreadInput(tid_fg, tid_t, True))
    try:
        user32.AllowSetForegroundWindow(-1)
        user32.BringWindowToTop(prior)
        user32.SetForegroundWindow(prior)
        user32.SetActiveWindow(prior)
    finally:
        if attached:
            user32.AttachThreadInput(tid_fg, tid_t, False)
    time.sleep(0.08)
    if user32.GetForegroundWindow() != prior:
        user32.keybd_event(VK_MENU, 0, 0, 0)
        time.sleep(0.02)
        user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
        user32.AllowSetForegroundWindow(-1)
        user32.SetForegroundWindow(prior)
        time.sleep(0.08)
    ok = user32.GetForegroundWindow() == prior
    return {
        "step": "RESTORE_OPERATOR_FOREGROUND",
        "restored": bool(ok),
        "hwnd": prior,
        "interop": "borrow_restore",
    }


def _borrow_sims_foreground(
    process_id: int | None,
    *,
    settle_for_interop_idle: bool = False,
    retries: int = 2,
) -> dict:
    """Briefly borrow Sims foreground for one authorized input effect.

    Operator may be in any other app (YouTube, browser, IDE). Live hotkeys need
    Sims focused briefly — then callers MUST restore the operator app.
    Does not replace the 15s interop idle gate. Mid-beat borrows stay fast;
    settle_for_interop_idle=True only when a new screen_admit lease follows Alt.
    """
    import ctypes

    from scripts.game_host import focus

    if process_id is None:
        raise GateError("PROCESS_ID_REQUIRED_FOR_SIMS_INPUT_BORROW")
    report = focus(process_id=process_id)
    user32 = ctypes.windll.user32
    hwnd = int(report["hwnd"])
    VK_MENU = 0x12
    KEYEVENTF_KEYUP = 0x0002
    used_alt_unlock = False
    fg_ok = False
    attempts = max(1, int(retries) + 1)
    for _attempt in range(attempts):
        if user32.GetForegroundWindow() == hwnd:
            fg_ok = True
            break
        fg = user32.GetForegroundWindow()
        tid_fg = user32.GetWindowThreadProcessId(fg, None)
        tid_t = user32.GetWindowThreadProcessId(hwnd, None)
        attached = False
        if tid_fg and tid_t and tid_fg != tid_t:
            attached = bool(user32.AttachThreadInput(tid_fg, tid_t, True))
        try:
            # Do not ShowWindow(SW_RESTORE) unless iconic — avoid yanking maximized
            # YouTube layouts more than necessary when Sims is already shown.
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, 9)
            user32.AllowSetForegroundWindow(-1)
            user32.SetForegroundWindow(hwnd)
            user32.SetActiveWindow(hwnd)
            user32.SetFocus(hwnd)
        finally:
            if attached:
                user32.AttachThreadInput(tid_fg, tid_t, False)
        time.sleep(0.1)
        if user32.GetForegroundWindow() == hwnd:
            fg_ok = True
            break
        user32.keybd_event(VK_MENU, 0, 0, 0)
        time.sleep(0.02)
        user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
        used_alt_unlock = True
        user32.AllowSetForegroundWindow(-1)
        user32.SetForegroundWindow(hwnd)
        user32.SetActiveWindow(hwnd)
        time.sleep(0.1)
        if user32.GetForegroundWindow() == hwnd:
            fg_ok = True
            break
    if used_alt_unlock and settle_for_interop_idle:
        time.sleep(15.25)
    report["foreground_ok"] = bool(fg_ok)
    report["used_alt_unlock"] = bool(used_alt_unlock)
    report["settle_for_interop_idle"] = bool(settle_for_interop_idle)
    report["borrow"] = True
    report["foreground_owner"] = "scripts.diy_skill_force._borrow_sims_foreground"
    if not fg_ok:
        raise GateError("SIMS_FOREGROUND_BORROW_FAILED_OPERATOR_APP_STILL_FOREGROUND")
    return report


def _with_sims_input_borrow(
    process_id: int | None,
    effect,
    *,
    idle_ms: int = 15000,
    wait_for_operator_idle: bool = True,
    wait_idle_timeout_sec: float = 600.0,
):
    """Wait for operator idle → snapshot app → borrow Sims → effect → restore.

    Interruptibility (ASYNC_INTEROP): any mouse motion or keyboard activity
    restarts the wait. Work is retained; this is the in-process resume path
    (CooperativeScreenQueue / host_listener tick) — not an OS cron, Task
    Scheduler, or background daemon. After >= idle_ms trusted quiet, borrow
    Sims briefly, run one effect, restore the operator's app (YouTube, …).
    """
    from betterinstincts.control_handoff import MIN_IDLE_MS

    idle_wait = None
    need = max(int(MIN_IDLE_MS), int(idle_ms))
    if wait_for_operator_idle and process_id is not None:
        idle_wait = _wait_for_input_idle(
            int(process_id),
            idle_ms=need,
            timeout_sec=float(wait_idle_timeout_sec),
            poll_sec=0.5,
        )
    snap = _snapshot_operator_foreground()
    borrow = _borrow_sims_foreground(
        process_id,
        settle_for_interop_idle=False,
        retries=2,
    )
    sims_hwnd = int(borrow["hwnd"])
    try:
        result = effect()
    finally:
        restore = _restore_operator_foreground(snap.get("hwnd"), sims_hwnd=sims_hwnd)
    return {
        "idle_wait": idle_wait,
        "snapshot": snap,
        "borrow": borrow,
        "restore": restore,
        "result": result,
        "resume_owner": "scripts.diy_skill_force._wait_for_input_idle",
        "not": ["OS_CRON", "TASK_SCHEDULER", "BACKGROUND_DAEMON"],
    }


def _focus(process_id: int | None, *, click_client: bool = False) -> dict:
    """Soft-focus Sims without stealing Build tools (no center click by default)."""
    report = _borrow_sims_foreground(
        process_id,
        settle_for_interop_idle=True,
        retries=2,
    )
    if click_client:
        import ctypes
        from ctypes import wintypes

        from scripts.win32_input import send_click

        user32 = ctypes.windll.user32
        hwnd = int(report["hwnd"])
        rect = wintypes.RECT()
        user32.GetClientRect(hwnd, ctypes.byref(rect))
        pt = wintypes.POINT(rect.right // 2, rect.bottom // 2)
        user32.ClientToScreen(hwnd, ctypes.byref(pt))
        send_click(int(pt.x), int(pt.y), between_sec=0.04)
        time.sleep(0.2)
    report["soft_focus"] = not click_client
    return report


def _play_brief_observe_repause(
    *,
    process_id: int | None = None,
    play_seconds: int | None = None,
    play_key: str = "1",
    pause_key: str = "0",
) -> dict:
    """Bounded Live tick for Skills-panel refresh, then always re-pause.

    Interruptible verify:
    1) borrow Sims → arm → press play → restore operator app
    2) wait play_seconds while operator keeps their app (YouTube, …)
    3) borrow Sims → arm → press pause → restore operator app

    Never leaves the operator trapped in Sims. Not main-menu Resume.
    """
    from scripts.win32_input import send_key_chord

    policy = skills_panel_observation_policy(purpose="verify")
    seconds = int(play_seconds if play_seconds is not None else policy["play_seconds"])
    seconds = max(int(policy["min_play_seconds"]), min(int(policy["max_play_seconds"]), seconds))
    play = str(play_key or policy["play_key"] or "1")[:1]
    pause = str(pause_key or policy["pause_key"] or "0")[:1]

    def _press_play():
        # No terrain RMB — map clicks are noise (operator 2026-11-10).
        send_key_chord([play], down_sec=0.06, after_sec=0.12, via="keybd_event")
        return {"pressed": play}

    def _press_pause():
        send_key_chord([pause], down_sec=0.06, after_sec=0.12, via="keybd_event")
        return {"pressed": pause}

    play_tick = _with_sims_input_borrow(process_id, _press_play)
    # Operator app restored — wait while they keep watching / working.
    time.sleep(float(seconds))
    pause_tick = _with_sims_input_borrow(process_id, _press_pause)
    time.sleep(0.2)
    return {
        "step": "PLAY_BRIEF_OBSERVE_REPAUSE",
        "action": "PLAY_BRIEF_OBSERVE_REPAUSE",
        "play_key": play,
        "pause_key": pause,
        "play_seconds": seconds,
        "always_repause": True,
        "interruptible": True,
        "no_terrain_rmb": True,
        "play_tick": play_tick,
        "pause_tick": pause_tick,
        "panel_status": "FRESH_PANEL_AFTER_PLAY_BRIEF",
        "note": (
            "Borrow Sims for 1/0 only — no map/terrain clicks. Restore "
            "operator app during the wait."
        ),
    }


def _accept_offered_reward_trait(
    step: dict,
    *,
    hwnd: int,
    observed_trait: str | None = None,
    dialog_text: str | None = None,
) -> dict:
    """Never dispatch unverified Enter/OK presses into arbitrary dialogs.

    Skill upgrades can surface preference Yes/No, occult, unrelated rewards,
    or no dialog at all. A fresh observation must reach its owning one-step
    adapter before UI input is authorized.

    Evil / harmful reward traits are NEVER blind-OK'd (2026-11-09 Servo Evil
    incident): when classified harmful the policy decision is ESCAPE_CANCEL_DIALOG
    (reported, not dispatched here); unclassified dialogs HOLD.
    """
    if step.get("never_press_cancel") is False:
        raise GateError("REWARD_TRAIT_CANCEL_FORBIDDEN")
    decision = decide_reward_dialog(observed_trait, dialog_text=dialog_text)
    if decision["decision"] == "ESCAPE_CANCEL_DIALOG":
        return {
            "step": "ACCEPT_OFFERED_REWARD_TRAIT",
            "state": "HARMFUL_REWARD_TRAIT_REFUSED",
            "actions": [],
            "never_press_cancel": True,
            "refuse_blind_ok": True,
            "decision": decision,
            "recommended_action": "ESCAPE_CANCEL_DIALOG",
            "next": "ONE_ESCAPE_CANCEL_OF_OBSERVED_DIALOG_BY_OWNING_ADAPTER_NEVER_ENTER_OR_OK",
            "proof_ceiling": "NO_REWARD_DIALOG_INPUT_DISPATCHED",
        }
    return {
        "step": "ACCEPT_OFFERED_REWARD_TRAIT",
        "state": "NEEDS_DIALOG_IDENTIFICATION",
        "actions": [],
        "never_press_cancel": True,
        "refuse_blind_ok": True,
        "decision": decision,
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
    if plan.get("skip_dispatch") or plan.get("state") == "SKILL_FORCE_MEMBER_NO_PENDING_DISPATCH_UNVERIFIED":
        return {
            "state": "SKILL_FORCE_MEMBER_NO_PENDING_DISPATCH_UNVERIFIED",
            "skipped": True,
            "member_key": member_key,
            "member_index": member_index,
            "skipped_skill_ids": list(plan.get("skipped_skill_ids") or []),
            "commands": [],
            "safe_cursor_rest": "UNCHANGED_NO_INPUT",
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

    def _focus_then_reidle() -> dict:
        """Soft-focus Alt ages last-input; wait again before admit confirm.

        Without a second idle wait, confirm() immediately sees RECENT_HUMAN_INPUT
        from the synthetic Alt unlock and fails closed even when the operator is quiet.
        """
        report = _focus(process_id)
        # Focus already slept ~15.25s; still re-poll in case a sidecar pulsed input.
        reidle = _wait_for_input_idle(
            int(process_id),
            idle_ms=idle_ms,
            timeout_sec=min(180.0, float(wait_idle_timeout_sec)),
            progress_path=wait_idle_progress_path,
        )
        report["idle_before_focus"] = idle_wait
        report["idle_after_focus"] = reidle
        return report

    with admitted_screen_lease(
        int(process_id),
        str(session_id),
        idle_ms=idle_ms,
        focus_fn=_focus_then_reidle,
        probe_fn=_admit_probe,
    ) as ensure_ready:
        try:
            handoff = ensure_ready()
        except HandoffError as exc:
            raise GateError(str(exc)) from exc
        handoff = {**handoff, "idle_wait": idle_wait}
        operator_snap = _snapshot_operator_foreground()
        focus_report = _focus(process_id)
        hwnd = int(focus_report["hwnd"])
        time.sleep(0.2)
        # Hold Sims for the typed batch; restore operator app after close.
        _toggle_cheat_console(process_id=int(process_id), restore_operator=False)
        time.sleep(0.15)
        _refocus_cheat_console()
        console_field_focused = True
        dispatched: list[str] = []
        reward_accepts: list[dict] = []
        testing_alias_sent = False
        for step in plan.get("steps") or []:
            name = str(step.get("step") or "")
            if name == "ACTIVATE_TESTING_CHEATS":
                cmd = str(step.get("command") or "")
                _type_cheat_line(cmd, refocus_strip=not console_field_focused)
                console_field_focused = True
                dispatched.append(cmd)
                alias = step.get("alias")
                if isinstance(alias, str) and alias.strip() and not testing_alias_sent:
                    _type_cheat_line(alias.strip(), refocus_strip=False)
                    dispatched.append(alias.strip())
                    testing_alias_sent = True
                continue
            if name == "SET_SKILL_LEVEL":
                cmd = str(step.get("command") or "")
                if not cmd:
                    continue
                _type_cheat_line(cmd, refocus_strip=not console_field_focused)
                console_field_focused = True
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
            _toggle_cheat_console(process_id=int(process_id), restore_operator=False)
            time.sleep(0.25)
        _restore_operator_foreground(operator_snap.get("hwnd"), sims_hwnd=hwnd)
        panel_verify = None
        if verify_skills_panel:
            panel_verify = _play_brief_observe_repause(
                process_id=int(process_id),
                play_seconds=verify_play_seconds,
            )
    cursor_rest = _park_safe_cursor_rest()
    return {
        "state": "DIY_SKILL_FORCE_DISPATCHED",
        "commands": dispatched,
        "safe_cursor_rest": cursor_rest,
        "interruptible_borrow_restore": True,
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


def _toggle_cheat_console(
    *,
    process_id: int | None = None,
    restore_operator: bool = True,
) -> dict:
    """Open/close cheat console via Ctrl+Shift+C.

    Prefer this over Escape: Esc while Live often opens the pause MENU and
    blocks household Space-traverse / skill typing.

    Interruptible by default (borrow → chord → restore). When about to type
    cheat lines, pass restore_operator=False and restore only after the batch
    closes — otherwise keystrokes land in the operator's other app.
    """
    from scripts.win32_input import send_key_chord

    def _chord():
        send_key_chord(
            ["CTRL", "SHIFT", "C"],
            down_sec=0.08,
            after_sec=0.4,
            via="keybd_event",
        )
        time.sleep(0.15)
        return True

    if process_id is None:
        _chord()
        return {
            "step": "TOGGLE_CHEAT_CONSOLE",
            "chord": "Ctrl+Shift+C",
            "chord_owner": "scripts.win32_input.send_key_chord",
            "chord_via": "keybd_event",
            "interruptible": False,
            "note": "No process_id — chord without borrow/restore",
        }
    if restore_operator:
        tick = _with_sims_input_borrow(int(process_id), _chord)
        return {
            "step": "TOGGLE_CHEAT_CONSOLE",
            "chord": "Ctrl+Shift+C",
            "chord_owner": "scripts.win32_input.send_key_chord",
            "chord_via": "keybd_event",
            "interruptible": True,
            "foreground_ok": bool((tick.get("borrow") or {}).get("foreground_ok")),
            "borrow_restore": tick,
        }
    # Keep Sims focused for an imminent type batch; caller restores after close.
    snap = _snapshot_operator_foreground()
    borrow = _borrow_sims_foreground(
        int(process_id),
        settle_for_interop_idle=False,
        retries=2,
    )
    _chord()
    return {
        "step": "TOGGLE_CHEAT_CONSOLE",
        "chord": "Ctrl+Shift+C",
        "chord_owner": "scripts.win32_input.send_key_chord",
        "chord_via": "keybd_event",
        "interruptible": False,
        "held_for_type_batch": True,
        "foreground_ok": bool(borrow.get("foreground_ok")),
        "borrow": borrow,
        "operator_hwnd_to_restore": snap.get("hwnd"),
        "sims_hwnd": int(borrow.get("hwnd") or 0),
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


def _type_cheat_line(cmd: str, *, refocus_strip: bool = True) -> None:
    """Type one cheat and submit with embedded newline via type_text.

    Live cert (P83): computer_type newlines do not submit Sims console lines.
    After Ctrl+Shift+C the game host focuses the cheat field — skip per-line
    strip re-click while that focus holds (operator correction 2026-11-09).
    """
    from scripts.win32_input import type_text

    if refocus_strip:
        _refocus_cheat_console()
    line = str(cmd).rstrip("\r\n")
    type_text(line + "\n")
    time.sleep(0.45)


def _arm_live_hotkeys(
    *,
    process_id: int | None = None,
    world_xy: tuple[int, int] | None = None,
    restore_operator: bool = True,
) -> dict:
    """Borrow Sims → terrain RMB → restore operator app (interruptible arm).

    Live hotkeys need Sims focused for the RMB arm, but the operator may be in
    YouTube or any other app. Default path snapshots their foreground, borrows
    Sims for the terrain right-click, then restores them. Pass
    restore_operator=False when the caller already wraps a borrow (e.g. play
    brief) so we do not double-restore mid-effect. Terrain RMB is NOT
    RIGHT_CLICK_VIEW portrait follow.
    """
    from betterinstincts.diy_skill_force import plan_live_hotkey_arm
    from scripts.win32_input import send_right_click

    # Skill-force: pin the contract default arm point. Roaming street corners /
    # map clicks / zoom is operator-forbidden noise and does not level skills.
    plan = plan_live_hotkey_arm(
        world_client_xy=None if world_xy is None else list(world_xy),
    )
    if world_xy is not None:
        default = list(plan.get("world_client_xy") or [880, 480])
        # Allow explicit override only when it matches the pinned default;
        # otherwise force the pinned point (ignore roam coords like 1200,700).
        if [int(world_xy[0]), int(world_xy[1])] != [int(default[0]), int(default[1])]:
            plan = plan_live_hotkey_arm(world_client_xy=None)
    x, y = int(plan["world_client_xy"][0]), int(plan["world_client_xy"][1])

    def _rmb():
        send_right_click(x, y, between_sec=0.05, safe_rest_after=True)
        time.sleep(0.15)
        return {"world_xy": [x, y], "pinned_arm": True}

    if process_id is None:
        _rmb()
        return {
            "step": "ARM_LIVE_HOTKEYS",
            "world_xy": [x, y],
            "order": list(plan["order"]),
            "interruptible": False,
            "repository_skill": plan.get("repository_skill"),
            "note": plan.get("select_note"),
        }

    if restore_operator:
        tick = _with_sims_input_borrow(int(process_id), _rmb)
        return {
            "step": "ARM_LIVE_HOTKEYS",
            "world_xy": [x, y],
            "order": list(plan["order"]),
            "interruptible": True,
            "borrow_restore": tick,
            "foreground_ok": bool((tick.get("borrow") or {}).get("foreground_ok")),
            "repository_skill": plan.get("repository_skill"),
            "note": plan.get("select_note"),
        }

    # Nested inside an outer borrow — Sims already foreground.
    _rmb()
    return {
        "step": "ARM_LIVE_HOTKEYS",
        "world_xy": [x, y],
        "order": list(plan["order"]),
        "interruptible": False,
        "nested_borrow": True,
        "repository_skill": plan.get("repository_skill"),
        "note": plan.get("select_note"),
    }


def _select_next_household_member(
    *, process_id: int | None, session_id: str | None, idle_ms: int,
) -> dict:
    """Arm Live hotkeys, then Space under a fresh admitted screen lease.

    Console must already be closed. Bare Space without left-click world +
    right-click cancel does nothing when focus is not in the game.
    """
    from betterinstincts.control_handoff import HandoffError
    from betterinstincts.player_presence import probe_windows
    from betterinstincts.screen_admit import admitted_screen_lease, require_execute_session
    from scripts.win32_input import tap_vk

    try:
        require_execute_session(session_id, process_id)
        _wait_for_input_idle(int(process_id), idle_ms=idle_ms, timeout_sec=60.0)
        with admitted_screen_lease(
            int(process_id), str(session_id), idle_ms=idle_ms,
            probe_fn=lambda: probe_windows(int(process_id)),
        ) as ensure_ready:
            ensure_ready()
            arm = _arm_live_hotkeys()
            tap_vk(0x20)  # VK_SPACE: select next household portrait
    except HandoffError as exc:
        raise GateError(str(exc)) from exc
    time.sleep(0.55)
    return {
        "step": "SELECT_NEXT_HOUSEHOLD_SIM",
        "key": "SPACE",
        "admitted": True,
        "arm": arm,
    }


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
    roster_keys: list[str] | None = None,
    first_portrait_attested: bool = False,
) -> dict:
    """Skill-round-robin: one skill × every portrait, then the next skill."""
    if first_portrait_attested is not True:
        raise GateError("FIRST_PORTRAIT_LOCAL_OBSERVATION_REQUIRED")
    count = int(household_plan.get("household_members") or 0)
    if roster_keys is None or len(roster_keys) != count:
        raise GateError("EXACT_OBSERVED_PORTRAIT_ROSTER_REQUIRED")
    try:
        require_fixed_roster(roster_keys, roster_keys)
    except HouseholdJudgmentError as exc:
        raise GateError(str(exc)) from exc
    ledger_path = (
        Path(completion_ledger_path)
        if completion_ledger_path is not None
        else default_completion_ledger_path()
    )
    expected_scope = household_plan.get("identity_scope_id")
    if expected_scope and load_completion_ledger(ledger_path).get("scope_id") != expected_scope:
        raise GateError("HOUSEHOLD_LEDGER_SCOPE_DRIFT")
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

    # A completed dispatch ledger is not a Skills-panel certificate. Critically,
    # when every cell is skipped, do NOT send Space, open the console, or move
    # the pointer just to produce a misleading `already maxed` result.
    if (
        not redo
        and household_plan.get("state") == "HOUSEHOLD_SKILL_FORCE_NO_PENDING_DISPATCH_UNVERIFIED"
        and all(bool(u.get("skip_dispatch")) for u in units)
    ):
        return {
            "state": "HOUSEHOLD_SKILL_FORCE_NO_PENDING_DISPATCH_UNVERIFIED",
            "dispatch_order": "skill_round_robin",
            "household_members": count,
            "cells_dispatched": 0,
            "cells_skipped_ledger_only": len(units),
            "members_dispatched": 0,
            "safe_cursor_rest": "UNCHANGED_NO_INPUT",
            "completion_ledger": str(ledger_path),
            "proof_ceiling": household_plan.get("proof_ceiling"),
            "pass_claim": "FORBIDDEN_UNTIL_SKILLS_PANEL_LOCAL_OBSERVED",
            "next_gate": "REVIEW_SKILLS_PANEL_OR_REDO_IN_DISPOSABLE_LAB",
        }

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
            # _execute_plan(close_console=True) already CLOSED the console.
            # Toggling here used to reopen it and send Space to the console.
            try:
                require_skill_action(
                    "SELECT_NEXT_HOUSEHOLD_SIM",
                    original_roster=roster_keys, observed_roster=roster_keys,
                )
            except HouseholdJudgmentError as exc:
                raise GateError(str(exc)) from exc
            select_report = _select_next_household_member(
                process_id=process_id, session_id=session_id, idle_ms=idle_ms,
            )
        else:
            select_report = {"step": "KEEP_CURRENT_SELECTION", "member_index": index}
        first_unit = False

        # Re-check ledger at execute time so mid-run / restarted workers skip done work.
        omit: list[str] = []
        if not redo:
            ledger = load_completion_ledger(ledger_path)
            if expected_scope and ledger.get("scope_id") != expected_scope:
                raise GateError("HOUSEHOLD_LEDGER_SCOPE_DRIFT")
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
                    "reason": "LEDGER_DISPATCH_RECORDED_NOT_PANEL_VERIFIED",
                    "live": {
                        "state": "SKILL_FORCE_MEMBER_NO_PENDING_DISPATCH_UNVERIFIED",
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
            "SKILL_FORCE_MEMBER_NO_PENDING_DISPATCH_UNVERIFIED"
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
                        "state": "SKILL_FORCE_MEMBER_NO_PENDING_DISPATCH_UNVERIFIED",
                        "commands": [],
                    },
                }
            )
            continue

        try:
            require_skill_action(
                "SET_SKILL_LEVEL",
                original_roster=roster_keys, observed_roster=roster_keys,
            )
        except HouseholdJudgmentError as exc:
            raise GateError(str(exc)) from exc
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
        "HOUSEHOLD_SKILL_FORCE_NO_PENDING_DISPATCH_UNVERIFIED"
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



def _add_household_scope_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profile-id", default=None,
                        help="Existing local installation preference profile (default active)")
    parser.add_argument("--save-key", default=None,
                        help="Locally observed opaque stable save identifier, not a filename/name")
    parser.add_argument("--household-key", default=None,
                        help="Locally observed opaque stable household identifier, not a name")


def _scoped_household_ledger(args, *, required: bool = False):
    """Resolve a private local ledger; no game scan or implicit write."""
    save_key = getattr(args, "save_key", None)
    household_key = getattr(args, "household_key", None)
    if not save_key and not household_key:
        if required:
            raise GateError("SAVE_AND_HOUSEHOLD_SCOPE_REQUIRED_BEFORE_EXECUTION")
        return None, None
    if not save_key or not household_key:
        raise GateError("SAVE_AND_HOUSEHOLD_SCOPE_MUST_BE_SUPPLIED_TOGETHER")
    roster_keys = list(getattr(args, "roster_key", []) or [])
    members = getattr(args, "members", None)
    if members is None or len(roster_keys) != members:
        raise GateError("EXACT_OBSERVED_PORTRAIT_ROSTER_REQUIRED_FOR_SCOPE")
    try:
        profile = getattr(args, "profile_id", None) or view_installation_profile()["profile_id"]
        view_installation_profile(profile_id=profile)
        scope = bind_household_scope(
            profile_id=profile, save_key=save_key,
            household_key=household_key, roster_keys=roster_keys,
        )
        path = household_ledger_path(profile_id=profile, scope_id=scope["scope_id"])
    except (InstallationProfileError, HouseholdJudgmentError) as exc:
        raise GateError(str(exc)) from exc
    return scope, path


def _resolve_ledger_path(args, scoped_path: Path | None) -> Path:
    requested = getattr(args, "completion_ledger", None)
    if requested is None:
        return scoped_path if scoped_path is not None else default_completion_ledger_path()
    path = Path(requested)
    if not path.is_absolute():
        path = ROOT / path
    if scoped_path is not None and path.resolve().is_relative_to(ROOT.resolve()):
        raise GateError("SCOPED_LEDGER_MUST_REMAIN_OUTSIDE_REPOSITORY")
    return path


def _validate_scope_ledger(ledger: dict, scope: dict | None) -> None:
    if scope is None:
        return
    old = ledger.get("scope_id")
    if old != scope["scope_id"] and (old is not None or ledger.get("members")):
        raise GateError("CROSS_HOUSEHOLD_LEDGER_REUSE_FORBIDDEN")
    old_roster = ledger.get("roster_fingerprint")
    if old_roster != scope["roster_fingerprint"] and (
        old_roster is not None or ledger.get("members")
    ):
        raise GateError("HOUSEHOLD_ROSTER_CHANGED_STOP_RECONCILE")
    ledger["scope_id"] = scope["scope_id"]
    ledger["roster_fingerprint"] = scope["roster_fingerprint"]


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


def _keybd_tap(vk: int) -> None:
    import ctypes

    user32 = ctypes.windll.user32
    keyup = 0x0002
    user32.keybd_event(vk, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(vk, 0, keyup, 0)
    time.sleep(0.12)


def execute_force_gaps(
    *,
    process_id: int,
    member_key: str,
    portrait_xy: tuple[int, int],
    session_id: str,
    bundle: str = "full_unlock",
    target_level: int = 10,
    redo: bool = False,
    always_include: list[str] | None = None,
    console_strip_observed: bool = False,
    idle_ms: int = 15000,
    play_seconds: int = 7,
    scroll_inventory: bool = True,
    completion_ledger_path: Path | None = None,
) -> dict:
    """Select portrait, type gap cheats (canonical spelling), play, optional scroll.

    Codifies the Live force path so agents stop re-authoring one-shot scripts.
    Never presses lone V (video). Away desk is not a busy invent.
    """
    from scripts.win32_input import (
        left_drag,
        park_safe_cursor_rest,
        send_click,
        send_right_click,
        send_wheel,
        type_text,
    )

    if not session_id or completion_ledger_path is None:
        raise GateError("SCOPED_LOCAL_SESSION_AND_LEDGER_REQUIRED_FOR_FORCE_GAPS")
    safety = assess_console_type_safety(console_strip_observed=console_strip_observed)
    if safety.get("state") != "CONSOLE_TYPE_ALLOWED":
        raise GateError("CONSOLE_STRIP_REQUIRED_BEFORE_FORCE_GAPS")

    ledger_path = Path(completion_ledger_path)
    ledger = load_completion_ledger(ledger_path)
    scope_id = ledger.get("scope_id")
    if not scope_id or not str(member_key).startswith(scope_id + "::key::"):
        raise GateError("FORCE_GAPS_MEMBER_MUST_MATCH_SCOPED_LEDGER")
    mk = str(member_key)
    observed = member_observed_levels_from_ledger(ledger, mk)
    plan = plan_force_gaps_beat(
        member_key=member_key,
        portrait_client_xy=portrait_xy,
        bundle=bundle,
        target_level=target_level,
        redo=redo,
        always_include=always_include,
        observed_levels=observed,
    )
    rows = list((plan.get("gaps") or {}).get("rows") or [])
    if not rows:
        return {
            "state": "FORCE_GAPS_EMPTY",
            "member_key": member_key,
            "plan": plan,
            "note": "No gap commands — ledger already PANEL_OBSERVED_MAX for bundle",
        }

    idle = _wait_for_input_idle(int(process_id), idle_ms=int(idle_ms), timeout_sec=180.0)
    if idle.get("state") != "INPUT_IDLE_READY":
        raise GateError(f"NOT_IDLE:{idle}")

    snap = _snapshot_operator_foreground()
    borrow = _borrow_sims_foreground(int(process_id), settle_for_interop_idle=False, retries=2)
    hwnd = int(borrow["hwnd"])
    typed: list[str] = []
    try:
        _arm_live_hotkeys(process_id=int(process_id), restore_operator=False)
        _keybd_tap(0x0D)  # Enter recenter
        time.sleep(0.2)
        send_click(int(portrait_xy[0]), int(portrait_xy[1]), between_sec=0.05, safe_rest_after=False)
        time.sleep(0.25)
        send_right_click(int(portrait_xy[0]), int(portrait_xy[1]), between_sec=0.05, safe_rest_after=False)
        time.sleep(0.45)
        _keybd_tap(0x0D)
        time.sleep(0.15)
        _keybd_tap(0x4A)  # J name proof
        time.sleep(0.35)
        _toggle_cheat_console(process_id=int(process_id), restore_operator=False)
        _refocus_cheat_console()
        time.sleep(0.12)
        type_text("testingcheats true\n")
        time.sleep(0.4)
        for row in rows:
            sid = str(row.get("skill_id") or "")
            cmd = str(row["command"])
            times = 2 if sid in {"photography", "writing", "media_production"} else 1
            for _ in range(times):
                type_text(cmd + "\n")
                time.sleep(0.34)
            typed.append(cmd)
        _toggle_cheat_console(process_id=int(process_id), restore_operator=False)
        _keybd_tap(0x0D)
    finally:
        _restore_operator_foreground(snap.get("hwnd"), sims_hwnd=hwnd)

    _play_brief_observe_repause(process_id=int(process_id), play_seconds=int(play_seconds))

    inventory_done = False
    if scroll_inventory:
        idle2 = _wait_for_input_idle(int(process_id), idle_ms=int(idle_ms), timeout_sec=180.0)
        if idle2.get("state") != "INPUT_IDLE_READY":
            raise GateError(f"NOT_IDLE_AFTER_PLAY:{idle2}")
        snap2 = _snapshot_operator_foreground()
        borrow2 = _borrow_sims_foreground(int(process_id), settle_for_interop_idle=False, retries=2)
        try:
            _arm_live_hotkeys(process_id=int(process_id), restore_operator=False)
            _keybd_tap(0x0D)
            send_click(int(portrait_xy[0]), int(portrait_xy[1]), between_sec=0.05, safe_rest_after=False)
            time.sleep(0.2)
            send_right_click(
                int(portrait_xy[0]), int(portrait_xy[1]), between_sec=0.05, safe_rest_after=False
            )
            time.sleep(0.4)
            _keybd_tap(0x0D)
            _keybd_tap(0x4C)  # L skills
            time.sleep(0.4)
            left_drag(1722, 810, 1722, 225, steps=12, step_sec=0.018, safe_rest_after=False)
            time.sleep(0.1)
            send_click(1700, 520, between_sec=0.04, safe_rest_after=False)
            send_wheel(-30, x=1700, y=520, safe_rest_after=False)
            time.sleep(0.2)
            send_wheel(12, x=1700, y=520, safe_rest_after=False)
            park_safe_cursor_rest()
            inventory_done = True
        finally:
            _restore_operator_foreground(snap2.get("hwnd"), sims_hwnd=int(borrow2["hwnd"]))

    return {
        "state": "FORCE_GAPS_DISPATCHED",
        "member_key": member_key,
        "portrait_xy": list(portrait_xy),
        "typed_count": len(typed),
        "commands": typed,
        "inventory_scrolled": inventory_done,
        "plan": plan,
        "proof_ceiling": "HOST_TYPED_NOT_PANEL_OBSERVED_MAX",
        "media_production_canonical": "stats.set_skill_level Major_MediaProduction 10",
        "next": "LOCAL_OBSERVE Skills panel (scroll); panel-record yellow vs non-yellow",
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("catalog")
    cmd = sub.add_parser(
        "commands",
        help="Print canonical skill_id → skill_stat → stats.set_skill_level lines (never invent spelling)",
    )
    cmd.add_argument("--bundle", default=None, help="Limit to a bundle (e.g. remote_income, full_unlock)")
    cmd.add_argument("--level", type=int, default=10)
    cmd.add_argument(
        "--gaps-from",
        default=None,
        help="JSON object of skill_id→observed_level; emit only non-yellow/below-target gap commands",
    )
    inv = sub.add_parser(
        "skills-inventory-plan",
        help="Plan burger-expand + scroll Skills list; non-yellow rows are gap targets",
    )
    inv.add_argument("--pages", type=int, default=8)

    fg = sub.add_parser(
        "force-gaps",
        help=(
            "Durable select→type canonical gap cheats→play→scroll inventory. "
            "Use --redo for full bundle on a locally observed target Sim. "
            "Canonical Media Production: stats.set_skill_level Major_MediaProduction 10"
        ),
    )
    fg.add_argument("--member-key", required=True, help="Stable locally observed portrait key; never display name")
    fg.add_argument(
        "--portrait-xy",
        required=True,
        help="Locally observed client X,Y for the selected portrait LEFT_CLICK",
    )
    fg.add_argument("--session-id", default=None)
    _add_household_scope_flags(fg)
    fg.add_argument("--members", type=int, default=None)
    fg.add_argument("--roster-key", action="append", default=[])
    fg.add_argument("--bundle", default="full_unlock")
    fg.add_argument("--level", type=int, default=10)
    fg.add_argument("--redo", action="store_true", help="Force entire bundle even if ledger MAX")
    fg.add_argument(
        "--always-include",
        action="append",
        default=[],
        help="Repeatable skill_id to force even if ledger says max (e.g. media_production)",
    )
    fg.add_argument("--process-id", type=int, default=None)
    fg.add_argument("--execute", action="store_true")
    fg.add_argument(
        "--console-strip-observed",
        action="store_true",
        help="Required with --execute: white cheat strip open+focused before type",
    )
    fg.add_argument("--idle-ms", type=int, default=15000)
    fg.add_argument("--play-seconds", type=int, default=7)
    fg.add_argument("--no-scroll-inventory", action="store_true")
    fg.add_argument("--completion-ledger", type=Path, default=None)
    fg.add_argument("--receipt", type=Path, default=None)

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

    tr = sub.add_parser(
        "trait-repair",
        help="Evaluate-only console plan: traits.remove_trait trait_Evil on the selected Sim",
    )
    tr.add_argument("--trait", action="append", default=[], help="Trait id/alias to remove (default trait_Evil)")
    tr.add_argument("--equip-good", action="store_true", help="Also equip trait_Good (needs --operator-requested-good)")
    tr.add_argument(
        "--operator-requested-good",
        action="store_true",
        help="Operator explicitly asked for trait_Good; default repair removes Evil only",
    )
    tr.add_argument("--game-mode", default="unknown")
    tr.add_argument("--receipt", type=Path, default=None)

    rc = sub.add_parser(
        "reward-check",
        help="Offline reward-dialog policy: Evil/harmful -> ESCAPE_CANCEL_DIALOG, never Enter/OK",
    )
    rc.add_argument("--trait", default=None, help="Observed reward trait id/label")
    rc.add_argument("--text", default=None, help="Observed dialog text")
    rc.add_argument("--receipt", type=Path, default=None)

    uc = sub.add_parser(
        "ui-check",
        help="Offline verdict for Escape / new-Servo / CAS-Continue / trait_Good actions",
    )
    uc.add_argument("--action", required=True)
    uc.add_argument("--context", default="")
    uc.add_argument("--operator-consent", action="store_true")
    uc.add_argument("--escape-cancel-requested", action="store_true")
    uc.add_argument("--operator-requested-good", action="store_true")
    uc.add_argument("--repeat-count", type=int, default=1)
    uc.add_argument("--receipt", type=Path, default=None)

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
    _add_household_scope_flags(hh)
    hh.add_argument("--roster-key", action="append", default=[],
                    help="Observed stable portrait ID, once per Sim, ordered from first portrait")
    hh.add_argument("--first-portrait-attested", action="store_true",
                    help="Require local proof that portrait 0 is selected before skill dispatch")
    hh.add_argument(
        "--detach",
        action="store_true",
        help="Disabled safety guard: detached UI worker execution is forbidden",
    )

    pr = sub.add_parser(
        "panel-record",
        help="Record Skills-panel LOCAL_OBSERVED levels into the completion ledger (no screenshots required next time)",
    )
    pr.add_argument("--session-id", required=True)
    _add_household_scope_flags(pr)
    pr.add_argument("--members", type=int, default=None, help="Exact observed portrait count N")
    pr.add_argument("--roster-key", action="append", default=[], help="Ordered portrait keys matching N")
    pr.add_argument("--display-name", action="append", default=[], help="Optional display names ordered with roster")
    pr.add_argument("--member-key", required=True, help="Portrait key receiving this panel reading")
    pr.add_argument("--member-display-name", default=None)
    pr.add_argument(
        "--skill-level",
        action="append",
        default=[],
        help="Repeatable skill=level (id or display name), e.g. cooking=10 robotics=3",
    )
    pr.add_argument(
        "--all-listed-max",
        action="store_true",
        help="Operator attested every visible skill at max; also mark remaining full_unlock rows PANEL_OBSERVED_MAX",
    )
    pr.add_argument("--target-level", type=int, default=10)
    pr.add_argument(
        "--completion-ledger",
        type=Path,
        default=None,
        help="Default dist/game-host/diy-skill-force-completion.json",
    )
    pr.add_argument("--receipt", type=Path, default=None)

    rs = sub.add_parser(
        "roster-status",
        help="Print household roster N + per-member panel/dispatched skill status from the ledger",
    )
    rs.add_argument("--session-id", default=None)
    _add_household_scope_flags(rs)
    rs.add_argument("--members", type=int, default=None)
    rs.add_argument("--roster-key", action="append", default=[])
    rs.add_argument("--completion-ledger", type=Path, default=None)
    rs.add_argument("--target-level", type=int, default=10)
    rs.add_argument("--bundle", default="full_unlock")

    ts = sub.add_parser(
        "target-sim",
        help=(
            "Plan select→evaluate→camera→console→force for one portrait. "
            "Evaluate-only unless identity header + console strip are attested "
            "(never type without strip; V starts video recording)."
        ),
    )
    ts.add_argument("--session-id", required=True)
    _add_household_scope_flags(ts)
    ts.add_argument("--members", type=int, required=True)
    ts.add_argument("--roster-key", action="append", default=[])
    ts.add_argument("--member-key", required=True)
    ts.add_argument("--display-name", required=True)
    ts.add_argument("--roster-index", type=int, required=True)
    ts.add_argument("--bundle", default="full_unlock")
    ts.add_argument("--target-level", type=int, default=10)
    ts.add_argument("--completion-ledger", type=Path, default=None)
    ts.add_argument(
        "--observed-panel-header",
        default=None,
        help="Exact Skills/Dynasty header text proving selection (e.g. \"Sim A hasn't earned…\")",
    )
    ts.add_argument("--observed-selected-roster-key", default=None)
    ts.add_argument(
        "--console-strip-observed",
        action="store_true",
        help="Attest white cheat strip is open+focused before any type_text",
    )
    ts.add_argument(
        "--portrait-client-xy",
        default=None,
        help="Optional client X,Y for LEFT_CLICK portrait (two ints)",
    )
    ts.add_argument("--receipt", type=Path, default=None)

    args = p.parse_args(argv)
    try:
        if args.command == "catalog":
            result = catalog_snapshot()
        elif args.command == "commands":
            if args.gaps_from:
                observed = json.loads(Path(args.gaps_from).read_text(encoding="utf-8"))
                if not isinstance(observed, dict):
                    raise GateError("GAPS_FROM_MUST_BE_JSON_OBJECT")
                result = gap_targets_from_observed_levels(
                    observed,
                    target_level=int(args.level),
                    bundle=args.bundle or "full_unlock",
                )
            else:
                result = canonical_skill_commands(
                    target_level=int(args.level),
                    bundle=args.bundle,
                )
        elif args.command == "skills-inventory-plan":
            result = plan_skills_panel_inventory(pages=int(args.pages))
        elif args.command == "force-gaps":
            xy_parts = [p.strip() for p in str(args.portrait_xy).split(",")]
            if len(xy_parts) != 2:
                raise GateError("PORTRAIT_XY_MUST_BE_X_COMMA_Y")
            portrait_xy = (int(xy_parts[0]), int(xy_parts[1]))
            scope, scoped_path = _scoped_household_ledger(
                args, required=bool(args.execute)
            )
            ledger_path = _resolve_ledger_path(args, scoped_path)
            ledger = load_completion_ledger(ledger_path)
            _validate_scope_ledger(ledger, scope)
            if scope is not None:
                if args.member_key not in args.roster_key:
                    raise GateError("FORCE_GAPS_MEMBER_NOT_IN_SCOPED_ROSTER")
                mk = scope["member_keys"][args.roster_key.index(args.member_key)]
            else:
                mk = completion_member_key(args.session_id, 0, args.member_key)
            observed = member_observed_levels_from_ledger(ledger, mk)
            if args.execute:
                if args.process_id is None:
                    raise GateError("PROCESS_ID_REQUIRED_FOR_EXECUTE")
                save_completion_ledger(ledger, ledger_path)
                result = execute_force_gaps(
                    process_id=int(args.process_id),
                    member_key=mk,
                    portrait_xy=portrait_xy,
                    session_id=str(args.session_id),
                    bundle=str(args.bundle),
                    target_level=int(args.level),
                    redo=bool(args.redo),
                    always_include=list(args.always_include or []),
                    console_strip_observed=bool(args.console_strip_observed),
                    idle_ms=int(args.idle_ms),
                    play_seconds=int(args.play_seconds),
                    scroll_inventory=not bool(args.no_scroll_inventory),
                    completion_ledger_path=ledger_path,
                )
            else:
                result = plan_force_gaps_beat(
                    member_key=str(args.member_key),
                    portrait_client_xy=portrait_xy,
                    bundle=str(args.bundle),
                    target_level=int(args.level),
                    redo=bool(args.redo),
                    always_include=list(args.always_include or []),
                    observed_levels=observed,
                )
            if args.receipt is not None:
                Path(args.receipt).parent.mkdir(parents=True, exist_ok=True)
                Path(args.receipt).write_text(
                    json.dumps(result, indent=2) + "\n", encoding="utf-8"
                )
                result = {**result, "receipt": str(args.receipt)}
        elif args.command == "panel-record":
            scope, scoped_path = _scoped_household_ledger(args)
            ledger_path = _resolve_ledger_path(args, scoped_path)
            ledger = load_completion_ledger(ledger_path)
            _validate_scope_ledger(ledger, scope)
            if args.members is not None:
                if len(args.roster_key) != int(args.members):
                    raise GateError("EXACT_OBSERVED_PORTRAIT_ROSTER_REQUIRED")
                set_household_roster(
                    ledger,
                    session_id=args.session_id,
                    members=int(args.members),
                    roster_keys=list(args.roster_key),
                    display_names=list(args.display_name) or None,
                )
            observed: dict[str, int] = {}
            for item in args.skill_level:
                if "=" not in str(item):
                    raise GateError("SKILL_LEVEL_MUST_BE_NAME_EQ_INT")
                name, _, lvl = str(item).partition("=")
                observed[name.strip()] = int(lvl)
            if not observed and not args.all_listed_max:
                raise GateError("SKILL_LEVEL_OR_ALL_LISTED_MAX_REQUIRED")
            if args.all_listed_max and not observed:
                # Treat as full max attestation with empty explicit map.
                observed = {}
            if scope is not None:
                if args.member_key not in args.roster_key:
                    raise GateError("PANEL_MEMBER_NOT_IN_OBSERVED_SCOPED_ROSTER")
                mkey = scope["member_keys"][args.roster_key.index(args.member_key)]
            else:
                mkey = (
                    args.member_key
                    if ("::key::" in args.member_key or "::idx::" in args.member_key)
                    else completion_member_key(args.session_id, 0, args.member_key)
                )
            snap = record_member_panel_snapshot(
                ledger,
                member_key=mkey,
                observed_skills=observed,
                display_name=args.member_display_name,
                mark_unlisted_full_unlock_max=bool(args.all_listed_max),
                target_level=int(args.target_level),
            )
            if scope is None and args.completion_ledger is None:
                raise GateError("PRIVATE_PROFILE_SCOPE_REQUIRED_FOR_PANEL_PERSISTENCE")
            path = save_completion_ledger(ledger, ledger_path)
            result = {
                "state": "SKILLS_PANEL_RECORDED",
                "ledger": str(path),
                "household_roster": ledger.get("household_roster"),
                "snapshot": snap,
                "note": "PANEL_OBSERVED_MAX skips future maximize cells; PANEL_OBSERVED stores gaps. No screenshot required once recorded.",
            }
            if args.receipt is not None:
                args.receipt.parent.mkdir(parents=True, exist_ok=True)
                args.receipt.write_text(
                    json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                )
        elif args.command == "roster-status":
            scope, scoped_path = _scoped_household_ledger(args)
            ledger_path = _resolve_ledger_path(args, scoped_path)
            ledger = load_completion_ledger(ledger_path)
            _validate_scope_ledger(ledger, scope)
            catalog = catalog_snapshot()
            bundle = args.bundle or "full_unlock"
            skill_ids = list((catalog.get("bundles") or {}).get(bundle, {}).get("skill_ids") or [])
            roster = ledger.get("household_roster") if isinstance(ledger.get("household_roster"), dict) else {}
            members_out = []
            for key, row in sorted((ledger.get("members") or {}).items()):
                if scope is not None and key not in scope["member_keys"]:
                    continue
                if scope is None and args.session_id and args.session_id not in str(key):
                    continue
                skills = (row or {}).get("skills") or {}
                done = completed_skill_ids_for_member(ledger, key, target_level=int(args.target_level))
                remaining = [sid for sid in skill_ids if sid not in done]
                members_out.append(
                    {
                        "member_key": key,
                        "display_name": (row or {}).get("display_name"),
                        "panel_or_dispatched_complete": sorted(done),
                        "remaining_for_bundle": remaining,
                        "skill_rows": skills,
                    }
                )
            result = {
                "state": "ROSTER_STATUS",
                "ledger": str(ledger_path),
                "household_roster": roster,
                "observed_n": roster.get("members"),
                "bundle": bundle,
                "members": members_out,
            }
        elif args.command == "trait-repair":
            plan = plan_trait_repair(
                remove_traits=list(args.trait) or None,
                equip_good=bool(args.equip_good),
                operator_requested_good=bool(args.operator_requested_good),
                game_mode=args.game_mode,
            )
            result = {
                "plan": plan,
                "commands": trait_repair_commands(plan),
                "execute": False,
            }
        elif args.command == "reward-check":
            result = {
                "decision": decide_reward_dialog(args.trait, dialog_text=args.text),
                "execute": False,
            }
        elif args.command == "ui-check":
            result = {
                "verdict": evaluate_ui_action(
                    args.action,
                    context=args.context,
                    operator_consent=bool(args.operator_consent),
                    escape_cancel_requested=bool(args.escape_cancel_requested),
                    operator_requested_good=bool(args.operator_requested_good),
                    repeat_count=int(args.repeat_count),
                ),
                "execute": False,
            }
        elif args.command == "target-sim":
            if len(args.roster_key) != int(args.members):
                raise GateError("EXACT_OBSERVED_PORTRAIT_ROSTER_REQUIRED")
            scope, scoped_path = _scoped_household_ledger(args)
            ledger_path = _resolve_ledger_path(args, scoped_path)
            ledger = load_completion_ledger(ledger_path)
            _validate_scope_ledger(ledger, scope)
            portrait_xy = None
            if args.portrait_client_xy:
                parts = [p.strip() for p in str(args.portrait_client_xy).split(",")]
                if len(parts) != 2:
                    raise GateError("PORTRAIT_CLIENT_XY_MUST_BE_X_COMMA_Y")
                portrait_xy = [int(parts[0]), int(parts[1])]
            plan = plan_target_sim_skill_algorithm(
                session_id=args.session_id,
                member_key=args.member_key,
                display_name=args.display_name,
                roster_index=int(args.roster_index),
                members=int(args.members),
                roster_keys=list(args.roster_key),
                bundle=args.bundle,
                target_level=int(args.target_level),
                ledger=ledger,
                observed_panel_header_name=args.observed_panel_header,
                observed_selected_roster_key=args.observed_selected_roster_key,
                console_strip_observed=bool(args.console_strip_observed),
                portrait_client_xy=portrait_xy,
            )
            result = {
                "plan": plan,
                "execute": False,
                "identity_check": assess_selection_identity(
                    expected_display_name=args.display_name,
                    observed_panel_header_name=args.observed_panel_header,
                    observed_selected_roster_key=args.observed_selected_roster_key,
                    expected_roster_key=args.roster_key[int(args.roster_index)],
                ),
                "console_check": assess_console_type_safety(
                    console_strip_observed=bool(args.console_strip_observed),
                ),
                "evaluation": evaluate_member_skill_levels(
                    ledger,
                    member_key=(
                        scope["member_keys"][int(args.roster_index)]
                        if scope is not None
                        else (
                            args.member_key
                            if "::key::" in args.member_key
                            else completion_member_key(
                                args.session_id, int(args.roster_index), args.member_key
                            )
                        )
                    ),
                    skill_ids=list(
                        (
                            (catalog_snapshot().get("bundles") or {})
                            .get(args.bundle or "full_unlock", {})
                            .get("skill_ids")
                        )
                        or []
                    ),
                    target_level=int(args.target_level),
                ),
                "note": (
                    "Evaluate-only plan. Live force requires proven panel header + "
                    "console strip; unfocused typing starts video via V."
                ),
            }
            if args.receipt is not None:
                args.receipt.parent.mkdir(parents=True, exist_ok=True)
                args.receipt.write_text(
                    json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                )
        elif args.command == "household":
            if args.detach:
                raise GateError("DETACHED_HOUSEHOLD_UI_UNSAFE_USE_FOREGROUND_SERIAL")
            if args.execute:
                if not args.first_portrait_attested:
                    raise GateError("FIRST_PORTRAIT_LOCAL_OBSERVATION_REQUIRED")
                if len(args.roster_key) != int(args.members):
                    raise GateError("EXACT_OBSERVED_PORTRAIT_ROSTER_REQUIRED")
                try:
                    require_fixed_roster(args.roster_key, args.roster_key)
                except HouseholdJudgmentError as exc:
                    raise GateError(str(exc)) from exc
            skill_ids = list(args.skill) or None
            bundle = args.bundle
            if isinstance(bundle, str) and not bundle.strip():
                bundle = None
            if bundle is None and not skill_ids:
                bundle = "full_unlock"
            accept = None if not getattr(args, "no_accept_reward_dialogs", False) else False
            scope, scoped_path = _scoped_household_ledger(
                args, required=bool(args.execute)
            )
            ledger_path = _resolve_ledger_path(args, scoped_path)
            ledger = (
                empty_completion_ledger()
                if getattr(args, "redo", False)
                else load_completion_ledger(ledger_path)
            )
            _validate_scope_ledger(ledger, scope)
            plan = plan_household_skill_force(
                members=int(args.members),
                skill_ids=skill_ids,
                bundle=bundle,
                level=args.level,
                game_mode=args.game_mode,
                accept_reward_dialogs=accept,
                session_id=getattr(args, "session_id", None),
                member_keys=list(args.roster_key) if args.roster_key else None,
                household_scope=scope,
                completion_ledger=ledger,
                redo=bool(getattr(args, "redo", False)),
            )
            result = {"plan": plan, "execute": False, "detached": False}
            if args.execute:
                save_completion_ledger(ledger, ledger_path)
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
                    roster_keys=list(args.roster_key),
                    first_portrait_attested=bool(args.first_portrait_attested),
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
    except (DiySkillForceError, HouseholdJudgmentError, GateError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
