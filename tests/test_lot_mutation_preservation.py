"""Regression: no Build/Buy purchase or structural edit before whole-lot backup."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from betterinstincts import build_library_checkpoint as blc
from betterinstincts import house_state as hs


def observed_two_story_lot():
    captures = ["capture:floor-one", "capture:floor-two", "capture:living-one", "capture:living-two"]
    entities = {}
    for number in (1, 2):
        story = f"FLOOR_{number}"
        base = {"confidence": "LOCAL_OBSERVED", "story": story,
                "zone": "LIVING", "domain": "INDOOR_FLOOR",
                "enclosure": "INSIDE", "status": "PRESENT"}
        entities[f"floor.{number}"] = dict(base, kind="FLOOR_TILE")
        entities[f"room.{number}"] = dict(base, kind="ROOM_ZONE")
        entities[f"sofa.{number}"] = dict(base, kind="SOFA",
                                         function_tags=["living"], style_tags=["modern"])
    model = hs.observe(hs.create_model("whole-lot-proof", "Bargain Bend"),
                       entities=entities, captures=captures)
    manifest = {
        "operator_confirmed": True,
        "all_stories_inspected": True,
        "lot_id": model["lot_id"],
        "model_revision": model["revision"],
        "floors": {
            f"FLOOR_{number}": {"rooms": [f"FLOOR_{number}:LIVING"],
                                "capture_ref": f"capture:floor-{'one' if number == 1 else 'two'}"}
            for number in (1, 2)
        },
        "rooms": {
            f"FLOOR_{number}:LIVING": {"capture_ref": f"capture:living-{'one' if number == 1 else 'two'}",
                                        "function_labels": ["living"], "style_labels": ["modern"]}
            for number in (1, 2)
        },
    }
    return model, manifest


class FullLotMutationProtectionTests(unittest.TestCase):
    def test_all_build_buy_actions_require_backup_including_inventory_and_purchase(self):
        model, _ = observed_two_story_lot()
        for action, kwargs in (
            ("PLACE_FROM_CATALOG", {"place_kind": "SOFA"}),
            ("BACKSPACE_TO_INVENTORY", {"targets": ["sofa.1"]}),
            ("SLEDGE", {"targets": ["floor.2"]}),
            ("HAND_MOVE", {"targets": ["sofa.2"]}),
            ("BUY_FROM_CATALOG", {"place_kind": "SOFA"}),
            ("SELL_OBJECT", {"targets": ["sofa.1"]}),
            ("DELETE_FLOOR", {"targets": ["floor.2"]}),
        ):
            with self.subTest(action=action):
                result = hs.admit_mutation(model, action, **kwargs)
                self.assertEqual(result["state"], "MUTATION_DENIED")
                self.assertEqual(result["reason"], "LOT_MUTATION_WITHOUT_COMPLETE_BACKUP")
                self.assertFalse(result["execute_allowed"])

    def test_partial_scan_or_missing_second_floor_cannot_attest_library(self):
        model, manifest = observed_two_story_lot()
        manifest["floors"].pop("FLOOR_2")
        with self.assertRaisesRegex(blc.BuildLibraryCheckpointError, "COVERAGE_MISMATCH"):
            hs.attest_library_save(model, building_id=model["lot_id"],
                                   library_item_name="BI Pre Edit Two Stories",
                                   capture_ref="capture:gallery-save",
                                   lot_manifest=manifest, operator_confirmed=True)

    def test_room_without_classification_denied(self):
        model, manifest = observed_two_story_lot()
        manifest["rooms"]["FLOOR_2:LIVING"]["style_labels"] = []
        with self.assertRaisesRegex(blc.BuildLibraryCheckpointError, "ROOM_STYLE_MISSING"):
            hs.attest_library_save(model, building_id=model["lot_id"],
                                   library_item_name="BI Pre Edit Two Stories",
                                   capture_ref="capture:gallery-save",
                                   lot_manifest=manifest, operator_confirmed=True)

    def test_unscanned_room_or_hypothesis_denied(self):
        model, manifest = observed_two_story_lot()
        model = hs.observe(model, entities={
            "room.3": {"kind": "ROOM_ZONE", "story": "FLOOR_2", "zone": "OFFICE",
                        "domain": "INDOOR_FLOOR", "confidence": "HYPOTHESIS"}
        })
        manifest["model_revision"] = model["revision"]
        with self.assertRaisesRegex(blc.BuildLibraryCheckpointError, "UNCLASSIFIED_OBSERVATIONS"):
            blc.validate_full_lot_manifest(model, manifest)

    def test_legacy_library_capture_and_save_as_do_not_satisfy_backup(self):
        model, _ = observed_two_story_lot()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(hs, "ROOT", Path(tmp)):
            legacy = hs.attest_library_save(model, building_id=model["lot_id"],
                                            library_item_name="BI Legacy Save",
                                            capture_ref="capture:gallery-save",
                                            operator_confirmed=True)
            result = hs.admit_mutation(legacy, "BACKSPACE_TO_INVENTORY", targets=["sofa.1"])
            self.assertEqual(result["violation"], "LOT_MUTATION_WITHOUT_COMPLETE_BACKUP")
            self.assertFalse(result["execute_allowed"])

    def test_verified_whole_lot_backup_admits_then_revision_change_denies(self):
        model, manifest = observed_two_story_lot()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(hs, "ROOT", Path(tmp)):
            saved = hs.attest_library_save(model, building_id=model["lot_id"],
                                           library_item_name="BI Pre Edit Two Stories",
                                           capture_ref="capture:gallery-save",
                                           lot_manifest=manifest, operator_confirmed=True)
            fresh = blc.library_checkpoint_fresh(saved, building_id=model["lot_id"])
            self.assertTrue(fresh["fresh"])
            self.assertEqual(fresh["lot_inventory"]["floor_count"], 2)
            self.assertEqual(fresh["lot_inventory"]["room_count"], 2)
            permitted = hs.admit_mutation(saved, "BACKSPACE_TO_INVENTORY", targets=["sofa.1"])
            self.assertEqual(permitted["state"], "MUTATION_ADMITTED")
            self.assertFalse(permitted["execute_allowed"])  # Offline is not live SendInput authority.
            advanced = hs.observe(saved, note="subsequent game observation")
            rejected = hs.admit_mutation(advanced, "BACKSPACE_TO_INVENTORY", targets=["sofa.1"])
            self.assertEqual(rejected["state"], "MUTATION_DENIED")
            self.assertEqual(rejected["violation"], "STALE_LIBRARY_CHECKPOINT")

    def test_missing_persisted_metadata_never_grants_backup(self):
        model, manifest = observed_two_story_lot()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(hs, "ROOT", Path(tmp)):
            saved = hs.attest_library_save(model, building_id=model["lot_id"],
                                           library_item_name="BI Pre Edit Two Stories",
                                           capture_ref="capture:gallery-save",
                                           lot_manifest=manifest, operator_confirmed=True)
            path = hs.model_path(saved["run_id"], saved["lot_id"])
            path.unlink()
            result = hs.admit_mutation(saved, "BACKSPACE_TO_INVENTORY", targets=["sofa.2"])
            self.assertEqual(result["violation"], "LOT_MUTATION_WITHOUT_COMPLETE_BACKUP")
            self.assertFalse(result["execute_allowed"])


if __name__ == "__main__":
    unittest.main()
