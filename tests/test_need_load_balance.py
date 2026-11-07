import unittest

from betterinstincts.host_stack import evaluate_turn
from betterinstincts.need_load_balance import (
    NeedLoadBalanceError,
    balance_need_services,
    health_check_service,
    load_contract,
    open_assumption_window,
)
from betterinstincts.need_services import evaluate_need_services

BLOCKED_HUNGER = {
    "hunger": 0.1,
    "bladder": 0.2,
    "energy": 0.8,
    "hygiene": 0.8,
    "fun": 0.5,
    "social": 0.5,
}
ALL_GREENISH = {
    "hunger": 0.7,
    "bladder": 0.6,
    "energy": 0.65,
    "hygiene": 0.7,
    "fun": 0.2,
    "social": 0.6,
}
LOW_FUN = {
    "hunger": 0.7,
    "bladder": 0.6,
    "energy": 0.65,
    "hygiene": 0.7,
    "fun": 0.2,
    "social": 0.6,
}


class NeedLoadBalanceTests(unittest.TestCase):
    def test_contract_loads(self):
        cfg = load_contract()
        self.assertEqual(cfg["schema"], "betterinstincts.need-load-balance/v1")
        self.assertIn("HEALTHY", cfg["health_statuses"])

    def test_blocked_hunger_detaches_and_rebalances_to_bladder(self):
        out = evaluate_need_services(
            BLOCKED_HUNGER,
            available_objects=["toilet", "bed", "shower", "phone"],
        )
        self.assertIn("hunger", out["detached_needs"])
        self.assertEqual(out["health"]["hunger"]["status"], "UNHEALTHY")
        self.assertEqual(out["gate"], "NEED_SERVICES_LOAD_BALANCE")
        self.assertEqual(out["primary_need"], "bladder")
        self.assertTrue(out["assumption_windows"])
        window = out["assumption_windows"][0]
        self.assertEqual(window["need"], "hunger")
        self.assertTrue(window["scene_reset"])
        self.assertIn("preferred_route_sticky", window["cleared_assumptions"])
        self.assertEqual(window["p95_ground"], "NEED_LOAD_BALANCE_ASSUMPTION_WINDOW")
        ids = {o["id"] for o in window["option_set"]}
        self.assertIn("FIND_OR_PLACE_NEED_OBJECT", ids)
        self.assertIn("MAP_TRAVEL_HOME", ids)

    def test_guests_do_not_detach_non_urgent_blocked_siblings(self):
        out = evaluate_need_services(
            LOW_FUN,
            available_objects=["phone", "tv"],
            occupied_objects=["tv"],
            guests_present=True,
        )
        self.assertEqual(out["gate"], "NEED_SERVICES_TANDEM")
        self.assertEqual(out["primary_need"], "fun")
        self.assertEqual(out["detached_needs"], [])
        self.assertEqual(out["assumption_windows"], [])
        # Hunger may be blocked without fridge under guests, but not material → DEGRADED.
        self.assertEqual(out["health"]["hunger"]["status"], "DEGRADED")
        self.assertFalse(out["health"]["hunger"]["detach"])

    def test_failure_signal_detaches_sticky_dead_route(self):
        out = evaluate_need_services(
            ALL_GREENISH,
            available_objects=["phone", "tv", "fridge", "toilet", "bed", "shower"],
            failure_signals={"fun": ["LANE_STUCK"], "fun:routes": ["PHONE_GAME"]},
        )
        self.assertIn("fun", out["detached_needs"])
        self.assertTrue(any(w["need"] == "fun" for w in out["assumption_windows"]))
        self.assertNotEqual(out["primary_need"], "fun")

    def test_clean_tandem_when_all_healthy(self):
        out = evaluate_need_services(
            {
                "hunger": 0.1,
                "bladder": 0.8,
                "energy": 0.8,
                "hygiene": 0.8,
                "fun": 0.5,
                "social": 0.5,
            },
            available_objects=["fridge", "toilet", "bed", "shower", "phone", "tv"],
        )
        self.assertEqual(out["gate"], "NEED_SERVICES_TANDEM")
        self.assertEqual(out["detached_needs"], [])
        self.assertEqual(out["primary_need"], "hunger")
        self.assertEqual(out["assumption_windows"], [])
        self.assertEqual(out["health"]["hunger"]["status"], "HEALTHY")

    def test_never_select_unhealthy_as_primary(self):
        services = {
            "hunger": {
                "gate": "NEED_SERVICE_BLOCKED",
                "primary_route": "QUICK_MEAL",
                "parallel_ready": [],
                "findings": ["NO_FREE_NEED_LANE"],
                "next_actions": [],
                "preferred_routes": [],
                "urgent": True,
                "low": True,
            },
            "bladder": {
                "gate": "NEED_SERVICE_PLAN",
                "primary_route": "USE_TOILET",
                "parallel_ready": ["toilet"],
                "findings": [],
                "next_actions": [
                    {"id": "USE_TOILET", "lane": "toilet", "objects": ["toilet"], "steps": []}
                ],
                "preferred_routes": ["USE_TOILET"],
                "urgent": True,
            },
            "energy": {
                "gate": "NEED_WATCH_OPTIONAL",
                "primary_route": None,
                "parallel_ready": [],
                "findings": [],
                "next_actions": [],
                "preferred_routes": [],
            },
            "hygiene": {
                "gate": "NEED_WATCH_OPTIONAL",
                "primary_route": None,
                "parallel_ready": [],
                "findings": [],
                "next_actions": [],
                "preferred_routes": [],
            },
            "fun": {
                "gate": "NEED_WATCH_OPTIONAL",
                "primary_route": None,
                "parallel_ready": [],
                "findings": [],
                "next_actions": [],
                "preferred_routes": [],
            },
            "social": {
                "gate": "NEED_WATCH_OPTIONAL",
                "primary_route": None,
                "parallel_ready": [],
                "findings": [],
                "next_actions": [],
                "preferred_routes": [],
            },
        }
        lb = balance_need_services(services, BLOCKED_HUNGER)
        self.assertEqual(lb["primary_need"], "bladder")
        self.assertIn("hunger", lb["detached_needs"])
        self.assertNotIn(lb["primary_need"], lb["detached_needs"])

    def test_assumption_window_penalizes_failed_route(self):
        health = {
            "status": "UNHEALTHY",
            "failed_routes": ["QUICK_MEAL"],
            "gate": "NEED_SERVICE_BLOCKED",
        }
        service = {
            "gate": "NEED_SERVICE_BLOCKED",
            "primary_route": "QUICK_MEAL",
            "next_actions": [
                {
                    "id": "QUICK_MEAL",
                    "lane": "quick_meal",
                    "objects": ["fridge"],
                    "steps": ["CLICK_FRIDGE"],
                },
                {
                    "id": "COOK_MEAL",
                    "lane": "cook",
                    "objects": ["stove"],
                    "steps": ["CLICK_STOVE"],
                },
            ],
        }
        window = open_assumption_window("hunger", service, health, needs=BLOCKED_HUNGER)
        by_id = {o["id"]: o["weight"] for o in window["option_set"]}
        self.assertLess(by_id["QUICK_MEAL"], by_id["COOK_MEAL"])
        self.assertEqual(window["p95_ground"], "NEED_LOAD_BALANCE_ASSUMPTION_WINDOW")

    def test_host_stack_load_balance_gate(self):
        result = evaluate_turn(
            BLOCKED_HUNGER,
            available_objects=["toilet", "bed", "shower", "phone"],
            viewport={"state": "VIEWPORT_OK"},
        )
        self.assertEqual(result["next_gate"], "NEED_SERVICES_LOAD_BALANCE")
        self.assertIn("hunger", result["fallback"]["detached_needs"])
        self.assertEqual(result["fallback"]["primary_need"], "bladder")
        self.assertEqual(
            result["fallback"]["p95_ground"],
            "NEED_LOAD_BALANCE_ASSUMPTION_WINDOW",
        )

    def test_health_yielded(self):
        row = health_check_service(
            "fun",
            {
                "gate": "PLAYER_FIRST_OR_BUSY",
                "findings": ["PLAYER_FIRST"],
                "parallel_ready": [],
            },
        )
        self.assertEqual(row["status"], "YIELDED")
        self.assertFalse(row["detach"])

    def test_bad_contract(self):
        with self.assertRaises(NeedLoadBalanceError):
            load_contract(__file__)


if __name__ == "__main__":
    unittest.main()
