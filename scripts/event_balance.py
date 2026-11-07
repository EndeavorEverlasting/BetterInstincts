"""CLI for hosted-event balance / outdoor-social call-stack evaluation."""
import argparse
import json
import sys

from betterinstincts.event_balance import EventBalanceError, evaluate_event_turn, load_contract


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--needs-json", required=True, help='JSON object of six needs 0..1')
    p.add_argument("--event-active", action="store_true")
    p.add_argument("--goals", default="", help="Comma-separated incomplete event goals")
    p.add_argument("--outdoor-social-prefix", action="store_true")
    p.add_argument("--indoor-capacity", action="store_true")
    p.add_argument("--homework-pending", action="store_true")
    p.add_argument("--player-directed", action="store_true")
    p.add_argument("--show-contract", action="store_true")
    args = p.parse_args(argv)
    try:
        if args.show_contract:
            print(json.dumps(load_contract(), indent=2))
            return 0
        needs = json.loads(args.needs_json)
        goals = [g.strip() for g in args.goals.split(",") if g.strip()]
        result = evaluate_event_turn(
            needs,
            event_active=args.event_active,
            event_goals_incomplete=goals,
            outdoor_social_prefix=args.outdoor_social_prefix,
            indoor_capacity_observed=args.indoor_capacity,
            homework_pending=args.homework_pending,
            player_directed=args.player_directed,
        )
        print(json.dumps(result, indent=2))
        return 0
    except (EventBalanceError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"state": "EVENT_BALANCE_FAILED_CLOSED", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
