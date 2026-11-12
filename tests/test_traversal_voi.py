"""Regression: Sim walk is transit to a real goal, camera is independent."""
from __future__ import annotations

import copy
import unittest

from betterinstincts.household_navigation import plan_household_navigation
from betterinstincts.traversal_voi import evaluate_traversal_voi
from betterinstincts.host_stack import evaluate_turn
from scripts.check_voi_traversal_harness import check as check_harness


def goal(domain="NEEDS", direct=False):
    return {
        "goal_id": "goal-eat", "domain": domain, "action_id": "eat_meal",
        "target_id": "fridge", "target_region": "kitchen",
        "affordance_verified": True, "direct_interaction_available": direct,
        "affordance_evidence_ref": "affordance-1",
    }


def observation():
    return {
        "scope_id": "lab-scope", "actor_id": "sim-a",
        "scene": "LIVE_MODE", "scene_revision": "rev-1",
        "observed_scene_revision": "rev-1", "graph_revision": "graph-1", "capture_ref": "cap-1",
        "human_present": False, "queue_verified": True, "queue": [],
        "movement_checkpoint": {
            "source": "HOST_OBSERVED", "proof_ref": "checkpoint-1",
            "scope_id": "lab-scope", "actor_id": "sim-a",
            "goal_id": "goal-eat", "capture_ref": "cap-1",
            "walks_since_goal_action": 0,
        },
    }


def route():
    def region():
        return {"lot_id": "lot-a", "lot_status": "VERIFIED_ON_LOT",
                "observed": True, "floor": 0}
    graph = {
        "scope_id": "lab-scope", "save_scope_id": "lab", "household_id": "hh",
        "lot_id": "lot-a", "actor_id": "sim-a", "game_build": "test-build",
        "scene": "LIVE_MODE", "scene_revision": "rev-1",
        "observed_scene_revision": "rev-1", "graph_revision": "graph-1",
        "objective_id": "goal-eat", "human_present": False,
        "position_source": "HOST_VERIFIED_OBSERVATION",
        "current_region": "living", "mode": "GOAL_ROUTING",
        "goal_region": "kitchen",
        "regions": {"living": region(), "kitchen": region()},
        "passages": [{
            "from": "living", "to": "kitchen", "cost": 1,
            "kind": "WALKABLE_PASSAGE", "verified": True,
            "source": "GAME_ROUTE_PROBE", "lot_id": "lot-a",
            "graph_revision": "graph-1", "bidirectional": True,
        }],
        "trace": [], "failed_transitions": [],
    }
    return plan_household_navigation(graph)


def host_row(kind, **fields):
    data = {
        "kind": kind, "origin": "HOST",
        "actor_id": "sim-a", "goal_id": "goal-eat",
        "capture_ref": "cap-1", "origin_proof_ref": "queue-1",
    }
    data.update(fields)
    return data


