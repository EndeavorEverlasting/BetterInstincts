"""CLI for career microsystem evaluation (teen homework tandem)."""
import argparse
import json
import sys

from betterinstincts.career_service import (
    CareerServiceError,
    evaluate_career_service,
    load_contract,
)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--needs-json", required=False, default=None)
    p.add_argument("--homework-pending", action="store_true")
    p.add_argument("--inventory-has-homework", default=None, choices=["true", "false"])
    p.add_argument("--homework-on-lot", default=None, choices=["true", "false"])
    p.add_argument("--location-kind", default="home")
    p.add_argument("--life-stage", default="teen")
    p.add_argument("--school-day-active", action="store_true")
    p.add_argument("--prior-json", default=None)
    p.add_argument("--show-contract", action="store_true")
    args = p.parse_args(argv)
    try:
        if args.show_contract:
            print(json.dumps(load_contract(), indent=2))
            return 0
        if not args.needs_json:
            raise CareerServiceError("NEEDS_JSON_REQUIRED")
        needs = json.loads(args.needs_json)
        inv = None if args.inventory_has_homework is None else args.inventory_has_homework == "true"
        on_lot = None if args.homework_on_lot is None else args.homework_on_lot == "true"
        prior = json.loads(args.prior_json) if args.prior_json else None
        result = evaluate_career_service(
            needs,
            location_kind=args.location_kind,
            school_day_active=args.school_day_active,
            homework_pending=args.homework_pending,
            inventory_has_homework=inv,
            homework_on_lot=on_lot,
            life_stage=args.life_stage,
            prior_state=prior,
        )
        print(json.dumps(result, indent=2))
        return 0
    except (CareerServiceError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(
            json.dumps({"state": "CAREER_SERVICE_FAILED_CLOSED", "error": str(exc)}),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
