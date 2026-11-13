"""Source-gated, cursor-free NanoCan recycling decisions for a native Sims adapter.

Pure policy: no Simoleons are posted, no EA resources are patched, and no
desktop controls, game APIs, saves or action queues are touched here.
The verified installed-game adapter is a separate P08/native successor.
"""
from __future__ import annotations

import math
import time
from collections.abc import Mapping

SCHEMA = "betterinstincts.nanocan-recycling/v1"
RESULT_SCHEMA = "betterinstincts.nanocan-recycling-result/v1"
OUTCOME_SCHEMA = "betterinstincts.nanocan-outcome/v1"
ROUTES = ("NATIVE_DRAG_EQUIVALENT", "NATIVE_SIM_DISPOSE")
ATTEMPTS = frozenset(("NONE", "QUEUED", "DISPATCHED", "CONFIRMED"))
MAX_DISHES, MAX_CANS, MAX_ROUTES, MAX_AGE = 32, 8, 64, 180
MAX_NATIVE_SIMS = 32
MAX_WASTE_ITEMS, MAX_PENDING_CLEANUP = 32, 12
WASTE_KINDS = frozenset(("TRASH_PILE", "EMPTY_CONTAINER", "SPOILED_GARBAGE",
                         "OTHER_VERIFIED_GARBAGE"))
NATIVE_QUEUE_ORIGINS = frozenset(("SIM_AUTONOMY", "WHIM_AUTONOMY",
                                  "VANILLA_ROUTINE"))
CLEANUP_DESTINATIONS = {
    "DISH_TO_SINK": "SINK",
    "DISH_TO_DISHWASHER": "DISHWASHER",
    "DISH_TO_STANDARD_BIN": "STANDARD_TRASH_CAN",
    "GARBAGE_TO_STANDARD_BIN": "STANDARD_TRASH_CAN",
}


class NanoCanRecyclingError(ValueError):
    """Malformed source evidence is not an eligibility signal."""


def _ref(value: object) -> bool:
    return (
        isinstance(value, str)
        and 1 <= len(value) <= 120
        and all(c.isalnum() or c in "_.:-" for c in value)
    )


