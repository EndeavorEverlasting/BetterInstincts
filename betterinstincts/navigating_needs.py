"""Navigating Needs Discovery Quest → motive-aligned host tandem planner.

Works with EA's top-left Navigating Needs panel: prefer actions that tick both
the linked motive and the incomplete quest goal. Offline / host planning only.
Never clicks the game or claims BI-002 hunger certification.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "navigating-needs.v1.json"
SIX = frozenset({"hunger", "bladder", "energy", "hygiene", "fun", "social"})


class NavigatingNeedsError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 256000:
        raise NavigatingNeedsError("UNSAFE_NAVIGATING_NEEDS_CONTRACT")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.navigating-needs/v1":
        raise NavigatingNeedsError("INVALID_NAVIGATING_NEEDS_SCHEMA")
    if not isinstance(data.get("goals"), dict) or not data["goals"]:
        raise NavigatingNeedsError("NAVIGATING_NEEDS_GOALS_EMPTY")
    if not isinstance(data.get("profiles"), dict) or not data["profiles"]:
        raise NavigatingNeedsError("NAVIGATING_NEEDS_PROFILES_EMPTY")
    return data


def _norm(text: str) -> str:
    s = str(text or "").strip().lower().replace("_", " ")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def resolve_goal_id(label: str, cfg: Optional[dict] = None) -> Optional[str]:
    """Map a HUD/operator label to a canonical Navigating Needs goal id."""
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


def _profile(cfg: dict, quest_profile: str) -> tuple[dict, str]:
    profiles = cfg["profiles"]
    key = _norm(quest_profile).replace(" ", "_") or str(
        cfg.get("default_profile") or "navigating_needs"
    )
    if key in profiles:
        return dict(profiles[key]), key
    for pid, row in profiles.items():
        aliases = {_norm(pid), *(_norm(a) for a in row.get("aliases", []))}
        if key in aliases or _norm(quest_profile) in aliases:
            return dict(row), str(pid)
    raise NavigatingNeedsError("UNKNOWN_NAVIGATING_NEEDS_PROFILE:" + quest_profile)


def _needs(raw: Mapping[str, float]) -> dict[str, float]:
    if set(raw) != SIX:
        raise NavigatingNeedsError("SIX_NEEDS_REQUIRED")
    out = {}
    for k, v in raw.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not (0 <= float(v) <= 1):
            raise NavigatingNeedsError("INVALID_NEED")
        out[k] = float(v)
    return out


def urgency_band(level: float, *, urgent: float, preempt: float) -> str:
    if level < urgent:
        return "critical"
    if level < preempt:
        return "low"
    if level < 0.75:
        return "watch"
    return "ok"


def urgent_motives(
    needs: Mapping[str, float],
    *,
    threshold: Optional[float] = None,
    cfg: Optional[dict] = None,
) -> list[str]:
    cfg = cfg or load_contract()
    thr = float(threshold if threshold is not None else cfg["urgency"]["urgent_threshold"])
    snap = _needs(needs)
    return sorted(n for n in SIX if snap[n] < thr)


def linked_need(goal_id: str, cfg: Optional[dict] = None) -> Optional[str]:
    cfg = cfg or load_contract()
    row = cfg["goals"].get(goal_id) or {}
    need = row.get("linked_need")
    return str(need) if need in SIX else None


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


def order_goals_by_motive_urgency(
    goal_ids: Sequence[str],
    needs: Mapping[str, float],
    *,
    fallback_priority: Sequence[str],
    cfg: Optional[dict] = None,
) -> list[str]:
    """Lowest linked motive first; ties use profile fallback, then input order."""
    cfg = cfg or load_contract()
    snap = _needs(needs)
    urgent = float(cfg["urgency"]["urgent_threshold"])
    preempt = float(cfg["urgency"]["preemptive_threshold"])
    band_rank = {"critical": 0, "low": 1, "watch": 2, "ok": 3}
    fallback_index = {g: i for i, g in enumerate(fallback_priority)}

    def sort_key(gid: str):
        need = linked_need(gid, cfg) or "fun"
        level = snap.get(need, 1.0)
        return (
            band_rank[urgency_band(level, urgent=urgent, preempt=preempt)],
            level,
            fallback_index.get(gid, 99),
            list(goal_ids).index(gid) if gid in goal_ids else 99,
        )

    return sorted(goal_ids, key=sort_key)


def _build_goal_plans(ordered, cfg, queue_hits):
    plans = []
    for gid in ordered:
        row = cfg["goals"][gid]
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
                "linked_need": row.get("linked_need"),
                "target_kind": row.get("target_kind"),
                "preferred_targets": list(row.get("preferred_targets", [])),
                "satisfying_interactions": interactions,
                "non_satisfying": list(row.get("non_satisfying", [])),
                "host_note": row.get("host_note"),
                "queue_matches": list(queue_hits.get(gid, [])),
                "in_progress": bool(queue_hits.get(gid)),
            }
        )
    return plans


def _pick_next(plans):
    for plan in plans:
        if plan["in_progress"] or not plan["satisfying_interactions"]:
            continue
        return plan["goal_id"], list(plan["satisfying_interactions"])
    for plan in plans:
        if not plan["satisfying_interactions"]:
            continue
        return plan["goal_id"], list(plan["satisfying_interactions"])
    return None, []


def plan_navigating_needs(
    incomplete_goals: Sequence[str],
    needs: Mapping[str, float],
    *,
    quest_profile: str = "navigating_needs",
    queue: Sequence[str] = (),
    capture_ref: str = "capture:navigating-needs",
) -> dict:
    """Plan panel-aligned need remedies for incomplete Navigating Needs goals."""
    cfg = load_contract()
    profile, profile_id = _profile(cfg, quest_profile)
    fallback = [str(g) for g in profile.get("goal_priority_fallback", [])]
    snap = _needs(needs)
    normalized, unknown, findings = _normalize_goal_ids(incomplete_goals, cfg)
    ordered = order_goals_by_motive_urgency(
        normalized, snap, fallback_priority=fallback, cfg=cfg
    )
    queue_hits = _match_queue(queue, ordered, cfg)
    covered = sorted(g for g, labels in queue_hits.items() if labels)
    uncovered = [g for g in ordered if g not in covered]
    if ordered and queue and not covered:
        findings.append("QUEUE_DOES_NOT_SATISFY_NAVIGATING_NEEDS")

    plans = _build_goal_plans(ordered, cfg, queue_hits)
    next_goal, next_actions = _pick_next(plans)
    primary_route = str(next_actions[0]["id"]) if next_actions else None
    preferred_routes = [str(a["id"]) for a in next_actions]
    panel_motives = {
        linked_need(g, cfg) for g in ordered if linked_need(g, cfg) is not None
    }
    urgent = urgent_motives(snap, cfg=cfg)
    uncovered_urgent = [n for n in urgent if n not in panel_motives]

    return {
        "schema": "betterinstincts.navigating-needs-plan/v1",
        "state": "NAVIGATING_NEEDS_PLANNED",
        "capture_ref": capture_ref,
        "quest_profile": profile_id,
        "goals_incomplete": ordered,
        "goals_unknown": unknown,
        "goals_covered_by_queue": covered,
        "goals_uncovered": uncovered,
        "panel_linked_motives": sorted(panel_motives),
        "urgent_motives": urgent,
        "uncovered_urgent_motives": uncovered_urgent,
        "next_goal": next_goal,
        "next_need": linked_need(next_goal, cfg) if next_goal else None,
        "next_actions": next_actions,
        "primary_route": primary_route,
        "preferred_routes": preferred_routes,
        "plans": plans,
        "findings": sorted(set(findings)),
        "proof_ceiling": cfg["proof_ceiling"],
        "action": "QUEUE_PANEL_ALIGNED_NEED_REMEDY" if ordered else "NO_NAVIGATING_NEEDS_GOALS",
    }


def _uncovered_urgent_outranks_panel(snap: Mapping[str, float], goal_plan: dict) -> bool:
    """True when an uncovered urgent motive is worse than any panel-covered urgent.

    If the panel already covers the worst urgent motive (e.g. hunger via cook while
    social is also urgent but not shown), keep tandem. If the worst urgent is not
    on the panel (e.g. bladder critical while only Fun goals show), fall through.
    """
    uncovered = list(goal_plan.get("uncovered_urgent_motives") or [])
    if not uncovered:
        return False
    panel_motives = set(goal_plan.get("panel_linked_motives") or [])
    urgent = list(goal_plan.get("urgent_motives") or [])
    panel_urgent = [n for n in urgent if n in panel_motives]
    if not panel_urgent:
        return True
    worst_uncovered = min(uncovered, key=lambda n: snap[n])
    worst_panel = min(panel_urgent, key=lambda n: snap[n])
    return snap[worst_uncovered] < snap[worst_panel]


def evaluate_navigating_needs_turn(
    needs: Mapping[str, float],
    *,
    navigating_needs_active: bool = False,
    navigating_needs_incomplete: Sequence[str] = (),
    quest_profile: str = "navigating_needs",
    school_day_active: bool = False,
    build_or_buy_mode: bool = False,
    player_directed: bool = False,
    already_busy: bool = False,
    queue: Sequence[str] = (),
    capture_ref: str = "capture:navigating-needs-turn",
) -> dict:
    """Return the highest-priority Navigating Needs call-stack gate for one turn."""
    cfg = load_contract()
    snap = _needs(needs)
    goals = [str(g) for g in navigating_needs_incomplete if isinstance(g, str) and g]
    goal_plan = None
    if navigating_needs_active and goals:
        goal_plan = plan_navigating_needs(
            goals,
            snap,
            quest_profile=quest_profile,
            queue=queue,
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
    elif build_or_buy_mode:
        gate = "BUILD_OR_BUY_YIELD"
        action = "ABSTAIN_NAVIGATING_NEEDS_WHILE_BUILDING"
        disposition = "EMULATE"
        findings.append("BUILD_OR_BUY_ABSTAINS_NAVIGATING_NEEDS")
    elif school_day_active:
        gate = "SCHOOL_DAY_OUTRANKS_NAVIGATING_NEEDS"
        action = "DEFER_NAVIGATING_NEEDS_TO_SCHOOL_DAY"
        disposition = "EMULATE"
        findings.append("SCHOOL_DAY_OUTRANKS_NAVIGATING_NEEDS")
    elif (
        navigating_needs_active
        and goals
        and goal_plan
        and _uncovered_urgent_outranks_panel(snap, goal_plan)
    ):
        gate = "URGENT_NEED_WITHOUT_PANEL_GOAL"
        action = "FALL_THROUGH_TO_INSTINCTS_FOR_UNCOVERED_URGENT"
        disposition = "OPTIMIZE"
        findings.append("URGENT_NEED_NOT_ON_VISIBLE_PANEL")
    elif (
        navigating_needs_active
        and goals
        and goal_plan
        and goal_plan.get("next_goal")
    ):
        gate = "NAVIGATING_NEEDS_TANDEM"
        action = "QUEUE_PANEL_ALIGNED_NEED_REMEDY"
        disposition = "EMULATE_THEN_OPTIMIZE"
        preferred_routes = list(
            goal_plan.get("preferred_routes") or ["PANEL_ALIGNED_NEED_ACTION"]
        )
        findings.append("TANDEM_WITH_NAVIGATING_NEEDS_PANEL")
    elif not navigating_needs_active:
        gate = "NAVIGATING_NEEDS_INACTIVE"
        action = "NO_NAVIGATING_NEEDS_ROUTING"
        disposition = "EMULATE"

    return {
        "schema": "betterinstincts.navigating-needs-result/v1",
        "state": "NAVIGATING_NEEDS_TURN_EVALUATED",
        "capture_ref": capture_ref,
        "gate": gate,
        "action": action,
        "disposition": disposition,
        "preferred_routes": preferred_routes,
        "primary_route": preferred_routes[0] if preferred_routes else None,
        "findings": sorted(set(findings)),
        "navigating_needs_active": navigating_needs_active,
        "goals_incomplete": goals,
        "school_day_active": school_day_active,
        "build_or_buy_mode": build_or_buy_mode,
        "goal_plan": goal_plan,
        "call_stack_order": stack,
        "proof_ceiling": cfg["proof_ceiling"],
    }
