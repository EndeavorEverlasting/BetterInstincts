"""Native callback fixtures for one selected skill across the current household."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from betterinstincts.household_skill_max import SCHEMA
from betterinstincts.installation_profiles import set_launch_preferences
from betterinstincts.installed_player_runtime import MANIFEST, start_installed
from tests.test_portrait_handoff import ANNA, BEA, CAM, ROSTER, frame
from tests.test_microsystem_handoff import lane, member, option, packet


class HouseholdSkillMaxTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "Mods" / "BetterInstincts"
        self.root.mkdir(parents=True)
        self.settings = self.root / "settings.v1.json"
        watcher = patch("betterinstincts.installation_profiles.settings_path", return_value=self.settings)
        watcher.start()
        self.addCleanup(watcher.stop)
        self.configure()
        self.adapter = Mock(game_build=frame(1).game_build)
        self.adapter.register.return_value = True
        self.adapter.analyze.return_value = ({}, None, {})
        self.adapter.read_portrait_handoff.return_value = None
        self.adapter.read_portrait_outcome.side_effect = self.portrait_outcome
        self.adapter.read_household_skill.side_effect = self.observation
        self.adapter.read_skill_max_outcome.side_effect = self.skill_outcome
        self.adapter.read_microsystem_handoff.side_effect = self.clear_microsystems
        self.levels = {ANNA: (1, 5), BEA: (2, 3), CAM: (5, 5)}
        self.runtime = self.start()

    def configure(self, **options):
        set_launch_preferences({"allow_cheats": True, "household_skill": "photography", **options},
                               self.settings)

    def start(self, **flags):
        (self.root / MANIFEST).write_text(json.dumps({
            "schema": "betterinstincts.native-ecology-ownership/v1",
            "game_build": frame(1).game_build, "installed_player_runtime": True,
            "installed_portrait_handoff": True, "installed_household_skill_max": True,
            "installed_microsystem_handoff": True, **flags,
        }), encoding="utf-8")
        return start_installed(self.adapter, exact_build=frame(1).game_build, owned_dir=self.root,
                               clock=lambda: 10.7, learning_opt_in=True)

    def current(self, number, actor=ANNA, **options):
        return frame(number, actor, **{"playing": False, "idle_seconds": 20,
                                      "save_ref": "lab-save", **options})

    def cycle(self, *frames):
        self.adapter.frame.side_effect = list(frames)
        return self.adapter.register.call_args.kwargs["cycle"]()

    def observation(self, current, skill):
        return {
            "schema": SCHEMA, "game_build": current.game_build, "run": current.run, "save": current.save_ref,
            "save_kind": "LAB_DISPOSABLE", "capture": current.capture, "household": current.household,
            "selected": current.actor, "skill": skill, "roster": ROSTER, "safe_to_leave": True,
            "members": {
                sim: ({"eligible": True, "level": value[0], "cap": value[1]}
                      if value else {"eligible": False})
                for sim, value in self.levels.items()
            },
        }

    def clear_microsystems(self, current):
        return packet(current, {actor: member(current) for actor in ROSTER}, roster=ROSTER)

    def skill_outcome(self, attempt, current):
        return {"status": "APPLIED", "actor": attempt.turn.actor, "skill": attempt.turn.skill,
                "capture": current.capture, "request_capture": attempt.dispatch.capture,
                "save": attempt.turn.save, "roster": ROSTER,
                "cap": attempt.turn.cap, "level": self.levels[attempt.turn.actor][0]}

    def portrait_outcome(self, attempt, current):
        return {"status": "APPLIED", "capture": current.capture, "save": attempt.selection.save,
                "roster": ROSTER, "request_capture": attempt.submit_capture,
                "target": attempt.selection.target}

    def test_planning_maxes_verified_caps_then_switches_and_skips_a_maxed_sim(self):
        self.assertEqual(self.cycle(self.current(1), self.current(2)), "SKILL_MAX_AWAITING_READBACK")
        self.assertEqual(self.cycle(self.current(3)), "SKILL_MAX_AWAITING_READBACK")
        self.adapter.submit_portrait_if_current.assert_not_called()
        self.levels[ANNA] = (5, 5)
        self.assertEqual(self.cycle(self.current(4)), "SKILL_MAX_VERIFIED")
        self.assertEqual(self.cycle(self.current(5), self.current(6)), "PORTRAIT_SWITCH_AWAITING_READBACK")
        attempt, _ = self.adapter.submit_portrait_if_current.call_args.args
        self.assertEqual(attempt.selection.target, BEA)
        self.assertEqual(attempt.skill_profile[::2], ("default", "photography"))
        self.assertEqual(self.cycle(self.current(7, BEA)), "PORTRAIT_SWITCH_CONFIRMED")
        self.assertEqual(self.cycle(self.current(7, BEA)), "PORTRAIT_SELECTION_REOBSERVE")
        self.assertEqual(self.cycle(self.current(8, BEA), self.current(9, BEA)),
                         "SKILL_MAX_AWAITING_READBACK")
        self.levels[BEA] = (3, 3)
        self.assertEqual(self.cycle(self.current(10, BEA)), "SKILL_MAX_VERIFIED")
        self.assertEqual(self.cycle(self.current(11, BEA)), "HOUSEHOLD_SKILL_MAX_VERIFIED")
        self.assertEqual(self.cycle(self.current(12, BEA)), "YIELD_TO_PLAYER")
        self.assertEqual(self.runtime.skill_max_state, "HOUSEHOLD_SKILL_MAX_VERIFIED")
        self.assertEqual([(args[0].turn.actor, args[0].turn.cap, args[1].playing)
                          for args, _ in self.adapter.submit_skill_max_if_current.call_args_list],
                         [(ANNA, 5, False), (BEA, 3, False)])
        self.adapter.submit_portrait_if_current.assert_called_once()
        self.adapter.submit.assert_not_called()

    def test_cheat_setting_and_zero_selection_never_emit_a_skill_or_portrait_effect(self):
        for options in ({"allow_cheats": False}, {"household_skill": "none"}):
            self.configure(**options)
            self.cycle(self.current(1))
        self.adapter.read_household_skill.assert_not_called()
        self.adapter.submit_portrait_if_current.assert_not_called()
        self.adapter.submit_skill_max_if_current.assert_not_called()

    def test_paused_mode_holds_regular_queues_and_respects_fresh_takeover(self):
        self.adapter.analyze.return_value = ({"needs": "eat-first"}, None, None)
        self.assertEqual(self.cycle(self.current(1)), "YIELD_TO_PLAYER")
        self.adapter.analyze.return_value = ({}, None, {})
        for options in ({"player_active": True}, {"player_queue": True}, {"playing": True},
                        {"input_generation": 11}, {"idle_seconds": 14.9}):
            self.cycle(self.current(2), self.current(3, **options))
        self.adapter.submit.assert_not_called()
        self.adapter.submit_skill_max_if_current.assert_not_called()

    def test_profile_change_aborts_second_probe_in_play_or_planning(self):
        for playing in (True, False):
            with self.subTest(playing=playing):
                self.configure()
                first = self.current(1, playing=playing)
                fresh = self.current(2, playing=playing)

                def frame_and_disable():
                    yield first
                    self.configure(allow_cheats=False)
                    yield fresh

                self.adapter.frame.side_effect = frame_and_disable()
                self.assertEqual(self.runtime.cycle(), "SKILL_MAX_REOBSERVE")
        self.adapter.submit_skill_max_if_current.assert_not_called()
        self.adapter.submit_portrait_if_current.assert_not_called()

    def test_unknown_or_unavailable_members_never_become_false_completion(self):
        self.levels = {ANNA: (3, 3), BEA: (None, 3), CAM: None}
        self.cycle(self.current(1))
        self.assertEqual(self.runtime.skill_max_state, "PORTRAIT_EARLIER_SKILL_PENDING")
        self.levels[BEA] = (3, 3)
        self.cycle(self.current(2))
        self.assertEqual(self.runtime.skill_max_state, "HOUSEHOLD_SKILL_MAX_VERIFIED")
        self.adapter.submit_skill_max_if_current.assert_not_called()

    def test_non_disposable_save_or_unqualified_roster_cannot_rotate_or_max(self):
        for overrides in ({"save_kind": "LAB_CONTINUATION"}, {"save": "another-save"},
                          {"roster": (ANNA, BEA)}, {"schema": None}):
            self.adapter.read_household_skill.side_effect = (
                lambda current, skill: {**self.observation(current, skill), **overrides}
            )
            self.cycle(self.current(1))
            self.assertEqual(self.runtime.skill_max_state, "SKILL_MAX_EVIDENCE_UNQUALIFIED")
        self.adapter.submit_skill_max_if_current.assert_not_called()
        self.adapter.submit_portrait_if_current.assert_not_called()

    def test_uncertain_submit_never_repeats_and_wrong_scope_cannot_clear_it(self):
        self.adapter.submit_skill_max_if_current.side_effect = RuntimeError("lost native acknowledgement")
        self.assertEqual(self.cycle(self.current(1, playing=True), self.current(2, playing=True)),
                         "SKILL_MAX_AWAITING_READBACK")
        self.levels[ANNA] = (5, 5)
        self.assertEqual(self.cycle(self.current(2)), "SKILL_MAX_AWAITING_READBACK")
        self.assertEqual(self.cycle(self.current(3, save_ref="another-save")), "SKILL_MAX_AWAITING_READBACK")
        self.adapter.read_skill_max_outcome.assert_not_called()
        self.adapter.read_skill_max_outcome.side_effect = (
            lambda attempt, current: {**self.skill_outcome(attempt, current), "actor": BEA})
        self.assertEqual(self.cycle(self.current(4, BEA)), "SKILL_MAX_AWAITING_READBACK")
        self.configure(allow_cheats=False)
        self.adapter.read_skill_max_outcome.side_effect = self.skill_outcome
        self.assertEqual(self.cycle(self.current(5, BEA, player_active=True)), "SKILL_MAX_VERIFIED")
        self.cycle(self.current(6, BEA))
        self.adapter.submit_skill_max_if_current.assert_called_once()
        self.adapter.submit_portrait_if_current.assert_not_called()

    def test_open_modal_cannot_submit_a_second_effect_while_skill_still_unresolved(self):
        self.runtime.trait_response = Mock()
        self.cycle(self.current(1), self.current(2))
        self.assertEqual(self.cycle(self.current(3, modal_open=True, modal_ref="offer-one")),
                         "SKILL_MAX_AWAITING_READBACK")
        self.runtime.trait_response.respond.assert_not_called()
        self.adapter.submit_skill_max_if_current.assert_called_once()

    def test_verified_no_effect_allows_retry_only_with_a_new_profile_revision(self):
        self.cycle(self.current(1), self.current(2))
        self.adapter.read_skill_max_outcome.side_effect = (
            lambda attempt, current: {**self.skill_outcome(attempt, current), "status": "NO_EFFECT"}
        )
        self.assertEqual(self.cycle(self.current(3)), "SKILL_MAX_NO_EFFECT")
        self.assertEqual(self.cycle(self.current(4), self.current(5)), "DUPLICATE_SKILL_MAX_REQUEST")
        self.configure(allow_cheats=False)
        self.cycle(self.current(6))
        self.configure(allow_cheats=True)
        self.assertEqual(self.cycle(self.current(7), self.current(8)), "SKILL_MAX_AWAITING_READBACK")
        self.assertEqual(self.adapter.submit_skill_max_if_current.call_count, 2)

    def test_optional_binding_requires_shared_portrait_support(self):
        with self.assertRaisesRegex(ValueError, "NATIVE_MICROSYSTEM_HANDOFF_PORTS_REQUIRED"):
            self.start(installed_portrait_handoff=False)
        with self.assertRaisesRegex(ValueError, "NATIVE_HOUSEHOLD_SKILL_MAX_PORTS_REQUIRED"):
            self.start(installed_microsystem_handoff=False)
        self.adapter.submit_skill_max_if_current = None
        with self.assertRaisesRegex(ValueError, "NATIVE_HOUSEHOLD_SKILL_MAX_PORTS_REQUIRED"):
            self.start()

    def test_planning_skill_waits_for_household_microsystem_clearance(self):
        self.runtime = self.start(installed_microsystem_handoff=True)

        def arbitration(current, urgent):
            members = {actor: member(current) for actor in ROSTER}
            if urgent:
                members[BEA] = member(current, NEEDS=lane(current, option("food")))
            return packet(current, members, roster=ROSTER)

        self.adapter.read_microsystem_handoff.side_effect = lambda current: arbitration(current, True)
        self.assertEqual(self.cycle(self.current(1)), "YIELD_TO_PLAYER")
        self.adapter.read_household_skill.assert_not_called()

        self.adapter.read_microsystem_handoff.side_effect = lambda current: arbitration(current, False)
        self.assertEqual(self.cycle(self.current(2), self.current(3)), "SKILL_MAX_AWAITING_READBACK")
        self.adapter.submit_skill_max_if_current.assert_called_once()
        self.adapter.submit_microsystem_if_current.assert_not_called()

    def test_missing_remote_priority_cannot_be_treated_as_an_absent_sim(self):
        self.adapter.read_microsystem_handoff.side_effect = lambda current: packet(
            current, {ANNA: member(current)}, roster=ROSTER)
        self.assertEqual(self.cycle(self.current(1)), "YIELD_TO_PLAYER")
        self.adapter.submit_skill_max_if_current.assert_not_called()
        self.adapter.read_household_skill.assert_not_called()

        self.levels[BEA] = None
        self.adapter.read_microsystem_handoff.side_effect = lambda current: packet(
            current, {ANNA: member(current), BEA: {**member(current), "available": False},
                      CAM: member(current)}, roster=ROSTER)
        self.assertEqual(self.cycle(self.current(2), self.current(3)), "SKILL_MAX_AWAITING_READBACK")

    def test_planning_activity_preview_takes_precedence_over_skill_max(self):
        from tests.test_installed_player_runtime import InstalledRuntimeTests

        self.runtime = self.start(installed_activity_chain=True)
        self.adapter.read_activity_chain.side_effect = lambda f: InstalledRuntimeTests.activity_packet(self, f)
        self.assertEqual(self.cycle(self.current(1)), "PLAN_STAGED")
        self.assertIsNotNone(self.runtime.activity_plan)
        self.adapter.read_household_skill.assert_not_called()
        self.adapter.submit_skill_max_if_current.assert_not_called()
        self.adapter.submit.assert_not_called()

    def test_activity_chain_in_play_rechecks_household_priority_before_submitting(self):
        from tests.test_installed_player_runtime import InstalledRuntimeTests

        self.runtime = self.start(installed_activity_chain=True)
        self.adapter.read_activity_chain.side_effect = lambda f: InstalledRuntimeTests.activity_packet(self, f)

        def arbitration(current):
            members = {actor: member(current) for actor in ROSTER}
            if current.capture == self.current(2).capture:
                members[BEA] = member(current, NEEDS=lane(current, option("food")))
            return packet(current, members, roster=ROSTER)

        self.adapter.read_microsystem_handoff.side_effect = arbitration
        self.assertEqual(self.cycle(self.current(1, playing=True), self.current(2, playing=True)),
                         "ACTIVITY_REOBSERVE_DOMAIN_PRIORITY")
        self.adapter.submit.assert_not_called()
        self.adapter.submit_skill_max_if_current.assert_not_called()

        self.adapter.submit.return_value = "QUEUED"
        fresh = self.current(4, playing=True)
        self.assertEqual(self.cycle(self.current(3, playing=True), fresh), "QUEUED")
        self.adapter.submit.assert_called_once_with("buy-material", fresh)
