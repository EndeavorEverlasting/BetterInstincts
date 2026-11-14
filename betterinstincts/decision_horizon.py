"""PS-0245: bounded, duration-aware stochastic planning over PS-0241 activity evidence.

Pure Python policy only. No EA hook, UI control, host listener, save IO, or
effect permit. A failed/partially observed action is an absorbing re-observe
boundary; never silently replay it. Discrete feasibility precedes any utility.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math

from betterinstincts.activity_chain import (
    ActivityChainError, _validate_steps, compile_activity_chain,
)

SCHEMA = "betterinstincts.decision-horizon/v1"
PROOF = "OFFLINE_BELLMAN_POLICY_ONLY_NOT_NATIVE_EFFECT"
MAX_ACTIONS = 24
MAX_ROUTES = 96
MAX_EXPANSIONS = 2000
MAX_DEPTH = 8
WEIGHTS = {"value": 1.0, "time": 0.25, "money": 0.05,
           "need": 0.4, "skill": 2.0, "mood": 0.3, "failure": 6.0}


class DecisionHorizonError(ValueError):
    pass


def _number(value: object, lo: float, hi: float) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and lo <= value <= hi


def _ref(value: object) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= 96 and all(
        ch.isalnum() or ch in "_.:-" for ch in value
    )


def _numeric_map(raw: object, *, lo: float, hi: float,
                 max_items: int = 24) -> dict[str, float]:
    if (not isinstance(raw, Mapping) or not 1 <= len(raw) <= max_items
            or any(not _ref(k) or not _number(v, lo, hi) for k, v in raw.items())):
        raise DecisionHorizonError("NUMERIC_STATE_INVALID")
    return {k: float(v) for k, v in raw.items()}


def _integer_map(raw: object, *, signed: bool = False) -> dict[str, int]:
    if (not isinstance(raw, Mapping) or len(raw) > 24
            or any(not _ref(k) or type(v) is not int
                   or not (-10000 if signed else 0) <= v <= 10000
                   for k, v in raw.items())):
        raise DecisionHorizonError("INVENTORY_STATE_INVALID")
    return dict(raw)


@dataclass(frozen=True)
class PlanningState:
    """One capture-qualified actor's forecast; no mutable game references."""
    elapsed: float
    location: str
    funds: float
    needs: tuple[tuple[str, float], ...]
    skills: tuple[tuple[str, float], ...]
    inventory: tuple[tuple[str, int], ...]
    done: frozenset[str]


@dataclass(frozen=True)
class ActionModel:
    id: str
    domain: str
    kind: str
    location: str
    duration: float
    deadline: float
    value: float
    cost: float
    probability: float
    after: frozenset[str]
    resources: frozenset[str]
    requires: tuple[tuple[str, int], ...]
    inventory_delta: tuple[tuple[str, int], ...]
    need_delta: tuple[tuple[str, float], ...]
    skill_delta: tuple[tuple[str, float], ...]
    mood_delta: float
    money_delta: float
    irreversible: bool
    evidence_ref: str


def _effect(raw: object) -> Mapping:
    if raw is None:
        return {}
    if not isinstance(raw, Mapping) or set(raw) - {
        "requires_inventory", "inventory_delta", "need_delta",
        "skill_delta", "mood_delta", "money_delta",
    }:
        raise DecisionHorizonError("ACTION_EFFECT_INVALID")
    return raw


def _models(steps: Sequence[Mapping]) -> dict[str, ActionModel]:
    try:
        validated = _validate_steps(steps)
    except ActivityChainError as exc:
        raise DecisionHorizonError(str(exc)) from exc
    if len(validated) > MAX_ACTIONS:
        raise DecisionHorizonError("ACTION_SEARCH_BOUND")
    models = {}
    for key, raw in validated.items():
        e = _effect(raw.get("effects"))
        requires = _integer_map(e.get("requires_inventory", {}))
        inventory = _integer_map(e.get("inventory_delta", {}), signed=True)
        need = {} if e.get("need_delta") is None else _numeric_map(
            e["need_delta"], lo=-100, hi=100)
        skill = {} if e.get("skill_delta") is None else _numeric_map(
            e["skill_delta"], lo=0, hi=10)
        p = raw.get("success_probability", 1.0)
        mood, money = e.get("mood_delta", 0), e.get("money_delta", 0)
        if (not _number(p, 0, 1) or not _number(mood, -100, 100)
                or not _number(money, -10000, 10000)
                or type(raw.get("irreversible", False)) is not bool
                or raw.get("cheat", False) is not False
                or raw.get("operator_authorized", False) is not False):
            raise DecisionHorizonError("ACTION_PROBABILITY_AUTHORITY_INVALID")
        models[key] = ActionModel(
            key, raw["domain"], raw["kind"], raw["location"],
            float(raw["upper_minutes"]), float(raw.get("deadline_minutes", 1_000_000)),
            float(raw.get("value", 1)), float(raw.get("cost", 0)), float(p),
            frozenset(raw["after"]), frozenset(raw["resources"]),
            tuple(sorted(requires.items())), tuple(sorted(inventory.items())),
            tuple(sorted(need.items())), tuple(sorted(skill.items())),
            float(mood), float(money), raw.get("irreversible", False),
            raw["evidence_ref"],
        )
    return models


