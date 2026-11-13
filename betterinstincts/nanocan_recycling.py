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
                    and q.get("origin") == "SIM_AUTONOMY"
                    and _ref(q.get("origin_proof_ref")) for q in queue))


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
    for can in cans:
        if (can.get("kind") != "NANOCAN_TOUCHLESS"
                or any(type(can.get(k)) is not bool for k in (
                    "verified", "usable", "cooldown_ready", "broken",
                    "player_reserved"))):
            raise NanoCanRecyclingError("NANOCAN_CAN_ROW_INVALID")
    for route in routes:
        if not isinstance(route, Mapping) or route.get("mode") not in ROUTES:
            raise NanoCanRecyclingError("NANOCAN_ROUTE_INVALID")
        if not all(_ref(route.get(k)) for k in (
            "dish_ref", "can_ref", "capture_ref", "ea_source_ref",
            "native_affordance_ref",
        )) or any(type(route.get(k)) is not bool for k in (
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
    if not dishes or not cans:
        return finish("NO_ELIGIBLE_DISH_OR_NANOCAN")

    by_dish = {d["dish_ref"]: d for d in dishes}
    by_can = {c["can_ref"]: c for c in cans}
    choices = []
    for route in routes:
        dish, can = by_dish.get(route["dish_ref"]), by_can.get(route["can_ref"])
        if dish is None or can is None:
            continue
        if (route["capture_ref"] != capture_ref
                or not route["available"] or not route["native_route_verified"]
                or dish.get("capture_ref") != capture_ref
                or can.get("capture_ref") != capture_ref):
            continue
        if (dish["state"] != "DIRTY_EMPTY" or dish["stack_size"] != 1
                or dish["attempt"] != "NONE"
                or not dish["verified"] or dish["player_reserved"]
                or not dish["disposal_allowed"]
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
        choices.append((ROUTES.index(route["mode"]), dish["dish_ref"],
                        can["can_ref"], route))
    if not choices:
        return finish("NATIVE_DISPOSAL_ROUTE_NOT_VERIFIED_OR_BUSY")
    _, dish_ref, can_ref, route = sorted(choices, key=lambda c: c[:3])[0]
    # A proposal is a plan, not a native queue action or a money mutation.
    result["proposal"] = {
        "kind": "CURSOR_FREE_NANOCAN_DISPOSAL_CANDIDATE",
        "mode": route["mode"],
        "dish_ref": dish_ref,
        "can_ref": can_ref,
        "actor_ref": route.get("actor_ref") if route["mode"] == "NATIVE_SIM_DISPOSE" else None,
        "capture_ref": capture_ref,
        "native_affordance_ref": route["native_affordance_ref"],
        "ea_source_ref": route["ea_source_ref"],
        "proposal_key": ":".join((capture_ref, dish_ref, can_ref, route["mode"])),
        "may_post_money": False,
        "requires_independent_actual_funds_delta": True,
        "needs_installed_build_native_adapter": True,
    }
    member_count = observation.get("household_member_count")
    if (observation.get("household_member_count_verified") is True
            and type(member_count) is int and 1 <= member_count <= 8):
        result["reported_reward_estimate_simoleons"] = (
            10 * member_count if route["mode"] == "NATIVE_DRAG_EQUIVALENT" else 10
        )
    # Sink suppression is ONLY a candidate when safe NanoCan disposal is
    # already eligible; never cancel a queue or override a manual wash.
    sink = by_dish[dish_ref].get("pending_sink")
    sink_actor = actor_map.get(sink.get("actor_ref")) if isinstance(sink, Mapping) else None
    if (isinstance(sink, Mapping)
            and sink.get("action_id") == "WASH_DISHES"
            and sink.get("origin") == "SIM_AUTONOMY"
            and sink.get("dish_ref") == dish_ref
            and sink.get("capture_ref") == capture_ref
            and _ref(sink.get("queue_slot_ref"))
            and _ref(sink.get("origin_proof_ref"))
            and sink_actor is not None and _actor_safe(sink_actor)
            and any(
                q.get("queue_slot_ref") == sink["queue_slot_ref"]
                and q.get("action_id") == "WASH_DISHES"
                and q.get("origin_proof_ref") == sink["origin_proof_ref"]
                for q in sink_actor["queue"]
            )):
        result["sink_suppression_candidate"] = {
            "queue_slot_ref": sink["queue_slot_ref"],
            "dish_ref": dish_ref,
            "requires": ["EA_NATIVE_AUTONOMY_TEST",
                         "RECHECK_PLAYER_QUEUE",
                         "RECHECK_NANOCAN_AVAILABLE"],
        }
    return finish("NANOCAN_NATIVE_DISPOSAL_CANDIDATE")


def reconcile_nanocan_outcome(receipt: Mapping) -> dict:
    """Verify money and actual disposal with independent causal evidence.

    No reconciliation function writes funds; a positive unrelated balance
    change is not proof of NanoCan recycling revenue.
    """
    if not isinstance(receipt, Mapping) or receipt.get("schema") != OUTCOME_SCHEMA:
        raise NanoCanRecyclingError("NANOCAN_OUTCOME_SCHEMA_INVALID")
    for key in ("proposal_key", "dish_ref", "can_ref", "before_capture_ref",
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
    if (receipt.get("dish_removed_verified") is not True
            or not _ref(receipt.get("disposal_proof_ref"))):
        outcome["state"] = "DISH_DISPOSAL_NOT_PROVED"
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
