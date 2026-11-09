#!/usr/bin/env python3
"""CLI: score intended chrome targets vs observed clicks; Escape-cancel on miss.

Examples:
  python -m scripts.click_error_eval against-chrome --mode BUILD --target catalog.search_field --observed 125 780 --client 1920 1080
  python -m scripts.click_error_eval session --trials tests/fixtures/click-error-session.v1.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from betterinstincts.click_error_eval import (
    ClickErrorEvalError,
    evaluate_against_chrome,
    evaluate_click,
    evaluate_session,
    load_contract_eval,
)


def _dump(payload: dict) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("contract", help="Dump click-error contract")
    p_one = commands.add_parser("score", help="Score raw intended vs observed client pixels")
    p_one.add_argument("--intended", nargs=2, type=int, metavar=("X", "Y"), required=True)
    p_one.add_argument("--observed", nargs=2, type=int, metavar=("X", "Y"), required=True)
    p_one.add_argument("--client", nargs=2, type=int, metavar=("W", "H"), required=True)
    p_chr = commands.add_parser("against-chrome", help="Resolve ui_chrome target then score")
    p_chr.add_argument("--mode", required=True, choices=["BUY", "BUILD"])
    p_chr.add_argument("--target", required=True)
    p_chr.add_argument("--observed", nargs=2, type=int, metavar=("X", "Y"), required=True)
    p_chr.add_argument("--client", nargs=2, type=int, metavar=("W", "H"), required=True)
    p_chr.add_argument("--profile", default=None)
    p_sess = commands.add_parser("session", help="Aggregate a JSON trial list")
    p_sess.add_argument("--trials", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "contract":
            return _dump(load_contract_eval())
        if args.command == "score":
            return _dump(
                evaluate_click(
                    intended_x=args.intended[0],
                    intended_y=args.intended[1],
                    observed_x=args.observed[0],
                    observed_y=args.observed[1],
                    client_width=args.client[0],
                    client_height=args.client[1],
                )
            )
        if args.command == "against-chrome":
            return _dump(
                evaluate_against_chrome(
                    target_id=args.target,
                    mode=args.mode,
                    observed_x=args.observed[0],
                    observed_y=args.observed[1],
                    client_width=args.client[0],
                    client_height=args.client[1],
                    profile=args.profile,
                )
            )
        path = Path(args.trials)
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 256_000:
            raise ClickErrorEvalError("TRIALS_FILE_UNSAFE")
        payload = json.loads(path.read_text(encoding="utf-8"))
        trials = payload["trials"] if isinstance(payload, dict) and "trials" in payload else payload
        return _dump(evaluate_session(trials))
    except ClickErrorEvalError as exc:
        print(json.dumps({"error": str(exc)}, indent=2, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
