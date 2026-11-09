"""Opt-in room census over an existing house_state JSON snapshot. No game access."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from betterinstincts.room_census import RoomCensusError, load_contract, scan_lot_model, ROOT


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("taxonomy")
    p = sub.add_parser("evaluate")
    p.add_argument("--model", required=True, help="An explicitly supplied model inside dist/house-state")
    args = parser.parse_args()
    try:
        if args.command == "taxonomy":
            cfg = load_contract()
            result = {"functional_labels": cfg["functional_labels"], "style_labels": cfg["style_labels"]}
        else:
            target = Path(args.model).resolve()
            root = (ROOT / "dist" / "house-state").resolve()
            if not target.is_relative_to(root) or target.is_symlink() or not target.is_file() or target.stat().st_size > 262144:
                raise RoomCensusError("MODEL_PATH_UNSAFE")
            result = scan_lot_model(json.loads(target.read_text(encoding="utf-8")))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (RoomCensusError, OSError, ValueError, TypeError, KeyError) as exc:
        print("ROOM_CENSUS_FAIL: " + str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
