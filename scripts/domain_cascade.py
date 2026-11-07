"""CLI for domain cascade poll receipts."""
import argparse
import json
import sys

from betterinstincts.domain_cascade import DomainCascadeError, load_contract, poll_cascade


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--needs-json", required=False, default="", help="JSON object of six needs 0..1")
    p.add_argument("--funds", type=float, default=None)
    p.add_argument("--objects", default="", help="Comma-separated available objects")
    p.add_argument("--show-contract", action="store_true")
    p.add_argument("--navigating-needs-active", action="store_true")
    p.add_argument("--navigating-goals", default="")
    p.add_argument("--scenario-active", action="store_true")
    p.add_argument("--scenario-goals", default="")
    args = p.parse_args(argv)
    try:
        if args.show_contract:
            print(json.dumps(load_contract(), indent=2))
            return 0
        if not args.needs_json:
            raise DomainCascadeError("NEEDS_JSON_REQUIRED")
        needs = json.loads(args.needs_json)
        objects = [x.strip() for x in args.objects.split(",") if x.strip()]
        nav_goals = [g.strip() for g in args.navigating_goals.split(",") if g.strip()]
        scen_goals = [g.strip() for g in args.scenario_goals.split(",") if g.strip()]
        result = poll_cascade(
            needs,
            available_objects=objects,
            funds=args.funds,
            navigating_needs_active=args.navigating_needs_active,
            navigating_needs_incomplete=nav_goals,
            scenario_active=args.scenario_active,
            scenario_goals_incomplete=scen_goals,
        )
        print(json.dumps(result, indent=2))
        return 0
    except (DomainCascadeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
