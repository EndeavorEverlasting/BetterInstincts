import time
import unittest
from betterinstincts.discovery_hud import (
    DiscoveryHudError, evaluate_discovery_hud,
)

NOW=time.time()
CAP="capture:quests"
NEEDS=dict(hunger=.3,bladder=.8,energy=.9,hygiene=.9,fun=.8,social=.8)


def observation(label="Navigating Needs",**kw):
    row=dict(
        schema="betterinstincts.discovery-hud/v1",
        sim_ref="sim:tim",selected_sim_ref="sim:tim",selection_verified=True,
        selection_proof_ref="proof:portrait",source="DISCOVERY_QUEST",
        mode="LIVE",panel_verified=True,scene_verified=True,
        panel_proof_ref="proof:quest",scene_proof_ref="proof:live",
        capture_ref=CAP,observed_at_unix=NOW,
        quest_label=label,incomplete_goals=["Cook a Meal or Have a Quick Meal"],
        queue_labels=[],phone_actions=[])
    row.update(kw)
    return row


class DiscoveryHudTests(unittest.TestCase):
    def run_hud(self,o,needs=NEEDS):
        return evaluate_discovery_hud(o,capture_ref=CAP,needs=needs,now=NOW)

    def test_navigating_needs_reuses_existing_goal_catalog(self):
        r=self.run_hud(observation())
        self.assertEqual(r["state"],"ROUTE_EXISTING_NAVIGATING_NEEDS")
        self.assertEqual(r["domain_plan"]["next_need"],"hunger")
        self.assertFalse(r["execute_allowed"])

    def test_scoring_routes_existing_scenario_not_generic_clicker(self):
        r=self.run_hud(observation("Scoring Simoleons",
                          incomplete_goals=["Earn §250","Craft an Object"]))
        self.assertEqual(r["state"],"ROUTE_EXISTING_SCORING_SIMOLEONS")
        self.assertIsNotNone(r["domain_plan"])
        self.assertFalse(r["execute_allowed"])

    def test_phone_goal_requires_current_visible_matching_action(self):
        r=self.run_hud(observation("You and Your Phone",
                         incomplete_goals=["Use phone"],
                         phone_actions=[dict(goal_label="Use phone",action_id="OPEN_PHONE",
                             available=True,sim_ref="sim:tim",capture_ref=CAP,
                             menu_observation_ref="proof:phone-menu")]))
        self.assertEqual(r["state"],"PHONE_GOAL_AFFORDANCE_CANDIDATE")
        self.assertEqual(r["next_action"]["action_id"],"OPEN_PHONE")
        for a in [[],[dict(goal_label="Use phone",action_id="OPEN_PHONE",
                         available=False,sim_ref="sim:tim",capture_ref=CAP,
                         menu_observation_ref="proof:phone-menu")],
                  [dict(goal_label="Use phone",action_id="OPEN_PHONE",
                         available=True,sim_ref="sim:alex",capture_ref=CAP,
                         menu_observation_ref="proof:phone-menu")]]:
            with self.subTest(a=a):
                self.assertIsNone(self.run_hud(observation("You and Your Phone",
                    incomplete_goals=["Use phone"],phone_actions=a))["next_action"])

    def test_unknown_unverified_nonlive_wrong_sim_preserves_control(self):
        for obs in [
            observation("Unrecognized Quest"),
            observation(panel_verified=False),
            observation(selected_sim_ref="sim:alex"),
            observation(mode="BUILD"),
            observation(source="SCENARIO"),
            observation(observed_at_unix=NOW-181),
            observation(player_active=True),
        ]:
            with self.subTest(obs=obs):
                r=self.run_hud(obs)
                self.assertFalse(r["execute_allowed"])
                self.assertIsNone(r["next_action"])
        self.assertEqual(self.run_hud(
            observation("You and Your Phone",mode="BUILD"))["state"],
            "REOBSERVE_TOP_LEFT_PANEL")

    def test_known_future_quests_are_separate_not_guessed(self):
        self.assertEqual(self.run_hud(
            observation("Skillful Sims"))["state"],
            "KNOWN_DISCOVERY_QUEST_NEEDS_OWN_MICROSYSTEM")

    def test_missing_needs_and_malformed_input(self):
        self.assertEqual(self.run_hud(observation(),needs=None)["state"],
                         "INSPECT_NEEDS_FOR_QUEST")
        with self.assertRaises(DiscoveryHudError):
            self.run_hud(observation(incomplete_goals=[{}]))


