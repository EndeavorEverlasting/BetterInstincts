import json
import unittest
from pathlib import Path

from betterinstincts.diy_skill_force import (
    DiySkillForceError,
    catalog_snapshot,
    load_contract,
    plan_skill_force,
    resolve_skills,
    steps_to_commands,
)


class DiySkillForceTests(unittest.TestCase):
    def test_contract_mode_agnostic(self):
        cfg = load_contract()
        seq = cfg["inject_sequence"]
        self.assertTrue(seq["mode_agnostic"])
        self.assertTrue(seq["never_force_mode_switch"])
        self.assertFalse(seq["require_live_mode"])
        self.assertEqual(seq["activate_testing_cheats"], "testingcheats enabled true")
        self.assertEqual(seq["open_console_chord"], ["CTRL", "SHIFT", "C"])
        self.assertEqual(seq["default_level"], 10)
        self.assertIn("diy_maker", cfg["bundles"])
        self.assertIn("full_unlock", cfg["bundles"])
        self.assertEqual(cfg["version"], 3)
        reward = seq["reward_dialog_accept"]
        self.assertTrue(reward["enabled_by_default"])
        self.assertTrue(reward["never_press_cancel"])
        self.assertEqual(reward["primary_confirm_key"], "ENTER")
        self.assertEqual(seq["typing_owner"], "scripts/win32_input.type_text")

    def test_catalog_includes_diy_and_unlock_cores(self):
        snap = catalog_snapshot()
        ids = {row["id"] for row in snap["skills"]}
        for required in (
            "handiness",
            "robotics",
            "fabrication",
            "programming",
            "cooking",
            "logic",
            "charisma",
            "fitness",
            "gardening",
        ):
            self.assertIn(required, ids)
        self.assertIn("practice_skill", snap["forbidden"])
        self.assertIn("claim_BI005", snap["forbidden"])
        self.assertIn("full_unlock", snap["bundles"])

    def test_diy_maker_bundle_unchanged(self):
        plan = plan_skill_force(bundle="diy_maker", game_mode="live")
        self.assertEqual(plan["state"], "DIY_SKILL_FORCE_PLAN_READY")
        self.assertEqual(plan["level"], 10)
        self.assertFalse(plan["execute_allowed"])
        self.assertTrue(plan["not_bi005"])
        cmds = steps_to_commands(plan)
        self.assertEqual(cmds[0], "testingcheats enabled true")
        self.assertEqual(
            [c for c in cmds if c.startswith("stats.set_skill_level ")],
            [
                "stats.set_skill_level Major_Handiness 10",
                "stats.set_skill_level Major_Robotics 10",
                "stats.set_skill_level Major_Fabrication 10",
                "stats.set_skill_level Major_Programming 10",
            ],
        )

    def test_full_unlock_all_the_way(self):
        plan = plan_skill_force(bundle="full_unlock", level=10, game_mode="live")
        self.assertGreaterEqual(len(plan["skills"]), 30)
        cmds = steps_to_commands(plan)
        self.assertIn("stats.set_skill_level Major_Handiness 10", cmds)
        self.assertIn("stats.set_skill_level Major_Cooking 10", cmds)
        self.assertIn("stats.set_skill_level Major_Logic 10", cmds)
        self.assertIn("stats.set_skill_level Major_Charisma 10", cmds)
        self.assertIn("stats.set_skill_level Major_Fitness 10", cmds)
        self.assertTrue(plan["not_bi005"])
        self.assertFalse(plan["execute_allowed"])
        self.assertTrue(plan["accept_reward_dialogs"])
        accept_steps = [s for s in plan["steps"] if s.get("step") == "ACCEPT_OFFERED_REWARD_TRAIT"]
        self.assertGreaterEqual(len(accept_steps), 2)
        for step in accept_steps:
            self.assertTrue(step["never_press_cancel"])
            self.assertEqual(step["confirm_key"], "ENTER")

    def test_reward_accept_can_be_disabled(self):
        plan = plan_skill_force(
            bundle="diy_maker",
            accept_reward_dialogs=False,
            game_mode="live",
        )
        self.assertFalse(plan["accept_reward_dialogs"])
        self.assertFalse(
            any(s.get("step") == "ACCEPT_OFFERED_REWARD_TRAIT" for s in plan["steps"])
        )

    def test_default_empty_resolves_full_unlock(self):
        rows = resolve_skills()
        ids = [r["id"] for r in rows]
        self.assertIn("handiness", ids)
        self.assertIn("cooking", ids)
        self.assertGreaterEqual(len(ids), 30)

    def test_servo_core_bundle_omits_fabrication(self):
        plan = plan_skill_force(bundle="servo_core", level=10, game_mode="build")
        stats = {s["skill_stat"] for s in plan["skills"]}
        self.assertEqual(stats, {"Major_Handiness", "Major_Robotics", "Major_Programming"})
        self.assertEqual(plan["game_mode"], "build")

    def test_explicit_skills_without_unknown(self):
        rows = resolve_skills(skill_ids=["handiness", "robotics"])
        self.assertEqual([r["id"] for r in rows], ["handiness", "robotics"])

    def test_unknown_skill_fails_closed(self):
        with self.assertRaises(DiySkillForceError) as ctx:
            plan_skill_force(skill_ids=["not_a_real_skill"], bundle=None)
        self.assertIn("UNKNOWN_DIY_SKILL", str(ctx.exception))

    def test_unknown_bundle_fails_closed(self):
        with self.assertRaises(DiySkillForceError) as ctx:
            plan_skill_force(bundle="not_a_bundle")
        self.assertIn("UNKNOWN_DIY_BUNDLE", str(ctx.exception))

    def test_invalid_level_fails_closed(self):
        with self.assertRaises(DiySkillForceError):
            plan_skill_force(bundle="diy_maker", level=0)
        with self.assertRaises(DiySkillForceError):
            plan_skill_force(bundle="diy_maker", level=11)

    def test_player_directed_yields(self):
        plan = plan_skill_force(bundle="full_unlock", player_directed=True)
        self.assertEqual(plan["state"], "YIELD_TO_PLAYER")
        self.assertEqual(plan["steps"], [])
        self.assertFalse(plan["execute_allowed"])

    def test_cli_script_compiles(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "diy_skill_force.py"
        compile(script.read_text(encoding="utf-8"), str(script), "exec")

    def test_contract_json_roundtrip(self):
        raw = json.loads(
            (Path(__file__).resolve().parents[1] / "contracts" / "diy-skill-force.v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(raw["version"], 3)
        self.assertEqual(raw["bundles"]["full_unlock"]["default_level"], 10)
        self.assertTrue(raw["inject_sequence"]["reward_dialog_accept"]["never_press_cancel"])


if __name__ == "__main__":
    unittest.main()
