"""CLI: structure-first Build/Buy integrity (evaluate-only)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from betterinstincts.build_integrity import (
    BuildIntegrityError,
    evaluate_integrity,
    load_contract,
    structure_restore_plan,
)
from betterinstincts.house_state import HouseStateError, load_or_create


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("show-contract")

    ev = sub.add_parser("evaluate")
    ev.add_argument("--run-id", required=True)
    ev.add_argument("--lot-id", required=True)
    ev.add_argument("--action", required=True)
    ev.add_argument("--target", action="append", default=[])
    ev.add_argument("--place-kind", default=None)
    ev.add_argument("--place-domain", default=None)
    ev.add_argument("--nest-risk", action="store_true")
    ev.add_argument("--strips-zone", default=None)

    rp = sub.add_parser("restore-plan")
    rp.add_argument("--run-id", required=True)
    rp.add_argument("--lot-id", required=True)

    args = p.parse_args(argv)
    try:
        if args.cmd == "show-contract":
            print(json.dumps(load_contract(), indent=2))
            return 0
        model = load_or_create(args.run_id, args.lot_id)
        if args.cmd == "restore-plan":
            print(json.dumps(structure_restore_plan(model), indent=2))
            return 0
        if args.cmd == "evaluate":
            print(json.dumps(
                evaluate_integrity(
                    model,
                    action=args.action,
                    targets=args.target,
                    place_kind=args.place_kind,
                    place_domain=args.place_domain,
                    nest_risk=args.nest_risk,
                    strips_zone=args.strips_zone,
                ),
                indent=2,
            ))
            return 0
        raise BuildIntegrityError("UNKNOWN_COMMAND")
    except (BuildIntegrityError, HouseStateError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"state": "BUILD_INTEGRITY_FAILED_CLOSED", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