class DiscoveryHostCompositionTests(unittest.TestCase):
    def setUp(self):
        self.needs = dict(hunger=.9,bladder=.9,energy=.9,hygiene=.9,fun=.9,social=.9)

    def host(self, obs, **kw):
        from betterinstincts.host_stack import evaluate_turn
        return evaluate_turn(
            self.needs, discovery_hud=obs,
            capture_ref=CAP, queue=[], location_kind="home",
            viewport={"state": "VIEWPORT_OK"}, **kw,
        )

    def test_verified_quest_routes_into_existing_host_owners(self):
        needs = self.host(observation())
        self.assertEqual(needs["discovery_hud"]["state"], "ROUTE_EXISTING_NAVIGATING_NEEDS")
        self.assertIsNotNone(needs["navigating_needs"])
        score = self.host(observation(
            "Scoring Simoleons", incomplete_goals=["Craft an Object"]))
        self.assertEqual(score["discovery_hud"]["state"], "ROUTE_EXISTING_SCORING_SIMOLEONS")
        self.assertIsNotNone(score["scenario"])

    def test_phone_remains_review_only_even_with_attested_menu(self):
        phone=self.host(observation("You and Your Phone",
            incomplete_goals=["Use phone"],
            phone_actions=[dict(goal_label="Use phone",action_id="OPEN_PHONE",
                available=True,sim_ref="sim:tim",capture_ref=CAP,
                menu_observation_ref="proof:phone")]))
        self.assertEqual(phone["next_gate"],"DISCOVERY_PHONE_REVIEW_ONLY")
        self.assertFalse(phone["fallback"]["execute_allowed"])
        self.assertEqual(phone["fallback"]["next_action"]["action_id"],"OPEN_PHONE")

    def test_actor_player_mode_and_legacy_conflict(self):
        from betterinstincts.host_stack import HostStackError
        for opts in [dict(player_directed=True),dict(build_or_buy_mode=True)]:
            r=self.host(observation(),**opts)
            self.assertNotEqual(r["discovery_hud"]["state"],"ROUTE_EXISTING_NAVIGATING_NEEDS")
        with self.assertRaisesRegex(HostStackError,"DISCOVERY_LEGACY_GOAL_CONFLICT"):
            self.host(observation(),scenario_active=True,scenario_goals_incomplete=["Craft an Object"])

    def test_existing_listener_transports_same_typed_quest_once(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from betterinstincts.host_listener import activate, tick, HostListenerError
        from betterinstincts.player_presence import PresenceProbe
        with tempfile.TemporaryDirectory() as temp, patch(
            "betterinstincts.host_listener.ROOT",Path(temp).resolve()
        ), patch("betterinstincts.host_listener.OUTPUT",Path(temp).resolve()/"dist/host-listener"):
            activate("quest-test")
            obs=dict(schema="betterinstincts.host-listener.observation/v1",
                     needs=self.needs,queue=[],location_kind="home",
                     capture_ref=CAP,viewport={"state":"VIEWPORT_OK"},
                     discovery_hud=observation())
            rec=tick("quest-test",obs,presence_probe=PresenceProbe(
                False,False,last_input_age_ms=20000,probe_ok=True))
            self.assertEqual(rec["host_stack"]["discovery_hud"]["state"],
                             "ROUTE_EXISTING_NAVIGATING_NEEDS")
            self.assertFalse(rec["execute_clicks"])
            with self.assertRaisesRegex(HostListenerError,"OBSERVATION_DISCOVERY_HUD_INVALID"):
                tick("quest-test",{**obs,"discovery_hud":[]})


if __name__=="__main__": unittest.main()
