"""Inside/outside + FLOOR_1/FLOOR_2 builder axes."""
from __future__ import annotations

import unittest

from betterinstincts import build_spatial as bs
from betterinstincts import house_state as hs
from betterinstincts.host_stack import evaluate_turn


class BuildSpatialTests(unittest.TestCase):
    def test_contract_axes(self):
        cfg = bs.load_contract()
        self.assertEqual(cfg["architecture"]["selected"], "ENCLOSURE_AND_STORY_AXES")
        self.assertIn("BUILD_F2_BEFORE_F1", cfg["forbidden"])

    def test_classify_inside_f1_and_outside(self):
        inside = bs.classify_entity({
            "kind": "FLOOR_TILE",
            "domain": "INDOOR_FLOOR",
            "story": "FLOOR_1",
            "status": "PRESENT",
        })
        self.assertEqual(inside["enclosure"], "INSIDE")
        self.assertEqual(inside["story"], "FLOOR_1")
        outside = bs.classify_entity({
            "kind": "FLOATER",
            "domain": "OUTDOOR_LOT",
        })
        self.assertEqual(outside["enclosure"], "OUTSIDE")

    def test_deny_outside_as_inside_and_f2_before_f1(self):
        model = hs.observe(
            hs.create_model("bi-spatial-1", "Bargain Bend"),
            entities={
                "grass": {"kind": "ROOM_ZONE", "confidence": "OPERATOR_ATTESTED", "domain": "OUTDOOR_LOT"},
            },
        )
        denied = bs.admit_spatial_placement(
            model, place_enclosure="OUTSIDE", place_story="FLOOR_1", indoor_required=True
        )
        self.assertEqual(denied["violation"], "OUTSIDE_AS_INSIDE")

        denied2 = bs.admit_spatial_placement(
            model, place_enclosure="INSIDE", place_story="FLOOR_2", indoor_required=True
        )
        self.assertEqual(denied2["violation"], "FLOOR2_BEFORE_FLOOR1")

    def test_inventory_and_build_order_f1_before_f2(self):
        model = hs.observe(
            hs.create_model("bi-spatial-1", "Bargain Bend"),
            entities={
                "floor.f1": {
                    "kind": "FLOOR_TILE",
                    "confidence": "LOCAL_OBSERVED",
                    "domain": "INDOOR_FLOOR",
                    "story": "FLOOR_1",
                    "status": "MISSING",
                },
                "floor.f2": {
                    "kind": "FLOOR_TILE",
                    "confidence": "OPERATOR_ATTESTED",
                    "domain": "INDOOR_FLOOR",
                    "story": "FLOOR_2",
                    "status": "MISSING",
                },
                "pod.f2": {
                    "kind": "SLEEP_POD",
                    "confidence": "OPERATOR_ATTESTED",
                    "domain": "INDOOR_FLOOR",
                    "story": "FLOOR_2",
                    "status": "MISSING",
                },
                "lamp.out": {
                    "kind": "FLOATER",
                    "confidence": "LOCAL_OBSERVED",
                    "domain": "OUTDOOR_LOT",
                    "status": "MIDAIR",
                },
            },
            open_goals=["RESTORE_FLOOR", "FLOOR_2"],
        )
        order = bs.build_order_plan(model)
        self.assertEqual(order["primary"]["story"], "FLOOR_1")
        self.assertEqual(order["primary"]["action"], "PLACE_FLOOR_TILES")
        stories = [s.get("story") for s in order["steps"] if s.get("step", "").startswith("FLOOR_")]
        self.assertEqual(stories[0], "FLOOR_1")

    def test_admit_after_f1_floor_present(self):
        model = hs.observe(
            hs.create_model("bi-spatial-1", "Bargain Bend"),
            entities={
                "floor.f1": {
                    "kind": "FLOOR_TILE",
                    "confidence": "LOCAL_OBSERVED",
                    "domain": "INDOOR_FLOOR",
                    "story": "1",
                    "status": "PRESENT",
                },
            },
        )
        ok = bs.admit_spatial_placement(
            model, place_enclosure="INSIDE", place_story="FLOOR_1", indoor_required=True
        )
        self.assertEqual(ok["state"], "SPATIAL_CLASSIFIED")
        admitted = hs.admit_mutation(
            model,
            "PLACE_FROM_CATALOG",
            place_kind="SLEEP_POD",
            place_domain="INDOOR_FLOOR",
            place_enclosure="INSIDE",
            place_story="FLOOR_1",
        )
        self.assertEqual(admitted["state"], "MUTATION_ADMITTED")

    def test_host_stack_surfaces_spatial_order(self):
        model = hs.observe(
            hs.create_model("bi-spatial-1", "Bargain Bend"),
            entities={
                "floor.f1": {
                    "kind": "FLOOR_TILE",
                    "confidence": "LOCAL_OBSERVED",
                    "domain": "INDOOR_FLOOR",
                    "story": "FLOOR_1",
                    "status": "MISSING",
                },
            },
        )
        turn = evaluate_turn(
            {"hunger": 0.8, "energy": 0.8, "bladder": 0.8, "hygiene": 0.8, "fun": 0.8, "social": 0.8},
            build_or_buy_mode=True,
            lot_model=model,
            available_objects=["fridge"],
            viewport={"state": "VIEWPORT_OK"},
        )
        self.assertIsNotNone(turn.get("build_spatial"))
        self.assertEqual(turn["fallback"]["mechanism"], "BUILD_SPATIAL_ORDER")
        self.assertEqual(turn["fallback"]["primary"]["story"], "FLOOR_1")


if __name__ == "__main__":
    unittest.main()