def _routes(origin: str, destination: str, routes: Sequence[Mapping],
            capture: str, teleport: bool) -> list[dict]:
    if origin == destination:
        return [{"method": "STAY", "upper_minutes": 0.0, "evidence_ref": None}]
    options = []
    for r in routes:
        if (r.get("from") != origin or r.get("to") != destination
                or r.get("capture_ref") != capture or r.get("admitted") is not True
                or r.get("method") not in ("WALK", "TELEPORT")
                or not _ref(r.get("evidence_ref"))
                or not _number(r.get("upper_minutes"), 0.001, 10000)):
            continue
        if r["method"] == "TELEPORT" and not teleport:
            continue
        options.append({"method": r["method"],
                        "upper_minutes": float(r["upper_minutes"]),
                        "evidence_ref": r["evidence_ref"]})
    # Both routes remain distinct; prefer measured faster only after full
    # action-value comparison. Duplicate evidence does not create extra paths.
    seen = set()
    unique = []
    for route in sorted(options, key=lambda x: (x["upper_minutes"], x["method"],
                                                 x["evidence_ref"])):
        signature = (route["method"], route["evidence_ref"])
        if signature not in seen:
            unique.append(route)
            seen.add(signature)
    return unique[:MAX_ROUTES]


def _receipt(capture: str, gate: str, **fields: object) -> dict:
    return {
        "schema": SCHEMA, "capture_ref": capture, "gate": gate,
        "next_step": None, "forecast_steps": [], "execute_allowed": False,
        "control_permit": None, "effect_admission_required": True,
        "failure_recovery": "REOBSERVE_AND_RECONCILE_NO_BLIND_RETRY",
        "proof_ceiling": PROOF, **fields,
    }


