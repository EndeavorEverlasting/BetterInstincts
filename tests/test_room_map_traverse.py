"""Offline falsifiers for ROOM_MAP_TRAVERSE graph planner + floor graph."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from betterinstincts.camera_traverse import CameraTraverseError, load_contract as load_cam
from betterinstincts.installation_profiles import set_toggle
from betterinstincts.lot_floor_map import (
    LotFloorMapError,
    ensure_floor_map,
    floor_map_path,
    load_floor_map,
    record_room_landmarks,
    upsert_graph_edge,
    upsert_graph_node,
)
from betterinstincts.room_map_traverse import (
    next_ring_direction,
    plan_room_map_traverse,
)


class RoomMapTraverseTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.settings = self.root / "BetterInstincts" / "settings.v1.json"
        self.settings.parent.mkdir(parents=True)
        with patch(
            "betterinstincts.installation_profiles.settings_path",
            return_value=self.settings,
        ), patch(
            "betterinstincts.lot_floor_map.settings_path",
            return_value=self.settings,
        ):
            set_toggle("learning.lot_floor_map_auto", True, self.settings)

    def _patched(self):
        return patch.multiple(
            "betterinstincts.lot_floor_map",
            settings_path=lambda **_k: self.settings,
        )

    def test_contract_pins_room_map_traverse(self):
        cam = load_cam()
        self.assertIn("room_map_traverse", cam)
        self.assertEqual(cam["room_map_traverse"]["id"], "ROOM_MAP_TRAVERSE")
        self.assertIn("LANDMARK_DINING_TABLE", cam["room_map_traverse"]["default_seed_landmarks"])

    def test_plan_requires_named_goal_and_known_kind(self):
        plan = plan_room_map_traverse(
            goal_id="map_corner_workbench",
            target_kind="ROBOTICS_WORKSTATION",
            seed_landmarks=["LANDMARK_DINING_TABLE", "LANDMARK_RUG_CLUSTER"],
        )
        self.assertEqual(plan["state"], "ROOM_MAP_TRAVERSE_PLAN_READY")
        self.assertFalse(plan["execute_allowed"])
        self.assertEqual(plan["zoom_mode_target"], "BUILD_TOP_DOWN_MAP")
        self.assertEqual(plan["primary_census"], "BUILD_TOP_DOWN_T")
        self.assertTrue(plan["observe_only"])
        self.assertEqual(plan["input_policy"]["preferred_channel"], "SELECT_INSPECT_THEN_ESCAPE")
        self.assertIn("ON_ERRONEOUS_GRAB_ESCAPE_AND_RESUME", plan["steps"])
        self.assertIn("LMB_DRAG_OR_PURCHASE_DURING_MAP_CENSUS", plan["forbidden"])
        self.assertIn("REZOOM_OR_PAN_AWAY_FROM_OPERATOR_CENTERED_ROOM_FIT", plan["forbidden"])
        self.assertEqual(len(plan["seed_graph"]["nodes"]), 3)
        self.assertTrue(any(e["relation"] == "CORNER_OF" for e in plan["seed_graph"]["edges"]))
        with self.assertRaises(CameraTraverseError):
            plan_room_map_traverse(goal_id="", target_kind="ROBOTICS_WORKSTATION")
        with self.assertRaisesRegex(LotFloorMapError, "UNKNOWN_OBJECT_KIND"):
            plan_room_map_traverse(goal_id="g", target_kind="MAGIC_PORTAL")

    def test_ring_direction_prefers_unvisited(self):
        self.assertEqual(next_ring_direction(visited=[], preferred=["E"]), "E")
        self.assertEqual(next_ring_direction(visited=["E", "SE"], preferred=["E"]), "N")
        self.assertIsNone(
            next_ring_direction(
                visited=["N", "NE", "E", "SE", "S", "SW", "W", "NW"],
            )
        )

    def test_graph_upsert_and_edge_endpoints(self):
        with self._patched():
            ensure_floor_map(
                profile_id="default",
                lot_key="household-n4-lab",
                settings_file=self.settings,
            )
            path = floor_map_path(
                profile_id="default", lot_key="household-n4-lab", settings_file=self.settings
            )
            doc = load_floor_map(path)
            upsert_graph_node(
                doc,
                node_id="landmark_dining_table",
                kind="LANDMARK_DINING_TABLE",
                client_xy=[900, 500],
            )
            upsert_graph_node(
                doc,
                node_id="robotics_workstation_primary",
                kind="ROBOTICS_WORKSTATION",
                role="TARGET",
                client_xy=[1516, 437],
            )
            with self.assertRaisesRegex(LotFloorMapError, "GRAPH_EDGE_ENDPOINTS_REQUIRED"):
                upsert_graph_edge(
                    doc,
                    from_id="landmark_dining_table",
                    to_id="missing",
                    relation="CORNER_OF",
                )
            edge = upsert_graph_edge(
                doc,
                from_id="landmark_dining_table",
                to_id="robotics_workstation_primary",
                direction="E",
                relation="CORNER_OF",
                pan_hint=["E", "SE"],
            )
            self.assertEqual(edge["to"], "robotics_workstation_primary")

    def test_record_room_landmarks_writes_graph(self):
        with self._patched():
            out = record_room_landmarks(
                profile_id="default",
                lot_key="household-n4-lab",
                workbench_xy=[1516, 437],
                dining_xy=[923, 540],
                rug_xy=[1121, 669],
                capture_ref="live:n4-lab-20261110-room-traverse",
                camera_revision="camera:live-room-map-1",
                settings_file=self.settings,
            )
            self.assertEqual(out["state"], "ROOM_LANDMARKS_RECORDED")
            doc = load_floor_map(Path(out["path"]))
            self.assertIn("robotics_workstation_primary", doc["graph"]["nodes"])
            self.assertEqual(
                doc["graph"]["nodes"]["robotics_workstation_primary"]["client_xy"],
                [1516, 437],
            )
            self.assertTrue(
                any(e["relation"] == "CORNER_OF" for e in doc["graph"]["edges"])
            )


if __name__ == "__main__":
    unittest.main()
