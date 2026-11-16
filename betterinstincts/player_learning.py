"""Bounded semantic player demonstrations for an explicitly opted-in listener.

The caller owns sensing and action attribution. This module accepts sanitized
facts, pairs them with outcomes, and supplies an advisory to the host listener.
"""
from __future__ import annotations

from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
from typing import Mapping

from betterinstincts import judgment_learning as judgment
from betterinstincts.priority import CRITICAL_BELOW, NEED_ACTIONS, URGENT_BELOW

TOKEN = re.compile(r"[A-Za-z0-9_-]{3,64}")
CAPTURE = re.compile(r"capture:[A-Za-z0-9_-]{3,64}")
ACTOR = re.compile(r"sim:[A-Za-z0-9_-]{3,64}")
MAX_OUTCOME_TICKS = 8
MAX_STORE_BYTES = 1_048_576
MIN_GAIN = 0.05
MATERIAL_NEED_LOSS = 0.10
COMMON = {"kind", "run", "household", "platform", "sequence"}
FIELDS = {
    "choice": {"interaction", "owner", "scenario", "style", "previous_action",
               "action", "available_actions"},
    "outcome": {"interaction", "effect_capture", "completed", "goal_delta"},
    "query": {"scenario", "style", "previous_action", "available_actions"},
}


class PlayerLearningError(ValueError):
    pass


def _digest(*values: object) -> str:
    return sha256(json.dumps(values, separators=(",", ":")).encode("utf-8")).hexdigest()


def profile_key(value: str) -> str:
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise PlayerLearningError("INVALID_PLAYER_LEARNING_PROFILE")
    return _digest(value)


def is_profile_key(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def receipt(state: str, **fields: object) -> dict:
    return {"state": state, **fields, "control_permit": None, "execute_clicks": False,
            "proof_ceiling": "SUPPLIED_SEMANTIC_EVIDENCE_ONLY"}


def _context(payload: Mapping, needs: Mapping) -> dict:
    lowest = min(needs.values())
    need_state = "critical" if lowest < CRITICAL_BELOW else "low" if lowest < URGENT_BELOW else "stable"
    return {"scenario": payload["scenario"], "style": payload["style"],
            "previous_action": payload["previous_action"],
            "need_state": need_state, "scene": "live"}


def _validate(event: Mapping, capture: object, actor: object, patch: object,
              needs: Mapping) -> str:
    if not isinstance(event, Mapping):
        raise PlayerLearningError("INVALID_PLAYER_LEARNING_EVENT")
    kind = event.get("kind")
    if not isinstance(kind, str) or kind not in FIELDS or set(event) != COMMON | FIELDS[kind]:
        raise PlayerLearningError("INVALID_PLAYER_LEARNING_FIELDS")
    if any(not isinstance(event[k], str) or not TOKEN.fullmatch(event[k])
           for k in ("run", "household")):
        raise PlayerLearningError("INVALID_PLAYER_LEARNING_SCOPE")
    if (not isinstance(capture, str) or not CAPTURE.fullmatch(capture)
            or not isinstance(actor, str) or not ACTOR.fullmatch(actor)
            or not isinstance(patch, str) or not judgment.PATCH_RE.fullmatch(patch)
            or event["platform"] not in ("windows", "linux", "macos")
            or type(event["sequence"]) is not int or event["sequence"] < 0
            or any(not 0 <= level <= 1 for level in needs.values())):
        raise PlayerLearningError("INVALID_PLAYER_LEARNING_CONTEXT")
    if kind in {"choice", "outcome"}:
        identity = event["interaction"]
        if not isinstance(identity, str) or not TOKEN.fullmatch(identity):
            raise PlayerLearningError("INVALID_PLAYER_INTERACTION")
    if kind == "outcome":
        delta = event["goal_delta"]
        effect = event["effect_capture"]
        if (not isinstance(effect, str) or not CAPTURE.fullmatch(effect) or effect == capture
                or type(event["completed"]) is not bool
                or type(delta) not in (int, float) or not -1 <= delta <= 1):
            raise PlayerLearningError("INVALID_PLAYER_OUTCOME")
    return kind


def _available(event: Mapping, context: Mapping) -> list[str]:
    judgment.validate_context(context)
    available = event["available_actions"]
    if (not isinstance(available, list) or len(available) > 16
            or any(not isinstance(value, str) or value not in judgment.ACTIONS
                   for value in available)
            or len(set(available)) != len(available)):
        raise PlayerLearningError("INVALID_PLAYER_ACTIONS")
    return available


def _outcome(before: Mapping, after: Mapping, delta: float, completed: bool) -> str:
    for need, _ in NEED_ACTIONS:
        if after[need] < URGENT_BELOW and (
            before[need] >= URGENT_BELOW or before[need] - after[need] >= MATERIAL_NEED_LOSS
        ):
            return "harmful"
    if delta <= -MIN_GAIN:
        return "harmful"
    return "helpful" if completed and delta >= MIN_GAIN else "neutral"


def _store(path: Path, *, write: bool) -> sqlite3.Connection | None:
    if (path.is_symlink() or any(parent.is_symlink() for parent in path.parents)
            or (path.exists() and (not path.is_file() or path.stat().st_size > MAX_STORE_BYTES))):
        raise PlayerLearningError("UNSAFE_PLAYER_LEARNING_STORE")
    if not write:
        if not path.exists():
            return None
        return sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=0)
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(path, timeout=0)


