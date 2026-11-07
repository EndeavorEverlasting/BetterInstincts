"""Offline safety/semantic regressions for ontology admission."""
from __future__ import annotations

import copy
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from scripts.check_ontology import (
    ROOT, ONTOLOGY, check_branch, changed_in_branch, first_mutation_commit,
    is_behavior_mutation, manifest_precedes, read_json, validate_consultation,
    validate_ontology, ontology_for_consultation,
)
from scripts.semantic_preflight import SemanticPreflightError, preflight


class OntologyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ontology = read_json(ROOT / ONTOLOGY)
        cls.manifest = read_json(
            ROOT / "contracts/consultations/BI-ONTOLOGY-HARNESS-20261107.v1.json"
        )

    def test_current_graph_valid(self):
        validate_ontology(self.ontology)

    def test_unknown_relation_fails_closed(self):
        bad = copy.deepcopy(self.ontology)
        bad["relations"].append({"from": "SIM", "predicate": "INVENTS", "to": "NONEXISTENT"})
        with self.assertRaisesRegex(ValueError, "ONTOLOGY_RELATION_INVALID"):
            validate_ontology(bad)

    def test_duplicate_invariant_is_invalid(self):
        bad = copy.deepcopy(self.ontology)
        bad["invariants"].append(copy.deepcopy(bad["invariants"][0]))
        with self.assertRaisesRegex(ValueError, "ONTOLOGY_INVARIANTS_INVALID"):
            validate_ontology(bad)

    def test_unknown_canonical_owner_is_invalid(self):
        bad = copy.deepcopy(self.ontology)
        bad["concepts"]["SIM"]["canonical_owner"] = "never/a/real/file.json"
        with self.assertRaisesRegex(ValueError, "CONCEPT_OWNER_MISSING"):
            validate_ontology(bad)

    def test_semantic_open_world_guardrails(self):
        self.assertIn("DOMAIN_CAPABILITY", self.ontology["concepts"])
        self.assertIn("GOAL_THREAD", self.ontology["concepts"])
        self.assertIn("OPEN", self.ontology["product_identity"]["capability_ceiling"])
        bad = copy.deepcopy(self.ontology)
        del bad["concepts"]["GOAL_THREAD"]
        with self.assertRaisesRegex(ValueError, "ONTOLOGY_SEMANTIC_CONCEPTS_MISSING"):
            validate_ontology(bad)
        bad = copy.deepcopy(self.ontology)
        bad["product_identity"]["capability_ceiling"] = "closed"
        with self.assertRaisesRegex(ValueError, "ONTOLOGY_OPEN_CAPABILITY_FREEDOM_MISSING"):
            validate_ontology(bad)

    def test_historical_receipt_keeps_original_ontology_provenance(self):
        historical = ontology_for_consultation(self.manifest, self.ontology)
        self.assertEqual(historical["revision"], 1)
        self.assertEqual(self.ontology["revision"], 2)
        validate_consultation(self.manifest, self.ontology, ["scripts/check_ontology.py"])

    def test_semantic_consultation_and_local_preflight(self):
        path = "contracts/consultations/BI-SEMANTIC-ORCHESTRATION-20261107.v1.json"
        record = read_json(ROOT / path)
        validate_consultation(record, self.ontology, ["betterinstincts/semantic_advisory.py"])
        admitted = preflight(path, operation="repo_mutation", files=("betterinstincts/semantic_advisory.py",))
        self.assertEqual(admitted["status"], "ONTOLOGY_PREFLIGHT_PASS_NOT_GAME_AUTHORITY")
        self.assertIsNone(admitted["control_permit"])
        with self.assertRaisesRegex(SemanticPreflightError, "GAME_SCOPE_NOT_CONSULTED"):
            preflight(path, operation="game_sampling", exact_game_build="1.121.361.1020")
        with self.assertRaisesRegex(ValueError, "CONSULTATION_UNMAPPED_MUTATIONS"):
            preflight(path, operation="repo_mutation", files=("betterinstincts/unmapped.py",))
        with self.assertRaisesRegex(SemanticPreflightError, "MUTATION_PATH_INVALID"):
            preflight(path, operation="repo_mutation", files=("../untrusted.py",))

    def test_blocked_and_deferred_consultations_fail_for_game_sampling(self):
        """A game preflight without file mutations must still reject a deny."""
        consult = "contracts/consultations/BI-P83-PREFLIGHT-INTENT-20261107.v1.json"
        real_read = read_json
        actual = read_json(ROOT / consult)
        for denied in ("BLOCK_UNSAFE", "DEFER_FOR_GAME_EVIDENCE",
                       "REQUIRE_ONTOLOGY_AMENDMENT"):
            candidate = copy.deepcopy(actual)
            candidate["decision"] = denied
            with self.subTest(decision=denied):
                with patch(
                    "scripts.semantic_preflight.read_json",
                    side_effect=lambda path: candidate if Path(path).name ==
                        "BI-P83-PREFLIGHT-INTENT-20261107.v1.json" else real_read(path),
                ):
                    with self.assertRaisesRegex(SemanticPreflightError, "CONSULTATION_NOT_ADMITTED"):
                        preflight(consult, operation="game_sampling",
                                  exact_game_build="1.121.361.1020")

    def test_accepted_scoped_consultation_is_not_game_authority(self):
        consult = "contracts/consultations/BI-P83-PREFLIGHT-INTENT-20261107.v1.json"
        candidate = copy.deepcopy(read_json(ROOT / consult))
        candidate["game_build_scope"] = "EXACT_GAME_BUILD:TEST_ONLY_1.2.3"
        real_read = read_json
        with patch(
            "scripts.semantic_preflight.read_json",
            side_effect=lambda path: candidate if Path(path).name ==
                "BI-P83-PREFLIGHT-INTENT-20261107.v1.json" else real_read(path),
        ):
            result = preflight(consult, operation="game_sampling",
                               exact_game_build="TEST_ONLY_1.2.3")
        self.assertEqual(result["status"], "ONTOLOGY_PREFLIGHT_PASS_NOT_GAME_AUTHORITY")
        self.assertIsNone(result["control_permit"])

    def test_preprototype_receipt_is_valid(self):
        validate_consultation(
            self.manifest, self.ontology,
            ["scripts/check_ontology.py", "tests/test_ontology_gate.py", "AGENTS.md", ".github/workflows/ci.yml"]
        )

    def test_missing_concept_and_unmapped_code_fails(self):
        bad = copy.deepcopy(self.manifest)
        bad["affected_concepts"] = ["NEVER_EXISTED"]
        with self.assertRaisesRegex(ValueError, "CONSULTATION_UNKNOWN_CONCEPT"):
            validate_consultation(bad, self.ontology, [])
        with self.assertRaisesRegex(ValueError, "CONSULTATION_UNMAPPED_MUTATIONS"):
            validate_consultation(self.manifest, self.ontology, ["betterinstincts/mutant.py"])

    def test_rejected_consultation_cannot_admit_code(self):
        bad = copy.deepcopy(self.manifest)
        bad["decision"] = "BLOCK_UNSAFE"
        with self.assertRaisesRegex(ValueError, "CONSULTATION_NOT_ADMITTED"):
            validate_consultation(bad, self.ontology, ["scripts/check_ontology.py"])

    def test_consultation_pinned_to_exact_ontology_revision(self):
        bad = copy.deepcopy(self.manifest)
        bad["ontology_blob_sha"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "CONSULTATION_ONTOLOGY_VERSION_MISMATCH"):
            validate_consultation(bad, self.ontology, [])

    def test_universal_invariants_and_offline_proof_are_required(self):
        bad = copy.deepcopy(self.manifest)
        bad["invariants_checked"] = ["BI-ONT-011"]
        with self.assertRaisesRegex(ValueError, "CONSULTATION_UNIVERSAL_INVARIANTS_MISSING"):
            validate_consultation(bad, self.ontology, [])
        bad = copy.deepcopy(self.manifest)
        bad["evidence_ceiling"] = "GAME_CERTIFIED"
        with self.assertRaisesRegex(ValueError, "CONSULTATION_OFFLINE_PROOF_INFLATED"):
            validate_consultation(bad, self.ontology, [])

    def test_protected_code_paths_and_docs_exemption(self):
        self.assertTrue(is_behavior_mutation("betterinstincts/host_stack.py"))
        self.assertTrue(is_behavior_mutation("scripts/game_host.py"))
        self.assertTrue(is_behavior_mutation("contracts/viewport-black.v1.json"))
        self.assertTrue(is_behavior_mutation(".cursor/rules/betterinstincts-compatibility.mdc"))
        self.assertTrue(is_behavior_mutation(".github/workflows/other.yml"))
        self.assertTrue(is_behavior_mutation("compatibility/catalog.v1.json"))
        self.assertFalse(is_behavior_mutation("docs/SCENE_INTELLIGENCE.md"))
        self.assertFalse(is_behavior_mutation("contracts/ontology.v1.json"))
        self.assertFalse(is_behavior_mutation("contracts/consultations/example.json"))


