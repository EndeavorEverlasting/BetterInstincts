"""Sixth-gear P82: learned Gaussian VAE, isolated local storage and hard safety."""
from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch as mock_patch

from betterinstincts.semantic_vae import (
    MAX_EVENTS, MAX_RETAINED, PROOF, SemanticVAEError, advise, empty_model, learn,
    load_local_model, record_if_enabled, record_local_sample, purge_local_model,
)
from tests.test_spatial_convolution import snapshot, grid, event


class SemanticVAETests(unittest.TestCase):
    def test_consent_missing_rejects_without_side_effect(self):
        with self.assertRaisesRegex(SemanticVAEError, "EXPLICIT_OPT_IN_REQUIRED"):
            learn(snapshot(), event(1), grid())
        with self.assertRaisesRegex(SemanticVAEError, "EXPLICIT_OPT_IN_REQUIRED"):
            record_local_sample(snapshot(), event(1), grid())
        self.assertEqual(record_if_enabled(snapshot(), event(1), grid(),
            profile_id="default")["status"], "LOCAL_TRAINING_DISABLED")

    def test_actual_encoder_decoder_and_gradient_update(self):
        world = snapshot()
        initial = empty_model(world)
        before = copy.deepcopy(initial)
        model = initial
        for index in range(32):
            model, state = learn(world, event(index, blocked=index % 2 == 1),
                                 grid(index % 2 == 1), prior=model,
                                 explicit_opt_in=True)
            self.assertIn(state, {"TRAINED_ON_DEVICE", "HELDOUT_VALIDATION_ONLY"})
        self.assertEqual(initial, before)  # Caller-owned model never mutated.
        self.assertNotEqual(model["encoder_mu"], initial["encoder_mu"])
        self.assertNotEqual(model["encoder_logvar"], initial["encoder_logvar"])
        self.assertNotEqual(model["decoder"], initial["decoder"])
        self.assertEqual(model["trained"] + model["heldout"], 32)
        self.assertEqual(len(model["samples"]), 32)
        self.assertEqual({r["partition"] for r in model["samples"]}, {"TRAIN", "HOLDOUT"})
        self.assertGreater(model["train_reconstruction_sum"], 0)
        self.assertGreater(model["heldout_reconstruction_sum"], 0)
        self.assertTrue(all(len(row["x"]) == 75 for row in model["samples"]))
        self.assertFalse(any("Sim" in str(row) or "before-" in str(row)
                             for row in model["samples"]))

    def test_holdout_never_changes_weights(self):
        initial = empty_model(snapshot())
        for index in range(100):
            new, state = learn(snapshot(), event(index), grid(),
                               prior=initial, explicit_opt_in=True)
            if state == "HELDOUT_VALIDATION_ONLY":
                for key in ("encoder_mu", "encoder_logvar", "bias_mu",
                            "bias_logvar", "decoder", "decoder_bias"):
                    self.assertEqual(new[key], initial[key], key)
                self.assertEqual(new["trained"], 0)
                self.assertEqual(new["heldout"], 1)
                return
        self.fail("No deterministic held-out sample")

    def test_replay_and_cross_world_are_refused(self):
        model, state = learn(snapshot(), event(1), grid(), explicit_opt_in=True)
        repeated, status = learn(snapshot(), event(1), grid(), prior=model,
                                 explicit_opt_in=True)
        self.assertEqual(status, "REPLAY_OR_BLOOM_COLLISION_IGNORED")
        self.assertEqual(repeated, model)
        bad = snapshot()
        bad["save_scope_id"] = "foreign"
        with self.assertRaises(SemanticVAEError):
            learn(bad, event(2), grid(), prior=model, explicit_opt_in=True)
        for change in ({"human_present": True}, {"player_directed": True},
                       {"observed_scene_revision": "old"},
                       {"graph_revision": "foreign"}):
            bad = snapshot()
            bad.update(change)
            with self.assertRaises(SemanticVAEError):
                learn(bad, event(3), grid(), explicit_opt_in=True)
        unsupported = grid()
        unsupported["source"] = "SCREENSHOT_GUESS"
        with self.assertRaises(SemanticVAEError):
            learn(snapshot(), event(5), unsupported, explicit_opt_in=True)

    def test_nonfinite_weights_and_wrong_shapes_are_rejected(self):
        old = empty_model(snapshot())
        bad = copy.deepcopy(old)
        bad["decoder"][0][0] = float("nan")
        with self.assertRaises(SemanticVAEError):
            learn(snapshot(), event(4), grid(), prior=bad, explicit_opt_in=True)
        bad = copy.deepcopy(old)
        bad["encoder_mu"][0].pop()
        with self.assertRaises(SemanticVAEError):
            learn(snapshot(), event(4), grid(), prior=bad, explicit_opt_in=True)
        bad = copy.deepcopy(old)
        bad["samples"] = [{"id":"a"*40,"partition":"TRAIN","x":[0]*75}]
        with self.assertRaises(SemanticVAEError):
            learn(snapshot(), event(4), grid(), prior=bad, explicit_opt_in=True)

    def test_decoder_cannot_certify_walk_camera_or_graph(self):
        world = snapshot()
        result = advise(world, empty_model(world), grid(), from_region="a", to_region="b")
        self.assertEqual(result["status"], "ABSTAIN_UNCALIBRATED")
        self.assertFalse(result["execute_allowed"])
        self.assertFalse(result["can_add_graph_edges"])
        self.assertFalse(result["can_move_camera"])
        self.assertFalse(result["can_walk_sim"])
        unknown = copy.deepcopy(world)
        unknown["current_region"] = "other-region"
        self.assertEqual(advise(unknown, empty_model(world), grid(),
                         from_region="a", to_region="b")["status"], "ABSTAIN_UNVERIFIED")
        self.assertIsNone(result["control_permit"])
        self.assertEqual(result["proof_ceiling"], PROOF)

    def test_sample_cap_fail_closed(self):
        world = snapshot()
        model = empty_model(world)
        model["trained"] = MAX_EVENTS
        model["seen_bloom"] = "01" + "00" * (16_384 - 1)
        with self.assertRaisesRegex(SemanticVAEError, "TRAINING_CAPACITY_REACHED"):
            learn(world, event(MAX_EVENTS + 1), grid(), prior=model,
                  explicit_opt_in=True)

    def test_rolling_corpus_keeps_training_weights_and_replay_guard(self):
        world = snapshot()
        model = empty_model(world)
        for i in range(MAX_RETAINED + 12):
            model, state = learn(world, event(i, blocked=i % 2 == 0),
                                 grid(i % 2 == 0), prior=model, explicit_opt_in=True)
            self.assertIn(state, {"TRAINED_ON_DEVICE", "HELDOUT_VALIDATION_ONLY"})
        self.assertEqual(len(model["samples"]), MAX_RETAINED)
        self.assertEqual(model["trained"] + model["heldout"], MAX_RETAINED + 12)
        self.assertGreater(model["trained"], 0)
        self.assertNotIn(model["samples"][0]["id"],
                         [r["id"] for r in empty_model(world)["samples"]])
        # An old replay remains excluded even after its raw vector was evicted.
        replay, state = learn(world, event(0, blocked=True), grid(True),
                              prior=model, explicit_opt_in=True)
        self.assertEqual(state, "REPLAY_OR_BLOOM_COLLISION_IGNORED")
        self.assertEqual(replay, model)

    def test_atomic_local_model_replay_and_scope_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            use = Path(tmp) / "app"
            with mock_patch("bootstrap.paths", return_value={"use":use}):
                self.assertFalse((Path(tmp)/"runtime").exists())
                first = record_local_sample(snapshot(), event(1), grid(),
                                            explicit_opt_in=True)
                self.assertIn(first["status"],
                    {"TRAINED_ON_DEVICE","HELDOUT_VALIDATION_ONLY"})
                again = record_local_sample(snapshot(), event(1), grid(),
                                            explicit_opt_in=True)
                self.assertEqual(again["status"], "REPLAY_OR_BLOOM_COLLISION_IGNORED")
                self.assertEqual(load_local_model(snapshot())["trained"] +
                                 load_local_model(snapshot())["heldout"], 1)
                other = snapshot()
                other["save_scope_id"] = "other"
                self.assertEqual(load_local_model(other)["trained"], 0)
                local = list((Path(tmp)/"runtime"/"semantic-vae").glob("*.json"))
                self.assertEqual(len(local),1)
                self.assertNotIn("lab-save", local[0].name)
                self.assertNotIn("actor-opaque", local[0].read_text())

    def test_profile_opt_in_forwards_exactly_one_approved_sample(self):
        with tempfile.TemporaryDirectory() as tmp:
            with (mock_patch("bootstrap.paths", return_value={"use":Path(tmp)/"app"}),
                 mock_patch("betterinstincts.installation_profiles.view",
                     return_value={"profile_id":"default","settings":{"learning.semantic_vae":True}})):
                accepted = record_if_enabled(snapshot(), event(1), grid())
                self.assertIn(accepted["status"], {"TRAINED_ON_DEVICE","HELDOUT_VALIDATION_ONLY"})
                self.assertEqual(load_local_model(snapshot())["trained"] +
                                 load_local_model(snapshot())["heldout"], 1)

    def test_purge_only_matching_local_scope_with_explicit_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            use = Path(tmp) / "app"
            with mock_patch("bootstrap.paths", return_value={"use":use}):
                a = snapshot()
                b = snapshot()
                b["save_scope_id"] = "another-save"
                record_local_sample(a, event(1), grid(), explicit_opt_in=True)
                with self.assertRaisesRegex(SemanticVAEError, "EXPLICIT_DELETE_CONFIRM_REQUIRED"):
                    purge_local_model(a)
                self.assertEqual(purge_local_model(b, explicit_confirm=True)["status"],
                                 "LOCAL_MODEL_NOT_PRESENT")
                self.assertEqual(load_local_model(a)["trained"] +
                                 load_local_model(a)["heldout"], 1)
                self.assertEqual(purge_local_model(a, explicit_confirm=True)["status"],
                                 "LOCAL_MODEL_PURGED")
                self.assertEqual(load_local_model(a)["trained"] +
                                 load_local_model(a)["heldout"], 0)

    def test_symlink_and_existing_lock_deny_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            use = Path(tmp)/"app"
            with mock_patch("bootstrap.paths", return_value={"use":use}):
                root = Path(tmp)/"runtime"/"semantic-vae"
                root.mkdir(parents=True)
                path = root / (empty_model(snapshot())["context_hash"]+".json")
                path.with_suffix(".lock").write_text("active")
                with self.assertRaisesRegex(SemanticVAEError, "CONCURRENT_WRITER_BUSY"):
                    record_local_sample(snapshot(), event(2), grid(), explicit_opt_in=True)
                path.with_suffix(".lock").unlink()
                path.symlink_to(Path(tmp)/"unsafe.json")
                with self.assertRaisesRegex(SemanticVAEError, "LOCAL_STORAGE_UNSAFE"):
                    record_local_sample(snapshot(), event(2), grid(), explicit_opt_in=True)

    def test_named_profiles_isolate_identical_world_and_purge(self):
        with tempfile.TemporaryDirectory() as tmp:
            use = Path(tmp) / "app"
            world = snapshot()
            with mock_patch("bootstrap.paths", return_value={"use": use}):
                # Preserve the pre-closer v1 default-profile checkpoint location.
                default = record_local_sample(world, event(1), grid(),
                                              explicit_opt_in=True)
                self.assertIn(default["status"], {"TRAINED_ON_DEVICE", "HELDOUT_VALIDATION_ONLY"})
                default_path = (Path(tmp) / "runtime" / "semantic-vae" /
                                (empty_model(world)["context_hash"] + ".json"))
                self.assertTrue(default_path.is_file())
                self.assertEqual(load_local_model(world, profile_id="household")["trained"] +
                                 load_local_model(world, profile_id="household")["heldout"], 0)
                named = record_local_sample(world, event(2), grid(),
                                            explicit_opt_in=True, profile_id="household")
                self.assertIn(named["status"], {"TRAINED_ON_DEVICE", "HELDOUT_VALIDATION_ONLY"})
                self.assertEqual(load_local_model(world, profile_id="household")["trained"] +
                                 load_local_model(world, profile_id="household")["heldout"], 1)
                self.assertEqual(load_local_model(world)["trained"] +
                                 load_local_model(world)["heldout"], 1)
                self.assertEqual(len(list(default_path.parent.glob("*.json"))), 2)
                with self.assertRaises(SemanticVAEError):
                    record_local_sample(world, event(3), grid(),
                                        explicit_opt_in=True, profile_id="../other")
                with self.assertRaises(SemanticVAEError):
                    purge_local_model(world, explicit_confirm=True, profile_id="../other")
                self.assertEqual(purge_local_model(world, explicit_confirm=True,
                                                   profile_id="household")["status"],
                                 "LOCAL_MODEL_PURGED")
                self.assertTrue(default_path.is_file())
                self.assertEqual(load_local_model(world)["trained"] +
                                 load_local_model(world)["heldout"], 1)
                self.assertEqual(load_local_model(world, profile_id="household")["trained"] +
                                 load_local_model(world, profile_id="household")["heldout"], 0)

    def test_malformed_profile_readback_denies_training(self):
        with mock_patch("betterinstincts.installation_profiles.view",
                        return_value={"settings":{"learning.semantic_vae":True}}):
            with self.assertRaisesRegex(SemanticVAEError, "LOCAL_CONSENT_PROFILE_UNVERIFIED"):
                record_if_enabled(snapshot(), event(1), grid())

    def test_named_profile_consent_is_strict_and_does_not_inherit_default(self):
        world = snapshot()
        with tempfile.TemporaryDirectory() as tmp:
            with (mock_patch("bootstrap.paths", return_value={"use": Path(tmp) / "app"}),
                  mock_patch("betterinstincts.installation_profiles.view",
                             side_effect=lambda profile_id=None: {
                                 "profile_id": profile_id or "default",
                                 "settings": {"learning.semantic_vae": profile_id != "household"},
                             })):
                response = record_if_enabled(world, event(1), grid(),
                                             profile_id="household")
                self.assertEqual(response["status"], "LOCAL_TRAINING_DISABLED")
                self.assertFalse((Path(tmp) / "runtime").exists())
                other = record_if_enabled(world, event(1), grid(), profile_id="default")
                self.assertIn(other["status"], {"TRAINED_ON_DEVICE", "HELDOUT_VALIDATION_ONLY"})



if __name__ == "__main__":
    unittest.main()
