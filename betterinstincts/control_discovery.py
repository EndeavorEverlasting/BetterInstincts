"""Opt-in agent-control discovery ledger; compact evidence, not raw screen logging.

All adopted computer-use adapters must journal an intended atomic effect BEFORE
dispatch, and an eventual queue status/outcome. Never equate dispatch, click,
observation, codification proposal or merged native implementation.
"""
from __future__ import annotations

import copy
import re
from collections.abc import Mapping

SCHEMA = "betterinstincts.control-discovery/v1"
EVENT_SCHEMA = "betterinstincts.control-discovery-event/v1"
TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,95}$")
PATCH = re.compile(r"^\d+(?:\.\d+){3}$")
MAX_STEPS = 32
MAX_EVENTS = 128
MAX_SUMMARY_ITEMS = 8
QUEUE_STATES = frozenset({
    "WAITING_FOR_USER", "WAITING_FOR_AGENT", "NEEDS_RECONCILIATION",
    "NEEDS_REVALIDATION", "COMPLETED", "BUSY", "WAIT_BUDGET_REACHED",
})
OUTCOMES = frozenset({"HELPFUL", "HARMFUL", "NEUTRAL", "UNKNOWN"})
DISCOVERY_KINDS = frozenset({
    "ACTION_MENU", "OBJECT_AFFORDANCE", "QUEUED_ACTION",
    "SENSOR_RECOVERY", "INTERRUPTION", "NEGATIVE_RESULT",
})
MAX_DISCOVERIES_PER_STEP = 6
NATIVE_GAP_REASONS = frozenset({
    "NATIVE_ROUTE_MISSING", "NATIVE_ROUTE_UNPROVEN", "EXISTING_RULE_FAILED",
})
FALLBACK_REASONS = frozenset({
    "NATIVE_ROUTE_MISSING", "NATIVE_ROUTE_UNPROVEN",
    "EXISTING_RULE_FAILED", "DISPOSABLE_GAME_DIAGNOSTIC",
})


class ControlDiscoveryError(ValueError):
    pass


def _token(value: object) -> bool:
    return isinstance(value, str) and TOKEN.fullmatch(value) is not None


def _required(event: Mapping, names: tuple[str, ...]) -> None:
    if any(not _token(event.get(name)) for name in names):
        raise ControlDiscoveryError("EVENT_PROVENANCE_REQUIRED")


def new_session(
    *, session_id: str, household_ref: str, goal_id: str,
    game_patch: str, fallback_reason: str, listener_active: bool,
    explicit_opt_in: bool,
) -> dict:
    """Open an in-memory contract only for an explicitly active game listener."""
    if any(not _token(v) for v in (session_id, household_ref, goal_id)):
        raise ControlDiscoveryError("SESSION_IDENTITY_INVALID")
    if not isinstance(game_patch, str) or not PATCH.fullmatch(game_patch):
        raise ControlDiscoveryError("EXACT_GAME_PATCH_REQUIRED")
    if fallback_reason not in FALLBACK_REASONS:
        raise ControlDiscoveryError("LAST_RESORT_REASON_REQUIRED")
    if listener_active is not True or explicit_opt_in is not True:
        raise ControlDiscoveryError("ACTIVE_OPT_IN_LISTENER_REQUIRED")
    return {
        "schema": SCHEMA, "session_id": session_id,
        "household_ref": household_ref, "goal_id": goal_id,
        "game_patch": game_patch, "fallback_reason": fallback_reason,
        "events": [], "steps": {}, "next_seq": 1,
        "proof_ceiling": "OBSERVED_SEMANTIC_AGENT_TRACE_NOT_NATIVE_MOD_PROOF",
    }


