"""Past experience is reused, but never replayed as current game proof."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from betterinstincts.experience_recall import (
    EVENT_SCHEMA, ExperienceRecallError, empty_memory, load_memory,
    recall, remember, record_new,
)


def context(*, profile="vanilla_lab_20261114", choice="yes_0",
            build="1.121.361.1020"):
    return {
        "domain": "preference_offer",
        "game_build": build,
        "installation_profile": profile,
        "mechanic_id": "ea_265965",
        "choice_id": choice,
    }


def event(*, source="p08_yes_rollback_20261114", result="actor_trait_258767_buff_263631",
          ctx=None):
    return {
        "schema": EVENT_SCHEMA, "context": ctx or context(),
        "result": result, "evidence_level": "OPERATOR_REPORTED_LIVE",
        "evidence_ref": source, "observed_at_ms": 1794697200000,
    }


class ExperienceRecallTests(unittest.TestCase):
    def test_new_then_prior_result_is_recalled_without_current_completion(self):
        memory, result = remember(empty_memory(), event())
        self.assertTrue(result["recorded"])
        self.assertEqual(result["state"], "NEW_EXPERIENCE_RECORDED")
        found = recall(memory, context())
        self.assertEqual(found["state"], "PAST_EXPERIENCE_RECALLED")
        self.assertEqual(found["past_result"], "actor_trait_258767_buff_263631")
        self.assertFalse(found["historical_research_needed"])
        self.assertFalse(found["execute_allowed"])
        self.assertFalse(found["current_dialog_completed"])
        self.assertFalse(found["current_outcome_proven"])
        self.assertTrue(found["current_dialog_requires_fresh_admission"])
        self.assertEqual(found["past_evidence"]["level"], "OPERATOR_REPORTED_LIVE")

    def test_second_encounter_or_different_capture_is_not_a_new_experience(self):
        first, _ = remember(empty_memory(), event())
        duplicate, result = remember(first, event(source="separate_capture_from_same_mechanic"))
        self.assertFalse(result["recorded"])
        self.assertEqual(result["state"], "ALREADY_KNOWN")
        self.assertEqual(duplicate, first)
        self.assertEqual(len(duplicate["records"]), 1)

    def test_no_outcome_is_distinct_not_no_op(self):
        yes, _ = remember(empty_memory(), event())
        no, new = remember(yes, event(
            ctx=context(choice="no_1"), result="actor_no_opinion_marker_266814",
            source="p08_no_20261114"))
        self.assertTrue(new["recorded"])
        self.assertEqual(len(no["records"]), 2)
        self.assertEqual(recall(no, context(choice="no_1"))["past_result"],
                         "actor_no_opinion_marker_266814")

    def test_exact_mod_profile_and_game_version_prevent_false_reuse(self):
        first, _ = remember(empty_memory(), event())
        for variant in (
            context(profile="modded_lab_20261114"),
            context(build="1.122.0.0"),
            context(choice="no_1"),
        ):
            with self.subTest(context=variant):
                unknown = recall(first, variant)
                self.assertEqual(unknown["state"], "NEW_EXPERIENCE")
                self.assertIsNone(unknown["past_result"])
                self.assertTrue(unknown["historical_research_needed"])

    def test_conflict_preserves_last_known_good_and_needs_review(self):
        first, _ = remember(empty_memory(), event())
        before = copy.deepcopy(first)
        held, result = remember(first, event(result="different_effect", source="new_proof"))
        self.assertEqual(result["state"], "CONFLICT_REVIEW_REQUIRED")
        self.assertFalse(result["recorded"])
        self.assertEqual(held, before)
        self.assertEqual(first, before)

    def test_invalid_or_unsafe_fields_do_not_enter_memory(self):
        invalid = (
            {**event(), "sim_name": "private"},
            {**event(), "result": "raw personal text with spaces"},
            {**event(), "evidence_level": "GAME_CERTIFIED"},
            {**event(), "observed_at_ms": True},
            {**event(), "context": {**context(), "sim_id": "12345"}},
            {**event(), "context": context(build="unknown")},
        )
        for candidate in invalid:
            with self.subTest(candidate=candidate), self.assertRaises(ExperienceRecallError):
                remember(empty_memory(), candidate)

    def test_persistence_writes_on_new_only_and_survives_new_call(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            path = root / "dist" / "experience-recall" / "experiences.json"
            self.assertFalse(path.exists())
            out = record_new(event(), root=root)
            self.assertEqual(out["state"], "NEW_EXPERIENCE_RECORDED")
            self.assertTrue(path.is_file())
            raw = path.read_bytes()
            before = path.stat().st_mtime_ns
            known = record_new(event(source="another_capture"), root=root)
            self.assertEqual(known["state"], "ALREADY_KNOWN")
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(path.stat().st_mtime_ns, before)
            self.assertEqual(recall(load_memory(root=root), context())["state"],
                             "PAST_EXPERIENCE_RECALLED")
            conflict = record_new(event(result="wrong_new_result"), root=root)
            self.assertEqual(conflict["state"], "CONFLICT_REVIEW_REQUIRED")
            self.assertEqual(path.read_bytes(), raw)

    def test_interleaved_distinct_writers_keep_both_new_experiences(self):
        # Simulate a stale initial read: another agent committed NO before
        # this writer obtained the lock. The under-lock read sees NO.
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            no = event(ctx=context(choice="no_1"), result="actor_no_opinion_marker_266814",
                       source="earlier_no_trial")
            record_new(no, root=root)
            with patch("betterinstincts.experience_recall.load_memory",
                       side_effect=[empty_memory(), load_memory(root=root)]):
                result = record_new(event(), root=root)
            self.assertEqual(result["state"], "NEW_EXPERIENCE_RECORDED")
            saved = load_memory(root=root)
            self.assertEqual(len(saved["records"]), 2)
            self.assertEqual(recall(saved, context(choice="no_1"))["past_result"],
                             "actor_no_opinion_marker_266814")
            self.assertEqual(recall(saved, context())["past_result"],
                             "actor_trait_258767_buff_263631")

    def test_repeated_known_experience_does_not_take_or_erase_another_lock(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            record_new(event(), root=root)
            store = root / "dist" / "experience-recall" / "experiences.json"
            lock = store.with_name("experiences.writer.lock")
            lock.write_text("other writer owns this lock")
            before = store.read_bytes(), store.stat().st_mtime_ns
            result = record_new(event(source="new_capture"), root=root)
            self.assertEqual(result["state"], "ALREADY_KNOWN")
            self.assertEqual((store.read_bytes(), store.stat().st_mtime_ns), before)
            self.assertEqual(lock.read_text(), "other writer owns this lock")

    def test_busy_writer_fails_without_losing_existing_experience(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            record_new(event(), root=root)
            store = root / "dist" / "experience-recall" / "experiences.json"
            lock = store.with_name("experiences.writer.lock")
            lock.write_text("unrelated agent still writing")
            before = store.read_bytes()
            with self.assertRaisesRegex(ExperienceRecallError, "EXPERIENCE_WRITER_BUSY"):
                record_new(event(ctx=context(choice="no_1"),
                                 result="actor_no_opinion_marker_266814",
                                 source="new_distinct_no"), root=root)
            self.assertEqual(store.read_bytes(), before)
            self.assertTrue(lock.exists())
            self.assertEqual(len(load_memory(root=root)["records"]), 1)

    def test_second_writer_recheck_deduplicates_without_rewrite(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            record_new(event(), root=root)
            store = root / "dist" / "experience-recall" / "experiences.json"
            before = store.read_bytes(), store.stat().st_mtime_ns
            # Initial read was stale; new record appeared before lock.
            with patch("betterinstincts.experience_recall.load_memory",
                       side_effect=[empty_memory(), load_memory(root=root)]):
                result = record_new(event(source="later_same_fact"), root=root)
            self.assertEqual(result["state"], "ALREADY_KNOWN")
            self.assertEqual((store.read_bytes(), store.stat().st_mtime_ns), before)
            self.assertFalse(store.with_name("experiences.writer.lock").exists())

    def test_symlink_and_tampered_stored_context_fail_closed(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            record_new(event(), root=root)
            path = root / "dist" / "experience-recall" / "experiences.json"
            data = json.loads(path.read_text())
            key = next(iter(data["records"]))
            data["records"][key]["context"]["game_build"] = "1.122.0.0"
            path.write_text(json.dumps(data))
            with self.assertRaises(ExperienceRecallError):
                load_memory(root=root)


if __name__ == "__main__":
    unittest.main()
