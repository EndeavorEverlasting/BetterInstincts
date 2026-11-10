"""P67/P62 synthetic spatial perception cases: safety and relation regression."""
from __future__ import annotations

import unittest

from betterinstincts.scenes import load_catalog
from betterinstincts.spatial_perception import (
    SCHEMA, SpatialPerceptionError, assess_frame,
)
from scripts.spatial_perception_eval import evaluate
from betterinstincts.host_listener import activate, deactivate, tick, HostListenerError
from betterinstincts.player_presence import PresenceProbe


def frame(**kwargs):
    scene = load_catalog()
    live = next(x for x in scene["scenes"] if x["id"] == "live_mode")
    doc = {
        "schema": SCHEMA, "source": "HOST_CAPTURE", "capture_ref": "capture:test",
        "camera_revision": "camA", "game_version": scene["game_version"],
        "scene_id": "live_mode", "scene_cues": live["required_cues"],
        "active_lot_id": "lot_1", "observed_lot_id": "lot_1",
        "width": 640, "height": 480, "objects": [],
    }
    doc.update(kwargs)
    return doc


class SpatialPerceptionTests(unittest.TestCase):
    def test_eval_matrix_all_cases_pass(self):
        result = evaluate()
        self.assertEqual(result["total"], 16)
        self.assertEqual(result["failed"], 0, result["cases"])
        self.assertEqual(result["precision_recall"], "NOT_MEASURED_NO_REAL_IMAGE_GROUND_TRUTH")
        self.assertFalse(result["game_certified"])

    def test_unverified_scene_cannot_promote_observation(self):
        item = {"id": "chair", "kind": "CHAIR", "bbox": [20, 20, 60, 70],
                "confidence": 0.99, "source": "HOST_CV",
                "evidence_ref": "capture:test", "camera_revision": "camA"}
        receipt = assess_frame(frame(scene_cues=[], objects=[item]))
        self.assertEqual(receipt["state"], "SCENE_UNVERIFIED")
        self.assertEqual(receipt["objects"][0]["zone"], "UNVERIFIED")
        self.assertFalse(receipt["execute_allowed"])

    def test_missing_regions_never_infer_inside_house(self):
        receipt = assess_frame(frame())
        self.assertEqual(receipt["state"], "TOPOLOGY_UNVERIFIED")
        self.assertEqual(receipt["camera_side"], "UNVERIFIED")

    def test_bool_coordinates_and_nan_confidence_rejected(self):
        for change in ({"bbox": [True, 1, 20, 30], "confidence": 0.9},
                       {"bbox": [1, 1, 20, 30], "confidence": float("nan")}):
            obj = {"id": "o", "kind": "WALL", "source": "HOST_CV",
                   "evidence_ref": "capture:test", "camera_revision": "camA", **change}
            with self.assertRaises(SpatialPerceptionError):
                assess_frame(frame(objects=[obj]))

    def test_camera_side_cannot_be_guessed_from_canvas(self):
        with self.assertRaisesRegex(SpatialPerceptionError, "VIEW_ANCHOR_INVALID"):
            assess_frame(frame(view={"side": "STREET_SIDE",
                "source": "HOST_CV", "camera_revision": "camA",
                "evidence_ref": "capture:guess"}))

    def test_unknown_patch_fails_before_world_reasoning(self):
        receipt = assess_frame(frame(game_version="0.0.0.0"))
        self.assertEqual(receipt["state"], "UNKNOWN_PATCH")
        self.assertEqual(receipt["objects"], [])
        self.assertFalse(receipt["execute_allowed"])


    def test_listener_reports_spatial_while_yielding_to_player(self):
        session = "spatialtest01"
        source = frame()
        activate(session, note="spatial-eval")
        try:
            report = tick(
                session,
                {
                    "schema": "betterinstincts.host-listener.observation/v1",
                    "needs": {k: 0.9 for k in ("hunger", "bladder", "energy", "hygiene", "fun", "social")},
                    "queue": [], "location_kind": "home",
                    "capture_ref": source["capture_ref"],
                    "game_version": source["game_version"],
                    "spatial_frame": source,
                },
                presence_probe=PresenceProbe(True, True),
            )
            self.assertEqual(report["listener_action"], "YIELD_TO_PLAYER")
            self.assertEqual(report["spatial_perception"]["state"], "TOPOLOGY_UNVERIFIED")
            self.assertFalse(report["spatial_perception"]["execute_allowed"])
            self.assertFalse(report["execute_clicks"])
        finally:
            deactivate(session)

    def test_listener_rejects_stale_capture_before_player_yield(self):
        session = "spatialtest02"
        source = frame()
        activate(session, note="spatial-eval")
        try:
            with self.assertRaisesRegex(HostListenerError, "SPATIAL_CAPTURE_OR_BUILD_MISMATCH"):
                tick(
                    session,
                    {
                        "schema": "betterinstincts.host-listener.observation/v1",
                        "needs": {k: 0.9 for k in ("hunger", "bladder", "energy", "hygiene", "fun", "social")},
                        "queue": [], "location_kind": "home",
                        "capture_ref": "capture:different",
                        "game_version": source["game_version"],
                        "spatial_frame": source,
                    },
                    presence_probe=PresenceProbe(True, True),
                )
        finally:
            deactivate(session)


if __name__ == "__main__":
    unittest.main()
