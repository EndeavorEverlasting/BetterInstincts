"""Version-bound, read-only scene classification and transition proposals.

These cues are machine-readable research slots, NOT calibrated image recognition.
The program NEVER clicks The Sims, reads save files or grants game certification.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "contracts" / "game-scenes.v1.json"
MAX_CATALOG_BYTES = 180_000
MAX_OBSERVATIONS = 32


class SceneError(ValueError):
    pass


def load_catalog(path: Path = CATALOG) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_CATALOG_BYTES:
        raise SceneError("CATALOG_MISSING_OR_UNSAFE")
    raw = path.read_bytes()
    if len(raw) > MAX_CATALOG_BYTES:
        raise SceneError("CATALOG_TOO_LARGE")
    try:
        catalog = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SceneError("CATALOG_INVALID_JSON") from exc
    validate_catalog(catalog)
    return catalog


def validate_catalog(catalog: dict) -> None:
    if not isinstance(catalog, dict) or catalog.get("schema") != "betterinstincts.scene-catalog/v1":
        raise SceneError("SCENE_SCHEMA_INVALID")
    if not isinstance(catalog.get("game_version"), str) or len(catalog["game_version"].split(".")) != 4:
        raise SceneError("EXACT_PATCH_REQUIRED")
    if catalog.get("version_policy") != "EXACT_MATCH_ONLY_NO_LATEST_FALLBACK":
        raise SceneError("SCENE_PATCH_FALLBACK_FORBIDDEN")
    scenes = catalog.get("scenes")
    if not isinstance(scenes, list) or not 20 <= len(scenes) <= 120:
        raise SceneError("SCENE_COUNT_INVALID")
    ids = [s.get("id") for s in scenes if isinstance(s, dict)]
    if len(set(ids)) != len(scenes) or "unknown" not in ids:
        raise SceneError("SCENE_IDENTITIES_INVALID")
    allowed_gates = {"OPERATOR_CONFIRMATION", "REVIEW_AND_SAVE_POLICY"}
    cues = set()
    for scene in scenes:
        if not isinstance(scene, dict) or not isinstance(scene.get("id"), str):
            raise SceneError("SCENE_ENTRY_INVALID")
        observed = scene.get("required_cues")
        if not isinstance(observed, list) or len(observed) != 2:
            raise SceneError("SCENE_REQUIRES_TWO_CUES")
        keys = []
        for c in observed:
            if not isinstance(c, dict) or set(c) != {"source", "token"} or c["source"] not in {"visual", "operator"} or not isinstance(c["token"], str) or not 1 <= len(c["token"]) <= 80:
                raise SceneError("SCENE_CUE_INVALID")
            keys.append((c["source"], c["token"]))
        if len({k[0] for k in keys}) != 2 or len(set(keys)) != 2:
            raise SceneError("SCENE_REQUIRES_INDEPENDENT_SOURCES")
        if scene["id"] != "unknown" and tuple(keys) in cues:
            raise SceneError("DUPLICATE_SCENE_SIGNATURE")
        cues.add(tuple(keys))
        transitions = scene.get("transitions")
        if not isinstance(transitions, list) or len(transitions) > 24:
            raise SceneError("INVALID_SCENE_TRANSITIONS")
        if scene["id"] == "unknown" and transitions:
            raise SceneError("UNKNOWN_SCENE_MUST_BE_TERMINAL")
        targets = set()
        for transition in transitions:
            if not isinstance(transition, dict) or transition.get("target") not in ids or transition.get("gate") not in allowed_gates or transition.get("execution") != "MANUAL_ONLY":
                raise SceneError("ILLEGAL_SCENE_TRANSITION")
            if transition["target"] in targets:
                raise SceneError("DUPLICATE_SCENE_TARGET")
            targets.add(transition["target"])
    forbidden = set(catalog.get("global_forbidden_actions", []))
    if not {"RESUME", "DELETE_SAVE", "OVERWRITE_SAVE", "AUTO_SELECT_UNKNOWN_SAVE", "AUTO_TRANSITION"}.issubset(forbidden):
        raise SceneError("SCENE_FORBIDDEN_ACTIONS_WEAKENED")


def classify(catalog: dict, game_version: str, observations: list[dict]) -> dict:
    validate_catalog(catalog)
    if game_version != catalog["game_version"]:
        return {"state": "UNKNOWN_PATCH", "scene_id": "unknown", "candidates": [],
                "proof_ceiling": "NO_SCENE_INFERENCE_FOR_UNCALIBRATED_PATCH"}
    if not isinstance(observations, list) or len(observations) > MAX_OBSERVATIONS:
        raise SceneError("INVALID_OBSERVATION_SET")
    keys = set()
    for item in observations:
        if not isinstance(item, dict) or set(item) != {"source", "token"} or item["source"] not in {"visual", "operator"} or not isinstance(item["token"], str) or len(item["token"]) > 80:
            raise SceneError("UNTRUSTED_OBSERVATION_FORMAT")
        keys.add((item["source"], item["token"]))
    matches = [scene["id"] for scene in catalog["scenes"]
               if scene["id"] != "unknown" and
               all((cue["source"], cue["token"]) in keys for cue in scene["required_cues"])]
    state = "CANDIDATE_UNVERIFIED" if len(matches) == 1 else "AMBIGUOUS_OR_UNKNOWN"
    return {"state": state, "scene_id": matches[0] if len(matches) == 1 else "unknown",
            "candidates": matches, "game_version": game_version,
            "proof_ceiling": "DECLARED_CUES_ONLY_NO_SCREENSHOT_VALIDATION_OR_AUTOMATION"}


def propose_transition(catalog: dict, classification: dict, target: str) -> dict:
    if classification.get("state") != "CANDIDATE_UNVERIFIED":
        return {"state": "BLOCKED", "reason": "SCENE_UNVERIFIED_OR_AMBIGUOUS"}
    source = next((x for x in catalog["scenes"] if x["id"] == classification["scene_id"]), None)
    if source is None:
        return {"state": "BLOCKED", "reason": "SCENE_NOT_IN_CATALOG"}
    transition = next((x for x in source["transitions"] if x["target"] == target), None)
    if transition is None:
        return {"state": "BLOCKED", "reason": "TRANSITION_NOT_ALLOWED"}
    return {"state": "PROPOSED_MANUAL_ONLY", "from": source["id"], "to": target,
            "gate": transition["gate"], "execution": "MANUAL_ONLY",
            "proof_ceiling": "TRANSITION_HYPOTHESIS_NOT_CLICK_OR_GAMEPLAY"}
