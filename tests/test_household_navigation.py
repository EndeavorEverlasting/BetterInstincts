"""P82 synthetic navigation and P00 safety regression suite."""
from __future__ import annotations

import copy
import unittest

from betterinstincts.household_navigation import plan_household_navigation
from betterinstincts.room_map_traverse import plan_semantic_region_route


def world(mode="GOAL_ROUTING", goal="d"):
    def edge(a, b, cost=1):
        return {"from": a, "to": b, "cost": cost, "kind": "WALKABLE_PASSAGE",
                "verified": True, "source": "GAME_ROUTE_PROBE", "lot_id": "lab-lot",
                "graph_revision": "graph-1", "bidirectional": True}
    return {
        "scope_id": "lab-save/household/lot", "save_scope_id": "lab-save",
        "household_id": "household", "lot_id": "lab-lot", "actor_id": "actor-opaque",
        "game_build": "synthetic-fixture", "scene": "LIVE_MODE",
        "scene_revision": "scene-1", "observed_scene_revision": "scene-1",
        "graph_revision": "graph-1", "objective_id": "objective-1",
        "human_present": False, "position_source": "HOST_VERIFIED_OBSERVATION",
        "current_region": "a", "mode": mode, "goal_region": goal,
        "regions": {r: {"lot_id": "lab-lot", "lot_status": "VERIFIED_ON_LOT",
                        "observed": True, "floor": 0} for r in "abcd"},
        "passages": [edge("a", "b"), edge("a", "c"),
                     edge("b", "d"), edge("c", "d")],
        "visited_regions": ["a"], "trace": [], "failed_transitions": []
    }


def trace(data, *regions):
    data["trace"] = [{"scope_id": data["scope_id"], "actor_id": data["actor_id"],
                      "region_id": r, "progress": False} for r in regions]
    data["current_region"] = regions[-1]
    return data


