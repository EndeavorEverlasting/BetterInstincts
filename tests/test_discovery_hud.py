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


if __name__=="__main__": unittest.main()
