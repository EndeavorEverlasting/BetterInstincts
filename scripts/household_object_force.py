#!/usr/bin/env python3
"""Reusable CLI for BetterInstincts household useful-item force catalog.

Library / evaluate-only by default. Does not SendInput.
Elementary unlock for catalog/hidden list items is bb.showhiddenobjects —
never substitute Better BuildBuy or gsi_create_obj.

Examples:
  python -m scripts.household_object_force catalog
  python -m scripts.household_object_force elementary-unlock
  python -m scripts.household_object_force plan --item-id all
  python -m scripts.household_object_force plan --item-id eco_matic_smog_vacuum,hydroponic_planter
  python -m scripts.household_object_force plan --item-id ufo_bed --include-optional
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from betterinstincts.household_object_force import (
    HouseholdObjectForceError,
    catalog_summary,
    elementary_unlock_steps,
    plan_force,
    steps_to_commands,
)


def _dump(payload: dict) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    p_cat = commands.add_parser("catalog", help="List durable useful-item catalog")
    p_cat.add_argument("--include-optional", action="store_true")

    commands.add_parser(
        "elementary-unlock",
        help="Emit the elementary testingcheats + bb.showhiddenobjects steps",
    )

    p_plan = commands.add_parser("plan", help="Plan force sequence for item id(s) or all")
    p_plan.add_argument("--item-id", default="all", help="Comma-separated ids or 'all'")
    p_plan.add_argument("--include-optional", action="store_true")
    p_plan.add_argument("--player-directed", action="store_true")
    p_plan.add_argument(
        "--skip-elementary-unlock",
        action="store_true",
        help="Negative test only — catalog paths must refuse",
    )
    p_plan.add_argument(
        "--substitute-bbb-for-unlock",
        action="store_true",
        help="Negative test only — must refuse",
    )
    p_plan.add_argument("--commands-only", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.command == "catalog":
            return _dump(catalog_summary(include_optional=bool(args.include_optional)))
        if args.command == "elementary-unlock":
            steps = elementary_unlock_steps()
            return _dump({
                "state": "ELEMENTARY_UNLOCK_STEPS",
                "show_hidden_objects": "bb.showhiddenobjects",
                "bbb_role": "OPTIONAL_CATALOG_UX_ONLY_NEVER_SUBSTITUTE",
                "steps": steps,
                "commands": [
                    s["command"] for s in steps if isinstance(s.get("command"), str)
                ],
                "execute_allowed": False,
            })
        if args.command == "plan":
            plan = plan_force(
                item_ids=args.item_id,
                include_optional=bool(args.include_optional),
                player_directed=bool(args.player_directed),
                skip_elementary_unlock=bool(args.skip_elementary_unlock),
                substitute_bbb_for_unlock=bool(args.substitute_bbb_for_unlock),
            )
            if args.commands_only:
                return _dump({"commands": steps_to_commands(plan), "execute_allowed": False})
            return _dump(plan)
    except HouseholdObjectForceError as exc:
        print(
            json.dumps({"state": "ERROR", "error": str(exc)}, indent=2, sort_keys=True),
            file=sys.stderr,
        )
        return 2
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
