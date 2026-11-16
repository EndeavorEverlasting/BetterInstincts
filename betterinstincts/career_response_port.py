"""Coordinate one career response via a trusted, exact-build EA adapter.

Create one port per active game session. The adapter observes the live game
and atomically revalidates the request on the game thread before submitting.
There is no default adapter, game import or desktop fallback here.
"""
from __future__ import annotations

from collections.abc import Mapping
from threading import Lock
from uuid import uuid4

from betterinstincts.career_decisions import _int, _ref
from betterinstincts.career_service import evaluate_career_event_turn, reconcile_career_event_turn

SCOPE = ("game_build", "session_ref", "process_instance_ref", "save_ref", "household_id")
EVENT = ("dialog_tuning_id", "event_ref", "event_revision", "native_hook_ref", "capture_ref",
         "recipient_sim_id", "career_id", "shift_ref")
MAX_ATTEMPTS = 256
ADAPTER_ERRORS = (OSError, RuntimeError, ValueError)


class CareerResponsePort:
    def __init__(self, adapter=None):
        self._adapter = adapter
        self._attempts = {}
        self._runtime = None
        self._lock = Lock()

    def respond(self, *, now_epoch_ms: int, enabled: bool = False) -> dict:
        if enabled is not True:
            return {"state": "HOLD", "reason": "CAREER_AUTONOMY_NOT_ENABLED"}
        adapter = self._adapter
        if adapter is None:
            return {"state": "NATIVE_ADAPTER_REQUIRED", "reason": "NO_EXACT_BUILD_EA_ADAPTER"}
        try:
            frame = adapter.read_career_event()
        except ADAPTER_ERRORS:
            return {"state": "REOBSERVE", "reason": "NATIVE_CAREER_EVENT_READ_FAILED"}
        if not isinstance(frame, Mapping) or not isinstance(frame.get("event"), Mapping):
            return {"state": "REOBSERVE", "reason": "NATIVE_CAREER_EVENT_REQUIRED"}
        event = frame["event"]
        if (frame.get("build_verified") is not True or frame.get("scene_verified") is not True
                or frame.get("save_authorized") is not True or not _ref(frame.get("session_ref"))
                or not _ref(frame.get("process_instance_ref")) or not _ref(frame.get("save_ref"))
                or type(frame.get("paused")) is not bool):
            return {"state": "REOBSERVE", "reason": "NATIVE_CAREER_SCOPE_UNVERIFIED"}
        if "disclosed_card" not in event:
            return {"state": "HOLD", "reason": "REVIEWED_DISCLOSED_CARD_REQUIRED"}
        decision = evaluate_career_event_turn(
            event, now_epoch_ms=now_epoch_ms, autonomy_enabled=True,
            player_active=frame.get("player_active"),
        )
        if decision["state"] != "RECOMMENDED_NATIVE_CHOICE":
            return decision
        request = {
            **{field: event[field] for field in (*EVENT, "game_build", "household_id")},
            **{field: frame[field] for field in ("session_ref", "process_instance_ref", "save_ref")},
            "captured_at_epoch_ms": event["captured_at_epoch_ms"],
            "response_id": decision["recommended_response_id"],
            "card_id": decision["card_id"],
            "card_source_ref": decision["card_source_ref"],
            "effect_basis_ref": decision["selected_effect_basis_ref"],
            "expected_paused": frame["paused"],
            "require_fame_allowed": True,
            "attempt_ref": "career-attempt:" + uuid4().hex,
        }
        key = (request["session_ref"], request["event_ref"])
        runtime = (request["game_build"], request["session_ref"], request["process_instance_ref"])
        with self._lock:
            if self._runtime is None:
                self._runtime = runtime
            elif self._runtime != runtime:
                return {"state": "REOBSERVE", "reason": "NATIVE_CAREER_RUNTIME_CHANGED"}
            prior = self._attempts.get(key)
            if prior is not None:
                if not prior.get("refused"):
                    return {"state": "RECONCILE_EXISTING_ATTEMPT", "event_ref": key[1]}
                if (request["capture_ref"] == prior["request"]["capture_ref"]
                        or request["captured_at_epoch_ms"] <= prior["request"]["captured_at_epoch_ms"]):
                    return {"state": "REOBSERVE", "reason": "FRESH_CAPTURE_AFTER_REFUSAL_REQUIRED"}
            if prior is None and len(self._attempts) >= MAX_ATTEMPTS:
                return {"state": "SESSION_BUDGET_REACHED", "event_ref": key[1]}
            entry = {"request": request, "decision": decision, "dispatch_ref": None, "pending": True}
            self._attempts[key] = entry
        # Reserve before the call, so concurrent callbacks cannot send it twice.
        try:
            ack = adapter.submit_if_current(dict(request))
        except ADAPTER_ERRORS:
            ack = None
        with self._lock:
            entry["pending"] = False
            if (isinstance(ack, Mapping) and ack.get("state") == "REFUSED_NO_EFFECT"
                    and ack.get("attempt_ref") == request["attempt_ref"]):
                entry["refused"] = True
                return {"state": "REOBSERVE", "reason": "ATOMIC_NATIVE_CHECK_REFUSED"}
            if (not isinstance(ack, Mapping) or ack.get("state") != "SUBMITTED"
                    or ack.get("attempt_ref") != request["attempt_ref"]
                    or not _ref(ack.get("dispatch_ref"))):
                return {"state": "DISPATCH_OUTCOME_UNKNOWN", "event_ref": key[1]}
            entry["dispatch_ref"] = ack["dispatch_ref"]
        return {"state": "BETTERINSTINCTS_RESPONSE_SUBMITTED", "event_ref": key[1],
                "choice": decision["option_label"], "response_id": request["response_id"],
                "dispatch_ref": ack["dispatch_ref"], "outcome_observed": False}

    def reconcile(self, session_ref, event_ref, response, effect, continuation) -> dict:
        if not _ref(session_ref) or not _ref(event_ref):
            return {"state": "UNATTRIBUTED", "reason": "CAREER_ATTEMPT_REQUIRED"}
        with self._lock:
            entry = self._attempts.get((session_ref, event_ref))
            if entry is None or entry["pending"] or entry.get("refused"):
                return {"state": "UNATTRIBUTED", "reason": "CAREER_ATTEMPT_REQUIRED"}
            request = entry["request"]
            if (not isinstance(response, Mapping)
                    or response.get("attempt_ref") != request["attempt_ref"]
                    or not _ref(response.get("dispatch_ref"))
                    or (entry["dispatch_ref"] is not None
                        and entry["dispatch_ref"] != response["dispatch_ref"])):
                return {"state": "UNATTRIBUTED", "reason": "CAREER_ATTEMPT_ACK_MISMATCH"}
            for receipt in (response, effect, continuation):
                if (not isinstance(receipt, Mapping)
                        or any(receipt.get(field) != request[field] for field in SCOPE)):
                    return {"state": "UNATTRIBUTED", "reason": "CAREER_READBACK_SCOPE_MISMATCH"}
            if (effect.get("dispatch_ref") != response["dispatch_ref"]
                    or continuation.get("dispatch_ref") != response["dispatch_ref"]):
                return {"state": "UNATTRIBUTED", "reason": "CAREER_REWARD_DISPATCH_MISMATCH"}
            result = reconcile_career_event_turn(entry["decision"], response,
                                                effect=effect, activity=continuation)
            if result["state"] == "RESPONSE_EFFECT_AND_RESUMPTION_SHAPE_MATCH":
                entry["dispatch_ref"] = response["dispatch_ref"]
            return result
