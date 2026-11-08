import unittest

from betterinstincts.career_service import (
    CareerServiceError,
    compact_career_service,
    evaluate_career_service,
    load_contract,
    should_attach_career_service,
)

GREEN = dict(hunger=0.9, bladder=0.9, energy=0.9, hygiene=0.9, fun=0.9, social=0.9)
HUNGRY = {**GREEN, "hunger": 0.2}


class CareerServiceTests(unittest.TestCase):
    def test_contract_loads(self):
        cfg = load_contract()
        self.assertEqual(cfg["schema"], "betterinstincts.career-service/v1")
        self.assertIn("high_school_student", cfg["career_tracks"])

    def test_survival_suspends_action_but_holds_obligation(self):
        report = evaluate_career_service(
            HUNGRY,
            homework_pending=True,
            inventory_has_homework=True,
            location_kind="home",
            life_stage="teen",
        )
        self.assertTrue(report["obligation_held"])
        self.assertEqual(report["microsystem_state"], "SUSPENDED_FOR_SURVIVAL")
        self.assertEqual(report["gate"], "SUSPENDED_FOR_SURVIVAL")
        self.assertEqual(report["next_actions"], [])
        self.assertIn("SURVIVAL_SUSPENDS_CAREER_ACTION_NOT_OBLIGATION", report["findings"])

    def test_prior_suspended_obligation_resumes_when_survival_green(self):
        suspended = evaluate_career_service(
            HUNGRY,
            homework_pending=True,
            inventory_has_homework=True,
            location_kind="home",
            life_stage="teen",
            capture_ref="capture:prior",
        )
        resumed = evaluate_career_service(
            GREEN,
            homework_pending=True,
            inventory_has_homework=True,
            location_kind="home",
            life_stage="teen",
            prior_state=suspended,
            capture_ref="capture:resume",
        )
        self.assertTrue(resumed["obligation_held"])
        self.assertEqual(resumed["microsystem_state"], "READY")
        self.assertEqual(resumed["gate"], "CAREER_READY_AFTER_NEEDS")
        self.assertTrue(resumed["next_actions"])
        self.assertIn("CAREER_RESUMED_AFTER_SURVIVAL_OR_CONTINUITY", resumed["findings"])

    def test_completed_homework_clears_even_with_prior_and_book_tokens(self):
        suspended = evaluate_career_service(
            HUNGRY,
            homework_pending=True,
            inventory_has_homework=False,
            homework_on_lot=True,
            available_objects=["homework"],
            location_kind="home",
            life_stage="teen",
        )
        done = evaluate_career_service(
            GREEN,
            homework_pending=False,
            inventory_has_homework=True,
            available_objects=["homework"],
            location_kind="home",
            life_stage="teen",
            prior_state=suspended,
        )
        self.assertFalse(done["obligation_held"])
        self.assertEqual(done["microsystem_state"], "COMPLETE")
        self.assertIn("CAREER_OBLIGATION_CLEARED_EXPLICIT_COMPLETE", done["findings"])

    def test_premises_block_holds_obligation(self):
        report = evaluate_career_service(
            GREEN,
            homework_pending=True,
            location_kind="school",
            school_day_active=True,
            life_stage="teen",
        )
        self.assertTrue(report["obligation_held"])
        self.assertEqual(report["microsystem_state"], "PREMISES_BLOCKED")

    def test_player_yield_preserves_tracking_flag_path(self):
        report = evaluate_career_service(
            GREEN,
            homework_pending=True,
            inventory_has_homework=True,
            location_kind="home",
            life_stage="teen",
            player_directed=True,
        )
        self.assertEqual(report["microsystem_state"], "YIELDED")
        self.assertTrue(report["obligation_held"])
        self.assertEqual(report["next_actions"], [])

    def test_attach_from_prior_without_fresh_homework_flag_still_tracks_when_pending(self):
        prior = {
            "obligation_held": True,
            "microsystem_state": "SUSPENDED_FOR_SURVIVAL",
            "obligation": {
                "track": "high_school_student",
                "daily_task": "homework",
                "source": "prior",
                "resume_condition": "FRESH_SURVIVAL_GREEN_HOME_REVALIDATION",
            },
        }
        self.assertTrue(should_attach_career_service(prior_state=prior))
        # Without homework_pending the obligation clears (explicit complete).
        cleared = evaluate_career_service(GREEN, prior_state=prior, life_stage="teen")
        self.assertEqual(cleared["microsystem_state"], "COMPLETE")

    def test_ready_inventory_missing_recovery_ladder(self):
        report = evaluate_career_service(
            GREEN,
            homework_pending=True,
            inventory_has_homework=False,
            homework_on_lot=True,
            available_objects=["homework book"],
            location_kind="home",
            life_stage="teen",
        )
        self.assertEqual(report["microsystem_state"], "READY")
        self.assertTrue(report["next_actions"])
        self.assertEqual(report["lanes"]["teen_homework"]["gate"], "HOMEWORK_INVENTORY_MISSING")

    def test_compact_strips_lane_bulk(self):
        report = evaluate_career_service(
            GREEN,
            homework_pending=True,
            inventory_has_homework=True,
            location_kind="home",
            life_stage="teen",
        )
        compact = compact_career_service(report)
        self.assertTrue(compact["compacted"])
        self.assertTrue(compact["obligation_held"])
        self.assertIn("teen_homework", compact["lanes"])

    def test_six_needs_required(self):
        with self.assertRaises(CareerServiceError):
            evaluate_career_service({"hunger": 0.5}, homework_pending=True, life_stage="teen")


if __name__ == "__main__":
    unittest.main()
