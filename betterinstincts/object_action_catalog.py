"""Portable, bounded object-menu learning; evidence is never an input permit.

Sensor adapters submit semantic, sanitized menu/selection/outcome events to the
existing opt-in listener. No desktop hooks, automatic screen capture, game IO,
raw object names, household-specific model weights, or network calls.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Mapping

SCHEMA = "betterinstincts.object-action-catalog/v1"
EVENT_SCHEMA = "betterinstincts.object-action-event/v1"
TOKEN = re.compile(r"^[a-z][a-z0-9_:-]{1,63}$")
SESSION = re.compile(r"^[A-Za-z0-9_-]{3,64}$")
PATCH = re.compile(r"^[0-9]+(?:\.[0-9]+){3}$")
DOMAINS = frozenset(("hunger", "bladder", "energy", "hygiene", "fun",
                     "social", "money", "skills", "career"))
MAX_ACTIONS = 32
MAX_CLASSES = 256
MAX_SESSIONS = 128
MAX_PENDING = 64
MAX_BYTES = 2_000_000
MAX_REVIEW_EVIDENCE = 64
MENU_AGE_MS = 30_000
OUTCOME_AGE_MS = 600_000


class ObjectActionCatalogError(ValueError):
    pass


def _token(value: object, field: str) -> str:
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise ObjectActionCatalogError("INVALID_" + field.upper())
    return value


def _session(value: object) -> str:
    if not isinstance(value, str) or not SESSION.fullmatch(value):
        raise ObjectActionCatalogError("INVALID_SESSION")
    return value


def _patch(value: object) -> str:
    if not isinstance(value, str) or not PATCH.fullmatch(value):
        raise ObjectActionCatalogError("EXACT_GAME_PATCH_REQUIRED")
    return value


def _time(value: object) -> int:
    if type(value) is not int or value < 0:
        raise ObjectActionCatalogError("INVALID_OBSERVATION_TIME")
    return value


def _action_list(value: object) -> list[str]:
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_ACTIONS:
        raise ObjectActionCatalogError("MENU_ACTIONS_INVALID")
    actions = [_token(a, "action_ref") for a in value]
    if len(set(actions)) != len(actions):
        raise ObjectActionCatalogError("DUPLICATE_MENU_ACTION")
    return actions


def _event(value: Mapping) -> dict:
    if not isinstance(value, dict) or value.get("schema") != EVENT_SCHEMA:
        raise ObjectActionCatalogError("EVENT_SCHEMA_INVALID")
    kind = value.get("kind")
    fields = {
        "menu": {"object_ref", "class_ref", "game_version", "actions"},
        "selection": {"object_ref", "class_ref", "game_version",
                      "action_ref", "interaction_ref"},
        "outcome": {"interaction_ref", "effects", "operator_reviewed"},
    }
    if kind not in fields:
        raise ObjectActionCatalogError("EVENT_KIND_INVALID")
    common = {"schema", "kind", "seq", "at_ms", "capture_ref", "source"}
    if set(value) != common | fields[kind]:
        raise ObjectActionCatalogError("EVENT_FIELDS_INVALID")
    seq = value["seq"]
    if type(seq) is not int or seq < 1:
        raise ObjectActionCatalogError("EVENT_SEQUENCE_INVALID")
    event = {
        "kind": kind, "seq": seq, "at_ms": _time(value["at_ms"]),
        "capture_ref": _token(value["capture_ref"], "capture_ref"),
        "source": value["source"],
    }
    if event["source"] not in {"PLAYER", "HOST", "SENSOR"}:
        raise ObjectActionCatalogError("EVENT_SOURCE_INVALID")
    if kind in {"menu", "selection"}:
        event.update({
            "object_ref": _token(value["object_ref"], "object_ref"),
            "class_ref": _token(value["class_ref"], "class_ref"),
            "game_version": _patch(value["game_version"]),
        })
    if kind == "menu":
        event["actions"] = _action_list(value["actions"])
    elif kind == "selection":
        event["action_ref"] = _token(value["action_ref"], "action_ref")
        event["interaction_ref"] = _token(value["interaction_ref"], "interaction_ref")
    else:
        event["interaction_ref"] = _token(value["interaction_ref"], "interaction_ref")
        if type(value["operator_reviewed"]) is not bool:
            raise ObjectActionCatalogError("REVIEW_FLAG_INVALID")
        event["operator_reviewed"] = value["operator_reviewed"]
        effects = value["effects"]
        if not isinstance(effects, list) or not 1 <= len(effects) <= len(DOMAINS):
            raise ObjectActionCatalogError("EFFECTS_INVALID")
        parsed = []
        for item in effects:
            if not isinstance(item, dict) or set(item) != {"domain", "result", "evidence_ref"}:
                raise ObjectActionCatalogError("EFFECT_FIELDS_INVALID")
            if item["domain"] not in DOMAINS or item["result"] not in {
                "helpful", "harmful", "unknown"
            }:
                raise ObjectActionCatalogError("EFFECT_INVALID")
            parsed.append({"domain": item["domain"], "result": item["result"],
                           "evidence_ref": _token(item["evidence_ref"], "evidence_ref")})
        if len({e["domain"] for e in parsed}) != len(parsed):
            raise ObjectActionCatalogError("DUPLICATE_EFFECT_DOMAIN")
        event["effects"] = parsed
    return event


def empty_catalog() -> dict:
    return {"schema": SCHEMA, "revision": 0, "classes": {}, "menus": {},
            "pending": {}, "cursors": {}, "receipt_heads": {}}


def _validate(value: Mapping) -> dict:
    required = {"schema", "revision", "classes", "menus", "pending", "cursors"}
    if (not isinstance(value, dict)
            or set(value) not in (required, required | {"receipt_heads"})
            or value.get("schema") != SCHEMA):
        raise ObjectActionCatalogError("CATALOG_SCHEMA_INVALID")
    if type(value["revision"]) is not int or value["revision"] < 0:
        raise ObjectActionCatalogError("CATALOG_REVISION_INVALID")
    for field, maximum in (("classes", MAX_CLASSES), ("menus", MAX_SESSIONS),
                           ("pending", MAX_PENDING), ("cursors", MAX_SESSIONS)):
        if not isinstance(value[field], dict) or len(value[field]) > maximum:
            raise ObjectActionCatalogError("CATALOG_" + field.upper() + "_BUDGET")
    for session, cursor in value["cursors"].items():
        _session(session)
        if type(cursor) is not int or cursor < 1:
            raise ObjectActionCatalogError("CATALOG_CURSOR_INVALID")
    heads = value.get("receipt_heads", {})
    if not isinstance(heads, dict) or len(heads) > MAX_SESSIONS:
        raise ObjectActionCatalogError("CATALOG_RECEIPT_HEADS_INVALID")
    for sid, receipt in heads.items():
        if (sid not in value["cursors"] or not isinstance(receipt, dict)
                or set(receipt) != {"seq", "at_ms", "fingerprint"}
                or receipt["seq"] != value["cursors"][sid]
                or type(receipt["at_ms"]) is not int or receipt["at_ms"] < 0
                or not isinstance(receipt["fingerprint"], str)
                or re.fullmatch(r"[a-f0-9]{32}", receipt["fingerprint"]) is None):
            raise ObjectActionCatalogError("CATALOG_RECEIPT_HEAD_INVALID")
    class_fields = {"game_version", "class_ref", "action_ref", "menu_seen",
                    "selections", "last_seen_ms", "effects"}
    for key, entry in value["classes"].items():
        if (not isinstance(key, str) or not isinstance(entry, dict)
                or set(entry) not in (class_fields, class_fields | {"review_evidence"})):
            raise ObjectActionCatalogError("CATALOG_CLASS_INVALID")
        if key != _key(_patch(entry["game_version"]),
                       _token(entry["class_ref"], "class_ref"),
                       _token(entry["action_ref"], "action_ref")):
            raise ObjectActionCatalogError("CATALOG_CLASS_KEY_INVALID")
        for count_field in ("menu_seen", "selections", "last_seen_ms"):
            if type(entry[count_field]) is not int or entry[count_field] < 0:
                raise ObjectActionCatalogError("CATALOG_CLASS_COUNT_INVALID")
        if not isinstance(entry["effects"], dict):
            raise ObjectActionCatalogError("CATALOG_EFFECTS_INVALID")
        for domain, counts in entry["effects"].items():
            if domain not in DOMAINS or not isinstance(counts, dict) or set(counts) != {
                "helpful", "harmful"
            } or any(type(v) is not int or v < 0 for v in counts.values()):
                raise ObjectActionCatalogError("CATALOG_EFFECT_COUNTS_INVALID")
        reviews = entry.get("review_evidence", [])
        if not isinstance(reviews, list) or len(reviews) > MAX_REVIEW_EVIDENCE:
            raise ObjectActionCatalogError("CATALOG_REVIEW_EVIDENCE_BUDGET")
        reviewed = set()
        for review in reviews:
            if (not isinstance(review, dict)
                    or set(review) != {"fingerprint", "domain", "result"}
                    or review["domain"] not in DOMAINS
                    or review["result"] not in {"helpful", "harmful"}
                    or not isinstance(review["fingerprint"], str)
                    or re.fullmatch(r"[a-f0-9]{32}", review["fingerprint"]) is None):
                raise ObjectActionCatalogError("CATALOG_REVIEW_PROOF_INVALID")
            marker = (review["domain"], review["fingerprint"])
            if marker in reviewed:
                raise ObjectActionCatalogError("CATALOG_DUPLICATE_REVIEW_PROOF")
            reviewed.add(marker)
    for sid, menu in value["menus"].items():
        _session(sid)
        if not isinstance(menu, dict) or set(menu) != {
            "object_ref", "class_ref", "game_version", "capture_ref",
            "at_ms", "actions"
        }:
            raise ObjectActionCatalogError("CATALOG_MENU_INVALID")
        for item in ("object_ref", "class_ref", "capture_ref"):
            _token(menu[item], item)
        _patch(menu["game_version"])
        _time(menu["at_ms"])
        _action_list(menu["actions"])
    for key, pending in value["pending"].items():
        if not isinstance(key, str) or not isinstance(pending, dict) or set(pending) != {
            "entry", "at_ms", "capture_ref"
        } or pending["entry"] not in value["classes"]:
            raise ObjectActionCatalogError("CATALOG_PENDING_INVALID")
        _time(pending["at_ms"])
        _token(pending["capture_ref"], "capture_ref")
    if len(json.dumps(value, sort_keys=True).encode("utf-8")) > MAX_BYTES:
        raise ObjectActionCatalogError("CATALOG_OVERSIZE")
    return value


def _key(patch: str, kind: str, action: str) -> str:
    return "|".join((patch, kind, action))


def ingest(catalog: Mapping, supplied_event: Mapping, *, session_id: str) -> tuple[dict, dict]:
    """Pure reducer: each opt-in session supplies monotonically increasing seq."""
    state = _validate(catalog)
    sid = _session(session_id)
    event = _event(supplied_event)
    previous_seq = state["cursors"].get(sid, 0)
    fingerprint = hashlib.blake2s(
        json.dumps(event, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        digest_size=16,
    ).hexdigest()
    previous_head = state.get("receipt_heads", {}).get(sid)
    if event["seq"] <= previous_seq:
        if (event["seq"] == previous_seq and previous_head is not None
                and previous_head["fingerprint"] == fingerprint):
            return state, {"state": "ALREADY_INDEXED", "recorded": False,
                           "execute_allowed": False}
        raise ObjectActionCatalogError("EVENT_STALE_OR_CONTRADICTORY_REPLAY")
    if event["seq"] != previous_seq + 1:
        raise ObjectActionCatalogError("EVENT_SEQUENCE_GAP")
    if previous_head is not None and event["at_ms"] < previous_head["at_ms"]:
        raise ObjectActionCatalogError("EVENT_TIME_REGRESSION")
    classes = {
        k: {**v, "effects": {d: dict(n) for d, n in v["effects"].items()},
            "review_evidence": [dict(item) for item in v.get("review_evidence", [])]}
        for k, v in state["classes"].items()
    }
    menus = {k: dict(v) for k, v in state["menus"].items()}
    pending = {k: dict(v) for k, v in state["pending"].items()}
    kind = event["kind"]
    now = event["at_ms"]
    if kind == "menu":
        menus[sid] = {k: event[k] for k in (
            "object_ref", "class_ref", "game_version", "capture_ref", "at_ms", "actions"
        )}
        for action in event["actions"]:
            key = _key(event["game_version"], event["class_ref"], action)
            row = classes.setdefault(key, {
                "game_version": event["game_version"], "class_ref": event["class_ref"],
                "action_ref": action, "menu_seen": 0, "selections": 0,
                "last_seen_ms": now, "effects": {}, "review_evidence": [],
            })
            row["menu_seen"] += 1
            row["last_seen_ms"] = now
    elif kind == "selection":
        menu = menus.get(sid)
        if (not menu or any(menu[field] != event[field] for field in (
            "object_ref", "class_ref", "game_version", "capture_ref"
        )) or not 0 <= now - menu["at_ms"] <= MENU_AGE_MS or
                event["action_ref"] not in menu["actions"]):
            raise ObjectActionCatalogError("SELECTION_NOT_IN_FRESH_MENU")
        key = _key(event["game_version"], event["class_ref"], event["action_ref"])
        interaction = sid + "|" + event["interaction_ref"]
        if interaction in pending:
            raise ObjectActionCatalogError("INTERACTION_ALREADY_PENDING")
        if len(pending) >= MAX_PENDING:
            raise ObjectActionCatalogError("PENDING_BUDGET_EXHAUSTED")
        classes[key]["selections"] += 1
        pending[interaction] = {"entry": key, "at_ms": now,
                                "capture_ref": event["capture_ref"]}
    else:
        interaction = sid + "|" + event["interaction_ref"]
        matched = pending.get(interaction)
        if (not matched or not 0 <= now - matched["at_ms"] <= OUTCOME_AGE_MS
                or event["capture_ref"] == matched["capture_ref"]):
            raise ObjectActionCatalogError("OUTCOME_UNMATCHED_OR_NOT_POST_ACTION")
        pending.pop(interaction)
        if event["operator_reviewed"]:
            row = classes[matched["entry"]]
            for effect in event["effects"]:
                if effect["result"] not in {"helpful", "harmful"}:
                    continue
                proof = hashlib.blake2s(
                    (effect["domain"] + "|" + effect["evidence_ref"]).encode("utf-8"),
                    digest_size=16,
                ).hexdigest()
                if any(r["domain"] == effect["domain"] and
                       r["fingerprint"] == proof for r in row["review_evidence"]):
                    continue  # The same observed outcome is not a second training sample.
                if len(row["review_evidence"]) >= MAX_REVIEW_EVIDENCE:
                    raise ObjectActionCatalogError("REVIEW_EVIDENCE_CAPACITY_EXHAUSTED")
                row["review_evidence"].append({
                    "fingerprint": proof, "domain": effect["domain"],
                    "result": effect["result"],
                })
                counts = row["effects"].setdefault(
                    effect["domain"], {"helpful": 0, "harmful": 0}
                )
                counts[effect["result"]] += 1
    updated = {
        "schema": SCHEMA, "revision": state["revision"] + 1,
        "classes": classes, "menus": menus, "pending": pending,
        "cursors": {**state["cursors"], sid: event["seq"]},
        "receipt_heads": {**state.get("receipt_heads", {}), sid: {
            "seq": event["seq"], "at_ms": event["at_ms"],
            "fingerprint": fingerprint,
        }},
    }
    _validate(updated)
    return updated, {"state": "OBJECT_ACTION_INDEXED", "recorded": True,
                     "revision": updated["revision"], "execute_allowed": False}


def recommend(catalog: Mapping, *, session_id: str, game_version: str,
              object_ref: str, class_ref: str, capture_ref: str, now_ms: int,
              available_actions: list[str], desired_domains: list[str],
              player_active: bool, player_queue_present: bool) -> dict:
    """Rank verified portable utility on a *fresh* active object's menu."""
    state = _validate(catalog)
    sid = _session(session_id)
    patch = _patch(game_version)
    obj = _token(object_ref, "object_ref")
    kind = _token(class_ref, "class_ref")
    capture = _token(capture_ref, "capture_ref")
    now = _time(now_ms)
    actions = _action_list(available_actions)
    if not isinstance(desired_domains, list) or len(desired_domains) > len(DOMAINS):
        raise ObjectActionCatalogError("DESIRED_DOMAINS_INVALID")
    if len(set(desired_domains)) != len(desired_domains) or any(
        d not in DOMAINS for d in desired_domains
    ):
        raise ObjectActionCatalogError("DESIRED_DOMAINS_INVALID")
    if type(player_active) is not bool or type(player_queue_present) is not bool:
        raise ObjectActionCatalogError("PLAYER_STATE_REQUIRED")
    base = {"schema": "betterinstincts.object-action-recommendation/v1",
            "execute_allowed": False, "cancel_allowed": False,
            "control_permit": None, "candidate": None}
    if player_active or player_queue_present:
        return {**base, "state": "PLAYER_FIRST"}
    menu = state["menus"].get(sid)
    if (not menu or menu["game_version"] != patch or
            menu["object_ref"] != obj or menu["class_ref"] != kind or
            menu["capture_ref"] != capture or menu["actions"] != actions or
            not 0 <= now - menu["at_ms"] <= MENU_AGE_MS):
        return {**base, "state": "REOBSERVE_CURRENT_OBJECT_MENU"}
    matches = []
    conflicting = saturated = False
    for action in actions:
        row = state["classes"].get(_key(patch, kind, action))
        if row is None:
            continue
        # Legacy aggregate counts are retained, but lack replay-unique review
        # provenance. They must not independently establish usable utility.
        reviews = row.get("review_evidence", [])
        if len(reviews) >= MAX_REVIEW_EVIDENCE:
            saturated = True
            continue
        for domain in desired_domains:
            positive = sum(r["result"] == "helpful" and r["domain"] == domain
                           for r in reviews)
            negative = sum(r["result"] == "harmful" and r["domain"] == domain
                           for r in reviews)
            total = positive + negative
            if positive >= 3 and total >= 3 and positive / total >= 0.75:
                if any(r["result"] == "harmful" and r["domain"] != domain
                       for r in reviews):
                    conflicting = True
                    continue
                matches.append((desired_domains.index(domain), -positive,
                                negative, action, domain, total))
    if not matches:
        reason = ("CONFLICTING_REVIEWED_EFFECTS" if conflicting else
                  "REVIEW_EVIDENCE_CAPACITY_EXHAUSTED" if saturated else
                  "INSUFFICIENT_REVIEWED_UTILITY")
        return {**base, "state": reason}
    _, neg_positive, negative, action, domain, total = min(matches)
    return {**base, "state": "ADVISORY_ONLY",
            "candidate": {"action_ref": action, "object_ref": obj,
                          "class_ref": kind, "goal_domain": domain,
                          "reviewed_helpful": -neg_positive,
                          "reviewed_harmful": negative,
                          "reviewed_total": total,
                          "capture_ref": capture,
                          "required_gates": ["PLAYER_IDLE", "FRESH_SCREEN_ADMIT",
                                             "EXACT_ACTOR_AND_OBJECT",
                                             "QUEUE_CAPACITY",
                                             "OBSERVE_OUTCOME"]}}


