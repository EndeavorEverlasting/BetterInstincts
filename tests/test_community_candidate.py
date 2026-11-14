"""Adversarial, portable and privacy-negative community learning tests."""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import tempfile
import unittest

from scripts.community_candidate import (
    CandidateError, HOLDOUT_SCHEMA, _holdout, _read_json,
    build_candidate, export_to, read_candidate, research_benchmark,
    run, validate_candidate,
)


def local_model() -> dict:
    return {
        "encoder_mu": [[0.0] * 75 for _ in range(4)],
        "encoder_logvar": [[0.0] * 75 for _ in range(4)],
        "bias_mu": [0.0] * 4,
        "bias_logvar": [0.0] * 4,
        "decoder": [[0.0] * 4 for _ in range(75)],
        "decoder_bias": [-1.0] * 75,
        "trained": 30,
        "heldout": 10,
        "heldout_reconstruction_sum": 3.0,
        "heldout_baseline_sum": 10 * math.log(2),
        "context_hash": "private-world-hash-never-export",
        "samples": [{"id": "private-source-id", "x": [1] * 75}],
        "seen_bloom": "private-replay-bloom",
        "profile_id": "private-installation",
        "save_id": "private-slot",
    }


def two_cohorts() -> tuple[list[list[int]], list[list[int]]]:
    zeros = [[0] * 75 for _ in range(8)]
    mostly_zeros = [[0] * 75 for _ in range(8)]
    mostly_zeros[0][0] = 1
    return zeros, mostly_zeros


class CommunityCandidateTests(unittest.TestCase):
    def test_strips_all_profile_and_world_material_and_never_grants_effects(self):
        source = local_model()
        pristine = copy.deepcopy(source)
        candidate = build_candidate(source)
        result = validate_candidate(candidate)
        self.assertEqual(source, pristine)
        self.assertFalse(result["execute_allowed"])
        self.assertFalse(result["safe_to_promote"])
        self.assertFalse(result["self_reported_metrics_trusted"])
        serialized = json.dumps(candidate)
        for private in ("private-world-hash", "private-source-id", "private-replay-bloom",
                        "private-installation", "private-slot", "samples",
                        "context_hash", "seen_bloom", "save_id", "profile_id"):
            self.assertNotIn(private, serialized)

    def test_exports_only_once_to_explicit_local_path(self):
        candidate = build_candidate(local_model())
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "candidate.json"
            export_to(target, candidate)
            self.assertEqual(read_candidate(target), candidate)
            with self.assertRaisesRegex(CandidateError, "ALREADY_EXISTS"):
                export_to(target, candidate)
            self.assertEqual(read_candidate(target), candidate)

    def test_export_requires_separate_explicit_share_ack(self):
        with self.assertRaisesRegex(CandidateError, "EXPLICIT_WEIGHT_SHARING_ACK_REQUIRED"):
            run(["export", "--snapshot", "nonexistent.json",
                 "--out", "candidate.json"])

    def test_unreviewed_author_claims_are_never_promotion_proof(self):
        item = validate_candidate(build_candidate(local_model()))
        self.assertEqual(item["state"], "STRUCTURAL_PASS_INDEPENDENT_REVIEW_REQUIRED")
        self.assertFalse(item["safe_to_promote"])

    def test_tampered_or_unbounded_weight_and_unauthorized_keys_block(self):
        valid = build_candidate(local_model())
        for manipulation in ("tamper", "oversized", "nan", "bool", "shape", "shell"):
            candidate = copy.deepcopy(valid)
            if manipulation == "tamper":
                candidate["weights"]["decoder_bias"][0] = 0.5
            elif manipulation == "oversized":
                candidate["weights"]["decoder_bias"][0] = 400
            elif manipulation == "nan":
                candidate["weights"]["decoder_bias"][0] = float("nan")
            elif manipulation == "bool":
                candidate["weights"]["decoder_bias"][0] = True
            elif manipulation == "shape":
                candidate["weights"]["encoder_mu"] = [[0.0] * 74 for _ in range(4)]
            else:
                candidate["__import__"] = "os.system('bad')"
            with self.subTest(manipulation=manipulation):
                with self.assertRaises(CandidateError):
                    validate_candidate(candidate)

    def test_undertrained_or_lied_baseline_blocks(self):
        for field, value in (("trained", 0), ("heldout", 0),
                             ("mean_heldout_loss", 0.693),
                             ("uniform_baseline", 0.1)):
            item = build_candidate(local_model())
            item["reported_training"][field] = value
            with self.subTest(field=field), self.assertRaises(CandidateError):
                validate_candidate(item)

    def test_json_parser_rejects_duplicate_keys_nonfinite_and_oversize(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidate.json"
            for data in ('{"schema":"a","schema":"b"}',
                         '{"tensor_sha256":NaN}', 'x' * 40001):
                path.write_text(data, encoding="utf-8")
                with self.assertRaises(CandidateError):
                    _read_json(path, 40_000)

    def test_structural_pass_does_not_replace_two_cohort_review(self):
        candidate = build_candidate(local_model())
        report = research_benchmark(candidate, two_cohorts())
        self.assertEqual(report["state"],
                         "RESEARCH_BENCHMARK_PASS_HUMAN_REVIEW_REQUIRED")
        self.assertTrue(all(item["pass"] for item in report["cohorts"]))
        self.assertFalse(report["independent_provenance_attested"])
        self.assertFalse(report["safe_to_promote"])
        self.assertTrue(report["privacy_review_required"])
        with self.assertRaisesRegex(CandidateError, "IDENTICAL_HOLDOUT_COHORTS"):
            research_benchmark(candidate, (two_cohorts()[0], two_cohorts()[0]))

    def test_adversarial_cross_host_dataset_fails(self):
        candidate = build_candidate(local_model())
        bad = [[1] * 75 for _ in range(8)]
        report = research_benchmark(candidate, (two_cohorts()[0], bad))
        self.assertEqual(report["state"], "RESEARCH_BENCHMARK_FAIL")
        self.assertFalse(report["cohorts"][1]["pass"])
        self.assertFalse(report["safe_to_promote"])

    def test_reviewer_holdout_schema_is_only_binary_semantic_vectors(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cohort.json"
            data = {"schema": HOLDOUT_SCHEMA, "vectors": two_cohorts()[0]}
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(_holdout(path), two_cohorts()[0])
            for addition in ({"save_name": "somebody"}, {"payload": "__import__"}):
                changed = dict(data, **addition)
                path.write_text(json.dumps(changed), encoding="utf-8")
                with self.assertRaises(CandidateError):
                    _holdout(path)


if __name__ == "__main__":
    unittest.main()
