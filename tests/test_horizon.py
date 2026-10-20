import json
import unittest
from dataclasses import replace
from pathlib import Path
from betterinstincts.horizon import Context,PolicyError,SIX_NEEDS,choose,validate_rules
from betterinstincts.priority import SimSnapshot,suggest

CONFIG=json.loads((Path(__file__).resolve().parents[1]/"contracts/needs.v1.json").read_text())
SAFE={n:.9 for n in SIX_NEEDS}
ACTIONS=("eat","use_toilet","sleep","wash","have_fun","socialize","earn_income","practice_skill","enjoy_leisure")

class HorizonTests(unittest.TestCase):
    def test_six_distinct_needs(self):
        self.assertEqual(len(validate_rules(CONFIG)),6)
    def test_each_need_urgent_and_preemptive(self):
        for rule in CONFIG["needs"]:
            for value in (.1,.45):
                with self.subTest(need=rule["id"],value=value):
                    result=choose(Context({**SAFE,rule["id"]:value},ACTIONS,
                                          needs_game_certified=True,income_due=True),CONFIG)
                    self.assertEqual(result.action,rule["action"])
                    self.assertEqual(result.domain,"needs")
    def test_old_baseline_did_not_support_fun_or_social(self):
        self.assertIsNone(suggest(SimSnapshot({"hunger":.9},("have_fun","socialize"))))
        for need,action in (("fun","have_fun"),("social","socialize")):
            self.assertEqual(choose(Context({**SAFE,need:.1},ACTIONS),CONFIG).action,action)
    def test_player_and_queued_command_are_sacrosanct(self):
        c=Context({**SAFE,"hunger":.1},ACTIONS)
        for field in ("player_directed","already_busy"):
            self.assertIsNone(choose(replace(c,**{field:True}),CONFIG))
        self.assertIsNone(choose(replace(c,autonomy_enabled=False),CONFIG))
    def test_unknown_life_or_motive_abstains(self):
        self.assertIsNone(choose(Context(SAFE,ACTIONS,supported_life_stage=False),CONFIG))
        self.assertIsNone(choose(Context({"hunger":.2},ACTIONS),CONFIG))
    def test_most_urgent_then_stable_ties(self):
        self.assertEqual(choose(Context({**SAFE,"hunger":.2,"bladder":.1},ACTIONS),CONFIG).action,"use_toilet")
        self.assertEqual(choose(Context({**SAFE,"hunger":.2,"bladder":.2},ACTIONS),CONFIG).action,"eat")
    def test_missing_remedy_does_not_trigger_income(self):
        c=Context({**SAFE,"hunger":.1},("earn_income",),income_due=True,needs_game_certified=True)
        self.assertIsNone(choose(c,CONFIG))
    def test_income_then_skill_evidence(self):
        c=Context(SAFE,ACTIONS,income_due=True,skill_goal_active=True)
        self.assertEqual(choose(c,CONFIG).domain,"leisure")
        c=replace(c,needs_game_certified=True)
        self.assertEqual(choose(c,CONFIG).domain,"income")
        c=replace(c,income_due=False)
        self.assertEqual(choose(c,CONFIG).domain,"leisure")
        c=replace(c,income_game_observed=True)
        self.assertEqual(choose(c,CONFIG).domain,"skills")
    def test_cooldown(self):
        c=Context(SAFE,ACTIONS,needs_game_certified=True,income_due=True,cooldown_actions=("earn_income",))
        self.assertNotEqual(choose(c,CONFIG).domain,"income")
    def test_invalid_values_rejected(self):
        for value in (float("nan"),float("inf"),-1,1.2,True):
            with self.assertRaises(PolicyError):
                choose(Context({**SAFE,"hunger":value},ACTIONS),CONFIG)
    def test_incomplete_config_rejected(self):
        for changed in ({"needs":CONFIG["needs"][:-1]},{"preemptive_threshold":.1},
                        {"urgency_threshold":True}):
            with self.assertRaises(PolicyError):
                validate_rules({**CONFIG,**changed})

if __name__=="__main__":
    unittest.main()