class HouseholdNavigationTests(unittest.TestCase):
    def assert_no_effect(self, plan):
        self.assertFalse(plan["execute_allowed"])
        self.assertIsNone(plan["control_permit"])
        self.assertEqual(plan["effects_issued"], 0)
        self.assertFalse(plan["goal_complete"])

    def test_verified_route_is_cost_minimal_and_deterministic(self):
        data = world()
        first = plan_household_navigation(data)
        self.assertEqual(first["route"], ["a", "b", "d"])
        data["passages"].reverse()
        data["regions"] = dict(reversed(list(data["regions"].items())))
        self.assertEqual(plan_household_navigation(data)["route"], first["route"])
        self.assert_no_effect(first)

    def test_weighted_route_can_avoid_expensive_edge(self):
        data = world()
        data["passages"][0]["cost"] = 20
        self.assertEqual(plan_household_navigation(data)["route"], ["a", "c", "d"])

    def test_discovery_only_scans_current_unvisited_region(self):
        data = world(mode="DISCOVERY")
        data["visited_regions"] = []
        plan = plan_household_navigation(data)
        self.assertEqual(plan["state"], "NAVIGATION_OBSERVE_REGION")
        self.assertEqual(plan["next_region"], "a")
        self.assert_no_effect(plan)

    def test_discovery_stable_frontier_selection(self):
        data = world(mode="DISCOVERY")
        plan = plan_household_navigation(data)
        self.assertEqual(plan["route"], ["a", "b"])
        self.assert_no_effect(plan)

    def test_coverage_not_claimed_full_household(self):
        data = world(mode="DISCOVERY")
        data["visited_regions"] = list(data["regions"])
        self.assertEqual(plan_household_navigation(data)["state"], "NAVIGATION_KNOWN_GRAPH_COVERED")

    def test_abab_replans_verified_alternative(self):
        data = trace(world(goal="d"), "a", "b", "a", "b")
        plan = plan_household_navigation(data)
        self.assertEqual(plan["state"], "NAVIGATION_RECOVERY_ROUTE")
        self.assertEqual(plan["route"], ["b", "d"])
        self.assert_no_effect(plan)

    def test_abab_reverse_is_blocked_not_blindly_replayed(self):
        data = trace(world(goal="a"), "a", "b", "a", "b")
        self.assertEqual(plan_household_navigation(data)["route"], ["b", "d", "c", "a"])
        data["passages"] = [data["passages"][0]]
        plan = plan_household_navigation(data)
        self.assertEqual(plan["state"], "NAVIGATION_STALL_ABSTAIN")
        self.assert_no_effect(plan)

    def test_two_failed_transitions_exclude_edge(self):
        data = world()
        data["failed_transitions"] = [{
            "scope_id": data["scope_id"], "actor_id": data["actor_id"],
            "graph_revision": "graph-1", "from": "a", "to": "b", "failures": 2
        }]
        self.assertEqual(plan_household_navigation(data)["route"], ["a", "c", "d"])

    def test_camera_pan_cannot_be_a_sim_passage(self):
        data = world(goal="b")
        data["passages"] = [{
            "from": "a", "to": "b", "cost": 1, "kind": "CAMERA_PAN_HINT",
            "source": "HOST_CAPTURE", "verified": True,
            "lot_id": "lab-lot", "graph_revision": "graph-1", "bidirectional": True
        }]
        plan = plan_household_navigation(data)
        self.assertEqual(plan["state"], "NAVIGATION_NO_SAFE_ROUTE")
        self.assertEqual(plan["excluded_unverified_passages"], 1)
        self.assert_no_effect(plan)

    def test_inferred_passage_is_not_verified_walking(self):
        data = world(goal="b")
        data["passages"] = [dict(data["passages"][0], source="INFERRED")]
        self.assertEqual(plan_household_navigation(data)["state"], "NAVIGATION_NO_SAFE_ROUTE")

    def test_off_lot_goal_is_rejected(self):
        data = world(goal="off-lot")
        data["regions"]["off-lot"] = {
            "lot_id": "lab-lot", "lot_status": "OFF_LOT", "floor": 0, "observed": True
        }
        self.assertEqual(plan_household_navigation(data)["reason"], "GOAL_UNKNOWN_OR_OFF_LOT")

    def test_unverified_current_relocalizes(self):
        data = world()
        data["regions"]["a"]["observed"] = False
        self.assertEqual(plan_household_navigation(data)["state"], "NAVIGATION_RELOCALIZE")

    def test_human_input_or_unknown_presence_yields(self):
        for present in (True, None):
            data = world()
            data["human_present"] = present
            plan = plan_household_navigation(data)
            self.assertEqual(plan["state"], "NAVIGATION_PAUSED_FOR_HUMAN")
            self.assert_no_effect(plan)

    def test_stale_scene_and_unknown_position_abstain(self):
        for field, value in (("observed_scene_revision", "stale"),
                             ("position_source", None)):
            data = world()
            data[field] = value
            self.assertEqual(plan_household_navigation(data)["state"], "NAVIGATION_ABSTAIN")

    def test_history_cannot_cross_actor_or_save(self):
        for field, value in (("actor_id", "other"), ("scope_id", "other-save")):
            data = trace(world(), "a", "b")
            data["trace"][0][field] = value
            self.assertEqual(plan_household_navigation(data)["reason"], "TRACE_STALE_OR_CROSS_SCOPE")

    def test_camera_motion_cannot_be_claimed_as_progress(self):
        data = trace(world(), "a", "a", "a")
        data["trace"][-1].update(progress=True, progress_kind="CAMERA_MOVED",
                                 evidence_ref="frame-1")
        self.assertEqual(plan_household_navigation(data)["reason"], "TRACE_STALE_OR_CROSS_SCOPE")

    def test_arrival_does_not_claim_task_success(self):
        plan = plan_household_navigation(world(goal="a"))
        self.assertEqual(plan["state"], "NAVIGATION_ARRIVED_AWAIT_OUTCOME")
        self.assert_no_effect(plan)

    def test_bounded_route_and_malformed_input(self):
        data = world()
        data["max_route_steps"] = 1
        self.assertEqual(plan_household_navigation(data)["state"], "NAVIGATION_ROUTE_BUDGET_HOLD")
        self.assert_no_effect(plan_household_navigation(None))

    def test_existing_room_map_entrypoint_delegates(self):
        data = world()
        self.assertEqual(plan_semantic_region_route(snapshot=data), plan_household_navigation(data))


if __name__ == "__main__":
    unittest.main()
