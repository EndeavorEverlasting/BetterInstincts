"""P95 need-service load balancer: health checks, detach, assumption windows.

Evaluate-only orchestration seam over tandem need microsystems.
Not a network LB, daemon, or EA autonomy hook.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional, Sequence

from betterinstincts.need_service_base import NeedServiceBaseError, normalize_needs, threshold_pair

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "need-load-balance.v1.json"
SIX_ORDER = ("bladder", "hunger", "energy", "hygiene", "fun", "social")
SURVIVAL = frozenset({"bladder", "hunger", "energy"})
PLAN_GATES = frozenset({"NEED_SERVICE_PLAN", "FUN_SERVICE_PLAN"})


class NeedLoadBalanceError(NeedServiceBaseError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 128000:
        raise NeedLoadBalanceError("UNSAFE_NEED_LOAD_BALANCE_CONTRACT")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise NeedLoadBalanceError("INVALID_NEED_LOAD_BALANCE_JSON") from exc
    if data.get("schema") != "betterinstincts.need-load-balance/v1":
        raise NeedLoadBalanceError("INVALID_NEED_LOAD_BALANCE_SCHEMA")
    if not isinstance(data.get("health_rules"), dict):
        raise NeedLoadBalanceError("NEED_LOAD_BALANCE_RULES_MISSING")
    return data


def _findings(row: Mapping) -> set[str]:
    return {str(x) for x in (row.get("findings") or [])}


def health_check_service(
    need_id: str,
    service_result: Mapping,
    *,
    failure_signals: Optional[Mapping[str, Sequence[str]]] = None,
    contract: Optional[Mapping] = None,
) -> dict:
    """Classify one need microsystem as HEALTHY / DEGRADED / UNHEALTHY / YIELDED."""
    cfg = contract or load_contract()
    rules = cfg["health_rules"]
    gate = str(service_result.get("gate") or "")
    findings = _findings(service_result)
    signals = {
        str(s).strip().upper()
        for s in (failure_signals or {}).get(need_id, ())
        if str(s).strip()
    }
    sticky_failed = {
        str(s).strip()
        for s in (failure_signals or {}).get(f"{need_id}:routes", ())
        if str(s).strip()
    }
    urgent = bool(service_result.get("urgent") or service_result.get("fun_urgent"))
    low = bool(service_result.get("low") or service_result.get("fun_low"))
    material = urgent or low or bool(signals) or bool(sticky_failed)

    if gate in rules["YIELDED"]["gates"]:
        status = "YIELDED"
    elif (
        (rules["UNHEALTHY"].get("failure_signal") and signals)
        or (
            service_result.get("primary_route")
            and sticky_failed
            and str(service_result.get("primary_route")) in sticky_failed
            and not (service_result.get("parallel_ready") or [])
        )
        or (
            material
            and (
                gate in rules["UNHEALTHY"]["gates"]
                or findings.intersection(rules["UNHEALTHY"].get("findings_any") or [])
            )
        )
    ):
        status = "UNHEALTHY"
    elif (
        gate in rules["DEGRADED"]["gates"]
        or findings.intersection(rules["DEGRADED"].get("findings_any") or [])
        or (
            sticky_failed
            and service_result.get("primary_route")
            and str(service_result.get("primary_route")) in sticky_failed
        )
        or (
            gate in rules["UNHEALTHY"]["gates"]
            or findings.intersection(rules["UNHEALTHY"].get("findings_any") or [])
        )
    ):
        status = "DEGRADED"
    elif gate in rules["HEALTHY"]["gates"] or gate in PLAN_GATES:
        status = "HEALTHY"
    elif not (service_result.get("parallel_ready") or []) and gate and material:
        status = "UNHEALTHY"
    else:
        status = "DEGRADED"

    rule = rules[status]
    if status == "DEGRADED":
        detach, open_window = False, False
        eligible = bool(rule.get("eligible_for_primary"))
        weight = float(rule.get("weight_multiplier", 0.55))
    else:
        detach = bool(rule.get("detach"))
        open_window = bool(rule.get("open_assumption_window"))
        eligible = bool(rule.get("eligible_for_primary"))
        weight = float(
            rule.get("weight_multiplier", 0.0 if status in {"UNHEALTHY", "YIELDED"} else 1.0)
        )
    return {
        "need": need_id,
        "status": status,
        "gate": gate,
        "detach": detach,
        "eligible_for_primary": eligible,
        "weight_multiplier": weight,
        "open_assumption_window": open_window,
        "failure_signals": sorted(signals),
        "failed_routes": sorted(sticky_failed),
        "primary_route": service_result.get("primary_route"),
        "parallel_ready": list(service_result.get("parallel_ready") or []),
        "material": material,
    }


def health_check_all(
    services: Mapping[str, Mapping],
    *,
    failure_signals: Optional[Mapping[str, Sequence[str]]] = None,
    contract: Optional[Mapping] = None,
) -> dict[str, dict]:
    cfg = contract or load_contract()
    out: dict[str, dict] = {}
    for need_id in SIX_ORDER:
        row = services.get(need_id)
        if not isinstance(row, Mapping):
            out[need_id] = {
                "need": need_id,
                "status": "UNHEALTHY",
                "gate": "SERVICE_MISSING",
                "detach": True,
                "eligible_for_primary": False,
                "weight_multiplier": 0.0,
                "open_assumption_window": True,
                "failure_signals": [],
                "failed_routes": [],
                "primary_route": None,
                "parallel_ready": [],
                "material": True,
            }
            continue
        out[need_id] = health_check_service(
            need_id, row, failure_signals=failure_signals, contract=cfg
        )
    return out


def _option_weight(
    *,
    action_id: str,
    lane: str,
    failed_routes: Sequence[str],
    window_cfg: Mapping,
    survival_critical: bool,
) -> float:
    w = 1.0
    if action_id in failed_routes or lane in failed_routes:
        w *= float(window_cfg.get("failed_route_penalty", 0.15))
    else:
        w *= float(window_cfg.get("alternate_boost", 1.35))
    if survival_critical and action_id in {
        "MAP_TRAVEL_HOME",
        "FIND_OR_PLACE_NEED_OBJECT",
        "QUICK_MEAL",
        "USE_TOILET",
        "SLEEP_IN_BED",
        "TAKE_NAP",
    }:
        w *= float(window_cfg.get("survival_travel_boost", 1.6))
    if lane in {"portable_phone", "personal_portable", "quick_meal", "outdoor_relief", "sink_wash"}:
        w *= 1.1
    return round(w, 4)


def open_assumption_window(
    need_id: str,
    service_result: Mapping,
    health: Mapping,
    *,
    needs: Mapping[str, float],
    contract: Optional[Mapping] = None,
) -> dict:
    """Detach creates a fresh exploration frame: reset scene/assumptions/options + reweight."""
    cfg = contract or load_contract()
    win = cfg["assumption_window"]
    urgent, _ = threshold_pair()
    snap = normalize_needs(needs)
    survival_critical = need_id in SURVIVAL and snap[need_id] < urgent
    failed = list(health.get("failed_routes") or [])
    if service_result.get("primary_route"):
        failed = sorted(set(failed + [str(service_result["primary_route"])]))

    detached_stack = [f"need_service:{need_id}", str(service_result.get("gate") or "UNKNOWN_GATE")]
    if service_result.get("primary_route"):
        detached_stack.append(f"route:{service_result['primary_route']}")
    for act in (service_result.get("next_actions") or [])[:1]:
        for step in (act.get("steps") or [])[:3]:
            detached_stack.append(str(step))

    options: list[dict] = []
    seen: set[str] = set()
    for act in service_result.get("next_actions") or []:
        aid = str(act.get("id") or "")
        if not aid or aid in seen:
            continue
        seen.add(aid)
        lane = str(act.get("lane") or "")
        options.append(
            {
                "id": aid,
                "lane": lane,
                "need": need_id,
                "weight": _option_weight(
                    action_id=aid,
                    lane=lane,
                    failed_routes=failed,
                    window_cfg=win,
                    survival_critical=survival_critical,
                ),
                "objects": list(act.get("objects") or []),
                "steps": list(act.get("steps") or []),
            }
        )

    escapes = []
    if health.get("status") == "UNHEALTHY" or survival_critical:
        escapes.append(
            {
                "id": "FIND_OR_PLACE_NEED_OBJECT",
                "lane": "exploration",
                "need": need_id,
                "weight": _option_weight(
                    action_id="FIND_OR_PLACE_NEED_OBJECT",
                    lane="exploration",
                    failed_routes=failed,
                    window_cfg=win,
                    survival_critical=survival_critical,
                ),
                "objects": [],
                "steps": ["SCAN_LOT_FOR_NEED_OBJECT", "BUILD_PLACE_IF_AUTHORIZED"],
            }
        )
    if survival_critical:
        escapes.append(
            {
                "id": "MAP_TRAVEL_HOME",
                "lane": "travel",
                "need": need_id,
                "weight": _option_weight(
                    action_id="MAP_TRAVEL_HOME",
                    lane="travel",
                    failed_routes=failed,
                    window_cfg=win,
                    survival_critical=True,
                ),
                "objects": [],
                "steps": ["OPEN_PHONE_OR_MAP", "TRAVEL_HOME_LOT"],
            }
        )
    for esc in escapes:
        if esc["id"] not in seen:
            options.append(esc)
            seen.add(esc["id"])
    options.sort(key=lambda o: (-float(o["weight"]), o["id"]))
    return {
        "schema": "betterinstincts.assumption-window/v1",
        "window_id": f"aw:{need_id}:{health.get('status')}",
        "need": need_id,
        "reason": f"SERVICE_{health.get('status')}:{service_result.get('gate')}",
        "detached_call_stack": detached_stack,
        "scene_reset": bool(win.get("scene_reset", True)),
        "cleared_assumptions": list(win.get("clears") or []),
        "option_set": options,
        "preferred_exploration": options[0]["id"] if options else None,
        "weight_policy": win.get("weight_policy"),
        "p95_ground": win.get("p95_ground"),
        "survival_critical": survival_critical,
        "proof_ceiling": cfg["proof_ceiling"],
    }


def detach_unhealthy(
    health_map: Mapping[str, Mapping],
    services: Mapping[str, Mapping],
    *,
    needs: Mapping[str, float],
    contract: Optional[Mapping] = None,
) -> tuple[list[str], list[dict]]:
    cfg = contract or load_contract()
    detached: list[str] = []
    windows: list[dict] = []
    for need_id in SIX_ORDER:
        health = health_map.get(need_id) or {}
        if not health.get("detach"):
            continue
        detached.append(need_id)
        if health.get("open_assumption_window"):
            windows.append(
                open_assumption_window(
                    need_id,
                    services.get(need_id) or {},
                    health,
                    needs=needs,
                    contract=cfg,
                )
            )
    return detached, windows


def load_balance_pick(
    services: Mapping[str, Mapping],
    health_map: Mapping[str, Mapping],
    needs: Mapping[str, float],
    *,
    detached: Sequence[str] = (),
    contract: Optional[Mapping] = None,
) -> Optional[str]:
    cfg = contract or load_contract()
    snap = normalize_needs(needs)
    detached_set = set(detached)
    pool_order = list(cfg["load_balance"].get("pool_order") or ["HEALTHY", "DEGRADED"])
    never = set(cfg["load_balance"].get("never_select") or ["UNHEALTHY", "YIELDED"])

    for status in pool_order:
        candidates: list[str] = []
        for need_id in SIX_ORDER:
            if need_id in detached_set:
                continue
            health = health_map.get(need_id) or {}
            if health.get("status") in never or health.get("status") != status:
                continue
            if not health.get("eligible_for_primary"):
                continue
            row = services.get(need_id) or {}
            if row.get("gate") not in PLAN_GATES or not row.get("primary_route"):
                continue
            candidates.append(need_id)
        if not candidates:
            continue

        def score(nid: str) -> tuple:
            health = health_map[nid]
            mult = max(float(health.get("weight_multiplier") or 0.01), 0.01)
            return (float(snap[nid]) / mult, SIX_ORDER.index(nid))

        return min(candidates, key=score)
    return None


def balance_need_services(
    services: Mapping[str, Mapping],
    needs: Mapping[str, float],
    *,
    failure_signals: Optional[Mapping[str, Sequence[str]]] = None,
    player_directed: bool = False,
    already_busy: bool = False,
    capture_ref: str = "capture:need-load-balance",
) -> dict:
    """Full LB pass: health → detach/windows → primary pick among healthy."""
    cfg = load_contract()
    gates = cfg["load_balance"]["gates"]
    snap = normalize_needs(needs)
    health_map = health_check_all(services, failure_signals=failure_signals, contract=cfg)
    detached, windows = detach_unhealthy(health_map, services, needs=snap, contract=cfg)
    primary = None
    if not (player_directed or already_busy):
        primary = load_balance_pick(
            services, health_map, snap, detached=detached, contract=cfg
        )
    primary_row = services.get(primary) if primary else None
    if player_directed or already_busy:
        gate, action = gates["player"], "YIELD_OR_EMULATE_ONLY"
    elif primary_row is None:
        gate, action = gates["idle"], "NO_READY_NEED_LANE"
        if windows:
            gate, action = gates["with_detach_or_window"], "EXPLORE_ASSUMPTION_WINDOW"
    elif detached or windows:
        gate, action = gates["with_detach_or_window"], "QUEUE_PRIMARY_NEED_SERVICE_ACTION"
    else:
        gate, action = gates["clean_tandem"], "QUEUE_PRIMARY_NEED_SERVICE_ACTION"
    return {
        "schema": "betterinstincts.need-load-balance-result/v1",
        "state": "NEED_LOAD_BALANCE_EVALUATED",
        "capture_ref": capture_ref,
        "gate": gate,
        "action": action,
        "primary_need": primary,
        "primary_route": (primary_row or {}).get("primary_route"),
        "preferred_routes": (primary_row or {}).get("preferred_routes") or [],
        "next_actions": (primary_row or {}).get("next_actions") or [],
        "health": health_map,
        "detached_needs": detached,
        "attached_needs": [n for n in SIX_ORDER if n not in detached],
        "assumption_windows": windows,
        "architecture": "NEED_LB_HEALTH_DETACH_ASSUMPTION_WINDOW",
        "p95_ground": cfg["assumption_window"]["p95_ground"],
        "proof_ceiling": cfg["proof_ceiling"],
        "anti_patterns": list(cfg.get("anti_patterns") or []),
    }
