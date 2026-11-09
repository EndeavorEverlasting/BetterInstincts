"""Active-Sim camera authority for agent-owned Sims 4 views.

No input effects here. The camera belongs to the player whenever the player is
active; otherwise the active Sim is the only default frame. A named, observed
goal may receive one short map lease, never indefinite free camera roaming.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from betterinstincts.camera_traverse import CameraTraverseError, plan_traverse
from betterinstincts.sim_camera import (
    CENTER_SIM, plan_sim_camera,
)
from betterinstincts.portrait_follow import plan_portrait_follow

MAX_MAP_LEASE_MS = 30_000
MAX_MAP_DIRECTIONS = 8
CAMERA_LOCK_PROOF = "OFFLINE_ACTIVE_SIM_CAMERA_GUARD_NOT_LIVE_GAME_CERTIFIED"


def evaluate_active_sim_camera_lock(
    *, capture_ref: str, observation: Mapping[str, Any] | None,
    map_requested: bool = False,
    map_goal: Mapping[str, Any] | None = None,
    directions: Sequence[str] = (),
    zoom_notches: int = 0,
    now_ms: int | None = None,
) -> dict:
    """Require an active-Sim anchor or a finite goal-scoped map exception.

    The observation must pass the existing player/scene checks before *any*
    camera action is planned. A returned plan is never an input permit.
    """
    base = {
        "policy": "ACTIVE_SIM_ONLY_UNLESS_GOAL_MAP_LEASE",
        "execute_allowed": False,
        "proof_ceiling": CAMERA_LOCK_PROOF,
    }

    def hold(gate: str, reason: str) -> dict:
        return {**base, "state": "CAMERA_LOCK_HOLD", "gate": gate,
                "reason": reason, "map_plan": None, "restore": None}

    center = plan_sim_camera(
        CENTER_SIM, capture_ref=capture_ref, observation=observation,
    )
    if center["state"] == "SIM_CAMERA_NOT_READY":
        return hold("CAMERA_LOCK_REOBSERVE_OR_YIELD", center["reason"])
    if not isinstance(observation, Mapping):
        return hold("CAMERA_LOCK_REOBSERVE_OR_YIELD", "HOST_CAMERA_OBSERVATION_REQUIRED")

    sim_id = center.get("sim_id")
    if type(sim_id) is not int or sim_id <= 0:
        return hold("CAMERA_LOCK_REOBSERVE_OR_YIELD", "ACTIVE_SIM_ID_REQUIRED")

    following = observation.get("camera_follow_sim_id") == sim_id
    centered_once = (observation.get("camera_centered_sim_id") == sim_id
                     and observation.get("camera_displaced") is False)
    anchored = following or centered_once
    portrait = plan_portrait_follow(capture_ref=capture_ref, observation=observation)
    movement_requested = bool(map_requested or directions or zoom_notches)

    if movement_requested:
        if not anchored:
            return {**base, "state": "CAMERA_LOCK_RECENTER_FIRST",
                    "gate": "CAMERA_ACTIVE_SIM_CENTER_REQUIRED",
                    "reason": "MAP_TRAVERSE_MUST_START_FROM_ACTIVE_SIM",
                    "sim_id": sim_id, "center": center, "map_plan": None,
                    "restore": None}
        if not isinstance(map_goal, Mapping):
            return hold("CAMERA_MAP_GOAL_REQUIRED", "NO_NAMED_GOAL_LEASE")
        goal_id, target_id = map_goal.get("goal_id"), map_goal.get("target_id")
        if not all(isinstance(v, str) and 1 <= len(v) <= 96 for v in (goal_id, target_id)):
            return hold("CAMERA_MAP_GOAL_REQUIRED", "GOAL_AND_TARGET_IDS_REQUIRED")
        if (
            map_goal.get("capture_ref") != capture_ref
            or map_goal.get("camera_revision") != center.get("camera_revision")
            or type(map_goal.get("active_sim_id")) is not int
            or map_goal["active_sim_id"] != sim_id
            or observation.get("active_goal_id") != goal_id
            or observation.get("map_target_id") != target_id
            or observation.get("map_goal_source") != "HOST_TASK"
        ):
            return hold("CAMERA_MAP_GOAL_REQUIRED", "UNVERIFIED_OR_STALE_GOAL")
        issued_ms = map_goal.get("issued_at_ms")
        if (
            type(now_ms) is not int or type(issued_ms) is not int
            or now_ms < issued_ms or now_ms - issued_ms > MAX_MAP_LEASE_MS
        ):
            return hold("CAMERA_MAP_LEASE_EXPIRED", "FRESH_BOUNDED_GOAL_REQUIRED")
        if not isinstance(directions, (tuple, list)) or len(directions) > MAX_MAP_DIRECTIONS:
            return hold("CAMERA_MAP_GOAL_REQUIRED", "INVALID_MAP_DIRECTIONS")
        try:
            plan = plan_traverse(directions, zoom_notches=zoom_notches)
        except (CameraTraverseError, TypeError, ValueError) as exc:
            return hold("CAMERA_MAP_GOAL_REQUIRED", str(exc))
        return {
            **base, "state": "CAMERA_MAP_LEASE_PLANNED",
            "gate": "CAMERA_MAP_LEASE_READY",
            "sim_id": sim_id, "goal_id": goal_id, "target_id": target_id,
            "issued_at_ms": issued_ms,
            "expires_at_ms": issued_ms + MAX_MAP_LEASE_MS,
            "capture_ref": capture_ref, "camera_revision": center["camera_revision"],
            "map_plan": plan,
            "restore": {
                "command": CENTER_SIM,
                "chord": ["ENTER"],
                "required_in_finally": True,
                "preferred_control": "RIGHT_CLICK_ACTIVE_SIM_PORTRAIT",
                "fallback_once_if_no_verified_portrait": "ENTER_CENTER_ONLY",
                "must_reobserve_follow_not_just_center": True,
                "reobserve_active_sim": True,
                "on_human_interruption": "YIELD_AND_MARK_RESTORE_PENDING",
                "forbidden": ["SHIFT_ENTER", "BLIND_PAN", "PARK_ON_STREET"],
            },
        }

    if following:
        return {**base, "state": "CAMERA_ACTIVE_SIM_LOCKED",
                "gate": "CAMERA_ACTIVE_SIM_LOCKED", "sim_id": sim_id,
                "center": None, "portrait_follow": None,
                "map_plan": None, "restore": None}
    if portrait["state"] == "PORTRAIT_FOLLOW_READY_FOR_ADMISSION":
        return {**base, "state": "CAMERA_PORTRAIT_FOLLOW_FIRST",
                "gate": "CAMERA_PORTRAIT_FOLLOW_REQUIRED",
                "sim_id": sim_id, "center": None,
                "portrait_follow": portrait, "map_plan": None, "restore": None}
    if centered_once:
        # A single Enter is not a following camera. Never silently consider
        # a centered-but-static view to be the default follow lock.
        return {**base, "state": "CAMERA_PORTRAIT_ATTESTATION_REQUIRED",
                "gate": "CAMERA_PORTRAIT_ATTESTATION_REQUIRED",
                "sim_id": sim_id, "center": None,
                "portrait_follow": portrait, "map_plan": None, "restore": None}
    return {**base, "state": "CAMERA_LOCK_RECENTER_FIRST",
            "gate": "CAMERA_ACTIVE_SIM_CENTER_REQUIRED",
            "reason": "ACTIVE_SIM_NOT_IN_CAMERA_FRAME",
            "preferred_control": "RIGHT_CLICK_ACTIVE_SIM_PORTRAIT",
            "temporary_center_only": True,
            "sim_id": sim_id, "center": center,
            "portrait_follow": portrait, "map_plan": None, "restore": None}
