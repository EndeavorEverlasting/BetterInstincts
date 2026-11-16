"""One response per offer through a trusted local EA adapter supplied by its owner.

Host Python coordinates the existing policy and receipt checks. The game-side
adapter owns observed EA state, player priority and atomic conditional submit.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from threading import Lock
from time import time
from uuid import uuid4

from betterinstincts.preference_native_map import (
    assess_native_offer_binding,
    assess_native_preference_outcome,
    assess_trait_decline_binding,
)
from betterinstincts.preference_prompts import TRAIT_OFFER, evaluate_offer, is_trait_offer

BINDING_FIELDS = (
    "game_build", "dialog_ref", "capture_ref", "recipient_sim_id", "household_id",
    "native_hook_ref", "state_revision", "originating_interaction_ref",
)
MAX_ATTEMPTS = 256
MAX_TRAIT_CAPTURE_AGE_MS = 1000


def _valid_dispatch_ref(value: object) -> bool:
    return (isinstance(value, str) and 1 <= len(value) <= 128
            and all(c.isascii() and (c.isalnum() or c in "._:-") for c in value))


class PreferenceResponsePort:
    """One bounded writer per live game session; create through a trusted adapter."""

    def __init__(self, adapter=None, *, trait_binding=None, now_ms=None):
        self._adapter = adapter
        self._trait_binding = deepcopy(trait_binding)
        self._now_ms = now_ms if now_ms is not None else lambda: int(time() * 1000)
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
            trait_offer = (
                (isinstance(offer, Mapping) and is_trait_offer(offer))
                or (isinstance(native, Mapping) and native.get("dialog_kind") == TRAIT_OFFER)
            )
            binding = (assess_trait_decline_binding(native, self._trait_binding)
                       if trait_offer else assess_native_offer_binding(native))
            if binding["state"] != "OFFER_BINDING_SHAPE_MATCH":
                return {"state": "REOBSERVE", "reason": binding["reason"]}
            dialog = binding["dialog_ref"]
            if dialog in self._attempts:
                return {"state": "RECONCILE_EXISTING_ATTEMPT", "dialog_ref": dialog}
            if (not isinstance(offer, Mapping)
                    or (not trait_offer and (offer.get("topic_id") != "video_gaming"
                                             or offer.get("offer_kind") != "like"))
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
            if trait_offer:
                if not 0 <= self._now_ms() - binding["captured_at_epoch_ms"] <= MAX_TRAIT_CAPTURE_AGE_MS:
                    return {"state": "REOBSERVE", "reason": "NATIVE_TRAIT_CAPTURE_STALE"}
                if (frame.get("native_idle_admitted") is not True
                        or type(frame.get("input_generation")) is not int
                        or frame["input_generation"] < 0):
                    return {"state": "YIELD_TO_PLAYER", "reason": "FRESH_NATIVE_IDLE_EVIDENCE_REQUIRED"}
                if decision["steps"] != ["NO"] or decision.get("target_label") != "No thanks!":
                    return {"state": "REOBSERVE", "reason": "AFFIRMATIVE_TRAIT_RESPONSE_FORBIDDEN"}
            else:
                continuation = decision["continuation"]
                if (continuation["state_revision"] != binding["state_revision"]
                        or continuation["native_hook_ref"] != binding["native_hook_ref"]
                        or continuation["recipient_household_id"] != binding["household_id"]):
                    return {"state": "REOBSERVE", "reason": "DECISION_STATE_BINDING_MISMATCH"}
            if len(self._attempts) >= MAX_ATTEMPTS:
                return {"state": "SESSION_BUDGET_REACHED", "reason": "RESPONSE_LIMIT"}

            choice = decision["steps"][0]
            request = {field: binding[field] for field in BINDING_FIELDS}
            attempt_ref = "bi-attempt:" + uuid4().hex
            request.update(response_id=binding["response_ids"][choice],
                           expected_paused=frame["paused"], attempt_ref=attempt_ref)
            if trait_offer:
                request.update(expected_label=decision["target_label"], expected_role="NO",
                               offered_trait_id=binding["trait_id"],
                               dialog_tuning_id=binding["dialog_tuning_id"],
                               expected_input_generation=frame["input_generation"])
            # Reserve before the call. The EA adapter must atomically recheck
            # dialog, actor, revision, save, pause and player intent before submit.
            entry = {"binding": binding, "choice": choice, "dispatch_ref": None,
                     "attempt_ref": attempt_ref}
            self._attempts[dialog] = entry
            try:
                acknowledgement = adapter.submit_if_current(dict(request))
            except (OSError, RuntimeError, ValueError):
                return {"state": "DISPATCH_OUTCOME_UNKNOWN", "dialog_ref": dialog}

            if isinstance(acknowledgement, Mapping) and acknowledgement.get("state") == "REFUSED":
                del self._attempts[dialog]
                return {"state": "REOBSERVE", "reason": "ATOMIC_NATIVE_CHECK_REFUSED"}
            ref = acknowledgement.get("dispatch_ref") if isinstance(acknowledgement, Mapping) else None
            if (not _valid_dispatch_ref(ref)
                    or acknowledgement.get("state") != "SUBMITTED"):
                return {"state": "DISPATCH_OUTCOME_UNKNOWN", "dialog_ref": dialog}
            entry["dispatch_ref"] = ref
            return {"state": "BETTERINSTINCTS_RESPONSE_SUBMITTED", "dialog_ref": dialog,
                    "dispatch_ref": ref, "choice": choice, "pause_before": frame["paused"],
                    "outcome_observed": False}

    def reconcile(self, dialog_ref: str, response: Mapping, effect: Mapping,
                  resumed: Mapping | None = None) -> dict:
        with self._lock:
            entry = self._attempts.get(dialog_ref)
            if (not entry or not isinstance(response, Mapping)
                    or type(response.get("response_id")) is not int
                    or response.get("response_id") != entry["binding"]["response_ids"][entry["choice"]]):
                return {"state": "BETTERINSTINCTS_RESPONSE_UNATTRIBUTED"}
            dispatch_ref = response.get("dispatch_ref")
            if not _valid_dispatch_ref(dispatch_ref):
                return {"state": "BETTERINSTINCTS_RESPONSE_UNATTRIBUTED"}
            # An adapter stamps attempt_ref only on a native ACK it correlated
            # with this submission, never on a screen/player reply or a mere
            # sighting of the same response ID. No retry after a lost return.
            if entry["dispatch_ref"] is None:
                if response.get("attempt_ref") != entry["attempt_ref"]:
                    return {"state": "BETTERINSTINCTS_RESPONSE_UNATTRIBUTED"}
            elif dispatch_ref != entry["dispatch_ref"]:
                return {"state": "BETTERINSTINCTS_RESPONSE_UNATTRIBUTED"}
            if (not entry["binding"].get("decline_only")
                    and (not isinstance(resumed, Mapping) or resumed.get("activity_ref")
                         != entry["binding"]["originating_interaction_ref"])):
                return {"state": "ORIGINAL_ACTIVITY_READBACK_REQUIRED"}
            outcome = assess_native_preference_outcome(entry["binding"], response, effect, resumed)
            if outcome["state"] == "OUTCOME_RECEIPTS_SCHEMA_MATCH":
                entry["dispatch_ref"] = dispatch_ref
            return outcome
