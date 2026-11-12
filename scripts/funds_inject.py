#!/usr/bin/env python3
"""Opt-in exact household funds through the existing Sims 4 host input lease.

Command stack: Ctrl+Shift+C -> testingcheats true -> money N -> HUD check.
No portrait click, fixed screen click, mode switch, extra motherlodes, or
automatic retries. The remote/CLI executor reports dispatch, NEVER a proven
balance change. Local P08 disposable game verification remains required.

Examples:
  python -m scripts.funds_inject plan --amount 1000000 --funds 38 --game-mode live
  python -m scripts.funds_inject inject --amount 1000000 --funds 38 --game-mode live
  python -m scripts.funds_inject inject --amount 1000000 --funds 38 --game-mode live --execute --process-id PID --session-id ACTIVE_SESSION
  python -m scripts.funds_inject verify --amount 1000000 --funds-before 38 --funds-after 1000000 --evidence-ref observed-hud-id
  python -m scripts.funds_inject recover --amount 1000000 --funds-before 38 --funds-after 38 --prior-dispatch-ref dispatch:ACTUAL --prior-receipt dist/game-host/ACTUAL.json --evidence-ref hud:ACTUAL --confirmed-noop --game-mode live --console-open-method operator-ready --console-ready
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from betterinstincts.funds_inject import (
    FundsInjectError,
    evaluate_subsidy_gate,
    plan_inject,
    plan_funds_recovery,
    steps_to_commands,
    subsidy_prompt,
    verify_funds_outcome,
)

OUTPUT = ROOT / "dist" / "game-host"


class GateError(ValueError):
    pass


class DispatchUncertain(GateError):
    """Input may have occurred; never label it a clean BLOCKED or retry."""

    def __init__(self, reason: str, *, commands_sent: list[str]):
        super().__init__(reason)
        self.commands_sent = list(commands_sent)



RECEIPT_MAX_BYTES = 64_000


def _safe_output_path(value: Path) -> Path:
    """Never follow a user-selected receipt path outside ignored game-host."""
    candidate = value if value.is_absolute() else ROOT / value
    if (OUTPUT.is_symlink() or OUTPUT.parent.is_symlink()
            or candidate.is_symlink()):
        raise GateError("FUNDS_RECEIPT_SYMLINK_FORBIDDEN")
    root = OUTPUT.resolve()
    path = candidate.resolve()
    if not path.is_relative_to(root) or path == root or path.suffix.lower() != ".json":
        raise GateError("RECEIPT_OUTSIDE_DIST_GAME_HOST")
    return path


def _reserve_receipt(value: Path | None, *, execute: bool) -> Path | None:
    """Reserve exclusive receipt name BEFORE any game/desktop side effect."""
    if value is None and not execute:
        return None
    if value is None:
        value = Path("dist/game-host") / ("funds-" + uuid.uuid4().hex + ".json")
    path = _safe_output_path(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as sink:
            sink.write(json.dumps({
                "schema": "betterinstincts.funds-dispatch-receipt/v1",
                "state": "PREPARED_EFFECT_OUTCOME_UNKNOWN_IF_UNFINALIZED",
                "next_gate": "RECONCILE_GAME_HUD_BEFORE_ANY_RETRY",
                "proof_ceiling": "NO_GAME_EFFECT_CLAIM",
            }) + "\n")
    except FileExistsError as exc:
        raise GateError("FUNDS_RECEIPT_ALREADY_EXISTS") from exc
    return path


def _write_receipt(path: Path, result: dict) -> None:
    """Finalize only this invocation's already reserved receipt."""
    if path.is_symlink() or not path.is_file():
        raise GateError("FUNDS_RECEIPT_CHANGED_AFTER_RESERVATION")
    payload = json.dumps({
        "schema": "betterinstincts.funds-dispatch-receipt/v1",
        **result,
    }, indent=2, sort_keys=True) + "\n"
    if len(payload.encode("utf-8")) > RECEIPT_MAX_BYTES:
        raise GateError("FUNDS_RECEIPT_TOO_LARGE")
    path.write_text(payload, encoding="utf-8")


