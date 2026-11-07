"""Read-only Sims 4 DBPF package index (TGI) inspection.

Parses header + resource-index metadata only. Never decompresses, extracts,
executes, or rewrites package payloads. Format facts follow the public
DBPF documentation at https://thesims4moddersreference.org/reference/dbpf-format/
(independently verified against synthetic fixtures; not a copy of any tool's code).
"""
from __future__ import annotations

import struct
from pathlib import Path

HEADER_SIZE = 96
MAX_PACKAGE_BYTES = 64 * 1024 * 1024
MAX_INDEX_ENTRIES = 10_000
MAX_REPORTED_RESOURCES = 256
FLAG_CONSTANT_TYPE = 0x1
FLAG_CONSTANT_GROUP = 0x2
FLAG_CONSTANT_INSTANCE_HI = 0x4
EXTENDED_ENTRY_BIT = 0x8000_0000


class DbpfError(ValueError):
    """Fail-closed package index rejection."""


def _u32(buf: bytes, offset: int) -> int:
    return struct.unpack_from("<I", buf, offset)[0]


def _u64(buf: bytes, offset: int) -> int:
    return struct.unpack_from("<Q", buf, offset)[0]


def _hex32(value: int) -> str:
    return f"{value:08X}"


def _hex64(value: int) -> str:
    return f"{value:016X}"


def read_package_index(path: str | Path, *, max_reported: int = MAX_REPORTED_RESOURCES) -> dict:
    """Return bounded TGI metadata from one package file.

    Proof ceiling: INDEX_KEYS_ONLY. Does not prove tuning semantics, skill hooks,
    resource collisions across packages, or gameplay compatibility.
    """
    if not isinstance(max_reported, int) or isinstance(max_reported, bool):
        raise DbpfError("INVALID_MAX_REPORTED")
    if max_reported < 1 or max_reported > MAX_REPORTED_RESOURCES:
        raise DbpfError("INVALID_MAX_REPORTED")
    package = Path(path)
    if package.is_symlink() or not package.is_file():
        raise DbpfError("PACKAGE_MUST_BE_A_REAL_FILE")
    size = package.stat().st_size
    if size < HEADER_SIZE:
        raise DbpfError("PACKAGE_TOO_SMALL")
    if size > MAX_PACKAGE_BYTES:
        raise DbpfError("PACKAGE_SIZE_BUDGET_EXCEEDED")
    with package.open("rb") as stream:
        header = stream.read(HEADER_SIZE)
        if len(header) != HEADER_SIZE or header[:4] != b"DBPF":
            raise DbpfError("INVALID_PACKAGE_MAGIC")
        major = _u32(header, 4)
        minor = _u32(header, 8)
        if major != 2:
            raise DbpfError("UNSUPPORTED_DBPF_MAJOR")
        index_count = _u32(header, 0x24)
        index_offset_short = _u32(header, 0x28)
        index_size = _u32(header, 0x2C)
        index_offset_long = _u64(header, 0x40)
        index_offset = index_offset_long if index_offset_short == 0 else index_offset_short
        if index_count == 0:
            return {
                "status": "INDEX_EMPTY",
                "format": f"{major}.{minor}",
                "index_count": 0,
                "reported": 0,
                "truncated": False,
                "resources": [],
                "issues": [],
                "proof_ceiling": "INDEX_KEYS_ONLY_NOT_TUNING_OR_GAMEPLAY_PROOF",
            }
        if index_count > MAX_INDEX_ENTRIES:
            raise DbpfError("INDEX_ENTRY_BUDGET_EXCEEDED")
        if index_offset < HEADER_SIZE or index_offset >= size:
            raise DbpfError("INVALID_INDEX_OFFSET")
        if index_size < 4 or index_offset + index_size > size:
            raise DbpfError("INVALID_INDEX_SIZE")
        stream.seek(index_offset)
        index_blob = stream.read(index_size)
        if len(index_blob) != index_size:
            raise DbpfError("INDEX_UNREADABLE")
    return _parse_index(
        index_blob,
        index_count=index_count,
        package_size=size,
        major=major,
        minor=minor,
        max_reported=max_reported,
    )


