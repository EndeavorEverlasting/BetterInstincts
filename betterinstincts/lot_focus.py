"""Recognize when the camera/scenery is off the active household lot.

Policy only — no input, saves, or street roam. Restore plans use Enter
(CENTER_ACTIVE_SIM), never Shift+Enter as the default Sim restore.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from betterinstincts.camera_traverse import assess_agent_zoom_mode, resolve_zoom_mode_alias
from betterinstincts.scenes import load_catalog
from betterinstincts.sim_camera import CENTER_SIM, plan_sim_camera

LOT_FOCUS_PROOF = "OFFLINE_LOT_FOCUS_POLICY_NOT_LIVE_CAMERA_CERTIFIED"

_ON_LOT_KINDS = frozenset(
    {"home", "active_household", "active_household_lot", "household_lot"}
)
_STREET_KINDS = frozenset(
    {"street", "neighborhood", "community", "off_lot", "world_map_scenery"}
)
_WATER_KINDS = frozenset({"water", "canal", "river", "pond", "ocean", "dock"})

_WATER_TOKENS = frozenset(
    {"water", "canal", "river", "pond", "dock", "ocean", "lagoon", "marina"}
)
_STREET_TOKENS = frozenset(
    {
        "street",
        "road",
        "crosswalk",
        "sidewalk",
        "neighborhood",
        "neighbor",
        "streetlight",
        "streetlights",
        "world_map",
        "off_lot",
    }
)


def _scenery_hits(tokens: set[str], keywords: frozenset[str]) -> bool:
    """Match exact tokens or compound labels like CANAL_LEFT / STREET_RIGHT."""
    if tokens & keywords:
        return True
    for token in tokens:
        parts = {p for p in token.replace("-", "_").split("_") if p}
        if parts & keywords:
            return True
        for key in keywords:
            if key in token:
                return True
    return False


class LotFocusError(ValueError):
    pass


def _live_hud_attested(observation: Mapping[str, Any]) -> bool:
    if observation.get("live_hud_present") is True:
        return True
    if observation.get("live_hud_present") is False:
        return False
    cues = observation.get("independent_cues")
    if not isinstance(cues, list):
        return False
    for cue in cues:
        if isinstance(cue, Mapping) and cue.get("source") == "visual":
            token = str(cue.get("token") or "")
            if token in {"live_hud", "live_hud_visible", "hud_cluster"}:
                return True
    return False


def _verified_travel_goal(travel_goal: Mapping[str, Any] | None) -> bool:
    if not isinstance(travel_goal, Mapping):
        return False
    goal_id = travel_goal.get("goal_id")
    return (
        isinstance(goal_id, str)
        and 1 <= len(goal_id) <= 96
        and travel_goal.get("kind") == "LONG_DISTANCE_TRAVEL"
        and travel_goal.get("source") == "HOST_TASK"
        and travel_goal.get("destination_attested") is True
    )


def should_assess_lot_focus(
    *,
    observation: Mapping[str, Any] | None = None,
    camera_recovery: Mapping[str, Any] | None = None,
) -> bool:
    """True when host_stack should attach a lot_focus assessment this turn."""
    if camera_recovery is not None and isinstance(camera_recovery, Mapping):
        rec_obs = camera_recovery.get("observation")
        if isinstance(rec_obs, Mapping) and rec_obs.get("lot_focus_cues"):
            return True
    if not isinstance(observation, Mapping):
        return False
    if observation.get("lot_focus_cues"):
        return True
    if observation.get("zoom_mode_observed") is not None:
        return True
    if observation.get("camera_lot_kind"):
        return True
    if observation.get("camera_on_active_household_lot") is not None:
        return True
    if observation.get("scenery_off_active_lot") is True:
        return True
    return observation.get("source") == "HOST_CAPTURE"


def assess_lot_focus(
    *,
    capture_ref: str,
    observation: Mapping[str, Any] | None = None,
    travel_goal: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify lot focus from a trusted host observation. Never grants input."""
    base: dict[str, Any] = {
        "execute_allowed": False,
        "proof_ceiling": LOT_FOCUS_PROOF,
        "contract": "contracts/camera-traverse.v1.json#lot_focus",
    }

    def hold(gate: str, reason: str, **extra: object) -> dict[str, Any]:
        return {
            **base,
            "state": "UNKNOWN",
            "gate": gate,
            "reason": reason,
            "restore": None,
            **extra,
        }

    if not isinstance(capture_ref, str) or not 1 <= len(capture_ref) <= 128:
        raise LotFocusError("LOT_FOCUS_CAPTURE_REF_REQUIRED")
    if observation is not None and not isinstance(observation, Mapping):
        return hold("LOT_FOCUS_REOBSERVE", "HOST_OBSERVATION_INVALID")

    if not isinstance(observation, Mapping):
        return hold("LOT_FOCUS_REOBSERVE", "HOST_CAPTURE_OBSERVATION_REQUIRED")

    version = load_catalog()["game_version"]
    if (
        observation.get("source") != "HOST_CAPTURE"
        or observation.get("game_version") != version
    ):
        return hold("LOT_FOCUS_SCENE_UNVERIFIED", "HOST_CAPTURE_AND_BUILD_REQUIRED")

    live_hud = _live_hud_attested(observation)
    on_lot_flag = observation.get("camera_on_active_household_lot")
    lot_kind = str(observation.get("camera_lot_kind") or "").lower().strip()

    travel_afar_without_goal = False
    zoom_observed = observation.get("zoom_mode_observed")
    if zoom_observed is not None:
        try:
            if resolve_zoom_mode_alias(str(zoom_observed)) == "TRAVEL_AFAR":
                travel_afar_without_goal = not _verified_travel_goal(travel_goal)
        except Exception:
            pass
    if not travel_afar_without_goal and observation.get("scenery_off_active_lot") is True:
        travel_afar_without_goal = not _verified_travel_goal(travel_goal)

    cues = observation.get("lot_focus_cues")
    host_tokens: list[str] = []
    if isinstance(cues, list):
        for item in cues:
            if isinstance(item, Mapping) and isinstance(item.get("token"), str):
                host_tokens.append(item["token"])

    landmarks = observation.get("landmark_tokens") or observation.get("scenery_tokens")
    scenery_tokens: set[str] = set()
    if isinstance(landmarks, list):
        scenery_tokens = {str(x).lower() for x in landmarks}

    host_token_set = {str(t).lower() for t in host_tokens}
    water_hint = (
        lot_kind in _WATER_KINDS
        or _scenery_hits(scenery_tokens, _WATER_TOKENS)
        or _scenery_hits(host_token_set, _WATER_TOKENS)
        or "water_scenery" in host_tokens
        or "canal_view" in host_tokens
    )
    lot_fraction = observation.get("lot_fraction_of_frame")
    altitude = str(observation.get("camera_altitude") or "").upper()
    neighborhood_high = altitude in {
        "NEIGHBORHOOD_HIGH",
        "NEIGHBORHOOD",
        "TRAVEL_AFAR",
        "WORLD",
    } or (
        isinstance(lot_fraction, (int, float)) and 0 < float(lot_fraction) < 0.45
    )
    street_hint = (
        lot_kind in _STREET_KINDS
        or _scenery_hits(scenery_tokens, _STREET_TOKENS)
        or _scenery_hits(host_token_set, _STREET_TOKENS)
        or "street_scenery" in host_tokens
        or "neighborhood_view" in host_tokens
        or neighborhood_high
        or (travel_afar_without_goal and not live_hud)
        or (travel_afar_without_goal and on_lot_flag is False)
    )

    on_lot = False
    if travel_afar_without_goal or street_hint or water_hint:
        on_lot = False
    elif on_lot_flag is True:
        on_lot = True
    elif on_lot_flag is False:
        on_lot = False
    elif lot_kind in _ON_LOT_KINDS and live_hud:
        on_lot = True
    elif live_hud and lot_kind in _ON_LOT_KINDS:
        on_lot = True
    else:
        return hold(
            "LOT_FOCUS_UNKNOWN",
            "INSUFFICIENT_LOT_FOCUS_CUES",
            live_hud_attested=live_hud,
            cues_observed=host_tokens,
        )

    if on_lot and not street_hint and not water_hint:
        return {
            **base,
            "state": "ON_LOT",
            "gate": "LOT_FOCUS_ON_ACTIVE_HOUSEHOLD_LOT",
            "live_hud_attested": live_hud,
            "camera_lot_kind": lot_kind or None,
            "restore": None,
            "forbidden": ["UNBOUNDED_CAMERA_PAN", "STREET_ROAM"],
        }

    state = "OFF_LOT_WATER" if water_hint and not street_hint else "OFF_LOT_STREET"
    if water_hint and street_hint:
        state = "OFF_LOT_STREET"

    restore = plan_sim_camera(CENTER_SIM, capture_ref=capture_ref, observation=observation)
    zoom = assess_agent_zoom_mode(observation=observation, travel_goal=travel_goal)
    return {
        **base,
        "state": state,
        "gate": "LOT_OFF_FOCUS_RESTORE_REQUIRED",
        "reason": "CAMERA_SCENERY_NOT_ON_ACTIVE_HOUSEHOLD_LOT",
        "live_hud_attested": live_hud,
        "camera_lot_kind": lot_kind or None,
        "travel_afar_without_goal": travel_afar_without_goal,
        "zoom_policy": zoom if zoom.get("state") == "AGENT_ZOOM_RESTORE_REQUIRED" else None,
        "restore_plan": {
            "command": CENTER_SIM,
            "hotkey_id": "CENTER_ACTIVE_SIM",
            "chord": ["ENTER"],
            "forbid_default": ["SHIFT_ENTER", "CENTER_CURRENT_LOT", "UNBOUNDED_CAMERA_PAN", "STREET_ROAM"],
        },
        "restore": restore,
        "next": "ADMITTED_ENTER_CENTER_ACTIVE_SIM_THEN_REOBSERVE",
        "forbidden": ["SHIFT_ENTER_AS_DEFAULT_SIM_RESTORE", "UNBOUNDED_CAMERA_PAN", "STREET_ROAM"],
    }
