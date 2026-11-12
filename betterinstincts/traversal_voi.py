"""Purposeful Sim traversal VOI: pure queue guard, never an actuator.

Camera motion is a separate viewport operation. Neither camera movement nor
an EA route plan is a Sim queue action or an observed domain outcome.
"""
from __future__ import annotations

import math
from collections.abc import Mapping

DOMAINS = frozenset({"NEEDS", "CAREER", "SKILLS", "WHIMS"})
QUEUE_KINDS = frozenset({"WALK", "GOAL_ACTION", "OTHER"})
ORIGINS = frozenset({"HOST", "PLAYER", "UNKNOWN"})
MAX_QUEUE = 16
PROOF = "OFFLINE_VOI_WALK_POLICY_NOT_LIVE_GAMEPLAY_OR_INPUT_PERMIT"


def _ref(value: object) -> bool:
    return (isinstance(value, str) and 1 <= len(value) <= 120
            and all(ch.isalnum() or ch in "_:.-" for ch in value))


def _result(goal: Mapping | None, gate: str) -> dict:
    goal = goal if isinstance(goal, Mapping) else {}
    return {
        "schema": "betterinstincts.traversal-voi.result/v1",
        "gate": gate,
        "goal_id": goal.get("goal_id"),
        "domain": goal.get("domain"),
        "sim": {"next": "HOLD", "walk_candidate": False,
                "goal_action_candidate": False},
        "camera": {"next": "CAPTURE_IN_PLACE", "motion_candidate": False,
                   "owner": "betterinstincts/camera_traverse.py",
                   "execute_allowed": False},
        "queue_proposal": [],
        "execute_allowed": False,
        "control_permit": None,
        "effects_issued": 0,
        "proof_ceiling": PROOF,
    }


def _voi_scores(estimate: object) -> dict | None:
    """Advisory scores only. Cost/risk are unitless, not model-certification."""
    if estimate is None:
        return {}
    if not isinstance(estimate, Mapping) or set(estimate) != {
        "passive", "camera", "sim"
    }:
        return None
    scores = {}
    for name in ("passive", "camera", "sim"):
        sample = estimate.get(name)
        if not isinstance(sample, Mapping) or set(sample) != {"gain", "cost", "risk"}:
            return None
        values = [sample.get(key) for key in ("gain", "cost", "risk")]
        if any(type(v) not in (int, float) or not math.isfinite(v)
               or not 0 <= v <= 1 for v in values):
            return None
        scores[name] = round(values[0] - values[1] - values[2], 6)
    return scores


