"""Observed fertilizer-supply prerequisite for the existing gardening service.

Pure advisory reducer. It NEVER drags, clicks, purchases, schedules or certifies
an in-game result. The local host supplies independently observed UI affordances
and remains responsible for player/scene/input admission.
"""
from __future__ import annotations

import math
import time
from collections.abc import Mapping

from betterinstincts.eco_resource_cycle import (
    EcoResourceCycleError, plan_fertilizer_sources,
)
from betterinstincts.fertilizer_hover_recognition import (
    FertilizerHoverError, recognize_super_fertilizer_hover,
)

SCHEMA = "betterinstincts.fertilizer-workflow/v1"
MAX_PLANTS = 32
MAX_SUPPLIES = 32
MAX_AGE_SECONDS = 180
LOCATIONS = ("SIM_INVENTORY", "GROUND", "HOUSEHOLD_INVENTORY")
STATES = ("PENDING", "VERIFIED_DONE")
QUALITY_TIERS = ("NORMAL", "NICE", "EXCELLENT", "MAGNIFICENT", "PERFECT")
CONDITIONS = ("GOOD", "LOW", "NONE", "DEPLETED", "UNKNOWN")
NEEDS_TREATMENT = ("DEPLETED", "NONE", "LOW")


class FertilizerWorkflowError(ValueError):
    pass


def _ref(value: object) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= 120 and all(
        c.isalnum() or c in "_:.-" for c in value
    )


def _number(value: object) -> bool:
    if type(value) is int:
        return 0 <= value <= 1_000_000_000_000
    return type(value) is float and math.isfinite(value) and 0 <= value <= 1_000_000_000_000


BACKYARD_SCAN_SCHEMA = "betterinstincts.backyard-fertilizer-scan/v1"
BACKYARD_IDENTITY_SOURCES = {"EA_READ_ONLY", "CALIBRATED_MULTIVIEW", "HOVER_TOOLTIP"}
FERTILIZER_ITEM_KINDS = {"FERTILIZER_BAG", "SUPER_FERTILIZER"}
SPATIAL_POSE_SOURCES = {"EA_READ_ONLY", "CALIBRATED_MULTIVIEW"}
MAX_BACKYARD_BAGS = 32
MAX_ROUTE_STEPS = 64


