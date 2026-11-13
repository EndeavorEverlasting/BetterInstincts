"""Convolutional offline learning: real updates, heldout, replay and player gates."""
from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch as mock_patch

from betterinstincts.spatial_convolution import (
    PATCH_SCHEMA, SpatialConvolutionError, advise, empty_model, learn,
    load_local_model, record_local_sample,
)
from betterinstincts.household_navigation import plan_household_navigation
from tests.test_household_navigation import world


def snapshot():
    data = world(goal="b")
    data["player_directed"] = False
    return data


def grid(blocked=False):
    cells = []
    for y in range(5):
        row = []
        for x in range(5):
            is_blocked = blocked and (x + y) % 3 != 0 and (x, y) != (4, 4)
            row.append([0, 1, 0] if is_blocked else [1, 0, int((x, y) == (4, 4))])
        cells.append(row)
    return {"schema": PATCH_SCHEMA, "source": "OPERATOR_REVIEWED_GEOMETRY",
            "graph_revision": "graph-1", "geometry_ref": "geometry-1",
            "floor": 0, "cells": cells}


def event(i, blocked=False):
    return {
        "event_ref": "evt-%d" % i, "source": "OPERATOR_VERIFIED_TRAVERSAL",
        "sensor_verified": False, "operator_reviewed": True,
        "scope_id": "lab-save/household/lot", "actor_id": "actor-opaque",
        "scene_revision": "scene-1", "graph_revision": "graph-1",
        "game_build": "synthetic-fixture",
        "from_region": "a", "to_region": "b",
        "before_capture_ref": "before-%d" % i, "after_capture_ref": "after-%d" % i,
        "player_interrupted": False, "outcome": "BLOCKED" if blocked else "SUCCESS",
        "observed_region": "a" if blocked else "b",
    }