def ingest(ledger: Mapping, raw: Mapping) -> dict:
    """One monotonic semantic event; caller persists each returned snapshot.

    PREPARE is required before queue admission. Every effect receives an
    independent QUEUE_STATUS and, when possible, OUTCOME. Human interruptions
    are preserved as pauses; resumption needs fresh queue admission, not replay.
    """
    if not isinstance(ledger, Mapping) or ledger.get("schema") != SCHEMA:
        raise ControlDiscoveryError("LEDGER_SCHEMA_INVALID")
    if not isinstance(raw, Mapping) or raw.get("schema") != EVENT_SCHEMA:
        raise ControlDiscoveryError("EVENT_SCHEMA_INVALID")
    if type(raw.get("seq")) is not int or raw["seq"] != ledger.get("next_seq"):
        raise ControlDiscoveryError("EVENT_SEQUENCE_INVALID")
    if not isinstance(ledger.get("events"), list) or len(ledger["events"]) >= MAX_EVENTS:
        raise ControlDiscoveryError("EVENT_BUDGET_EXHAUSTED")
    if not isinstance(ledger.get("steps"), dict):
        raise ControlDiscoveryError("STEP_STORE_INVALID")
    event = dict(raw)
    if not _token(event.get("work_id")):
        raise ControlDiscoveryError("WORK_ID_REQUIRED")
    if event.get("kind") == "PREPARE":
        if set(event) != {"schema", "seq", "kind", "work_id", "action_ref",
                          "object_class_ref", "before_capture_ref", "authority_ref"}:
            raise ControlDiscoveryError("PREPARE_FIELDS_INVALID")
        _required(event, ("action_ref", "object_class_ref", "before_capture_ref",
                          "authority_ref"))
        if event["work_id"] in ledger["steps"] or len(ledger["steps"]) >= MAX_STEPS:
            raise ControlDiscoveryError("STEP_ID_OR_BUDGET_INVALID")
    elif event.get("kind") == "DISPATCH_BOUNDARY":
        if set(event) != {"schema", "seq", "kind", "work_id"}:
            raise ControlDiscoveryError("DISPATCH_BOUNDARY_FIELDS_INVALID")
        step = ledger["steps"].get(event["work_id"])
        if step is None:
            raise ControlDiscoveryError("UNPREPARED_EFFECT_DENIED")
        if (step.get("dispatch_seq") is not None
                or step["queue_state"] in {"COMPLETED", "NEEDS_RECONCILIATION"}
                or step.get("outcome") is not None):
            raise ControlDiscoveryError("DISPATCH_ALREADY_BEGUN_OR_TERMINAL")
    elif event.get("kind") == "QUEUE_STATUS":
        if set(event) != {"schema", "seq", "kind", "work_id", "queue_state"}:
            raise ControlDiscoveryError("QUEUE_STATUS_FIELDS_INVALID")
        if event["queue_state"] not in QUEUE_STATES:
            raise ControlDiscoveryError("QUEUE_STATUS_INVALID")
        if event["work_id"] not in ledger["steps"]:
            raise ControlDiscoveryError("UNPREPARED_EFFECT_DENIED")
    elif event.get("kind") == "OUTCOME":
        if set(event) != {"schema", "seq", "kind", "work_id", "outcome",
                          "after_capture_ref", "outcome_ref", "player_interrupted"}:
            raise ControlDiscoveryError("OUTCOME_FIELDS_INVALID")
        _required(event, ("after_capture_ref", "outcome_ref"))
        if (event["outcome"] not in OUTCOMES
                or type(event["player_interrupted"]) is not bool):
            raise ControlDiscoveryError("OUTCOME_INVALID")
        if event["work_id"] not in ledger["steps"]:
            raise ControlDiscoveryError("UNPREPARED_EFFECT_DENIED")
        step = ledger["steps"][event["work_id"]]
        if (step.get("outcome") is not None
                and (step.get("outcome") != "UNKNOWN" or event["outcome"] == "UNKNOWN"
                     or step.get("player_interrupted") is True
                     or step.get("codification") is not None
                     or step.get("after_capture_ref") == event["after_capture_ref"])):
            raise ControlDiscoveryError("OUTCOME_ALREADY_RECORDED")
        if step["before_capture_ref"] == event["after_capture_ref"]:
            raise ControlDiscoveryError("POST_ACTION_CAPTURE_MUST_DIFFER")
        if step.get("queue_state") not in {"COMPLETED", "NEEDS_RECONCILIATION"}:
            raise ControlDiscoveryError("ACTION_NOT_OBSERVED_AS_ATTEMPTED")
    elif event.get("kind") == "DISCOVERY":
        # Reviewed semantic facts may arrive from the live listener while
        # gameplay effects are paused. Never admit text dumps or raw input.
        if set(event) != {"schema", "seq", "kind", "work_id",
                          "discovery_kind", "fact_ref", "source_ref",
                          "evidence_ref"}:
            raise ControlDiscoveryError("DISCOVERY_FIELDS_INVALID")
        _required(event, ("fact_ref", "source_ref", "evidence_ref"))
        if event["discovery_kind"] not in DISCOVERY_KINDS:
            raise ControlDiscoveryError("DISCOVERY_KIND_INVALID")
        if event["work_id"] not in ledger["steps"]:
            raise ControlDiscoveryError("UNPREPARED_DISCOVERY_DENIED")
        step = ledger["steps"][event["work_id"]]
        if step.get("codification") is not None:
            raise ControlDiscoveryError("DISCOVERY_AFTER_CODIFICATION_DENIED")
        discoveries = step.get("discoveries") or []
        if len(discoveries) >= MAX_DISCOVERIES_PER_STEP:
            raise ControlDiscoveryError("DISCOVERY_STEP_BUDGET_EXHAUSTED")
        if any(d["fact_ref"] == event["fact_ref"]
               and d["evidence_ref"] == event["evidence_ref"]
               for d in discoveries):
            raise ControlDiscoveryError("DUPLICATE_DISCOVERY_EVIDENCE")
    elif event.get("kind") == "CODIFICATION_RECEIPT":
        if set(event) != {"schema", "seq", "kind", "work_id",
                          "module_ref", "test_ref", "commit_ref", "review_ref"}:
            raise ControlDiscoveryError("CODIFICATION_FIELDS_INVALID")
        _required(event, ("module_ref", "test_ref", "commit_ref", "review_ref"))
        if event["work_id"] not in ledger["steps"]:
            raise ControlDiscoveryError("UNPREPARED_EFFECT_DENIED")
        step = ledger["steps"][event["work_id"]]
        if step.get("codification") is not None:
            raise ControlDiscoveryError("CODIFICATION_ALREADY_SUBMITTED")
        if step.get("outcome") in {None, "UNKNOWN"} or step.get("player_interrupted") is True:
            raise ControlDiscoveryError("REVIEW_OUTCOME_BEFORE_CODIFICATION")
    else:
        raise ControlDiscoveryError("EVENT_KIND_INVALID")

    state = copy.deepcopy(dict(ledger))
    state["events"].append(event)
    state["next_seq"] += 1
    work_id = event["work_id"]
    if event["kind"] == "PREPARE":
        state["steps"][work_id] = {
            "action_ref": event["action_ref"],
            "object_class_ref": event["object_class_ref"],
            "before_capture_ref": event["before_capture_ref"],
            "authority_ref": event["authority_ref"],
            "queue_state": "PREPARED",
            "outcome": None,
            "codification": None,
            "discoveries": [],
        }
    elif event["kind"] == "DISPATCH_BOUNDARY":
        state["steps"][work_id]["dispatch_seq"] = event["seq"]
    elif event["kind"] == "QUEUE_STATUS":
        state["steps"][work_id]["queue_state"] = event["queue_state"]
    elif event["kind"] == "OUTCOME":
        state["steps"][work_id].update(
            outcome=event["outcome"],
            after_capture_ref=event["after_capture_ref"],
            outcome_ref=event["outcome_ref"],
            player_interrupted=event["player_interrupted"],
        )
    elif event["kind"] == "DISCOVERY":
        state["steps"][work_id]["discoveries"].append({
            "discovery_kind": event["discovery_kind"],
            "fact_ref": event["fact_ref"],
            "source_ref": event["source_ref"],
            "evidence_ref": event["evidence_ref"],
        })
    elif event["kind"] == "CODIFICATION_RECEIPT":
        state["steps"][work_id]["codification"] = {
            "module_ref": event["module_ref"], "test_ref": event["test_ref"],
            "commit_ref": event["commit_ref"], "review_ref": event["review_ref"],
            "status": "RECEIPT_SUBMITTED_NOT_MERGE_VERIFIED",
        }
    return state


