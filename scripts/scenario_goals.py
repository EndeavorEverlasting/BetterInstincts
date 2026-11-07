"""CLI for scenario goal planning and turn evaluation."""
import argparse
import json
import sys

from betterinstincts.scenario_goals import (
    ScenarioGoalsError,
    evaluate_scenario_turn,
    load_contract,
    plan_scenario_goals,
)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--goals", default="", help="Comma-separated incomplete scenario HUD goals")
    p.add_argument("--queue", default="", help="Comma-separated queued interaction labels")
    p.add_argument("--evaluate-turn", action="store_true")
    p.add_argument("--scenario-active", action="store_true")
    p.add_argument("--school-day-active", action="store_true")
    p.add_argument("--allow-career", action="store_true")
    p.add_argument("--needs-game-certified", action="store_true")
    p.add_argument("--income-game-observed", action="store_true")
    p.add_argument("--needs-json", default="", help="JSON object of six needs 0..1")
    p.add_argument("--show-contract", action="store_true")
    p.add_argument("--scenario-profile", default="scoring_simoleons")
    args = p.parse_args(argv)
    try:
        if args.show_contract:
            print(json.dumps(load_contract(), indent=2))
            return 0
        goals = [g.strip() for g in args.goals.split(",") if g.strip()]
        queue = [q.strip() for q in args.queue.split(",") if q.strip()]
        if args.evaluate_turn:
            if not args.needs_json:
                raise ScenarioGoalsError("NEEDS_JSON_REQUIRED_FOR_TURN")
            needs = json.loads(args.needs_json)
            result = evaluate_scenario_turn(
                needs,
                scenario_active=args.scenario_active,
                scenario_goals_incomplete=goals,
                scenario_profile=args.scenario_profile,
                school_day_active=args.school_day_active,
                allow_career=args.allow_career,
                needs_game_certified=args.needs_game_certified,
                income_game_observed=args.income_game_observed,
                queue=queue,
            )
        else:
            result = plan_scenario_goals(
                goals,
                scenario_profile=args.scenario_profile,
                queue=queue,
                allow_career=args.allow_career,
                needs_game_certified=args.needs_game_certified,
                income_game_observed=args.income_game_observed,
            )
        print(json.dumps(result, indent=2))
        return 0
    except (ScenarioGoalsError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"state": "SCENARIO_GOALS_FAILED_CLOSED", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
