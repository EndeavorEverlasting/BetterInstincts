"""Source-only regression tests for the private seam closure loop."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.launch_receipt import SCHEMA as LAUNCH_SCHEMA, gap, write_result
from scripts.seam_closure import MAX_EVENTS, SCHEMA, identify, read_events, latest_run_handoff


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
