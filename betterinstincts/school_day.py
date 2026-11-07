"""School-day goal → Sims interaction catalog for hosted school lot play.

Offline / host planning only. Never clicks the game or claims EA tuning truth.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "school-day.v1.json"
SIX = frozenset({"hunger", "bladder", "energy", "hygiene", "fun", "social"})
SURVIVAL = frozenset({"hunger", "bladder", "energy"})
SURVIVAL_THRESHOLD = 0.35


class SchoolDayError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 256000:
        raise SchoolDayError("UNSAFE_SCHOOL_DAY_CONTRACT")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.school-day/v1":
        raise SchoolDayError("INVALID_SCHOOL_DAY_SCHEMA")
    if not isinstance(data.get("goals"), dict) or not data["goals"]:
        raise SchoolDayError("SCHOOL_DAY_GOALS_EMPTY")
    if not isinstance(data.get("profiles"), dict) or not data["profiles"]:
        raise SchoolDayError("SCHOOL_DAY_PROFILES_EMPTY")
    if not isinstance(data.get("phases"), dict) or not data["phases"]:
        raise SchoolDayError("SCHOOL_DAY_PHASES_EMPTY")
    return data


def _norm(text: str) -> str:
    s = str(text or "").strip().lower().replace("_", " ")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def resolve_goal_id(label: str, cfg: Optional[dict] = None) -> Optional[str]:
    """Map a HUD/operator label to a canonical school goal id, or None if unknown."""
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


def resolve_phase(phase_label: str, cfg: Optional[dict] = None) -> tuple[dict, str]:
    cfg = cfg or load_contract()
    phases = cfg["phases"]
    key = _norm(phase_label).replace(" ", "_") or "morning_free_time"
    if key in phases:
        return dict(phases[key]), key
    for pid, row in phases.items():
        aliases = {_norm(pid), *(_norm(a) for a in row.get("aliases", []))}
        if key in aliases or _norm(phase_label) in aliases:
            return dict(row), str(pid)
    raise SchoolDayError("UNKNOWN_SCHOOL_PHASE:" + phase_label)


def _profile(cfg: dict, school_profile: str) -> tuple[dict, str]:
    profiles = cfg["profiles"]
    key = _norm(school_profile).replace(" ", "_") or str(cfg.get("default_profile") or "high_school_years")
    if key in profiles:
        return dict(profiles[key]), key
    for pid, row in profiles.items():
        aliases = {_norm(pid), *(_norm(a) for a in row.get("aliases", []))}
        if key in aliases or _norm(school_profile) in aliases:
            return dict(row), str(pid)
    raise SchoolDayError("UNKNOWN_SCHOOL_PROFILE:" + school_profile)


def match_pinned_whim(
    pinned_whims: Sequence[str],
    *,
    cfg: Optional[dict] = None,
) -> Optional[str]:
    """Return canonical pinned whim id (e.g. not_stumble) when labels match."""
    cfg = cfg or load_contract()
    catalog = cfg.get("pinned_whims") or {}
    for raw in pinned_whims:
        needle = _norm(raw)
        if not needle:
            continue
        for whim_id, row in catalog.items():
            aliases = {_norm(whim_id), *(_norm(a) for a in row.get("aliases", []))}
            if needle in aliases or any(needle == a or a in needle for a in aliases):
                return str(whim_id)
    return None


def homework_blocked_on_premises(
    *,
    location_kind: str,
    school_phase: Optional[str] = None,
    cfg: Optional[dict] = None,
) -> bool:
    """True when homework must not run on the current school premises."""
    if location_kind != "school":
        return False
    cfg = cfg or load_contract()
    panel = (cfg.get("career_panel") or {}).get("homework") or {}
    if panel.get("allowed_on_school_premises") is False:
        return True
    if school_phase:
        try:
            phase_row, _ = resolve_phase(school_phase, cfg)
        except SchoolDayError:
            return True
        if phase_row.get("homework_allowed") is False:
            return True
    return False


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


def plan_school_day_goals(
    incomplete_goals: Sequence[str],
    *,
    school_profile: str = "high_school_years",
    school_phase: str = "morning_free_time",
    queue: Sequence[str] = (),
    pinned_whims: Sequence[str] = (),
    capture_ref: str = "capture:school-day",
) -> dict:
    """Plan concrete school-day actions for incomplete HUD goals."""
    cfg = load_contract()
    profile, profile_id = _profile(cfg, school_profile)
    phase_row, phase_id = resolve_phase(school_phase, cfg)
    priority = [str(g) for g in profile.get("goal_priority", [])]
    findings: list[str] = []
    normalized: list[str] = []
    unknown: list[str] = []
    for raw in incomplete_goals:
        gid = resolve_goal_id(raw, cfg)
        if gid is None:
            unknown.append(str(raw))
            findings.append("UNKNOWN_GOAL_LABEL")
            continue
        if gid not in normalized:
            normalized.append(gid)

    pinned = match_pinned_whim(pinned_whims, cfg=cfg)
    if pinned == "not_stumble":
        findings.append("PINNED_NOT_STUMBLE_PREFERS_STUDY")
        if "study_for_exams" in normalized and normalized[0] != "study_for_exams":
            normalized.remove("study_for_exams")
            normalized.insert(0, "study_for_exams")

    ordered = [g for g in priority if g in normalized]
    ordered.extend(g for g in normalized if g not in ordered)

    queue_hits: dict[str, list[str]] = {g: [] for g in ordered}
    for item in queue:
        label = str(item)
        for gid in ordered:
            for interaction in cfg["goals"][gid].get("satisfying_interactions", []):
                if _interaction_matches(label, interaction):
                    if pinned == "not_stumble" and not interaction.get("stumble_safe", True):
                        findings.append("PINNED_WHIM_REJECTS_ATHLETIC_QUEUE_MATCH")
                        continue
                    if label not in queue_hits[gid]:
                        queue_hits[gid].append(label)
                    break

    covered = sorted(g for g, labels in queue_hits.items() if labels)
    uncovered = [g for g in ordered if g not in covered]
    if ordered and queue and not covered:
        findings.append("QUEUE_DOES_NOT_SATISFY_SCHOOL_GOALS")

    plans = []
    for gid in ordered:
        row = cfg["goals"][gid]
        interactions = []
        for inter in row.get("satisfying_interactions", []):
            if pinned == "not_stumble" and not inter.get("stumble_safe", True):
                continue
            if pinned == "not_stumble" and not inter.get("sedentary", False):
                continue
            interactions.append(
                {
                    "id": inter["id"],
                    "labels": list(inter.get("labels", [])),
                    "steps": list(inter.get("steps", [])),
                    "sedentary": bool(inter.get("sedentary", False)),
                    "stumble_safe": bool(inter.get("stumble_safe", False)),
                    "confidence": inter.get("confidence", "HOST_HEURISTIC"),
                }
            )
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
            }
        )

    next_goal = None
    next_actions: list[dict] = []
    for plan in plans:
        if plan["in_progress"]:
            continue
        if not plan["satisfying_interactions"]:
            continue
        next_goal = plan["goal_id"]
        next_actions = list(plan["satisfying_interactions"])
        break
    if next_goal is None and plans:
        for plan in plans:
            if plan["satisfying_interactions"]:
                next_goal = plan["goal_id"]
                next_actions = list(plan["satisfying_interactions"])
                break
        if covered:
            findings.append("GOALS_ALREADY_QUEUED_REINFORCE")

    primary_route = None
    preferred_routes: list[str] = []
    if next_actions:
        primary_route = str(next_actions[0]["id"])
        preferred_routes = [str(a["id"]) for a in next_actions]

    return {
        "schema": "betterinstincts.school-day-plan/v1",
        "state": "SCHOOL_DAY_GOALS_PLANNED",
        "capture_ref": capture_ref,
        "school_profile": profile_id,
        "school_phase": phase_id,
        "phase_homework_allowed": bool(phase_row.get("homework_allowed", False)),
        "goals_incomplete": ordered,
        "goals_unknown": unknown,
        "goals_covered_by_queue": covered,
        "goals_uncovered": uncovered,
        "pinned_whim": pinned,
        "next_goal": next_goal,
        "next_actions": next_actions,
        "primary_route": primary_route,
        "preferred_routes": preferred_routes,
        "plans": plans,
        "findings": sorted(set(findings)),
        "proof_ceiling": cfg["proof_ceiling"],
        "action": "QUEUE_INCOMPLETE_SCHOOL_GOALS" if ordered else "NO_SCHOOL_GOALS",
    }


def _needs(raw: Mapping[str, float]) -> dict[str, float]:
    if set(raw) != SIX:
        raise SchoolDayError("SIX_NEEDS_REQUIRED")
    out = {}
    for k, v in raw.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not (0 <= float(v) <= 1):
            raise SchoolDayError("INVALID_NEED")
        out[k] = float(v)
    return out


def evaluate_school_day_turn(
    needs: Mapping[str, float],
    *,
    school_day_active: bool = False,
    school_goals_incomplete: Sequence[str] = (),
    school_phase: str = "morning_free_time",
    school_profile: str = "high_school_years",
    location_kind: str = "unknown",
    homework_pending: bool = False,
    player_directed: bool = False,
    already_busy: bool = False,
    queue: Sequence[str] = (),
    pinned_whims: Sequence[str] = (),
    capture_ref: str = "capture:school-turn",
) -> dict:
    """Return the highest-priority school-day call-stack gate for one turn."""
    cfg = load_contract()
    snap = _needs(needs)
    thr = SURVIVAL_THRESHOLD
    survival_critical = sorted(n for n in SURVIVAL if snap[n] < thr)
    goals = [str(g) for g in school_goals_incomplete if isinstance(g, str) and g]
    premises_blocked = homework_blocked_on_premises(
        location_kind=location_kind,
        school_phase=school_phase,
        cfg=cfg,
    )
    goal_plan = None
    if school_day_active and goals:
        goal_plan = plan_school_day_goals(
            goals,
            school_profile=school_profile,
            school_phase=school_phase,
            queue=queue,
            pinned_whims=pinned_whims,
            capture_ref=capture_ref,
        )

    findings: list[str] = []
    if goal_plan:
        findings.extend(goal_plan.get("findings", []))
    if homework_pending and premises_blocked:
        findings.append("HOMEWORK_DEFERRED_ON_SCHOOL_PREMISES")

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
    elif school_day_active and goals and not survival_critical:
        gate = "SCHOOL_DAY_GOAL_PROGRESS"
        action = "QUEUE_INCOMPLETE_SCHOOL_GOALS"
        disposition = "EMULATE_THEN_OPTIMIZE"
        preferred_routes = list((goal_plan or {}).get("preferred_routes") or ["SCHOOL_GOAL_ACTION"])
    elif homework_pending and premises_blocked and not survival_critical:
        gate = "HOMEWORK_PREMISES_BLOCKED"
        action = "DEFER_HOMEWORK_UNTIL_HOME"
        disposition = "EMULATE"
    elif homework_pending and location_kind == "home" and not survival_critical:
        gate = "HOMEWORK_AT_HOME"
        action = "QUEUE_HOMEWORK_AT_HOME"
        disposition = "EMULATE_THEN_OPTIMIZE"
    elif not school_day_active:
        gate = "SCHOOL_DAY_INACTIVE"
        action = "NO_SCHOOL_DAY_ROUTING"
        disposition = "EMULATE"

    return {
        "schema": "betterinstincts.school-day-result/v1",
        "state": "SCHOOL_DAY_TURN_EVALUATED",
        "capture_ref": capture_ref,
        "gate": gate,
        "action": action,
        "disposition": disposition,
        "preferred_routes": preferred_routes,
        "primary_route": preferred_routes[0] if preferred_routes else None,
        "findings": sorted(set(findings)),
        "survival_critical": survival_critical,
        "school_day_active": school_day_active,
        "goals_incomplete": goals,
        "school_phase": school_phase,
        "location_kind": location_kind,
        "homework_pending": homework_pending,
        "homework_blocked_on_premises": premises_blocked,
        "goal_plan": goal_plan,
        "call_stack_order": stack,
        "proof_ceiling": cfg["proof_ceiling"],
    }
