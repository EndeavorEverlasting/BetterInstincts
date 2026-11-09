"""Opt-in, event-driven tooltip and action/outcome temporal evaluator.

The host supplies *semantic* observations. No mouse hooks, screenshots, raw
tooltip text, background polling, game actions, or model training live here.
"""
from __future__ import annotations

import json
import re
from typing import Mapping

SCHEMA = "betterinstincts.hover-session/v1"
EVENT_SCHEMA = "betterinstincts.hover-event/v1"
WINDOWS = (180, 300, 600, 1800, 3600)
MAX_EVENTS = 256
MAX_BYTES = 64000
TOKEN = re.compile(r"^[a-z][a-z0-9_:-]{1,63}$")
EVENT_ID = re.compile(r"^[A-Za-z0-9_-]{3,48}$")
KINDS = {"hover", "tooltip_visible", "tooltip_hidden", "action", "outcome"}


class HoverLearningError(ValueError):
    pass


def _token(value: object, name: str) -> str:
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise HoverLearningError("INVALID_" + name.upper())
    return value


def _event(value: Mapping) -> dict:
    if not isinstance(value, Mapping) or value.get("schema") != EVENT_SCHEMA:
        raise HoverLearningError("BAD_HOVER_EVENT_SCHEMA")
    allowed = {"schema", "id", "at_ms", "kind", "target_ref", "tooltip_ref",
               "interaction_ref", "action_ref", "outcome", "evidence_ref",
               "operator_reviewed", "source"}
    if set(value) - allowed:
        raise HoverLearningError("UNEXPECTED_HOVER_EVENT_FIELDS")
    if not isinstance(value.get("id"), str) or not EVENT_ID.fullmatch(value["id"]):
        raise HoverLearningError("INVALID_EVENT_ID")
    ms = value.get("at_ms")
    if isinstance(ms, bool) or not isinstance(ms, int) or ms < 0:
        raise HoverLearningError("INVALID_EVENT_TIME")
    kind = value.get("kind")
    if kind not in KINDS:
        raise HoverLearningError("INVALID_EVENT_KIND")
    if value.get("source") not in {"sensor_supplied", "operator_supplied"}:
        raise HoverLearningError("SOURCE_PROVENANCE_REQUIRED")
    result = {"id": value["id"], "at_ms": ms, "kind": kind,
              "source": value["source"]}
    required = {
        "hover": ("target_ref",),
        "tooltip_visible": ("target_ref", "tooltip_ref"),
        "tooltip_hidden": ("target_ref",),
        "action": ("target_ref", "interaction_ref", "action_ref"),
        "outcome": ("interaction_ref", "outcome", "evidence_ref",
                    "operator_reviewed"),
    }[kind]
    for key in required:
        if key not in value:
            raise HoverLearningError("MISSING_" + key.upper())
        if key == "operator_reviewed":
            if not isinstance(value[key], bool):
                raise HoverLearningError("REVIEW_FLAG_NOT_BOOLEAN")
            result[key] = value[key]
        elif key == "outcome":
            if value[key] not in {"helpful", "harmful", "unknown"}:
                raise HoverLearningError("INVALID_OUTCOME")
            result[key] = value[key]
        else:
            result[key] = _token(value[key], key)
    if "operator_reviewed" in required and result["operator_reviewed"] and result["outcome"] == "unknown":
        raise HoverLearningError("CANNOT_REVIEW_UNKNOWN_OUTCOME")
    if set(value) != {"schema", "id", "at_ms", "kind", "source", *required}:
        raise HoverLearningError("EVENT_FIELDS_NOT_KIND_SCOPED")
    return result


def empty_state() -> dict:
    return {"schema": SCHEMA, "events": [], "active_tooltip": None,
            "revision": 0}


def _validated_state(state: Mapping) -> dict:
    if not isinstance(state, dict) or set(state) != {"schema", "events", "active_tooltip", "revision"}:
        raise HoverLearningError("BAD_HOVER_STATE")
    if state["schema"] != SCHEMA or not isinstance(state["events"], list):
        raise HoverLearningError("BAD_HOVER_STATE")
    if len(state["events"]) > MAX_EVENTS or len(json.dumps(state).encode("utf-8")) > MAX_BYTES:
        raise HoverLearningError("HOVER_STATE_BUDGET_EXCEEDED")
    if isinstance(state["revision"], bool) or not isinstance(state["revision"], int) or state["revision"] < 0:
        raise HoverLearningError("INVALID_HOVER_REVISION")
    if state["active_tooltip"] is not None:
        active = state["active_tooltip"]
        if not isinstance(active, dict) or set(active) != {"target_ref", "tooltip_ref"}:
            raise HoverLearningError("BAD_ACTIVE_TOOLTIP")
        for k, v in active.items():
            _token(v, k)
    ids = set()
    last = -1
    for item in state["events"]:
        if not isinstance(item, dict):
            raise HoverLearningError("BAD_STORED_HOVER_EVENT")
        # Stored events use the normalized schema, no additional state.
        raw = {**item, "schema": EVENT_SCHEMA}
        item_valid = _event(raw)
        if item_valid != item or item["id"] in ids or item["at_ms"] < last:
            raise HoverLearningError("CORRUPT_HOVER_HISTORY")
        ids.add(item["id"])
        last = item["at_ms"]
    return state


