"""Offline falsifiers for per-profile lot floor maps."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from betterinstincts.installation_profiles import set_toggle
from betterinstincts.lot_floor_map import (
    LotFloorMapError,
    assess_interaction_against_memorial,
    ensure_floor_map,
    floor_map_path,
    infer_object_kind,
    ingest_parts_buy_observations,
    invalidate_memorial,
    list_remap_targets,
    load_contract,
    load_floor_map,
    memorialize_object,
    on_build_mode_entered,
    client_center_from_bbox,
    opportunistic_needs_map,
    record_build_select_inspect,
    record_builder_placement,
    upsert_object,
)


class LotFloorMapTests(unittest.TestCase):
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
            # Creates settings.v1.json with default profile + auto floor-map on.
            set_toggle("learning.lot_floor_map_auto", True, self.settings)

    def _patched(self):
        return patch.multiple(
            "betterinstincts.lot_floor_map",
            settings_path=lambda **_k: self.settings,
        )

    def test_contract_pins_kinds_and_auto_build(self):
        cfg = load_contract()
        self.assertIn("COMPUTER_DESKTOP", cfg["object_kinds"])
        self.assertIn("ROBOTICS_WORKSTATION", cfg["object_kinds"])
        self.assertTrue(cfg["auto_on_build"]["default"])
        self.assertEqual(cfg["auto_on_build"]["setting_key"], "learning.lot_floor_map_auto")
        self.assertFalse(cfg["execute_allowed_default"])

    def test_ensure_and_build_trigger_write_private_floors(self):
        with self._patched():
            out = ensure_floor_map(
                profile_id="default",
                lot_key="household-n4-lab",
                settings_file=self.settings,
            )
            path = Path(out["path"])
            self.assertTrue(path.is_file())
            self.assertIn("floors", str(path).replace("\\", "/"))
            doc = load_floor_map(path)
            self.assertIn("COMPUTER_DESKTOP", [r["kind"] for r in doc["objects"].values()])
            build = on_build_mode_entered(
                profile_id="default",
                lot_key="household-n4-lab",
                settings_file=self.settings,
            )
            self.assertEqual(build["state"], "FLOOR_MAP_ENSURED")
            self.assertTrue(
                any(t["trigger"] == "BUILD_MODE_ENTERED" for t in load_floor_map(path)["triggers"])
            )

    def test_auto_skip_when_toggle_false(self):
        with self._patched():
            set_toggle("learning.lot_floor_map_auto", False, self.settings)
            out = on_build_mode_entered(
                profile_id="default",
                lot_key="household-n4-lab",
                settings_file=self.settings,
            )
            self.assertEqual(out["state"], "FLOOR_MAP_AUTO_SKIPPED")

    def test_upsert_and_ingest_parts_buy(self):
        with self._patched():
            path = floor_map_path(
                profile_id="default", lot_key="household-n4-lab", settings_file=self.settings
            )
            ensure_floor_map(
                profile_id="default", lot_key="household-n4-lab", settings_file=self.settings
            )
            doc = load_floor_map(path)
            upsert_object(
                doc,
                kind="COMPUTER_DESKTOP",
                object_id="desk_computer_progress_bar",
                client_xy=[1299, 280],
                status="OBSERVED",
                path_ids=["computer_order_upgrade_parts"],
            )
            ledger = {
                "targets": {
                    "live.phone": {"client_xy": [282, 1055]},
                    "phone.shopping_bag": {
                        "client_xy": [216, 857],
                        "status": "WRONG_CONTROL_GIFTS",
                        "note": "gifts",
                    },
                    "live.desk_laptop": {"client_xy": [1000, 378]},
                },
                "steps": [],
            }
            ingested = ingest_parts_buy_observations(
                ledger,
                profile_id="default",
                lot_key="household-n4-lab",
                settings_file=self.settings,
            )
            self.assertEqual(ingested["state"], "FLOOR_MAP_INGESTED")
            final = load_floor_map(path)
            self.assertIn("phone_hud", final["objects"])
            self.assertIn("avoid_plumbob_lamps", final["objects"])
            self.assertIn("robotics_workstation_primary", final["objects"])

    def test_unknown_kind_fails_closed(self):
        with self._patched():
            ensure_floor_map(
                profile_id="default", lot_key="lot-a", settings_file=self.settings
            )
            doc = load_floor_map(
                floor_map_path(profile_id="default", lot_key="lot-a", settings_file=self.settings)
            )
            with self.assertRaisesRegex(LotFloorMapError, "UNKNOWN_OBJECT_KIND"):
                upsert_object(doc, kind="MAGIC_PORTAL", status="OBSERVED")

    def test_memorial_freeze_and_interaction_invalidation(self):
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
            upsert_object(
                doc,
                kind="COMPUTER_DESKTOP",
                object_id="desk_computer_primary",
                client_xy=[1299, 280],
                status="OBSERVED",
                path_ids=["computer_order_upgrade_parts"],
            )
            memorialize_object(
                doc,
                object_id="desk_computer_primary",
                expected_interactions=["Order", "Purchase Upgrade Parts"],
            )
            # Casual OBSERVED noise must not move durable xy.
            upsert_object(
                doc,
                kind="COMPUTER_DESKTOP",
                object_id="desk_computer_primary",
                client_xy=[1, 2],
                status="OBSERVED",
            )
            row = doc["objects"]["desk_computer_primary"]
            self.assertEqual(row["status"], "MEMORIALIZED")
            self.assertEqual(row["client_xy"], [1299, 280])
            self.assertEqual(row["last_client_xy"], [1, 2])
            keep = assess_interaction_against_memorial(
                doc,
                object_id="desk_computer_primary",
                observed_interactions=["Order", "Purchase Upgrade Parts", "More Choices"],
            )
            self.assertEqual(keep["state"], "MEMORIAL_STILL_VALID")
            stale = assess_interaction_against_memorial(
                doc,
                object_id="desk_computer_primary",
                observed_interactions=["Online Charity", "Donate $10 to..."],
            )
            self.assertEqual(stale["state"], "INVALIDATED_NEEDS_REMAP")
            self.assertEqual(
                doc["objects"]["desk_computer_primary"]["status"], "STALE_NEEDS_REMAP"
            )
            self.assertEqual(list_remap_targets(doc), ["desk_computer_primary"])
            # Remap then re-memorialize.
            upsert_object(
                doc,
                kind="COMPUTER_DESKTOP",
                object_id="desk_computer_primary",
                client_xy=[1189, 281],
                status="HIT_ATTESTED",
                force_remap=True,
                path_ids=["computer_order_upgrade_parts"],
            )
            memorialize_object(
                doc,
                object_id="desk_computer_primary",
                expected_interactions=["Order", "Purchase Upgrade Parts"],
            )
            self.assertEqual(
                doc["objects"]["desk_computer_primary"]["client_xy"], [1189, 281]
            )
            with self.assertRaisesRegex(LotFloorMapError, "UNKNOWN_INVALIDATION_REASON"):
                invalidate_memorial(
                    doc, object_id="desk_computer_primary", reason="FEELING_LUCKY"
                )

    def test_record_build_select_inspect_documents_params_and_xy(self):
        with self._patched():
            out = record_build_select_inspect(
                profile_id="default",
                lot_key="household-n4-lab",
                catalog_name="Glass Top Dining Table",
                bbox_client=[1000, 200, 1208, 296],
                capture_ref="capture:census-1",
                camera_revision="camera:build-t-room-fit",
                price="§450",
                category="Surfaces",
                params={"energy": None, "environment": 2},
                note="select-inspect",
                settings_file=self.settings,
            )
            self.assertEqual(out["state"], "BUILD_CENSUS_RECORDED")
            self.assertEqual(out["zoom_mode"], "BUILD_TOP_DOWN_MAP")
            self.assertEqual(out["client_xy"], [1104, 248])
            self.assertEqual(out["click_target"], "BBOX_CENTER")
            doc = load_floor_map(Path(out["path"]))
            row = doc["objects"][out["object_id"]]
            self.assertEqual(row["catalog_name"], "Glass Top Dining Table")
            self.assertEqual(row["client_xy"], [1104, 248])
            self.assertEqual(row["census_method"], "BUILD_SELECT_INSPECT_ESCAPE")
            self.assertTrue(row["escape_required_after_inspect"])
            self.assertTrue(doc["census_zoom"]["room_fit_attested"])

    def test_builder_placement_maps_center_and_chair_desk_link(self):
        self.assertEqual(client_center_from_bbox([10, 20, 30, 40]), [20, 30])
        with self._patched():
            desk = record_builder_placement(
                profile_id="default",
                lot_key="household-n4-lab",
                catalog_name="Simple Desk",
                object_id="desk_surface_1",
                bbox_client=[400, 400, 600, 500],
                capture_ref="capture:place-desk",
                camera_revision="camera:build-place-1",
                kind="BUILD_CENSUS_ITEM",
                settings_file=self.settings,
            )
            self.assertEqual(desk["state"], "BUILD_PLACEMENT_RECORDED")
            self.assertEqual(desk["client_xy"], [500, 450])
            self.assertEqual(desk["runtime"], "HOST_LISTENER_COOPERATIVE_TICK")
            self.assertIn("OS_TASK_SCHEDULER", desk["not_runtime"])
            chair = record_builder_placement(
                profile_id="default",
                lot_key="household-n4-lab",
                catalog_name="Office Chair",
                object_id="chair_1",
                bbox_client=[480, 500, 560, 580],
                capture_ref="capture:place-chair",
                camera_revision="camera:build-place-1",
                parent_object_id="desk_surface_1",
                link_relation="SEATED_AT",
                settings_file=self.settings,
            )
            self.assertEqual(chair["state"], "BUILD_PLACEMENT_RECORDED")
            doc = load_floor_map(Path(chair["path"]))
            self.assertEqual(doc["objects"]["chair_1"]["parent_object_id"], "desk_surface_1")
            rels = {e["relation"] for e in doc["graph"]["edges"]}
            self.assertIn("SEATED_AT", rels)

    def test_opportunistic_needs_map_preferred_over_blind_resample(self):
        self.assertEqual(infer_object_kind("fridge_computer_desk"), "COMPUTER_DESKTOP")
        with self._patched():
            out = opportunistic_needs_map(
                profile_id="default",
                lot_key="household-n4-lab",
                target_id="desk_computer_primary",
                need_id="hunger",
                observation={
                    "source": "HOST_CAPTURE",
                    "capture_ref": "capture:needs-1",
                    "camera_revision": "camera:7",
                    "bbox_client": [1200, 200, 1400, 360],
                },
                settings_file=self.settings,
            )
            self.assertEqual(out["state"], "NEEDS_MAP_OBSERVED")
            self.assertEqual(out["client_xy"], [1300, 280])
            self.assertEqual(out["source"], "NEEDS_INVESTIGATION")
            # Second pass with memorial keeps without xy rewrite.
            path = floor_map_path(
                profile_id="default", lot_key="household-n4-lab", settings_file=self.settings
            )
            doc = load_floor_map(path)
            memorialize_object(
                doc,
                object_id="desk_computer_primary",
                expected_interactions=["Order"],
            )
            from betterinstincts.lot_floor_map import save_floor_map

            save_floor_map(doc, path)
            kept = opportunistic_needs_map(
                profile_id="default",
                lot_key="household-n4-lab",
                target_id="desk_computer_primary",
                observation={
                    "capture_ref": "capture:needs-2",
                    "camera_revision": "camera:8",
                    "client_xy": [9, 9],
                },
                settings_file=self.settings,
            )
            self.assertEqual(kept["state"], "MEMORIAL_REUSED")
            final = load_floor_map(path)
            self.assertEqual(final["objects"]["desk_computer_primary"]["client_xy"], [1300, 280])


if __name__ == "__main__":
    unittest.main()