def _require_exact_predecessor(
    path_value: Path | None, plan: dict, *, process_id: int | None,
    session_id: str | None,
) -> dict:
    """Bind a fallback to an actual previous local exact-money dispatch.

    A human HUD reference is still an external attestation, not a sensor proof.
    This independently rejects arbitrary strings presented as dispatch receipts.
    """
    if path_value is None:
        raise GateError("PRIOR_EXACT_DISPATCH_RECEIPT_REQUIRED")
    path = _safe_output_path(path_value)
    if (not path.is_file() or path.is_symlink()
            or path.stat().st_size > RECEIPT_MAX_BYTES):
        raise GateError("PRIOR_EXACT_DISPATCH_RECEIPT_UNSAFE")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError, OSError) as exc:
        raise GateError("PRIOR_EXACT_DISPATCH_RECEIPT_INVALID") from exc
    live = data.get("live") if isinstance(data, dict) else None
    if not isinstance(live, dict):
        raise GateError("PRIOR_EXACT_DISPATCH_NOT_OBSERVED")
    target = plan.get("target_funds")
    before = plan.get("funds_before_exact")
    if (data.get("schema") != "betterinstincts.funds-dispatch-receipt/v1"
            or data.get("execute") is not True
            or live.get("state") != "FUNDS_INJECT_DISPATCHED_NOT_VERIFIED"
            or live.get("commands") != ["testingcheats true", f"money {target}"]
            or live.get("dispatch_ref") != plan.get("prior_dispatch_ref")
            or live.get("game_mode") != plan.get("game_mode")
            or live.get("funds_before_reported") != before
            or live.get("target_funds") != target
            or live.get("session_id") != session_id
            or live.get("process_id") != process_id):
        raise GateError("PRIOR_EXACT_DISPATCH_MISMATCH")
    return live


def _claim_recovery_once(dispatch_ref: str) -> str:
    """Single-use durable, atomic claim BEFORE any fallback keyboard effect.

    A crash after the claim is UNKNOWN, not permission to replay. The existing
    predecessor must be re-observed or replaced by a new exact dispatch.
    """
    if (not isinstance(dispatch_ref, str)
            or not dispatch_ref.startswith("dispatch:")
            or len(dispatch_ref) != 41
            or not all(c in "0123456789abcdef" for c in dispatch_ref[9:])):
        raise GateError("UNTRUSTED_DISPATCH_ID")
    root = OUTPUT / "funds-recovery-claims"
    if root.is_symlink():
        raise GateError("RECOVERY_CLAIMS_SYMLINK_FORBIDDEN")
    root.mkdir(parents=True, exist_ok=True)
    claim = root / (dispatch_ref[9:] + ".json")
    try:
        with claim.open("x", encoding="utf-8") as sink:
            sink.write(json.dumps({"schema": "betterinstincts.funds-recovery-claim/v1",
                                   "dispatch_ref": dispatch_ref,
                                   "state": "CLAIMED_BEFORE_EFFECT_NO_REPLAY"}) + "\n")
    except FileExistsError as exc:
        raise GateError("RECOVERY_ALREADY_CLAIMED_NO_REPLAY") from exc
    return str(claim.relative_to(ROOT))


def _focus(process_id: int | None) -> dict:
    """Soft-focus Sims; never click the world or a fixed console pixel."""
    import ctypes

    from scripts.game_host import focus

    report = focus(process_id=process_id)
    user32 = ctypes.windll.user32
    hwnd = int(report["hwnd"])
    # Alt-unlock + AttachThreadInput: background agents often cannot SetForeground alone.
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
    fg_ok = user32.GetForegroundWindow() == hwnd
    report["foreground_ok"] = fg_ok
    report["soft_focus"] = True
    if not fg_ok:
        raise GateError("SIMS_FOREGROUND_REQUIRED_FOR_CHEAT_CONSOLE")
    return report


def _send_vk(vk: int, *, up: bool = False) -> None:
    from scripts.win32_input import send_vk

    send_vk(vk, up=up)


def _tap(vk: int) -> None:
    from scripts.win32_input import tap_vk

    tap_vk(vk)


def _type_text(text: str) -> None:
    from scripts.win32_input import type_text

    type_text(text)


def _click(x: int, y: int) -> None:
    """Legacy shared-input adapter API; never called by funding workflow."""
    from scripts.win32_input import send_click

    send_click(x, y, between_sec=0.04)


def _open_console_chord() -> None:
    """A balanced input chord: release all modifiers even if C fails."""
    ctrl_down = shift_down = False
    try:
        _send_vk(0x11)  # CTRL
        ctrl_down = True
        _send_vk(0x10)  # SHIFT
        shift_down = True
        _tap(0x43)  # C
    finally:
        if shift_down:
            _send_vk(0x10, up=True)
        if ctrl_down:
            _send_vk(0x11, up=True)


