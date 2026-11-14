"""Adversarial fixtures for P00/P01 oldest-first save candidate advisory."""
import copy
import unittest

from betterinstincts.save_policy import MANIFEST_SCHEMA, SavePolicyError, decide
from scripts.save_candidate_priority import rank_lab_candidates
from scripts.check_save_candidate_priority import check

RUN = "lab-review"
PATCH = "1.121.361.1020"


def lab(number: int, day: int, *, classification: str = "LAB_DISPOSABLE") -> dict:
    return {
        "save_id": f"slot:lab-{number:03d}",
        "alias": (f"BI_TMP_TRIAL_{number:03d}" if classification == "LAB_DISPOSABLE"
                  else f"BI_CONT_TRIAL_{number:03d}"),
        "classification": classification,
        "origin": "LAB_CREATED",
        "lab_origin_confirmed": True,
        "creation_run_id": "lab-creation",
        "authorized_run_id": RUN,
        "capture_ref": f"capture:lab-{number:03d}",
        "game_version": PATCH,
        "operator_confirmed": True,
        "lab_created_at_utc": f"2026-11-{day:02d}T10:00:00Z",
        "lab_creation_time_confirmed": True,
    }


def rank(entries: list[dict]) -> dict:
    return rank_lab_candidates(
        {"schema": MANIFEST_SCHEMA, "entries": entries},
        run_id=RUN, game_version=PATCH,
    )


class SaveCandidatePriorityTests(unittest.TestCase):
    def test_oldest_first_even_when_newest_listed_first(self):
        result = rank([lab(3, 14), lab(1, 2), lab(2, 8)])
        self.assertEqual(result["state"], "PRIORITY_ADVISORY_ONLY")
        self.assertEqual([x["save_id"] for x in result["ranked_candidates"]],
                         ["slot:lab-001", "slot:lab-002", "slot:lab-003"])
        self.assertEqual([x["priority"] for x in result["ranked_candidates"]], [1, 2, 3])
        self.assertIsNone(result["selected_save_id"])
        self.assertFalse(result["automatic_input"])
        self.assertFalse(result["save_file_access"])
        self.assertIsNone(result["control_permit"])

    def test_older_protected_and_lab_continuation_cannot_be_promoted(self):
        protected = lab(10, 1)
        protected.update(classification="USER_PROTECTED", origin="USER_CREATED")
        unknown = lab(11, 1)
        unknown.update(classification="UNKNOWN_PROTECTED", origin="UNKNOWN")
        result = rank([protected, unknown, lab(4, 1, classification="LAB_CONTINUATION"),
                       lab(1, 13), lab(2, 14)])
        self.assertEqual([x["save_id"] for x in result["ranked_candidates"]],
                         ["slot:lab-001", "slot:lab-002"])
        self.assertEqual(result["protected_or_continuation_excluded"], 3)

    def test_unproven_origin_or_current_run_abstains_instead_of_favoring_newer(self):
        for key, value in (("lab_origin_confirmed", False),
                           ("operator_confirmed", False),
                           ("origin", "USER_CREATED"),
                           ("authorized_run_id", "stale-run"),
                           ("game_version", "1.120.0.0"),
                           ("capture_ref", "not-a-capture")):
            with self.subTest(key=key):
                bad = lab(1, 2)
                bad[key] = value
                result = rank([lab(2, 14), bad])
                self.assertEqual(result["state"], "ABSTAIN_UNRANKABLE_LAB_CANDIDATE")
                self.assertEqual(result["ranked_candidates"], [])

    def test_missing_invalid_or_unconfirmed_creation_date_abstains(self):
        for key, value in (("lab_created_at_utc", None),
                           ("lab_created_at_utc", "2026-11-12T10:00:00-05:00"),
                           ("lab_created_at_utc", "2026-11-99T10:00:00Z"),
                           ("lab_creation_time_confirmed", False)):
            with self.subTest(key=key):
                untrusted = lab(2, 2)
                untrusted[key] = value
                self.assertEqual(rank([lab(1, 14), untrusted])["state"],
                                 "ABSTAIN_UNRANKABLE_LAB_CANDIDATE")

    def test_tied_creation_time_is_ambiguous(self):
        self.assertEqual(rank([lab(1, 10), lab(2, 10)])["state"],
                         "ABSTAIN_AMBIGUOUS_CREATION_ORDER")

    def test_duplicate_slot_or_alias_abstains(self):
        duplicate = lab(2, 12)
        duplicate["alias"] = lab(1, 2)["alias"]
        self.assertEqual(rank([lab(1, 2), duplicate])["state"],
                         "ABSTAIN_UNRANKABLE_LAB_CANDIDATE")

    def test_no_lab_candidate_never_auto_loads_user_save(self):
        protected = lab(1, 1)
        protected.update(classification="USER_PROTECTED", origin="USER_CREATED")
        result = rank([protected])
        self.assertEqual(result["state"], "NO_ELIGIBLE_LAB_DISPOSABLE_CANDIDATE")
        self.assertIsNone(result["selected_save_id"])

    def test_priority_does_not_change_existing_delete_resume_auto_select_denials(self):
        source = lab(1, 2)
        registry = {"schema": MANIFEST_SCHEMA, "entries": [source]}
        for intent in ("DELETE", "OVERWRITE", "RESUME", "AUTO_SELECT", "MIGRATE"):
            with self.subTest(intent=intent):
                decision = decide(registry, save_id=source["save_id"],
                                  alias=source["alias"], run_id=RUN,
                                  game_version=PATCH, capture_ref=source["capture_ref"],
                                  intent=intent)
                self.assertEqual(decision["state"], "DENIED")

    def test_malformed_registry_or_run_is_rejected(self):
        with self.assertRaises(SavePolicyError):
            rank_lab_candidates({"schema": "wrong", "entries": []}, run_id=RUN, game_version=PATCH)
        with self.assertRaises(SavePolicyError):
            rank_lab_candidates({"schema": MANIFEST_SCHEMA, "entries": []},
                                run_id="invalid run", game_version=PATCH)

    def test_harness_completeness_and_policy_canary(self):
        self.assertEqual(check(), "SAVE_PRIORITY_P00_P01_HARNESS_PASS_ADVISORY_ONLY")


if __name__ == "__main__":
    unittest.main()
