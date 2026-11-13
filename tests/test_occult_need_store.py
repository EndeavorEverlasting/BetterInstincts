"""Reviewed novel action admission and guarded opt-in durable local snapshots."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from betterinstincts.occult_needs import (
    OccultNeedsError, learn, learn_candidate, new_model, recommend,
)
from betterinstincts.occult_need_store import (
    LocalLearningStoreError, load_local_model, save_local_model,
)

PATCH = "1.121.361.1020"
SIX = {"bladder": .8, "hunger": .1, "energy": .8,
       "hygiene": .8, "fun": .8, "social": .8}


def model():
    return new_model(profile="human", game_version=PATCH, platform="windows")


def observed(ref: str, *, action: str = "EAT_SNACK",
             outcome: str = "helpful", before: float = .1, after: float = .5):
    return {
        "observation_ref": ref, "need": "hunger", "action": action,
        "outcome": outcome, "operator_reviewed": True, "opt_in": True,
        "scene_verified": True, "menu_observed": True, "before": before,
        "after": after, "game_version": PATCH, "platform": "windows",
    }


def advise(stored, *, available=("EAT_SNACK",)):
    return recommend("human", SIX, list(available), model=stored,
                     game_version=PATCH, platform="windows")


class LearnedNewActionTests(unittest.TestCase):
    def test_new_semantic_action_starts_untrusted(self):
        first = learn_candidate(model(), observed("capture:novel:0001"))
        self.assertEqual(advise(first)["state"], "ABSTAIN")
        self.assertEqual(len(first["candidate_events"]), 1)

    def test_three_reviewed_outcomes_promote_only_current_menu_action(self):
        candidate = model()
        for n in range(3):
            candidate = learn_candidate(candidate, observed(f"capture:novel:{n:04d}"))
        self.assertEqual(advise(candidate)["suggested_action"], "EAT_SNACK")
        self.assertEqual(advise(candidate)["source"], "REVIEWED_OUTCOMES")
        self.assertFalse(advise(candidate)["execute"])
        self.assertEqual(advise(candidate, available=())["state"], "ABSTAIN")

    def test_harmful_or_mixed_records_do_not_promote(self):
        candidate = model()
        for n in range(2):
            candidate = learn_candidate(candidate, observed(f"capture:good:{n:04d}"))
        candidate = learn_candidate(candidate, observed(
            "capture:bad:0001", outcome="harmful", after=.05))
        self.assertEqual(advise(candidate)["state"], "ABSTAIN")

    def test_no_learning_without_observed_menu_review_or_opt_in(self):
        for field in ("menu_observed", "operator_reviewed", "opt_in", "scene_verified"):
            raw = observed("capture:reject:0001")
            raw[field] = False
            with self.subTest(field=field), self.assertRaises(OccultNeedsError):
                learn_candidate(model(), raw)

    def test_bad_action_name_unknown_motive_and_patch_rejected(self):
        for action in ("CLICK!NOW", "x", "QUICK_MEAL"):
            with self.subTest(action=action), self.assertRaises(OccultNeedsError):
                learn_candidate(model(), observed("capture:reject:0001", action=action))
        wrong = observed("capture:reject:0001")
        wrong["need"] = "thirst"
        with self.assertRaises(OccultNeedsError):
            learn_candidate(model(), wrong)
        wrong = observed("capture:reject:0001")
        wrong["game_version"] = "1.121.361.1019"
        with self.assertRaises(OccultNeedsError):
            learn_candidate(model(), wrong)

    def test_cross_channel_evidence_replay(self):
        m = learn_candidate(model(), observed("capture:cross:0001"))
        known = observed("capture:cross:0001", action="QUICK_MEAL")
        del known["menu_observed"]
        with self.assertRaisesRegex(OccultNeedsError, "OBSERVATION_REPLAY"):
            learn(m, known)
        with self.assertRaisesRegex(OccultNeedsError, "OBSERVATION_REPLAY"):
            learn_candidate(m, observed("capture:cross:0001"))

    def test_old_snapshot_without_candidate_field_remains_valid(self):
        old = model()
        old.pop("candidate_events")
        updated = learn_candidate(old, observed("capture:legacy:0001"))
        self.assertIn("candidate_events", updated)
        self.assertNotIn("candidate_events", old)

    def test_corrupted_candidate_history_denied(self):
        m = learn_candidate(model(), observed("capture:copy:0001"))
        forged = copy.deepcopy(m)
        forged["candidate_events"].append(dict(forged["candidate_events"][0]))
        with self.assertRaises(OccultNeedsError):
            advise(forged)

    def test_player_first_even_after_candidate_promotion(self):
        m = model()
        for n in range(3):
            m = learn_candidate(m, observed(f"capture:player:{n:04d}"))
        out = recommend("human", SIX, ["EAT_SNACK"], model=m,
                        game_version=PATCH, platform="windows", player_active=True)
        self.assertEqual(out["reason"], "PLAYER_FIRST_OR_BUSY")


class LocalStoreTests(unittest.TestCase):
    def test_only_explicit_selected_directory_can_create(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            m = model()
            with self.assertRaisesRegex(LocalLearningStoreError, "OPERATOR_APPROVAL_REQUIRED"):
                save_local_model(m, directory=folder, operator_approved=False)
            self.assertEqual(list(folder.iterdir()), [])
            out = save_local_model(m, directory=folder, operator_approved=True)
            self.assertTrue(out["filename"].endswith("--windows.json"))
            loaded = load_local_model(directory=folder, profile="human",
                                      game_version=PATCH, platform="windows")
            self.assertEqual(loaded["sha256"], out["sha256"])
            self.assertEqual(loaded["model"], m)

    def test_compare_and_replace_preserves_previous_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            first = save_local_model(model(), directory=folder, operator_approved=True)
            learned = learn_candidate(model(), observed("capture:disk:0001"))
            with self.assertRaisesRegex(LocalLearningStoreError, "PROFILE_CHANGED_OR_HASH_REQUIRED"):
                save_local_model(learned, directory=folder, operator_approved=True)
            after = save_local_model(learned, directory=folder, operator_approved=True,
                                     expected_sha256=first["sha256"])
            self.assertNotEqual(after["sha256"], first["sha256"])
            self.assertEqual(after["event_count"], 1)
            with self.assertRaisesRegex(LocalLearningStoreError, "PROFILE_CHANGED_OR_HASH_REQUIRED"):
                save_local_model(model(), directory=folder, operator_approved=True,
                                 expected_sha256=first["sha256"])
            self.assertEqual(
                load_local_model(directory=folder, profile="human",
                                 game_version=PATCH, platform="windows")["model"],
                learned)
            self.assertEqual(sorted(p.name for p in folder.iterdir()), [after["filename"]])

    def test_corrupt_or_wrong_profile_never_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            first = save_local_model(model(), directory=folder, operator_approved=True)
            target = folder / first["filename"]
            target.write_text("broken", encoding="utf-8")
            with self.assertRaises(LocalLearningStoreError):
                load_local_model(directory=folder, profile="human",
                                 game_version=PATCH, platform="windows")
            with self.assertRaises(LocalLearningStoreError):
                save_local_model(model(), directory=folder, operator_approved=True,
                                 expected_sha256=first["sha256"])

    def test_no_implicit_directory_creation_or_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing"
            with self.assertRaisesRegex(LocalLearningStoreError,
                                        "EXISTING_REAL_PROFILE_DIRECTORY_REQUIRED"):
                save_local_model(model(), directory=missing, operator_approved=True)
            self.assertFalse(missing.exists())

    def test_symlinks_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "actual"
            folder.mkdir()
            link = root / "alias"
            try:
                link.symlink_to(folder, target_is_directory=True)
            except OSError:
                self.skipTest("Symlink not supported by host")
            with self.assertRaisesRegex(LocalLearningStoreError, "DIRECTORY_REQUIRED"):
                save_local_model(model(), directory=link, operator_approved=True)
            first = save_local_model(model(), directory=folder, operator_approved=True)
            target = folder / first["filename"]
            target.unlink()
            target.symlink_to(root / "outside.json")
            with self.assertRaisesRegex(LocalLearningStoreError, "PROFILE_LINK_DENIED"):
                save_local_model(model(), directory=folder, operator_approved=True)
            self.assertFalse((root / "outside.json").exists())

    def test_model_is_patch_and_profile_isolated(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            save_local_model(model(), directory=folder, operator_approved=True)
            with self.assertRaisesRegex(LocalLearningStoreError, "LOCAL_PROFILE_NOT_FOUND"):
                load_local_model(directory=folder, profile="human",
                                 game_version="1.121.361.1021", platform="windows")
            with self.assertRaisesRegex(LocalLearningStoreError, "LOCAL_PROFILE_NOT_FOUND"):
                load_local_model(directory=folder, profile="alien", game_version=PATCH,
                                 platform="windows")


if __name__ == "__main__":
    unittest.main()