def observe(state: Mapping, supplied_event: Mapping) -> tuple[dict, dict]:
    """Pure state transition; repeated visible polls are edge-deduplicated."""
    previous = _validated_state(state)
    event = _event(supplied_event)
    events = previous["events"]
    if any(e["id"] == event["id"] for e in events):
        raise HoverLearningError("DUPLICATE_HOVER_EVENT_ID")
    if events and event["at_ms"] < events[-1]["at_ms"]:
        raise HoverLearningError("HOVER_TIME_REGRESSION")
    active = previous["active_tooltip"]
    next_active = active
    kind = event["kind"]
    if kind == "tooltip_visible":
        incoming = {k: event[k] for k in ("target_ref", "tooltip_ref")}
        if active == incoming:
            return previous, {"state": "UNCHANGED_TOOLTIP", "recorded": False}
        next_active = incoming
    elif kind == "hover":
        if active is not None and active["target_ref"] != event["target_ref"]:
            next_active = None
    elif kind == "tooltip_hidden":
        if active is None:
            return previous, {"state": "UNCHANGED_TOOLTIP", "recorded": False}
        if active["target_ref"] != event["target_ref"]:
            raise HoverLearningError("HIDDEN_TARGET_MISMATCH")
        next_active = None
    elif kind == "action":
        if active is None or active["target_ref"] != event["target_ref"]:
            raise HoverLearningError("ACTION_WITHOUT_MATCHED_TOOLTIP")
        if any(e["kind"] == "action" and
               e["interaction_ref"] == event["interaction_ref"] for e in events):
            raise HoverLearningError("DUPLICATE_INTERACTION_REF")
        event["tooltip_ref"] = active["tooltip_ref"]
    elif kind == "outcome":
        actions = [e for e in events if e["kind"] == "action" and
                   e["interaction_ref"] == event["interaction_ref"]]
        if len(actions) != 1:
            raise HoverLearningError("OUTCOME_WITHOUT_MATCHED_ACTION")
        if any(e["kind"] == "outcome" and
               e["interaction_ref"] == event["interaction_ref"] for e in events):
            raise HoverLearningError("DUPLICATE_INTERACTION_OUTCOME")
    if len(events) >= MAX_EVENTS:
        raise HoverLearningError("HOVER_EVENT_BUDGET_EXCEEDED")
    next_state = {"schema": SCHEMA, "events": [*events, event],
                  "active_tooltip": next_active,
                  "revision": previous["revision"] + 1}
    if len(json.dumps(next_state).encode("utf-8")) > MAX_BYTES:
        raise HoverLearningError("HOVER_STATE_BUDGET_EXCEEDED")
    return next_state, {"state": "RECORDED_OBSERVATION", "recorded": True,
                        "revision": next_state["revision"], "event_kind": kind,
                        "control_permit": None, "execute_clicks": False}


def evaluate(state: Mapping, *, now_ms: int) -> dict:
    """Count observed associations by window, not causal benefits or clicks."""
    source = _validated_state(state)
    if isinstance(now_ms, bool) or not isinstance(now_ms, int) or now_ms < 0:
        raise HoverLearningError("INVALID_EVALUATION_TIME")
    if source["events"] and now_ms < source["events"][-1]["at_ms"]:
        raise HoverLearningError("EVALUATION_BEFORE_LAST_EVENT")
    events = source["events"]
    by_ref = {e["interaction_ref"]: e for e in events if e["kind"] == "outcome"}
    windows = {}
    for seconds in WINDOWS:
        cutoff = now_ms - seconds * 1000
        within = [e for e in events if cutoff <= e["at_ms"] <= now_ms]
        actions = [e for e in within if e["kind"] == "action"]
        groups = {}
        for action in actions:
            key = (action["target_ref"], action["tooltip_ref"], action["action_ref"])
            g = groups.setdefault(key, {"target_ref": key[0], "tooltip_ref": key[1],
                                        "action_ref": key[2], "attempts": 0,
                                        "reviewed_helpful": 0, "reviewed_harmful": 0,
                                        "pending_review_or_outcome": 0})
            g["attempts"] += 1
            outcome = by_ref.get(action["interaction_ref"])
            if outcome is None or outcome["at_ms"] > now_ms or outcome["at_ms"] < cutoff or not outcome["operator_reviewed"]:
                g["pending_review_or_outcome"] += 1
            elif outcome["outcome"] == "helpful":
                g["reviewed_helpful"] += 1
            elif outcome["outcome"] == "harmful":
                g["reviewed_harmful"] += 1
            else:
                g["pending_review_or_outcome"] += 1
        rows = []
        for key in sorted(groups):
            g = groups[key]
            reviewed = g["reviewed_helpful"] + g["reviewed_harmful"]
            g["reviewed_success_rate"] = round(g["reviewed_helpful"] / reviewed, 4) if reviewed else None
            g["learning_eligible"] = reviewed >= 3 and g["reviewed_helpful"] >= 3 and g["reviewed_success_rate"] >= 0.75
            rows.append(g)
        windows[str(seconds)] = {
            "minutes": seconds // 60,
            "tooltip_appearances": sum(e["kind"] == "tooltip_visible" for e in within),
            "hover_observations": sum(e["kind"] == "hover" for e in within),
            "action_observations": len(actions),
            "patterns": rows,
        }
    return {"schema": "betterinstincts.hover-evaluation/v1",
            "windows": windows, "event_count": len(events),
            "revision": source["revision"], "control_permit": None,
            "execute_clicks": False, "automatically_trained": False,
            "proof_ceiling": "SUPPLIED_SEMANTIC_EVENTS_REVIEWED_ASSOCIATIONS_NOT_CAUSAL_GAME_CERT"}
