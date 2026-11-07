"""Orchestrate six independent need services in tandem (P95/P124).

Hunger/bladder/energy/hygiene/social use need-lanes; Fun delegates to fun_service.
Offline evaluate-only — not a daemon.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional, Sequence

from betterinstincts.fun_service import evaluate_fun_service
from betterinstincts.need_service_base import (
    NeedServiceBaseError,
    normalize_needs,
    norm_token,
    plan_lanes,
    survival_critical,
    threshold_pair,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "contracts" / "need-services.v1.json"
LANES = ROOT / "contracts" / "need-lanes.v1.json"
SIX_ORDER = ("bladder", "hunger", "energy", "hygiene", "fun", "social")


class NeedServicesError(NeedServiceBaseError):
    pass


def load_registry(path: Path = REGISTRY) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 128000:
        raise NeedServicesError("UNSAFE_NEED_SERVICES_REGISTRY")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.need-services/v1":
        raise NeedServicesError("INVALID_NEED_SERVICES_SCHEMA")
    reg = data.get("registry")
    if not isinstance(reg, dict) or set(reg) != set(SIX_ORDER):
        raise NeedServicesError("NEED_SERVICES_REGISTRY_INCOMPLETE")
    return data


def load_lanes(path: Path = LANES) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 256000:
        raise NeedServicesError("UNSAFE_NEED_LANES_CONTRACT")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.need-lanes/v1":
        raise NeedServicesError("INVALID_NEED_LANES_SCHEMA")
    services = data.get("services")
    if not isinstance(services, dict):
        raise NeedServicesError("NEED_LANES_EMPTY")
    return data


def should_attach_need_services(
    needs: Mapping[str, float],
    *,
    guests_present: bool = False,
    force: bool = False,
) -> bool:
    if force:
        return True
    snap = normalize_needs(needs)
    urgent, preemptive = threshold_pair()
    if any(snap[n] < preemptive for n in SIX_ORDER):
        return True
    return bool(guests_present) and any(snap[n] < 0.75 for n in ("fun", "social"))


def evaluate_need_lanes(
    need_id: str,
    needs: Mapping[str, float],
    *,
    available_objects: Sequence[str] = (),
    occupied_objects: Sequence[str] = (),
    guests_present: bool = False,
    life_stage: str = "young_adult",
    traits: Sequence[str] = (),
    sibling_lane_claims: Sequence[str] = (),
    player_directed: bool = False,
    already_busy: bool = False,
    capture_ref: str = "capture:need-lanes",
) -> dict:
    """Plan one non-Fun need service from need-lanes.v1.json."""
    if need_id not in {"hunger", "bladder", "energy", "hygiene", "social"}:
        raise NeedServicesError("UNKNOWN_NEED_LANE_SERVICE:" + need_id)
    lanes_cfg = load_lanes()
    svc = lanes_cfg["services"][need_id]
    snap = normalize_needs(needs)
    urgent, preemptive = threshold_pair()
    level = snap[need_id]
    critical = survival_critical(snap, urgent)

    if player_directed or already_busy:
        return {
            "schema": "betterinstincts.need-lane-result/v1",
            "state": "NEED_SERVICE_YIELDED",
            "need": need_id,
            "gate": "PLAYER_FIRST_OR_BUSY",
            "action": "YIELD_OR_EMULATE_ONLY",
            "lanes": [],
            "parallel_ready": [],
            "preferred_routes": [],
            "primary_route": None,
            "next_actions": [],
            "findings": ["PLAYER_FIRST"],
            "level": level,
            "proof_ceiling": lanes_cfg["proof_ceiling"],
            "capture_ref": capture_ref,
        }

    # Non-survival needs defer when survival is critical.
    if need_id not in {"bladder", "hunger", "energy"} and critical:
        return {
            "schema": "betterinstincts.need-lane-result/v1",
            "state": "NEED_SERVICE_DEFERRED",
            "need": need_id,
            "gate": "SURVIVAL_NEEDS_CRITICAL",
            "action": "RECOVER_SURVIVAL_BEFORE_NEED",
            "lanes": [],
            "parallel_ready": [],
            "preferred_routes": [],
            "primary_route": None,
            "next_actions": [],
            "findings": ["SURVIVAL_OUTRANKS_NEED"],
            "survival_critical": critical,
            "level": level,
            "proof_ceiling": lanes_cfg["proof_ceiling"],
            "capture_ref": capture_ref,
        }

    available = {norm_token(o) for o in available_objects if str(o).strip()}
    occupied = {norm_token(o) for o in occupied_objects if str(o).strip()}
    claimed = {norm_token(c) for c in sibling_lane_claims if str(c).strip()}
    order = list(
        svc.get("lane_priority_when_guests")
        if guests_present and svc.get("lane_priority_when_guests")
        else svc.get("lane_priority")
        or list(svc["lanes"])
    )
    lane_results, parallel_ready, preferred, actions, findings = plan_lanes(
        need_id=need_id,
        lanes=svc["lanes"],
        lane_order=order,
        available=available,
        occupied=occupied,
        claimed=claimed,
        life_stage=life_stage,
        traits=traits,
    )
    if guests_present or occupied:
        findings.append("NEED_OBJECT_CONTENTION")

    urgent_need = level < urgent
    low_need = level < preemptive
    if not urgent_need and not low_need and not guests_present:
        gate = "NEED_WATCH_OPTIONAL"
        action = "ALLOW_LEISURE_NEED_LANES"
        disposition = "EMULATE"
    elif parallel_ready:
        gate = "NEED_SERVICE_PLAN"
        action = "QUEUE_FREE_NEED_LANE_ACTION"
        disposition = "OPTIMIZE" if (guests_present or occupied or urgent_need) else "EMULATE_THEN_OPTIMIZE"
    else:
        gate = "NEED_SERVICE_BLOCKED"
        action = "FIND_OR_PLACE_NEED_OBJECT"
        disposition = "OPTIMIZE"
        findings.append("NO_FREE_NEED_LANE")

    primary = preferred[0] if preferred else None
    if need_id == "social" and (guests_present or occupied):
        for act in actions:
            if act["lane"] in {"sit_and_chat", "portable_phone"}:
                primary = act["id"]
                preferred = [primary, *[r for r in preferred if r != primary]]
                break

    return {
        "schema": "betterinstincts.need-lane-result/v1",
        "state": "NEED_SERVICE_EVALUATED",
        "need": need_id,
        "service_id": svc.get("service_id"),
        "gate": gate,
        "action": action,
        "disposition": disposition,
        "lanes": lane_results,
        "parallel_ready": parallel_ready,
        "preferred_routes": preferred,
        "primary_route": primary,
        "next_actions": actions[:8],
        "findings": sorted(set(findings)),
        "level": level,
        "urgent": urgent_need,
        "low": low_need,
        "architecture": "TANDEM_NEED_SERVICE",
        "proof_ceiling": lanes_cfg["proof_ceiling"],
        "capture_ref": capture_ref,
    }


def evaluate_need_services(
    needs: Mapping[str, float],
    *,
    available_objects: Sequence[str] = (),
    occupied_objects: Sequence[str] = (),
    guests_present: bool = False,
    emotion: Optional[str] = None,
    moodlets: Sequence[str] = (),
    life_stage: str = "young_adult",
    traits: Sequence[str] = (),
    queue: Sequence[str] = (),
    player_directed: bool = False,
    already_busy: bool = False,
    event_active: bool = False,
    event_fun_via_goals: bool = False,
    sibling_lane_claims: Optional[Mapping[str, Sequence[str]]] = None,
    capture_ref: str = "capture:need-services",
) -> dict:
    """Plan all six need services independently; pick primary by urgency among READY."""
    registry = load_registry()
    snap = normalize_needs(needs)
    urgent, preemptive = threshold_pair()
    claims = sibling_lane_claims or {}
    services: dict[str, dict] = {}

    for need_id in ("hunger", "bladder", "energy", "hygiene", "social"):
        services[need_id] = evaluate_need_lanes(
            need_id,
            snap,
            available_objects=available_objects,
            occupied_objects=occupied_objects,
            guests_present=guests_present,
            life_stage=life_stage,
            traits=traits,
            sibling_lane_claims=tuple(claims.get(need_id, ())),
            player_directed=player_directed,
            already_busy=already_busy,
            capture_ref=capture_ref,
        )

    services["fun"] = evaluate_fun_service(
        snap,
        available_objects=available_objects,
        occupied_objects=occupied_objects,
        guests_present=guests_present,
        emotion=emotion,
        moodlets=moodlets,
        life_stage=life_stage,
        traits=traits,
        queue=queue,
        player_directed=player_directed,
        already_busy=already_busy,
        event_active=event_active,
        event_fun_via_goals=event_fun_via_goals,
        sibling_lane_claims=tuple(claims.get("fun", ())),
        capture_ref=capture_ref,
    )

    ready = []
    for need_id in SIX_ORDER:
        row = services[need_id]
        gate = row.get("gate")
        if gate in {"NEED_SERVICE_PLAN", "FUN_SERVICE_PLAN"} and row.get("primary_route"):
            ready.append(need_id)

    def urgency_key(nid: str) -> tuple:
        return (snap[nid], SIX_ORDER.index(nid))

    primary_need = min(ready, key=urgency_key) if ready else None
    primary_row = services.get(primary_need) if primary_need else None

    if player_directed or already_busy:
        gate = "PLAYER_FIRST_OR_BUSY"
        action = "YIELD_OR_EMULATE_ONLY"
    elif primary_row is None:
        gate = "NEED_SERVICES_IDLE"
        action = "NO_READY_NEED_LANE"
    else:
        gate = "NEED_SERVICES_TANDEM"
        action = "QUEUE_PRIMARY_NEED_SERVICE_ACTION"

    return {
        "schema": "betterinstincts.need-services-result/v1",
        "state": "NEED_SERVICES_EVALUATED",
        "capture_ref": capture_ref,
        "gate": gate,
        "action": action,
        "primary_need": primary_need,
        "primary_route": (primary_row or {}).get("primary_route"),
        "preferred_routes": (primary_row or {}).get("preferred_routes") or [],
        "next_actions": (primary_row or {}).get("next_actions") or [],
        "parallel_ready_needs": ready,
        "services": services,
        "architecture": "TANDEM_NEED_SERVICES_NOT_MONOLITH_QUEUE",
        "registry_owners": {
            nid: registry["registry"][nid]["owner"] for nid in SIX_ORDER
        },
        "proof_ceiling": registry["proof_ceiling"],
        "thresholds": {"urgent": urgent, "preemptive": preemptive},
    }
