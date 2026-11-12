"""Portable, explicitly selected EA DBPF package resource indexing only.

Never executes binary code, scans Sims folders, opens user saves, or claims
that a DBPF index is a decoded floor plan. The input is an explicitly supplied
.package path; results identify resources by content rather than install path.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from betterinstincts.dbpf import MAX_PACKAGE_BYTES, DbpfError, read_package_index

BUILD = re.compile(r"^[0-9]+(?:\.[0-9]+){2,4}$")


class EaGeometryIntakeError(ValueError):
    """Unsupported or unsafe read-only source."""


def inspect_ea_package(
    package_path: str | Path, *, declared_game_build: str,
    max_reported: int = 128,
) -> dict:
    """Read an approved DBPF index, never the resource bodies.

    Provenance identifies the exact bytes but does not verify that the caller's
    declared game build or TGI semantics match installed EA code.
    """
    if not isinstance(declared_game_build, str) or not BUILD.fullmatch(declared_game_build):
        raise EaGeometryIntakeError("EXACT_DECLARED_BUILD_REQUIRED")
    p = Path(package_path)
    if (p.suffix.lower() != ".package" or p.name.lower().startswith("slot_")
            or any(part.lower() in {"saves", "tray"} for part in p.parts)
            or p.is_symlink() or not p.is_file()):
        raise EaGeometryIntakeError("EXPLICIT_NON_SAVE_PACKAGE_REQUIRED")
    initial = p.stat()
    if not 96 <= initial.st_size <= MAX_PACKAGE_BYTES:
        raise EaGeometryIntakeError("PACKAGE_SIZE_UNSAFE")
    try:
        index = read_package_index(p, max_reported=max_reported)
        digest = hashlib.sha256()
        with p.open("rb") as file:
            for block in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(block)
        final = p.stat()
        if (initial.st_size, initial.st_mtime_ns) != (final.st_size, final.st_mtime_ns):
            raise EaGeometryIntakeError("PACKAGE_CHANGED_DURING_READ")
    except (DbpfError, OSError) as exc:
        raise EaGeometryIntakeError("EA_DBPF_INDEX_REJECTED:" + str(exc)) from exc
    resources = sorted(index["resources"],
                       key=lambda r: (r["type"], r["group"], r["instance"]))
    return {
        "schema": "betterinstincts.ea-resource-index/v1",
        "state": "READ_ONLY_TGI_INDEX_NOT_BUILDING_GEOMETRY",
        "source_sha256": digest.hexdigest(),
        "source_filename": p.name,
        "declared_game_build": declared_game_build,
        "game_build_verified": False,
        "dbpf_format": index["format"],
        "index_count": index["index_count"],
        "index_truncated": index["truncated"],
        "resource_keys": [
            {"type": r["type"], "group": r["group"], "instance": r["instance"]}
            for r in resources
        ],
        "issues": index["issues"],
        "geometry_decoded": False,
        "native_code_executed": False,
        "execute_allowed": False,
        "proof_ceiling": "DBPF_TGI_KEYS_AND_CONTENT_HASH_ONLY_NOT_LOT_OR_FLOOR_DECODER",
    }
