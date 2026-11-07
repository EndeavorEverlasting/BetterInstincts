"""Event hosting balance evaluator — outdoor-social RCA + call-stack gates.

Offline / host planning only. Never rewrites Sims autonomy or clicks the game.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional, Sequence

from betterinstincts.moodlets import MoodletError, evaluate_moodlets

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "event-balance.v1.json"
NEEDS = ROOT / "contracts" / "needs.v1.json"
SIX = frozenset({"hunger", "bladder", "energy", "hygiene", "fun", "social"})
SURVIVAL = frozenset({"bladder", "hunger", "energy"})


class EventBalanceError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 128000:
        raise EventBalanceError("UNSAFE_EVENT_BALANCE_CONTRACT")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.event-balance/v1":
        raise EventBalanceError("INVALID_EVENT_BALANCE_SCHEMA")
    return data


def _threshold() -> float:
    return float(json.loads(NEEDS.read_text(encoding="utf-8"))["urgency_threshold"])


def _needs(raw: Mapping[str, float]) -> dict[str, float]:
    if set(raw) != SIX:
        raise EventBalanceError("SIX_NEEDS_REQUIRED")
    out = {}
    for k, v in raw.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not (0 <= float(v) <= 1):
            raise EventBalanceError("INVALID_NEED")
        out[k] = float(v)
    return out


def evaluate_event_turn(
    needs: Mapping[str, float],
    *,
    event_active: bool = False,
    event_goals_incomplete: Sequence[str] = (),
    outdoor_social_prefix: bool = False,
    indoor_capacity_observed: bool = False,
    homework_pending: bool = False,
    player_directed: bool = False,
    already_busy: bool = False,
    viewport_ok: bool = True,
    emotion: Optional[str] = None,
    moodlets: Sequence[str] = (),
    capture_ref: str = "capture:event-turn",
) -> dict:
    """Return the highest-priority call-stack gate for one hosted-event turn."""
    cfg = load_contract()
    snap = _needs(needs)
    thr = _threshold()
    survival_critical = sorted(n for n in SURVIVAL if snap[n] < thr)
    fun_urgent = snap["fun"] < thr
    goals = [str(g) for g in event_goals_incomplete if isinstance(g, str) and g]
    try:
        mood = evaluate_moodlets(
            emotion=emotion,
            moodlets=moodlets,
            needs=snap,
            outdoor_social_prefix=outdoor_social_prefix,
            indoor_capacity_observed=indoor_capacity_observed,
            event_active=event_active,
            capture_ref=capture_ref,
        )
    except MoodletError as exc:
        raise EventBalanceError(str(exc)) from exc
    findings = []
    if outdoor_social_prefix and indoor_capacity_observed and event_active:
        findings.append("OUTDOOR_SOCIAL_DEFAULT_WITH_INDOOR_CAPACITY")
    if event_active and goals and outdoor_social_prefix:
        findings.append("EVENT_GOAL_NEGLECT_WHILE_SPAMMING_SIDEWALK_CHAT")
    findings.extend(mood.get("findings", []))

    stack = list(cfg["call_stack"]["order"])
    gate = "LEISURE_OR_IDLE"
    action = cfg["call_stack"]["gates"]["LEISURE_OR_IDLE"]["action"]
    disposition = "EMULATE"
    preferred_routes: list[str] = []

    if player_directed or already_busy:
        gate, action, disposition = "PLAYER_FIRST_OR_BUSY", "YIELD_OR_EMULATE_ONLY", "EMULATE"
    elif not viewport_ok:
        gate, action, disposition = (
            "VIEWPORT_OK",
            "RECOVER_VIEWPORT_BEFORE_EVENT_CLICKS",
            "OPTIMIZE",
        )
    elif survival_critical:
        gate = "SURVIVAL_NEEDS_CRITICAL"
        action = "RECOVER_SURVIVAL_NEED_LOCAL_OR_MAP_TRAVEL"
        disposition = "OPTIMIZE"
        preferred_routes = ["VENUE_OBJECT_IF_PRESENT", "MAP_TRAVEL_HOME"]
    elif event_active and outdoor_social_prefix and indoor_capacity_observed:
        gate = "EVENT_INDOOR_ROUTING"
        action = "CANCEL_OUTDOOR_WALK_RETARGET_INDOOR"
        disposition = "OPTIMIZE"
        preferred_routes = list(
            cfg["call_stack"]["gates"]["EVENT_INDOOR_ROUTING"]["preferred_routes"]
        )
        if "TENSE_MOOD_OUTDOOR_SOCIAL" in mood.get("findings", []):
            preferred_routes = ["CLICK_INDOOR_SIM", "GO_HERE_INDOOR", *preferred_routes]
    elif event_active and goals and not survival_critical:
        gate = "EVENT_GOAL_PROGRESS"
        action = "QUEUE_INCOMPLETE_EVENT_GOALS_INDOOR"
        disposition = "EMULATE_THEN_OPTIMIZE"
        preferred_routes = ["INDOOR_GOAL_ACTION"]
        if fun_urgent:
            findings.append("FUN_VIA_EVENT_GOALS")
            gate = "EVENT_FUN_VIA_GOALS"
            action = "SATISFY_FUN_THROUGH_EVENT_GOALS_NOT_LEAVE"
    elif homework_pending and event_active and not survival_critical:
        gate = "HOMEWORK_HOLD_OR_SCHEDULE"
        action = "HOLD_UNTIL_EVENT_ENDS_OR_SURVIVAL_FORCES_HOME"
        disposition = "EMULATE"
    elif homework_pending and not event_active:
        gate = "HOMEWORK_HOLD_OR_SCHEDULE"
        action = "DO_HOMEWORK_WHEN_EVENT_CLEAR"
        disposition = "EMULATE_THEN_OPTIMIZE"
    elif any(snap[n] < thr for n in ("hygiene", "fun", "social")):
        gate = "NONCRITICAL_NEEDS"
        action = "RECOVER_IF_NOT_COVERED_BY_EVENT"
        disposition = "EMULATE_THEN_OPTIMIZE"

    if "TENSE_MOOD_OUTDOOR_SOCIAL" in mood.get("findings", []):
        findings.append("MOODLET_REINFORCES_INDOOR_ROUTING")

    leading = [h["id"] for h in cfg["rca"]["hypotheses"] if h.get("status") == "LEADING"]
    return {
        "schema": "betterinstincts.event-balance-result/v1",
        "state": "EVENT_TURN_EVALUATED",
        "capture_ref": capture_ref,
        "gate": gate,
        "action": action,
        "disposition": disposition,
        "preferred_routes": preferred_routes,
        "findings": sorted(set(findings)),
        "survival_critical": survival_critical,
        "fun_urgent": fun_urgent,
        "event_active": event_active,
        "goals_incomplete": goals,
        "homework_pending": homework_pending,
        "moodlets": mood,
        "call_stack_order": stack,
        "rca_leading": leading,
        "proof_ceiling": cfg["proof_ceiling"],
    }
