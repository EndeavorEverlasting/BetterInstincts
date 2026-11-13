"""Typed Sim motive catalogs with opt-in, bounded reviewed-outcome ranking.

Pure offline decision aid. Does not import a game API, inspect screenshots,
write user profiles, enqueue Sims actions, spawn watchers or take desktop input.
"""
from __future__ import annotations

import json
import re
from math import isfinite
from pathlib import Path
from typing import Mapping, Sequence

from betterinstincts.need_service_base import threshold_pair

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "occult-needs.v1.json"
SCHEMA = "betterinstincts.occult-needs/v1"
MODEL_SCHEMA = "betterinstincts.occult-needs-model/v1"
PATCH = re.compile(r"^[0-9]+(?:\.[0-9]+){3}$")
REF = re.compile(r"^[A-Za-z0-9_.:-]{8,80}$")
PLATFORMS = frozenset(("windows", "linux", "macos"))
PROOF = "OFFLINE_PROFILE_AND_REVIEWED_OUTCOME_ADVISORY_NOT_GAMEPLAY"
MAX_EVENTS = 128
MAX_AVAILABLE = 32


class OccultNeedsError(ValueError):
    """Invalid catalog, observations or opt-in learning event."""


def load_catalog(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 128000:
        raise OccultNeedsError("UNSAFE_OCCULT_CATALOG")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise OccultNeedsError("INVALID_OCCULT_CATALOG_JSON") from exc
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise OccultNeedsError("INVALID_OCCULT_CATALOG_SCHEMA")
    profiles, motives = data.get("profiles"), data.get("motives")
    if not isinstance(profiles, dict) or not isinstance(motives, dict):
        raise OccultNeedsError("INVALID_OCCULT_CATALOG_SHAPE")
    if set(data.get("ordinary_six", ())) != {
        "bladder", "hunger", "energy", "hygiene", "fun", "social"
    }:
        raise OccultNeedsError("SIX_ORDINARY_MOTIVES_REQUIRED")
    for need, actions in motives.items():
        if not isinstance(need, str) or not isinstance(actions, list) or not actions:
            raise OccultNeedsError("INVALID_MOTIVE_ACTIONS")
        ids = []
        for row in actions:
            if (not isinstance(row, dict) or not isinstance(row.get("id"), str)
                    or not row.get("source")
                    or row.get("admission") not in ("OBSERVED_INTERACTION_ONLY", "PLAYER_ONLY")):
                raise OccultNeedsError("INVALID_MOTIVE_ACTION")
            ids.append(row["id"])
        if len(set(ids)) != len(ids):
            raise OccultNeedsError("DUPLICATE_MOTIVE_ACTION")
    for name, profile in profiles.items():
        if not isinstance(profile, dict) or profile.get("status") not in (
            "CATALOG_READY", "LOCAL_MOTIVE_SCHEMA_REQUIRED"
        ):
            raise OccultNeedsError("INVALID_OCCULT_PROFILE")
        fields = profile.get("motives")
        if not isinstance(fields, list) or len(fields) != len(set(fields)):
            raise OccultNeedsError("INVALID_PROFILE_MOTIVES")
        if any(need not in motives for need in fields):
            raise OccultNeedsError("UNMAPPED_PROFILE_MOTIVE")
        if profile["status"] == "CATALOG_READY" and not fields:
            raise OccultNeedsError("EMPTY_READY_PROFILE")
    return data


def _patch(version: str, platform: str) -> None:
    if not isinstance(version, str) or not PATCH.fullmatch(version):
        raise OccultNeedsError("EXACT_GAME_PATCH_REQUIRED")
    if platform not in PLATFORMS:
        raise OccultNeedsError("PLATFORM_REQUIRED")


def _level(value: object) -> float:
    if type(value) not in (int, float) or not isfinite(value) or not 0 <= value <= 1:
        raise OccultNeedsError("INVALID_MOTIVE_LEVEL")
    return float(value)


def _advisory(reason: str, **details: object) -> dict:
    return {"state": "ABSTAIN", "reason": reason, "execute": False,
            "proof_ceiling": PROOF, **details}


def _profile(catalog: Mapping, name: str) -> dict | None:
    if not isinstance(name, str):
        return None
    return catalog["profiles"].get(name)


def _validate_model(model: Mapping, catalog: Mapping) -> dict:
    if not isinstance(model, dict) or model.get("schema") != MODEL_SCHEMA:
        raise OccultNeedsError("INVALID_LEARNING_MODEL")
    _patch(model.get("game_version"), model.get("platform"))
    p = _profile(catalog, model.get("profile"))
    if p is None or p["status"] != "CATALOG_READY":
        raise OccultNeedsError("UNKNOWN_MODEL_PROFILE")
    events = model.get("events")
    if not isinstance(events, list) or len(events) > MAX_EVENTS:
        raise OccultNeedsError("LEARNING_MODEL_LIMIT")
    seen = set()
    for event in events:
        if not isinstance(event, dict) or set(event) != {
            "observation_ref", "need", "action", "outcome"
        }:
            raise OccultNeedsError("INVALID_REVIEWED_EVENT")
        ref = event["observation_ref"]
        if not isinstance(ref, str) or not REF.fullmatch(ref) or ref in seen:
            raise OccultNeedsError("DUPLICATE_OR_INVALID_EVIDENCE")
        seen.add(ref)
        need = event["need"]
        if (need not in p["motives"] or event["outcome"] not in ("helpful", "harmful")
                or event["action"] not in {
                    row["id"] for row in catalog["motives"][need]
                    if row["admission"] == "OBSERVED_INTERACTION_ONLY"
                }):
            raise OccultNeedsError("MODEL_EVENT_NOT_IN_PROFILE")
    return model


def new_model(*, profile: str, game_version: str, platform: str,
              catalog: Mapping | None = None) -> dict:
    config = load_catalog() if catalog is None else catalog
    _patch(game_version, platform)
    p = _profile(config, profile)
    if p is None or p["status"] != "CATALOG_READY":
        raise OccultNeedsError("UNSUPPORTED_PROFILE")
    return {"schema": MODEL_SCHEMA, "profile": profile, "game_version": game_version,
            "platform": platform, "events": []}


def learn(model: Mapping, event: Mapping, *, catalog: Mapping | None = None) -> dict:
    """Return a new opt-in model; never persist automatically or infer causality."""
    config = load_catalog() if catalog is None else catalog
    valid = _validate_model(model, config)
    if not isinstance(event, Mapping) or set(event) != {
        "observation_ref", "need", "action", "outcome", "operator_reviewed",
        "opt_in", "scene_verified", "before", "after", "game_version", "platform"
    }:
        raise OccultNeedsError("REVIEWED_EVENT_FIELDS_REQUIRED")
    if any(event[flag] is not True for flag in ("operator_reviewed", "opt_in", "scene_verified")):
        raise OccultNeedsError("REVIEW_AND_OPT_IN_REQUIRED")
    if (event["game_version"], event["platform"]) != (
            valid["game_version"], valid["platform"]):
        raise OccultNeedsError("MODEL_PATCH_PLATFORM_MISMATCH")
    ref = event["observation_ref"]
    if not isinstance(ref, str) or not REF.fullmatch(ref):
        raise OccultNeedsError("INVALID_OBSERVATION_REFERENCE")
    if ref in {old["observation_ref"] for old in valid["events"]}:
        raise OccultNeedsError("OBSERVATION_REPLAY")
    if len(valid["events"]) >= MAX_EVENTS:
        raise OccultNeedsError("EVIDENCE_CAP_REACHED")
    need, action = event["need"], event["action"]
    if (need not in config["profiles"][valid["profile"]]["motives"]
            or action not in {
                x["id"] for x in config["motives"][need]
                if x["admission"] == "OBSERVED_INTERACTION_ONLY"
            }):
        raise OccultNeedsError("ACTION_NOT_IN_PROFILE")
    before, after = _level(event["before"]), _level(event["after"])
    if event["outcome"] not in ("helpful", "harmful"):
        raise OccultNeedsError("INVALID_REVIEWED_OUTCOME")
    if event["outcome"] == "helpful" and after - before < 0.02:
        raise OccultNeedsError("HELPFUL_OUTCOME_NOT_MEASURED")
    return {**valid, "events": [
        *valid["events"], {"observation_ref": ref, "need": need,
                           "action": action, "outcome": event["outcome"]}
    ]}


def _score(events: Sequence[Mapping], need: str, action: str) -> tuple[int, int]:
    selected = [row for row in events if row["need"] == need and row["action"] == action]
    return sum(row["outcome"] == "helpful" for row in selected), sum(
        row["outcome"] == "harmful" for row in selected)


def recommend(
    profile: str,
    needs: Mapping[str, float],
    available_actions: Sequence[str],
    *,
    game_version: str,
    platform: str,
    installed_packs: Sequence[str] = (),
    capabilities: Sequence[str] = (),
    player_directed: bool = False,
    player_active: bool = False,
    already_busy: bool = False,
    supported_life_stage: bool = True,
    model: Mapping | None = None,
    catalog: Mapping | None = None,
) -> dict:
    """Propose at most one currently observed action; never authorize gameplay."""
    config = load_catalog() if catalog is None else catalog
    _patch(game_version, platform)
    p = _profile(config, profile)
    if p is None:
        return _advisory("UNSUPPORTED_OR_HYBRID_SIM_PROFILE")
    if p["status"] != "CATALOG_READY":
        return _advisory("LOCAL_MOTIVE_SCHEMA_REQUIRED")
    if not all(type(flag) is bool for flag in (
        player_directed, player_active, already_busy, supported_life_stage
    )):
        raise OccultNeedsError("INVALID_PLAYER_GATE")
    if player_directed or player_active or already_busy or not supported_life_stage:
        return _advisory("PLAYER_FIRST_OR_BUSY")
    if p["pack"] != "base" and p["pack"] not in installed_packs:
        return _advisory("REQUIRED_PACK_NOT_CONFIRMED")
    if not isinstance(needs, Mapping) or set(needs) != set(p["motives"]):
        return _advisory("MOTIVE_SCHEMA_MISMATCH", expected_motives=list(p["motives"]))
    levels = {need: _level(value) for need, value in needs.items()}
    if (not isinstance(available_actions, (list, tuple))
            or len(available_actions) > MAX_AVAILABLE
            or any(not isinstance(x, str) for x in available_actions)
            or len(set(available_actions)) != len(available_actions)):
        raise OccultNeedsError("INVALID_OBSERVED_ACTIONS")
    observed = set(available_actions)
    if (not isinstance(capabilities, (list, tuple))
            or any(not isinstance(x, str) for x in capabilities)):
        raise OccultNeedsError("INVALID_CAPABILITIES")
    approved = None
    if model is not None:
        approved = _validate_model(model, config)
        if (approved["profile"], approved["game_version"], approved["platform"]) != (
            profile, game_version, platform
        ):
            raise OccultNeedsError("MODEL_CONTEXT_MISMATCH")
    _, preemptive = threshold_pair()
    due = sorted((level, index, need) for index, (need, level) in enumerate(
        (item, levels[item]) for item in p["motives"]
    ) if level < preemptive)
    if not due:
        return _advisory("NO_MOTIVE_BELOW_PREEMPTIVE_THRESHOLD")
    for level, _, need in due:
        candidates = []
        for order, item in enumerate(config["motives"][need]):
            action = item["id"]
            if (item["admission"] != "OBSERVED_INTERACTION_ONLY"
                    or action not in observed
                    or (item.get("requires_capability")
                        and item["requires_capability"] not in capabilities)):
                continue
            helped, harmed = _score(
                approved["events"] if approved is not None else (), need, action)
            if harmed >= 1 and helped == 0:
                continue  # A reviewed harmful attempt blocks unsafe replay.
            n = helped + harmed
            learned = n >= 3 and helped >= 3 and helped / n >= 0.75
            # Bayesian smoothed point estimate is ONLY a within-need tie-breaker.
            posterior = (helped + 1) / (n + 2) if learned else 0.5
            candidates.append((-int(learned), -posterior, order, action, helped, harmed))
        if candidates:
            _, _, _, chosen, helped, harmed = min(candidates)
            return {"state": "ADVISORY", "profile": profile, "need": need,
                    "level": level, "suggested_action": chosen,
                    "source": "REVIEWED_OUTCOMES" if helped >= 3 and helped / (
                        helped + harmed) >= .75 else "DETERMINISTIC_CATALOG",
                    "helpful": helped, "harmful": harmed, "execute": False,
                    "proof_ceiling": PROOF}
    return _advisory("NO_SAFE_OBSERVED_REMEDY")
