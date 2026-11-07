"""CLI for Fun-need tandem lane planning."""
import argparse
import json
import sys

from betterinstincts.fun_service import FunServiceError, evaluate_fun_service, load_contract


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--needs-json", required=False, default=None)
    p.add_argument("--available-objects", default="", help="Comma-separated lot/inventory objects")
    p.add_argument("--occupied-objects", default="", help="Objects guests/other Sims are using")
    p.add_argument("--guests-present", action="store_true")
    p.add_argument("--emotion", default=None)
    p.add_argument("--moodlets", default="")
    p.add_argument("--life-stage", default="young_adult")
    p.add_argument("--traits", default="")
    p.add_argument("--queue", default="")
    p.add_argument("--event-active", action="store_true")
    p.add_argument("--event-fun-via-goals", action="store_true")
    p.add_argument("--show-contract", action="store_true")
    args = p.parse_args(argv)
    try:
        if args.show_contract:
            print(json.dumps(load_contract(), indent=2))
            return 0
        if not args.needs_json:
            raise FunServiceError("NEEDS_JSON_REQUIRED")
        needs = json.loads(args.needs_json)
        result = evaluate_fun_service(
            needs,
            available_objects=[x.strip() for x in args.available_objects.split(",") if x.strip()],
            occupied_objects=[x.strip() for x in args.occupied_objects.split(",") if x.strip()],
            guests_present=args.guests_present,
            emotion=args.emotion,
            moodlets=[x.strip() for x in args.moodlets.split(",") if x.strip()],
            life_stage=args.life_stage,
            traits=[x.strip() for x in args.traits.split(",") if x.strip()],
            queue=[x.strip() for x in args.queue.split(",") if x.strip()],
            event_active=args.event_active,
            event_fun_via_goals=args.event_fun_via_goals,
        )
        print(json.dumps(result, indent=2))
        return 0
    except (FunServiceError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"state": "FUN_SERVICE_FAILED_CLOSED", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
