import unittest

from betterinstincts.career_service import (
    CareerServiceError,
    compact_career_service,
    evaluate_career_service,
    load_contract,
    should_attach_career_service,
    evaluate_work_shift_tone,
)

GREEN = dict(hunger=0.9, bladder=0.9, energy=0.9, hygiene=0.9, fun=0.9, social=0.9)
HUNGRY = {**GREEN, "hunger": 0.2}


class CareerServiceTests(unittest.TestCase):
    def _shift(self, **updates):
        row = {
            "schema": "betterinstincts.work-shift.observation/v1",
            "member_key": "sim:one",
            "capture_ref": "capture:work001",
            "shift_ref": "shift:career001",
            "state": "AT_WORK",
            "work_mode": "RABBIT_HOLE",
            "promotion_requirements": "MET",
            "daily_task": "COMPLETE",
            "performance": "BELOW_TARGET",
            "current_tone": "NORMAL",
            "tone_owner": "GAME",
            "work_hard_available": True,
        }
        row.update(updates)
        return row

    def _tone(self, shift, **kwargs):
        return evaluate_work_shift_tone(
            shift, member_key="sim:one", capture_ref="capture:work001",
            wellbeing_ready=kwargs.get("wellbeing_ready", True),
            player_reserved=kwargs.get("player_reserved", False),
        )

    def test_work_hard_is_a_proposal_not_a_promotion_or_effect(self):
        report = self._tone(self._shift())
        self.assertEqual(report["gate"], "WORK_HARD_ADMISSION_REQUIRED")
        self.assertEqual(report["recommended_tone"], "WORK_HARD")
        self.assertFalse(report["handoff_ready"])
        self.assertFalse(report["execute_allowed"])
        self.assertFalse(report["promotion_guaranteed"])

    def test_confirmed_work_hard_releases_actor_attention_without_reapplying(self):
        report = self._tone(self._shift(current_tone="WORK_HARD"))
        self.assertEqual(report["gate"], "WORK_HARD_OBSERVED_HANDOFF_READY")
        self.assertTrue(report["handoff_ready"])
        self.assertIsNone(report["recommended_tone"])

    def test_preserves_player_owned_other_and_unknown_tones(self):
        for row in (
            self._shift(tone_owner="PLAYER"),
            self._shift(tone_owner="UNKNOWN"),
            self._shift(current_tone="OTHER"),
            self._shift(current_tone="UNKNOWN"),
        ):
            with self.subTest(tone=row):
                report = self._tone(row)
                self.assertEqual(report["gate"], "PRESERVE_EXISTING_OR_UNKNOWN_WORK_TONE")
                self.assertTrue(report["handoff_ready"])
                self.assertIsNone(report["recommended_tone"])

    def test_promotion_unmet_daily_task_or_performance_blocks_work_hard(self):
        for change in (
            {"promotion_requirements": "UNMET"},
            {"promotion_requirements": "UNKNOWN"},
            {"daily_task": "INCOMPLETE"},
            {"daily_task": "UNKNOWN"},
            {"performance": "READY"},
            {"performance": "UNKNOWN"},
        ):
            with self.subTest(change=change):
                report = self._tone(self._shift(**change))
                self.assertEqual(report["gate"], "PROMOTION_OPPORTUNITY_NOT_PROVEN")
                self.assertTrue(report["handoff_ready"])
        self.assertEqual(
            self._tone(self._shift(daily_task="NOT_REQUIRED"))["gate"],
            "WORK_HARD_ADMISSION_REQUIRED",
        )

    def test_low_wellbeing_or_unavailable_tone_skips_not_retries(self):
        self.assertEqual(
            self._tone(self._shift(), wellbeing_ready=False)["gate"],
            "WELLBEING_FIRST_SKIP_WORK_HARD",
        )
        self.assertEqual(
            self._tone(self._shift(work_hard_available=False))["gate"],
            "WORK_HARD_NOT_OBSERVED_AVAILABLE",
        )

    def test_active_career_and_player_reservation_are_not_rabbit_holes(self):
        self.assertEqual(
            self._tone(self._shift(work_mode="ACTIVE_CAREER"))["gate"],
            "ACTIVE_OR_UNKNOWN_CAREER_HOLD",
        )
        self.assertFalse(
            self._tone(self._shift(work_mode="UNKNOWN"))["handoff_ready"],
        )
        self.assertFalse(
            self._tone(self._shift(), player_reserved=True)["handoff_ready"],
        )

    def test_incomplete_or_stale_shift_observation_fails_closed(self):
        cases = [
            self._shift(member_key="sim:other"),
            self._shift(capture_ref="capture:stale"),
            self._shift(work_mode="INVALID"),
            self._shift(state="LEAVING"),
            self._shift(work_hard_available="yes"),
        ]
        missing = self._shift()
        missing.pop("shift_ref")
        cases.append(missing)
        for shift in cases:
            with self.subTest(shift=shift), self.assertRaises(CareerServiceError):
                self._tone(shift)

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
