"""Recursive lot model: accumulate, plan, admit — never blank-slate reassess."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from betterinstincts import house_state as hs


class HouseStateTests(unittest.TestCase):
    def setUp(self):
        self.cfg = hs.load_contract()
        self.assertEqual(self.cfg["architecture"]["selected"], "RECURSIVE_LOT_MODEL")

    def test_contract_forbids_blank_slate_loop(self):
        forbidden = set(self.cfg["forbidden"])
        self.assertIn("BLANK_SLATE_REASSESS", forbidden)
        self.assertIn("DISCARD_MODEL_AFTER_ACTION", forbidden)
        self.assertIn("BULK_SWEEP_WITHOUT_ENTITY_TARGETS", forbidden)

    def test_observe_merges_same_model_and_bumps_revision(self):
        model = hs.create_model("bi-house-1", "Bargain Bend")
        m1 = hs.observe(
            model,
            entities={
                "table.1": {"kind": "DINING_TABLE", "confidence": "LOCAL_OBSERVED", "status": "PRESENT"},
                "chair.slot6": {"kind": "DINING_CHAIR", "confidence": "LOCAL_OBSERVED", "status": "MISSING"},
            },
            open_goals=["SEAT_SIXTH_CHAIR"],
            captures=["capture:lot_wide3"],
        )
        self.assertEqual(m1["revision"], 1)
        m2 = hs.observe(
            m1,
            entities={
                "floater.1": {"kind": "FLOATER", "confidence": "OPERATOR_ATTESTED", "status": "MIDAIR"},
            },
            note="saw floater",
        )
        self.assertEqual(m2["revision"], 2)
        self.assertIn("table.1", m2["entities"])
        self.assertIn("chair.slot6", m2["entities"])
        self.assertIn("floater.1", m2["entities"])
        self.assertEqual(len(m2["entities"]), 3)

    def test_plan_and_admit_require_accumulated_model(self):
        empty = hs.create_model("bi-house-1", "Bargain Bend")
        plan0 = hs.plan_next(empty)
        self.assertEqual(plan0["state"], "MODEL_EMPTY")
        denied = hs.admit_mutation(empty, "PLACE_FROM_CATALOG", targets=["chair.slot6"])
        self.assertEqual(denied["state"], "MUTATION_DENIED")
        self.assertEqual(denied["reason"], "MUTATE_WITHOUT_MODEL_REVISION")

        model = hs.observe(
            empty,
            entities={
                "floor.1": {
                    "kind": "FLOOR_TILE",
                    "confidence": "LOCAL_OBSERVED",
                    "domain": "INDOOR_FLOOR",
                    "story": "FLOOR_1",
                    "status": "PRESENT",
                },
                "table.1": {
                    "kind": "DINING_TABLE",
                    "confidence": "LOCAL_OBSERVED",
                    "domain": "INDOOR_FLOOR",
                    "status": "PRESENT",
                },
                "chair.slot6": {
                    "kind": "DINING_CHAIR",
                    "confidence": "LOCAL_OBSERVED",
                    "status": "MISSING",
                    "domain": "INDOOR_FLOOR",
                },
            },
            open_goals=["SEAT_SIXTH_CHAIR"],
        )
        plan = hs.plan_next(model)
        self.assertEqual(plan["action"], "PLACE_FROM_CATALOG")
        self.assertEqual(plan["gate"], "PLAN_FROM_MODEL")
        admitted = hs.admit_mutation(
            model,
            "PLACE_FROM_CATALOG",
            targets=["chair.slot6"],
            expected_revision=model["revision"],
            place_kind="DINING_CHAIR",
            place_domain="INDOOR_FLOOR",
            place_enclosure="INSIDE",
            place_story="FLOOR_1",
        )
        self.assertEqual(admitted["state"], "MUTATION_ADMITTED")
        self.assertEqual(admitted["next"], "OBSERVE_OUTCOME_INTO_SAME_MODEL")

    def test_bulk_sweep_denied_even_with_model(self):
        model = hs.observe(
            hs.create_model("bi-house-1", "Bargain Bend"),
            entities={"floater.1": {"kind": "FLOATER", "confidence": "OPERATOR_ATTESTED"}},
        )
        denied = hs.admit_mutation(model, "BULK_INVENTORY_SWEEP", targets=["floater.1"])
        self.assertEqual(denied["reason"], "BULK_SWEEP_WITHOUT_ENTITY_TARGETS")

    def test_targeted_floater_clear_planned_and_admitted(self):
        model = hs.observe(
            hs.create_model("bi-house-1", "Bargain Bend"),
            entities={
                "floor.1": {
                    "kind": "FLOOR_TILE",
                    "confidence": "LOCAL_OBSERVED",
                    "domain": "INDOOR_FLOOR",
                    "story": "FLOOR_1",
                    "status": "PRESENT",
                },
                "table.1": {
                    "kind": "DINING_TABLE",
                    "confidence": "LOCAL_OBSERVED",
                    "domain": "INDOOR_FLOOR",
                    "status": "PRESENT",
                },
                "floater.lamp": {
                    "kind": "FLOATER",
                    "confidence": "OPERATOR_ATTESTED",
                    "status": "MIDAIR",
                    "domain": "OUTDOOR_LOT",
                },
            },
        )
        plan = hs.plan_next(model)
        self.assertEqual(plan["action"], "BACKSPACE_TO_INVENTORY")
        self.assertIn("floater.lamp", plan["targets"])
        admitted = hs.admit_mutation(model, "BACKSPACE_TO_INVENTORY", targets=["floater.lamp"])
        self.assertEqual(admitted["state"], "MUTATION_ADMITTED")

    def test_destructive_requires_library_then_save_as(self):
        model = hs.observe(
            hs.create_model("bi-house-1", "Bargain Bend"),
            entities={
                "room.1": {"kind": "ROOM_ZONE", "confidence": "OPERATOR_ATTESTED", "domain": "OUTDOOR_LOT"},
                "floor.1": {
                    "kind": "FLOOR_TILE",
                    "confidence": "LOCAL_OBSERVED",
                    "domain": "INDOOR_FLOOR",
                    "story": "FLOOR_1",
                    "status": "PRESENT",
                },
            },
            open_goals=["RESTORE_STRUCTURE"],
        )
        denied_lib = hs.admit_mutation(model, "MULTI_OBJECT_REARRANGE", targets=["room.1"])
        self.assertEqual(denied_lib["reason"], "MUTATE_ROOM_WITHOUT_LIBRARY_SAVE")
        with_lib = hs.attest_library_save(
            model,
            building_id="Bargain Bend",
            library_item_name="BI Bargain Bend PreRearrange",
            capture_ref="capture:library-pre-rearrange",
            operator_confirmed=True,
        )
        denied_save = hs.admit_mutation(with_lib, "MULTI_OBJECT_REARRANGE", targets=["room.1"])
        self.assertEqual(denied_save["reason"], "DESTRUCTIVE_REQUIRES_SAVE_AS_ATTESTATION")
        # Save As bumps revision → re-attest library at the new tip.
        attested = hs.attest_save_as(
            with_lib,
            alias="BI_TMP_BARGAIN_BEND_PRE",
            capture_ref="capture:pre-mutate",
            operator_confirmed=True,
        )
        fresh = hs.attest_library_save(
            attested,
            building_id="Bargain Bend",
            library_item_name="BI Bargain Bend PreRearrange",
            capture_ref="capture:library-pre-rearrange-2",
            operator_confirmed=True,
        )
        admitted = hs.admit_mutation(fresh, "MULTI_OBJECT_REARRANGE", targets=["room.1"])
        self.assertEqual(admitted["state"], "MUTATION_ADMITTED")

    def test_mutation_outcome_updates_same_model_not_new_identity(self):
        model = hs.observe(
            hs.create_model("bi-house-1", "Bargain Bend"),
            entities={
                "chair.slot6": {"kind": "DINING_CHAIR", "confidence": "LOCAL_OBSERVED", "status": "MISSING"},
                "table.1": {"kind": "DINING_TABLE", "confidence": "LOCAL_OBSERVED"},
            },
        )
        run_id = model["run_id"]
        after = hs.record_mutation_outcome(
            model,
            action="PLACE_FROM_CATALOG",
            targets=["chair.slot6"],
            entity_updates={
                "chair.slot6": {"kind": "DINING_CHAIR", "confidence": "LOCAL_OBSERVED", "status": "PRESENT"},
            },
        )
        self.assertEqual(after["run_id"], run_id)
        self.assertEqual(after["entities"]["chair.slot6"]["status"], "PRESENT")
        self.assertGreater(after["revision"], model["revision"])
        self.assertEqual(after["last_action"]["action"], "PLACE_FROM_CATALOG")

    def test_reject_blank_slate_patterns(self):
        for pattern in (
            "BLANK_SLATE_REASSESS",
            "DISCARD_MODEL_AFTER_ACTION",
            "CHECKPOINT_FROM_SCRATCH",
            "REASSESS_AS_IF_UNKNOWN",
        ):
            with self.subTest(pattern=pattern):
                r = hs.reject_blank_slate({"pattern": pattern})
                self.assertEqual(r["state"], "BLANK_SLATE_REJECTED")

    def test_stale_revision_denied(self):
        model = hs.observe(
            hs.create_model("bi-house-1", "Bargain Bend"),
            entities={"table.1": {"kind": "DINING_TABLE", "confidence": "LOCAL_OBSERVED"}},
        )
        denied = hs.admit_mutation(
            model,
            "HAND_MOVE",
            targets=["table.1"],
            expected_revision=model["revision"] - 1,
        )
        self.assertEqual(denied["reason"], "STALE_MODEL_REVISION")

    def test_persist_checkpoint_is_continuity_of_same_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "house-state"
            with mock.patch.object(hs, "_storage_root", return_value=root):
                with mock.patch.object(hs, "ROOT", Path(tmp)):
                    # Remap ROOT-relative save: patch model_path destination via storage root only
                    pass
        model = hs.observe(
            hs.create_model("bi-house-ckpt", "Bargain Bend"),
            entities={"table.1": {"kind": "DINING_TABLE", "confidence": "LOCAL_OBSERVED"}},
            captures=["capture:lot-a", "capture:lot-b"],
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dist = tmp_path / "dist" / "house-state"
            dist.mkdir(parents=True)

            def fake_root(contract=None):
                return dist

            with mock.patch.object(hs, "_storage_root", fake_root), mock.patch.object(hs, "ROOT", tmp_path):
                receipt = hs.persist_checkpoint(model, label="pre-place")
                self.assertEqual(receipt["state"], "CHECKPOINT_PERSISTED")
                self.assertEqual(receipt["receipt"]["continuity"], "SAME_MODEL_PERSISTED_NOT_BLANK_SLATE")
                model_file = tmp_path / receipt["model_path"]
                self.assertTrue(model_file.is_file())
                loaded = json.loads(model_file.read_text(encoding="utf-8"))
                self.assertEqual(loaded["revision"], model["revision"])
                self.assertIn("table.1", loaded["entities"])

    def test_recovery_advice_prefers_load_not_overwrite(self):
        advice = hs.recovery_advice(has_known_good_save=True)
        self.assertEqual(advice["gate"], "LOAD_LAST_KNOWN_GOOD_SAVE")
        self.assertIn("do not Save over", advice["do"])


if __name__ == "__main__":
    unittest.main()
