"""Bounded, portable agent context for BetterInstincts (offline policy only).

Callers supply explicit, opaque, provenance-bearing state and records. This
module never searches a profile, loads a save, invokes tools, or grants effects.
"""
from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence

SCHEMA = "betterinstincts.agent-context/v1"
PACKET_SCHEMA = "betterinstincts.agent-context-packet/v1"
MAX_RECORDS = 64
MAX_HANDOFF_ITEMS = 16
MAX_AGE_SECONDS = 180
MIN_BUDGET = 512
MAX_BUDGET = 16384

# Descriptions are an allowlisted retrieval interface, not callable tools.
ROUTES = {
    "GOAL": ("lookup_goal", "betterinstincts/task_continuity.py",
             "Read the current actor's goal, interruption and queue evidence."),
    "MECHANIC": ("lookup_mechanic", "betterinstincts/mechanics_registry.py",
                 "Read registered Sims mechanics, gaps and source maturity."),
    "RELATION": ("query_relationships", "contracts/ontology.v1.json",
                 "Read evidenced links between household, goal, object and mechanic."),
    "OBSERVATION": ("inspect_observation", "betterinstincts/need_signal_fusion.py",
                    "Read capture-bound need and mood observation evidence."),
    "AUTHORITY": ("check_authority", "contracts/effect-authority.v1.json",
                  "Inspect player-first authority rules; never grant a control permit."),
}
KINDS = frozenset(ROUTES)
STATES = frozenset({"LOCAL_OBSERVED", "REVIEWED_SOURCE", "CANDIDATE"})


class AgentContextError(ValueError):
    pass


def _id(value: object) -> bool:
    return (isinstance(value, str) and 1 <= len(value) <= 120
            and all(char.isalnum() or char in "_.:-/" for char in value))


def _text(value: object, limit: int = 400) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= limit


def _items(value: object) -> list[str]:
    if not isinstance(value, list) or len(value) > MAX_HANDOFF_ITEMS:
        raise AgentContextError("HANDOFF_ITEMS_INVALID")
    if any(not _text(item, 240) for item in value):
        raise AgentContextError("HANDOFF_ITEM_INVALID")
    return list(dict.fromkeys(value))


def _instant(value: object) -> bool:
    return type(value) in (float, int) and math.isfinite(value)


