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

from betterinstincts.control_handoff import DEFAULT_IDLE_MS
from betterinstincts.player_presence import PresenceProbe, probe_windows
from betterinstincts.host_listener import (
    HostListenerError,
    activate,
    deactivate,
    status,
    tick,
    observe_hover,
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
    tk.add_argument("--process-id", type=int, default=None, help="Win32 presence probe, no input hooks")
    tk.add_argument("--idle-ms", type=int, default=DEFAULT_IDLE_MS)
    tk.add_argument("--declared-playing", action="store_true")
    tk.add_argument("--learning-model", type=Path, help="Explicit aggregate model under dist/judgment-learning")
    tk.add_argument("--learning-query", type=Path, help="Explicit sanitized query under dist/judgment-learning")
    tk.add_argument("--observation", type=Path, required=True,
                    help="JSON observation (needs, queue, location_kind, capture_ref)")
    for command in ("hover", "behavior"):
        hv = sub.add_parser(command, help="Ingest sanitized semantic tooltip, hotkey or cheat action events; no hooks")
        hv.add_argument("--session-id", required=True)
        hv.add_argument("--event", type=Path, required=True)
        hv.add_argument("--explicit-opt-in", action="store_true")
    sub.add_parser("behavior-catalog", help="Show canonical safe hotkey and cheat IDs")
    args = p.parse_args(argv)
    try:
        if args.command == "activate":
            result = activate(args.session_id, note=args.note)
        elif args.command == "status":
            result = status(args.session_id)
        elif args.command == "deactivate":
            result = deactivate(args.session_id)
        elif args.command == "behavior-catalog":
            from betterinstincts.behavior_input_catalog import catalog
            result = catalog()
        elif args.command in {"hover", "behavior"}:
            if args.event.is_symlink() or not args.event.is_file() or args.event.stat().st_size > 4096:
                raise HostListenerError("BEHAVIOR_EVENT_FILE_UNSAFE")
            event = json.loads(args.event.read_text(encoding="utf-8"))
            result = observe_hover(args.session_id, event, explicit_opt_in=args.explicit_opt_in)
        else:
            path = args.observation
            if not path.is_file() or path.stat().st_size > 32_000:
                raise HostListenerError("OBSERVATION_FILE_UNSAFE")
            obs = json.loads(path.read_text(encoding="utf-8"))
            probe = probe_windows(args.process_id) if args.process_id is not None else None
            if args.declared_playing:
                if probe is None:
                    probe = PresenceProbe(False, False, operator_declared_playing=True, probe_ok=False)
                else:
                    from dataclasses import replace
                    probe = replace(probe, operator_declared_playing=True)
            learning_model = learning_query = None
            if args.learning_model is not None or args.learning_query is not None:
                if args.learning_model is None or args.learning_query is None:
                    raise HostListenerError("LEARNING_MODEL_AND_QUERY_REQUIRED_TOGETHER")
                from scripts.judgment_learning import _load
                learning_model = _load(args.learning_model)
                learning_query = _load(args.learning_query)
            result = tick(args.session_id, obs, presence_probe=probe, idle_ms=args.idle_ms,
                          learning_model=learning_model, learning_query=learning_query)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (HostListenerError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
