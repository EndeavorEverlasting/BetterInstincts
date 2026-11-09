#!/usr/bin/env python3
"""CLI for Build Mode floor-activity census (listener peer).

Examples:
  python -m scripts.build_floor_activity themes
  python -m scripts.build_floor_activity evaluate --observation dist/game-host/build-floor-obs.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from betterinstincts.build_floor_activity import (
    BuildFloorActivityError,
    evaluate_floor_activity,
    load_contract,
)


def _dump(payload: dict) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("themes", help="List theme vocabulary and category map")
    p_eval = commands.add_parser("evaluate", help="Evaluate floor activity from observation JSON")
    p_eval.add_argument("--observation", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        cfg = load_contract()
        if args.command == "themes":
            return _dump({
                "themes": cfg["themes"],
                "category_to_theme": cfg["category_to_theme"],
                "theme_optimize_hints": cfg["theme_optimize_hints"],
                "architecture": cfg["architecture"]["selected"],
            })
        raw = json.loads(Path(args.observation).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise BuildFloorActivityError("OBSERVATION_MUST_BE_OBJECT")
        result = evaluate_floor_activity(
            build_or_buy_mode=bool(raw.get("build_or_buy_mode", True)),
            active_story=raw.get("active_story"),
            stories_touched=raw.get("stories_touched") or (),
            floor_items=raw.get("floor_items") or (),
            player_directed=bool(raw.get("player_directed", False)),
        )
        return _dump(result)
    except BuildFloorActivityError as exc:
        print(json.dumps({"state": "ERROR", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
