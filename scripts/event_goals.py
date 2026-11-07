"""CLI for event goal → interaction planning."""
import argparse
import json
import sys

from betterinstincts.event_goals import EventGoalsError, load_contract, plan_event_goals


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--goals", default="", help="Comma-separated incomplete HUD goals")
    p.add_argument("--queue", default="", help="Comma-separated queued interaction labels")
    p.add_argument("--event-profile", default="lounge_party")
    p.add_argument("--outdoor-social-prefix", action="store_true")
    p.add_argument("--show-contract", action="store_true")
    args = p.parse_args(argv)
    try:
        if args.show_contract:
            print(json.dumps(load_contract(), indent=2))
            return 0
        goals = [g.strip() for g in args.goals.split(",") if g.strip()]
        queue = [q.strip() for q in args.queue.split(",") if q.strip()]
        result = plan_event_goals(
            goals,
            event_profile=args.event_profile,
            queue=queue,
            outdoor_social_prefix=args.outdoor_social_prefix,
        )
        print(json.dumps(result, indent=2))
        return 0
    except (EventGoalsError, TypeError, ValueError) as exc:
        print(json.dumps({"state": "EVENT_GOALS_FAILED_CLOSED", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
