"""CI fixtures only; live-game receipts are simulated and never certified."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from betterinstincts.live_eval import EvidenceError
from scripts import game_baseline, game_host, live_cert

RUN = "bi002-first-boot"
PATCH = "1.121.361.1020"


class GameBaselineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.host_output = Path(self.tmp.name) / "dist" / "game-host"
        self.cert_output = Path(self.tmp.name) / "dist" / "live-cert"
        patcher = patch.object(game_host, "OUTPUT", self.host_output)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.root = game_host.run_root(RUN)
        self.root.mkdir(parents=True)
        (self.root / "run.json").write_text(json.dumps({
            "schema": game_host.SCHEMA, "run_id": RUN, "platform": "windows",
            "mode": "new", "game_version": None, "save_alias": "BI_LAB_DISPOSABLE_01",
        }), encoding="utf-8")
        self.event("SESSION_CREATED")
        self.event("NEW_GAME_CAS_REQUESTED")

    def event(self, state, **fields):
        with (self.root / "events.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"schema": game_host.SCHEMA, "state": state, **fields}) + "\n")

    def attested(self):
        self.event("LIVE_REPORTED_UNREVIEWED", game_version=PATCH, capture_ref="capture:live-mode-001")

    def test_cas_only_cannot_create_baseline(self):
        with self.assertRaisesRegex(game_host.GateError, "LIVE_MODE_ATTESTATION_REQUIRED"):
            game_baseline.prepare(RUN, output=self.cert_output)
        self.assertFalse(self.cert_output.exists())

    def test_confirmed_session_opens_empty_recorder_no_gameplay_claim(self):
        self.attested()
        result = game_baseline.prepare(RUN, output=self.cert_output)
        self.assertEqual(result["state"], "BASELINE_RECORDER_CREATED")
        self.assertEqual(result["game_version"], PATCH)
        self.assertEqual(result["baseline_trials"], 0)
        self.assertEqual(result["next_stage"], "baseline")
        self.assertEqual(result["studio_build"], live_cert.PENDING_STUDIO)
        self.assertIn("NOT_GAMEPLAY", result["proof_ceiling"])
        self.assertEqual(live_cert.status(RUN, self.cert_output)["progress"]["observations_recorded"], 0)

    def test_retry_preserves_existing_real_trial(self):
        self.attested()
        game_baseline.prepare(RUN, output=self.cert_output)
        live_cert.record(RUN, {
            "stage": "baseline", "trial": 1, "seconds_to_eat": 95,
            "min_hunger": 0.24, "sim_lag_ms": 30, "player_interruptions": 0,
            "action_loops": 0, "exceptions": 0,
            "observation_ref": "fixture:trial-1"
        }, self.cert_output)
        reused = game_baseline.prepare(RUN, output=self.cert_output)
        self.assertEqual(reused["state"], "EXISTING_RECORDER_PRESERVED")
        self.assertEqual(reused["baseline_trials"], 1)
        self.assertEqual(reused["modified_trials"], 0)

    def test_version_mismatch_fails_without_overwrite(self):
        self.attested()
        live_cert.init(RUN, "1.111.2.1020", "windows", "some studio", self.cert_output)
        before = (self.cert_output / RUN / "run.json").read_bytes()
        with self.assertRaisesRegex(game_host.GateError, "VERSION_MISMATCH"):
            game_baseline.prepare(RUN, output=self.cert_output)
        self.assertEqual((self.cert_output / RUN / "run.json").read_bytes(), before)

    def test_pending_studio_cannot_attest_as_certified(self):
        self.attested()
        game_baseline.prepare(RUN, output=self.cert_output)
        with self.assertRaisesRegex(EvidenceError, "STUDIO_BUILD_UNOBSERVED"):
            live_cert.attest(RUN, "a" * 64, "b" * 64, "synthetic-tuning",
                             "capture:test-fixture", True, True, self.cert_output)
        self.assertIsNone(live_cert.load(RUN, self.cert_output)[0]["package_sha256"])
        evidence = live_cert.record_studio_build(RUN, "locally-observed-studio-build", self.cert_output)
        self.assertEqual(evidence["state"], "STUDIO_BUILD_RECORDED_UNREVIEWED")
        with self.assertRaisesRegex(EvidenceError, "STUDIO_BUILD_ALREADY_RECORDED"):
            live_cert.record_studio_build(RUN, "different-version", self.cert_output)

    def test_rejects_session_without_real_version(self):
        self.event("LIVE_REPORTED_UNREVIEWED", game_version="UNKNOWN_VERSION")
        with self.assertRaisesRegex(game_host.GateError, "EXACT_LIVE_GAME_VERSION_REQUIRED"):
            game_baseline.prepare(RUN, output=self.cert_output)

    def test_sample_event_after_live_still_eligible(self):
        self.attested()
        self.event("SAMPLE_INGESTED_UNVERIFIED", samples=1)
        self.assertEqual(game_baseline.prepare(RUN, output=self.cert_output)["baseline_trials"], 0)


if __name__ == "__main__":
    unittest.main()
