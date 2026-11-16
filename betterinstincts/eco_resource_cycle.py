"""Bounded, observe-first Eco Lifestyle material and fabrication planning.

This policy never buys, queues, clicks, consumes inventory, or reads saves.
EA-native action adapters require exact-patch P08 proof (issue #171).
"""
from __future__ import annotations

import math
import time
from collections import defaultdict
from collections.abc import Mapping

from betterinstincts.build_library_checkpoint import (
    BuildLibraryCheckpointError, admit_live_structure_effect,
)
from betterinstincts.compatibility import VERSION_RE
from betterinstincts.budget_eval import household_reserve
from betterinstincts.funds_inject import MAX_HOUSEHOLD_FUNDS
from betterinstincts.house_state import LOT_ID_RE

MAX_AGE = 180
MAX_ROWS = 48
KINDS = {
    "MANURE", "HARVESTED_PRODUCE", "FISH", "GARDEN_STALL",
    "PLANTER_PURCHASE", "PICKUP", "OTHER_OBSERVED",
}
SOURCE_PRIORITY = {
    "MANURE": 0, "HARVESTED_PRODUCE": 1, "PICKUP": 2,
    "FISH": 3, "GARDEN_STALL": 4, "PLANTER_PURCHASE": 5,
    "OTHER_OBSERVED": 6,
}

SAFE_TRIAL_CLASSES = {
    "TRASH", "SALVAGE_ELECTRONICS", "SALVAGE_MECHANICAL", "SALVAGE_FURNITURE",
    "SURPLUS_BOOK", "SURPLUS_COLLECTIBLE", "ORGANIC_WASTE",
}
ECO_DEBUG_DELTAS = {
    "DEBUG_FABRICATOR_BOTH": {"bits": 50, "pieces": 50},
    "DEBUG_SIM_BITS": {"bits": 500, "pieces": 0},
    "DEBUG_SIM_PIECES": {"bits": 0, "pieces": 500},
}
ECO_DEBUG_MENU = {
    "DEBUG_FABRICATOR_BOTH": ("Give Bits and Pieces",),
    "DEBUG_SIM_BITS": ("Give Bucks", "Recycle Bits"),
    "DEBUG_SIM_PIECES": ("Give Bucks", "Recycle Pieces"),
}
ECO_OPPORTUNITIES = (*ECO_DEBUG_DELTAS, "DIVE_FOR_BITS_AND_PIECES", "RUMMAGE",
                     "DIVE_FOR_DEALS", "USE_COMMUNITY_RECYCLER")


class EcoResourceCycleError(ValueError):
    """Invalid or ambiguous provenance, quantities or resource semantics."""


def _ref(value: object) -> bool:
    return (
        isinstance(value, str) and 1 <= len(value) <= 120
        and all(c.isalnum() or c in "_:.-" for c in value)
    )


def _count(value: object) -> bool:
    return type(value) is int and 0 <= value <= 100000


def _money(value: object) -> bool:
    # Check integer bounds *before* float conversion: very large ints overflow
    # math.isfinite, bypassing the caller's typed error handling.
    if type(value) is int:
        return 0 <= value <= 1_000_000
    return type(value) is float and math.isfinite(value) and 0 <= value <= 1_000_000


def _timestamp(value: object) -> bool:
    # Prevent float/int arithmetic overflow with unbounded external timestamps.
    if type(value) is int:
        return 0 <= value <= 1_000_000_000_000
    return type(value) is float and math.isfinite(value) and 0 <= value <= 1_000_000_000_000


def _rows(value: object, name: str) -> list:
    if not isinstance(value, list) or len(value) > MAX_ROWS:
        raise EcoResourceCycleError(name + "_ROWS_INVALID")
    return value


def _admit(observation: Mapping, schema: str, capture_ref: str, now: float | None) -> str:
    if not isinstance(observation, Mapping) or observation.get("schema") != schema:
        raise EcoResourceCycleError("ECO_OBSERVATION_SCHEMA_INVALID")
    sim = observation.get("sim_ref")
    if not _ref(sim) or not _ref(capture_ref):
        raise EcoResourceCycleError("ECO_ACTOR_OR_CAPTURE_INVALID")
    stamp = observation.get("observed_at_unix")
    at = time.time() if now is None else now
    if (
        not _timestamp(stamp) or not _timestamp(at)
        or not 0 <= at - stamp <= MAX_AGE
        or observation.get("capture_ref") != capture_ref
        or observation.get("scene_verified") is not True
        or observation.get("queue_verified") is not True
    ):
        return "REOBSERVE"
    if observation.get("player_directed") is not False:
        return "PLAYER_FIRST"
    if observation.get("needs_safe") is not True:
        return "NEEDS_FIRST"
    return "READY"


