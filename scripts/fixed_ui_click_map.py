#!/usr/bin/env python3
"""CLI for fixed-HUD click ledger (evaluate/record only — no SendInput)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from betterinstincts.fixed_ui_click_map import (
    FixedUiClickMapError,
    classify_click,
    default_ledger_path,
    ensure_seeded_ledger,
    load_contract,
    load_ledger,
    plan_arm_to_console_handoff,
    record_click_attempt,
    resolve_target_xy,
    save_ledger,
    seed_targets_from_contract,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Fixed UI click map / arm→console handoff")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog", help="Show seed targets + handoff contract")
    rs = sub.add_parser("resolve", help="Resolve attested/candidate xy for a target")
    rs.add_argument("--target-id", required=True)
    rs.add_argument("--ledger", type=Path, default=None)
    rec = sub.add_parser("record", help="Append a click attempt to the ledger")
    rec.add_argument("--target-id", required=True)
    rec.add_argument("--client-xy", required=True, help="X,Y client pixels")
    rec.add_argument(
        "--classification",
        required=True,
        choices=["HIT", "NEAR_MISS", "MISS", "WRONG_CONTROL", "OUT_OF_SCOPE_MOVING_TARGET"],
    )
    rec.add_argument("--observed-control-id", default=None)
    rec.add_argument("--note", default="")
    rec.add_argument("--moving-target", action="store_true")
    rec.add_argument("--ledger", type=Path, default=None)
    sub.add_parser("handoff", help="Plan ARM_LIVE_HOTKEYS → CHEAT_CONSOLE handoff")
    sc = sub.add_parser("score", help="Score intended vs observed xy")
    sc.add_argument("--intended-xy", required=True)
    sc.add_argument("--observed-xy", required=True)
    sc.add_argument("--intended-target-id", default=None)
    sc.add_argument("--observed-control-id", default=None)
    args = p.parse_args(argv)

    try:
        if args.command == "catalog":
            cfg = load_contract()
            result = {
                "contract": "contracts/fixed-ui-click-map.v1.json",
                "handoff": cfg.get("handoff"),
                "seed_targets": seed_targets_from_contract(cfg),
                "ledger_default": str(default_ledger_path(cfg)),
                "execute_allowed": False,
            }
        elif args.command == "resolve":
            ledger = ensure_seeded_ledger(load_ledger(args.ledger))
            result = resolve_target_xy(ledger, args.target_id)
        elif args.command == "record":
            parts = [p.strip() for p in str(args.client_xy).split(",")]
            if len(parts) != 2:
                raise FixedUiClickMapError("CLIENT_XY_MUST_BE_X_COMMA_Y")
            xy = [int(parts[0]), int(parts[1])]
            path = args.ledger or default_ledger_path()
            ledger = ensure_seeded_ledger(load_ledger(path))
            attempt = record_click_attempt(
                ledger,
                target_id=args.target_id,
                client_xy=xy,
                classification=args.classification,
                observed_control_id=args.observed_control_id,
                note=args.note,
                moving_target=bool(args.moving_target)
                or args.classification == "OUT_OF_SCOPE_MOVING_TARGET",
            )
            saved = save_ledger(ledger, path)
            result = {"attempt": attempt, "ledger": str(saved), "targets": ledger.get("targets")}
        elif args.command == "handoff":
            result = plan_arm_to_console_handoff()
        elif args.command == "score":
            def _xy(raw: str) -> list[int]:
                parts = [p.strip() for p in str(raw).split(",")]
                if len(parts) != 2:
                    raise FixedUiClickMapError("XY_MUST_BE_X_COMMA_Y")
                return [int(parts[0]), int(parts[1])]

            result = classify_click(
                intended_xy=_xy(args.intended_xy),
                observed_xy=_xy(args.observed_xy),
                intended_target_id=args.intended_target_id,
                observed_control_id=args.observed_control_id,
            )
        else:
            raise FixedUiClickMapError("UNKNOWN_COMMAND")
    except FixedUiClickMapError as exc:
        print(json.dumps({"state": "ERROR", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
