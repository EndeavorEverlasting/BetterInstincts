"""Source-only regression tests for the private seam closure loop."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.launch_receipt import SCHEMA as LAUNCH_SCHEMA, gap, write_result
from scripts.seam_closure import MAX_EVENTS, SCHEMA, identify, read_events, latest_run_handoff, record_native_notice
from betterinstincts.runtime_seam import notice_for


class SeamClosureTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run_id = "a" * 32
        self.dir = Path(self.temp.name) / self.run_id
        self.dir.mkdir()
        self.path = self.dir / "launch.json"

    def blocked(self, stage="startup_catalog", reason="CURRENT_GAME_SAVE_CATALOG_REQUIRED"):
        return {
            "schema": LAUNCH_SCHEMA, "run_id": self.run_id, "status": "blocked",
            "stage": stage, "reason": reason,
            "automation_gaps": [gap(stage, reason, "private path C:\\Host\\Secret", "scripts/startup_handoff.py", actor="repository")],
        }

    def test_known_gap_has_stable_typed_handoff_and_private_event(self):
        result = self.blocked()
        write_result(self.path, result)
        self.assertEqual(result["seam_closure"]["current"][0]["capability"], "PROCESS_BOUND_SAVE_CATALOG")
        self.assertEqual(result["seam_closure"]["current"][0]["resolution_state"], "HOST_OBSERVATION_REQUIRED")
        self.assertEqual(result["seam_closure"]["current"][0]["effect_admission"], "NOT_GRANTED")
        self.assertEqual(len(read_events(self.path, self.run_id)), 1)
        self.assertEqual(json.loads(self.path.read_text())["seam_closure"]["event_count"], 1)
        self.assertNotIn("Secret", (self.dir / "seam-events.json").read_text())

    def test_idempotent_rewrites_and_different_gates(self):
        result = self.blocked()
        write_result(self.path, result)
        first = read_events(self.path, self.run_id)[0]
        write_result(self.path, result)
        self.assertEqual(read_events(self.path, self.run_id), [first])
        write_result(self.path, self.blocked("native_restock_binding", "NATIVE_BINDING_MISSING"))
        self.assertEqual(len(read_events(self.path, self.run_id)), 2)

    def test_unregistered_and_policy_denial_do_not_grant_shell(self):
        row = identify({"stage": "made_up", "reason": "path C:\\Secret",
                        "repository_owner": "../../../evil.py"}, self.run_id)
        self.assertEqual(row["capability"], "UNREGISTERED_SEAM")
        self.assertEqual(row["canonical_owner"], None)
        self.assertEqual(row["reason_code"], "UNCLASSIFIED_REASON")
        deny = identify({"stage": "checkout", "reason": "OPERATOR_DESKTOP_BOUNDARY",
                         "repository_owner": "scripts/play.py"}, self.run_id)
        self.assertEqual(deny["resolution_state"], "POLICY_HOLD")
        self.assertEqual(deny["effect_admission"], "NOT_GRANTED")

    def test_success_cannot_erase_or_claim_live_proof(self):
        write_result(self.path, self.blocked())
        write_result(self.path, {"schema": LAUNCH_SCHEMA, "run_id": self.run_id,
                                 "status": "ok", "stage": "complete", "automation_gaps": []})
        self.assertEqual(len(read_events(self.path, self.run_id)), 1)
        self.assertNotIn("seam_closure", json.loads(self.path.read_text()))


    def test_latest_run_handoff_rehydrates_without_private_data(self):
        older = self.blocked()
        older["started_at"] = "2026-11-18T20:00:00+00:00"
        write_result(self.path, older)
        state = latest_run_handoff(Path(self.temp.name))
        self.assertEqual(state["state"], "BLOCKED_RUN_RECOVERABLE")
        self.assertEqual(state["seams"][0]["capability"], "PROCESS_BOUND_SAVE_CATALOG")
        self.assertNotIn("event_file", state)
        self.assertNotIn("Secret", json.dumps(state))
        newer_id = "b" * 32
        newer = Path(self.temp.name) / newer_id
        newer.mkdir()
        write_result(newer / "launch.json", {
            "schema": LAUNCH_SCHEMA, "run_id": newer_id,
            "started_at": "2026-11-18T20:01:00+00:00", "status": "ok",
            "stage": "complete", "automation_gaps": [],
        })
        self.assertEqual(latest_run_handoff(Path(self.temp.name))["state"], "NO_CURRENT_BLOCKED_RUN")

    def test_native_runtime_notice_joins_exact_process_and_existing_run(self):
        process = {"pid": 1234, "creation_ticks": "1001234",
                   "executable": r"C:\Games\TS4_x64.exe", "game_version": "1.121.361.1020"}
        self.assertTrue(self.run_id)
        launch = {"schema": LAUNCH_SCHEMA, "run_id": self.run_id,
                  "started_at": "2026-11-18T20:00:00+00:00",
                  "status": "ok", "stage": "complete",
                  "game_process": process, "automation_gaps": []}
        write_result(self.path, launch)
        notice = notice_for("NATIVE_SESSION_REBIND_REQUIRED",
                            game_build=process["game_version"], session="game-run")
        joined = record_native_notice(self.path, notice, observed_process=process,
                                      observed_session="game-run")
        self.assertEqual(joined["state"], "NATIVE_NOTICE_RECORDED")
        self.assertEqual(joined["effect_admission"], "NOT_GRANTED")
        record_native_notice(self.path, notice, observed_process=process, observed_session="game-run")
        self.assertEqual(len(read_events(self.path, self.run_id)), 1)
        self.assertNotIn("Games", (self.dir / "seam-events.json").read_text())
        adopted = latest_run_handoff(Path(self.temp.name))
        self.assertEqual(adopted["state"], "HISTORICAL_NATIVE_NOTICES_REOBSERVE")
        self.assertEqual(adopted["seams"][0]["stage"], "native_runtime")

    def test_native_runtime_notice_rejects_unbound_session_or_process(self):
        process = {"pid": 1234, "creation_ticks": "1001234",
                   "executable": r"C:\Games\TS4_x64.exe", "game_version": "1.121.361.1020"}
        write_result(self.path, {"schema": LAUNCH_SCHEMA, "run_id": self.run_id,
                                 "status": "ok", "game_process": process})
        notice = notice_for("NATIVE_FRAME_UNQUALIFIED",
                            game_build=process["game_version"], session="game-run")
        with self.assertRaisesRegex(ValueError, "SEAM_NATIVE_NOTICE_UNCORRELATED"):
            record_native_notice(self.path, notice, observed_process=process,
                                 observed_session="another-run")
        wrong = {**process, "creation_ticks": "1001235"}
        with self.assertRaisesRegex(ValueError, "SEAM_NATIVE_PROCESS_NOT_BOUND"):
            record_native_notice(self.path, notice, observed_process=wrong,
                                 observed_session="game-run")
        self.assertFalse((self.dir / "seam-events.json").exists())

    def test_symlink_event_store_is_denied(self):
        other = self.dir / "other.json"
        other.write_text("{}")
        (self.dir / "seam-events.json").symlink_to(other)
        with self.assertRaisesRegex(ValueError, "SEAM_RECEIPT_STORE_UNSAFE"):
            write_result(self.path, self.blocked())
        self.assertEqual(other.read_text(), "{}")

    def test_bounded_log_rejects_new_event_without_losing_history(self):
        for n in range(MAX_EVENTS):
            write_result(self.path, self.blocked("stage_" + str(n), "MISSING_" + str(n)))
        self.assertEqual(len(read_events(self.path, self.run_id)), MAX_EVENTS)
        with self.assertRaisesRegex(ValueError, "SEAM_RECEIPT_STORE_FULL"):
            write_result(self.path, self.blocked("last_stage", "MISSING_LAST"))
        self.assertEqual(len(read_events(self.path, self.run_id)), MAX_EVENTS)


if __name__ == "__main__":
    unittest.main()
