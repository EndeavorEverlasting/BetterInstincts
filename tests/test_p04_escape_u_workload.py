"""P04 regression: keyboard incident is an owned supporting workload, not game proof."""
import copy
import json
import unittest
from pathlib import Path

from scripts.check_horizon import HorizonError, validate, validate_dispatch

ROOT = Path(__file__).resolve().parents[1]
HORIZON = ROOT / "plans/horizon.v1.json"
DISPATCH = ROOT / "plans/active/BI-HORIZON.dispatch.v1.json"


class EscapeUP04WorkloadTests(unittest.TestCase):
    def setUp(self):
        self.horizon = json.loads(HORIZON.read_text(encoding="utf-8"))
        self.dispatch = json.loads(DISPATCH.read_text(encoding="utf-8"))

    def test_registered_workload_preserves_parent_and_world_priority(self):
        self.assertEqual(validate(self.horizon)["state"], "PASS")
        d = validate_dispatch(self.horizon, self.dispatch)
        self.assertEqual(d["state"], "PASS")
        self.assertEqual(self.horizon["current_gate"], "BI-002")
        self.assertEqual(self.horizon["next_supporting_priority"]["id"],
                         "BI-WORLD-TRAVERSAL-P08-SENSOR")
        self.assertNotIn("BI-ESC-U-FORENSICS-P04",
                         [x["id"] for x in self.horizon["stages"]])

    def test_removing_workload_fails_closed(self):
        broken = copy.deepcopy(self.horizon)
        broken.pop("supporting_workloads")
        with self.assertRaisesRegex(HorizonError, "ESC_U_P04_CANONICAL_WORKLOAD_LOST"):
            validate(broken)

    def test_offline_ci_cannot_be_promoted_to_physical_key_proof(self):
        for status_field in ("physical_escape_menu", "physical_u_clubs",
                             "local_hook_active", "culpable_cursor_session"):
            with self.subTest(status_field=status_field):
                broken = copy.deepcopy(self.horizon)
                broken["supporting_workloads"]["escape_u_input_forensics"][
                    "status_dimensions"][status_field] = "PASS_FROM_CI"
                with self.assertRaisesRegex(HorizonError, "ESC_U_PHYSICAL_CAUSALITY_UNPROVEN"):
                    validate(broken)

    def test_delete_os_or_input_guard_denies(self):
        for guard in ("NO_OS_KEY_REMAP", "NO_UNATTENDED_KEY_INJECTION",
                      "NO_PERSONAL_SAVE_ACCESS", "SINGLE_CURSOR_LEASE"):
            with self.subTest(guard=guard):
                broken = copy.deepcopy(self.horizon)
                row = broken["supporting_workloads"]["escape_u_input_forensics"]
                row["safety"].remove(guard)
                with self.assertRaisesRegex(HorizonError, "ESC_U_P04_SOVEREIGNTY_GUARD_LOST"):
                    validate(broken)

    def test_missing_lane_is_rejected(self):
        broken = copy.deepcopy(self.dispatch)
        broken["lanes"] = [x for x in broken["lanes"]
                           if x["id"] != "ESC_U_CURSOR_PROVENANCE"]
        with self.assertRaisesRegex(HorizonError, "ESC_U_P04_DISPATCH_LANE_COVERAGE_LOST"):
            validate_dispatch(self.horizon, broken)

    def test_interactive_lane_must_not_be_labeled_autonomous(self):
        broken = copy.deepcopy(self.dispatch)
        row = next(x for x in broken["lanes"] if x["id"] == "ESC_U_OPERATOR_KEY_MATRIX")
        row["execution_environment"] = "CURRENT_CHAT_RUNTIME"
        with self.assertRaisesRegex(HorizonError, "ESC_U_P04_RUNTIME_PARTITION_OR_DEPENDENCY_LOST"):
            validate_dispatch(self.horizon, broken)

    def test_forensic_convergence_waits_for_both_local_evidence_lanes(self):
        broken = copy.deepcopy(self.dispatch)
        row = next(x for x in broken["lanes"] if x["id"] == "ESC_U_RECONCILE")
        row["dependencies"] = ["ESC_U_CURSOR_PROVENANCE"]
        with self.assertRaisesRegex(HorizonError, "ESC_U_P04_RUNTIME_PARTITION_OR_DEPENDENCY_LOST"):
            validate_dispatch(self.horizon, broken)

    def test_claimed_physical_parallel_execution_is_rejected(self):
        broken = copy.deepcopy(self.dispatch)
        broken["parallel_execution"]["escape_u_observed_parallelism"] = True
        with self.assertRaisesRegex(HorizonError, "ESC_U_P04_FALSE_PARALLELISM_CLAIM"):
            validate_dispatch(self.horizon, broken)


if __name__ == "__main__":
    unittest.main()
