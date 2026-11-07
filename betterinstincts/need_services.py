"""Orchestrate six independent need services in tandem (P95/P124).

Hunger/bladder/energy/hygiene/social use need-lanes; Fun delegates to fun_service.
Offline evaluate-only — not a daemon.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional, Sequence

from betterinstincts.fun_service import evaluate_fun_service
from betterinstincts.need_load_balance import balance_need_services
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
    if guests_present or bool(occupied):
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
    failure_signals: Optional[Mapping[str, Sequence[str]]] = None,
    capture_ref: str = "capture:need-services",
) -> dict:
    """Plan six need services; load-balance primary via health/detach/windows."""
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

    lb = balance_need_services(
        services,
        snap,
        failure_signals=failure_signals,
        player_directed=player_directed,
        already_busy=already_busy,
        capture_ref=capture_ref,
    )
    detached = set(lb.get("detached_needs") or [])
    ready = [
        nid
        for nid in SIX_ORDER
        if nid not in detached
        and services[nid].get("gate") in {"NEED_SERVICE_PLAN", "FUN_SERVICE_PLAN"}
        and services[nid].get("primary_route")
        and (lb.get("health") or {}).get(nid, {}).get("eligible_for_primary", True)
    ]

    return {
        "schema": "betterinstincts.need-services-result/v1",
        "state": "NEED_SERVICES_EVALUATED",
        "capture_ref": capture_ref,
        "gate": lb["gate"],
        "action": lb["action"],
        "primary_need": lb.get("primary_need"),
        "primary_route": lb.get("primary_route"),
        "preferred_routes": lb.get("preferred_routes") or [],
        "next_actions": lb.get("next_actions") or [],
        "parallel_ready_needs": ready,
        "services": services,
        "health": lb.get("health") or {},
        "detached_needs": list(lb.get("detached_needs") or []),
        "attached_needs": list(lb.get("attached_needs") or []),
        "assumption_windows": list(lb.get("assumption_windows") or []),
        "load_balance": {
            "schema": lb.get("schema"),
            "gate": lb.get("gate"),
            "p95_ground": lb.get("p95_ground"),
            "architecture": lb.get("architecture"),
            "proof_ceiling": lb.get("proof_ceiling"),
        },
        "architecture": "TANDEM_NEED_SERVICES_WITH_LB_HEALTH_DETACH",
        "registry_owners": {
            nid: registry["registry"][nid]["owner"] for nid in SIX_ORDER
        },
        "proof_ceiling": registry["proof_ceiling"],
        "thresholds": {"urgent": urgent, "preemptive": preemptive},
    }


def compact_need_services(report: dict, *, max_actions: int = 4) -> dict:
    """Listener-safe summary — strip per-lane dumps that explode session JSON."""
    services = {}
    for nid, row in (report.get("services") or {}).items():
        if not isinstance(row, dict):
            continue
        services[nid] = {
            "gate": row.get("gate"),
            "primary_route": row.get("primary_route"),
            "parallel_ready": list(row.get("parallel_ready") or [])[:6],
            "level": row.get("level"),
            "urgent": row.get("urgent"),
            "low": row.get("low"),
        }
    health = {}
    for nid, row in (report.get("health") or {}).items():
        if not isinstance(row, dict):
            continue
        health[nid] = {
            "status": row.get("status"),
            "detach": row.get("detach"),
            "weight_multiplier": row.get("weight_multiplier"),
        }
    windows = []
    for win in (report.get("assumption_windows") or [])[:4]:
        if not isinstance(win, dict):
            continue
        windows.append(
            {
                "window_id": win.get("window_id"),
                "need": win.get("need"),
                "reason": win.get("reason"),
                "preferred_exploration": win.get("preferred_exploration"),
                "option_ids": [o.get("id") for o in (win.get("option_set") or [])[:6]],
            }
        )
    return {
        "schema": report.get("schema"),
        "state": report.get("state"),
        "capture_ref": report.get("capture_ref"),
        "gate": report.get("gate"),
        "action": report.get("action"),
        "primary_need": report.get("primary_need"),
        "primary_route": report.get("primary_route"),
        "preferred_routes": list(report.get("preferred_routes") or [])[:8],
        "next_actions": list(report.get("next_actions") or [])[:max_actions],
        "parallel_ready_needs": list(report.get("parallel_ready_needs") or []),
        "services": services,
        "health": health,
        "detached_needs": list(report.get("detached_needs") or []),
        "attached_needs": list(report.get("attached_needs") or []),
        "assumption_windows": windows,
        "load_balance": report.get("load_balance"),
        "architecture": report.get("architecture"),
        "proof_ceiling": report.get("proof_ceiling"),
        "thresholds": report.get("thresholds"),
        "compacted": True,
    }