def _backyard_transfer_candidate(
    scan: Mapping, actions: list[dict], *, sim_ref: str,
    capture_ref: str, now: float,
    expected_lot_ref: str | None, expected_game_build: str | None,
) -> dict:
    """Read a bounded, same-lot bag survey; never move an actual game object.

    A bag-shaped screen blob is insufficient. Require a source-attested item
    identity, on-lot route, personal-inventory destination and an *enabled*
    exact-target transfer affordance in the same current capture.
    """
    base = {
        "gate": "FERTILIZER_BACKYARD_SCAN_REQUIRED",
        "action": "OBSERVE_ALREADY_OWNED_BACKYARD_FERTILIZER_BAGS",
        "next_actions": [],
        "dispatch_authorized": False,
        "proof_ceiling": "OFFLINE_BACKYARD_BAG_ADVICE_NOT_GAME_TRANSFER",
    }
    if not isinstance(scan, Mapping) or scan.get("schema") != BACKYARD_SCAN_SCHEMA:
        raise FertilizerWorkflowError("BACKYARD_SCAN_SCHEMA_INVALID")
    if scan.get("sim_ref") != sim_ref:
        raise FertilizerWorkflowError("BACKYARD_SCAN_ACTOR_MISMATCH")
    if not _ref(scan.get("lot_ref")) or not _ref(scan.get("game_build")):
        raise FertilizerWorkflowError("BACKYARD_SCAN_LOT_OR_BUILD_INVALID")
    if not _ref(expected_lot_ref) or scan["lot_ref"] != expected_lot_ref:
        raise FertilizerWorkflowError("BACKYARD_SCAN_PARENT_LOT_MISMATCH")
    if not _ref(expected_game_build) or scan["game_build"] != expected_game_build:
        raise FertilizerWorkflowError("BACKYARD_SCAN_PARENT_BUILD_MISMATCH")
    bags = scan.get("bags")
    if not isinstance(bags, list) or len(bags) > MAX_BACKYARD_BAGS:
        raise FertilizerWorkflowError("BACKYARD_SCAN_BAGS_INVALID")
    # When the caller has already compiled the canonical semantic spatial
    # map, cross-check discovered bag IDs there instead of trusting a
    # second label-only object list.
    world_map = scan.get("spatial_map")
    if world_map is not None:
        if (not isinstance(world_map, Mapping)
                or world_map.get("schema") != "betterinstincts.semantic-spatial-map-doc/v1"
                or world_map.get("lot_id") != scan["lot_ref"]
                or world_map.get("game_build") != scan["game_build"]
                or world_map.get("execute_allowed") is not False
                or not isinstance(world_map.get("objects"), Mapping)):
            raise FertilizerWorkflowError("BACKYARD_SPATIAL_MAP_SCOPE_INVALID")
    # Validate all current survey identities before choosing any bag.
    ready = []
    hover_reobserve = []
    hover_eligibility = []
    seen = set()
    for bag in bags:
        if not isinstance(bag, Mapping) or not _ref(bag.get("item_ref")):
            raise FertilizerWorkflowError("BACKYARD_BAG_REF_INVALID")
        ref = bag["item_ref"]
        if ref in seen:
            raise FertilizerWorkflowError("BACKYARD_BAG_DUPLICATE")
        seen.add(ref)
        steps = bag.get("route_steps")
        refs = bag.get("identity_evidence_refs")
        if (type(steps) is not int or not 0 <= steps <= MAX_ROUTE_STEPS
                or not isinstance(bag.get("identity_source"), str)
                or bag["identity_source"] not in BACKYARD_IDENTITY_SOURCES
                or not isinstance(refs, list) or not 1 <= len(refs) <= 4
                or any(not _ref(x) for x in refs) or len(set(refs)) != len(refs)
                or (bag.get("identity_source") == "CALIBRATED_MULTIVIEW" and len(refs) < 2)):
            raise FertilizerWorkflowError("BACKYARD_BAG_PROVENANCE_INVALID")
        quantity = bag.get("quantity")
        if type(quantity) is not int or not 0 <= quantity <= 999:
            raise FertilizerWorkflowError("BACKYARD_BAG_STOCK_INVALID")
        # The in-world tooltip is better identification evidence than the
        # apparent shape of a grey bag, but it never supplies ownership,
        # fertilizer eligibility, action authority or a world-space pose.
        if bag.get("identity_source") == "HOVER_TOOLTIP":
            try:
                hover = recognize_super_fertilizer_hover(
                    bag.get("hover_observation"), capture_ref=capture_ref,
                    item_ref=ref,
                )
            except FertilizerHoverError as exc:
                raise FertilizerWorkflowError(str(exc)) from exc
            if not hover["recognized"] or hover["item_kind"] != bag.get("item_kind"):
                continue
            if hover["host_reobservation_required"]:
                hover_reobserve.append(ref)
                continue
            if (bag.get("fertilizer_eligible") is not True
                    or not _ref(bag.get("eligibility_evidence_ref"))):
                hover_eligibility.append(ref)
                continue
        if world_map is not None:
            mapped = world_map["objects"].get(ref)
            if (not isinstance(mapped, Mapping)
                    or not isinstance(mapped.get("category"), str)
                    or mapped["category"] not in FERTILIZER_ITEM_KINDS
                    or mapped.get("floor_id") != "OUTSIDE"
                    or mapped.get("center") is None
                    or not isinstance(mapped.get("pose_source"), str)
                    or mapped["pose_source"] not in SPATIAL_POSE_SOURCES
                    or not isinstance(mapped.get("pose_refs"), list)
                    or not mapped["pose_refs"]):
                continue
        if (not isinstance(bag.get("item_kind"), str)
                or bag["item_kind"] not in FERTILIZER_ITEM_KINDS
                or bag.get("fertilizer_eligible") is not True
                or not _ref(bag.get("eligibility_evidence_ref"))
                or bag.get("location") != "GROUND"
                or bag.get("zone") != "BACKYARD"
                or bag.get("lot_ref") != scan["lot_ref"]
                or bag.get("lot_status") != "VERIFIED_ON_LOT"
                or bag.get("household_owned") is not True
                or bag.get("player_reserved") is not False
                or bag.get("protected") is not False
                or bag.get("route_reachable") is not True
                or not _ref(bag.get("route_evidence_ref"))
                or bag.get("transferable") is not True
                or quantity == 0):
            continue
        ready.append((steps, ref))
    stamp = scan.get("observed_at_unix")
    if (not _number(stamp) or not _number(now)
            or not 0 <= now - stamp <= MAX_AGE_SECONDS
            or scan.get("capture_ref") != capture_ref
            or scan.get("scene_verified") is not True
            or scan.get("active_sim_verified") is not True
            or scan.get("inventory_destination_verified") is not True):
        return {**base, "gate": "FERTILIZER_BACKYARD_REOBSERVE",
                "action": "REOBSERVE_CURRENT_SIM_LOT_BAGS_AND_INVENTORY"}
    transfer = scan.get("pending_transfer")
    if transfer is not None:
        if (not isinstance(transfer, Mapping)
                or not isinstance(transfer.get("status"), str)
                or transfer["status"] not in {"QUEUED", "AWAITING_INVENTORY_READBACK"}
                or not _ref(transfer.get("bag_ref"))
                or transfer.get("sim_ref") != sim_ref
                or transfer.get("lot_ref") != scan["lot_ref"]
                or not _ref(transfer.get("action_ref"))):
            raise FertilizerWorkflowError("BACKYARD_PENDING_TRANSFER_INVALID")
        return {**base, "gate": "FERTILIZER_BACKYARD_TRANSFER_PENDING",
                "action": "WAIT_FOR_EXACT_ITEM_INVENTORY_READBACK_NO_REPEAT"}
    if not ready:
        if hover_reobserve:
            return {**base, "gate": "FERTILIZER_BACKYARD_HOVER_REOBSERVE",
                    "action": "RECONFIRM_TOOLTIP_IN_CURRENT_GAME_HOST",
                    "hover_identity_candidates": hover_reobserve}
        if hover_eligibility:
            return {**base, "gate": "FERTILIZER_BACKYARD_ELIGIBILITY_REQUIRED",
                    "action": "VERIFY_SUPER_FERTILIZER_ITEM_ELIGIBILITY",
                    "hover_identity_candidates": hover_eligibility}
        return {**base, "gate": "FERTILIZER_BACKYARD_BAGS_NOT_FOUND",
                "action": "REINSPECT_ACCESSIBLE_EXISTING_BACKYARD_BAGS"}
    # Existing action envelope comes from gardening_service's fresh affordance
    # filter; do not derive an executable drag route from an item description.
    for _, ref in sorted(ready):
        selected = next((row for row in actions if
                         row.get("action_id") == "TRANSFER_FERTILIZER_TO_SIM_INVENTORY"
                         and row.get("target_ref") == ref
                         and row.get("available") is True
                         and row.get("capture_ref") == capture_ref), None)
        if selected is not None:
            return {**base,
                    "gate": "FERTILIZER_BACKYARD_TRANSFER_READY",
                    "action": "TRANSFER_ONE_EXISTING_BAG_TO_SELECTED_SIM_THEN_REOBSERVE",
                    "next_actions": [{**selected, "item_ref": ref, "quantity": 1,
                                      "source_location": "BACKYARD_GROUND",
                                      "destination_sim_ref": sim_ref}]}
    return {**base, "gate": "FERTILIZER_BACKYARD_TRANSFER_AFFORDANCE_REQUIRED",
            "action": "INSPECT_ENABLED_EXACT_BAG_TO_PERSONAL_INVENTORY_TRANSFER"}