def _execute_plan(
    plan: dict,
    *,
    process_id: int | None,
    close_console: bool = False,
    session_id: str | None = None,
    idle_ms: int = 15000,
    console_open_method: str = "chord",
    console_ready: bool = False,
    before_input=None,
) -> dict:
    """One bounded funding dispatch under explicit human-first admission.

    The permitted input burst must not masquerade as a verified money change.
    GetLastInputInfo sees our own injected keystrokes, so a fresh 15-second
    idle lease between each *synthetic* character would deadlock. The caller
    holds one exclusive desktop/game lease, probes before borrowing focus,
    and checks exact foreground PID and ACTIVE session between commands.
    """
    if sys.platform != "win32":
        raise GateError("LOCAL_WINDOWS_GAME_HOST_REQUIRED")
    commands = steps_to_commands(plan)
    if console_open_method not in ("chord", "operator-ready"):
        raise GateError("UNSUPPORTED_CONSOLE_OPEN_METHOD")
    if console_open_method == "operator-ready" and console_ready is not True:
        raise GateError("OPERATOR_CONSOLE_FOCUS_ATTESTATION_REQUIRED")
    if (plan.get("state") == "FUNDS_RECOVERY_PLAN_READY"
            and (console_open_method != "operator-ready" or console_ready is not True)):
        raise GateError("RECOVERY_REQUIRES_READY_CONSOLE_NO_TOGGLE")
    if plan.get("game_mode") not in {"live", "build", "buy"}:
        raise GateError("EXPLICIT_GAME_MODE_REQUIRED")
    if any(s.get("step") == "ENSURE_LIVE_MODE" for s in (plan.get("steps") or [])):
        raise GateError("ENSURE_LIVE_MODE_FORBIDDEN")
    if close_console:
        # Esc's menu/cancellation semantics are under separate local forensics.
        # Do not toggle or spam an unverified key after money dispatch.
        raise GateError("CLOSE_CONSOLE_REQUIRES_SEPARATE_LOCAL_CERTIFICATION")
    from betterinstincts.control_handoff import HandoffError
    from betterinstincts.screen_admit import admitted_screen_lease, require_execute_session
    from betterinstincts.host_listener import status as listener_status
    from betterinstincts.player_presence import probe_windows

    try:
        require_execute_session(session_id, process_id)
    except HandoffError as exc:
        raise GateError(str(exc)) from exc

    def verify_game_focus() -> None:
        observed = probe_windows(int(process_id))
        if (
            not observed.probe_ok
            or not observed.foreground_is_sims
            or observed.foreground_process_id != int(process_id)
            or str(observed.foreground_process_name or "").lower() not in ("ts4_x64.exe", "ts4.exe")
            or listener_status(str(session_id)).get("state") != "ACTIVE"
        ):
            raise GateError("GAME_FOREGROUND_OR_SESSION_LOST")

    dispatched = []
    effect_started = False
    claim_path = None
    try:
        with admitted_screen_lease(
            int(process_id),
            str(session_id),
            idle_ms=idle_ms,
            # An operator-armed console must ALREADY own foreground; never
            # borrow focus and invalidate the operator's observed text cursor.
            focus_fn=(None if console_open_method == "operator-ready"
                      else lambda: _focus(process_id)),
        ) as ensure_ready:
            handoff = ensure_ready()
            verify_game_focus()
            if before_input is not None:
                claim_path = before_input()  # Atomic single-use claim after admission.
            if console_open_method == "chord":
                effect_started = True
                _open_console_chord()
                time.sleep(0.55)
            for cmd in commands:
                verify_game_focus()
                effect_started = True
                _type_text(cmd)
                verify_game_focus()
                _tap(0x0D)  # Enter
                time.sleep(0.40)
                dispatched.append(cmd)
    except Exception as exc:
        # Any unexpected input-adapter error after the first key may represent
        # a partially dispatched cheat. Never silently drop this distinction.
        if effect_started:
            raise DispatchUncertain("INPUT_EFFECT_MAY_HAVE_OCCURRED:" + str(exc),
                                    commands_sent=dispatched) from exc
        if isinstance(exc, HandoffError):
            raise GateError("HOST_CONTROL_NOT_ADMITTED:" + str(exc)) from exc
        if isinstance(exc, GateError):
            raise
        raise GateError("FUNDS_PRE_EFFECT_GATE_FAILED:" + type(exc).__name__) from exc
    return {
        "state": "FUNDS_INJECT_DISPATCHED_NOT_VERIFIED",
        "dispatch_ref": "dispatch:" + uuid.uuid4().hex,
        "commands": dispatched,
        "open_console": ("Ctrl+Shift+C" if console_open_method == "chord"
                         else "OPERATOR_ATTESTED_READY_CONSOLE"),
        "mode_agnostic": True,
        "forced_live_mode": False,
        "game_mode": plan.get("game_mode"),
        "handoff": handoff,
        "session_id": session_id,
        "process_id": process_id,
        "recovery_claim": claim_path,
        "target_funds": plan.get("target_funds"),
        "funds_before_reported": plan.get("funds_observed"),
        "proof_ceiling": "INPUT_DISPATCH_ONLY_NOT_ACCEPTANCE_OR_BALANCE_PROOF",
        "next_gate": "OBSERVE_HOUSEHOLD_FUNDS_UI_THEN_VERIFY_WITH_EVIDENCE",
        "auto_retry": False,
        "one_effect_per_invocation": True,
        "console_input_focus_proof": ("OPERATOR_ATTESTED" if console_open_method == "operator-ready" else "NOT_INDEPENDENTLY_PROVEN"),
    }


