#!/usr/bin/env python3
"""Explicit repository-owned scenery discovery recorder, no background capture.

Host adapters supply fresh observations; only --apply writes the one canonical
registry under contracts/ (never saves, Mods, screenshots or user profiles).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from betterinstincts.scenery_memory import (
    SceneryMemoryError, record_scenery, review_scenery, validate_registry,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "contracts" / "scenery-discoveries.v1.json"
MAX_BYTES = 64_000
MAX_INPUT = 4_096


def load_registry() -> dict:
    if REGISTRY.is_symlink() or not REGISTRY.is_file() or REGISTRY.stat().st_size > MAX_BYTES:
        raise SceneryMemoryError("SCENERY_REGISTRY_UNSAFE")
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    validate_registry(data)
    return data


def write_registry(registry: dict) -> None:
    """Single fixed repository destination; no arbitrary path or auto-commit."""
    validate_registry(registry)
    if REGISTRY.is_symlink() or not REGISTRY.is_file():
        raise SceneryMemoryError("SCENERY_REGISTRY_UNSAFE")
    payload = json.dumps(registry, indent=2, sort_keys=True) + "\n"
    if len(payload.encode("utf-8")) > MAX_BYTES:
        raise SceneryMemoryError("SCENERY_REGISTRY_OVER_SIZE")
    REGISTRY.write_text(payload, encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    record = sub.add_parser("record")
    record.add_argument("--capture-ref", required=True)
    record.add_argument("--observation-json", required=True)
    record.add_argument("--apply", action="store_true")
    review = sub.add_parser("review")
    review.add_argument("--signature", required=True)
    review.add_argument("--review-ref", required=True)
    review.add_argument("--route-label", required=True)
    review.add_argument("--apply", action="store_true")
    sub.add_parser("list")
    args = parser.parse_args(argv)
    try:
        current = load_registry()
        if args.command == "list":
            print(json.dumps(current, indent=2))
            return 0
        if args.command == "record":
            if len(args.observation_json.encode("utf-8")) > MAX_INPUT:
                raise SceneryMemoryError("SCENERY_INPUT_TOO_LARGE")
            event = json.loads(args.observation_json)
            result = record_scenery(
                current, capture_ref=args.capture_ref, observation=event,
            )
            future = result["registry"]
            report = {k:v for k,v in result.items() if k != "registry"}
        else:
            future = review_scenery(
                current, signature=args.signature,
                review={"source": "OPERATOR_REVIEW", "approved": True,
                        "review_ref": args.review_ref, "route_label": args.route_label},
            )
            report = {"state": "SCENERY_REVIEW_REQUEST", "signature": args.signature,
                      "execute_allowed": False}
        if args.apply:
            write_registry(future)
        print(json.dumps({**report,
            "registry_mutated": bool(args.apply),
            "next": "REVIEW_AND_COMMIT_CHANGED_REGISTRY" if args.apply else "ADD_--apply_FOR_EXPLICIT_REPO_WRITE",
        }, indent=2))
        return 0
    except (SceneryMemoryError, ValueError, TypeError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"state": "REFUSED", "reason": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
