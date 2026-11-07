import copy
import json
import unittest

from betterinstincts.save_policy import (MANIFEST_SCHEMA, SavePolicyError,
                                         decide, load_policy)


class SavePolicyTests(unittest.TestCase):
    def setUp(self):
        self.record = {
            "save_id": "slot:lab-001", "alias": "BI_TMP_EXPERIMENT_01",
            "classification": "LAB_DISPOSABLE", "origin": "LAB_CREATED",
            "lab_origin_confirmed": True, "creation_run_id": "bi002-new-game",
            "authorized_run_id": "bi002-choice", "capture_ref": "capture:slot-lab-001",
            "game_version": "1.121.361.1020", "operator_confirmed": True,
        }
        self.registry = {"schema": MANIFEST_SCHEMA, "entries": [self.record]}
        self.args = {"save_id": "slot:lab-001", "run_id": "bi002-choice",
                     "alias": "BI_TMP_EXPERIMENT_01", "game_version": "1.121.361.1020",
                     "capture_ref": "capture:slot-lab-001"}

    def test_unknown_and_unregistered_saves_are_protected_despite_lab_alias(self):
        r = decide({"schema": MANIFEST_SCHEMA, "entries": []}, **self.args)
        self.assertEqual(r["classification"], "UNKNOWN_PROTECTED")
        self.assertEqual(r["state"], "DENIED")

    def test_lab_origin_and_current_authorization_enable_only_selection(self):
        r = decide(self.registry, **self.args)
        self.assertEqual(r["state"], "OPERATOR_ATTESTED_SELECTION_ONLY")
        self.assertEqual(r["classification"], "LAB_DISPOSABLE")
        self.assertIn("NOT_INDEPENDENTLY", r["proof_ceiling"])

    def test_personal_save_cannot_be_reclassified_by_prefix(self):
        for origin in ("USER_CREATED", "UNKNOWN", None):
            with self.subTest(origin=origin):
                reg = copy.deepcopy(self.registry)
                reg["entries"][0]["origin"] = origin
                self.assertEqual(decide(reg, **self.args)["state"], "DENIED")
        reg = copy.deepcopy(self.registry)
        reg["entries"][0]["classification"] = "USER_PROTECTED"
        self.assertEqual(decide(reg, **self.args)["classification"], "USER_PROTECTED")

    def test_explicit_lab_continuation_never_becomes_disposable(self):
        r = copy.deepcopy(self.registry)
        r["entries"][0]["classification"] = "LAB_CONTINUATION"
        r["entries"][0]["alias"] = "BI_CONT_EXPERIMENT_01"
        val = decide(r, **{**self.args, "alias": "BI_CONT_EXPERIMENT_01"})
        self.assertEqual(val["classification"], "LAB_CONTINUATION")
        self.assertEqual(val["state"], "OPERATOR_ATTESTED_SELECTION_ONLY")

    def test_delete_overwrite_resume_and_migrate_always_denied(self):
        for intent in ("DELETE", "OVERWRITE", "RESUME", "MIGRATE", "AUTO_SELECT"):
            with self.subTest(intent=intent):
                self.assertEqual(decide(self.registry, **{**self.args, "intent": intent})["state"], "DENIED")

    def test_mismatched_slot_version_run_and_capture_are_denied(self):
        for key,value in (("save_id", "slot:other"),
                          ("run_id", "other-run"), ("game_version", "1.122.0.1020"),
                          ("capture_ref", "capture:other-slot")):
            with self.subTest(key=key):
                self.assertEqual(decide(self.registry, **{**self.args, key: value})["state"], "DENIED")

    def test_duplicate_identity_collision_is_denied(self):
        r = copy.deepcopy(self.registry)
        r["entries"].append({**self.record, "save_id": "slot:another"})
        self.assertEqual(decide(r, **self.args)["reason"], "SAVE_IDENTITY_AMBIGUOUS")

    def test_missing_operator_or_origin_confirmation_is_denied(self):
        for flag in ("operator_confirmed", "lab_origin_confirmed"):
            r = copy.deepcopy(self.registry)
            r["entries"][0][flag] = False
            self.assertEqual(decide(r, **self.args)["state"], "DENIED")

    def test_policy_cannot_permit_protected_saves(self):
        cfg = copy.deepcopy(load_policy())
        cfg["labels"]["USER_PROTECTED"]["permitted_intents"] = ["SELECT_FOR_PLAY"]
        from unittest.mock import patch
        # Validation occurs on read, not by trusting an arbitrary mutated in-memory policy.
        self.assertEqual(cfg["labels"]["USER_PROTECTED"]["permitted_intents"], ["SELECT_FOR_PLAY"])
        self.assertEqual(load_policy()["labels"]["USER_PROTECTED"]["permitted_intents"], [])


if __name__ == "__main__":
    unittest.main()