def _receipt(schema: str, capture_ref: str, gate: str, action: str, **kwargs) -> dict:
    return {
        "schema": schema,
        "capture_ref": capture_ref,
        "gate": gate,
        "action": action,
        "next_actions": [],
        "dispatch_authorized": False,
        "proof_ceiling": "OFFLINE_ECO_MATERIAL_ADVISORY_NOT_GAMEPLAY",
        **kwargs,
    }


def plan_fertilizer_sources(
    observation: Mapping, *, capture_ref: str, now: float | None = None,
    expected_sim_ref: str | None = None,
    expected_deficit_units: int | None = None,
    purchase_targets: set[str] | None = None,
) -> dict:
    """Choose one *observed* safe source when the existing pocket is short.

    The existing fertilizer_workflow remains the owner of plant selection,
    transfers, cooldowns and per-plant completion. This port only sources stock.
    """
    state = _admit(observation, "betterinstincts.fertilizer-sourcing/v1",
                   capture_ref, now)
    deficit = observation.get("deficit_units")
    if not _count(deficit):
        raise EcoResourceCycleError("FERTILIZER_DEFICIT_INVALID")
    if expected_sim_ref is not None and observation.get("sim_ref") != expected_sim_ref:
        raise EcoResourceCycleError("FERTILIZER_SOURCE_ACTOR_MISMATCH")
    if expected_deficit_units is not None and deficit != expected_deficit_units:
        raise EcoResourceCycleError("FERTILIZER_SOURCE_DEFICIT_MISMATCH")
    cash, reserve = observation.get("cash"), observation.get("cash_reserve")
    strict_purchase = purchase_targets is not None
    if strict_purchase:
        valid_budget = (
            type(cash) is int and type(reserve) is int
            and 0 <= reserve <= cash <= MAX_HOUSEHOLD_FUNDS
        )
    else:
        valid_budget = _money(cash) and _money(reserve) and reserve <= cash
    if not valid_budget:
        raise EcoResourceCycleError("FERTILIZER_BUDGET_INVALID")
    spendable = cash - reserve
    if strict_purchase:
        spendable = min(spendable, household_reserve(cash)["spend_max"])
    sources = _rows(observation.get("sources"), "FERTILIZER")
    report = _receipt("betterinstincts.fertilizer-source-result/v1",
                      capture_ref, "FERTILIZER_SOURCE_INSPECT",
                      "INSPECT_FERTILIZER_OR_HARVEST_SOURCE",
                      missing_units=deficit, candidates_scanned=len(sources))
    if state != "READY":
        report.update(gate="FERTILIZER_" + state,
                      action="REOBSERVE_SOURCE_AND_PLAYER" if state == "REOBSERVE"
                      else "DEFER_SOURCE_WITH_GOAL_HELD")
        return report
    if deficit == 0:
        report.update(gate="FERTILIZER_SUPPLY_READY",
                      action="RETURN_TO_EXISTING_FERTILIZER_WORKFLOW")
        return report
    candidates = []
    refs = set()
    for row in sources:
        if not isinstance(row, Mapping) or not _ref(row.get("source_ref")):
            raise EcoResourceCycleError("FERTILIZER_SOURCE_REF_INVALID")
        ident = row["source_ref"]
        if ident in refs or not isinstance(row.get("kind"), str) or row["kind"] not in KINDS:
            raise EcoResourceCycleError("FERTILIZER_SOURCE_ID_OR_KIND_INVALID")
        refs.add(ident)
        qty, held = row.get("quantity"), row.get("reserve_quantity")
        value, cost = row.get("unit_opportunity_cost"), row.get("unit_cash_cost")
        if (not _count(qty) or not _count(held) or held > qty
                or not _money(value) or not _money(cost)):
            raise EcoResourceCycleError("FERTILIZER_SOURCE_RESOURCE_INVALID")
        if (row.get("available") is not True or row.get("player_reserved") is not False
                or not _ref(row.get("action_id")) or not _ref(row.get("target_ref"))
                or row.get("capture_ref") != capture_ref
                or qty <= held):
            continue
        if strict_purchase and (
                row.get("kind") not in ("GARDEN_STALL", "PLANTER_PURCHASE")
                or row.get("action_id") != "PURCHASE_FERTILIZER"
                or row["target_ref"] not in purchase_targets
                or not _ref(row.get("item_ref"))
                or row.get("personal_inventory_delivery_verified") is not True
                or observation.get("funds_verified") is not True
                or type(cost) is not int or cost <= 0):
            continue
        take = min(deficit, qty - held)
        if cost:
            if row.get("purchase_reviewed") is not True:
                continue
            # Bounded binary search also handles tiny fractional unit prices
            # without constructing an unbounded float->int quotient.
            lower, upper = 0, take
            while lower < upper:
                mid = (lower + upper + 1) // 2
                if cost * mid <= spendable:
                    lower = mid
                else:
                    upper = mid - 1
            take = lower
        if not take:
            continue
        # Quality replenishment fills as much of the current deficit as
        # possible in one purchase. The original Eco lane is cost-first.
        total_cost = (value + cost) * take
        coverage_priority = -take if strict_purchase else 0
        candidates.append((
            (coverage_priority, total_cost, SOURCE_PRIORITY[row["kind"]], -take, ident),
            row, take,
        ))
    if not candidates:
        report.update(gate="FERTILIZER_SOURCE_UNKNOWN_OR_UNAFFORDABLE",
                      action="INSPECT_SURPLUS_PRODUCE_MANURE_OR_PURCHASE_OPTIONS")
        return report
    _, chosen, take = min(candidates, key=lambda candidate: candidate[0])
    report.update(
        gate="FERTILIZER_SOURCE_READY",
        action="SOURCE_ONE_OBSERVED_FERTILIZER_ITEM_THEN_REOBSERVE",
        next_actions=[{
            "action_id": chosen["action_id"], "target_ref": chosen["target_ref"],
            "source_ref": chosen["source_ref"], "quantity": take,
            "capture_ref": capture_ref,
        }],
        source_kind=chosen["kind"],
        units_planned=take,
    )
    if strict_purchase:
        report["next_actions"][0].update(
            item_ref=chosen["item_ref"], estimated_cash_cost=chosen["unit_cash_cost"] * take,
        )
    return report


