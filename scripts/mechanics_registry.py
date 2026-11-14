"""Portable read-only mechanics status / reviewed outcome reconciliation.

No changes to catalog, profile, game or repo are performed by this CLI.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from betterinstincts.mechanics_registry import (
    MechanicsRegistryError, load_registry, validate_registry, review_outcomes,
)


def _read(path: Path) -> dict:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 32768:
        raise MechanicsRegistryError("OUTCOME_RECEIPT_FILE_UNSAFE")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {"capture_ref", "outcomes"}:
        raise MechanicsRegistryError("REVIEW_REQUEST_SCHEMA_INVALID")
    return data


def run(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["status", "reconcile"])
    parser.add_argument("--outcomes", type=Path, help="Separate reviewed per-capture outcome record")
    args = parser.parse_args(argv)
    catalog = load_registry()
    if args.command == "status":
        if args.outcomes:
            raise MechanicsRegistryError("OUTCOMES_NOT_ALLOWED_FOR_STATUS")
        return validate_registry(catalog)
    if args.outcomes is None:
        raise MechanicsRegistryError("OUTCOMES_FILE_REQUIRED")
    review = _read(args.outcomes)
    return review_outcomes(catalog, review["outcomes"],
                           capture_ref=review["capture_ref"])


def main() -> int:
    try:
        print(json.dumps(run(), indent=2, sort_keys=True))
        return 0
    except (MechanicsRegistryError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"state": "MECHANICS_REVIEW_BLOCKED", "reason": str(exc)}),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
