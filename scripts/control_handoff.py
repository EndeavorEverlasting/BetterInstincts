#!/usr/bin/env python3
"""One-shot, opt-in screen handoff status: HUMAN pause or HOST ready.

No watcher, daemon, sleep loop, or Sims control. The local game agent calls this
before its own action and must still verify scene, selected save and player queue.
"""
from __future__ import annotations

import argparse
import json
import sys

from betterinstincts.control_handoff import HandoffError, confirm, decide, screen_owner_busy
from betterinstincts.host_listener import HostListenerError, status
from betterinstincts.player_presence import probe_windows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--session-id", required=True)
    p.add_argument("--process-id", type=int, required=True)
    p.add_argument("--idle-ms", type=int, default=15000)
    p.add_argument("--confirm", action="store_true", help="Two distinct input observations for next one-step admission")
    args = p.parse_args(argv)
    try:
        if args.process_id <= 0 or sys.platform != "win32":
            raise HandoffError("LOCAL_WINDOWS_GAME_HOST_REQUIRED")
        active = status(args.session_id).get("state") == "ACTIVE"
        if args.confirm:
            result = confirm(
                lambda: probe_windows(args.process_id),
                session_active=active,
                idle_ms=args.idle_ms,
            )
        else:
            result = decide(
                probe_windows(args.process_id),
                session_active=active,
                idle_ms=args.idle_ms,
            )
        if result["screen_control_allowed"] and screen_owner_busy(args.process_id):
            result = {
                **result,
                "state": "PAUSED_FOR_AGENT",
                "owner": "ANOTHER_EXECUTOR",
                "reason": "SCREEN_OWNER_BUSY",
                "screen_control_allowed": False,
            }
        print(json.dumps(result, sort_keys=True))
        return 0 if result["screen_control_allowed"] else 3
    except (HandoffError, HostListenerError, OSError, TypeError, ValueError) as exc:
        print(json.dumps({"state": "PAUSED_FOR_PLAYER", "reason": str(exc), "screen_control_allowed": False}, sort_keys=True))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
