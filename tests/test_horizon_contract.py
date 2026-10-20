import json
import unittest
from pathlib import Path
from scripts.check_horizon import validate,HorizonError

ROOT=Path(__file__).resolve().parents[1]
ORIGINAL=json.loads((ROOT/"plans/horizon.v1.json").read_text())

def clone():
    return json.loads(json.dumps(ORIGINAL))

class HorizonContractTests(unittest.TestCase):
    def test_current_horizon_valid(self):
        self.assertEqual(validate(clone())["state"],"PASS")
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
