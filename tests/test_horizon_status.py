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
    def test_escape_u_p04_workload_discoverable_without_stage_promotion(self):
        r=status(Path(__file__).resolve().parents[1])
        esc=r["supporting_workloads"]["escape_u_input_forensics"]
        self.assertEqual(r["current_gate"],"BI-002")
        self.assertEqual(r["next_supporting_priority"],"BI-WORLD-TRAVERSAL-P08-SENSOR")
        self.assertEqual(esc["id"],"BI-ESC-U-FORENSICS-P04")
        self.assertEqual(esc["source_pr"],183)
        self.assertEqual(esc["local_escape_menu"],"NOT_OBSERVED")
        self.assertEqual(esc["local_u_clubs"],"NOT_OBSERVED")
        self.assertEqual(esc["cursor_session_attribution"],"UNATTRIBUTED")
        self.assertEqual(esc["live_proof"],"UNPROVEN_OPERATOR_HOST")
        self.assertEqual(esc["lane_order"],[
            "ESC_U_OPERATOR_KEY_MATRIX","ESC_U_CURSOR_PROVENANCE","ESC_U_RECONCILE"])
        self.assertEqual(r["closure"],"UNPROVEN_GAME_HOST")

if __name__=="__main__":
    unittest.main()
