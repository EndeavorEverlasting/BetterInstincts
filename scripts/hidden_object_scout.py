"""Bounded, resumable Hidden Catalog Scout for the existing Windows game agent.

This CLI never launches The Sims, loops on a timer or injects UI input.
The *local agent* calls next/record for each admitted, observed catalog batch.
"""
from __future__ import annotations

import argparse
import json
import sys

from betterinstincts.hidden_object_scout import (
    ScoutError, change_mode, load_goal, next_search, record_batch, start, status,
)
from scripts.hidden_object_discovery import _read_observation


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("goal", help="Read the machine-owned 4-hour mission")
    start_parser = sub.add_parser("start", help="Create a checkpointed mission without game input")
    start_parser.add_argument("--session-id", required=True)
    start_parser.add_argument("--minutes", type=int, default=None)
    start_parser.add_argument("--target", type=int, default=None)
    for name in ("status", "pause", "resume", "stop"):
        command = sub.add_parser(name)
        command.add_argument("--session-id", required=True)
    for name in ("next", "record"):
        command = sub.add_parser(name)
        command.add_argument("--session-id", required=True)
        command.add_argument("--observation", required=True, help="Actual current host observation under dist/")
        command.add_argument("--p04-receipt", required=True, help="Audited initial debug unlock receipt under dist/")
        if name == "record":
            command.add_argument("--report", required=True, help="One bounded real-capture batch under dist/")
    args = parser.parse_args(argv)
    try:
        if args.action == "goal":
            output = load_goal()
        elif args.action == "start":
            output = start(args.session_id, minutes=args.minutes, target=args.target)
        elif args.action == "status":
            output = status(args.session_id)
        elif args.action in ("pause", "resume", "stop"):
            output = change_mode(args.session_id, args.action)
        else:
            observation = _read_observation(args.observation)
            receipt = _read_observation(args.p04_receipt)
            if args.action == "next":
                output = next_search(args.session_id, observation, receipt)
            else:
                report = _read_observation(args.report)
                output = record_batch(args.session_id, report, observation, receipt)
        print(json.dumps(output, indent=2, sort_keys=True))
        state = output.get("state", "")
        return 2 if state in ("ABSTAIN", "COOLDOWN", "P04_EVIDENCE_INCOMPLETE") else 0
    except (ScoutError, OSError, TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"state": "SCOUT_FAILED_CLOSED", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
