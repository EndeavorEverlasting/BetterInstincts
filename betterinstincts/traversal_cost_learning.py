"""Replay-safe, opt-in local edge-cost calibration for verified Sims region routes.

Policy/host evidence only. No game input, polling, screenshots or save access.
The existing household graph and player/scene/VOI gates remain authoritative.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Mapping

SCHEMA = "betterinstincts.traversal-cost-learning/v1"
EVENT_SCHEMA = "betterinstincts.traversal-transition/v1"
PROOF = "OFFLINE_OBSERVED_EDGE_COSTS_NOT_GAME_MOVEMENT_OR_INPUT_CERT"
TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")
BLOOM_BYTES = 16_384
BLOOM_BITS = BLOOM_BYTES * 8
MAX_EVENTS = 20_000
MAX_EDGES = 512
MAX_PROFILES = 64
MAX_BYTES = 128_000
REQUIRED_EVENT = frozenset({
    "schema", "event_ref", "source", "operator_reviewed", "sensor_verified",
    "player_interrupted", "scope_id", "actor_id", "scene_revision",
    "from_region", "to_region", "before_capture_ref", "after_capture_ref",
    "outcome", "elapsed_ms",
})
ROW_FIELDS = frozenset({
    "from", "to", "base_cost", "expected_ms", "observations",
    "successes", "mean_ratio", "failure_ewma",
})


class TraversalLearningError(ValueError):
    """Untrusted event, profile, replay capacity, or storage boundary."""


def _token(value: object) -> bool:
    return isinstance(value, str) and TOKEN.fullmatch(value) is not None


def _scope(value: object) -> bool:
    # Repository scope identifiers may contain hierarchical separators. They
    # are never written verbatim to the local model; only a digest is retained.
    return (isinstance(value, str) and 1 <= len(value) <= 160
            and all(ch.isalnum() or ch in "_./:-" for ch in value))


def context_hash(snapshot: Mapping) -> str:
    """Opaque install-local routing context; no raw Sim/save names are retained."""
    if not isinstance(snapshot, Mapping):
        raise TraversalLearningError("SNAPSHOT_INVALID")
    fields = ("scope_id", "save_scope_id", "household_id", "lot_id",
              "game_build", "graph_revision")
    if any(not _scope(snapshot.get(field)) for field in fields):
        raise TraversalLearningError("CONTEXT_IDENTITY_UNVERIFIED")
    material = json.dumps([snapshot[field] for field in fields],
                          separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(("traversal-cost/v1:" + material).encode()).hexdigest()


def empty_model(snapshot: Mapping) -> dict:
    return {
        "schema": SCHEMA, "context_hash": context_hash(snapshot),
        "game_build": snapshot["game_build"],
        "edges": [], "seen_count": 0,
        "seen_bloom": "00" * BLOOM_BYTES,
        "proof_ceiling": PROOF,
    }


def _valid_model(model: Mapping, snapshot: Mapping) -> dict:
    if (not isinstance(model, dict)
            or set(model) != {"schema", "context_hash", "game_build", "edges",
                                  "seen_count", "seen_bloom", "proof_ceiling"}
            or model["schema"] != SCHEMA or model["proof_ceiling"] != PROOF
            or model["context_hash"] != context_hash(snapshot)
            or model["game_build"] != snapshot["game_build"]):
        raise TraversalLearningError("MODEL_CONTEXT_OR_SCHEMA_MISMATCH")
    count = model["seen_count"]
    if type(count) is not int or not 0 <= count <= MAX_EVENTS:
        raise TraversalLearningError("MODEL_EVENT_COUNT_INVALID")
    bloom = model["seen_bloom"]
    if not isinstance(bloom, str) or len(bloom) != BLOOM_BYTES * 2:
        raise TraversalLearningError("MODEL_BLOOM_INVALID")
    try:
        bytes.fromhex(bloom)
    except ValueError as exc:
        raise TraversalLearningError("MODEL_BLOOM_INVALID") from exc
    rows = model["edges"]
    if not isinstance(rows, list) or len(rows) > MAX_EDGES:
        raise TraversalLearningError("MODEL_EDGE_LIMIT")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != ROW_FIELDS:
            raise TraversalLearningError("MODEL_EDGE_SCHEMA_INVALID")
        edge = (row["from"], row["to"])
        if (not all(_token(x) for x in edge) or edge[0] == edge[1]
                or edge in seen):
            raise TraversalLearningError("MODEL_EDGE_IDENTITY_INVALID")
        seen.add(edge)
        if (type(row["base_cost"]) is not int or not 1 <= row["base_cost"] <= 1000
                or type(row["expected_ms"]) is not int
                or not 100 <= row["expected_ms"] <= 300_000
                or type(row["observations"]) is not int
                or not 1 <= row["observations"] <= MAX_EVENTS
                or type(row["successes"]) is not int
                or not 0 <= row["successes"] <= row["observations"]):
            raise TraversalLearningError("MODEL_EDGE_COUNTS_INVALID")
        for field, lo, hi in (("mean_ratio", 0.5, 3.0),
                              ("failure_ewma", 0.0, 1.0)):
            value = row[field]
            if type(value) not in (int, float) or not math.isfinite(value) or not lo <= value <= hi:
                raise TraversalLearningError("MODEL_EDGE_ESTIMATE_INVALID")
    return model


def _passage(snapshot: Mapping, a: str, b: str) -> tuple[int, int] | None:
    """Only verified current-graph traversable edges, including reverse legs."""
    passages = snapshot.get("passages")
    regions = snapshot.get("regions")
    if not isinstance(passages, list) or len(passages) > 512 or not isinstance(regions, dict):
        return None
    if a not in regions or b not in regions or a == b:
        return None
    for node in (a, b):
        region = regions[node]
        if (not isinstance(region, Mapping) or region.get("lot_id") != snapshot.get("lot_id")
                or region.get("lot_status") != "VERIFIED_ON_LOT"
                or region.get("observed") is not True):
            return None
    candidates = []
    for row in passages:
        if not isinstance(row, Mapping):
            continue
        direct = row.get("from") == a and row.get("to") == b
        reverse = row.get("from") == b and row.get("to") == a and row.get("bidirectional") is True
        weight, ms = row.get("cost"), row.get("expected_ms")
        if ((direct or reverse) and row.get("kind") == "WALKABLE_PASSAGE"
                and row.get("verified") is True
                and row.get("source") in {"GAME_ROUTE_PROBE", "OPERATOR_VERIFIED_TRAVERSAL"}
                and row.get("lot_id") == snapshot.get("lot_id")
                and row.get("graph_revision") == snapshot.get("graph_revision")
                and type(row.get("bidirectional")) is bool
                and type(weight) is int and 1 <= weight <= 1000
                and type(ms) is int and 100 <= ms <= 300_000):
            candidates.append((weight, ms))
    return min(candidates) if candidates else None


def _bloom_indices(context: str, ref: str) -> tuple[int, ...]:
    digest = hashlib.sha256((context + ":" + ref).encode("utf-8")).digest()
    return tuple(int.from_bytes(digest[i * 4:i * 4 + 4], "big") % BLOOM_BITS
                 for i in range(4))


def learn_transition(snapshot: Mapping, event: Mapping, *,
                     prior: Mapping | None = None) -> tuple[dict, str]:
    """One independent source-qualified outcome, never a simulated walk or pan.

    A Bloom filter favors safe false-positive abstention over replay acceptance.
    The same event reference cannot increase counts across process restarts.
    """
    context = context_hash(snapshot)
    if (snapshot.get("scene") != "LIVE_MODE"
            or snapshot.get("observed_scene_revision") != snapshot.get("scene_revision")
            or snapshot.get("human_present") is not False
            or snapshot.get("position_source") not in {"GAME_STATE", "HOST_VERIFIED_OBSERVATION"}
            or snapshot.get("player_directed") is True):
        raise TraversalLearningError("LIVE_SCENE_PLAYER_OR_POSITION_UNVERIFIED")
    if not isinstance(event, Mapping) or set(event) != REQUIRED_EVENT:
        raise TraversalLearningError("EVENT_FIELDS_INVALID")
    for field in ("event_ref", "actor_id", "scene_revision",
                  "from_region", "to_region", "before_capture_ref", "after_capture_ref"):
        if not _token(event.get(field)):
            raise TraversalLearningError("EVENT_IDENTITY_INVALID:" + field)
    if not _scope(event.get("scope_id")):
        raise TraversalLearningError("EVENT_SCOPE_INVALID")
    if (event["schema"] != EVENT_SCHEMA or event["scope_id"] != snapshot["scope_id"]
            or event["actor_id"] != snapshot.get("actor_id")
            or event["scene_revision"] != snapshot["scene_revision"]
            or event["before_capture_ref"] == event["after_capture_ref"]
            or event["from_region"] == event["to_region"]
            or event["player_interrupted"] is not False):
        raise TraversalLearningError("EVENT_STALE_REPLAY_OR_INTERRUPTED")
    source = event.get("source")
    if not (source == "GAME_ROUTE_PROBE" and event.get("sensor_verified") is True
            or source == "OPERATOR_VERIFIED_TRAVERSAL" and event.get("operator_reviewed") is True):
        raise TraversalLearningError("INDEPENDENT_SOURCE_ATTESTATION_REQUIRED")
    if type(event.get("operator_reviewed")) is not bool or type(event.get("sensor_verified")) is not bool:
        raise TraversalLearningError("SOURCE_FLAGS_INVALID")
    outcome = event.get("outcome")
    elapsed = event.get("elapsed_ms")
    if outcome == "SUCCESS":
        if (type(elapsed) is not int or not 100 <= elapsed <= 300_000
                or snapshot.get("current_region") != event["to_region"]):
            raise TraversalLearningError("SUCCESS_ARRIVAL_OR_DURATION_UNVERIFIED")
    elif outcome in ("BLOCKED", "TIMEOUT"):
        if elapsed is not None or snapshot.get("current_region") != event["from_region"]:
            raise TraversalLearningError("FAILURE_POSITION_OR_DURATION_UNVERIFIED")
    else:
        raise TraversalLearningError("OUTCOME_UNKNOWN")
    verified = _passage(snapshot, event["from_region"], event["to_region"])
    if verified is None:
        raise TraversalLearningError("VERIFIED_BASELINE_EDGE_AND_TIMING_REQUIRED")
    model = json.loads(json.dumps(prior)) if prior is not None else empty_model(snapshot)
    _valid_model(model, snapshot)
    bloom = bytearray.fromhex(model["seen_bloom"])
    indices = _bloom_indices(context, event["event_ref"])
    if all(bloom[i // 8] & (1 << (i % 8)) for i in indices):
        return model, "REPLAY_OR_BLOOM_COLLISION_IGNORED"
    if model["seen_count"] >= MAX_EVENTS:
        raise TraversalLearningError("BOUNDED_EVENT_CAPACITY_REACHED")
    rows = {(r["from"], r["to"]): r for r in model["edges"]}
    key = (event["from_region"], event["to_region"])
    if key not in rows:
        if len(rows) >= MAX_EDGES:
            raise TraversalLearningError("BOUNDED_EDGE_CAPACITY_REACHED")
        rows[key] = {
            "from": key[0], "to": key[1], "base_cost": verified[0],
            "expected_ms": verified[1], "observations": 0,
            "successes": 0, "mean_ratio": 1.0, "failure_ewma": 0.0,
        }
    row = rows[key]
    if (row["base_cost"], row["expected_ms"]) != verified:
        raise TraversalLearningError("BASELINE_CHANGED_REQUIRES_GRAPH_REVISION")
    row["observations"] += 1
    alpha_fail = 1 / min(row["observations"], 16)
    row["failure_ewma"] = (1 - alpha_fail) * row["failure_ewma"] + alpha_fail * (outcome != "SUCCESS")
    if outcome == "SUCCESS":
        row["successes"] += 1
        ratio = max(0.5, min(3.0, elapsed / verified[1]))
        alpha_time = 1 / min(row["successes"], 16)
        row["mean_ratio"] = (1 - alpha_time) * row["mean_ratio"] + alpha_time * ratio
    for i in indices:
        bloom[i // 8] |= 1 << (i % 8)
    model["edges"] = [rows[k] for k in sorted(rows)]
    model["seen_bloom"] = bloom.hex()
    model["seen_count"] += 1
    _valid_model(model, snapshot)
    return model, "ACCEPTED_OBSERVED_TRANSITION"


def apply_learned_costs(snapshot: Mapping, graph: Mapping[str, Mapping[str, int]]
                        ) -> tuple[dict[str, dict[str, int]], str, int]:
    """Fixed-point Dijkstra weights; never add an edge or an input permission."""
    model = snapshot.get("traversal_cost_model")
    baseline = {a: dict(edges) for a, edges in graph.items()}
    if model is None:
        return baseline, "NO_MODEL_BASELINE_ONLY", 0
    try:
        _valid_model(model, snapshot)
    except (TraversalLearningError, TypeError, KeyError, ValueError):
        return baseline, "INVALID_OR_CROSS_SCOPE_MODEL_BASELINE_ONLY", 0
    rows = {(r["from"], r["to"]): r for r in model["edges"]}
    adjusted = 0
    result = {a: {b: cost * 1000 for b, cost in edges.items()}
              for a, edges in baseline.items()}
    for a, edges in baseline.items():
        for b, cost in edges.items():
            row = rows.get((a, b))
            if row is None or (row["base_cost"], row["expected_ms"]) != _passage(snapshot, a, b):
                continue
            n = row["observations"]
            support = min(0.75, n / (n + 6))
            factor = max(0.75, min(2.5, 1 + support * (
                (row["mean_ratio"] - 1 if row["successes"] else 0)
                + 1.5 * row["failure_ewma"])))
            result[a][b] = max(1, int(cost * 1000 * factor + 0.5))
            adjusted += 1
    return result, "LEARNED_COSTS_APPLIED" if adjusted else "NO_MATCHING_VERIFIED_SAMPLES", adjusted


def _local_path(snapshot: Mapping) -> Path:
    # The sole canonical machine-scoped use path is defined by bootstrap.paths.
    from bootstrap import paths
    use = paths()["use"]
    parent = use.parent
    root = parent / "runtime" / "learning"
    for entry in (parent, root.parent, root):
        if entry.is_symlink():
            raise TraversalLearningError("LEARNING_STORAGE_SYMLINK_DENIED")
    return root / (context_hash(snapshot) + ".json")


def load_local_model(snapshot: Mapping) -> dict:
    """Read opted-in model only when explicitly called; no discovery or writes."""
    path = _local_path(snapshot)
    if path.is_symlink():
        raise TraversalLearningError("LEARNING_MODEL_SYMLINK_DENIED")
    if not path.exists():
        return empty_model(snapshot)
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise TraversalLearningError("LEARNING_MODEL_FILE_UNSAFE")
    try:
        model = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise TraversalLearningError("LEARNING_MODEL_UNREADABLE") from exc
    return _valid_model(model, snapshot)


def record_local_transition(snapshot: Mapping, event: Mapping, *,
                            explicit_opt_in: bool = False) -> dict:
    """One user-scoped atomic update from an explicitly active host session.

    Does not install a watcher, read a saved game, or create a background job.
    """
    if explicit_opt_in is not True:
        raise TraversalLearningError("EXPLICIT_LOCAL_LEARNING_OPT_IN_REQUIRED")
    # Validate before creating any new user-scoped files.
    learn_transition(snapshot, event)
    path = _local_path(snapshot)
    root = path.parent
    if not root.exists():
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.is_symlink() or not root.is_dir():
        raise TraversalLearningError("LEARNING_STORAGE_UNSAFE")
    if not path.exists() and sum(p.suffix == ".json" for p in root.iterdir()) >= MAX_PROFILES:
        raise TraversalLearningError("LEARNING_PROFILE_CAP_REACHED")
    lock = path.with_suffix(".lock")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(lock, flags, 0o600)
    except FileExistsError as exc:
        raise TraversalLearningError("LEARNING_WRITER_BUSY") from exc
    tmp = None
    try:
        os.close(fd)
        prior = load_local_model(snapshot)
        model, status = learn_transition(snapshot, event, prior=prior)
        if status != "ACCEPTED_OBSERVED_TRANSITION":
            return {"status": status, "seen_count": prior["seen_count"], "proof_ceiling": PROOF}
        raw = (json.dumps(model, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        if len(raw) > MAX_BYTES:
            raise TraversalLearningError("LEARNING_MODEL_FILE_TOO_LARGE")
        fd, temp_name = tempfile.mkstemp(prefix=".edge-", dir=str(root))
        tmp = Path(temp_name)
        with os.fdopen(fd, "wb") as stream:
            os.chmod(tmp, 0o600)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if path.is_symlink():
            raise TraversalLearningError("LEARNING_MODEL_SYMLINK_DENIED")
        os.replace(tmp, path)
        tmp = None
        return {"status": status, "seen_count": model["seen_count"],
                "profile_hash": model["context_hash"], "proof_ceiling": PROOF}
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


__all__ = ["TraversalLearningError", "context_hash", "empty_model", "learn_transition",
           "apply_learned_costs", "load_local_model", "record_local_transition"]
