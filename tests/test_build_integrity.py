"""Structure-first Build/Buy integrity — outdoor≠indoor, floor first, no nesting."""
from __future__ import annotations

import unittest

from betterinstincts import build_integrity as bi
from betterinstincts import house_state as hs


def _model_with(**entities):
    model = hs.create_model("bi-integrity-1", "Bargain Bend")
    return hs.observe(model, entities=entities, open_goals=["RESTORE_STRUCTURE"])


class BuildIntegrityTests(unittest.TestCase):
    def test_contract_structure_first(self):
        cfg = bi.load_contract()
        self.assertEqual(cfg["architecture"]["selected"], "STRUCTURE_FIRST_SPATIAL_ADMISSION")
        self.assertIn("TREAT_OUTDOOR_AS_INDOOR", cfg["forbidden"])

    def test_deny_place_indoor_on_outdoor_grass(self):
        model = _model_with(
            floor_missing={"kind": "FLOOR_TILE", "confidence": "OPERATOR_ATTESTED", "status": "MISSING", "domain": "INDOOR_FLOOR"},
        )
        # No present floor
        denied = bi.evaluate_integrity(
            model,
            action="PLACE_FROM_CATALOG",
            place_kind="SLEEP_POD",
            place_domain="OUTDOOR_LOT",
        )
        self.assertEqual(denied["state"], "INTEGRITY_DENY")
        self.assertEqual(denied["violation"], "OUTDOOR_AS_INDOOR")

    def test_deny_place_without_floor(self):
        model = hs.observe(
            hs.create_model("bi-integrity-1", "Bargain Bend"),
            entities={
                "grass": {"kind": "ROOM_ZONE", "confidence": "OPERATOR_ATTESTED", "domain": "OUTDOOR_LOT", "status": "PRESENT"},
            },
        )
        denied = bi.evaluate_integrity(
            model,
            action="PLACE_FROM_INVENTORY",
            place_kind="DINING_TABLE",
            place_domain="INDOOR_FLOOR",
        )
        self.assertEqual(denied["violation"], "PLACE_WITHOUT_FLOOR")
        self.assertEqual(denied["gate"], "RESTORE_FLOOR_BEFORE_FURNITURE")

    def test_deny_nesting(self):
        model = hs.observe(
            hs.create_model("bi-integrity-1", "Bargain Bend"),
            entities={
                "floor.1": {
                    "kind": "FLOOR_TILE",
                    "confidence": "LOCAL_OBSERVED",
                    "domain": "INDOOR_FLOOR",
                    "story": "FLOOR_1",
                    "status": "PRESENT",
                },
            },
        )
        denied = bi.evaluate_integrity(
            model,
            action="PLACE_FROM_CATALOG",
            place_kind="DINING_CHAIR",
            place_domain="INDOOR_FLOOR",
            nest_risk=True,
        )
        self.assertEqual(denied["violation"], "NESTED_OBJECTS")

    def test_admit_indoor_place_with_floor(self):
        model = hs.observe(
            hs.create_model("bi-integrity-1", "Bargain Bend"),
            entities={
                "floor.1": {
                    "kind": "FLOOR_TILE",
                    "confidence": "LOCAL_OBSERVED",
                    "domain": "INDOOR_FLOOR",
                    "story": "FLOOR_1",
                    "status": "PRESENT",
                },
            },
        )
        ok = bi.evaluate_integrity(
            model,
            action="PLACE_FROM_CATALOG",
            place_kind="SLEEP_POD",
            place_domain="INDOOR_FLOOR",
        )
        self.assertEqual(ok["state"], "INTEGRITY_ADMIT")

    def test_structure_delete_needs_restore_goal_and_save_as(self):
        model = hs.observe(
            hs.create_model("bi-integrity-1", "Bargain Bend"),
            entities={
                "wall.1": {
                    "kind": "WALL_SEGMENT",
                    "confidence": "OPERATOR_ATTESTED",
                    "domain": "WALL",
                    "status": "PRESENT",
                    "zone": "KITCHEN",
                },
            },
        )
        denied = bi.evaluate_integrity(model, action="SLEDGE", targets=["wall.1"], place_kind="WALL_SEGMENT")
        self.assertEqual(denied["violation"], "STRUCTURE_DELETE_UNGUARDED")

        model2 = hs.observe(model, open_goals=["RESTORE_WALLS"])
        denied2 = bi.evaluate_integrity(model2, action="SLEDGE", targets=["wall.1"], place_kind="WALL_SEGMENT")
        self.assertEqual(denied2["violation"], "STRUCTURE_DELETE_UNGUARDED")  # still no Save As

        attested = hs.attest_save_as(
            model2,
            alias="BI_TMP_PRE_RESTORE",
            capture_ref="capture:pre-wall",
            operator_confirmed=True,
        )
        ok = bi.evaluate_integrity(attested, action="SLEDGE", targets=["wall.1"], place_kind="WALL_SEGMENT")
        self.assertEqual(ok["state"], "INTEGRITY_ADMIT")

    def test_kitchen_strip_denied_without_restore(self):
        model = hs.observe(
            hs.create_model("bi-integrity-1", "Bargain Bend"),
            entities={
                "stove.1": {
                    "kind": "APPLIANCE",
                    "confidence": "OPERATOR_ATTESTED",
                    "domain": "INDOOR_FLOOR",
                    "zone": "KITCHEN",
                    "status": "PRESENT",
                },
            },
        )
        denied = bi.evaluate_integrity(
            model,
            action="BACKSPACE_TO_INVENTORY",
            targets=["stove.1"],
            place_kind="APPLIANCE",
            strips_zone="KITCHEN",
        )
        self.assertEqual(denied["violation"], "AESTHETIC_ZONE_DESTRUCT")

    def test_structure_restore_plan_orders_floor_first(self):
        model = hs.observe(
            hs.create_model("bi-integrity-1", "Bargain Bend"),
            entities={
                "floor.1": {
                    "kind": "FLOOR_TILE",
                    "confidence": "OPERATOR_ATTESTED",
                    "domain": "INDOOR_FLOOR",
                    "story": "FLOOR_1",
                    "status": "MISSING",
                },
                "table.1": {
                    "kind": "DINING_TABLE",
                    "confidence": "OPERATOR_ATTESTED",
                    "status": "MISSING",
                    "domain": "INDOOR_FLOOR",
                    "zone": "DINING",
                },
                "pod.1": {
                    "kind": "SLEEP_POD",
                    "confidence": "OPERATOR_ATTESTED",
                    "status": "MISSING",
                    "domain": "INDOOR_FLOOR",
                    "zone": "BEDROOM",
                },
                "kitchen.zone": {
                    "kind": "ROOM_ZONE",
                    "confidence": "OPERATOR_ATTESTED",
                    "zone": "KITCHEN",
                    "status": "STRIPPED",
                    "domain": "INDOOR_FLOOR",
                },
            },
            open_goals=["RESTORE_KITCHEN", "RESTORE_FLOOR"],
        )
        plan = bi.structure_restore_plan(model)
        self.assertEqual(plan["state"], "STRUCTURE_RESTORE_REQUIRED")
        self.assertEqual(plan["steps"][0]["step"], "RESTORE_FLOOR")

    def test_house_state_admit_wires_integrity(self):
        model = hs.observe(
            hs.create_model("bi-integrity-1", "Bargain Bend"),
            entities={
                "floor.1": {
                    "kind": "FLOOR_TILE",
                    "confidence": "LOCAL_OBSERVED",
                    "domain": "INDOOR_FLOOR",
                    "story": "FLOOR_1",
                    "status": "PRESENT",
                },
                "chair.1": {
                    "kind": "DINING_CHAIR",
                    "confidence": "LOCAL_OBSERVED",
                    "domain": "INDOOR_FLOOR",
                    "status": "MISSING",
                },
            },
        )
        denied = hs.admit_mutation(
            model,
            "PLACE_FROM_CATALOG",
            targets=["chair.1"],
            place_kind="DINING_CHAIR",
            place_domain="OUTDOOR_LOT",
            place_enclosure="OUTSIDE",
            place_story="FLOOR_1",
        )
        self.assertEqual(denied["state"], "MUTATION_DENIED")
        self.assertIn(denied["reason"], {
            "MUTATE_WITHOUT_BUILD_INTEGRITY",
            "MUTATE_WITHOUT_SPATIAL_AXES",
        })

        ok = hs.admit_mutation(
            model,
            "PLACE_FROM_CATALOG",
            targets=["chair.1"],
            place_kind="DINING_CHAIR",
            place_domain="INDOOR_FLOOR",
            place_enclosure="INSIDE",
            place_story="FLOOR_1",
        )
        self.assertEqual(ok["state"], "MUTATION_ADMITTED")
        self.assertEqual(ok["reason"], "MODEL_SPATIAL_AND_INTEGRITY_BACKED_MUTATION")


if __name__ == "__main__":
    unittest.main()
