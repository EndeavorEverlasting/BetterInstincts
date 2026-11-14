#!/usr/bin/env python3
"""Read-only bottom-right Sims HUD pixel observation and posture proposal.

Usage:
  python -m scripts.hud_panel_state --image capture.png --mode LIVE
  python -m scripts.hud_panel_state --image capture.png --mode LIVE --intent INVENTORY_AUDIT

No screen capture, live input, agent execution, or game save access.
Pillow is a host-only optional dependency for PNG decoding.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from betterinstincts.hud_panel_state import (
    PATCH, observe_inventory_png, propose_panel_posture,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--image", type=Path, required=True)
    p.add_argument("--mode", required=True, choices=("LIVE", "BUY", "BUILD"))
    p.add_argument("--patch", default=PATCH)
    p.add_argument("--intent", choices=("LONG_LIST", "INVENTORY_AUDIT", "SCROLL_SEARCH",
                                       "QUICK_STATUS", "SINGLE_ITEM", "FINISHED"))
    p.add_argument("--operator-idle", action="store_true")
    p.add_argument("--panel-owner", choices=("HOST", "OPERATOR", "UNKNOWN"), default="UNKNOWN")
    p.add_argument("--visible-panel-id", default="UNKNOWN")
    p.add_argument("--scene-fresh", action="store_true")
    p.add_argument("--sim-fresh", action="store_true")
    args = p.parse_args(argv)
    try:
        # No implicit capture, background polling, file discovery or stale-cache reuse.
        if not args.image.is_file():
            raise ValueError("IMAGE_NOT_FOUND")
        if args.image.stat().st_size > 25_000_000:
            raise ValueError("IMAGE_TOO_LARGE")
        observed = observe_inventory_png(str(args.image), mode=args.mode, patch=args.patch)
        out = {"schema": "betterinstincts.hud-panel-observation/v1",
               "observation": observed.as_dict(), "execute_allowed": False}
        if args.intent:
            out["proposal"] = propose_panel_posture(
                observed, intent=args.intent, operator_idle=args.operator_idle,
                panel_owner=args.panel_owner,
                current_visible_panel_id=args.visible_panel_id,
                scene_fresh=args.scene_fresh, sim_fresh=args.sim_fresh,
            )
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0
    except (ValueError, OSError, ImportError) as exc:
        print(json.dumps({"state": "UNKNOWN", "error": str(exc),
                          "execute_allowed": False}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
