"""CLI for teen homework career-performance turn evaluation."""
import argparse
import json
import sys

from betterinstincts.teen_homework import (
    TeenHomeworkError,
    evaluate_teen_homework_turn,
    load_contract,
    recovery_plan,
)


def _tri(name: str) -> bool | None:
    if not name:
        return None
    low = name.lower()
    if low in {"true", "1", "yes"}:
        return True
    if low in {"false", "0", "no"}:
        return False
    return None


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evaluate-turn", action="store_true")
    p.add_argument("--needs-json", default="", help="JSON object of six needs 0..1")
    p.add_argument("--location-kind", default="home")
    p.add_argument("--school-day-active", action="store_true")
    p.add_argument("--homework-pending", action="store_true")
    p.add_argument("--inventory-has-homework", default="", help="true|false|omit")
    p.add_argument("--homework-on-lot", default="", help="true|false|omit")
    p.add_argument("--available-objects", default="", help="Comma-separated lot object labels")
    p.add_argument("--queue", default="", help="Comma-separated queue labels")
    p.add_argument("--life-stage", default="teen")
    p.add_argument("--show-contract", action="store_true")
    p.add_argument("--show-recovery", action="store_true")
    args = p.parse_args(argv)
    try:
        if args.show_contract:
            print(json.dumps(load_contract(), indent=2))
            return 0
        if args.show_recovery:
            print(
                json.dumps(
                    {
                        "recovery_ladder": recovery_plan(
                            homework_on_lot=_tri(args.homework_on_lot),
                        )
                    },
                    indent=2,
                )
            )
            return 0
        if not args.evaluate_turn:
            raise TeenHomeworkError("USE_EVALUATE_TURN_OR_SHOW_CONTRACT")
        if not args.needs_json:
            raise TeenHomeworkError("NEEDS_JSON_REQUIRED_FOR_TURN")
        needs = json.loads(args.needs_json)
        queue = [q.strip() for q in args.queue.split(",") if q.strip()]
        objects = [o.strip() for o in args.available_objects.split(",") if o.strip()]
        result = evaluate_teen_homework_turn(
            needs,
            location_kind=args.location_kind,
            school_day_active=args.school_day_active,
            homework_pending=args.homework_pending,
            inventory_has_homework=_tri(args.inventory_has_homework),
            homework_on_lot=_tri(args.homework_on_lot),
            available_objects=objects,
            queue=queue,
            life_stage=args.life_stage,
        )
        print(json.dumps(result, indent=2))
        return 0
    except (TeenHomeworkError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"state": "TEEN_HOMEWORK_FAILED_CLOSED", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
