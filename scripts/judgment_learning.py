#!/usr/bin/env python3
"""Explicit local learning: reviewed semantic examples -> bounded Markov model.

Never auto-captures, auto-trains, launches Sims, or writes outside repo dist.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist" / "judgment-learning"

from betterinstincts.judgment_learning import (
    JudgmentLearningError, learn, recommend, prequential_evaluate,
)


def _path(value: Path) -> Path:
    if OUTPUT.is_symlink() or value.is_symlink():
        raise JudgmentLearningError("UNSAFE_LEARNING_PATH")
    root = OUTPUT.resolve()
    candidate = (value if value.is_absolute() else ROOT / value).resolve()
    if not candidate.is_relative_to(root):
        raise JudgmentLearningError("LEARNING_PATH_OUTSIDE_DIST")
    return candidate


def _load(value: Path):
    path = _path(value)
    if not path.is_file() or path.stat().st_size > 64000:
        raise JudgmentLearningError("LEARNING_FILE_INVALID_OR_TOO_LARGE")
    return json.loads(path.read_text(encoding="utf-8"))


def _write(value: Path, payload: dict) -> str:
    path = _path(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if len(raw) > 64000:
        raise JudgmentLearningError("LEARNING_OUTPUT_TOO_LARGE")
    # Atomic local replace; never follows an existing link.
    if path.is_symlink():
        raise JudgmentLearningError("UNSAFE_LEARNING_PATH")
    with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, prefix=".learning-", delete=False) as tmp:
        tmp.write(raw)
        temp = Path(tmp.name)
    try:
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()
    return str(path.relative_to(ROOT))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    train_p = sub.add_parser("train")
    train_p.add_argument("--reviewed-examples", type=Path, required=True)
    train_p.add_argument("--game-version", required=True)
    train_p.add_argument("--platform", required=True, choices=("windows","linux","macos"))
    train_p.add_argument("--model-out", type=Path, required=True)
    train_p.add_argument("--prior-model", type=Path)
    train_p.add_argument("--explicit-opt-in", action="store_true")
    train_p.add_argument("--evaluation-out", type=Path)
    rec_p = sub.add_parser("recommend")
    rec_p.add_argument("--model", type=Path, required=True)
    rec_p.add_argument("--query", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "train":
            if not args.explicit_opt_in:
                raise JudgmentLearningError("EXPLICIT_OPT_IN_REQUIRED")
            reviewed = _load(args.reviewed_examples)
            prior = _load(args.prior_model) if args.prior_model else None
            model = learn(reviewed, game_version=args.game_version, platform=args.platform, prior=prior)
            evaluation = prequential_evaluate(reviewed, game_version=args.game_version, platform=args.platform)
            evaluation.pop("model", None)  # Counts only in owned model file.
            result = {"state": "OFFLINE_MODEL_TRAINED", "model_path": _write(args.model_out, model),
                      "evaluation": evaluation, "execute_clicks": False,
                      "proof_ceiling": "OFFLINE_MODEL_NOT_SIMS_CERTIFICATION"}
            if args.evaluation_out:
                result["evaluation_path"] = _write(args.evaluation_out, evaluation)
        else:
            result = recommend(_load(args.model), _load(args.query))
        print(json.dumps(result, sort_keys=True))
        return 0
    except (JudgmentLearningError, OSError, TypeError, ValueError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc), "execute_clicks": False}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
