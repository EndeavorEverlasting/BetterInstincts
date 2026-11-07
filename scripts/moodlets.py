"""CLI for supplied Sim emotion/moodlet strip evaluation."""
import argparse
import json
import sys

from betterinstincts.moodlets import MoodletError, evaluate_moodlets, load_contract


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--emotion", default=None)
    p.add_argument("--moodlets", default="", help="Comma-separated moodlet labels from HUD")
    p.add_argument("--needs-json", default=None)
    p.add_argument("--event-active", action="store_true")
    p.add_argument("--outdoor-social-prefix", action="store_true")
    p.add_argument("--indoor-capacity", action="store_true")
    p.add_argument("--show-contract", action="store_true")
    args = p.parse_args(argv)
    try:
        if args.show_contract:
            print(json.dumps(load_contract(), indent=2))
            return 0
        needs = json.loads(args.needs_json) if args.needs_json else None
        moodlets = [m.strip() for m in args.moodlets.split(",") if m.strip()]
        result = evaluate_moodlets(
            emotion=args.emotion,
            moodlets=moodlets,
            needs=needs,
            event_active=args.event_active,
            outdoor_social_prefix=args.outdoor_social_prefix,
            indoor_capacity_observed=args.indoor_capacity,
        )
        print(json.dumps(result, indent=2))
        return 0
    except (MoodletError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"state": "MOODLET_EVAL_FAILED_CLOSED", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
