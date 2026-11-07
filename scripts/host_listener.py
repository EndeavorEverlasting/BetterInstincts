#!/usr/bin/env python3
"""Opt-in host listener — activate, tick with observation JSON, deactivate.

Never autoruns. Never a GitHub Actions substitute. Evaluate-only by default.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from betterinstincts.host_listener import (
    HostListenerError,
    activate,
    deactivate,
    status,
    tick,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    act = sub.add_parser("activate")
    act.add_argument("--session-id", required=True)
    act.add_argument("--note", default=None)
    st = sub.add_parser("status")
    st.add_argument("--session-id", required=True)
    de = sub.add_parser("deactivate")
    de.add_argument("--session-id", required=True)
    tk = sub.add_parser("tick")
    tk.add_argument("--session-id", required=True)
    tk.add_argument("--observation", type=Path, required=True,
                    help="JSON observation (needs, queue, location_kind, capture_ref)")
    args = p.parse_args(argv)
    try:
        if args.command == "activate":
            result = activate(args.session_id, note=args.note)
        elif args.command == "status":
            result = status(args.session_id)
        elif args.command == "deactivate":
            result = deactivate(args.session_id)
        else:
            path = args.observation
            if not path.is_file() or path.stat().st_size > 32_000:
                raise HostListenerError("OBSERVATION_FILE_UNSAFE")
            obs = json.loads(path.read_text(encoding="utf-8"))
            result = tick(args.session_id, obs)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (HostListenerError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
