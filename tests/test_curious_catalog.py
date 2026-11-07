import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from betterinstincts.curious_catalog import (
    CuriousCatalogError,
    activate,
    deactivate,
    evaluate_advisory,
    load_contract,
    money_garden_shop_list,
    plan_reveal,
    reject_if_slash_joined,
    shelf_peek_prompt,
    status,
    steps_to_commands,
)


class CuriousCatalogTests(unittest.TestCase):
    def test_contract_invariants(self):
        cfg = load_contract()
        self.assertTrue(cfg["activation"]["never_on_startup"])
        self.assertTrue(cfg["activation"]["never_touch_game_speed"])
        self.assertEqual(cfg["notice"]["default_option_id"], "not_today")
        self.assertIn("buydebug", cfg["reveal_sequence"]["forbidden_typable_forms"])
        self.assertGreaterEqual(len(cfg["money_garden_shop_list"]), 8)

    def test_slash_join_forbidden(self):
        with self.assertRaises(CuriousCatalogError):
            reject_if_slash_joined("bb.showhiddenobjects / buydebug")
        with self.assertRaises(CuriousCatalogError):
            reject_if_slash_joined("buydebug")

    def test_plan_one_command_per_line(self):
        plan = plan_reveal()
        cmds = steps_to_commands(plan)
        self.assertEqual(cmds, ["testingcheats enabled true", "bb.showhiddenobjects"])
        self.assertTrue(plan["never_touch_game_speed"])
        self.assertTrue(any(r["id"] == "quill_fruit" for r in plan["shop_list"]))

    def test_shop_list_s_tier(self):
        rows = money_garden_shop_list(tier="S")
        self.assertTrue(rows)
        self.assertTrue(all(r["money_tier"] == "S" for r in rows))

    def test_prompt_immersive(self):
        prompt = shelf_peek_prompt()
        self.assertEqual(prompt["title"], "CURIOUS CATALOG")
        self.assertEqual(prompt["default_option_id"], "not_today")

    def test_session_and_idle_advisory(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("betterinstincts.curious_catalog.SESSION_ROOT", Path(tmp)):
                sid = "lab-unit"
                self.assertEqual(status(sid)["state"], "INACTIVE")
                activate(sid)
                self.assertEqual(status(sid)["state"], "ACTIVE")
                deactivate(sid)
        adv = evaluate_advisory(session_active=False, whims=["alien fruit"])
        self.assertEqual(adv["gate"], "CURIOUS_CATALOG_IDLE")
        self.assertFalse(adv["autorun"])

    def test_cli_compiles(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "curious_catalog.py"
        compile(script.read_text(encoding="utf-8"), str(script), "exec")

    def test_contract_json(self):
        raw = json.loads(
            (Path(__file__).resolve().parents[1] / "contracts" / "curious-catalog.v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(raw["version"], 3)


if __name__ == "__main__":
    unittest.main()