class PurposefulTraversalTests(unittest.TestCase):
    def deny_effect(self, result):
        self.assertFalse(result["execute_allowed"])
        self.assertIsNone(result["control_permit"])
        self.assertEqual(result["effects_issued"], 0)
        self.assertFalse(result["camera"]["execute_allowed"])

    def test_one_walk_then_domain_action_is_full_plan_not_queue_spam(self):
        for domain in ("NEEDS", "CAREER", "SKILLS", "WHIMS"):
            with self.subTest(domain=domain):
                r = evaluate_traversal_voi(observation(), goal=goal(domain), route=route())
                self.assertEqual(r["gate"], "SINGLE_GOAL_BOUND_WALK_CANDIDATE")
                self.assertTrue(r["sim"]["walk_candidate"])
                self.assertEqual([x["kind"] for x in r["queue_proposal"]],
                                 ["WALK", "GOAL_ACTION"])
                self.assertEqual(r["queue_proposal"][1]["domain"], domain)
                self.deny_effect(r)

    def test_direct_native_object_interaction_avoids_extraneous_walk(self):
        r = evaluate_traversal_voi(observation(), goal=goal(direct=True))
        self.assertEqual(r["gate"], "PREFER_NATIVE_OBJECT_INTERACTION")
        self.assertEqual([x["kind"] for x in r["queue_proposal"]], ["GOAL_ACTION"])
        self.assertFalse(r["sim"]["walk_candidate"])
        self.deny_effect(r)

    def test_pending_walk_cannot_trigger_another_walk(self):
        o = observation()
        o["queue"] = [host_row("WALK", target_region="kitchen")]
        r = evaluate_traversal_voi(o, goal=goal(), route=route())
        self.assertEqual(r["gate"], "WALK_PENDING_AWAIT_DOMAIN_ACTION")
        self.assertEqual(r["queue_proposal"], [])
        self.deny_effect(r)

    def test_existing_walk_plus_followup_waits_for_real_outcome(self):
        o = observation()
        o["queue"] = [
            host_row("WALK", target_region="kitchen"),
            host_row("GOAL_ACTION", action_id="eat_meal", target_id="fridge"),
        ]
        r = evaluate_traversal_voi(o, goal=goal(), route=route())
        self.assertEqual(r["gate"], "WALK_FOLLOWUP_ALREADY_QUEUED")
        self.assertFalse(r["sim"]["walk_candidate"])
        self.deny_effect(r)

    def test_second_consecutive_walk_is_detected_even_with_valid_goal(self):
        o = observation()
        o["queue"] = [host_row("WALK", target_region="kitchen"),
                      host_row("WALK", target_region="kitchen"),
                      host_row("GOAL_ACTION", action_id="eat_meal", target_id="fridge")]
        r = evaluate_traversal_voi(o, goal=goal(), route=route())
        self.assertEqual(r["gate"], "WALK_SPAM_DETECTED_REOBSERVE")
        self.deny_effect(r)

    def test_walk_before_goal_not_reverse_queue(self):
        o = observation()
        o["queue"] = [host_row("GOAL_ACTION", action_id="eat_meal", target_id="fridge"),
                      host_row("WALK", target_region="kitchen")]
        self.assertEqual(evaluate_traversal_voi(o, goal=goal())["gate"],
                         "WALK_NOT_FOLLOWED_BY_GOAL_ACTION")

    def test_drained_queue_does_not_reset_used_walk_checkpoint(self):
        o = observation()
        o["movement_checkpoint"]["walks_since_goal_action"] = 1
        r = evaluate_traversal_voi(o, goal=goal(), route=route())
        self.assertEqual(r["gate"], "ONE_WALK_USED_AWAIT_OBSERVED_DOMAIN_ACTION")
        self.deny_effect(r)

    def test_missing_checkpoint_and_unknown_origin_fail_closed(self):
        o = observation()
        o.pop("movement_checkpoint")
        self.assertEqual(evaluate_traversal_voi(o, goal=goal(), route=route())["gate"],
                         "MOVEMENT_CHECKPOINT_REOBSERVE_REQUIRED")
        o = observation()
        o["queue"] = [host_row("WALK", origin="UNKNOWN", target_region="kitchen")]
        self.assertEqual(evaluate_traversal_voi(o, goal=goal(), route=route())["gate"],
                         "QUEUE_ORIGIN_UNVERIFIED")

    def test_player_queue_and_presence_yield_without_cancellation(self):
        o = observation()
        o["queue"] = [host_row("WALK", origin="PLAYER", target_region="kitchen")]
        self.assertEqual(evaluate_traversal_voi(o, goal=goal())["gate"],
                         "YIELD_TO_PLAYER_QUEUE")
        o = observation()
        o["human_present"] = True
        self.assertEqual(evaluate_traversal_voi(o, goal=goal())["gate"],
                         "YIELD_TO_PLAYER")

    def test_stale_scene_route_or_cross_actor_abstain(self):
        o = observation()
        o["observed_scene_revision"] = "old"
        self.assertEqual(evaluate_traversal_voi(o, goal=goal(), route=route())["gate"],
                         "REOBSERVE_SCENE_QUEUE_OR_PRESENCE")
        o = observation()
        bad = dict(route(), actor_id="different")
        self.assertEqual(evaluate_traversal_voi(o, goal=goal(), route=bad)["gate"],
                         "SIM_ROUTE_STALE_OR_UNVERIFIED")
        o = observation()
        old_graph = dict(route(), graph_revision="stale-graph")
        self.assertEqual(evaluate_traversal_voi(o, goal=goal(), route=old_graph)["gate"],
                         "SIM_ROUTE_STALE_OR_UNVERIFIED")
        o["movement_checkpoint"]["scope_id"] = "other-save"
        self.assertEqual(evaluate_traversal_voi(o, goal=goal(), route=route())["gate"],
                         "MOVEMENT_CHECKPOINT_REOBSERVE_REQUIRED")

    def test_camera_has_separate_voi_advice_and_cannot_walk_without_route(self):
        o = observation()
        o.update(
            target_visible=False, camera_capture_ref="cap-1",
            camera_revision="cam-2",
            voi_estimates={
                "passive": {"gain": 0.1, "cost": 0.0, "risk": 0.0},
                "camera": {"gain": 0.8, "cost": 0.1, "risk": 0.0},
                "sim": {"gain": 1.0, "cost": 0.0, "risk": 0.0},
            },
        )
        r = evaluate_traversal_voi(o, goal=goal())
        self.assertEqual(r["camera"]["next"], "NAMED_CAMERA_REFRAME_LEASE_REQUIRED")
        self.assertTrue(r["camera"]["motion_candidate"])
        self.assertEqual(r["gate"], "CAMERA_REOBSERVE_BEFORE_SIM_WALK")
        self.assertFalse(r["sim"]["walk_candidate"])
        self.deny_effect(r)

    def test_bad_vois_missing_affordance_and_no_inferred_route(self):
        o = observation()
        o["voi_estimates"] = {
            "passive": {"gain": 0.0, "cost": 0.0, "risk": 0.0},
            "camera": {"gain": float("nan"), "cost": 0.0, "risk": 0.0},
            "sim": {"gain": 1.0, "cost": 0.0, "risk": 0.0},
        }
        self.assertEqual(evaluate_traversal_voi(o, goal=goal(), route=route())["gate"],
                         "VOI_ESTIMATE_INVALID")
        g = goal()
        g["affordance_verified"] = False
        self.assertEqual(evaluate_traversal_voi(observation(), goal=g, route=route())["gate"],
                         "ATTEST_DOMAIN_AFFORDANCE_FIRST")

    def test_host_plan_walk_budget_requires_goaled_voi_evidence(self):
        needs = {"hunger": 0.6, "bladder": 0.7, "energy": 0.8,
                 "hygiene": 0.7, "fun": 0.7, "social": 0.6}
        o = observation()
        o.update(goal=goal(), route=route(), requested_action_kind="WALK")
        r = evaluate_turn(needs, capture_ref="cap-1", queue=[],
                          multitasking=False, traversal_voi_observation=o)
        self.assertEqual(r["traversal_voi"]["gate"],
                         "SINGLE_GOAL_BOUND_WALK_CANDIDATE")
        self.assertEqual(r["queue_capacity"]["max_new_actions"], 1)
        # An emptied queue does not allow a second walk without goal action.
        o["movement_checkpoint"]["walks_since_goal_action"] = 1
        r = evaluate_turn(needs, capture_ref="cap-1", queue=[],
                          multitasking=False, traversal_voi_observation=o)
        self.assertEqual(r["queue_capacity"]["gate"], "VOI_WALK_DENIED")
        self.assertFalse(r["queue_capacity"]["enqueue_allowed"])
        self.assertEqual(r["traversal_voi"]["gate"],
                         "ONE_WALK_USED_AWAIT_OBSERVED_DOMAIN_ACTION")
        # Camera requests do not consume or bypass physical movement budget.
        o["requested_action_kind"] = "GOAL_ACTION"
        r = evaluate_turn(needs, capture_ref="cap-1", queue=[],
                          multitasking=False, traversal_voi_observation=o)
        self.assertTrue(r["queue_capacity"]["enqueue_allowed"])
        self.assertFalse(r["traversal_voi"]["sim"]["walk_candidate"])

    def test_host_plan_capture_mismatch_and_player_control_fail_closed(self):
        needs = {"hunger": 0.6, "bladder": 0.7, "energy": 0.8,
                 "hygiene": 0.7, "fun": 0.7, "social": 0.6}
        o = observation()
        o.update(goal=goal(), route=route(), requested_action_kind="WALK")
        r = evaluate_turn(needs, capture_ref="later-cap", queue=[],
                          multitasking=False, traversal_voi_observation=o)
        self.assertEqual(r["queue_capacity"]["gate"], "VOI_WALK_DENIED")
        r = evaluate_turn(needs, capture_ref="cap-1", queue=[],
                          multitasking=False, player_directed=True,
                          traversal_voi_observation=o)
        self.assertIn(r["traversal_voi"]["gate"],
                      {"YIELD_TO_PLAYER", "REOBSERVE_SCENE_QUEUE_OR_PRESENCE"})
        self.assertFalse(r["queue_capacity"]["enqueue_allowed"])
        self.assertEqual(r["queue_capacity"]["gate"], "PLAYER_QUEUE_YIELD")
        r = evaluate_turn(needs, capture_ref="cap-1", queue=[],
                          multitasking=False, already_busy=True,
                          traversal_voi_observation=o)
        self.assertEqual(r["queue_capacity"]["gate"], "HOST_BUSY_YIELD")

    def test_no_mutation_and_harness_smoke(self):
        o, g, r = observation(), goal(), route()
        before = copy.deepcopy((o, g, r))
        result = evaluate_traversal_voi(o, goal=g, route=r)
        self.assertEqual((o, g, r), before)
        self.deny_effect(result)
        check_harness()


if __name__ == "__main__":
    unittest.main()