def _record(path: Path, *, identity: str, captures: tuple[str, str, str],
            partition: str, context: dict, action: str, outcome: str) -> str:
    with closing(_store(path, write=True)) as db, db:
        page_size = db.execute("PRAGMA page_size").fetchone()[0]
        db.execute("PRAGMA max_page_count = " + str(MAX_STORE_BYTES // page_size))
        db.execute("BEGIN IMMEDIATE")
        db.execute("""CREATE TABLE IF NOT EXISTS episodes (
            identity TEXT PRIMARY KEY, choice_frame TEXT, outcome_frame TEXT, effect_frame TEXT,
            partition TEXT, context TEXT, action TEXT, outcome TEXT
        )""")
        row = (identity, *captures, partition, json.dumps(context, sort_keys=True), action, outcome)
        previous = db.execute("""SELECT * FROM episodes WHERE identity = ?
            OR choice_frame IN (?2, ?3, ?4) OR outcome_frame IN (?2, ?3, ?4)
            OR effect_frame IN (?2, ?3, ?4)""", (identity, *captures)).fetchall()
        if previous:
            return "OUTCOME_ALREADY_RECORDED" if previous == [row] else "OUTCOME_EVIDENCE_CONFLICT"
        if db.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] >= judgment.MAX_EXAMPLES:
            return "PLAYER_LEARNING_CAPACITY_REACHED"
        db.execute("INSERT INTO episodes VALUES (?, ?, ?, ?, ?, ?, ?, ?)", row)
        return "PLAYER_OUTCOME_" + outcome.upper()


def _advise(path: Path, *, partition: str, capture: str, context: dict,
            available: list[str], needs: Mapping) -> dict:
    if any(needs[need] < URGENT_BELOW for need, _ in NEED_ACTIONS):
        return receipt("ABSTAIN", reason="URGENT_NEEDS_FIRST")
    database = _store(path, write=False)
    if database is None:
        return receipt("ABSTAIN", reason="NO_PLAYER_DEMONSTRATIONS")
    with closing(database) as db:
        if db.execute("""SELECT 1 FROM episodes WHERE choice_frame = ?
            OR outcome_frame = ? OR effect_frame = ?""", (capture, capture, capture)).fetchone():
            return receipt("ABSTAIN", reason="TRAINING_CAPTURE_IS_NOT_FRESH")
        rows = db.execute("""SELECT action, outcome FROM episodes
            WHERE partition = ? AND context = ? ORDER BY rowid""",
            (partition, json.dumps(context, sort_keys=True))).fetchall()
    return receipt(**judgment.recommend_observed(rows, available))


def observe(
    path: Path, event: Mapping, *, pending: dict | None, tick: int, exact_patch: str,
    actor: str, capture: str, process_id: int, needs: Mapping, player_active: bool,
    queue_busy: bool,
) -> tuple[dict | None, dict]:
    """Process a supplied choice, outcome or query in a qualified Live tick."""
    kind = _validate(event, capture, actor, exact_patch, needs)
    partition = _digest(exact_patch, event["platform"], event["household"])
    scope = _digest(partition, event["run"], process_id, actor)
    frame = _digest(event["run"], capture)
    if pending and (pending["scope"] != scope or tick - pending["tick"] > MAX_OUTCOME_TICKS):
        pending = None
    if kind == "query":
        if player_active or queue_busy:
            return pending, receipt("ABSTAIN", reason="PLAYER_OR_QUEUE_FIRST")
        if pending:
            return pending, receipt("ABSTAIN", reason="PLAYER_OUTCOME_PENDING")
        context = _context(event, needs)
        return pending, _advise(path, partition=partition, capture=frame, context=context,
                                available=_available(event, context), needs=needs)

    identity = _digest(event["run"], event["interaction"])
    if kind == "choice":
        if not player_active or event["owner"] != "PLAYER":
            return None, receipt("ABSTAIN", reason="PLAYER_CHOICE_UNPROVEN")
        context = _context(event, needs)
        if not isinstance(event["action"], str) or event["action"] not in _available(event, context):
            return pending, receipt("ABSTAIN", reason="ACTION_NOT_AVAILABLE")
        if pending:
            if pending["identity"] == identity and pending["frame"] == frame:
                return pending, receipt("CHOICE_ALREADY_PENDING")
            if event["sequence"] <= pending["sequence"]:
                return pending, receipt("ABSTAIN", reason="STALE_PLAYER_CHOICE")
            if pending["identity"] == identity:
                return pending, receipt("ABSTAIN", reason="CHOICE_EVIDENCE_CONFLICT")
        return {
            "scope": scope, "identity": identity, "frame": frame, "context": context,
            "sequence": event["sequence"], "tick": tick, "needs": dict(needs),
            "action": event["action"],
        }, receipt("PLAYER_CHOICE_PENDING")

    if not pending or pending["identity"] != identity:
        return pending, receipt("ABSTAIN", reason="NO_MATCHING_PLAYER_CHOICE")
    effect = _digest(event["run"], event["effect_capture"])
    if (not 0 < event["sequence"] - pending["sequence"] <= MAX_OUTCOME_TICKS
            or pending["frame"] in {frame, effect}):
        return pending, receipt("ABSTAIN", reason="OUTCOME_EVIDENCE_NOT_INDEPENDENT")
    label = _outcome(pending["needs"], needs, event["goal_delta"], event["completed"])
    state = _record(path, identity=identity, captures=(pending["frame"], frame, effect),
                    partition=partition, context=pending["context"],
                    action=pending["action"], outcome=label)
    return None, receipt(state)
