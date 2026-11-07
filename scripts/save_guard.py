"""Offline, read-only classification of an explicitly chosen Sims save identity."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from betterinstincts.save_policy import SavePolicyError, decide, load_registry


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True, help="Operator-selected private manifest; not save files")
    parser.add_argument("--save-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--alias", required=True)
    parser.add_argument("--game-version", required=True)
    parser.add_argument("--capture-ref", required=True)
    parser.add_argument("--intent", default="SELECT_FOR_PLAY")
    args = parser.parse_args(argv)
    try:
        result = decide(load_registry(args.registry), save_id=args.save_id,
                        run_id=args.run_id, alias=args.alias,
                        game_version=args.game_version, capture_ref=args.capture_ref,
                        intent=args.intent)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["state"] == "OPERATOR_ATTESTED_SELECTION_ONLY" else 2
    except (SavePolicyError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
