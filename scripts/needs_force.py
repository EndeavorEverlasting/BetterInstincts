#!/usr/bin/env python3
"""Critical-needs force planner/runner — MAP_TRAVEL first, never in-frame walk thrash.

Plan is always available. --execute SendInputs only on Windows with explicit flag.
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

from betterinstincts.needs_force import NeedsForceError, plan_force
from scripts.win32_input import send_click as _send_click

OUTPUT = ROOT / "dist" / "game-host"


class GateError(ValueError):
    pass


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    plan_p = sub.add_parser("plan")
    plan_p.add_argument("--location-kind", default="school")
    plan_p.add_argument("--objects-on-lot", action="store_true")
    plan_p.add_argument("--disposition", default="OPTIMIZE")
    run_p = sub.add_parser("run")
    run_p.add_argument("--location-kind", default="school")
    run_p.add_argument("--objects-on-lot", action="store_true")
    run_p.add_argument("--disposition", default="OPTIMIZE")
    run_p.add_argument("--process-id", type=int, default=None)
    run_p.add_argument("--session-id", default=None, help="Explicitly activated host-listener session")
    run_p.add_argument("--step-id", default=None, help="One verified, scene-appropriate UI step per invocation")
    run_p.add_argument("--idle-ms", type=int, default=15000)
    run_p.add_argument("--execute", action="store_true")
    run_p.add_argument("--settle-sec", type=float, default=1.5)
    run_p.add_argument("--run-id", default=None)
    run_p.add_argument("--receipt", type=Path, default=None)
    args = p.parse_args(argv)
    try:
        plan = plan_force(
            location_kind=args.location_kind,
            objects_on_current_lot=bool(getattr(args, "objects_on_lot", False)),
            disposition=args.disposition,
        )
        if args.command == "plan" or not args.execute:
            print(json.dumps({"state": "DRY_RUN" if args.command == "run" else plan["state"],
                              "plan": plan}, sort_keys=True))
            return 0
        if sys.platform != "win32":
            raise GateError("LOCAL_WINDOWS_GAME_HOST_REQUIRED")
        if "IN_FRAME_WALK_THRASH" in plan.get("forbidden", []):
            # Structural guard — plan route must not be walk thrash.
            if plan.get("route") == "IN_FRAME_WALK_THRASH":
                raise GateError("FORBIDDEN_ROUTE_IN_FRAME_WALK_THRASH")
        # Shared screen control is NOT implicit in --execute: the operator must
        # activate a bounded session. One click is the maximum control lease.
        if not args.session_id or not args.step_id:
            raise GateError("HANDOFF_SESSION_AND_SINGLE_STEP_REQUIRED")
        if args.process_id is None or args.process_id <= 0:
            raise GateError("EXACT_GAME_PROCESS_ID_REQUIRED")
        selected = [s for s in plan["steps"] if s["id"] == args.step_id and s["execution"] == "HOST_SENDINPUT"]
        if len(selected) != 1:
            raise GateError("STEP_NOT_IN_VERIFIED_PLAN")
        # Validate receipt destination BEFORE any UI mutation.
        receipt_path = None
        if args.receipt is not None:
            receipt_path = args.receipt if args.receipt.is_absolute() else ROOT / args.receipt
            receipt_path = receipt_path.resolve()
            if not receipt_path.is_relative_to(OUTPUT.resolve()) or receipt_path.is_symlink():
                raise GateError("RECEIPT_OUTSIDE_DIST_GAME_HOST")
        from betterinstincts.control_handoff import HandoffError
        from betterinstincts.screen_admit import admitted_screen_lease
        from scripts.game_host import focus
        # Shared gate doubles the input-age check BEFORE focus and AFTER
        # focus, then enforces exact game foreground for this single step.
        with admitted_screen_lease(
            args.process_id, args.session_id, idle_ms=args.idle_ms,
            focus_fn=lambda: focus(process_id=args.process_id),
        ) as ensure_ready:
            try:
                handoff = ensure_ready()
            except HandoffError as exc:
                raise GateError(str(exc)) from exc
            step = selected[0]
            x, y = step["click"]
            _send_click(int(x), int(y))
            time.sleep(max(0.3, min(5.0, float(args.settle_sec))))
            dispatched = [{"id": step["id"], "click": [x, y], "state": "CLICK_DISPATCHED"}]
            out = {
                "state": "NEEDS_FORCE_DISPATCHED",
                "route": plan["route"],
                "steps": dispatched,
                "run_id": args.run_id,
                "handoff": handoff,
                "session_id": args.session_id,
                "single_step_only": True,
                "proof_ceiling": "NEEDS_FORCE_CLICK_DISPATCH_NOT_LIVE_CERT",
                "forbidden": plan["forbidden"],
            }
            if receipt_path is not None:
                receipt_path.parent.mkdir(parents=True, exist_ok=True)
                receipt_path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                out["receipt"] = str(receipt_path.relative_to(ROOT))
        print(json.dumps(out, sort_keys=True))
        return 0
    except (NeedsForceError, GateError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
