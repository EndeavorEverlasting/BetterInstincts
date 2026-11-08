"""CLI: Build/Buy yield microsystem — rank + per-category best pools (evaluate-only)."""
import argparse
import json
import sys

from betterinstincts.build_optimize import (
    BuildOptimizeError,
    best_pools,
    evaluate_build_optimize,
    evaluate_category_pools,
    load_contract,
    rank_items,
)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--objective",
        default=None,
        choices=[
            "MAXIMIZE_ENV",
            "MAXIMIZE_GREEN",
            "MAXIMIZE_INDUSTRIAL",
            "BALANCED_ENV_GREEN",
            "MAXIMIZE_YIELD",
            "MAXIMIZE_BILL_SAVINGS",
        ],
        help="Ranking objective (default: MAXIMIZE_YIELD)",
    )
    p.add_argument(
        "--category",
        default="wall_covering",
        choices=[
            "wall_covering",
            "floor_covering",
            "window",
            "door",
            "lighting",
            "plumbing",
            "appliance",
            "furniture_decor",
            "outdoor",
            "buy_object",
            "all",
        ],
    )
    p.add_argument(
        "--owned-packs",
        default="base",
        help="Comma-separated pack ids (include base). Example: base,EP09,GP02,EP19",
    )
    p.add_argument("--budget", type=float, default=None)
    p.add_argument("--panels", type=int, default=12, help="Wall panels / instances to project")
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--pool-size", type=int, default=None)
    p.add_argument("--pools", action="store_true", help="Emit per-category best-value pools")
    p.add_argument("--pools-only", action="store_true", help="Only evaluate category pools")
    p.add_argument("--include-pools", action="store_true", help="Attach pools to rank receipt")
    p.add_argument("--player-directed", action="store_true")
    p.add_argument("--not-build-mode", action="store_true")
    p.add_argument("--rank-only", action="store_true")
    p.add_argument("--show-contract", action="store_true")
    args = p.parse_args(argv)
    try:
        if args.show_contract:
            print(json.dumps(load_contract(), indent=2))
            return 0
        packs = [x.strip() for x in args.owned_packs.split(",") if x.strip()]
        category = None if args.category == "all" else args.category
        if args.pools_only or args.pools:
            result = evaluate_category_pools(
                owned_packs=packs,
                budget=args.budget,
                pool_size=args.pool_size,
                player_directed=args.player_directed,
                build_or_buy_mode=not args.not_build_mode,
            )
            print(json.dumps(result, indent=2))
            return 0
        if args.rank_only:
            obj = args.objective or load_contract()["policies"]["default_household_objective"]
            ranked = rank_items(
                obj,
                category=category,
                owned_packs=packs,
                budget=args.budget,
                limit=args.limit,
            )
            payload = {"objective": obj, "picks": ranked}
            if args.include_pools:
                payload["pools"] = best_pools(
                    owned_packs=packs,
                    budget=args.budget,
                    pool_size=args.pool_size,
                )
            print(json.dumps(payload, indent=2))
            return 0
        result = evaluate_build_optimize(
            args.objective,
            category=category,
            owned_packs=packs,
            budget=args.budget,
            panels=args.panels,
            limit=args.limit,
            player_directed=args.player_directed,
            build_or_buy_mode=not args.not_build_mode,
            include_pools=args.include_pools,
            pool_size=args.pool_size,
        )
        print(json.dumps(result, indent=2))
        return 0
    except (BuildOptimizeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(
            json.dumps({"state": "BUILD_OPTIMIZE_FAILED_CLOSED", "error": str(exc)}),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
