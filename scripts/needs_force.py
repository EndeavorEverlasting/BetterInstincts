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

OUTPUT = ROOT / "dist" / "game-host"


class GateError(ValueError):
    pass


def _send_click(x: int, y: int) -> None:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    LD, LU = 2, 4

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", ctypes.c_long), ("dy", ctypes.c_long),
            ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class INPUT(ctypes.Structure):
        class _I(ctypes.Union):
            _fields_ = [("mi", MOUSEINPUT)]

        _anonymous_ = ("i",)
        _fields_ = [("type", wintypes.DWORD), ("i", _I)]

    user32.SetCursorPos(x, y)
    time.sleep(0.05)
    for flag in (LD, LU):
        inp = INPUT(type=0)
        inp.mi = MOUSEINPUT(0, 0, 0, flag, 0, None)
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        time.sleep(0.05)


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
        from scripts.game_host import focus
        focus(process_id=args.process_id)
        dispatched = []
        for step in plan["steps"]:
            if step.get("execution") != "HOST_SENDINPUT":
                continue
            x, y = step["click"]
            _send_click(int(x), int(y))
            time.sleep(max(0.3, min(5.0, float(args.settle_sec))))
            dispatched.append({"id": step["id"], "click": [x, y], "state": "CLICK_DISPATCHED"})
        out = {
            "state": "NEEDS_FORCE_DISPATCHED",
            "route": plan["route"],
            "steps": dispatched,
            "run_id": args.run_id,
            "proof_ceiling": "NEEDS_FORCE_CLICK_DISPATCH_NOT_LIVE_CERT",
            "forbidden": plan["forbidden"],
        }
        if args.receipt is not None:
            path = args.receipt if args.receipt.is_absolute() else ROOT / args.receipt
            path = path.resolve()
            if not path.is_relative_to(OUTPUT.resolve()):
                raise GateError("RECEIPT_OUTSIDE_DIST_GAME_HOST")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            out["receipt"] = str(path.relative_to(ROOT))
        print(json.dumps(out, sort_keys=True))
        return 0
    except (NeedsForceError, GateError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
