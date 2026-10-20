import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.validate_doctrine import DoctrineViolation, ROOT, validate

class DoctrineTests(unittest.TestCase):
    def test_current_doctrine(self):
        self.assertEqual(validate()["state"], "PASS")

    def test_missing_entrypoint_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(DoctrineViolation, "MISSING_CANONICAL_PATH"):
                validate(Path(temp))

    def test_acknowledgement_only_governance_rejected(self):
        original = Path.read_text
        def replaced(path, *args, **kwargs):
            if path.name == "AGENTS.md":
                return "Got it, will do."
            return original(path, *args, **kwargs)
        with patch.object(Path, "read_text", autospec=True, side_effect=replaced):
            with self.assertRaisesRegex(DoctrineViolation, "GOVERNANCE_GAP"):
                validate(ROOT)

    def test_missing_product_vision_rejected(self):
        original = Path.read_text
        def replaced(path, *args, **kwargs):
            if path.name == "LEDGER.md":
                return "All work complete."
            return original(path, *args, **kwargs)
        with patch.object(Path, "read_text", autospec=True, side_effect=replaced):
            with self.assertRaisesRegex(DoctrineViolation, "PARENT_OR_PROOF_LOST"):
                validate(ROOT)

if __name__ == "__main__":
    unittest.main()
