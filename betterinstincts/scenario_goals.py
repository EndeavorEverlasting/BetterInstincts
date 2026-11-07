"""Scenario scoring goals → Sims interaction catalog for hosted scenario play.

Offline / host planning only. Never clicks the game or claims EA career/income cert.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "scenario-goals.v1.json"
SIX = frozenset({"hunger", "bladder", "energy", "hygiene", "fun", "social"})
SURVIVAL = frozenset({"hunger", "bladder", "energy"})
SURVIVAL_THRESHOLD = 0.35


class ScenarioGoalsError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 256000:
        raise ScenarioGoalsError("UNSAFE_SCENARIO_GOALS_CONTRACT")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.scenario-goals/v1":
        raise ScenarioGoalsError("INVALID_SCENARIO_GOALS_SCHEMA")
    if not isinstance(data.get("goals"), dict) or not data["goals"]:
        raise ScenarioGoalsError("SCENARIO_GOALS_EMPTY")
    if not isinstance(data.get("profiles"), dict) or not data["profiles"]:
        raise ScenarioGoalsError("SCENARIO_PROFILES_EMPTY")
    return data


def _norm(text: str) -> str:
    s = str(text or "").strip().lower().replace("_", " ")
    s = re.sub(r"[^a-z0-9\s§]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def resolve_goal_id(label: str, cfg: Optional[dict] = None) -> Optional[str]:
    """Map a HUD/operator label to a canonical scenario goal id, or None if unknown."""
    cfg = cfg or load_contract()
    needle = _norm(label)
    if not needle:
        return None
    for goal_id, row in cfg["goals"].items():
        aliases = [_norm(goal_id), *(_norm(a) for a in row.get("hud_aliases", []))]
        hint = _norm(row.get("display_hint", ""))
        if needle in aliases or needle == hint:
            return str(goal_id)
        if any(needle == a or needle in a or a in needle for a in aliases if a):
            return str(goal_id)
    return None


def _profile(cfg: dict, scenario_profile: str) -> tuple[dict, str]:
    profiles = cfg["profiles"]
    key = _norm(scenario_profile).replace(" ", "_") or str(cfg.get("default_profile") or "scoring_simoleons")
    if key in profiles:
        return dict(profiles[key]), key
    for pid, row in profiles.items():
        aliases = {_norm(pid), *(_norm(a) for a in row.get("aliases", []))}
        if key in aliases or _norm(scenario_profile) in aliases:
            return dict(row), str(pid)
    raise ScenarioGoalsError("UNKNOWN_SCENARIO_PROFILE:" + scenario_profile)


def career_horizon_blocked(
    *,
    allow_career: bool = False,
    needs_game_certified: bool = False,
    income_game_observed: bool = False,
) -> bool:
    """True when get_career must stay deferred per horizon alignment."""
    return not (allow_career and needs_game_certified and income_game_observed)


def _interaction_matches(label: str, interaction: dict) -> bool:
    needle = _norm(label)
    if not needle:
        return False
    for cand in interaction.get("labels", []):
        c = _norm(cand)
        if not c:
            continue
        if needle == c or c in needle or needle in c:
            return True
    return False


def _normalize_goal_ids(incomplete_goals, cfg):
    findings = []
    normalized = []
    unknown = []
    for raw in incomplete_goals:
        gid = resolve_goal_id(raw, cfg)
        if gid is None:
            unknown.append(str(raw))
            findings.append("UNKNOWN_GOAL_LABEL")
            continue
        if gid not in normalized:
            normalized.append(gid)
    return normalized, unknown, findings


def _order_goals(normalized, priority, *, defer_career):
    ordered = [g for g in priority if g in normalized]
    ordered.extend(g for g in normalized if g not in ordered)
    if defer_career and "get_career" in ordered:
        ordered = [g for g in ordered if g != "get_career"] + ["get_career"]
    return ordered


def _match_queue(queue, ordered, cfg):
    hits = {g: [] for g in ordered}
    for item in queue:
        label = str(item)
        for gid in ordered:
            for interaction in cfg["goals"][gid].get("satisfying_interactions", []):
                if _interaction_matches(label, interaction):
                    if label not in hits[gid]:
                        hits[gid].append(label)
                    break
    return hits


def _build_goal_plans(ordered, cfg, queue_hits, *, defer_career):
    plans = []
    for gid in ordered:
        row = cfg["goals"][gid]
        if gid == "get_career" and defer_career:
            plans.append(
                {
                    "goal_id": gid,
                    "display_hint": row.get("display_hint"),
                    "horizon_deferred": True,
                    "satisfying_interactions": [],
                    "queue_matches": [],
                    "in_progress": False,
                    "deferred": True,
                }
            )
            continue
        interactions = [
            {
                "id": inter["id"],
                "labels": list(inter.get("labels", [])),
                "steps": list(inter.get("steps", [])),
                "confidence": inter.get("confidence", "HOST_HEURISTIC"),
            }
            for inter in row.get("satisfying_interactions", [])
        ]
        plans.append(
            {
                "goal_id": gid,
                "display_hint": row.get("display_hint"),
                "target_kind": row.get("target_kind"),
                "preferred_targets": list(row.get("preferred_targets", [])),
                "satisfying_interactions": interactions,
                "non_satisfying": list(row.get("non_satisfying", [])),
                "host_note": row.get("host_note"),
                "queue_matches": list(queue_hits.get(gid, [])),
                "in_progress": bool(queue_hits.get(gid)),
                "horizon_deferred": bool(row.get("horizon_deferred", False)),
            }
        )
    return plans


def _pick_next(plans):
    for plan in plans:
        if plan.get("deferred") or plan["in_progress"] or not plan["satisfying_interactions"]:
            continue
        return plan["goal_id"], list(plan["satisfying_interactions"])
    for plan in plans:
        if plan.get("deferred") or not plan["satisfying_interactions"]:
            continue
        return plan["goal_id"], list(plan["satisfying_interactions"])
    return None, []



def plan_scenario_goals(
    incomplete_goals: Sequence[str],
    *,
    scenario_profile: str = "scoring_simoleons",
    queue: Sequence[str] = (),
    allow_career: bool = False,
    needs_game_certified: bool = False,
    income_game_observed: bool = False,
    capture_ref: str = "capture:scenario-goals",
) -> dict:
    """Plan concrete scenario actions for incomplete HUD goals."""
    cfg = load_contract()
    profile, profile_id = _profile(cfg, scenario_profile)
    priority = [str(g) for g in profile.get("goal_priority", [])]
    defer_career = career_horizon_blocked(
        allow_career=allow_career,
        needs_game_certified=needs_game_certified,
        income_game_observed=income_game_observed,
    )
    normalized, unknown, findings = _normalize_goal_ids(incomplete_goals, cfg)

    if defer_career and "get_career" in normalized:
        findings.append("CAREER_HORIZON_DEFERRED")
    if "motherlode_for_scenario" in (profile.get("forbidden") or []):
        findings.append("MOTHERLODE_FORBIDDEN_FOR_SCENARIO")

    ordered = _order_goals(normalized, priority, defer_career=defer_career)
    queue_hits = _match_queue(queue, ordered, cfg)
    covered = sorted(g for g, labels in queue_hits.items() if labels)
    uncovered = [g for g in ordered if g not in covered]
    if ordered and queue and not covered:
        findings.append("QUEUE_DOES_NOT_SATISFY_SCENARIO_GOALS")

    plans = _build_goal_plans(ordered, cfg, queue_hits, defer_career=defer_career)
    next_goal, next_actions = _pick_next(plans)
    primary_route = str(next_actions[0]["id"]) if next_actions else None
    preferred_routes = [str(a["id"]) for a in next_actions]
    career_only = normalized == ["get_career"]

    return {
        "schema": "betterinstincts.scenario-goals-plan/v1",
        "state": "SCENARIO_GOALS_PLANNED",
        "capture_ref": capture_ref,
        "scenario_profile": profile_id,
        "goals_incomplete": ordered,
        "goals_unknown": unknown,
        "goals_covered_by_queue": covered,
        "goals_uncovered": uncovered,
        "career_horizon_blocked": defer_career,
        "career_goal_only": career_only,
        "next_goal": next_goal,
        "next_actions": next_actions,
        "primary_route": primary_route,
        "preferred_routes": preferred_routes,
        "plans": plans,
        "findings": sorted(set(findings)),
        "proof_ceiling": cfg["proof_ceiling"],
        "action": "QUEUE_INCOMPLETE_SCENARIO_GOALS" if ordered else "NO_SCENARIO_GOALS",
    }


def _needs(raw: Mapping[str, float]) -> dict[str, float]:
    if set(raw) != SIX:
        raise ScenarioGoalsError("SIX_NEEDS_REQUIRED")
    out = {}
    for k, v in raw.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not (0 <= float(v) <= 1):
            raise ScenarioGoalsError("INVALID_NEED")
        out[k] = float(v)
    return out


def evaluate_scenario_turn(
    needs: Mapping[str, float],
    *,
    scenario_active: bool = False,
    scenario_goals_incomplete: Sequence[str] = (),
    scenario_profile: str = "scoring_simoleons",
    school_day_active: bool = False,
    allow_career: bool = False,
    needs_game_certified: bool = False,
    income_game_observed: bool = False,
    player_directed: bool = False,
    already_busy: bool = False,
    queue: Sequence[str] = (),
    capture_ref: str = "capture:scenario-turn",
) -> dict:
    """Return the highest-priority scenario call-stack gate for one turn."""
    cfg = load_contract()
    snap = _needs(needs)
    thr = SURVIVAL_THRESHOLD
    survival_critical = sorted(n for n in SURVIVAL if snap[n] < thr)
    goals = [str(g) for g in scenario_goals_incomplete if isinstance(g, str) and g]
    goal_plan = None
    if scenario_active and goals:
        goal_plan = plan_scenario_goals(
            goals,
            scenario_profile=scenario_profile,
            queue=queue,
            allow_career=allow_career,
            needs_game_certified=needs_game_certified,
            income_game_observed=income_game_observed,
            capture_ref=capture_ref,
        )

    findings: list[str] = []
    if goal_plan:
        findings.extend(goal_plan.get("findings", []))

    stack = list(cfg["call_stack"]["order"])
    gate = "LEISURE_OR_IDLE"
    action = cfg["call_stack"]["gates"]["LEISURE_OR_IDLE"]["action"]
    disposition = "EMULATE"
    preferred_routes: list[str] = []

    if player_directed or already_busy:
        gate, action, disposition = "PLAYER_FIRST_OR_BUSY", "YIELD_OR_EMULATE_ONLY", "EMULATE"
    elif survival_critical:
        gate = "SURVIVAL_NEEDS_CRITICAL"
        action = "RECOVER_SURVIVAL_NEED_LOCAL_OR_MAP_TRAVEL"
        disposition = "OPTIMIZE"
        preferred_routes = ["VENUE_OBJECT_IF_PRESENT", "MAP_TRAVEL_HOME"]
    elif school_day_active and not survival_critical:
        gate = "SCHOOL_DAY_OUTRANKS_SCENARIO"
        action = "DEFER_SCENARIO_TO_SCHOOL_DAY"
        disposition = "EMULATE"
        findings.append("SCHOOL_DAY_OUTRANKS_SCENARIO")
    elif (
        scenario_active
        and goals
        and goal_plan
        and goal_plan.get("career_goal_only")
        and goal_plan.get("career_horizon_blocked")
        and not goal_plan.get("next_goal")
        and not survival_critical
    ):
        gate = "SCENARIO_CAREER_DEFERRED"
        action = "DEFER_CAREER_UNTIL_INCOME_PROOF"
        disposition = "EMULATE"
        findings.append("CAREER_DEFERRED_HORIZON")
    elif scenario_active and goals and goal_plan and goal_plan.get("next_goal") and not survival_critical:
        gate = "SCENARIO_GOAL_PROGRESS"
        action = "QUEUE_INCOMPLETE_SCENARIO_GOALS"
        disposition = "EMULATE_THEN_OPTIMIZE"
        preferred_routes = list(goal_plan.get("preferred_routes") or ["SCENARIO_GOAL_ACTION"])
    elif not scenario_active:
        gate = "SCENARIO_INACTIVE"
        action = "NO_SCENARIO_ROUTING"
        disposition = "EMULATE"

    return {
        "schema": "betterinstincts.scenario-goals-result/v1",
        "state": "SCENARIO_TURN_EVALUATED",
        "capture_ref": capture_ref,
        "gate": gate,
        "action": action,
        "disposition": disposition,
        "preferred_routes": preferred_routes,
        "primary_route": preferred_routes[0] if preferred_routes else None,
        "findings": sorted(set(findings)),
        "survival_critical": survival_critical,
        "scenario_active": scenario_active,
        "goals_incomplete": goals,
        "school_day_active": school_day_active,
        "goal_plan": goal_plan,
        "call_stack_order": stack,
        "proof_ceiling": cfg["proof_ceiling"],
    }