def _rank_recycling_trials(observation: Mapping, capture_ref: str) -> list[dict]:
    """Compute evidence-backed yields, never prices-as-yields or fake training."""
    data = _rows(observation.get("recycle_outcomes", []), "RECYCLE_OUTCOMES")
    totals = defaultdict(lambda: [0, 0, 0, 0.0])
    proofs = set()
    capture_pairs = set()
    dispatches = set()
    for row in data:
        if not isinstance(row, Mapping) or not _ref(row.get("source_class")):
            raise EcoResourceCycleError("RECYCLE_OUTCOME_ID_INVALID")
        proof = row.get("outcome_ref")
        if not _ref(proof) or proof in proofs:
            raise EcoResourceCycleError("RECYCLE_OUTCOME_REPLAY")
        proofs.add(proof)
        bits, pieces, cost = row.get("bits_gained"), row.get("pieces_gained"), row.get("consumed_value")
        if not _count(bits) or not _count(pieces) or not _money(cost):
            raise EcoResourceCycleError("RECYCLE_OUTCOME_QUANTITY_INVALID")
        if row.get("player_interrupted") is not False:
            continue
        # Only source-proven outcomes within this patch and actor scope count.
        if (not _ref(observation.get("game_build"))
                or row.get("game_build") != observation["game_build"]
                or row.get("sim_ref") != observation.get("sim_ref")
                or (observation.get("sourcing") is not None and (
                    row.get("household_ref") != observation.get("household_ref")
                    or row.get("method") != "RECYCLER"
                    or row.get("outcome_verified") is not True
                    or not _ref(row.get("dispatch_ref"))))
                or not _ref(row.get("before_ref")) or not _ref(row.get("after_ref"))
                or row["before_ref"] == row["after_ref"]):
            continue
        pair = (row["before_ref"], row["after_ref"])
        if pair in capture_pairs:
            raise EcoResourceCycleError("RECYCLE_OUTCOME_CAPTURE_REPLAY")
        capture_pairs.add(pair)
        if observation.get("sourcing") is not None:
            dispatch = row["dispatch_ref"]
            if dispatch in dispatches:
                raise EcoResourceCycleError("RECYCLE_OUTCOME_DISPATCH_REPLAY")
            dispatches.add(dispatch)
        t = totals[row["source_class"]]
        t[0] += 1
        t[1] += bits
        t[2] += pieces
        t[3] += cost
    return [{
        "source_class": key, "observed_count": value[0],
        "average_bits": value[1] / value[0],
        "average_pieces": value[2] / value[0],
        "average_input_value": value[3] / value[0],
        "decision_grade": value[0] >= 2,
    } for key, value in sorted(totals.items())]


