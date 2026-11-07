"""Opt-in host listener session: observe queue → evaluate → plan (no daemon).

Activation is explicit. Library never starts threads. Live clicks stay outside.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Mapping, Sequence

from betterinstincts.behavior_eval import BehaviorEvalError, evaluate_queue
from betterinstincts.host_stack import HostStackError, evaluate_turn
from betterinstincts.instincts_host import InstinctsHostError, NeedSnapshot, plan, plan_to_dict
from betterinstincts.needs_force import NeedsForceError, plan_force
from betterinstincts.player_presence import (
    PlayerPresenceError,
    PresenceProbe,
    classify as classify_presence,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "host-listener.v1.json"
OUTPUT = ROOT / "dist" / "host-listener"
MAX_CONTRACT = 32_000
SIX = frozenset({"hunger", "bladder", "energy", "hygiene", "fun", "social"})


class HostListenerError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_CONTRACT:
        raise HostListenerError("HOST_LISTENER_CONTRACT_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.host-listener/v1":
        raise HostListenerError("BAD_HOST_LISTENER_SCHEMA")
    if cfg.get("activation", {}).get("require_explicit_activate") is not True:
        raise HostListenerError("LISTENER_MUST_REQUIRE_EXPLICIT_ACTIVATE")
    if cfg.get("activation", {}).get("forbid_autorun") is not True:
        raise HostListenerError("LISTENER_MUST_FORBID_AUTORUN")
    return cfg


def _session_dir(session_id: str) -> Path:
    if not session_id or not session_id.replace("-", "").replace("_", "").isalnum() or len(session_id) > 64:
        raise HostListenerError("INVALID_SESSION_ID")
    root = OUTPUT.resolve()
    path = (OUTPUT / session_id).resolve()
    if not path.is_relative_to(root):
        raise HostListenerError("SESSION_OUTSIDE_DIST")
    return path


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if len(raw.encode("utf-8")) > 64_000:
        raise HostListenerError("SESSION_PAYLOAD_TOO_LARGE")
    path.write_text(raw, encoding="utf-8")


def activate(session_id: str, *, note: str | None = None) -> dict:
    cfg = load_contract()
    path = _session_dir(session_id)
    meta_path = path / "session.json"
    if meta_path.is_file():
        existing = json.loads(meta_path.read_text(encoding="utf-8"))
        if existing.get("state") == "ACTIVE":
            return {"state": "ALREADY_ACTIVE", "session_id": session_id, "path": str(path.relative_to(ROOT))}
    payload = {
        "schema": "betterinstincts.host-listener.session/v1",
        "session_id": session_id,
        "state": "ACTIVE",
        "activated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ticks": 0,
        "max_ticks": int(cfg["bounds"]["max_ticks_per_session"]),
        "note": note,
        "proof_ceiling": cfg.get("proof_ceiling"),
        "contract": "contracts/host-listener.v1.json",
    }
    _write_json(meta_path, payload)
    return {"state": "ACTIVATED", "session_id": session_id, "path": str(path.relative_to(ROOT))}


def deactivate(session_id: str) -> dict:
    path = _session_dir(session_id)
    meta_path = path / "session.json"
    if not meta_path.is_file():
        raise HostListenerError("SESSION_NOT_FOUND")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["state"] = "INACTIVE"
    meta["deactivated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _write_json(meta_path, meta)
    return {"state": "DEACTIVATED", "session_id": session_id}


def status(session_id: str) -> dict:
    path = _session_dir(session_id)
    meta_path = path / "session.json"
    if not meta_path.is_file():
        return {"state": "INACTIVE", "session_id": session_id, "reason": "NO_SESSION"}
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return {
        "state": meta.get("state", "UNKNOWN"),
        "session_id": session_id,
        "ticks": meta.get("ticks", 0),
        "max_ticks": meta.get("max_ticks"),
        "path": str(path.relative_to(ROOT)),
    }


def _load_observation(raw: Mapping) -> dict:
    if raw.get("schema") != "betterinstincts.host-listener.observation/v1":
        raise HostListenerError("BAD_OBSERVATION_SCHEMA")
    needs = raw.get("needs")
    queue = raw.get("queue")
    location = raw.get("location_kind", "unknown")
    if not isinstance(needs, dict) or set(needs) != SIX:
        raise HostListenerError("OBSERVATION_NEEDS_INVALID")
    if not isinstance(queue, list):
        raise HostListenerError("OBSERVATION_QUEUE_INVALID")
    if location not in {"home", "school", "community", "work", "unknown"}:
        raise HostListenerError("OBSERVATION_LOCATION_INVALID")
    return {
        "needs": {k: float(needs[k]) for k in SIX},
        "queue": [str(x) for x in queue],
        "location_kind": location,
        "objects_on_current_lot": bool(raw.get("objects_on_current_lot", location == "home")),
        "player_directed": bool(raw.get("player_directed", False)),
        "already_busy": bool(raw.get("already_busy", False)),
        "available_objects": tuple(raw.get("available_objects") or ()),
        "capture_ref": str(raw.get("capture_ref") or "capture:listener"),
        "viewport": raw.get("viewport"),
    }


def tick(
    session_id: str,
    observation: Mapping,
    *,
    presence_probe: PresenceProbe | None = None,
) -> dict:
    """One evaluator pass for an ACTIVE session. Plan only — no SendInput."""
    cfg = load_contract()
    path = _session_dir(session_id)
    meta_path = path / "session.json"
    if not meta_path.is_file():
        raise HostListenerError("SESSION_NOT_ACTIVE")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("state") != "ACTIVE":
        raise HostListenerError("SESSION_NOT_ACTIVE")
    ticks = int(meta.get("ticks") or 0)
    if ticks >= int(meta.get("max_ticks") or cfg["bounds"]["max_ticks_per_session"]):
        raise HostListenerError("SESSION_TICK_BUDGET_EXCEEDED")

    obs = _load_observation(observation)
    # Presence gate: if operator is on-canvas / playing, yield before eval side-plans.
    if presence_probe is None:
        presence_probe = PresenceProbe(
            foreground_is_sims=False,
            cursor_in_client=False,
            operator_declared_playing=bool(observation.get("operator_declared_playing", False)),
            player_directed_queue=bool(obs["player_directed"]),
            probe_ok=True,
        )
    else:
        # Merge observation player_directed into probe if set.
        if obs["player_directed"] and not presence_probe.player_directed_queue:
            presence_probe = PresenceProbe(
                foreground_is_sims=presence_probe.foreground_is_sims,
                cursor_in_client=presence_probe.cursor_in_client,
                last_input_age_ms=presence_probe.last_input_age_ms,
                operator_declared_playing=presence_probe.operator_declared_playing,
                player_directed_queue=True,
                probe_ok=presence_probe.probe_ok,
            )
    try:
        presence = classify_presence(presence_probe, session_active=True)
    except PlayerPresenceError as exc:
        raise HostListenerError(str(exc)) from exc
    if presence["host"] == "YIELD_TO_PLAYER":
        ticks = ticks + 1
        meta["ticks"] = ticks
        meta["last_tick_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        meta["last_disposition"] = "YIELD_TO_PLAYER"
        receipt = {
            "schema": "betterinstincts.host-listener.tick/v1",
            "session_id": session_id,
            "tick": ticks,
            "presence": presence,
            "listener_action": "YIELD_TO_PLAYER",
            "execute_clicks": False,
            "proof_ceiling": cfg.get("proof_ceiling"),
            "next": "Player playing or unknown presence — host stands down this tick.",
        }
        _write_json(meta_path, meta)
        tick_path = path / f"tick-{ticks:04d}.json"
        _write_json(tick_path, receipt)
        receipt["receipt"] = str(tick_path.relative_to(ROOT))
        return receipt

    try:
        behavior = evaluate_queue(
            obs["needs"],
            obs["queue"],
            player_directed=obs["player_directed"],
            objects_on_current_lot=obs["objects_on_current_lot"],
            location_kind=obs["location_kind"],
            capture_ref=obs["capture_ref"],
        )
        snap = NeedSnapshot(
            needs=obs["needs"],
            available_objects=obs["available_objects"],
            player_directed=obs["player_directed"],
            already_busy=obs["already_busy"],
            capture_ref=obs["capture_ref"],
        )
        instincts = plan_to_dict(plan(snap))
        stack = evaluate_turn(
            obs["needs"],
            available_objects=obs["available_objects"],
            player_directed=obs["player_directed"],
            already_busy=obs["already_busy"],
            capture_ref=obs["capture_ref"],
            viewport=obs.get("viewport"),
            location_kind=obs["location_kind"],
            objects_on_current_lot=obs["objects_on_current_lot"],
            queue=obs["queue"],
        )
        force = plan_force(
            location_kind=obs["location_kind"],
            objects_on_current_lot=obs["objects_on_current_lot"],
            disposition=behavior["clarity"]["disposition"],
        )
    except (BehaviorEvalError, InstinctsHostError, HostStackError, NeedsForceError) as exc:
        raise HostListenerError(str(exc)) from exc

    disposition = behavior["clarity"]["disposition"]
    receipt = {
        "schema": "betterinstincts.host-listener.tick/v1",
        "session_id": session_id,
        "tick": ticks + 1,
        "presence": presence,
        "behavior": behavior,
        "instincts": instincts,
        "host_stack": stack,
        "needs_force_plan": force,
        "listener_action": (
            "RECORD_EMULATION_PLAN"
            if disposition == "EMULATE"
            else "RECORD_OPTIMIZATION_PLAN"
            if disposition == "OPTIMIZE"
            else "RECORD_EMULATE_THEN_OPTIMIZE_PLAN"
        ),
        "execute_clicks": False,
        "proof_ceiling": cfg.get("proof_ceiling"),
        "next": (
            "If OPTIMIZE/MAP_TRAVEL and still HOST_MAY_AUTOMATE: "
            "python -m scripts.needs_force run --location-kind "
            f"{obs['location_kind']} --process-id PID --execute "
            "(re-probe presence first). Listener itself never SendInputs."
        ),
    }
    meta["ticks"] = ticks + 1
    meta["last_tick_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    meta["last_disposition"] = disposition
    _write_json(meta_path, meta)
    tick_path = path / f"tick-{ticks + 1:04d}.json"
    _write_json(tick_path, receipt)
    receipt["receipt"] = str(tick_path.relative_to(ROOT))
    return receipt
