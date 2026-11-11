"""P00/P01 executable governance regressions, no Sims/desktop access."""
from __future__ import annotations

import copy
import unittest
from pathlib import Path

from scripts.check_world_traversal_harness import (
    WorldTraversalHarnessError, check, load_inputs, validate_contract,
)

ROOT = Path(__file__).resolve().parents[1]


class WorldTraversalHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = load_inputs(ROOT)

    def validate(self, *replacements):
        values = [copy.deepcopy(x) for x in self.inputs]
        for index, replacement in replacements:
            values[index] = replacement
        return validate_contract(*values, root=ROOT)

    def test_root_world_traversal_governance_complete_and_nonexecuting(self):
        status = check(ROOT)
        self.assertEqual(status["status"], "P00_P01_WORLD_TRAVERSAL_HARNESS_PASS")
        self.assertEqual(status["ontology_revision"], 5)
        self.assertEqual(status["product_gate"], "BI-002")
        self.assertEqual(status["artifact_classes"], 4)
        self.assertFalse(status["local_game_activation_observed"])
        self.assertFalse(status["game_input_authorized"])

    def test_p00_all_three_semantics_required(self):
        ontology = copy.deepcopy(self.inputs[1])
        ontology["concepts"].pop("WORLD_TARGET_TRACK")
        with self.assertRaisesRegex(WorldTraversalHarnessError, "WORLD_SEMANTIC_OWNER_LOST"):
            self.validate((1, ontology))

    def test_p00_semantic_owner_cannot_become_input_controller(self):
        ontology = copy.deepcopy(self.inputs[1])
        ontology["concepts"]["HIGHLIGHT_OBSERVATION"]["canonical_owner"] = "betterinstincts/screen_admit.py"
        with self.assertRaisesRegex(WorldTraversalHarnessError, "WORLD_SEMANTIC_OWNER_LOST"):
            self.validate((1, ontology))
        ontology = copy.deepcopy(self.inputs[1])
        ontology["relations"] = [r for r in ontology["relations"]
                                  if r.get("predicate") != "CANNOT_MINT_INPUT_AUTHORITY"]
        with self.assertRaisesRegex(WorldTraversalHarnessError, "WORLD_SEMANTIC_AUTHORITY_RELATION_LOST"):
            self.validate((1, ontology))

    def test_p00_critical_invariants_must_remain_mapped(self):
        ontology = copy.deepcopy(self.inputs[1])
        ontology["invariants"] = [r for r in ontology["invariants"]
                                  if r["id"] != "BI-ONT-029"]
        with self.assertRaisesRegex(WorldTraversalHarnessError, "WORLD_SEMANTIC_INVARIANT_LOST"):
            self.validate((1, ontology))

    def test_p00_highlight_two_frames_and_absent_id_policy_fail_closed(self):
        domain = copy.deepcopy(self.inputs[2])
        domain["frames"]["min_for_lock"] = 1
        with self.assertRaisesRegex(WorldTraversalHarnessError, "WORLD_TRACK_OR_REPLAY_SAFETY_DRIFT"):
            self.validate((2, domain))
        domain = copy.deepcopy(self.inputs[2])
        domain["frames"]["highlight_target_id_policy"] = "NON_NULL_ALWAYS"
        with self.assertRaisesRegex(WorldTraversalHarnessError, "WORLD_TRACK_OR_REPLAY_SAFETY_DRIFT"):
            self.validate((2, domain))

    def test_p00_replay_holdout_and_player_interrupt_attestation_immutable(self):
        domain = copy.deepcopy(self.inputs[2])
        domain["learning"]["heldout_training_overlap"] = "ALLOW"
        with self.assertRaisesRegex(WorldTraversalHarnessError, "WORLD_TRACK_OR_REPLAY_SAFETY_DRIFT"):
            self.validate((2, domain))
        domain = copy.deepcopy(self.inputs[2])
        domain["learning"]["player_interrupted_attestation"] = "UNKNOWN_COUNTS_AS_FALSE"
        with self.assertRaisesRegex(WorldTraversalHarnessError, "WORLD_TRACK_OR_REPLAY_SAFETY_DRIFT"):
            self.validate((2, domain))
        domain = copy.deepcopy(self.inputs[2])
        domain["boundaries"]["execute_allowed_default"] = True
        with self.assertRaisesRegex(WorldTraversalHarnessError, "WORLD_TRACK_OR_REPLAY_SAFETY_DRIFT"):
            self.validate((2, domain))

    def test_horizon_cannot_promote_world_sensor_to_product_gate(self):
        horizon = copy.deepcopy(self.inputs[3])
        horizon["current_gate"] = "BI-WORLD-TRAVERSAL-P08-SENSOR"
        with self.assertRaisesRegex(WorldTraversalHarnessError, "WORLD_HORIZON_PRIORITY_DRIFT"):
            self.validate((3, horizon))

    def test_harness_never_authorizes_live_sims_input_or_auto_capture(self):
        harness = copy.deepcopy(self.inputs[0])
        for flag in ("execute_allowed", "auto_collect_frames",
                     "auto_persist_models", "auto_use_saves",
                     "may_change_windows_peripherals",
                     "may_replace_screen_input_owner", "may_certify_BI002"):
            with self.subTest(flag=flag):
                changed = copy.deepcopy(harness)
                changed["safety"][flag] = True
                with self.assertRaisesRegex(WorldTraversalHarnessError,
                                            "WORLD_P01_HARNESS_EFFECT_GRANTED"):
                    self.validate((0, changed))

    def test_harness_cannot_run_game_sensor_on_chat_host(self):
        harness = copy.deepcopy(self.inputs[0])
        harness["workflow"][1]["owner"] = "CURRENT_CHAT_RUNTIME"
        with self.assertRaisesRegex(WorldTraversalHarnessError, "WORLD_P01_GAME_HOST_OWNER_DRIFT"):
            self.validate((0, harness))

    def test_harness_cannot_make_live_clicks_parallel(self):
        harness = copy.deepcopy(self.inputs[0])
        harness["runtime_partition"]["shared_desktop"] = "TWO_CURSOR_WORKERS"
        with self.assertRaisesRegex(WorldTraversalHarnessError, "WORLD_P01_PHANTOM_LOCAL_ACTIVATION"):
            self.validate((0, harness))
        harness = copy.deepcopy(self.inputs[0])
        harness["runtime_partition"]["auto_dispatch"] = True
        with self.assertRaisesRegex(WorldTraversalHarnessError, "WORLD_P01_PHANTOM_LOCAL_ACTIVATION"):
            self.validate((0, harness))

    def test_harness_click_outcome_depends_on_real_sensor(self):
        harness = copy.deepcopy(self.inputs[0])
        harness["workflow"][2]["depends_on"] = ["OFFLINE_PREFLIGHT"]
        with self.assertRaisesRegex(WorldTraversalHarnessError, "WORLD_P01_DEPENDENCY_DRIFT"):
            self.validate((0, harness))

    def test_harness_cannot_publish_local_sensor_receipt(self):
        harness = copy.deepcopy(self.inputs[0])
        harness["artifacts"][1]["visibility"] = "PUBLIC_TRACKED_SANITIZED"
        with self.assertRaisesRegex(WorldTraversalHarnessError, "WORLD_P01_ARTIFACT_PRIVACY_DRIFT"):
            self.validate((0, harness))

    def test_p01_uses_canonical_platform_paths_not_new_clones(self):
        paths = copy.deepcopy(self.inputs[5])
        paths["profiles"]["windows"]["use"] = paths["profiles"]["windows"]["development"]
        with self.assertRaisesRegex(WorldTraversalHarnessError, "WORLD_P01_WORKSTATION_PROFILE_MISSING"):
            self.validate((5, paths))
        manifest = copy.deepcopy(self.inputs[0])
        manifest["workstation"]["canonical_owner"] = "docs/guess-paths.json"
        with self.assertRaisesRegex(WorldTraversalHarnessError, "WORLD_P01_WORKSTATION_OWNER_DRIFT"):
            self.validate((0, manifest))

    def test_p01_harness_map_cannot_route_to_missing_or_escaping_file(self):
        harness = copy.deepcopy(self.inputs[0])
        harness["codebase_map"].append({"surface": "UNMAPPED",
                                        "paths": ["scripts/newly-invented-untracked.py"]})
        with self.assertRaisesRegex(WorldTraversalHarnessError, "WORLD_P01_CODEBASE_OWNER_MISSING"):
            self.validate((0, harness))
        harness = copy.deepcopy(self.inputs[0])
        harness["codebase_map"].append({"surface": "UNMAPPED",
                                        "paths": ["../../saves/Slot_00000007.save"]})
        with self.assertRaisesRegex(WorldTraversalHarnessError, "HARNESS_PATH_INVALID"):
            self.validate((0, harness))

    def test_p00_root_budget_keeps_detailed_instruction_owner(self):
        contents = copy.deepcopy(self.inputs[6])
        contents["AGENTS.md"] += "New unbounded duplicated instructions must not live in root."
        with self.assertRaisesRegex(WorldTraversalHarnessError,
                                    "WORLD_P01_ROOT_GOVERNANCE_BUDGET"):
            self.validate((6, contents))

    def test_p01_local_skill_doctrine_or_ci_gate_cannot_disappear(self):
        for path, needle in (
            ("AGENTS.md", "docs/WORLD_TRAVERSAL_HARNESS.md"),
            ("docs/DOCTRINE.md", "WORLD_INTERACTION_ATTEMPT"),
            (".cursor/skills/world-traversal-p08/SKILL.md", "WORLD_OUTCOME"),
            (".github/workflows/ci.yml", "python -m scripts.check_world_traversal_harness"),
        ):
            with self.subTest(path=path):
                contents = copy.deepcopy(self.inputs[6])
                contents[path] = contents[path].replace(needle, "")
                with self.assertRaisesRegex(WorldTraversalHarnessError, "WORLD_P01_ROUTE_TEXT_DRIFT"):
                    self.validate((6, contents))


if __name__ == "__main__":
    unittest.main()
