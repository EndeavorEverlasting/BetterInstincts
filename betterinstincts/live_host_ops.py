"""Durable live-host operating policy (P00/P01).

Chat operator corrections are incomplete until encoded here / in
``contracts/live-host-ops.v1.json``. Pure policy — no SendInput.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "live-host-ops.v1.json"
MAX_BYTES = 64_000
PROOF = "CONTRACT_HARNESS_NOT_LIVE_PARTS_HIT_NOT_BI002_CLOSE"


class LiveHostOpsError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise LiveHostOpsError("LIVE_HOST_OPS_CONTRACT_UNSAFE")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.live-host-ops/v1":
        raise LiveHostOpsError("INVALID_LIVE_HOST_OPS_SCHEMA")
    if data.get("architecture", {}).get("selected") != "PAUSED_PRODUCTIVITY_BEFORE_TIME_RISK":
        raise LiveHostOpsError("PAUSED_PRODUCTIVITY_ARCHITECTURE_REQUIRED")
    return data


def priority_order(cfg: Optional[Mapping[str, Any]] = None) -> list[str]:
    cfg = cfg or load_contract()
    order = cfg.get("priority_order") or []
    if not isinstance(order, list) or not order:
        raise LiveHostOpsError("PRIORITY_ORDER_MISSING")
    return [str(x) for x in order]


def assess_unpause_admission(
    *,
    parts_gate_open: bool,
    household_queue_incomplete: bool,
    paused_verified: bool,
    cfg: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Deny Play/unpause while paused-productivity gates are open."""
    cfg = cfg or load_contract()
    gate = (cfg.get("gates") or {}).get("PAUSED_PRODUCTIVITY_REQUIRED") or {}
    forbid = list(gate.get("forbid") or ["UNPAUSE", "PLAY", "SPEED_UP"])
    blocked = bool(parts_gate_open or household_queue_incomplete)
    if blocked:
        return {
            "admit": False,
            "gate": "PAUSED_PRODUCTIVITY_REQUIRED",
            "forbid": forbid,
            "require_paused": True,
            "paused_verified": paused_verified,
            "next": "KEEP_PAUSED_COMPLETE_PARTS_AND_HOUSEHOLD_QUEUES",
            "proof_ceiling": PROOF,
        }
    return {
        "admit": True,
        "gate": None,
        "forbid": [],
        "require_paused": False,
        "paused_verified": paused_verified,
        "next": "UNPAUSE_ALLOWED_AFTER_QUEUES",
        "proof_ceiling": PROOF,
    }


def assess_edge_creek_flag(
    *,
    cursor_in_edge_band: bool,
    scenery_tokens: Optional[Sequence[str]] = None,
    cfg: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Oldest regression: mouse at edge → camera pans to creek/canal."""
    cfg = cfg or load_contract()
    tokens = {str(t).upper() for t in (scenery_tokens or [])}
    creekish = bool(tokens & {"CREEK", "CANAL", "WATER", "STREET", "OFF_LOT", "ASPHALT"})
    triggered = bool(cursor_in_edge_band or creekish)
    gate = (cfg.get("gates") or {}).get("EDGE_CREEK_REGRESSION") or {}
    return {
        "triggered": triggered,
        "gate": "EDGE_CREEK_REGRESSION" if triggered else None,
        "recovery": list(gate.get("recovery") or ["SAFE_CURSOR_REST", "SHIFT_ENTER"]),
        "forbid": list(gate.get("forbid") or []),
        "cursor_in_edge_band": cursor_in_edge_band,
        "creekish_scenery": creekish,
        "proof_ceiling": PROOF,
    }


def assess_world_xy_policy(
    *,
    target_kind: str,
    using_hardcoded_field_xy: bool,
    target_visible_in_fresh_capture: bool,
    cfg: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Hardcoded field XY are not durable across zoom for world objects."""
    cfg = cfg or load_contract()
    world = str(target_kind).upper() in {
        "WORLD_OBJECT",
        "WORKSTATION",
        "COMPUTER",
        "FRIDGE",
        "ROBOTICS",
    }
    if not world:
        return {"admit": True, "gate": None, "proof_ceiling": PROOF}
    if using_hardcoded_field_xy and not target_visible_in_fresh_capture:
        return {
            "admit": False,
            "gate": "HARDCODED_FIELD_XY_FORBIDDEN",
            "next": "FRESH_CAPTURE_THEN_CLICK_VISIBLE_TARGET_OR_OFF_INTENT_ARM",
            "proof_ceiling": PROOF,
        }
    if not target_visible_in_fresh_capture:
        return {
            "admit": False,
            "gate": "TARGET_NOT_IN_CURRENT_FRAME",
            "next": "SHIFT_ENTER_ARM_OR_OPERATOR_FRAME",
            "proof_ceiling": PROOF,
        }
    return {"admit": True, "gate": None, "proof_ceiling": PROOF}