class SpatialConvolutionTests(unittest.TestCase):
    def test_baseline_navigation_identical_without_explicit_opt_in(self):
        data = snapshot()
        baseline = plan_household_navigation(data)
        self.assertNotIn("spatial_learning_advisory", baseline)
        self.assertEqual(baseline["route"], ["a", "b"])
        self.assertFalse(baseline["execute_allowed"])
        with self.assertRaisesRegex(SpatialConvolutionError, "OPT_IN"):
            learn(data, event(1), grid())

    def test_training_updates_filters_not_only_statistics(self):
        data = snapshot()
        original = empty_model(data)
        changed = None
        for i in range(60):
            new, state = learn(data, event(i, i % 2 == 1), grid(i % 2 == 1),
                               prior=changed or original, explicit_opt_in=True)
            changed = new
        self.assertNotEqual(changed["filters"], original["filters"])
        self.assertGreater(changed["trained"], 20)
        self.assertGreater(changed["heldout"], 0)
        self.assertEqual(changed["trained"] + changed["heldout"], 60)
        self.assertEqual(changed["positive"] + changed["negative"], changed["trained"])
        result = advise(data, changed, grid(), from_region="a", to_region="b")
        self.assertIn(result["status"], {"CALIBRATED_ADVISORY", "ABSTAIN_UNCALIBRATED"})
        self.assertFalse(result["execute_allowed"])

    def test_heldout_does_not_backpropagate(self):
        data = snapshot()
        seed = empty_model(data)
        for i in range(100):
            candidate, state = learn(data, event(i), grid(), prior=seed,
                                     explicit_opt_in=True)
            if state == "HELDOUT_VALIDATION_ONLY":
                self.assertEqual(candidate["filters"], seed["filters"])
                self.assertEqual(candidate["head"], seed["head"])
                self.assertEqual(candidate["head_bias"], seed["head_bias"])
                self.assertEqual(candidate["heldout"], 1)
                self.assertEqual(candidate["trained"], 0)
                break
        else:
            self.fail("deterministic holdout not found")

    def test_replay_provenance_and_invalid_shapes_refused(self):
        data = snapshot()
        learned, _ = learn(data, event(1), grid(), explicit_opt_in=True)
        repeated, status = learn(data, event(1), grid(), prior=learned,
                                 explicit_opt_in=True)
        self.assertEqual(status, "REPLAY_IGNORED")
        self.assertEqual(learned, repeated)
        forged = event(2)
        forged["before_capture_ref"] = "before-1"
        repeated, status = learn(data, forged, grid(), prior=learned,
                                 explicit_opt_in=True)
        self.assertEqual(status, "REPLAY_IGNORED")
        malformed = grid()
        malformed["cells"][0][0] = [float("nan"), 0, 0]
        with self.assertRaisesRegex(SpatialConvolutionError, "CELL"):
            learn(data, event(3), malformed, explicit_opt_in=True)
        tampered = copy.deepcopy(learned)
        tampered["filters"][0][0][0][0] = float("inf")
        with self.assertRaisesRegex(SpatialConvolutionError, "WEIGHT"):
            learn(data, event(4), grid(), prior=tampered, explicit_opt_in=True)

    def test_cross_scope_unknown_edge_and_player_presence_fail_closed(self):
        data = snapshot()
        model, _ = learn(data, event(1), grid(), explicit_opt_in=True)
        for change in ({"human_present": True}, {"observed_scene_revision": "old"},
                       {"save_scope_id": "other-save"}, {"graph_revision": "other-graph"},
                       {"player_directed": True}):
            other = copy.deepcopy(data)
            other.update(change)
            self.assertEqual(advise(other, model, grid(),
                                    from_region="a", to_region="b")["status"],
                             "ABSTAIN_INVALID_EVIDENCE")
        self.assertEqual(advise(data, model, grid(),
                                from_region="a", to_region="d")["status"],
                         "ABSTAIN_INVALID_EVIDENCE")
        bad = grid()
        bad["source"] = "SCREENSHOT_GUESS"
        with self.assertRaises(SpatialConvolutionError):
            learn(data, event(3), bad, explicit_opt_in=True)

    def test_advisory_is_integrated_without_mutating_route_or_effects(self):
        data = snapshot()
        model = empty_model(data)
        before = plan_household_navigation(data)
        data["spatial_convolution"] = {
            "model": model, "patch": grid(),
            "from_region": "a", "to_region": "b",
        }
        after = plan_household_navigation(data)
        self.assertEqual(before["route"], after["route"])
        self.assertEqual(before["next_region"], after["next_region"])
        self.assertEqual(after["spatial_learning_advisory"]["status"],
                         "ABSTAIN_UNCALIBRATED")
        self.assertEqual(after["effects_issued"], 0)
        self.assertIsNone(after["control_permit"])
        data["spatial_convolution"]["to_region"] = "c"
        self.assertEqual(plan_household_navigation(data)["spatial_learning_advisory"]["status"],
                         "ABSTAIN_TARGET_MISMATCH")
        data["human_present"] = True
        self.assertNotIn("spatial_learning_advisory", plan_household_navigation(data))

    def test_storage_opt_in_atomic_and_profile_separation(self):
        with tempfile.TemporaryDirectory() as tmp:
            use = Path(tmp) / "app"
            with mock_patch("bootstrap.paths", return_value={"use": use}):
                data = snapshot()
                with self.assertRaises(SpatialConvolutionError):
                    record_local_sample(data, event(1), grid())
                one = record_local_sample(data, event(1), grid(), explicit_opt_in=True)
                repeat = record_local_sample(data, event(1), grid(), explicit_opt_in=True)
                self.assertIn(one["status"], {"TRAINED_OBSERVED_SAMPLE", "HELDOUT_VALIDATION_ONLY"})
                self.assertEqual(repeat["status"], "REPLAY_IGNORED")
                self.assertEqual(load_local_model(data)["trained"] +
                                 load_local_model(data)["heldout"], 1)
                other = snapshot()
                other["save_scope_id"] = "different"
                self.assertEqual(load_local_model(other)["trained"], 0)
                self.assertEqual(load_local_model(other)["heldout"], 0)


if __name__ == "__main__":
    unittest.main()