def _parse_index(
    index_blob: bytes,
    *,
    index_count: int,
    package_size: int,
    major: int,
    minor: int,
    max_reported: int,
) -> dict:
    flags = _u32(index_blob, 0)
    if flags & ~0x7:
        raise DbpfError("UNSUPPORTED_INDEX_FLAGS")
    cursor = 4
    constant_type = constant_group = constant_instance_hi = None
    if flags & FLAG_CONSTANT_TYPE:
        if cursor + 4 > len(index_blob):
            raise DbpfError("TRUNCATED_INDEX_HEADER")
        constant_type = _u32(index_blob, cursor)
        cursor += 4
    if flags & FLAG_CONSTANT_GROUP:
        if cursor + 4 > len(index_blob):
            raise DbpfError("TRUNCATED_INDEX_HEADER")
        constant_group = _u32(index_blob, cursor)
        cursor += 4
    if flags & FLAG_CONSTANT_INSTANCE_HI:
        if cursor + 4 > len(index_blob):
            raise DbpfError("TRUNCATED_INDEX_HEADER")
        constant_instance_hi = _u32(index_blob, cursor)
        cursor += 4

    resources: list[dict] = []
    issues: list[str] = []
    truncated = False

    def need(nbytes: int) -> None:
        if cursor + nbytes > len(index_blob):
            raise DbpfError("TRUNCATED_INDEX_ENTRIES")

    for _ in range(index_count):
        type_id = constant_type
        group_id = constant_group
        instance_hi = constant_instance_hi
        if type_id is None:
            need(4)
            type_id = _u32(index_blob, cursor)
            cursor += 4
        if group_id is None:
            need(4)
            group_id = _u32(index_blob, cursor)
            cursor += 4
        if instance_hi is None:
            need(4)
            instance_hi = _u32(index_blob, cursor)
            cursor += 4
        need(16)
        instance_lo = _u32(index_blob, cursor)
        cursor += 4
        resource_offset = _u32(index_blob, cursor)
        cursor += 4
        compressed_field = _u32(index_blob, cursor)
        cursor += 4
        uncompressed_size = _u32(index_blob, cursor)
        cursor += 4
        extended = bool(compressed_field & EXTENDED_ENTRY_BIT)
        compressed_size = compressed_field & ~EXTENDED_ENTRY_BIT
        compression = None
        if extended:
            need(4)
            compression = struct.unpack_from("<HH", index_blob, cursor)
            cursor += 4
        if resource_offset >= package_size:
            issues.append("RESOURCE_OFFSET_OUT_OF_RANGE")
        if compressed_size > package_size:
            issues.append("COMPRESSED_SIZE_OUT_OF_RANGE")
        if len(resources) < max_reported:
            instance = (instance_hi << 32) | instance_lo
            resources.append(
                {
                    "type": _hex32(type_id),
                    "group": _hex32(group_id),
                    "instance": _hex64(instance),
                    "offset": resource_offset,
                    "compressed_bytes": compressed_size,
                    "uncompressed_bytes": uncompressed_size,
                    "compression": None if compression is None else f"{compression[0]:04X}",
                }
            )
        else:
            truncated = True
    return {
        "status": "INDEX_READ_ONLY",
        "format": f"{major}.{minor}",
        "index_count": index_count,
        "reported": len(resources),
        "truncated": truncated,
        "resources": resources,
        "issues": sorted(set(issues)),
        "proof_ceiling": "INDEX_KEYS_ONLY_NOT_TUNING_OR_GAMEPLAY_PROOF",
    }


def build_synthetic_package(
    resources: list[tuple[int, int, int]],
    *,
    constant_flags: int = 0,
) -> bytes:
    """Fabricate a minimal valid DBPF 2.1 package for offline tests only."""
    if not resources:
        raise DbpfError("SYNTHETIC_REQUIRES_RESOURCES")
    if constant_flags & ~0x7:
        raise DbpfError("UNSUPPORTED_INDEX_FLAGS")
    payloads = b"".join(b"\x00" * 4 for _ in resources)
    index_parts = bytearray()
    constants: list[int] = []
    type_id = resources[0][0]
    group_id = resources[0][1]
    instance_hi = (resources[0][2] >> 32) & 0xFFFFFFFF
    if constant_flags & FLAG_CONSTANT_TYPE:
        if any(item[0] != type_id for item in resources):
            raise DbpfError("CONSTANT_TYPE_MISMATCH")
        constants.append(type_id)
    if constant_flags & FLAG_CONSTANT_GROUP:
        if any(item[1] != group_id for item in resources):
            raise DbpfError("CONSTANT_GROUP_MISMATCH")
        constants.append(group_id)
    if constant_flags & FLAG_CONSTANT_INSTANCE_HI:
        if any(((item[2] >> 32) & 0xFFFFFFFF) != instance_hi for item in resources):
            raise DbpfError("CONSTANT_INSTANCE_HI_MISMATCH")
        constants.append(instance_hi)
    index_parts += struct.pack("<I", constant_flags)
    for value in constants:
        index_parts += struct.pack("<I", value)
    offset = HEADER_SIZE
    for type_v, group_v, instance in resources:
        if not (constant_flags & FLAG_CONSTANT_TYPE):
            index_parts += struct.pack("<I", type_v)
        if not (constant_flags & FLAG_CONSTANT_GROUP):
            index_parts += struct.pack("<I", group_v)
        if not (constant_flags & FLAG_CONSTANT_INSTANCE_HI):
            index_parts += struct.pack("<I", (instance >> 32) & 0xFFFFFFFF)
        index_parts += struct.pack("<I", instance & 0xFFFFFFFF)
        index_parts += struct.pack("<I", offset)
        index_parts += struct.pack("<I", 4 | EXTENDED_ENTRY_BIT)
        index_parts += struct.pack("<I", 4)
        index_parts += struct.pack("<HH", 0x0000, 1)
        offset += 4
    index_blob = bytes(index_parts)
    index_offset = HEADER_SIZE + len(payloads)
    header = bytearray(HEADER_SIZE)
    header[0:4] = b"DBPF"
    struct.pack_into("<I", header, 4, 2)
    struct.pack_into("<I", header, 8, 1)
    struct.pack_into("<I", header, 0x24, len(resources))
    struct.pack_into("<I", header, 0x28, 0)
    struct.pack_into("<I", header, 0x2C, len(index_blob))
    struct.pack_into("<I", header, 0x3C, 3)
    struct.pack_into("<Q", header, 0x40, index_offset)
    return bytes(header) + payloads + index_blob