def optimize_activity_plan(
    snapshot: Mapping, steps: Sequence[Mapping], routes: Sequence[Mapping] = (),
    *, capture_ref: str, horizon_minutes: float = 120,
    max_expansions: int = 1000, max_depth: int = 6,
) -> dict:
    """Bounded semi-Markov expected-value search, maximizing net utility.

    Q(s,a) = immediate weighted outcome + p(success)*V(s') +
             (1-p(success))*terminal_failure_penalty.
    The failure branch is absorbing until an independent game observation.
    Forecasted duration consumes needs/time even before effects occur.
    """
    if (not isinstance(snapshot, Mapping) or not _ref(capture_ref)
            or not _number(horizon_minutes, 0.1, 10000)
            or type(max_expansions) is not int or not 1 <= max_expansions <= MAX_EXPANSIONS
            or type(max_depth) is not int or not 1 <= max_depth <= MAX_DEPTH
            or not isinstance(routes, (tuple, list)) or len(routes) > MAX_ROUTES
            or any(not isinstance(r, Mapping) for r in routes)):
        raise DecisionHorizonError("PLANNER_BOUND_OR_SNAPSHOT_INVALID")
    models = _models(steps)
    # Reuse PS-0241's evidence, dependency, completed-step and interruption
    # checks rather than establishing a second source of safety truth.
    try:
        base = compile_activity_chain(snapshot, steps, routes, capture_ref=capture_ref)
    except ActivityChainError as exc:
        raise DecisionHorizonError(str(exc)) from exc
    hard_stops = {
        "REOBSERVE_SCENE_AND_QUEUE", "PLAYER_FIRST", "NEEDS_FIRST",
        "REVALIDATE_PREVIOUS_COMPLETIONS", "RECONCILE_INFLIGHT_BEFORE_REPLAY",
    }
    if base["gate"] in hard_stops:
        return _receipt(capture_ref, base["gate"], baseline_gate=base["gate"])
    if (snapshot.get("schema") != "betterinstincts.activity-chain/v1"
            or snapshot.get("selected_sim_ref") != snapshot.get("sim_ref")
            or snapshot.get("queue_owner") != "AUTONOMY"
            or snapshot.get("player_active") is not False
            or snapshot.get("scene_verified") is not True
            or snapshot.get("queue_verified") is not True):
        return _receipt(capture_ref, "ACTOR_QUEUE_OR_PLAYER_REVALIDATION_REQUIRED")
    depth, capacity = snapshot.get("queue_depth"), snapshot.get("queue_capacity")
    if (type(depth) is not int or type(capacity) is not int
            or not 0 <= depth <= 8 or not 1 <= capacity <= 8
            or depth >= capacity):
        return _receipt(capture_ref, "QUEUE_OWNERSHIP_OR_CAPACITY")
    if (snapshot.get("checkpoint_capture_ref") not in (None, capture_ref)
            or snapshot.get("interrupted") is True):
        return _receipt(capture_ref, "REVALIDATE_CHECKPOINT_AFTER_INTERRUPTION")
    needs = _numeric_map(snapshot.get("needs"), lo=0, hi=100, max_items=16)
    rates = _numeric_map(snapshot.get("need_rates"), lo=-10, hi=10, max_items=16)
    floors = _numeric_map(snapshot.get("need_floors"), lo=0, hi=100, max_items=16)
    if set(needs) != set(rates) or set(needs) != set(floors):
        raise DecisionHorizonError("NEED_SIGNAL_KEYS_MISMATCH")
    skills = _numeric_map(snapshot.get("skills"), lo=0, hi=10)
    inventory = _integer_map(snapshot.get("inventory", {}))
    if (not _number(snapshot.get("available_funds"), 0, 1_000_000)
            or any(not _ref(x) for x in snapshot.get("blocked_resources", []))
            or not isinstance(snapshot.get("blocked_resources", []), list)):
        raise DecisionHorizonError("RESOURCE_EVIDENCE_INVALID")
    supplied = snapshot.get("shadow_prices", {})
    if (not isinstance(supplied, Mapping) or set(supplied) - set(WEIGHTS)
            or any(not _number(v, 0, 1000) for v in supplied.values())):
        raise DecisionHorizonError("SHADOW_PRICE_INVALID")
    weights = {**WEIGHTS, **supplied}
    teleport = (snapshot.get("teleport_unlocked") is True
                and _ref(snapshot.get("teleport_evidence_ref"))
                and snapshot.get("teleport_evidence_capture_ref") == capture_ref)
    available = max(0.0, min(
        float(snapshot["minutes_until_work"]),
        float(snapshot["minutes_until_need_floor"]),
        float(horizon_minutes),
    ) - float(snapshot.get("reserve_minutes", 0)))
    completed = frozenset(x["step_id"] for x in snapshot.get("completed", []))
    state = PlanningState(
        0.0, snapshot["location"], float(snapshot["available_funds"]),
        tuple(sorted(needs.items())), tuple(sorted(skills.items())),
        tuple(sorted(inventory.items())), completed,
    )
    blocked = set(snapshot.get("blocked_resources", []))
    # Per-decision max expansions caps work even in wide dependency graphs.
    expansions = 0
    best: tuple[float, tuple[dict, ...], PlanningState] = (0.0, (), state)
    first_blockers: set[str] = set()

    def search(current: PlanningState, path: tuple[dict, ...],
               score: float, survival: float) -> None:
        nonlocal expansions, best
        if (score > best[0] + 1e-9
                or (abs(score - best[0]) <= 1e-9 and path
                    and (not best[1] or current.elapsed < best[2].elapsed))):
            best = (score, path, current)
        if len(path) >= max_depth or expansions >= max_expansions:
            return
        for action in sorted(models.values(), key=lambda x: x.id):
            if action.id in current.done or not action.after <= current.done:
                continue
            if action.irreversible or action.resources & blocked:
                first_blockers.add("IRREVERSIBLE_OR_RESERVED_RESOURCE")
                continue
            for route in _routes(current.location, action.location, routes,
                                 capture_ref, bool(teleport)):
                minutes = route["upper_minutes"] + action.duration
                finish = current.elapsed + minutes
                if (finish > available + 1e-9 or finish > action.deadline
                        or action.cost > current.funds):
                    first_blockers.add("TIME_DEADLINE_OR_FUNDS")
                    continue
                stock = dict(current.inventory)
                if any(stock.get(k, 0) < count for k, count in action.requires):
                    first_blockers.add("INVENTORY_PRECONDITION")
                    continue
                future_needs = dict(current.needs)
                effects = dict(action.need_delta)
                for need, before in current.needs:
                    # Conservative linear need-rate forecast: action benefits
                    # occur after transit/interaction, not before.
                    during = before + rates[need] * minutes
                    after = min(100.0, max(0.0, during + effects.get(need, 0.0)))
                    if after < floors[need] - 1e-9:
                        first_blockers.add("NEED_FLOOR")
                        break
                    future_needs[need] = after
                else:
                    for item, count in action.requires:
                        stock[item] -= count
                    for item, delta in action.inventory_delta:
                        stock[item] = stock.get(item, 0) + delta
                    if min(stock.values(), default=0) < 0:
                        first_blockers.add("INVENTORY_NEGATIVE")
                        continue
                    future_skills = dict(current.skills)
                    for skill, gain in action.skill_delta:
                        if skill not in future_skills:
                            first_blockers.add("UNOBSERVED_SKILL")
                            break
                        future_skills[skill] = min(10.0, future_skills[skill] + gain)
                    else:
                        money = current.funds - action.cost + action.money_delta
                        if money < 0:
                            first_blockers.add("NEGATIVE_FUNDS")
                            continue
                        utility = (
                            weights["value"] * action.value
                            - weights["time"] * minutes
                            - weights["money"] * (action.cost - action.money_delta)
                            + weights["need"] * sum(
                                future_needs[k] - dict(current.needs)[k] for k in future_needs
                            )
                            + weights["skill"] * sum(
                                future_skills[k] - dict(current.skills)[k] for k in future_skills
                            )
                            + weights["mood"] * action.mood_delta
                        )
                        p = action.probability
                        next_score = score + survival * (
                            p * utility - (1.0 - p) * weights["failure"]
                        )
                        successor = PlanningState(
                            finish, action.location, money,
                            tuple(sorted(future_needs.items())),
                            tuple(sorted(future_skills.items())),
                            tuple(sorted(stock.items())),
                            current.done | frozenset((action.id,)),
                        )
                        planned = {
                            "step_id": action.id, "kind": action.kind,
                            "domain": action.domain, "evidence_ref": action.evidence_ref,
                            "travel": route, "upper_minutes": minutes,
                            "success_probability": p,
                            "failure_requires_reconciliation": True,
                        }
                        expansions += 1
                        search(successor, path + (planned,), next_score, survival * p)
                        if expansions >= max_expansions:
                            return

    search(state, (), 0.0, 1.0)
    score, path, projected = best
    truncated = expansions >= max_expansions
    gate = "BOUNDED_SEARCH_PARTIAL_REVIEW" if truncated else (
        "FORECAST_STAGED_NOT_DISPATCHABLE" if path else "NO_POSITIVE_FEASIBLE_PLAN")
    return _receipt(
        capture_ref, gate, next_step=path[0] if path else None,
        forecast_steps=list(path), expected_net_utility=round(score, 6),
        projected_minutes=round(projected.elapsed, 6),
        projected_funds=round(projected.funds, 6),
        projected_needs=dict(projected.needs),
        available_minutes=round(available, 6),
        expansions=expansions, max_expansions=max_expansions,
        truncated=truncated, shadow_prices=weights,
        binding_or_blocking_constraints=sorted(first_blockers),
        baseline_gate=base["gate"],
    )


