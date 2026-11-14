"""Bounded, observe-first Eco Lifestyle material and fabrication planning.

This policy never buys, queues, clicks, consumes inventory, or reads saves.
EA-native action adapters require exact-patch P08 proof (issue #171).
"""
from __future__ import annotations

import math
import time
from collections import defaultdict
from collections.abc import Mapping

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
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1000000


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
        type(stamp) not in (int, float) or not math.isfinite(stamp)
        or type(at) not in (int, float) or not math.isfinite(at)
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
    observation: Mapping, *, capture_ref: str, now: float | None = None
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
    cash, reserve = observation.get("cash"), observation.get("cash_reserve")
    if not _money(cash) or not _money(reserve) or reserve > cash:
        raise EcoResourceCycleError("FERTILIZER_BUDGET_INVALID")
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
        if ident in refs or row.get("kind") not in KINDS:
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
        take = min(deficit, qty - held)
        if cost * take > cash - reserve:
            continue
        if cost and row.get("purchase_reviewed") is not True:
            continue
        # Prefer verified zero-cost surplus and low opportunity-cost sources.
        candidates.append((
            SOURCE_PRIORITY[row["kind"]], value * take + cost * take,
            ident, row, take,
        ))
    if not candidates:
        report.update(gate="FERTILIZER_SOURCE_UNKNOWN_OR_UNAFFORDABLE",
                      action="INSPECT_SURPLUS_PRODUCE_MANURE_OR_PURCHASE_OPTIONS")
        return report
    _, _, _, chosen, take = min(candidates, key=lambda v: v[:3])
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
    return report


def _rank_recycling_trials(observation: Mapping, capture_ref: str) -> list[dict]:
    """Compute evidence-backed yields, never prices-as-yields or fake training."""
    data = _rows(observation.get("recycle_outcomes", []), "RECYCLE_OUTCOMES")
    totals = defaultdict(lambda: [0, 0, 0, 0.0])
    proofs = set()
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
        if (row.get("game_build") != observation.get("game_build")
                or row.get("sim_ref") != observation.get("sim_ref")
                or not _ref(row.get("before_ref")) or not _ref(row.get("after_ref"))
                or row["before_ref"] == row["after_ref"]):
            continue
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


def plan_eco_fabrication(
    observation: Mapping, *, capture_ref: str, now: float | None = None
) -> dict:
    """Resolve career objective -> recipe -> ingredients -> recyclable input.

    A selected recipe cannot be swapped for a profitable side quest. Recycle
    outcomes improve source-class choices only after independent observations.
    """
    state = _admit(observation, "betterinstincts.eco-fabrication/v1",
                   capture_ref, now)
    bits, pieces, skill = (
        observation.get("bits"), observation.get("pieces"),
        observation.get("fabrication_skill"),
    )
    if not _count(bits) or not _count(pieces) or type(skill) is not int or not 0 <= skill <= 10:
        raise EcoResourceCycleError("FABRICATION_RESOURCE_OR_SKILL_INVALID")
    recipes = _rows(observation.get("recipes"), "FABRICATION_RECIPES")
    candidates = _rows(observation.get("recyclable_items"), "RECYCLER_ITEMS")
    rankings = _rank_recycling_trials(observation, capture_ref)
    result = _receipt(
        "betterinstincts.eco-fabrication-result/v1", capture_ref,
        "ECO_CAREER_INSPECT", "INSPECT_CAREER_RECIPE_AND_MATERIALS",
        ranking=rankings, bits=bits, pieces=pieces,
        shortfall={"bits": 0, "pieces": 0},
    )
    if state != "READY":
        result.update(gate="ECO_" + state, action="REOBSERVE_OR_YIELD_WITH_GOAL_HELD")
        return result
    task = observation.get("daily_task")
    if (observation.get("career_track") == "GREEN_TECHNICIAN"
            and task == "FABRICATE_ECO_UPGRADE_PART"):
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
    if chosen is None or chosen.get("unlocked") is not True or skill < chosen["min_skill"]:
        result.update(gate="ECO_RECIPE_LOCKED_OR_UNOBSERVED",
                      action="INSPECT_SKILL_CAREER_RECIPE_UNLOCK")
        return result
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
        return result
    if observation.get("recycler_available") is not True:
        result.update(gate="ECO_RECYCLER_ACCESS_REQUIRED",
                      action="INSPECT_COMMUNITY_RECYCLER_BEFORE_PURCHASE")
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
        # Explicitly low-cost trash is the only cold-start trial; no guesses
        # about yields of valuable or unmeasured inventory objects.
        cold_start = row["source_class"] == "TRASH" and value == 0 and empirical is None
        if empirical is None and not cold_start:
            continue
        if empirical is not None:
            benefit = (min(empirical["average_bits"], short_bits)
                       + min(empirical["average_pieces"], short_pieces))
            score = benefit / (1 + value + empirical["average_input_value"])
        else:
            score = 0
        viable.append((-score, not cold_start, value, ref, row, cold_start))
    if not viable:
        result.update(gate="ECO_SAFE_RECYCLABLE_SOURCE_REQUIRED",
                      action="INSPECT_DISCARDABLE_TRASH_AND_VERIFIED_RECYCLE_YIELDS")
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
    return result
