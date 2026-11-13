"""Bounded trainable spatial convolution on independently observed Sims routes.

Pure read-only inference and explicitly opted-in local training. Never controls
the game, camera, queue or save. Existing graph/EA authority remains upstream.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Mapping

from betterinstincts.traversal_cost_learning import context_hash

SCHEMA = "betterinstincts.spatial-convolution.model/v1"
PATCH_SCHEMA = "betterinstincts.spatial-convolution.patch/v1"
PROOF = "OFFLINE_LABELLED_CONVOLUTION_NOT_LIVE_SIM_OR_SENSOR_CERT"
TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")
MAX_EVENTS = 256
MAX_BYTES = 100_000
MAX_PROFILES = 64
CHANNELS = ("WALKABLE", "BLOCKED", "TARGET")
LR = 0.08


class SpatialConvolutionError(ValueError):
    """Unsupported spatial evidence, stale context or model corruption."""


def _token(value: object) -> bool:
    return isinstance(value, str) and TOKEN.fullmatch(value) is not None


def _number(value: object, limit: float = 4.0) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > limit:
        raise SpatialConvolutionError("NONFINITE_OR_UNBOUNDED_WEIGHT")
    return float(value)


def _context(snapshot: Mapping) -> str:
    try:
        key = context_hash(snapshot)
    except (ValueError, TypeError, KeyError) as exc:
        raise SpatialConvolutionError("CONTEXT_UNVERIFIED") from exc
    if (snapshot.get("scene") != "LIVE_MODE"
            or snapshot.get("scene_revision") != snapshot.get("observed_scene_revision")
            or snapshot.get("human_present") is not False
            or snapshot.get("player_directed") is True
            or snapshot.get("position_source") not in {"GAME_STATE", "HOST_VERIFIED_OBSERVATION"}
            or not _token(snapshot.get("actor_id"))):
        raise SpatialConvolutionError("PLAYER_OR_SCENE_GATE")
    return key


def _edge(snapshot: Mapping, start: str, end: str) -> int:
    if not _token(start) or not _token(end) or start == end:
        raise SpatialConvolutionError("EDGE_IDENTITY_INVALID")
    regions = snapshot.get("regions")
    if not isinstance(regions, Mapping):
        raise SpatialConvolutionError("REGIONS_MISSING")
    a, b = regions.get(start), regions.get(end)
    if any(not isinstance(r, Mapping)
           or r.get("lot_id") != snapshot.get("lot_id")
           or r.get("lot_status") != "VERIFIED_ON_LOT"
           or r.get("observed") is not True
           or type(r.get("floor")) is not int for r in (a, b)):
        raise SpatialConvolutionError("REGIONS_NOT_VERIFIED")
    if a["floor"] != b["floor"]:
        raise SpatialConvolutionError("FLOOR_CROSSING_REQUIRES_NATIVE_EVIDENCE")
    passages = snapshot.get("passages")
    if not isinstance(passages, list) or len(passages) > 512:
        raise SpatialConvolutionError("PASSAGES_UNBOUNDED")
    for item in passages:
        if not isinstance(item, Mapping):
            continue
        forward = item.get("from") == start and item.get("to") == end
        backward = (item.get("bidirectional") is True
                    and item.get("to") == start and item.get("from") == end)
        if (forward or backward) and (item.get("kind") == "WALKABLE_PASSAGE"
                and item.get("verified") is True
                and item.get("source") in {"GAME_ROUTE_PROBE", "OPERATOR_VERIFIED_TRAVERSAL"}
                and item.get("lot_id") == snapshot.get("lot_id")
                and item.get("graph_revision") == snapshot.get("graph_revision")):
            return a["floor"]
    raise SpatialConvolutionError("VERIFIED_WALKABLE_EDGE_REQUIRED")


def _patch(snapshot: Mapping, patch: Mapping, start: str, end: str) -> list:
    floor = _edge(snapshot, start, end)
    if (not isinstance(patch, Mapping) or set(patch) !=
            {"schema", "source", "graph_revision", "geometry_ref", "floor", "cells"}
            or patch.get("schema") != PATCH_SCHEMA
            or patch.get("source") not in {"EA_READ_ONLY", "OPERATOR_REVIEWED_GEOMETRY"}
            or patch.get("graph_revision") != snapshot.get("graph_revision")
            or not _token(patch.get("geometry_ref"))
            or type(patch.get("floor")) is not int or patch["floor"] != floor):
        raise SpatialConvolutionError("PATCH_PROVENANCE_OR_FLOOR_INVALID")
    cells = patch.get("cells")
    if not isinstance(cells, list) or len(cells) != 5:
        raise SpatialConvolutionError("PATCH_DIMENSIONS_INVALID")
    targets = known = 0
    for row in cells:
        if not isinstance(row, list) or len(row) != 5:
            raise SpatialConvolutionError("PATCH_DIMENSIONS_INVALID")
        for cell in row:
            if (not isinstance(cell, list) or len(cell) != 3
                    or any(type(v) is not int or v not in (0, 1) for v in cell)
                    or cell[0] + cell[1] > 1 or (cell[2] and cell[0] != 1)):
                raise SpatialConvolutionError("PATCH_CELL_INVALID")
            known += cell[0] + cell[1]
            targets += cell[2]
    if targets != 1 or known < 20:
        raise SpatialConvolutionError("PATCH_TARGET_OR_COVERAGE_INSUFFICIENT")
    return cells


def empty_model(snapshot: Mapping) -> dict:
    key = _context(snapshot)
    weights = []
    for sign in (1, -1):
        weights.append([[
            [-0.04 * sign, 0.12 * sign, 0.02 * sign] for _ in range(3)
        ] for _ in range(3)])
    return {
        "schema": SCHEMA, "context_hash": key, "channels": list(CHANNELS),
        "filters": weights, "conv_bias": [0.1, 0.1],
        "head": [0.2, -0.2], "head_bias": 0.0,
        "trained": 0, "positive": 0, "negative": 0, "heldout": 0,
        "heldout_brier_sum": 0.0, "baseline_brier_sum": 0.0,
        "seen": [], "proof_ceiling": PROOF,
    }


def _model(model: Mapping, snapshot: Mapping) -> dict:
    if not isinstance(model, dict) or set(model) != set(empty_model(snapshot)):
        raise SpatialConvolutionError("MODEL_SCHEMA_INVALID")
    if (model["schema"] != SCHEMA or model["proof_ceiling"] != PROOF
            or model["channels"] != list(CHANNELS)
            or model["context_hash"] != _context(snapshot)):
        raise SpatialConvolutionError("MODEL_CROSS_SCOPE")
    for k in ("trained", "positive", "negative", "heldout"):
        if type(model[k]) is not int or not 0 <= model[k] <= MAX_EVENTS:
            raise SpatialConvolutionError("MODEL_COUNT_INVALID")
    if model["positive"] + model["negative"] != model["trained"]:
        raise SpatialConvolutionError("MODEL_COUNT_MISMATCH")
    ids = model["seen"]
    if (not isinstance(ids, list) or len(ids) != model["trained"] + model["heldout"]
            or len(ids) > MAX_EVENTS or len(ids) != len(set(ids))
            or any(not isinstance(v, str) or not re.fullmatch("[0-9a-f]{40}", v) for v in ids)):
        raise SpatialConvolutionError("MODEL_REPLAY_RECORD_INVALID")
    for k in ("heldout_brier_sum", "baseline_brier_sum"):
        if not 0 <= _number(model[k], MAX_EVENTS) <= MAX_EVENTS:
            raise SpatialConvolutionError("MODEL_VALIDATION_INVALID")
    if not isinstance(model["filters"], list) or len(model["filters"]) != 2:
        raise SpatialConvolutionError("MODEL_FILTER_SHAPE")
    for f in model["filters"]:
        if not isinstance(f, list) or len(f) != 3:
            raise SpatialConvolutionError("MODEL_FILTER_SHAPE")
        for row in f:
            if not isinstance(row, list) or len(row) != 3:
                raise SpatialConvolutionError("MODEL_FILTER_SHAPE")
            for channels in row:
                if not isinstance(channels, list) or len(channels) != 3:
                    raise SpatialConvolutionError("MODEL_FILTER_SHAPE")
                for w in channels:
                    _number(w)
    for k in ("head", "conv_bias"):
        if not isinstance(model[k], list) or len(model[k]) != 2:
            raise SpatialConvolutionError("MODEL_HEAD_SHAPE")
        for w in model[k]:
            _number(w)
    _number(model["head_bias"])
    return model


def _forward(model: Mapping, cells: list) -> tuple[float, list, list]:
    activations = []
    pools = []
    for f, bias in zip(model["filters"], model["conv_bias"]):
        fmap = []
        for y in range(3):
            row = []
            for x in range(3):
                value = bias + sum(
                    f[j][i][channel] * cells[y + j][x + i][channel]
                    for j in range(3) for i in range(3) for channel in range(3)
                )
                row.append(value)
            fmap.append(row)
        activations.append(fmap)
        pools.append(sum(max(0.0, z) for row in fmap for z in row) / 9.0)
    z = model["head_bias"] + sum(w * v for w, v in zip(model["head"], pools))
    p = 1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, z))))
    return p, pools, activations


def _sample(snapshot: Mapping, event: Mapping, patch: Mapping) -> tuple[list, int, str]:
    _context(snapshot)
    if not isinstance(event, Mapping):
        raise SpatialConvolutionError("EVENT_MISSING")
    for k in ("event_ref", "actor_id", "scene_revision", "from_region",
              "to_region", "before_capture_ref", "after_capture_ref"):
        if not _token(event.get(k)):
            raise SpatialConvolutionError("EVENT_IDENTITY_INVALID:" + k)
    if (event.get("scope_id") != snapshot.get("scope_id")
            or event["actor_id"] != snapshot["actor_id"]
            or event["scene_revision"] != snapshot["scene_revision"]
            or event.get("graph_revision") != snapshot["graph_revision"]
            or event.get("game_build") != snapshot["game_build"]
            or event["before_capture_ref"] == event["after_capture_ref"]
            or event.get("player_interrupted") is not False):
        raise SpatialConvolutionError("EVENT_STALE_OR_INTERRUPTED")
    source = event.get("source")
    if not (source == "GAME_ROUTE_PROBE" and event.get("sensor_verified") is True
            or source == "OPERATOR_VERIFIED_TRAVERSAL" and event.get("operator_reviewed") is True):
        raise SpatialConvolutionError("INDEPENDENT_OUTCOME_REQUIRED")
    label = {"SUCCESS": 0, "BLOCKED": 1}.get(event.get("outcome"))
    if label is None:
        raise SpatialConvolutionError("UNSUPPORTED_OUTCOME")
    observed = event.get("observed_region")
    if observed != (event["from_region"] if label else event["to_region"]):
        raise SpatialConvolutionError("OBSERVED_ARRIVAL_OR_BLOCK_REQUIRED")
    cells = _patch(snapshot, patch, event["from_region"], event["to_region"])
    fingerprint = hashlib.sha256(
        (snapshot["game_build"] + ":" + event["before_capture_ref"]).encode("utf-8")
    ).hexdigest()[:40]
    return cells, label, fingerprint


def _qualified(model: Mapping) -> bool:
    return (model["trained"] >= 24 and model["positive"] >= 6
            and model["negative"] >= 6 and model["heldout"] >= 8
            and model["heldout_brier_sum"] + model["heldout"] * 0.02
                < model["baseline_brier_sum"])


def learn(snapshot: Mapping, event: Mapping, patch: Mapping, *,
          prior: Mapping | None = None, explicit_opt_in: bool = False) -> tuple[dict, str]:
    """One bounded online SGD step; 1/5 of independent samples are holdout only.

    The holdout is selected from the pre-action capture fingerprint before
    looking at the label. No training, tuning, or model selection uses it.
    """
    if explicit_opt_in is not True:
        raise SpatialConvolutionError("EXPLICIT_LEARNING_OPT_IN_REQUIRED")
    cells, label, fingerprint = _sample(snapshot, event, patch)
    model = copy.deepcopy(prior) if prior is not None else empty_model(snapshot)
    _model(model, snapshot)
    if fingerprint in model["seen"]:
        return model, "REPLAY_IGNORED"
    if len(model["seen"]) >= MAX_EVENTS:
        raise SpatialConvolutionError("MODEL_CAPACITY_REACHED")
    p, pools, activations = _forward(model, cells)
    if int(fingerprint[:8], 16) % 5 == 0:
        baseline = (model["positive"] + 1) / (model["trained"] + 2)
        model["heldout_brier_sum"] += (p - label) ** 2
        model["baseline_brier_sum"] += (baseline - label) ** 2
        model["heldout"] += 1
        state = "HELDOUT_VALIDATION_ONLY"
    else:
        err = p - label
        old_head = model["head"][:]
        # Backpropagate through ReLU and spatial mean pooling. Clip each
        # trainable parameter; a malformed update must never poison a model.
        for filt in range(2):
            factor = err * old_head[filt] / 9.0
            for j in range(3):
                for i in range(3):
                    for channel in range(3):
                        grad = sum(
                            cells[y + j][x + i][channel]
                            for y in range(3) for x in range(3)
                            if activations[filt][y][x] > 0
                        ) * factor
                        old = model["filters"][filt][j][i][channel]
                        model["filters"][filt][j][i][channel] = max(-4.0, min(4.0, old - LR * grad))
            active = sum(v > 0 for row in activations[filt] for v in row)
            model["conv_bias"][filt] = max(-4.0, min(4.0,
                model["conv_bias"][filt] - LR * factor * active))
            model["head"][filt] = max(-4.0, min(4.0,
                model["head"][filt] - LR * err * pools[filt]))
        model["head_bias"] = max(-4.0, min(4.0, model["head_bias"] - LR * err))
        model["trained"] += 1
        model["positive" if label else "negative"] += 1
        state = "TRAINED_OBSERVED_SAMPLE"
    model["seen"].append(fingerprint)
    _model(model, snapshot)
    return model, state


def advise(snapshot: Mapping, model: Mapping, patch: Mapping, *,
           from_region: str, to_region: str) -> dict:
    """Advisory only; never changes the graph, path, control permit or UI."""
    try:
        _context(snapshot)
        _model(model, snapshot)
        cells = _patch(snapshot, patch, from_region, to_region)
        if snapshot.get("current_region") != from_region:
            raise SpatialConvolutionError("STALE_CURRENT_REGION")
        if not _qualified(model):
            return {"status": "ABSTAIN_UNCALIBRATED", "blocked_probability": None,
                    "execute_allowed": False}
        p, _, _ = _forward(model, cells)
        return {"status": "CALIBRATED_ADVISORY", "blocked_probability": round(p, 5),
                "execute_allowed": False, "proof_ceiling": PROOF}
    except (SpatialConvolutionError, TypeError, ValueError, KeyError):
        return {"status": "ABSTAIN_INVALID_EVIDENCE", "blocked_probability": None,
                "execute_allowed": False}


def _local_path(snapshot: Mapping) -> Path:
    from bootstrap import paths
    root = paths()["use"].parent / "runtime" / "spatial-convolution"
    for path in (root.parent.parent, root.parent, root):
        if path.is_symlink():
            raise SpatialConvolutionError("LOCAL_STORAGE_SYMLINK_DENIED")
    return root / (context_hash(snapshot) + ".json")


def load_local_model(snapshot: Mapping) -> dict:
    _context(snapshot)
    path = _local_path(snapshot)
    if path.is_symlink():
        raise SpatialConvolutionError("MODEL_SYMLINK_DENIED")
    if not path.exists():
        return empty_model(snapshot)
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise SpatialConvolutionError("MODEL_FILE_UNSAFE")
    try:
        return _model(json.loads(path.read_text(encoding="utf-8")), snapshot)
    except (OSError, ValueError, UnicodeError, KeyError, TypeError) as exc:
        raise SpatialConvolutionError("MODEL_FILE_INVALID") from exc


def record_local_sample(snapshot: Mapping, event: Mapping, patch: Mapping, *,
                        explicit_opt_in: bool = False) -> dict:
    """Explicit local-only atomic update, with bounded no-follow writer lock."""
    if explicit_opt_in is not True:
        raise SpatialConvolutionError("EXPLICIT_LEARNING_OPT_IN_REQUIRED")
    _sample(snapshot, event, patch)  # Reject before touching local storage.
    path = _local_path(snapshot)
    root = path.parent
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.is_symlink() or not root.is_dir():
        raise SpatialConvolutionError("LOCAL_STORAGE_UNSAFE")
    if not path.exists() and sum(p.suffix == ".json" for p in root.iterdir()) >= MAX_PROFILES:
        raise SpatialConvolutionError("PROFILE_CAPACITY_REACHED")
    lock = path.with_suffix(".lock")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(lock, flags, 0o600)
    except FileExistsError as exc:
        raise SpatialConvolutionError("CONCURRENT_WRITER_BUSY") from exc
    temporary = None
    try:
        os.close(fd)
        old = load_local_model(snapshot)
        new, status = learn(snapshot, event, patch, prior=old, explicit_opt_in=True)
        if status == "REPLAY_IGNORED":
            return {"status": status, "trained": old["trained"],
                    "heldout": old["heldout"], "proof_ceiling": PROOF}
        payload = (json.dumps(new, sort_keys=True, separators=(",", ":")) + "\n").encode()
        if len(payload) > MAX_BYTES:
            raise SpatialConvolutionError("MODEL_STORAGE_LIMIT")
        fd, filename = tempfile.mkstemp(prefix=".spatial-", dir=str(root))
        temporary = Path(filename)
        with os.fdopen(fd, "wb") as stream:
            os.chmod(temporary, 0o600)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if path.is_symlink():
            raise SpatialConvolutionError("MODEL_SYMLINK_DENIED")
        os.replace(temporary, path)
        temporary = None
        return {"status": status, "trained": new["trained"],
                "heldout": new["heldout"], "proof_ceiling": PROOF}
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


__all__ = ["SpatialConvolutionError", "PATCH_SCHEMA", "PROOF", "empty_model",
           "learn", "advise", "load_local_model", "record_local_sample"]
