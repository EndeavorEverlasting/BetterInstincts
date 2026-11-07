import unittest

from betterinstincts.host_listener import activate, deactivate, tick
from betterinstincts.host_stack import evaluate_turn
from betterinstincts.player_presence import PresenceProbe
from betterinstincts.social_opportunity import (
    SocialOpportunityError,
    evaluate_social_opportunity,
    invitee_from_prompt,
    load_contract,
    lookup_sim_library,
)

SIX_OK = {
    "hunger": 0.6,
    "bladder": 0.45,
    "energy": 0.7,
    "hygiene": 0.7,
    "fun": 0.25,
    "social": 0.8,
}
PROMPT = "Should Charlee invite over classmate Morgan?"


class SocialOpportunityTests(unittest.TestCase):
    def test_contract_and_prompt_parse(self):
        cfg = load_contract()
        self.assertEqual(cfg["schema"], "betterinstincts.social-opportunity/v1")
        self.assertIn("sim_library", cfg)
        self.assertEqual(invitee_from_prompt(PROMPT), "Morgan")
        self.assertIn("SOCIAL_LOOKUP_REQUIRED", cfg["call_stack_gates"])

    def test_lookup_required_before_ok(self):
        report = evaluate_social_opportunity(
            social_prompt_active=True,
            prompt_text=PROMPT,
        )
        self.assertEqual(report["gate"], "SOCIAL_LOOKUP_REQUIRED")
        self.assertEqual(report["dialog_choice"], "CANCEL")
        self.assertFalse(report["press_ok_allowed"])
        self.assertEqual(report["invitee_name"], "Morgan")

    def test_unique_human_allows_ok(self):
        library = [{"name": "Morgan", "occult_status": "HUMAN", "sim_id": "npc:morgan"}]
        report = evaluate_social_opportunity(
            social_prompt_active=True,
            prompt_text=PROMPT,
            sim_library=library,
            lookup_ran=True,
        )
        self.assertEqual(report["gate"], "SOCIAL_OPPORTUNITY_OK_ALLOWED")
        self.assertTrue(report["press_ok_allowed"])
        self.assertEqual(report["dialog_choice"], "OK")
        self.assertEqual(report["occult_status"], "HUMAN")

    def test_vampire_blocks_ok(self):
        library = [{"name": "Morgan", "occult_status": "VAMPIRE"}]
        report = evaluate_social_opportunity(
            social_prompt_active=True,
            invitee_name="Morgan",
            sim_library=library,
            lookup_ran=True,
        )
        self.assertEqual(report["gate"], "SOCIAL_OCCULT_UNSAFE_HOME_INVITE")
        self.assertEqual(report["dialog_choice"], "CANCEL")

    def test_ambiguous_name_fails_closed(self):
        library = [
            {"name": "Morgan", "occult_status": "HUMAN"},
            {"name": "Morgan", "occult_status": "VAMPIRE", "sim_id": "other"},
        ]
        hit = lookup_sim_library("Morgan", library)
        self.assertEqual(hit["state"], "AMBIGUOUS_NAME")
        report = evaluate_social_opportunity(
            social_prompt_active=True,
            invitee_name="Morgan",
            sim_library=library,
            lookup_ran=True,
        )
        self.assertEqual(report["gate"], "SOCIAL_LOOKUP_AMBIGUOUS_OR_MISSING")
        self.assertFalse(report["press_ok_allowed"])

    def test_unknown_occult_after_unique_match(self):
        library = [{"name": "Morgan", "occult_status": "UNKNOWN"}]
        report = evaluate_social_opportunity(
            social_prompt_active=True,
            invitee_name="Morgan",
            sim_library=library,
            lookup_ran=True,
        )
        self.assertEqual(report["gate"], "SOCIAL_OCCULT_UNKNOWN")
        self.assertEqual(report["dialog_choice"], "CANCEL")

    def test_host_stack_morgan_lookup_required(self):
        result = evaluate_turn(
            SIX_OK,
            social_prompt_active=True,
            social_prompt_text=PROMPT,
            viewport={"state": "VIEWPORT_OK"},
        )
        self.assertEqual(result["next_gate"], "SOCIAL_LOOKUP_REQUIRED")
        self.assertFalse(result["fallback"]["press_ok_allowed"])
        self.assertEqual(result["social_opportunity"]["invitee_name"], "Morgan")

    def test_host_stack_camera_home_sim_at_school_blocks_homework_lot_scan(self):
        result = evaluate_turn(
            SIX_OK,
            location_kind="home",
            camera_lot_kind="home",
            sim_at_school=True,
            homework_pending=True,
            inventory_has_homework=False,
            life_stage="teen",
            viewport={"state": "VIEWPORT_OK"},
        )
        self.assertEqual(result["sim_premises"]["effective_location_kind"], "school")
        self.assertEqual(result["next_gate"], "HOMEWORK_PREMISES_BLOCKED")
        self.assertNotEqual(
            (result.get("teen_homework") or {}).get("primary_route"),
            "LOT_SCAN_PUT_HOMEWORK_IN_INVENTORY",
        )

    def test_listener_social_fields(self):
        sid = "testsocial01"
        activate(sid, note="unit")
        try:
            receipt = tick(
                sid,
                {
                    "schema": "betterinstincts.host-listener.observation/v1",
                    "needs": SIX_OK,
                    "queue": [],
                    "location_kind": "home",
                    "capture_ref": "capture:social-listener",
                    "social_prompt_active": True,
                    "social_prompt_text": PROMPT,
                    "sim_library": [{"name": "Morgan", "occult_status": "HUMAN"}],
                    "social_lookup_ran": True,
                },
                presence_probe=PresenceProbe(False, False, last_input_age_ms=9000),
            )
            stack = receipt["host_stack"]
            self.assertEqual(stack["next_gate"], "SOCIAL_OPPORTUNITY_OK_ALLOWED")
            self.assertTrue(stack["fallback"]["press_ok_allowed"])
        finally:
            deactivate(sid)

    def test_invalid_occult_fails_closed(self):
        with self.assertRaises(SocialOpportunityError):
            lookup_sim_library("Morgan", [{"name": "Morgan", "occult_status": "DRAGON"}])


if __name__ == "__main__":
    unittest.main()
