"""Event goal → Sims interaction catalog for hosted social events.

Offline / host planning only. Never clicks the game or claims EA tuning truth.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "event-goals.v1.json"


class EventGoalsError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 256000:
        raise EventGoalsError("UNSAFE_EVENT_GOALS_CONTRACT")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.event-goals/v1":
        raise EventGoalsError("INVALID_EVENT_GOALS_SCHEMA")
    if not isinstance(data.get("goals"), dict) or not data["goals"]:
        raise EventGoalsError("EVENT_GOALS_EMPTY")
    if not isinstance(data.get("profiles"), dict) or not data["profiles"]:
        raise EventGoalsError("EVENT_PROFILES_EMPTY")
    return data


def _norm(text: str) -> str:
    s = str(text or "").strip().lower().replace("_", " ")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def resolve_goal_id(label: str, cfg: Optional[dict] = None) -> Optional[str]:
    """Map a HUD/operator label to a canonical goal id, or None if unknown."""
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


def _profile(cfg: dict, event_profile: str) -> tuple[dict, str]:
    profiles = cfg["profiles"]
    key = _norm(event_profile).replace(" ", "_") or str(cfg.get("default_profile") or "lounge_party")
    if key in profiles:
        return dict(profiles[key]), key
    for pid, row in profiles.items():
        aliases = {_norm(pid), *(_norm(a) for a in row.get("aliases", []))}
        if key in aliases or _norm(event_profile) in aliases:
            return dict(row), str(pid)
    raise EventGoalsError("UNKNOWN_EVENT_PROFILE:" + event_profile)


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


def match_queue_to_goals(
    queue: Sequence[str],
    *,
    incomplete_goals: Sequence[str] = (),
    cfg: Optional[dict] = None,
) -> dict[str, list[str]]:
    """Return goal_id → matching queue labels that may satisfy it."""
    cfg = cfg or load_contract()
    wanted = []
    for raw in incomplete_goals:
        gid = resolve_goal_id(raw, cfg)
        if gid and gid not in wanted:
            wanted.append(gid)
    if not wanted:
        wanted = list(cfg["goals"])
    hits: dict[str, list[str]] = {g: [] for g in wanted}
    for item in queue:
        label = str(item)
        for gid in wanted:
            for interaction in cfg["goals"][gid].get("satisfying_interactions", []):
                if _interaction_matches(label, interaction):
                    if label not in hits[gid]:
                        hits[gid].append(label)
                    break
    return hits


def plan_event_goals(
    incomplete_goals: Sequence[str],
    *,
    event_profile: str = "lounge_party",
    queue: Sequence[str] = (),
    outdoor_social_prefix: bool = False,
    capture_ref: str = "capture:event-goals",
) -> dict:
    """Plan concrete indoor actions for incomplete event HUD goals."""
    cfg = load_contract()
    profile, profile_id = _profile(cfg, event_profile)
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

    # Stable order: profile priority first, then any extras.
    ordered = [g for g in priority if g in normalized]
    ordered.extend(g for g in normalized if g not in ordered)

    queue_hits = match_queue_to_goals(queue, incomplete_goals=ordered, cfg=cfg)
    covered = sorted(g for g, labels in queue_hits.items() if labels)
    uncovered = [g for g in ordered if g not in covered]
    if ordered and queue and not covered:
        findings.append("QUEUE_DOES_NOT_SATISFY_EVENT_GOALS")
    if outdoor_social_prefix and ordered:
        findings.append("SPAM_OUTDOOR_GREET_HOPING_GOALS_TICK")

    plans = []
    for gid in ordered:
        row = cfg["goals"][gid]
        interactions = []
        for inter in row.get("satisfying_interactions", []):
            if outdoor_social_prefix and inter.get("indoor") is False:
                continue
            interactions.append(
                {
                    "id": inter["id"],
                    "labels": list(inter.get("labels", [])),
                    "steps": list(inter.get("steps", [])),
                    "indoor": bool(inter.get("indoor", True)),
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
        next_goal = plan["goal_id"]
        next_actions = list(plan["satisfying_interactions"])
        break
    if next_goal is None and plans:
        # All incomplete goals already have a matching queue item — reinforce first.
        next_goal = plans[0]["goal_id"]
        next_actions = list(plans[0]["satisfying_interactions"])
        findings.append("GOALS_ALREADY_QUEUED_REINFORCE")

    primary_route = None
    preferred_routes: list[str] = []
    if next_actions:
        primary_route = str(next_actions[0]["id"])
        preferred_routes = [str(a["id"]) for a in next_actions]
        if outdoor_social_prefix:
            preferred_routes = [
                "SIT_AND_CHAT_HERE_INDOOR",
                *[r for r in preferred_routes if r != "SIT_AND_CHAT_HERE_INDOOR"],
            ]
            if primary_route != "SIT_AND_CHAT_HERE_INDOOR":
                # Ground first, then the goal-specific interaction.
                preferred_routes = ["SIT_AND_CHAT_HERE_INDOOR", primary_route, *preferred_routes[1:]]
                primary_route = "SIT_AND_CHAT_HERE_INDOOR"

    return {
        "schema": "betterinstincts.event-goals-plan/v1",
        "state": "EVENT_GOALS_PLANNED",
        "capture_ref": capture_ref,
        "event_profile": profile_id,
        "goals_incomplete": ordered,
        "goals_unknown": unknown,
        "goals_covered_by_queue": covered,
        "goals_uncovered": uncovered,
        "next_goal": next_goal,
        "next_actions": next_actions,
        "primary_route": primary_route,
        "preferred_routes": preferred_routes,
        "plans": plans,
        "findings": sorted(set(findings)),
        "proof_ceiling": cfg["proof_ceiling"],
        "action": "QUEUE_INCOMPLETE_EVENT_GOALS_INDOOR" if ordered else "NO_EVENT_GOALS",
    }
