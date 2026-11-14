"""Bounded, evidence-bound cross-domain activity planning for BetterInstincts.

Pure policy: no EA hook, UI action, file writes, runtime dispatch, or game proof.
Domain owners supply observed atomic capabilities and their dependency edges.
"""
from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence

SCHEMA = "betterinstincts.activity-chain/v1"
PROOF = "OFFLINE_ACTIVITY_CHAIN_ADVISORY_NOT_GAME_EFFECT"
TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")
MAX_STEPS = 48
MAX_ROUTES = 96


class ActivityChainError(ValueError):
    """Invalid evidence, incompatible graph or unbounded input."""


def _ref(value: object) -> bool:
    return isinstance(value, str) and TOKEN.fullmatch(value) is not None


def _num(value: object, *, positive: bool = False) -> bool:
    if type(value) is int:
        return 0 < value <= 1_000_000 if positive else 0 <= value <= 1_000_000
    return type(value) is float and math.isfinite(value) and (
        0 < value <= 1_000_000 if positive else 0 <= value <= 1_000_000
    )


def _receipt(capture_ref: str, gate: str, **kwargs: object) -> dict:
    return {
        "schema": "betterinstincts.activity-chain-plan/v1",
        "capture_ref": capture_ref,
        "gate": gate,
        "mode": kwargs.pop("mode", "UNKNOWN"),
        "steps": [], "deferred": [], "total_upper_minutes": 0.0,
        "execute_allowed": False,
        "effect_admission_required": True,
        "proof_ceiling": PROOF, **kwargs,
    }


def _validate_steps(steps: Sequence[Mapping]) -> dict[str, dict]:
    if not isinstance(steps, (list, tuple)) or not 1 <= len(steps) <= MAX_STEPS:
        raise ActivityChainError("ACTIVITY_STEP_LIMIT")
    nodes: dict[str, dict] = {}
    for row in steps:
        if not isinstance(row, Mapping):
            raise ActivityChainError("ACTIVITY_STEP_INVALID")
        keys = ("id", "domain", "kind", "location", "evidence_ref")
        if any(not _ref(row.get(k)) for k in keys):
            raise ActivityChainError("ACTIVITY_IDENTITY_OR_EVIDENCE_MISSING")
        sid = row["id"]
        deps = row.get("after", [])
        if (sid in nodes or not isinstance(deps, list) or len(deps) > MAX_STEPS
                or any(not _ref(x) or x == sid for x in deps)
                or len(set(deps)) != len(deps)
                or not _num(row.get("upper_minutes"), positive=True)
                or not _num(row.get("cost", 0))
                or not _num(row.get("deadline_minutes", 1_000_000))
                or not _num(row.get("value", 1))):
            raise ActivityChainError("ACTIVITY_STEP_FIELDS_INVALID")
        resources = row.get("resources", [])
        if not isinstance(resources, list) or len(resources) > 16 or any(not _ref(x) for x in resources):
            raise ActivityChainError("ACTIVITY_RESOURCE_INVALID")
        nodes[sid] = {**row, "after": deps, "resources": resources}
    if any(dep not in nodes for row in nodes.values() for dep in row["after"]):
        raise ActivityChainError("ACTIVITY_DEPENDENCY_MISSING")
    seen: set[str] = set()
    pending = set(nodes)
    while pending:
        ready = {sid for sid in pending if set(nodes[sid]["after"]) <= seen}
        if not ready:
            raise ActivityChainError("ACTIVITY_DEPENDENCY_CYCLE")
        seen.update(ready)
        pending.difference_update(ready)
    return nodes


def _route(routes: Sequence[Mapping], origin: str, target: str,
           *, capture_ref: str, teleport_unlocked: bool) -> dict | None:
    if origin == target:
        return {"method": "STAY", "upper_minutes": 0.0}
    eligible = []
    for r in routes:
        if r.get("from") != origin or r.get("to") != target:
            continue
        if (r.get("capture_ref") != capture_ref or r.get("admitted") is not True
                or not _ref(r.get("evidence_ref"))
                or r.get("method") not in ("WALK", "TELEPORT")
                or not _num(r.get("upper_minutes"), positive=True)):
            continue
        if r["method"] == "TELEPORT" and not teleport_unlocked:
            continue
        eligible.append(r)
    return min(eligible, key=lambda r: (r["upper_minutes"], r["method"])) if eligible else None