def evaluate_traversal_voi(observation: Mapping, *, goal: Mapping,
                           route: Mapping | None = None) -> dict:
    """Return at most one WALK→GOAL_ACTION *proposal*, never SendInput permission.

    An independently sourced checkpoint survives an empty action queue. A
    successful walk does not reset that checkpoint; only an actual observed
    domain action does. The caller must keep this checkpoint consistent with
    real queue/outcome evidence, not reinitialize it per planning turn.
    """
    out = _result(goal, "ABSTAIN_INVALID_INPUT")
    if not isinstance(observation, Mapping) or not isinstance(goal, Mapping):
        return out
    if (any(not _ref(goal.get(k)) for k in
            ("goal_id", "action_id", "target_id", "target_region"))
            or goal.get("domain") not in DOMAINS
            or type(goal.get("affordance_verified")) is not bool
            or type(goal.get("direct_interaction_available")) is not bool
            or not _ref(goal.get("affordance_evidence_ref"))):
        out["gate"] = "GOAL_ACTION_IDENTITY_OR_AFFORDANCE_UNVERIFIED"
        return out

    scores = _voi_scores(observation.get("voi_estimates"))
    if scores is None:
        out["gate"] = "VOI_ESTIMATE_INVALID"
        return out
    out["voi_scores"] = scores  # Always advisory, never a permit.
    current = observation.get("capture_ref")
    if (any(not _ref(observation.get(k)) for k in
            ("scope_id", "actor_id", "scene_revision", "capture_ref"))
            or observation.get("scene") != "LIVE_MODE"
            or observation.get("observed_scene_revision") != observation.get("scene_revision")
            or observation.get("queue_verified") is not True
            or observation.get("human_present") is not False):
        out["gate"] = ("YIELD_TO_PLAYER" if observation.get("human_present") is True
                       else "REOBSERVE_SCENE_QUEUE_OR_PRESENCE")
        return out

    # Camera advice does not alter the physical Sim or its movement checkpoint.
    if observation.get("target_visible") is False:
        if (observation.get("camera_capture_ref") == current
                and _ref(observation.get("camera_revision"))
                and (not scores or scores["camera"] > scores["passive"])):
            out["camera"].update(next="NAMED_CAMERA_REFRAME_LEASE_REQUIRED",
                                 motion_candidate=True)
        else:
            out["camera"]["next"] = "REFRESH_CAMERA_CAPTURE"
    checkpoint = observation.get("movement_checkpoint")
    if (not isinstance(checkpoint, Mapping)
            or checkpoint.get("source") != "HOST_OBSERVED"
            or not _ref(checkpoint.get("proof_ref"))
            or checkpoint.get("scope_id") != observation["scope_id"]
            or checkpoint.get("actor_id") != observation["actor_id"]
            or checkpoint.get("goal_id") != goal["goal_id"]
            or checkpoint.get("capture_ref") != current
            or type(checkpoint.get("walks_since_goal_action")) is not int
            or checkpoint["walks_since_goal_action"] not in (0, 1)):
        out["gate"] = "MOVEMENT_CHECKPOINT_REOBSERVE_REQUIRED"
        return out

    queue = observation.get("queue")
    if not isinstance(queue, (list, tuple)) or len(queue) > MAX_QUEUE:
        out["gate"] = "QUEUE_UNVERIFIED_OR_UNBOUNDED"
        return out
    host_walks: list[int] = []
    host_actions: list[int] = []
    for index, row in enumerate(queue):
        if not isinstance(row, Mapping):
            out["gate"] = "QUEUE_ROW_UNVERIFIED"
            return out
        if (row.get("kind") not in QUEUE_KINDS
                or row.get("origin") not in ORIGINS
                or row.get("actor_id") != observation["actor_id"]
                or row.get("capture_ref") != current):
            out["gate"] = "QUEUE_ROW_UNVERIFIED"
            return out
        if row["origin"] == "PLAYER":
            out["gate"] = "YIELD_TO_PLAYER_QUEUE"
            return out
        if row["origin"] != "HOST" or not _ref(row.get("origin_proof_ref")):
            out["gate"] = "QUEUE_ORIGIN_UNVERIFIED"
            return out
        if row.get("goal_id") != goal["goal_id"]:
            out["gate"] = "OTHER_HOST_GOAL_IN_QUEUE"
            return out
        if row["kind"] == "WALK":
            # A walk has a destination but no independent goal outcome.
            if row.get("target_region") != goal["target_region"]:
                out["gate"] = "WALK_TARGET_DRIFT"
                return out
            host_walks.append(index)
        elif row["kind"] == "GOAL_ACTION":
            if (row.get("action_id") != goal["action_id"]
                    or row.get("target_id") != goal["target_id"]):
                out["gate"] = "GOAL_ACTION_TARGET_DRIFT"
                return out
            host_actions.append(index)

    if len(host_walks) > 1:
        out["gate"] = "WALK_SPAM_DETECTED_REOBSERVE"
        return out
    if host_walks:
        out["gate"] = ("WALK_PENDING_AWAIT_DOMAIN_ACTION" if
                       not host_actions else "WALK_FOLLOWUP_ALREADY_QUEUED")
        if host_actions and any(i < host_walks[0] for i in host_actions):
            out["gate"] = "WALK_NOT_FOLLOWED_BY_GOAL_ACTION"
        out["sim"]["next"] = "WAIT_FOR_DOMAIN_ACTION"
        return out
    if host_actions:
        out["gate"] = "DOMAIN_ACTION_ALREADY_QUEUED"
        out["sim"]["next"] = "WAIT_FOR_DOMAIN_ACTION"
        return out
    if checkpoint["walks_since_goal_action"] >= 1:
        out["gate"] = "ONE_WALK_USED_AWAIT_OBSERVED_DOMAIN_ACTION"
        return out
    if goal["affordance_verified"] is not True:
        out["gate"] = "ATTEST_DOMAIN_AFFORDANCE_FIRST"
        return out
    if goal["direct_interaction_available"] is True:
        out["gate"] = "PREFER_NATIVE_OBJECT_INTERACTION"
        out["sim"].update(next="PROPOSE_GOAL_ACTION",
                          goal_action_candidate=True)
        out["queue_proposal"] = [{
            "kind": "GOAL_ACTION", "goal_id": goal["goal_id"],
            "domain": goal["domain"], "action_id": goal["action_id"],
            "target_id": goal["target_id"],
        }]
        return out
    if not isinstance(route, Mapping):
        out["gate"] = "VERIFIED_SIM_ROUTE_REQUIRED"
        return out
    if (route.get("schema") != "betterinstincts.household-navigation.plan/v1"
            or route.get("state") not in {
                "NAVIGATION_ROUTE_PROPOSED", "NAVIGATION_RECOVERY_ROUTE"
            }
            or route.get("scope_id") != observation["scope_id"]
            or route.get("actor_id") != observation["actor_id"]
            or route.get("objective_id") != goal["goal_id"]
            or route.get("scene_revision") != observation["scene_revision"]
            or route.get("execute_allowed") is not False
            or route.get("control_permit") is not None
            or not isinstance(route.get("route"), list)
            or not 2 <= len(route["route"]) <= 33
            or route.get("next_region") != route["route"][1]
            or route.get("target_region") != goal["target_region"]):
        out["gate"] = "SIM_ROUTE_STALE_OR_UNVERIFIED"
        return out
    out["gate"] = "SINGLE_GOAL_BOUND_WALK_CANDIDATE"
    out["sim"].update(next="PROPOSE_ONE_WALK_THEN_GOAL_ACTION",
                      walk_candidate=True)
    out["queue_proposal"] = [
        {"kind": "WALK", "goal_id": goal["goal_id"],
         "target_region": goal["target_region"],
         "verified_route": list(route["route"])},
        {"kind": "GOAL_ACTION", "goal_id": goal["goal_id"],
         "domain": goal["domain"], "action_id": goal["action_id"],
         "target_id": goal["target_id"]},
    ]
    return out


__all__ = ["evaluate_traversal_voi", "DOMAINS", "MAX_QUEUE"]
