"""Bounded Gaussian-process duration comparison for PS-0241 ecology planning.

Standard-library Matérn-3/2 GP on at most 24 provenance-qualified observations.
A deterministic conservative upper bound wins unless held-out accuracy AND
coverage improve. No training daemon, telemetry persistence or effect authority.
"""
from __future__ import annotations

import math
import statistics
from collections.abc import Mapping

MAX_SAMPLES = 24
MIN_SAMPLES = 10
LENGTH_SCALES = (0.12, 0.25, 0.5, 1.0)


class EcologyForecastError(ValueError):
    pass


def _finite(v: object, lo: float, hi: float) -> bool:
    return type(v) in (int, float) and math.isfinite(v) and lo <= v <= hi


def _ref(v: object) -> bool:
    return isinstance(v, str) and 1 <= len(v) <= 120 and all(
        c.isalnum() or c in "_:.-" for c in v
    )


def _kernel(x: float, y: float, ell: float, variance: float) -> float:
    z = math.sqrt(3.0) * abs(x - y) / ell
    return variance * (1 + z) * math.exp(-z)


def _cholesky(matrix: list[list[float]]) -> list[list[float]]:
    n = len(matrix)
    lower = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            v = matrix[i][j] - sum(lower[i][k] * lower[j][k] for k in range(j))
            if i == j:
                if v <= 0 or not math.isfinite(v):
                    raise EcologyForecastError("GP_NON_POSITIVE_COVARIANCE")
                lower[i][j] = math.sqrt(v)
            else:
                lower[i][j] = v / lower[j][j]
    return lower


def _solve(lower: list[list[float]], vector: list[float]) -> list[float]:
    n = len(vector)
    forward = [0.0] * n
    for i in range(n):
        forward[i] = (vector[i] - sum(lower[i][j] * forward[j] for j in range(i))) / lower[i][i]
    backward = [0.0] * n
    for i in range(n - 1, -1, -1):
        backward[i] = (forward[i] - sum(lower[j][i] * backward[j] for j in range(i + 1, n))) / lower[i][i]
    return backward


def _predict(
    training: list[tuple[float, float]], query: float, ell: float,
) -> tuple[float, float]:
    xs = [x for x, _ in training]
    ys = [y for _, y in training]
    mu = statistics.median(ys)
    amplitude = max(0.25, statistics.pstdev(ys))
    variance = amplitude * amplitude
    noise = max(0.01, variance * 0.04)
    matrix = [
        [_kernel(xs[i], xs[j], ell, variance) + (noise if i == j else 0.0)
         for j in range(len(xs))] for i in range(len(xs))
    ]
    lower = _cholesky(matrix)
    k = [_kernel(x, query, ell, variance) for x in xs]
    weights = _solve(lower, [y - mu for y in ys])
    mean = mu + sum(a * b for a, b in zip(k, weights))
    v = _solve(lower, k)
    var = max(0.0, variance - sum(a * b for a, b in zip(k, v))) + noise
    return mean, math.sqrt(var)


def compare_duration_models(
    samples: list[Mapping], *, game_build: str, action_id: str,
    context: float, baseline_upper_sim_minutes: float,
) -> dict:
    """Hold out the newest 25%; use GP only with better error and no missed upper.

    The caller must supply a source-verified normalized scalar feature, such as
    an exact-patch activity-speed factor. Discontinuities, mismatched sources,
    insufficient evidence, or poor coverage favor the deterministic baseline.
    """
    if (not _ref(game_build) or not _ref(action_id)
            or not _finite(context, 0, 1)
            or not _finite(baseline_upper_sim_minutes, 0.01, 500)):
        raise EcologyForecastError("GP_INPUT_INVALID")
    result = {
        "model": "DETERMINISTIC", "selected_upper_sim_minutes": float(baseline_upper_sim_minutes),
        "baseline_upper_sim_minutes": float(baseline_upper_sim_minutes),
        "gate": "INSUFFICIENT_SOURCE_QUALIFIED_SAMPLES",
        "training_count": 0, "holdout_count": 0,
    }
    if not isinstance(samples, list) or len(samples) > MAX_SAMPLES:
        raise EcologyForecastError("GP_SAMPLE_BOUND")
    if len(samples) < MIN_SAMPLES:
        return result
    seen = set()
    pairs = []
    for sample in samples:
        if not isinstance(sample, Mapping):
            return {**result, "gate": "GP_SAMPLE_UNTRUSTWORTHY"}
        if (sample.get("game_build") != game_build
                or sample.get("action_id") != action_id
                or not _ref(sample.get("proof_ref"))
                or not _ref(sample.get("capture_ref"))
                or not _finite(sample.get("context"), 0, 1)
                or not _finite(sample.get("duration_sim_minutes"), 0.01, 500)
                or sample["capture_ref"] in seen):
            return {**result, "gate": "GP_SAMPLE_UNTRUSTWORTHY"}
        seen.add(sample["capture_ref"])
        pairs.append((float(sample["context"]), float(sample["duration_sim_minutes"])))
    size = max(2, len(pairs) // 4)
    train, holdout = pairs[:-size], pairs[-size:]
    result.update(training_count=len(train), holdout_count=len(holdout))
    deterministic_mean = statistics.median(y for _, y in train)
    baseline_error = statistics.mean(abs(deterministic_mean - y) for _, y in holdout)
    if baseline_error < 0.02:
        return {**result, "gate": "DETERMINISTIC_ALREADY_ACCURATE"}
    passing = []
    for scale in LENGTH_SCALES:
        try:
            predictions = [_predict(train, x, scale) for x, _ in holdout]
        except (EcologyForecastError, OverflowError, ZeroDivisionError):
            continue
        gp_error = statistics.mean(abs(pred[0] - y) for pred, (_, y) in zip(predictions, holdout))
        upper_covers_holdout = all(pred[0] + 2 * pred[1] >= y for pred, (_, y) in zip(predictions, holdout))
        if gp_error <= 0.9 * baseline_error and upper_covers_holdout:
            passing.append((gp_error, scale))
    if not passing:
        return {**result, "gate": "GP_FAILED_HOLDOUT_ACCURACY_OR_COVERAGE"}
    _, scale = min(passing)
    predicted, uncertainty = _predict(train, float(context), scale)
    candidate_upper = max(
        0.8 * baseline_upper_sim_minutes, predicted + 2 * uncertainty
    )
    if (not math.isfinite(candidate_upper)
            or candidate_upper >= baseline_upper_sim_minutes):
        return {**result, "gate": "GP_NO_DECISION_IMPROVEMENT"}
    return {
        **result, "model": "GAUSSIAN_PROCESS_MATERN32",
        "selected_upper_sim_minutes": round(candidate_upper, 6),
        "gate": "GP_VALIDATED_ON_CHRONOLOGICAL_HOLDOUT",
        "holdout_baseline_mae": round(baseline_error, 6),
        "kernel_length_scale": scale,
    }
