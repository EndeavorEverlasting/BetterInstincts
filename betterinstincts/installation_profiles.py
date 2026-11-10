"""Versioned per-installation preferences; distinct from Sims/save/game profiles.

No implicit scanning, collection, background worker, desktop/game authority or
installer-manifest mutation. Callers opt in to reading settings at their own gate.
"""
from __future__ import annotations

import json
import os
import re
import stat
import sys
import tempfile
from pathlib import Path
from typing import Callable

SCHEMA = "betterinstincts.installation-profiles/v1"
MAX_BYTES = 32_768
MAX_PROFILES = 16
PROFILE_ID = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
class InstallationProfileError(ValueError):
    pass


CATALOG_PATH = Path(__file__).resolve().parents[1] / "contracts" / "installation-profiles.v1.json"


def _catalog_defaults() -> dict[str, bool]:
    # The versioned catalog is the sole default value owner (P124).
    if CATALOG_PATH.is_symlink() or not CATALOG_PATH.is_file() or CATALOG_PATH.stat().st_size > MAX_BYTES:
        raise InstallationProfileError("SETTINGS_CATALOG_UNSAFE")
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    values = data.get("defaults")
    if data.get("schema") != "betterinstincts.installation-profiles-catalog/v1" or not isinstance(values, dict):
        raise InstallationProfileError("SETTINGS_CATALOG_INVALID")
    if not values or len(values) > 64 or any(not isinstance(k, str) or not k or type(v) is not bool for k, v in values.items()):
        raise InstallationProfileError("SETTINGS_CATALOG_INVALID")
    return values


DEFAULTS = _catalog_defaults()


def settings_path(*, home: Path | None = None, platform: str | None = None,
                  environment: dict[str, str] | None = None) -> Path:
    """The sole local preferences path owner. Never install under checkout/app/saves."""
    home = Path.home() if home is None else Path(home)
    platform = sys.platform if platform is None else platform
    env = os.environ if environment is None else environment
    if not home.is_absolute():
        raise InstallationProfileError("HOME_NOT_ABSOLUTE")
    if platform == "win32":
        base = env.get("LOCALAPPDATA")
        if not base or not Path(base).is_absolute():
            raise InstallationProfileError("LOCALAPPDATA_REQUIRED")
        return Path(base) / "BetterInstincts" / "settings.v1.json"
    if platform.startswith("linux"):
        base = Path(env.get("XDG_CONFIG_HOME", str(home / ".config")))
        if not base.is_absolute():
            raise InstallationProfileError("XDG_CONFIG_HOME_NOT_ABSOLUTE")
        return base / "betterinstincts" / "settings.v1.json"
    raise InstallationProfileError("UNSUPPORTED_OS")


def _empty() -> dict:
    return {"schema": SCHEMA, "revision": 0, "active_profile": "default",
            "profiles": {"default": {}}}


def _safe_path(path: Path) -> None:
    if path.name != "settings.v1.json":
        raise InstallationProfileError("SETTINGS_PATH_NOT_CANONICAL")
    if path.is_symlink() or path.parent.is_symlink():
        raise InstallationProfileError("SYMLINK_SETTINGS_PATH_FORBIDDEN")
    if path.exists() and (not path.is_file() or path.stat().st_size > MAX_BYTES):
        raise InstallationProfileError("SETTINGS_FILE_UNSAFE")
    if path.parent.exists() and not path.parent.is_dir():
        raise InstallationProfileError("SETTINGS_DIRECTORY_UNSAFE")


def _validate(document: dict) -> dict:
    if not isinstance(document, dict) or set(document) != {
        "schema", "revision", "active_profile", "profiles"
    } or document["schema"] != SCHEMA:
        raise InstallationProfileError("SETTINGS_SCHEMA_INVALID")
    revision = document["revision"]
    if type(revision) is not int or not 0 <= revision <= 2**31 - 1:
        raise InstallationProfileError("SETTINGS_REVISION_INVALID")
    profiles = document["profiles"]
    if not isinstance(profiles, dict) or not 1 <= len(profiles) <= MAX_PROFILES:
        raise InstallationProfileError("PROFILE_COUNT_INVALID")
    if "default" not in profiles or document["active_profile"] not in profiles:
        raise InstallationProfileError("ACTIVE_OR_DEFAULT_PROFILE_MISSING")
    for name, overrides in profiles.items():
        if not isinstance(name, str) or not PROFILE_ID.fullmatch(name):
            raise InstallationProfileError("PROFILE_ID_INVALID")
        if not isinstance(overrides, dict):
            raise InstallationProfileError("PROFILE_OVERRIDES_INVALID")
        for key, value in overrides.items():
            if key not in DEFAULTS or type(value) is not bool:
                raise InstallationProfileError("SETTING_UNKNOWN_OR_TYPE_INVALID")
    return document


