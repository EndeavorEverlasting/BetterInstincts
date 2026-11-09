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

    def test_catalog_includes_diy_core(self):
        snap = catalog_snapshot()
        ids = {row["id"] for row in snap["skills"]}
        self.assertEqual(ids, {"handiness", "robotics", "fabrication", "programming"})
        self.assertIn("practice_skill", snap["forbidden"])
        self.assertIn("claim_BI005", snap["forbidden"])

    def test_default_bundle_plan_super_useful(self):
        plan = plan_skill_force(bundle="diy_maker", game_mode="live")
        self.assertEqual(plan["state"], "DIY_SKILL_FORCE_PLAN_READY")
        self.assertEqual(plan["level"], 10)
        self.assertFalse(plan["execute_allowed"])
        self.assertTrue(plan["not_bi005"])
        self.assertTrue(plan["not_practice_skill"])
        steps = [s["step"] for s in plan["steps"]]
        self.assertNotIn("ENSURE_LIVE_MODE", steps)
        self.assertIn("REQUIRE_ACTIVE_SIM_SELECTION", steps)
        self.assertIn("PRESERVE_OPERATOR_MODE", steps)
        cmds = steps_to_commands(plan)
        self.assertEqual(cmds[0], "testingcheats enabled true")
        self.assertIn("stats.set_skill_level Major_Handiness 10", cmds)
        self.assertIn("stats.set_skill_level Major_Robotics 10", cmds)
        self.assertIn("stats.set_skill_level Major_Fabrication 10", cmds)
        self.assertIn("stats.set_skill_level Major_Programming 10", cmds)

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
            plan_skill_force(skill_ids=["cooking"], bundle=None)
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
        plan = plan_skill_force(bundle="diy_maker", player_directed=True)
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
        self.assertEqual(raw["version"], 1)
        self.assertEqual(raw["bundles"]["diy_maker"]["default_level"], 10)


if __name__ == "__main__":
    unittest.main()