def _sourcing_scope(row, observation, capture_ref):
    return isinstance(row, Mapping) and all(
        row.get(key) == expected for key, expected in (
            ("capture_ref", capture_ref),
            ("household_ref", observation.get("household_ref")),
            ("game_build", observation.get("game_build")),
        )
    )


def _offer(result, gate, action, **parameters):
    result.update(gate=gate, action=action, next_actions=[{
        "action_id": action, "capture_ref": result["capture_ref"], **parameters,
    }])
    return result


def _hold(result, gate, action):
    result.update(gate=gate, action=action)
    return result


def _catalog_stock(sourcing, observation, result, lot_model):
    """Buying a part can satisfy a stock goal only after an inventory readback."""
    capture = result["capture_ref"]
    if sourcing.get("mode") == "LIVE":
        return _hold(result, "ECO_PARTS_STOCK_CATALOG_REVIEW", "REVIEW_ECO_PART_BUILD_BUY_CATALOG")
    if sourcing.get("mode") not in ("BUY", "BUILD"):
        return _hold(result, "ECO_SOURCE_SCOPE_UNVERIFIED", "OBSERVE_BUILD_BUY_CONTEXT")
    if sourcing.get("catalog_purchase_opt_in") is not True:
        return _hold(result, "ECO_PARTS_STOCK_CATALOG_REVIEW", "REVIEW_ECO_PART_PURCHASE_OPT_IN")
    result["catalog_query"] = "Eco-Upgrade Part"
    item = sourcing.get("catalog_part")
    if (not _sourcing_scope(item, observation, capture)
            or item.get("lot_ref") != sourcing["lot_ref"]
            or item.get("definition_id") != "ECO_UPGRADE_PART"
            or item.get("label") != result["catalog_query"]
            or not _ref(item.get("catalog_ref"))
            or item.get("available") is not True):
        if sourcing.get("debug_catalog_opt_in") is True:
            result["catalog_reveal"] = ["testingcheats true", "bb.showhiddenobjects"]
        return _hold(result, "ECO_PARTS_STOCK_CATALOG_REVIEW", "VERIFY_EXACT_DEBUG_CATALOG_LISTING")
    price, funds = item.get("unit_price"), item.get("funds")
    if (type(price) is not int or not 0 < price <= 50 or type(funds) is not int
            or not 0 <= funds <= MAX_HOUSEHOLD_FUNDS
            or price > household_reserve(funds)["spend_max"]):
        return _hold(result, "ECO_PARTS_STOCK_CATALOG_REVIEW", "VERIFY_PRICE_AND_HOUSEHOLD_RESERVE")
    if not isinstance(lot_model, Mapping) or lot_model.get("lot_id") != sourcing.get("lot_ref"):
        return _hold(result, "ECO_PARTS_STOCK_CATALOG_REVIEW", "VERIFY_WHOLE_LOT_BUILD_CHECKPOINT")
    try:
        checkpoint = admit_live_structure_effect(lot_model, "PURCHASE_BUILD_OBJECT")
    except (BuildLibraryCheckpointError, TypeError, ValueError):
        checkpoint = {}
    if checkpoint.get("state") != "LIBRARY_ADMIT":
        return _hold(result, "ECO_PARTS_STOCK_CATALOG_REVIEW", "VERIFY_WHOLE_LOT_BUILD_CHECKPOINT")
    return _offer(
        result, "ECO_PARTS_STOCK_PURCHASE_CANDIDATE", "PURCHASE_ONE_ECO_UPGRADE_PART",
        target_ref=item["catalog_ref"], quantity=1, unit_price=price,
        verify_after="OBSERVE_MATCHING_STOCK_AND_FUNDS_DELTA",
    )