def _plant_quality(observation: Mapping, plants: list, capture_ref: str) -> dict:
    tracking = observation["quality_tracking"]
    if (not isinstance(tracking, Mapping)
            or not _ref(observation.get("lot_ref"))
            or not _ref(tracking.get("household_ref"))
            or tracking.get("lot_ref") != observation["lot_ref"]
            or tracking.get("active_household_verified") is not True
            or tracking.get("capture_ref") != capture_ref
            or type(tracking.get("census_complete")) is not bool):
        raise FertilizerWorkflowError("GARDEN_QUALITY_SCOPE_INVALID")

    rows = []
    for plant in plants:
        status = plant.get("status")
        if (not isinstance(status, Mapping)
                or status.get("capture_ref") != capture_ref
                or status.get("household_ref") != tracking["household_ref"]
                or status.get("lot_ref") != tracking["lot_ref"]
                or status.get("target_ref") != plant["target_ref"]
                or not _ref(status.get("evidence_ref"))):
            raise FertilizerWorkflowError("GARDEN_PLANT_STATUS_PROOF_REQUIRED")
        tier, progress = status.get("quality_tier"), status.get("progress_in_tier")
        water, fertilizer = status.get("water"), status.get("fertilizer")
        if (tier not in (*QUALITY_TIERS, "UNKNOWN")
                or (progress is not None and (not _number(progress) or progress > 1
                                               or tier == "UNKNOWN"))
                or water not in CONDITIONS or fertilizer not in CONDITIONS):
            raise FertilizerWorkflowError("GARDEN_PLANT_STATUS_INVALID")
        rows.append({
            "target_ref": plant["target_ref"], "quality_tier": tier,
            "progress_in_tier": progress, "water": water, "fertilizer": fertilizer,
            "evidence_ref": status["evidence_ref"],
        })
    perfect = sum(row["quality_tier"] == "PERFECT" for row in rows)
    return {
        "household_ref": tracking["household_ref"],
        "lot_ref": tracking["lot_ref"],
        "plants": rows,
        "observed_count": len(rows),
        "perfect_count": perfect,
        "census_complete": tracking["census_complete"],
        "goal_state": ("MAX_QUALITY_OBSERVED"
                       if tracking["census_complete"] and perfect == len(rows)
                       else "CONTINUE_OBSERVING_AND_CARING"),
    }


