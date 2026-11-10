"""Lot cardinal semantics — FALLBACK navigation intuition (P00/P01).

Preferred authority remains authorized EA save/Tray parse, then the profile
``lot_floor_map`` graph. This module encodes corner/side relations and
workstation / library-search gates so chat corrections are not the sole carrier.
Pure policy — no SendInput.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "lot-cardinal-semantics.v1.json"
MAX_BYTES = 96_000
PROOF = "CONTRACT_HARNESS_NOT_LIVE_WORKSTATION_HIT_NOT_EA_PARSER_NOT_BI002_CLOSE"

CARDINAL_DEGREES = {
    "N": 0,
    "NE": 45,
    "E": 90,
    "SE": 135,
    "S": 180,
    "SW": 225,
    "W": 270,
    "NW": 315,
}


class LotCardinalSemanticsError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise LotCardinalSemanticsError("LOT_CARDINAL_CONTRACT_UNSAFE")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.lot-cardinal-semantics/v1":
        raise LotCardinalSemanticsError("INVALID_LOT_CARDINAL_SCHEMA")
    stack = data.get("authority_stack") or []
    if not isinstance(stack, list) or stack[0] != "EA_SAVE_OR_TRAY_PARSER_WHEN_AUTHORIZED":
        raise LotCardinalSemanticsError("AUTHORITY_STACK_MUST_PREFER_EA_PARSER")
    if "CARDINAL_SEMANTIC_MODEL" not in stack:
        raise LotCardinalSemanticsError("CARDINAL_MODEL_MISSING_FROM_STACK")
    return data


def authority_stack(cfg: Optional[Mapping[str, Any]] = None) -> list[str]:
    cfg = cfg or load_contract()
    return [str(x) for x in (cfg.get("authority_stack") or [])]


def bearing_degrees(cardinal: str, cfg: Optional[Mapping[str, Any]] = None) -> int:
    cfg = cfg or load_contract()
    table = (cfg.get("bearing_math") or {}).get("cardinal_degrees") or CARDINAL_DEGREES
    key = str(cardinal).upper()
    if key not in table:
        raise LotCardinalSemanticsError(f"UNKNOWN_CARDINAL:{key}")
    return int(table[key])


def angular_delta_deg(a: float, b: float) -> float:
    """Smallest absolute angle between two bearings in degrees."""
    d = abs(float(a) - float(b)) % 360.0
    return d if d <= 180.0 else 360.0 - d


def is_ninety_deg_from(
    *,
    front_cardinal: str,
    target_cardinal: str,
    cfg: Optional[Mapping[str, Any]] = None,
) -> bool:
    cfg = cfg or load_contract()
    tol = float((cfg.get("bearing_math") or {}).get("ninety_deg_tolerance_deg") or 20)
    front = bearing_degrees(front_cardinal, cfg)
    target = bearing_degrees(target_cardinal, cfg)
    return abs(angular_delta_deg(front, target) - 90.0) <= tol


def landmark_relations(
    landmark_id: str,
    *,
    cfg: Optional[Mapping[str, Any]] = None,
) -> list[dict[str, str]]:
    """Return SAME_SIDE_AS / OPPOSITE / NINETY_DEG relations for a seed landmark."""
    cfg = cfg or load_contract()
    seed = cfg.get("bargain_bendh_lab_seed_20261110") or {}
    landmarks = seed.get("landmarks") or {}
    row = landmarks.get(str(landmark_id))
    if not isinstance(row, Mapping):
        return []
    out: list[dict[str, str]] = []
    for rel in row.get("relations") or []:
        if isinstance(rel, Mapping) and rel.get("kind") and rel.get("of"):
            out.append({"kind": str(rel["kind"]), "of": str(rel["of"])})
    return out


def describe_landmark(
    landmark_id: str,
    *,
    cfg: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    cfg = cfg or load_contract()
    seed = cfg.get("bargain_bendh_lab_seed_20261110") or {}
    landmarks = seed.get("landmarks") or {}
    row = landmarks.get(str(landmark_id))
    if not isinstance(row, Mapping):
        return {
            "found": False,
            "landmark_id": landmark_id,
            "proof_ceiling": PROOF,
            "next": "UNKNOWN_LANDMARK_USE_FLOOR_MAP_OR_OPERATOR",
        }
    return {
        "found": True,
        "landmark_id": landmark_id,
        "note": row.get("note"),
        "relations": landmark_relations(landmark_id, cfg=cfg),
        "authority": "CARDINAL_SEMANTIC_MODEL_FALLBACK",
        "prefer_over": [],
        "outranked_by": [
            "EA_SAVE_OR_TRAY_PARSER_WHEN_AUTHORIZED",
            "LOT_FLOOR_MAP_GRAPH",
        ],
        "proof_ceiling": PROOF,
    }


def assess_workstation_candidate(
    *,
    body_color: Optional[str] = None,
    pie_tokens: Optional[Sequence[str]] = None,
    gardener_bot_needs_fix: Optional[bool] = None,
    servo_activate_affordance: Optional[bool] = None,
    dominant_blue_glow_cylinder: Optional[bool] = None,
    cfg: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Admit gray robotics workstation; deny blue water-generator / Activate Servo."""
    cfg = cfg or load_contract()
    identity = cfg.get("robotics_workstation_identity") or {}
    visual = identity.get("visual") or {}
    deny_if = {str(x).upper() for x in (identity.get("deny_if") or [])}
    tokens = {str(t).upper() for t in (pie_tokens or [])}
    color = str(body_color or "").upper()
    reasons: list[str] = []

    if dominant_blue_glow_cylinder is True or color in {
        "BLUE",
        "COPPER_BLUE",
        "ATMOSPHERIC_WATER_GENERATOR",
    }:
        reasons.append("DOMINANT_BLUE_GLOW_CYLINDER")
    if tokens & {"ADD_FUEL", "START_WATER_GENERATOR", "ADD_INSECT_BIO_FUEL"}:
        reasons.append("PIE_SHOWS_WATER_GENERATOR")
    if servo_activate_affordance is True:
        reasons.append("SERVO_ACTIVATE_AFFORDANCE_SELECTED")
    if color and color not in {"", "GRAY", "GREY", "UNKNOWN"} and color not in {
        "GRAY",
        "GREY",
    }:
        if color in {"BLUE", "CYAN", "TEAL_BLUE"}:
            reasons.append("FORBIDDEN_COLOR_ALIAS")

    servo_forbid = list(
        ((identity.get("attachments") or {}).get("servo_pending") or {}).get("forbid") or []
    )

    if reasons:
        return {
            "admit": False,
            "gate": "ROBOTICS_WORKSTATION_IDENTITY_MISMATCH",
            "reasons": reasons,
            "expected_body_color": visual.get("body_color") or "GRAY",
            "forbidden": servo_forbid + ["CLICK_BLUE_WATER_GENERATOR_AS_WORKSTATION"],
            "next": "REOBSERVE_GRAY_WORKSTATION_WITH_GARDENER_BOT_DO_NOT_ACTIVATE_SERVO",
            "proof_ceiling": PROOF,
        }

    cues_hit = []
    if color in {"GRAY", "GREY"}:
        cues_hit.append("GRAY_BODY")
    if gardener_bot_needs_fix is True:
        cues_hit.append("GARDENER_BOT_NEEDS_FIX")
    if servo_activate_affordance is False:
        cues_hit.append("SERVO_NEARBY_INACTIVE")

    return {
        "admit": True,
        "gate": None,
        "reasons": [],
        "cues_hit": cues_hit,
        "expected_body_color": visual.get("body_color") or "GRAY",
        "forbidden": servo_forbid,
        "deny_if": sorted(deny_if),
        "next": "CLICK_GRAY_WORKSTATION_OR_COMPUTER_ORDER_PARTS_WHILE_PAUSED",
        "proof_ceiling": PROOF,
    }