def compile_activity_chain(snapshot: Mapping, steps: Sequence[Mapping],
                           routes: Sequence[Mapping] = (), *, capture_ref: str) -> dict:
    """Deterministic dependency/time/budget plan; never authorizes gameplay input.

    An unresolved in-flight effect blocks replay until independent observation.
    Validated completions are explicit and retained, never guessed from a queue.
    """
    if not isinstance(snapshot, Mapping) or snapshot.get("schema") != SCHEMA or not _ref(capture_ref):
        raise ActivityChainError("ACTIVITY_SNAPSHOT_INVALID")
    if (not isinstance(routes, (tuple, list)) or len(routes) > MAX_ROUTES
            or any(not isinstance(r, Mapping) for r in routes)):
        raise ActivityChainError("ACTIVITY_ROUTES_INVALID")
    mode = snapshot.get("mode")
    if mode not in ("PLANNING", "PLAY"):
        raise ActivityChainError("ACTIVITY_MODE_INVALID")
    nodes = _validate_steps(steps)
    if any(not _ref(snapshot.get(k)) for k in ("sim_ref", "household_ref", "location")):
        raise ActivityChainError("ACTIVITY_ACTOR_INVALID")
    if (snapshot.get("capture_ref") != capture_ref
            or snapshot.get("scene_verified") is not True
            or snapshot.get("queue_verified") is not True):
        return _receipt(capture_ref, "REOBSERVE_SCENE_AND_QUEUE", mode=mode)
    if snapshot.get("player_directed") is not False:
        return _receipt(capture_ref, "PLAYER_FIRST", mode=mode)
    if snapshot.get("needs_safe") is not True:
        return _receipt(capture_ref, "NEEDS_FIRST", mode=mode)
    if (not _num(snapshot.get("minutes_until_work"))
            or not _num(snapshot.get("minutes_until_need_floor"))
            or not _num(snapshot.get("reserve_minutes", 0))
            or not _num(snapshot.get("available_funds"))):
        raise ActivityChainError("ACTIVITY_BUDGET_INVALID")
    completed = snapshot.get("completed", [])
    if not isinstance(completed, list) or len(completed) > MAX_STEPS:
        raise ActivityChainError("ACTIVITY_COMPLETIONS_INVALID")
    done = set()
    for row in completed:
        if (not isinstance(row, Mapping) or row.get("step_id") not in nodes
                or row["step_id"] in done or not _ref(row.get("outcome_ref"))
                or row.get("outcome_capture_ref") != capture_ref):
            raise ActivityChainError("ACTIVITY_COMPLETION_PROOF_INVALID")
        done.add(row["step_id"])
    inflight = snapshot.get("inflight_step")
    if inflight is not None:
        if inflight not in nodes or inflight in done:
            raise ActivityChainError("ACTIVITY_INFLIGHT_INVALID")
        return _receipt(capture_ref, "RECONCILE_INFLIGHT_BEFORE_REPLAY", mode=mode,
                        retained_goal_ids=sorted(set(nodes) - done), inflight_step=inflight)
    blocked_resources = snapshot.get("blocked_resources", [])
    if (not isinstance(blocked_resources, list)
            or any(not _ref(x) for x in blocked_resources)):
        raise ActivityChainError("ACTIVITY_RESOURCE_STATE_INVALID")
    budget = max(0.0, min(snapshot["minutes_until_work"],
                           snapshot["minutes_until_need_floor"]) - snapshot.get("reserve_minutes", 0))
    spent, elapsed = 0.0, 0.0
    position = snapshot["location"]
    queue = []
    waiting = set(nodes) - done
    # A verified teleport capability is scoped to the current capture/Sim.
    teleport = snapshot.get("teleport_unlocked") is True and _ref(snapshot.get("teleport_evidence_ref"))
    while waiting:
        ready = [nodes[sid] for sid in waiting if set(nodes[sid]["after"]) <= done]
        if not ready:
            break
        ready.sort(key=lambda x: (x.get("deadline_minutes", 1_000_000), -x.get("value", 1), x["id"]))
        choice = None
        for row in ready:
            if set(row["resources"]) & set(blocked_resources):
                continue
            passage = _route(routes, position, row["location"], capture_ref=capture_ref,
                             teleport_unlocked=bool(teleport))
            if passage is None:
                continue
            required = passage["upper_minutes"] + row["upper_minutes"]
            if (elapsed + required <= budget and spent + row.get("cost", 0) <= snapshot["available_funds"]
                    and elapsed + required <= row.get("deadline_minutes", 1_000_000)):
                choice = row, passage, required
                break
        if choice is None:
            break
        row, passage, required = choice
        if passage["method"] != "STAY":
            queue.append({"kind": "TRAVEL", "method": passage["method"],
                          "from": position, "to": row["location"],
                          "upper_minutes": passage["upper_minutes"],
                          "evidence_ref": passage["evidence_ref"]})
        queue.append({"kind": "ACTIVITY", "step_id": row["id"],
                      "domain": row["domain"], "activity_kind": row["kind"],
                      "upper_minutes": row["upper_minutes"],
                      "evidence_ref": row["evidence_ref"]})
        position = row["location"]
        elapsed += required
        spent += row.get("cost", 0)
        done.add(row["id"])
        waiting.remove(row["id"])
    gate = "PLAN_STAGED" if queue and mode == "PLANNING" else (
        "EFFECT_ADMISSION_REQUIRED" if queue else "INSUFFICIENT_EVIDENCE_OR_BUDGET")
    return _receipt(capture_ref, gate, mode=mode, steps=queue,
                    deferred=sorted(waiting), total_upper_minutes=elapsed,
                    projected_spend=spent, available_minutes=budget,
                    retained_goal_ids=sorted(nodes), sim_ref=snapshot["sim_ref"])


