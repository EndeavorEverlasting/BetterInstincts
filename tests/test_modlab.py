"""No game install needed; all tests use disposable temporary fixtures."""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from betterinstincts.dbpf import build_synthetic_package
from betterinstincts.modlab import ModLabError, inspect_mods_root
from scripts.modlab import main


class ModLabTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.mods = Path(self.tmp.name) / "Mods"
        self.mods.mkdir()

    def script(self, name: str, entries: list[str]):
        file = self.mods / name
        file.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(file, "w") as archive:
            for entry in entries:
                archive.writestr(entry, b"not executable; never imported")
        return file

    def test_empty_inventory_and_no_storage_side_effect(self):
        before = list(self.mods.iterdir())
        result = inspect_mods_root(self.mods)
        self.assertEqual(result["inspected_files"], 0)
        self.assertEqual(result["status"], "READ_ONLY_INVENTORY")
        self.assertEqual(before, list(self.mods.iterdir()))
        self.assertNotIn(str(self.mods.resolve()), json.dumps(result))

    def test_package_signature_is_metadata_not_validation(self):
        (self.mods / "ok.package").write_bytes(build_synthetic_package([(0xA, 0xB, 0xC)]))
        (self.mods / "bad.package").write_bytes(b"BAD!")
        found = {i["path"]: i for i in inspect_mods_root(self.mods)["items"]}
        self.assertEqual(found["ok.package"]["issues"], [])
        self.assertEqual(found["ok.package"]["package_index"]["index_count"], 1)
        self.assertEqual(found["ok.package"]["package_index"]["resources"][0]["type"], "0000000A")
        self.assertEqual(found["bad.package"]["issues"], ["INVALID_PACKAGE_MAGIC"])
        self.assertIsNone(found["bad.package"]["package_index"])

    def test_package_index_does_not_claim_resource_conflicts(self):
        (self.mods / "one.package").write_bytes(build_synthetic_package([(0x1, 0x0, 0x10)]))
        (self.mods / "two.package").write_bytes(build_synthetic_package([(0x1, 0x0, 0x10)]))
        result = inspect_mods_root(self.mods)
        self.assertIn("NOT_RESOURCE_CONFLICT", result["proof_ceiling"])
        self.assertNotIn("resource_overlap", result)

    def test_script_archive_module_names_only(self):
        self.script("Tools/foo.ts4script", ["my_mod/__init__.pyc", "my_mod/skills.pyc", "README.txt"])
        result = inspect_mods_root(self.mods)
        self.assertEqual(result["items"][0]["modules"], ["my_mod", "my_mod.skills"])
        self.assertEqual(result["items"][0]["issues"], [])

    def test_overlaps_are_only_candidates(self):
        self.script("a.ts4script", ["x/skills.py"])
        self.script("b.ts4script", ["x/skills.pyc"])
        result = inspect_mods_root(self.mods)
        self.assertEqual(result["module_overlap_candidates"], [{"module": "x.skills", "providers": ["a.ts4script", "b.ts4script"]}])
        self.assertIn("NOT_RESOURCE_CONFLICT", result["proof_ceiling"])

    def test_nested_script_is_flagged_not_moved(self):
        path = self.script("deep/extra/s.ts4script", ["x.py"])
        self.assertIn("SCRIPT_NESTING_REVIEW", inspect_mods_root(self.mods)["items"][0]["issues"])
        self.assertTrue(path.exists())

    def test_oversize_archive_is_skipped_without_reading_it(self):
        path = self.mods / "huge.ts4script"
        with path.open("wb") as file:
            file.truncate(64 * 1024 * 1024 + 1)
        self.assertIn("SCRIPT_ARCHIVE_SIZE_BUDGET_EXCEEDED", inspect_mods_root(self.mods)["items"][0]["issues"])

    def test_bad_zip_kept_not_deleted(self):
        path = self.mods / "bad.ts4script"
        path.write_bytes(b"oops")
        self.assertEqual(inspect_mods_root(self.mods)["items"][0]["issues"], ["INVALID_SCRIPT_ARCHIVE"])
        self.assertEqual(path.read_bytes(), b"oops")

    def test_unsafe_member_not_imported_or_extracted(self):
        self.script("bad.ts4script", ["../escape.pyc", "/abs.py", "safe.py"])
        r = inspect_mods_root(self.mods)
        self.assertEqual(r["items"][0]["modules"], ["safe"])
        self.assertIn("UNSAFE_OR_NONSTANDARD_MODULE_NAME", r["items"][0]["issues"])
        self.assertFalse((self.mods.parent / "escape.pyc").exists())

    def test_reject_non_mods_root(self):
        with self.assertRaisesRegex(ModLabError, "NAMED_MODS"):
            inspect_mods_root(self.mods.parent)

    def test_reject_max_file_budget_without_partial_success(self):
        for n in range(3):
            (self.mods / f"{n}.package").write_bytes(b"DBPF")
        with self.assertRaisesRegex(ModLabError, "FILE_BUDGET_EXCEEDED"):
            inspect_mods_root(self.mods, max_files=2)

    def test_symlink_is_never_followed(self):
        outside = Path(self.tmp.name) / "external"
        outside.mkdir()
        (outside / "external.package").write_bytes(b"DBPF")
        try:
            (self.mods / "linked").symlink_to(outside, target_is_directory=True)
            (self.mods / "linked.package").symlink_to(outside / "external.package")
        except (NotImplementedError, OSError):
            self.skipTest("Host disallows creating symlinks")
        r = inspect_mods_root(self.mods)
        self.assertEqual(r["inspected_files"], 0)
        self.assertEqual({f["code"] for f in r["findings"]}, {"LINKED_DIRECTORY_SKIPPED", "LINKED_FILE_SKIPPED"})

    def test_cli_json_and_failure_code(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["--mods-root", str(self.mods)]), 0)
        self.assertEqual(json.loads(output.getvalue())["schema"], "betterinstincts.modlab.inventory.v1")
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["--mods-root", str(self.mods.parent)]), 2)
        self.assertEqual(json.loads(output.getvalue())["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