def coverage(ledger: Mapping) -> dict:
    """Every attempted action stays open until code and tests are reviewed."""
    if not isinstance(ledger, Mapping) or ledger.get("schema") != SCHEMA:
        raise ControlDiscoveryError("LEDGER_SCHEMA_INVALID")
    steps = ledger.get("steps")
    if not isinstance(steps, dict):
        raise ControlDiscoveryError("STEP_STORE_INVALID")
    outstanding: list[dict] = []
    summarized = {"prepared": 0, "awaiting_outcome": 0,
                  "review_ready": 0, "interrupted": 0, "receipt_submitted": 0}
    for work_id in sorted(steps):
        step = steps[work_id]
        if step.get("codification") is not None:
            status = "receipt_submitted"
        elif step.get("player_interrupted") is True:
            status = "interrupted"
        elif step.get("outcome") == "UNKNOWN":
            status = "awaiting_outcome"
        elif step.get("outcome") is not None:
            status = "review_ready"
        elif step.get("queue_state") == "PREPARED":
            status = "prepared"
        else:
            status = "awaiting_outcome"
        summarized[status] += 1
        if status != "receipt_submitted":
            outstanding.append({
                "work_id": work_id, "action_ref": step["action_ref"],
                "object_class_ref": step["object_class_ref"],
                "status": status,
                "next_gate": ("VERIFY_POST_ACTION_OUTCOME" if status in {
                    "prepared", "awaiting_outcome"} else
                    "RECONCILE_HUMAN_INTERRUPTION" if status == "interrupted"
                    else "REVIEW_AND_IMPLEMENT_REUSABLE_RULE"),
            })
    return {
        "schema": "betterinstincts.control-discovery-coverage/v1",
        "total_attempts": len(steps),
        "counts": summarized,
        "unresolved_total": len(outstanding),
        "unresolved": outstanding[:MAX_SUMMARY_ITEMS],
        "unresolved_truncated": max(0, len(outstanding) - MAX_SUMMARY_ITEMS),
        # A source/test/commit receipt is an assertion awaiting independent
        # provider/mainline verification, not proof that game logic was shipped.
        "source_verification_pending_total": summarized["receipt_submitted"],
        "source_verified_total": 0,
        "all_attempts_source_verified": len(steps) == 0,
        "control_permit": None, "execute_allowed": False,
        "proof_ceiling": "CODIFICATION_CANDIDATES_NOT_MERGED_GAMEPLAY",
    }



