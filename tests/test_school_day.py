import unittest

from betterinstincts.host_listener import activate, deactivate, tick
from betterinstincts.host_stack import evaluate_turn
from betterinstincts.player_presence import PresenceProbe
from betterinstincts.school_day import (
    SchoolDayError,
    evaluate_school_day_turn,
    homework_blocked_on_premises,
    load_contract,
    plan_school_day_goals,
    resolve_goal_id,
)

SIX_OK = {
    "hunger": 0.6,
    "bladder": 0.45,
    "energy": 0.7,
    "hygiene": 0.7,
    "fun": 0.25,
    "social": 0.8,
}
CRITICAL = {
    "hunger": 0.05,
    "bladder": 0.9,
    "energy": 0.9,
    "hygiene": 0.9,
    "fun": 0.2,
    "social": 0.2,
}


class SchoolDayTests(unittest.TestCase):
    def test_contract_high_school_priority(self):
        cfg = load_contract()
        self.assertEqual(cfg["default_profile"], "high_school_years")
        self.assertIn("study_for_exams", cfg["goals"])
        self.assertEqual(
            cfg["profiles"]["high_school_years"]["goal_priority"][0],
            "study_for_exams",
        )
        self.assertIn("SCHOOL_DAY_GOAL_PROGRESS", cfg["call_stack_gates"])
        self.assertIn("HOMEWORK_PREMISES_BLOCKED", cfg["call_stack_gates"])
        self.assertFalse(cfg["phases"]["morning_free_time"]["homework_allowed"])
        self.assertFalse(cfg["career_panel"]["homework"]["allowed_on_school_premises"])
        study = cfg["goals"]["study_for_exams"]["satisfying_interactions"][0]
        self.assertEqual(study["id"], "HIGH_SCHOOL_STUDY_FOR_EXAMS")
        self.assertEqual(study["steps"][1], "PIE_HIGH_SCHOOL")

    def test_morning_free_time_study_with_pinned_whim(self):
        plan = plan_school_day_goals(
            ["socialize_at_school", "study for exams"],
            school_phase="morning free time",
            pinned_whims=["Not Stumble for 4 Hours"],
        )
        self.assertEqual(plan["next_goal"], "study_for_exams")
        self.assertEqual(plan["primary_route"], "HIGH_SCHOOL_STUDY_FOR_EXAMS")
        self.assertIn("PINNED_NOT_STUMBLE_PREFERS_STUDY", plan["findings"])
        self.assertEqual(resolve_goal_id("Study for Exams"), "study_for_exams")

    def test_homework_blocked_on_premises(self):
        self.assertTrue(
            homework_blocked_on_premises(
                location_kind="school",
                school_phase="morning_free_time",
            )
        )
        report = evaluate_school_day_turn(
            SIX_OK,
            school_day_active=False,
            homework_pending=True,
            location_kind="school",
            school_phase="morning_free_time",
        )
        self.assertEqual(report["gate"], "HOMEWORK_PREMISES_BLOCKED")
        self.assertTrue(report["homework_blocked_on_premises"])

    def test_survival_outranks_school_goals(self):
        report = evaluate_school_day_turn(
            CRITICAL,
            school_day_active=True,
            school_goals_incomplete=["study_for_exams"],
            location_kind="school",
        )
        self.assertEqual(report["gate"], "SURVIVAL_NEEDS_CRITICAL")
        self.assertIn("hunger", report["survival_critical"])

    def test_green_needs_school_day_goal_progress(self):
        report = evaluate_school_day_turn(
            SIX_OK,
            school_day_active=True,
            school_goals_incomplete=["study_for_exams", "participate"],
            location_kind="school",
            school_phase="morning_free_time",
        )
        self.assertEqual(report["gate"], "SCHOOL_DAY_GOAL_PROGRESS")
        self.assertIsNotNone(report["goal_plan"])
        self.assertEqual(report["goal_plan"]["next_goal"], "study_for_exams")

    def test_host_stack_school_day_gate(self):
        result = evaluate_turn(
            SIX_OK,
            school_day_active=True,
            school_goals_incomplete=["study_for_exams"],
            school_phase="morning_free_time",
            location_kind="school",
            pinned_whims=["not stumble"],
            viewport={"state": "VIEWPORT_OK"},
        )
        self.assertEqual(result["next_gate"], "SCHOOL_DAY_GOAL_PROGRESS")
        self.assertIsNotNone(result["school_day"])
        self.assertEqual(result["fallback"]["next_goal"], "study_for_exams")
        self.assertEqual(
            result["fallback"]["next_actions"][0]["id"],
            "HIGH_SCHOOL_STUDY_FOR_EXAMS",
        )

    def test_listener_tick_passes_school_fields(self):
        sid = "testschoolday01"
        activate(sid, note="unit")
        try:
            receipt = tick(
                sid,
                {
                    "schema": "betterinstincts.host-listener.observation/v1",
                    "needs": SIX_OK,
                    "queue": [],
                    "location_kind": "school",
                    "objects_on_current_lot": False,
                    "capture_ref": "capture:school-listener",
                    "school_day_active": True,
                    "school_goals_incomplete": ["study_for_exams"],
                    "school_phase": "morning_free_time",
                    "pinned_whims": ["not stumble"],
                    "homework_pending": False,
                    "emotion": "FINE",
                    "moodlets": [],
                    "traits": ["Clumsy"],
                    "whims": ["Not Stumble"],
                },
                presence_probe=PresenceProbe(False, False, last_input_age_ms=19000),
            )
            stack = receipt["host_stack"]
            self.assertEqual(stack["next_gate"], "SCHOOL_DAY_GOAL_PROGRESS")
            self.assertIsNotNone(stack.get("school_day"))
        finally:
            deactivate(sid)

    def test_unknown_profile_fails_closed(self):
        with self.assertRaises(SchoolDayError):
            plan_school_day_goals(["study_for_exams"], school_profile="middle_school_mystery")


if __name__ == "__main__":
    unittest.main()
