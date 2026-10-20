import json
import tempfile
import unittest
from pathlib import Path
from betterinstincts.compatibility import load_catalog, select_profile, CompatibilityError
from scripts.check_backward_compat import check

class CompatibilityTests(unittest.TestCase):
    def test_empty_catalog_means_unknown_not_latest(self):
        cat = load_catalog(Path(__file__).resolve().parents[1])
        self.assertEqual(select_profile(cat, "1.128.90.1020", "windows", "hunger")["status"], "UNKNOWN_VERSION")
    def test_multiple_versions_kept_separately(self):
        # Synthetic fixtures, NEVER real game certification.
        cat = {"profiles": [
            {"id":"a","game_version":"1.111.2.1020","platform":"windows","module":"hunger","status":"certified"},
            {"id":"b","game_version":"1.112.2.1020","platform":"windows","module":"hunger","status":"certified"},
        ]}
        self.assertEqual(select_profile(cat, "1.111.2.1020", "windows", "hunger")["profile"]["id"], "a")
        self.assertEqual(select_profile(cat, "1.112.2.1020", "windows", "hunger")["profile"]["id"], "b")
        self.assertEqual(select_profile(cat, "1.112.2.1021", "windows", "hunger")["status"], "UNKNOWN_VERSION")
        self.assertEqual(select_profile(cat, "1.111.2.1020", "mac", "hunger")["status"], "UNKNOWN_VERSION")
    def test_experimental_is_never_selected(self):
        cat = {"profiles":[{"id":"x","game_version":"1.111.2.1020","platform":"windows","module":"hunger","status":"experimental"}]}
        self.assertEqual(select_profile(cat, "1.111.2.1020", "windows", "hunger")["status"], "UNVERIFIED")
    def test_ambiguous_certified_requires_explicit_id(self):
        rows=[{"id":i,"game_version":"1.111.2.1020","platform":"windows","module":"hunger","status":"certified"} for i in ("a","b")]
        self.assertEqual(select_profile({"profiles":rows}, "1.111.2.1020", "windows", "hunger")["status"], "AMBIGUOUS")
        self.assertEqual(select_profile({"profiles":rows}, "1.111.2.1020", "windows", "hunger", "b")["profile"]["id"], "b")
    def test_path_escape_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"compatibility").mkdir()
            (root/"compatibility/catalog.v1.json").write_text(json.dumps({
                "schema":"betterinstincts.compatibility/v1",
                "profiles":[{"id":"foo","game_version":"1.111.2.1020","platform":"windows","module":"hunger",
                             "status":"experimental","path":"../../../../foo"}]}))
            with self.assertRaisesRegex(CompatibilityError,"PROFILE_PATH_MUST_BE_CANONICAL"):
                load_catalog(root)
    def test_current_old_catalog_passes(self):
        x=check("fake",old_reader=lambda ref,path: json.dumps({"schema":"betterinstincts.compatibility/v1","profiles":[]}).encode())
        self.assertEqual(x["certified_preserved"],0)
    def test_certified_profile_never_removed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"compatibility").mkdir()
            (root/"compatibility/catalog.v1.json").write_text(json.dumps({"schema":"betterinstincts.compatibility/v1","profiles":[]}))
            old={"schema":"betterinstincts.compatibility/v1","profiles":[
                {"id":"old","game_version":"1.111.2.1020","platform":"windows","module":"hunger",
                 "status":"certified","path":"compatibility/profiles/old.json"}]}
            with self.assertRaisesRegex(CompatibilityError,"CERTIFIED_PROFILE_REWRITTEN"):
                check("fake",root=root,old_reader=lambda ref,path: json.dumps(old).encode())
if __name__ == "__main__":
    unittest.main()
