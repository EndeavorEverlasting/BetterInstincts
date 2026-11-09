#!/usr/bin/env python3
"""CLI for host UI chrome maps, hotkeys, and catalog→inventory plans.

Examples:
  python -m scripts.ui_chrome glossary
  python -m scripts.ui_chrome resolve --mode BUILD --target catalog.search_field --client 1920 1080
  python -m scripts.ui_chrome resolve-item --query "wall shelf"
  python -m scripts.ui_chrome plan --item-id "wall shelf" --mode BUILD --client 1920 1080
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from betterinstincts.ui_chrome import (
    UIChromeError,
    glossary_snapshot,
    load_contract,
    plan_catalog_to_inventory,
    resolve_catalog_item,
    resolve_target,
)


def _dump(payload: dict) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("glossary", help="Hotkeys + panels + catalog items by mode")
    p_res = commands.add_parser("resolve", help="Resolve a named chrome target")
    p_res.add_argument("--mode", required=True, choices=["LIVE", "BUY", "BUILD"])
    p_res.add_argument("--target", required=True)
    p_res.add_argument("--profile", default=None)
    p_res.add_argument("--client", nargs=2, type=int, metavar=("W", "H"), default=None)
    p_item = commands.add_parser(
        "resolve-item",
        help="Resolve catalog item id or operator synonym (wall shelf → a_ok_bloomer)",
    )
    p_item.add_argument("--query", required=True)
    p_plan = commands.add_parser("plan", help="Catalog→Household Inventory plan")
    p_plan.add_argument(
        "--item-id",
        required=True,
        help="Catalog item id or synonym (e.g. a_ok_bloomer, wall shelf)",
    )
    p_plan.add_argument("--mode", required=True, choices=["BUY", "BUILD"])
    p_plan.add_argument("--profile", default=None)
    p_plan.add_argument("--client", nargs=2, type=int, metavar=("W", "H"), default=None)
    args = parser.parse_args(argv)
    try:
        cfg = load_contract()
        if args.command == "glossary":
            return _dump(glossary_snapshot(cfg))
        if args.command == "resolve-item":
            return _dump(resolve_catalog_item(args.query, cfg=cfg))
        width = height = None
        if args.client is not None:
            width, height = args.client
        if args.command == "resolve":
            return _dump(resolve_target(
                args.target,
                mode=args.mode,
                profile=args.profile,
                client_width=width,
                client_height=height,
                cfg=cfg,
            ))
        return _dump(plan_catalog_to_inventory(
            args.item_id,
            mode=args.mode,
            profile=args.profile,
            client_width=width,
            client_height=height,
            cfg=cfg,
        ))
    except UIChromeError as exc:
        print(json.dumps({"error": str(exc)}, indent=2, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
