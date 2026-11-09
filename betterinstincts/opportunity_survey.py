"""Always-on *within an active listener* read-only lot opportunity projection.

The house-state/room-census authority owns geometry and classifications.
The queue-capacity owner estimates slots, and the hover index memoizes observed
affordances. This module scores candidates, never installs a timer, scans a
screen, moves the camera, issues input or claims observed outcomes.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from betterinstincts.affordance_memory import empty_index, known_targets, AffordanceMemoryError
from betterinstincts.need_service_base import normalize_needs, NeedServiceBaseError
from betterinstincts.queue_capacity import evaluate_queue_capacity, QueueCapacityError
from betterinstincts.room_census import scan_lot_model, RoomCensusError
from betterinstincts.study_space import evaluate_study_space

SCHEMA = "betterinstincts.opportunity-survey/v1"
MAX_CANDIDATES = 32
MAX_EXPLORE = 4
MAX_GOALS = 16


class OpportunitySurveyError(ValueError):
    pass


def _roles(item: Mapping) -> list[str]:
    """Observed object plus *heuristic* function hints; never a discovered pie menu."""
    category = item.get("category", "")
    label = item.get("label", "").lower()
    if category in {"bed", "sleep_pod"}:
        return ["energy"]
    if category == "plumbing":
        return (["bladder"] if "toilet" in label else
                ["hygiene"] if any(t in label for t in ("shower", "bath", "sink")) else [])
    if category == "appliance" and any(t in label for t in ("fridge", "refrigerator")):
        return ["hunger"]
    if category in {"computer", "toy"}:
        return ["fun"]
    return []


def _validated_goals(goals: Sequence[Mapping], capture_ref: str) -> list[dict]:
    if not isinstance(goals, (list, tuple)) or len(goals) > MAX_GOALS:
        raise OpportunitySurveyError("SURVEY_GOAL_BUDGET_INVALID")
    verified = []
    seen = set()
    for row in goals:
        if not isinstance(row, Mapping) or set(row) - {
            "id", "domain", "target_ref", "priority", "capture_ref"
        }:
            raise OpportunitySurveyError("SURVEY_GOAL_FIELDS_INVALID")
        target = row.get("target_ref")
        name = row.get("id")
        domain = row.get("domain")
        priority = row.get("priority", 0)
        if (not isinstance(name, str) or not name or len(name) > 80
            or not isinstance(target, str) or not target.startswith("object:")
            or len(target) > 120 or not isinstance(domain, str)
            or not domain or len(domain) > 64
            or type(priority) not in (float, int) or not 0 <= priority <= 1
            or row.get("capture_ref") != capture_ref or name in seen):
            raise OpportunitySurveyError("SURVEY_GOAL_NOT_CURRENT_OR_INVALID")
        seen.add(name)
        verified.append({"id": name, "domain": domain, "target_ref": target,
                         "priority": priority})
    return verified


def evaluate_opportunity_survey(
    needs: Mapping,
    *,
    queue: Sequence[str] = (),
    multitasking: bool | None = None,
    lot_model: Mapping | None = None,
    active_lot_id: str | None = None,
    game_version: str | None = None,
    capture_ref: str = "capture:opportunity",
    homework_pending: bool = False,
    inventory_has_homework: bool | None = None,
    observed_goals: Sequence[Mapping] = (),
    aff_index: Mapping | None = None,
    player_active: bool = False,
    host_may_control: bool = False,
    verified_live_mode: bool = False,
    camera_follow_attested: bool = False,
    actor_ref: str | None = None,
    occupied_objects: Sequence[str] = (),
) -> dict:
    """Survey supplied attested lot evidence irrespective of player's occupancy.

    No queue additions or map traversals occur. A queued Sim still permits
    passive ranking, and a player-active desktop never grants an explore lease.
    """
    if not isinstance(capture_ref, str) or not capture_ref.startswith("capture:"):
        raise OpportunitySurveyError("SURVEY_CAPTURE_REQUIRED")
    if not isinstance(occupied_objects, (list, tuple)) or len(occupied_objects) > 128 or any(
        not isinstance(x, str) or len(x) > 120 for x in occupied_objects
    ):
        raise OpportunitySurveyError("OCCUPANCY_OBSERVATION_INVALID")
    if type(player_active) is not bool or type(host_may_control) is not bool:
        raise OpportunitySurveyError("PRESENCE_FLAGS_INVALID")
    try:
        snap = normalize_needs(needs)
        budget = evaluate_queue_capacity(
            queue, multitasking=multitasking, player_directed=player_active
        )
        known = known_targets(aff_index or empty_index(), game_version=game_version)
    except (NeedServiceBaseError, QueueCapacityError, AffordanceMemoryError) as exc:
        raise OpportunitySurveyError(str(exc)) from exc
    goals = _validated_goals(observed_goals, capture_ref)
    report = {
        "schema": SCHEMA, "state": "SURVEY_WAITING_FOR_LOT",
        "capture_ref": capture_ref, "lot_id": None, "lot_revision": None,
        "queue_budget": budget, "room_count": 0, "rooms": [],
        "candidates": [], "exploration_targets": [], "queue_recommendation": None,
        "survey_mode": "PASSIVE_READ_ONLY",
        "exploration_gate": "NO_ATTESTED_LOT",
        "knowledge_hits": 0, "unknown_targets": 0,
        "execute_allowed": False, "control_permit": None,
        "proof_ceiling": "OBSERVED_LOT_ADVISORY_NOT_SIMS_INTERACTION_CERT",
    }
    if lot_model is None:
        return report
    if active_lot_id is not None and lot_model.get("lot_id") != active_lot_id:
        report["exploration_gate"] = "ACTIVE_LOT_MISMATCH"
        return report
    try:
        census = scan_lot_model(lot_model)
    except (RoomCensusError, TypeError, ValueError, KeyError):
        report["exploration_gate"] = "LOT_MODEL_UNVERIFIED"
        return report
    report["state"] = "OPPORTUNITIES_EVALUATED"
    report["lot_id"], report["lot_revision"] = census["lot_id"], census["model_revision"]
    report["room_count"] = len(census["rooms"])
    report["rooms"] = [{
        "room_id": room["room_id"], "story": room["story"],
        "enclosure": room["enclosure"],
        "functions": room["function_labels"],
        "styles": room["style_labels"],
        "item_count": room["item_count"],
    } for room in census["rooms"].values()
       if room["room_evidence"] == "STRUCTURE_ATTESTED"][:24]
    candidates = []
    unseen = []
    occupied = set(occupied_objects)
    for room in census["rooms"].values():
        if room["room_evidence"] != "STRUCTURE_ATTESTED" or room["enclosure_conflict"]:
            continue
        for item in room["items"]:
            ref = f"object:{item['id']}"
            # Only token-like references can be correlated with the hover index.
            if not item["id"].replace("_", "").replace("-", "").isalnum():
                continue
            known_here = ref in known
            if known_here:
                report["knowledge_hits"] += 1
            else:
                unseen.append({"target_ref": ref, "room_id": room["room_id"],
                               "story": room["story"], "kind": "HOVER_DISCOVERY_CANDIDATE",
                               "lot_revision": census["model_revision"]})
            if item["id"] in occupied or ref in occupied:
                continue
            for need in _roles(item):
                candidates.append({
                    "goal_id": "need:" + need,
                    "domain": "needs", "need": need,
                    "target_ref": ref, "room_id": room["room_id"],
                    "lot_revision": census["model_revision"],
                    "priority": round(1 - snap[need], 4),
                    "evidence": "ATTESTED_OBJECT_WITH_HEURISTIC_FUNCTION",
                    "affordance_observed": known_here,
                    "execute_allowed": False,
                })
            for goal in goals:
                if goal["target_ref"] == ref:
                    candidates.append({
                        "goal_id": goal["id"], "domain": goal["domain"],
                        "need": None, "target_ref": ref, "room_id": room["room_id"],
                        "lot_revision": census["model_revision"],
                        "priority": goal["priority"], "evidence": "CAPTURE_BOUND_GOAL_TARGET",
                        "affordance_observed": known_here,
                        "execute_allowed": False,
                    })
    if homework_pending and inventory_has_homework is True:
        study = evaluate_study_space(lot_model)
        if study["state"] == "STUDY_LOCATION_CANDIDATE":
            candidates.append({
                "goal_id": "career:teen_homework", "domain": "career",
                "need": None, "target_ref": "object:" + study["surface_id"],
                "room_id": study["room_id"], "lot_revision": census["model_revision"],
                "priority": 0.7,
                "evidence": "ATTESTED_SEAT_AND_SURFACE_REQUIRES_SIM_SEATED_RECHECK",
                "affordance_observed": ("object:" + study["surface_id"]) in known,
                "execute_allowed": False,
            })
    candidates.sort(key=lambda row: (
        -row["priority"], row["domain"], row["goal_id"], row["room_id"], row["target_ref"]
    ))
    report["candidates"] = candidates[:MAX_CANDIDATES]
    # A previous tooltip observation prevents repeated discovery even after a
    # new active listener session; neither a hover nor an earlier review is a
    # live affordance certificate for this specific lot revision.
    seen_refs = set()
    for row in unseen:
        if row["target_ref"] not in seen_refs:
            seen_refs.add(row["target_ref"])
    report["unknown_targets"] = len(seen_refs)
    interest = {c["target_ref"] for c in candidates[:MAX_CANDIDATES]}
    unseen.sort(key=lambda row: (row["target_ref"] not in interest, row["story"],
                                 row["room_id"], row["target_ref"]))
    used = set()
    report["exploration_targets"] = []
    for row in unseen:
        if row["target_ref"] in used:
            continue
        used.add(row["target_ref"])
        report["exploration_targets"].append(row)
        if len(report["exploration_targets"]) >= MAX_EXPLORE:
            break
    can_propose = (
        budget["enqueue_allowed"] and not player_active and host_may_control
        and verified_live_mode
    )
    if can_propose and candidates:
        report["queue_recommendation"] = {
            **candidates[0], "gate": "REOBSERVE_AFFORDANCE_AND_QUEUE_BEFORE_INPUT",
            "execute_allowed": False,
        }
    if player_active or not host_may_control:
        report["exploration_gate"] = "PLAYER_ACTIVE_PASSIVE_ONLY"
    elif not verified_live_mode:
        report["exploration_gate"] = "LIVE_SCENE_NOT_CERTIFIED"
    elif not game_version:
        report["exploration_gate"] = "EXACT_GAME_PATCH_REQUIRED"
    elif not actor_ref or not camera_follow_attested:
        report["exploration_gate"] = "ACTIVE_SIM_FOLLOW_REQUIRED"
    elif not active_lot_id:
        report["exploration_gate"] = "ACTIVE_LOT_ID_REQUIRED"
    elif not report["exploration_targets"]:
        report["exploration_gate"] = "KNOWN_TARGETS_NO_REDISCOVERY"
    else:
        report["exploration_gate"] = "IDLE_EXPLORATION_CANDIDATE"
    return report
