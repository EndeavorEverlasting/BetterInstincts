"""Opt-in, on-device semantic variational autoencoder for verified Sims floor patches.

This is a real (tiny) Gaussian VAE: encoder mean/log-variance, reparameterized
latent sample, sigmoid decoder, reconstruction loss + beta-KL SGD. No numpy,
PyTorch, raw screenshots, game inputs, network, or auto-sampling is required.
Decoded probabilities are hypotheses, never geometry or a control permit.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path
import random
import tempfile
from typing import Mapping

from betterinstincts.spatial_convolution import (
    SpatialConvolutionError, _context, _patch, _sample,
)
from betterinstincts.traversal_cost_learning import context_hash

SCHEMA = "betterinstincts.semantic-vae.model/v1"
PROOF = "OFFLINE_LOCAL_SEMANTIC_VAE_NOT_GAME_SLAM_OR_INPUT_CERT"
DIM, LATENT = 75, 4
MAX_EVENTS, MAX_RETAINED, MAX_BYTES, MAX_PROFILES = 10_000, 128, 125_000, 64
BLOOM_BYTES = 16_384
BLOOM_BITS = BLOOM_BYTES * 8
LEARNING_RATE, BETA = 0.12, 0.02
KEYS = {"schema", "context_hash", "dimensions", "latent_dimensions",
        "encoder_mu", "encoder_logvar", "bias_mu", "bias_logvar",
        "decoder", "decoder_bias", "trained", "heldout",
        "train_reconstruction_sum", "heldout_reconstruction_sum",
        "heldout_baseline_sum", "samples", "seen_bloom", "proof_ceiling"}


class SemanticVAEError(ValueError):
    """Invalid provenance, model, capacity, or local storage authority."""


def _num(value: object) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 4:
        raise SemanticVAEError("MODEL_PARAMETER_INVALID")
    return float(value)


def _matrix(value: object, rows: int, columns: int) -> None:
    if not isinstance(value, list) or len(value) != rows:
        raise SemanticVAEError("MODEL_TENSOR_SHAPE_INVALID")
    for row in value:
        if not isinstance(row, list) or len(row) != columns:
            raise SemanticVAEError("MODEL_TENSOR_SHAPE_INVALID")
        for w in row:
            _num(w)


def empty_model(snapshot: Mapping) -> dict:
    try:
        _context(snapshot)
        scope = context_hash(snapshot)
    except (SpatialConvolutionError, ValueError, TypeError, KeyError) as exc:
        raise SemanticVAEError("CONTEXT_UNVERIFIED") from exc
    rng = random.Random(int(hashlib.sha256(("semantic-vae:" + scope).encode()).hexdigest()[:16], 16))
    weights = lambda n, m: [[round(rng.uniform(-0.03, 0.03), 8)
                             for _ in range(m)] for _ in range(n)]
    return {
        "schema": SCHEMA, "context_hash": scope,
        "dimensions": DIM, "latent_dimensions": LATENT,
        "encoder_mu": weights(LATENT, DIM),
        "encoder_logvar": weights(LATENT, DIM),
        "bias_mu": [0.0] * LATENT, "bias_logvar": [0.0] * LATENT,
        "decoder": weights(DIM, LATENT),
        "decoder_bias": [0.0] * DIM,
        "trained": 0, "heldout": 0,
        "train_reconstruction_sum": 0.0, "heldout_reconstruction_sum": 0.0,
        "heldout_baseline_sum": 0.0, "samples": [],
        "seen_bloom": "00" * BLOOM_BYTES, "proof_ceiling": PROOF,
    }


def _validate(model: Mapping, snapshot: Mapping) -> dict:
    if (not isinstance(model, dict) or set(model) != KEYS
            or model.get("schema") != SCHEMA or model.get("proof_ceiling") != PROOF
            or model.get("context_hash") != context_hash(snapshot)
            or model.get("dimensions") != DIM or model.get("latent_dimensions") != LATENT):
        raise SemanticVAEError("MODEL_CONTEXT_OR_SCHEMA_INVALID")
    _matrix(model["encoder_mu"], LATENT, DIM)
    _matrix(model["encoder_logvar"], LATENT, DIM)
    _matrix(model["decoder"], DIM, LATENT)
    for key, size in (("bias_mu", LATENT), ("bias_logvar", LATENT),
                      ("decoder_bias", DIM)):
        if not isinstance(model[key], list) or len(model[key]) != size:
            raise SemanticVAEError("MODEL_BIAS_SHAPE_INVALID")
        for value in model[key]:
            _num(value)
    if any(type(model[k]) is not int or not 0 <= model[k] <= MAX_EVENTS
           for k in ("trained", "heldout")):
        raise SemanticVAEError("MODEL_COUNT_INVALID")
    rows = model["samples"]
    total = model["trained"] + model["heldout"]
    if (not isinstance(rows, list) or len(rows) > MAX_RETAINED
            or total > MAX_EVENTS or len(rows) > total):
        raise SemanticVAEError("MODEL_SAMPLE_COUNT_INVALID")
    raw_bloom = model.get("seen_bloom")
    if not isinstance(raw_bloom, str) or len(raw_bloom) != BLOOM_BYTES * 2:
        raise SemanticVAEError("MODEL_BLOOM_INVALID")
    try:
        bloom = bytes.fromhex(raw_bloom)
    except ValueError as exc:
        raise SemanticVAEError("MODEL_BLOOM_INVALID") from exc
    if total == 0 and any(bloom):
        raise SemanticVAEError("EMPTY_MODEL_BLOOM_NOT_EMPTY")
    if total > 0 and not any(bloom):
        raise SemanticVAEError("NONEMPTY_MODEL_BLOOM_EMPTY")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"id", "partition", "x"}:
            raise SemanticVAEError("SAMPLE_SCHEMA_INVALID")
        identity = row["id"]
        if (not isinstance(identity, str) or len(identity) != 40
                or any(ch not in "0123456789abcdef" for ch in identity)
                or identity in seen or row["partition"] not in ("TRAIN", "HOLDOUT")
                or not isinstance(row["x"], list) or len(row["x"]) != DIM
                or any(type(v) is not int or v not in (0, 1) for v in row["x"])):
            raise SemanticVAEError("SAMPLE_REPLAY_OR_VECTOR_INVALID")
        seen.add(identity)
        if not all(bloom[index // 8] & (1 << (index % 8))
                   for index in _bloom_indices(model["context_hash"], identity)):
            raise SemanticVAEError("MODEL_BLOOM_SAMPLE_MISMATCH")
    if sum(row["partition"] == "TRAIN" for row in rows) > model["trained"]:
        raise SemanticVAEError("MODEL_TRAIN_COUNT_INVALID")
    if sum(row["partition"] == "HOLDOUT" for row in rows) > model["heldout"]:
        raise SemanticVAEError("MODEL_HOLDOUT_COUNT_INVALID")
    for k in ("train_reconstruction_sum", "heldout_reconstruction_sum",
              "heldout_baseline_sum"):
        v = model[k]
        if type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= MAX_EVENTS * 20:
            raise SemanticVAEError("MODEL_LOSS_INVALID")
    return model


def _sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    exp = math.exp(x)
    return exp / (1.0 + exp)


def _forward(model: Mapping, x: list[int], epsilon: list[float]) -> tuple:
    mu = [model["bias_mu"][j] + sum(a * b for a, b in zip(model["encoder_mu"][j], x))
          for j in range(LATENT)]
    lv = [max(-5.0, min(5.0, model["bias_logvar"][j]
          + sum(a * b for a, b in zip(model["encoder_logvar"][j], x))))
          for j in range(LATENT)]
    sigma = [math.exp(0.5 * v) for v in lv]
    z = [mu[j] + sigma[j] * epsilon[j] for j in range(LATENT)]
    p = [_sigmoid(model["decoder_bias"][i]
          + sum(model["decoder"][i][j] * z[j] for j in range(LATENT)))
          for i in range(DIM)]
    recon = sum(-(x[i] * math.log(max(1e-9, p[i]))
                  + (1-x[i]) * math.log(max(1e-9, 1-p[i])))
                for i in range(DIM)) / DIM
    kl = sum((mu[j] ** 2 + math.exp(lv[j]) - 1 - lv[j]) * 0.5
             for j in range(LATENT)) / LATENT
    return mu, lv, sigma, z, p, recon, kl


def _flatten(cells: list) -> list[int]:
    return [v for row in cells for cell in row for v in cell]


def _bloom_indices(context: str, identity: str) -> tuple[int, ...]:
    digest = hashlib.sha256(("semantic-vae-bloom:" + context + ":" + identity).encode()).digest()
    return tuple(int.from_bytes(digest[i:i+4], "big") % BLOOM_BITS
                 for i in (0, 4, 8, 12))


def _step(model: dict, x: list[int], fingerprint: str) -> float:
    rng = random.Random(int(fingerprint[:16], 16))
    epsilon = [rng.gauss(0, 1) for _ in range(LATENT)]
    mu, lv, sigma, z, p, reconstruction, _ = _forward(model, x, epsilon)
    grad_out = [(p[i] - x[i]) / DIM for i in range(DIM)]
    grad_z = [sum(grad_out[i] * model["decoder"][i][j]
                  for i in range(DIM)) for j in range(LATENT)]
    # Gradients use frozen decoder weights, then update both heads.
    gmu = [grad_z[j] + BETA * mu[j] / LATENT for j in range(LATENT)]
    glv = [grad_z[j] * 0.5 * sigma[j] * epsilon[j]
           + BETA * 0.5 * (math.exp(lv[j]) - 1) / LATENT
           for j in range(LATENT)]
    def updated(old: float, grad: float) -> float:
        return round(max(-4.0, min(4.0, old - LEARNING_RATE *
                     max(-1.0, min(1.0, grad)))), 10)
    for i in range(DIM):
        for j in range(LATENT):
            model["decoder"][i][j] = updated(
                model["decoder"][i][j], grad_out[i] * z[j])
        model["decoder_bias"][i] = updated(model["decoder_bias"][i], grad_out[i])
    for j in range(LATENT):
        for i in range(DIM):
            model["encoder_mu"][j][i] = updated(model["encoder_mu"][j][i], gmu[j] * x[i])
            model["encoder_logvar"][j][i] = updated(model["encoder_logvar"][j][i], glv[j] * x[i])
        model["bias_mu"][j] = updated(model["bias_mu"][j], gmu[j])
        model["bias_logvar"][j] = updated(model["bias_logvar"][j], glv[j])
    return reconstruction


def learn(snapshot: Mapping, event: Mapping, patch: Mapping, *,
          prior: Mapping | None = None, explicit_opt_in: bool = False) -> tuple[dict, str]:
    """Train on one independently reviewed sample; holdout remains untouched."""
    if explicit_opt_in is not True:
        raise SemanticVAEError("EXPLICIT_OPT_IN_REQUIRED")
    try:
        cells, _, fingerprint = _sample(snapshot, event, patch)
        model = copy.deepcopy(prior) if prior is not None else empty_model(snapshot)
        _validate(model, snapshot)
    except (SpatialConvolutionError, ValueError, TypeError, KeyError) as exc:
        raise SemanticVAEError("SOURCE_OR_MODEL_UNVERIFIED") from exc
    indices = _bloom_indices(model["context_hash"], fingerprint)
    bloom = bytearray.fromhex(model["seen_bloom"])
    if all(bloom[index // 8] & (1 << (index % 8)) for index in indices):
        return model, "REPLAY_OR_BLOOM_COLLISION_IGNORED"
    if model["trained"] + model["heldout"] >= MAX_EVENTS:
        raise SemanticVAEError("TRAINING_CAPACITY_REACHED")
    x = _flatten(cells)
    holdout = int(fingerprint[:8], 16) % 5 == 0
    if holdout:
        _, _, _, _, _, loss, kl = _forward(model, x, [0.0] * LATENT)
        model["heldout_reconstruction_sum"] += loss + BETA * kl
        model["heldout_baseline_sum"] += math.log(2)
        model["heldout"] += 1
        partition, status = "HOLDOUT", "HELDOUT_VALIDATION_ONLY"
    else:
        model["train_reconstruction_sum"] += _step(model, x, fingerprint)
        model["trained"] += 1
        partition, status = "TRAIN", "TRAINED_ON_DEVICE"
    for index in indices:
        bloom[index // 8] |= 1 << (index % 8)
    model["seen_bloom"] = bloom.hex()
    model["samples"].append({"id": fingerprint, "partition": partition, "x": x})
    if len(model["samples"]) > MAX_RETAINED:
        model["samples"].pop(0)  # Bounded corpus; learned weights and dedup persist.
    _validate(model, snapshot)
    return model, status


def advise(snapshot: Mapping, model: Mapping, patch: Mapping, *,
           from_region: str, to_region: str) -> dict:
    """Decoder outputs are never certified world geometry or a motion permit."""
    result = {"status": "ABSTAIN_UNVERIFIED", "execute_allowed": False,
              "control_permit": None, "can_add_graph_edges": False,
              "can_move_camera": False, "can_walk_sim": False,
              "proof_ceiling": PROOF}
    try:
        _context(snapshot)
        _validate(model, snapshot)
        x = _flatten(_patch(snapshot, patch, from_region, to_region))
        if snapshot.get("current_region") != from_region:
            return result
        if model["trained"] < 24 or model["heldout"] < 8:
            result["status"] = "ABSTAIN_UNCALIBRATED"
            return result
        loss = model["heldout_reconstruction_sum"] / model["heldout"]
        baseline = model["heldout_baseline_sum"] / model["heldout"]
        if loss + 0.01 >= baseline:
            result["status"] = "ABSTAIN_HOLDOUT_NO_IMPROVEMENT"
            return result
        mu, _, _, _, decoded, _, _ = _forward(model, x, [0.0] * LATENT)
        result.update(status="DECODER_RESEARCH_ADVISORY",
                      latent_mean=[round(a, 5) for a in mu],
                      decoded_channels=[round(a, 5) for a in decoded],
                      heldout_reconstruction=round(loss, 6),
                      heldout_uniform_baseline=round(baseline, 6))
    except (SpatialConvolutionError, SemanticVAEError, KeyError, TypeError,
            ValueError, OverflowError):
        return result
    return result


def _local_path(snapshot: Mapping, *, profile_id: str = "default") -> Path:
    """Canonical local checkpoint; preserve v1 default path without migration.

    Named installation profiles share neither training samples nor purge paths,
    even when viewing exactly the same Sims world/game scope.
    """
    from bootstrap import paths
    from betterinstincts.installation_profiles import PROFILE_ID
    if not isinstance(profile_id, str) or not PROFILE_ID.fullmatch(profile_id):
        raise SemanticVAEError("INSTALLATION_PROFILE_ID_INVALID")
    base = paths()["use"].parent
    root = base / "runtime" / "semantic-vae"
    for directory in (base, root.parent, root):
        if directory.is_symlink():
            raise SemanticVAEError("LOCAL_STORAGE_SYMLINK_DENIED")
    world_key = context_hash(snapshot)
    if profile_id == "default":
        checkpoint_key = world_key  # Existing local v1 users keep their data.
    else:
        checkpoint_key = hashlib.sha256(
            ("semantic-vae-profile/v1:" + profile_id + ":" + world_key).encode()
        ).hexdigest()
    return root / (checkpoint_key + ".json")


def load_local_model(snapshot: Mapping, *, profile_id: str = "default") -> dict:
    try:
        _context(snapshot)
        path = _local_path(snapshot, profile_id=profile_id)
        if path.is_symlink():
            raise SemanticVAEError("LOCAL_MODEL_SYMLINK_DENIED")
        if not path.exists():
            return empty_model(snapshot)
        if not path.is_file() or path.stat().st_size > MAX_BYTES:
            raise SemanticVAEError("LOCAL_MODEL_UNSAFE")
        return _validate(json.loads(path.read_text(encoding="utf-8")), snapshot)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError,
            SpatialConvolutionError) as exc:
        raise SemanticVAEError("LOCAL_MODEL_INVALID") from exc


def record_local_sample(snapshot: Mapping, event: Mapping, patch: Mapping, *,
                        explicit_opt_in: bool = False,
                        profile_id: str = "default") -> dict:
    """One explicitly admitted write; local user-owned model and corpus only."""
    if explicit_opt_in is not True:
        raise SemanticVAEError("EXPLICIT_OPT_IN_REQUIRED")
    try:
        _sample(snapshot, event, patch)  # Validate before even creating a directory.
        path = _local_path(snapshot, profile_id=profile_id)
    except (SpatialConvolutionError, KeyError, TypeError, ValueError) as exc:
        raise SemanticVAEError("SOURCE_UNVERIFIED") from exc
    root = path.parent
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    if root.is_symlink() or not root.is_dir() or path.is_symlink():
        raise SemanticVAEError("LOCAL_STORAGE_UNSAFE")
    if not path.exists() and sum(p.suffix == ".json" for p in root.iterdir()) >= MAX_PROFILES:
        raise SemanticVAEError("PROFILE_CAPACITY_REACHED")
    lock = path.with_suffix(".lock")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(lock, flags, 0o600)
    except FileExistsError as exc:
        raise SemanticVAEError("CONCURRENT_WRITER_BUSY") from exc
    temporary = None
    try:
        os.close(fd)
        old = load_local_model(snapshot, profile_id=profile_id)
        updated, state = learn(snapshot, event, patch, prior=old, explicit_opt_in=True)
        if state == "REPLAY_OR_BLOOM_COLLISION_IGNORED":
            return {"status": state, "trained": old["trained"],
                    "heldout": old["heldout"], "proof_ceiling": PROOF}
        payload = (json.dumps(updated, sort_keys=True, separators=(",", ":"),
                              allow_nan=False) + "\n").encode("utf-8")
        if len(payload) > MAX_BYTES:
            raise SemanticVAEError("LOCAL_STORAGE_LIMIT")
        file_descriptor, filename = tempfile.mkstemp(prefix=".semantic-vae-", dir=root)
        temporary = Path(filename)
        with os.fdopen(file_descriptor, "wb") as stream:
            os.chmod(temporary, 0o600)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if path.is_symlink():
            raise SemanticVAEError("LOCAL_MODEL_SYMLINK_DENIED")
        os.replace(temporary, path)
        temporary = None
        return {"status": state, "trained": updated["trained"],
                "heldout": updated["heldout"], "proof_ceiling": PROOF}
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def purge_local_model(snapshot: Mapping, *, explicit_confirm: bool = False,
                      profile_id: str = "default") -> dict:
    """Erase exactly one scoped local model/corpus; never touch saves or other profiles."""
    if explicit_confirm is not True:
        raise SemanticVAEError("EXPLICIT_DELETE_CONFIRM_REQUIRED")
    try:
        _context(snapshot)
        path = _local_path(snapshot, profile_id=profile_id)
        if path.is_symlink():
            raise SemanticVAEError("LOCAL_MODEL_SYMLINK_DENIED")
        if not path.exists():
            return {"status": "LOCAL_MODEL_NOT_PRESENT", "proof_ceiling": PROOF}
        if not path.is_file() or path.stat().st_size > MAX_BYTES:
            raise SemanticVAEError("LOCAL_MODEL_UNSAFE")
        lock = path.with_suffix(".lock")
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(lock, flags, 0o600)
        except FileExistsError as exc:
            raise SemanticVAEError("CONCURRENT_WRITER_BUSY") from exc
        try:
            os.close(fd)
            if path.is_symlink():
                raise SemanticVAEError("LOCAL_MODEL_SYMLINK_DENIED")
            path.unlink()
        finally:
            lock.unlink(missing_ok=True)
        return {"status": "LOCAL_MODEL_PURGED", "proof_ceiling": PROOF}
    except (SpatialConvolutionError, ValueError, KeyError, TypeError) as exc:
        raise SemanticVAEError("PURGE_SCOPE_INVALID") from exc


def record_if_enabled(snapshot: Mapping, event: Mapping, patch: Mapping, *,
                      profile_id: str | None = None) -> dict:
    """Local profile opt-in adapter. No auto-sensor or training loop is installed."""
    from betterinstincts.installation_profiles import (
        InstallationProfileError, view,
    )
    try:
        selected = view(profile_id=profile_id)
        enabled = selected["settings"]["learning.semantic_vae"]
        selected_profile = selected["profile_id"]
    except (InstallationProfileError, KeyError, TypeError) as exc:
        raise SemanticVAEError("LOCAL_CONSENT_PROFILE_UNVERIFIED") from exc
    if enabled is not True:
        return {"status": "LOCAL_TRAINING_DISABLED", "execute_allowed": False,
                "proof_ceiling": PROOF}
    return record_local_sample(snapshot, event, patch, explicit_opt_in=True,
                               profile_id=selected_profile)


__all__ = ["SemanticVAEError", "SCHEMA", "PROOF", "empty_model", "learn",
           "advise", "load_local_model", "record_local_sample",
           "record_if_enabled", "purge_local_model"]
