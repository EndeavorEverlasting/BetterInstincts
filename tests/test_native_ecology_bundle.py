"""Packaging regression coverage; never invokes the game or alters user Mods."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import py_compile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts.native_ecology_bundle import (
    MOD_FILE, MANIFEST_FILE, MODULE_PYC, RUNTIME_MEMBERS, TRAIT_MEMBERS, NativeEcologyPackageError,
    build_package, install_package, uninstall_package, verify_hook_proof,
)

BUILD = "1.121.361.1020"
SOURCE = b"# candidate native loader, only after local EA hook proof\n"


def hook_proof():
    return {
        "schema": "betterinstincts.native-ecology-hook-proof/v1",
        "game_build": BUILD,
        "embedded_python": "3.7",
        "source_sha256": hashlib.sha256(SOURCE).hexdigest(),
        "installed_ea_source_ref": "local:EA:Gameplay:1.121.361",
        "native_event_signature_ref": "local:EA:event:signature",
        "native_queue_signature_ref": "local:EA:queue:signature",
        "native_import_activation_ref": "local:EA:import:signature",
        "player_preemption_verified": True,
    }


class NativeEcologyPackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.mod_dir = self.root / "Mods"
        self.mod_dir.mkdir()
        (self.mod_dir / "Resource.cfg").write_text("original")
        (self.mod_dir / "Unrelated.package").write_bytes(b"keep")
        self.py37 = self.root / "python37"
        self.py37.write_text("fake test path")
        self.source = self.root / "BetterInstincts_Ecology.py"
        self.source.write_bytes(SOURCE)
        self.proof = self.root / "proof.json"
        self.proof.write_text(json.dumps(hook_proof()))
        self.output = self.root / "out"

    def fake_interpreter(self, argv, **kwargs):
        if "py_compile" in argv[2]:
            Path(argv[-1]).write_bytes(bytes([66, 13, 13, 10]) + b"\x00" * 24)
            return subprocess.CompletedProcess(argv, 0, "", "")
        return subprocess.CompletedProcess(argv, 0, "3.7\n", "")

    def build(self):
        with patch("scripts.native_ecology_bundle.subprocess.run",
                   side_effect=self.fake_interpreter):
            return build_package(
                python37=self.py37, source_path=self.source,
                hook_proof_path=self.proof, output_dir=self.output, game_build=BUILD,
            )

    def test_proof_requires_source_hash_and_runtime_hook_evidence(self):
        good = hook_proof()
        self.assertEqual(verify_hook_proof(good, source=SOURCE, game_build=BUILD), good)
        for change in (
            {"native_import_activation_ref": ""},
            {"player_preemption_verified": False},
            {"embedded_python": "3.13"},
            {"game_build": "LATEST"},
            {"source_sha256": "0" * 64},
        ):
            with self.subTest(change=change):
                broken = {**good, **change}
                with self.assertRaisesRegex(NativeEcologyPackageError, "LOCAL_EA_HOOK_PROOF_REQUIRED"):
                    verify_hook_proof(broken, source=SOURCE, game_build=BUILD)

    def test_packaging_rejects_wrong_python_version(self):
        with patch("scripts.native_ecology_bundle.subprocess.run",
                   return_value=subprocess.CompletedProcess([], 0, "3.13\n", "")):
            with self.assertRaisesRegex(NativeEcologyPackageError, "PYTHON_3_7_REQUIRED"):
                build_package(
                    python37=self.py37, source_path=self.source,
                    hook_proof_path=self.proof, output_dir=self.output, game_build=BUILD,
                )

    def test_build_install_readback_uninstall_preserves_other_mods(self):
        built = self.build()
        self.assertTrue(Path(built["package"]).exists())
        with zipfile.ZipFile(built["package"]) as z:
            self.assertEqual(z.namelist(), [MODULE_PYC])
        with self.assertRaisesRegex(NativeEcologyPackageError, "GAME_CLOSED_CONFIRMATION_REQUIRED"):
            install_package(
                mods_dir=self.mod_dir, package_path=Path(built["package"]),
                manifest_path=Path(built["manifest"]), game_closed_confirmed=False,
            )
        result = install_package(
            mods_dir=self.mod_dir, package_path=Path(built["package"]),
            manifest_path=Path(built["manifest"]), game_closed_confirmed=True,
        )
        self.assertEqual(result["sha256"], built["sha256"])
        installed = self.mod_dir / "BetterInstincts" / MOD_FILE
        manifest = self.mod_dir / "BetterInstincts" / MANIFEST_FILE
        self.assertTrue(installed.exists())
        self.assertTrue(manifest.exists())
        with self.assertRaisesRegex(NativeEcologyPackageError, "MODS_OWNERSHIP_COLLISION"):
            install_package(
                mods_dir=self.mod_dir, package_path=Path(built["package"]),
                manifest_path=Path(built["manifest"]), game_closed_confirmed=True,
            )
        result = uninstall_package(mods_dir=self.mod_dir, game_closed_confirmed=True)
        self.assertIn("OWNED_FILE_REMOVED_ONLY", result["proof"])
        self.assertFalse(installed.exists())
        self.assertEqual((self.mod_dir / "Resource.cfg").read_text(), "original")
        self.assertEqual((self.mod_dir / "Unrelated.package").read_bytes(), b"keep")

    def test_modification_blocks_uninstall_to_prevent_clobber(self):
        built = self.build()
        install_package(
            mods_dir=self.mod_dir, package_path=Path(built["package"]),
            manifest_path=Path(built["manifest"]), game_closed_confirmed=True,
        )
        modified = self.mod_dir / "BetterInstincts" / MOD_FILE
        modified.write_bytes(b"somebody else's change")
        with self.assertRaisesRegex(NativeEcologyPackageError, "OWNED_PACKAGE_MODIFIED"):
            uninstall_package(mods_dir=self.mod_dir, game_closed_confirmed=True)
        self.assertEqual(modified.read_bytes(), b"somebody else's change")

    def test_no_install_without_real_mods_resource_config(self):
        built = self.build()
        (self.mod_dir / "Resource.cfg").unlink()
        with self.assertRaisesRegex(NativeEcologyPackageError, "MODS_LOCATION_OR_SOURCE_UNVERIFIED"):
            install_package(
                mods_dir=self.mod_dir, package_path=Path(built["package"]),
                manifest_path=Path(built["manifest"]), game_closed_confirmed=True,
            )

    def test_embedded_bundle_needs_binding_and_imports_without_checkout(self):
        with patch("scripts.native_ecology_bundle._compile_py37", side_effect=self.compile_for_test):
            args = dict(python37=self.py37, source_path=self.source, hook_proof_path=self.proof,
                        output_dir=self.output, game_build=BUILD, installed_player_runtime=True)
            with self.assertRaisesRegex(NativeEcologyPackageError, "RUNTIME_BINDING_PROOF_REQUIRED"):
                build_package(**args)
            self.proof.write_text(json.dumps({
                **hook_proof(), "installed_player_runtime_binding_ref": "local:verified:binding",
            }))
            built = build_package(**args)
        with zipfile.ZipFile(built["package"]) as archive:
            self.assertEqual(archive.namelist(), [MODULE_PYC, *RUNTIME_MEMBERS])
        installed = install_package(
            mods_dir=self.mod_dir, package_path=Path(built["package"]),
            manifest_path=Path(built["manifest"]), game_closed_confirmed=True,
        )
        process = subprocess.run(
            [sys.executable, "-I", "-c",
             "import sys; sys.path.insert(0, sys.argv[1]);"
             "from betterinstincts.installed_player_runtime import IDLE_SECONDS;"
             "assert IDLE_SECONDS == 5", installed["installed"]],
            cwd=self.root, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        retained_learning = Path(installed["installed"]).with_name("player-learning.sqlite3")
        retained_learning.write_bytes(b"retained")
        uninstall_package(mods_dir=self.mod_dir, game_closed_confirmed=True)
        install_package(mods_dir=self.mod_dir, package_path=Path(built["package"]),
                        manifest_path=Path(built["manifest"]), game_closed_confirmed=True)
        self.assertEqual(retained_learning.read_bytes(), b"retained")

    def test_installed_trait_archive_imports_policy_without_checkout(self):
        options = dict(python37=self.py37, source_path=self.source, hook_proof_path=self.proof,
                       output_dir=self.output, game_build=BUILD, installed_player_runtime=True,
                       installed_trait_responder=True)
        proof = {**hook_proof(), "installed_player_runtime_binding_ref": "local:verified:binding"}
        self.proof.write_text(json.dumps(proof))
        with self.assertRaisesRegex(NativeEcologyPackageError, "TRAIT_RESPONDER_BINDING_PROOF_REQUIRED"):
            build_package(**options)
        self.proof.write_text(json.dumps({
            **proof, "installed_trait_responder_binding_ref": "local:verified:trait-binding",
        }))
        with patch("scripts.native_ecology_bundle._compile_py37", side_effect=self.compile_for_test):
            built = build_package(**options)
        with zipfile.ZipFile(built["package"]) as archive:
            self.assertEqual(archive.namelist(), [MODULE_PYC, *RUNTIME_MEMBERS, *TRAIT_MEMBERS])
        installed = install_package(mods_dir=self.mod_dir, package_path=Path(built["package"]),
                                    manifest_path=Path(built["manifest"]), game_closed_confirmed=True)
        script = """
