"""Offline PS-0245 Bellman/KKT contracts: synthetic tests, NOT game proof."""
from __future__ import annotations

import math
import unittest

from betterinstincts.activity_chain import compile_activity_chain
from betterinstincts.decision_horizon import (
    DecisionHorizonError, allocate_continuous_time, optimize_activity_plan,
)

CAPTURE = "cap-245"


def snapshot(**changes):
    data = {
        "schema": "betterinstincts.activity-chain/v1",
        "capture_ref": CAPTURE, "mode": "PLANNING",
        "sim_ref": "actor-1", "selected_sim_ref": "actor-1",
        "household_ref": "house-1", "location": "home",
        "scene_verified": True, "queue_verified": True,
        "player_directed": False, "player_active": False,
        "queue_owner": "AUTONOMY", "queue_depth": 0, "queue_capacity": 2,
        "needs_safe": True, "needs": {"energy": 75, "hunger": 85},
        "need_rates": {"energy": -0.1, "hunger": -0.1},
        "need_floors": {"energy": 20, "hunger": 30},
        "skills": {"gardening": 1}, "inventory": {},
        "minutes_until_work": 60, "minutes_until_need_floor": 60,
        "reserve_minutes": 0, "available_funds": 100,
        "blocked_resources": [], "completed": [],
        "teleport_unlocked": True, "teleport_evidence_ref": "proof-teleport",
        "teleport_evidence_capture_ref": CAPTURE,
    }
    data.update(changes)
    return data


def step(identity, *, place="home", after=None, duration=1, value=1,
         cost=0, effects=None, probability=1.0, deadline=100):
    return {
        "id": identity, "domain": "gardening", "kind": "ACTIVITY",
        "location": place, "evidence_ref": "observed-" + identity,
        "after": [] if after is None else list(after),
        "resources": [], "upper_minutes": duration,
        "deadline_minutes": deadline, "value": value, "cost": cost,
        "effects": effects or {}, "success_probability": probability,
    }


def routes():
    return [
        {"from": "home", "to": "computer", "method": "WALK",
         "upper_minutes": 1, "admitted": True, "capture_ref": CAPTURE,
         "evidence_ref": "walk-computer"},
        {"from": "computer", "to": "garden", "method": "WALK",
         "upper_minutes": 13, "admitted": True, "capture_ref": CAPTURE,
         "evidence_ref": "walk-garden"},
        {"from": "computer", "to": "garden", "method": "TELEPORT",
         "upper_minutes": 1, "admitted": True, "capture_ref": CAPTURE,
         "evidence_ref": "observed-teleport-garden"},
    ]


def chain():
    return [
        step("purchase", place="computer", duration=1, value=0, cost=20,
             effects={"inventory_delta": {"fertilizer": 1}}),
        step("fertilize", place="garden", after=["purchase"], duration=1,
             value=25, effects={"requires_inventory": {"fertilizer": 1},
                                "skill_delta": {"gardening": 0.1}}),
    ]


def plan(state, actions, paths=(), **settings):
    return optimize_activity_plan(state, actions, paths,
                                  capture_ref=CAPTURE, **settings)


