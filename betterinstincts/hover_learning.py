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
KINDS = {"hover", "tooltip_visible", "tooltip_hidden", "action", "hotkey_action", "cheat_action", "outcome"}
ACTION_KINDS = frozenset({"action", "hotkey_action", "cheat_action"})


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
               "operator_reviewed", "source", "mode", "hotkey_id", "cheat_id"}
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
        "hotkey_action": ("mode", "hotkey_id", "interaction_ref"),
        "cheat_action": ("cheat_id", "interaction_ref"),
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
        elif key in {"mode", "hotkey_id"}:
            if not isinstance(value[key], str) or not re.fullmatch(r"[A-Z0-9_]{2,64}", value[key]):
                raise HoverLearningError("INVALID_" + key.upper())
            result[key] = value[key]
        else:
            result[key] = _token(value[key], key)
    if "operator_reviewed" in required and result["operator_reviewed"] and result["outcome"] == "unknown":
        raise HoverLearningError("CANNOT_REVIEW_UNKNOWN_OUTCOME")
    if set(value) != {"schema", "id", "at_ms", "kind", "source", *required}:
        raise HoverLearningError("EVENT_FIELDS_NOT_KIND_SCOPED")
    if kind in {"hotkey_action", "cheat_action"}:
        from betterinstincts.behavior_input_catalog import (
            BehaviorInputCatalogError, resolve_hotkey, resolve_cheat,
        )
        try:
            result["action_ref"] = (
                resolve_hotkey(result["mode"], result["hotkey_id"])
                if kind == "hotkey_action" else resolve_cheat(result["cheat_id"])
            )
        except (BehaviorInputCatalogError, KeyError, ValueError) as exc:
            raise HoverLearningError("UNRECOGNIZED_INPUT_CHANNEL:" + str(exc)) from exc
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
        if item.get("kind") == "action":
            raw.pop("tooltip_ref", None)  # Derived only from matched visible tooltip.
            _token(item.get("tooltip_ref"), "tooltip_ref")
        elif item.get("kind") in {"hotkey_action", "cheat_action"}:
            raw.pop("action_ref", None)  # Derived solely from canonical catalog.
        item_valid = _event(raw)
        if item.get("kind") == "action":
            item_valid["tooltip_ref"] = item["tooltip_ref"]
        if item_valid != item or item["id"] in ids or item["at_ms"] < last:
            raise HoverLearningError("CORRUPT_HOVER_HISTORY")
        ids.add(item["id"])
        last = item["at_ms"]
    return state


def observe(state: Mapping, supplied_event: Mapping) -> tuple[dict, dict]:
    """Pure state transition; repeated visible polls are edge-deduplicated."""
    previous = _validated_state(state)
    event = _event(supplied_event)
    # Retain only the last hour of semantic events; do not grow with session age.
    cutoff = event["at_ms"] - WINDOWS[-1] * 1000
    events = [e for e in previous["events"] if e["at_ms"] >= cutoff]
    if any(e["id"] == event["id"] for e in previous["events"]):
        raise HoverLearningError("DUPLICATE_HOVER_EVENT_ID")
    if previous["events"] and event["at_ms"] < previous["events"][-1]["at_ms"]:
        raise HoverLearningError("HOVER_TIME_REGRESSION")
    active = previous["active_tooltip"] if events else None
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
    elif kind in ACTION_KINDS:
        if kind == "action":
            if active is None or active["target_ref"] != event["target_ref"]:
                raise HoverLearningError("ACTION_WITHOUT_MATCHED_TOOLTIP")
            event["tooltip_ref"] = active["tooltip_ref"]
        if any(e["kind"] in ACTION_KINDS and
               e["interaction_ref"] == event["interaction_ref"] for e in events):
            raise HoverLearningError("DUPLICATE_INTERACTION_REF")
    elif kind == "outcome":
        actions = [e for e in events if e["kind"] in ACTION_KINDS and
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
        actions = [e for e in within if e["kind"] in ACTION_KINDS]
        groups = {}
        for action in actions:
            channel = {"action": "tooltip", "hotkey_action": "hotkey",
                       "cheat_action": "cheat"}[action["kind"]]
            trigger_ref = (action.get("tooltip_ref") if channel == "tooltip"
                           else action["action_ref"])
            key = (channel, action.get("target_ref") or "", trigger_ref, action["action_ref"])
            g = groups.setdefault(key, {"channel": channel,
                                        "trigger_ref": trigger_ref,
                                        "target_ref": action.get("target_ref"),
                                        "tooltip_ref": action.get("tooltip_ref"),
                                        "action_ref": action["action_ref"], "attempts": 0,
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
            "hotkey_action_observations": sum(e["kind"] == "hotkey_action" for e in actions),
            "cheat_action_observations": sum(e["kind"] == "cheat_action" for e in actions),
            "patterns": rows,
        }
    return {"schema": "betterinstincts.hover-evaluation/v1",
            "windows": windows, "event_count": len(events),
            "revision": source["revision"], "control_permit": None,
            "execute_clicks": False, "automatically_trained": False,
            "proof_ceiling": "SUPPLIED_SEMANTIC_EVENTS_REVIEWED_ASSOCIATIONS_NOT_CAUSAL_GAME_CERT"}