import sys
sys.path.insert(0, sys.argv[1])
from betterinstincts.preference_response_port import PreferenceResponsePort
from betterinstincts.preference_prompts import evaluate_offer
offer = dict(dialog_class="sim_trait_offer", dialog_stage="offer", scene="live",
             topic_id="chased_by_death", offer_kind="add_trait", title="Chased by Death",
             trait_label="Chased by Death", button_labels={"YES": "Yes", "NO": "No thanks!"},
             visible_buttons=["NO", "YES"], player_directed=False, sim_ref="sim:actor",
             capture_ref="capture:exact")
assert evaluate_offer(offer, automation_opt_in=True)["target_label"] == "No thanks!"
assert PreferenceResponsePort().respond(enabled=True)["state"] == "NATIVE_ADAPTER_REQUIRED"
"""
        result = subprocess.run([sys.executable, "-I", "-c", script, installed["installed"]],
                                cwd=self.root, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def compile_for_test(self, _python37, source):
        import ast

        # Syntax admission plus real archive import under the test interpreter.
        ast.parse(source.read_text(encoding="utf-8"), feature_version=(3, 7))
        output = self.root / "isolated-test.pyc"
        py_compile.compile(str(source), cfile=str(output), doraise=True)
        return output.read_bytes()

    def test_existing_output_never_overwritten(self):
        self.build()
        with self.assertRaisesRegex(NativeEcologyPackageError, "PACKAGE_OUTPUT_ALREADY_EXISTS"):
            self.build()


if __name__ == "__main__":
    unittest.main()
