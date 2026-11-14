"""Privacy, replay and authority regressions for reviewed community-case intake."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.community_candidate import CandidateError
from scripts.community_cases import (
    POLICY, SCHEMA, _hash, audit_repo, build_bundle, export_to, read_bundle,
    run, validate_bundle,
)


def source(ref="capture:localaaa", outcome="helpful", action="eat",
           version="1.120.113.1020"):
    return {"schema": "betterinstincts.judgment-example/v1",
            "game_version": version, "platform": "windows",
            "context": {"scenario": "needs", "need_state": "critical",
                        "scene": "live", "previous_action": "none",
                        "style": "balanced"},
            "action": action, "outcome": outcome, "operator_reviewed": True,
            "opt_in": True, "observation_ref": ref}


class CommunityCasesTests(unittest.TestCase):
    def test_source_ref_and_unbounded_private_fields_cannot_escape(self):
        local = source("capture:privatehousehold")
        original = copy.deepcopy(local)
        b = build_bundle([local])
        self.assertEqual(local, original)
        self.assertEqual(b["schema"], SCHEMA)
        self.assertEqual(b["effect_policy"], POLICY)
        self.assertEqual(validate_bundle(b)["cases"], 1)
        text = json.dumps(b)
        for private in ("privatehousehold", "observation_ref", "operator_reviewed",
                        "opt_in", "save_id", "sim_name"):
            self.assertNotIn(private, text)
        self.assertFalse(validate_bundle(b)["safe_to_promote"])

    def test_export_is_explicit_local_only_and_nonoverwriting(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "bundle.json"
            b = build_bundle([source()])
            export_to(p, b)
            self.assertEqual(read_bundle(p), b)
            with self.assertRaisesRegex(CandidateError, "TARGET_EXISTS"):
                export_to(p, b)

    def test_ack_required_even_before_reading_private_source(self):
        with self.assertRaisesRegex(CandidateError, "SHARING_ACK_REQUIRED"):
            run(["export", "--reviewed-examples", "PRIVATE_MISSING.json",
                 "--out", "new.json"])

    def test_not_reviewed_or_extra_private_data_rejected(self):
        for name, value in (("unreviewed", False), ("not_opted_in", False)):
            row = source()
            row["operator_reviewed" if name == "unreviewed" else "opt_in"] = value
            with self.subTest(name=name), self.assertRaises(CandidateError):
                build_bundle([row])
        row = source()
        row["save_path"] = "C:/private/user"
        with self.assertRaises(CandidateError):
            build_bundle([row])

    def test_duplicate_and_cross_version_rejected(self):
        with self.assertRaisesRegex(CandidateError, "DUPLICATE_SEMANTIC_CASE"):
            build_bundle([source("capture:aa1"), source("capture:aa2")])
        with self.assertRaisesRegex(CandidateError, "MIXED_GAME_VERSION"):
            build_bundle([source(), source(version="1.119.0.1000")])

    def test_digest_replay_and_unknown_fields_rejected(self):
        b = build_bundle([source()])
        cases = [
            lambda c: c["cases"][0].update({"outcome": "harmful"}),
            lambda c: c["cases"][0].update({"observation_ref": "private"}),
            lambda c: c.update({"source_path": "private"}),
            lambda c: c.update({"effect_policy": "EXECUTE"}),
            lambda c: c["cases"].append(dict(c["cases"][0])),
            lambda c: c.update({"bundle_sha256": "0" * 64}),
        ]
        for change in cases:
            c = copy.deepcopy(b)
            change(c)
            with self.subTest(change=change), self.assertRaises(CandidateError):
                validate_bundle(c)

    def test_opposing_labels_are_flagged_not_promoted(self):
        b = build_bundle([source("capture:aa1"), source("capture:bb2",
                                                       outcome="harmful")])
        res = validate_bundle(b)
        self.assertEqual(res["opposing_label_contexts"], 1)
        self.assertFalse(res["safe_to_promote"])
        self.assertFalse(res["provenance_attested"])
        self.assertFalse(res["share_consent_attested"])

    def test_untrusted_json_duplicate_keys_and_raw_text_disallowed(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "untrusted.json"
            p.write_text('{"schema":"A","schema":"B"}', encoding="utf-8")
            with self.assertRaises(CandidateError):
                read_bundle(p)
            b = build_bundle([source()])
            b["cases"][0]["action"] = "arbitrary user name"
            b["cases"][0]["case_sha256"] = _hash(b["cases"][0])
            b["bundle_sha256"] = _hash({k:v for k,v in b.items()
                                       if k != "bundle_sha256"})
            p.write_text(json.dumps(b), encoding="utf-8")
            with self.assertRaises(CandidateError):
                read_bundle(p)


if __name__ == "__main__":
    unittest.main()
