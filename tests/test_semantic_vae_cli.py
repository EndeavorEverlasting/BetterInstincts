"""P83/P03 closer: actual CLI routes profile settings, model and deletion together."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch as mock_patch

from betterinstincts.installation_profiles import create_profile
from betterinstincts.semantic_vae import load_local_model, SemanticVAEError
from scripts.semantic_vae import run
from tests.test_spatial_convolution import snapshot, grid, event


class SemanticVAECLITests(unittest.TestCase):
    def test_profile_selection_end_to_end_and_purge_only_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            setting_file = root / "settings.v1.json"
            paths = {"use": root / "app"}
            with (mock_patch("betterinstincts.installation_profiles.settings_path",
                             return_value=setting_file),
                  mock_patch("bootstrap.paths", return_value=paths)):
                create_profile("family")
                self.assertEqual(run(["status"])["state"], "DISABLED")
                self.assertEqual(run(["status", "--profile", "family"])["state"], "DISABLED")
                with self.assertRaisesRegex(ValueError, "EXPLICIT_LOCAL_DATA_ACK_REQUIRED"):
                    run(["enable", "--profile", "family"])
                enabled = run(["enable", "--profile", "family", "--ack-local-data"])
                self.assertEqual(enabled["profile"], "family")
                self.assertEqual(run(["status"])["state"], "DISABLED")
                self.assertEqual(run(["status", "--profile", "family"])["state"], "ENABLED")
                self.assertEqual(run(["disable", "--profile", "family"])["profile"], "family")
                self.assertEqual(run(["status", "--profile", "family"])["state"], "DISABLED")
                run(["enable", "--profile", "family", "--ack-local-data"])

                pieces = {"snapshot": snapshot(), "event": event(1), "patch": grid()}
                input_args = []
                for field, obj in pieces.items():
                    file = root / (field + ".json")
                    file.write_text(json.dumps(obj), encoding="utf-8")
                    input_args += ["--" + field, str(file)]
                self.assertEqual(run(["train"] + input_args)["status"],
                                 "LOCAL_TRAINING_DISABLED")
                first = run(["train", "--profile", "family"] + input_args)
                self.assertIn(first["status"], {"TRAINED_ON_DEVICE", "HELDOUT_VALIDATION_ONLY"})
                profile = run(["status", "--profile", "family",
                               "--snapshot", str(root / "snapshot.json")])
                self.assertEqual(profile["trained"] + profile["heldout"], 1)
                self.assertEqual(profile["retained_examples"], 1)
                default = run(["status", "--snapshot", str(root / "snapshot.json")])
                self.assertEqual(default["trained"] + default["heldout"], 0)
                self.assertEqual(load_local_model(pieces["snapshot"])["trained"] +
                                 load_local_model(pieces["snapshot"])["heldout"], 0)
                self.assertEqual(load_local_model(pieces["snapshot"], profile_id="family")["trained"] +
                                 load_local_model(pieces["snapshot"], profile_id="family")["heldout"], 1)

                with self.assertRaisesRegex(ValueError, "EXPLICIT_DELETE_CONFIRM_REQUIRED"):
                    run(["purge", "--profile", "family",
                         "--snapshot", str(root / "snapshot.json")])
                self.assertEqual(run(["purge", "--snapshot", str(root / "snapshot.json"),
                                      "--ack-delete-local-data"])["status"],
                                 "LOCAL_MODEL_NOT_PRESENT")
                self.assertEqual(run(["purge", "--profile", "family",
                                      "--snapshot", str(root / "snapshot.json"),
                                      "--ack-delete-local-data"])["status"], "LOCAL_MODEL_PURGED")
                self.assertEqual(run(["status", "--profile", "family",
                                      "--snapshot", str(root / "snapshot.json")])["retained_examples"], 0)
                self.assertEqual(run(["status", "--profile", "family"])["state"], "ENABLED")

    def test_invalid_existing_profile_is_rejected_before_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_file = Path(tmp) / "settings.v1.json"
            with mock_patch("betterinstincts.installation_profiles.settings_path",
                            return_value=settings_file):
                for args in (["status", "--profile", "unknown"],
                             ["enable", "--profile", "unknown", "--ack-local-data"],
                             ["disable", "--profile", "unknown"]):
                    with self.subTest(args=args), self.assertRaisesRegex(
                        Exception, "PROFILE_NOT_FOUND"
                    ):
                        run(args)
                self.assertFalse(settings_file.exists())


if __name__ == "__main__":
    unittest.main()