def _alternate_eco_source(sourcing, observation, result, short_bits, short_pieces, *, recycler_ready):
    capture = result["capture_ref"]
    routes = _rows(sourcing.get("opportunities", []), "ECO_SOURCE_OPPORTUNITIES")
    options, seen = {}, set()
    for row in routes:
        if not isinstance(row, Mapping) or not _ref(row.get("opportunity_ref")):
            raise EcoResourceCycleError("ECO_SOURCE_OPPORTUNITY_ID_INVALID")
        ref = row["opportunity_ref"]
        if ref in seen:
            raise EcoResourceCycleError("ECO_SOURCE_OPPORTUNITY_REPLAY")
        seen.add(ref)
        kind = row.get("kind")
        if (kind not in ECO_OPPORTUNITIES or not _sourcing_scope(row, observation, capture)
                or row.get("sim_ref") != observation["sim_ref"]
                or not _ref(row.get("target_ref")) or not _ref(row.get("interaction_ref"))
                or row.get("available") is not True
                or row.get("attempt_state") != "NOT_ATTEMPTED"
                or row.get("lot_ref") != sourcing.get("lot_ref")
                or (kind == "USE_COMMUNITY_RECYCLER" and row.get("free_use_verified") is not True)):
            continue
        options.setdefault(kind, []).append(row)

    natural = ("DIVE_FOR_BITS_AND_PIECES", "RUMMAGE", "DIVE_FOR_DEALS")
    if not recycler_ready:
        natural = ("USE_COMMUNITY_RECYCLER", *natural)
    for kind in natural:
        if kind in options:
            row = min(options[kind], key=lambda item: item["opportunity_ref"])
            return _offer(
                result, "ECO_NATURAL_SOURCE_CANDIDATE", kind,
                target_ref=row["target_ref"], interaction_ref=row["interaction_ref"],
                opportunity_ref=row["opportunity_ref"],
                verify_after="OBSERVE_HOUSEHOLD_BALANCE_AND_SALVAGE_READBACK",
            )
    if (sourcing.get("natural_sources_exhausted") is not True
            or sourcing.get("debug_opt_in") is not True
            or sourcing.get("testingcheats_enabled") is not True):
        return result
    debug = []
    for kind, delta in ECO_DEBUG_DELTAS.items():
        covered = min(short_bits, delta["bits"]) + min(short_pieces, delta["pieces"])
        if covered == 0:
            continue
        for row in options.get(kind, ()):
            menu = row.get("menu_path")
            if (not isinstance(menu, (list, tuple)) or tuple(menu) != ECO_DEBUG_MENU[kind]
                    or (kind != "DEBUG_FABRICATOR_BOTH" and row["target_ref"] != observation["sim_ref"])
                    or (kind == "DEBUG_FABRICATOR_BOTH" and row.get("target_kind") != "HOME_FABRICATOR")):
                continue
            excess = sum(delta.values()) - covered
            debug.append((-covered, excess, row["opportunity_ref"], kind, row))
    if debug:
        _, _, _, kind, row = min(debug)
        return _offer(
            result, "ECO_DEBUG_RESOURCE_CANDIDATE", kind, target_ref=row["target_ref"],
            interaction_ref=row["interaction_ref"], opportunity_ref=row["opportunity_ref"],
            menu_path=list(ECO_DEBUG_MENU[kind]), testingcheats_required=True,
            community_reported_delta=dict(ECO_DEBUG_DELTAS[kind]), training_eligible=False,
            verify_after="REOBSERVE_BOTH_HOUSEHOLD_CURRENCIES_BEFORE_NEXT_STEP",
        )
    return result


