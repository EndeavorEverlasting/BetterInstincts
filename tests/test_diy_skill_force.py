import json
import unittest
from pathlib import Path

from betterinstincts.diy_skill_force import (
    DiySkillForceError,
    catalog_snapshot,
    load_contract,
    plan_household_skill_force,
    plan_skill_force,
    required_residual_skills,
    resolve_skills,
    skills_panel_observation_policy,
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
        self.assertEqual(cfg["version"], 8)
        self.assertEqual(cfg["household_traverse"]["min_members"], 1)
        self.assertGreaterEqual(int(cfg["household_traverse"]["sanity_max_members"]), 100)
        self.assertEqual(
            next(s for s in cfg["skill_catalog"] if s["id"] == "cooking")["skill_stat"],
            "Major_HomestyleCooking",
        )
        self.assertEqual(
            next(s for s in cfg["skill_catalog"] if s["id"] == "fitness")["skill_stat"],
            "Skill_Fitness",
        )
        self.assertEqual(
            next(s for s in cfg["skill_catalog"] if s["id"] == "natural_living")["skill_stat"],
            "Skill_NLS",
        )
        self.assertTrue(seq["pass_requires_skills_panel_local_observed"])
        self.assertTrue(seq["console_text_is_not_pass"])
        self.assertTrue(seq["level_up_toast_is_not_pass"])
        self.assertEqual(seq["cheat_line_submit"], "type_text_embedded_newline_keybd_event")
        self.assertEqual(seq["open_console_chord_owner"], "scripts.win32_input.send_key_chord")
        self.assertIn("claim_pass_from_console_text", seq["forbidden"])
        self.assertIn("skills_panel_local_observed_required_for_pass", cfg["invariants"])
        self.assertEqual(required_residual_skills(cfg), ["cooking", "fitness", "natural_living"])
        self.assertIn("residual_core", cfg["bundles"])
        self.assertEqual(cfg["household_traverse"]["next_member_key"], "SPACE")
        reward = seq["reward_dialog_accept"]
        self.assertTrue(reward["enabled_by_default"])
        self.assertTrue(reward["never_press_cancel"])
        self.assertEqual(reward["primary_confirm_key"], "ENTER")
        self.assertEqual(seq["typing_owner"], "scripts/win32_input.type_text")
        panel = seq["skills_panel_observation"]
        self.assertEqual(panel["paused_panel_status"], "UNPROVEN_STALE")
        self.assertEqual(panel["verify_default"], "PLAY_BRIEF_OBSERVE_REPAUSE")
        play = panel["play_brief_for_fresh_panel"]
        self.assertEqual(play["min_play_seconds"], 5)
        self.assertEqual(play["max_play_seconds"], 10)
        self.assertTrue(play["always_repause"])
        self.assertIn("leave_sim_speed_running_after_panel_verify", seq["forbidden"])

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
        self.assertIn("stats.set_skill_level Major_HomestyleCooking 10", cmds)
        self.assertIn("stats.set_skill_level Major_Logic 10", cmds)
        self.assertIn("stats.set_skill_level Major_Charisma 10", cmds)
        self.assertIn("stats.set_skill_level Skill_Fitness 10", cmds)
        self.assertIn("stats.set_skill_level Skill_NLS 10", cmds)
        # Residuals are re-applied at the tail so mid-batch truncation cannot drop them.
        tail = cmds[-6:]
        self.assertGreaterEqual(tail.count("stats.set_skill_level Major_HomestyleCooking 10"), 1)
        self.assertGreaterEqual(tail.count("stats.set_skill_level Skill_Fitness 10"), 1)
        self.assertGreaterEqual(tail.count("stats.set_skill_level Skill_NLS 10"), 1)
        self.assertGreaterEqual(cmds.count("stats.set_skill_level Major_HomestyleCooking 10"), 2)
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
        self.assertEqual(raw["version"], 8)
        self.assertEqual(raw["bundles"]["full_unlock"]["default_level"], 10)
        self.assertEqual(raw["required_residual_skills"], ["cooking", "fitness", "natural_living"])
        self.assertTrue(raw["inject_sequence"]["reward_dialog_accept"]["never_press_cancel"])

    def test_skills_panel_dispatch_keeps_paused(self):
        policy = skills_panel_observation_policy(
            purpose="dispatch",
            precious_time=True,
            concurrent_live_cert=True,
            main_goal_unfinished=True,
        )
        self.assertEqual(policy["action"], "KEEP_PAUSED")
        self.assertEqual(policy["panel_status"], "UNPROVEN_STALE")

    def test_skills_panel_verify_play_brief_repause(self):
        policy = skills_panel_observation_policy(
            purpose="verify",
            precious_time=True,
            concurrent_live_cert=True,
            main_goal_unfinished=True,
        )
        self.assertEqual(policy["action"], "PLAY_BRIEF_OBSERVE_REPAUSE")
        self.assertGreaterEqual(policy["play_seconds"], 5)
        self.assertLessEqual(policy["play_seconds"], 10)
        self.assertTrue(policy["always_repause"])
        self.assertEqual(policy["play_key"], "1")
        self.assertEqual(policy["pause_key"], "0")

    def test_plan_includes_keep_paused_and_play_brief_steps(self):
        plan = plan_skill_force(bundle="diy_maker", game_mode="live")
        names = [s.get("step") for s in plan["steps"]]
        self.assertIn("KEEP_PAUSED", names)
        self.assertIn("PLAY_BRIEF_OBSERVE_REPAUSE", names)
        self.assertEqual(plan["skills_panel_observation"]["verify"]["action"], "PLAY_BRIEF_OBSERVE_REPAUSE")

    def test_household_plan_counts_any_members_and_spaces(self):
        plan = plan_household_skill_force(members=3, bundle="full_unlock", game_mode="live")
        self.assertEqual(plan["state"], "HOUSEHOLD_SKILL_FORCE_PLAN_READY")
        self.assertEqual(plan["household_members"], 3)
        self.assertEqual(len(plan["member_plans"]), 3)
        self.assertIsNone(plan["member_plans"][0]["select"])
        self.assertEqual(plan["member_plans"][1]["select"]["key"], "SPACE")
        self.assertEqual(plan["member_plans"][2]["select"]["key"], "SPACE")
        self.assertTrue(plan["member_plans"][1]["select"]["close_console_before"])
        self.assertEqual(plan["required_residual_skills"], ["cooking", "fitness", "natural_living"])
        self.assertTrue(plan["async_detach_supported"])
        self.assertFalse(plan["execute_allowed"])

    def test_household_invalid_member_count_fails_closed(self):
        with self.assertRaises(DiySkillForceError) as ctx:
            plan_household_skill_force(members=0)
        self.assertIn("INVALID_HOUSEHOLD_MEMBER_COUNT", str(ctx.exception))
        with self.assertRaises(DiySkillForceError):
            plan_household_skill_force(members=101)

    def test_household_accepts_observed_n_whatever_size(self):
        # N is observed household size — including large households (e.g. 10).
        for n in (1, 2, 3, 8, 10, 24):
            plan = plan_household_skill_force(members=n, bundle="residual_core")
            self.assertEqual(plan["household_members"], n)
            self.assertEqual(len(plan["member_plans"]), n)

    def test_catalog_exposes_household_and_residuals(self):
        snap = catalog_snapshot()
        self.assertEqual(snap["required_residual_skills"], ["cooking", "fitness", "natural_living"])
        self.assertEqual(snap["household_traverse"]["next_member_key"], "SPACE")
        self.assertIn("residual_core", snap["bundles"])
        self.assertEqual(snap.get("close_console_key"), "CTRL_SHIFT_C_TOGGLE")
        submit = str(snap.get("cheat_line_submit") or "").upper()
        self.assertTrue(
            "NEWLINE" in submit or "ENTER" in submit,
            msg=f"cheat_line_submit must embed newline/Enter submit, got {submit!r}",
        )
        seq = snap.get("inject_sequence") or {}
        self.assertEqual(seq.get("close_console_key"), "CTRL_SHIFT_C_TOGGLE")
        self.assertTrue(seq.get("console_text_is_not_pass"))
        self.assertTrue(seq.get("pass_requires_skills_panel_local_observed"))


if __name__ == "__main__":
    unittest.main()
