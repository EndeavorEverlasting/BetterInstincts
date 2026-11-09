"""Chance-card research and memoization seam; no screen capture or game input.

The existing decision_eval catalog remains the owner of known heuristic choices.
This module consumes *supplied*, independently observed popup evidence and
returns a research dispatch + companion presentation for an external host.
It never clicks, fetches the web, runs background work, or edits game saves.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Mapping

SCHEMA = "betterinstincts.chance-event/v1"
CACHE_SCHEMA = "betterinstincts.chance-event-memo/v1"
RESULT_SCHEMA = "betterinstincts.chance-event-advisory/v1"
EVIDENCE = frozenset({"LOCAL_TUNING", "LOCAL_OBSERVED", "EXTERNAL_REFERENCE"})
RISK = frozenset({"REVERSIBLE", "PERSISTENT", "IRREVERSIBLE", "UNKNOWN"})
MAX_MEMO_BYTES = 512_000
MAX_RECORDS = 128
MAX_TEXT = 4000
DEFAULT_TTL_DAYS = 30
TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")


class ChanceEventError(ValueError):
    """An untrusted popup or memo cannot authorize a game decision."""


def _text(value: object, field: str, limit: int = MAX_TEXT) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ChanceEventError("INVALID_" + field)
    return " ".join(value.split())


def _timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ChanceEventError("INVALID_TIMESTAMP") from exc
    if parsed.tzinfo is None:
        raise ChanceEventError("TIMESTAMP_MUST_HAVE_OFFSET")
    return parsed.astimezone(timezone.utc)


def _context(value: object) -> dict:
    if not isinstance(value, Mapping):
        raise ChanceEventError("CONTEXT_REQUIRED")
    version = _text(value.get("game_version"), "GAME_VERSION", 80)
    locale = _text(value.get("locale"), "LOCALE", 32)
    # Unknown mod signatures are NOT equivalent to an unmodded game.
    mods = _text(value.get("mods_digest"), "MODS_DIGEST", 128)
    packs = value.get("packs")
    if not isinstance(packs, list) or len(packs) > 128 or any(
        not isinstance(x, str) or not TOKEN.fullmatch(x) for x in packs
    ):
        raise ChanceEventError("INVALID_PACKS")
    return {"game_version": version, "locale": locale,
            "mods_digest": mods, "packs": sorted(set(packs))}


def identify(observation: Mapping) -> dict:
    """Identity includes event text, choices, patch, DLC, mods and locale."""
    if not isinstance(observation, Mapping) or observation.get("schema") != SCHEMA:
        raise ChanceEventError("INVALID_EVENT_SCHEMA")
    ref = _text(observation.get("capture_ref"), "CAPTURE_REF", 128)
    title = _text(observation.get("title"), "EVENT_TITLE", 180)
    body = _text(observation.get("body"), "EVENT_BODY")
    options = observation.get("options")
    if not isinstance(options, list) or not 2 <= len(options) <= 8:
        raise ChanceEventError("TWO_TO_EIGHT_OPTIONS_REQUIRED")
    normalized = []
    for row in options:
        if not isinstance(row, Mapping) or not isinstance(row.get("id"), str) or not TOKEN.fullmatch(row["id"]):
            raise ChanceEventError("OPTION_ID_INVALID")
        normalized.append({"id": row["id"], "label": _text(row.get("label"), "OPTION_LABEL", 180)})
    ids = [x["id"] for x in normalized]
    if len(set(ids)) != len(ids):
        raise ChanceEventError("DUPLICATE_OPTION_IDS")
    context = _context(observation.get("context"))
    fingerprint = {"title": title.casefold(), "body": body.casefold(),
                   "options": normalized, "context": context}
    key = hashlib.sha256(json.dumps(
        fingerprint, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    cues = observation.get("scene_cues") or []
    if not isinstance(cues, list) or any(not isinstance(x, str) for x in cues):
        raise ChanceEventError("INVALID_SCENE_CUES")
    confirmed = bool(observation.get("modal_visible") is True and
                     len(set(cues) & {"dialog_bounds", "choice_controls", "modal_layer"}) >= 2)
    return {"key": key, "capture_ref": ref, "title": title, "body": body,
            "options": normalized, "context": context, "confirmed": confirmed}


def empty_memo() -> dict:
    return {"schema": CACHE_SCHEMA, "records": {}}


def _validate_memo(memo: Mapping) -> dict:
    if not isinstance(memo, Mapping) or memo.get("schema") != CACHE_SCHEMA:
        raise ChanceEventError("MEMO_SCHEMA_INVALID")
    records = memo.get("records")
    if not isinstance(records, dict) or len(records) > MAX_RECORDS:
        raise ChanceEventError("MEMO_RECORDS_INVALID")
    return dict(records)


def _research_lanes(*, external_opt_in: bool, existing: Mapping | None = None) -> list:
    recorded = {r.get("kind") for r in (existing or {}).get("sources", [])
                if isinstance(r, Mapping)}
    lanes = [
        {"lane": "LOCAL_MECHANICS", "state": "EVIDENCE_RECORDED" if
         "LOCAL_TUNING" in recorded or "LOCAL_OBSERVED" in recorded else "RESEARCH_REQUIRED",
         "task": "Inspect exact installed tuning, pack, patch and observed option outcomes."},
        {"lane": "FRONTIER_CROSSCHECK", "state": ("EVIDENCE_RECORDED" if
         "EXTERNAL_REFERENCE" in recorded else
         "RESEARCH_REQUIRED" if external_opt_in else "OPT_IN_REQUIRED"),
         "task": "Look up versioned source provenance; challenge stale guides and assumptions."},
    ]
    return lanes


def _ui(*, phase: str, title: str, options: list, status: str,
        lanes: list, implications: list | None = None) -> dict:
    return {
        "component": "chance_event_companion", "surface": "HOST_PRESENTATION_MODEL_ONLY",
        "layout": "ADJACENT_TO_NATIVE_DIALOG", "non_modal": True,
        "focus": "GAME_RETAINS_KEYBOARD_AND_POINTER",
        "motion": "SUBTLE_OR_STATIC_WITH_REDUCED_MOTION",
        "phase": phase, "title": title, "status_text": status,
        "research_lanes": lanes, "choices": implications or
            [{"option_id": x["id"], "label": x["label"],
              "benefits": [], "risks": [], "unknowns": ["Outcome not verified"],
              "permanence": "UNKNOWN", "confidence": "UNKNOWN"} for x in options],
        "controls": ["INSPECT_SOURCES", "DISMISS_COMPANION"],
        "game_choice_control": "PLAYER_ONLY",
    }


def assess(observation: Mapping, memo: Mapping | None = None, *,
           now: datetime | None = None, external_research_opt_in: bool = False,
           host_research_state: str = "IDLE") -> dict:
    """Produce bounded dispatch and companion states, never a click permit.

    RUNNING is only displayed if the caller has genuine worker evidence;
    assessment does not launch workers or make up progress percentages.
    """
    if host_research_state not in {"IDLE", "RUNNING", "FAILED"}:
        raise ChanceEventError("RESEARCH_STATE_INVALID")
    identity = identify(observation)
    records = _validate_memo(memo or empty_memo())
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ChanceEventError("NAIVE_NOW_FORBIDDEN")
    current = current.astimezone(timezone.utc)
    record = records.get(identity["key"])
    lanes = _research_lanes(external_opt_in=external_research_opt_in,
                            existing=record if isinstance(record, Mapping) else None)
    base = {"schema": RESULT_SCHEMA, "event_key": identity["key"],
            "capture_ref": identity["capture_ref"],
            "execute_clicks": False, "control_permit": None,
            "memo_hit": False, "research_dispatch": [],
            "proof_ceiling": "OFFLINE_ADVISORY_NOT_GAME_OBSERVED"}
    if not identity["confirmed"]:
        base.update(state="OBSERVATION_REQUIRED", ui=_ui(
            phase="OBSERVING", title=identity["title"], options=identity["options"],
            status="Confirm the on-screen event before researching or choosing.", lanes=[]))
        return base
    valid = False
    if isinstance(record, Mapping):
        try:
            valid = (_timestamp(record.get("expires_at", "")) > current and
                     record.get("key") == identity["key"] and
                     record.get("context") == identity["context"] and
                     record.get("reviewed") is True and
                     isinstance(record.get("sources"), list) and
                     bool(record["sources"]) and
                     isinstance(record.get("implications"), list) and
                     {x["option_id"] for x in record["implications"]} ==
                     {x["id"] for x in identity["options"]} and
                     all(s.get("kind") in EVIDENCE and s.get("ref") and
                         s.get("observed_at") for s in record["sources"]))
        except (ChanceEventError, TypeError, KeyError):
            valid = False
    if valid:
        implications = record["implications"]
        choice = record.get("recommended_option_id")
        # High-consequence outcomes require corroboration from local mechanics.
        local_proof = any(s["kind"] in {"LOCAL_TUNING", "LOCAL_OBSERVED"}
                          for s in record["sources"])
        uncertain = any(x.get("permanence") not in RISK or
                        x.get("permanence") == "UNKNOWN" or
                        x.get("disputed") is True for x in implications)
        consequential = any(x.get("permanence") in {"PERSISTENT", "IRREVERSIBLE"}
                            for x in implications)
        recommendable = (not uncertain and
                         (not consequential or local_proof) and
                         choice in {x["id"] for x in identity["options"]})
        base.update(
            state="READY_FOR_PLAYER" if recommendable else "REVIEW_REQUIRED",
            memo_hit=True,
            recommended_option_id=choice if recommendable else None,
            ui=_ui(phase="READY" if recommendable else "NEEDS_REVIEW",
                   title=identity["title"], options=identity["options"],
                   status=("Research reviewed. You choose the action." if recommendable
                           else "Some implications remain uncertain. You choose."),
                   lanes=lanes, implications=implications),
        )
        return base
    dispatch = [{"lane": "LOCAL_MECHANICS", "event_key": identity["key"],
                 "capture_ref": identity["capture_ref"], "network": False,
                 "check": "PATCH_PACKS_MODS_TUNING_AND_LOCAL_OUTCOME"}]
    if external_research_opt_in:
        dispatch.append({"lane": "FRONTIER_CROSSCHECK", "event_key": identity["key"],
                         "capture_ref": identity["capture_ref"], "network": True,
                         "check": "DATE_VERSION_AND_INDEPENDENT_SOURCE_CONFLICTS",
                         "privacy": "SANITIZE_BEFORE_EXTERNAL_QUERY"})
    state = ("RESEARCHING" if host_research_state == "RUNNING" else
             "RESEARCH_FAILED" if host_research_state == "FAILED" else "RESEARCH_REQUIRED")
    base.update(state=state, research_dispatch=dispatch,
                ui=_ui(phase=state, title=identity["title"],
                       options=identity["options"], lanes=lanes,
                       status=("Research in progress; no choice has been made." if
                               state == "RESEARCHING" else
                               "Research could not finish; keep the native choice available." if
                               state == "RESEARCH_FAILED" else
                               "Checking event mechanics before recommending a decision.")))
    return base


def remember(memo: Mapping, observation: Mapping, research: Mapping, *,
             now: datetime, ttl_days: int = DEFAULT_TTL_DAYS) -> dict:
    """Memoize reviewed computations, never a fabricated or unreviewed claim."""
    identity = identify(observation)
    if not identity["confirmed"]:
        raise ChanceEventError("UNCONFIRMED_EVENT_CANNOT_BE_MEMOIZED")
    if now.tzinfo is None or not 1 <= ttl_days <= 90:
        raise ChanceEventError("MEMO_TIME_INVALID")
    if research.get("reviewed") is not True:
        raise ChanceEventError("EXPLICIT_RESEARCH_REVIEW_REQUIRED")
    sources = research.get("sources")
    items = research.get("implications")
    if not isinstance(sources, list) or not sources or len(sources) > 16:
        raise ChanceEventError("SOURCES_REQUIRED")
    for s in sources:
        if not isinstance(s, Mapping) or s.get("kind") not in EVIDENCE:
            raise ChanceEventError("SOURCE_KIND_INVALID")
        _text(s.get("ref"), "SOURCE_REF", 512)
        _timestamp(s.get("observed_at"))
    if not isinstance(items, list) or len(items) != len(identity["options"]):
        raise ChanceEventError("IMPLICATIONS_INCOMPLETE")
    expected = {x["id"] for x in identity["options"]}
    if {x.get("option_id") for x in items if isinstance(x, Mapping)} != expected:
        raise ChanceEventError("IMPLICATION_OPTIONS_MISMATCH")
    for item in items:
        if (item.get("permanence") not in RISK or
            any(not isinstance(item.get(k), list) or
                len(item[k]) > 12 or any(not isinstance(t, str) or len(t) > 240 for t in item[k])
                for k in ("benefits", "risks", "unknowns")) or
            not isinstance(item.get("confidence"), str)):
            raise ChanceEventError("INVALID_IMPLICATION")
    choice = research.get("recommended_option_id")
    if choice is not None and choice not in expected:
        raise ChanceEventError("BAD_RECOMMENDATION")
    records = _validate_memo(memo)
    records[identity["key"]] = {
        "key": identity["key"], "context": identity["context"], "reviewed": True,
        "sources": [dict(x) for x in sources], "implications": [dict(x) for x in items],
        "recommended_option_id": choice,
        "expires_at": (now.astimezone(timezone.utc) +
                       timedelta(days=ttl_days)).isoformat(),
    }
    if len(records) > MAX_RECORDS:
        raise ChanceEventError("MEMO_BUDGET_REACHED")
    payload = {"schema": CACHE_SCHEMA, "records": records}
    if len(json.dumps(payload).encode("utf-8")) > MAX_MEMO_BYTES:
        raise ChanceEventError("MEMO_BYTES_EXCEEDED")
    return payload


def load_memo(path: Path) -> dict:
    """Load explicit local memo path; do not search player profile or saves."""
    path = Path(path)
    if not path.exists():
        return empty_memo()
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_MEMO_BYTES:
        raise ChanceEventError("MEMO_PATH_UNSAFE")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ChanceEventError("MEMO_JSON_INVALID") from exc
    _validate_memo(data)
    return data


def save_memo(path: Path, memo: Mapping) -> None:
    """Explicit local path, atomic replacement; no user saves or telemetry."""
    path = Path(path)
    _validate_memo(memo)
    raw = json.dumps(memo, sort_keys=True, indent=2) + "\n"
    if len(raw.encode("utf-8")) > MAX_MEMO_BYTES:
        raise ChanceEventError("MEMO_BYTES_EXCEEDED")
    if path.is_symlink() or not path.parent.is_dir() or path.parent.is_symlink():
        raise ChanceEventError("MEMO_PATH_UNSAFE")
    tmp = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8",
                                         dir=path.parent, prefix=".chance-",
                                         suffix=".tmp", delete=False) as handle:
            tmp = Path(handle.name)
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