def gp_duration_forecast(samples: Sequence[Mapping], x: float, *, cohort: str,
                         kernel: str = "MATERN32", length_scale: float = 1.0,
                         amplitude: float = 10.0, noise: float = 0.1,
                         period: float = 24.0) -> dict:
    """Small-data GP, cohort-isolated, advisory-only posterior duration bound.

    Never infer effect availability, a game's discontinuous rules or permits.
    A caller must validate cohort provenance and independently enforce hard caps.
    """
    if (not _ref(cohort) or not isinstance(samples, (list, tuple))
            or not 3 <= len(samples) <= 24 or kernel not in ("RBF", "MATERN32", "PERIODIC")
            or not _num(x) or not all(_num(y, positive=True) for y in (length_scale, amplitude, noise, period))):
        raise ActivityChainError("GP_PARAMETERS_INVALID")
    refs = set()
    values = []
    for s in samples:
        if (not isinstance(s, Mapping) or s.get("cohort") != cohort
                or not _ref(s.get("observation_ref")) or s["observation_ref"] in refs
                or not _num(s.get("x")) or not _num(s.get("minutes"), positive=True)):
            raise ActivityChainError("GP_COHORT_OR_EVIDENCE_INVALID")
        refs.add(s["observation_ref"])
        values.append((float(s["x"]), float(s["minutes"])))
    def cov(a: float, b: float) -> float:
        d = abs(a-b) / length_scale
        if kernel == "RBF":
            return amplitude**2 * math.exp(-0.5*d*d)
        if kernel == "MATERN32":
            z = math.sqrt(3.0)*d
            return amplitude**2 * (1+z)*math.exp(-z)
        return amplitude**2 * math.exp(-2 * math.sin(math.pi*abs(a-b)/period)**2 / length_scale**2)
    n = len(values)
    baseline = sum(v for _,v in values)/n
    gram = [[cov(a[0],b[0]) + (noise**2 + 1e-8 if i == j else 0)
             for j,b in enumerate(values)] for i,a in enumerate(values)]
    # Cholesky solve, no covariance inversion or unbounded linear algebra dependency.
    lower = [[0.0]*n for _ in range(n)]
    for i in range(n):
        for j in range(i+1):
            rest = gram[i][j] - sum(lower[i][k]*lower[j][k] for k in range(j))
            if i == j:
                if rest <= 0 or not math.isfinite(rest):
                    raise ActivityChainError("GP_NUMERICALLY_UNSTABLE")
                lower[i][j] = math.sqrt(rest)
            else:
                lower[i][j] = rest/lower[j][j]
    def solve(vector: list[float]) -> list[float]:
        forward = [0.0]*n
        for i in range(n):
            forward[i] = (vector[i] - sum(lower[i][j]*forward[j] for j in range(i)))/lower[i][i]
        backward = [0.0]*n
        for i in reversed(range(n)):
            backward[i] = (forward[i] - sum(lower[j][i]*backward[j] for j in range(i+1,n)))/lower[i][i]
        return backward
    projection = [cov(x, v[0]) for v in values]
    alpha = solve([v[1]-baseline for v in values])
    mean = max(0.0, baseline + sum(a*b for a,b in zip(projection, alpha)))
    variance = max(0.0, cov(x,x) - sum(a*b for a,b in zip(projection, solve(projection))))
    sigma = math.sqrt(variance)
    return {"schema": "betterinstincts.gp-duration/v1", "cohort": cohort,
            "kernel": kernel, "mean_minutes": mean, "sigma_minutes": sigma,
            "upper_minutes": mean + 2*sigma,
            "sample_count": n, "execute_allowed": False,
            "proof_ceiling": "OFFLINE_STATISTICAL_ESTIMATE_NOT_GAME_TIMING_PROOF"}
