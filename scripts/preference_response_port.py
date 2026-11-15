"""One response per offer through a trusted local EA adapter supplied by its owner.

Host Python coordinates the existing policy and receipt checks. The game-side
adapter owns observed EA state, player priority and atomic conditional submit.
"""
from __future__ import annotations

from collections.abc import Mapping
from threading import Lock

from betterinstincts.preference_native_map import (
    assess_native_offer_binding,
    assess_native_preference_outcome,
)
from betterinstincts.preference_prompts import evaluate_offer

BINDING_FIELDS = (
    "game_build", "dialog_ref", "capture_ref", "recipient_sim_id", "household_id",
    "native_hook_ref", "state_revision", "originating_interaction_ref",
)
MAX_ATTEMPTS = 256


class PreferenceResponsePort:
    """One bounded writer per live game session; create through a trusted adapter."""

    def __init__(self, adapter=None):
        self._adapter = adapter
        self._attempts = {}
        self._lock = Lock()

    def respond(self, *, enabled: bool = False) -> dict:
        if enabled is not True:
            return {"state": "PLAYER_RETAINS_CHOICE", "reason": "AUTOMATION_NOT_OPTED_IN"}

        with self._lock:
            adapter = self._adapter
            if adapter is None:
                return {"state": "NATIVE_ADAPTER_REQUIRED", "reason": "NO_TRUSTED_RESPONSE_ADAPTER",
                        "next": "Inspect the local EA dialog adapter and recover a current observation. "
                                "Keep the running game and carry forward historical evidence."}
            try:
                frame = adapter.read_offer()
            except (OSError, RuntimeError, ValueError):
                return {"state": "REOBSERVE", "reason": "NATIVE_OFFER_READ_FAILED"}
            if not isinstance(frame, Mapping):
                return {"state": "REOBSERVE", "reason": "NO_CURRENT_NATIVE_OFFER"}
            native = frame.get("native_offer")
            offer = frame.get("policy_offer")
            binding = assess_native_offer_binding(native)
            if binding["state"] != "OFFER_BINDING_SHAPE_MATCH":
                return {"state": "REOBSERVE", "reason": binding["reason"]}
            dialog = binding["dialog_ref"]
            if dialog in self._attempts:
                return {"state": "RECONCILE_EXISTING_ATTEMPT", "dialog_ref": dialog}
            if (not isinstance(offer, Mapping) or offer.get("topic_id") != "video_gaming"
                    or offer.get("offer_kind") != "like"
                    or offer.get("captured_at_epoch_ms") != binding["captured_at_epoch_ms"]
                    or offer.get("capture_ref") != binding["capture_ref"]
                    or offer.get("recipient_sim_id") != binding["recipient_sim_id"]):
                return {"state": "REOBSERVE", "reason": "DECISION_OFFER_BINDING_MISMATCH"}
            if (frame.get("player_active") is not False
                    or frame.get("player_directed") is not False):
                return {"state": "YIELD_TO_PLAYER", "reason": "PLAYER_OWNERSHIP"}
            if (frame.get("save_authorized") is not True
                    or frame.get("scene_verified") is not True
                    or type(frame.get("paused")) is not bool):
                return {"state": "REOBSERVE", "reason": "LIVE_SCOPE_NOT_VERIFIED"}
            decision = evaluate_offer(offer, automation_opt_in=True)
            if decision["decision"] == "HOLD":
                return {"state": "NEEDS_DECISION_EVIDENCE", "reason": decision["reason"]}
            continuation = decision["continuation"]
            if (continuation["state_revision"] != binding["state_revision"]
                    or continuation["native_hook_ref"] != binding["native_hook_ref"]
                    or continuation["recipient_household_id"] != binding["household_id"]):
                return {"state": "REOBSERVE", "reason": "DECISION_STATE_BINDING_MISMATCH"}
            if len(self._attempts) >= MAX_ATTEMPTS:
                return {"state": "SESSION_BUDGET_REACHED", "reason": "RESPONSE_LIMIT"}

            choice = decision["steps"][0]
            request = {field: binding[field] for field in BINDING_FIELDS}
            request.update(response_id=binding["response_ids"][choice],
                           expected_paused=frame["paused"])
            # Reserve before the call. The EA adapter must atomically recheck
            # dialog, actor, revision, save, pause and player intent before submit.
            entry = {"binding": binding, "choice": choice, "dispatch_ref": None}
            self._attempts[dialog] = entry
            try:
                acknowledgement = adapter.submit_if_current(dict(request))
            except (OSError, RuntimeError, ValueError):
                return {"state": "DISPATCH_OUTCOME_UNKNOWN", "dialog_ref": dialog}

            if isinstance(acknowledgement, Mapping) and acknowledgement.get("state") == "REFUSED":
                del self._attempts[dialog]
                return {"state": "REOBSERVE", "reason": "ATOMIC_NATIVE_CHECK_REFUSED"}
            ref = acknowledgement.get("dispatch_ref") if isinstance(acknowledgement, Mapping) else None
            if (not isinstance(ref, str) or not 1 <= len(ref) <= 128
                    or not all(c.isascii() and (c.isalnum() or c in "._:-") for c in ref)
                    or acknowledgement.get("state") != "SUBMITTED"):
                return {"state": "DISPATCH_OUTCOME_UNKNOWN", "dialog_ref": dialog}
            entry["dispatch_ref"] = ref
            return {"state": "BETTERINSTINCTS_RESPONSE_SUBMITTED", "dialog_ref": dialog,
                    "dispatch_ref": ref, "choice": choice, "pause_before": frame["paused"],
                    "outcome_observed": False}

    def reconcile(self, dialog_ref: str, response: Mapping, effect: Mapping, resumed: Mapping) -> dict:
        with self._lock:
            entry = self._attempts.get(dialog_ref)
            if (not entry or entry["dispatch_ref"] is None or not isinstance(response, Mapping)
                    or response.get("dispatch_ref") != entry["dispatch_ref"]
                    or response.get("response_id") != entry["binding"]["response_ids"][entry["choice"]]):
                return {"state": "BETTERINSTINCTS_RESPONSE_UNATTRIBUTED"}
            if (not isinstance(resumed, Mapping) or resumed.get("activity_ref")
                    != entry["binding"]["originating_interaction_ref"]):
                return {"state": "ORIGINAL_ACTIVITY_READBACK_REQUIRED"}
            return assess_native_preference_outcome(entry["binding"], response, effect, resumed)
