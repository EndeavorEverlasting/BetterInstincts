"""ROOM_MAP_TRAVERSE — named-goal camera-away room scan into a floor graph.

Default agent posture remains active-Sim center. A fresh named map lease may
leave that center to pan/zoom/analyze world objects, upsert graph nodes/edges
into the profile lot floor map, then restore Enter. Pure planner — no SendInput.
"""
from __future__ import annotations

from typing import Mapping, Optional, Sequence

from betterinstincts.camera_traverse import (
    CameraTraverseError,
    load_contract as load_camera_contract,
    plan_object_pick_identify,
    plan_traverse,
)
from betterinstincts.lot_floor_map import LotFloorMapError, load_contract as load_floor_contract
from betterinstincts.household_navigation import plan_household_navigation

PROOF = "OFFLINE_ROOM_MAP_TRAVERSE_PLAN_PLUS_LOCAL_GRAPH_STORE_NOT_LIVE_CLICK_CERT"

# Compass ring for one room cell expansion (N→clockwise). Bounded; not street roam.
RING_DIRECTIONS: tuple[str, ...] = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")

DEFAULT_LANDMARK_HINT = {
    "goal_id": "map_corner_workbench",
    "target_kind": "ROBOTICS_WORKSTATION",
    "seed_landmarks": (
        "LANDMARK_DINING_TABLE",
        "LANDMARK_RUG_CLUSTER",
    ),
    "adjacency_note": (
        "Corner of room: overlapping rugs + dinner table → workbench/robotics. "
        "Cardinal FALLBACK (lot-cardinal-semantics): ~90° from FRONT_DOOR; "
        "GRAY body + Gardener-Bot needs fix; never Activate pending Servo; "
        "never blue Atmospheric Water Generator."
    ),
    "cardinal_owner": "contracts/lot-cardinal-semantics.v1.json",
}


def _cfg_room(cfg: Mapping[str, object] | None = None) -> dict:
    data = dict(cfg or load_camera_contract())
    row = data.get("room_map_traverse")
    if not isinstance(row, Mapping):
        raise CameraTraverseError("ROOM_MAP_TRAVERSE_MISSING")
    return dict(row)


