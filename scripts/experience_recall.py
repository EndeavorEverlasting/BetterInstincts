"""Explicit, local-only historical Sims experience memoization.

No observer, game launcher, desktop input, save access or implicit monitoring.
Run from the canonical repository with an already observed sanitized receipt.
"""
from __future__ import annotations

import argparse
import json

from betterinstincts.experience_recall import (
    EVENT_SCHEMA, ExperienceRecallError, load_memory, recall, record_new,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    for name in ("remember", "recall"):
        p = subs.add_parser(name)
        p.add_argument("--domain", required=True)
        p.add_argument("--game-build", required=True)
        p.add_argument("--installation-profile", required=True)
        p.add_argument("--mechanic-id", required=True)
        p.add_argument("--choice-id", required=True)
        if name == "remember":
            p.add_argument("--result", required=True)
            p.add_argument("--evidence-level", required=True, choices=(
                "SOURCE_INSPECTED", "OPERATOR_REPORTED_LIVE",
                "LOCAL_ARTIFACT_VERIFIED", "NATIVE_RECEIPT",
            ))
            p.add_argument("--evidence-ref", required=True)
            p.add_argument("--observed-at-ms", required=True, type=int)
    args = parser.parse_args(argv)
    context = {
        "domain": args.domain, "game_build": args.game_build,
        "installation_profile": args.installation_profile,
        "mechanic_id": args.mechanic_id, "choice_id": args.choice_id,
    }
    try:
        if args.command == "recall":
            result = recall(load_memory(), context)
        else:
            result = record_new({
                "schema": EVENT_SCHEMA, "context": context,
                "result": args.result, "evidence_level": args.evidence_level,
                "evidence_ref": args.evidence_ref,
                "observed_at_ms": args.observed_at_ms,
            })
        print(json.dumps(result, sort_keys=True))
        return 0 if result["state"] != "CONFLICT_REVIEW_REQUIRED" else 2
    except (ExperienceRecallError, OSError, TypeError, ValueError) as exc:
        print(json.dumps({"state": "HOLD", "reason": str(exc),
                          "execute_allowed": False, "control_permit": None},
                         sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
