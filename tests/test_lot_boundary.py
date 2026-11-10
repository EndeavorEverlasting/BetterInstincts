"""Offline lot footprint / boundary admission."""
from __future__ import annotations

import unittest

from betterinstincts.lot_boundary import (
    admit_world_click_in_footprint,
    assess_lot_boundary,
    load_contract,
    point_in_aabb,
)


class LotBoundaryTests(unittest.TestCase):
    def test_contract_authority(self):
        cfg = load_contract()
        self.assertEqual(cfg["schema"], "betterinstincts.lot-boundary/v1")
        self.assertIn("MEASURED_FOOTPRINT_AABB_CAMERA_REVISION_BOUND", cfg["authority_stack"])
        self.assertIn("CLICK_STREET_AS_HOUSE", cfg["forbidden_always"])

    def test_street_frame_denies(self):
        b = assess_lot_boundary(
            observation={"scenery_tokens": ["ASPHALT", "STREET"]},
            lot_focus={"classification": "OFF_LOT", "scenery_focus": "STREET_OR_ROOFTOP_OFF_FOCUS"},
        )
        self.assertEqual(b["state"], "OUTSIDE_FOOTPRINT")
        self.assertFalse(b["admit_world_clicks"])
        denied = admit_world_click_in_footprint(
            client_xy=[900, 500],
            observation={"scenery_tokens": ["ASPHALT"]},
            lot_focus={"classification": "OFF_LOT"},
            click_zone="STREET",
        )
        self.assertFalse(denied["admit"])
        self.assertEqual(denied["gate"], "LOT_BOUNDARY_OUTSIDE_FOOTPRINT")

    def test_buy_without_census_denies(self):
        b = assess_lot_boundary(
            observation={"mode": "BUY", "buy_catalog_open": True},
            lot_focus={"classification": "ON_LOT"},
        )
        self.assertEqual(b["gate"], "LOT_BOUNDARY_BUY_WITHOUT_CENSUS")
        self.assertFalse(b["admit_world_clicks"])

    def test_on_lot_interior_admits_with_zone(self):
        obs = {
            "scenery_tokens": ["INTERIOR", "FURNITURE"],
            "camera_revision": "rev1",
            "footprint_aabb": {
                "x0": 400,
                "y0": 100,
                "x1": 1600,
                "y1": 900,
                "camera_revision": "rev1",
            },
        }
        focus = {"classification": "ON_LOT", "scenery_focus": "ON_LOT_INTERIOR_OR_YARD"}
        b = assess_lot_boundary(observation=obs, lot_focus=focus)
        self.assertTrue(b["inside_footprint"])
        ok = admit_world_click_in_footprint(
            client_xy=[800, 400],
            observation=obs,
            lot_focus=focus,
            click_zone="INTERIOR",
        )
        self.assertTrue(ok["admit"])
        outside = admit_world_click_in_footprint(
            client_xy=[50, 50],
            observation=obs,
            lot_focus=focus,
            click_zone="INTERIOR",
        )
        self.assertFalse(outside["admit"])
        self.assertEqual(outside["reason"], "CLIENT_XY_OUTSIDE_MEASURED_FOOTPRINT_AABB")

    def test_street_zone_denied_even_on_lot_claim(self):
        denied = admit_world_click_in_footprint(
            client_xy=[800, 400],
            observation={"scenery_tokens": ["INTERIOR"], "operator_attests_inside_footprint": True},
            lot_focus={"classification": "ON_LOT"},
            click_zone="STREET",
        )
        self.assertFalse(denied["admit"])

    def test_point_in_aabb(self):
        box = {"x0": 10, "y0": 10, "x1": 100, "y1": 100}
        self.assertTrue(point_in_aabb([10, 10], box))
        self.assertTrue(point_in_aabb([100, 100], box))
        self.assertFalse(point_in_aabb([9, 50], box))


if __name__ == "__main__":
    unittest.main()
