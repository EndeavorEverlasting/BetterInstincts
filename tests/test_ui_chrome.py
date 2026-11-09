"""Offline falsifiers for host UI chrome maps and AOK deposit recipes."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from betterinstincts.ui_chrome import (
    UIChromeError,
    glossary_snapshot,
    load_contract,
    plan_catalog_to_inventory,
    resolve_target,
)

ROOT = Path(__file__).resolve().parents[1]


class UIChromeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = load_contract()

    def test_contract_aok_and_deposit_safety(self) -> None:
        self.assertEqual(self.cfg["catalog_items"]["a_ok_bloomer"]["search_term"], "AOK")
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
        self.assertEqual(hit["x"], 125)
        self.assertEqual(hit["y"], 866)
        self.assertIs(hit["execute_allowed"], False)

    def test_resolve_unknown_profile_fails(self) -> None:
        with self.assertRaisesRegex(UIChromeError, "UNKNOWN_RESOLUTION_PROFILE"):
            resolve_target("catalog.search_field", mode="BUILD", profile="800x600", cfg=self.cfg)

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
            self.assertEqual(panels[name]["status"], "UNCALIBRATED_STUB")
        self.assertEqual(glossary_snapshot(self.cfg)["modes"]["LIVE"]["targets"], [])

    def test_aok_plan_types_AOK_and_forbids_placement(self) -> None:
        plan = plan_catalog_to_inventory(
            "a_ok_bloomer",
            mode="BUILD",
            client_width=1920,
            client_height=1080,
            cfg=self.cfg,
        )
        self.assertEqual(plan["search_term"], "AOK")
        self.assertIs(plan["execute_allowed"], False)
        self.assertIn("LOT_PLACEMENT", plan["forbidden"])
        typed = [s for s in plan["steps"] if s.get("op") == "TYPE_TEXT"]
        self.assertEqual(typed[0]["text"], "AOK")
        clicks = [s for s in plan["steps"] if s.get("op") == "CLICK_TARGET"]
        self.assertEqual(clicks[0]["resolved"]["x"], 125)
        keys = [s for s in plan["steps"] if s.get("op") == "KEY" and s.get("chord") == ["BACKSPACE"]]
        self.assertEqual(len(keys), 1)

    def test_live_plan_refused(self) -> None:
        with self.assertRaisesRegex(UIChromeError, "CATALOG_DEPOSIT_REQUIRES_BUY_OR_BUILD"):
            plan_catalog_to_inventory("a_ok_bloomer", mode="LIVE", cfg=self.cfg)

    def test_aok_search_drift_rejected_on_load(self) -> None:
        bad = json.loads(json.dumps(self.cfg))
        bad["catalog_items"]["a_ok_bloomer"]["search_term"] = "a-ok"
        path = ROOT / "dist" / "game-host" / "_tmp_ui_chrome_bad.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaisesRegex(UIChromeError, "AOK_SEARCH_TERM_REQUIRED"):
            load_contract(path)
        path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
