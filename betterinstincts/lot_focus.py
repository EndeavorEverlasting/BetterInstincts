"""Recognize when the camera/scenery is off the active household lot.

Policy only — no input, saves, or street roam. Restore plans use Enter
(CENTER_ACTIVE_SIM), never Shift+Enter as the default Sim restore.

Classification (``classification`` field):
  ON_LOT     household lot attested by >=2 agreeing cues (flag/kind + Live HUD
             or household interior cue) and no decisive off-lot scenery.
  OFF_LOT    neighboring houses, canal/water, neighborhood/Travel Afar zoom,
             small lot fraction, or dominant sidewalk/streetlamp scenery.
  AMBIGUOUS  insufficient or uncorroborated cues; reobserve, no restore.
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
# Decisive off-lot scenery: neighboring houses, neighborhood/world zoom classes.
_STRONG_STREET_TOKENS = frozenset(
    {
        "neighborhood",
        "neighbor",
        "neighbors",
        "neighboring",
        "world_map",
        "off_lot",
        "street_topdown",
        "full_zoom_out",
        "travel_afar",
        "street_scenery",
        "neighborhood_view",
    }
)
# Lot-edge furniture (sidewalk, streetlamp, road) also appears on a healthy
# on-lot frame. It forces OFF_LOT only when it dominates (2+ families) or when
# on-lot is not corroborated. Each token is counted in one family only.
_EDGE_FAMILIES: tuple[tuple[str, frozenset[str]], ...] = (
    (
        "lighting",
        frozenset({"streetlight", "streetlights", "streetlamp", "streetlamps", "lamppost"}),
    ),
    ("sidewalk", frozenset({"sidewalk", "curb", "pavement", "crosswalk"})),
    ("street", frozenset({"street", "road"})),
)
_STREET_TOKENS = _STRONG_STREET_TOKENS | frozenset().union(*(k for _, k in _EDGE_FAMILIES))
# Household fixtures/rooms that merely contain words like "water" or "street".
_FIXTURE_PARTS = frozenset(
    {
        "sink",
        "faucet",
        "bathtub",
        "tub",
        "shower",
        "toilet",
        "cooler",
        "aquarium",
        "dishwasher",
        "fridge",
        "kitchen",
        "bathroom",
    }
)
_HOUSEHOLD_PARTS = frozenset(
    {
        "interior",
        "kitchen",
        "living",
        "bedroom",
        "bathroom",
        "household",
        "furniture",
        "sofa",
        "counter",
        "room",
    }
)
_NEIGHBORHOOD_ALTITUDES = frozenset(
    {
        "NEIGHBORHOOD_HIGH",
        "NEIGHBORHOOD",
        "NEIGHBORHOOD_ZOOM",
        "TRAVEL_AFAR",
        "FULL_ZOOM_OUT",
        "STREET_TOPDOWN",
        "WORLD_MAP",
        "WORLD",
    }
)
_MAX_TOKENS = 64
_MAX_TOKEN_LEN = 80


def _parts(token: str) -> set[str]:
    return {p for p in token.replace("-", "_").replace(" ", "_").split("_") if p}


def _is_fixture(token: str) -> bool:
    return bool(_parts(token) & _FIXTURE_PARTS)


def _token_hits(token: str, keywords: frozenset[str]) -> bool:
    if token in keywords or _parts(token) & keywords:
        return True
    return any(key in token for key in keywords)


def _scenery_hits(tokens: set[str], keywords: frozenset[str]) -> bool:
    """Match exact tokens or compound labels like CANAL_LEFT / STREET_RIGHT.

    Household fixtures (SINK_WATER, BATHROOM_STREETLIGHT_DECOR) never count as
    outdoor scenery.
    """
    return any(_token_hits(t, keywords) for t in tokens if not _is_fixture(t))


def _edge_families(tokens: set[str]) -> set[str]:
    found: set[str] = set()
    for token in tokens:
        if _is_fixture(token):
            continue
        for name, keys in _EDGE_FAMILIES:
            if _token_hits(token, keys):
                found.add(name)
                break
    return found


def _household_cues(tokens: set[str], observation: Mapping[str, Any]) -> bool:
    if observation.get("active_sim_in_frame") is True:
        return True
    return any(_parts(t) & _HOUSEHOLD_PARTS for t in tokens)


def _bounded_tokens(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw[:_MAX_TOKENS]:
        if isinstance(item, str):
            out.append(item.lower().strip()[:_MAX_TOKEN_LEN])
    return out


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
    if observation.get("landmark_tokens") or observation.get("scenery_tokens"):
        return True
    if observation.get("camera_altitude") or observation.get("lot_fraction_of_frame") is not None:
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
            "classification": "AMBIGUOUS",
            "gate": gate,
            "reason": reason,
            "restore": None,
            "next": "REOBSERVE_WITH_SECOND_INDEPENDENT_CUE",
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
    neighborhood_zoom_label = False
    if zoom_observed is not None:
        label = str(zoom_observed).upper().replace("-", "_").replace(" ", "_")
        # TRAVEL_AFAR is decided by the verified-goal check below, not by label.
        neighborhood_zoom_label = (
            label in _NEIGHBORHOOD_ALTITUDES and label != "TRAVEL_AFAR"
        )
        try:
            if resolve_zoom_mode_alias(str(zoom_observed)) == "TRAVEL_AFAR":
                travel_afar_without_goal = not _verified_travel_goal(travel_goal)
        except Exception:
            pass
    if not travel_afar_without_goal and observation.get("scenery_off_active_lot") is True:
        travel_afar_without_goal = not _verified_travel_goal(travel_goal)

    host_tokens: list[str] = []
    cues = observation.get("lot_focus_cues")
    if isinstance(cues, list):
        for item in cues[:_MAX_TOKENS]:
            if isinstance(item, Mapping) and isinstance(item.get("token"), str):
                host_tokens.append(item["token"][:_MAX_TOKEN_LEN])

    landmarks = observation.get("landmark_tokens") or observation.get("scenery_tokens")
    scenery_tokens = set(_bounded_tokens(landmarks))
    host_token_set = {t.lower() for t in host_tokens}
    all_tokens = scenery_tokens | host_token_set

    water_hint = (
        lot_kind in _WATER_KINDS
        or _scenery_hits(all_tokens, _WATER_TOKENS)
        or "water_scenery" in host_token_set
        or "canal_view" in host_token_set
    )
    lot_fraction = observation.get("lot_fraction_of_frame")
    altitude = (
        str(observation.get("camera_altitude") or "").upper().replace("-", "_").replace(" ", "_")
    )
    small_lot_fraction = (
        isinstance(lot_fraction, (int, float))
        and not isinstance(lot_fraction, bool)
        and 0 < float(lot_fraction) < 0.45
    )
    neighborhood_high = (
        altitude in _NEIGHBORHOOD_ALTITUDES or neighborhood_zoom_label or small_lot_fraction
    )
    strong_street = (
        lot_kind in _STREET_KINDS
        or _scenery_hits(all_tokens, _STRONG_STREET_TOKENS)
        or neighborhood_high
        or (travel_afar_without_goal and not live_hud)
        or (travel_afar_without_goal and on_lot_flag is False)
    )
    edge_families = _edge_families(all_tokens)
    household = _household_cues(all_tokens, observation)
    corroborated = live_hud or household

    # Dominant lot-edge scenery (e.g. sidewalk + streetlamp) is off-lot.
    street_hint = strong_street or len(edge_families) >= 2

    evidence = {
        "live_hud_attested": live_hud,
        "household_cues": household,
        "edge_scenery_families": sorted(edge_families),
        "camera_lot_kind": lot_kind or None,
    }

    if travel_afar_without_goal or street_hint or water_hint:
        pass  # off-lot; handled below
    elif len(edge_families) == 1 and on_lot_flag is not False:
        # A lone sidewalk/streetlamp/road cue is normal at a lot edge: on-lot
        # only with corroboration, otherwise ask for another cue.
        if corroborated and (on_lot_flag is True or lot_kind in _ON_LOT_KINDS):
            return _on_lot(base, evidence, edge_scenery_ignored=True)
        return hold(
            "LOT_FOCUS_UNKNOWN",
            "LONE_EDGE_SCENERY_WITHOUT_HOUSEHOLD_CORROBORATION",
            cues_observed=host_tokens,
            **evidence,
        )
    elif len(edge_families) == 1:
        street_hint = True  # explicit off-lot flag + street furniture
    elif on_lot_flag is True or (on_lot_flag is None and lot_kind in _ON_LOT_KINDS):
        if corroborated:
            return _on_lot(base, evidence)
        return hold(
            "LOT_FOCUS_UNKNOWN",
            "ON_LOT_CLAIM_WITHOUT_LIVE_HUD_OR_HOUSEHOLD_CUE",
            cues_observed=host_tokens,
            **evidence,
        )
    elif on_lot_flag is not False:
        return hold(
            "LOT_FOCUS_UNKNOWN",
            "INSUFFICIENT_LOT_FOCUS_CUES",
            cues_observed=host_tokens,
            **evidence,
        )

    if not (travel_afar_without_goal or street_hint or water_hint):
        street_hint = True  # on_lot_flag False with no scenery detail

    state = "OFF_LOT_WATER" if water_hint and not street_hint else "OFF_LOT_STREET"

    # Off-lot scenery outranks a stale "already following the Sim" flag: a
    # follow lock that is not framing the lot would otherwise plan NO_EFFECT.
    restore_obs = dict(observation)
    follow_overridden = restore_obs.get("camera_follow_sim_id") is not None
    restore_obs["camera_follow_sim_id"] = None
    restore_obs["camera_displaced"] = True
    restore = plan_sim_camera(CENTER_SIM, capture_ref=capture_ref, observation=restore_obs)
    zoom = assess_agent_zoom_mode(observation=observation, travel_goal=travel_goal)
    return {
        **base,
        "state": state,
        "classification": "OFF_LOT",
        "gate": "LOT_OFF_FOCUS_RESTORE_REQUIRED",
        "reason": "CAMERA_SCENERY_NOT_ON_ACTIVE_HOUSEHOLD_LOT",
        "conflict": "ON_LOT_FLAG_CONTRADICTED_BY_SCENERY" if on_lot_flag is True else None,
        "follow_flag_overridden": follow_overridden,
        **evidence,
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


def _on_lot(base: dict[str, Any], evidence: dict[str, Any], **extra: object) -> dict[str, Any]:
    return {
        **base,
        "state": "ON_LOT",
        "classification": "ON_LOT",
        "gate": "LOT_FOCUS_ON_ACTIVE_HOUSEHOLD_LOT",
        **evidence,
        **extra,
        "restore": None,
        "forbidden": ["UNBOUNDED_CAMERA_PAN", "STREET_ROAM"],
    }
