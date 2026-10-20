import unittest
from pathlib import Path
from scripts.horizon_status import status

class HorizonStatusTests(unittest.TestCase):
    def test_hunger_stays_active_without_game_certification(self):
        r=status(Path(__file__).resolve().parents[1])
        self.assertEqual(r["current_gate"],"BI-002")
        self.assertEqual(r["certified_module_patch_combinations"],0)
        self.assertEqual(r["closure"],"UNPROVEN_GAME_HOST")
        self.assertEqual(len(r["after_hunger"]),5)
        self.assertEqual((r["balance_gate"],r["income_gate"],r["skills_gate"]),
                         ("BI-003F","BI-004","BI-005"))
if __name__=="__main__":
    unittest.main()