def plan_eco_fabrication(
    observation: Mapping, *, capture_ref: str, now: float | None = None,
    lot_model: Mapping | None = None,
) -> dict:
    """Resolve career objective -> recipe -> ingredients -> recyclable input.

    A selected recipe cannot be swapped for a profitable side quest. Recycle
    outcomes improve source-class choices only after independent observations.
    """
    state = _admit(observation, "betterinstincts.eco-fabrication/v1",
                   capture_ref, now)
    sourcing = observation.get("sourcing")
    result = _receipt(
        "betterinstincts.eco-fabrication-result/v1", capture_ref,
        "ECO_CAREER_INSPECT", "INSPECT_CAREER_RECIPE_AND_MATERIALS",
        ranking=[], bits=None, pieces=None, shortfall={"bits": 0, "pieces": 0},
    )
    if state != "READY" and sourcing is not None:
        return _hold(result, "ECO_" + state, "REOBSERVE_OR_YIELD_WITH_GOAL_HELD")
    build = observation.get("game_build")
    if sourcing is not None:
        if (not _ref(build) or not _ref(observation.get("household_ref")) or not VERSION_RE.fullmatch(build)
                or not _sourcing_scope(sourcing, observation, capture_ref)
                or not _ref(sourcing.get("session_ref"))
                or not isinstance(sourcing.get("lot_ref"), str)
                or LOT_ID_RE.fullmatch(sourcing["lot_ref"]) is None
                or sourcing.get("lab_save_verified") is not True
                or sourcing.get("eco_lifestyle") is not True):
            return _hold(result, "ECO_SOURCE_SCOPE_UNVERIFIED", "OBSERVE_MATCHING_HOUSEHOLD_AND_BUILD")
        if sourcing.get("effect_pending") is not False:
            return _hold(result, "ECO_RECONCILE_PREVIOUS_EFFECT", "OBSERVE_PREVIOUS_ATTEMPT_BEFORE_RETRY")
        career_task = observation.get("daily_task") == "FABRICATE_ECO_UPGRADE_PART"
        if sourcing.get("objective") == "STOCK_ECO_UPGRADE_PART" and not career_task:
            if sourcing.get("stock_shortfall_verified") is not True:
                return _hold(result, "ECO_PARTS_STOCK_CATALOG_REVIEW", "VERIFY_ECO_PART_STOCK_SHORTFALL")
            return _catalog_stock(sourcing, observation, result, lot_model)
        if sourcing.get("mode") != "LIVE":
            return _hold(result, "ECO_SOURCE_SCOPE_UNVERIFIED", "OBSERVE_LIVE_FABRICATION_CONTEXT")
        balances = sourcing.get("balances")
        if (not _sourcing_scope(balances, observation, capture_ref)
                or balances.get("source") not in ("HOUSEHOLD_FUNDS_HOVER", "RECYCLER_HOVER", "EA_HOUSEHOLD_READBACK")
                or balances.get("lot_ref") != sourcing["lot_ref"]
                or not _ref(balances.get("evidence_ref"))
                or not all(_count(balances.get(key)) for key in ("bits", "pieces"))):
            return _hold(result, "ECO_OBSERVE_HOUSEHOLD_BALANCE", "READ_BITS_AND_PIECES_FROM_HOUSEHOLD_FUNDS_OR_RECYCLER")
        bits, pieces = balances["bits"], balances["pieces"]
    else:
        bits, pieces = observation.get("bits"), observation.get("pieces")
    skill = observation.get("fabrication_skill")
    if not _count(bits) or not _count(pieces) or type(skill) is not int or not 0 <= skill <= 10:
        raise EcoResourceCycleError("FABRICATION_RESOURCE_OR_SKILL_INVALID")
    recipes = _rows(observation.get("recipes"), "FABRICATION_RECIPES")
    candidates = _rows(observation.get("recyclable_items"), "RECYCLER_ITEMS")
    rankings = _rank_recycling_trials(observation, capture_ref)
    result.update(ranking=rankings, bits=bits, pieces=pieces)
    if state != "READY":
        return _hold(result, "ECO_" + state, "REOBSERVE_OR_YIELD_WITH_GOAL_HELD")
    if not _ref(build):
        return _hold(result, "ECO_BUILD_UNVERIFIED", "INSPECT_EXACT_INSTALLED_PATCH_BEFORE_ECO_ACTION")
    task = observation.get("daily_task")
    if (observation.get("career_track") == "GREEN_TECHNICIAN"
            and task == "FABRICATE_ECO_UPGRADE_PART"):
        task_status = observation.get("daily_task_status")
        if task_status == "COMPLETE":
            result.update(gate="ECO_CAREER_TASK_COMPLETE",
                          action="NO_DUPLICATE_CAREER_FABRICATION")
            return result
        if task_status != "PENDING":
            result.update(gate="ECO_CAREER_TASK_STATUS_UNKNOWN",
                          action="READ_CURRENT_CAREER_PANEL_BEFORE_FABRICATING")
            return result
        target_recipe = "FABRICATED_ECO_UPGRADE_PART"
    else:
        target_recipe = observation.get("goal_recipe_id")
    if not _ref(target_recipe):
        result.update(gate="ECO_GOAL_UNRESOLVED",
                      action="READ_EXACT_DAILY_TASK_OR_PLAYER_CRAFT_GOAL")
        return result
    chosen = None
    recipe_ids = set()
    for row in recipes:
        if not isinstance(row, Mapping) or not _ref(row.get("recipe_id")):
            raise EcoResourceCycleError("FABRICATION_RECIPE_INVALID")
        if row["recipe_id"] in recipe_ids:
            raise EcoResourceCycleError("FABRICATION_DUPLICATE_RECIPE")
        recipe_ids.add(row["recipe_id"])
        rb, rp, unlock = (
            row.get("bits_required"), row.get("pieces_required"),
            row.get("min_skill"),
        )
        if not _count(rb) or not _count(rp) or type(unlock) is not int or not 0 <= unlock <= 10:
            raise EcoResourceCycleError("FABRICATION_RECIPE_COST_INVALID")
        if row["recipe_id"] == target_recipe:
            chosen = row
    if (chosen is None or chosen.get("unlocked") is not True or skill < chosen["min_skill"]
            or (sourcing is not None and (
                not _sourcing_scope(chosen, observation, capture_ref)
                or chosen.get("lot_ref") != sourcing["lot_ref"]))):
        result.update(gate="ECO_RECIPE_LOCKED_OR_UNOBSERVED",
                      action="INSPECT_SKILL_CAREER_RECIPE_UNLOCK")
        return result
    if (sourcing is not None and target_recipe == "FABRICATED_ECO_UPGRADE_PART"
            and (chosen["bits_required"], chosen["pieces_required"]) != (15, 10)):
        return _hold(result, "ECO_RECIPE_COST_MISMATCH", "VERIFY_EXACT_ECO_UPGRADE_PART_RECIPE_COST")
    short_bits = max(0, chosen["bits_required"] - bits)
    short_pieces = max(0, chosen["pieces_required"] - pieces)
    result["shortfall"] = {"bits": short_bits, "pieces": short_pieces}
    result["target_recipe_id"] = target_recipe
    if not short_bits and not short_pieces:
        if (observation.get("fabricator_available") is True
                and chosen.get("available") is True
                and chosen.get("capture_ref") == capture_ref
                and _ref(chosen.get("station_ref"))):
            result.update(
                gate="ECO_FABRICATE_READY",
                action="FABRICATE_EXACT_OBSERVED_RECIPE_THEN_VERIFY_DAILY_TASK",
                next_actions=[{
                    "action_id": "FABRICATE", "recipe_id": target_recipe,
                    "target_ref": chosen["station_ref"], "capture_ref": capture_ref,
                }],
            )
        else:
            result.update(gate="ECO_FABRICATOR_ACCESS_REQUIRED",
                          action="INSPECT_COMMUNITY_FABRICATOR_OR_REVIEW_BUILD_CHECKPOINT")
        if sourcing is not None and result["next_actions"]:
            result["next_actions"][0]["verify_after"] = "OBSERVE_CRAFTED_PART_AND_MATCHING_CAREER_PROGRESS"
        return result
    recycler = sourcing.get("recycler") if sourcing is not None else None
    recycler_ready = observation.get("recycler_available") is True and (
        sourcing is None or (_sourcing_scope(recycler, observation, capture_ref)
            and recycler.get("lot_ref") == sourcing["lot_ref"]
            and recycler.get("available") is True and _ref(recycler.get("target_ref")))
    )
    if not recycler_ready:
        _hold(result, "ECO_RECYCLER_ACCESS_REQUIRED", "INSPECT_COMMUNITY_RECYCLER_BEFORE_PURCHASE")
        if sourcing is not None:
            _alternate_eco_source(
                sourcing, observation, result, short_bits, short_pieces, recycler_ready=recycler_ready
            )
            if sourcing.get("natural_sources_exhausted") is True and not result["next_actions"]:
                result.update(action="REVIEW_HOME_RECYCLER_BUILD_BUY",
                              catalog_query="Guntdach Home Recycler", catalog_reference_price=845,
                              requires_budget_and_whole_lot_checkpoint=True)
        return result
    known = {r["source_class"]: r for r in rankings if r["decision_grade"]}
    viable = []
    seen = set()
    for row in candidates:
        if not isinstance(row, Mapping) or not _ref(row.get("item_ref")):
            raise EcoResourceCycleError("RECYCLER_ITEM_REF_INVALID")
        ref = row["item_ref"]
        if ref in seen or not _ref(row.get("source_class")):
            raise EcoResourceCycleError("RECYCLER_ITEM_REPLAY_OR_CLASS_INVALID")
        seen.add(ref)
        qty, reserve, value = (
            row.get("quantity"), row.get("reserve_quantity"),
            row.get("unit_opportunity_cost"),
        )
        if (not _count(qty) or not _count(reserve) or reserve > qty
                or not _money(value)):
            raise EcoResourceCycleError("RECYCLER_ITEM_QUANTITY_INVALID")
        if (row.get("capture_ref") != capture_ref or row.get("available") is not True
                or row.get("recycle_eligible") is not True
                or row.get("protected") is not False
                or row.get("player_reserved") is not False
                or row.get("required_elsewhere") is not False
                or row.get("unique") is not False or qty <= reserve):
            continue
        empirical = known.get(row["source_class"])
        if sourcing is not None and (
                not _sourcing_scope(row, observation, capture_ref)
                or row.get("inventory_scope") not in ("PERSONAL", "HOUSEHOLD")
                or (row.get("inventory_scope") == "PERSONAL"
                    and row.get("sim_ref") != observation["sim_ref"])
                or row.get("in_current_recycler_picker") is not True
                or row.get("recycler_ref") != recycler["target_ref"]
                or row.get("attempt_state") != "NOT_ATTEMPTED"):
            continue
        # Cash value and item category never imply a yield. Permit an explicit
        # discardable zero-value trial on opted-in observations.
        cold_start = value == 0 and empirical is None and (
            row["source_class"] == "TRASH" if sourcing is None else
            row["source_class"] in SAFE_TRIAL_CLASSES and row.get("discardable_verified") is True
        )
        if empirical is None and not cold_start:
            continue
        if empirical is not None:
            benefit = (min(empirical["average_bits"], short_bits)
                       + min(empirical["average_pieces"], short_pieces))
            if benefit == 0 and sourcing is not None:
                continue
            score = benefit / (1 + value + empirical["average_input_value"])
        else:
            score = 0
        viable.append((-score, not cold_start, value, ref, row, cold_start))
    if not viable:
        _hold(result, "ECO_SAFE_RECYCLABLE_SOURCE_REQUIRED",
              "INSPECT_DISCARDABLE_TRASH_AND_VERIFIED_RECYCLE_YIELDS")
        if sourcing is not None:
            return _alternate_eco_source(
                sourcing, observation, result, short_bits, short_pieces, recycler_ready=recycler_ready
            )
        return result
    _, _, _, _, row, cold_start = min(viable)
    result.update(
        gate="ECO_RECYCLE_CANDIDATE",
        action="RECYCLE_ONE_OBSERVED_ITEM_AND_MEASURE_ACTUAL_BITS_PIECES",
        next_actions=[{
            "action_id": "RECYCLE_ONE", "target_ref": row["item_ref"],
            "item_ref": row["item_ref"], "quantity": 1,
            "capture_ref": capture_ref, "measurement_trial": cold_start,
        }],
        chosen_source_class=row["source_class"],
    )
    if sourcing is not None:
        result["next_actions"][0].update(
            recycler_ref=recycler["target_ref"], inventory_scope=row["inventory_scope"],
            verify_after="OBSERVE_ITEM_CONSUMPTION_AND_HOUSEHOLD_CURRENCY_DELTA",
        )
    return result
