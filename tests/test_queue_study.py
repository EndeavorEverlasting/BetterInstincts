"""P82 regression: queue capacity and seated indoor homework are non-optional."""
import unittest

from betterinstincts.house_state import create_model, observe
from betterinstincts.queue_capacity import QueueCapacityError, evaluate_queue_capacity
from betterinstincts.study_space import evaluate_study_space
from betterinstincts.teen_homework import evaluate_teen_homework_turn
from betterinstincts.host_stack import evaluate_turn

OK = {
    "hunger": .65, "bladder": .65, "energy": .75,
    "hygiene": .8, "fun": .6, "social": .6,
}


def study_lot(*, outdoor=False, with_seat=True, unverified=False):
    m = create_model("queue_study_lab", "Homework Lab")
    where = "OUTSIDE" if outdoor else "INSIDE"
    confidence = "HYPOTHESIS" if unverified else "LOCAL_OBSERVED"
    entities = {
        "study-room": {"kind": "ROOM_ZONE", "story": "FLOOR_1", "zone": "STUDY",
                       "enclosure": where, "confidence": "LOCAL_OBSERVED"},
        "desk": {"kind": "DESK", "story": "FLOOR_1", "zone": "STUDY",
                 "enclosure": where, "confidence": confidence},
    }
    if with_seat:
        entities["chair"] = {
            "kind": "DINING_CHAIR", "story": "FLOOR_1", "zone": "STUDY",
            "enclosure": where, "confidence": "LOCAL_OBSERVED",
        }
    return observe(m, entities=entities)


def homework(**kwargs):
    data = dict(
        location_kind="home", homework_pending=True,
        inventory_has_homework=True, multitasking=False, queue=[],
    )
    data.update(kwargs)
    return evaluate_teen_homework_turn(OK, **data)


class QueueBudgetTests(unittest.TestCase):
    def test_operator_bands_and_conservative_budgets(self):
        a = evaluate_queue_capacity(["Chat"], multitasking=True)
        self.assertEqual(a["operator_reported_capacity_band"], [2, 3])
        self.assertEqual(a["max_new_actions"], 1)
        self.assertFalse(evaluate_queue_capacity(["Chat", "Cook"], multitasking=True)["enqueue_allowed"])
        b = evaluate_queue_capacity(["a"] * 5, multitasking=False)
        self.assertEqual(b["operator_reported_capacity_band"], [6, 7])
        self.assertEqual(b["max_new_actions"], 1)
        self.assertFalse(evaluate_queue_capacity(["a"] * 6, multitasking=False)["enqueue_allowed"])

    def test_unknown_player_and_rejected_enqueue_hold(self):
        self.assertEqual(evaluate_queue_capacity([], multitasking=None)["max_new_actions"], 0)
        self.assertEqual(evaluate_queue_capacity([], multitasking=False, player_directed=True)["gate"], "PLAYER_QUEUE_YIELD")
        self.assertFalse(evaluate_queue_capacity([], multitasking=False, rejected_last_enqueue=True)["enqueue_allowed"])
        with self.assertRaises(QueueCapacityError):
            evaluate_queue_capacity(["a"], multitasking="yes")


class HomeworkStudyTests(unittest.TestCase):
    def test_no_lot_snapshot_abstains_not_sidewalk(self):
        r = homework()
        self.assertEqual(r["gate"], "HOMEWORK_STUDY_SCAN_REQUIRED")
        self.assertIn("HOMEWORK_ON_SIDEWALK", r["study_space"]["forbidden"])
        self.assertIsNone(r["primary_route"])

    def test_outdoor_unseated_and_unverified_areas_not_promoted(self):
        for m in (study_lot(outdoor=True), study_lot(with_seat=False), study_lot(unverified=True)):
            with self.subTest(revision=m["revision"]):
                r = homework(lot_model=m)
                self.assertEqual(r["gate"], "HOMEWORK_STUDY_SCAN_REQUIRED")
                self.assertIsNone(r["study_space"]["room_id"])

    def test_reuses_revisioned_room_census_and_prefers_seated_indoor_desk(self):
        model = study_lot()
        result = evaluate_study_space(model, emotion="Focused", lot_traits=["Study Spot"])
        self.assertEqual(result["state"], "STUDY_LOCATION_CANDIDATE")
        self.assertEqual(result["room_id"], "FLOOR_1:STUDY")
        self.assertEqual(result["surface_id"], "desk")
        self.assertEqual(result["seat_id"], "chair")
        self.assertTrue(result["focused_emotion_observed"])
        self.assertTrue(result["study_spot_trait_observed"])
        self.assertFalse(result["execute_allowed"])

    def test_move_and_reobserve_before_queue_then_one_homework(self):
        model = study_lot()
        a = homework(lot_model=model)
        self.assertEqual(a["gate"], "PREPARE_STUDY_LOCATION")
        self.assertEqual(a["primary_route"], "MOVE_TO_STUDY_SEAT")
        b = homework(lot_model=model, sim_room_id="FLOOR_1:STUDY",
                     sim_seated=True, sim_seat_id="wrong-chair")
        self.assertEqual(b["gate"], "PREPARE_STUDY_LOCATION")
        c = homework(lot_model=model, sim_room_id="FLOOR_1:STUDY",
                     sim_seated=True, sim_seat_id="chair")
        self.assertEqual(c["gate"], "QUEUE_TEEN_HOMEWORK")
        self.assertEqual(c["primary_route"], "DO_HOMEWORK")

    def test_known_busy_queue_unknown_capacity_and_existing_homework(self):
        model = study_lot()
        position = {"lot_model": model, "sim_room_id": "FLOOR_1:STUDY",
                    "sim_seated": True, "sim_seat_id": "chair"}
        self.assertEqual(homework(**position, multitasking=None)["gate"], "HOMEWORK_QUEUE_CAPACITY_HOLD")
        self.assertEqual(homework(**position, multitasking=True, queue=["Chat", "Browse"])["gate"],
                         "HOMEWORK_QUEUE_CAPACITY_HOLD")
        self.assertEqual(homework(**position, queue=["Do Homework"])["gate"],
                         "HOMEWORK_ALREADY_QUEUED")
        self.assertEqual(homework(**position, player_directed=True)["gate"], "PLAYER_FIRST_OR_BUSY")

    def test_host_stack_applies_homework_gate_and_exposes_queue_capacity(self):
        model = study_lot()
        a = evaluate_turn(OK, location_kind="home", homework_pending=True,
                          inventory_has_homework=True, life_stage="teen",
                          multitasking=False, queue=[], lot_model=model,
                          viewport={"state": "VIEWPORT_OK"})
        self.assertEqual(a["next_gate"], "PREPARE_STUDY_LOCATION")
        self.assertEqual(a["queue_capacity"]["conservative_limit"], 6)
        self.assertFalse(a["fallback"]["execute_allowed"])
        b = evaluate_turn(OK, location_kind="home", homework_pending=True,
                          inventory_has_homework=True, life_stage="teen",
                          multitasking=False, queue=[], lot_model=model,
                          sim_room_id="FLOOR_1:STUDY", sim_seated=True, sim_seat_id="chair",
                          viewport={"state": "VIEWPORT_OK"})
        self.assertEqual(b["next_gate"], "QUEUE_TEEN_HOMEWORK")


if __name__ == "__main__":
    unittest.main()
