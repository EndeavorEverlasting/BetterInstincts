"""Falsifiers for the opt-in gardening fertilizer pocket and queue seam."""
import copy
import time
import unittest

from betterinstincts.fertilizer_workflow import (
    FertilizerWorkflowError, evaluate_fertilizer_workflow,
)
from betterinstincts.gardening_service import evaluate_gardening_turn
from betterinstincts.need_services import evaluate_need_services

CAPTURE = "capture:fert"
NEEDS = dict(hunger=.95, energy=.95, fun=.95, social=.95, bladder=.95, hygiene=.95)


def act(action_id, target):
    return {"action_id": action_id, "target_ref": target, "capture_ref": CAPTURE,
            "available": True, "label": action_id}


def plant(ref="plant:a", *, state="PENDING", ready=True):
    row = {"target_ref": ref, "state": state, "fertilize_ready": ready}
    if state == "VERIFIED_DONE":
        row.update(outcome_ref="outcome:observed", outcome_capture_ref="capture:proof")
    return row


def supply(ref="item:a", location="SIM_INVENTORY", qty=1, **extra):
    return {"item_ref": ref, "location": location, "quantity": qty,
            "fertilizer_eligible": True, **extra}


def workflow(**changes):
    row = {"schema": "betterinstincts.fertilizer-workflow/v1",
           "capture_ref": CAPTURE, "observed_at_unix": time.time(),
           "sim_ref": "sim:garden", "actor_verified": True, "inventory_verified": True,
           "lot_ref": "lot:home", "game_build": "build:verified",
           "transfer_authorized": False, "plants": [plant()],
           "supplies": [supply()]}
    row.update(changes)
    return row


def evaluate(w, a, **kwargs):
    return evaluate_fertilizer_workflow(w, a, capture_ref=CAPTURE, **kwargs)


def garden_context(w, a, **extra):
    ctx = {
        "capture_ref": CAPTURE, "observed_at_unix": time.time(),
        "scene_verified": True, "queue_verified": True,
        "responsibilities_checked": True, "minutes_until_obligation": 120,
        "observed_actions": a, "fertilizer_workflow": w,
    }
    ctx.update(extra)
    return ctx


def run_garden(ctx, *, needs=None, **kwargs):
    n = NEEDS if needs is None else needs
    report = evaluate_need_services(n, available_objects=["bed"], capture_ref=CAPTURE)
    return evaluate_gardening_turn(n, report, ctx, capture_ref=CAPTURE, **kwargs)


