"""CLI: classify inside/outside and FLOOR_1/FLOOR_2; print build order."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from betterinstincts.build_spatial import (
    BuildSpatialError,
    admit_spatial_placement,
    build_order_plan,
    inventory_spatial,
    load_contract,
)
from betterinstincts.house_state import HouseStateError, load_or_create


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show-contract")

    inv = sub.add_parser("inventory")
    inv.add_argument("--run-id", required=True)
    inv.add_argument("--lot-id", required=True)

    order = sub.add_parser("order")
    order.add_argument("--run-id", required=True)
    order.add_argument("--lot-id", required=True)

    admit = sub.add_parser("admit")
    admit.add_argument("--run-id", required=True)
    admit.add_argument("--lot-id", required=True)
    admit.add_argument("--enclosure", required=True)
    admit.add_argument("--story", required=True)
    admit.add_argument("--domain", default=None)
    admit.add_argument("--outdoor-ok", action="store_true")

    args = p.parse_args(argv)
    try:
        if args.cmd == "show-contract":
            print(json.dumps(load_contract(), indent=2))
            return 0
        model = load_or_create(args.run_id, args.lot_id)
        if args.cmd == "inventory":
            print(json.dumps(inventory_spatial(model), indent=2))
            return 0
        if args.cmd == "order":
            print(json.dumps(build_order_plan(model), indent=2))
            return 0
        if args.cmd == "admit":
            print(json.dumps(
                admit_spatial_placement(
                    model,
                    place_enclosure=args.enclosure,
                    place_story=args.story,
                    place_domain=args.domain,
                    indoor_required=not args.outdoor_ok,
                ),
                indent=2,
            ))
            return 0
        raise BuildSpatialError("UNKNOWN_COMMAND")
    except (BuildSpatialError, HouseStateError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"state": "BUILD_SPATIAL_FAILED_CLOSED", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
