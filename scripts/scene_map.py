"""Read-only candidate scene classifier and guarded transition planner."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from betterinstincts.scenes import SceneError, load_catalog, classify, propose_transition


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=None)
    parser.add_argument("--game-version", required=True)
    parser.add_argument("--observations", type=Path, required=True, help="Explicit JSON array with visual and operator cues; no screenshots processed")
    parser.add_argument("--target", default=None, help="Optional next scene; produces proposal only, NEVER a click")
    args = parser.parse_args(argv)
    try:
        catalog = load_catalog(args.catalog) if args.catalog else load_catalog()
        path = args.observations
        if path.is_symlink() or path.stat().st_size > 8_192:
            raise SceneError("OBSERVATIONS_FILE_UNSAFE")
        observations = json.loads(path.read_text(encoding="utf-8"))
        state = classify(catalog, args.game_version, observations)
        if args.target is not None:
            state["proposal"] = propose_transition(catalog, state, args.target)
        print(json.dumps(state, sort_keys=True))
        return 0 if state["state"] == "CANDIDATE_UNVERIFIED" else 2
    except (SceneError, OSError, KeyError, ValueError, TypeError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
