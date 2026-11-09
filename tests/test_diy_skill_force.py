import json
import unittest
from pathlib import Path

from betterinstincts.diy_skill_force import (
    DiySkillForceError,
    catalog_snapshot,
    classify_reward_trait,
    completed_skill_ids_for_member,
    completion_member_key,
    decide_reward_dialog,
    empty_completion_ledger,
    evaluate_ui_action,
    load_contract,
    plan_household_skill_force,
    plan_skill_force,
    plan_trait_repair,
    trait_repair_commands,
    record_skill_dispatched,
    required_residual_skills,
    resolve_skills,
    save_completion_ledger,
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
        self.assertEqual(cfg["version"], 10)
        self.assertFalse(cfg["execution_policy"]["detached_worker"])
        self.assertTrue(cfg["completion_ledger"]["space_to_next_needing"])
        self.assertIn("skip_skills_already_recorded_complete", cfg["invariants"])
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

    def test_wait_for_input_idle_ready_and_continuous_block(self):
        import scripts.diy_skill_force as cli
        from betterinstincts.player_presence import PresenceProbe
        from unittest.mock import patch

        ready = PresenceProbe(
            foreground_is_sims=True,
            cursor_in_client=False,
            last_input_age_ms=20000,
        )
        with patch("betterinstincts.player_presence.probe_windows", return_value=ready):
            out = cli._wait_for_input_idle(1, idle_ms=15000, timeout_sec=2.0, poll_sec=0.01)
        self.assertEqual(out["state"], "INPUT_IDLE_READY")

        busy = PresenceProbe(
            foreground_is_sims=True,
            cursor_in_client=False,
            last_input_age_ms=100,
        )
        def _moving_cursor():
            x = 10
            while True:
                yield (x, 10)
                x += 1

        with patch("betterinstincts.player_presence.probe_windows", return_value=busy), patch(
            "scripts.diy_skill_force._cursor_pos", side_effect=_moving_cursor()
        ):
            with self.assertRaises(cli.GateError) as ctx:
                cli._wait_for_input_idle(1, idle_ms=15000, timeout_sec=0.3, poll_sec=0.05)
        self.assertIn("CONTINUOUS_INPUT_BLOCKING_ADMIT", str(ctx.exception))

        # Stationary cursor is not idleness during voice dictation/typing.
        with patch("betterinstincts.player_presence.probe_windows", return_value=busy), patch(
            "scripts.diy_skill_force._cursor_pos", return_value=(400, 20)
        ):
            with self.assertRaisesRegex(cli.GateError, "CONTINUOUS_INPUT_BLOCKING_ADMIT"):
                cli._wait_for_input_idle(1, idle_ms=15000, timeout_sec=0.3, poll_sec=0.05)

        # No reward-trait "OK" click is dispatched without classified dialog.
        with patch("scripts.win32_input.send_click") as click, patch(
            "scripts.win32_input.tap_vk"
        ) as tap:
            held = cli._accept_offered_reward_trait({"never_press_cancel": True}, hwnd=12)
        self.assertEqual(held["state"], "NEEDS_DIALOG_IDENTIFICATION")
        self.assertEqual(held["actions"], [])
        click.assert_not_called()
        tap.assert_not_called()

    def test_contract_json_roundtrip(self):
        raw = json.loads(
            (Path(__file__).resolve().parents[1] / "contracts" / "diy-skill-force.v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(raw["version"], 10)
        self.assertEqual(
            raw["completion_ledger"]["schema"],
            "betterinstincts.diy-skill-force.completion/v1",
        )
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
        self.assertEqual(plan["dispatch_order"], "skill_round_robin")
        self.assertEqual(len(plan["member_plans"]), 3)
        self.assertIsNone(plan["member_plans"][0]["select"])
        self.assertEqual(plan["member_plans"][1]["select"]["key"], "SPACE")
        self.assertEqual(plan["member_plans"][2]["select"]["key"], "SPACE")
        self.assertTrue(plan["member_plans"][1]["select"]["close_console_before"])
        self.assertEqual(plan["required_residual_skills"], ["cooking", "fitness", "natural_living"])
        self.assertFalse(plan["async_detach_supported"])
        self.assertFalse(plan["execute_allowed"])
        # Round-robin: skill0×m0, skill0×m1, skill0×m2, skill1×m0, ...
        units = plan["dispatch_units"]
        self.assertEqual(len(units), 3 * len(plan["skills"]))
        self.assertEqual(units[0]["skill_id"], plan["skills"][0]["id"])
        self.assertEqual(units[0]["member_index"], 0)
        self.assertIsNone(units[0]["select_before"])
        self.assertEqual(units[1]["member_index"], 1)
        self.assertEqual(units[1]["select_before"]["key"], "SPACE")
        self.assertEqual(units[2]["member_index"], 2)
        self.assertEqual(units[3]["skill_id"], plan["skills"][1]["id"])
        self.assertEqual(units[3]["member_index"], 0)

    def test_household_skill_round_robin_diy_maker_order(self):
        plan = plan_household_skill_force(members=2, bundle="diy_maker", game_mode="live")
        ids = [u["skill_id"] for u in plan["dispatch_units"]]
        members = [u["member_index"] for u in plan["dispatch_units"]]
        self.assertEqual(
            ids,
            [
                "handiness",
                "handiness",
                "robotics",
                "robotics",
                "fabrication",
                "fabrication",
                "programming",
                "programming",
            ],
        )
        self.assertEqual(members, [0, 1, 0, 1, 0, 1, 0, 1])
        self.assertEqual(plan["cells_needing_work"], 8)

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
        self.assertEqual(snap["household_traverse"]["dispatch_order"], "skill_round_robin")
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

    def test_completion_ledger_skips_maxed_skills_and_members(self):
        import tempfile

        ledger = empty_completion_ledger()
        m0 = completion_member_key("sess-lab", 0)
        m1 = completion_member_key("sess-lab", 1)
        for sid, stat in (
            ("handiness", "Major_Handiness"),
            ("robotics", "Major_Robotics"),
            ("programming", "Major_Programming"),
        ):
            record_skill_dispatched(
                ledger, member_key=m0, skill_id=sid, skill_stat=stat, level=10
            )
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "completion.json"
            save_completion_ledger(ledger, path)
            done = completed_skill_ids_for_member(
                ledger, m0, target_level=10
            )
            self.assertEqual(done, {"handiness", "robotics", "programming"})

            already = plan_skill_force(
                bundle="servo_core",
                omit_skill_ids=sorted(done),
                game_mode="live",
            )
            self.assertEqual(already["state"], "SKILL_FORCE_MEMBER_NO_PENDING_DISPATCH_UNVERIFIED")
            self.assertTrue(already["skip_dispatch"])
            self.assertEqual(already["skills"], [])

            residual_only = plan_skill_force(
                bundle="full_unlock",
                omit_skill_ids=["handiness", "robotics", "programming"],
                game_mode="live",
            )
            ids = {s["id"] for s in residual_only["skills"]}
            self.assertNotIn("handiness", ids)
            self.assertIn("cooking", ids)

            hh = plan_household_skill_force(
                members=3,
                bundle="servo_core",
                session_id="sess-lab",
                completion_ledger=ledger,
                game_mode="live",
            )
            self.assertEqual(hh["members_needing_work"], 2)
            self.assertTrue(hh["member_plans"][0]["skip_dispatch"])
            self.assertFalse(hh["member_plans"][1]["skip_dispatch"])
            self.assertEqual(hh["member_plans"][1]["select"]["key"], "SPACE")
            self.assertEqual(hh["member_plans"][0]["member_key"], m0)
            self.assertEqual(hh["member_plans"][1]["member_key"], m1)
            # Member 0 cells skipped; members 1–2 still need each servo_core skill.
            self.assertEqual(hh["cells_needing_work"], 6)
            skipped0 = [
                u for u in hh["dispatch_units"] if u["member_index"] == 0
            ]
            self.assertTrue(all(u["skip_dispatch"] for u in skipped0))
            self.assertFalse(hh["dispatch_units"][1]["skip_dispatch"])
            self.assertEqual(hh["dispatch_units"][1]["member_index"], 1)
            self.assertEqual(hh["dispatch_units"][1]["skill_id"], "handiness")

            # Fully done household
            for idx in (1, 2):
                mk = completion_member_key("sess-lab", idx)
                for sid, stat in (
                    ("handiness", "Major_Handiness"),
                    ("robotics", "Major_Robotics"),
                    ("programming", "Major_Programming"),
                ):
                    record_skill_dispatched(
                        ledger, member_key=mk, skill_id=sid, skill_stat=stat, level=10
                    )
            hh_done = plan_household_skill_force(
                members=3,
                bundle="servo_core",
                session_id="sess-lab",
                completion_ledger=ledger,
                game_mode="live",
            )
            self.assertEqual(
                hh_done["state"], "HOUSEHOLD_SKILL_FORCE_NO_PENDING_DISPATCH_UNVERIFIED"
            )
            self.assertEqual(hh_done["members_needing_work"], 0)

            redo = plan_household_skill_force(
                members=3,
                bundle="servo_core",
                session_id="sess-lab",
                completion_ledger=ledger,
                redo=True,
                game_mode="live",
            )
            self.assertEqual(redo["members_needing_work"], 3)
            self.assertFalse(any(s["skip_dispatch"] for s in redo["member_plans"]))

    def test_household_executor_does_not_reopen_console_before_space(self):
        """Prior regression: _execute_plan closes console, extra toggle reopened it."""
        from unittest.mock import patch
        from scripts import diy_skill_force as executor

        roster = ["sim:first", "servo:second"]
        plan = plan_household_skill_force(
            members=2, skill_ids=["handiness", "robotics"],
            session_id="test-serial", member_keys=roster,
            completion_ledger=empty_completion_ledger(),
        )
        with patch.object(executor, "_execute_plan", return_value={"state": "DISPATCHED"}) as dispatch, \
             patch.object(executor, "_select_next_household_member", return_value={"admitted": True}) as select, \
             patch.object(executor, "_toggle_cheat_console") as toggle, \
             patch.object(executor, "_park_safe_cursor_rest", return_value={"state": "SAFE_REST"}):
            result = executor._execute_household(
                plan, process_id=123, session_id="test-serial",
                roster_keys=roster, first_portrait_attested=True, redo=True,
            )
        self.assertEqual(result["cells_dispatched"], 4)
        self.assertEqual(dispatch.call_count, 4)
        self.assertEqual(select.call_count, 3)  # only between cells
        toggle.assert_not_called()
        self.assertEqual([c["skill_id"] for c in result["cells"]],
                         ["handiness", "handiness", "robotics", "robotics"])
        self.assertEqual([c["member_index"] for c in result["cells"]], [0, 1, 0, 1])

    def test_household_executor_requires_attested_first_portrait_and_roster(self):
        from scripts import diy_skill_force as executor
        from scripts.diy_skill_force import GateError
        plan = plan_household_skill_force(members=2, skill_ids=["handiness"])
        with self.assertRaisesRegex(GateError, "FIRST_PORTRAIT"):
            executor._execute_household(plan, process_id=123)
        with self.assertRaisesRegex(GateError, "EXACT_OBSERVED"):
            executor._execute_household(plan, process_id=123, first_portrait_attested=True)

    def test_detached_ui_command_is_denied_before_worker_launch(self):
        import contextlib
        import io
        from scripts import diy_skill_force as executor
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = executor.main(["household", "--members", "2", "--execute", "--detach"])
        self.assertEqual(rc, 2)
        self.assertIn("DETACHED_HOUSEHOLD_UI_UNSAFE", out.getvalue())

    def test_single_skipped_member_no_longer_claims_max_or_moves_cursor(self):
        from unittest.mock import patch
        from scripts import diy_skill_force as executor

        plan = plan_skill_force(
            bundle="servo_core",
            omit_skill_ids=["handiness", "robotics", "programming"],
        )
        self.assertEqual(
            plan["state"], "SKILL_FORCE_MEMBER_NO_PENDING_DISPATCH_UNVERIFIED"
        )
        self.assertTrue(plan["skip_dispatch"])
        with patch.object(executor.sys, "platform", "win32"), \
             patch.object(executor, "_park_safe_cursor_rest") as park:
            result = executor._execute_plan(plan, process_id=None)
        park.assert_not_called()
        self.assertTrue(result["skipped"])
        self.assertEqual(result["state"], "SKILL_FORCE_MEMBER_NO_PENDING_DISPATCH_UNVERIFIED")
        self.assertEqual(result["safe_cursor_rest"], "UNCHANGED_NO_INPUT")
        self.assertIn("LOCAL_OBSERVED", result["pass_claim"])

    def test_dispatched_ledger_never_proves_panel_max_and_all_skip_sends_no_input(self):
        """P83: DISPATCHED means typed, not live Skills-panel verification."""
        from unittest.mock import patch
        from scripts import diy_skill_force as executor

        ledger = empty_completion_ledger()
        members = ["sim:original-a", "servo:original-b"]
        for index, label in enumerate(members):
            record_skill_dispatched(
                ledger,
                member_key=completion_member_key("session-p83", index, label),
                skill_id="handiness",
                skill_stat="Major_Handiness",
                level=10,
            )
        plan = plan_household_skill_force(
            members=2, skill_ids=["handiness"],
            session_id="session-p83",
            member_keys=members,
            completion_ledger=ledger,
        )
        self.assertEqual(plan["cells_needing_work"], 0)
        self.assertFalse(plan["max_level_verified_by_ledger"])
        self.assertEqual(plan["state"], "HOUSEHOLD_SKILL_FORCE_NO_PENDING_DISPATCH_UNVERIFIED")
        self.assertEqual(plan["next_gate"], "REVIEW_SKILLS_PANEL_BEFORE_MAX_CLAIM")

        with patch.object(executor, "_execute_plan") as execute, \
             patch.object(executor, "_select_next_household_member") as select, \
             patch.object(executor, "_park_safe_cursor_rest") as park:
            result = executor._execute_household(
                plan, process_id=None, session_id="session-p83",
                roster_keys=members, first_portrait_attested=True,
            )
        execute.assert_not_called()
        select.assert_not_called()
        park.assert_not_called()
        self.assertEqual(result["state"], "HOUSEHOLD_SKILL_FORCE_NO_PENDING_DISPATCH_UNVERIFIED")
        self.assertEqual(result["safe_cursor_rest"], "UNCHANGED_NO_INPUT")
        self.assertEqual(result["cells_dispatched"], 0)
        self.assertIn("LOCAL_OBSERVED", result["pass_claim"])

    def test_ledger_skip_can_be_redone_without_claiming_panel_pass(self):
        ledger = empty_completion_ledger()
        member = completion_member_key("redo", 0, "original")
        record_skill_dispatched(ledger, member_key=member, skill_id="handiness",
                                skill_stat="Major_Handiness", level=10)
        plan = plan_household_skill_force(
            members=1, skill_ids=["handiness"], session_id="redo",
            member_keys=["original"], completion_ledger=ledger, redo=True,
        )
        self.assertEqual(plan["state"], "HOUSEHOLD_SKILL_FORCE_PLAN_READY")
        self.assertEqual(plan["cells_needing_work"], 1)
        self.assertFalse(plan["max_level_verified_by_ledger"])


class ServoEvilEscapeRegressionTests(unittest.TestCase):
    """P62 falsifiers for the 2026-11-09 new-Servo Evil / Escape / laundry incident."""

    # (1) Evil reward -> never ACCEPT / never Enter or OK
    def test_evil_reward_is_never_accepted(self):
        for observed, text in (
            ("trait_Evil", None),
            ("Evil", None),
            ("TRAIT_EVIL", None),
            (None, "Mastery reward: you have become Evil"),
            ("trait evil", "Accept this trait?"),
        ):
            d = decide_reward_dialog(observed, dialog_text=text)
            self.assertEqual(d["decision"], "ESCAPE_CANCEL_DIALOG", msg=(observed, text))
            self.assertFalse(d["accept"])
            self.assertEqual(d["allowed_keys"], ["ESCAPE"])
            self.assertIn("ENTER", d["forbidden_keys"])
            self.assertIn("OK_CLICK", d["forbidden_keys"])
            self.assertEqual(d["classification"]["trait_id"], "trait_Evil")
        # Unclassified dialogs HOLD: no Enter, no OK, no Cancel.
        held = decide_reward_dialog(None)
        self.assertEqual(held["decision"], "HOLD")
        self.assertFalse(held["accept"])
        self.assertEqual(held["allowed_keys"], [])
        # A benign trait is not misclassified by substring (devil-ish words).
        self.assertEqual(classify_reward_trait("trait_Creative")["class"], "OTHER")
        self.assertEqual(classify_reward_trait(None, dialog_text="medieval armor")["class"], "OTHER")

    def test_reward_plan_step_and_cli_guard_refuse_blind_ok(self):
        import scripts.diy_skill_force as cli
        from unittest.mock import patch

        plan = plan_skill_force(bundle="diy_maker", game_mode="live")
        step = next(s for s in plan["steps"] if s["step"] == "ACCEPT_OFFERED_REWARD_TRAIT")
        self.assertTrue(step["refuse_blind_ok"])
        self.assertIn("trait_Evil", step["forbidden_reward_traits"])
        self.assertEqual(step["harmful_trait_action"], "ESCAPE_CANCEL_DIALOG")
        self.assertTrue(step["never_press_cancel"])  # benign traits: still never Cancel
        with patch("scripts.win32_input.send_click") as click, patch(
            "scripts.win32_input.tap_vk"
        ) as tap, patch("scripts.win32_input.send_vk", create=True) as send_vk:
            refused = cli._accept_offered_reward_trait(step, hwnd=1, observed_trait="trait_Evil")
            blind = cli._accept_offered_reward_trait(step, hwnd=1)
        self.assertEqual(refused["state"], "HARMFUL_REWARD_TRAIT_REFUSED")
        self.assertEqual(refused["recommended_action"], "ESCAPE_CANCEL_DIALOG")
        self.assertEqual(refused["actions"], [])
        self.assertEqual(blind["state"], "NEEDS_DIALOG_IDENTIFICATION")
        self.assertEqual(blind["actions"], [])
        click.assert_not_called()
        tap.assert_not_called()
        send_vk.assert_not_called()

    def test_contract_pins_evil_guard_and_load_fails_closed_without_it(self):
        import copy
        import tempfile

        cfg = load_contract()
        reward = cfg["inject_sequence"]["reward_dialog_accept"]
        self.assertTrue(reward["refuse_blind_ok"])
        self.assertEqual(reward["forbidden_reward_traits"], ["trait_Evil"])
        self.assertEqual(reward["harmful_trait_action"], "ESCAPE_CANCEL_DIALOG")
        self.assertIn("blind_ok_harmful_reward_trait", cfg["inject_sequence"]["forbidden"])
        self.assertIn("never_blind_ok_evil_or_harmful_reward_trait", cfg["invariants"])
        for mutate, code in (
            (lambda c: c["inject_sequence"]["reward_dialog_accept"].__setitem__("refuse_blind_ok", False),
             "REWARD_REFUSE_BLIND_OK_REQUIRED"),
            (lambda c: c["inject_sequence"]["reward_dialog_accept"].__setitem__("forbidden_reward_traits", []),
             "REWARD_FORBID_EVIL_REQUIRED"),
            (lambda c: c["trait_repair"].__setitem__("default_remove_trait_ids", ["trait_Evil", "trait_Good"]),
             "TRAIT_REPAIR_DEFAULT_REMOVE_EVIL_ONLY_REQUIRED"),
            (lambda c: c["trait_repair"]["optional_equip_good"].__setitem__("requires_operator_request", False),
             "TRAIT_REPAIR_GOOD_REQUIRES_OPERATOR_REQUEST"),
            (lambda c: c["ui_forbids"]["escape_as_household_traverse_close"].__setitem__("forbidden", False),
             "UI_FORBID_ESCAPE_TRAVERSE_CLOSE_REQUIRED"),
            (lambda c: c["ui_forbids"]["create_or_activate_new_servo"].__setitem__(
                "forbidden_without_operator_consent", False),
             "UI_FORBID_NEW_SERVO_CONSENT_REQUIRED"),
        ):
            weakened = copy.deepcopy(cfg)
            mutate(weakened)
            with tempfile.TemporaryDirectory() as td:
                path = Path(td) / "weak.json"
                path.write_text(json.dumps(weakened), encoding="utf-8")
                with self.assertRaisesRegex(DiySkillForceError, code):
                    load_contract(path)

    # (2) trait_repair plan emits remove Evil (and only that by default)
    def test_trait_repair_default_plan_removes_evil_only(self):
        plan = plan_trait_repair(game_mode="live")
        self.assertEqual(plan["state"], "TRAIT_REPAIR_PLAN_READY")
        self.assertFalse(plan["execute_allowed"])
        self.assertEqual(plan["remove_trait_ids"], ["trait_Evil"])
        self.assertEqual(plan["equip_trait_ids"], [])
        cmds = trait_repair_commands(plan)
        self.assertEqual(cmds[0], "testingcheats enabled true")
        self.assertIn("traits.remove_trait trait_Evil", cmds)
        self.assertFalse(any(c.startswith("traits.equip_trait") for c in cmds))
        names = [s["step"] for s in plan["steps"]]
        self.assertIn("REQUIRE_ACTIVE_SIM_SELECTION", names)
        close = next(s for s in plan["steps"] if s["step"] == "CLOSE_CHEAT_CONSOLE")
        self.assertEqual(close["key"], "CTRL_SHIFT_C_TOGGLE")
        self.assertFalse(
            any(str(s.get("key") or "").upper() in {"ESCAPE", "ESC"} for s in plan["steps"])
        )
        self.assertIn("OBSERVE_TRAIT_REMOVED", names)

    def test_trait_repair_aliases_good_gate_and_unknown_traits(self):
        for alias in ("evil", "Evil", "trait_evil", "TRAIT_EVIL", "trait_Evil"):
            plan = plan_trait_repair(remove_traits=[alias])
            self.assertEqual(plan["remove_trait_ids"], ["trait_Evil"], msg=alias)
        dup = plan_trait_repair(remove_traits=["evil", "trait_Evil"])
        self.assertEqual(dup["remove_trait_ids"], ["trait_Evil"])
        with self.assertRaisesRegex(DiySkillForceError, "GOOD_TRAIT_REQUIRES_OPERATOR_REQUEST"):
            plan_trait_repair(equip_good=True)
        good = plan_trait_repair(equip_good=True, operator_requested_good=True)
        self.assertIn("traits.equip_trait trait_Good", trait_repair_commands(good))
        self.assertIn("traits.remove_trait trait_Evil", trait_repair_commands(good))
        # operator_requested_good alone (no equip_good) never equips
        self.assertEqual(plan_trait_repair(operator_requested_good=True)["equip_trait_ids"], [])
        with self.assertRaisesRegex(DiySkillForceError, "TRAIT_NOT_REPAIRABLE"):
            plan_trait_repair(remove_traits=["trait_Genius"])
        self.assertEqual(plan_trait_repair(player_directed=True)["state"], "YIELD_TO_PLAYER")

    # (3) Escape forbidden as household-traverse console close
    def test_escape_forbidden_as_household_traverse_close(self):
        for ctx in ("household_traverse", "console close", "CLOSE_CHEAT_CONSOLE", "skill_force"):
            v = evaluate_ui_action("ESCAPE", context=ctx)
            self.assertFalse(v["allowed"], msg=ctx)
            self.assertEqual(v["reason"], "ESCAPE_AS_HOUSEHOLD_TRAVERSE_CLOSE_FORBIDDEN")
            self.assertEqual(v["use_instead"], "CTRL_SHIFT_C_TOGGLE")
        spam = evaluate_ui_action("ESCAPE", context="cas", repeat_count=3)
        self.assertFalse(spam["allowed"])
        self.assertIn("TRAVEL_MAP_OR_MENU", spam["reason"])
        self.assertFalse(evaluate_ui_action("ESCAPE", context="mystery")["allowed"])
        # One deliberate Escape-cancel of an observed dialog remains allowed.
        self.assertTrue(evaluate_ui_action("ESCAPE", context="reward_dialog")["allowed"])
        # No generated household plan closes with Escape.
        hh = plan_household_skill_force(members=3, bundle="servo_core", game_mode="live")
        self.assertEqual(hh["household_traverse"]["next_member_key"], "SPACE")
        self.assertTrue(hh["ui_forbids"]["escape_as_household_traverse_close"]["forbidden"])
        for unit in hh["dispatch_units"]:
            for step in (unit["plan"] or {}).get("steps") or []:
                if step.get("step") == "CLOSE_CHEAT_CONSOLE":
                    self.assertEqual(step["key"], "CTRL_SHIFT_C_TOGGLE")
        self.assertIn("escape_as_household_traverse_close", catalog_snapshot()["forbidden"])
        self.assertIn("escape_spam", catalog_snapshot()["forbidden"])

    # (4) new-Servo activate forbidden without explicit consent
    def test_new_servo_activate_forbidden_without_consent(self):
        for act in ("ACTIVATE_NEW_SERVO", "create new servo", "CREATE_NEW_SIM"):
            v = evaluate_ui_action(act)
            self.assertFalse(v["allowed"], msg=act)
            self.assertEqual(v["reason"], "NEW_SERVO_CREATE_ACTIVATE_REQUIRES_OPERATOR_CONSENT")
        cancel = evaluate_ui_action("ACTIVATE_NEW_SERVO", escape_cancel_requested=True)
        self.assertFalse(cancel["allowed"])
        self.assertEqual(cancel["use_instead"], "ESCAPE_CANCEL_CAS")
        # Consent does not override an explicit Escape-cancel request.
        self.assertFalse(
            evaluate_ui_action(
                "ACTIVATE_NEW_SERVO", operator_consent=True, escape_cancel_requested=True
            )["allowed"]
        )
        self.assertTrue(evaluate_ui_action("ACTIVATE_NEW_SERVO", operator_consent=True)["allowed"])
        # CAS gender Continue is the incident path.
        for act in ("CAS_CONTINUE", "CAS_GENDER_CONTINUE"):
            blocked = evaluate_ui_action(act, escape_cancel_requested=True, operator_consent=True)
            self.assertFalse(blocked["allowed"], msg=act)
            self.assertEqual(blocked["reason"], "CAS_CONTINUE_FORBIDDEN_WHEN_ESCAPE_CANCEL_REQUESTED")
            self.assertFalse(evaluate_ui_action(act)["allowed"])
        self.assertFalse(evaluate_ui_action("EQUIP_TRAIT_GOOD")["allowed"])
        self.assertTrue(evaluate_ui_action("EQUIP_TRAIT_GOOD", operator_requested_good=True)["allowed"])
        self.assertFalse(evaluate_ui_action("BLIND_OK_REWARD_TRAIT")["allowed"])

    def test_cli_trait_repair_reward_and_ui_check(self):
        import io
        from contextlib import redirect_stdout

        import scripts.diy_skill_force as cli

        def run(argv):
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = cli.main(argv)
            return code, json.loads(buf.getvalue())

        code, out = run(["trait-repair"])
        self.assertEqual(code, 0)
        self.assertIn("traits.remove_trait trait_Evil", out["commands"])
        self.assertFalse(out["execute"])
        code, out = run(["reward-check", "--trait", "trait_Evil"])
        self.assertEqual(code, 0)
        self.assertEqual(out["decision"]["decision"], "ESCAPE_CANCEL_DIALOG")
        code, out = run(["ui-check", "--action", "ESCAPE", "--context", "household_traverse"])
        self.assertEqual(code, 0)
        self.assertFalse(out["verdict"]["allowed"])
        code, out = run(["trait-repair", "--equip-good"])
        self.assertEqual(code, 2)
        self.assertIn("GOOD_TRAIT_REQUIRES_OPERATOR_REQUEST", out["reason"])


if __name__ == "__main__":
    unittest.main()
