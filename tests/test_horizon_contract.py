import json
import unittest
from pathlib import Path
from scripts.check_horizon import validate,validate_dispatch,HorizonError

ROOT=Path(__file__).resolve().parents[1]
ORIGINAL=json.loads((ROOT/"plans/horizon.v1.json").read_text())
DISPATCH=json.loads((ROOT/"plans/active/BI-HORIZON.dispatch.v1.json").read_text())

def clone():
    return json.loads(json.dumps(ORIGINAL))

class HorizonContractTests(unittest.TestCase):
    def test_current_horizon_valid(self):
        self.assertEqual(validate(clone())["state"],"PASS")
    def test_p04_supporting_priority_routed_to_native_dispatch(self):
        horizon=clone()
        self.assertEqual(horizon["current_gate"],"BI-002")
        self.assertEqual(horizon["next_supporting_priority"]["id"],
                         "BI-WORLD-TRAVERSAL-P08-SENSOR")
        self.assertEqual(validate_dispatch(horizon,json.loads(json.dumps(DISPATCH)))["state"],"PASS")

    def test_p04_supporting_priority_cannot_disappear(self):
        horizon=clone()
        horizon.pop("next_supporting_priority")
        with self.assertRaisesRegex(HorizonError,"SUPPORTING_WORLD_SENSOR_PRIORITY_LOST"):
            validate(horizon)

    def test_p04_supporting_priority_cannot_replace_product_hunger_gate(self):
        horizon=clone()
        horizon["next_supporting_priority"]["current_product_gate"]="BI-005"
        with self.assertRaisesRegex(HorizonError,"SUPPORTING_WORLD_SENSOR_PRIORITY_LOST"):
            validate(horizon)

    def test_p04_sensor_must_run_on_local_game_host(self):
        dispatch=json.loads(json.dumps(DISPATCH))
        next(x for x in dispatch["lanes"] if x["id"]=="WORLD_SENSOR")["host"]="CURRENT_CHAT_RUNTIME"
        with self.assertRaisesRegex(HorizonError,"P04_LOCAL_GAME_HOST_OR_PRIVACY_LOST"):
            validate_dispatch(clone(),dispatch)

    def test_p04_one_screen_no_parallel_cursor_agents(self):
        dispatch=json.loads(json.dumps(DISPATCH))
        dispatch["parallel_execution"]["observed_parallelism"]=True
        with self.assertRaisesRegex(HorizonError,"P04_PHANTOM_PARALLEL_GAME_AGENT"):
            validate_dispatch(clone(),dispatch)
        dispatch=json.loads(json.dumps(DISPATCH))
        next(x for x in dispatch["lanes"] if x["id"]=="WORLD_OUTCOME")["serial_with"]=[]
        with self.assertRaisesRegex(HorizonError,"P04_LOCAL_GAME_HOST_OR_PRIVACY_LOST|P04_SINGLE_CURSOR_OWNERSHIP_LOST"):
            validate_dispatch(clone(),dispatch)

    def test_p04_outcome_cannot_run_before_real_sensor_proof(self):
        dispatch=json.loads(json.dumps(DISPATCH))
        next(x for x in dispatch["lanes"] if x["id"]=="WORLD_OUTCOME")["dependencies"]=[]
        with self.assertRaisesRegex(HorizonError,"P04_WORLD_SENSOR_EXECUTION_ORDER_LOST"):
            validate_dispatch(clone(),dispatch)

    def test_p04_dangling_unsafe_dependency_and_writer_collision_fail(self):
        dispatch=json.loads(json.dumps(DISPATCH))
        next(x for x in dispatch["lanes"] if x["id"]=="WORLD_INTEGRATE")["dependencies"]=["OTHER_UNMERGED_PR"]
        with self.assertRaisesRegex(HorizonError,"P04_DISPATCH_DANGLING_DEPENDENCY"):
            validate_dispatch(clone(),dispatch)
        dispatch=json.loads(json.dumps(DISPATCH))
        next(x for x in dispatch["lanes"] if x["id"]=="WORLD_INTEGRATE")["status"]="READY_TO_OVERWRITE_PR159"
        with self.assertRaisesRegex(HorizonError,"P04_PR159_COLLISION_GUARD_LOST"):
            validate_dispatch(clone(),dispatch)

    def test_income_cannot_skip_needs_balance(self):
        item=clone()
        next(x for x in item["stages"] if x["id"]=="BI-004")["depends_on"]=[]
        with self.assertRaisesRegex(HorizonError,"PHASE_ORDER_REGRESSION"):
            validate(item)
    def test_skill_cannot_skip_income(self):
        item=clone()
        next(x for x in item["stages"] if x["id"]=="BI-005")["depends_on"]=[]
        with self.assertRaisesRegex(HorizonError,"PHASE_ORDER_REGRESSION"):
            validate(item)
    def test_need_removed_rejected(self):
        item=clone()
        item["stages"]=[x for x in item["stages"] if x["id"]!="BI-003D"]
        with self.assertRaises(HorizonError):
            validate(item)
    def test_cycles_rejected(self):
        item=clone()
        next(x for x in item["stages"] if x["id"]=="BI-002")["depends_on"]=["BI-004"]
        with self.assertRaisesRegex(HorizonError,"CYCLE"):
            validate(item)
    def test_hunger_cannot_be_buried(self):
        item=clone()
        item["current_gate"]="BI-004"
        with self.assertRaisesRegex(HorizonError,"HUNGER_GATE_LOST"):
            validate(item)

if __name__=="__main__":
    unittest.main()