def _compact(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def route_context(intent: str) -> dict:
    """Advertise the exact existing data owner for one retrieval intent.

    No adapter is invoked. An agent must independently request and verify the
    corresponding read, and independently admit any eventual game effect.
    """
    if intent not in ROUTES:
        raise AgentContextError("UNREGISTERED_RETRIEVAL_INTENT")
    name, owner, description = ROUTES[intent]
    return {
        "tool": name,
        "owner": owner,
        "description": description,
        "scope": intent,
        "read_only": True,
        "invoked": False,
        "execute_allowed": False,
        "proof_ceiling": "ROUTING_ONLY_NO_TOOL_EXECUTION",
    }


def _validate_handoff(handoff: Mapping) -> dict:
    if not isinstance(handoff, Mapping) or handoff.get("schema") != SCHEMA:
        raise AgentContextError("HANDOFF_SCHEMA_INVALID")
    required_ids = ("household_ref", "active_goal_id", "next_gate", "source_revision")
    if any(not _id(handoff.get(key)) for key in required_ids):
        raise AgentContextError("HANDOFF_IDENTITY_INVALID")
    if not _text(handoff.get("parent_objective"), 500):
        raise AgentContextError("PARENT_OBJECTIVE_REQUIRED")
    game_build = handoff.get("game_build")
    if game_build is not None and not _id(game_build):
        raise AgentContextError("GAME_BUILD_INVALID")
    return {
        "schema": SCHEMA,
        "household_ref": handoff["household_ref"],
        "game_build": game_build,
        "parent_objective": handoff["parent_objective"],
        "active_goal_id": handoff["active_goal_id"],
        "next_gate": handoff["next_gate"],
        "source_revision": handoff["source_revision"],
        "corrections": _items(handoff.get("corrections", [])),
        "rejected_paths": _items(handoff.get("rejected_paths", [])),
        "blockers": _items(handoff.get("blockers", [])),
    }


def continue_handoff(previous: Mapping, update: Mapping) -> dict:
    """Advance only a proven gate; never silently rewrite operator intent."""
    base = _validate_handoff(previous)
    if not isinstance(update, Mapping):
        raise AgentContextError("HANDOFF_UPDATE_INVALID")
    protected = ("parent_objective", "household_ref", "game_build")
    if any(key in update and update[key] != base[key] for key in protected):
        raise AgentContextError("PARENT_OR_SCOPE_MUTATION_DENIED")
    if "next_gate" in update or "active_goal_id" in update:
        if not _id(update.get("evidence_ref")):
            raise AgentContextError("TRANSITION_EVIDENCE_REQUIRED")
    for key in ("corrections", "rejected_paths", "blockers"):
        if key in update:
            base[key] = _items(base[key] + _items(update[key]))
    if "source_revision" in update and not _id(update.get("evidence_ref")):
        raise AgentContextError("TRANSITION_EVIDENCE_REQUIRED")
    for key in ("next_gate", "active_goal_id", "source_revision"):
        if key in update:
            if not _id(update[key]):
                raise AgentContextError("HANDOFF_IDENTITY_INVALID")
            base[key] = update[key]
    return base


def _record(record: Mapping, handoff: dict, capture_ref: str, now: float) -> dict:
    if not isinstance(record, Mapping):
        raise AgentContextError("CONTEXT_RECORD_INVALID")
    ids = ("fact_id", "source_owner", "evidence_ref", "source_revision")
    if any(not _id(record.get(key)) for key in ids):
        raise AgentContextError("RECORD_PROVENANCE_REQUIRED")
    if record.get("kind") not in KINDS or record.get("evidence_state") not in STATES:
        raise AgentContextError("RECORD_TYPE_INVALID")
    if not _text(record.get("claim"), 320):
        raise AgentContextError("RECORD_CLAIM_INVALID")
    if record.get("household_ref") != handoff["household_ref"]:
        raise AgentContextError("CROSS_HOUSEHOLD_RECORD_DENIED")
    if handoff["game_build"] != record.get("game_build"):
        raise AgentContextError("CROSS_BUILD_RECORD_DENIED")
    stamp = record.get("observed_at_unix")
    if not _instant(stamp):
        raise AgentContextError("RECORD_TIMESTAMP_INVALID")
    if record["kind"] in {"OBSERVATION", "GOAL"} and record.get("capture_ref") != capture_ref:
        raise AgentContextError("CROSS_CAPTURE_RECORD_DENIED")
    if not _id(record.get("query_key")):
        raise AgentContextError("RECORD_QUERY_KEY_REQUIRED")
    return {
        "fact_id": record["fact_id"],
        "kind": record["kind"],
        "query_key": record["query_key"],
        "claim": record["claim"],
        "source_owner": record["source_owner"],
        "source_revision": record["source_revision"],
        "evidence_ref": record["evidence_ref"],
        "evidence_state": record["evidence_state"],
        "observed_at_unix": stamp,
        "fresh": (0 <= now - stamp <= MAX_AGE_SECONDS
                  if record["evidence_state"] == "LOCAL_OBSERVED"
                  or record["kind"] in {"GOAL", "OBSERVATION"}
                  else stamp <= now and record["source_revision"] == handoff["source_revision"]),
    }


def compile_agent_context(
    handoff: Mapping,
    records: Sequence[Mapping],
    *,
    intent: str,
    query_key: str,
    capture_ref: str,
    now: float,
    budget_chars: int = 4096,
) -> dict:
    """Return a deterministic bounded context projection and read-only route.

    Operator intent, rejected paths and blockers are mandatory and never cut
    for a token budget. Evidence is a separate field from claims. Invalid,
    stale, conflicting and speculative observations are not trusted evidence.
    """
    state = _validate_handoff(handoff)
    if not (_id(query_key) and _id(capture_ref) and _instant(now)):
        raise AgentContextError("CONTEXT_QUERY_INVALID")
    if (type(budget_chars) is not int
            or not MIN_BUDGET <= budget_chars <= MAX_BUDGET):
        raise AgentContextError("CONTEXT_BUDGET_INVALID")
    if not isinstance(records, (list, tuple)) or len(records) > MAX_RECORDS:
        raise AgentContextError("CONTEXT_RECORD_COUNT_INVALID")
    route = route_context(intent)
    core = {
        "schema": PACKET_SCHEMA,
        "handoff": state,
        "capture_ref": capture_ref,
        "retrieval": route,
        "query_key": query_key,
        "records": [],
        "status": "RETRIEVAL_REQUIRED",
        "excluded": {"stale": 0, "candidate": 0, "irrelevant": 0, "conflict": 0, "budget": 0},
        "execute_allowed": False,
        "control_permit": None,
        "proof_ceiling": "OFFLINE_CONTEXT_NOT_GAME_EFFECT",
    }
    if len(_compact(core)) > budget_chars:
        raise AgentContextError("MANDATORY_CONTEXT_EXCEEDS_BUDGET")
    by_id: dict[str, list[dict]] = {}
    for raw in records:
        row = _record(raw, state, capture_ref, now)
        if row["kind"] not in {intent, "AUTHORITY", "GOAL"} or (
            row["kind"] == intent and row["query_key"] != query_key
        ):
            core["excluded"]["irrelevant"] += 1
            continue
        if not row["fresh"]:
            core["excluded"]["stale"] += 1
            continue
        if row["evidence_state"] == "CANDIDATE":
            core["excluded"]["candidate"] += 1
            continue
        by_id.setdefault(row["fact_id"], []).append(row)
    eligible: list[dict] = []
    for key in sorted(by_id):
        variants = by_id[key]
        # Never pick a convenient story from two incompatible verified claims.
        facts = {(r["claim"], r["source_owner"], r["source_revision"]) for r in variants}
        if len(facts) > 1:
            core["excluded"]["conflict"] += 1
            continue
        eligible.append(sorted(variants, key=lambda r: (-r["observed_at_unix"], r["evidence_ref"]))[0])
    eligible.sort(key=lambda r: (
        0 if r["kind"] == "AUTHORITY" else 1 if r["kind"] == "GOAL" else 2,
        0 if r["evidence_state"] == "LOCAL_OBSERVED" else 1,
        r["fact_id"],
    ))
    # Source-claimed context is never automatically a verified gameplay effect.
    for row in eligible:
        candidate = dict(core)
        candidate["records"] = core["records"] + [row]
        if len(_compact(candidate)) <= budget_chars:
            core["records"].append(row)
        else:
            core["excluded"]["budget"] += 1
    matched = any(r["kind"] == intent and r["query_key"] == query_key for r in core["records"])
    core["status"] = "EVIDENCE_SELECTED" if matched else "RETRIEVAL_REQUIRED"
    # Include the size metadata itself in the enforced serialized character
    # budget. This is a character ceiling, never a measured tokenizer count.
    core["char_budget"] = budget_chars
    core["chars_used"] = 0
    while True:
        if not any(r["kind"] == intent and r["query_key"] == query_key
                   for r in core["records"]):
            core["status"] = "RETRIEVAL_REQUIRED"
        for _ in range(5):
            measured = len(_compact(core))
            if measured == core["chars_used"]:
                break
            core["chars_used"] = measured
        if len(_compact(core)) <= budget_chars:
            break
        if not core["records"]:
            raise AgentContextError("MANDATORY_CONTEXT_EXCEEDS_BUDGET")
        core["records"].pop()
        core["excluded"]["budget"] += 1
    return core


def diagnose_context_failure(
    *,
    required_fact_id: str,
    available_fact_ids: Sequence[str],
    retrieved_fact_ids: Sequence[str],
    retrieval_called: bool,
    decision_used_retrieval: bool,
) -> dict:
    """Locate the lowest unproven layer before changing prompt/decision logic."""
    if not _id(required_fact_id) or type(retrieval_called) is not bool or type(decision_used_retrieval) is not bool:
        raise AgentContextError("DIAGNOSIS_INPUT_INVALID")
    if any(not _id(x) for x in [*available_fact_ids, *retrieved_fact_ids]):
        raise AgentContextError("DIAGNOSIS_FACT_ID_INVALID")
    if required_fact_id not in available_fact_ids:
        layer, gate = "DATA_LAYER", "REPAIR_MISSING_SOURCE_RELATION"
    elif not retrieval_called:
        layer, gate = "DECISION_LAYER", "QUERY_RELEVANT_SOURCE"
    elif required_fact_id not in retrieved_fact_ids:
        layer, gate = "RETRIEVAL_LAYER", "CHECK_EDGE_TYPE_AND_SEARCH_DEPTH"
    elif not decision_used_retrieval:
        layer, gate = "DECISION_LAYER", "USE_RETRIEVED_EVIDENCE"
    else:
        layer, gate = "SUPPORTED", "REVIEW_RESULT_WITH_SOURCE_OWNER"
    return {
        "layer": layer, "next_gate": gate, "execute_allowed": False,
        "proof_ceiling": "OFFLINE_DIAGNOSIS_NOT_GAME_ACTION",
    }

# A generic model summary, elapsed play time, and paused Sims screen never
# certify the operator's parent goal. Preserve the single agent-context owner.
TURN_BOUNDARY_SCHEMA = "betterinstincts.agent-turn-boundary/v1"
TURN_EFFECT_STATES = frozenset({
    "WAITING_FOR_USER", "WAITING_FOR_AGENT", "NEEDS_REVALIDATION",
    "NEEDS_RECONCILIATION", "COMPLETED", "BUSY", "WAIT_BUDGET_REACHED",
})


def assess_agent_turn_boundary(
    handoff: Mapping,
    *,
    listener_active: bool,
    effect_pending: bool,
    effect_state: str | None,
    player_presence: str,
    game_state: str,
    safe_offline_action: str | None = None,
    host_access: str = "UNKNOWN",
    host_unavailable_ref: str | None = None,
    claimed_acceptance_refs: Sequence[str] = (),
) -> dict:
    """Classify one read-only next gate; never certify a Codex stop or game effect.

    Source refs, even 'success' refs, are claims until independently reviewed.
    The current control runner remains ACTIVE on user interruption. Ordinary
    game PAUSED or passive listener COMPLETED cannot terminate the parent.
    """
    parent = _validate_handoff(handoff)
    if (type(listener_active) is not bool or type(effect_pending) is not bool
            or effect_state is not None and effect_state not in TURN_EFFECT_STATES):
        raise AgentContextError("TURN_EFFECT_STATE_INVALID")
    if player_presence not in {"ACTIVE", "INACTIVE", "UNKNOWN"}:
        raise AgentContextError("TURN_PLAYER_PRESENCE_INVALID")
    if game_state not in {"PAUSED", "RUNNING", "NOT_VISIBLE", "UNKNOWN"}:
        raise AgentContextError("TURN_GAME_STATE_INVALID")
    if host_access not in {"AVAILABLE", "UNAVAILABLE", "UNKNOWN"}:
        raise AgentContextError("TURN_HOST_ACCESS_INVALID")
    if (safe_offline_action is not None
            and (not isinstance(safe_offline_action, str)
                 or not safe_offline_action.strip() or len(safe_offline_action) > 240)):
        raise AgentContextError("TURN_OFFLINE_ACTION_INVALID")
    if host_unavailable_ref is not None and not _id(host_unavailable_ref):
        raise AgentContextError("TURN_HOST_EVIDENCE_INVALID")
    if (not isinstance(claimed_acceptance_refs, (list, tuple))
            or len(claimed_acceptance_refs) > 16
            or any(not _id(x) for x in claimed_acceptance_refs)
            or len(set(claimed_acceptance_refs)) != len(claimed_acceptance_refs)):
        raise AgentContextError("TURN_ACCEPTANCE_REFS_INVALID")

    def choose(gate: str, next_action: str, *, quiesce: bool = False) -> dict:
        return {
            "schema": TURN_BOUNDARY_SCHEMA,
            "household_ref": parent["household_ref"],
            "active_goal_id": parent["active_goal_id"],
            "parent_objective": parent["parent_objective"],
            "gate": gate,
            "next_action": next_action,
            "turn_quiescence_supported": quiesce,
            "parent_complete": False,
            "terminal_stop_proven": False,
            "listener_remains_active": listener_active,
            "effect_pending": effect_pending,
            "execute_allowed": False,
            "proof_ceiling": "READ_ONLY_BOUNDARY_NOT_INDEPENDENT_PARENT_ACCEPTANCE_OR_GAME_EFFECT",
        }

    # Player activity blocks screen effects, but not the listener or an
    # independently ready read-only source/test action.
    if player_presence != "INACTIVE":
        if safe_offline_action is not None:
            return choose("CONTINUE_OFFLINE_WHILE_PLAYER_ACTIVE",
                          safe_offline_action.strip())
        return choose("YIELD_EFFECTS_KEEP_LISTENER",
                      "REOBSERVE_TRUSTED_IDLE_WITH_EXISTING_LISTENER", quiesce=True)

    # Do not call a queue's COMPLETED / passive listener COMPLETED the game's
    # outcome, and never drop an unresolved prepared action on agent turn end.
    if effect_pending:
        if effect_state in {"COMPLETED", "NEEDS_RECONCILIATION"}:
            return choose("RECONCILE_PENDING_EFFECT_OUTCOME",
                          "OBSERVE_REAL_GAME_OUTCOME_AND_RETAIN_CODIFICATION")
        return choose("PENDING_EFFECT_KEEP_LISTENER",
                      "REVALIDATE_AND_ADVANCE_EXISTING_EFFECT_QUEUE")

    if safe_offline_action is not None:
        return choose("CONTINUE_OFFLINE", safe_offline_action.strip())

    # No operator-summary or caller-supplied acceptance references alone can
    # upgrade completion. They demand independent acceptance verification.
    if claimed_acceptance_refs:
        return choose("VERIFY_CLAIMED_PARENT_ACCEPTANCE",
                      "INDEPENDENTLY_MATCH_PROOFS_TO_EVERY_PARENT_ACCEPTANCE_GATE")
    if not listener_active:
        return choose("RECOVER_EXPLICIT_LISTENER",
                      "RECHECK_LOCAL_AUTHORITY_AND_START_APPROVED_LISTENER_IF_PERMITTED")
    if host_access == "UNAVAILABLE":
        if host_unavailable_ref is None:
            return choose("REOBSERVE_HOST_ACCESS",
                          "OBTAIN_ACTUAL_LOCAL_HOST_UNAVAILABILITY_EVIDENCE")
        return choose("BLOCKED_EXACT_LOCAL_GAME_ACCESS",
                      "RESUME_ON_HOST_RECOVERY_REVERIFY_SAVE_SCENE_AND_PLAYER",
                      quiesce=True)
    if game_state == "PAUSED":
        return choose("GAME_PAUSED_PARENT_OPEN",
                      "FRESH_PID_SCENE_SAVE_PLAYER_AND_ONE_EFFECT_ADMISSION")
    if game_state == "RUNNING":
        return choose("OBSERVE_ACTIVE_GAME_GOAL",
                      "REOBSERVE_SELECTED_SIM_QUEUE_NEEDS_AND_NEXT_TASK")
    return choose("INVESTIGATE_NEXT_GATE",
                  "RECOVER_CURRENT_HOST_SCENE_AND_INDEPENDENT_SOURCE_WORK")
