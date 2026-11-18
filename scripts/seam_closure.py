"""Seam Closure Loop: bounded, effect-free recovery handoffs from Play receipts.

A seam is a missing executable capability, not a game-input authorization.
This module identifies source owners and persists private per-run evidence.
The local agent may implement a missing handler, but cannot treat classification
as permission to run Shell, read saves, open a protected slot, or click the game.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from uuid import uuid4

SCHEMA = "betterinstincts.seam-closure/v1"
MAX_EVENTS = 32
MAX_BYTES = 32_768
MAX_GAPS = 8
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


def record(path: Path, receipt: dict) -> dict | None:
    """Persist each distinct blocked gate before it is overwritten by a later stage.

    Safe on repeated write_result calls; source-only progress never closes live
    certification. All records stay in the existing private run folder.
    """
    if receipt.get("status") != "blocked" or not receipt.get("automation_gaps"):
        return None
    run_id = receipt.get("run_id")
    if not isinstance(run_id, str) or not RUN.fullmatch(run_id):
        raise ValueError("SEAM_RUN_ID_INVALID")
    gaps = receipt["automation_gaps"]
    if not isinstance(gaps, list) or len(gaps) > MAX_GAPS:
        raise ValueError("SEAM_GAP_COUNT_INVALID")
    path = Path(path)
    target = _event_file(path, run_id)
    if target.is_symlink():
        raise ValueError("SEAM_RECEIPT_STORE_UNSAFE")
    events = read_events(path, run_id)
    known = {row.get("seam_id") for row in events}
    observed = []
    for gap in gaps:
        event = identify(gap, run_id)
        observed.append(event)
        if event["seam_id"] not in known:
            if len(events) >= MAX_EVENTS:
                raise ValueError("SEAM_RECEIPT_STORE_FULL")
            event["observed_at"] = datetime.now(timezone.utc).isoformat()
            events.append(event)
            known.add(event["seam_id"])
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
    return {
        "schema": SCHEMA, "state": "OPEN", "event_count": len(events),
        "event_file": str(target), "current": observed,
        "effect_admission": "NOT_GRANTED",
    }


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
    if latest.get("status") != "blocked":
        return empty
    events = read_events(path, run_id)
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
    }
