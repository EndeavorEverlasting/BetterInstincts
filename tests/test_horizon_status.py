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
        self.assertEqual((r["balance_gate"],r["income_gate"],r["skills_gate"],r["tooling_lane"]),
                         ("BI-003F","BI-004","BI-005","BI-MODLAB"))
    def test_next_supporting_world_sensor_is_discoverable_without_hunger_promotion(self):
        r=status(Path(__file__).resolve().parents[1])
        self.assertEqual(r["current_gate"],"BI-002")
        self.assertEqual(r["next_supporting_priority"],"BI-WORLD-TRAVERSAL-P08-SENSOR")
        self.assertEqual(r["dispatch_validation"],"PASS")
        self.assertEqual(r["supporting_launch_order"],["WORLD_SENSOR","WORLD_OUTCOME","WORLD_INTEGRATE"])
        self.assertEqual(r["supporting_first_command"],"python -m scripts.check_horizon")
        self.assertEqual(r["supporting_local_host_state"],"BLOCKED_LOCAL_GAME_ACCESS_UNTIL_AUTHORIZED")
        self.assertEqual(r["closure"],"UNPROVEN_GAME_HOST")
if __name__=="__main__":
    unittest.main()
