"""Synthetic DBPF TGI index fixtures; no real game packages required."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from betterinstincts.dbpf import (
    FLAG_CONSTANT_GROUP,
    FLAG_CONSTANT_INSTANCE_HI,
    FLAG_CONSTANT_TYPE,
    DbpfError,
    build_synthetic_package,
    read_package_index,
)


class DbpfIndexTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, name: str, payload: bytes) -> Path:
        path = self.root / name
        path.write_bytes(payload)
        return path

    def test_reads_tgi_keys_without_payload_execution(self):
        package = self.write(
            "sample.package",
            build_synthetic_package(
                [
                    (0x220557DA, 0x00000000, 0x0000000000001234),
                    (0x545AC67A, 0x00000001, 0x00000000ABCDEF01),
                ]
            ),
        )
        before = package.read_bytes()
        report = read_package_index(package)
        self.assertEqual(report["status"], "INDEX_READ_ONLY")
        self.assertEqual(report["index_count"], 2)
        self.assertEqual(report["reported"], 2)
        self.assertFalse(report["truncated"])
        self.assertEqual(report["resources"][0]["type"], "220557DA")
        self.assertEqual(report["resources"][0]["group"], "00000000")
        self.assertEqual(report["resources"][0]["instance"], "0000000000001234")
        self.assertEqual(report["resources"][1]["type"], "545AC67A")
        self.assertIn("INDEX_KEYS_ONLY", report["proof_ceiling"])
        self.assertEqual(package.read_bytes(), before)

    def test_constant_index_header_fields(self):
        flags = FLAG_CONSTANT_TYPE | FLAG_CONSTANT_GROUP | FLAG_CONSTANT_INSTANCE_HI
        package = self.write(
            "const.package",
            build_synthetic_package(
                [
                    (0x11111111, 0x22222222, 0x3333333300000001),
                    (0x11111111, 0x22222222, 0x3333333300000002),
                ],
                constant_flags=flags,
            ),
        )
        report = read_package_index(package)
        self.assertEqual(report["index_count"], 2)
        self.assertEqual({item["type"] for item in report["resources"]}, {"11111111"})
        self.assertEqual({item["group"] for item in report["resources"]}, {"22222222"})
        self.assertEqual(
            [item["instance"] for item in report["resources"]],
            ["3333333300000001", "3333333300000002"],
        )

    def test_report_budget_truncates_without_claiming_complete_listing(self):
        keys = [(0x1, 0x2, index) for index in range(5)]
        package = self.write("many.package", build_synthetic_package(keys))
        report = read_package_index(package, max_reported=2)
        self.assertEqual(report["index_count"], 5)
        self.assertEqual(report["reported"], 2)
        self.assertTrue(report["truncated"])

    def test_invalid_magic_and_symlink_rejected(self):
        bad = self.write("bad.package", b"BAD!" + b"\x00" * 100)
        with self.assertRaisesRegex(DbpfError, "INVALID_PACKAGE_MAGIC"):
            read_package_index(bad)
        outside = self.root / "outside.package"
        outside.write_bytes(build_synthetic_package([(1, 2, 3)]))
        linked = self.root / "linked.package"
        try:
            linked.symlink_to(outside)
        except (NotImplementedError, OSError):
            self.skipTest("Host disallows creating symlinks")
        with self.assertRaisesRegex(DbpfError, "PACKAGE_MUST_BE_A_REAL_FILE"):
            read_package_index(linked)

    def test_truncated_index_fails_closed(self):
        payload = bytearray(build_synthetic_package([(1, 2, 3)]))
        # Corrupt declared index size so the blob is truncated relative to entry count.
        import struct

        struct.pack_into("<I", payload, 0x2C, 8)
        package = self.write("trunc.package", bytes(payload))
        with self.assertRaisesRegex(DbpfError, "TRUNCATED_INDEX"):
            read_package_index(package)


if __name__ == "__main__":
    unittest.main()
