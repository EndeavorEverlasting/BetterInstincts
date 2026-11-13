"""Explicit per-installation local learning snapshot I/O, not an auto-writer.

Caller must select an existing folder and authorize every write. No filesystem
discovery, profile migration, timers, sockets, Sims hooks or background startup.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Mapping

from betterinstincts.occult_needs import (
    OccultNeedsError, _patch, _validate_model, load_catalog,
)

MAX_BYTES = 256_000


class LocalLearningStoreError(OccultNeedsError):
    pass


def _directory(value: Path) -> Path:
    if not isinstance(value, (Path, str)):
        raise LocalLearningStoreError("EXPLICIT_PROFILE_DIRECTORY_REQUIRED")
    folder = Path(value)
    if not folder.is_dir() or folder.is_symlink():
        raise LocalLearningStoreError("EXISTING_REAL_PROFILE_DIRECTORY_REQUIRED")
    return folder


def _file(folder: Path, profile: str, version: str, platform: str) -> Path:
    cfg = load_catalog()
    _patch(version, platform)
    if profile not in cfg["profiles"] or not cfg["profiles"][profile]["motives"]:
        raise LocalLearningStoreError("UNKNOWN_PROFILE")
    return folder / f"occult-needs--{profile}--{version}--{platform}.json"


def _read_bytes(path: Path) -> bytes:
    if path.is_symlink():
        raise LocalLearningStoreError("PROFILE_LINK_DENIED")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except FileNotFoundError as exc:
        raise LocalLearningStoreError("LOCAL_PROFILE_NOT_FOUND") from exc
    except OSError as exc:
        raise LocalLearningStoreError("LOCAL_PROFILE_UNREADABLE") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
            raise LocalLearningStoreError("UNSAFE_LOCAL_PROFILE_FILE")
        with os.fdopen(fd, "rb", closefd=False) as file:
            data = file.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise LocalLearningStoreError("LOCAL_PROFILE_TOO_LARGE")
        return data
    finally:
        os.close(fd)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _decode(data: bytes) -> dict:
    try:
        model = json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise LocalLearningStoreError("LOCAL_PROFILE_INVALID_JSON") from exc
    try:
        return _validate_model(model, load_catalog())
    except OccultNeedsError as exc:
        raise LocalLearningStoreError("LOCAL_PROFILE_INVALID_MODEL") from exc


def load_local_model(*, directory: Path, profile: str,
                     game_version: str, platform: str) -> dict:
    """Read only an explicitly selected existing local profile."""
    path = _file(_directory(directory), profile, game_version, platform)
    data = _read_bytes(path)
    model = _decode(data)
    if (model["profile"], model["game_version"], model["platform"]) != (
        profile, game_version, platform
    ):
        raise LocalLearningStoreError("LOCAL_PROFILE_IDENTITY_MISMATCH")
    return {"model": model, "sha256": _digest(data), "filename": path.name}


def save_local_model(
    model: Mapping, *, directory: Path, operator_approved: bool,
    expected_sha256: str | None = None,
) -> dict:
    """Create or compare-and-replace ONLY this modeled profile after approval.

    For an existing profile, caller must supply its exact SHA-256 from the
    previous load or save. A single-owner lock prevents two cooperating writers
    from silently racing. No data are written without explicit approval.
    """
    if operator_approved is not True:
        raise LocalLearningStoreError("OPERATOR_APPROVAL_REQUIRED")
    try:
        valid = _validate_model(model, load_catalog())
    except OccultNeedsError as exc:
        raise LocalLearningStoreError("LOCAL_PROFILE_INVALID_MODEL") from exc
    folder = _directory(directory)
    path = _file(folder, valid["profile"], valid["game_version"], valid["platform"])
    if path.is_symlink():
        raise LocalLearningStoreError("PROFILE_LINK_DENIED")
    data = (json.dumps(valid, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            + "\n").encode("utf-8")
    if len(data) > MAX_BYTES:
        raise LocalLearningStoreError("LOCAL_PROFILE_TOO_LARGE")
    lock = path.with_name(path.name + ".lock")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        lock_fd = os.open(lock, flags, 0o600)
    except OSError as exc:
        raise LocalLearningStoreError("PROFILE_WRITE_LOCK_UNAVAILABLE") from exc
    os.close(lock_fd)
    temporary: Path | None = None
    try:
        if path.exists() or path.is_symlink():
            actual = _read_bytes(path)
            old = _decode(actual)
            if (old["profile"], old["game_version"], old["platform"]) != (
                valid["profile"], valid["game_version"], valid["platform"]
            ):
                raise LocalLearningStoreError("LOCAL_PROFILE_IDENTITY_MISMATCH")
            if expected_sha256 is None or _digest(actual) != expected_sha256:
                raise LocalLearningStoreError("PROFILE_CHANGED_OR_HASH_REQUIRED")
        elif expected_sha256 is not None:
            raise LocalLearningStoreError("EXPECTED_PROFILE_NOT_FOUND")
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=folder, prefix=".occult-needs-", suffix=".tmp",
            delete=False
        ) as tmp:
            temporary = Path(tmp.name)
            try:
                os.chmod(temporary, 0o600)
            except OSError:
                pass  # OS-specific permissions; directory access is operator-chosen.
            tmp.write(data)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(temporary, path)
        temporary = None
        readback = load_local_model(
            directory=folder, profile=valid["profile"],
            game_version=valid["game_version"], platform=valid["platform"]
        )
        if readback["sha256"] != _digest(data):
            raise LocalLearningStoreError("LOCAL_PROFILE_READBACK_MISMATCH")
        return {"filename": path.name, "sha256": readback["sha256"],
                "event_count": len(valid["events"]) + len(valid.get("candidate_events", []))}
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
        lock.unlink()
