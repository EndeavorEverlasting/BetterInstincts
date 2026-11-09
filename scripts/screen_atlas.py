"""Inspect the Sims 4 screen map. Never clicks, types or launches the game."""
from __future__ import annotations

import argparse
import json

from betterinstincts.screen_atlas import ScreenAtlasError, inventory, resolved_calibration
from betterinstincts.ui_chrome import resolve_target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("inventory")
    target = sub.add_parser("target")
    target.add_argument("--mode", required=True, choices=["LIVE", "BUY", "BUILD"])
    target.add_argument("--id", required=True)
    target.add_argument("--profile", default="1920x1080")
    target.add_argument("--width", type=int, default=1920)
    target.add_argument("--height", type=int, default=1080)
    args = parser.parse_args(argv)
    try:
        if args.command == "inventory":
            out = inventory()
        else:
            out = resolve_target(args.id, mode=args.mode, profile=args.profile,
                                 client_width=args.width, client_height=args.height)
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0
    except (ScreenAtlasError, ValueError, KeyError) as exc:
        print(json.dumps({"state": "REFUSED", "reason": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
