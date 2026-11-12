"""Read-only synthetic DBPF resource-index provenance, no real EA assets."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from betterinstincts.dbpf import build_synthetic_package
from betterinstincts.ea_geometry_intake import EaGeometryIntakeError, inspect_ea_package


class EaGeometryIntakeTests(unittest.TestCase):
    def test_identical_package_in_different_install_roots_has_same_identity(self):
        blob = build_synthetic_package([(0x12345678, 0, 1), (0x11111111, 2, 3)])
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "linux_app" / "sample.package"
            b = Path(tmp) / "windows_app" / "sample.package"
            for item in (a, b):
                item.parent.mkdir()
                item.write_bytes(blob)
            one = inspect_ea_package(a, declared_game_build="1.121.361.1020")
            two = inspect_ea_package(b, declared_game_build="1.121.361.1020")
            self.assertEqual(one, two)
            self.assertEqual(one["index_count"], 2)
            self.assertFalse(one["geometry_decoded"])
            self.assertFalse(one["game_build_verified"])
            self.assertFalse(one["execute_allowed"])

    def test_save_path_or_unversioned_source_is_rejected_before_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            saves = root / "saves"
            saves.mkdir()
            fake = saves / "Slot_00000007.save"
            fake.write_bytes(b"NEVER")
            with self.assertRaises(EaGeometryIntakeError):
                inspect_ea_package(fake, declared_game_build="1.121.361.1020")
            pkg = root / "thing.package"
            pkg.write_bytes(build_synthetic_package([(1, 2, 3)]))
            for bad in ("latest", "", "UNKNOWN"):
                with self.subTest(build=bad), self.assertRaises(EaGeometryIntakeError):
                    inspect_ea_package(pkg, declared_game_build=bad)
            with self.assertRaises(EaGeometryIntakeError):
                inspect_ea_package(root / "missing.package", declared_game_build="1.121.361.1020")
            pointer = root / "alias.package"
            try:
                pointer.symlink_to(pkg)
            except (OSError, NotImplementedError):
                pass
            else:
                with self.assertRaises(EaGeometryIntakeError):
                    inspect_ea_package(pointer, declared_game_build="1.121.361.1020")

if __name__ == "__main__":
    unittest.main()
