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


if __name__ == "__main__":
    unittest.main()
