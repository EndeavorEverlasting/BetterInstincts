"""Household lot FOOTPRINT / BOUNDARY admission (P00/P01).

Agents must know where the house ends before Live world clicks. Street,
asphalt, neighbor lots, canal, and Buy thrash are OUTSIDE. Pure policy —
no SendInput.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "lot-boundary.v1.json"
MAX_BYTES = 64_000
PROOF = "CONTRACT_HARNESS_NOT_LIVE_FOOTPRINT_MEASURE_NOT_BI002_CLOSE"

INSIDE_ZONES = frozenset({"INTERIOR", "YARD"})
OUTSIDE_ZONES = frozenset({"STREET", "WATER", "NEIGHBOR"})


class LotBoundaryError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise LotBoundaryError("LOT_BOUNDARY_CONTRACT_UNSAFE")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.lot-boundary/v1":
        raise LotBoundaryError("INVALID_LOT_BOUNDARY_SCHEMA")
    stack = data.get("authority_stack") or []
    if not isinstance(stack, list) or "MEASURED_FOOTPRINT_AABB_CAMERA_REVISION_BOUND" not in stack:
        raise LotBoundaryError("FOOTPRINT_AUTHORITY_MISSING")
    return data


def _norm_zone(zone: Optional[str]) -> str:
    z = str(zone or "UNKNOWN").upper()
    aliases = {
        "ASPHALT": "STREET",
        "SIDEWALK": "STREET",
        "ROAD": "STREET",
        "CANAL": "WATER",
        "CREEK": "WATER",
        "OFF_LOT": "STREET",
        "HOUSE": "INTERIOR",
        "INDOOR": "INTERIOR",
        "OUTDOOR_YARD": "YARD",
        "GARDEN": "YARD",
    }
    return aliases.get(z, z)


def point_in_aabb(client_xy: Sequence[int], aabb: Mapping[str, Any]) -> bool:
    if not isinstance(client_xy, (list, tuple)) or len(client_xy) != 2:
        return False
    try:
        x, y = int(client_xy[0]), int(client_xy[1])
        x0, y0 = int(aabb["x0"]), int(aabb["y0"])
        x1, y1 = int(aabb["x1"]), int(aabb["y1"])
    except (KeyError, TypeError, ValueError):
        return False
    if x0 > x1 or y0 > y1:
        return False
    return x0 <= x <= x1 and y0 <= y <= y1


def assess_lot_boundary(
    *,
    observation: Optional[Mapping[str, Any]] = None,
    lot_focus: Optional[Mapping[str, Any]] = None,
    cfg: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Classify whether the current frame is inside the household footprint."""
    cfg = cfg or load_contract()
    obs = observation if isinstance(observation, Mapping) else {}
    focus = lot_focus if isinstance(lot_focus, Mapping) else {}

    buy_open = bool(
        obs.get("buy_catalog_open")
        or obs.get("build_buy_open")
        or obs.get("mode") in {"BUY", "BUILD"}
    )
    census_lease = bool(obs.get("build_census_lease"))
    classification = str(
        focus.get("classification")
        or obs.get("lot_classification")
        or obs.get("classification")
        or ""
    ).upper()
    scenery = str(focus.get("scenery_focus") or obs.get("scenery_focus") or "").upper()
    zones_raw = obs.get("visible_zones") or obs.get("zones") or []
    zones = {_norm_zone(z) for z in zones_raw if z}
    tokens = {str(t).upper() for t in (obs.get("scenery_tokens") or [])}
    if tokens & {"STREET", "ASPHALT", "SIDEWALK", "ROAD", "OFF_LOT"}:
        zones.add("STREET")
    if tokens & {"WATER", "CANAL", "CREEK"}:
        zones.add("WATER")
    if tokens & {"NEIGHBOR", "NEIGHBORING_HOUSE"}:
        zones.add("NEIGHBOR")
    if tokens & {"INTERIOR", "FLOOR_GRID", "FURNITURE"}:
        zones.add("INTERIOR")
    if tokens & {"YARD", "PLANTER", "HYDROPONIC", "FENCE_INSIDE"}:
        zones.add("YARD")

    aabb = obs.get("footprint_aabb") if isinstance(obs.get("footprint_aabb"), Mapping) else None
    camera_revision = obs.get("camera_revision")
    aabb_ok = False
    if aabb is not None:
        aabb_rev = aabb.get("camera_revision")
        aabb_ok = (
            isinstance(camera_revision, str)
            and isinstance(aabb_rev, str)
            and aabb_rev == camera_revision
            and all(k in aabb for k in ("x0", "y0", "x1", "y1"))
        )

    outside_visible = bool(zones & OUTSIDE_ZONES)
    inside_visible = bool(zones & INSIDE_ZONES)

    if buy_open and not census_lease:
        return {
            "state": "BUY_BUILD_WITHOUT_CENSUS",
            "inside_footprint": False,
            "gate": "LOT_BOUNDARY_BUY_WITHOUT_CENSUS",
            "zones": sorted(zones),
            "footprint_aabb_usable": aabb_ok,
            "admit_world_clicks": False,
            "recovery": ["ESC", "F1", "CONFIRM_LIVE_HUD"],
            "forbidden": list(
                (cfg.get("gates") or {})
                .get("LOT_BOUNDARY_BUY_WITHOUT_CENSUS", {})
                .get("forbid")
                or []
            ),
            "next": "EXIT_BUY_TO_LIVE_THEN_REOBSERVE_ON_LOT",
            "proof_ceiling": PROOF,
        }

    if classification in {"OFF_LOT", "MISS_OFF_LOT"} or scenery in {
        "STREET_OR_ROOFTOP_OFF_FOCUS",
        "MANAGE_WORLDS_MAP",
        "TRAVELING_WITH_BANNER",
    }:
        return {
            "state": "OUTSIDE_FOOTPRINT",
            "inside_footprint": False,
            "gate": "LOT_BOUNDARY_OUTSIDE_FOOTPRINT",
            "zones": sorted(zones) or ["STREET"],
            "lot_focus_classification": classification or None,
            "scenery_focus": scenery or None,
            "footprint_aabb_usable": aabb_ok,
            "admit_world_clicks": False,
            "recovery": ["ESC", "F1_IF_BUY", "SHIFT_ENTER", "REOBSERVE_ON_LOT"],
            "forbidden": list(cfg.get("forbidden_always") or []),
            "next": "RESTORE_ON_LOT_BEFORE_ANY_WORLD_CLICK",
            "proof_ceiling": PROOF,
        }

    if outside_visible and not inside_visible and classification != "ON_LOT":
        return {
            "state": "OUTSIDE_FOOTPRINT",
            "inside_footprint": False,
            "gate": "LOT_BOUNDARY_OUTSIDE_FOOTPRINT",
            "zones": sorted(zones),
            "footprint_aabb_usable": aabb_ok,
            "admit_world_clicks": False,
            "recovery": ["SHIFT_ENTER", "REOBSERVE_ON_LOT"],
            "forbidden": list(cfg.get("forbidden_always") or []),
            "next": "RESTORE_ON_LOT_BEFORE_ANY_WORLD_CLICK",
            "proof_ceiling": PROOF,
        }

    if classification == "ON_LOT" or (inside_visible and not outside_visible):
        return {
            "state": "INSIDE_FOOTPRINT",
            "inside_footprint": True,
            "gate": None,
            "zones": sorted(zones) or ["INTERIOR"],
            "lot_focus_classification": classification or "ON_LOT",
            "footprint_aabb_usable": aabb_ok,
            "footprint_aabb": dict(aabb) if aabb_ok else None,
            "admit_world_clicks": True,
            "note": "Point-level admit still required via admit_world_click_in_footprint",
            "forbidden": ["STREET_ROAM", "CLICK_OUTSIDE_AABB_WHEN_MEASURED"],
            "next": "ADMIT_POINT_CHECK_THEN_WORLD_CLICK",
            "proof_ceiling": PROOF,
        }

    return {
        "state": "AMBIGUOUS_FOOTPRINT",
        "inside_footprint": False,
        "gate": "LOT_BOUNDARY_AMBIGUOUS",
        "zones": sorted(zones),
        "footprint_aabb_usable": aabb_ok,
        "admit_world_clicks": False,
        "forbidden": ["BLIND_WORLD_CLICK"],
        "next": "BLOCKED_NEED_OPERATOR_FRAME_OR_REMEASURE_FOOTPRINT",
        "proof_ceiling": PROOF,
    }


