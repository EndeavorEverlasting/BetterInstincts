"""P82 adversarial tests for locally adaptive, non-actuating Sims travel costs."""
from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from betterinstincts.household_navigation import plan_household_navigation
from betterinstincts.traversal_cost_learning import (
    TraversalLearningError, apply_learned_costs, context_hash, empty_model,
    learn_transition, load_local_model, record_local_transition,
)
from betterinstincts import host_listener
from tests.test_household_navigation import world


def fixture():
    data = world()
    data["player_directed"] = False
    # Real exact-build adapters must provide these independently sourced
    # baselines. The synthetic test does not pretend they exist in a game.
    for passage in data["passages"]:
        passage["expected_ms"] = 1_000
    return data


def event(*, outcome="SUCCESS", event_ref="event-1", elapsed_ms=3_000):
    return {
        "schema": "betterinstincts.traversal-transition/v1",
        "event_ref": event_ref,
        "source": "GAME_ROUTE_PROBE",
        "operator_reviewed": False,
        "sensor_verified": True,
        "player_interrupted": False,
        "scope_id": "lab-save/household/lot",
        "actor_id": "actor-opaque",
        "scene_revision": "scene-1",
        "from_region": "a",
        "to_region": "b",
        "before_capture_ref": "capture-before-1",
        "after_capture_ref": "capture-after-1",
        "outcome": outcome,
        "elapsed_ms": elapsed_ms if outcome == "SUCCESS" else None,
    }


def observed(data, outcome="SUCCESS"):
    result = copy.deepcopy(data)
    result["current_region"] = "b" if outcome == "SUCCESS" else "a"
    return result


