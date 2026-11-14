"""Mechanics registry covers real source owners and keeps unresolved gaps visible."""
from __future__ import annotations

import copy
import unittest

from betterinstincts.mechanics_registry import (
    MechanicsRegistryError, load_registry, validate_registry, review_outcomes,
)
from scripts.mechanics_registry import run


class MechanicsRegistryTests(unittest.TestCase):
    def test_coverage_is_source_owned_and_never_claims_native_effect(self):
        data = load_registry()
        report = validate_registry(data)
        self.assertEqual(report["mechanics_total"], 39)
        self.assertEqual(report["source_present"], 32)
        self.assertEqual(report["visible_gaps"], 7)
        self.assertEqual(report["live_game_certified"], 0)
        self.assertIn("household-yield-accounting", report["gaps"])
        self.assertIn("pet-care", report["gaps"])
        portrait = next(row for row in data["mechanics"]
                        if row["id"] == "household-portrait-attention-rotation")
        self.assertEqual(portrait["evidence_state"], "SOURCE_PRESENT")
        self.assertEqual(portrait["owner"], "betterinstincts/household_economy.py")
        self.assertFalse(portrait["game_effect_certified"])
        work_tone = next(row for row in data["mechanics"]
                         if row["id"] == "career-work-hard-tone")
        self.assertEqual(work_tone["evidence_state"], "SOURCE_PRESENT")
        self.assertEqual(work_tone["owner"], "betterinstincts/career_service.py")
        self.assertEqual(work_tone["dependencies"],
                         ["career-progress", "household-portrait-attention-rotation"])
        self.assertFalse(work_tone["game_effect_certified"])
        self.assertEqual(run(["status"])["mechanics_total"], 39)

    def test_duplicate_unknown_owner_and_game_claim_fail(self):
        base = load_registry()
        for mutation in ("duplicate", "owner", "effect", "deps", "cycle", "gap"):
            rows = copy.deepcopy(base)
            if mutation == "duplicate":
                rows["mechanics"][1]["id"] = rows["mechanics"][0]["id"]
            elif mutation == "owner":
                rows["mechanics"][0]["owner"] = "betterinstincts/no_such_owner.py"
            elif mutation == "effect":
                rows["mechanics"][0]["game_effect_certified"] = True
            elif mutation == "deps":
                rows["mechanics"][0]["dependencies"] = ["unsupported-mechanic"]
            elif mutation == "cycle":
                rows["mechanics"][0]["dependencies"] = ["need-bladder"]
                rows["mechanics"][1]["dependencies"] = ["need-hunger"]
            else:
                next(row for row in rows["mechanics"] if row["id"] == "pet-care")["owner"] = "betterinstincts/priority.py"
            with self.subTest(mutation=mutation), self.assertRaises(MechanicsRegistryError):
                validate_registry(rows)

    def test_failed_mechanics_replanned_not_auto_promoted_or_omitted(self):
        data = load_registry()
        snapshot = copy.deepcopy(data)
        out = review_outcomes(data, [
            {"mechanic_id": "gardening", "outcome": "FAILED",
             "proof_ref": "capture:failed-gardening", "capture_ref": "capture:current",
             "player_interrupted": False},
            {"mechanic_id": "pet-care", "outcome": "UNAVAILABLE",
             "proof_ref": "capture:missing-pets", "capture_ref": "capture:current",
             "player_interrupted": False},
        ], capture_ref="capture:current")
        self.assertEqual(len(out["replan_proposals"]), 2)
        self.assertEqual(out["replan_proposals"][0]["finding"],
                         "REPLAN_FROM_FAILURE_NOT_BLIND_RETRY")
        self.assertEqual(out["replan_proposals"][1]["finding"], "MISSING_MECHANIC_OWNER")
        self.assertEqual(data, snapshot)
        self.assertFalse(out["mutation_allowed"])
        self.assertFalse(out["game_action_allowed"])

    def test_replay_stale_capture_and_unknown_mechanic_rejected(self):
        data = load_registry()
        event = {"mechanic_id": "gardening", "outcome": "FAILED",
                 "proof_ref": "capture:proof001", "capture_ref": "capture:current",
                 "player_interrupted": False}
        for pair in ([event,event], [{**event,"capture_ref":"capture:prior"}],
                     [{**event,"mechanic_id":"fictional-task"}]):
            with self.assertRaises(MechanicsRegistryError):
                review_outcomes(data, pair, capture_ref="capture:current")

    def test_player_interruption_never_updates_coverage_or_forces_replan(self):
        data = load_registry()
        receipt = review_outcomes(data, [{
            "mechanic_id": "gardening", "outcome": "FAILED",
            "proof_ref": "capture:interrupted", "capture_ref": "capture:current",
            "player_interrupted": True,
        }], capture_ref="capture:current")
        self.assertEqual(receipt["replan_proposals"], [])


if __name__ == "__main__":
    unittest.main()
