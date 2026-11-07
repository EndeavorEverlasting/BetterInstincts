"""CLI for social-opportunity Sims-library occult gates."""
import argparse
import json
import sys

from betterinstincts.social_opportunity import (
    SocialOpportunityError,
    evaluate_social_opportunity,
    load_contract,
    lookup_sim_library,
)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--show-contract", action="store_true")
    p.add_argument("--lookup", action="store_true")
    p.add_argument("--evaluate", action="store_true")
    p.add_argument("--invitee-name", default="")
    p.add_argument("--prompt-text", default="")
    p.add_argument("--sim-library-json", default="", help="JSON list of {name, occult_status}")
    p.add_argument("--lookup-ran", action="store_true")
    p.add_argument("--occult-status", default="")
    p.add_argument("--social-prompt-active", action="store_true")
    args = p.parse_args(argv)
    try:
        if args.show_contract:
            print(json.dumps(load_contract(), indent=2))
            return 0
        library = json.loads(args.sim_library_json) if args.sim_library_json else []
        if args.lookup:
            if not args.invitee_name:
                raise SocialOpportunityError("INVITEE_NAME_REQUIRED")
            print(json.dumps(lookup_sim_library(args.invitee_name, library), indent=2))
            return 0
        if not args.evaluate:
            raise SocialOpportunityError("USE_EVALUATE_OR_LOOKUP_OR_SHOW_CONTRACT")
        result = evaluate_social_opportunity(
            social_prompt_active=args.social_prompt_active or True,
            prompt_text=args.prompt_text,
            invitee_name=args.invitee_name or None,
            sim_library=library,
            lookup_ran=args.lookup_ran,
            occult_status=args.occult_status or None,
        )
        print(json.dumps(result, indent=2))
        return 0
    except (SocialOpportunityError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"state": "SOCIAL_OPPORTUNITY_FAILED_CLOSED", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
