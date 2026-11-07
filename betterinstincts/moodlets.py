"""Moodlet / emotion evaluation for host call stacks (P95).

Observations must be supplied (operator or future sensor). This module never
claims screenshot vision classification or a Sims API.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "moodlets.v1.json"
SIX = frozenset({"hunger", "bladder", "energy", "hygiene", "fun", "social"})


class MoodletError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 128000:
        raise MoodletError("UNSAFE_MOODLET_CONTRACT")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.moodlets/v1":
        raise MoodletError("INVALID_MOODLET_SCHEMA")
    return data


def _norm_token(raw: str) -> str:
    return raw.strip().lower().replace(" ", "_").replace("-", "_")


def _resolve_moodlet(token: str, catalog: Mapping[str, dict]) -> Optional[str]:
    key = _norm_token(token)
    if key in catalog:
        return key
    for mid, row in catalog.items():
        aliases = {_norm_token(a) for a in row.get("aliases", [])}
        if key in aliases or key == _norm_token(mid):
            return mid
    return None


def _resolve_emotion(token: Optional[str], emotions: Mapping[str, dict]) -> str:
    if not token:
        return "UNKNOWN"
    key = token.strip().upper().replace(" ", "_").replace("-", "_")
    if key in emotions:
        return key
    # Soft match common HUD strings like "Very Angry"
    compact = key.replace("_", "")
    for name in emotions:
        if name.replace("_", "") == compact:
            return name
    return "UNKNOWN"


def evaluate_moodlets(
    *,
    emotion: Optional[str] = None,
    moodlets: Sequence[str] = (),
    needs: Optional[Mapping[str, float]] = None,
    outdoor_social_prefix: bool = False,
    indoor_capacity_observed: bool = False,
    event_active: bool = False,
    capture_ref: str = "capture:moodlets",
) -> dict:
    """Score supplied emotion + moodlet strip into host routing hints."""
    cfg = load_contract()
    catalog = cfg["moodlets"]
    emotions = cfg["emotions"]
    if len(moodlets) > 16:
        raise MoodletError("TOO_MANY_MOODLETS")

    if emotion is None and not moodlets:
        return {
            "schema": "betterinstincts.moodlet-result/v1",
            "state": "SENSOR_NOT_SUPPLIED",
            "emotion": None,
            "moodlets": [],
            "need_pressure": [],
            "relief": [],
            "findings": ["MOODLETS_NOT_OBSERVED"],
            "gate": None,
            "disposition": "EMULATE",
            "social_routing_bias": "NEUTRAL",
            "capture_ref": capture_ref,
            "proof_ceiling": cfg["proof_ceiling"],
        }

    emotion_id = _resolve_emotion(emotion, emotions)
    if emotion_id == "UNKNOWN" and moodlets:
        # Infer a soft emotion hint from the strongest moodlet.
        for token in moodlets:
            mid = _resolve_moodlet(token, catalog)
            if mid and catalog[mid].get("emotion_hint") in emotions:
                emotion_id = catalog[mid]["emotion_hint"]
                break

    resolved = []
    unknown = []
    need_pressure: set[str] = set(emotions.get(emotion_id, {}).get("need_pressure", []))
    relief: list[str] = []
    for token in moodlets:
        if not isinstance(token, str) or not token or len(token) > 80:
            raise MoodletError("INVALID_MOODLET_TOKEN")
        mid = _resolve_moodlet(token, catalog)
        if mid is None:
            unknown.append(_norm_token(token))
            continue
        row = catalog[mid]
        resolved.append(mid)
        need_pressure.update(row.get("need_links", []))
        for item in row.get("relief", []):
            if item not in relief:
                relief.append(item)

    if needs is not None and set(needs) != SIX:
        raise MoodletError("SIX_NEEDS_REQUIRED")

    emo = emotions.get(emotion_id, emotions["UNKNOWN"])
    findings = []
    if unknown:
        findings.append("UNKNOWN_MOODLET_LABEL")
    if emotion_id in {"VERY_ANGRY", "ANGRY", "SCARED"} and outdoor_social_prefix and indoor_capacity_observed:
        findings.append("TENSE_MOOD_OUTDOOR_SOCIAL")
    if "uncomfortable" in resolved and needs is not None:
        if float(needs.get("bladder", 1)) < 0.45 or float(needs.get("hygiene", 1)) < 0.45:
            findings.append("UNCOMFORTABLE_ALIGN_SURVIVAL")
    if "tired" in resolved or (needs is not None and float(needs.get("energy", 1)) < 0.35):
        if "tired" in resolved:
            findings.append("TIRED_MOODLET_ENERGY")

    gate = None
    disposition = emo.get("host_disposition", "EMULATE")
    bias = emo.get("social_routing_bias", "NEUTRAL")
    if "TENSE_MOOD_OUTDOOR_SOCIAL" in findings and event_active:
        gate = "MOODLET_AWARE_ROUTING"
        disposition = "OPTIMIZE"
        bias = "AVOID_TENSE_OUTDOOR_IF_INDOOR_CAPACITY"
        if "SIT_AND_CHAT_HERE_INDOOR" not in relief:
            relief = ["SIT_AND_CHAT_HERE_INDOOR", "CANCEL_OUTDOOR_WALK_SIT_AND_CHAT_HERE", *relief]
        elif "CANCEL_OUTDOOR_WALK_SIT_AND_CHAT_HERE" not in relief:
            relief = ["CANCEL_OUTDOOR_WALK_SIT_AND_CHAT_HERE", *relief]
    elif "UNCOMFORTABLE_ALIGN_SURVIVAL" in findings:
        gate = "MOODLET_AWARE_ROUTING"
        disposition = "OPTIMIZE"
    elif resolved or emotion_id not in {"UNKNOWN", "FINE", "HAPPY"}:
        gate = "MOODLET_AWARE_ROUTING"

    return {
        "schema": "betterinstincts.moodlet-result/v1",
        "state": "MOODLETS_EVALUATED",
        "emotion": emotion_id,
        "emotion_family": emo.get("family"),
        "severity": emo.get("severity"),
        "moodlets": resolved,
        "unknown_moodlets": unknown,
        "need_pressure": sorted(need_pressure),
        "relief": relief[:12],
        "findings": sorted(set(findings)),
        "gate": gate,
        "disposition": disposition,
        "social_routing_bias": bias,
        "capture_ref": capture_ref,
        "proof_ceiling": cfg["proof_ceiling"],
    }
