"""World-object highlight continuity + bounded, labelled online learning.

Read-only and opt-in. Camera framing, lot boundaries and player authority remain
with their existing owners; neither classifier nor model can send input.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "world-traversal-learning.v1.json"
FRAME_SCHEMA = "betterinstincts.world-traversal.frame/v1"
MODEL_SCHEMA = "betterinstincts.world-traversal.model/v1"
PROOF = "OFFLINE_HIGHLIGHT_AND_LABELLED_OUTCOMES_NOT_LIVE_CLICK_CERT"
TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:+-]{0,95}$")


class WorldTraversalLearningError(ValueError):
    """Unsafe, unsupported or malformed candidate evidence."""


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 48_000:
        raise WorldTraversalLearningError("CONTRACT_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if (cfg.get("schema") != "betterinstincts.world-traversal-learning/v1"
            or cfg.get("boundaries", {}).get("execute_allowed_default") is not False
            or cfg.get("frames", {}).get("min_for_lock") != 2):
        raise WorldTraversalLearningError("CONTRACT_GUARD_DRIFT")
    return cfg


def _token(value: object) -> bool:
    return isinstance(value, str) and TOKEN.fullmatch(value) is not None


def _score(value: object, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
        raise WorldTraversalLearningError("INVALID_CONFIDENCE:" + label)
    return float(value)


def _rect(value: object) -> tuple[int, int, int, int] | None:
    if value is None:
        return None
    if (not isinstance(value, (tuple, list)) or len(value) != 4
            or any(type(n) is not int for n in value)):
        raise WorldTraversalLearningError("INVALID_TARGET_RECT")
    l, t, r, b = value
    if not (0 <= l < r <= 16384 and 0 <= t < b <= 16384):
        raise WorldTraversalLearningError("INVALID_TARGET_RECT")
    return l, t, r, b


def _iou(a: Sequence[int], b: Sequence[int]) -> float:
    iw = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    ih = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return iw * ih / (area_a + area_b - iw * ih)


def _frame(frame: Mapping[str, Any], target_id: str, cfg: Mapping) -> dict:
    if not isinstance(frame, Mapping) or frame.get("schema") != FRAME_SCHEMA:
        raise WorldTraversalLearningError("FRAME_SCHEMA_INVALID")
    for field in ("capture_ref", "camera_revision", "target_id"):
        if not _token(frame.get(field)):
            raise WorldTraversalLearningError("FRAME_FIELD_INVALID:" + field)
    # A real detector often reports no highlighted identity after the glow
    # disappears. Treat that as evidence to classify, not malformed input.
    highlighted_id = frame.get("highlight_target_id")
    if highlighted_id is not None and not _token(highlighted_id):
        raise WorldTraversalLearningError("FRAME_FIELD_INVALID:highlight_target_id")
    if type(frame.get("frame_index")) is not int or frame["frame_index"] < 0:
        raise WorldTraversalLearningError("FRAME_INDEX_INVALID")
    if frame.get("source") != "HOST_CAPTURE":
        raise WorldTraversalLearningError("HOST_CAPTURE_REQUIRED")
    if type(frame.get("target_visible")) is not bool or type(frame.get("occluded")) is not bool:
        raise WorldTraversalLearningError("VISIBILITY_FLAGS_REQUIRED")
    confidence = _score(frame.get("object_confidence"), "object")
    if frame.get("pointer_context") not in {"HOVERING_TARGET", "AWAY", "UNKNOWN"}:
        raise WorldTraversalLearningError("POINTER_CONTEXT_INVALID")
    box = _rect(frame.get("bbox_client"))
    cues = frame.get("highlight_cues")
    if not isinstance(cues, list) or not 1 <= len(cues) <= 4:
        raise WorldTraversalLearningError("HIGHLIGHT_CUES_REQUIRED")
    seen = set()
    accepted = []
    for cue in cues:
        if not isinstance(cue, Mapping):
            raise WorldTraversalLearningError("INVALID_CUE")
        source = cue.get("source")
        if source not in cfg["frames"]["cue_sources"] or source in seen:
            raise WorldTraversalLearningError("CUE_SOURCE_UNTRUSTED_OR_DUPLICATE")
        seen.add(source)
        if cue.get("state") not in {"PRESENT", "ABSENT", "UNKNOWN"}:
            raise WorldTraversalLearningError("INVALID_HIGHLIGHT_STATE")
        score = _score(cue.get("confidence"), "cue")
        if score >= cfg["frames"]["confidence_floor"] and cue["state"] != "UNKNOWN":
            accepted.append(cue["state"])
    state = "UNKNOWN"
    if len(accepted) >= 2:
        if all(s == "PRESENT" for s in accepted):
            state = "PRESENT"
        elif all(s == "ABSENT" for s in accepted):
            state = "ABSENT"
        else:
            state = "CONFLICT"
    return {
        "capture_ref": frame["capture_ref"], "camera_revision": frame["camera_revision"],
        "frame_index": frame["frame_index"], "target_id": frame["target_id"],
        "highlight_target_id": highlighted_id,
        "target_visible": frame["target_visible"], "occluded": frame["occluded"],
        "object_confidence": confidence, "bbox_client": box,
        "pointer_context": frame["pointer_context"], "state": state,
    }


def assess_highlight_continuity(
    *, target_id: str, frames: Sequence[Mapping[str, Any]],
    capture_ref: str, camera_revision: str | None = None,
    cfg: Mapping[str, Any] | None = None,
) -> dict:
    """Two fresh, independently supported highlight observations are required.

    The last two distinct frames must agree, with matching target/camera and
    pointer hover. Missing information yields; a single blink never proves loss.
    This is NOT a segmentation or screenshot inference engine.
    """
    cfg = cfg or load_contract()
    if not _token(target_id) or not _token(capture_ref):
        raise WorldTraversalLearningError("TARGET_IDENTITY_INVALID")
    if (not isinstance(frames, (list, tuple)) or not 1 <= len(frames) <= cfg["frames"]["max"]):
        raise WorldTraversalLearningError("FRAME_BUDGET_INVALID")
    parsed = [_frame(x, target_id, cfg) for x in frames]
    if (len({x["capture_ref"] for x in parsed}) != len(parsed)
            or any(a["frame_index"] >= b["frame_index"] for a, b in zip(parsed, parsed[1:]))):
        raise WorldTraversalLearningError("REPLAY_OR_OUT_OF_ORDER_CAPTURE")
    latest = parsed[-1]
    reason = "HIGHLIGHT_UNVERIFIED"
    if latest["capture_ref"] != capture_ref:
        reason = "HIGHLIGHT_UNVERIFIED"
    elif camera_revision is not None and latest["camera_revision"] != camera_revision:
        reason = "CAMERA_CHANGED_REACQUIRE"
    elif any(x["camera_revision"] != latest["camera_revision"] for x in parsed):
        reason = "CAMERA_CHANGED_REACQUIRE"
    elif any(x["target_id"] != target_id or (
            x["highlight_target_id"] is not None
            and x["highlight_target_id"] != target_id) for x in parsed):
        reason = "TARGET_IDENTITY_CHANGED"
    elif any(x["state"] == "PRESENT" and x["highlight_target_id"] is None
             for x in parsed[-2:]):
        reason = "HIGHLIGHT_UNVERIFIED"
    elif any(x["pointer_context"] != "HOVERING_TARGET" for x in parsed[-2:]):
        reason = "HIGHLIGHT_NOT_EXPECTED"
    elif any(x["occluded"] for x in parsed[-2:]):
        reason = "TARGET_OCCLUDED"
    elif any(not x["target_visible"] for x in parsed[-2:]):
        reason = "TARGET_LOST"
    elif any(x["object_confidence"] < cfg["frames"]["confidence_floor"] for x in parsed[-2:]):
        reason = "HIGHLIGHT_UNVERIFIED"
    elif any(x["state"] == "CONFLICT" for x in parsed[-2:]):
        reason = "HIGHLIGHT_AMBIGUOUS"
    elif len(parsed) < cfg["frames"]["min_for_lock"]:
        reason = "HIGHLIGHT_UNVERIFIED"
    elif (parsed[-1]["bbox_client"] is None or parsed[-2]["bbox_client"] is None):
        reason = "HIGHLIGHT_UNVERIFIED"
    elif _iou(parsed[-2]["bbox_client"], parsed[-1]["bbox_client"]) < 0.20:
        reason = "TARGET_TRACK_DRIFT"
    elif parsed[-2]["state"] == parsed[-1]["state"] == "PRESENT":
        reason = "LOCKED"
    elif parsed[-2]["state"] == parsed[-1]["state"] == "ABSENT":
        reason = "HIGHLIGHT_LOST"
    elif "UNKNOWN" in (parsed[-2]["state"], parsed[-1]["state"]):
        reason = "HIGHLIGHT_UNVERIFIED"
    else:
        reason = "HIGHLIGHT_TRANSIENT"
    return {
        "schema": "betterinstincts.world-traversal.highlight-result/v1",
        "target_id": target_id, "capture_ref": capture_ref,
        "camera_revision": latest["camera_revision"], "state": reason,
        "highlight_locked": reason == "LOCKED",
        "click_ready": False, "execute_allowed": False,
        "next": ("INDEPENDENT_FRAMING_AND_LOT_PLAYER_ADMISSION"
                 if reason == "LOCKED" else "STOP_AND_REACQUIRE_FRESH_TARGET_HIGHLIGHT"),
        "evaluated_frames": len(parsed), "proof_ceiling": PROOF,
    }


def empty_model() -> dict:
    return {"schema": MODEL_SCHEMA, "contexts": {}, "seen_attempts": []}


def _context(sample: Mapping) -> str:
    # No household, personal Sim names, coordinates or screenshot refs in model.
    keys = ("game_version", "target_kind", "scene_id", "view_kind",
            "zoom_bin", "strategy")
    if not isinstance(sample, Mapping) or any(not _token(sample.get(k)) for k in keys):
        raise WorldTraversalLearningError("LEARNING_CONTEXT_INVALID")
    return "|".join(sample[k] for k in keys)


def _check_model(model: Mapping, cfg: Mapping) -> dict:
    if (not isinstance(model, Mapping) or model.get("schema") != MODEL_SCHEMA
            or not isinstance(model.get("contexts"), Mapping)
            or len(model["contexts"]) > cfg["learning"]["max_contexts"]):
        raise WorldTraversalLearningError("MODEL_SCHEMA_OR_BUDGET_INVALID")
    cells = {}
    for key, raw in model["contexts"].items():
        if (not isinstance(key, str) or len(key) > 640 or len(key.split("|")) != 6
                or not all(_token(x) for x in key.split("|"))
                or not isinstance(raw, Mapping)
                or set(raw) != {"successes", "failures"}):
            raise WorldTraversalLearningError("MODEL_CELL_INVALID")
        yes, no = raw["successes"], raw["failures"]
        if (type(yes) is not int or type(no) is not int
                or min(yes, no) < 0 or yes + no > cfg["learning"]["max_count_per_context"]):
            raise WorldTraversalLearningError("MODEL_COUNT_INVALID")
        cells[key] = {"successes": yes, "failures": no}
    # Model history and counts are inseparable. An old snapshot with counts
    # but no evidence ledger cannot be upgraded by pretending it is unique.
    raw_seen = model.get("seen_attempts")
    if raw_seen is None:
        if any(c["successes"] or c["failures"] for c in cells.values()):
            raise WorldTraversalLearningError("LEGACY_MODEL_MISSING_REPLAY_PROOF")
        raw_seen = []
    limit = cfg["learning"]["max_seen_attempts"]
    if (not isinstance(raw_seen, list) or len(raw_seen) > limit
            or any(not isinstance(x, str)
                   or re.fullmatch(r"[0-9a-f]{40}", x) is None
                   for x in raw_seen)
            or len(set(raw_seen)) != len(raw_seen)):
        raise WorldTraversalLearningError("MODEL_REPLAY_HISTORY_INVALID")
    if sum(c["successes"] + c["failures"] for c in cells.values()) != len(raw_seen):
        raise WorldTraversalLearningError("MODEL_REPLAY_HISTORY_COUNT_MISMATCH")
    return cells, set(raw_seen)


def _attempt_fingerprint(sample: Mapping[str, Any]) -> str:
    """Opaque, portable attempt identity; never persist raw captures or Sims."""
    # A single pre-action frame cannot be credited repeatedly, even if a caller
    # relabels the strategy, outcome, target or post-action frame on replay.
    identity = [sample["game_version"], sample["before_capture_ref"]]
    raw = json.dumps(identity, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("ascii")).hexdigest()[:40]


def _observed_outcome(sample: Mapping, cfg: Mapping) -> bool | None:
    """Only independently observed post-click outcomes can supply a label."""
    if not isinstance(sample, Mapping):
        raise WorldTraversalLearningError("SAMPLE_INVALID")
    _context(sample)
    if sample.get("player_interrupted") is not False:
        return None
    if (sample.get("evidence_source") not in cfg["learning"]["allow_outcome_sources"]
            or not _token(sample.get("target_id"))
            or not _token(sample.get("before_capture_ref"))
            or not _token(sample.get("after_capture_ref"))
            or sample["before_capture_ref"] == sample["after_capture_ref"]):
        return None
    outcome = sample.get("outcome")
    result = sample.get("observed_result")
    observed = sample.get("observed_target_id")
    if outcome == "SUCCESS" and result == "TARGET_INTERACTION" and observed == sample["target_id"]:
        return True
    if outcome == "FAILURE" and result in {"NO_RESPONSE", "WRONG_OBJECT"}:
        if result == "WRONG_OBJECT" and (not _token(observed) or observed == sample["target_id"]):
            return None
        return False
    return None


def learn_observed_attempts(
    model: Mapping, attempts: Sequence[Mapping], *,
    cfg: Mapping[str, Any] | None = None,
) -> dict:
    """Return new model; caller explicitly controls any persistence."""
    cfg = cfg or load_contract()
    cells, seen = _check_model(model, cfg)
    if not isinstance(attempts, (list, tuple)) or not 1 <= len(attempts) <= cfg["learning"]["max_examples_per_update"]:
        raise WorldTraversalLearningError("LEARNING_BATCH_BUDGET_INVALID")
    accepted = 0
    abstained = 0
    replayed = 0
    for attempt in attempts:
        key = _context(attempt)
        label = _observed_outcome(attempt, cfg)
        if label is None:
            abstained += 1
            continue
        fingerprint = _attempt_fingerprint(attempt)
        if fingerprint in seen:
            replayed += 1
            abstained += 1
            continue
        if len(seen) >= cfg["learning"]["max_seen_attempts"]:
            raise WorldTraversalLearningError("MODEL_REPLAY_HISTORY_BUDGET_EXCEEDED")
        if key not in cells and len(cells) == cfg["learning"]["max_contexts"]:
            raise WorldTraversalLearningError("MODEL_CONTEXT_BUDGET_EXCEEDED")
        cell = cells.setdefault(key, {"successes": 0, "failures": 0})
        if cell["successes"] + cell["failures"] >= cfg["learning"]["max_count_per_context"]:
            raise WorldTraversalLearningError("MODEL_SAMPLE_BUDGET_EXCEEDED")
        cell["successes" if label else "failures"] += 1
        seen.add(fingerprint)
        accepted += 1
    return {
        "schema": "betterinstincts.world-traversal.training/v1",
        "model": {"schema": MODEL_SCHEMA, "contexts": cells,
                  "seen_attempts": sorted(seen)},
        "accepted": accepted, "abstained": abstained, "replayed": replayed,
        "execute_allowed": False, "proof_ceiling": PROOF,
    }


def rank_strategies(model: Mapping, contexts: Sequence[Mapping], *,
                    cfg: Mapping[str, Any] | None = None) -> dict:
    """Conservative empirical-Bayes ranking; never proposes action authority."""
    cfg = cfg or load_contract()
    cells, _ = _check_model(model, cfg)
    if not isinstance(contexts, (list, tuple)) or not 1 <= len(contexts) <= 16:
        raise WorldTraversalLearningError("RANK_BUDGET_INVALID")
    ranked = []
    for context in contexts:
        key = _context(context)
        counts = cells.get(key, {"successes": 0, "failures": 0})
        n = counts["successes"] + counts["failures"]
        a = counts["successes"] + cfg["learning"]["prior_alpha"]
        b = counts["failures"] + cfg["learning"]["prior_beta"]
        mean = a / (a + b)
        variance = a * b / ((a + b) ** 2 * (a + b + 1))
        lower = max(0.0, mean - cfg["learning"]["confidence_bound_z"] * math.sqrt(variance))
        ranked.append({
            "context": key, "samples": n, "posterior_mean": round(mean, 6),
            "conservative_lower_bound": round(lower, 6),
            "eligible": n >= cfg["learning"]["min_examples_to_rank"],
        })
    ranked.sort(key=lambda x: (not x["eligible"], -x["conservative_lower_bound"], x["context"]))
    eligible = [x for x in ranked if x["eligible"]]
    return {
        "schema": "betterinstincts.world-traversal.ranking/v1",
        "state": "ADVISORY_RANKING" if eligible else "ABSTAIN_INSUFFICIENT_LABELS",
        "recommended_context": eligible[0]["context"] if eligible else None,
        "rankings": ranked, "execute_allowed": False, "proof_ceiling": PROOF,
    }


def evaluate_holdout(model: Mapping, attempts: Sequence[Mapping], *,
                     cfg: Mapping[str, Any] | None = None) -> dict:
    """Held-out Brier score against 0.5 baseline; no training on holdout."""
    cfg = cfg or load_contract()
    cells, trained = _check_model(model, cfg)
    if not isinstance(attempts, (list, tuple)) or not 1 <= len(attempts) <= 256:
        raise WorldTraversalLearningError("HOLDOUT_BUDGET_INVALID")
    evaluated = 0
    abstained = 0
    replayed = 0
    holdout_seen: set[str] = set()
    error = 0.0
    for sample in attempts:
        key = _context(sample)
        label = _observed_outcome(sample, cfg)
        cell = cells.get(key)
        if label is None or cell is None or cell["successes"] + cell["failures"] < cfg["learning"]["min_examples_to_rank"]:
            abstained += 1
            continue
        fingerprint = _attempt_fingerprint(sample)
        if fingerprint in trained or fingerprint in holdout_seen:
            replayed += 1
            abstained += 1
            continue
        holdout_seen.add(fingerprint)
        pred = (cell["successes"] + 1) / (cell["successes"] + cell["failures"] + 2)
        error += (pred - int(label)) ** 2
        evaluated += 1
    return {
        "schema": "betterinstincts.world-traversal.holdout/v1",
        "state": "EVALUATED" if evaluated else "NOT_EVALUABLE",
        "total": len(attempts), "evaluated": evaluated, "abstained": abstained,
        "coverage": round(evaluated / len(attempts), 6),
        "replayed": replayed,
        "brier": round(error / evaluated, 6) if evaluated else None,
        "baseline_brier": 0.25 if evaluated else None,
        "execute_allowed": False, "proof_ceiling": PROOF,
    }
