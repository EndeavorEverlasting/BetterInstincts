"""CLI for Curious Catalog — rare/money garden shelves. Never touches game speed."""
from __future__ import annotations

import argparse
import json
import sys

from betterinstincts.curious_catalog import (
    CuriousCatalogError,
    activate,
    deactivate,
    evaluate_advisory,
    is_active,
    load_contract,
    money_garden_shop_list,
    plan_reveal,
    shelf_peek_prompt,
    status,
)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    act = sub.add_parser("activate")
    act.add_argument("--session-id", required=True)
    act.add_argument("--note", default=None)

    de = sub.add_parser("deactivate")
    de.add_argument("--session-id", required=True)

    st = sub.add_parser("status")
    st.add_argument("--session-id", required=True)

    sub.add_parser("plan")
    shop = sub.add_parser("shop-list", help="Ranked rare/money garden targets")
    shop.add_argument("--tier", default=None, help="S | A | tool")

    sub.add_parser("prompt")
    adv = sub.add_parser("advisory")
    adv.add_argument("--session-id", default=None)
    adv.add_argument("--whims", default="")
    adv.add_argument("--player-requested", action="store_true")

    rev = sub.add_parser("reveal", help="Plan reveal (no SendInput — pause-safe)")
    rev.add_argument("--session-id", required=True)
    rev.add_argument("--live-edit", action="store_true")

    sub.add_parser("show-contract")

    args = p.parse_args(argv)
    try:
        cfg = load_contract()
        if args.cmd == "show-contract":
            print(json.dumps(cfg, indent=2))
            return 0
        if args.cmd == "activate":
            print(json.dumps(activate(args.session_id, note=args.note), indent=2))
            return 0
        if args.cmd == "deactivate":
            print(json.dumps(deactivate(args.session_id), indent=2))
            return 0
        if args.cmd == "status":
            print(json.dumps(status(args.session_id), indent=2))
            return 0
        if args.cmd == "plan":
            print(json.dumps(plan_reveal(), indent=2))
            return 0
        if args.cmd == "shop-list":
            print(json.dumps(money_garden_shop_list(tier=args.tier), indent=2))
            return 0
        if args.cmd == "prompt":
            print(json.dumps(shelf_peek_prompt(cfg), indent=2))
            return 0
        if args.cmd == "advisory":
            active = bool(args.session_id and is_active(args.session_id))
            whims = [x.strip() for x in args.whims.split(",") if x.strip()]
            print(
                json.dumps(
                    evaluate_advisory(
                        session_active=active,
                        whims=whims,
                        player_requested=bool(args.player_requested),
                    ),
                    indent=2,
                )
            )
            return 0
        if args.cmd == "reveal":
            if not is_active(args.session_id):
                print(
                    json.dumps(
                        {
                            "state": "SESSION_NOT_ACTIVE",
                            "next": "activate first; reveal is plan-only (no SendInput)",
                        }
                    ),
                    file=sys.stderr,
                )
                return 2
            plan = plan_reveal(include_live_edit=bool(args.live_edit))
            print(
                json.dumps(
                    {
                        "state": "CURIOUS_CATALOG_REVEAL_PLAN_ONLY",
                        "note": "SendInput disabled — operator types player_lines while paused; never touch speed",
                        "plan": plan,
                    },
                    indent=2,
                )
            )
            return 0
        return 2
    except (CuriousCatalogError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(
            json.dumps({"state": "CURIOUS_CATALOG_FAILED_CLOSED", "error": str(exc)}),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
