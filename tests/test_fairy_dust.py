"""Fairy Dust policy and installed-callback regressions with supplied frames."""
from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock

from betterinstincts.fairy_dust import ASK, DAY_MINUTES, HOME_USE, PACK, SHAKE, plan_fairy_dust
from betterinstincts.installed_player_runtime import Frame, MANIFEST, start_installed

BUILD = "1.121.361.1020"
FIRST = Frame(BUILD, "game-run", "house-one", "sim:actor", True, True, True, False,
              False, True, 3, 10, 5, "capture:one")
SECOND = replace(FIRST, capture="capture:two")
AFTER = replace(FIRST, capture="capture:three")


def interaction(frame, action, available=True):
    return dict(action=action, capture=frame.capture, opportunity="intent-one", available=available,
                reason="NO_FAIRY_DUST" if not available else None)


def observation(frame, *, available=True):
    return dict(scope=frame.scope(), capture=frame.capture, pack=PACK, dust_count=0,
                goal_count=1, needs_safe=True, game_minute=DAY_MINUTES,
                home=dict(target="object:bungalow", on_actor_lot=True, accessible=True,
                          last_empty_check_game_minute=0, shake=interaction(frame, SHAKE, available)))


class FairyDustPolicyTests(unittest.TestCase):
    def test_time_and_disabled_menu_do_not_imply_dust(self):
        obs = observation(FIRST, available=False)
        self.assertEqual(plan_fairy_dust(FIRST, obs)["recheck_game_minute"], 2 * DAY_MINUTES)
        obs["game_minute"] -= 2
        self.assertEqual(plan_fairy_dust(FIRST, obs)["recheck_game_minute"], DAY_MINUTES)
        obs["home"]["shake"] = None
        obs["game_minute"] = DAY_MINUTES
        self.assertEqual(plan_fairy_dust(FIRST, obs)["state"], "REOBSERVE_HOME_OR_FIND_FAIRY")
        self.assertEqual(plan_fairy_dust(replace(FIRST, playing=False), obs)["state"], "WAIT_FOR_GAME_TIME")

    def test_current_shake_takes_priority_even_before_recheck(self):
        obs = observation(FIRST)
        obs["game_minute"] = 10
        self.assertEqual(plan_fairy_dust(FIRST, obs)["proposal"]["action"], SHAKE)

    def test_only_verified_active_fairy_can_use_home_for_a_need(self):
        obs = observation(FIRST, available=False)
        for action in HOME_USE:
            obs["home"]["use"] = dict(interaction(FIRST, action), benefits_current_need=True)
            for fairy in (None, False, "true"):
                self.assertNotIn("proposal", plan_fairy_dust(FIRST, dict(obs, actor_is_fairy=fairy)))
            self.assertEqual(plan_fairy_dust(FIRST, dict(obs, actor_is_fairy=True))["proposal"]["action"], action)
        obs["home"]["use"]["benefits_current_need"] = False
        self.assertNotIn("proposal", plan_fairy_dust(FIRST, dict(obs, actor_is_fairy=True)))

    def test_direct_ask_requires_observed_distinct_reachable_npc_fairy(self):
        obs = observation(FIRST, available=False)
        npc = dict(target="sim:outsider", npc_fairy=True, on_actor_lot=True, accessible=True,
                   ask=interaction(FIRST, ASK))
        self.assertEqual(plan_fairy_dust(FIRST, dict(obs, npc=npc))["proposal"]["action"], ASK)
        for override in (dict(target=FIRST.actor), dict(npc_fairy=False), dict(on_actor_lot=False),
                         dict(accessible=False), dict(ask=interaction(SECOND, ASK)),
                         dict(ask=interaction(FIRST, "INVITE_NPC_FAIRY")),
                         dict(ask=interaction(FIRST, "BECOME_A_FAIRY"))):
            self.assertNotIn("proposal", plan_fairy_dust(FIRST, dict(obs, npc={**npc, **override})))

    def test_scope_pack_goal_and_survival_are_gates(self):
        obs = observation(FIRST)
        for override, state in ((dict(scope=()), "REOBSERVE_DUST_SCOPE"),
                                (dict(pack="unknown"), "DUST_PACK_UNVERIFIED"),
                                (dict(dust_count=1), "DUST_GOAL_MET"),
                                (dict(dust_count=False), "DUST_INVENTORY_OR_GOAL_UNVERIFIED"),
                                (dict(needs_safe=False), "NEEDS_FIRST")):
            self.assertEqual(plan_fairy_dust(FIRST, {**obs, **override})["state"], state)


class InstalledFairyDustTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "Mods" / "BetterInstincts"
        self.root.mkdir(parents=True)
        (self.root / MANIFEST).write_text(json.dumps({
            "schema": "betterinstincts.native-ecology-ownership/v1", "game_build": BUILD,
            "installed_player_runtime": True, "installed_fairy_dust": True,
        }))
        self.adapter = Mock(game_build=BUILD)
        self.adapter.register.return_value = True
        self.adapter.analyze.return_value = ({}, None, {})
        self.adapter.read_fairy_dust.side_effect = observation
        self.adapter.submit_fairy_dust.return_value = "QUEUED"
        self.adapter.read_fairy_dust_outcome.return_value = None

    def start(self):
        return start_installed(self.adapter, exact_build=BUILD, owned_dir=self.root,
                               learning_opt_in=True, clock=lambda: 10)

    def test_install_requires_all_dust_ports(self):
        self.adapter.submit_fairy_dust = None
        with self.assertRaisesRegex(ValueError, "FAIRY_DUST_PORTS_REQUIRED"):
            self.start()
        self.adapter.register.assert_not_called()

    def test_fairy_lane_yields_to_existing_priorities_and_fresh_player_control(self):
        runtime = self.start()
        self.adapter.frame.side_effect = [replace(FIRST, idle_seconds=4.999), FIRST,
                                          replace(SECOND, input_generation=4), FIRST, SECOND]
        self.assertEqual(runtime.cycle(), "YIELD_TO_PLAYER")
        self.assertEqual(runtime.cycle(), "YIELD_TO_PLAYER")
        self.adapter.submit_fairy_dust.assert_not_called()
        self.adapter.analyze.return_value = ({"ordinary": "ordinary-one"}, None, {})
        self.adapter.submit.return_value = "QUEUED"
        self.assertEqual(runtime.cycle(), "QUEUED")
        self.adapter.submit_fairy_dust.assert_not_called()
        self.adapter.submit.assert_called_once()

    def test_disappearing_affordance_or_changed_target_cannot_submit(self):
        runtime = self.start()
        self.adapter.frame.side_effect = [FIRST, SECOND, FIRST, SECOND]
        changed = observation(SECOND)
        changed["home"]["target"] = "object:different"
        self.adapter.read_fairy_dust.side_effect = [observation(FIRST), observation(SECOND, available=False),
                                                   observation(FIRST), changed]
        self.assertEqual(runtime.cycle(), "REOBSERVE_DUST_SCOPE")
        self.assertEqual(runtime.cycle(), "REOBSERVE_DUST_SCOPE")
        self.adapter.submit_fairy_dust.assert_not_called()

    def test_empty_home_hint_is_bound_to_the_current_capture(self):
        runtime = self.start()
        self.adapter.frame.side_effect = [FIRST, SECOND, AFTER]
        self.adapter.read_fairy_dust.side_effect = [observation(FIRST, available=False),
                                                   TimeoutError("stale producer"), None]
        self.assertEqual(runtime.cycle(), "WAIT_FOR_HOME_RECHECK")
        self.assertEqual(runtime.dust_recheck, dict(state="WAIT_FOR_HOME_RECHECK",
                         target="object:bungalow", recheck_game_minute=2 * DAY_MINUTES,
                         scope=FIRST.scope(), capture=FIRST.capture))
        self.assertEqual(runtime.cycle(), "REOBSERVE_DUST_SCOPE")
        self.assertIsNone(runtime.dust_recheck)
        self.assertEqual(runtime.cycle(), "NO_NATIVE_PROPOSAL")
        self.adapter.submit_fairy_dust.assert_not_called()

    def test_lost_ack_and_unrelated_inventory_gain_require_distinct_matched_readback(self):
        runtime = self.start()
        self.adapter.frame.side_effect = [FIRST, SECOND, FIRST, SECOND, AFTER, AFTER, FIRST]
        self.adapter.submit_fairy_dust.side_effect = OSError("lost acknowledgement")
        self.assertEqual(runtime.cycle(), "NATIVE_DISPATCH_RECONCILIATION")
        proposal = self.adapter.submit_fairy_dust.call_args.args[0]
        outcome = dict(scope=AFTER.scope(), proposal=proposal, completed=True, dust_count=1)
        self.adapter.read_fairy_dust_outcome.side_effect = [
            dict(outcome, capture=FIRST.capture, attributed_dust_gain=1),
            dict(outcome, capture=SECOND.capture, attributed_dust_gain=1),
            dict(outcome, capture=AFTER.capture, attributed_dust_gain=0),
            dict(outcome, capture=AFTER.capture, attributed_dust_gain=1),
        ]
        self.assertEqual(runtime.cycle(), "NATIVE_DISPATCH_RECONCILIATION")
        self.assertEqual(runtime.cycle(), "NATIVE_DISPATCH_RECONCILIATION")
        self.assertEqual(runtime.cycle(), "NATIVE_DISPATCH_RECONCILIATION")
        self.assertEqual(runtime.cycle(), "DUST_GAIN_OBSERVED")
        self.assertEqual(runtime.cycle(), "DUPLICATE_NATIVE_PROPOSAL")
        self.adapter.submit_fairy_dust.assert_called_once()

    def test_finished_sleep_without_dust_rechecks_home_and_does_not_replay(self):
        runtime = self.start()
        self.adapter.frame.side_effect = [FIRST, SECOND, AFTER, FIRST, SECOND]

        def sleep(frame):
            obs = observation(frame, available=False)
            obs["actor_is_fairy"] = True
            obs["home"]["use"] = dict(interaction(frame, HOME_USE[0]), benefits_current_need=True)
            return obs

        self.adapter.read_fairy_dust.side_effect = sleep
        self.assertEqual(runtime.cycle(), "QUEUED")
        proposal = self.adapter.submit_fairy_dust.call_args.args[0]
        self.adapter.read_fairy_dust_outcome.return_value = dict(
            scope=AFTER.scope(), capture=AFTER.capture, proposal=proposal, completed=True,
            dust_count=0, attributed_dust_gain=0)
        self.assertEqual(runtime.cycle(), "FAIRY_HOME_USED_RECHECK")
        self.assertEqual(runtime.cycle(), "WAIT_FOR_HOME_RECHECK")
        self.adapter.submit_fairy_dust.assert_called_once()

    def test_pending_dust_readback_preserves_existing_actions(self):
        runtime = self.start()
        self.adapter.frame.side_effect = [FIRST, SECOND, AFTER, FIRST]
        self.assertEqual(runtime.cycle(), "QUEUED")
        self.adapter.analyze.return_value = ({"ordinary": "ordinary-one"}, None, {})
        self.adapter.submit.return_value = "QUEUED"
        self.assertEqual(runtime.cycle(), "QUEUED")
        self.adapter.submit.assert_called_once()
        self.adapter.submit_fairy_dust.assert_called_once()
        self.assertIn(FIRST.scope(), runtime.dust_attempts)

    def test_spent_shake_does_not_mask_an_observed_npc_request(self):
        runtime = self.start()

        def both(frame):
            obs = observation(frame)
            obs["npc"] = dict(target="sim:outsider", npc_fairy=True, on_actor_lot=True,
                              accessible=True, ask=dict(interaction(frame, ASK), opportunity="ask-one"))
            return obs

        self.adapter.read_fairy_dust.side_effect = both
        self.adapter.frame.side_effect = [FIRST, SECOND, FIRST, SECOND, FIRST]
        self.adapter.submit_fairy_dust.return_value = "NO_EFFECT"
        self.assertEqual(runtime.cycle(), "NO_EFFECT")
        self.assertEqual(runtime.cycle(), "NO_EFFECT")
        self.assertEqual(runtime.cycle(), "DUPLICATE_NATIVE_PROPOSAL")
        self.assertEqual([call.args[0]["action"] for call in self.adapter.submit_fairy_dust.call_args_list],
                         [SHAKE, ASK])

    def test_dust_readback_and_submissions_are_scoped_to_the_actor(self):
        runtime = self.start()
        other = replace(FIRST, capture="capture:other-one", actor="sim:other")
        other_fresh = replace(other, capture="capture:other-two")
        self.adapter.frame.side_effect = [FIRST, SECOND, other, other_fresh, AFTER]
        self.assertEqual(runtime.cycle(), "QUEUED")
        self.assertEqual(runtime.cycle(), "QUEUED")
        self.adapter.read_fairy_dust_outcome.assert_not_called()
        self.assertEqual(set(runtime.dust_attempts), {FIRST.scope(), other.scope()})
        original = self.adapter.submit_fairy_dust.call_args_list[0].args[0]
        wrong_scope = dict(scope=other.scope(), capture=AFTER.capture, proposal=original,
                           completed=True, dust_count=1, attributed_dust_gain=1)
        self.adapter.read_fairy_dust_outcome.return_value = wrong_scope
        self.assertEqual(runtime.cycle(), "NATIVE_DISPATCH_RECONCILIATION")
        self.assertEqual(set(runtime.dust_attempts), {FIRST.scope(), other.scope()})

    def test_verified_terminal_no_effect_releases_other_dust_opportunities(self):
        runtime = self.start()
        self.adapter.frame.side_effect = [FIRST, SECOND, AFTER, FIRST, SECOND]
        self.assertEqual(runtime.cycle(), "QUEUED")
        proposal = self.adapter.submit_fairy_dust.call_args.args[0]
        self.adapter.read_fairy_dust_outcome.return_value = dict(
            scope=AFTER.scope(), capture=AFTER.capture, proposal=proposal, completed=False,
            no_effect_verified=True, dust_count=0, attributed_dust_gain=0)
        self.assertEqual(runtime.cycle(), "DUST_NO_EFFECT_OBSERVED")
        self.assertEqual(runtime.cycle(), "DUPLICATE_NATIVE_PROPOSAL")
        self.adapter.submit_fairy_dust.assert_called_once()
