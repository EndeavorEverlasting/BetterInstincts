"""Safety/continuity regressions for certification-first Sims save handoff."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from betterinstincts.save_policy import MANIFEST_SCHEMA
from scripts.launch_save_route import (
    CERTIFICATION_ID, CONTEXT_SCHEMA, household_handoff, load_context, route_launch,
    route_local_context,
)
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


def context(status: str = "PENDING") -> dict:
    return {
        "schema": CONTEXT_SCHEMA,
        "certification_id": CERTIFICATION_ID,
        "run_id": RUN,
        "game_version": PATCH,
        "status": status,
    }


def register(*records: dict) -> dict:
    return {"schema": MANIFEST_SCHEMA, "entries": list(records)}


def completed() -> dict:
    item = context("REVIEWED_COMPLETE")
    item["completion_review"] = {
        "reviewer_verified": True,
        "game_version": PATCH,
        "current_offer_outcome_ref": "capture:current-dialog-outcome",
        "native_effect_ref": "capture:native-effect-ack",
        "rollback_ref": "capture:hash-verified-rollback",
        "review_ref": "capture:independent-review",
    }
    return item


class CertificationFirstRouteTests(unittest.TestCase):
    def test_single_household_resolves_and_ambiguous_or_stale_choice_waits(self):
        a, b = "household:a", "household:b"
        self.assertEqual(household_handoff((a,), None)["household_id"], a)
        self.assertEqual(household_handoff((a, b), None)["state"], "HOUSEHOLD_CHOICE_REQUIRED")
        self.assertEqual(household_handoff((a, b), b)["household_id"], b)
        self.assertEqual(household_handoff((a,), b)["state"], "HOUSEHOLD_CHOICE_REQUIRED")

    def test_reviewed_successor_ranks_only_current_household_disposable_saves(self):
        a, b = "household:a", "household:b"
        item = completed()
        item["household_id"] = item["completion_review"]["household_id"] = a
        successor = "bi002-hunger"
        def row(number, day, household, **extra):
            return {**lab(number, day), "authorized_run_id": successor, "household_id": household,
                    "household_binding_confirmed": True, **extra}

        saves = register(row(1, 1, b), row(2, 2, a, classification="USER_PROTECTED"),
                         row(3, 3, a), row(4, 4, a))
        args = dict(available_households=(a, b), preferred_household=a,
                    observed_game_version=PATCH, successor_run_id=successor)
        routed = route_launch(item, lab_registry=saves, **args)
        self.assertEqual(routed["candidate_save_id"], "slot:lab-003")
        self.assertIsNone(routed["selected_save_id"])
        self.assertIsNone(routed["control_permit"])
        self.assertEqual(route_launch(item, lab_registry=saves, **{**args, "preferred_household": b})
                         ["state"], "HOLD_CERTIFICATION_HOUSEHOLD")
        self.assertEqual(route_launch(item, lab_registry=saves, **{**args, "successor_run_id": RUN})
                         ["state"], "HOLD_SUCCESSOR_RUN")
        saves["entries"].append(row(5, 1, a, household_binding_confirmed=False))
        self.assertEqual(route_launch(item, lab_registry=saves, **args)["state"],
                         "HOLD_STANDARDIZED_LAB_RANKING")

    def test_existing_game_keeps_current_dialog_even_when_oldest_lab_exists(self):
        result = route_launch(
            context(), game_running_observed=True,
            lab_registry=register(lab(1, 1), lab(2, 14)),
        )
        self.assertEqual(result["state"], "PRESERVE_RUNNING_CERTIFICATION_SESSION")
        self.assertIsNone(result["selected_save_id"])
        self.assertNotIn("candidate_save_id", result)
        self.assertFalse(result["automatic_input"])

    def test_pending_without_running_game_requires_explicit_pin(self):
        result = route_launch(context(), lab_registry=register(lab(1, 1)))
        self.assertEqual(result["state"], "HOLD_CERTIFICATION_PIN")
        self.assertNotIn("lab_advisory", result)

    def test_pinned_lab_is_only_advised_not_loaded(self):
        continuation = lab(2, 14, classification="LAB_CONTINUATION")
        item = context()
        item["pinned_save"] = {
            key: continuation[key] for key in ("save_id", "alias", "capture_ref")
        }
        result = route_launch(item, lab_registry=register(lab(1, 1), continuation))
        self.assertEqual(result["state"], "CERTIFICATION_PINNED_LAB_SAVE_ADVISORY")
        self.assertEqual(result["candidate_save_id"], continuation["save_id"])
        self.assertEqual(result["candidate_classification"], "LAB_CONTINUATION")
        self.assertIsNone(result["selected_save_id"])
        self.assertIsNone(result["control_permit"])

    def test_pinned_unknown_or_unbound_save_cannot_be_promoted_by_old_age(self):
        item = context()
        old = lab(1, 1)
        item["pinned_save"] = {
            key: old[key] for key in ("save_id", "alias", "capture_ref")
        }
        for changed in (
            {"classification": "USER_PROTECTED", "origin": "USER_CREATED"},
            {"authorized_run_id": "another-run"},
            {"capture_ref": "capture:wrong"},
        ):
            with self.subTest(changed=changed):
                record = {**old, **changed}
                result = route_launch(item, lab_registry=register(record))
                self.assertEqual(result["state"], "HOLD_CERTIFICATION_PIN")
                self.assertNotIn("candidate_save_id", result)

    def test_historical_yes_no_data_does_not_certify_current_dialog(self):
        item = context()
        item["historical_yes_no"] = {"yes": "observed", "no": "observed"}
        self.assertEqual(route_launch(item, lab_registry=register(lab(1, 1)))["state"],
                         "HOLD_CERTIFICATION_PIN")
        item["status"] = "REVIEWED_COMPLETE"
        self.assertEqual(route_launch(item, lab_registry=register(lab(1, 1)))["state"],
                         "HOLD_CERTIFICATION_REVIEW")

    def test_complete_claim_requires_four_distinct_bound_review_captures(self):
        item = completed()
        for change in (
            {"reviewer_verified": False},
            {"rollback_ref": None},
            {"rollback_ref": "capture:current-dialog-outcome"},
            {"game_version": "1.120.1.1"},
        ):
            with self.subTest(change=change):
                bad = copy.deepcopy(item)
                bad["completion_review"].update(change)
                self.assertEqual(
                    route_launch(bad, lab_registry=register(lab(1, 1)))["state"],
                    "HOLD_CERTIFICATION_REVIEW",
                )

    def test_complete_and_reviewed_switches_to_oldest_eligible_lab_only(self):
        newest, oldest, protected = lab(3, 14), lab(1, 2), lab(2, 1)
        protected.update(classification="USER_PROTECTED", origin="USER_CREATED")
        result = route_launch(
            completed(), lab_registry=register(newest, oldest, protected),
        )
        self.assertEqual(result["state"], "STANDARDIZED_OLDEST_DISPOSABLE_ADVISORY")
        ranked = result["lab_advisory"]["ranked_candidates"]
        self.assertEqual([x["save_id"] for x in ranked],
                         [oldest["save_id"], newest["save_id"]])
        self.assertIsNone(result["selected_save_id"])
        self.assertFalse(result["game_effect"])

    def test_missing_age_or_tied_timestamps_blocks_standardized_ranking(self):
        not_dated = lab(1, 1)
        not_dated.pop("lab_created_at_utc")
        for records in (
            [not_dated, lab(2, 14)],
            [lab(1, 1), lab(2, 1)],
        ):
            with self.subTest(records=records):
                self.assertEqual(
                    route_launch(completed(), lab_registry=register(*records))["state"],
                    "HOLD_STANDARDIZED_LAB_RANKING",
                )

    def test_completion_without_registry_never_guesses_a_save(self):
        result = route_launch(completed())
        self.assertEqual(result["state"], "HOLD_STANDARDIZED_LAB_REGISTRY")
        self.assertIsNone(result["selected_save_id"])

    def test_build_run_status_and_process_ambiguity_deny(self):
        for change in (
            {"game_version": "1.invalid"},
            {"run_id": "not a run"},
            {"status": "COMPLETED_FROM_HISTORICAL_DATA"},
            {"certification_id": "UNKNOWN"},
        ):
            with self.subTest(change=change):
                item = {**context(), **change}
                self.assertEqual(route_launch(item)["state"], "HOLD_CERTIFICATION_CONTEXT")
        self.assertEqual(
            route_launch(context(), observed_game_version="1.120.1.1")["state"],
            "HOLD_CERTIFICATION_CONTEXT",
        )
        self.assertEqual(
            route_launch(context(), game_running_observed="yes")["state"],
            "HOLD_CERTIFICATION_CONTEXT",
        )

    def test_private_context_is_read_only_and_symlinks_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            memo = folder / "active.json"
            memo.write_text(json.dumps(context()), encoding="utf-8")
            original = memo.read_bytes()
            result = route_local_context(path=memo, game_running_observed=True)
            self.assertEqual(result["state"], "PRESERVE_RUNNING_CERTIFICATION_SESSION")
            self.assertEqual(memo.read_bytes(), original)
            symlink = folder / "alias.json"
            try:
                symlink.symlink_to(memo)
            except OSError:
                return
            self.assertEqual(route_local_context(path=symlink)["state"],
                             "HOLD_CERTIFICATION_CONTEXT")

    def test_every_route_never_grants_a_game_or_save_effect(self):
        cases = [
            route_launch(context(), game_running_observed=True),
            route_launch(context()),
            route_launch(completed()),
            route_launch(completed(), lab_registry=register(lab(1, 1))),
            route_launch({"schema": "wrong"}),
        ]
        for result in cases:
            with self.subTest(state=result["state"]):
                self.assertIsNone(result["selected_save_id"])
                self.assertIsNone(result["control_permit"])
                self.assertFalse(result["automatic_input"])
                self.assertFalse(result["save_file_access"])
                self.assertFalse(result["game_effect"])


if __name__ == "__main__":
    unittest.main()