def _purchase_scope_matches(source: object, workflow: Mapping, household_ref: str) -> bool:
    return (
        isinstance(source, Mapping)
        and source.get("household_ref") == household_ref
        and source.get("lot_ref") == workflow["lot_ref"]
        and source.get("game_build") == workflow["game_build"]
    )



def _batch_matches(observation: Mapping, ready: list[str], capture_ref: str) -> bool:
    batch = observation.get("fertilize_all_scope")
    if (not isinstance(batch, Mapping)
            or batch.get("capture_ref") != capture_ref
            or not _ref(batch.get("evidence_ref"))):
        return False
    targets = batch.get("target_refs")
    return (isinstance(targets, list) and len(targets) == len(ready)
            and all(_ref(ref) for ref in targets) and set(targets) == set(ready))


def _inventory_readback(spec: Mapping, supply_units: Mapping, *, sim_ref: str,
                        lot_ref: str, capture_ref: str) -> bool:
    if (not isinstance(spec, Mapping)
            or spec.get("sim_ref") != sim_ref or spec.get("lot_ref") != lot_ref
            or not _ref(spec.get("item_ref")) or not _ref(spec.get("before_capture_ref"))
            or not _ref(spec.get("action_ref"))
            or type(spec.get("before_units")) is not int
            or not 0 <= spec["before_units"] <= 999
            or type(spec.get("expected_units")) is not int
            or not 1 <= spec["expected_units"] <= MAX_PLANTS
            or spec["before_units"] + spec["expected_units"] > 999):
        raise FertilizerWorkflowError("FERTILIZER_PENDING_ACQUISITION_INVALID")
    return (capture_ref != spec["before_capture_ref"]
            and supply_units.get(spec["item_ref"], 0)
            >= spec["before_units"] + spec["expected_units"])