class TraversalCostLearningTests(unittest.TestCase):
    def test_baseline_is_unchanged_before_evidence(self):
        data = fixture()
        self.assertEqual(plan_household_navigation(data)["route"], ["a", "b", "d"])
        self.assertEqual(plan_household_navigation(data)["learning_status"], "NO_MODEL_BASELINE_ONLY")

    def test_confirmed_slow_path_improves_next_route_without_new_passages(self):
        data = fixture()
        model, state = learn_transition(observed(data), event())
        self.assertEqual(state, "ACCEPTED_OBSERVED_TRANSITION")
        self.assertEqual(model["seen_count"], 1)
        data["traversal_cost_model"] = model
        result = plan_household_navigation(data)
        self.assertEqual(result["route"], ["a", "c", "d"])
        self.assertEqual(result["learning_status"], "LEARNED_COSTS_APPLIED")
        self.assertEqual(result["learned_edge_count"], 1)
        self.assertEqual(result["effects_issued"], 0)
        self.assertIsNone(result["control_permit"])
        self.assertFalse(result["goal_complete"])

    def test_identical_observation_never_trains_twice(self):
        data = observed(fixture())
        first, state = learn_transition(data, event())
        self.assertEqual(state, "ACCEPTED_OBSERVED_TRANSITION")
        second, status = learn_transition(data, event(), prior=first)
        self.assertEqual(status, "REPLAY_OR_BLOOM_COLLISION_IGNORED")
        self.assertEqual(second, first)

    def test_real_failure_increases_penalty_without_false_arrival(self):
        data = fixture()
        model, _ = learn_transition(observed(data, outcome="BLOCKED"),
                                    event(outcome="BLOCKED"))
        data["traversal_cost_model"] = model
        result = plan_household_navigation(data)
        self.assertEqual(result["route"], ["a", "c", "d"])
        self.assertEqual(model["edges"][0]["successes"], 0)
        self.assertEqual(model["edges"][0]["observations"], 1)

    def test_missing_timing_baseline_or_unverified_edge_refuses_learning(self):
        data = observed(world())
        data["player_directed"] = False
        with self.assertRaisesRegex(TraversalLearningError, "BASELINE_EDGE"):
            learn_transition(data, event())
        data = observed(fixture())
        data["passages"][0]["source"] = "CAMERA_HINT"
        with self.assertRaisesRegex(TraversalLearningError, "BASELINE_EDGE"):
            learn_transition(data, event())
        data = fixture()
        data["traversal_cost_model"] = empty_model(data)
        self.assertEqual(plan_household_navigation(data)["route"], ["a", "b", "d"])

    def test_player_interruption_stale_scene_and_unknown_source_refuse(self):
        for key, value in (
            ("human_present", True),
            ("observed_scene_revision", "scene-stale"),
            ("scene", "BUILD_MODE"),
            ("position_source", None),
            ("player_directed", True),
        ):
            data = observed(fixture())
            data[key] = value
            with self.subTest(key=key), self.assertRaises(TraversalLearningError):
                learn_transition(data, event())
        e = event()
        e["source"] = "CAMERA_PAN"
        with self.assertRaisesRegex(TraversalLearningError, "SOURCE_ATTESTATION"):
            learn_transition(observed(fixture()), e)
        e = event()
        e["player_interrupted"] = True
        with self.assertRaises(TraversalLearningError):
            learn_transition(observed(fixture()), e)

    def test_success_must_finish_at_target_and_have_independent_capture(self):
        for change in (
            {"after_capture_ref": "capture-before-1"},
            {"elapsed_ms": 0},
            {"elapsed_ms": 300_001},
            {"outcome": "CLAIMED_BY_AGENT"},
            {"extra_private_name": "Sim"},
        ):
            e = event()
            e.update(change)
            with self.subTest(change=change), self.assertRaises(TraversalLearningError):
                learn_transition(observed(fixture()), e)
        with self.assertRaises(TraversalLearningError):
            learn_transition(fixture(), event())

    def test_operator_reviewed_outcome_can_learn_without_host_sensor(self):
        data = observed(fixture())
        e = event()
        e["source"] = "OPERATOR_VERIFIED_TRAVERSAL"
        e["sensor_verified"] = False
        e["operator_reviewed"] = True
        model, state = learn_transition(data, e)
        self.assertEqual(state, "ACCEPTED_OBSERVED_TRANSITION")
        self.assertEqual(model["seen_count"], 1)

    def test_context_changes_never_leak_learned_costs(self):
        data = fixture()
        model, _ = learn_transition(observed(data), event())
        for key, replacement in (
            ("scope_id", "another/save"),
            ("save_scope_id", "other-save"),
            ("household_id", "other-household"),
            ("lot_id", "other-lot"),
            ("graph_revision", "graph-new"),
            ("game_build", "unknown-patch"),
        ):
            other = fixture()
            other[key] = replacement
            other["traversal_cost_model"] = model
            result = plan_household_navigation(other)
            if key == "lot_id":
                # Unverified regions fail before any model consideration.
                self.assertNotEqual(result["state"], "NAVIGATION_ROUTE_PROPOSED")
            elif key == "graph_revision":
                self.assertNotEqual(result["state"], "NAVIGATION_ROUTE_PROPOSED")
            else:
                self.assertEqual(result["route"], ["a", "b", "d"])
                self.assertEqual(result["learning_status"], "INVALID_OR_CROSS_SCOPE_MODEL_BASELINE_ONLY")

    def test_corrupt_prediction_falls_back_without_side_effects(self):
        data = fixture()
        model, _ = learn_transition(observed(data), event())
        model["edges"][0]["mean_ratio"] = float("nan")
        data["traversal_cost_model"] = model
        result = plan_household_navigation(data)
        self.assertEqual(result["route"], ["a", "b", "d"])
        self.assertEqual(result["learning_status"], "INVALID_OR_CROSS_SCOPE_MODEL_BASELINE_ONLY")
        self.assertFalse(result["execute_allowed"])

    def test_opaque_profile_is_not_raw_save_name(self):
        data = fixture()
        self.assertEqual(len(context_hash(data)), 64)
        self.assertNotIn("lab-save", context_hash(data))

    def test_opt_in_storage_is_bounded_atomic_and_replay_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            use = Path(tmp) / "app"
            with patch("bootstrap.paths", return_value={"use": use}):
                data = observed(fixture())
                with self.assertRaisesRegex(TraversalLearningError, "OPT_IN"):
                    record_local_transition(data, event())
                first = record_local_transition(data, event(), explicit_opt_in=True)
                self.assertEqual(first["status"], "ACCEPTED_OBSERVED_TRANSITION")
                self.assertEqual(first["seen_count"], 1)
                repeat = record_local_transition(data, event(), explicit_opt_in=True)
                self.assertEqual(repeat["seen_count"], 1)
                self.assertEqual(repeat["status"], "REPLAY_OR_BLOOM_COLLISION_IGNORED")
                self.assertEqual(load_local_model(data)["seen_count"], 1)
                paths = list((Path(tmp) / "runtime" / "learning").glob("*.json"))
                self.assertEqual(len(paths), 1)
                self.assertEqual(paths[0].stem, context_hash(data))
                other = fixture()
                other["save_scope_id"] = "new-save"
                self.assertEqual(load_local_model(other)["seen_count"], 0)

    def test_host_listener_requires_activated_session_and_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            use = Path(tmp) / "app"
            with (patch("bootstrap.paths", return_value={"use": use}),
                  patch.object(host_listener, "OUTPUT", Path(tmp) / "host-listener")):
                data = observed(fixture())
                with self.assertRaises(host_listener.HostListenerError):
                    host_listener.observe_traversal_transition(
                        "demo-session", data, event(), explicit_opt_in=True)
                host_listener.activate("demo-session")
                with self.assertRaises(host_listener.HostListenerError):
                    host_listener.observe_traversal_transition("demo-session", data, event())
                receipt = host_listener.observe_traversal_transition(
                    "demo-session", data, event(), explicit_opt_in=True)
                self.assertEqual(receipt["seen_count"], 1)
                plan = host_listener.plan_learned_traversal(
                    "demo-session", fixture(), explicit_opt_in=True)
                self.assertEqual(plan["route"], ["a", "c", "d"])
                self.assertFalse(plan["execute_allowed"])
                host_listener.deactivate("demo-session")
                with self.assertRaises(host_listener.HostListenerError):
                    host_listener.plan_learned_traversal(
                        "demo-session", fixture(), explicit_opt_in=True)


if __name__ == "__main__":
    unittest.main()
