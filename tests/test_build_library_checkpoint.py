"""Library-save-before-room-mutate — walls cannot sledge without My Library save."""
from __future__ import annotations

import unittest

from betterinstincts import build_library_checkpoint as blc
from betterinstincts import house_state as hs
from betterinstincts.host_stack import evaluate_turn


class BuildLibraryCheckpointTests(unittest.TestCase):
    def test_contract_selects_architecture(self):
        cfg = blc.load_contract()
        self.assertEqual(
            cfg["architecture"]["selected"], "LIBRARY_SAVE_BEFORE_ROOM_MUTATE"
        )
        self.assertIn("MUTATE_ROOM_WITHOUT_LIBRARY_SAVE", cfg["forbidden"])

    def test_sledge_wall_denied_without_library(self):
        model = hs.observe(
            hs.create_model("bi-lib-1", "Bargain Bend"),
            entities={
                "wall.1": {
                    "kind": "WALL_SEGMENT",
                    "confidence": "LOCAL_OBSERVED",
                    "domain": "WALL",
                    "status": "PRESENT",
                },
            },
        )
        denied = hs.admit_mutation(model, "SLEDGE", targets=["wall.1"])
        self.assertEqual(denied["state"], "MUTATION_DENIED")
        self.assertEqual(denied["reason"], "LOT_MUTATION_WITHOUT_COMPLETE_BACKUP")
        self.assertEqual(denied["violation"], "MUTATE_ROOM_WITHOUT_LIBRARY_SAVE")

    def test_library_then_save_as_then_sledge_admitted(self):
        model = hs.observe(
            hs.create_model("bi-lib-1", "Bargain Bend"),
            entities={
                "wall.1": {
                    "kind": "WALL_SEGMENT",
                    "confidence": "LOCAL_OBSERVED",
                    "domain": "WALL",
                    "status": "PRESENT",
                    "zone": "KITCHEN",
                },
            },
            open_goals=["RESTORE_WALLS"],
        )
        lib = hs.attest_library_save(
            model,
            building_id="Bargain Bend",
            library_item_name="BI Bargain Bend PreWall",
            capture_ref="capture:library-pre-wall",
            operator_confirmed=True,
        )
        self.assertTrue(lib["library_checkpoint"]["library_saved"])
        # Still need Save As for destructive + integrity restore goal.
        attested = hs.attest_save_as(
            lib,
            alias="BI_TMP_PRE_WALL",
            capture_ref="capture:save-as-pre-wall",
            operator_confirmed=True,
        )
        # attest_save_as bumps revision → library checkpoint becomes stale.
        denied_stale = hs.admit_mutation(attested, "SLEDGE", targets=["wall.1"])
        self.assertEqual(denied_stale["reason"], "LOT_MUTATION_WITHOUT_COMPLETE_BACKUP")
        self.assertEqual(denied_stale["violation"], "STALE_LIBRARY_CHECKPOINT")

        fresh = hs.attest_library_save(
            attested,
            building_id="Bargain Bend",
            library_item_name="BI Bargain Bend PreWall",
            capture_ref="capture:library-pre-wall-2",
            operator_confirmed=True,
        )
        ok = hs.admit_mutation(fresh, "SLEDGE", targets=["wall.1"])
        self.assertEqual(ok["state"], "MUTATION_DENIED")
        self.assertEqual(ok["violation"], "LOT_MUTATION_WITHOUT_COMPLETE_BACKUP")
        # A Library UI attestation without a whole-lot census is not authority.

    def test_save_as_is_not_library_checkpoint(self):
        model = hs.observe(
            hs.create_model("bi-lib-1", "Bargain Bend"),
            entities={
                "wall.1": {
                    "kind": "WALL_SEGMENT",
                    "confidence": "LOCAL_OBSERVED",
                    "domain": "WALL",
                    "status": "PRESENT",
                },
            },
        )
        only_save_as = hs.attest_save_as(
            model,
            alias="BI_TMP_ONLY_SAVE",
            capture_ref="capture:save-only",
            operator_confirmed=True,
        )
        denied = hs.admit_mutation(only_save_as, "SLEDGE", targets=["wall.1"])
        self.assertEqual(denied["reason"], "LOT_MUTATION_WITHOUT_COMPLETE_BACKUP")

    def test_outdoor_floater_inventory_skips_library(self):
        model = hs.observe(
            hs.create_model("bi-lib-1", "Bargain Bend"),
            entities={
                "floater.1": {
                    "kind": "FLOATER",
                    "confidence": "LOCAL_OBSERVED",
                    "domain": "OUTDOOR_LOT",
                    "status": "PRESENT",
                },
            },
        )
        gate = blc.evaluate_library_checkpoint(
            model, "BACKSPACE_TO_INVENTORY", targets=["floater.1"]
        )
        self.assertEqual(gate["state"], "LIBRARY_DENY")
        admitted = hs.admit_mutation(
            model, "BACKSPACE_TO_INVENTORY", targets=["floater.1"]
        )
        self.assertEqual(admitted["state"], "MUTATION_DENIED")

    def test_plan_next_demands_library_before_restore(self):
        model = hs.observe(
            hs.create_model("bi-lib-1", "Bargain Bend"),
            entities={
                "floor.1": {
                    "kind": "FLOOR_TILE",
                    "confidence": "LOCAL_OBSERVED",
                    "domain": "INDOOR_FLOOR",
                    "story": "FLOOR_1",
                    "status": "MISSING",
                },
            },
            open_goals=["RESTORE_FLOOR"],
        )
        plan = hs.plan_next(model)
        self.assertEqual(plan["action"], "SCAN_ALL_FLOORS_AND_ROOMS")
        self.assertEqual(plan["gate"], "LIBRARY_CHECKPOINT_REQUIRED")

    def test_save_to_library_lease_without_prior_checkpoint(self):
        model = hs.observe(
            hs.create_model("bi-lib-1", "Bargain Bend"),
            entities={
                "wall.1": {
                    "kind": "WALL_SEGMENT",
                    "confidence": "LOCAL_OBSERVED",
                    "status": "PRESENT",
                },
            },
        )
        admitted = hs.admit_mutation(model, "SAVE_TO_LIBRARY")
        self.assertEqual(admitted["state"], "MUTATION_ADMITTED")
        self.assertEqual(admitted["reason"], "LIBRARY_SAVE_ACTION_BEFORE_ROOM_MUTATE")

    def test_host_stack_surfaces_library_gate(self):
        model = hs.observe(
            hs.create_model("bi-lib-1", "Bargain Bend"),
            entities={
                "wall.1": {
                    "kind": "WALL_SEGMENT",
                    "confidence": "LOCAL_OBSERVED",
                    "status": "MISSING",
                    "domain": "WALL",
                },
            },
            open_goals=["RESTORE_WALLS"],
        )
        turn = evaluate_turn(
            {"hunger": 0.8, "energy": 0.8, "bladder": 0.8, "hygiene": 0.8, "fun": 0.8, "social": 0.8},
            player_directed=False,
            already_busy=False,
            build_or_buy_mode=True,
            lot_model=model,
            available_objects=["fridge"],
            viewport={"state": "VIEWPORT_OK"},
        )
        self.assertEqual(turn["next_gate"], "LIBRARY_CHECKPOINT_REQUIRED")
        self.assertEqual(turn["fallback"]["action"], "SCAN_ALL_FLOORS_AND_ROOMS")
        self.assertEqual(turn["build_library"]["action"], "SCAN_ALL_FLOORS_AND_ROOMS")

    def test_building_scope_mismatch(self):
        model = hs.observe(
            hs.create_model("bi-lib-1", "Bargain Bend"),
            entities={
                "wall.1": {
                    "kind": "WALL_SEGMENT",
                    "confidence": "LOCAL_OBSERVED",
                    "status": "PRESENT",
                },
            },
        )
        lib = hs.attest_library_save(
            model,
            building_id="Bargain Bend",
            library_item_name="BI Bargain Bend Shell",
            capture_ref="capture:lib-shell",
            operator_confirmed=True,
        )
        denied = blc.evaluate_library_checkpoint(
            lib, "WALL_ROOM_TOOL", building_id="Other Lot"
        )
        self.assertEqual(denied["state"], "LIBRARY_DENY")
        self.assertEqual(denied["violation"], "BUILDING_SCOPE_MISMATCH")


if __name__ == "__main__":
    unittest.main()
