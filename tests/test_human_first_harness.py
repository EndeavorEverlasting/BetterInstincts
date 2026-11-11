"""P01: executable semantic harness/adapter coverage and failure cases."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.check_human_sovereignty import ROOT, MANIFEST, HarnessCoverageError, validate_manifest, validate


class HumanFirstHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / MANIFEST).read_text(encoding="utf-8"))

    def test_real_harness_including_source_inventory_passes(self):
        receipt = validate()
        self.assertEqual(receipt["state"], "HUMAN_FIRST_HARNESS_PASS_STATIC_ONLY")
        self.assertGreaterEqual(receipt["registered_adapters"], 15)
        self.assertEqual(receipt["local_hook_or_physical_input_proof"], "NOT_OBSERVED")

    def test_missing_or_unknown_adapters_are_rejected(self):
        bad = copy.deepcopy(self.manifest)
        bad["sources"][0]["classification"] = "UNDECIDED"
        with self.assertRaisesRegex(HarnessCoverageError,"UNCLASSIFIED_ADAPTER"):
            validate_manifest(bad)
        bad = copy.deepcopy(self.manifest)
        bad["sources"][0]["marker"] = "not a real imported API"
        with self.assertRaisesRegex(HarnessCoverageError,"ADAPTER_ADMISSION_ANCHOR_MISSING"):
            validate_manifest(bad)
        bad = copy.deepcopy(self.manifest)
        bad["sources"].append(copy.deepcopy(bad["sources"][0]))
        with self.assertRaisesRegex(HarnessCoverageError,"DUPLICATED_OR_UNKNOWN_ADAPTER"):
            validate_manifest(bad)

    def test_cannot_promote_raw_input_into_background_or_proved_gate(self):
        bad = copy.deepcopy(self.manifest)
        entry = next(x for x in bad["sources"] if x["path"] == "scripts/win32_input.py")
        entry["status"] = "ADOPTED_READ_ONLY_WITH_CALLBACK_TRUST"
        with self.assertRaisesRegex(HarnessCoverageError,"SCREEN_EFFECT_AS_BACKGROUND"):
            validate_manifest(bad)
        entry["status"] = "ADOPTED_GATED"
        with self.assertRaisesRegex(HarnessCoverageError,"FALSE_ADOPTED_GATE_CLAIM"):
            validate_manifest(bad)

    def test_unclassified_os_and_unknown_effect_are_denied(self):
        from betterinstincts.effect_authority import assess_effect
        for klass in ("OS_CONFIGURATION","UNKNOWN",None):
            with self.subTest(klass=klass):
                self.assertFalse(assess_effect(klass, session_active=True)["execute_allowed"])

    def test_new_unregistered_raw_input_source_fails(self):
        # The real repo scan is deterministic; simulate the source addition by
        # pointing a copied registry at a small independent fixture directory.
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            (base/"scripts").mkdir()
            (base/"scripts"/"future_cursor.py").write_text(
                "from scripts.win32_input import send_click\n", encoding="utf-8"
            )
            roots = copy.deepcopy(self.manifest)
            roots["source_scan"]["roots"] = ["scripts"]
            # Validator requires the rest of the canonical repo; inject one
            # synthetic source into a repo-local copy of the scanner instead.
            from scripts.check_human_sovereignty import _unregistered_sources
            extra = _unregistered_sources(roots, base, registered=set())
            self.assertEqual(extra, ["scripts/future_cursor.py"])

    def test_no_local_runtime_proof_from_static_manifest(self):
        self.assertIn("CANONICAL_DEV_CHECKOUT_CURRENT", self.manifest["proof_dimensions"])
        self.assertIn("LOCAL_CURSOR_HOOK_ACTIVE", self.manifest["proof_dimensions"])
        self.assertIn("GAMEPLAY_CERTIFIED", self.manifest["proof_dimensions"])
        self.assertIn("UNADOPTED_LEGACY_NO_LIVE_AUTHORITY",
                      {x["status"] for x in self.manifest["sources"]})


if __name__ == "__main__":
    unittest.main()