def _number(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _rows(raw: object, limit: int, kind: str, key: str) -> list[dict]:
    if not isinstance(raw, list) or len(raw) > limit:
        raise NanoCanRecyclingError("NANOCAN_" + kind + "_BOUNDS_INVALID")
    seen: set[str] = set()
    cleaned = []
    for item in raw:
        if not isinstance(item, Mapping) or not _ref(item.get(key)):
            raise NanoCanRecyclingError("NANOCAN_" + kind + "_IDENTITY_INVALID")
        if item[key] in seen:
            raise NanoCanRecyclingError("NANOCAN_" + kind + "_DUPLICATE")
        seen.add(item[key])
        cleaned.append(dict(item))
    return cleaned


def _actor_safe(actor: Mapping) -> bool:
    """Only a proven idle, unowned Sim may perform a native trash interaction."""
    if any(actor.get(k) is not False for k in (
        "player_command_present", "player_owned", "urgent_need",
        "imminent_obligation",
    )):
        return False
    if actor.get("queue_verified") is not True or actor.get("policy_opt_in") is not True:
        return False
    queue = actor.get("queue")
    return (isinstance(queue, list) and len(queue) <= 24
            and all(isinstance(q, Mapping)
                    and q.get("origin") in NATIVE_QUEUE_ORIGINS
                    and _ref(q.get("origin_proof_ref")) for q in queue))


def _pending_cleanup(item: Mapping, *, item_ref: str) -> list[dict]:
    """Validate native action IDs, not UI strings or guesses about an action."""
    rows = item.get("pending_cleanup", [])
    if not isinstance(rows, list) or len(rows) > MAX_PENDING_CLEANUP:
        raise NanoCanRecyclingError("NANOCAN_PENDING_CLEANUP_BOUNDS_INVALID")
    seen = set()
    verified = []
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise NanoCanRecyclingError("NANOCAN_PENDING_CLEANUP_ROW_INVALID")
        if (not all(_ref(raw.get(k)) for k in (
                    "item_ref", "actor_ref", "queue_slot_ref", "action_id",
                    "origin_proof_ref", "native_action_source_ref", "destination_ref",
                    "capture_ref", "game_build"))
                or raw.get("origin") not in NATIVE_QUEUE_ORIGINS
                or raw.get("cleanup_kind") not in CLEANUP_DESTINATIONS
                or raw.get("destination_kind") != CLEANUP_DESTINATIONS[raw["cleanup_kind"]]
                or type(raw.get("action_kind_verified")) is not bool
                or raw.get("source_kind") not in {"EA_TUNING", "EA_SCRIPT"}
                or raw.get("queue_phase") not in {"QUEUED", "ACTIVE", "UNKNOWN"}
                or not _ref(raw.get("queue_revision_ref"))):
            raise NanoCanRecyclingError("NANOCAN_PENDING_CLEANUP_PROOF_INVALID")
        if (raw["cleanup_kind"].startswith("DISH_") != (item.get("dish_ref") == item_ref)):
            raise NanoCanRecyclingError("NANOCAN_CLEANUP_ITEM_KIND_CONFLICT")
        identity = (raw["actor_ref"], raw["queue_slot_ref"])
        if identity in seen:
            raise NanoCanRecyclingError("NANOCAN_DUPLICATE_CLEANUP_SLOT")
        seen.add(identity)
        verified.append(dict(raw))
    return verified


def _player_claims_item(item_ref: str, actors: Mapping, *, capture_ref: str) -> bool:
    """Protect an item if current household queue ownership is not resolved.

    A manual/unknown command with no observed target might concern *any*
    item. Missing or stale Sim queues never prove there is no player claim.
    """
    if not actors:
        return True
    for actor in actors.values():
        queue = actor.get("queue")
        if (actor.get("capture_ref") != capture_ref
                or actor.get("queue_verified") is not True
                or not isinstance(queue, list) or len(queue) > 24):
            return True
        if actor.get("player_command_present") is True and not queue:
            return True
        for row in queue:
            if not isinstance(row, Mapping):
                return True
            native = (row.get("origin") in NATIVE_QUEUE_ORIGINS
                      and _ref(row.get("origin_proof_ref")))
            target = row.get("item_ref")
            # Unidentified player or unknown target is a household-wide hold.
            if ((not _ref(target) and
                 (not native or row.get("cleanup_kind") in CLEANUP_DESTINATIONS))
                    or (target == item_ref and not native)):
                return True
    return False


def _queued_item_claimed(item_ref: str, actors: Mapping) -> bool:
    """An existing queued use of an item requires a proven paired replacement.

    A source-qualified but busy item is not free for a separate NanoCan action.
    """
    return any(isinstance(actor.get("queue"), list)
               and any(isinstance(row, Mapping) and row.get("item_ref") == item_ref
                       for row in actor["queue"])
               for actor in actors.values())


def _spatial_route_proven(
    route: Mapping, *, observation: Mapping, item_ref: str, can_ref: str,
    game_build: str, capture_ref: str,
) -> bool:
    """Bind a native route to independently observed objects and traversability.

    This attestation is *not* a live SLAM detector or queue effect permission.
    EA game routing, not camera pixels, must ultimately authorize pathfinding.
    """
    geometry = route.get("spatial_proof")
    if not isinstance(geometry, Mapping) or not _ref(observation.get("lot_ref")):
        return False
    if (geometry.get("lot_ref") != observation["lot_ref"]
            or not _ref(observation.get("world_revision_ref"))
            or geometry.get("world_revision_ref") != observation["world_revision_ref"]
            or geometry.get("game_build") != game_build
            or geometry.get("capture_ref") != capture_ref
            or geometry.get("item_ref") != item_ref
            or geometry.get("can_ref") != can_ref
            or geometry.get("source") not in {"EA_LOT_GRAPH", "SEMANTIC_3D"}
            or not all(_ref(geometry.get(k)) for k in (
                "source_ref", "world_revision_ref", "item_floor_id", "can_floor_id"))
            or any(geometry.get(k) is not True for k in (
                "item_identity_verified", "can_identity_verified",
                "native_route_reachable_verified"))):
        return False
    if (route["mode"] == "NATIVE_SIM_DISPOSE"
            and geometry.get("sim_route_reachable_verified") is not True):
        return False
    if (geometry["item_floor_id"] != geometry["can_floor_id"]
            and geometry.get("vertical_route_verified") is not True):
        return False
    return True


def _queue_cleanup_candidate(
    item: Mapping, *, item_ref: str, can_ref: str, route: Mapping,
    observation: Mapping, actor_map: Mapping, game_build: str,
    capture_ref: str, proposal_key: str,
) -> dict | None:
    """One exact, coupled suppression+replacement suggestion; never dispatch."""
    if (not _spatial_route_proven(
            route, observation=observation, item_ref=item_ref, can_ref=can_ref,
            game_build=game_build, capture_ref=capture_ref)
            or not _ref(observation.get("queue_revision_ref"))):
        return None
    for cleanup in _pending_cleanup(item, item_ref=item_ref):
        if (cleanup["item_ref"] != item_ref
                or cleanup["capture_ref"] != capture_ref
                or cleanup["game_build"] != game_build
                or cleanup["action_kind_verified"] is not True
                or cleanup["queue_phase"] != "QUEUED"
                or cleanup["queue_revision_ref"] != observation["queue_revision_ref"]):
            continue
        actor = actor_map.get(cleanup["actor_ref"])
        if actor is None or actor.get("capture_ref") != capture_ref or not _actor_safe(actor):
            continue
        if (route["mode"] == "NATIVE_SIM_DISPOSE"
                and route.get("actor_ref") != actor["sim_ref"]):
            continue
        matches = [q for q in actor["queue"]
                   if all(q.get(k) == cleanup[k] for k in (
                       "queue_slot_ref", "action_id", "origin", "origin_proof_ref",
                       "item_ref", "cleanup_kind", "destination_ref",
                       "native_action_source_ref", "capture_ref",
                       "game_build", "source_kind", "destination_kind",
                       "queue_phase", "queue_revision_ref"))
                   and q.get("action_kind_verified") is True]
        if len(matches) != 1:
            continue
        return {
            "kind": "ATOMIC_NATIVE_CLEANUP_REDIRECTION_CANDIDATE",
            "actor_ref": cleanup["actor_ref"],
            "queue_slot_ref": cleanup["queue_slot_ref"],
            "source_action_id": cleanup["action_id"],
            "source_origin": cleanup["origin"],
            "source_destination_kind": cleanup["destination_kind"],
            "native_action_source_ref": cleanup["native_action_source_ref"],
            "queue_revision_ref": cleanup["queue_revision_ref"],
            "source_kind": cleanup["source_kind"],
            "item_ref": item_ref, "can_ref": can_ref,
            "replacement_proposal_key": proposal_key,
            "spatial_source_ref": route["spatial_proof"]["source_ref"],
            "requires_native_transaction": True,
            "cancel_first_without_replacement": False,
            "requires": [
                "RECHECK_EXACT_SOURCE_QUEUE_SLOT_AND_ORIGIN",
                "RECHECK_PLAYER_INTENT_AND_ACTIVE_GOAL",
                "RECHECK_CURRENT_OBJECTS_LOT_AND_NATIVE_PATH",
                "RECHECK_NANOCAN_COOLDOWN_AND_NATIVE_AFFORDANCE",
                "NATIVE_ATOMIC_REPLACE_OR_PRESERVE_ORIGINAL_ACTION",
                "OBSERVE_ITEM_REMOVAL_AND_INDEPENDENT_FUNDS_DELTA",
            ],
        }
    return None


def evaluate_nanocan_recycling(
    observation: Mapping, *, household_ref: str, game_build: str,
    capture_ref: str, player_active: bool | None,
    sims: list[Mapping], now: float | None = None,
) -> dict:
    """Propose one native, cursor-free disposal; never authorize a side effect.

    A player's drag/drop and a Sim's ordinary disposal are *different reward
    mechanics*. Their community-reported values are only planning hypotheses,
    not in-game certification or an instruction to increase household funds.
    """
    if not isinstance(observation, Mapping) or observation.get("schema") != SCHEMA:
        raise NanoCanRecyclingError("NANOCAN_SCHEMA_INVALID")
    if not all(_ref(x) for x in (household_ref, game_build, capture_ref)):
        raise NanoCanRecyclingError("NANOCAN_CONTEXT_INVALID")
    if (game_build.lower() in {"unknown", "any", "latest"}
            or player_active not in (True, False, None)
            or not isinstance(sims, list) or len(sims) > MAX_NATIVE_SIMS):
        raise NanoCanRecyclingError("NANOCAN_HOST_CONTEXT_INVALID")
    if (observation.get("household_ref") != household_ref
            or observation.get("game_build") != game_build
            or observation.get("capture_ref") != capture_ref):
        raise NanoCanRecyclingError("NANOCAN_CONTEXT_MISMATCH")
    dishes = _rows(observation.get("dishes"), MAX_DISHES, "DISHES", "dish_ref")
    waste = _rows(observation.get("waste_items", []), MAX_WASTE_ITEMS,
                  "WASTE", "waste_ref")
    cans = _rows(observation.get("cans"), MAX_CANS, "CANS", "can_ref")
    routes = observation.get("native_routes")
    if not isinstance(routes, list) or len(routes) > MAX_ROUTES:
        raise NanoCanRecyclingError("NANOCAN_ROUTES_BOUNDS_INVALID")
    actor_map = {}
    for sim in sims:
        if not isinstance(sim, Mapping) or not _ref(sim.get("sim_ref")):
            raise NanoCanRecyclingError("NANOCAN_SIM_ID_INVALID")
        if sim["sim_ref"] in actor_map:
            raise NanoCanRecyclingError("NANOCAN_DUPLICATE_SIM")
        actor_map[sim["sim_ref"]] = sim
    for dish in dishes:
        if (dish.get("state") not in {
                "DIRTY_EMPTY", "EDIBLE_FOOD", "LEFTOVERS", "CLEAN",
                "UNKNOWN", "PLAYER_RESERVED"}
                or dish.get("attempt", "NONE") not in ATTEMPTS
                or type(dish.get("stack_size")) is not int
                or not 1 <= dish["stack_size"] <= 32
                or any(type(dish.get(k)) is not bool for k in
                       ("verified", "player_reserved", "disposal_allowed"))):
            raise NanoCanRecyclingError("NANOCAN_DISH_ROW_INVALID")
        _pending_cleanup(dish, item_ref=dish["dish_ref"])
    for item in waste:
        if (item.get("kind") not in WASTE_KINDS
                or not _ref(item.get("identity_proof_ref"))
                or item.get("attempt", "NONE") not in ATTEMPTS
                or any(type(item.get(k)) is not bool for k in (
                    "verified", "player_reserved", "disposal_allowed"))):
            raise NanoCanRecyclingError("NANOCAN_WASTE_ROW_INVALID")
        _pending_cleanup(item, item_ref=item["waste_ref"])
    for can in cans:
        if (can.get("kind") != "NANOCAN_TOUCHLESS"
                or any(type(can.get(k)) is not bool for k in (
                    "verified", "usable", "cooldown_ready", "broken",
                    "player_reserved"))):
            raise NanoCanRecyclingError("NANOCAN_CAN_ROW_INVALID")
    for route in routes:
        if not isinstance(route, Mapping) or route.get("mode") not in ROUTES:
            raise NanoCanRecyclingError("NANOCAN_ROUTE_INVALID")
        if (sum(_ref(route.get(k)) for k in ("dish_ref", "waste_ref")) != 1
                or not all(_ref(route.get(k)) for k in (
                    "can_ref", "capture_ref", "ea_source_ref", "native_affordance_ref",
                ))) or any(type(route.get(k)) is not bool for k in (
            "available", "native_route_verified")):
            raise NanoCanRecyclingError("NANOCAN_ROUTE_PROOF_INVALID")
        if (route.get("game_build") != game_build
                or route.get("source_kind") not in {"EA_TUNING", "EA_SCRIPT"}
                or route.get("mechanism_verified") is not True):
            raise NanoCanRecyclingError("NANOCAN_NATIVE_BUILD_OR_SOURCE_PROOF_INVALID")
        if route["mode"] == "NATIVE_SIM_DISPOSE":
            if not _ref(route.get("actor_ref")):
                raise NanoCanRecyclingError("NANOCAN_ROUTE_ACTOR_INVALID")
        elif (type(route.get("reward_equivalence_verified")) is not bool
              or (route["reward_equivalence_verified"] is True
                  and not _ref(route.get("reward_proof_ref")))):
            raise NanoCanRecyclingError("NANOCAN_REWARD_PROOF_INVALID")

    result = {
        "schema": RESULT_SCHEMA,
        "capture_ref": capture_ref,
        "household_ref": household_ref,
        "game_build": game_build,
        "state": "REOBSERVE_NANOCAN",
        "proposal": None,
        "sink_suppression_candidate": None,
        "queue_redirection_candidate": None,
        "reported_reward_estimate_simoleons": None,
        "reported_reward_is_game_proven": False,
        "dispatch_authorized": False,
        "cancel_allowed": False,
        "desktop_input_allowed": False,
        "proof_ceiling": "OFFLINE_NANOCAN_NATIVE_POLICY_NOT_EA_DISPOSAL_OR_MONEY",
    }
    def finish(state: str) -> dict:
        result["state"] = state
        return result

    stamp = observation.get("observed_at_unix")
    instant = time.time() if now is None else now
    if (not _number(stamp) or not _number(instant)
            or not 0 <= instant - stamp <= MAX_AGE):
        return finish("REOBSERVE_NANOCAN")
    if player_active is not False:
        return finish("PLAYER_FIRST")
    if (observation.get("policy_opt_in") is not True
            or observation.get("scene") != "LIVE"
            or observation.get("lot_scope") != "HOME"
            or observation.get("household_verified") is not True
            or observation.get("lot_verified") is not True
            or observation.get("queue_verified") is not True):
        return finish("NANOCAN_HOME_OPT_IN_OR_PROOF_REQUIRED")
    if (not dishes and not waste) or not cans:
        return finish("NO_ELIGIBLE_DISH_OR_NANOCAN")

    by_dish = {d["dish_ref"]: d for d in dishes}
    by_waste = {w["waste_ref"]: w for w in waste}
    by_can = {c["can_ref"]: c for c in cans}
    choices = []
    for route in routes:
        is_dish = _ref(route.get("dish_ref"))
        item_ref = route["dish_ref"] if is_dish else route["waste_ref"]
        item = (by_dish if is_dish else by_waste).get(item_ref)
        can = by_can.get(route["can_ref"])
        if item is None or can is None or _player_claims_item(
                item_ref, actor_map, capture_ref=capture_ref):
            continue
        if (route["capture_ref"] != capture_ref
                or not route["available"] or not route["native_route_verified"]
                or item.get("capture_ref") != capture_ref
                or can.get("capture_ref") != capture_ref):
            continue
        if ((is_dish and (item["state"] != "DIRTY_EMPTY"
                          or item["stack_size"] != 1))
                or item["attempt"] != "NONE"
                or not item["verified"] or item["player_reserved"]
                or not item["disposal_allowed"]
                or not can["verified"] or not can["usable"]
                or can["broken"] or can["player_reserved"]
                or not can["cooldown_ready"]):
            continue
        if route["mode"] == "NATIVE_DRAG_EQUIVALENT":
            if route.get("reward_equivalence_verified") is not True:
                continue
        else:
            actor = actor_map.get(route["actor_ref"])
            if actor is None or actor.get("capture_ref") != capture_ref:
                continue
            if not _actor_safe(actor):
                continue
        choices.append((ROUTES.index(route["mode"]), item_ref,
                        can["can_ref"], route))
    if not choices:
        return finish("NATIVE_DISPOSAL_ROUTE_NOT_VERIFIED_OR_BUSY")
    # Prefer an exact replaceable autonomous queue action over an unpaired
    # high-payout route. Preserve the old drag-first ranking otherwise.
    ranked = []
    for route_rank, candidate_ref, candidate_can, candidate_route in choices:
        candidate_is_dish = _ref(candidate_route.get("dish_ref"))
        candidate_item = (by_dish if candidate_is_dish else by_waste)[candidate_ref]
        proposal_key = ":".join((capture_ref, candidate_ref, candidate_can,
                                 candidate_route["mode"]))
        paired = _queue_cleanup_candidate(
            candidate_item, item_ref=candidate_ref, can_ref=candidate_can,
            route=candidate_route, observation=observation, actor_map=actor_map,
            game_build=game_build, capture_ref=capture_ref, proposal_key=proposal_key)
        if paired is None and _queued_item_claimed(candidate_ref, actor_map):
            continue
        ranked.append((0 if paired else 1, route_rank, candidate_ref,
                       candidate_can, candidate_route, paired))
    if not ranked:
        return finish("NATIVE_DISPOSAL_ROUTE_NOT_VERIFIED_OR_BUSY")
    _, _, item_ref, can_ref, route, paired_redirection = min(
        ranked, key=lambda c: c[:4])
    is_dish = _ref(route.get("dish_ref"))
    selected = (by_dish if is_dish else by_waste)[item_ref]
    # A proposal is a plan, not a native queue action or a money mutation.
    result["proposal"] = {
        "kind": "CURSOR_FREE_NANOCAN_DISPOSAL_CANDIDATE",
        "mode": route["mode"],
        "dish_ref": item_ref if is_dish else None,
        "waste_ref": None if is_dish else item_ref,
        "item_kind": "DIRTY_EMPTY_DISH" if is_dish else selected["kind"],
        "can_ref": can_ref,
        "actor_ref": route.get("actor_ref") if route["mode"] == "NATIVE_SIM_DISPOSE" else None,
        "capture_ref": capture_ref,
        "native_affordance_ref": route["native_affordance_ref"],
        "ea_source_ref": route["ea_source_ref"],
        "proposal_key": ":".join((capture_ref, item_ref, can_ref, route["mode"])),
        "may_post_money": False,
        "requires_independent_actual_funds_delta": True,
        "needs_installed_build_native_adapter": True,
    }
    member_count = observation.get("household_member_count")
    if (is_dish and observation.get("household_member_count_verified") is True
            and type(member_count) is int and 1 <= member_count <= 8):
        result["reported_reward_estimate_simoleons"] = (
            10 * member_count if route["mode"] == "NATIVE_DRAG_EQUIVALENT" else 10
        )
    # Sink suppression is ONLY a candidate when safe NanoCan disposal is
    # already eligible; never cancel a queue or override a manual wash.
    result["queue_redirection_candidate"] = paired_redirection
    # Legacy sink field is now an alias of the *same proven* native
    # redirection. An unverified pending_sink hint grants no suppression.
    if (is_dish and paired_redirection is not None
            and paired_redirection["source_destination_kind"] == "SINK"
            and paired_redirection["source_origin"] == "SIM_AUTONOMY"):
        result["sink_suppression_candidate"] = {
            "queue_slot_ref": paired_redirection["queue_slot_ref"],
            "dish_ref": item_ref,
            "requires": paired_redirection["requires"],
        }
    return finish("NANOCAN_NATIVE_DISPOSAL_CANDIDATE")


def reconcile_nanocan_outcome(receipt: Mapping) -> dict:
    """Verify money and actual disposal with independent causal evidence.

    No reconciliation function writes funds; a positive unrelated balance
    change is not proof of NanoCan recycling revenue.
    """
    if not isinstance(receipt, Mapping) or receipt.get("schema") != OUTCOME_SCHEMA:
        raise NanoCanRecyclingError("NANOCAN_OUTCOME_SCHEMA_INVALID")
    is_waste = _ref(receipt.get("waste_ref"))
    if (is_waste == _ref(receipt.get("dish_ref"))):
        raise NanoCanRecyclingError("NANOCAN_OUTCOME_ITEM_IDENTITY_INVALID")
    for key in ("proposal_key", "can_ref", "before_capture_ref",
                "after_capture_ref", "attempt_ref"):
        if not _ref(receipt.get(key)):
            raise NanoCanRecyclingError("NANOCAN_OUTCOME_IDENTITY_INVALID")
    before, after = receipt.get("funds_before"), receipt.get("funds_after")
    if not _number(before) or not _number(after):
        raise NanoCanRecyclingError("NANOCAN_FUNDS_PROOF_INVALID")
    if (receipt["before_capture_ref"] == receipt["after_capture_ref"]
            or receipt.get("attempt_state") != "DISPATCHED"):
        raise NanoCanRecyclingError("NANOCAN_OUTCOME_TRANSITION_INVALID")
    change = after - before
    outcome = {
        "schema": "betterinstincts.nanocan-outcome-result/v1",
        "proposal_key": receipt["proposal_key"],
        "verified_reward_simoleons": None,
        "state": "NOT_VERIFIED",
        "modifies_household_funds": False,
    }
    if ((receipt.get("waste_removed_verified") if is_waste else
         receipt.get("dish_removed_verified")) is not True
            or not _ref(receipt.get("disposal_proof_ref"))):
        outcome["state"] = "WASTE_DISPOSAL_NOT_PROVED" if is_waste else "DISH_DISPOSAL_NOT_PROVED"
    elif (receipt.get("causal_reward_verified") is not True
          or not _ref(receipt.get("causal_reward_proof_ref"))):
        outcome["state"] = "FUNDS_DELTA_NOT_ATTRIBUTED_TO_NANOCAN"
    elif change < 0:
        outcome["state"] = "AMBIGUOUS_NEGATIVE_FUNDS_CHANGE"
    elif change == 0:
        outcome["state"] = "NO_REWARD_OBSERVED"
        outcome["verified_reward_simoleons"] = 0
    else:
        outcome["state"] = "VERIFIED_REWARD"
        outcome["verified_reward_simoleons"] = change
    return outcome