def load_catalog(path: Path) -> dict:
    path = Path(path)
    if not path.exists():
        return empty_catalog()
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ObjectActionCatalogError("CATALOG_FILE_UNSAFE")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ObjectActionCatalogError("CATALOG_READ_FAILED") from exc
    return _validate(value)


def record_event(path: Path, event: Mapping, *, session_id: str) -> dict:
    """One-writer, atomic, bounded opt-in projection; never a game side effect."""
    path = Path(path)
    if path.is_symlink() or path.parent.is_symlink():
        raise ObjectActionCatalogError("CATALOG_PATH_SYMLINK_FORBIDDEN")
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(".lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ObjectActionCatalogError("CATALOG_WRITER_BUSY") from exc
    try:
        os.close(fd)
        updated, receipt = ingest(load_catalog(path), event, session_id=session_id)
        if not receipt["recorded"]:
            return receipt
        raw = json.dumps(updated, sort_keys=True, indent=2) + "\n"
        if len(raw.encode("utf-8")) > MAX_BYTES:
            raise ObjectActionCatalogError("CATALOG_OVERSIZE")
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent,
                prefix=".object-action-", suffix=".tmp", delete=False
            ) as handle:
                temporary = Path(handle.name)
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return {**receipt, "class_actions": len(updated["classes"])}
    finally:
        lock.unlink(missing_ok=True)
