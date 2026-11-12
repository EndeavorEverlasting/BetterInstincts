import json
import tempfile
import unittest
from pathlib import Path
from betterinstincts.live_eval import EvidenceError
from scripts.live_cert import init,record,attest,status,run_root

def row(stage,n,sec):
    return {"stage":stage,"trial":n,"seconds_to_eat":sec,"min_hunger":.22,
            "sim_lag_ms":30,"player_interruptions":0,"action_loops":0,
            "exceptions":0,"observation_ref":"manual-capture-fixture-"+stage+"-"+str(n)}

class LabCLITests(unittest.TestCase):
    def test_scoped_and_bounded_receipts(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"dist/live-cert"
            location=init("bi002-testing","1.111.2.1020","windows","synthetic-studio",out)
            self.assertTrue(location.is_relative_to(out))
            self.assertEqual(status("bi002-testing",out)["state"],"INCOMPLETE")
            self.assertEqual(status("bi002-testing",out)["progress"]["observations_percent"],0)
            for n in range(1,6):
                record("bi002-testing",row("baseline",n,100),out)
                record("bi002-testing",row("modified",n,70),out)
            record("bi002-testing",row("rollback",1,100),out)
            self.assertEqual(status("bi002-testing",out)["state"],"MEASUREMENTS_FAIL")
            self.assertEqual(status("bi002-testing",out)["progress"]["observations_percent"],100)
            self.assertEqual(status("bi002-testing",out)["progress"]["game_certification"],"NOT_GRANTED_BY_CLI")
            attest("bi002-testing","a"*64,"b"*64,"synthetic-resource",
                   "capture:synthetic-fixture",True,True,out)
            self.assertEqual(status("bi002-testing",out,save_report=True)["state"],
                             "MEASUREMENTS_PASS_REVIEW_REQUIRED")
            self.assertTrue((location/"report.json").is_file())
            with self.assertRaisesRegex(EvidenceError,"DUPLICATE_TRIAL"):
                record("bi002-testing",row("baseline",1,100),out)
    def test_replayed_observation_ref_is_rejected_before_append(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            location = init("replay-run", "1.111.2.1020", "windows", "synthetic-studio", out)
            first = row("baseline", 1, 100)
            record("replay-run", first, out)
            replay = row("modified", 1, 70)
            replay["observation_ref"] = first["observation_ref"]
            before = (location / "observations.jsonl").read_bytes()
            with self.assertRaisesRegex(EvidenceError, "DUPLICATE_OBSERVATION_REF"):
                record("replay-run", replay, out)
            self.assertEqual((location / "observations.jsonl").read_bytes(), before)
            self.assertEqual(status("replay-run", out)["counts"]["baseline"], 1)
            self.assertEqual(status("replay-run", out)["counts"]["modified"], 0)

    def test_replayed_persisted_observations_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            location = init("replay-run", "1.111.2.1020", "windows", "synthetic-studio", out)
            first = row("baseline", 1, 100)
            record("replay-run", first, out)
            tampered = row("modified", 2, 70)
            tampered["observation_ref"] = first["observation_ref"]
            with (location / "observations.jsonl").open("a", encoding="utf-8") as sink:
                sink.write(json.dumps(tampered) + "\n")
            with self.assertRaisesRegex(EvidenceError, "DUPLICATE_OBSERVATION_REF"):
                status("replay-run", out)

    def test_run_id_traversal_rejected(self):
        for bad in ("../saves","x/../../saves","..","x","C:relative"):
            with self.assertRaises(EvidenceError):
                run_root(bad,Path("/tmp/harmless"))
    def test_init_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)
            init("proof-run","1.111.2.1020","windows","synthetic-studio",target)
            with self.assertRaises(FileExistsError):
                init("proof-run","1.111.2.1020","windows","synthetic-studio",target)
    def test_real_attestation_required(self):
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)
            init("proof-run","1.111.2.1020","windows","synthetic-studio",target)
            with self.assertRaisesRegex(EvidenceError,"REQUIRED_LOCAL_ATTESTATION_MISSING"):
                attest("proof-run","a"*64,"b"*64,"fake-id","capture:test",output=target)
if __name__=="__main__":
    unittest.main()