def evaluate_fertilizer_workflow(
    observation: Mapping,
    actions: list[dict],
    *,
    capture_ref: str,
    now: float | None = None,
    exact_target: str | None = None,
    required_action: str | None = None,
    expected_sim_ref: str | None = None,
) -> dict:
    """Plan at most ONE evidenced transfer or gardening interaction.

    Supply quantities are observed items, not inferred from item labels. The
    completion counter only accepts outcome-backed plant status; a cooldown is
    never completion. Missing evidence fails closed without losing the goal.
    """
    if not isinstance(observation, Mapping) or observation.get("schema") != SCHEMA:
        raise FertilizerWorkflowError("FERTILIZER_WORKFLOW_SCHEMA_INVALID")
    sim_ref = observation.get("sim_ref")
    if not _ref(capture_ref) or not _ref(sim_ref):
        raise FertilizerWorkflowError("FERTILIZER_ACTOR_INVALID")
    if expected_sim_ref is not None and sim_ref != expected_sim_ref:
        raise FertilizerWorkflowError("FERTILIZER_TASK_ACTOR_MISMATCH")
    if exact_target is not None and not _ref(exact_target):
        raise FertilizerWorkflowError("FERTILIZER_TASK_TARGET_INVALID")
    if required_action is not None and required_action not in {"FERTILIZE", "FERTILIZE_ALL"}:
        raise FertilizerWorkflowError("FERTILIZER_TASK_ACTION_INVALID")
    plants = observation.get("plants")
    supplies = observation.get("supplies")
    if not isinstance(plants, list) or not 1 <= len(plants) <= MAX_PLANTS:
        raise FertilizerWorkflowError("FERTILIZER_PLANTS_INVALID")
    if not isinstance(supplies, list) or len(supplies) > MAX_SUPPLIES:
        raise FertilizerWorkflowError("FERTILIZER_SUPPLIES_INVALID")
    if not isinstance(actions, list):
        raise FertilizerWorkflowError("FERTILIZER_ACTIONS_INVALID")

    tracking = "quality_tracking" in observation
    pending, ready, done = [], [], []
    seen: set[str] = set()
    for plant in plants:
        if not isinstance(plant, Mapping) or not _ref(plant.get("target_ref")):
            raise FertilizerWorkflowError("FERTILIZER_PLANT_REF_INVALID")
        ref = plant["target_ref"]
        if ref in seen or plant.get("state") not in STATES:
            raise FertilizerWorkflowError("FERTILIZER_PLANT_STATE_INVALID")
        seen.add(ref)
        if plant["state"] == "VERIFIED_DONE":
            if not _ref(plant.get("outcome_ref")) or not _ref(plant.get("outcome_capture_ref")):
                raise FertilizerWorkflowError("FERTILIZER_OUTCOME_PROOF_REQUIRED")
            done.append(ref)
        else:
            pending.append(ref)
            if plant.get("fertilize_ready") is True:
                ready.append(ref)
    if not tracking and exact_target is not None and exact_target not in pending:
        # The separate task-continuity owner alone can promote completion.
        return {
            "schema": "betterinstincts.fertilizer-result/v1", "gate": "REOBSERVE_TASK_TARGET",
            "action": "VERIFY_TASK_AND_PLANT_LIST", "next_actions": [],
            "pending_targets": pending, "verified_done_targets": done,
            "dispatch_authorized": False,
        }

    pocket_units = {}
    ground = []
    owned_lot_stock_seen = False
    ids: set[str] = set()
    for supply in supplies:
        if not isinstance(supply, Mapping) or not _ref(supply.get("item_ref")):
            raise FertilizerWorkflowError("FERTILIZER_SUPPLY_INVALID")
        sid, qty, location = supply["item_ref"], supply.get("quantity"), supply.get("location")
        if sid in ids or type(qty) is not int or not 0 <= qty <= 999 or location not in LOCATIONS:
            raise FertilizerWorkflowError("FERTILIZER_STOCK_INVALID")
        ids.add(sid)
        if (tracking and location != "SIM_INVENTORY" and qty > 0
                and supply.get("fertilizer_eligible") is True
                and supply.get("lot_ref") == observation.get("lot_ref")
                and supply.get("household_owned") is True):
            owned_lot_stock_seen = True
        if (supply.get("fertilizer_eligible") is True
                and supply.get("protected") is not True
                and supply.get("player_reserved") is not True):
            if location == "SIM_INVENTORY":
                pocket_units[sid] = qty
            elif qty > 0 and supply.get("transferable") is True:
                ground.append(supply)

    stock = sum(pocket_units.values())
    result = {
        "schema": "betterinstincts.fertilizer-result/v1",
        "gate": "INSPECT_FERTILIZER",
        "action": "INSPECT_SUPPLY_AND_PLANT_AFFORDANCES",
        "next_actions": [],
        "sim_ref": sim_ref,
        "capture_ref": capture_ref,
        "pending_targets": pending,
        "ready_targets": ready,
        "verified_done_targets": done,
        "inventory_units": stock,
        "needed_units": len(ready),
        "dispatch_authorized": False,
        "proof_ceiling": "OFFLINE_FERTILIZER_QUEUE_CANDIDATE_NOT_GAME_OUTCOME",
    }

    def finish(gate: str, action: str, selected: dict | None = None) -> dict:
        result.update(gate=gate, action=action)
        if selected is not None:
            result["next_actions"] = [selected]
        return result

    at = time.time() if now is None else now
    stamp = observation.get("observed_at_unix")
    if (
        not _number(at) or not _number(stamp)
        or not 0 <= at - stamp <= MAX_AGE_SECONDS
        or observation.get("capture_ref") != capture_ref
        or observation.get("actor_verified") is not True
        or observation.get("inventory_verified") is not True
    ):
        return finish("REOBSERVE_FERTILIZER", "INSPECT_CURRENT_SIM_POCKET_AND_PLANTS")
    if tracking:
        quality = _plant_quality(observation, plants, capture_ref)
        result["plant_quality"] = quality
        condition = {row["target_ref"]: row["fertilizer"] for row in quality["plants"]}
        # Readiness and current condition are independent. A plant that was
        # fertilized on an earlier turn can need care again.
        pending = sorted(ref for ref in seen if condition[ref] != "GOOD")
        ready = sorted(
            (p["target_ref"] for p in plants
             if (condition[p["target_ref"]] in NEEDS_TREATMENT
                 and p.get("fertilize_ready") is True
                 and exact_target in (None, p["target_ref"]))),
            key=lambda ref: (NEEDS_TREATMENT.index(condition[ref]), ref),
        )
        result.update(pending_targets=pending, ready_targets=ready,
                      verified_done_targets=[ref for ref in done if condition[ref] == "GOOD"],
                      needed_units=len(ready))
        if "pending_acquisition" in observation:
            verified = _inventory_readback(
                observation["pending_acquisition"], pocket_units, sim_ref=sim_ref,
                lot_ref=observation["lot_ref"], capture_ref=capture_ref,
            )
            if not verified:
                return finish("FERTILIZER_ACQUISITION_PENDING",
                              "RECONCILE_EXACT_ITEM_IN_PERSONAL_INVENTORY")
            result["inventory_gain_verified"] = True
    if tracking and exact_target is not None and exact_target not in pending:
        return finish("REOBSERVE_TASK_TARGET", "VERIFY_TASK_AND_PLANT_LIST")
    if not pending:
        if tracking:
            return finish("FERTILIZER_CONDITION_MAINTAINED", "REOBSERVE_PLANT_CARE")
        return finish("FERTILIZER_VERIFIED_COMPLETE", "NO_FURTHER_FERTILIZER_QUEUE")
    if exact_target is not None:
        ready = [ref for ref in ready if ref == exact_target]
        result.update(ready_targets=ready, needed_units=len(ready))
    if not ready:
        if tracking and any(condition[ref] == "UNKNOWN" for ref in pending
                            if exact_target in (None, ref)):
            return finish("FERTILIZER_STATUS_UNKNOWN", "REOBSERVE_EXACT_PLANT_FERTILIZER_STATUS")
        return finish("FERTILIZER_WAIT_ELIGIBILITY", "RECHECK_CURRENT_FERTILIZE_ELIGIBILITY")

    def observed(action_id: str, target_ref: str) -> dict | None:
        return next((dict(row) for row in actions if
                     row.get("action_id") == action_id
                     and row.get("target_ref") == target_ref
                     and row.get("capture_ref") == capture_ref
                     and row.get("available") is True), None)

    def acquisition(candidate: dict, item_ref: str) -> dict:
        if not tracking:
            return candidate
        return {**candidate, "inventory_readback": {
            "sim_ref": sim_ref, "lot_ref": observation["lot_ref"],
            "item_ref": item_ref, "before_capture_ref": capture_ref,
            "before_units": pocket_units.get(item_ref, 0),
            "expected_units": candidate["quantity"],
        }}

    # If the local host supplies a fresh backyard survey, the bought ground
    # bags outrank any new sourcing/purchases. This is an opt-in read-only port;
    # missing/failed proof does not fall through to an unsafe generic drag.
    scan = observation.get("backyard_scan")
    pickup_pending = False
    lot_supply_exhausted = False
    deferred_scan = None
    if scan is not None and stock < len(ready):
        try:
            candidate = _backyard_transfer_candidate(
                scan, actions, sim_ref=sim_ref,
                capture_ref=capture_ref, now=at,
                expected_lot_ref=observation.get("lot_ref"),
                expected_game_build=observation.get("game_build"),
            )
        except FertilizerWorkflowError:
            # Optional malformed/stale discovery may not confiscate
            # independently verified fertilizer already in the Sim's pocket.
            if stock == 0:
                raise
            candidate = None
        if candidate is not None:
            result["backyard_scan"] = candidate
            if candidate["gate"] == "FERTILIZER_BACKYARD_TRANSFER_READY":
                selected = candidate["next_actions"][0]
                return finish(candidate["gate"], candidate["action"],
                              acquisition(selected, selected["item_ref"]))
            if candidate["gate"] == "FERTILIZER_BACKYARD_TRANSFER_PENDING":
                if stock == 0:
                    return finish(candidate["gate"], candidate["action"])
                # One already-held unit remains useful even while a *different*
                # item pickup is queued. Never issue another transfer this turn.
                pickup_pending = True
            if tracking and scan.get("pending_transfer") is not None:
                # Even a stale survey can report an unresolved attempt.
                # Only new inventory evidence can settle that attempt.
                pickup_pending = True
            lot_supply_exhausted = (
                tracking and not pickup_pending and candidate["gate"] == "FERTILIZER_BACKYARD_BAGS_NOT_FOUND"
                and scan.get("lot_coverage_verified") is True
                and scan.get("bags") == []
                and not ground and not owned_lot_stock_seen
            )
            if (stock == 0 and not lot_supply_exhausted
                    and (not tracking
                         or candidate["gate"] != "FERTILIZER_BACKYARD_BAGS_NOT_FOUND")):
                if (not tracking or candidate["gate"] != "FERTILIZER_BACKYARD_REOBSERVE"
                        or scan.get("pending_transfer") is not None):
                    return finish(candidate["gate"], candidate["action"])
                # A stale survey cannot establish absence. A separate current
                # exact-target affordance can still transfer verified stock.
                deferred_scan = candidate
        # With 1+ real inventory units, a failed optional bag scan must not
        # block the existing single-plant FERTILIZE option (not FERTILIZE_ALL).


    # Prefer to prepare enough supply for the currently observed eligible set,
    # rather than repeatedly failing a menu picker while items lie on the floor.
    if (stock < len(ready) and not pickup_pending
            and observation.get("transfer_authorized") is True):
        for item in ground:
            if tracking and (item.get("lot_ref") != observation["lot_ref"]
                             or item.get("household_owned") is not True
                             or item.get("lot_status") != "VERIFIED_ON_LOT"):
                continue
            selected = observed("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", item["item_ref"])
            if selected is not None:
                amount = min(item["quantity"], len(ready) - stock)
                selected["quantity"] = amount
                selected["item_ref"] = item["item_ref"]
                return finish("FERTILIZER_TRANSFER_READY",
                              "TRANSFER_TO_SELECTED_SIM_POCKET_THEN_REOBSERVE",
                              acquisition(selected, item["item_ref"]))
        if ground:
            return finish("INSPECT_TRANSFER_AFFORDANCE", "FIND_EXACT_INVENTORY_DRAG_PATH")
    if deferred_scan is not None:
        return finish(deferred_scan["gate"], deferred_scan["action"])
    sourcing = observation.get("sourcing")
    source_scope_valid = (
        tracking and lot_supply_exhausted
        and _purchase_scope_matches(sourcing, observation, quality["household_ref"])
    )
    if "sourcing" in observation and tracking and lot_supply_exhausted and not source_scope_valid:
        result["source_scope_verified"] = False
        if stock == 0:
            return finish("FERTILIZER_SOURCE_REOBSERVE_SCOPE",
                          "VERIFY_PURCHASE_HOUSEHOLD_LOT_AND_BUILD")
    if ((not tracking and stock == 0 and "sourcing" in observation)
            or (source_scope_valid and stock < len(ready))):
        try:
            source = plan_fertilizer_sources(
                sourcing, capture_ref=capture_ref, now=now,
                expected_sim_ref=sim_ref,
                expected_deficit_units=len(ready) - stock,
                purchase_targets=(
                    {row["target_ref"] for row in actions
                     if row.get("action_id") == "PURCHASE_FERTILIZER"
                     and row.get("capture_ref") == capture_ref
                     and row.get("available") is True} if tracking else None
                ),
            )
        except EcoResourceCycleError as exc:
            raise FertilizerWorkflowError(str(exc)) from exc
        result["source_plan"] = source
        if source["gate"] == "FERTILIZER_SOURCE_READY":
            selected = source["next_actions"][0]
            return finish(
                "FERTILIZER_SOURCE_ACTION_READY",
                "SOURCE_ONE_SAFE_ITEM_THEN_REOBSERVE_POCKET",
                acquisition(selected, selected["item_ref"]) if tracking else selected,
            )
    if stock < 1:
        return finish("FERTILIZER_SUPPLY_REQUIRED", "INSPECT_EXISTING_FERTILIZER_SOURCES")

    # The native batch command is version/pack dependent. It must be ACTUALLY
    # enabled on a current plant and have sufficient personally held supply.
    if (exact_target is None and required_action in (None, "FERTILIZE_ALL")
            and stock >= len(ready)):
        if not tracking or _batch_matches(observation, ready, capture_ref):
            for ref in ready:
                selected = observed("FERTILIZE_ALL", ref)
                if selected is not None:
                    return finish("FERTILIZER_ACTION_READY",
                                  "QUEUE_OBSERVED_FERTILIZE_ALL_THEN_REOBSERVE", selected)
    if required_action == "FERTILIZE_ALL":
        return finish("INSPECT_FERTILIZE_ALL", "RECHECK_BATCH_ELIGIBILITY_AND_SUPPLY")
    for ref in ready:
        selected = observed("FERTILIZE", ref)
        if selected is not None:
            return finish("FERTILIZER_ACTION_READY",
                          "QUEUE_ONE_OBSERVED_FERTILIZE_THEN_REOBSERVE", selected)
    return finish("INSPECT_FERTILIZE_AFFORDANCE", "FIND_ENABLED_PLANT_FERTILIZE_MENU")
