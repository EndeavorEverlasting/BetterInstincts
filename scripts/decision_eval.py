#!/usr/bin/env python3
"""Evaluate a catalogued Sims chance-card / dialog decision against needs JSON.

Example:
  python -m scripts.decision_eval --prompt-id school.geology.rock_collection \\
    --needs-json dist/game-host/bi002-quiz-boot/needs-snap-school.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from betterinstincts.decision_eval import DecisionEvalError, recommend, recommendation_to_dict
from betterinstincts.host_stack import HostStackError, evaluate_turn


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prompt-id", required=True)
    p.add_argument("--needs-json", required=True)
    p.add_argument("--objects", default="")
    p.add_argument("--prefer-home-control", action="store_true")
    p.add_argument("--host-turn", action="store_true",
                   help="Also emit composed instincts+decision host stack JSON")
    p.add_argument("--capture-ref", default="capture:decision-eval")
    args = p.parse_args(argv)
    path = Path(args.needs_json)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 16_384:
        print(json.dumps({"state": "BLOCKED", "reason": "NEEDS_JSON_UNSAFE"}))
        return 2
    raw = json.loads(path.read_text(encoding="utf-8"))
    needs = raw.get("needs", raw)
    objects = tuple(x.strip() for x in args.objects.split(",") if x.strip())
    if raw.get("available_objects"):
        objects = tuple(raw["available_objects"])
    try:
        if args.host_turn:
            out = evaluate_turn(
                needs,
                available_objects=objects,
                prompt_id=args.prompt_id,
                prefer_home_control=args.prefer_home_control,
                capture_ref=args.capture_ref,
            )
        else:
            out = recommendation_to_dict(
                recommend(args.prompt_id, needs, prefer_home_control=args.prefer_home_control)
            )
            out["capture_ref"] = args.capture_ref
    except (DecisionEvalError, HostStackError, TypeError, ValueError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc)}))
        return 2
    print(json.dumps(out, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
