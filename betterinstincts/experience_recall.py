"""Sanitized, bounded recall of *past* Sims outcomes; never a game controller.

An experience is identified by exact mechanics, patch, mod/pack profile and
choice -- not by a new screenshot or Sim name. Repeated encounters are reads,
not new training rows or another gameplay experiment. Review current live
state independently before any action; this module grants no permits.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Mapping

SCHEMA = "betterinstincts.experience-recall/v1"
EVENT_SCHEMA = "betterinstincts.experience-observation/v1"
PROOF = "SANITIZED_HISTORICAL_CLAIM_NOT_AUTHENTICATED_CURRENT_GAMEPLAY"
MAX_RECORDS = 128
MAX_BYTES = 128_000
PATCH = re.compile(r"^[0-9]+(?:\.[0-9]+){3}$")
TOKEN = re.compile(r"^[a-z][a-z0-9_.:-]{1,95}$")
REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{2,127}$")
CONTEXT_KEYS = frozenset({
    "domain", "game_build", "installation_profile", "mechanic_id", "choice_id",
})
RECORD_KEYS = frozenset({
    "context", "result", "evidence_level", "evidence_ref", "observed_at_ms",
})
EVIDENCE_LEVELS = frozenset({
    "SOURCE_INSPECTED", "OPERATOR_REPORTED_LIVE",
    "LOCAL_ARTIFACT_VERIFIED", "NATIVE_RECEIPT",
})
ROOT = Path(__file__).resolve().parents[1]


class ExperienceRecallError(ValueError):
    pass


def _token(value: object, name: str) -> str:
    if type(value) is not str or not TOKEN.fullmatch(value):
        raise ExperienceRecallError("INVALID_" + name.upper())
    return value


def _context(value: object) -> dict:
    if not isinstance(value, Mapping) or set(value) != CONTEXT_KEYS:
        raise ExperienceRecallError("EXACT_EXPERIENCE_CONTEXT_REQUIRED")
    if type(value.get("game_build")) is not str or not PATCH.fullmatch(value["game_build"]):
        raise ExperienceRecallError("EXACT_GAME_BUILD_REQUIRED")
    return {
        "domain": _token(value["domain"], "domain"),
        "game_build": value["game_build"],
        "installation_profile": _token(value["installation_profile"], "installation_profile"),
        "mechanic_id": _token(value["mechanic_id"], "mechanic_id"),
        "choice_id": _token(value["choice_id"], "choice_id"),
    }


def _key(context: Mapping) -> str:
    raw = json.dumps(_context(context), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _record(event: Mapping) -> dict:
    if not isinstance(event, Mapping) or set(event) != RECORD_KEYS | {"schema"}:
        raise ExperienceRecallError("EXPERIENCE_EVENT_FIELDS_INVALID")
    if event.get("schema") != EVENT_SCHEMA:
        raise ExperienceRecallError("EXPERIENCE_EVENT_SCHEMA_INVALID")
    context = _context(event["context"])
    result = _token(event["result"], "result")
    level = event["evidence_level"]
    if type(level) is not str or level not in EVIDENCE_LEVELS:
        raise ExperienceRecallError("UNRECOGNIZED_PROVENANCE")
    ref = event["evidence_ref"]
    if type(ref) is not str or not REF.fullmatch(ref):
        raise ExperienceRecallError("SANITIZED_EVIDENCE_REF_REQUIRED")
    observed = event["observed_at_ms"]
    if type(observed) is not int or observed <= 0:
        raise ExperienceRecallError("OBSERVATION_TIME_REQUIRED")
    return {
        "context": context, "result": result,
        "evidence_level": level, "evidence_ref": ref,
        "observed_at_ms": observed,
    }


def empty_memory() -> dict:
    return {"schema": SCHEMA, "records": {}}


def _validate(memory: Mapping) -> dict:
    if not isinstance(memory, Mapping) or set(memory) != {"schema", "records"}:
        raise ExperienceRecallError("MEMORY_SCHEMA_INVALID")
    if memory["schema"] != SCHEMA or not isinstance(memory["records"], dict):
        raise ExperienceRecallError("MEMORY_SCHEMA_INVALID")
    if len(memory["records"]) > MAX_RECORDS:
        raise ExperienceRecallError("EXPERIENCE_MEMORY_FULL")
    for key, record in memory["records"].items():
        validated = _record({"schema": EVENT_SCHEMA, **record})
        if key != _key(validated["context"]):
            raise ExperienceRecallError("MEMORY_FINGERPRINT_MISMATCH")
    if len(json.dumps(memory, sort_keys=True).encode("utf-8")) > MAX_BYTES:
        raise ExperienceRecallError("EXPERIENCE_MEMORY_TOO_LARGE")
    return deepcopy(dict(memory))


def remember(memory: Mapping, event: Mapping) -> tuple[dict, dict]:
    """Create only on the first new semantic experience; no repeated writes."""
    existing = _validate(memory)
    record = _record(event)
    key = _key(record["context"])
    prior = existing["records"].get(key)
    baseline = {
        "experience_key": key, "execute_allowed": False,
        "control_permit": None, "current_dialog_completed": False,
        "proof_ceiling": PROOF,
    }
    if prior is not None:
        if prior["result"] != record["result"]:
            return existing, {**baseline, "state": "CONFLICT_REVIEW_REQUIRED", "recorded": False}
        return existing, {**baseline, "state": "ALREADY_KNOWN", "recorded": False}
    if len(existing["records"]) >= MAX_RECORDS:
        raise ExperienceRecallError("EXPERIENCE_MEMORY_FULL")
    updated = deepcopy(existing)
    updated["records"][key] = record
    _validate(updated)
    return updated, {**baseline, "state": "NEW_EXPERIENCE_RECORDED", "recorded": True}


def recall(memory: Mapping, context: Mapping) -> dict:
    """Return a prior lesson, NOT a claim that this current dialog was answered."""
    entries = _validate(memory)["records"]
    key = _key(context)
    baseline = {
        "experience_key": key, "execute_allowed": False,
        "control_permit": None, "current_dialog_completed": False,
        "current_outcome_proven": False, "proof_ceiling": PROOF,
    }
    record = entries.get(key)
    if record is None:
        return {**baseline, "state": "NEW_EXPERIENCE", "past_result": None,
                "historical_research_needed": True}
    return {**baseline, "state": "PAST_EXPERIENCE_RECALLED",
            "past_result": record["result"],
            "past_evidence": {
                "level": record["evidence_level"],
                "ref": record["evidence_ref"],
                "observed_at_ms": record["observed_at_ms"],
            },
            "historical_research_needed": False,
            "current_dialog_requires_fresh_admission": True}


def _path(root: Path) -> Path:
    base = Path(root)
    output = base / "dist" / "experience-recall"
    if (base.is_symlink() or (base / "dist").is_symlink()
            or output.is_symlink()):
        raise ExperienceRecallError("EXPERIENCE_PATH_SYMLINK")
    path = output / "experiences.json"
    if path.is_symlink():
        raise ExperienceRecallError("EXPERIENCE_PATH_SYMLINK")
    return path


def load_memory(*, root: Path = ROOT) -> dict:
    path = _path(root)
    if not path.exists():
        return empty_memory()
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ExperienceRecallError("EXPERIENCE_FILE_INVALID")
    try:
        return _validate(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ExperienceRecallError("EXPERIENCE_JSON_INVALID") from exc


@contextmanager
def _exclusive_writer(path: Path):
    """One bounded local writer. Never steal a crash/foreign writer's lock.

    The initial duplicate check is lock-free. Only a candidate NEW experience
    attempts this O_EXCL lock. Under it we *re-read* the latest index to avoid
    replacing another agent's just-committed independent experience.
    """
    lock = path.with_name("experiences.writer.lock")
    if lock.is_symlink() or path.parent.is_symlink():
        raise ExperienceRecallError("EXPERIENCE_PATH_SYMLINK")
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ExperienceRecallError("EXPERIENCE_WRITER_BUSY") from exc
    try:
        yield
    finally:
        os.close(fd)
        lock.unlink()


def record_new(event: Mapping, *, root: Path = ROOT) -> dict:
    """Write a genuinely new semantic fact; never lose a competing new fact."""
    path = _path(root)
    # Fast path: known and contradictory cases do not even create a lock.
    initial = load_memory(root=root)
    _, first_check = remember(initial, event)
    if not first_check["recorded"]:
        return first_check  # No mkdir, lock, temp file, rewrite or mtime change.
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or path.parent.is_symlink():
        raise ExperienceRecallError("EXPERIENCE_PATH_SYMLINK")
    with _exclusive_writer(path):
        # Another agent may have committed a different fact after our first read.
        # Recompute against the actual last-known-good index under the lock.
        latest = load_memory(root=root)
        updated, result = remember(latest, event)
        if not result["recorded"]:
            return result  # Another writer won, or a conflicting fact appeared.
        raw = (json.dumps(updated, sort_keys=True, indent=2) + "\n").encode("utf-8")
        if len(raw) > MAX_BYTES:
            raise ExperienceRecallError("EXPERIENCE_MEMORY_TOO_LARGE")
        temp = None
        try:
            with tempfile.NamedTemporaryFile("wb", dir=path.parent,
                                             prefix=".experience-", delete=False) as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
                temp = Path(handle.name)
            os.replace(temp, path)
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)
        return result
