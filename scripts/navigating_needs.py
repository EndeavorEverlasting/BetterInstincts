"""CLI for Navigating Needs tandem planning and turn evaluation."""
import argparse
import json
import sys

from betterinstincts.navigating_needs import (
    NavigatingNeedsError,
    evaluate_navigating_needs_turn,
    load_contract,
    plan_navigating_needs,
)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--goals", default="", help="Comma-separated incomplete panel goals")
    p.add_argument("--queue", default="", help="Comma-separated queued interaction labels")
    p.add_argument("--evaluate-turn", action="store_true")
    p.add_argument("--navigating-needs-active", action="store_true")
    p.add_argument("--school-day-active", action="store_true")
    p.add_argument("--build-or-buy-mode", action="store_true")
    p.add_argument("--needs-json", default="", help="JSON object of six needs 0..1")
    p.add_argument("--show-contract", action="store_true")
    p.add_argument("--quest-profile", default="navigating_needs")
    args = p.parse_args(argv)
    try:
        if args.show_contract:
            print(json.dumps(load_contract(), indent=2))
            return 0
        goals = [g.strip() for g in args.goals.split(",") if g.strip()]
        queue = [q.strip() for q in args.queue.split(",") if q.strip()]
        if not args.needs_json:
            raise NavigatingNeedsError("NEEDS_JSON_REQUIRED")
        needs = json.loads(args.needs_json)
        if args.evaluate_turn:
            result = evaluate_navigating_needs_turn(
                needs,
                navigating_needs_active=args.navigating_needs_active,
                navigating_needs_incomplete=goals,
                quest_profile=args.quest_profile,
                school_day_active=args.school_day_active,
                build_or_buy_mode=args.build_or_buy_mode,
                queue=queue,
            )
        else:
            result = plan_navigating_needs(
                goals,
                needs,
                quest_profile=args.quest_profile,
                queue=queue,
            )
        print(json.dumps(result, indent=2))
        return 0
    except (NavigatingNeedsError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
