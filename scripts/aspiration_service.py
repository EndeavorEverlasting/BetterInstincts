"""CLI for aspiration microsystem evaluation (dialog OK/Cancel tandem)."""
import argparse
import json
import sys

from betterinstincts.aspiration_service import (
    AspirationServiceError,
    evaluate_aspiration_service,
    load_contract,
)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prompt-id", default=None)
    p.add_argument("--prompt-text", default="")
    p.add_argument("--aspiration-prompt-active", action="store_true")
    p.add_argument(
        "--aspiration-completion",
        choices=["true", "false"],
        default="false",
        help="Lab default false (Cancel life-state). Product users pass true.",
    )
    p.add_argument("--occult-needs-ready", action="store_true")
    p.add_argument("--operator-prefers-ok", action="store_true")
    p.add_argument("--prior-json", default=None)
    p.add_argument("--show-contract", action="store_true")
    args = p.parse_args(argv)
    try:
        if args.show_contract:
            print(json.dumps(load_contract(), indent=2))
            return 0
        prior = json.loads(args.prior_json) if args.prior_json else None
        result = evaluate_aspiration_service(
            aspiration_prompt_active=args.aspiration_prompt_active
            or bool(args.prompt_text)
            or bool(args.prompt_id),
            prompt_id=args.prompt_id,
            prompt_text=args.prompt_text,
            aspiration_completion_enabled=args.aspiration_completion == "true",
            occult_needs_engine_ready=args.occult_needs_ready,
            operator_prefers_ok=True if args.operator_prefers_ok else None,
            prior_state=prior,
        )
        print(json.dumps(result, indent=2))
        return 0
    except (AspirationServiceError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(
            json.dumps({"state": "ASPIRATION_SERVICE_FAILED_CLOSED", "error": str(exc)}),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
