#!/usr/bin/env python3
"""Dismiss known Sims main-menu blockers before Load Game / Play.

Durable host fallback: MEMORY BOOST IS NOW ON must be closed via modal X before
template navigation. Never Resume. Never READ FAQ.

Examples:
  python -m scripts.menu_blockers plan
  python -m scripts.menu_blockers dismiss --process-id PID --session-id SESSION --execute
  python -m scripts.menu_blockers dismiss --blocker memory_boost_on --process-id PID --session-id SESSION --execute
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

from betterinstincts.menu_blockers import (
    MenuBlockerError,
    assert_safe_action,
    plan_dismiss,
)
from scripts.win32_input import send_click

OUTPUT = ROOT / "dist" / "game-host"


class GateError(ValueError):
    pass


def _focus(process_id: int | None) -> None:
    from scripts.game_host import focus

    focus(process_id=process_id)


def _send_click(x: int, y: int) -> None:
    send_click(x, y, between_sec=0.04)


def dismiss(*, process_id: int | None, execute: bool, blocker_ids: list[str] | None,
            receipt: Path | None, session_id: str | None = None, idle_ms: int = 8000) -> dict:
    plan = plan_dismiss(blocker_ids)
    out: dict = {
        "plan": plan,
        "execute": bool(execute),
        "proof_ceiling": "MENU_BLOCKER_CLICK_DISPATCH_NOT_LIVE_PROOF",
    }
    if not execute:
        out["state"] = "DRY_RUN"
        out["next"] = (
            "python -m scripts.menu_blockers dismiss --process-id PID "
            "--session-id SESSION --execute"
        )
        return out
    if sys.platform != "win32":
        raise GateError("LOCAL_WINDOWS_GAME_HOST_REQUIRED")
    from betterinstincts.control_handoff import HandoffError
    from betterinstincts.screen_admit import admitted_screen_lease, require_execute_session
    try:
        require_execute_session(session_id, process_id)
    except HandoffError as exc:
        raise GateError(str(exc)) from exc
    steps = []
    last_handoff = None
    with admitted_screen_lease(
        int(process_id),
        str(session_id),
        idle_ms=idle_ms,
        focus_fn=lambda: _focus(process_id),
    ) as ensure_ready:
        for step in plan["steps"]:
            assert_safe_action(step["step"])
            try:
                last_handoff = ensure_ready()
            except HandoffError as exc:
                raise GateError(str(exc)) from exc
            x, y = step["click"]
            _send_click(int(x), int(y))
            time.sleep(0.8)
            steps.append({
                "step": step["step"],
                "blocker_id": step["blocker_id"],
                "click": [x, y],
                "state": "DISMISS_CLICK_DISPATCHED",
                "forbidden": step["forbidden"],
            })
    out["steps"] = steps
    out["session_id"] = session_id
    out["handoff"] = last_handoff
    out["state"] = "MENU_BLOCKERS_DISMISS_DISPATCHED"
    out["next"] = (
        "PrintWindow-confirm main_menu clear of Memory Boost; then "
        "game_host navigate Load Game → LabLab → Play — never Resume"
    )
    if receipt is not None:
        path = receipt if receipt.is_absolute() else ROOT / receipt
        path = path.resolve()
        if not path.is_relative_to(OUTPUT.resolve()):
            raise GateError("RECEIPT_OUTSIDE_DIST_GAME_HOST")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        out["receipt"] = str(path.relative_to(ROOT))
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    d = sub.add_parser("dismiss")
    d.add_argument("--process-id", type=int, default=None)
    d.add_argument("--session-id", default=None, help="ACTIVE host_listener session for --execute")
    d.add_argument("--idle-ms", type=int, default=8000)
    d.add_argument("--execute", action="store_true")
    d.add_argument("--blocker", action="append", default=None,
                   help="Optional blocker id; repeatable. Default: all known blockers.")
    d.add_argument("--receipt", type=Path, default=None)
    args = p.parse_args(argv)
    try:
        if args.command == "plan":
            result = plan_dismiss(None)
        else:
            result = dismiss(
                process_id=args.process_id,
                execute=bool(args.execute),
                blocker_ids=args.blocker,
                receipt=args.receipt,
                session_id=args.session_id,
                idle_ms=int(args.idle_ms),
            )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (MenuBlockerError, GateError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
