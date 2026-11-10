#!/usr/bin/env python3
"""CLI for click miss-cause classification + corpus (evaluate/record only)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from betterinstincts.click_miss_cause import (
    ClickMissCauseError,
    classify_miss_cause,
    default_corpus_path,
    ingest_parts_buy_ledger,
    load_contract,
    load_corpus,
    save_corpus,
    summarize_corpus,
)


def _bool_flag(value: str) -> bool:
    return str(value).lower() in {"1", "true", "yes", "y"}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Click miss-cause classifier / corpus")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog", help="Show miss causes + feature schema")
    cl = sub.add_parser("classify", help="Classify one click outcome")
    cl.add_argument("--geometry", required=True)
    cl.add_argument("--error-px", type=float, default=0.0)
    cl.add_argument("--dx", type=float, default=0.0)
    cl.add_argument("--dy", type=float, default=0.0)
    cl.add_argument("--peer-hud-busy", default="false")
    cl.add_argument("--overlay-clear-during-peer-lease", default="false")
    cl.add_argument("--intended-surface-absent", default="false")
    cl.add_argument("--wrong-control", default="false")
    cl.add_argument("--zoom-fraction", type=float, default=None)
    cl.add_argument("--object-pick-identify-used", default="false")
    cl.add_argument("--lot-punch-through-risk", default="false")
    cl.add_argument("--idle-ms", type=float, default=None)
    sm = sub.add_parser("summarize", help="Summarize corpus cause counts")
    sm.add_argument("--corpus", type=Path, default=None)
    ing = sub.add_parser("ingest-parts-buy", help="Seed corpus from parts-buy click ledger")
    ing.add_argument(
        "--ledger",
        type=Path,
        default=ROOT / "dist/game-host/parts-buy/click-ledger.v1.json",
    )
    ing.add_argument("--corpus", type=Path, default=None)
    args = p.parse_args(argv)

    try:
        if args.command == "catalog":
            cfg = load_contract()
            result = {
                "miss_causes": cfg.get("miss_causes"),
                "feature_schema": cfg.get("feature_schema"),
                "recommended_practice": cfg.get("recommended_practice"),
                "classifier": cfg.get("classifier"),
                "corpus_default": str(default_corpus_path(cfg)),
                "execute_allowed": False,
                "proof_ceiling": cfg["proof_ceiling"],
            }
        elif args.command == "classify":
            result = classify_miss_cause(
                geometry=args.geometry,
                error_px=args.error_px,
                dx=args.dx,
                dy=args.dy,
                peer_hud_busy=_bool_flag(args.peer_hud_busy),
                overlay_clear_during_peer_lease=_bool_flag(
                    args.overlay_clear_during_peer_lease
                ),
                intended_surface_absent=_bool_flag(args.intended_surface_absent),
                wrong_control=_bool_flag(args.wrong_control),
                zoom_fraction=args.zoom_fraction,
                object_pick_identify_used=_bool_flag(args.object_pick_identify_used),
                lot_punch_through_risk=_bool_flag(args.lot_punch_through_risk),
                idle_ms_at_click=args.idle_ms,
            )
        elif args.command == "summarize":
            result = summarize_corpus(load_corpus(args.corpus))
        elif args.command == "ingest-parts-buy":
            if not args.ledger.is_file():
                raise ClickMissCauseError("PARTS_BUY_LEDGER_MISSING")
            ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
            path = args.corpus or default_corpus_path()
            book = ingest_parts_buy_ledger(ledger, corpus=load_corpus(path))
            save_corpus(book, path)
            result = {
                "corpus": str(path),
                "summary": summarize_corpus(book),
                "execute_allowed": False,
            }
        else:
            raise ClickMissCauseError("UNKNOWN_COMMAND")
    except ClickMissCauseError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
