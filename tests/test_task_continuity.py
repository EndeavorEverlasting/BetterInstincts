import copy
import time
import unittest

from betterinstincts.task_continuity import (
    TaskContinuityError, evaluate_task_continuity,
)
from betterinstincts.gardening_service import evaluate_gardening_turn
from betterinstincts.need_services import evaluate_need_services
from betterinstincts.host_stack import evaluate_turn

CAPTURE = "capture:tim-garden"
NOW = 1794245000.0
NEEDS = dict(hunger=.9, bladder=.9, energy=.9, hygiene=.9, fun=.9, social=.9)


def task(**changes):
    row = {
        "schema": "betterinstincts.task-continuity/v1",
        "goal_id": "goal:fertilize-all", "sim_ref": "sim:tim",
        "action_id": "FERTILIZE", "player_command_ref": "command:user-1",
        "capture_ref": CAPTURE, "observed_at_unix": NOW,
        "queue_verified": True, "queue": [],
        "targets": [
            {"target_ref": "plant:1", "state": "VERIFIED_DONE",
             "outcome_ref": "receipt:plant-1", "outcome_capture_ref": "capture:previous"},
            {"target_ref": "plant:2", "state": "PENDING"},
            {"target_ref": "plant:3", "state": "IN_PROGRESS"},
        ],
    }
    row.update(changes)
    return row


def queue_row(action="CHAT", target="sim:visitor", origin="SIM_AUTONOMY", proof="event:autonomy-1", **changes):
    row = dict(action_id=action, target_ref=target, origin=origin,
               origin_proof_ref=proof, capture_ref=CAPTURE, sim_ref="sim:tim")
    row.update(changes)
    return row


def garden(task_row, *, actions=None, **changes):
    ctx = {
        "capture_ref": CAPTURE, "observed_at_unix": time.time(),
        "scene_verified": True, "queue_verified": True,
        "responsibilities_checked": True,
        "minutes_until_obligation": 120,
        "observed_actions": actions if actions is not None else [
            dict(action_id="FERTILIZE", label="Fertilize",
                 target_ref="plant:2", capture_ref=CAPTURE, available=True)],
        "task_continuity": {**task_row, "observed_at_unix": time.time()},
    }
    ctx.update(changes)
    return ctx


class TaskContinuityTests(unittest.TestCase):
    def check(self, record=None):
        return evaluate_task_continuity(record or task(), capture_ref=CAPTURE, now=NOW)

    def test_partial_completion_resumes_first_unfinished_target(self):
        x = self.check()
        self.assertEqual(x["gate"], "TASK_RESUME_CANDIDATE")
        self.assertEqual(x["next_target_ref"], "plant:2")
        self.assertEqual(x["verified_done_count"], 1)
        self.assertEqual(x["pending_targets"], ["plant:2", "plant:3"])
        self.assertFalse(x["execute_allowed"])
        self.assertFalse(x["cancel_allowed"])

    def test_autonomous_chat_preserves_goal_and_never_grants_cancel(self):
        x = self.check(task(queue=[queue_row()]))
        self.assertEqual(x["gate"], "AUTONOMOUS_TASK_INTERRUPTION")
        self.assertEqual(x["state"], "INTERRUPTED")
        self.assertEqual(x["next_target_ref"], "plant:2")
        self.assertFalse(x["cancel_allowed"])

    def test_existing_queued_fertilization_not_duplicated(self):
        x = self.check(task(queue=[
            queue_row("CHAT"),
            queue_row("FERTILIZE", "plant:2", "PLAYER", "command:user-1"),
        ]))
        self.assertEqual(x["gate"], "TASK_ALREADY_QUEUED")
        self.assertEqual(x["state"], "IN_PROGRESS")

    def test_player_override_and_new_player_queue_yield(self):
        self.assertEqual(self.check(task(player_override={
            "kind": "CANCEL_GOAL", "proof_ref": "event:player-cancel",
        }))["state"], "SUPERSEDED")
        self.assertEqual(self.check(task(queue=[
            queue_row("CHAT", origin="PLAYER", proof="event:player-chat"),
        ]))["gate"], "PLAYER_CHANGED_QUEUE")

    def test_unproven_origin_stale_queue_and_cross_sim_fail_closed(self):
        cases = [
            task(queue=[queue_row(proof=None)]),
            task(queue=[queue_row(capture_ref="capture:old")]),
            task(queue=[queue_row(sim_ref="sim:other")]),
            task(queue_verified=False),
            task(observed_at_unix=NOW-181),
            task(capture_ref="capture:old"),
        ]
        for row in cases:
            with self.subTest(row=row):
                self.assertEqual(self.check(row)["gate"], "REOBSERVE_TASK_QUEUE")

    def test_verification_required_to_claim_completion(self):
        all_done = task(targets=[
            {"target_ref": "plant:1", "state": "VERIFIED_DONE",
             "outcome_ref": "proof:1", "outcome_capture_ref": "capture:1"}])
        self.assertEqual(self.check(all_done)["state"], "VERIFIED_COMPLETE")
        for row in (
            task(targets=[{"target_ref": "plant:1", "state": "VERIFIED_DONE"}]),
            task(targets=[{"target_ref": "plant:2", "state": "PENDING"}]*2),
            task(targets=[]),
            task(queue=[queue_row(origin="BOGUS")]),
            task(player_override={"kind": "CANCEL_GOAL"}),
        ):
            with self.subTest(row=row), self.assertRaises(TaskContinuityError):
                self.check(row)

    def test_idempotent_and_pure_with_bounded_multi_plant_goals(self):
        record = task()
        before = copy.deepcopy(record)
        self.assertEqual(self.check(record), self.check(record))
        self.assertEqual(record, before)
        with self.assertRaises(TaskContinuityError):
            self.check(task(targets=[{"target_ref": f"plant:{i}", "state": "PENDING"}
                                     for i in range(33)]))
        with self.assertRaises(TaskContinuityError):
            self.check(task(queue=[queue_row()]*25))


