import unittest

from betterinstincts.fun_service import (
    FunServiceError,
    evaluate_fun_service,
    load_contract,
    should_attach_fun_service,
)
from betterinstincts.host_stack import evaluate_turn

LOW_FUN = {
    "hunger": 0.7,
    "bladder": 0.6,
    "energy": 0.65,
    "hygiene": 0.7,
    "fun": 0.2,
    "social": 0.6,
}
CRITICAL_HUNGER = {**LOW_FUN, "hunger": 0.1, "fun": 0.15}


class FunServiceTests(unittest.TestCase):
    def test_contract_lanes(self):
        cfg = load_contract()
        self.assertIn("personal_portable", cfg["lanes"])
        self.assertIn("playful_exclusive", cfg["lanes"])
        self.assertEqual(cfg["lane_priority_when_guests"][0], "personal_portable")

    def test_guests_prefer_portable_when_tv_occupied(self):
        report = evaluate_fun_service(
            LOW_FUN,
            available_objects=["tv", "computer", "phone", "stereo"],
            occupied_objects=["tv", "computer"],
            guests_present=True,
        )
        self.assertEqual(report["gate"], "FUN_SERVICE_PLAN")
        self.assertEqual(report["primary_route"], "PHONE_GAME")
        self.assertIn("personal_portable", report["parallel_ready"])
        self.assertIn("GUESTS_PRESENT_PREFER_PORTABLE_FUN", report["findings"])
        self.assertEqual(report["architecture"], "TANDEM_LANE_SERVICES_NOT_MONOLITH_QUEUE")

    def test_playful_exclusive_requires_emotion(self):
        blocked = evaluate_fun_service(
            LOW_FUN,
            available_objects=["computer", "piano"],
            emotion="HAPPY",
        )
        exclusive = [L for L in blocked["lanes"] if L["id"] == "playful_exclusive"][0]
        self.assertEqual(exclusive["status"], "NEEDS_PLAYFUL")

        ready = evaluate_fun_service(
            LOW_FUN,
            available_objects=["computer", "piano"],
            emotion="PLAYFUL",
        )
        exclusive = [L for L in ready["lanes"] if L["id"] == "playful_exclusive"][0]
        self.assertEqual(exclusive["status"], "READY")
        self.assertTrue(any(a["id"] == "SCOUR_FOR_MEMES" for a in exclusive["actions"]))

    def test_survival_outranks_fun(self):
        report = evaluate_fun_service(CRITICAL_HUNGER, available_objects=["phone"])
        self.assertEqual(report["gate"], "SURVIVAL_NEEDS_CRITICAL")

    def test_parallel_lanes_ready_without_monolith(self):
        report = evaluate_fun_service(
            LOW_FUN,
            available_objects=["phone", "guitar", "book", "tv"],
        )
        self.assertGreaterEqual(len(report["parallel_ready"]), 2)
        self.assertIn("personal_portable", report["parallel_ready"])
        self.assertIn("creative_hobbies", report["parallel_ready"])

    def test_sibling_lane_claim_avoids_pileup(self):
        report = evaluate_fun_service(
            LOW_FUN,
            available_objects=["phone", "tv"],
            sibling_lane_claims=["personal_portable"],
            guests_present=True,
        )
        personal = [L for L in report["lanes"] if L["id"] == "personal_portable"][0]
        self.assertEqual(personal["status"], "CLAIMED_BY_SIBLING_SIM")

    def test_should_attach(self):
        self.assertTrue(should_attach_fun_service(LOW_FUN))
        self.assertTrue(should_attach_fun_service({**LOW_FUN, "fun": 0.7}, guests_present=True))
        self.assertFalse(should_attach_fun_service({**LOW_FUN, "fun": 0.9}))

    def test_host_stack_fun_gate(self):
        result = evaluate_turn(
            LOW_FUN,
            available_objects=["phone", "tv"],
            occupied_objects=["tv"],
            guests_present=True,
            viewport={"state": "VIEWPORT_OK"},
        )
        self.assertEqual(result["next_gate"], "FUN_SERVICE_PLAN")
        self.assertEqual(result["fallback"]["primary_route"], "PHONE_GAME")
        self.assertIn("personal_portable", result["fun_service"]["parallel_ready"])

    def test_invalid_needs(self):
        with self.assertRaises(FunServiceError):
            evaluate_fun_service({"hunger": 1.0})


if __name__ == "__main__":
    unittest.main()
