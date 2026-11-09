"""Opt-in contextual click learning and bounded camera-signal interpretation.

Offline, pure and advisory: no mouse hooks, native input, game mutation,
network listener, scheduled polling or automatic target calibration.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Mapping, Any

from betterinstincts.scenes import load_catalog
from betterinstincts.ui_chrome import UIChromeError, resolve_target, hotkeys_for_mode
from betterinstincts.ui_microsystems import UIMicrosystemError, resolve_action

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "click-learning.v1.json"
SCHEMA = "betterinstincts.click-learning.state/v1"
EVENT_SCHEMA = "betterinstincts.click-learning.event/v1"
TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")
PATCH = re.compile(r"^[0-9]+(?:\.[0-9]+){3}$")
FIELDS = {
    "schema", "event_id", "at_ms", "kind", "actor", "source",
    "game_version", "mode", "scene_id", "profile", "ui_revision",
    "panel_id", "target_id", "target_kind", "interaction_id", "result",
    "geometry", "camera_event", "evidence_sources", "evidence_ref",
    "opt_in", "operator_reviewed",
}
NEGATIVE_CAMERA = {"EDGE_PAN", "OVER_ZOOM", "LOST_FRAMING"}
POSITIVE_CAMERA = {"REFOCUSED", "BOUNDED_ZOOM_IN"}


class ClickLearningError(ValueError):
    """Invalid observational evidence or exhausted bounded model."""


def contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 48000:
        raise ClickLearningError("CLICK_LEARNING_CONTRACT_UNSAFE")
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ClickLearningError("CLICK_LEARNING_JSON_INVALID") from exc
    if (cfg.get("schema") != "betterinstincts.click-learning/v1"
            or cfg.get("policy") != "VERIFIED_OUTCOME_FEEDBACK_NOT_GEOMETRY_AS_SUCCESS"
            or cfg.get("opt_in_default") is not False
            or cfg.get("execute_allowed_default") is not False
            or cfg.get("mapping", {}).get("never_auto_promote") is not True
            or cfg.get("mapping", {}).get("never_execute_from_statistics") is not True
            or set(cfg.get("event", {}).get("all_fields") or []) != FIELDS
            or cfg.get("learning", {}).get("algorithm") != "EXPONENTIALLY_DISCOUNTED_BETA_BERNOULLI"):
        raise ClickLearningError("CLICK_LEARNING_POLICY_UNSAFE")
    decay = cfg["learning"].get("evidence_decay")
    if type(decay) is not float or not 0.9 <= decay < 1:
        raise ClickLearningError("INVALID_EVIDENCE_DECAY")
    return cfg


def empty_state() -> dict:
    return {
        "schema": SCHEMA, "revision": 0, "last_ms": -1,
        "seen_event_ids": [], "recent": [], "targets": {}, "candidates": {},
    }


def _token(value: Any, field: str) -> str:
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise ClickLearningError("INVALID_" + field.upper())
    return value


def _bounded_state(state: Mapping, cfg: dict) -> None:
    if (not isinstance(state, Mapping)
            or set(state) != {"schema", "revision", "last_ms", "seen_event_ids",
                             "recent", "targets", "candidates"}
            or state.get("schema") != SCHEMA
            or type(state.get("revision")) is not int or state["revision"] < 0
            or type(state.get("last_ms")) is not int or state["last_ms"] < -1):
        raise ClickLearningError("CLICK_STATE_INVALID")
    lim = cfg["limits"]
    if (not isinstance(state["seen_event_ids"], list)
            or len(state["seen_event_ids"]) > lim["max_seen_ids"]
            or any(not isinstance(x, str) or not TOKEN.fullmatch(x) for x in state["seen_event_ids"])
            or len(set(state["seen_event_ids"])) != len(state["seen_event_ids"])
            or not isinstance(state["recent"], list)
            or len(state["recent"]) > lim["max_recent_events"]
            or not isinstance(state["targets"], dict)
            or len(state["targets"]) > lim["max_target_contexts"]
            or not isinstance(state["candidates"], dict)
            or len(state["candidates"]) > lim["max_candidate_targets"]):
        raise ClickLearningError("CLICK_STATE_BUDGET_EXCEEDED")
    for key, row in state["targets"].items():
        if not isinstance(key, str) or not isinstance(row, dict):
            raise ClickLearningError("CLICK_TARGET_MODEL_INVALID")
        if set(row) != {"positive", "negative", "unverified", "alpha", "beta", "mapping_status"}:
            raise ClickLearningError("CLICK_TARGET_MODEL_FIELDS_INVALID")
        for k in ("positive", "negative", "unverified"):
            if type(row[k]) is not int or row[k] < 0:
                raise ClickLearningError("CLICK_TARGET_COUNT_INVALID")
        for k in ("alpha", "beta"):
            if type(row[k]) not in (int, float) or not 1 <= row[k] <= 256 or not math.isfinite(row[k]):
                raise ClickLearningError("CLICK_POSTERIOR_INVALID")
        if row["mapping_status"] not in ("CATALOGUED_UNVERIFIED_GAMEPLAY", "CANDIDATE_REQUIRES_EXACT_BUILD_CALIBRATION"):
            raise ClickLearningError("CLICK_MAPPING_STATUS_INVALID")
    try:
        encoded = json.dumps(state, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise ClickLearningError("CLICK_STATE_NOT_SERIALIZABLE") from exc
    if len(encoded) > lim["max_state_bytes"]:
        raise ClickLearningError("CLICK_STATE_BUDGET_EXCEEDED")


def _validate_event(raw: Mapping, cfg: dict) -> dict:
    if not isinstance(raw, Mapping) or set(raw) != FIELDS or raw.get("schema") != EVENT_SCHEMA:
        raise ClickLearningError("CLICK_EVENT_FIELDS_INVALID")
    event = dict(raw)
    if (not isinstance(event["event_id"], str)
            or not 3 <= len(event["event_id"]) <= cfg["limits"]["max_event_id_chars"]):
        raise ClickLearningError("EVENT_ID_INVALID")
    _token(event["event_id"], "event_id")
    if type(event["at_ms"]) is not int or event["at_ms"] < 0:
        raise ClickLearningError("EVENT_TIME_INVALID")
    if event["opt_in"] is not True or type(event["operator_reviewed"]) is not bool:
        raise ClickLearningError("EXPLICIT_OBSERVATION_OPT_IN_REQUIRED")
    for field, choices in (
        ("kind", "kinds"), ("actor", "actors"), ("source", "sources"),
        ("mode", "modes"), ("target_kind", "target_kinds"),
        ("result", "results"), ("geometry", "geometry"),
        ("camera_event", "camera_events"),
    ):
        if event[field] not in cfg["event"][choices]:
            raise ClickLearningError("INVALID_EVENT_" + field.upper())
    if not isinstance(event["game_version"], str) or not PATCH.fullmatch(event["game_version"]):
        raise ClickLearningError("EXACT_GAME_PATCH_REQUIRED")
    scene = load_catalog()
    if event["game_version"] != scene["game_version"] or event["scene_id"] not in {s["id"] for s in scene["scenes"]}:
        raise ClickLearningError("UNRECOGNIZED_GAME_SCENE_OR_PATCH")
    for k in ("target_id", "profile", "ui_revision", "interaction_id", "evidence_ref"):
        _token(event[k], k)
    if event["panel_id"] is not None:
        _token(event["panel_id"], "panel_id")
    if len(event["evidence_ref"]) > cfg["limits"]["max_evidence_ref_chars"]:
        raise ClickLearningError("EVIDENCE_REF_TOO_LONG")
    sources = event["evidence_sources"]
    if (not isinstance(sources, list) or not 1 <= len(sources) <= 2
            or any(x not in cfg["event"]["evidence_sources"] for x in sources)
            or len(set(sources)) != len(sources)):
        raise ClickLearningError("EVIDENCE_SOURCES_INVALID")
    if event["operator_reviewed"] and "OPERATOR" not in sources:
        raise ClickLearningError("OPERATOR_REVIEW_UNPROVEN")
    if event["kind"] == "TARGET_DISCOVERY" and (
        event["result"] != "UNKNOWN" or event["geometry"] != "UNKNOWN"
        or event["camera_event"] != "NONE"
    ):
        raise ClickLearningError("DISCOVERY_IS_NOT_AN_OUTCOME")
    if event["kind"] == "CAMERA_CONTEXT" and (
        event["target_kind"] != "CAMERA" or event["target_id"] != "camera.frame"
        or event["panel_id"] is not None or event["camera_event"] == "NONE"
    ):
        raise ClickLearningError("CAMERA_CONTEXT_INVALID")
    if event["target_kind"] == "PANEL" and event["panel_id"] is None:
        raise ClickLearningError("PANEL_CONTEXT_REQUIRED")
    return event


def _map_status(event: dict, cfg: dict) -> str:
    status = cfg["mapping"]["discovery_status"]
    if event["target_kind"] == "PANEL":
        try:
            resolve_action(event["panel_id"], event["target_id"], mode=event["mode"])
            return cfg["mapping"]["known_status"]
        except UIMicrosystemError:
            return status
    if event["target_kind"] == "CHROME":
        try:
            resolve_target(event["target_id"], mode=event["mode"], profile=event["profile"])
            return cfg["mapping"]["known_status"]
        except UIChromeError:
            return status
    if event["target_kind"] == "CAMERA" and event["target_id"] == "camera.frame":
        return cfg["mapping"]["known_status"]
    return status


def _label(event: dict) -> tuple[str, str]:
    # Geometry alone cannot establish success; each outcome needs independent
    # postcondition evidence. An intentional player camera move is not bad.
    if event["kind"] == "TARGET_DISCOVERY":
        return "UNVERIFIED", "DISCOVERY_ONLY"
    if len(event["evidence_sources"]) < 2:
        return "UNVERIFIED", "INDEPENDENT_POSTCONDITION_EVIDENCE_REQUIRED"
    if event["kind"] == "CAMERA_CONTEXT":
        if event["actor"] == "USER":
            return "UNVERIFIED", "PLAYER_CAMERA_CHOICE_NOT_ERROR"
        if event["result"] == "UNINTENDED" and event["camera_event"] in NEGATIVE_CAMERA:
            return "NEGATIVE", event["camera_event"]
        if event["result"] == "INTENDED" and event["camera_event"] in POSITIVE_CAMERA:
            return "POSITIVE", "RECOVERED_CAMERA_CONTEXT"
        return "UNVERIFIED", "CAMERA_RESULT_UNPROVEN"
    if event["camera_event"] in NEGATIVE_CAMERA:
        if event["actor"] in {"AGENT", "HOST"} and event["result"] == "UNINTENDED":
            return "NEGATIVE", event["camera_event"]
        return "UNVERIFIED", "CONTRADICTORY_CAMERA_CONTEXT"
    if event["result"] == "UNINTENDED":
        return "NEGATIVE", ("GEOMETRIC_MISS" if event["geometry"] in {"MISS", "NEAR_MISS"}
                            else "WRONG_POSTCONDITION")
    if event["result"] == "INTENDED" and event["geometry"] in {"HIT", "NEAR_MISS"}:
        return "POSITIVE", ("INTENDED_EFFECT" if event["geometry"] == "HIT"
                            else "INTENDED_EFFECT_RECALIBRATE_GEOMETRY")
    return "UNVERIFIED", "POSTCONDITION_OR_GEOMETRY_UNPROVEN"


def _context_key(event: dict) -> str:
    return "|".join((
        event["game_version"], event["mode"], event["scene_id"],
        event["profile"], event["ui_revision"],
        event["target_kind"], event["panel_id"] or "-", event["target_id"],
    ))


def observe(state: Mapping, supplied_event: Mapping, *, cfg: dict | None = None) -> tuple[dict, dict]:
    """One idempotent, opt-in observation; never a control permit or click."""
    cfg = cfg or contract()
    _bounded_state(state, cfg)
    event = _validate_event(supplied_event, cfg)
    if event["event_id"] in state["seen_event_ids"]:
        return dict(state), {"state": "DUPLICATE_IGNORED", "event_id": event["event_id"],
                             "execute_allowed": False, "control_permit": None}
    if event["at_ms"] < state["last_ms"]:
        raise ClickLearningError("OUT_OF_ORDER_CLICK_EVENT")
    key = _context_key(event)
    label, reason = _label(event)
    mapping_status = _map_status(event, cfg)
    rows = {k: dict(v) for k, v in state["targets"].items()}
    row = rows.get(key, {"positive": 0, "negative": 0, "unverified": 0,
                         "alpha": 1.0, "beta": 1.0, "mapping_status": mapping_status})
    if key not in rows and len(rows) >= cfg["limits"]["max_target_contexts"]:
        raise ClickLearningError("TARGET_CONTEXT_BUDGET_REACHED")
    row["mapping_status"] = mapping_status
    row[label.lower()] += 1
    if label in {"POSITIVE", "NEGATIVE"}:
        decay = cfg["learning"]["evidence_decay"]
        row["alpha"] = round(1 + (row["alpha"] - 1) * decay + (1 if label == "POSITIVE" else 0), 6)
        row["beta"] = round(1 + (row["beta"] - 1) * decay + (1 if label == "NEGATIVE" else 0), 6)
    rows[key] = row
    candidates = dict(state["candidates"])
    if mapping_status == cfg["mapping"]["discovery_status"]:
        if key not in candidates and len(candidates) >= cfg["limits"]["max_candidate_targets"]:
            raise ClickLearningError("DISCOVERY_CANDIDATE_BUDGET_REACHED")
        candidates[key] = {"status": mapping_status, "last_evidence_ref": event["evidence_ref"]}
    recent = [*state["recent"], {"event_id": event["event_id"], "at_ms": event["at_ms"],
                                 "context": key, "label": label, "reason": reason}]
    seen = [*state["seen_event_ids"], event["event_id"]]
    updated = {
        "schema": SCHEMA, "revision": state["revision"] + 1,
        "last_ms": event["at_ms"],
        "seen_event_ids": seen[-cfg["limits"]["max_seen_ids"]:],
        "recent": recent[-cfg["limits"]["max_recent_events"]:],
        "targets": rows, "candidates": candidates,
    }
    _bounded_state(updated, cfg)
    return updated, {
        "state": "OBSERVED_NOT_EXECUTED", "event_id": event["event_id"],
        "context": key, "label": label, "reason": reason,
        "mapping_status": mapping_status,
        "posterior_mean": round(row["alpha"] / (row["alpha"] + row["beta"]), 6),
        "execute_allowed": False, "control_permit": None,
        "proof_ceiling": cfg["proof_ceiling"],
    }


def evaluate(state: Mapping, *, cfg: dict | None = None) -> dict:
    """Patch-scoped Beta model: meaningful uncertainty, no click permission."""
    cfg = cfg or contract()
    _bounded_state(state, cfg)
    results = []
    for key, row in sorted(state["targets"].items()):
        a, b = float(row["alpha"]), float(row["beta"])
        mean = a / (a+b)
        sd = math.sqrt(a*b / ((a+b)**2 * (a+b+1)))
        n = row["positive"] + row["negative"]
        disposition = "MORE_VERIFIED_EXAMPLES"
        if n >= cfg["learning"]["minimum_reviewed_trials_for_signal"]:
            disposition = "REVIEW_FAILED_TARGETING" if mean < 0.5 else "PROMISING_BUT_REQUIRES_CALIBRATION"
        results.append({
            "context": key, "mapping_status": row["mapping_status"],
            "positive": row["positive"], "negative": row["negative"],
            "unverified": row["unverified"], "verified_trials": n,
            "posterior_mean": round(mean, 6),
            "two_sd_range_heuristic": [round(max(0., mean-2*sd), 6),
                                       round(min(1., mean+2*sd), 6)],
            "recommendation": disposition, "execute_allowed": False,
        })
    return {
        "schema": "betterinstincts.click-learning.evaluation/v1",
        "revision": state["revision"], "targets": results,
        "candidate_contexts": sorted(state["candidates"]),
        "execute_allowed": False, "control_permit": None,
        "proof_ceiling": cfg["proof_ceiling"],
    }


def camera_poll_delta(before: Mapping, after: Mapping) -> dict:
    """Interpret two supplied bounded game snapshots; never start a poller.

    A camera delta alone is a *candidate*, not a negative learning label.
    Host adapters still need opt-in, independent outcome evidence and intent.
    """
    fields = {"game_version", "scene_id", "camera_revision", "cursor_zone",
              "zoom_band", "target_framed", "at_ms"}
    if not isinstance(before, Mapping) or not isinstance(after, Mapping) or (
            set(before) != fields or set(after) != fields):
        raise ClickLearningError("CAMERA_POLL_FIELDS_REQUIRED")
    for snap in (before, after):
        if (not isinstance(snap["game_version"], str)
                or not PATCH.fullmatch(snap["game_version"])
                or not isinstance(snap["scene_id"], str)
                or not TOKEN.fullmatch(snap["camera_revision"])
                or snap["cursor_zone"] not in {"INTERIOR", "EDGE"}
                or snap["zoom_band"] not in {"CLOSE", "NORMAL", "WIDE", "EXTREME"}
                or type(snap["target_framed"]) is not bool
                or type(snap["at_ms"]) is not int or snap["at_ms"] < 0):
            raise ClickLearningError("CAMERA_POLL_INVALID")
    if (after["at_ms"] < before["at_ms"]
            or after["game_version"] != before["game_version"]
            or after["scene_id"] != before["scene_id"]):
        return {"state": "REOBSERVE", "signals": [], "reason": "CAMERA_FRAME_CONTEXT_CHANGED",
                "execute_allowed": False}
    signals = []
    if before["target_framed"] and not after["target_framed"]:
        signals.append("LOST_FRAMING")
    if before["zoom_band"] in {"NORMAL", "CLOSE"} and after["zoom_band"] in {"WIDE", "EXTREME"}:
        signals.append("OVER_ZOOM")
    if after["cursor_zone"] == "EDGE" and before["camera_revision"] != after["camera_revision"]:
        signals.append("EDGE_PAN")
    return {"state": "CANDIDATE_CAMERA_SIGNALS" if signals else "NO_CAMERA_ANOMALY",
            "signals": signals, "execute_allowed": False,
            "proof_ceiling": "POLL_DELTA_CANDIDATES_NOT_VERIFIED_CAUSALITY"}


def recovery_advice(event: Mapping, *, focus: str = "SIM") -> dict:
    """Offer safe steps reusing canonical camera/chrome intents, never effects."""
    cfg = contract()
    e = _validate_event(event, cfg)
    label, reason = _label(e)
    if focus not in {"SIM", "LOT", "NONE"}:
        raise ClickLearningError("UNKNOWN_CAMERA_FOCUS")
    steps = []
    if label == "NEGATIVE" and e["camera_event"] in NEGATIVE_CAMERA:
        steps.append({"intent": "SAFE_REST", "owner": "betterinstincts.camera_traverse"})
        if e["mode"] == "LIVE" and focus != "NONE":
            hotkey_id = "CENTER_ACTIVE_SIM" if focus == "SIM" else "CENTER_CURRENT_LOT"
            hotkey = next((x for x in hotkeys_for_mode("LIVE") if x["id"] == hotkey_id), None)
            if hotkey is None:
                raise ClickLearningError("CANONICAL_CAMERA_HOTKEY_MISSING")
            steps.append({"intent": hotkey_id, "chord": list(hotkey["chord"]),
                          "owner": "betterinstincts.sim_camera"})
        if e["camera_event"] == "OVER_ZOOM":
            steps.append({"intent": "HOST_OBSERVED_BOUNDED_ZOOM_IN",
                          "owner": "betterinstincts.camera_traverse",
                          "key_binding": "UNVERIFIED_DO_NOT_GUESS"})
        steps.append({"intent": "CAPTURE_OBSERVE_REDETECT_TARGET",
                      "owner": "betterinstincts.screen_atlas"})
    return {"state": "ADVISORY_ONLY", "reason": reason, "label": label,
            "steps": steps, "execute_allowed": False, "control_permit": None,
            "proof_ceiling": cfg["proof_ceiling"]}