def read_document(path: Path | None = None) -> dict:
    path = settings_path() if path is None else Path(path)
    _safe_path(path)
    if not path.exists():
        return _empty()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError, OSError) as exc:
        raise InstallationProfileError("SETTINGS_CONTENT_INVALID") from exc
    return _validate(payload)


def view(path: Path | None = None, *, profile_id: str | None = None) -> dict:
    document = read_document(path)
    selected = profile_id if profile_id is not None else document["active_profile"]
    if selected not in document["profiles"]:
        raise InstallationProfileError("PROFILE_NOT_FOUND")
    overrides = document["profiles"][selected]
    return {
        "schema": SCHEMA,
        "state": "PROFILE_READ_ONLY",
        "revision": document["revision"],
        "profile_id": selected,
        "active_profile": document["active_profile"],
        "profiles": sorted(document["profiles"]),
        "settings": {**DEFAULTS, **overrides},
        "overrides": dict(overrides),
        "game_control_permit": None,
        "proof_ceiling": "LOCAL_PROFILE_PREFERENCE_ONLY",
    }


def _mutation(path: Path | None, change: Callable[[dict], None]) -> dict:
    """Single local writer; corrupt input is never overwritten or reset implicitly."""
    path = settings_path() if path is None else Path(path)
    _safe_path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    _safe_path(path)
    lock = path.with_suffix(".lock")
    if lock.is_symlink():
        raise InstallationProfileError("SETTINGS_LOCK_UNSAFE")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise InstallationProfileError("SETTINGS_WRITER_BUSY") from exc
    temporary = None
    try:
        os.close(fd)
        original = read_document(path)
        updated = json.loads(json.dumps(original))
        change(updated)
        _validate(updated)
        if updated == original:
            return view(path)
        updated["revision"] += 1
        _validate(updated)
        raw = json.dumps(updated, sort_keys=True, indent=2) + "\n"
        if len(raw.encode("utf-8")) > MAX_BYTES:
            raise InstallationProfileError("SETTINGS_FILE_TOO_LARGE")
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", prefix=".settings-", suffix=".tmp",
            dir=path.parent, delete=False,
        ) as handle:
            temporary = Path(handle.name)
            if os.name != "nt":
                os.chmod(temporary, stat.S_IRUSR | stat.S_IWUSR)
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        _safe_path(path)
        os.replace(temporary, path)
        temporary = None
        return view(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def create_profile(profile_id: str, path: Path | None = None) -> dict:
    if not isinstance(profile_id, str) or not PROFILE_ID.fullmatch(profile_id):
        raise InstallationProfileError("PROFILE_ID_INVALID")
    def change(doc: dict) -> None:
        if profile_id in doc["profiles"]:
            raise InstallationProfileError("PROFILE_ALREADY_EXISTS")
        if len(doc["profiles"]) >= MAX_PROFILES:
            raise InstallationProfileError("PROFILE_LIMIT_REACHED")
        doc["profiles"][profile_id] = {}
    return _mutation(path, change)


def choose_profile(profile_id: str, path: Path | None = None) -> dict:
    def change(doc: dict) -> None:
        if profile_id not in doc["profiles"]:
            raise InstallationProfileError("PROFILE_NOT_FOUND")
        doc["active_profile"] = profile_id
    return _mutation(path, change)


def set_toggle(key: str, enabled: bool, path: Path | None = None,
               *, profile_id: str | None = None) -> dict:
    if key not in DEFAULTS or type(enabled) is not bool:
        raise InstallationProfileError("SETTING_UNKNOWN_OR_TYPE_INVALID")
    def change(doc: dict) -> None:
        selected = profile_id if profile_id is not None else doc["active_profile"]
        if selected not in doc["profiles"]:
            raise InstallationProfileError("PROFILE_NOT_FOUND")
        overrides = doc["profiles"][selected]
        if enabled == DEFAULTS[key]:
            overrides.pop(key, None)
        else:
            overrides[key] = enabled
    return _mutation(path, change)


def reset_toggle(key: str, path: Path | None = None,
                 *, profile_id: str | None = None) -> dict:
    if key not in DEFAULTS:
        raise InstallationProfileError("SETTING_UNKNOWN")
    return set_toggle(key, DEFAULTS[key], path, profile_id=profile_id)


def household_ledger_path(
    *,
    profile_id: str,
    scope_id: str,
    settings_file: Path | None = None,
) -> Path:
    """Private local state owner for one installation-profile/save/household.

    This does not create a file or scan saves. The caller must bind observed
    portrait identities through household_judgment.bind_household_scope first.
    """
    if not isinstance(scope_id, str) or not re.fullmatch(r"[0-9a-f]{64}", scope_id):
        raise InstallationProfileError("HOUSEHOLD_SCOPE_ID_INVALID")
    settings_file = settings_path() if settings_file is None else Path(settings_file)
    _safe_path(settings_file)
    view(settings_file, profile_id=profile_id)  # Existing named profile only.
    return settings_file.parent / "households" / profile_id / (scope_id + ".json")
