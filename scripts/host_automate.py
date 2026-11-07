#!/usr/bin/env python3
"""Presence-gated host automation planner (evaluate-only by default).

Respects PLAYER_PLAYING / off-canvas. Never autoruns.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from betterinstincts.host_automate import HostAutomateError, plan_automation
from betterinstincts.player_presence import PresenceProbe, probe_windows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--observation", type=Path, required=True)
    p.add_argument("--session-id", default=None,
                   help="If set, require matching ACTIVE host_listener session")
    p.add_argument("--session-active", action="store_true",
                   help="Declare session active without listener file (tests)")
    p.add_argument("--process-id", type=int, default=None)
    p.add_argument("--probe-json", type=Path, default=None,
                   help="Inject PresenceProbe JSON instead of Win32 probe")
    p.add_argument("--declared-playing", action="store_true")
    p.add_argument("--idle-ms", type=int, default=8000, help="Minimum desktop idle before host planning")
    args = p.parse_args(argv)
    try:
        if not args.observation.is_file() or args.observation.stat().st_size > 32_000:
            raise HostAutomateError("OBSERVATION_UNSAFE")
        obs = json.loads(args.observation.read_text(encoding="utf-8"))
        if args.probe_json is not None:
            raw = json.loads(args.probe_json.read_text(encoding="utf-8"))
            probe = PresenceProbe(
                foreground_is_sims=bool(raw.get("foreground_is_sims")),
                cursor_in_client=bool(raw.get("cursor_in_client")),
                last_input_age_ms=raw.get("last_input_age_ms"),
                operator_declared_playing=bool(
                    raw.get("operator_declared_playing", args.declared_playing)
                ),
                player_directed_queue=bool(raw.get("player_directed_queue",
                                                   obs.get("player_directed", False))),
                probe_ok=bool(raw.get("probe_ok", True)),
            )
        else:
            probe = probe_windows(args.process_id)
            if args.declared_playing:
                probe = PresenceProbe(
                    foreground_is_sims=probe.foreground_is_sims,
                    cursor_in_client=probe.cursor_in_client,
                    last_input_age_ms=probe.last_input_age_ms,
                    operator_declared_playing=True,
                    player_directed_queue=bool(obs.get("player_directed", False)),
                    probe_ok=probe.probe_ok,
                )
        result = plan_automation(
            obs,
            probe,
            session_id=args.session_id,
            session_active=True if args.session_active else None,
            idle_ms=args.idle_ms,
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (HostAutomateError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
