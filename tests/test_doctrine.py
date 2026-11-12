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

    def test_offline_policy_io_regression_rejected(self):
        original = Path.read_text
        def replaced(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            if path.name == "priority.py":
                return "import os\n" + text
            return text
        with patch.object(Path, "read_text", autospec=True, side_effect=replaced):
            with self.assertRaisesRegex(DoctrineViolation, "OFFLINE_POLICY_IO_IMPORT"):
                validate(ROOT)

    def test_hunger_sprint_cannot_close_without_game_cert(self):
        original = Path.read_text
        def replaced(path, *args, **kwargs):
            s = original(path, *args, **kwargs)
            if path.name == "BI-002.md":
                return s.replace("# BI-002 —", "# BI-002 CLOSED —")
            return s
        with patch.object(Path, "read_text", autospec=True, side_effect=replaced):
            with self.assertRaisesRegex(DoctrineViolation, "HUNGER_SPRINT_CLOSURE_WITHOUT_GAME_CERT"):
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


    def test_doctrine_survives_actions_workflow_retirement(self):
        original = Path.is_file

        def hidden_workflow(path, *args, **kwargs):
            if path.as_posix().endswith("/.github/workflows/ci.yml"):
                return False
            return original(path, *args, **kwargs)

        with patch.object(Path, "is_file", autospec=True, side_effect=hidden_workflow):
            self.assertEqual(validate(ROOT)["state"], "PASS")

    def test_missing_local_quality_contract_is_rejected(self):
        original = Path.is_file

        def missing_local_quality(path, *args, **kwargs):
            if path.name == "local-quality-checks.v1.json":
                return False
            return original(path, *args, **kwargs)

        with patch.object(Path, "is_file", autospec=True, side_effect=missing_local_quality):
            with self.assertRaisesRegex(DoctrineViolation, "MISSING_CANONICAL_PATH"):
                validate(ROOT)

    def test_diluted_local_quality_floor_is_rejected(self):
        original = Path.read_text

        def weakened(path, *args, **kwargs):
            content = original(path, *args, **kwargs)
            if path.name == "local-quality-checks.v1.json":
                import json
                data = json.loads(content)
                data["checks"] = data["checks"][:48]
                return json.dumps(data)
            return content

        with patch.object(Path, "read_text", autospec=True, side_effect=weakened):
            with self.assertRaisesRegex(DoctrineViolation, "LOCAL_QUALITY_FLOOR_LOST"):
                validate(ROOT)


if __name__ == "__main__":
    unittest.main()