def plan_room_map_traverse(
    *,
    goal_id: str,
    target_kind: str,
    target_id: str | None = None,
    seed_landmarks: Sequence[str] = (),
    adjacency_note: str = "",
    max_pan_steps: int | None = None,
    observation: Mapping[str, object] | None = None,
    cfg: Mapping[str, object] | None = None,
    floor_cfg: Mapping[str, object] | None = None,
) -> dict:
    """Plan: dismiss overlay → optional anchor → ENVIRONMENT_NAV ring scan →
    identify → upsert graph → OBJECT_PICK_IDENTIFY on target → restore Enter.

    execute_allowed is always false. Directions are host-observed later; this
    returns the algorithm skeleton and seed graph edges only.
    """
    room = _cfg_room(cfg)
    floor = dict(floor_cfg or load_floor_contract())
    kinds = set(floor.get("object_kinds") or [])
    if not isinstance(goal_id, str) or not 1 <= len(goal_id) <= 96:
        raise CameraTraverseError("ROOM_MAP_GOAL_ID_REQUIRED")
    if target_kind not in kinds:
        raise LotFloorMapError("UNKNOWN_OBJECT_KIND:" + str(target_kind))
    tid = str(target_id or target_kind.lower())
    seeds = [str(s) for s in (seed_landmarks or room.get("default_seed_landmarks") or ())]
    for sk in seeds:
        if sk not in kinds:
            raise LotFloorMapError("UNKNOWN_OBJECT_KIND:" + sk)

    max_steps = int(
        max_pan_steps
        if max_pan_steps is not None
        else room.get("max_pan_steps")
        or 8
    )
    if max_steps < 1 or max_steps > 8:
        raise CameraTraverseError("ROOM_MAP_PAN_BUDGET_INVALID")

    # One bounded ring plan (capture-first); host fills actual dirs from sight.
    ring = list(RING_DIRECTIONS[:max_steps])
    traverse = plan_traverse(ring[:1], zoom_notches=0, cfg=cfg)  # sample shape
    pick = plan_object_pick_identify(target_id=tid, observation=observation, cfg=cfg)

    steps = list(room.get("steps") or [
        "REQUIRE_NAMED_MAP_GOAL",
        "LOAD_MEMORIALIZED_GRAPH",
        "DISMISS_BLOCKING_OVERLAY",
        "ENTER_BUILD_OBSERVE_ONLY",
        "CAMERA_BUILD_TOP_DOWN_T",
        "ZOOM_OUT_UNTIL_ROOM_CENSUS_VISIBLE",
        "CAPTURE_OBSERVE_ONLY_STALE_OR_UNKNOWN_NODES",
        "UPSERT_GRAPH_NODES_EDGES",
        "MEMORIALIZE_NEW_MAPPED_ITEMS",
        "ON_ERRONEOUS_GRAB_ESCAPE_AND_RESUME",
        "OPTIONAL_LOCAL_LIBRARY_SAVE_FOLDER_ONLY_NO_GALLERY",
        "EXIT_BUILD_F1_RESTORE_LIVE",
        "SAFE_CURSOR_REST",
        "AT_INTERACT_TIME_ASSESS_EXPECTED_INTERACTIONS",
        "IF_EXPECTED_MISSING_INVALIDATE_AND_REMAP_NODE",
    ])

    seed_nodes = [
        {
            "node_id": sk.lower(),
            "kind": sk,
            "status": "SKELETON",
            "role": "LANDMARK",
        }
        for sk in seeds
    ]
    seed_nodes.append(
        {
            "node_id": tid,
            "kind": target_kind,
            "status": "SKELETON",
            "role": "TARGET",
        }
    )
    seed_edges = []
    if len(seeds) >= 2:
        seed_edges.append(
            {
                "from": seeds[0].lower(),
                "to": seeds[1].lower(),
                "direction": "OVERLAP",
                "relation": "COLOCATED_LANDMARK",
            }
        )
    if seeds:
        seed_edges.append(
            {
                "from": seeds[-1].lower(),
                "to": tid,
                "direction": "E",
                "relation": "CORNER_OF",
                "pan_hint": ["E", "SE"],
            }
        )

    return {
        "schema": "betterinstincts.room-map-traverse.plan/v1",
        "state": "ROOM_MAP_TRAVERSE_PLAN_READY",
        "gate": "ROOM_MAP_TRAVERSE",
        "goal_id": goal_id,
        "target_kind": target_kind,
        "target_id": tid,
        "zoom_mode_target": room.get("zoom_mode_target") or "BUILD_TOP_DOWN_MAP",
        "primary_census": room.get("primary_census") or "BUILD_TOP_DOWN_T",
        "observe_only": True,
        "input_policy": dict(room.get("input_policy") or {
            "preferred_channel": "SELECT_INSPECT_THEN_ESCAPE",
            "allow_during_census": ["LMB_SELECT_INSPECT", "ESCAPE"],
            "forbid_during_census": ["LMB_DRAG_MOVE", "CATALOG_PURCHASE", "PAN_OR_REZOOM_AFTER_ROOM_FIT"],
        }),
        "census_inspect": dict(room.get("census_inspect") or {
            "id": "BUILD_SELECT_INSPECT_ESCAPE",
            "preserve_camera": True,
        }),
        "on_erroneous_grab": dict(room.get("on_erroneous_grab") or {
            "action": ["ESCAPE", "RESUME_SELECT_INSPECT_ESCAPE_MAPPING"],
        }),
        "map_lease_ms_max": int(room.get("map_lease_ms_max") or 30_000),
        "max_pan_steps": max_steps,
        "ring_directions": ring,
        "steps": steps,
        "seed_graph": {"nodes": seed_nodes, "edges": seed_edges},
        "adjacency_note": str(adjacency_note or room.get("default_adjacency_note") or ""),
        "traverse_sample": {
            "state": traverse.get("state"),
            "terminal_safe_rest_required": True,
        },
        "object_pick": {
            "gate": pick.get("gate"),
            "zoom_actuator": pick.get("zoom_actuator"),
            "note": "Live object-pick is separate from Build top-down graph census",
        },
        "forbidden": list(room.get("forbidden") or [
            "UNBOUNDED_CAMERA_PAN",
            "LEAVE_CAMERA_ON_STREET",
            "MAP_TRAVERSE_WITHOUT_NAMED_GOAL",
            "FORGET_RESTORE_AFTER_MAP_LEASE",
            "EDGE_MOUSE_PARK",
            "MUTATE_LOT_WHILE_MAPPING",
            "LMB_LOT_OBJECTS_DURING_MAP_CENSUS",
            "CONTINUE_AFTER_GRAB_WITHOUT_ESCAPE",
            "GALLERY_SHARE_OR_EA_CONNECT",
            "ONLINE_FEATURES",
            "ARBITRARY_LIVE_PERSPECTIVE_CLICK_AS_GRAPH_AUTHORITY",
        ]),
        "execute_allowed": False,
        "proof_ceiling": room.get("proof_ceiling") or PROOF,
        "note": (
            "Build F3 → T top-down → BUILD_TOP_DOWN_MAP room-fit (preserve "
            "operator-centered frame) → Select-click → bottom-right params → "
            "document → Escape → next. On grab → Escape → resume. No Gallery/"
            "online. F1 restores Live."
        ),
    }


def next_ring_direction(
    *,
    visited: Sequence[str],
    preferred: Sequence[str] = (),
) -> Optional[str]:
    """Pick the next unvisited compass cell (preferred first, then ring order)."""
    seen = {str(d).upper() for d in visited}
    for d in list(preferred) + list(RING_DIRECTIONS):
        key = str(d).upper()
        if key in RING_DIRECTIONS and key not in seen:
            return key
    return None


def plan_semantic_region_route(*, snapshot: Mapping[str, object]) -> dict:
    """P01: region-graph route; camera ring cannot certify Sim travel."""
    return plan_household_navigation(snapshot)


__all__ = [
    "PROOF",
    "RING_DIRECTIONS",
    "DEFAULT_LANDMARK_HINT",
    "plan_room_map_traverse",
    "next_ring_direction",
    "plan_semantic_region_route",
    "plan_semantic_3d_target",
]


def plan_semantic_3d_target(
    *,
    spatial_map: Mapping[str, object],
    camera_calibration: Mapping[str, object] | None,
    object_id: str,
    active_floor_id: str,
    camera_revision: str,
    capture_ref: str,
    visibility: Mapping[str, object] | None = None,
) -> dict:
    """P95: world XYZ + floor + camera-local projection -> advisory room target.

    Does not own the sensor, actual camera motion, click admission or game queue.
    """
    from betterinstincts.semantic_spatial_map import plan_spatial_target
    return plan_spatial_target(
        spatial_map, camera_calibration,
        object_id=object_id,
        requested_floor=active_floor_id,
        camera_revision=camera_revision,
        capture_ref=capture_ref,
        visibility=visibility,
    )
