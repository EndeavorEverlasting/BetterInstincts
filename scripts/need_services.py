"""CLI for tandem six-need service orchestration."""
import argparse
import json
import sys

from betterinstincts.need_services import (
    NeedServicesError,
    evaluate_need_services,
    load_registry,
)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--needs-json", required=False, default=None)
    p.add_argument("--available-objects", default="")
    p.add_argument("--occupied-objects", default="")
    p.add_argument("--guests-present", action="store_true")
    p.add_argument("--emotion", default=None)
    p.add_argument("--life-stage", default="young_adult")
    p.add_argument("--show-registry", action="store_true")
    args = p.parse_args(argv)
    try:
        if args.show_registry:
            print(json.dumps(load_registry(), indent=2))
            return 0
        if not args.needs_json:
            raise NeedServicesError("NEEDS_JSON_REQUIRED")
        needs = json.loads(args.needs_json)
        result = evaluate_need_services(
            needs,
            available_objects=[x.strip() for x in args.available_objects.split(",") if x.strip()],
            occupied_objects=[x.strip() for x in args.occupied_objects.split(",") if x.strip()],
            guests_present=args.guests_present,
            emotion=args.emotion,
            life_stage=args.life_stage,
        )
        print(json.dumps(result, indent=2))
        return 0
    except (NeedServicesError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"state": "NEED_SERVICES_FAILED_CLOSED", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
