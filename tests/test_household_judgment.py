"""Offline regression guards for household task scope and online actions."""
import unittest

from betterinstincts.household_judgment import (
    HouseholdJudgmentError, judge_action, load_contract,
    require_fixed_roster, require_skill_action,
)
from betterinstincts.menu_blockers import MenuBlockerError, assert_safe_action


class HouseholdJudgmentTests(unittest.TestCase):
    def setUp(self):
        self.roster = ["portrait:sim-1", "portrait:servo-2", "portrait:sim-3"]

    def test_contract_is_offline_and_serial(self):
        cfg = load_contract()
        self.assertFalse(cfg["execution"]["detached_worker"])
        self.assertEqual(cfg["roster"]["changes"], "STOP_AND_RECONCILE")

    def test_fixed_roster_accepts_exact_n_without_synthetic_cap(self):
        self.assertEqual(require_fixed_roster(self.roster, list(self.roster)), tuple(self.roster))
        for n in (1, 8, 10, 24):
            identities = [f"sim:{i}" for i in range(n)]
            self.assertEqual(require_fixed_roster(identities, identities), tuple(identities))

    def test_expansion_reorder_and_missing_identifiers_deny(self):
        with self.assertRaisesRegex(HouseholdJudgmentError, "ROSTER_CHANGED"):
            require_fixed_roster(self.roster, [*self.roster, "servo:new"])
        with self.assertRaisesRegex(HouseholdJudgmentError, "ROSTER_CHANGED"):
            require_fixed_roster(self.roster, list(reversed(self.roster)))
        with self.assertRaisesRegex(HouseholdJudgmentError, "IDS_INVALID"):
            require_fixed_roster(["a", "a"], ["a", "a"])
        with self.assertRaisesRegex(HouseholdJudgmentError, "REQUIRED"):
            require_fixed_roster(self.roster, None)

    def test_skill_actions_do_not_grant_execution(self):
        for action in ("SET_SKILL_LEVEL", "SELECT_NEXT_HOUSEHOLD_SIM", "OPEN_SKILLS_PANEL"):
            result = judge_action(action, original_roster=self.roster, observed_roster=self.roster)
            self.assertEqual(result["state"], "ACTION_IN_SCOPE")
            self.assertFalse(result["execute_allowed"])

    def test_creation_servo_and_unrelated_game_actions_deny(self):
        for action in ("ADD_SIM", "CREATE_SIM", "ADD_SERVO", "CREATE_SERVO", "MOVE_IN_SIM",
                       "BUY_OBJECT", "OPEN_CAS", "TRAVEL_TO_OTHER_WORLD", "DELETE_SIM"):
            result = judge_action(action, original_roster=self.roster, observed_roster=self.roster)
            self.assertEqual(result["state"], "BLOCKED", action)

    def test_online_routes_deny_even_outside_skill_task(self):
        for action in ("CONNECT", "CONNECT_ONLINE", "EA_CONNECT", "OPEN_GALLERY",
                       "OPEN_ONLINE_GALLERY", "FORCE_SIMS_ONLINE", "OPEN_STORE"):
            for task in ("HOUSEHOLD_SKILL_ROUND_ROBIN", "OTHER_GOAL"):
                result = judge_action(action, task=task, original_roster=self.roster,
                                      observed_roster=self.roster)
                self.assertEqual(result["reason"], "OFFLINE_ONLY_ONLINE_ACTION_FORBIDDEN")

    def test_offline_choice_requires_observed_connection_modal(self):
        blocked = judge_action("STAY_OFFLINE", original_roster=self.roster, observed_roster=self.roster)
        self.assertEqual(blocked["state"], "BLOCKED")
        allowed = judge_action("STAY_OFFLINE", original_roster=self.roster, observed_roster=self.roster,
                               connection_dialog_observed=True)
        self.assertEqual(allowed["state"], "ACTION_IN_SCOPE")
        self.assertFalse(allowed["execute_allowed"])

    def test_detached_skill_action_is_blocked(self):
        with self.assertRaisesRegex(HouseholdJudgmentError, "DETACHED"):
            require_skill_action("SET_SKILL_LEVEL", original_roster=self.roster,
                                 observed_roster=self.roster, detached=True)

    def test_menu_actions_block_connect(self):
        for action in ("CONNECT_ONLINE", "EA_CONNECT", "OPEN_GALLERY"):
            with self.assertRaises(MenuBlockerError):
                assert_safe_action(action)


if __name__ == "__main__":
    unittest.main()
