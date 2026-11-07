"""P124 shared primitives for tandem need services.

Agents must reuse these helpers instead of reinventing need/object/lane parsing.
Evaluate-only — never clicks the game or starts a daemon.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
NEEDS = ROOT / "contracts" / "needs.v1.json"
SIX = frozenset({"hunger", "bladder", "energy", "hygiene", "fun", "social"})
SURVIVAL = frozenset({"bladder", "hunger", "energy"})


class NeedServiceBaseError(ValueError):
    pass


def threshold_pair(path: Path = NEEDS) -> tuple[float, float]:
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    return float(cfg["urgency_threshold"]), float(cfg["preemptive_threshold"])


def normalize_needs(raw: Mapping[str, float]) -> dict[str, float]:
    if set(raw) != SIX:
        raise NeedServiceBaseError("SIX_NEEDS_REQUIRED")
    out = {}
    for k, v in raw.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not (0 <= float(v) <= 1):
            raise NeedServiceBaseError("INVALID_NEED")
        out[k] = float(v)
    return out


def norm_token(text: str) -> str:
    return str(text or "").strip().lower().replace("-", "_").replace(" ", "_")


def objects_free(
    required: Sequence[str],
    available: set[str],
    occupied: set[str],
) -> bool:
    """True when any required object is free (available and not occupied)."""
    if not required:
        return True
    for obj in required:
        o = norm_token(obj)
        if o in occupied:
            continue
        if not available or o in available or any(o in a or a in o for a in available):
            return True
    if not available:
        return not any(norm_token(obj) in occupied for obj in required)
    return False


def life_stage_ok(lane: Mapping[str, object], life_stage: str, traits: Sequence[str]) -> bool:
    stages = {norm_token(str(s)) for s in (lane.get("life_stages") or [])}
    if not stages:
        return True
    if norm_token(life_stage) in stages:
        return True
    also = {norm_token(str(t)) for t in (lane.get("also_trait") or [])}
    return bool(also.intersection({norm_token(t) for t in traits}))


def survival_critical(needs: Mapping[str, float], urgent: Optional[float] = None) -> list[str]:
    thr = float(urgent if urgent is not None else threshold_pair()[0])
    snap = normalize_needs(needs)
    return sorted(n for n in SURVIVAL if snap[n] < thr)


def plan_lanes(
    *,
    need_id: str,
    lanes: Mapping[str, dict],
    lane_order: Sequence[str],
    available: set[str],
    occupied: set[str],
    claimed: set[str],
    life_stage: str = "young_adult",
    traits: Sequence[str] = (),
    require_emotion_ok: bool = True,
    emotion_gate_label: str = "NEEDS_EMOTION",
) -> tuple[list[dict], list[str], list[str], list[dict], list[str]]:
    """Evaluate independent lanes for one need service.

    Returns (lane_results, parallel_ready, preferred_routes, next_actions, findings).
    """
    lane_results: list[dict] = []
    parallel_ready: list[str] = []
    preferred_routes: list[str] = []
    next_actions: list[dict] = []
    findings: list[str] = []

    for lane_id in lane_order:
        lane = lanes.get(lane_id)
        if not isinstance(lane, dict):
            continue
        if not life_stage_ok(lane, life_stage, traits):
            lane_results.append(
                {
                    "id": lane_id,
                    "service_id": lane.get("service_id"),
                    "status": "LIFE_STAGE_SKIP",
                    "actions": [],
                }
            )
            continue
        requires_emo = lane.get("requires_emotion") or []
        if requires_emo and not require_emotion_ok:
            lane_results.append(
                {
                    "id": lane_id,
                    "service_id": lane.get("service_id"),
                    "status": emotion_gate_label,
                    "actions": [],
                }
            )
            findings.append(emotion_gate_label)
            continue
        if lane_id in claimed:
            lane_results.append(
                {
                    "id": lane_id,
                    "service_id": lane.get("service_id"),
                    "status": "CLAIMED_BY_SIBLING_SIM",
                    "actions": [],
                }
            )
            findings.append("MONOLITH_SINGLE_NEED_QUEUE_FOR_ALL_SIMS")
            continue

        ready_actions = []
        blocked: list[str] = []
        for act in lane.get("activities", []):
            objs = list(act.get("objects", []))
            if not objects_free(objs, available, occupied):
                blocked.extend(norm_token(o) for o in objs)
                continue
            if any(norm_token(o) in occupied for o in objs):
                blocked.extend(norm_token(o) for o in objs)
                continue
            ready_actions.append(
                {
                    "id": act["id"],
                    "need": need_id,
                    "lane": lane_id,
                    "service_id": lane.get("service_id"),
                    "labels": list(act.get("labels", [])),
                    "objects": objs,
                    "steps": list(act.get("steps", [])),
                    "contention_class": lane.get("contention_class"),
                }
            )

        if ready_actions:
            status = "READY"
            parallel_ready.append(lane_id)
            for act in ready_actions:
                if act["id"] not in preferred_routes:
                    preferred_routes.append(act["id"])
                next_actions.append(act)
        elif blocked:
            status = "CONTENDED"
            findings.append("NEED_OBJECT_CONTENTION")
        else:
            status = "NO_MATCHING_OBJECTS"

        lane_results.append(
            {
                "id": lane_id,
                "service_id": lane.get("service_id"),
                "status": status,
                "blocked_objects": sorted(set(blocked)),
                "actions": ready_actions,
            }
        )

    return lane_results, parallel_ready, preferred_routes, next_actions, findings