def allocate_continuous_time(budget: float, activities: Mapping) -> dict:
    """Solve concave sum(w_i * log(1+x_i)) with bounds by KKT water filling.

    This is a continuous *relaxation* for advisory time allocation, not a
    solver for discrete inventory menus, teleport unlocks or game effects.
    """
    if (not _number(budget, 0, 10000) or not isinstance(activities, Mapping)
            or not 1 <= len(activities) <= 16):
        raise DecisionHorizonError("KKT_ALLOCATION_BOUND")
    params: dict[str, tuple[float, float]] = {}
    for key, row in activities.items():
        if (not _ref(key) or not isinstance(row, Mapping)
                or set(row) != {"weight", "max_minutes"}
                or not _number(row["weight"], 0.001, 1000)
                or not _number(row["max_minutes"], 0, 10000)):
            raise DecisionHorizonError("KKT_ACTIVITY_INVALID")
        params[key] = (float(row["weight"]), float(row["max_minutes"]))
    total = sum(cap for _, cap in params.values())
    if total <= budget:
        allocations = {k: cap for k, (_, cap) in params.items()}
        lam = 0.0
    elif budget == 0:
        allocations = {k: 0.0 for k in params}
        lam = max(weight for weight, _ in params.values())
    else:
        low, high = 0.0, max(w for w, _ in params.values())
        for _ in range(80):
            mid = (low + high) / 2
            spent = sum(min(cap, max(0.0, w / mid - 1))
                        for w, cap in params.values())
            if spent > budget:
                low = mid
            else:
                high = mid
        lam = high
        allocations = {k: min(cap, max(0.0, w / lam - 1))
                       for k, (w, cap) in params.items()}
    used = sum(allocations.values())
    # Stationarity check applies to interior activities only.
    residual = max((abs(w / (1 + allocations[k]) - lam)
                    for k, (w, cap) in params.items()
                    if 1e-7 < allocations[k] < cap - 1e-7), default=0.0)
    return {
        "schema": "betterinstincts.continuous-time-relaxation/v1",
        "allocations_minutes": {k: round(v, 8) for k, v in allocations.items()},
        "shadow_price_lambda": round(lam, 8),
        "budget_binding": budget < total,
        "budget_slack_minutes": round(max(0.0, budget - used), 8),
        "interior_kkt_residual": round(residual, 8),
        "execute_allowed": False,
        "proof_ceiling": PROOF,
    }
