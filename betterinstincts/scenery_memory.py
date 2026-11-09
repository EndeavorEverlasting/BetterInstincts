"""Bounded, reviewable scenery discovery memory; distinct from game mode scenes.

One HOST_CAPTURE + visual/operator corroboration yields a candidate viewpoint
record. Records can be stored in the designated repository manifest; they do
NOT authorize navigation or permanent beliefs without operator review.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from betterinstincts.scenes import load_catalog

TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")
SCHEMA = "betterinstincts.scenery-discoveries/v1"
MAX_ENTRIES = 96
MAX_SIGHTINGS = 9999
PROOF = "SEMANTIC_SCENERY_CANDIDATES_NOT_GAME_NAVIGATION_AUTHORITY"


class SceneryMemoryError(ValueError):
    pass


def _token(s: object) -> bool:
    return isinstance(s, str) and bool(TOKEN.fullmatch(s))


def validate_registry(registry: Mapping[str, Any]) -> None:
    if (not isinstance(registry, Mapping) or registry.get("schema") != SCHEMA
            or not isinstance(registry.get("records"), list)
            or len(registry["records"]) > MAX_ENTRIES):
        raise SceneryMemoryError("SCENERY_REGISTRY_INVALID")
    seen = set()
    for r in registry["records"]:
        if (not isinstance(r, Mapping)
                or not _token(r.get("signature"))
                or not _token(r.get("world_ref"))
                or not _token(r.get("lot_ref"))
                or r.get("status") not in {"CANDIDATE", "OPERATOR_REVIEWED"}
                or type(r.get("sightings")) is not int
                or not 1 <= r["sightings"] <= MAX_SIGHTINGS
                or r["signature"] in seen):
            raise SceneryMemoryError("SCENERY_REGISTRY_ENTRY_INVALID")
        seen.add(r["signature"])


def record_scenery(
    registry: Mapping[str, Any], *, capture_ref: str,
    observation: Mapping[str, Any], operator_reviewed: bool = False,
) -> dict:
    """Produce a deterministic versioned registry update and receipt, no IO."""
    validate_registry(registry)
    if operator_reviewed:
        raise SceneryMemoryError("REVIEW_REQUIRES_SEPARATE_EXPLICIT_PROVENANCE")
    if (not _token(capture_ref) or not isinstance(observation, Mapping)
            or observation.get("source") != "HOST_CAPTURE"
            or observation.get("capture_ref") != capture_ref
            or observation.get("game_version") != load_catalog()["game_version"]
            or observation.get("scene_id") not in {
                "live_mode", "buy_mode", "build_mode"
            }):
        raise SceneryMemoryError("SCENERY_HOST_SCENE_UNVERIFIED")
    for key in ("world_ref", "lot_ref", "view_kind", "view_sector", "camera_revision"):
        if not _token(observation.get(key)):
            raise SceneryMemoryError("SCENERY_IDENTITY_MISSING:" + key)
    tags = observation.get("landmark_tokens")
    if (not isinstance(tags, list) or not 1 <= len(tags) <= 8 or
            any(not _token(x) for x in tags) or len(set(tags)) != len(tags)):
        raise SceneryMemoryError("SCENERY_LANDMARKS_INVALID")
    cues = observation.get("scene_cues")
    if (not isinstance(cues, list) or len(cues) != 2
            or any(not isinstance(v, Mapping) or set(v) != {"source", "token"} for v in cues)
            or {v.get("source") for v in cues} != {"visual", "operator"}
            or any(not _token(v.get("token")) for v in cues)):
        raise SceneryMemoryError("SCENERY_INDEPENDENT_CUES_REQUIRED")
    goal_id = observation.get("intended_goal_id")
    target_id = observation.get("intended_target_id")
    if (goal_id is not None and not _token(goal_id)) or (target_id is not None and not _token(target_id)):
        raise SceneryMemoryError("SCENERY_GOAL_TARGET_INVALID")
    identity = {
        "game_version": observation["game_version"],
        "world_ref": observation["world_ref"],
        "lot_ref": observation["lot_ref"],
        "view_kind": observation["view_kind"],
        "view_sector": observation["view_sector"],
        "landmark_tokens": sorted(tags),
    }
    signature = "scene:"+hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:24]
    records = [dict(item) for item in registry["records"]]
    existing = next((x for x in records if x["signature"] == signature), None)
    if existing is not None:
        if existing["sightings"] >= MAX_SIGHTINGS:
            raise SceneryMemoryError("SCENERY_SIGHTINGS_AT_LIMIT")
        existing["sightings"] += 1
        existing["last_capture_ref"] = capture_ref
        existing["last_camera_revision"] = observation["camera_revision"]
        existing["last_observed_goal_id"] = goal_id
        # Never downgrade a reviewed record, nor auto-promote a candidate.
        state = "SCENERY_DEDUPLICATED"
    else:
        if len(records) >= MAX_ENTRIES:
            raise SceneryMemoryError("SCENERY_REGISTRY_FULL")
        records.append({
            "signature": signature, **identity, "status": "CANDIDATE",
            "sightings": 1, "last_capture_ref": capture_ref,
            "last_camera_revision": observation["camera_revision"],
            "last_observed_goal_id": goal_id,
            "first_observed_target_id": target_id,
            "reason": "OFF_TARGET" if observation.get("on_intended_target") is False else "DISCOVERY",
            "route_status": "UNVERIFIED_NO_NAVIGATION",
        })
        state = "SCENERY_CANDIDATE_RECORDED"
    out = {**dict(registry), "records": sorted(records, key=lambda x:x["signature"])}
    return {
        "state": state, "signature": signature, "registry": out,
        "record": next(x for x in out["records"] if x["signature"] == signature),
        "execute_allowed": False, "proof_ceiling": PROOF,
    }


def review_scenery(
    registry: Mapping[str, Any], *, signature: str,
    review: Mapping[str, Any],
) -> dict:
    """Explicit operator attestation is the ONLY promotion from candidate."""
    validate_registry(registry)
    if (not _token(signature) or not isinstance(review, Mapping)
            or review.get("source") != "OPERATOR_REVIEW"
            or review.get("approved") is not True
            or not _token(review.get("review_ref"))
            or not _token(review.get("route_label"))):
        raise SceneryMemoryError("OPERATOR_SCENE_REVIEW_REQUIRED")
    records = [dict(x) for x in registry["records"]]
    record = next((x for x in records if x["signature"] == signature), None)
    if record is None:
        raise SceneryMemoryError("SCENERY_SIGNATURE_UNKNOWN")
    record["status"] = "OPERATOR_REVIEWED"
    record["review_ref"] = review["review_ref"]
    record["route_label"] = review["route_label"]
    # Review does not fabricate route coordinates.
    return {**dict(registry), "records": records}


def propose_revisit(
    registry: Mapping[str, Any], *, signature: str,
    game_version: str, current_goal_id: str | None, target_id: str | None,
) -> dict:
    """Expose reviewed landmark as a hint; host still needs fresh target lease."""
    validate_registry(registry)
    record = next((x for x in registry["records"] if x["signature"] == signature), None)
    if (record is None or record.get("status") != "OPERATOR_REVIEWED"
            or record["game_version"] != game_version
            or not _token(current_goal_id) or not _token(target_id)):
        return {"state": "SCENERY_REVISIT_NOT_ADMITTED", "execute_allowed": False}
    return {
        "state": "SCENERY_REVISIT_CANDIDATE", "execute_allowed": False,
        "signature": signature, "route_label": record["route_label"],
        "world_ref": record["world_ref"], "lot_ref": record["lot_ref"],
        "view_kind": record["view_kind"], "landmark_tokens": record["landmark_tokens"],
        "target_id": target_id, "goal_id": current_goal_id,
        "next": "FRESH_HOST_TASK_GOAL_AND_CAMERA_MAP_LEASE_REQUIRED",
        "proof_ceiling": PROOF,
    }
