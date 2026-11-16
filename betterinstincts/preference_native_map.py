"""Read-only exact-build Sims Video Gaming preference offer evidence binding.

This is a normalized host-side validator for the locally sourced EA tuning
map, NOT an embedded game hook or a response sender. Observer output and
effect events require independently authenticated local game provenance.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import json
from pathlib import Path
import re

MAP_PATH = (Path(__file__).resolve().parents[1] / "contracts"
            / "preference-native-response-map.v1.json")
OFFER_SCHEMA = "betterinstincts.preference-native-offer-observation/v1"
RESPONSE_SCHEMA = "betterinstincts.preference-native-response-observation/v1"
EFFECT_SCHEMA = "betterinstincts.preference-native-effect-observation/v1"
RESUME_SCHEMA = "betterinstincts.preference-native-activity-observation/v1"
TRAIT_MAP_SCHEMA = "betterinstincts.chased-by-death-native-binding/v1"
PROOF = "OFFLINE_OBSERVATION_SHAPE_NOT_AUTHENTICATED_NATIVE_GAME_EFFECT"
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


def _ref(value: object) -> bool:
    return type(value) is str and _ID.fullmatch(value) is not None


def _sim_id(value: object) -> bool:
    return (type(value) is str and 1 <= len(value) <= 20
            and value.isascii() and value.isdecimal() and value[0] != "0"
            and 0 < int(value) <= (1 << 64) - 1)


def _time(value: object) -> bool:
    return type(value) is int and value > 0


def _hold(reason: str) -> dict:
    return {"state": "HOLD", "reason": reason, "execute_allowed": False,
            "control_permit": None, "proof_ceiling": PROOF}


def load_response_map() -> dict:
    """Read only the repository-owned mapping; never scan saves or EA files."""
    data = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.preference-native-response-map/v1":
        raise ValueError("RESPONSE_MAP_SCHEMA_INVALID")
    if set(data.get("responses", {})) != {"YES", "NO"}:
        raise ValueError("RESPONSE_MAP_BRANCHES_INVALID")
    for choice in ("YES", "NO"):
        row = data["responses"][choice]
        if (type(row.get("response_id")) is not int
                or type(row.get("loot_id")) is not int
                or not isinstance(row.get("effect"), Mapping)
                or row["effect"].get("subject") != "Actor"):
            raise ValueError("RESPONSE_MAP_ACTOR_EFFECT_INVALID")
    return data


def assess_native_offer_binding(
    observation: Mapping[str, object] | None,
    *, response_map: Mapping[str, object] | None = None,
) -> dict:
    """Cross-check one reported native offer and Actor resolver; never respond.

    Matching caller-supplied fields cannot authenticate the EA observer.
    In particular, an on-screen selected Sim may differ from the recipient.
    """
    m = response_map if response_map is not None else load_response_map()
    if not isinstance(observation, Mapping):
        return _hold("NATIVE_OFFER_OBSERVATION_REQUIRED")
    if (observation.get("schema") != OFFER_SCHEMA
            or observation.get("source") != "EA_NATIVE"
            or observation.get("read_origin") != "RUNNING_GAME_MEMORY"):
        return _hold("LIVE_NATIVE_OFFER_SOURCE_REQUIRED")
    dialog = m["dialog"]
    if (observation.get("game_build") != m["game_build"]
            or type(observation.get("dialog_tuning_id")) is not int
            or observation.get("dialog_tuning_id") != dialog["tuning_id"]
            or observation.get("localization_key") != dialog["localization_key"]):
        return _hold("EXACT_PREFERENCE_TUNING_MISMATCH")
    if (observation.get("resolver_source") != m["resolver"]["source"]
            or observation.get("resolver_role") != m["resolver"]["recipient_role"]):
        return _hold("PREFERENCE_RESOLVER_ROLE_UNVERIFIED")
    actor = observation.get("resolver_actor_sim_id")
    if (not _sim_id(actor) or observation.get("moment_sim_id") != actor
            or not _sim_id(observation.get("household_id"))):
        return _hold("RESOLVER_ACTOR_NOT_MOMENT_RECIPIENT")
    selected = observation.get("selected_sim_id")
    if selected is not None and not _sim_id(selected):
        return _hold("SELECTED_SIM_ID_INVALID")
    keys = ("dialog_ref", "capture_ref", "native_hook_ref",
            "state_revision", "originating_interaction_ref")
    if any(not _ref(observation.get(k)) for k in keys) or not _time(
            observation.get("captured_at_epoch_ms")):
        return _hold("NATIVE_DIALOG_IDENTITY_OR_TIME_REQUIRED")
    ids = observation.get("response_ids")
    expected = {choice: m["responses"][choice]["response_id"]
                for choice in ("YES", "NO")}
    if (not isinstance(ids, Mapping) or set(ids) != {"YES", "NO"}
            or any(type(ids[k]) is not int or ids[k] != v
                   for k, v in expected.items())):
        return _hold("RESPONSE_IDS_DIFFER_FROM_INSTALLED_TUNING_MAP")
    return {
        "state": "OFFER_BINDING_SHAPE_MATCH", "reason": None,
        "game_build": m["game_build"], "dialog_ref": observation["dialog_ref"],
        "capture_ref": observation["capture_ref"],
        "captured_at_epoch_ms": observation["captured_at_epoch_ms"],
        "recipient_sim_id": actor, "household_id": observation["household_id"],
        "selected_sim_id": selected,
        "native_hook_ref": observation["native_hook_ref"],
        "state_revision": observation["state_revision"],
        "originating_interaction_ref": observation["originating_interaction_ref"],
        "response_ids": expected,
        "expected_effects": deepcopy(m["responses"]),
        "common_effects": deepcopy(m["common_effects"]),
        "execute_allowed": False, "control_permit": None, "proof_ceiling": PROOF,
    }


def assess_trait_decline_binding(observation, local_map):
    """Use explicit, exact-build installed tuning from the trusted adapter owner."""
    if not isinstance(local_map, Mapping) or local_map.get("schema") != TRAIT_MAP_SCHEMA:
        return _hold("LOCAL_TRAIT_RESPONSE_MAP_REQUIRED")
    ids = local_map.get("response_ids")
    if (local_map.get("topic_id") != "chased_by_death"
            or not _ref(local_map.get("installed_tuning_ref"))
            or not isinstance(local_map.get("game_build"), str)
            or not re.fullmatch(r"[0-9]+(?:\.[0-9]+){3}", local_map["game_build"])
            or not _ref(local_map.get("localization_key"))
            or any(type(local_map.get(k)) is not int or local_map[k] <= 0
                   for k in ("dialog_tuning_id", "trait_id"))
            or not isinstance(ids, Mapping) or set(ids) != {"YES", "NO"}
            or any(type(v) is not int or not 0 <= v <= 2**31 - 1 for v in ids.values())
            or ids["YES"] == ids["NO"]):
        return _hold("LOCAL_TRAIT_RESPONSE_MAP_INVALID")
    if (not isinstance(observation, Mapping)
            or observation.get("dialog_kind") != "sim_trait_offer"
            or type(observation.get("offered_trait_id")) is not int
            or observation.get("offered_trait_id") != local_map["trait_id"]
            or observation.get("recipient_trait_present") is not False
            or observation.get("button_labels") != {"YES": "Yes", "NO": "No thanks!"}):
        return _hold("EXACT_NATIVE_TRAIT_OFFER_REQUIRED")
    # Reuse the existing EA source, Actor, dialog, scope and response ID checks.
    m = {
        "game_build": local_map["game_build"],
        "dialog": {"tuning_id": local_map["dialog_tuning_id"],
                   "localization_key": local_map["localization_key"]},
        "resolver": {"source": "originating_interaction", "recipient_role": "Actor"},
        "responses": {role: {"response_id": rid} for role, rid in ids.items()},
        "common_effects": [],
    }
    binding = assess_native_offer_binding(observation, response_map=m)
    if binding["state"] == "OFFER_BINDING_SHAPE_MATCH":
        binding.update(trait_id=local_map["trait_id"], decline_only=True,
                       dialog_tuning_id=local_map["dialog_tuning_id"])
    return binding


def assess_native_preference_outcome(
    binding: Mapping[str, object] | None,
    response: Mapping[str, object] | None,
    effect: Mapping[str, object] | None,
    resumed: Mapping[str, object] | None,
) -> dict:
    """Check four correlated independent receipts, not just an input click.

    Caller-asserted receipts still require trusted game-host review to become
    proof. A common ActiveHousehold buff must not be counted as an Actor trait.
    """
    if not isinstance(binding, Mapping) or binding.get("state") != "OFFER_BINDING_SHAPE_MATCH":
        return _hold("VALID_OFFER_BINDING_REQUIRED")
    if (not isinstance(response, Mapping)
            or response.get("schema") != RESPONSE_SCHEMA
            or response.get("source") != "EA_NATIVE"
            or response.get("dialog_ref") != binding["dialog_ref"]
            or response.get("recipient_sim_id") != binding["recipient_sim_id"]
            or response.get("accepted_by_native_dialog") is not True
            or not _ref(response.get("event_ref"))
            or not _time(response.get("captured_at_epoch_ms"))
            or response["captured_at_epoch_ms"] <= binding["captured_at_epoch_ms"]):
        return _hold("MATCHED_NATIVE_RESPONSE_ACK_REQUIRED")
    rid = response.get("response_id")
    if type(rid) is not int:
        return _hold("RESPONSE_ID_INVALID")
    choice = next((k for k, v in binding["response_ids"].items() if v == rid), None)
    if choice is None:
        return _hold("RESPONSE_ID_NOT_IN_OFFER")
    if binding.get("decline_only") is True and choice != "NO":
        return _hold("AFFIRMATIVE_TRAIT_ACK_FORBIDDEN")
    if (not isinstance(effect, Mapping)
            or effect.get("schema") != EFFECT_SCHEMA
            or effect.get("source") != "EA_NATIVE"
            or effect.get("dialog_ref") != binding["dialog_ref"]
            or effect.get("response_event_ref") != response["event_ref"]
            or effect.get("recipient_sim_id") != binding["recipient_sim_id"]
            or not _ref(effect.get("capture_ref"))
            or effect["capture_ref"] == binding["capture_ref"]
            or not _time(effect.get("captured_at_epoch_ms"))
            or effect["captured_at_epoch_ms"] < response["captured_at_epoch_ms"]):
        return _hold("POST_RESPONSE_EFFECT_OBSERVATION_REQUIRED")
    if binding.get("decline_only") is True:
        if (type(effect.get("offered_trait_id")) is not int
                or effect.get("offered_trait_id") != binding["trait_id"]
                or effect.get("recipient_trait_present") is not False
                or effect.get("dialog_closed") is not True
                or effect["captured_at_epoch_ms"] <= response["captured_at_epoch_ms"]):
            return _hold("DECLINED_TRAIT_ABSENCE_AND_DIALOG_CLOSURE_REQUIRED")
        return {
            "state": "OUTCOME_RECEIPTS_SCHEMA_MATCH", "reason": None,
            "dialog_ref": binding["dialog_ref"], "recipient_sim_id": binding["recipient_sim_id"],
            "response_choice": "NO", "response_id": rid, "trait_added": False,
            "execute_allowed": False, "control_permit": None, "proof_ceiling": PROOF,
        }
    expected = binding["expected_effects"][choice]
    trait_key = "trait_id" if choice == "YES" else "marker_id"
    actor_effect = effect.get("actor_effect")
    common_effect = effect.get("common_effect")
    expected_common = binding["common_effects"][0]
    if (not isinstance(actor_effect, Mapping)
            or actor_effect.get("subject") != "Actor"
            or actor_effect.get("applied") is not True
            or type(actor_effect.get("loot_id")) is not int
            or actor_effect["loot_id"] != expected["loot_id"]
            or type(actor_effect.get("trait_or_marker_id")) is not int
            or actor_effect["trait_or_marker_id"] != expected["effect"][trait_key]
            or not isinstance(common_effect, Mapping)
            or common_effect.get("subject") != "ActiveHousehold"
            or common_effect.get("applied") is not True
            or type(common_effect.get("buff_id")) is not int
            or common_effect["buff_id"] != expected_common["buff_id"]):
        return _hold("ACTOR_AND_HOUSEHOLD_EFFECTS_NOT_SEPARATELY_OBSERVED")
    if (not isinstance(resumed, Mapping)
            or resumed.get("schema") != RESUME_SCHEMA
            or resumed.get("source") != "EA_NATIVE"
            or resumed.get("dialog_ref") != binding["dialog_ref"]
            or resumed.get("recipient_sim_id") != binding["recipient_sim_id"]
            or resumed.get("resumed") is not True
            or not _ref(resumed.get("activity_ref"))
            or not _ref(resumed.get("capture_ref"))
            or resumed["capture_ref"] == effect["capture_ref"]
            or resumed["capture_ref"] == binding["capture_ref"]
            or not _time(resumed.get("captured_at_epoch_ms"))
            or resumed["captured_at_epoch_ms"] <= effect["captured_at_epoch_ms"]):
        return _hold("POST_DIALOG_ACTIVITY_RESUMPTION_NOT_OBSERVED")
    return {
        "state": "OUTCOME_RECEIPTS_SCHEMA_MATCH", "reason": None,
        "dialog_ref": binding["dialog_ref"],
        "recipient_sim_id": binding["recipient_sim_id"],
        "response_choice": choice, "response_id": rid,
        "actor_loot_id": actor_effect["loot_id"],
        "actor_trait_or_marker_id": actor_effect["trait_or_marker_id"],
        "household_buff_id": common_effect["buff_id"],
        "resumed_activity_ref": resumed["activity_ref"],
        "execute_allowed": False, "control_permit": None, "proof_ceiling": PROOF,
    }
