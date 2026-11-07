"""Read-only CLI for scoped hidden-object Build/Buy discovery.

Use explicit, sanitized observation JSON under dist/; no SendInput or writes.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from betterinstincts.hidden_object_discovery import (
    DiscoveryError, ROOT, audit_p04_receipt, load_contract, p04_guide,
    plan_discovery, review_catalog_entry,
)


def _read_observation(raw: str) -> dict:
    path = (ROOT / raw).resolve()
    allowed = (ROOT / "dist").resolve()
    if not path.is_relative_to(allowed) or path.is_symlink() or not path.is_file():
        raise DiscoveryError("OBSERVATION_MUST_BE_EXISTING_DIST_JSON")
    if path.suffix != ".json" or path.stat().st_size > 64_000:
        raise DiscoveryError("OBSERVATION_JSON_TOO_LARGE_OR_WRONG_TYPE")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise DiscoveryError("OBSERVATION_NOT_OBJECT")
    return data


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("categories", help="Inspect static discovery hints")
    commands.add_parser("guide", help="P04-required complete ordered operator recipe; no game input")
    audit = commands.add_parser("audit", help="Fail-closed structural receipt audit, never live certification")
    audit.add_argument("--observation", required=True, help="Existing local host receipt JSON under dist/")
    plan = commands.add_parser("plan", help="Emit manual-only, evidence-gated instructions")
    plan.add_argument("--observation", required=True, help="Existing JSON under dist/")
    plan.add_argument("--category", default="all")
    plan.add_argument("--target", default=None)
    plan.add_argument("--live-edit", action="store_true")
    review = commands.add_parser("review-entry", help="Classify one reviewed catalog result")
    review.add_argument("--observation", required=True, help="Existing JSON under dist/")
    args = parser.parse_args(argv)
    try:
        if args.command == "categories":
            result = load_contract()["search_contract"]["classes"]
        elif args.command == "guide":
            result = p04_guide()
        elif args.command == "audit":
            result = audit_p04_receipt(_read_observation(args.observation))
        elif args.command == "plan":
            result = plan_discovery(
                _read_observation(args.observation),
                category=args.category,
                target=args.target,
                include_live_edit=args.live_edit,
            )
        else:
            result = review_catalog_entry(_read_observation(args.observation))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2 if result.get("state") in ("ABSTAIN", "P04_EVIDENCE_INCOMPLETE") else 0
    except (DiscoveryError, ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"state": "DISCOVERY_FAIL_CLOSED", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
