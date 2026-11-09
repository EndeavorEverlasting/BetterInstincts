import time
import unittest

from betterinstincts.selected_sim_continuity import (
    SelectedSimContinuityError, evaluate_selected_sim_goal,
)
from betterinstincts.gardening_service import evaluate_gardening_turn
from betterinstincts.need_services import evaluate_need_services

NOW = time.time()
CAP = "capture:current"
NEEDS = dict(hunger=.9, bladder=.9, energy=.9, hygiene=.9, fun=.9, social=.9)


def task(**kw):
    row = dict(
        schema="betterinstincts.task-continuity/v1",
        goal_id="goal:plants", sim_ref="sim:tim", action_id="FERTILIZE",
        player_command_ref="cmd:player", capture_ref=CAP,
        observed_at_unix=NOW, queue_verified=True, queue=[],
        targets=[{"target_ref":"plant:1", "state":"PENDING"},
                 {"target_ref":"plant:2", "state":"PENDING"}])
    row.update(kw)
    return row


def selection(**kw):
    row = dict(schema="betterinstincts.selected-sim-observation/v1",
               selected_sim_ref="sim:tim", selection_verified=True,
               selection_proof_ref="evidence:portrait", capture_ref=CAP,
               observed_at_unix=NOW)
    row.update(kw)
    return row


class SelectedSimTests(unittest.TestCase):
    def call(self, t=None, s=None):
        return evaluate_selected_sim_goal(
            t if t is not None else task(),
            s if s is not None else selection(), capture_ref=CAP, now=NOW)

    def test_selected_current_goal_plans_exact_target(self):
        r = self.call()
        self.assertEqual(r["gate"], "SELECTED_SIM_GOAL_EVALUATED")
        self.assertEqual(r["task_continuity"]["next_target_ref"], "plant:1")
        self.assertFalse(r["execute_allowed"])

    def test_offscreen_preserves_all_targets_and_never_assumes_queue_survived(self):
        r = self.call(s=selection(selected_sim_ref="sim:alex"))
        self.assertEqual(r["gate"], "SIM_NOT_SELECTED")
        self.assertEqual(r["task_continuity"]["pending_targets"], ["plant:1", "plant:2"])
        self.assertFalse(r["cancel_allowed"])

    def test_reselect_requires_fresh_actor_and_queue_proof(self):
        for t,s in [
            (task(observed_at_unix=NOW-181),selection()),
            (task(capture_ref="capture:old"),selection()),
            (task(),selection(selection_verified=False)),
            (task(),selection(capture_ref="capture:old")),
            (task(),selection(observed_at_unix=NOW-181)),
            (task(),selection(selection_proof_ref=None)),
        ]:
            with self.subTest(t=t,s=s):
                self.assertEqual(self.call(t,s)["gate"], "REOBSERVE_SELECTED_SIM")

    def test_gardening_host_composition_yields_offscreen(self):
        ctx = dict(
            capture_ref=CAP, observed_at_unix=NOW, scene_verified=True,
            queue_verified=True, responsibilities_checked=True,
            no_upcoming_obligation=True,
            observed_actions=[dict(action_id="FERTILIZE",label="Fertilize",
                                   target_ref="plant:1",capture_ref=CAP,available=True)],
            task_continuity=task(),
            selected_sim_observation=selection(selected_sim_ref="sim:alex"))
        report = evaluate_need_services(NEEDS,capture_ref=CAP)
        out = evaluate_gardening_turn(NEEDS,report,ctx,capture_ref=CAP,now=NOW)
        self.assertEqual(out["gate"], "GARDEN_SIM_NOT_SELECTED")
        self.assertEqual(out["next_actions"], [])
        self.assertFalse(out["dispatch_authorized"])
        ctx["selected_sim_observation"]=selection()
        self.assertEqual(evaluate_gardening_turn(NEEDS,report,ctx,capture_ref=CAP,now=NOW)["gate"],
                         "GARDEN_ACTION_READY")

    def test_explicit_cancel_or_verified_completion_survives_portrait_switch(self):
        canceled = task(player_override={
            "kind": "CANCEL_GOAL", "proof_ref": "proof:player-cancel"})
        self.assertEqual(self.call(canceled, selection(selected_sim_ref="sim:alex"))["gate"],
                         "PLAYER_GOAL_SUPERSEDED")
        done = task(targets=[{
            "target_ref": "plant:1", "state": "VERIFIED_DONE",
            "outcome_ref": "proof:completed", "outcome_capture_ref": "capture:verified"}])
        self.assertEqual(self.call(done, selection(selected_sim_ref="sim:alex"))["gate"],
                         "TASK_VERIFIED_COMPLETE")
        ctx = dict(
            capture_ref=CAP, observed_at_unix=NOW, scene_verified=True,
            queue_verified=True, responsibilities_checked=True,
            no_upcoming_obligation=True, observed_actions=[],
            task_continuity=canceled,
            selected_sim_observation=selection(selected_sim_ref="sim:alex"))
        report = evaluate_need_services(NEEDS, capture_ref=CAP)
        r = evaluate_gardening_turn(NEEDS, report, ctx, capture_ref=CAP, now=NOW)
        self.assertEqual(r["goal_state"], "SUPERSEDED")
        self.assertEqual(r["next_actions"], [])
        self.assertEqual(r["gate"], "GARDEN_PLAYER_FIRST")

    def test_invalid_selection_is_rejected(self):
        with self.assertRaises(SelectedSimContinuityError):
            self.call(s={"schema":"wrong"})


if __name__=="__main__":
    unittest.main()
