import unittest
from betterinstincts.priority import SimSnapshot, suggest

class PolicyTests(unittest.TestCase):
    def test_hunger_over_career(self):
        snap = SimSnapshot({"hunger": .2, "energy": .9}, ("eat", "career_prep"), aspiration="career")
        self.assertEqual(suggest(snap).action, "eat")
    def test_most_urgent_eligible_need(self):
        snap = SimSnapshot({"hunger": .24, "bladder": .12}, ("eat", "use_toilet"))
        self.assertEqual(suggest(snap).action, "use_toilet")
    def test_unavailable_actions_never_invented(self):
        snap = SimSnapshot({"hunger": 0}, ("enjoy_leisure",))
        self.assertEqual(suggest(snap).action, "enjoy_leisure")
    def test_player_direction_prevents_override(self):
        snap = SimSnapshot({"hunger": 0}, ("eat",), player_directed=True)
        self.assertIsNone(suggest(snap))
    def test_autonomy_off(self):
        snap = SimSnapshot({"hunger": 0}, ("eat",), autonomy_enabled=False)
        self.assertIsNone(suggest(snap))
    def test_income_when_safe_and_selected(self):
        snap = SimSnapshot({"hunger": .9}, ("earn_income", "enjoy_leisure"), aspiration="income")
        self.assertEqual(suggest(snap).action, "earn_income")
    def test_balanced_keeps_leisure(self):
        snap = SimSnapshot({"hunger": .9}, ("earn_income", "enjoy_leisure"))
        self.assertEqual(suggest(snap).action, "enjoy_leisure")
    def test_no_available_action(self):
        self.assertIsNone(suggest(SimSnapshot({"hunger": 0}, ())))
    def test_invalid_need_range(self):
        with self.assertRaises(ValueError):
            suggest(SimSnapshot({"hunger": 1.5}, ("eat",)))
    def test_invalid_aspiration(self):
        with self.assertRaises(ValueError):
            suggest(SimSnapshot({}, (), aspiration="maximize_everything"))

if __name__ == "__main__":
    unittest.main()
