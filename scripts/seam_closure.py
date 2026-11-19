"""Seam Closure Loop: bounded, effect-free recovery handoffs from Play receipts.

A seam is a missing executable capability, not a game-input authorization.
This module identifies source owners and persists private per-run evidence.
The local agent may implement a missing handler, but cannot treat classification
as permission to run Shell, read saves, open a protected slot, or click the game.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import errno
import hashlib
import json
import os
from pathlib import Path
import re
from stat import S_ISREG
from time import monotonic, sleep
from uuid import uuid4

SCHEMA = "betterinstincts.seam-closure/v1"
MAX_EVENTS = 32
MAX_BYTES = 32_768
MAX_GAPS = 8
EVENT_LOCK_TIMEOUT = 2.0
EVENT_APPEND_PENDING = "EVENT_APPEND_PENDING"
EVENT_STORE_BUSY = "SEAM_RECEIPT_STORE_BUSY_RETRY"
CODE = re.compile(r"^[A-Z][A-Z0-9_]{2,100}$")
STAGE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
OWNER = re.compile(r"^(?:scripts|betterinstincts)/[A-Za-z0-9_/-]+\.py$|^Start-BetterInstincts\.cmd$")
RUN = re.compile(r"^[a-f0-9]{32}$")

# The existing owner is the handler. A recorded handler is not evidence it ran.
# Safety and host observation are distinct from source availability.
ROUTES = {
    "bootstrap": ("CHECKOUT_RECONCILIATION", "Start-BetterInstincts.cmd", "HOST_RUNNER_REQUIRED"),
    "checkout": ("CHECKOUT_RECONCILIATION", "scripts/continue_certification.py", "POLICY_OR_HOST_HOLD"),
    "host": ("WINDOWS_GAME_SESSION", "scripts/play.py", "HOST_RUNNER_REQUIRED"),
    "save_context": ("PRIVATE_STARTUP_CONTEXT", "scripts/startup_handoff.py", "HOST_BINDING_REQUIRED"),
    "startup_catalog": ("PROCESS_BOUND_SAVE_CATALOG", "scripts/startup_handoff.py", "HOST_OBSERVATION_REQUIRED"),
    "dev_save_candidate": ("AUTHORIZED_LAB_REGISTRY", "scripts/launch_save_route.py", "PRIVATE_EVIDENCE_REQUIRED"),
    "dev_calibration": ("EXACT_SLOT_MENU_CALIBRATION", "scripts/game_host.py", "HOST_OBSERVATION_REQUIRED"),
    "game_process": ("EXISTING_GAME_PROCESS", "scripts/smart_start.py", "HOST_OBSERVATION_REQUIRED"),
    "existing_game": ("PRESERVE_EXISTING_SESSION", "scripts/play.py", "HOST_OBSERVATION_REQUIRED"),
    "native_restock_binding": ("EXACT_BUILD_NATIVE_BRIDGE", "scripts/lab_upgrade_parts.py", "IMPLEMENTATION_OR_HOST_PROOF_REQUIRED"),
    "lab_upgrade_parts": ("NATIVE_RESTOCK_RECONCILIATION", "scripts/lab_upgrade_parts.py", "OBSERVE_BEFORE_RETRY"),
    "native_responder_handoff": ("NATIVE_RESPONDER_OUTCOME", "scripts/lab_upgrade_parts.py", "OBSERVE_BEFORE_RETRY"),
    "startup_handoff": ("STARTUP_RESPONDER_OUTCOME", "scripts/startup_handoff.py", "OBSERVE_BEFORE_RETRY"),
    "dev_save_dispatch": ("CURRENT_GAME_SAVE_IDENTITY", "scripts/game_host.py", "OBSERVE_BEFORE_RETRY"),
    "certification": ("ACTIVE_CERTIFICATION_CONTINUATION", "scripts/continue_certification.py", "PRESERVE_ACTIVE_SESSION"),
    "receipt": ("PRIVATE_RECEIPT_RECOVERY", "scripts/launch_receipt.py", "PRIVATE_STORAGE_REQUIRED"),
}
# A denied host tool is never a missing permit to manufacture.
POLICY_DENIALS = frozenset({
    "OPERATOR_DESKTOP_BOUNDARY", "UNADMITTED_DESKTOP_SHELL",
    "PROTECTED_SLOT", "CONTROL_PERMIT_DENIED",
})


class EventStoreBusy(ValueError):
    """The bounded per-run writer lock could not be acquired."""


def _reason_code(value: object) -> str:
    return value if isinstance(value, str) and CODE.fullmatch(value) else "UNCLASSIFIED_REASON"


def _safe_stage(value: object) -> str:
    return value if isinstance(value, str) and STAGE.fullmatch(value) else "unclassified"


def identify(gap: dict, run_id: str) -> dict:
    """Classify one gap without copying raw host errors or private filenames."""
    if not isinstance(gap, dict) or not RUN.fullmatch(run_id):
        raise ValueError("SEAM_INVALID_INPUT")
    stage = _safe_stage(gap.get("stage"))
    reason_code = _reason_code(gap.get("reason"))
    source = gap.get("repository_owner")
    source = source if isinstance(source, str) and OWNER.fullmatch(source) else None
    route = ROUTES.get(stage)
    if reason_code in POLICY_DENIALS:
        capability, handler, state = "EXPLICIT_DESKTOP_AUTHORITY", None, "POLICY_HOLD"
    elif route is None:
        capability, handler, state = "UNREGISTERED_SEAM", None, "IMPLEMENTATION_REQUIRED"
    else:
        capability, handler, state = route
    fingerprint = json.dumps([stage, reason_code, source, capability], separators=(",", ":"))
    return {
        "schema": SCHEMA, "type": "BLOCKED_GATE", "run_id": run_id,
        "seam_id": "scl-" + hashlib.sha256(fingerprint.encode("ascii")).hexdigest()[:20],
        "stage": stage, "reason_code": reason_code,
        "capability": capability, "canonical_owner": handler or source,
        "resolution_state": state,
        "effect_admission": "NOT_GRANTED",
        "proof_ceiling": "CLASSIFIED_REPOSITORY_GATE_NOT_GAME_OBSERVATION",
    }


def _event_file(path: Path, run_id: str) -> Path:
    if path.name != "launch.json" or path.is_symlink() or path.parent.is_symlink() or path.parent.name != run_id:
        raise ValueError("SEAM_RECEIPT_PATH_UNSAFE")
    return path.parent / "seam-events.json"


def read_events(path: Path, run_id: str) -> list[dict]:
    """Read only the selected run; never inspect other receipt directories."""
    target = _event_file(Path(path), run_id)
    if not target.exists():
        return []
    if target.is_symlink() or not target.is_file() or target.stat().st_size > MAX_BYTES:
        raise ValueError("SEAM_RECEIPT_STORE_UNSAFE")
    data = json.loads(target.read_text(encoding="utf-8"))
    events = data.get("events") if isinstance(data, dict) and data.get("schema") == SCHEMA and data.get("run_id") == run_id else None
    if not isinstance(events, list) or len(events) > MAX_EVENTS or any(not isinstance(e, dict) or e.get("run_id") != run_id or e.get("schema") != SCHEMA for e in events):
        raise ValueError("SEAM_RECEIPT_STORE_INVALID")
    return events


def _save_events(path: Path, run_id: str, events: list[dict]) -> Path:
    """Atomic, bounded event write for one selected private Play run."""
    target = _event_file(path, run_id)
    if target.is_symlink() or len(events) > MAX_EVENTS:
        raise ValueError("SEAM_RECEIPT_STORE_UNSAFE")
    raw = json.dumps({"schema": SCHEMA, "run_id": run_id, "events": events}, sort_keys=True, indent=2) + "\n"
    if len(raw.encode("utf-8")) > MAX_BYTES:
        raise ValueError("SEAM_RECEIPT_TOO_LARGE")
    temp = target.with_name(uuid4().hex + ".tmp")
    try:
        with temp.open("x", encoding="utf-8") as stream:
            stream.write(raw)
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)
    return target


@contextmanager
def _event_writer_lock(target: Path):
    """Serialize host writes across processes, including after a writer exits."""
    lock = target.with_suffix(".lock")
    if lock.is_symlink():
        raise ValueError("SEAM_RECEIPT_STORE_UNSAFE")
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    fd = os.open(lock, flags, 0o600)
    try:
        if not S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("SEAM_RECEIPT_STORE_UNSAFE")
        deadline = monotonic() + EVENT_LOCK_TIMEOUT
        while True:
            try:
                if os.name == "nt":
                    import msvcrt

                    # An open handle owns the first byte even in an empty lock file.
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as error:
                if error.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise
                if monotonic() >= deadline:
                    raise EventStoreBusy(EVENT_STORE_BUSY) from error
                sleep(0.02)
        yield
    finally:
        os.close(fd)


def _append_events(path: Path, run_id: str, observed: list[dict], *, observed_at: str | None = None) -> int:
    target = _event_file(path, run_id)
    with _event_writer_lock(target):
        if target.is_symlink():
            raise ValueError("SEAM_RECEIPT_STORE_UNSAFE")
        events = read_events(path, run_id)
        known = {(row.get("type"), row.get("seam_id")) for row in events}
        original_count = len(events)
        for event in observed:
            key = (event["type"], event["seam_id"])
            if key not in known:
                if len(events) >= MAX_EVENTS:
                    raise ValueError("SEAM_RECEIPT_STORE_FULL")
                event["observed_at"] = observed_at or datetime.now(timezone.utc).isoformat()
                events.append(event)
                known.add(key)
        if len(events) != original_count:
            _save_events(path, run_id, events)
        return len(events)


def _identify_gaps(receipt: dict, run_id: str) -> list[dict]:
    gaps = receipt.get("automation_gaps")
    if not isinstance(gaps, list) or not 0 < len(gaps) <= MAX_GAPS:
        raise ValueError("SEAM_GAP_COUNT_INVALID")
    return [identify(gap, run_id) for gap in gaps]


def record(path: Path, receipt: dict, *, defer_if_busy: bool = False) -> dict | None:
    """Persist each distinct blocked gate before it is overwritten by a later stage.

    Safe on repeated write_result calls; source-only progress never closes live
    certification. All records stay in the existing private run folder.
    """
    if receipt.get("status") != "blocked" or not receipt.get("automation_gaps"):
        return None
    run_id = receipt.get("run_id")
    if not isinstance(run_id, str) or not RUN.fullmatch(run_id):
        raise ValueError("SEAM_RUN_ID_INVALID")
    path = Path(path)
    target = _event_file(path, run_id)
    observed = _identify_gaps(receipt, run_id)
    observed_at = datetime.now(timezone.utc).isoformat()
    previous = receipt.get("seam_closure")
    if isinstance(previous, dict) and previous.get("state") == EVENT_APPEND_PENDING:
        timestamp = previous.get("observed_at")
        if not isinstance(timestamp, str) or datetime.fromisoformat(timestamp).tzinfo is None:
            raise ValueError("SEAM_PENDING_OBSERVATION_TIME_INVALID")
        observed_at = timestamp
    closure = {
        "schema": SCHEMA,
        "event_file": str(target), "current": observed,
        "effect_admission": "NOT_GRANTED",
    }
    try:
        event_count = _append_events(path, run_id, observed, observed_at=observed_at)
    except EventStoreBusy:
        if not defer_if_busy:
            raise
        return {**closure, "state": EVENT_APPEND_PENDING, "reason_code": EVENT_STORE_BUSY,
                "observed_at": observed_at}
    return {**closure, "state": "OPEN", "event_count": event_count}


def record_native_notice(
    path: Path, notice: dict, *, observed_process: dict, observed_session: str,
) -> dict:
    """Join a native adapter notice to an existing selected private Play run.

    Only an already admitted same-process host adapter should invoke this.
    The event file records sanitized semantics; matching provided process and
    session is not a replacement for fresh actual game observation.
    """
    from betterinstincts.runtime_seam import notice_for

    path = Path(path)
    if (path.name != "launch.json" or path.is_symlink() or not path.is_file()
            or path.stat().st_size > 32_768):
        raise ValueError("SEAM_NATIVE_PLAY_RECEIPT_UNSAFE")
    try:
        launch = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as error:
        raise ValueError("SEAM_NATIVE_PLAY_RECEIPT_INVALID") from error
    run_id = launch.get("run_id") if isinstance(launch, dict) else None
    if (not isinstance(run_id, str) or not RUN.fullmatch(run_id)
            or path.parent.name != run_id
            or launch.get("schema") != "betterinstincts.play-launch-receipt/v1"):
        raise ValueError("SEAM_NATIVE_PLAY_RECEIPT_INVALID")
    bound = launch.get("game_process")
    if (not isinstance(bound, dict) or not isinstance(observed_process, dict)
            or observed_process != bound or type(bound.get("pid")) is not int
            or bound["pid"] <= 0
            or not isinstance(bound.get("creation_ticks"), str)
            or not bound["creation_ticks"]
            or not isinstance(bound.get("executable"), str)
            or not bound["executable"]):
        raise ValueError("SEAM_NATIVE_PROCESS_NOT_BOUND")
    expected = notice_for(
        notice.get("reason_code") if isinstance(notice, dict) else None,
        game_build=bound.get("game_version"), session=observed_session,
    )
    if expected is None or notice != expected or notice.get("session_tag") is None:
        raise ValueError("SEAM_NATIVE_NOTICE_UNCORRELATED")
    # Correlation tags and private launch fields stay out of the event log.
    event = {
        "schema": SCHEMA, "type": "NATIVE_RUNTIME_SEAM",
        "run_id": run_id, "seam_id": notice["seam_id"],
        "stage": notice["stage"], "reason_code": notice["reason_code"],
        "capability": notice["capability"], "resolution_state": notice["resolution_state"],
        "canonical_owner": notice["canonical_owner"],
        "effect_admission": "NOT_GRANTED",
        "proof_ceiling": "CORRELATED_ADAPTER_NOTICE_NOT_GAME_CERTIFICATION",
    }
    _append_events(path, run_id, [event])
    return {"schema": SCHEMA, "state": "NATIVE_NOTICE_RECORDED",
            "run_id": run_id, "seam_id": notice["seam_id"],
            "effect_admission": "NOT_GRANTED"}


def latest_run_handoff(folder: Path) -> dict:
    """Identify the latest private Play run for an installed local agent.

    Scans only the bounded, app-owned Play receipt store. The newest run may
    supersede an earlier blocked run; never resurrect a stale gate as current.
    The summary contains no paths, roster, slot or untrusted exception strings.
    """
    folder = Path(folder)
    empty = {"schema": SCHEMA, "state": "NO_CURRENT_BLOCKED_RUN",
             "effect_admission": "NOT_GRANTED"}
    if not folder.exists():
        return empty
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("SEAM_RUNTIME_STORE_UNSAFE")
    candidates = []
    entries = list(folder.iterdir())
    if len(entries) > 128:
        raise ValueError("SEAM_RUNTIME_STORE_FULL")
    for directory in entries:
        if not RUN.fullmatch(directory.name) or directory.is_symlink() or not directory.is_dir():
            continue
        path = directory / "launch.json"
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 32_768:
            continue
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
            if (not isinstance(receipt, dict)
                    or receipt.get("schema") != "betterinstincts.play-launch-receipt/v1"
                    or receipt.get("run_id") != directory.name):
                continue
            stamp = datetime.fromisoformat(receipt["started_at"])
            if stamp.tzinfo is None:
                continue
            candidates.append((stamp, directory.name, receipt, path))
        except (ValueError, KeyError, TypeError, UnicodeError):
            continue
    if not candidates:
        return empty
    _, run_id, latest, path = max(candidates, key=lambda x: (x[0], x[1]))
    events = read_events(path, run_id)
    if latest.get("status") != "blocked":
        native = [row for row in events if row.get("type") == "NATIVE_RUNTIME_SEAM"]
        if not native:
            return empty
        return {
            "schema": SCHEMA, "state": "HISTORICAL_NATIVE_NOTICES_REOBSERVE",
            "run_id": run_id,
            "seams": [{key: entry[key] for key in (
                "seam_id", "stage", "reason_code", "capability",
                "canonical_owner", "resolution_state", "effect_admission",
            )} for entry in native[-MAX_GAPS:]],
            "proof_ceiling": "NATIVE_ADAPTER_NOTICE_NOT_CURRENT_GAME_PROOF",
            "effect_admission": "NOT_GRANTED",
        }
    append_status = {}
    closure = latest.get("seam_closure")
    if isinstance(closure, dict) and closure.get("state") == EVENT_APPEND_PENDING:
        pending = {(row["type"], row["seam_id"]): row for row in _identify_gaps(latest, run_id)}
        events = [row for row in events if (row.get("type"), row.get("seam_id")) not in pending]
        events.extend(pending.values())
        append_status = {"event_append_state": EVENT_APPEND_PENDING}
    if not events:
        return empty
    return {
        "schema": SCHEMA, "state": "BLOCKED_RUN_RECOVERABLE",
        "run_id": run_id,
        "stage": _safe_stage(latest.get("stage")),
        "seams": [{key: entry[key] for key in (
            "seam_id", "stage", "reason_code", "capability",
            "canonical_owner", "resolution_state", "effect_admission",
        )} for entry in events[-MAX_GAPS:]],
        "proof_ceiling": "PRIVATE_LAUNCH_RECEIPT_ONLY_REOBSERVE_GAME_AND_SCOPE",
        "effect_admission": "NOT_GRANTED",
        **append_status,
    }