class BellmanPlannerTests(unittest.TestCase):
    def test_precondition_chain_and_teleport(self):
        result = plan(snapshot(), chain(), routes(), horizon_minutes=5)
        self.assertEqual(result["gate"], "FORECAST_STAGED_NOT_DISPATCHABLE")
        self.assertEqual([s["step_id"] for s in result["forecast_steps"]],
                         ["purchase", "fertilize"])
        self.assertEqual(result["forecast_steps"][1]["travel"]["method"],
                         "TELEPORT")
        self.assertEqual(result["projected_funds"], 80)
        self.assertLessEqual(result["projected_minutes"], 5)
        self.assertFalse(result["execute_allowed"])
        self.assertIsNone(result["control_permit"])

    def test_horizon_beats_deadline_greedy_on_fixed_counterexample(self):
        # Greedy earliest deadline starts an expendable task, then buys a
        # prerequisite that cannot be used before the work deadline.
        actions = [step("diversion", duration=3, value=5, deadline=3)] + chain()
        state = snapshot(minutes_until_work=5, minutes_until_need_floor=5)
        baseline = compile_activity_chain(state, actions, routes(),
                                          capture_ref=CAPTURE)
        optimized = plan(state, actions, routes(), horizon_minutes=5)
        self.assertEqual(baseline["gate"], "DEFER_UNFINISHED_PURCHASE_CHAIN")
        self.assertEqual([r["step_id"] for r in optimized["forecast_steps"]],
                         ["purchase", "fertilize"])
        self.assertGreater(optimized["expected_net_utility"], 0)
        # This is a synthetic fixture only; NO observed gameplay gain.

    def test_teleport_needs_same_capture_unlock(self):
        state = snapshot(teleport_unlocked=False,
                         teleport_evidence_ref=None)
        result = plan(state, chain(), routes(), horizon_minutes=5)
        self.assertEqual(result["forecast_steps"], [])
        self.assertEqual(result["gate"], "NO_POSITIVE_FEASIBLE_PLAN")
        stale = snapshot(teleport_evidence_capture_ref="old-cap")
        self.assertEqual(plan(stale, chain(), routes(), horizon_minutes=5)
                         ["forecast_steps"], [])

    def test_no_purchase_without_money(self):
        result = plan(snapshot(available_funds=0), chain(), routes())
        self.assertIsNone(result["next_step"])
        self.assertIn("TIME_DEADLINE_OR_FUNDS",
                      result["binding_or_blocking_constraints"])

    def test_no_action_without_stock_even_if_prior_step_marked_complete(self):
        completed = [{"step_id": "purchase", "outcome_ref": "proof-purchase",
                      "outcome_capture_ref": CAPTURE}]
        result = plan(snapshot(completed=completed), chain(), routes(),
                      horizon_minutes=5)
        self.assertIsNone(result["next_step"])
        self.assertIn("INVENTORY_PRECONDITION",
                      result["binding_or_blocking_constraints"])

    def test_stale_completion_or_unreconciled_inflight_abstains(self):
        recorded = [{"step_id": "purchase", "outcome_ref": "proof-purchase",
                     "outcome_capture_ref": "old-capture"}]
        stale = plan(snapshot(completed=recorded), chain(), routes())
        self.assertEqual(stale["gate"], "REVALIDATE_PREVIOUS_COMPLETIONS")
        pending = plan(snapshot(inflight_step="purchase"), chain(), routes())
        self.assertEqual(pending["gate"], "RECONCILE_INFLIGHT_BEFORE_REPLAY")

    def test_interruption_player_and_wrong_portrait_yield(self):
        a = [step("rest", value=10)]
        self.assertEqual(plan(snapshot(player_directed=True), a)
                         ["gate"], "PLAYER_FIRST")
        self.assertEqual(plan(snapshot(interrupted=True), a)
                         ["gate"], "REVALIDATE_CHECKPOINT_AFTER_INTERRUPTION")
        self.assertEqual(plan(snapshot(selected_sim_ref="other"), a)
                         ["gate"], "ACTOR_QUEUE_OR_PLAYER_REVALIDATION_REQUIRED")
        self.assertEqual(plan(snapshot(player_active=True), a)
                         ["gate"], "ACTOR_QUEUE_OR_PLAYER_REVALIDATION_REQUIRED")
        self.assertEqual(plan(snapshot(queue_depth=2), a)
                         ["gate"], "QUEUE_OWNERSHIP_OR_CAPACITY")

    def test_stale_capture_and_queue_ownership(self):
        one = [step("rest", value=10)]
        self.assertEqual(plan(snapshot(capture_ref="stale"), one)
                         ["gate"], "REOBSERVE_SCENE_AND_QUEUE")
        self.assertEqual(plan(snapshot(queue_owner="PLAYER"), one)
                         ["gate"], "ACTOR_QUEUE_OR_PLAYER_REVALIDATION_REQUIRED")
        self.assertEqual(plan(snapshot(checkpoint_capture_ref="older"), one)
                         ["gate"], "REVALIDATE_CHECKPOINT_AFTER_INTERRUPTION")

    def test_need_rate_can_make_action_infeasible(self):
        state = snapshot(needs={"energy": 22, "hunger": 80},
                         need_rates={"energy": -10, "hunger": 0},
                         need_floors={"energy": 20, "hunger": 30})
        result = plan(state, [step("study", duration=1, value=50)])
        self.assertEqual(result["gate"], "NO_POSITIVE_FEASIBLE_PLAN")
        self.assertIn("NEED_FLOOR", result["binding_or_blocking_constraints"])

    def test_probabilistic_failure_penalty_affects_policy(self):
        actions = [
            step("unsafe-return", value=20, probability=0.1),
            step("reliable-work", value=8, probability=1.0),
        ]
        result = plan(snapshot(), actions, horizon_minutes=1)
        self.assertEqual(result["next_step"]["step_id"], "reliable-work")
        self.assertEqual(result["failure_recovery"],
                         "REOBSERVE_AND_RECONCILE_NO_BLIND_RETRY")

    def test_noop_does_not_loop_and_search_is_bounded(self):
        action = [step("noop", duration=0.1, value=0)]
        self.assertEqual(plan(snapshot(), action)["forecast_steps"], [])
        numerous = [step("thing-" + str(i), value=5) for i in range(10)]
        result = plan(snapshot(), numerous, max_expansions=2)
        self.assertEqual(result["gate"], "BOUNDED_SEARCH_PARTIAL_REVIEW")
        self.assertLessEqual(result["expansions"], 2)
        self.assertFalse(result["execute_allowed"])
        self.assertEqual(len({x["step_id"] for x in result["forecast_steps"]}),
                         len(result["forecast_steps"]))

    def test_block_cheats_irreversible_and_invalid_probabilities(self):
        irreversible = step("sell", value=1000)
        irreversible["irreversible"] = True
        self.assertIsNone(plan(snapshot(), [irreversible])["next_step"])
        cheating = step("funds", value=100)
        cheating["cheat"] = True
        with self.assertRaises(DecisionHorizonError):
            plan(snapshot(), [cheating])
        out_of_range = step("risky", probability=2)
        with self.assertRaises(DecisionHorizonError):
            plan(snapshot(), [out_of_range])

    def test_typed_bounds_and_missing_state_fields(self):
        with self.assertRaises(DecisionHorizonError):
            plan(snapshot(need_rates={"energy": 0}), [step("eat")])
        with self.assertRaises(DecisionHorizonError):
            plan(snapshot(), [step("eat")], max_expansions=2001)
        with self.assertRaises(DecisionHorizonError):
            plan(snapshot(shadow_prices={"player": 10}), [step("eat")])
        with self.assertRaises(DecisionHorizonError):
            plan(snapshot(), [step(str(i)) for i in range(25)])


