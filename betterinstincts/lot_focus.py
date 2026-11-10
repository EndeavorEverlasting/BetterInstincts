"""Recognize when the camera/scenery is off the active household lot.

Policy only — no input, saves, or street roam. Restore plans use Enter
(CENTER_ACTIVE_SIM), with Shift+Enter (CENTER_CURRENT_LOT) only as an
escalation when Enter leaves street/rooftop. Travel-banner cancel uses the
fixed-ui seed, never crown/footprint. Viewport black/white is distinct and
owned by betterinstincts/viewport.py.

Classification (``classification`` field, legacy):
  ON_LOT     household lot attested by >=2 agreeing cues (flag/kind + Live HUD
             or household interior cue) and no decisive off-lot scenery.
  OFF_LOT    neighboring houses, canal/water, neighborhood/Travel Afar zoom,
             small lot fraction, or dominant sidewalk/streetlamp scenery.
  AMBIGUOUS  insufficient or uncorroborated cues; reobserve, no restore.

Scenery focus (``scenery_focus`` field, operator 2026-11-10):
  ON_LOT_INTERIOR_OR_YARD | STREET_OR_ROOFTOP_OFF_FOCUS | MANAGE_WORLDS_MAP |
  TRAVELING_WITH_BANNER | VIEWPORT_BLACK_OR_WHITE | AMBIGUOUS

Off-intent view (``assess_off_intent_view``, operator 2026-11-10):
  After a *world object* click intended for a framed object, if the post-click
  view is street/empty asphalt OR Buy/Build catalog opened → OFF_INTENT_VIEW /
  MISS_OFF_LOT. Recovery: Esc(+F1 if Buy) then Shift+Enter lot arm. Do not
  roam hardcoded field XY; re-click only from a fresh capture that shows the
  target. Buy after intended Live object click = assume clicked off — arm, do
  not explore Buy.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from betterinstincts.camera_traverse import assess_agent_zoom_mode, resolve_zoom_mode_alias
from betterinstincts.scenes import load_catalog
from betterinstincts.sim_camera import CENTER_SIM, plan_sim_camera

LOT_FOCUS_PROOF = "OFFLINE_LOT_FOCUS_POLICY_NOT_LIVE_CAMERA_CERTIFIED"
SCENERY_FOCUS_PROOF = "OFFLINE_SCENERY_FOCUS_POLICY_NOT_LIVE_CAMERA_CERTIFIED"
OFF_INTENT_VIEW_PROOF = "OFFLINE_OFF_INTENT_VIEW_POLICY_NOT_LIVE_CAMERA_CERTIFIED"

OFF_INTENT_VIEW = "OFF_INTENT_VIEW"
MISS_OFF_LOT = "MISS_OFF_LOT"

SCENERY_ON_LOT = "ON_LOT_INTERIOR_OR_YARD"
SCENERY_STREET_ROOFTOP = "STREET_OR_ROOFTOP_OFF_FOCUS"
SCENERY_MANAGE_WORLDS = "MANAGE_WORLDS_MAP"
SCENERY_TRAVELING = "TRAVELING_WITH_BANNER"
SCENERY_VIEWPORT = "VIEWPORT_BLACK_OR_WHITE"
SCENERY_AMBIGUOUS = "AMBIGUOUS"

SCENERY_FOCUS_CLASSES = frozenset(
    {
        SCENERY_ON_LOT,
        SCENERY_STREET_ROOFTOP,
        SCENERY_MANAGE_WORLDS,
        SCENERY_TRAVELING,
        SCENERY_VIEWPORT,
        SCENERY_AMBIGUOUS,
    }
)

# PrintWindow-remeasured travel-party cancel (fixed-ui-click-map v15; prior scale was 1055,33).
_TRAVEL_CANCEL_CLIENT_XY = (1055, 22)
_TRAVEL_CANCEL_CANVAS_XY = (800, 25)
_TRAVEL_CANCEL_SEED = "host.manage_worlds_travel_party_cancel_x"

_ON_LOT_KINDS = frozenset(
    {"home", "active_household", "active_household_lot", "household_lot", "yard", "interior"}
)
_STREET_KINDS = frozenset(
    {
        "street",
        "neighborhood",
        "community",
        "off_lot",
        "world_map_scenery",
        "rooftop",
        "roof",
        "lot_exterior",
    }
)
_WATER_KINDS = frozenset({"water", "canal", "river", "pond", "ocean", "dock"})
_MANAGE_WORLDS_KINDS = frozenset(
    {"manage_worlds", "world_map", "travel_map", "neighborhood_map", "map_view"}
)

_WATER_TOKENS = frozenset(
    {"water", "canal", "river", "pond", "dock", "ocean", "lagoon", "marina"}
)
_ROOFTOP_TOKENS = frozenset(
    {
        "rooftop",
        "roof",
        "rooftops",
        "overlooking",
        "lot_exterior",
        "street_rooftop",
        "exterior_overlook",
        "roof_edge",
    }
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
) | _ROOFTOP_TOKENS
_TRAVELING_TOKENS = frozenset(
    {
        "traveling_with",
        "traveling_with_banner",
        "travel_party_banner",
        "travel_with",
        "party_traveling",
        "sulani_travel_banner",
        "willow_creek_travel_banner",
    }
)
_MANAGE_WORLDS_TOKENS = frozenset(
    {
        "manage_worlds",
        "manage_world",
        "world_select",
        "travel_map",
        "neighborhood_map",
        "map_globe",
        "world_picker",
    }
)
_VIEWPORT_BLACK_WHITE = frozenset(
    {
        "FULL_CLIENT_BLACK",
        "VIEWPORT_NEAR_BLACK",
        "VIEWPORT_BLACK_HUD_ALIVE",
        "VOID_LOT_PLATFORM_WIREFRAME",
        "BUILD_BUY_CATALOG_RECOVERY",
        "FULL_CLIENT_WHITE",
        "VIEWPORT_WHITE",
        "PRINTWINDOW_WHITE",
        "BLACK",
        "WHITE",
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
        "yard",
        "garden",
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
        "ROOFTOP",
        "STREET_ROOFTOP",
    }
)
_MAX_TOKENS = 64
_MAX_TOKEN_LEN = 80

_COMMON_FORBIDDEN = [
    "UNBOUNDED_CAMERA_PAN",
    "STREET_ROAM",
    "CLICK_VOID",
    "SELL",
    "DELETE_SAVE",
    "CROWN",
    "FOOTPRINT",
]


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


def _collect_tokens(observation: Mapping[str, Any]) -> tuple[list[str], set[str]]:
    host_tokens: list[str] = []
    cues = observation.get("lot_focus_cues")
    if isinstance(cues, list):
        for item in cues[:_MAX_TOKENS]:
            if isinstance(item, Mapping) and isinstance(item.get("token"), str):
                host_tokens.append(item["token"][:_MAX_TOKEN_LEN])
    landmarks = observation.get("landmark_tokens") or observation.get("scenery_tokens")
    scenery_tokens = set(_bounded_tokens(landmarks))
    host_token_set = {t.lower() for t in host_tokens}
    return host_tokens, scenery_tokens | host_token_set


def _mode_upper(observation: Mapping[str, Any]) -> str:
    for key in ("mode", "ui_mode", "scene_mode", "host_mode"):
        raw = observation.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.upper().replace("-", "_").replace(" ", "_")
    return ""


def _viewport_anomaly(observation: Mapping[str, Any]) -> bool:
    for key in ("viewport_classification", "viewport_state", "capture_quality"):
        raw = observation.get(key)
        if not isinstance(raw, str):
            continue
        label = raw.upper().replace("-", "_").replace(" ", "_")
        if label in _VIEWPORT_BLACK_WHITE:
            return True
        if "BLACK" in label or label.endswith("_WHITE") or label == "WHITE":
            return True
    if observation.get("viewport_black") is True or observation.get("viewport_white") is True:
        return True
    return False


def _traveling_with_banner(observation: Mapping[str, Any], tokens: set[str]) -> bool:
    if observation.get("traveling_with_banner") is True:
        return True
    if observation.get("travel_party_banner") is True:
        return True
    banner = observation.get("banner_text")
    if isinstance(banner, str) and "traveling with" in banner.lower():
        return True
    return _scenery_hits(tokens, _TRAVELING_TOKENS)


def _manage_worlds_map(observation: Mapping[str, Any], tokens: set[str]) -> bool:
    mode = _mode_upper(observation)
    if mode in {"MANAGE_WORLDS", "MAP", "WORLD_MAP", "TRAVEL_MAP"}:
        return True
    lot_kind = str(observation.get("camera_lot_kind") or "").lower().strip()
    if lot_kind in _MANAGE_WORLDS_KINDS:
        return True
    if observation.get("manage_worlds") is True or observation.get("on_manage_worlds_map") is True:
        return True
    return _scenery_hits(tokens, _MANAGE_WORLDS_TOKENS)


def recovery_for_scenery_focus(scenery_focus: str) -> dict[str, Any]:
    """Machine recovery mapping for a scenery_focus class (never grants input)."""
    if scenery_focus == SCENERY_ON_LOT:
        return {
            "scenery_focus": scenery_focus,
            "action": None,
            "forbidden": list(_COMMON_FORBIDDEN),
        }
    if scenery_focus == SCENERY_STREET_ROOFTOP:
        return {
            "scenery_focus": scenery_focus,
            "primary": {
                "command": "CENTER_ACTIVE_SIM",
                "hotkey_id": "CENTER_ACTIVE_SIM",
                "chord": ["ENTER"],
            },
            "escalation": {
                "command": "CENTER_CURRENT_LOT",
                "hotkey_id": "CENTER_CURRENT_LOT",
                "chord": ["SHIFT", "ENTER"],
                "when": "ENTER_LEFT_STREET_CANAL_OR_ROOFTOP",
            },
            "forbidden": list(_COMMON_FORBIDDEN)
            + ["SHIFT_ENTER_AS_DEFAULT_SIM_RESTORE", "TERRAIN_ARM_WHILE_OFF_LOT"],
            "note": "Enter first; Shift+Enter only when Enter recenters the Sim onto street/canal/rooftop.",
        }
    if scenery_focus == SCENERY_MANAGE_WORLDS:
        return {
            "scenery_focus": scenery_focus,
            "primary": {
                "action": "EXIT_OR_CANCEL_UNINTENDED_MANAGE_WORLDS",
                "note": "Do not Enter-roam the travel map; cancel unintended travel or return to Live lot.",
            },
            "forbidden": list(_COMMON_FORBIDDEN)
            + ["ENTER_AS_MAP_ROAM", "ESC_AS_TRAVEL_CANCEL"],
        }
    if scenery_focus == SCENERY_TRAVELING:
        return {
            "scenery_focus": scenery_focus,
            "primary": {
                "action": "CANCEL_TRAVELING_WITH_PARTY",
                "seed": _TRAVEL_CANCEL_SEED,
                "client_xy": list(_TRAVEL_CANCEL_CLIENT_XY),
                "canvas_1456x840_xy": list(_TRAVEL_CANCEL_CANVAS_XY),
                "prefer": "TOP_BANNER_X",
            },
            "forbidden": list(_COMMON_FORBIDDEN)
            + ["ESC_AS_TRAVEL_CANCEL", "CLICK_BANNER_TEXT"],
            "note": "Cancel X is first circular icon after household name; never footprint or crown.",
        }
    if scenery_focus == SCENERY_VIEWPORT:
        return {
            "scenery_focus": scenery_focus,
            "primary": {
                "owner": "betterinstincts/viewport.py",
                "contract": "contracts/viewport-black.v1.json",
                "action": "VIEWPORT_RECOVERY_LADDER",
            },
            "forbidden": list(_COMMON_FORBIDDEN)
            + ["TREAT_AS_STREET_ROOFTOP", "ENTER_AS_SCENERY_RESTORE"],
            "note": "Black/white PrintWindow is distinct from street/rooftop off-focus.",
        }
    return {
        "scenery_focus": SCENERY_AMBIGUOUS,
        "action": None,
        "next": "REOBSERVE_WITH_SECOND_INDEPENDENT_CUE",
        "forbidden": list(_COMMON_FORBIDDEN),
    }


def recovery_for_off_intent_view(*, buy_or_build_opened: bool = False) -> dict[str, Any]:
    """Recovery chord when a world-object click missed into street/Buy.

    Policy only — never grants input. Esc clears overlays; F1 if Buy/Build;
    Shift+Enter arms the active lot. Forbidden: Sell, street roam, more
    hardcoded field XY, exploring Buy catalog.
    """
    steps: list[dict[str, Any]] = [
        {
            "step": "CLEAR_OVERLAYS",
            "chord": ["ESCAPE"],
            "repeat_max": 4,
            "never": ["SELL"],
        }
    ]
    if buy_or_build_opened:
        steps.append(
            {
                "step": "EXIT_BUY_BUILD_TO_LIVE",
                "chord": ["F1"],
                "never": ["SELL", "GALLERY", "EXPLORE_BUY_CATALOG"],
            }
        )
    steps.append(
        {
            "step": "ARM_ACTIVE_LOT",
            "command": "CENTER_CURRENT_LOT",
            "hotkey_id": "CENTER_CURRENT_LOT",
            "chord": ["SHIFT", "ENTER"],
            "note": "Shift+Enter is the arm after OFF_INTENT_VIEW miss — not roam, not hardcoded field XY.",
        }
    )
    steps.append(
        {
            "step": "CONFIRM_PAUSED",
            "chord": ["0"],
            "forbidden": ["PLAY", "1", "2", "3", "UNPAUSE"],
        }
    )
    return {
        "flag": OFF_INTENT_VIEW,
        "classification": MISS_OFF_LOT,
        "order": steps,
        "next": "REOBSERVE_PRINTWINDOW_FOR_TARGET_THEN_CLICK_ONLY_IF_VISIBLE",
        "blocked_if_target_absent": "BLOCKED_NEED_OPERATOR_FRAME",
        "forbidden": list(_COMMON_FORBIDDEN)
        + [
            "HARDCODED_FIELD_XY_AFTER_MISS",
            "EXPLORE_BUY_CATALOG",
            "STREET_ROAM",
            "SELL",
            "PLAY_WHILE_PARTS_GATE",
            "CLICK_WITHOUT_TARGET_IN_CURRENT_CAPTURE",
        ],
        "proof_ceiling": OFF_INTENT_VIEW_PROOF,
    }


def assess_off_intent_view(
    *,
    observation: Mapping[str, Any] | None = None,
    intent: str | None = None,
) -> dict[str, Any]:
    """Detect OFF_INTENT_VIEW / MISS_OFF_LOT after an intended Live world-object click.

    Triggers when ``intent`` is a world-object click (or observation says so) AND
    post-click cues show street/empty asphalt OR Buy/Build catalog. Camera-relative
    object clicks are not durable as hardcoded field XY across zoom.
    """
    obs = observation if isinstance(observation, Mapping) else {}
    intent_s = str(intent or obs.get("click_intent") or obs.get("intent") or "").strip().upper()
    world_object_intent = intent_s in {
        "WORLD_OBJECT",
        "LIVE_WORLD_OBJECT",
        "OBJECT_PIE",
        "ROBOTICS_WORKSTATION",
        "COMPUTER",
        "FRIDGE",
    } or obs.get("intended_world_object_click") is True

    buy_open = bool(
        obs.get("buy_mode") is True
        or obs.get("build_mode") is True
        or obs.get("buy_catalog_open") is True
        or obs.get("build_buy_catalog_open") is True
        or str(obs.get("ui_mode") or "").strip().lower() in {"buy", "build", "build_buy"}
    )
    street_or_empty = bool(
        obs.get("street_empty_asphalt") is True
        or obs.get("empty_asphalt") is True
        or obs.get("post_click_view") in {"street", "empty_asphalt", "canal", "water", "off_lot"}
        or str(obs.get("scenery_focus") or "") == SCENERY_STREET_ROOFTOP
        or str(obs.get("classification") or "") == "OFF_LOT"
    )
    # Token / kind hints
    host, tokens = _collect_tokens(obs) if obs else ([], set())
    token_blob = " ".join(host)
    if any(t in tokens for t in ("street", "asphalt", "sidewalk", "canal", "off_lot", "neighborhood")):
        street_or_empty = True
    if "buy" in token_blob or "build_buy" in token_blob or "catalog" in token_blob:
        buy_open = True

    base = {
        "ok": True,
        "flag": None,
        "classification": None,
        "triggered": False,
        "proof_ceiling": OFF_INTENT_VIEW_PROOF,
        "world_object_intent": world_object_intent,
        "buy_or_build_opened": buy_open,
        "street_or_empty_asphalt": street_or_empty,
    }
    if not world_object_intent:
        return {
            **base,
            "reason": "NO_WORLD_OBJECT_CLICK_INTENT",
            "next": "NO_OFF_INTENT_CHECK",
        }
    if not (buy_open or street_or_empty):
        return {
            **base,
            "reason": "POST_CLICK_VIEW_NOT_OFF_INTENT",
            "next": "CONTINUE_IF_TARGET_VISIBLE_IN_CURRENT_CAPTURE",
        }

    recovery = recovery_for_off_intent_view(buy_or_build_opened=buy_open)
    return {
        **base,
        "ok": False,
        "triggered": True,
        "flag": OFF_INTENT_VIEW,
        "classification": MISS_OFF_LOT,
        "reason": (
            "BUY_BUILD_AFTER_WORLD_OBJECT_CLICK"
            if buy_open
            else "STREET_OR_EMPTY_ASPHALT_AFTER_WORLD_OBJECT_CLICK"
        ),
        "gate": "OFF_INTENT_VIEW_ARM_REQUIRED",
        "recovery": recovery,
        "next": recovery["next"],
        "forbidden": recovery["forbidden"],
        "note": (
            "Buy/Build after intended Live object click = assume clicked off; "
            "run Esc(+F1)+Shift+Enter arm — do not explore Buy. "
            "Hardcoded field XY are not durable across zoom."
        ),
    }


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
    if observation.get("traveling_with_banner") is True or observation.get("travel_party_banner") is True:
        return True
    if observation.get("manage_worlds") is True or observation.get("on_manage_worlds_map") is True:
        return True
    if _viewport_anomaly(observation):
        return True
    mode = _mode_upper(observation)
    if mode in {"MANAGE_WORLDS", "MAP", "WORLD_MAP", "TRAVEL_MAP"}:
        return True
    return observation.get("source") == "HOST_CAPTURE"


def assess_lot_focus(
    *,
    capture_ref: str,
    observation: Mapping[str, Any] | None = None,
    travel_goal: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify lot/scenery focus from a trusted host observation. Never grants input."""
    base: dict[str, Any] = {
        "execute_allowed": False,
        "proof_ceiling": LOT_FOCUS_PROOF,
        "scenery_focus_proof_ceiling": SCENERY_FOCUS_PROOF,
        "contract": "contracts/camera-traverse.v1.json#lot_focus",
    }

    def hold(gate: str, reason: str, **extra: object) -> dict[str, Any]:
        scenery = str(extra.pop("scenery_focus", SCENERY_AMBIGUOUS))
        if scenery not in SCENERY_FOCUS_CLASSES:
            scenery = SCENERY_AMBIGUOUS
        out = {
            **base,
            "state": "UNKNOWN",
            "classification": "AMBIGUOUS",
            "scenery_focus": scenery,
            "gate": gate,
            "reason": reason,
            "restore": None,
            "recovery": recovery_for_scenery_focus(scenery),
            "next": "REOBSERVE_WITH_SECOND_INDEPENDENT_CUE",
            **extra,
        }
        return out

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

    host_tokens, all_tokens = _collect_tokens(observation)

    # Priority 1: black/white viewport (distinct from scenery off-lot).
    if _viewport_anomaly(observation):
        return {
            **base,
            "state": "VIEWPORT_BLACK_OR_WHITE",
            "classification": "AMBIGUOUS",
            "scenery_focus": SCENERY_VIEWPORT,
            "gate": "VIEWPORT_RECOVERY_REQUIRED",
            "reason": "VIEWPORT_BLACK_OR_WHITE_DISTINCT_FROM_LOT_SCENERY",
            "cues_observed": host_tokens,
            "restore": None,
            "recovery": recovery_for_scenery_focus(SCENERY_VIEWPORT),
            "next": "RUN_VIEWPORT_RECOVERY_LADDER_THEN_REOBSERVE",
            "forbidden": recovery_for_scenery_focus(SCENERY_VIEWPORT)["forbidden"],
        }

    # Priority 2: TRAVELING WITH party banner (Manage Worlds stuck travel).
    if _traveling_with_banner(observation, all_tokens):
        recovery = recovery_for_scenery_focus(SCENERY_TRAVELING)
        return {
            **base,
            "state": "TRAVELING_WITH_BANNER",
            "classification": "OFF_LOT",
            "scenery_focus": SCENERY_TRAVELING,
            "gate": "TRAVEL_PARTY_CANCEL_REQUIRED",
            "reason": "TRAVELING_WITH_BANNER_NOT_HOUSEHOLD_LOT_FOCUS",
            "cues_observed": host_tokens,
            "restore": None,
            "restore_plan": None,
            "recovery": recovery,
            "next": "ADMITTED_CLICK_TRAVEL_PARTY_CANCEL_X_THEN_REOBSERVE",
            "forbidden": recovery["forbidden"],
        }

    # Priority 3: Manage Worlds / travel map (without traveling banner).
    if _manage_worlds_map(observation, all_tokens):
        recovery = recovery_for_scenery_focus(SCENERY_MANAGE_WORLDS)
        return {
            **base,
            "state": "MANAGE_WORLDS_MAP",
            "classification": "OFF_LOT",
            "scenery_focus": SCENERY_MANAGE_WORLDS,
            "gate": "MANAGE_WORLDS_FOCUS_RESTORE_REQUIRED",
            "reason": "MANAGE_WORLDS_MAP_NOT_HOUSEHOLD_LOT_FOCUS",
            "cues_observed": host_tokens,
            "restore": None,
            "restore_plan": None,
            "recovery": recovery,
            "next": "EXIT_MANAGE_WORLDS_OR_CANCEL_UNINTENDED_TRAVEL_THEN_REOBSERVE",
            "forbidden": recovery["forbidden"],
        }

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

    water_hint = (
        lot_kind in _WATER_KINDS
        or _scenery_hits(all_tokens, _WATER_TOKENS)
        or "water_scenery" in {t.lower() for t in host_tokens}
        or "canal_view" in {t.lower() for t in host_tokens}
    )
    rooftop_hint = (
        lot_kind in {"rooftop", "roof", "lot_exterior"}
        or _scenery_hits(all_tokens, _ROOFTOP_TOKENS)
        or observation.get("street_rooftop_overlook") is True
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
        or rooftop_hint
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
        "rooftop_hint": rooftop_hint,
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
    if rooftop_hint and not water_hint:
        state = "OFF_LOT_STREET"

    recovery = recovery_for_scenery_focus(SCENERY_STREET_ROOFTOP)

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
        "scenery_focus": SCENERY_STREET_ROOFTOP,
        "gate": "LOT_OFF_FOCUS_RESTORE_REQUIRED",
        "reason": "CAMERA_SCENERY_NOT_ON_ACTIVE_HOUSEHOLD_LOT",
        "conflict": "ON_LOT_FLAG_CONTRADICTED_BY_SCENERY" if on_lot_flag is True else None,
        "follow_flag_overridden": follow_overridden,
        **evidence,
        "travel_afar_without_goal": travel_afar_without_goal,
        "zoom_policy": zoom if zoom.get("state") == "AGENT_ZOOM_RESTORE_REQUIRED" else None,
        "restore_plan": {
            "command": "CENTER_ACTIVE_SIM",
            "hotkey_id": "CENTER_ACTIVE_SIM",
            "chord": ["ENTER"],
            "escalation_chord": ["SHIFT", "ENTER"],
            "escalation_when": "ENTER_LEFT_STREET_CANAL_OR_ROOFTOP",
            "forbid_default": [
                "SHIFT_ENTER",
                "CENTER_CURRENT_LOT",
                "UNBOUNDED_CAMERA_PAN",
                "STREET_ROAM",
                "CROWN",
                "FOOTPRINT",
                "SELL",
                "DELETE_SAVE",
            ],
            "note": "Shift+Enter is forbidden as the default Sim restore; use recovery.escalation only when Enter leaves street/canal/rooftop.",
        },
        "restore": restore,
        "recovery": recovery,
        "next": "ADMITTED_ENTER_CENTER_ACTIVE_SIM_THEN_REOBSERVE",
        "forbidden": recovery["forbidden"],
    }


def _on_lot(base: dict[str, Any], evidence: dict[str, Any], **extra: object) -> dict[str, Any]:
    recovery = recovery_for_scenery_focus(SCENERY_ON_LOT)
    return {
        **base,
        "state": "ON_LOT",
        "classification": "ON_LOT",
        "scenery_focus": SCENERY_ON_LOT,
        "gate": "LOT_FOCUS_ON_ACTIVE_HOUSEHOLD_LOT",
        **evidence,
        **extra,
        "restore": None,
        "recovery": recovery,
        "forbidden": recovery["forbidden"],
    }
