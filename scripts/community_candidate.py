"""Offline, data-only community VAE candidate boundary.

Never uploads, installs, executes, promotes, or loads a contribution as a
gameplay controller. Exporting learned weights is a SEPARATE player decision:
weights may still reveal facts about training examples.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

from betterinstincts.semantic_vae import BETA, _forward, load_local_model
from betterinstincts.installation_profiles import view
from scripts.semantic_vae import _read as read_snapshot

SCHEMA = "betterinstincts.community-learning.candidate/v1"
HOLDOUT_SCHEMA = "betterinstincts.community-learning.holdout/v1"
KIND = "SEMANTIC_VAE_5X5X3_V1"
MAX_CANDIDATE_BYTES = 40_000
MAX_HOLDOUT_BYTES = 32_000
WEIGHTS = ("encoder_mu", "encoder_logvar", "bias_mu", "bias_logvar",
           "decoder", "decoder_bias")
MIN_TRAIN, MIN_HOLDOUT, MIN_DELTA = 24, 8, 0.01
NO_EFFECT = "UNTRUSTED_DATA_ONLY_NO_GAME_OR_OS_AUTHORITY"


class CandidateError(ValueError):
    """Candidate is unsafe, incomplete, or not independently supported."""


def _number(value: object) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 4:
        raise CandidateError("NONFINITE_OR_OUT_OF_BOUNDS_WEIGHT")
    return float(value)


def _matrix(value: object, rows: int, columns: int) -> None:
    if not isinstance(value, list) or len(value) != rows:
        raise CandidateError("BAD_WEIGHT_MATRIX_SHAPE")
    for row in value:
        if not isinstance(row, list) or len(row) != columns:
            raise CandidateError("BAD_WEIGHT_MATRIX_SHAPE")
        for cell in row:
            _number(cell)


def _vector(value: object, length: int) -> None:
    if not isinstance(value, list) or len(value) != length:
        raise CandidateError("BAD_WEIGHT_VECTOR_SHAPE")
    for cell in value:
        _number(cell)


def _weights(value: object) -> dict:
    if not isinstance(value, dict) or set(value) != set(WEIGHTS):
        raise CandidateError("UNKNOWN_OR_MISSING_WEIGHT_FIELD")
    _matrix(value["encoder_mu"], 4, 75)
    _matrix(value["encoder_logvar"], 4, 75)
    _matrix(value["decoder"], 75, 4)
    _vector(value["bias_mu"], 4)
    _vector(value["bias_logvar"], 4)
    _vector(value["decoder_bias"], 75)
    return value


def _digest(weights: dict) -> str:
    content = json.dumps(weights, sort_keys=True, separators=(",", ":"),
                         allow_nan=False).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def validate_candidate(value: object) -> dict:
    """Validate inert tensors only; never certify authorship, privacy or quality."""
    if not isinstance(value, dict) or set(value) != {
        "schema", "kind", "feature_shape", "latent_size", "weights",
        "tensor_sha256", "reported_training", "effect_policy", "review_state",
    }:
        raise CandidateError("CANDIDATE_SCHEMA_UNKNOWN_FIELDS")
    if (value["schema"] != SCHEMA or value["kind"] != KIND
            or value["feature_shape"] != [5, 5, 3]
            or type(value["latent_size"]) is not int or value["latent_size"] != 4
            or value["effect_policy"] != NO_EFFECT
            or value["review_state"] != "UNREVIEWED"):
        raise CandidateError("CANDIDATE_KIND_OR_AUTHORITY_INVALID")
    weights = _weights(value["weights"])
    digest = _digest(weights)
    if value["tensor_sha256"] != digest:
        raise CandidateError("CANDIDATE_TENSOR_DIGEST_MISMATCH")
    metrics = value["reported_training"]
    if not isinstance(metrics, dict) or set(metrics) != {
        "trained", "heldout", "mean_heldout_loss", "uniform_baseline",
    }:
        raise CandidateError("CANDIDATE_METRICS_SCHEMA_INVALID")
    if (type(metrics["trained"]) is not int or not MIN_TRAIN <= metrics["trained"] <= 10_000
            or type(metrics["heldout"]) is not int
            or not MIN_HOLDOUT <= metrics["heldout"] <= 10_000
            or metrics["trained"] + metrics["heldout"] > 10_000):
        raise CandidateError("CANDIDATE_INSUFFICIENT_OR_INVALID_COUNTS")
    loss = metrics["mean_heldout_loss"]
    baseline = metrics["uniform_baseline"]
    if (type(loss) not in (float, int) or type(baseline) not in (float, int)
            or not math.isfinite(loss) or not math.isfinite(baseline)
            or loss < 0 or abs(baseline - math.log(2)) > 1e-8
            or loss + MIN_DELTA >= baseline):
        raise CandidateError("CANDIDATE_SELF_REPORTED_HOLDOUT_NOT_READY")
    return {
        "state": "STRUCTURAL_PASS_INDEPENDENT_REVIEW_REQUIRED",
        "tensor_sha256": digest,
        "execute_allowed": False,
        "safe_to_promote": False,
        "self_reported_metrics_trusted": False,
    }


def build_candidate(model: dict) -> dict:
    """Strip profile, world/save hashes, replay Bloom, sample IDs and samples."""
    if not isinstance(model, dict):
        raise CandidateError("SOURCE_MODEL_INVALID")
    # No arbitrary model fields are copied, and no code/pickled objects are read.
    weights = {name: model[name] for name in WEIGHTS}
    _weights(weights)
    heldout = model.get("heldout")
    trained = model.get("trained")
    if (type(heldout) is not int or heldout < MIN_HOLDOUT
            or type(trained) is not int or trained < MIN_TRAIN):
        raise CandidateError("SOURCE_MODEL_INSUFFICIENT_HOLDOUT")
    loss = model["heldout_reconstruction_sum"] / heldout
    baseline = model["heldout_baseline_sum"] / heldout
    candidate = {
        "schema": SCHEMA,
        "kind": KIND,
        "feature_shape": [5, 5, 3],
        "latent_size": 4,
        "weights": weights,
        "tensor_sha256": _digest(weights),
        "reported_training": {
            "trained": trained,
            "heldout": heldout,
            "mean_heldout_loss": loss,
            "uniform_baseline": baseline,
        },
        "effect_policy": NO_EFFECT,
        "review_state": "UNREVIEWED",
    }
    validate_candidate(candidate)
    return candidate


def _strict_json(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise CandidateError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _read_json(path: Path, cap: int) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > cap:
        raise CandidateError("UNSAFE_OR_OVERSIZED_INPUT")
    raw = path.read_bytes()
    if len(raw) > cap:
        raise CandidateError("OVERSIZED_INPUT")
    try:
        return json.loads(
            raw.decode("utf-8"), object_pairs_hook=_strict_json,
            parse_constant=lambda _: (_ for _ in ()).throw(
                CandidateError("NONFINITE_JSON_VALUE")
            ),
        )
    except (UnicodeError, RecursionError, json.JSONDecodeError) as exc:
        raise CandidateError("INVALID_JSON_INPUT") from exc


def read_candidate(path: Path) -> dict:
    result = _read_json(path, MAX_CANDIDATE_BYTES)
    validate_candidate(result)
    return result


def _holdout(path: Path) -> list[list[int]]:
    value = _read_json(path, MAX_HOLDOUT_BYTES)
    if not isinstance(value, dict) or set(value) != {"schema", "vectors"}:
        raise CandidateError("HOLDOUT_SCHEMA_INVALID")
    rows = value["vectors"]
    if (value["schema"] != HOLDOUT_SCHEMA or not isinstance(rows, list)
            or not 8 <= len(rows) <= 64):
        raise CandidateError("HOLDOUT_COUNT_OR_KIND_INVALID")
    for row in rows:
        if (not isinstance(row, list) or len(row) != 75
                or any(type(cell) is not int or cell not in (0, 1) for cell in row)):
            raise CandidateError("HOLDOUT_VECTOR_INVALID")
    return rows


def research_benchmark(candidate: dict, cohorts: tuple[list, list]) -> dict:
    """Non-executable offline screening; dataset independence is NOT attested."""
    validate_candidate(candidate)
    if len(cohorts) != 2:
        raise CandidateError("TWO_REVIEWER_COHORTS_REQUIRED")
    if cohorts[0] == cohorts[1]:
        raise CandidateError("IDENTICAL_HOLDOUT_COHORTS")
    results = []
    for rows in cohorts:
        if not isinstance(rows, list) or not 8 <= len(rows) <= 64:
            raise CandidateError("HOLDOUT_COUNT_INVALID")
        total = 0.0
        for row in rows:
            if (not isinstance(row, list) or len(row) != 75
                    or any(type(n) is not int or n not in (0, 1) for n in row)):
                raise CandidateError("HOLDOUT_VECTOR_INVALID")
            *_, reconstruction, kl = _forward(candidate["weights"], row, [0.0] * 4)
            total += reconstruction + BETA * kl
        mean = total / len(rows)
        if not math.isfinite(mean):
            raise CandidateError("BENCHMARK_NONFINITE")
        results.append({"examples": len(rows), "mean_loss": round(mean, 6),
                        "improvement_vs_uniform": round(math.log(2) - mean, 6),
                        "pass": mean + MIN_DELTA < math.log(2)})
    passed = all(item["pass"] for item in results)
    return {
        "state": ("RESEARCH_BENCHMARK_PASS_HUMAN_REVIEW_REQUIRED" if passed
                  else "RESEARCH_BENCHMARK_FAIL"),
        "cohorts": results,
        "execute_allowed": False,
        "safe_to_promote": False,
        "independent_provenance_attested": False,
        "privacy_review_required": True,
        "developer_approval_required": True,
    }


def export_to(path: Path, candidate: dict) -> None:
    validate_candidate(candidate)
    if path.parent.is_symlink() or not path.parent.is_dir() or path.is_symlink():
        raise CandidateError("UNSAFE_EXPORT_TARGET")
    payload = (json.dumps(candidate, sort_keys=True, separators=(",", ":"),
                          allow_nan=False) + "\n").encode("utf-8")
    if len(payload) > MAX_CANDIDATE_BYTES:
        raise CandidateError("CANDIDATE_EXCEEDS_SIZE_CAP")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise CandidateError("EXPORT_TARGET_ALREADY_EXISTS") from exc
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)


def run(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    exp = commands.add_parser("export", help="Explicit export; no network or automatic PR")
    exp.add_argument("--snapshot", required=True)
    exp.add_argument("--profile", help="Existing profile, or current if omitted")
    exp.add_argument("--out", type=Path, required=True)
    exp.add_argument("--ack-share-weights", action="store_true",
                     help="Acknowledge weights can reveal learned training details")
    check = commands.add_parser("validate", help="Reject malformed untrusted JSON")
    check.add_argument("--candidate", type=Path, required=True)
    benchmark = commands.add_parser("benchmark", help="Research-only two-cohort eval")
    benchmark.add_argument("--candidate", type=Path, required=True)
    benchmark.add_argument("--holdout-a", type=Path, required=True)
    benchmark.add_argument("--holdout-b", type=Path, required=True)
    opts = parser.parse_args(argv)
    if opts.command == "export":
        if not opts.ack_share_weights:
            raise CandidateError("EXPLICIT_WEIGHT_SHARING_ACK_REQUIRED")
        selected = view(profile_id=opts.profile)["profile_id"]
        model = load_local_model(read_snapshot(opts.snapshot), profile_id=selected)
        candidate = build_candidate(model)
        export_to(opts.out, candidate)
        return {"state": "LOCAL_CANDIDATE_EXPORTED_NOT_UPLOADED",
                "tensor_sha256": candidate["tensor_sha256"],
                "execute_allowed": False, "safe_to_promote": False}
    candidate = read_candidate(opts.candidate)
    if opts.command == "validate":
        return validate_candidate(candidate)
    return research_benchmark(candidate, (
        _holdout(opts.holdout_a), _holdout(opts.holdout_b)
    ))


def main() -> int:
    try:
        print(json.dumps(run(), sort_keys=True))
        return 0
    except (CandidateError, OSError, ValueError, TypeError, KeyError,
            OverflowError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
