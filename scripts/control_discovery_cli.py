"""Explicit local host listener control discovery utilities; never launches Sims."""
from __future__ import annotations

import argparse
import json
import sys

from betterinstincts.host_listener import (
    open_control_discovery, read_control_discovery, record_control_discovery,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bounded agent-control discovery journal")
    sub = parser.add_subparsers(dest="action", required=True)
    opened = sub.add_parser("open", help="Attach to an already ACTIVE host listener")
    opened.add_argument("--session", required=True)
    opened.add_argument("--household", required=True)
    opened.add_argument("--goal", required=True)
    opened.add_argument("--patch", required=True)
    opened.add_argument("--reason", required=True)
    opened.add_argument("--opt-in", action="store_true", required=True)
    record = sub.add_parser("record", help="Read one sanitized event JSON from stdin")
    record.add_argument("--session", required=True)
    record.add_argument("--opt-in", action="store_true", required=True)
    state = sub.add_parser("status", help="Compact unresolved codification handoff")
    state.add_argument("--session", required=True)
    args = parser.parse_args(argv)
    if args.action == "open":
        output = open_control_discovery(
            args.session, household_ref=args.household, goal_id=args.goal,
            game_patch=args.patch, fallback_reason=args.reason,
            explicit_opt_in=args.opt_in,
        )
    elif args.action == "record":
        raw = sys.stdin.read(4097)
        if len(raw) > 4096:
            parser.error("SEMANTIC_EVENT_TOO_LARGE")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            parser.error("INVALID_EVENT_JSON:" + str(exc))
        output = record_control_discovery(
            args.session, payload, explicit_opt_in=args.opt_in,
        )
    else:
        output = read_control_discovery(args.session)
    print(json.dumps(output, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
