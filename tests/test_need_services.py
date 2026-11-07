import unittest

from betterinstincts.host_stack import evaluate_turn
from betterinstincts.need_service_base import objects_free, normalize_needs
from betterinstincts.need_services import (
    NeedServicesError,
    evaluate_need_lanes,
    evaluate_need_services,
    load_registry,
    should_attach_need_services,
)

LOW_FUN = {
    "hunger": 0.7,
    "bladder": 0.6,
    "energy": 0.65,
    "hygiene": 0.7,
    "fun": 0.2,
    "social": 0.6,
}
HUNGER_CRITICAL = {
    "hunger": 0.1,
    "bladder": 0.8,
    "energy": 0.8,
    "hygiene": 0.8,
    "fun": 0.5,
    "social": 0.5,
}


class NeedServicesTests(unittest.TestCase):
    def test_registry_six(self):
        reg = load_registry()
        self.assertEqual(set(reg["registry"]), set(LOW_FUN))
        self.assertEqual(reg["registry"]["fun"]["owner"], "betterinstincts/fun_service.py")

    def test_base_objects_free(self):
        self.assertTrue(objects_free(["fridge"], {"fridge"}, set()))
        self.assertFalse(objects_free(["fridge"], {"fridge"}, {"fridge"}))

    def test_hunger_lane_under_contention(self):
        report = evaluate_need_lanes(
            "hunger",
            HUNGER_CRITICAL,
            available_objects=["fridge", "stove"],
            occupied_objects=["stove"],
        )
        self.assertEqual(report["gate"], "NEED_SERVICE_PLAN")
        self.assertEqual(report["primary_route"], "QUICK_MEAL")

    def test_orchestrator_picks_hunger_over_fun(self):
        out = evaluate_need_services(
            HUNGER_CRITICAL,
            available_objects=["fridge", "phone", "tv", "toilet", "bed", "shower"],
        )
        self.assertEqual(out["gate"], "NEED_SERVICES_TANDEM")
        self.assertEqual(out["primary_need"], "hunger")
        self.assertIn("fun", out["services"])
        self.assertIn("hunger", out["parallel_ready_needs"])
        self.assertEqual(out["services"]["fun"]["gate"], "SURVIVAL_NEEDS_CRITICAL")
        self.assertEqual(out["architecture"], "TANDEM_NEED_SERVICES_NOT_MONOLITH_QUEUE")

    def test_host_stack_need_services_tandem(self):
        result = evaluate_turn(
            HUNGER_CRITICAL,
            available_objects=["fridge", "phone", "toilet", "bed", "shower", "tv"],
            viewport={"state": "VIEWPORT_OK"},
        )
        self.assertEqual(result["next_gate"], "NEED_SERVICES_TANDEM")
        self.assertEqual(result["fallback"]["primary_need"], "hunger")
        self.assertIsNotNone(result["need_services"])
        self.assertIsNotNone(result["fun_service"])

    def test_fun_still_nested_when_guests(self):
        result = evaluate_turn(
            LOW_FUN,
            available_objects=["phone", "tv"],
            occupied_objects=["tv"],
            guests_present=True,
            viewport={"state": "VIEWPORT_OK"},
        )
        self.assertEqual(result["next_gate"], "NEED_SERVICES_TANDEM")
        self.assertEqual(result["need_services"]["primary_need"], "fun")
        self.assertEqual(result["fallback"]["primary_route"], "PHONE_GAME")

    def test_should_attach(self):
        self.assertTrue(should_attach_need_services(LOW_FUN))
        self.assertFalse(should_attach_need_services(normalize_needs({
            "hunger": 0.9, "bladder": 0.9, "energy": 0.9,
            "hygiene": 0.9, "fun": 0.9, "social": 0.9,
        })))

    def test_unknown_need(self):
        with self.assertRaises(NeedServicesError):
            evaluate_need_lanes("charisma", LOW_FUN)


if __name__ == "__main__":
    unittest.main()
