"""CLI for school-day goal planning and turn evaluation."""
import argparse
import json
import sys

from betterinstincts.school_day import (
    SchoolDayError,
    evaluate_school_day_turn,
    load_contract,
    plan_school_day_goals,
)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--goals", default="", help="Comma-separated incomplete school HUD goals")
    p.add_argument("--queue", default="", help="Comma-separated queued interaction labels")
    p.add_argument("--phase", default="morning_free_time")
    p.add_argument("--pinned-whims", default="", help="Comma-separated pinned whim labels")
    p.add_argument("--evaluate-turn", action="store_true")
    p.add_argument("--school-day-active", action="store_true")
    p.add_argument("--location-kind", default="school")
    p.add_argument("--homework-pending", action="store_true")
    p.add_argument("--needs-json", default="", help="JSON object of six needs 0..1")
    p.add_argument("--show-contract", action="store_true")
    p.add_argument("--school-profile", default="high_school_years")
    args = p.parse_args(argv)
    try:
        if args.show_contract:
            print(json.dumps(load_contract(), indent=2))
            return 0
        goals = [g.strip() for g in args.goals.split(",") if g.strip()]
        queue = [q.strip() for q in args.queue.split(",") if q.strip()]
        whims = [w.strip() for w in args.pinned_whims.split(",") if w.strip()]
        if args.evaluate_turn:
            if not args.needs_json:
                raise SchoolDayError("NEEDS_JSON_REQUIRED_FOR_TURN")
            needs = json.loads(args.needs_json)
            result = evaluate_school_day_turn(
                needs,
                school_day_active=args.school_day_active,
                school_goals_incomplete=goals,
                school_phase=args.phase,
                school_profile=args.school_profile,
                location_kind=args.location_kind,
                homework_pending=args.homework_pending,
                queue=queue,
                pinned_whims=whims,
            )
        else:
            result = plan_school_day_goals(
                goals,
                school_profile=args.school_profile,
                school_phase=args.phase,
                queue=queue,
                pinned_whims=whims,
            )
        print(json.dumps(result, indent=2))
        return 0
    except (SchoolDayError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"state": "SCHOOL_DAY_FAILED_CLOSED", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
