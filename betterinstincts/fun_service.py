"""Independent Fun-need service: parallel activity lanes under guest contention.

Offline / host planning only. Peer to event_balance/school_day — not a daemon.
Never clicks the game or claims EA tuning truth.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "fun-service.v1.json"
NEEDS = ROOT / "contracts" / "needs.v1.json"
SIX = frozenset({"hunger", "bladder", "energy", "hygiene", "fun", "social"})
SURVIVAL = frozenset({"bladder", "hunger", "energy"})


class FunServiceError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 512000:
        raise FunServiceError("UNSAFE_FUN_SERVICE_CONTRACT")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.fun-service/v1":
        raise FunServiceError("INVALID_FUN_SERVICE_SCHEMA")
    if not isinstance(data.get("lanes"), dict) or not data["lanes"]:
        raise FunServiceError("FUN_LANES_EMPTY")
    return data


def _threshold_pair() -> tuple[float, float]:
    cfg = json.loads(NEEDS.read_text(encoding="utf-8"))
    return float(cfg["urgency_threshold"]), float(cfg["preemptive_threshold"])


def _needs(raw: Mapping[str, float]) -> dict[str, float]:
    if set(raw) != SIX:
        raise FunServiceError("SIX_NEEDS_REQUIRED")
    out = {}
    for k, v in raw.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not (0 <= float(v) <= 1):
            raise FunServiceError("INVALID_NEED")
        out[k] = float(v)
    return out


def _norm(text: str) -> str:
    return str(text or "").strip().lower().replace("-", "_").replace(" ", "_")


def _is_playful(emotion: Optional[str], moodlets: Sequence[str]) -> bool:
    if emotion and "playful" in _norm(emotion):
        return True
    return any("playful" in _norm(m) for m in moodlets)


def _objects_free(
    required: Sequence[str],
    available: set[str],
    occupied: set[str],
) -> bool:
    if not required:
        return True
    # Activity is usable if any required object is available and not occupied.
    for obj in required:
        o = _norm(obj)
        if o in occupied:
            continue
        if not available or o in available or any(o in a or a in o for a in available):
            return True
    # If available_objects empty → unknown inventory; allow personal_portable-style guess
    # only when required objects are never listed as occupied.
    if not available:
        return not any(_norm(obj) in occupied for obj in required)
    return False


def _life_ok(lane: dict, life_stage: str, traits: Sequence[str]) -> bool:
    stages = {_norm(s) for s in lane.get("life_stages", [])}
    if not stages:
        return True
    if _norm(life_stage) in stages:
        return True
    also = {_norm(t) for t in lane.get("also_trait", [])}
    return bool(also.intersection({_norm(t) for t in traits}))


def should_attach_fun_service(
    needs: Mapping[str, float],
    *,
    guests_present: bool = False,
    force: bool = False,
) -> bool:
    """Attach whenever Fun is urgent/low or guests contend for lot activities."""
    if force:
        return True
    snap = _needs(needs)
    urgent, preemptive = _threshold_pair()
    if snap["fun"] < preemptive:
        return True
    return bool(guests_present) and snap["fun"] < 0.75


def evaluate_fun_service(
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
    sibling_lane_claims: Sequence[str] = (),
    capture_ref: str = "capture:fun-service",
) -> dict:
    """Plan Fun recovery across independent lanes; prefer free/portable under contention."""
    cfg = load_contract()
    snap = _needs(needs)
    urgent, preemptive = _threshold_pair()
    survival_critical = sorted(n for n in SURVIVAL if snap[n] < urgent)
    fun_level = snap["fun"]
    fun_urgent = fun_level < urgent
    fun_low = fun_level < preemptive
    playful = _is_playful(emotion, moodlets)
    available = {_norm(o) for o in available_objects if str(o).strip()}
    occupied = {_norm(o) for o in occupied_objects if str(o).strip()}
    claimed = {_norm(c) for c in sibling_lane_claims if str(c).strip()}
    findings: list[str] = []

    if player_directed or already_busy:
        return {
            "schema": "betterinstincts.fun-service-result/v1",
            "state": "FUN_SERVICE_YIELDED",
            "capture_ref": capture_ref,
            "gate": "PLAYER_FIRST_OR_BUSY",
            "action": "YIELD_OR_EMULATE_ONLY",
            "lanes": [],
            "parallel_ready": [],
            "preferred_routes": [],
            "primary_route": None,
            "next_actions": [],
            "findings": ["PLAYER_FIRST"],
            "fun_level": fun_level,
            "proof_ceiling": cfg["proof_ceiling"],
        }

    if survival_critical:
        return {
            "schema": "betterinstincts.fun-service-result/v1",
            "state": "FUN_SERVICE_DEFERRED",
            "capture_ref": capture_ref,
            "gate": "SURVIVAL_NEEDS_CRITICAL",
            "action": "RECOVER_SURVIVAL_BEFORE_FUN",
            "lanes": [],
            "parallel_ready": [],
            "preferred_routes": [],
            "primary_route": None,
            "next_actions": [],
            "findings": ["SURVIVAL_OUTRANKS_FUN"],
            "survival_critical": survival_critical,
            "fun_level": fun_level,
            "proof_ceiling": cfg["proof_ceiling"],
        }

    if event_active and event_fun_via_goals and not fun_urgent:
        findings.append("LEAVE_EVENT_FOR_TV_FLUFF_WHEN_EVENT_GOALS_COVER_FUN")
        # Still surface portable lane if guests contend — do not leave party for shared TV.
        guests_present = True

    if guests_present or occupied:
        findings.append("SHARED_FUN_OBJECT_CONTENTION")
    if guests_present:
        findings.append("GUESTS_PRESENT_PREFER_PORTABLE_FUN")

    order = list(
        cfg["lane_priority_when_guests"]
        if (guests_present or occupied)
        else cfg["lane_priority_default"]
    )

    lane_results = []
    parallel_ready: list[str] = []
    preferred_routes: list[str] = []
    next_actions: list[dict] = []

    for lane_id in order:
        lane = cfg["lanes"].get(lane_id)
        if not isinstance(lane, dict):
            continue
        if not _life_ok(lane, life_stage, traits):
            lane_results.append(
                {
                    "id": lane_id,
                    "service_id": lane.get("service_id"),
                    "status": "LIFE_STAGE_SKIP",
                    "actions": [],
                }
            )
            continue
        requires_emo = {_norm(e).upper() for e in lane.get("requires_emotion", [])}
        if requires_emo and not playful:
            lane_results.append(
                {
                    "id": lane_id,
                    "service_id": lane.get("service_id"),
                    "status": "NEEDS_PLAYFUL",
                    "actions": [],
                }
            )
            findings.append("PLAYFUL_EXCLUSIVE_WITHOUT_PLAYFUL_EMOTION")
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
            findings.append("MONOLITH_SINGLE_FUN_QUEUE_FOR_ALL_SIMS")
            continue

        ready_actions = []
        blocked = []
        for act in lane.get("activities", []):
            objs = list(act.get("objects", []))
            if act.get("playful") == "requires" and not playful:
                continue
            if not _objects_free(objs, available, occupied):
                blocked.extend(_norm(o) for o in objs)
                continue
            # Prefer not recommending objects that are occupied even as soft matches.
            if any(_norm(o) in occupied for o in objs):
                blocked.extend(_norm(o) for o in objs)
                continue
            ready_actions.append(
                {
                    "id": act["id"],
                    "lane": lane_id,
                    "service_id": lane.get("service_id"),
                    "labels": list(act.get("labels", [])),
                    "objects": objs,
                    "steps": list(act.get("steps", [])),
                    "fun_speed": act.get("fun_speed"),
                    "playful": act.get("playful"),
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
            findings.append("PILE_ONTO_CONTENDED_TV_OR_COMPUTER")
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

    if guests_present and "personal_portable" not in parallel_ready:
        findings.append("IGNORE_PORTABLE_FUN_WHEN_GUESTS_PRESENT")

    # Queue already doing fun? reinforce rather than thrash.
    qnorm = " ".join(_norm(q).replace("_", " ") for q in queue)
    queue_covers = any(
        any( _norm(lab).replace("_", " ") in qnorm for lab in act.get("labels", []) )
        for act in next_actions
    )
    if queue and queue_covers:
        findings.append("FUN_ALREADY_QUEUED_REINFORCE")

    if not fun_urgent and not fun_low and not guests_present:
        gate = "FUN_WATCH_OPTIONAL"
        action = "ALLOW_LEISURE_FUN_LANES"
        disposition = "EMULATE"
    elif parallel_ready:
        gate = "FUN_SERVICE_PLAN"
        action = "QUEUE_FREE_FUN_LANE_ACTION"
        disposition = "OPTIMIZE" if (guests_present or occupied) else "EMULATE_THEN_OPTIMIZE"
    else:
        gate = "FUN_SERVICE_BLOCKED"
        action = "FIND_OR_PLACE_FUN_OBJECT_OR_USE_PHONE"
        disposition = "OPTIMIZE"
        findings.append("NO_FREE_FUN_LANE")

    primary = preferred_routes[0] if preferred_routes else None
    # Under guest contention, force portable id first when present.
    if guests_present or occupied:
        for act in next_actions:
            if act["lane"] == "personal_portable":
                primary = act["id"]
                preferred_routes = [
                    primary,
                    *[r for r in preferred_routes if r != primary],
                ]
                break

    return {
        "schema": "betterinstincts.fun-service-result/v1",
        "state": "FUN_SERVICE_EVALUATED",
        "capture_ref": capture_ref,
        "gate": gate,
        "action": action,
        "disposition": disposition,
        "lanes": lane_results,
        "parallel_ready": parallel_ready,
        "preferred_routes": preferred_routes,
        "primary_route": primary,
        "next_actions": next_actions[:8],
        "findings": sorted(set(findings)),
        "fun_level": fun_level,
        "fun_urgent": fun_urgent,
        "fun_low": fun_low,
        "guests_present": bool(guests_present),
        "occupied_objects": sorted(occupied),
        "playful": playful,
        "architecture": "TANDEM_LANE_SERVICES_NOT_MONOLITH_QUEUE",
        "proof_ceiling": cfg["proof_ceiling"],
    }