def admit_world_click_in_footprint(
    *,
    client_xy: Sequence[int],
    observation: Optional[Mapping[str, Any]] = None,
    lot_focus: Optional[Mapping[str, Any]] = None,
    click_zone: Optional[str] = None,
    cfg: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Fail-closed: admit a Live world click only inside the household footprint."""
    cfg = cfg or load_contract()
    boundary = assess_lot_boundary(
        observation=observation, lot_focus=lot_focus, cfg=cfg
    )
    zone = _norm_zone(click_zone)
    obs = observation if isinstance(observation, Mapping) else {}

    if not boundary.get("admit_world_clicks"):
        return {
            "admit": False,
            "gate": boundary.get("gate") or "LOT_BOUNDARY_OUTSIDE_FOOTPRINT",
            "boundary": boundary,
            "client_xy": list(client_xy) if isinstance(client_xy, (list, tuple)) else None,
            "click_zone": zone,
            "forbidden": list(boundary.get("forbidden") or [])
            + ["WORLD_OBJECT_CLICK", "HARDCODED_FIELD_XY"],
            "recovery": list(boundary.get("recovery") or ["SHIFT_ENTER"]),
            "next": boundary.get("next"),
            "proof_ceiling": PROOF,
        }

    if zone in OUTSIDE_ZONES:
        return {
            "admit": False,
            "gate": "LOT_BOUNDARY_OUTSIDE_FOOTPRINT",
            "boundary": boundary,
            "client_xy": [int(client_xy[0]), int(client_xy[1])],
            "click_zone": zone,
            "reason": "CLICK_ZONE_OUTSIDE_HOUSE",
            "forbidden": list(cfg.get("forbidden_always") or []),
            "recovery": ["SHIFT_ENTER", "REOBSERVE_ON_LOT"],
            "next": "DO_NOT_CLICK_STREET_WATER_OR_NEIGHBOR",
            "proof_ceiling": PROOF,
        }

    aabb = boundary.get("footprint_aabb")
    if boundary.get("footprint_aabb_usable") and isinstance(aabb, Mapping):
        if not point_in_aabb(client_xy, aabb):
            return {
                "admit": False,
                "gate": "LOT_BOUNDARY_OUTSIDE_FOOTPRINT",
                "boundary": boundary,
                "client_xy": [int(client_xy[0]), int(client_xy[1])],
                "click_zone": zone,
                "reason": "CLIENT_XY_OUTSIDE_MEASURED_FOOTPRINT_AABB",
                "forbidden": list(cfg.get("forbidden_always") or []),
                "recovery": ["SHIFT_ENTER", "REOBSERVE_ON_LOT"],
                "next": "CLICK_ONLY_INSIDE_FOOTPRINT_AABB",
                "proof_ceiling": PROOF,
            }

    if zone == "UNKNOWN" and not boundary.get("footprint_aabb_usable"):
        # ON_LOT frame but unknown point zone and no AABB → require explicit inside zone
        if obs.get("operator_attests_inside_footprint") is not True:
            return {
                "admit": False,
                "gate": "LOT_BOUNDARY_AMBIGUOUS",
                "boundary": boundary,
                "client_xy": [int(client_xy[0]), int(client_xy[1])]
                if isinstance(client_xy, (list, tuple)) and len(client_xy) == 2
                else None,
                "click_zone": zone,
                "reason": "POINT_ZONE_UNKNOWN_WITHOUT_AABB",
                "forbidden": ["BLIND_WORLD_CLICK"],
                "next": "REQUIRE_CLICK_ZONE_INTERIOR_OR_YARD_OR_MEASURE_AABB",
                "proof_ceiling": PROOF,
            }

    return {
        "admit": True,
        "gate": None,
        "boundary": boundary,
        "client_xy": [int(client_xy[0]), int(client_xy[1])],
        "click_zone": zone if zone != "UNKNOWN" else "INTERIOR_OR_YARD_IMPLIED",
        "forbidden": ["STREET_ROAM", "ACTIVATE_SERVO"],
        "next": "WORLD_CLICK_ADMITTED_INSIDE_FOOTPRINT",
        "proof_ceiling": PROOF,
        "cardinal_semantics_allowed": True,
    }
