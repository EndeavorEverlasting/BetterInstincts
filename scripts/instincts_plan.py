#!/usr/bin/env python3
"""Plan six-need host instincts from an explicit need snapshot JSON.

Does not click the game, delete saves, or claim live certification.
Example:
  python -m scripts.instincts_plan --needs-json dist/game-host/needs-snap.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from betterinstincts.instincts_host import (
    InstinctsHostError,
    NeedSnapshot,
    is_lab_alias,
    plan,
    plan_to_dict,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--needs-json", required=True, help="JSON object with six need floats 0..1")
    p.add_argument("--objects", default="", help="Comma-separated available object tags")
    p.add_argument("--sim-absent", action="store_true")
    p.add_argument("--player-directed", action="store_true")
    p.add_argument("--already-busy", action="store_true")
    p.add_argument("--capture-ref", default="capture:needs-snap")
    p.add_argument("--continuation-alias", default="BI_CONT_NEEDS_GREEN_01")
    p.add_argument("--green-floor", type=float, default=0.75)
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
        if not is_lab_alias(args.continuation_alias) or not args.continuation_alias.startswith("BI_CONT_"):
            raise InstinctsHostError("LAB_CONTINUATION_ALIAS_REQUIRED")
        snap = NeedSnapshot(
            needs=needs,
            available_objects=objects,
            player_directed=args.player_directed,
            already_busy=args.already_busy,
            sim_absent=args.sim_absent or bool(raw.get("sim_absent")),
            capture_ref=args.capture_ref,
        )
        result = plan(snap, green_floor=args.green_floor, continuation_alias=args.continuation_alias)
    except (InstinctsHostError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc)}))
        return 2
    out = plan_to_dict(result)
    out["capture_ref"] = snap.capture_ref
    print(json.dumps(out, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
