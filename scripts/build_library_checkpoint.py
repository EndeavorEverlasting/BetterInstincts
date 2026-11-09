"""CLI: library-save-before-room-mutate admission (evaluate / plan / live-preflight)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from betterinstincts.build_library_checkpoint import (
    BuildLibraryCheckpointError,
    admit_live_structure_effect,
    evaluate_library_checkpoint,
    load_contract,
    plan_library_save_if_required,
)
from betterinstincts.house_state import HouseStateError, load_or_create


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "CLI: require Sims My Library building save before room/structure/"
            "FLOOR_2/stairs mutation; live-preflight before SendInput."
        )
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show-contract", help="Print the library checkpoint contract")
    admit = sub.add_parser("admit", help="Evaluate library gate for an action")
    admit.add_argument("--run-id", required=True)
    admit.add_argument("--lot-id", required=True)
    admit.add_argument("--action", required=True)
    admit.add_argument("--target", action="append", default=[])
    admit.add_argument("--place-kind", default=None)
    admit.add_argument("--place-story", default=None)
    admit.add_argument("--building-id", default=None)
    admit.add_argument("--held-object", default=None)
    plan = sub.add_parser("plan", help="Whether SAVE_TO_LIBRARY is required next")
    plan.add_argument("--run-id", required=True)
    plan.add_argument("--lot-id", required=True)
    live = sub.add_parser(
        "live-preflight",
        help="Mandatory preflight before live structure SendInput (DELETE/SLEDGE/etc.)",
    )
    live.add_argument("--run-id", required=True)
    live.add_argument("--lot-id", required=True)
    live.add_argument("--action", required=True)
    live.add_argument("--target", action="append", default=[])
    live.add_argument("--place-kind", default=None)
    live.add_argument("--place-story", default=None)
    live.add_argument("--building-id", default=None)
    live.add_argument("--held-object", default=None)
    args = parser.parse_args(argv)
    try:
        if args.cmd == "show-contract":
            print(json.dumps(load_contract(), indent=2, sort_keys=True))
            return 0
        model = load_or_create(args.run_id, args.lot_id)
        if args.cmd == "plan":
            result = plan_library_save_if_required(model) or {
                "state": "LIBRARY_NOT_REQUIRED_FOR_PLAN",
                "action": None,
            }
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        if args.cmd == "live-preflight":
            result = admit_live_structure_effect(
                model,
                args.action,
                targets=args.target,
                place_kind=args.place_kind,
                place_story=args.place_story,
                building_id=args.building_id,
                held_object=args.held_object,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result.get("state") in {
                "LIBRARY_ADMIT", "NOT_ROOM_MUTATION", "LIBRARY_SAVE_ACTION"
            } else 2
        result = evaluate_library_checkpoint(
            model,
            args.action,
            targets=args.target,
            place_kind=args.place_kind,
            place_story=args.place_story,
            building_id=args.building_id,
            held_object=args.held_object,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("state") in {
            "LIBRARY_ADMIT", "NOT_ROOM_MUTATION", "LIBRARY_SAVE_ACTION"
        } else 2
    except (BuildLibraryCheckpointError, HouseStateError, OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
