#!/usr/bin/env python3
"""Upgrade-parts spam-buy planner CLI (Robot Salvage Parts and siblings).

Remembers the forgotten path:
  Computer → Order → Purchase Upgrade Parts → Robot Salvage Parts

Lab bulk alternative:
  testingcheats → Shift+click robotics workstation → Spawn Crafting Supplies

Evaluate-only by default. Live pie-menu / Shift+click SendInput remains P08-gated
under screen_admit — this CLI prints durable plans and how-to-buy checklists.

Examples:
  python -m scripts.upgrade_parts_force catalog
  python -m scripts.upgrade_parts_force how-to-buy
  python -m scripts.upgrade_parts_force how-to-buy --part robot_salvage_parts
  python -m scripts.upgrade_parts_force plan --part robot_salvage_parts --quantity 20
  python -m scripts.upgrade_parts_force plan --part \"gardener bot parts\" --path spawn
  python -m scripts.upgrade_parts_force plan --quantity 4 --checklist
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from betterinstincts.upgrade_parts_force import (
    UpgradePartsForceError,
    catalog_snapshot,
    how_to_buy,
    plan_parts_force,
    steps_to_operator_checklist,
)


def _print(obj: object) -> int:
    print(json.dumps(obj, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("catalog", help="List upgrade-part catalog + path summaries")

    how = sub.add_parser("how-to-buy", help="Print the forgotten computer Order path")
    how.add_argument("--part", default="robot_salvage_parts")

    plan = sub.add_parser("plan", help="Emit evaluate-only spam-buy / spawn plan")
    plan.add_argument("--part", default="robot_salvage_parts")
    plan.add_argument("--quantity", type=int, default=None)
    plan.add_argument("--path", choices=["computer", "spawn"], default=None)
    plan.add_argument("--mode", default="live", help="Game mode (computer/spawn require live)")
    plan.add_argument("--player-directed", action="store_true")
    plan.add_argument(
        "--checklist",
        action="store_true",
        help="Also emit a flat operator checklist beside the plan JSON",
    )

    args = parser.parse_args(argv)
    try:
        if args.cmd == "catalog":
            return _print(catalog_snapshot())
        if args.cmd == "how-to-buy":
            return _print(how_to_buy(args.part))
        if args.cmd == "plan":
            result = plan_parts_force(
                part_id=args.part,
                quantity=args.quantity,
                path=args.path,
                game_mode=args.mode,
                player_directed=bool(args.player_directed),
            )
            if args.checklist:
                result = dict(result)
                result["operator_checklist"] = steps_to_operator_checklist(result)
            return _print(result)
    except UpgradePartsForceError as exc:
        print(json.dumps({"error": str(exc)}, indent=2, sort_keys=True), file=sys.stderr)
        return 2
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
