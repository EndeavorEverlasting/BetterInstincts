import tempfile
import unittest
from pathlib import Path
from scripts.tuning_audit import inspect,TuningAuditError

class TuningAuditTests(unittest.TestCase):
    def test_synthetic_xml_identity_and_fingerprint(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"synthetic.xml"
            p.write_text('<I c="TEST" i="interaction" n="synthetic_hunger" s="123"><L n="autonomy"><T n="hunger_score">1</T></L></I>')
            r=inspect(p)
            self.assertEqual(r["resource"]["s"],"123")
            self.assertEqual(r["status"],"EXTRACTED_METADATA_ONLY")
            self.assertTrue(any("hunger" in row["hints"] for row in r["hunger_related_candidates"]))
            self.assertEqual(len(r["sha256"]),64)
            self.assertNotIn("synthetic_hunger",str(r["hunger_related_candidates"]))
    def test_dtd_and_entities_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"bad.xml"
            p.write_text('<!DOCTYPE foo [<!ENTITY leak "evil">]><I/>')
            with self.assertRaisesRegex(TuningAuditError,"UNSAFE_XML"):
                inspect(p)
    def test_noxml_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"nope.txt"
            p.write_text('<I/>')
            with self.assertRaisesRegex(TuningAuditError,"INPUT_MUST_BE_XML"):
                inspect(p)
    def test_file_too_large(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"large.xml"
            p.write_bytes(b"x"*2000001)
            with self.assertRaisesRegex(TuningAuditError,"INPUT_TOO_LARGE"):
                inspect(p)
if __name__=="__main__":
    unittest.main()
