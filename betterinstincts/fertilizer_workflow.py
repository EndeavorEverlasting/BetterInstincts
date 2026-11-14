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

SCHEMA = "betterinstincts.fertilizer-workflow/v1"
MAX_PLANTS = 32
MAX_SUPPLIES = 32
MAX_AGE_SECONDS = 180
LOCATIONS = {"SIM_INVENTORY", "GROUND", "HOUSEHOLD_INVENTORY"}
STATES = {"PENDING", "VERIFIED_DONE"}


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
BACKYARD_IDENTITY_SOURCES = {"EA_READ_ONLY", "CALIBRATED_MULTIVIEW"}
MAX_BACKYARD_BAGS = 32
MAX_ROUTE_STEPS = 64


def _backyard_transfer_candidate(
    scan: Mapping, actions: list[dict], *, sim_ref: str,
    capture_ref: str, now: float,
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
    bags = scan.get("bags")
    if not isinstance(bags, list) or len(bags) > MAX_BACKYARD_BAGS:
        raise FertilizerWorkflowError("BACKYARD_SCAN_BAGS_INVALID")
    # Validate all current survey identities before choosing any bag.
    ready = []
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
                or bag.get("identity_source") not in BACKYARD_IDENTITY_SOURCES
                or not isinstance(refs, list) or not 1 <= len(refs) <= 4
                or any(not _ref(x) for x in refs) or len(set(refs)) != len(refs)
                or (bag.get("identity_source") == "CALIBRATED_MULTIVIEW" and len(refs) < 2)):
            raise FertilizerWorkflowError("BACKYARD_BAG_PROVENANCE_INVALID")
        quantity = bag.get("quantity")
        if type(quantity) is not int or not 0 <= quantity <= 999:
            raise FertilizerWorkflowError("BACKYARD_BAG_STOCK_INVALID")
        if (bag.get("item_kind") != "FERTILIZER_BAG"
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
                or transfer.get("status") not in {"QUEUED", "AWAITING_INVENTORY_READBACK"}
                or not _ref(transfer.get("bag_ref"))
                or transfer.get("sim_ref") != sim_ref
                or transfer.get("lot_ref") != scan["lot_ref"]
                or not _ref(transfer.get("action_ref"))):
            raise FertilizerWorkflowError("BACKYARD_PENDING_TRANSFER_INVALID")
        return {**base, "gate": "FERTILIZER_BACKYARD_TRANSFER_PENDING",
                "action": "WAIT_FOR_EXACT_ITEM_INVENTORY_READBACK_NO_REPEAT"}
    if not ready:
        return {**base, "gate": "FERTILIZER_BACKYARD_BAGS_NOT_FOUND",
                "action": "REINSPECT_ACCESSIBLE_EXISTING_BACKYARD_BAGS"}
    # Existing action envelope comes from gardening_service's fresh affordance
    # filter; do not derive an executable drag route from an item description.
    for _, ref in sorted(ready):
        selected = next((row for row in actions if
                         row.get("action_id") == "TRANSFER_FERTILIZER_TO_SIM_INVENTORY"
                         and row.get("target_ref") == ref
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
    if exact_target is not None and exact_target not in pending:
        # The separate task-continuity owner alone can promote completion.
        return {
            "schema": "betterinstincts.fertilizer-result/v1", "gate": "REOBSERVE_TASK_TARGET",
            "action": "VERIFY_TASK_AND_PLANT_LIST", "next_actions": [],
            "pending_targets": pending, "verified_done_targets": done,
            "dispatch_authorized": False,
        }

    stock = 0
    ground = []
    ids: set[str] = set()
    for supply in supplies:
        if not isinstance(supply, Mapping) or not _ref(supply.get("item_ref")):
            raise FertilizerWorkflowError("FERTILIZER_SUPPLY_INVALID")
        sid, qty, location = supply["item_ref"], supply.get("quantity"), supply.get("location")
        if sid in ids or type(qty) is not int or not 0 <= qty <= 999 or location not in LOCATIONS:
            raise FertilizerWorkflowError("FERTILIZER_STOCK_INVALID")
        ids.add(sid)
        if supply.get("fertilizer_eligible") is True and supply.get("protected") is not True:
            if location == "SIM_INVENTORY":
                stock += qty
            elif qty > 0 and supply.get("transferable") is True:
                ground.append(supply)

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
    if not pending:
        return finish("FERTILIZER_VERIFIED_COMPLETE", "NO_FURTHER_FERTILIZER_QUEUE")
    if exact_target is not None:
        ready = [ref for ref in ready if ref == exact_target]
    if not ready:
        return finish("FERTILIZER_WAIT_ELIGIBILITY", "RECHECK_AFTER_OBSERVED_COOLDOWN")

    def observed(action_id: str, target_ref: str) -> dict | None:
        return next((dict(row) for row in actions if
                     row.get("action_id") == action_id
                     and row.get("target_ref") == target_ref
                     and row.get("capture_ref") == capture_ref), None)

    # If the local host supplies a fresh backyard survey, the bought ground
    # bags outrank any new sourcing/purchases. This is an opt-in read-only port;
    # missing/failed proof does not fall through to an unsafe generic drag.
    if "backyard_scan" in observation:
        candidate = _backyard_transfer_candidate(
            observation["backyard_scan"], actions, sim_ref=sim_ref,
            capture_ref=capture_ref, now=at,
        )
        result["backyard_scan"] = candidate
        if candidate["gate"] == "FERTILIZER_BACKYARD_TRANSFER_PENDING":
            return finish(candidate["gate"], candidate["action"])
        if stock < len(ready):
            return finish(candidate["gate"], candidate["action"],
                          candidate["next_actions"][0] if candidate["next_actions"] else None)

    # Prefer to prepare enough supply for the currently observed eligible set,
    # rather than repeatedly failing a menu picker while items lie on the floor.
    if stock < len(ready) and observation.get("transfer_authorized") is True:
        for item in ground:
            selected = observed("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", item["item_ref"])
            if selected is not None:
                amount = min(item["quantity"], len(ready) - stock)
                selected["quantity"] = amount
                selected["item_ref"] = item["item_ref"]
                return finish("FERTILIZER_TRANSFER_READY",
                              "TRANSFER_TO_SELECTED_SIM_POCKET_THEN_REOBSERVE", selected)
        if ground:
            return finish("INSPECT_TRANSFER_AFFORDANCE", "FIND_EXACT_INVENTORY_DRAG_PATH")
    if stock < 1:
        if "sourcing" in observation:
            try:
                source = plan_fertilizer_sources(
                    observation["sourcing"], capture_ref=capture_ref, now=now,
                    expected_sim_ref=sim_ref,
                    expected_deficit_units=len(ready) - stock,
                )
            except EcoResourceCycleError as exc:
                raise FertilizerWorkflowError(str(exc)) from exc
            result["source_plan"] = source
            if source["gate"] == "FERTILIZER_SOURCE_READY":
                return finish(
                    "FERTILIZER_SOURCE_ACTION_READY",
                    "SOURCE_ONE_SAFE_ITEM_THEN_REOBSERVE_POCKET",
                    source["next_actions"][0],
                )
        return finish("FERTILIZER_SUPPLY_REQUIRED", "INSPECT_EXISTING_FERTILIZER_SOURCES")

    # The native batch command is version/pack dependent. It must be ACTUALLY
    # enabled on a current plant and have sufficient personally held supply.
    if exact_target is None and required_action in (None, "FERTILIZE_ALL") and stock >= len(ready):
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
