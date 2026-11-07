"""Pure, read-only semantic coordinator over existing domain-cascade receipts.

This is an offline P95 call-stack prototype. It does not poll, click, grant
control permits, infer a game patch, or certify Sims 4 behavior.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isfinite


class SemanticAdvisoryError(ValueError):
    pass


def _goal(row: Mapping) -> dict:
    if not isinstance(row, Mapping):
        raise SemanticAdvisoryError("GOAL_NOT_A_MAPPING")
    identifier, domain = row.get("id"), row.get("domain")
    if not isinstance(identifier, str) or not identifier.strip():
        raise SemanticAdvisoryError("GOAL_ID_MISSING")
    if not isinstance(domain, str) or not domain.strip():
        raise SemanticAdvisoryError("GOAL_DOMAIN_MISSING")
    try:
        priority = float(row.get("priority", 0))
    except (TypeError, ValueError) as exc:
        raise SemanticAdvisoryError("GOAL_PRIORITY_INVALID") from exc
    if not isfinite(priority) or priority < 0:
        raise SemanticAdvisoryError("GOAL_PRIORITY_INVALID")
    resources = row.get("resource_claims", ())
    if not isinstance(resources, (list, tuple)) or any(
        not isinstance(v, str) or not v.strip() for v in resources
    ):
        raise SemanticAdvisoryError("GOAL_RESOURCES_INVALID")
    return {
        "id": identifier.strip(),
        "domain": domain.strip(),  # intentionally OPEN, not an enum
        "actor_scope": str(row.get("actor_scope") or "unspecified"),
        "priority": priority,
        "resource_claims": sorted(set(resources)),
        "mechanic_path": str(row.get("mechanic_path") or "unresolved"),
        "status": str(row.get("status") or "READY"),
    }


def _observed_event(row: Mapping, known: set[str], capture: str) -> dict | None:
    """Unverified, expired or unmapped contingencies never force preemption."""
    if not isinstance(row, Mapping):
        return None
    goal_id = row.get("goal_id")
    if goal_id not in known or row.get("evidence_state") not in {
        "LOCAL_OBSERVED", "GAME_CERTIFIED"
    }:
        return None
    if not isinstance(row.get("observation_ref"), str) or not row["observation_ref"].strip():
        return None
    # A time-sensitive signal belongs to the current bounded observation.
    # A prior tick's urgency cannot remain an evergreen emergency.
    if row.get("capture_ref") != capture:
        return None
    deadline = row.get("deadline_ticks")
    if deadline is not None and (
        not isinstance(deadline, int) or isinstance(deadline, bool) or deadline <= 0
    ):
        return None
    try:
        urgency = float(row.get("urgency", 0))
    except (TypeError, ValueError):
        return None
    if not isfinite(urgency) or urgency < 0:
        return None
    return {
        "goal_id": goal_id,
        "observation_ref": row["observation_ref"],
        "urgency": urgency,
        "deadline_ticks": deadline,
    }


def _retain_intent(suspended: list[dict], goal_id: str | None, reason: str, capture: str) -> None:
    if goal_id and all(item["goal_id"] != goal_id for item in suspended):
        suspended.append({
            "goal_id": goal_id, "reason": reason,
            "resume_condition": "FRESH_REVALIDATION_AFTER_INTERRUPTION",
            "observation_ref": capture, "revalidation_required": True,
        })


def compose_semantic_turn(
    cascade: Mapping,
    goals: Sequence[Mapping],
    *,
    contingencies: Sequence[Mapping] = (),
    previous: Mapping | None = None,
    player_directed: bool = False,
) -> dict:
    """Assess concurrent goals and return ONE advisory choice, never an action.

    Existing domain_cascade is the poll owner; semantic coordination only
    consumes its evidence and continuity records. No game state is mutated.
    """
    if cascade.get("schema") != "betterinstincts.domain-cascade-result/v1":
        raise SemanticAdvisoryError("CASCADE_RECEIPT_REQUIRED")
    capture = cascade.get("capture_ref")
    if not isinstance(capture, str) or not capture.strip():
        raise SemanticAdvisoryError("CAPTURE_REF_REQUIRED")
    normalized = [_goal(g) for g in goals]
    by_id = {g["id"]: g for g in normalized}
    if len(by_id) != len(normalized):
        raise SemanticAdvisoryError("DUPLICATE_GOAL_THREAD")
    previous = previous or {}
    prior_id = previous.get("selected_goal_id")
    suspended = [
        {
            "goal_id": entry["goal_id"],
            "reason": entry.get("reason", "RECHECK_STATE"),
            "resume_condition": entry.get(
                "resume_condition", "FRESH_REVALIDATION_AFTER_INTERRUPTION"
            ),
            "observation_ref": entry.get("observation_ref"),
            "revalidation_required": True,
        }
        for entry in (previous.get("suspended") or [])
        if isinstance(entry, Mapping)
        and isinstance(entry.get("goal_id"), str)
        and entry["goal_id"].strip()
    ]
    if player_directed or cascade.get("state") == "DOMAIN_CASCADE_YIELDED" or cascade.get("gate") == "PLAYER_FIRST_OR_BUSY":
        _retain_intent(suspended, prior_id, "PLAYER_ACTIVITY_YIELD", capture)
        return {
            "schema": "betterinstincts.semantic-advisory/v1",
            "capture_ref": capture, "state": "YIELD_TO_PLAYER",
            "selected_goal_id": None, "suspended": suspended,
            "evaluated_domains": sorted({g["domain"] for g in normalized}),
            "resource_conflicts": [], "resume_candidates": [],
            "revalidation_pending": sorted({item["goal_id"] for item in suspended}),
            "resumed_goals": [],
            "control_permit": None, "proof_ceiling": "OFFLINE_ADVISORY_ONLY",
        }
    # A suspended goal is NOT eligible merely because a new caller marks it
    # READY. Require a fresh, same-capture revalidation record. It remains a
    # goal thread while deferred, and this module never issues a game permit.
    suspended_ids = {item["goal_id"] for item in suspended}
    revalidated_ids = {
        normalized_goal["id"]
        for normalized_goal, raw in zip(normalized, goals)
        if normalized_goal["id"] in suspended_ids
        and raw.get("revalidated_capture_ref") == capture
        and raw.get("revalidation_outcome") == "SAFE_TO_RECONSIDER"
    }
    active = [
        g for g in normalized
        if g["status"] == "READY"
        and (g["id"] not in suspended_ids or g["id"] in revalidated_ids)
    ]
    events = [
        event for row in contingencies
        if (event := _observed_event(row, set(by_id), capture)) is not None
    ]
    event_by_goal = {}
    for event in events:
        old = event_by_goal.get(event["goal_id"])
        if old is None or event["urgency"] > old["urgency"]:
            event_by_goal[event["goal_id"]] = event
    # Compare *candidate advisories* only; no fixed domain priority or click.
    ranked = sorted(
        active,
        key=lambda g: (
            -max(g["priority"], event_by_goal[g["id"]]["urgency"] if g["id"] in event_by_goal else 0),
            0 if g["mechanic_path"] == "native" else 1,
            g["id"],
        ),
    )
    chosen = ranked[0] if ranked else None
    current_id = chosen["id"] if chosen else None
    preempted = bool(prior_id and current_id and prior_id != current_id and current_id in event_by_goal)
    if preempted:
        _retain_intent(suspended, prior_id, "OBSERVED_CONTINGENCY_PREEMPTION", capture)
    if current_id is None:
        _retain_intent(suspended, prior_id, "NO_READY_GOALS", capture)
    resumed_goals = [current_id] if current_id in revalidated_ids else []
    if resumed_goals:
        suspended = [item for item in suspended if item["goal_id"] != current_id]
    resume_candidates = [
        item["goal_id"] for item in suspended
        if item["goal_id"] in by_id and by_id[item["goal_id"]]["status"] == "READY"
        and item["goal_id"] != current_id
    ]
    revalidation_pending = sorted({
        goal_id for goal_id in resume_candidates if goal_id not in revalidated_ids
    })
    selected_resources = set(chosen["resource_claims"]) if chosen else set()
    resource_conflicts = [
        g["id"] for g in ranked[1:]
        if selected_resources.intersection(g["resource_claims"])
    ]
    return {
        "schema": "betterinstincts.semantic-advisory/v1",
        "capture_ref": capture,
        "state": "ADVISORY_ONLY" if chosen else "NO_READY_GOALS",
        "selected_goal_id": current_id,
        "selected_domain": chosen["domain"] if chosen else None,
        "selected_mechanic_path": chosen["mechanic_path"] if chosen else None,
        "contingency_preemption": preempted,
        "suspended": suspended,
        "resume_candidates": sorted(set(resume_candidates)),
        "revalidation_pending": revalidation_pending,
        "resumed_goals": resumed_goals,
        "resume_selected_requires_revalidation": False,
        "evaluated_domains": sorted({g["domain"] for g in normalized}),
        "resource_conflicts": resource_conflicts,
        "control_permit": None,
        "proof_ceiling": "OFFLINE_ADVISORY_ONLY",
    }