def codification_work_items(ledger: Mapping, *, offset: int = 0,
                            limit: int = 4) -> dict:
    """Expose every attempted action as a small, cursor-paged source task.

    This is a deterministic semantic projection of the existing journal;
    no extra screenshots, raw input logs, token history or profile reads.
    A receipt cannot close source verification without provider readback.
    """
    if not isinstance(ledger, Mapping) or ledger.get("schema") != SCHEMA:
        raise ControlDiscoveryError("LEDGER_SCHEMA_INVALID")
    if not isinstance(ledger.get("steps"), dict):
        raise ControlDiscoveryError("STEP_STORE_INVALID")
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 8:
        raise ControlDiscoveryError("CODIFICATION_PAGE_INVALID")
    keys = sorted(ledger["steps"])
    items = []
    for work_id in keys[offset:offset + limit]:
        step = ledger["steps"][work_id]
        if step.get("codification") is not None:
            gate = "VERIFY_COMMIT_TEST_AND_MAIN_READBACK"
        elif step.get("player_interrupted") is True:
            gate = "RECONCILE_INTERRUPTED_OUTCOME"
        elif step.get("outcome") == "UNKNOWN":
            gate = "RECONCILE_UNKNOWN_OUTCOME"
        elif step.get("outcome") is not None:
            gate = "IMPLEMENT_SOURCE_RULE_AND_REGRESSION_TEST"
        else:
            gate = "CAPTURE_AND_REVIEW_ACTUAL_OUTCOME"
        items.append({
            "work_id": work_id,
            "goal_id": ledger["goal_id"],
            "fallback_reason": ledger["fallback_reason"],
            "game_patch": ledger["game_patch"],
            "action_ref": step["action_ref"],
            "object_class_ref": step["object_class_ref"],
            "before_capture_ref": step["before_capture_ref"],
            "queue_state": step["queue_state"],
            "native_responder_gap": ledger["fallback_reason"] in NATIVE_GAP_REASONS,
            "effect_trace": {
                "before": {"capture_ref": step["before_capture_ref"],
                           "authority_ref": step["authority_ref"]},
                "during": {"dispatch_boundary_seq": step.get("dispatch_seq"),
                           "queue_state": step["queue_state"]},
                "after": {"capture_ref": step.get("after_capture_ref"),
                          "outcome_ref": step.get("outcome_ref"),
                          "classification": step.get("outcome"),
                          "player_interrupted": step.get("player_interrupted")},
                "origin": "AGENT_FALLBACK",
                "native_resolution_proved": False,
            },
            "observed_outcome": step.get("outcome"),
            "after_capture_ref": step.get("after_capture_ref"),
            "outcome_ref": step.get("outcome_ref"),
            "player_interrupted": step.get("player_interrupted"),
            "submitted_codification": step.get("codification"),
            "discoveries": list(step.get("discoveries") or []),
            "next_gate": gate,
            "required_regression": [
                "REPLAY_OBSERVED_BEHAVIOR_OR_FAILURE",
                "DENY_PLAYER_QUEUE_OVERRIDE",
                "RECHECK_STALE_SCENE_AND_TARGET",
                "VERIFY_IDEMPOTENCE_AND_NO_BLIND_REPLAY",
                "KEEP_ASSISTED_EFFECT_DISTINCT_FROM_NATIVE_RESOLUTION",
            ],
            "source_verified": False,
        })
    next_offset = offset + len(items)
    return {
        "schema": "betterinstincts.codification-work-items/v1",
        "total_attempted": len(keys),
        "offset": offset,
        "next_offset": next_offset if next_offset < len(keys) else None,
        "items": items,
        "execute_allowed": False,
        "proof_ceiling": "SOURCE_TASKS_NOT_REPOSITORY_MERGE_PROOF",
    }


def compact_handoff(ledger: Mapping, *, offset: int = 0, limit: int = 4) -> dict:
    """Low-context portable digest; raw interactions remain local/offline."""
    result = coverage(ledger)
    return {
        "schema": "betterinstincts.control-discovery-handoff/v1",
        "session_id": ledger["session_id"], "household_ref": ledger["household_ref"],
        "goal_id": ledger["goal_id"], "game_patch": ledger["game_patch"],
        "fallback_reason": ledger["fallback_reason"],
        "events_count": len(ledger["events"]),
        "codification_coverage": result,
        "codification_work": codification_work_items(ledger, offset=offset, limit=limit),
        "requires_fresh_control_admission": True,
        "proof_ceiling": "COMPACT_SEMANTIC_MEMORY_NOT_GAME_EFFECT",
    }
