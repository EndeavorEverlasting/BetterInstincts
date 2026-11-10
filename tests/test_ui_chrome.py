"""Offline falsifiers for host UI chrome maps and AOK deposit recipes."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from betterinstincts.ui_chrome import (
    UIChromeError,
    bottom_right_panel_hotkey_rows,
    glossary_snapshot,
    load_contract,
    plan_catalog_to_inventory,
    prefer_hotkey_step,
    resolve_bottom_right_panel_hotkey,
    resolve_catalog_item,
    resolve_target,
)

ROOT = Path(__file__).resolve().parents[1]


class UIChromeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = load_contract()

    def test_contract_aok_and_deposit_safety(self) -> None:
        self.assertEqual(self.cfg["catalog_items"]["a_ok_bloomer"]["search_term"], "A-OK")
        recipe = self.cfg["recipes"]["catalog_to_household_inventory"]
        self.assertIs(recipe["execute_allowed_default"], False)
        self.assertIn("LOT_PLACEMENT", recipe["forbidden"])
        self.assertEqual(recipe["mutating_action"], "BACKSPACE_TO_INVENTORY")

    def test_resolve_search_field_1920x1080(self) -> None:
        hit = resolve_target(
            "catalog.search_field",
            mode="BUILD",
            profile="1920x1080",
            client_width=1920,
            client_height=1080,
            cfg=self.cfg,
        )
        self.assertEqual(hit["x"], 140)
        self.assertEqual(hit["y"], 864)
        self.assertIs(hit["execute_allowed"], False)

    def test_resolve_unknown_profile_fails(self) -> None:
        with self.assertRaisesRegex(UIChromeError, "UNKNOWN_RESOLUTION_PROFILE"):
            resolve_target("catalog.search_field", mode="BUILD", profile="800x600", cfg=self.cfg)

    def test_live_camera_zoom_hotkeys_catalogued(self) -> None:
        by_id = {h["id"]: h for h in glossary_snapshot(self.cfg)["modes"]["LIVE"]["hotkeys"]}
        self.assertEqual(by_id["CAMERA_ZOOM_IN"]["chord"], ["Z"])
        self.assertEqual(by_id["CAMERA_ZOOM_OUT"]["chord"], ["X"])
        self.assertEqual(by_id["CAMERA_ZOOM_IN"]["preferred_channel"], "KEY")
        self.assertIn("RIGHT_CLICK", by_id["CAMERA_ZOOM_IN"]["not"])
        self.assertEqual(by_id["CAMERA_ZOOM_IN"]["wheel_equivalent"], "SCROLL_WHEEL_ZOOM_IN")

    def test_bottom_right_panel_hotkeys_catalogued(self) -> None:
        rows = bottom_right_panel_hotkey_rows(cfg=self.cfg)
        by_panel = {r["panel_id"]: r["chord"] for r in rows}
        self.assertEqual(by_panel["aspirations"], ["G"])
        self.assertEqual(by_panel["career"], ["J"])
        self.assertEqual(by_panel["skills"], ["L"])
        self.assertEqual(by_panel["relationships"], ["R"])
        self.assertEqual(by_panel["personal_inventory"], ["I"])
        self.assertEqual(by_panel["simology"], ["Y"])
        self.assertEqual(by_panel["needs"], ["O"])
        self.assertEqual(by_panel["clubs"], ["U"])
        work = resolve_bottom_right_panel_hotkey("work", cfg=self.cfg)
        self.assertEqual(work["hotkey_id"], "PANEL_CAREER")
        self.assertEqual(work["chord"], ["J"])
        self.assertEqual(work["channel"], "HOTKEY")
        self.assertFalse(work["execute_allowed"])
        gloss = glossary_snapshot(cfg=self.cfg)
        self.assertEqual(len(gloss["bottom_right_panel_hotkeys"]), 8)
        with self.assertRaisesRegex(UIChromeError, "UNKNOWN_BOTTOM_RIGHT_PANEL"):
            resolve_bottom_right_panel_hotkey("phone", cfg=self.cfg)

    def test_live_mode_refuses_catalog_target(self) -> None:
        with self.assertRaisesRegex(UIChromeError, "TARGET_NOT_IN_MODE"):
            resolve_target("catalog.search_field", mode="LIVE", cfg=self.cfg)

    def test_hotkeys_backspace_in_build_and_buy(self) -> None:
        gloss = glossary_snapshot(self.cfg)
        for mode in ("BUILD", "BUY"):
            ids = {h["id"] for h in gloss["modes"][mode]["hotkeys"]}
            self.assertIn("BACKSPACE_TO_HOUSEHOLD_INVENTORY", ids)
            self.assertFalse(any(h.get("proves_mode") for h in gloss["modes"][mode]["hotkeys"] if "proves_mode" in h))

    def test_live_panels_are_stubs_without_click_points(self) -> None:
        panels = glossary_snapshot(self.cfg)["modes"]["LIVE"]["panels"]
        for name in ("needs", "career", "skills", "phone"):
            status = panels[name]["status"]
            # Hotkeys may be catalogued; hitboxes stay uncalibrated — no click points.
            self.assertTrue(
                status.startswith("UNCALIBRATED") or "UNCALIBRATED" in status,
                msg=f"{name}={status}",
            )
            self.assertNotIn("client_xy", panels[name])
            self.assertNotIn("hitbox", panels[name])
        self.assertEqual(glossary_snapshot(self.cfg)["modes"]["LIVE"]["targets"], [])

    def test_aok_plan_types_AOK_and_forbids_placement(self) -> None:
        plan = plan_catalog_to_inventory(
            "a_ok_bloomer",
            mode="BUILD",
            client_width=1920,
            client_height=1080,
            cfg=self.cfg,
        )
        self.assertEqual(plan["search_term"], "A-OK")
        self.assertIs(plan["execute_allowed"], False)
        self.assertEqual(plan["input_preference"], "HOTKEY_FIRST_WHEN_EQUIVALENT")
        self.assertIn("LOT_PLACEMENT", plan["forbidden"])
        typed = [s for s in plan["steps"] if s.get("op") == "TYPE_TEXT"]
        self.assertEqual(typed[0]["text"], "A-OK")
        clicks = [s for s in plan["steps"] if s.get("op") == "CLICK_TARGET"]
        self.assertEqual(clicks[0]["resolved"]["x"], 140)
        self.assertEqual(clicks[0]["resolved"]["y"], 864)
        self.assertEqual(clicks[0]["verify"], "VERIFY_THEN_ESCAPE_ON_MISS")
        self.assertEqual(clicks[0]["channel"], "MOUSE_FALLBACK")
        keys = [s for s in plan["steps"] if s.get("op") == "KEY" and s.get("chord") == ["BACKSPACE"]]
        self.assertEqual(len(keys), 1)
        self.assertEqual(keys[0]["channel"], "HOTKEY")
        mode_keys = [
            s for s in plan["steps"]
            if s.get("op") == "KEY" and s.get("hotkey_id") == "MODE_BUILD"
        ]
        self.assertEqual(len(mode_keys), 1)
        self.assertEqual(mode_keys[0]["chord"], ["F3"])
        self.assertFalse(any(s.get("hotkey_id") == "MODE_BUY" for s in plan["steps"]))

    def test_hotkey_first_rewrites_click_when_preferred_hotkey(self) -> None:
        rewritten = prefer_hotkey_step(
            {"op": "CLICK_TARGET", "target": "catalog.search_field", "preferred_hotkey": "UNDO"},
            mode="BUILD",
            cfg=self.cfg,
        )
        self.assertEqual(rewritten["op"], "KEY")
        self.assertEqual(rewritten["channel"], "HOTKEY")
        self.assertEqual(rewritten["hotkey_id"], "UNDO")
        self.assertEqual(rewritten["chord"], ["CTRL", "Z"])
        self.assertEqual(rewritten["rewritten_from"], "CLICK_TARGET")

    def test_mouse_fallback_preserved_without_hotkey(self) -> None:
        step = prefer_hotkey_step(
            {"op": "CLICK_TARGET", "target": "catalog.search_field"},
            mode="BUILD",
            cfg=self.cfg,
        )
        self.assertEqual(step["op"], "CLICK_TARGET")
        self.assertEqual(step["channel"], "MOUSE_FALLBACK")
        self.assertEqual(step["mouse_fallback_reason"], "NO_CATALOGUED_SEARCH_FOCUS_HOTKEY")

    def test_unknown_hotkey_id_fails_closed(self) -> None:
        with self.assertRaisesRegex(UIChromeError, "UNKNOWN_HOTKEY_ID"):
            prefer_hotkey_step(
                {"op": "KEY", "chord": ["X"], "hotkey_id": "NOT_A_REAL_HOTKEY"},
                mode="BUILD",
                cfg=self.cfg,
            )

    def test_buy_plan_prefers_f2_not_f3(self) -> None:
        plan = plan_catalog_to_inventory("a_ok_bloomer", mode="BUY", cfg=self.cfg)
        self.assertTrue(any(s.get("hotkey_id") == "MODE_BUY" for s in plan["steps"]))
        self.assertFalse(any(s.get("hotkey_id") == "MODE_BUILD" for s in plan["steps"]))

    def test_aok_live_handoff_is_discoverable_and_has_proof_gates(self) -> None:
        """Protect the handoff from regressing to a plan-only success claim."""
        name = "BI-AOK-BLOOMER-INVENTORY-P04-2026-11-09.md"
        handoff = ROOT / "docs" / "handoff" / name
        self.assertTrue(handoff.is_file())
        body = handoff.read_text(encoding="utf-8")
        owner_doc = (ROOT / "docs" / "UI_CHROME.md").read_text(encoding="utf-8")
        self.assertIn(name, owner_doc)
        for required in (
            "AOK",
            "Backspace",
            "HOUSEHOLD_INVENTORY",
            "AOK_IN_HOUSEHOLD_INVENTORY_OBSERVED",
            "ALREADY_PRESENT",
            "NOT_PROVEN",
            "15-second",
            "CANDIDATE_UNVERIFIED",
            "BI-002",
        ):
            with self.subTest(required=required):
                self.assertIn(required, body)

    def test_live_plan_refused(self) -> None:
        with self.assertRaisesRegex(UIChromeError, "CATALOG_DEPOSIT_REQUIRES_BUY_OR_BUILD"):
            plan_catalog_to_inventory("a_ok_bloomer", mode="LIVE", cfg=self.cfg)

    def test_aok_search_drift_rejected_on_load(self) -> None:
        bad = json.loads(json.dumps(self.cfg))
        bad["catalog_items"]["a_ok_bloomer"]["search_term"] = "AOK"
        path = ROOT / "dist" / "game-host" / "_tmp_ui_chrome_bad.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaisesRegex(UIChromeError, "AOK_SEARCH_TERM_REQUIRED"):
            load_contract(path)
        path.unlink(missing_ok=True)

    def test_wall_shelf_synonym_resolves_to_aok_bloomer(self) -> None:
        """Operator correction: wall shelf is the coveted Bloomer, not a new shelf."""
        for query in (
            "wall shelf",
            "Wall Shelf",
            "wall_shelf",
            "vertical garden",
            "a-ok",
            "bloomer",
            "A-OK-Bloomer Vertical Garden",
        ):
            with self.subTest(query=query):
                hit = resolve_catalog_item(query, cfg=self.cfg)
                self.assertEqual(hit["item_id"], "a_ok_bloomer")
                self.assertEqual(hit["search_term"], "A-OK")
                self.assertEqual(hit["resolved_via"], "synonym")

    def test_plan_accepts_wall_shelf_synonym(self) -> None:
        plan = plan_catalog_to_inventory(
            "wall shelf",
            mode="BUILD",
            client_width=1920,
            client_height=1080,
            cfg=self.cfg,
        )
        self.assertEqual(plan["item_id"], "a_ok_bloomer")
        self.assertEqual(plan["search_term"], "A-OK")
        self.assertEqual(plan["display_name"], "A-OK-Bloomer Vertical Garden")

    def test_wall_shelf_synonym_required_on_load(self) -> None:
        bad = json.loads(json.dumps(self.cfg))
        bad["catalog_items"]["a_ok_bloomer"]["synonyms"] = ["bloomer"]
        path = ROOT / "dist" / "game-host" / "_tmp_ui_chrome_no_shelf.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaisesRegex(UIChromeError, "AOK_WALL_SHELF_SYNONYM_REQUIRED"):
            load_contract(path)
        path.unlink(missing_ok=True)

    def test_unknown_synonym_fails_closed(self) -> None:
        with self.assertRaisesRegex(UIChromeError, "UNKNOWN_CATALOG_ITEM_OR_SYNONYM"):
            resolve_catalog_item("random bookshelf product", cfg=self.cfg)


if __name__ == "__main__":
    unittest.main()