class GardeningContinuityIntegrationTests(unittest.TestCase):
    def run_garden(self, task_row, **flags):
        ctx = garden(task_row)
        report = evaluate_need_services(NEEDS, capture_ref=CAPTURE)
        return evaluate_gardening_turn(NEEDS, report, ctx, capture_ref=CAPTURE, **flags)

    def test_fertilize_target_specific_selection(self):
        out = self.run_garden(task())
        self.assertEqual(out["gate"], "GARDEN_ACTION_READY")
        self.assertEqual(out["next_actions"][0]["target_ref"], "plant:2")
        self.assertEqual(out["task_continuity"]["verified_done_count"], 1)
        self.assertFalse(out["dispatch_authorized"])

    def test_chat_interrupt_and_busy_host_no_click(self):
        row = task(queue=[queue_row()])
        out = self.run_garden(row, already_busy=True)
        self.assertEqual(out["gate"], "GARDEN_AUTONOMOUS_INTERRUPTION")
        self.assertEqual(out["next_actions"], [])
        self.assertFalse(out["dispatch_authorized"])
        self.assertEqual(out["task_continuity"]["state"], "INTERRUPTED")

    def test_player_and_need_responsibilities_still_outrank_goal(self):
        self.assertEqual(self.run_garden(task(), player_directed=True)["gate"],
                         "GARDEN_PLAYER_FIRST")
        out = evaluate_turn(NEEDS, gardening=garden(task()),
                            queue=[], capture_ref=CAPTURE, location_kind="home",
                            viewport={"state": "VIEWPORT_OK"}, homework_pending=True)
        self.assertEqual(out["gardening"]["gate"], "GARDEN_RESPONSIBILITY_FIRST")
        out = evaluate_turn(NEEDS, gardening=garden(task()),
                            queue=[], capture_ref=CAPTURE, location_kind="home",
                            viewport={"state": "VIEWPORT_OK"})
        self.assertEqual(out["next_gate"], "GARDEN_ACTION_READY")

    def test_stale_target_action_and_queued_duplicate_not_selected(self):
        report = evaluate_need_services(NEEDS, capture_ref=CAPTURE)
        bad_action = [dict(action_id="FERTILIZE", label="Fertilize",
                           target_ref="plant:3", capture_ref=CAPTURE, available=True)]
        out = evaluate_gardening_turn(NEEDS, report, garden(task(), actions=bad_action),
                                     capture_ref=CAPTURE)
        self.assertEqual(out["gate"], "GARDEN_INSPECT_TASK_TARGET")
        self.assertEqual(out["next_actions"], [])
        out = self.run_garden(task(queue=[
            queue_row("FERTILIZE", "plant:2", "PLAYER", "command:user-1")]))
        self.assertEqual(out["gate"], "GARDEN_TASK_ALREADY_QUEUED")
        self.assertEqual(out["next_actions"], [])


if __name__ == "__main__":
    unittest.main()
