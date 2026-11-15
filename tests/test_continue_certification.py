"""The dispatch is a supervised task, with no Sims launch or input side effects."""

from contextlib import nullcontext
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from betterinstincts.first_run import FirstRunError
from scripts import continue_certification as handoff
from scripts.launch_save_route import CERTIFICATION_ID, CONTEXT_SCHEMA


class ContinueCertificationTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name).resolve() / "live-cert-worktree"
        self.root.mkdir()
        (self.root / ".git").write_text("gitdir: ../gitdir\n", encoding="utf-8")
        for relative in ("docs/AGENT_OPERATING_RULES.md",
                         "plans/active/BI-002.execution.v1.json"):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()

    def test_running_session_is_handed_off_even_without_local_memo(self):
        with patch.object(handoff, "read_sims_processes", return_value={53: "TS4_x64.exe"}):
            task = handoff.build_handoff(self.root)
        self.assertIn('"pids": [53]', task)
        self.assertIn("HOLD_CERTIFICATION_CONTEXT", task)
        self.assertIn("Recover missing run context", task)
        self.assertIn("keep it open", task)
        self.assertLess(task.index("## 2. Close the current offer"), task.index("## 3. Begin BI-002"))
        self.assertFalse((self.root / "dist").exists())

    def test_handoff_loads_known_results_from_the_original_checkout(self):
        from betterinstincts.experience_recall import EVENT_SCHEMA, record_new

        context = dict(domain="preference_offer", game_build="1.121.361.1020",
                       installation_profile="trial", mechanic_id="ea_265965", choice_id="yes_0")
        record_new({"schema": EVENT_SCHEMA, "context": context, "result": "actor_trait_258767",
                    "evidence_level": "LOCAL_ARTIFACT_VERIFIED", "evidence_ref": "capture:prior-yes",
                    "observed_at_ms": 1000}, root=self.root)
        with (patch.object(handoff, "read_sims_processes", return_value={53: "TS4_x64.exe"}),
              patch.object(handoff, "view", return_value={"profile_id": "trial",
                                                          "preferred_household_id": None,
                                                          "profiles": ["trial"]})):
            payload = handoff.build_handoff(self.root)
        self.assertIn("PAST_EXPERIENCE_RECALLED", payload)
        self.assertIn("NEW_EXPERIENCE", payload)
        self.assertIn('"current_outcome_proven": false', payload)

    def test_existing_memo_is_used_in_the_evidence_checkout_without_writes(self):
        memo = self.root / handoff.LOCAL_CONTEXT.relative_to(handoff.ROOT)
        memo.parent.mkdir(parents=True)
        memo.write_text(json.dumps({
            "schema": CONTEXT_SCHEMA, "certification_id": CERTIFICATION_ID,
            "status": "PENDING", "run_id": "bi-preference", "game_version": "1.121.361.1020",
        }), encoding="utf-8")
        before = memo.read_bytes(), memo.stat().st_mtime_ns
        with patch.object(handoff, "read_sims_processes", return_value={53: "TS4_x64.exe"}):
            self.assertIn("PRESERVE_RUNNING_CERTIFICATION_SESSION", handoff.build_handoff(self.root))
        self.assertEqual(before, (memo.read_bytes(), memo.stat().st_mtime_ns))

    def test_ambiguous_and_unavailable_processes_are_distinct_observations(self):
        with patch.object(handoff, "read_sims_processes",
                          return_value={17: "TS4.exe", 53: "TS4_x64.exe"}):
            task = handoff.build_handoff(self.root)
            self.assertIn('"pids": [17, 53]', task)
            self.assertIn("HOLD_PROCESS_IDENTITY", task)
        with patch.object(handoff, "read_sims_processes",
                          side_effect=FirstRunError("PROCESS_INVENTORY_UNAVAILABLE")):
            task = handoff.build_handoff(self.root)
        self.assertIn("PROCESS_INVENTORY_UNAVAILABLE", task)
        self.assertNotIn('"pids"', task)

    def test_codex_receives_stdin_once_in_original_checkout_and_keeps_failure(self):
        installed = self.root.parent / "local-tools" / "codex.cmd"
        with (patch.object(handoff.sys, "platform", "win32"),
              patch.object(handoff, "installed_codex", return_value=installed),
              patch.object(handoff, "checkout_dispatch", return_value=nullcontext()) as lock,
              patch.object(handoff, "build_handoff", return_value="one certification task"),
              patch.object(handoff.subprocess, "run",
                           return_value=subprocess.CompletedProcess([], 7)) as run):
            self.assertEqual(7, handoff.dispatch(self.root))
        lock.assert_called_once_with(self.root)
        run.assert_called_once_with([str(installed), "exec", "-"], cwd=self.root,
                                    input=b"one certification task", check=False)

    def test_invalid_checkout_refused_before_dispatch(self):
        with (patch.object(handoff.sys, "platform", "win32"),
              patch.object(handoff, "installed_codex") as resolve):
            with self.assertRaisesRegex(handoff.HandoffError, "evidence checkout"):
                handoff.dispatch(self.root.parent)
        resolve.assert_not_called()

    def test_missing_and_checkout_local_codex_are_refused(self):
        with patch.object(handoff.shutil, "which", return_value=None):
            with self.assertRaisesRegex(handoff.HandoffError, "not found"):
                handoff.installed_codex(self.root)
        with patch.object(handoff.shutil, "which", return_value=str(self.root / "codex.exe")):
            with self.assertRaisesRegex(handoff.HandoffError, "outside this checkout"):
                handoff.installed_codex(self.root)

    def test_non_windows_does_not_dispatch(self):
        with (patch.object(handoff.sys, "platform", "linux"),
              patch.object(handoff.subprocess, "run") as run):
            with self.assertRaisesRegex(handoff.HandoffError, "Windows Sims host"):
                handoff.dispatch(self.root)
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
