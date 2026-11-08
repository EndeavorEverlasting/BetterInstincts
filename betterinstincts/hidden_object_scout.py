"""Resumable hidden catalog scout mission for a *local* game-capable agent.

No polling loop, background task, input injection, game process access or save changes.
One local host agent owns UI control. This module only checks evidence and stores
bounded, review-qualified progress under ignored dist/.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Mapping

from betterinstincts.hidden_object_discovery import (
    ROOT, audit_p04_receipt, plan_discovery, review_catalog_entry,
)

CONTRACT = ROOT / "contracts" / "hidden-object-scout-goal.v1.json"
STATE_ROOT = ROOT / "dist" / "hidden-object-scout"
SESSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
PROOF = "LOCAL_CHECKPOINT_SHAPE_NOT_LIVE_GAME_PROOF"


class ScoutError(ValueError):
    pass


def load_goal(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 64000:
        raise ScoutError("SCOUT_CONTRACT_UNSAFE")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.hidden-object-scout-goal/v1":
        raise ScoutError("SCOUT_GOAL_SCHEMA_INVALID")
    goals = data.get("objectives", {})
    rotation = goals.get("category_rotation")
    if rotation != ["clutter", "collectibles", "landscape", "lighting", "world"]:
        raise ScoutError("SCOUT_CATEGORY_ROTATION_INVALID")
    if data.get("engine") != "SCOPED_READ_ONLY_CHECKPOINTS_NO_GAME_INPUT":
        raise ScoutError("SCOUT_NO_GAME_INPUT_REQUIRED")
    for field in ("default_duration_minutes", "min_duration_minutes", "max_duration_minutes",
                  "max_batches", "max_items_per_batch", "max_consecutive_zero_new_batches",
                  "minimum_seconds_between_batches", "observation_max_age_seconds"):
        if type(goals.get(field)) is not int or goals[field] <= 0:
            raise ScoutError("SCOUT_BOUNDS_INVALID:" + field)
    return data


def _id(raw: str) -> str:
    if not isinstance(raw, str) or not SESSION_RE.fullmatch(raw):
        raise ScoutError("INVALID_SESSION_ID")
    return raw


def _opaque(raw: object) -> bool:
    return isinstance(raw, str) and bool(REF_RE.fullmatch(raw))


def _folder(session_id: str) -> Path:
    return STATE_ROOT / _id(session_id)


def _file(session_id: str) -> Path:
    return _folder(session_id) / "state.json"


@contextmanager
def _lock(session_id: str):
    directory = _folder(session_id)
    if STATE_ROOT.is_symlink() or directory.is_symlink():
        raise ScoutError("SCOUT_SESSION_SYMLINK_FORBIDDEN")
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory / ".lock"
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ScoutError("SCOUT_SESSION_ALREADY_WRITING") from exc
    try:
        os.close(fd)
        yield
    finally:
        lock.unlink(missing_ok=True)


def _read(session_id: str) -> dict:
    path = _file(session_id)
    if path.is_symlink() or not path.is_file():
        raise ScoutError("SCOUT_SESSION_NOT_FOUND")
    if path.stat().st_size > load_goal()["checkpoint"]["max_file_bytes"]:
        raise ScoutError("SCOUT_CHECKPOINT_TOO_LARGE")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.hidden-object-scout-session/v1" or data.get("session_id") != session_id:
        raise ScoutError("SCOUT_CHECKPOINT_CORRUPT")
    return data


def _write(session_id: str, state: dict) -> None:
    path = _file(session_id)
    if path.is_symlink() or path.parent.is_symlink():
        raise ScoutError("SCOUT_CHECKPOINT_SYMLINK_FORBIDDEN")
    raw = (json.dumps(state, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if len(raw) > load_goal()["checkpoint"]["max_file_bytes"]:
        raise ScoutError("SCOUT_CHECKPOINT_BUDGET_EXCEEDED")
    temp = path.with_suffix(".pending")
    if temp.is_symlink():
        raise ScoutError("SCOUT_PENDING_SYMLINK_FORBIDDEN")
    try:
        with temp.open("xb") as out:
            out.write(raw)
            out.flush()
            os.fsync(out.fileno())
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def start(session_id: str, *, minutes: int | None = None,
          target: int | None = None, now: int | None = None) -> dict:
    """Create an opt-in *plan state*, without enabling cheats or claiming input authority."""
    cfg = load_goal()
    bounds = cfg["objectives"]
    minutes = bounds["default_duration_minutes"] if minutes is None else minutes
    target = bounds["target_unique_candidates"] if target is None else target
    if type(minutes) is not int or not bounds["min_duration_minutes"] <= minutes <= bounds["max_duration_minutes"]:
        raise ScoutError("INVALID_MISSION_DURATION")
    if type(target) is not int or not 1 <= target <= 10000:
        raise ScoutError("INVALID_DISCOVERY_TARGET")
    now = int(time.time()) if now is None else now
    _id(session_id)
    with _lock(session_id):
        if _file(session_id).exists():
            raise ScoutError("SCOUT_SESSION_ALREADY_EXISTS")
        state = {
            "schema": "betterinstincts.hidden-object-scout-session/v1",
            "session_id": session_id, "mode": "ACTIVE",
            "created_at": now, "deadline": now + minutes * 60,
            "duration_minutes": minutes, "target_unique_candidates": target,
            "paused_at": None, "pinned_build": None, "pinned_platform": None,
            "pinned_save_ref": None, "batches": [], "items": {},
            "consecutive_zero_new": 0, "last_recorded_at": None,
        }
        _write(session_id, state)
    return status(session_id, now=now)


def _time(state: dict, now: int, cfg: dict) -> str:
    if state["mode"] == "STOPPED":
        return "STOPPED"
    if state["mode"] == "PAUSED":
        return "PAUSED"
    if now >= state["deadline"]:
        return "TIMEBOX_EXPIRED"
    if len(state["batches"]) >= cfg["objectives"]["max_batches"]:
        return "MAX_BATCHES"
    if state["consecutive_zero_new"] >= cfg["objectives"]["max_consecutive_zero_new_batches"]:
        return "DISCOVERY_PLATEAU"
    return "ACTIVE"


def _metrics(state: dict) -> dict:
    items = list(state["items"].values())
    reviewed = [x for x in items if x["reviewed"]]
    return {
        "unique_candidates": len(items),
        "reviewed_unique": len(reviewed),
        "reviewed_free": sum(x["free"] is True for x in reviewed),
        "reviewed_priced": sum(x["free"] is False for x in reviewed),
        "reviewed_price_unknown": sum(x["free"] is None for x in reviewed),
        "pending_review": len(items) - len(reviewed),
        "completed_batches": len(state["batches"]),
        "zero_new_streak": state["consecutive_zero_new"],
        "by_category": {cat: sum(x["category"] == cat for x in items)
                        for cat in load_goal()["objectives"]["category_rotation"]},
    }


def status(session_id: str, *, now: int | None = None) -> dict:
    now = int(time.time()) if now is None else now
    state = _read(session_id)
    cfg = load_goal()
    at = state["paused_at"] if state["mode"] == "PAUSED" else now
    return {
        "state": _time(state, now, cfg),
        "session_id": session_id, "duration_minutes": state["duration_minutes"],
        "target_unique_candidates": state["target_unique_candidates"],
        "target_reached": len(state["items"]) >= state["target_unique_candidates"],
        "remaining_seconds": max(0, state["deadline"] - at),
        "pinned_build": state["pinned_build"], "pinned_save_ref": state["pinned_save_ref"],
        "metrics": _metrics(state), "proof_ceiling": PROOF, "gameplay_certified": False,
    }


def _selection(state: dict, cfg: dict) -> tuple[str, str, str]:
    count = len(state["batches"])
    rotation = cfg["objectives"]["category_rotation"]
    category = rotation[count % len(rotation)]
    from betterinstincts.hidden_object_discovery import load_contract
    hints = load_contract()["search_contract"]["classes"][category]["search_hints"]
    search = hints[(count // len(rotation)) % len(hints)]
    return category, search, f"{state['session_id']}-B{count+1:03}"


def _admit(state: dict, observation: Mapping, p04_receipt: Mapping,
           *, category: str, now: int, cfg: dict) -> list[str]:
    reasons = []
    result = audit_p04_receipt(p04_receipt)
    if result["state"] != "P04_EVIDENCE_SHAPE_COMPLETE_PENDING_INDEPENDENT_REVIEW":
        reasons.append("P04_SETUP_RECEIPT_INCOMPLETE")
    if not isinstance(observation, Mapping):
        return reasons + ["CURRENT_GAME_OBSERVATION_MISSING"]
    if observation.get("scene_id") != "build_buy":
        reasons.append("CURRENT_BUILD_BUY_NOT_OBSERVED")
    if not _opaque(observation.get("visual_cue_ref")) or not _opaque(observation.get("operator_cue_ref")):
        reasons.append("CURRENT_TWO_SOURCE_CUES_REQUIRED")
    elif observation["visual_cue_ref"] == observation["operator_cue_ref"]:
        reasons.append("CURRENT_TWO_SOURCE_CUES_COLLIDE")
    seen_time = observation.get("observed_at_unix")
    if type(seen_time) not in (int, float) or not (0 <= now - seen_time <= cfg["objectives"]["observation_max_age_seconds"]):
        reasons.append("CURRENT_OBSERVATION_STALE")
    save_ref = observation.get("save_ref")
    if not _opaque(save_ref) or save_ref != p04_receipt.get("save_ref"):
        reasons.append("LAB_SAVE_IDENTITY_NOT_BOUND_TO_P04")
    if observation.get("exact_game_build") != p04_receipt.get("exact_game_build"):
        reasons.append("P04_GAME_BUILD_MISMATCH")
    if observation.get("platform") != p04_receipt.get("platform"):
        reasons.append("P04_PLATFORM_MISMATCH")
    if state["pinned_build"] is not None and state["pinned_build"] != observation.get("exact_game_build"):
        reasons.append("PINNED_GAME_BUILD_CHANGED")
    if state["pinned_save_ref"] is not None and state["pinned_save_ref"] != save_ref:
        reasons.append("PINNED_SAVE_IDENTITY_CHANGED")
    if state["pinned_platform"] is not None and state["pinned_platform"] != observation.get("platform"):
        reasons.append("PINNED_PLATFORM_CHANGED")
    plan = plan_discovery(observation, category=category)
    if plan["state"] != "DISCOVERY_PLAN_READY_NOT_AUTHORIZED":
        reasons.append("SCENE_PLAYER_OR_LEASE_NOT_ADMITTED")
    return reasons


def next_search(session_id: str, observation: Mapping, p04_receipt: Mapping,
                *, now: int | None = None) -> dict:
    now = int(time.time()) if now is None else now
    state = _read(session_id)
    cfg = load_goal()
    mode = _time(state, now, cfg)
    if mode != "ACTIVE":
        return {"state": mode, "next_action": None, "host_action_authorized": False}
    last = state["last_recorded_at"]
    if last is not None and now < last + cfg["objectives"]["minimum_seconds_between_batches"]:
        return {"state": "COOLDOWN", "remaining_seconds": last + cfg["objectives"]["minimum_seconds_between_batches"] - now,
                "next_action": None, "host_action_authorized": False}
    category, search, batch_id = _selection(state, cfg)
    problems = _admit(state, observation, p04_receipt, category=category, now=now, cfg=cfg)
    if problems:
        return {"state": "ABSTAIN", "problems": problems, "batch_id": batch_id,
                "next_action": None, "host_action_authorized": False, "proof_ceiling": PROOF}
    return {
        "state": "SCOUT_SEARCH_PROPOSED_NOT_AUTHORIZED",
        "batch_id": batch_id, "category": category, "search_term": search,
        "next_action": "LOCAL_HOST_SEARCH_AND_CAPTURE_ONE_BOUNDED_BATCH",
        "max_items": cfg["objectives"]["max_items_per_batch"],
        "requires_reobserved_screen_admit_per_UI_step": True,
        "repeat_cheat_console_setup": False,
        "host_action_authorized": False, "gameplay_certified": False,
        "proof_ceiling": PROOF,
    }


def _norm(value: str) -> str:
    return " ".join(value.lower().split())


def _capture_entry(raw: Mapping) -> dict:
    if not isinstance(raw, Mapping):
        raise ScoutError("INVALID_ITEM_ENTRY")
    name, capture = raw.get("item_label"), raw.get("capture_ref")
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120 or not _opaque(capture):
        raise ScoutError("ITEM_NAME_OR_CAPTURE_REQUIRED")
    if raw.get("result_visible") is not True or type(raw.get("operator_reviewed")) is not bool:
        raise ScoutError("ITEM_VISIBILITY_OR_REVIEW_STATE_REQUIRED")
    pack = raw.get("pack_name", "UNKNOWN")
    if not isinstance(pack, str) or not 1 <= len(pack.strip()) <= 80:
        raise ScoutError("INVALID_PACK_LABEL")
    pack = pack.strip()
    if raw["operator_reviewed"] is False:
        if "price_simoleons" in raw and raw["price_simoleons"] is not None:
            raise ScoutError("UNREVIEWED_PRICE_MUST_NOT_BE_PROMOTED")
        return {"name": name.strip(), "pack": pack, "capture_ref": capture,
                "reviewed": False, "free": None, "price_simoleons": None}
    reviewed = review_catalog_entry(raw)
    if reviewed["state"] == "ENTRY_NOT_VERIFIED":
        raise ScoutError("REVIEWED_ITEM_EVIDENCE_INVALID")
    return {"name": name.strip(), "pack": pack, "capture_ref": capture,
            "reviewed": True, "free": reviewed["free"],
            "price_simoleons": reviewed["price_simoleons"]}


def record_batch(session_id: str, report: Mapping, observation: Mapping, p04_receipt: Mapping,
                 *, now: int | None = None) -> dict:
    now = int(time.time()) if now is None else now
    if not isinstance(report, Mapping):
        raise ScoutError("BATCH_REPORT_NOT_OBJECT")
    encoded = json.dumps(report, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    cfg = load_goal()
    with _lock(session_id):
        state = _read(session_id)
        key = report.get("batch_id")
        for prior in state["batches"]:
            if prior["batch_id"] == key:
                if prior["report_digest"] == digest:
                    return {"state": "BATCH_ALREADY_RECORDED", "batch_id": key, "metrics": _metrics(state),
                            "gameplay_certified": False}
                raise ScoutError("BATCH_RETRY_CONFLICT")
        if _time(state, now, cfg) != "ACTIVE":
            raise ScoutError("MISSION_NOT_ACTIVE_OR_TIMEBOX_EXPIRED")
        category, search, expected = _selection(state, cfg)
        if key != expected or report.get("category") != category or report.get("search_term") != search:
            raise ScoutError("BATCH_ID_OR_SEARCH_MISMATCH")
        problems = _admit(state, observation, p04_receipt, category=category, now=now, cfg=cfg)
        if problems:
            raise ScoutError("BATCH_HOST_ADMISSION_FAILED:" + ",".join(problems))
        if not _opaque(report.get("search_capture_ref")):
            raise ScoutError("SEARCH_CAPTURE_REQUIRED")
        results = report.get("items")
        if not isinstance(results, list) or len(results) > cfg["objectives"]["max_items_per_batch"]:
            raise ScoutError("BATCH_ITEMS_LIMIT_OR_SHAPE")
        if report.get("result_state") not in ("ITEMS_CAPTURED", "NO_MATCH"):
            raise ScoutError("BATCH_RESULT_STATE_INVALID")
        if report["result_state"] == "NO_MATCH" and results:
            raise ScoutError("NO_MATCH_WITH_ITEMS")
        if report["result_state"] == "ITEMS_CAPTURED" and not results:
            raise ScoutError("ITEMS_CAPTURED_EMPTY")
        proposed = [_capture_entry(row) for row in results]
        captures = [report["search_capture_ref"]] + [row["capture_ref"] for row in proposed]
        if len(captures) != len(set(captures)):
            raise ScoutError("BATCH_CAPTURE_COLLISION")
        prior_captures = {b["search_capture_ref"] for b in state["batches"]}
        prior_captures.update(v["capture_ref"] for v in state["items"].values())
        if any(ref in prior_captures for ref in captures):
            raise ScoutError("REUSED_CAPTURE_PROVENANCE")
        count = 0
        promoted = 0
        updated = dict(state["items"])
        for row in proposed:
            stable = _norm(row["name"]) + "|" + _norm(row["pack"])
            old = updated.get(stable)
            if old is None:
                updated[stable] = {**row, "category": category}
                count += 1
            elif row["reviewed"] and not old["reviewed"]:
                updated[stable] = {**row, "category": old["category"]}
                promoted += 1
            elif row["reviewed"] and old["reviewed"]:
                if old["price_simoleons"] is not None and row["price_simoleons"] is not None and old["price_simoleons"] != row["price_simoleons"]:
                    raise ScoutError("CONFLICTING_REVIEWED_PRICE")
                if old["price_simoleons"] is None and row["price_simoleons"] is not None:
                    updated[stable] = {**row, "category": old["category"]}
                    promoted += 1
        state["items"] = updated
        state["batches"].append({
            "batch_id": key, "category": category, "search_term": search,
            "search_capture_ref": report["search_capture_ref"], "report_digest": digest,
            "observed_at_unix": observation["observed_at_unix"],
            "new_unique_items": count, "promoted_reviews": promoted,
        })
        state["pinned_build"] = observation["exact_game_build"]
        state["pinned_platform"] = observation["platform"]
        state["pinned_save_ref"] = observation["save_ref"]
        state["last_recorded_at"] = now
        state["consecutive_zero_new"] = 0 if count + promoted else state["consecutive_zero_new"] + 1
        _write(session_id, state)
    return {"state": "BATCH_CHECKPOINTED_NOT_GAME_CERTIFIED",
            "batch_id": key, "new_unique": count, "promoted_reviews": promoted,
            "metrics": _metrics(state), "gameplay_certified": False, "proof_ceiling": PROOF}


def change_mode(session_id: str, action: str, *, now: int | None = None) -> dict:
    now = int(time.time()) if now is None else now
    if action not in ("pause", "resume", "stop"):
        raise ScoutError("UNKNOWN_MISSION_ACTION")
    with _lock(session_id):
        state = _read(session_id)
        mode = state["mode"]
        if action == "pause":
            if mode != "ACTIVE" or _time(state, now, load_goal()) != "ACTIVE":
                raise ScoutError("MISSION_NOT_PAUSABLE")
            state["mode"] = "PAUSED"
            state["paused_at"] = now
        elif action == "resume":
            if mode != "PAUSED":
                raise ScoutError("MISSION_NOT_PAUSED")
            state["deadline"] += max(0, now - state["paused_at"])
            state["paused_at"] = None
            state["mode"] = "ACTIVE"
        elif action == "stop":
            if mode == "STOPPED":
                return status(session_id, now=now)
            state["mode"] = "STOPPED"
        _write(session_id, state)
    return status(session_id, now=now)