class KktRelaxationTests(unittest.TestCase):
    def test_binding_budget_stationarity_and_dual_price(self):
        result = allocate_continuous_time(4, {
            "skills": {"weight": 5, "max_minutes": 10},
            "leisure": {"weight": 2, "max_minutes": 10},
        })
        amounts = result["allocations_minutes"]
        self.assertAlmostEqual(sum(amounts.values()), 4, places=6)
        self.assertTrue(result["budget_binding"])
        self.assertGreater(result["shadow_price_lambda"], 0)
        self.assertLess(result["interior_kkt_residual"], 1e-6)
        self.assertAlmostEqual(5 / (1 + amounts["skills"]),
                               2 / (1 + amounts["leisure"]), places=6)
        self.assertFalse(result["execute_allowed"])

    def test_nonbinding_cap_and_zero_budget(self):
        policies = {
            "focus": {"weight": 3, "max_minutes": 2},
            "rest": {"weight": 2, "max_minutes": 1},
        }
        free = allocate_continuous_time(10, policies)
        self.assertEqual(free["allocations_minutes"], {"focus": 2, "rest": 1})
        self.assertFalse(free["budget_binding"])
        self.assertEqual(free["shadow_price_lambda"], 0)
        zero = allocate_continuous_time(0, policies)
        self.assertEqual(sum(zero["allocations_minutes"].values()), 0)
        self.assertTrue(zero["budget_binding"])

    def test_invalid_and_nan_rejected(self):
        with self.assertRaises(DecisionHorizonError):
            allocate_continuous_time(float("nan"), {
                "rest": {"weight": 1, "max_minutes": 3}
            })
        with self.assertRaises(DecisionHorizonError):
            allocate_continuous_time(10, {
                "rest": {"weight": -1, "max_minutes": 3}
            })


if __name__ == "__main__":
    unittest.main()