def _show_overlay(prompt: dict) -> str:
    """Sims-styled yes/no card. Returns option_id."""
    import tkinter as tk

    choice: dict[str, str] = {"value": str(prompt.get("default_option_id") or "accept_subsidy")}

    root = tk.Tk()
    root.title("")
    root.attributes("-topmost", True)
    root.resizable(False, False)
    root.configure(bg="#f4efe6")
    # Center-ish over primary display
    w, h = 520, 280
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 3}")
    root.overrideredirect(True)

    frame = tk.Frame(root, bg="#f4efe6", highlightbackground="#2c2c2c", highlightthickness=2)
    frame.pack(fill="both", expand=True, padx=2, pady=2)

    tk.Label(
        frame,
        text=str(prompt.get("title") or "HOUSEHOLD NOTICE"),
        font=("Segoe UI", 14, "bold"),
        fg="#1a1a1a",
        bg="#f4efe6",
    ).pack(pady=(28, 8))
    tk.Label(
        frame,
        text=str(prompt.get("body") or ""),
        font=("Segoe UI", 11),
        fg="#2a2a2a",
        bg="#f4efe6",
        wraplength=440,
        justify="center",
    ).pack(padx=28, pady=8)

    btn_row = tk.Frame(frame, bg="#f4efe6")
    btn_row.pack(pady=24)

    def pick(oid: str) -> None:
        choice["value"] = oid
        root.destroy()

    options = prompt.get("options") or []
    for opt in options:
        oid = str(opt.get("option_id"))
        label = str(opt.get("label") or oid)
        tk.Button(
            btn_row,
            text=label,
            font=("Segoe UI", 10, "bold"),
            width=16,
            relief="solid",
            bd=1,
            bg="#ffffff",
            fg="#1a1a1a",
            activebackground="#e8e0d4",
            command=lambda o=oid: pick(o),
        ).pack(side="left", padx=12)

    root.bind("<Escape>", lambda _e: pick("decline_subsidy"))
    root.mainloop()
    return choice["value"]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    pl = sub.add_parser("plan")
    pl.add_argument("--funds", type=float, default=None)
    pl.add_argument("--amount", type=float, default=None)
    pl.add_argument("--game-mode", default="unknown")

    pr = sub.add_parser("prompt")
    gate = sub.add_parser("subsidy")
    gate.add_argument("--funds", type=float, required=True)
    gate.add_argument("--choice", default=None, help="accept_subsidy | decline_subsidy; omit for prompt UI")
    gate.add_argument("--game-mode", default="unknown", help="live|build|buy|unknown — never forced")
    gate.add_argument("--overlay", action="store_true", help="Show Sims-styled yes/no card")
    gate.add_argument("--execute", action="store_true")
    gate.add_argument("--close-console", action="store_true", help="Optional Esc after inject (off by default)")
    gate.add_argument("--process-id", type=int, default=None)
    gate.add_argument("--session-id", default=None, help="ACTIVE host_listener session for --execute")
    gate.add_argument("--idle-ms", type=int, default=15000)
    gate.add_argument("--receipt", type=Path, default=None)

    inj = sub.add_parser("inject")
    inj.add_argument("--amount", type=float, default=None)
    inj.add_argument("--funds", type=float, default=None, help="Observed funds for remaining-chunk math")
    inj.add_argument("--game-mode", default="unknown", help="live|build|buy|unknown — never forced")
    inj.add_argument("--execute", action="store_true")
    inj.add_argument("--close-console", action="store_true")
    inj.add_argument("--process-id", type=int, default=None)
    inj.add_argument("--session-id", default=None, help="ACTIVE host_listener session for --execute")
    inj.add_argument("--idle-ms", type=int, default=15000)
    inj.add_argument("--receipt", type=Path, default=None)

    recover = sub.add_parser("recover", help="One explicit observed-noop additive fallback; no chain")
    recover.add_argument("--amount", type=float, required=True)
    recover.add_argument("--funds-before", type=float, required=True)
    recover.add_argument("--funds-after", type=float, required=True)
    recover.add_argument("--evidence-ref", required=True, help="Distinct post-exact HUD observation")
    recover.add_argument("--prior-dispatch-ref", required=True, help="Actual exact-money dispatch ID")
    recover.add_argument("--prior-receipt", type=Path, default=None,
                         help="Original exact-money result under dist/game-host (mandatory for --execute)")
    recover.add_argument("--confirmed-noop", action="store_true",
                         help="Operator confirms no pending exact-money effect")
    recover.add_argument("--game-mode", default="unknown")
    recover.add_argument("--execute", action="store_true")
    recover.add_argument("--close-console", action="store_true")
    recover.add_argument("--process-id", type=int, default=None)
    recover.add_argument("--session-id", default=None)
    recover.add_argument("--idle-ms", type=int, default=15000)
    recover.add_argument("--receipt", type=Path, default=None)

    verify = sub.add_parser("verify", help="Classify externally observed HUD funds; no game input")
    verify.add_argument("--amount", type=float, required=True)
    verify.add_argument("--funds-before", type=float, required=True)
    verify.add_argument("--funds-after", type=float, required=True)
    verify.add_argument("--evidence-ref", default=None)
    verify.add_argument("--route", choices=("exact", "recovery"), default="exact")
    verify.add_argument("--game-mode", default="unknown")
    verify.add_argument("--funds-after-exact", type=float, default=None,
                        help="For recovery: the unchanged HUD after exact money")
    verify.add_argument("--prior-dispatch-ref", default=None)
    verify.add_argument("--no-op-evidence-ref", default=None)
    verify.add_argument("--confirmed-noop", action="store_true")

    for command_parser in (inj, gate, recover):
        command_parser.add_argument("--console-open-method", choices=("chord", "operator-ready"),
                                    default="chord")
        command_parser.add_argument("--console-ready", action="store_true",
                                    help="Required for operator-ready, confirmed live console focus")

    args = p.parse_args(argv)
    receipt_path: Path | None = None
    try:
        if getattr(args, "execute", False):
            # Preserve the existing no-session denial before any other action.
            from betterinstincts.screen_admit import require_execute_session
            from betterinstincts.control_handoff import HandoffError

            try:
                require_execute_session(args.session_id, args.process_id)
            except HandoffError as exc:
                raise GateError(str(exc)) from exc
        receipt_path = _reserve_receipt(
            getattr(args, "receipt", None),
            execute=bool(getattr(args, "execute", False)),
        )
        if args.command == "prompt":
            result = subsidy_prompt()
        elif args.command == "plan":
            result = plan_inject(
                amount=args.amount,
                funds_observed=args.funds,
                game_mode=args.game_mode,
            )
        elif args.command == "verify":
            prior_plan = plan_inject(
                amount=args.amount, funds_observed=args.funds_before,
                game_mode=args.game_mode,
            )
            if args.route == "recovery":
                if args.funds_after_exact is None:
                    raise GateError("POST_EXACT_FUNDS_OBSERVATION_REQUIRED")
                prior_plan = plan_funds_recovery(
                    prior_plan=prior_plan,
                    funds_after=args.funds_after_exact,
                    evidence_ref=args.no_op_evidence_ref,
                    prior_dispatch_ref=args.prior_dispatch_ref,
                    confirmed_noop=args.confirmed_noop,
                )
            result = verify_funds_outcome(
                prior_plan, funds_after=args.funds_after, evidence_ref=args.evidence_ref,
            )
        elif args.command == "recover":
            prior_plan = plan_inject(
                amount=args.amount, funds_observed=args.funds_before,
                game_mode=args.game_mode,
            )
            plan = plan_funds_recovery(
                prior_plan=prior_plan, funds_after=args.funds_after,
                evidence_ref=args.evidence_ref,
                prior_dispatch_ref=args.prior_dispatch_ref,
                confirmed_noop=args.confirmed_noop,
            )
            result = {"plan": plan, "execute": bool(args.execute)}
            if args.execute:
                _require_exact_predecessor(
                    args.prior_receipt, plan,
                    process_id=args.process_id, session_id=args.session_id,
                )
                result["live"] = _execute_plan(
                    plan, process_id=args.process_id,
                    close_console=bool(args.close_console),
                    session_id=args.session_id, idle_ms=int(args.idle_ms),
                    console_open_method=args.console_open_method,
                    console_ready=bool(args.console_ready),
                    before_input=lambda: _claim_recovery_once(plan["prior_dispatch_ref"]),
                )
        elif args.command == "subsidy":
            choice = args.choice
            if args.overlay and choice is None:
                choice = _show_overlay(subsidy_prompt())
            result = evaluate_subsidy_gate(
                args.funds,
                choice=choice,
                game_mode=args.game_mode,
            )
            if (
                args.execute
                and result.get("next_gate") == "EXECUTE_FUNDS_INJECT_WITH_ADMISSION"
                and isinstance(result.get("inject"), dict)
            ):
                live = _execute_plan(
                    result["inject"],
                    process_id=args.process_id,
                    close_console=bool(args.close_console),
                    session_id=args.session_id,
                    idle_ms=int(args.idle_ms),
                    console_open_method=args.console_open_method,
                    console_ready=bool(args.console_ready),
                )
                result = {**result, "live": live, "execute": True}
            else:
                result = {**result, "execute": False}
        else:
            plan = plan_inject(
                amount=args.amount,
                funds_observed=args.funds,
                game_mode=args.game_mode,
            )
            result = {"plan": plan, "execute": bool(args.execute)}
            if args.execute:
                result["live"] = _execute_plan(
                    plan,
                    process_id=args.process_id,
                    close_console=bool(args.close_console),
                    session_id=args.session_id,
                    idle_ms=int(args.idle_ms),
                    console_open_method=args.console_open_method,
                    console_ready=bool(args.console_ready),
                )

        if receipt_path is not None:
            result["receipt"] = str(receipt_path.relative_to(ROOT))
            try:
                _write_receipt(receipt_path, result)
            except (GateError, OSError, ValueError) as exc:
                # INPUT ALREADY MAY HAVE OCCURRED. Never hide the dispatch ref.
                result["receipt_write_error"] = type(exc).__name__ + ":" + str(exc)
                result["persistence_state"] = "RECEIPT_WRITE_FAILED_RECONCILE_NO_REPLAY"
                print(json.dumps(result, sort_keys=True))
                return 3
        print(json.dumps(result, sort_keys=True))
        return 0
    except DispatchUncertain as exc:
        result = {
            "state": "FUNDS_DISPATCH_UNCERTAIN_RECONCILE_NO_REPLAY",
            "reason": str(exc),
            "commands_sent": exc.commands_sent,
            "next_gate": "OBSERVE_HUD_WITH_PLAYER_NO_AUTOMATIC_RETRY",
            "proof_ceiling": "POSSIBLE_INPUT_EFFECT_NOT_VERIFIED",
        }
        if receipt_path is not None:
            result["receipt"] = str(receipt_path.relative_to(ROOT))
            try:
                _write_receipt(receipt_path, result)
            except (GateError, OSError, ValueError) as write_error:
                result["receipt_write_error"] = type(write_error).__name__ + ":" + str(write_error)
        print(json.dumps(result, sort_keys=True))
        return 3
    except (FundsInjectError, GateError, OSError, ValueError, TypeError) as exc:
        result = {"state": "BLOCKED", "reason": str(exc)}
        if receipt_path is not None:
            result["receipt"] = str(receipt_path.relative_to(ROOT))
            try:
                _write_receipt(receipt_path, result)
            except (GateError, OSError, ValueError):
                result["persistence_state"] = "BLOCKED_RECEIPT_WRITE_FAILED_NO_EFFECT_CONFIRMED"
        print(json.dumps(result, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