class FertilizerWorkflowTests(unittest.TestCase):
    def test_pocket_stock_selects_exact_plant_not_ground(self):
        w = workflow()
        original = copy.deepcopy(w)
        out = evaluate(w, [act("FERTILIZE", "plant:a")])
        self.assertEqual(out["gate"], "FERTILIZER_ACTION_READY")
        self.assertEqual(out["next_actions"][0]["target_ref"], "plant:a")
        self.assertEqual(w, original)
        self.assertFalse(out["dispatch_authorized"])

    def test_ground_stock_not_falsely_consumed(self):
        out = evaluate(workflow(supplies=[
            supply(location="GROUND", qty=7, transferable=True)]),
            [act("FERTILIZE", "plant:a")])
        self.assertEqual(out["gate"], "FERTILIZER_SUPPLY_REQUIRED")
        self.assertFalse(out["next_actions"])

    def test_authorized_ground_transfer_precedes_fertilization(self):
        out = evaluate(workflow(transfer_authorized=True, plants=[
            plant("plant:a"), plant("plant:b"), plant("plant:c")],
            supplies=[supply(location="GROUND", qty=2, transferable=True)]),
            [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:a"),
             act("FERTILIZE", "plant:a")])
        self.assertEqual(out["gate"], "FERTILIZER_TRANSFER_READY")
        self.assertEqual(out["next_actions"][0]["quantity"], 2)
        self.assertEqual(out["next_actions"][0]["item_ref"], "item:a")
        self.assertEqual(out["inventory_units"], 0)
        self.assertEqual(out["needed_units"], 3)

    def test_transfer_requires_current_observed_affordance(self):
        out = evaluate(workflow(transfer_authorized=True,
            supplies=[supply(location="GROUND", qty=2, transferable=True)]),
            [act("FERTILIZE", "plant:a")])
        self.assertEqual(out["gate"], "INSPECT_TRANSFER_AFFORDANCE")
        self.assertFalse(out["next_actions"])

    def test_ground_item_protected_or_ineligible_cannot_transfer(self):
        for changes in ({"protected": True}, {"fertilizer_eligible": False},
                        {"transferable": False}):
            with self.subTest(changes=changes):
                out = evaluate(workflow(transfer_authorized=True,
                    supplies=[supply(location="GROUND", qty=2,
                                     **({"transferable": True} | changes))]),
                    [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:a")])
                self.assertEqual(out["gate"], "FERTILIZER_SUPPLY_REQUIRED")

    def test_native_batch_only_when_observed_and_stock_covers_all_ready(self):
        w = workflow(plants=[plant("plant:a"), plant("plant:b")],
                     supplies=[supply(qty=2)])
        out = evaluate(w, [act("FERTILIZE_ALL", "plant:a"),
                           act("FERTILIZE", "plant:a")])
        self.assertEqual(out["next_actions"][0]["action_id"], "FERTILIZE_ALL")
        out = evaluate(workflow(plants=w["plants"], supplies=[supply(qty=1)]),
                       [act("FERTILIZE_ALL", "plant:a"),
                        act("FERTILIZE", "plant:a")])
        self.assertEqual(out["next_actions"][0]["action_id"], "FERTILIZE")
        self.assertEqual(len(out["next_actions"]), 1)

    def test_batch_never_inferred_from_version_or_missing_menu(self):
        out = evaluate(workflow(plants=[plant("plant:a"), plant("plant:b")],
            supplies=[supply(qty=5)]), [act("FERTILIZE", "plant:b")])
        self.assertEqual(out["next_actions"][0]["action_id"], "FERTILIZE")
        self.assertEqual(out["next_actions"][0]["target_ref"], "plant:b")

    def test_ready_false_is_cooldown_not_completion(self):
        out = evaluate(workflow(plants=[plant(ready=False)]),
                       [act("FERTILIZE", "plant:a")])
        self.assertEqual(out["gate"], "FERTILIZER_WAIT_ELIGIBILITY")
        self.assertEqual(out["pending_targets"], ["plant:a"])
        self.assertEqual(out["verified_done_targets"], [])

    def test_verified_done_requires_real_outcome_references(self):
        out = evaluate(workflow(plants=[plant(state="VERIFIED_DONE")]), [])
        self.assertEqual(out["gate"], "FERTILIZER_VERIFIED_COMPLETE")
        with self.assertRaisesRegex(FertilizerWorkflowError, "OUTCOME_PROOF"):
            evaluate(workflow(plants=[{"target_ref":"plant:a",
                    "state":"VERIFIED_DONE"}]), [])

    def test_stale_or_wrong_actor_or_inventory_fails_closed(self):
        for change in ({"capture_ref":"capture:old"},
                       {"actor_verified":False}, {"inventory_verified":False},
                       {"observed_at_unix":time.time()-181}):
            with self.subTest(change=change):
                out = evaluate(workflow(**change), [act("FERTILIZE", "plant:a")])
                self.assertEqual(out["gate"], "REOBSERVE_FERTILIZER")
                self.assertFalse(out["next_actions"])

    def test_exact_task_resumption_never_retargets_other_plant(self):
        w = workflow(plants=[plant("plant:a"), plant("plant:b")],
                     supplies=[supply(qty=2)])
        out = evaluate(w, [act("FERTILIZE", "plant:b")],
                       exact_target="plant:a", required_action="FERTILIZE",
                       expected_sim_ref="sim:garden")
        self.assertEqual(out["gate"], "INSPECT_FERTILIZE_AFFORDANCE")
        with self.assertRaisesRegex(FertilizerWorkflowError, "ACTOR_MISMATCH"):
            evaluate(w, [], expected_sim_ref="sim:other")

    def test_invalid_quantities_lists_and_duplicates_fail_closed(self):
        for change in ({"supplies":[supply(qty=True)]},
                       {"supplies":[supply(qty=-1)]},
                       {"supplies":[supply(), supply()]},
                       {"plants":[plant(), plant()]},
                       {"plants":[plant("plant:%d"%i) for i in range(33)]}):
            with self.subTest(change=str(change)[:25]), self.assertRaises(FertilizerWorkflowError):
                evaluate(workflow(**change), [])

    def test_host_gardening_composes_supply_before_action(self):
        w = workflow(supplies=[supply(location="GROUND", qty=3, transferable=True)],
                     transfer_authorized=True)
        ctx = garden_context(w, [
            act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:a"),
            act("FERTILIZE", "plant:a")])
        out = run_garden(ctx)
        self.assertEqual(out["gate"], "GARDEN_ACTION_READY")
        self.assertEqual(out["next_actions"][0]["quantity"], 1)
        self.assertFalse(out["dispatch_authorized"])

    def test_player_school_needs_and_manual_busy_win(self):
        ctx = garden_context(workflow(), [act("FERTILIZE", "plant:a")])
        self.assertEqual(run_garden(ctx, player_directed=True)["gate"], "GARDEN_PLAYER_FIRST")
        self.assertEqual(run_garden(ctx, already_busy=True)["next_actions"], [])
        self.assertEqual(run_garden(ctx, homework_pending=True)["gate"], "GARDEN_RESPONSIBILITY_FIRST")
        low = {**NEEDS, "energy": .01}
        self.assertEqual(run_garden(ctx, needs=low)["gate"], "GARDEN_INSPECT_NEED_ACTIONS")

    def test_fertilizer_cooldown_allows_garden_maintenance_without_goal_loss(self):
        ctx = garden_context(
            workflow(plants=[plant(ready=False)]),
            [act("WATER", "plant:a"), act("TEND_GARDEN", "plant:a")],
        )
        out = run_garden(ctx)
        self.assertEqual(out["gate"], "GARDEN_ACTION_READY")
        self.assertEqual(out["next_actions"][0]["action_id"], "WATER")
        self.assertEqual(out["goal_state"], "PENDING")
        self.assertEqual(out["fertilizer_workflow"]["pending_targets"], ["plant:a"])

    def test_missing_stock_allows_evolve_or_weed_but_not_side_quest(self):
        w = workflow(supplies=[supply(location="GROUND", qty=4)])
        ctx = garden_context(w, [act("EVOLVE", "plant:a"),
                                 act("CHAT_WITH_NEIGHBOR", "sim:other")])
        out = run_garden(ctx)
        self.assertEqual(out["next_actions"][0]["action_id"], "EVOLVE")
        self.assertEqual(out["goal_state"], "PENDING")
        out = run_garden(garden_context(w, [act("CHAT_WITH_NEIGHBOR", "sim:other")]))
        self.assertEqual(out["gate"], "GARDEN_FERTILIZER_SUPPLY_REQUIRED")
        self.assertFalse(out["next_actions"])

    def test_exact_player_fertilization_task_is_not_replaced_with_other_care(self):
        task = {
            "schema": "betterinstincts.task-continuity/v1",
            "goal_id": "goal:fertilize", "sim_ref": "sim:garden",
            "action_id": "FERTILIZE", "player_command_ref": "player:command",
            "targets": [{"target_ref": "plant:a", "state": "PENDING"}],
            "capture_ref": CAPTURE, "observed_at_unix": time.time(),
            "queue_verified": True, "queue": [],
        }
        ctx = garden_context(workflow(supplies=[
            supply(location="GROUND", qty=1)]),
            [act("WATER", "plant:a")], task_continuity=task)
        out = run_garden(ctx)
        self.assertEqual(out["gate"], "GARDEN_FERTILIZER_SUPPLY_REQUIRED")
        self.assertEqual(out["next_actions"], [])
        self.assertEqual(out["goal_state"], "PENDING")

    def test_no_workflow_keeps_legacy_gardening_behavior(self):
        ctx = garden_context(workflow(), [act("FERTILIZE", "plant:a")])
        del ctx["fertilizer_workflow"]
        out = run_garden(ctx)
        self.assertEqual(out["gate"], "GARDEN_ACTION_READY")
        self.assertEqual(out["next_actions"][0]["action_id"], "FERTILIZE")



def backyard_bag(ref="item:bag", **changes):
    row = {
        "item_ref": ref, "item_kind": "FERTILIZER_BAG",
        "identity_source": "EA_READ_ONLY", "identity_evidence_refs": ["ea:tgi"],
        "fertilizer_eligible": True, "eligibility_evidence_ref": "ea:fertilizer",
        "quantity": 1, "location": "GROUND", "zone": "BACKYARD",
        "lot_ref": "lot:home", "lot_status": "VERIFIED_ON_LOT",
        "household_owned": True, "player_reserved": False, "protected": False,
        "route_reachable": True, "route_evidence_ref": "route:verified",
        "route_steps": 3, "transferable": True,
    }
    row.update(changes)
    return row


def super_hover(ref="item:bag", source="HOST_VERIFIED_HOVER", **changes):
    row = {
        "schema": "betterinstincts.fertilizer-hover/v1", "source": source,
        "capture_ref": CAPTURE, "pointer_target_ref": ref,
        "highlighted_target_ref": ref, "tooltip_attached_to_target": True,
        "title": "SUPER FERTILIZER",
        "description": "Special fertilizer received from Jasmine as part of the Growfruit Challenge.",
        "displayed_value": "§80",
    }
    row.update(changes)
    return row


def backyard_scan(**changes):
    row = {
        "schema": "betterinstincts.backyard-fertilizer-scan/v1",
        "sim_ref": "sim:garden", "lot_ref": "lot:home",
        "game_build": "build:verified", "capture_ref": CAPTURE,
        "observed_at_unix": time.time(), "scene_verified": True,
        "active_sim_verified": True, "inventory_destination_verified": True,
        "bags": [backyard_bag()],
    }
    row.update(changes)
    return row


class BackyardFertilizerBagTests(unittest.TestCase):
    def test_hover_identified_super_fertilizer_goes_to_sim_only_with_current_host_proof(self):
        bag = backyard_bag(
            item_kind="SUPER_FERTILIZER", identity_source="HOVER_TOOLTIP",
            identity_evidence_refs=[CAPTURE], hover_observation=super_hover())
        out = evaluate(
            workflow(supplies=[], backyard_scan=backyard_scan(bags=[bag])),
            [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")])
        self.assertEqual(out["gate"], "FERTILIZER_BACKYARD_TRANSFER_READY")
        self.assertEqual(out["next_actions"][0]["destination_sim_ref"], "sim:garden")
        self.assertEqual(out["inventory_units"], 0)
        self.assertFalse(out["dispatch_authorized"])
        self.assertFalse(out["next_actions"][0].get("purchase", False))

    def test_uploaded_screenshot_identifies_bag_but_cannot_grant_transfer(self):
        bag = backyard_bag(
            item_kind="SUPER_FERTILIZER", identity_source="HOVER_TOOLTIP",
            identity_evidence_refs=[CAPTURE],
            hover_observation=super_hover(source="USER_SCREENSHOT"))
        out = evaluate(
            workflow(supplies=[], backyard_scan=backyard_scan(bags=[bag])),
            [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")])
        self.assertEqual(out["gate"], "FERTILIZER_BACKYARD_HOVER_REOBSERVE")
        self.assertEqual(out["backyard_scan"]["hover_identity_candidates"], ["item:bag"])
        self.assertFalse(out["next_actions"])

    def test_host_hover_requires_independent_fertilizer_eligibility(self):
        bag = backyard_bag(
            item_kind="SUPER_FERTILIZER", identity_source="HOVER_TOOLTIP",
            identity_evidence_refs=[CAPTURE], hover_observation=super_hover(),
            fertilizer_eligible=None, eligibility_evidence_ref=None)
        out = evaluate(
            workflow(supplies=[], backyard_scan=backyard_scan(bags=[bag])),
            [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")])
        self.assertEqual(out["gate"], "FERTILIZER_BACKYARD_ELIGIBILITY_REQUIRED")
        self.assertFalse(out["next_actions"])

    def test_wrong_hover_target_or_false_tooltip_does_not_transfer(self):
        bag = backyard_bag(
            item_kind="SUPER_FERTILIZER", identity_source="HOVER_TOOLTIP",
            identity_evidence_refs=[CAPTURE],
            hover_observation=super_hover(pointer_target_ref="item:other"))
        with self.assertRaisesRegex(FertilizerWorkflowError, "HOVER_TARGET_UNBOUND"):
            evaluate(workflow(supplies=[], backyard_scan=backyard_scan(bags=[bag])),
                     [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")])
        bag["hover_observation"] = super_hover(title="FERTILIZER BAG")
        out = evaluate(workflow(supplies=[], backyard_scan=backyard_scan(bags=[bag])),
                       [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")])
        self.assertEqual(out["gate"], "FERTILIZER_BACKYARD_BAGS_NOT_FOUND")
        self.assertFalse(out["next_actions"])

    def test_known_super_fertilizer_optional_world_map_can_confirm_source_class(self):
        bag = backyard_bag(
            item_kind="SUPER_FERTILIZER", identity_source="HOVER_TOOLTIP",
            identity_evidence_refs=[CAPTURE], hover_observation=super_hover())
        world = {
            "schema": "betterinstincts.semantic-spatial-map-doc/v1",
            "lot_id": "lot:home", "game_build": "build:verified",
            "execute_allowed": False, "objects": {
                "item:bag": {
                    "category": "SUPER_FERTILIZER", "floor_id": "OUTSIDE",
                    "center": [1, 2, 0], "size": [1, 1, 1],
                    "pose_source": "EA_READ_ONLY", "pose_refs": ["ea:pose"],
                },
            },
        }
        out = evaluate(workflow(supplies=[], backyard_scan=backyard_scan(
            bags=[bag], spatial_map=world)),
            [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")])
        self.assertEqual(out["gate"], "FERTILIZER_BACKYARD_TRANSFER_READY")
        world["objects"]["item:bag"]["category"] = "UNKNOWN_OBJECT"
        out = evaluate(workflow(supplies=[], backyard_scan=backyard_scan(
            bags=[bag], spatial_map=world)),
            [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")])
        self.assertEqual(out["gate"], "FERTILIZER_BACKYARD_BAGS_NOT_FOUND")

    def test_gardening_service_preserves_enabled_flag_without_admitting_disabled(self):
        row = act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")
        w = workflow(supplies=[], backyard_scan=backyard_scan())
        enabled = run_garden(garden_context(w, [row]))
        self.assertEqual(enabled["gate"], "GARDEN_ACTION_READY")
        self.assertIs(enabled["next_actions"][0]["available"], True)
        disabled = dict(row, available=False)
        rejected = run_garden(garden_context(w, [disabled]))
        self.assertNotEqual(rejected["gate"], "GARDEN_ACTION_READY")
        self.assertFalse(rejected["next_actions"])

    def test_current_transfer_action_must_be_enabled_not_just_named(self):
        action = act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")
        action["available"] = False
        out = evaluate(workflow(supplies=[], backyard_scan=backyard_scan()),
                       [action])
        self.assertEqual(out["gate"], "FERTILIZER_BACKYARD_TRANSFER_AFFORDANCE_REQUIRED")
        self.assertFalse(out["next_actions"])

    def test_full_pocket_outweighs_malformed_or_pending_optional_scan(self):
        for scan in ("invalid", backyard_scan(sim_ref="sim:other"),
                     backyard_scan(pending_transfer={
                         "status": "QUEUED", "bag_ref": "item:bag",
                         "sim_ref": "sim:garden", "lot_ref": "lot:home",
                         "action_ref": "queue:pending",
                     })):
            with self.subTest(scan=str(scan)[:30]):
                out = evaluate(workflow(supplies=[supply(qty=2)],
                               plants=[plant("plant:a"), plant("plant:b")],
                               backyard_scan=scan),
                               [act("FERTILIZE", "plant:a")])
                self.assertEqual(out["gate"], "FERTILIZER_ACTION_READY")
                self.assertEqual(out["next_actions"][0]["action_id"], "FERTILIZE")
                self.assertNotIn("backyard_scan", out)

    def test_partial_pocket_still_fertilizes_one_when_backyard_unavailable(self):
        row = workflow(supplies=[supply(qty=1)], plants=[
            plant("plant:a"), plant("plant:b")],
            backyard_scan=backyard_scan(bags=[]))
        out = evaluate(row, [act("FERTILIZE", "plant:a"),
                             act("FERTILIZE_ALL", "plant:a")])
        self.assertEqual(out["gate"], "FERTILIZER_ACTION_READY")
        self.assertEqual(out["next_actions"][0]["action_id"], "FERTILIZE")
        self.assertEqual(out["inventory_units"], 1)
        self.assertEqual(out["needed_units"], 2)
        self.assertFalse(out["dispatch_authorized"])

    def test_partial_pocket_does_not_fail_from_unusable_optional_scan(self):
        row = workflow(supplies=[supply(qty=1)], plants=[
            plant("plant:a"), plant("plant:b")],
            backyard_scan=backyard_scan(sim_ref="sim:other"))
        out = evaluate(row, [act("FERTILIZE", "plant:a")])
        self.assertEqual(out["gate"], "FERTILIZER_ACTION_READY")
        self.assertEqual(out["next_actions"][0]["target_ref"], "plant:a")

    def test_distinct_followup_capture_reports_real_pocket_not_transfer_imagination(self):
        first = evaluate(workflow(supplies=[], backyard_scan=backyard_scan()),
                         [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")])
        new_ref = "capture:after"
        latest = workflow(capture_ref=new_ref, supplies=[supply("item:bag",
                         location="SIM_INVENTORY", qty=1)],
                         backyard_scan=backyard_scan(capture_ref="capture:old"))
        action = act("FERTILIZE", "plant:a")
        action["capture_ref"] = new_ref
        later = evaluate_fertilizer_workflow(
            latest, [action], capture_ref=new_ref)
        self.assertNotEqual(first["capture_ref"], later["capture_ref"])
        self.assertEqual(later["inventory_units"], 1)
        self.assertEqual(later["gate"], "FERTILIZER_ACTION_READY")
        self.assertEqual(later["verified_done_targets"], [])

    def test_discovered_owned_bag_to_selected_sim_inventory_is_one_proposal(self):
        w = workflow(supplies=[], backyard_scan=backyard_scan())
        original = copy.deepcopy(w)
        out = evaluate(w, [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")])
        self.assertEqual(out["gate"], "FERTILIZER_BACKYARD_TRANSFER_READY")
        self.assertEqual(len(out["next_actions"]), 1)
        self.assertEqual(out["next_actions"][0]["item_ref"], "item:bag")
        self.assertEqual(out["next_actions"][0]["destination_sim_ref"], "sim:garden")
        self.assertEqual(out["next_actions"][0]["quantity"], 1)
        self.assertEqual(out["inventory_units"], 0)
        self.assertFalse(out["dispatch_authorized"])
        self.assertEqual(w, original)

    def test_prefer_nearest_proven_reachable_bag_not_first_or_cheapest_purchase(self):
        survey = backyard_scan(bags=[
            backyard_bag("item:far", route_steps=13),
            backyard_bag("item:near", route_steps=2),
            backyard_bag("item:offlot", lot_ref="lot:neighbor", route_steps=1),
        ])
        out = evaluate(workflow(supplies=[], backyard_scan=survey,
                                sourcing={"schema": "fake:purchase"}),
                       [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:far"),
                        act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:near")])
        self.assertEqual(out["next_actions"][0]["item_ref"], "item:near")
        self.assertEqual(out["gate"], "FERTILIZER_BACKYARD_TRANSFER_READY")
        self.assertNotIn("source_plan", out)

    def test_two_step_readback_then_exact_plant_without_false_success(self):
        first = evaluate(workflow(supplies=[], backyard_scan=backyard_scan()),
                         [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")])
        self.assertEqual(first["inventory_units"], 0)
        self.assertEqual(first["verified_done_targets"], [])
        pending = backyard_scan(pending_transfer={
            "status": "AWAITING_INVENTORY_READBACK", "bag_ref": "item:bag",
            "sim_ref": "sim:garden", "lot_ref": "lot:home",
            "action_ref": "queue:pickup",
        })
        second = evaluate(workflow(supplies=[], backyard_scan=pending),
                          [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")])
        self.assertEqual(second["gate"], "FERTILIZER_BACKYARD_TRANSFER_PENDING")
        self.assertFalse(second["next_actions"])
        # Only an independently observed pocket stock in a subsequent capture
        # can satisfy the existing plant picker; transfer proposal never counts.
        after = "capture:after-transfer"
        new_capture = backyard_scan(bags=[], capture_ref=after)
        new_state = workflow(capture_ref=after,
                             supplies=[supply("item:bag", qty=1)],
                             backyard_scan=new_capture)
        new_action = act("FERTILIZE", "plant:a")
        new_action["capture_ref"] = after
        third = evaluate_fertilizer_workflow(
            new_state, [new_action], capture_ref=after)
        self.assertNotEqual(first["capture_ref"], third["capture_ref"])
        self.assertEqual(third["gate"], "FERTILIZER_ACTION_READY")
        self.assertEqual(third["next_actions"][0]["target_ref"], "plant:a")
        self.assertEqual(third["verified_done_targets"], [])

    def test_stock_readback_fertilizes_despite_stale_backyard_survey(self):
        # Once the selected Sim actually holds the item, only the newly
        # observed plant affordance matters; old backyard surveys are stale.
        out = evaluate(workflow(supplies=[supply("item:bag", qty=1)],
                       backyard_scan=backyard_scan(capture_ref="capture:old")),
                       [act("FERTILIZE", "plant:a")])
        self.assertEqual(out["gate"], "FERTILIZER_ACTION_READY")
        self.assertEqual(out["next_actions"][0]["action_id"], "FERTILIZE")
        self.assertEqual(out["next_actions"][0]["target_ref"], "plant:a")
        self.assertNotIn("backyard_scan", out)

    def test_parent_lot_and_game_build_must_match_backyard_survey(self):
        for parent in ({"lot_ref": "lot:other"},
                       {"game_build": "build:other"},
                       {"game_build": None}, {"lot_ref": None}):
            with self.subTest(parent=parent), self.assertRaisesRegex(
                    FertilizerWorkflowError, "BACKYARD_SCAN_PARENT"):
                evaluate(workflow(supplies=[], backyard_scan=backyard_scan(), **parent),
                         [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")])

    def test_registered_semantic_spatial_map_confirms_physical_bag_identity(self):
        world = {
            "schema": "betterinstincts.semantic-spatial-map-doc/v1",
            "lot_id": "lot:home", "game_build": "build:verified",
            "execute_allowed": False,
            "objects": {
                "item:bag": {
                    "category": "FERTILIZER_BAG", "floor_id": "OUTSIDE",
                    "pose_source": "EA_READ_ONLY", "pose_refs": ["ea:pose"],
                    "center": [1, 2, 0], "size": [1, 1, 1],
                },
                "item:chair": {
                    "category": "CHAIR", "floor_id": "OUTSIDE",
                    "pose_source": "EA_READ_ONLY", "pose_refs": ["ea:chair"],
                    "center": [3, 4, 0], "size": [1, 1, 1],
                },
            }, "relations": [],
        }
        observed = [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")]
        accepted = evaluate(workflow(supplies=[], backyard_scan=backyard_scan(
            spatial_map=world)), observed)
        self.assertEqual(accepted["gate"], "FERTILIZER_BACKYARD_TRANSFER_READY")
        for bad_row in (
            {"category": "UNKNOWN_OBJECT"},
            {"floor_id": "FLOOR_1"},
            {"center": None},
            {"pose_source": "NONE"},
        ):
            with self.subTest(bad_row=bad_row):
                modified = copy.deepcopy(world)
                modified["objects"]["item:bag"].update(bad_row)
                denied = evaluate(workflow(supplies=[], backyard_scan=backyard_scan(
                    spatial_map=modified)), observed)
                self.assertEqual(denied["gate"], "FERTILIZER_BACKYARD_BAGS_NOT_FOUND")
                self.assertFalse(denied["next_actions"])
        with self.assertRaisesRegex(FertilizerWorkflowError, "SPATIAL_MAP_SCOPE"):
            evaluate(workflow(supplies=[], backyard_scan=backyard_scan(
                spatial_map={**world, "lot_id": "lot:unrelated"})), observed)

    def test_partial_pocket_pending_transfer_uses_one_plant_without_second_pickup(self):
        pending = backyard_scan(pending_transfer={
            "status": "QUEUED", "bag_ref": "item:bag",
            "sim_ref": "sim:garden", "lot_ref": "lot:home",
            "action_ref": "queue:inflight",
        })
        row = workflow(
            plants=[plant("plant:a"), plant("plant:b")],
            supplies=[supply("item:held", qty=1),
                      supply("item:ground", location="GROUND", qty=2, transferable=True)],
            transfer_authorized=True, backyard_scan=pending,
        )
        result = evaluate(row, [
            act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag"),
            act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:ground"),
            act("FERTILIZE_ALL", "plant:a"), act("FERTILIZE", "plant:a"),
        ])
        self.assertEqual(result["gate"], "FERTILIZER_ACTION_READY")
        self.assertEqual(len(result["next_actions"]), 1)
        self.assertEqual(result["next_actions"][0]["action_id"], "FERTILIZE")
        self.assertEqual(result["backyard_scan"]["gate"], "FERTILIZER_BACKYARD_TRANSFER_PENDING")
        self.assertEqual(result["inventory_units"], 1)
        self.assertFalse(result["dispatch_authorized"])
        empty = evaluate(workflow(supplies=[], backyard_scan=pending), [
            act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")])
        self.assertEqual(empty["gate"], "FERTILIZER_BACKYARD_TRANSFER_PENDING")
        self.assertFalse(empty["next_actions"])

    def test_external_unhashable_bag_fields_never_escape_typed_refusal(self):
        for field in ("identity_source", "pending_transfer"):
            with self.subTest(field=field), self.assertRaises(FertilizerWorkflowError):
                if field == "identity_source":
                    scan = backyard_scan(bags=[backyard_bag(identity_source=[])])
                else:
                    scan = backyard_scan(pending_transfer={
                        "status": [], "bag_ref": "item:bag",
                        "sim_ref": "sim:garden", "lot_ref": "lot:home",
                        "action_ref": "queue:pending",
                    })
                evaluate(workflow(supplies=[], backyard_scan=scan),
                         [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")])
        for field in ("item_kind", "category", "pose_source"):
            with self.subTest(field=field):
                bag = backyard_bag()
                scan = backyard_scan(bags=[bag])
                if field == "item_kind":
                    bag[field] = []
                else:
                    scan["spatial_map"] = {
                        "schema": "betterinstincts.semantic-spatial-map-doc/v1",
                        "lot_id": "lot:home", "game_build": "build:verified",
                        "execute_allowed": False,
                        "objects": {"item:bag": {
                            "category": "FERTILIZER_BAG", "floor_id": "OUTSIDE",
                            "pose_source": "EA_READ_ONLY", "pose_refs": ["ea:pose"],
                            "center": [1, 2, 0],
                        }},
                    }
                    scan["spatial_map"]["objects"]["item:bag"][field] = []
                out = evaluate(workflow(supplies=[], backyard_scan=scan),
                               [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")])
                self.assertEqual(out["gate"], "FERTILIZER_BACKYARD_BAGS_NOT_FOUND")
                self.assertFalse(out["next_actions"])

    def test_no_requeue_if_pickup_in_flight(self):
        for status in ("QUEUED", "AWAITING_INVENTORY_READBACK"):
            with self.subTest(status=status):
                scan = backyard_scan(pending_transfer={
                    "status": status, "bag_ref": "item:bag",
                    "sim_ref": "sim:garden", "lot_ref": "lot:home",
                    "action_ref": "queue:itembag",
                })
                out = evaluate(workflow(supplies=[], backyard_scan=scan),
                               [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")])
                self.assertEqual(out["gate"], "FERTILIZER_BACKYARD_TRANSFER_PENDING")
                self.assertFalse(out["next_actions"])

    def test_missing_current_transfer_affordance_does_not_guess_drag(self):
        out = evaluate(workflow(supplies=[], backyard_scan=backyard_scan()),
                       [act("FERTILIZE", "plant:a")])
        self.assertEqual(out["gate"], "FERTILIZER_BACKYARD_TRANSFER_AFFORDANCE_REQUIRED")
        self.assertFalse(out["next_actions"])

    def test_unverified_bag_and_wrong_lot_or_owner_are_ignored(self):
        mutations = [
            {"item_kind": "SEED_PACKET"}, {"fertilizer_eligible": False},
            {"location": "HOUSEHOLD_INVENTORY"}, {"lot_ref": "lot:other"},
            {"lot_status": "UNKNOWN"}, {"household_owned": False},
            {"player_reserved": True}, {"protected": True},
            {"route_reachable": False}, {"transferable": False}, {"quantity": 0},
            {"zone": "STREET"},
        ]
        for changes in mutations:
            with self.subTest(changes=changes):
                bag = backyard_bag(**changes)
                out = evaluate(workflow(supplies=[], backyard_scan=backyard_scan(bags=[bag])),
                               [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")])
                self.assertEqual(out["gate"], "FERTILIZER_BACKYARD_BAGS_NOT_FOUND")
                self.assertFalse(out["next_actions"])

    def test_stale_or_wrong_actor_scan_refuses_supply(self):
        for changes in (
            {"capture_ref": "capture:old"},
            {"observed_at_unix": time.time() - 190},
            {"scene_verified": False},
            {"active_sim_verified": False},
            {"inventory_destination_verified": False},
        ):
            with self.subTest(changes=changes):
                out = evaluate(workflow(supplies=[], backyard_scan=backyard_scan(**changes)),
                               [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")])
                self.assertEqual(out["gate"], "FERTILIZER_BACKYARD_REOBSERVE")
                self.assertFalse(out["next_actions"])
        with self.assertRaisesRegex(FertilizerWorkflowError, "ACTOR_MISMATCH"):
            evaluate(workflow(supplies=[], backyard_scan=backyard_scan(sim_ref="sim:other")),
                     [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")])

    def test_identity_and_route_must_have_independent_proof(self):
        invalid = [
            {"identity_source": "SCREEN_LABEL"}, {"identity_evidence_refs": []},
            {"identity_evidence_refs": ["ea:one", "ea:one"]},
            {"identity_source": "CALIBRATED_MULTIVIEW", "identity_evidence_refs": ["view:one"]},
            {"route_steps": True}, {"route_steps": -1}, {"route_steps": 65},
            {"quantity": True}, {"quantity": -1},
        ]
        for changes in invalid:
            with self.subTest(changes=changes), self.assertRaises(FertilizerWorkflowError):
                evaluate(workflow(supplies=[], backyard_scan=backyard_scan(
                    bags=[backyard_bag(**changes)])),
                    [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")])

    def test_duplicate_bag_id_and_invalid_pending_transfer_denied(self):
        for bad_scan in (
            backyard_scan(bags=[backyard_bag(), backyard_bag()]),
            backyard_scan(pending_transfer={"status": "QUEUED", "bag_ref": "item:bag",
                "sim_ref": "sim:other", "lot_ref": "lot:home", "action_ref": "queue:x"}),
        ):
            with self.assertRaises(FertilizerWorkflowError):
                evaluate(workflow(supplies=[], backyard_scan=bad_scan),
                         [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")])

    def test_player_and_needs_priority_remain_above_backyard(self):
        ctx = garden_context(workflow(supplies=[], backyard_scan=backyard_scan()),
                             [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")])
        out = run_garden(ctx)
        self.assertEqual(out["gate"], "GARDEN_ACTION_READY")
        self.assertEqual(out["next_actions"][0]["item_ref"], "item:bag")
        self.assertFalse(out["dispatch_authorized"])
        self.assertEqual(run_garden(ctx, player_directed=True)["gate"], "GARDEN_PLAYER_FIRST")
        self.assertFalse(run_garden(ctx, already_busy=True)["next_actions"])
        self.assertEqual(run_garden(ctx, needs={**NEEDS, "hunger": .02})["gate"],
                         "GARDEN_INSPECT_NEED_ACTIONS")

    def test_exact_player_target_and_no_finished_or_cooling_plant(self):
        w = workflow(supplies=[], plants=[plant("plant:a"), plant("plant:b")],
                     backyard_scan=backyard_scan())
        out = evaluate(w, [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")],
                       exact_target="plant:b", required_action="FERTILIZE",
                       expected_sim_ref="sim:garden")
        self.assertEqual(out["gate"], "FERTILIZER_BACKYARD_TRANSFER_READY")
        completed = evaluate(workflow(supplies=[], plants=[plant(state="VERIFIED_DONE")],
                        backyard_scan=backyard_scan()),
                        [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")])
        self.assertEqual(completed["gate"], "FERTILIZER_VERIFIED_COMPLETE")
        cooling = evaluate(workflow(supplies=[], plants=[plant(ready=False)],
                      backyard_scan=backyard_scan()),
                      [act("TRANSFER_FERTILIZER_TO_SIM_INVENTORY", "item:bag")])
        self.assertEqual(cooling["gate"], "FERTILIZER_WAIT_ELIGIBILITY")



if __name__ == "__main__":
    unittest.main()