def assess_library_search_admission(
    *,
    current_search_text: Optional[str],
    intended_query: str,
    search_cleared: bool = False,
    cfg: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Deny typing a new Library/Gallery query over a leftover term (e.g. Smog)."""
    cfg = cfg or load_contract()
    block = cfg.get("library_search") or {}
    current = (current_search_text or "").strip()
    intended = (intended_query or "").strip()
    if search_cleared or current == "" or current.upper() == intended.upper():
        return {
            "admit": True,
            "gate": None,
            "require": [],
            "current_search_text": current,
            "intended_query": intended,
            "next": "TYPE_QUERY",
            "proof_ceiling": block.get("proof_ceiling") or PROOF,
        }
    return {
        "admit": False,
        "gate": "CLEAR_SEARCH_BEFORE_QUERY",
        "require": list(block.get("require_before_type") or ["FOCUS_SEARCH_FIELD", "SELECT_ALL", "DELETE_OR_BACKSPACE"]),
        "chord_until_measured": list(block.get("chord_until_measured") or ["CTRL_A", "DELETE"]),
        "current_search_text": current,
        "intended_query": intended,
        "forbidden": list(block.get("forbidden") or []),
        "known_regression": block.get("known_regression_20261110"),
        "next": "CLEAR_SEARCH_FIELD_THEN_RECHECK_EMPTY",
        "proof_ceiling": block.get("proof_ceiling") or PROOF,
    }
