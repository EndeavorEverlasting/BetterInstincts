"""Offline world highlight, contextual learning and holdout evaluator CLI.

No game host, input, network, background sampling or automatic model persistence.
All supplied data are fixtures/observations; this CLI cannot certify screenshots.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Mapping

from betterinstincts.world_traversal_learning import (
    WorldTraversalLearningError, assess_highlight_continuity,
    empty_model, learn_observed_attempts, evaluate_holdout, rank_strategies,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/world-traversal-learning.v1.json"
DIST = ROOT / "dist/world-traversal-eval"
MAX_JSON_BYTES = 262_144


def safe_path(raw: str, *, fixture_ok: bool = False, write: bool = False) -> Path:
    """Limit all persistent snapshots to the ignored, repo-owned eval subtree."""
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    if any(part == ".." for part in path.parts):
        raise WorldTraversalLearningError("PATH_PARENT_TRAVERSAL_FORBIDDEN")
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise WorldTraversalLearningError("SYMLINK_PATH_FORBIDDEN")
    resolved = path.resolve()
    if not (resolved.is_relative_to(DIST) or (fixture_ok and not write and resolved == FIXTURE)):
        raise WorldTraversalLearningError("PATH_OUTSIDE_PRIVATE_EVAL_ROOT")
    if resolved.suffix != ".json":
        raise WorldTraversalLearningError("JSON_ONLY")
    return resolved


def read_json(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size > MAX_JSON_BYTES:
        raise WorldTraversalLearningError("INPUT_MISSING_OR_TOO_LARGE")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise WorldTraversalLearningError("JSON_OBJECT_REQUIRED")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", default=str(FIXTURE))
    parser.add_argument("--model-in")
    parser.add_argument("--model-out", help="Explicit snapshot destination under dist/world-traversal-eval")
    parser.add_argument("--out", help="Explicit evaluation receipt destination under dist/world-traversal-eval")
    args = parser.parse_args(argv)
    try:
        fixture = read_json(safe_path(args.fixture, fixture_ok=True))
        if fixture.get("schema") != "betterinstincts.world-traversal-eval.fixture/v1":
            raise WorldTraversalLearningError("EVAL_FIXTURE_SCHEMA_INVALID")
        model = read_json(safe_path(args.model_in)) if args.model_in else empty_model()
        tracking = assess_highlight_continuity(
            target_id=fixture["target_id"], frames=fixture["frames"],
            capture_ref=fixture["capture_ref"],
            camera_revision=fixture["camera_revision"],
        )
        train = learn_observed_attempts(model, fixture["train"])
        if not fixture["train"]:
            raise WorldTraversalLearningError("TRAINING_REQUIRED")
        context_candidates = []
        seen = set()
        for sample in fixture["train"]:
            key = tuple(sample.get(k) for k in (
                "game_version", "target_kind", "scene_id", "view_kind", "zoom_bin", "strategy"
            ))
            if key not in seen:
                seen.add(key)
                context_candidates.append(sample)
        ranking = rank_strategies(train["model"], context_candidates)
        holdout = evaluate_holdout(train["model"], fixture["holdout"])
        receipt = {
            "schema": "betterinstincts.world-traversal-eval.receipt/v1",
            "tracking": tracking, "training": {
                "accepted": train["accepted"], "abstained": train["abstained"],
                "model_contexts": len(train["model"]["contexts"]),
            }, "ranking": ranking, "holdout": holdout,
            "execute_allowed": False,
            "proof_ceiling": "OFFLINE_SUPPLIED_FIXTURE_NO_LIVE_DETECTOR_OR_ACTION_PROOF",
        }
        if args.model_out:
            output = safe_path(args.model_out, write=True)
            if args.model_in and output == safe_path(args.model_in):
                raise WorldTraversalLearningError("DO_NOT_OVERWRITE_MODEL_INPUT")
            if output.exists():
                raise WorldTraversalLearningError("MODEL_OUTPUT_EXISTS_USE_VERSIONED_SNAPSHOT")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(train["model"], sort_keys=True, indent=2) + "\n", encoding="utf-8")
        if args.out:
            output = safe_path(args.out, write=True)
            if output.exists():
                raise WorldTraversalLearningError("RECEIPT_OUTPUT_EXISTS_USE_NEW_RECEIPT_NAME")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(receipt, sort_keys=True))
        return 0
    except (WorldTraversalLearningError, ValueError, KeyError, TypeError, OSError) as exc:
        print("WORLD_TRAVERSAL_EVAL_BLOCKED " + str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
