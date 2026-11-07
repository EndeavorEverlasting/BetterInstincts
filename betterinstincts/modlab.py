"""Explicit-root, read-only inventory for Sims 4 mod-development reconnaissance.

No game API calls, file writes, archive extraction, imports from mods or background work.
"""
from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
import zipfile

SCHEMA = "betterinstincts.modlab.inventory.v1"
MAX_FILES = 10_000
MAX_ZIP_ENTRIES = 2_000
MAX_SCRIPT_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_MODULES_PER_ARCHIVE = 256
MOD_SUFFIXES = {".package", ".ts4script"}


class ModLabError(ValueError):
    """Fail-closed input or budget rejection."""


def _safe_zip_module(entry_name: str) -> str | None:
    """Return a Python module name from a simple archive entry, never open it."""
    if "\\" in entry_name or entry_name.startswith("/") or ":" in entry_name:
        return None
    path = PurePosixPath(entry_name)
    if ".." in path.parts or not path.parts or len(path.parts) > 16:
        return None
    if path.suffix.lower() not in {".py", ".pyc"}:
        return None
    components = list(path.with_suffix("").parts)
    if components[-1] == "__init__":
        components.pop()
    if not components or any(not s.isidentifier() for s in components):
        return None
    return ".".join(components)


def _script_modules(path: Path) -> tuple[list[str], list[str]]:
    """Inspect central-directory names only; zip members are NEVER read/executed."""
    issues: list[str] = []
    modules: set[str] = set()
    try:
        if path.stat().st_size > MAX_SCRIPT_ARCHIVE_BYTES:
            return [], ["SCRIPT_ARCHIVE_SIZE_BUDGET_EXCEEDED"]
        with zipfile.ZipFile(path) as archive:
            info = archive.infolist()
            if len(info) > MAX_ZIP_ENTRIES:
                return [], ["ZIP_ENTRY_BUDGET_EXCEEDED"]
            for member in info:
                if member.is_dir():
                    continue
                name = _safe_zip_module(member.filename)
                if (member.filename.endswith((".py", ".pyc")) and name is None):
                    issues.append("UNSAFE_OR_NONSTANDARD_MODULE_NAME")
                if name is not None:
                    modules.add(name)
                if len(modules) > MAX_MODULES_PER_ARCHIVE:
                    return [], ["MODULE_BUDGET_EXCEEDED"]
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile):
        return [], ["INVALID_SCRIPT_ARCHIVE"]
    return sorted(modules), sorted(set(issues))


def inspect_mods_root(root: str | Path, *, max_files: int = MAX_FILES) -> dict:
    """Walk only an operator-provided Mods directory, without following links.

    Report paths relative to the selected root; never disclose the absolute root.
    This is an inventory, not a package resource conflict detector, dependency
    resolver, installer or game-compatibility certification.
    """
    supplied = Path(root)
    if supplied.is_symlink() or not supplied.is_dir():
        raise ModLabError("EXPLICIT_MODS_ROOT_MUST_BE_A_REAL_DIRECTORY")
    if supplied.name.casefold() != "mods":
        raise ModLabError("EXPLICIT_DIRECTORY_MUST_BE_NAMED_MODS")
    if not isinstance(max_files, int) or isinstance(max_files, bool) or max_files < 1 or max_files > MAX_FILES:
        raise ModLabError("INVALID_MAX_FILES")
    entries: list[dict] = []
    findings: list[dict] = []
    module_owners: dict[str, list[str]] = {}
    examined = 0
    def onerror(exc: OSError) -> None:
        raise ModLabError("MODS_ROOT_UNREADABLE") from exc

    for parent, dirs, files in os.walk(supplied, topdown=True, followlinks=False, onerror=onerror):
        parent_path = Path(parent)
        for name in sorted(dirs[:]):
            if (parent_path / name).is_symlink():
                dirs.remove(name)
                findings.append({"path": (parent_path / name).relative_to(supplied).as_posix(), "code": "LINKED_DIRECTORY_SKIPPED"})
        dirs.sort(key=str.casefold)
        for name in sorted(files, key=str.casefold):
            candidate = parent_path / name
            suffix = candidate.suffix.casefold()
            if suffix not in MOD_SUFFIXES:
                continue
            examined += 1
            if examined > max_files:
                raise ModLabError("FILE_BUDGET_EXCEEDED")
            relative = candidate.relative_to(supplied).as_posix()
            if candidate.is_symlink():
                findings.append({"path": relative, "code": "LINKED_FILE_SKIPPED"})
                continue
            try:
                stat = candidate.stat()
                if not candidate.is_file():
                    findings.append({"path": relative, "code": "NON_FILE_SKIPPED"})
                    continue
                item = {"path": relative, "kind": "package" if suffix == ".package" else "script", "bytes": stat.st_size, "modules": [], "issues": []}
                if suffix == ".package":
                    with candidate.open("rb") as stream:
                        if stream.read(4) != b"DBPF":
                            item["issues"].append("INVALID_PACKAGE_MAGIC")
                else:
                    item["modules"], item["issues"] = _script_modules(candidate)
                    if len(Path(relative).parts) > 2:
                        item["issues"].append("SCRIPT_NESTING_REVIEW")
                    for module in item["modules"]:
                        module_owners.setdefault(module, []).append(relative)
                entries.append(item)
            except OSError:
                findings.append({"path": relative, "code": "FILE_UNREADABLE"})
    overlaps = [{"module": module, "providers": sorted(providers)} for module, providers in sorted(module_owners.items()) if len(providers) > 1]
    return {
        "schema": SCHEMA,
        "status": "READ_ONLY_INVENTORY",
        "root_label": supplied.name,
        "inspected_files": len(entries),
        "items": entries,
        "module_overlap_candidates": overlaps,
        "findings": sorted(findings, key=lambda item: (item["path"], item["code"])),
        "proof_ceiling": "FILE_METADATA_AND_ARCHIVE_NAMES_ONLY_NOT_RESOURCE_CONFLICT_OR_GAMEPLAY_PROOF",
    }
