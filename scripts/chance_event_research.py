"""CLI bridge from explicitly supplied host observations to advisory receipts.

Does not inspect the screen, run an agent, access the internet, or click The Sims.
The real host remains responsible for calibrated sensing, worker scheduling,
companion rendering, player activity admission and gameplay certification.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from betterinstincts.chance_event_research import (
    ChanceEventError, assess, load_memo, remember, save_memo,
)

MEMO_DIR = ROOT / "dist" / "chance-event-research"
MEMO_PATH = MEMO_DIR / "memo.json"


def read_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32_000:
        raise ChanceEventError("INPUT_JSON_UNSAFE")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ChanceEventError("INPUT_JSON_INVALID") from exc
    if not isinstance(value, dict):
        raise ChanceEventError("INPUT_MAPPING_REQUIRED")
    return value


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("assess", help="Evaluate supplied popup + memo; return dispatch and overlay model")
    a.add_argument("--observation", type=Path, required=True)
    a.add_argument("--external-research-opt-in", action="store_true")
    a.add_argument("--host-research-state", choices=["IDLE", "RUNNING", "FAILED"], default="IDLE")
    w = sub.add_parser("remember", help="Persist explicitly reviewed research for the observed event")
    w.add_argument("--observation", type=Path, required=True)
    w.add_argument("--reviewed-research", type=Path, required=True)
    w.add_argument("--ttl-days", type=int, default=30)
    args = p.parse_args(argv)
    try:
        observed = read_json(args.observation)
        memo = load_memo(MEMO_PATH)
        if args.command == "assess":
            result = assess(observed, memo,
                            external_research_opt_in=args.external_research_opt_in,
                            host_research_state=args.host_research_state)
        else:
            reviewed = read_json(args.reviewed_research)
            updated = remember(memo, observed, reviewed, now=datetime.now(timezone.utc),
                               ttl_days=args.ttl_days)
            MEMO_DIR.mkdir(parents=True, exist_ok=True)
            save_memo(MEMO_PATH, updated)
            result = {"schema": "betterinstincts.chance-event-memo-receipt/v1",
                      "state": "MEMO_UPDATED", "memo_records": len(updated["records"]),
                      "path": str(MEMO_PATH.relative_to(ROOT)),
                      "execute_clicks": False, "control_permit": None,
                      "proof_ceiling": "EXPLICITLY_REVIEWED_OFFLINE_RESEARCH"}
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ChanceEventError, OSError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc),
                          "execute_clicks": False, "control_permit": None}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
