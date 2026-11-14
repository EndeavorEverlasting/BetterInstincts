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
    return type(value) in (int, float) and math.isfinite(value)


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
                    observation["sourcing"], capture_ref=capture_ref, now=now
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