class ConsultationChronologyTests(unittest.TestCase):
    def git(self, root, *args):
        result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)
        if result.returncode:
            raise AssertionError(f"git failed: {result.stderr}")
        return result.stdout.strip()

    def test_consultation_precedes_mutation_not_same_commit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.git(root, "init", "-b", "main")
            self.git(root, "config", "user.name", "Ontology Test")
            self.git(root, "config", "user.email", "ontology@example.invalid")
            (root / "README.md").write_text("baseline\n")
            self.git(root, "add", "README.md")
            self.git(root, "commit", "-m", "base")
            base = self.git(root, "rev-parse", "HEAD")
            self.git(root, "checkout", "-b", "candidate")
            manifest = root / "contracts/consultations/early.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text("{}\n")
            self.git(root, "add", ".")
            self.git(root, "commit", "-m", "consult first")
            code = root / "betterinstincts/new_mutation.py"
            code.parent.mkdir(parents=True)
            code.write_text("pass\n")
            self.git(root, "add", ".")
            self.git(root, "commit", "-m", "mutate later")
            first = first_mutation_commit(base, root)
            self.assertTrue(manifest_precedes("contracts/consultations/early.json", first, root))
            self.assertEqual(changed_in_branch(base, root), ["betterinstincts/new_mutation.py"])
            self.assertFalse(manifest_precedes("betterinstincts/new_mutation.py", first, root))


    def test_late_consultation_does_not_precede_code(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.git(root, "init", "-b", "main")
            self.git(root, "config", "user.name", "Ontology Test")
            self.git(root, "config", "user.email", "ontology@example.invalid")
            (root / "README.md").write_text("base\n")
            self.git(root, "add", ".")
            self.git(root, "commit", "-m", "base")
            base = self.git(root, "rev-parse", "HEAD")
            code = root / "betterinstincts/mutation.py"
            code.parent.mkdir(parents=True)
            code.write_text("pass\n")
            self.git(root, "add", ".")
            self.git(root, "commit", "-m", "mutation before review")
            manifest = root / "contracts/consultations/late.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text("{}\n")
            self.git(root, "add", ".")
            self.git(root, "commit", "-m", "late consultation")
            first = first_mutation_commit(base, root)
            self.assertFalse(manifest_precedes("contracts/consultations/late.json", first, root))


if __name__ == "__main__":
    unittest.main()
