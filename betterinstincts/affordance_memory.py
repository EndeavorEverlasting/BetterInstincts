"""Bounded, token-only cross-session affordance memory for opt-in hover observations.

Session hover_learning remains the authoritative input validator. This module
retains compact, evidence-qualified associations, not raw UI text, screenshots,
global keystrokes or game-control instructions. A learned entry is advisory.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Mapping

from betterinstincts.hover_learning import _event as validate_hover_event

SCHEMA = "betterinstincts.affordance-memory/v1"
MAX_ENTRIES = 128
MAX_EVENTS = 512
MAX_PENDING = 64
MAX_BYTES = 128_000
SCOPE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}$")
PATCH = re.compile(r"^[0-9]+(?:\.[0-9]+){1,5}$")


class AffordanceMemoryError(ValueError):
    pass


def empty_index() -> dict:
    return {"schema": SCHEMA, "revision": 0, "entries": {},
            "seen_event_ids": [], "pending_actions": {}}


def _validate(index: Mapping) -> dict:
    if not isinstance(index, dict) or set(index) != {
        "schema", "revision", "entries", "seen_event_ids", "pending_actions"
    } or index.get("schema") != SCHEMA:
        raise AffordanceMemoryError("AFFORDANCE_INDEX_SCHEMA_INVALID")
    if type(index["revision"]) is not int or index["revision"] < 0:
        raise AffordanceMemoryError("AFFORDANCE_REVISION_INVALID")
    if not isinstance(index["entries"], dict) or len(index["entries"]) > MAX_ENTRIES:
        raise AffordanceMemoryError("AFFORDANCE_ENTRIES_INVALID")
    if not isinstance(index["seen_event_ids"], list) or len(index["seen_event_ids"]) > MAX_EVENTS:
        raise AffordanceMemoryError("AFFORDANCE_EVENT_IDS_INVALID")
    if not isinstance(index["pending_actions"], dict) or len(index["pending_actions"]) > MAX_PENDING:
        raise AffordanceMemoryError("AFFORDANCE_PENDING_INVALID")
    if any(not isinstance(k, str) or not isinstance(v, dict)
           for k, v in index["entries"].items()):
        raise AffordanceMemoryError("AFFORDANCE_ENTRY_INVALID")
    if len(json.dumps(index).encode("utf-8")) > MAX_BYTES:
        raise AffordanceMemoryError("AFFORDANCE_INDEX_OVERSIZE")
    return index


def _scope(game_version: str | None, lot_id: str | None) -> tuple[str, str]:
    if game_version is not None and (not isinstance(game_version, str) or
                                    not PATCH.fullmatch(game_version)):
        raise AffordanceMemoryError("GAME_VERSION_INVALID")
    if lot_id is not None and (not isinstance(lot_id, str) or not SCOPE.fullmatch(lot_id)):
        raise AffordanceMemoryError("LOT_ID_INVALID")
    return game_version or "UNKNOWN_PATCH", lot_id or "UNKNOWN_LOT"


def _key(patch: str, target: str, tooltip: str) -> str:
    return "|".join((patch, target, tooltip))


def ingest(
    index: Mapping,
    event: Mapping,
    *,
    session_id: str,
    game_version: str | None = None,
    lot_id: str | None = None,
    hover_state: Mapping | None = None,
) -> tuple[dict, dict]:
    """Merge one previously accepted hover event. Replay is idempotent.

    A matching observed action and operator-reviewed outcome can strengthen
    an association, but neither hover nor outcome permits a game click.
    """
    src = _validate(index)
    if not isinstance(session_id, str) or not SCOPE.fullmatch(session_id):
        raise AffordanceMemoryError("SESSION_ID_INVALID")
    patch, lot = _scope(game_version, lot_id)
    try:
        validated = validate_hover_event(event)
    except (ValueError, KeyError, TypeError) as exc:
        raise AffordanceMemoryError("HOVER_EVENT_INVALID:" + str(exc)) from exc
    event_id = f"{session_id}:{validated['id']}"
    if event_id in src["seen_event_ids"]:
        return src, {"state": "ALREADY_INDEXED", "recorded": False, "execute_allowed": False}

    entries = {key: dict(row) for key, row in src["entries"].items()}
    pending = {key: dict(row) for key, row in src["pending_actions"].items()}
    kind = validated["kind"]
    at_ms = validated["at_ms"]
    matched = None
    if kind == "tooltip_visible":
        matched = _key(patch, validated["target_ref"], validated["tooltip_ref"])
        row = entries.get(matched, {
            "game_version": patch, "target_ref": validated["target_ref"],
            "tooltip_ref": validated["tooltip_ref"], "seen_count": 0,
            "last_seen_ms": at_ms, "lots": [], "action_refs": [],
            "reviewed_helpful": 0, "reviewed_harmful": 0, "status": "CANDIDATE",
        })
        row["seen_count"] += 1
        row["last_seen_ms"] = at_ms
        if lot not in row["lots"]:
            row["lots"] = (row["lots"] + [lot])[-8:]
        entries[matched] = row
    elif kind == "action":
        # hover_learning itself binds an action to a visible tooltip; use that
        # normalized event rather than trusting a caller-supplied tooltip.
        if hover_state is None or not isinstance(hover_state.get("events"), list):
            raise AffordanceMemoryError("HOVER_STATE_REQUIRED_FOR_ACTION")
        matched_events = [e for e in hover_state["events"] if e.get("id") == validated["id"]]
        if len(matched_events) != 1 or matched_events[0].get("kind") != "action":
            raise AffordanceMemoryError("MATCHED_HOVER_ACTION_REQUIRED")
        tooltip = matched_events[0].get("tooltip_ref")
        if not isinstance(tooltip, str):
            raise AffordanceMemoryError("TOOLTIP_ASSOCIATION_REQUIRED")
        matched = _key(patch, validated["target_ref"], tooltip)
        if matched not in entries:
            # Action may have been observed across a retained/restarted window.
            # Preserve the factual association but not a claimed prior tooltip count.
            entries[matched] = {
                "game_version": patch, "target_ref": validated["target_ref"],
                "tooltip_ref": tooltip, "seen_count": 0,
                "last_seen_ms": at_ms, "lots": [lot], "action_refs": [],
                "reviewed_helpful": 0, "reviewed_harmful": 0, "status": "CANDIDATE",
            }
        row = entries[matched]
        row["last_seen_ms"] = at_ms
        if validated["action_ref"] not in row["action_refs"]:
            row["action_refs"] = (row["action_refs"] + [validated["action_ref"]])[-16:]
        pending[f"{session_id}:{validated['interaction_ref']}"] = {
            "entry": matched, "at_ms": at_ms
        }
    elif kind == "outcome":
        interaction = f"{session_id}:{validated['interaction_ref']}"
        reference = pending.pop(interaction, None)
        if reference and reference["entry"] in entries and validated["operator_reviewed"]:
            row = entries[reference["entry"]]
            field = "reviewed_helpful" if validated["outcome"] == "helpful" else "reviewed_harmful"
            if validated["outcome"] in {"helpful", "harmful"}:
                row[field] += 1
                count = row["reviewed_helpful"] + row["reviewed_harmful"]
                if count >= 3 and row["reviewed_helpful"] >= 3 and row["reviewed_helpful"] / count >= .75:
                    row["status"] = "REVIEWED_ASSOCIATION_NOT_GAME_PROOF"
                matched = reference["entry"]

    # Preserve most recent bounded discoveries; drop any pending references to
    # evicted entries. These limits are intentionally independent of sessions.
    entries = dict(sorted(
        entries.items(), key=lambda item: (-item[1]["last_seen_ms"], item[0])
    )[:MAX_ENTRIES])
    pending = {k: v for k, v in list(pending.items())[-MAX_PENDING:]
               if v["entry"] in entries}
    updated = {
        "schema": SCHEMA, "revision": src["revision"] + 1,
        "entries": entries,
        "seen_event_ids": (src["seen_event_ids"] + [event_id])[-MAX_EVENTS:],
        "pending_actions": pending,
    }
    _validate(updated)
    return updated, {
        "state": "AFFORDANCE_EVENT_INDEXED", "recorded": True,
        "entry_key": matched, "revision": updated["revision"],
        "execute_allowed": False, "control_permit": None,
    }


def load_index(path: Path) -> dict:
    path = Path(path)
    if not path.exists():
        return empty_index()
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise AffordanceMemoryError("AFFORDANCE_INDEX_FILE_UNSAFE")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AffordanceMemoryError("AFFORDANCE_INDEX_READ_FAILED") from exc
    return _validate(data)


def record_event(
    path: Path,
    event: Mapping,
    *,
    session_id: str,
    game_version: str | None = None,
    lot_id: str | None = None,
    hover_state: Mapping | None = None,
) -> dict:
    """Atomic, bounded cross-session update under existing opt-in host lifecycle."""
    path = Path(path)
    if path.is_symlink() or path.parent.is_symlink():
        raise AffordanceMemoryError("AFFORDANCE_PATH_SYMLINK_FORBIDDEN")
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(".lock")
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise AffordanceMemoryError("AFFORDANCE_INDEX_WRITER_BUSY") from exc
    try:
        os.close(fd)
        updated, receipt = ingest(
            load_index(path), event, session_id=session_id,
            game_version=game_version, lot_id=lot_id, hover_state=hover_state
        )
        if not receipt["recorded"]:
            return receipt
        raw = json.dumps(updated, sort_keys=True, indent=2) + "\n"
        if len(raw.encode("utf-8")) > MAX_BYTES:
            raise AffordanceMemoryError("AFFORDANCE_INDEX_OVERSIZE")
        temp = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent,
                prefix=".affordance-", suffix=".tmp", delete=False
            ) as fp:
                temp = Path(fp.name)
                fp.write(raw)
                fp.flush()
                os.fsync(fp.fileno())
            os.replace(temp, path)
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)
        return {**receipt, "entry_count": len(updated["entries"]),
                "index_path": str(path)}
    finally:
        lock.unlink(missing_ok=True)


def known_targets(index: Mapping, *, game_version: str | None) -> set[str]:
    """Patch-specific observed tooltips, excluding unscoped/other-patch claims."""
    _validate(index)
    if game_version is None:
        return set()
    _scope(game_version, None)
    return {row["target_ref"] for row in index["entries"].values()
            if row["game_version"] == game_version and row["seen_count"] > 0}
