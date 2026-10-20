import unittest
from betterinstincts.live_eval import evaluate, EvidenceError

META={"disposable_save_confirmed":True,"user_selected_mods_root_confirmed":True,
"package_sha256":"a"*64,"tuning_source_sha256":"b"*64,"tuning_resource_id":"fixture-resource",
"capture_ref":"evidence:manual-observation-fixture"}

def trial(stage, i, seconds=100, lag=50, interrupts=0):
    return {"stage":stage,"trial":i,"seconds_to_eat":seconds,"min_hunger":.15,
            "sim_lag_ms":lag,"player_interruptions":interrupts,"action_loops":0,
            "exceptions":0,"observation_ref":"synthetic-test-only:"+str(i)}

def populated():
    return [trial("baseline",i) for i in range(1,6)]+[
        trial("modified",i,seconds=70) for i in range(1,6)]+[trial("rollback",1)]

class LiveEvalTests(unittest.TestCase):
    def test_no_trials_no_pass(self):
        self.assertEqual(evaluate(META,[])["state"],"INCOMPLETE")
    def test_complete_numeric_evidence_needs_review(self):
        result=evaluate(META,populated())
        self.assertEqual(result["state"],"MEASUREMENTS_PASS_REVIEW_REQUIRED")
        self.assertEqual(result["proof_ceiling"],"UNVERIFIED_OBSERVATIONS_ONLY")
    def test_manual_override_regression_fails(self):
        rows=populated()
        rows[5]["player_interruptions"]=1
        self.assertEqual(evaluate(META,rows)["state"],"MEASUREMENTS_FAIL")
    def test_lag_regression_fails(self):
        rows=populated()
        for r in rows[5:10]:
            r["sim_lag_ms"]=120
        self.assertEqual(evaluate(META,rows)["state"],"MEASUREMENTS_FAIL")
    def test_no_attestation_fails(self):
        self.assertEqual(evaluate({},populated())["state"],"MEASUREMENTS_FAIL")
    def test_duplicate_trial_rejected(self):
        with self.assertRaisesRegex(EvidenceError,"DUPLICATE_TRIAL"):
            evaluate(META,populated()+[trial("baseline",1)])
    def test_nonfinite_numeric_rejected(self):
        rows=populated()
        rows[0]["seconds_to_eat"]=float("nan")
        with self.assertRaisesRegex(EvidenceError,"INVALID_METRIC"):
            evaluate(META,rows)
    def test_unsafe_negative_metrics_rejected(self):
        rows=populated()
        rows[0]["exceptions"]=-1
        with self.assertRaisesRegex(EvidenceError,"INVALID_COUNT"):
            evaluate(META,rows)
if __name__ == "__main__":
    unittest.main()
