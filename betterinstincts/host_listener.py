"""Opt-in host listener session: observe queue → evaluate → plan (no daemon).

Activation is explicit. Library never starts threads. Live clicks stay outside.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Mapping, Sequence
from dataclasses import replace

from betterinstincts.behavior_eval import BehaviorEvalError, evaluate_queue
from betterinstincts.build_floor_activity import (
    BuildFloorActivityError,
    evaluate_floor_activity,
)
from betterinstincts.host_stack import HostStackError, evaluate_turn
from betterinstincts.instincts_host import InstinctsHostError, NeedSnapshot, plan, plan_to_dict
from betterinstincts.needs_force import NeedsForceError, plan_force
from betterinstincts.judgment_learning import JudgmentLearningError, recommend as recommend_judgment
from betterinstincts.player_presence import PresenceProbe
from betterinstincts.ui_mode import UIModeError, evaluate_mode
from betterinstincts.control_handoff import (
    DEFAULT_IDLE_MS,
    HandoffError,
    as_presence,
    decide,
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


def observe_hover(
    session_id: str, supplied_event: Mapping, *, explicit_opt_in: bool = False
) -> dict:
    """Ingest one supplied tooltip edge/action/outcome into an active session.

    This is an observational port; the caller owns any calibrated sensing.
    One writer per session, atomic sidecar replacement, no game input or timer.
    """
    import os
    import tempfile

    from betterinstincts.hover_learning import (
        HoverLearningError, MAX_BYTES, empty_state, evaluate, observe,
    )

    if explicit_opt_in is not True:
        raise HostListenerError("EXPLICIT_HOVER_OPT_IN_REQUIRED")
    path = _session_dir(session_id)
    meta_path = path / "session.json"
    if meta_path.is_symlink() or not meta_path.is_file():
        raise HostListenerError("HOVER_SESSION_NOT_ACTIVE")
    state_path = path / "hover-learning.json"
    lock_path = path / ".hover-writer.lock"
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise HostListenerError("HOVER_WRITER_BUSY") from exc
    try:
        os.close(fd)
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("state") != "ACTIVE":
            raise HostListenerError("HOVER_SESSION_NOT_ACTIVE")
        if state_path.is_symlink():
            raise HostListenerError("HOVER_STATE_SYMLINK_FORBIDDEN")
        if state_path.exists():
            if not state_path.is_file() or state_path.stat().st_size > MAX_BYTES:
                raise HostListenerError("HOVER_STATE_FILE_UNSAFE")
            current = json.loads(state_path.read_text(encoding="utf-8"))
        else:
            current = empty_state()
        try:
            updated, transition = observe(current, supplied_event)
            evaluation = evaluate(updated, now_ms=supplied_event["at_ms"])
        except (HoverLearningError, KeyError) as exc:
            raise HostListenerError("HOVER_EVENT_INVALID:" + str(exc)) from exc
        if transition["recorded"]:
            raw = json.dumps(updated, sort_keys=True, indent=2) + "\n"
            if len(raw.encode("utf-8")) > MAX_BYTES:
                raise HostListenerError("HOVER_STATE_BUDGET_EXCEEDED")
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", dir=path,
                    prefix=".hover-", suffix=".tmp", delete=False,
                ) as handle:
                    temporary = Path(handle.name)
                    handle.write(raw)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, state_path)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
        return {
            "schema": "betterinstincts.hover-observation-receipt/v1",
            "session_id": session_id, "transition": transition,
            "evaluation": evaluation, "state_path": str(state_path.relative_to(ROOT)),
            "execute_clicks": False, "control_permit": None,
        }
    finally:
        lock_path.unlink(missing_ok=True)


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
    school_goals = raw.get("school_goals_incomplete") or ()
    if not isinstance(school_goals, (list, tuple)):
        raise HostListenerError("OBSERVATION_SCHOOL_GOALS_INVALID")
    scenario_goals = raw.get("scenario_goals_incomplete") or ()
    if not isinstance(scenario_goals, (list, tuple)):
        raise HostListenerError("OBSERVATION_SCENARIO_GOALS_INVALID")
    navigating_goals = raw.get("navigating_needs_incomplete") or ()
    if not isinstance(navigating_goals, (list, tuple)):
        raise HostListenerError("OBSERVATION_NAVIGATING_NEEDS_INVALID")
    pinned = raw.get("pinned_whims") or ()
    if not isinstance(pinned, (list, tuple)):
        raise HostListenerError("OBSERVATION_PINNED_WHIMS_INVALID")
    traits = raw.get("traits") or ()
    if not isinstance(traits, (list, tuple)):
        raise HostListenerError("OBSERVATION_TRAITS_INVALID")
    inv = raw.get("inventory_has_homework")
    if inv is not None and not isinstance(inv, bool):
        raise HostListenerError("OBSERVATION_INVENTORY_HOMEWORK_INVALID")
    on_lot_hw = raw.get("homework_on_lot")
    if on_lot_hw is not None and not isinstance(on_lot_hw, bool):
        raise HostListenerError("OBSERVATION_HOMEWORK_ON_LOT_INVALID")
    sim_at_school = raw.get("sim_at_school")
    if sim_at_school is not None and not isinstance(sim_at_school, bool):
        raise HostListenerError("OBSERVATION_SIM_AT_SCHOOL_INVALID")
    sim_library = raw.get("sim_library") or ()
    if not isinstance(sim_library, (list, tuple)):
        raise HostListenerError("OBSERVATION_SIM_LIBRARY_INVALID")
    life_stage = raw.get("life_stage")
    if life_stage is not None and not isinstance(life_stage, str):
        raise HostListenerError("OBSERVATION_LIFE_STAGE_INVALID")
    gardening = raw.get("gardening")
    if gardening is not None and not isinstance(gardening, Mapping):
        raise HostListenerError("OBSERVATION_GARDENING_INVALID")
    cursor_x = raw.get("cursor_client_x")
    cursor_y = raw.get("cursor_client_y")
    for label, val in (("cursor_client_x", cursor_x), ("cursor_client_y", cursor_y)):
        if val is not None and (isinstance(val, bool) or not isinstance(val, int)):
            raise HostListenerError("OBSERVATION_CURSOR_INVALID:" + label)
    client_w = raw.get("client_width")
    client_h = raw.get("client_height")
    for label, val in (("client_width", client_w), ("client_height", client_h)):
        if val is not None and (isinstance(val, bool) or not isinstance(val, int)):
            raise HostListenerError("OBSERVATION_CLIENT_SIZE_INVALID:" + label)
    pan_dirs = raw.get("camera_pan_directions") or ()
    if not isinstance(pan_dirs, (list, tuple)):
        raise HostListenerError("OBSERVATION_CAMERA_PAN_DIRS_INVALID")
    world_target = raw.get("world_target")
    if world_target is not None:
        if not isinstance(world_target, Mapping) or len(json.dumps(dict(world_target))) > 8192:
            raise HostListenerError("OBSERVATION_WORLD_TARGET_INVALID")
    stories_touched = raw.get("stories_touched") or ()
    if not isinstance(stories_touched, (list, tuple)):
        raise HostListenerError("OBSERVATION_STORIES_TOUCHED_INVALID")
    floor_items = raw.get("floor_items") or ()
    if not isinstance(floor_items, (list, tuple)):
        raise HostListenerError("OBSERVATION_FLOOR_ITEMS_INVALID")
    lot_model = raw.get("lot_model")
    if lot_model is not None:
        if not isinstance(lot_model, Mapping) or len(json.dumps(lot_model).encode("utf-8")) > 262144:
            raise HostListenerError("OBSERVATION_LOT_MODEL_INVALID")
    return {
        "needs": {k: float(needs[k]) for k in SIX},
        "gardening": dict(gardening) if gardening is not None else None,
        "queue": [str(x) for x in queue],
        "location_kind": location,
        "objects_on_current_lot": bool(raw.get("objects_on_current_lot", location == "home")),
        "player_directed": bool(raw.get("player_directed", False)),
        "already_busy": bool(raw.get("already_busy", False)),
        "available_objects": tuple(raw.get("available_objects") or ()),
        "capture_ref": str(raw.get("capture_ref") or "capture:listener"),
        "viewport": raw.get("viewport"),
        "school_day_active": bool(raw.get("school_day_active", False)),
        "school_goals_incomplete": [str(x) for x in school_goals],
        "scenario_active": bool(raw.get("scenario_active", False)),
        "scenario_goals_incomplete": [str(x) for x in scenario_goals],
        "scenario_profile": str(raw.get("scenario_profile") or "scoring_simoleons"),
        "allow_career": bool(raw.get("allow_career", False)),
        "needs_game_certified": bool(raw.get("needs_game_certified", False)),
        "income_game_observed": bool(raw.get("income_game_observed", False)),
        "navigating_needs_active": bool(raw.get("navigating_needs_active", False)),
        "navigating_needs_incomplete": [str(x) for x in navigating_goals],
        "navigating_needs_profile": str(
            raw.get("navigating_needs_profile") or "navigating_needs"
        ),
        "build_or_buy_mode": bool(raw.get("build_or_buy_mode", False)),
        "active_story": raw.get("active_story"),
        "stories_touched": list(raw.get("stories_touched") or []),
        "floor_items": list(raw.get("floor_items") or []),
        "lot_model": lot_model,
        "school_phase": (str(raw["school_phase"]) if raw.get("school_phase") else None),
        "pinned_whims": [str(x) for x in pinned],
        "homework_pending": bool(raw.get("homework_pending", False)),
        "inventory_has_homework": inv if isinstance(inv, bool) else None,
        "homework_on_lot": on_lot_hw if isinstance(on_lot_hw, bool) else None,
        "prior_career_state": (
            raw.get("prior_career_state")
            if isinstance(raw.get("prior_career_state"), Mapping)
            else None
        ),
        "aspiration_prompt_active": bool(raw.get("aspiration_prompt_active", False)),
        "aspiration_prompt_id": (
            str(raw["aspiration_prompt_id"]) if raw.get("aspiration_prompt_id") else None
        ),
        "aspiration_prompt_text": str(raw.get("aspiration_prompt_text") or ""),
        "aspiration_completion_enabled": bool(
            raw.get("aspiration_completion_enabled", False)
        ),
        "occult_needs_engine_ready": bool(raw.get("occult_needs_engine_ready", False)),
        "operator_prefers_aspiration_ok": (
            bool(raw["operator_prefers_aspiration_ok"])
            if isinstance(raw.get("operator_prefers_aspiration_ok"), bool)
            else None
        ),
        "prior_aspiration_state": (
            raw.get("prior_aspiration_state")
            if isinstance(raw.get("prior_aspiration_state"), Mapping)
            else None
        ),
        "balance_level": (
            str(raw["balance_level"]) if raw.get("balance_level") else None
        ),
        "ailment": str(raw["ailment"]) if raw.get("ailment") else None,
        "inventory_has_holistic_cure": (
            bool(raw["inventory_has_holistic_cure"])
            if isinstance(raw.get("inventory_has_holistic_cure"), bool)
            else None
        ),
        "apothecary_stall_available": bool(raw.get("apothecary_stall_available", False)),
        "apothecary_skill_level": (
            int(raw["apothecary_skill_level"])
            if isinstance(raw.get("apothecary_skill_level"), int)
            else None
        ),
        "natural_living_meditate_available": bool(
            raw.get("natural_living_meditate_available", False)
        ),
        "houseplants_available": bool(raw.get("houseplants_available", False)),
        "prior_balance_state": (
            raw.get("prior_balance_state")
            if isinstance(raw.get("prior_balance_state"), Mapping)
            else None
        ),
        "sim_at_school": sim_at_school if isinstance(sim_at_school, bool) else None,
        "camera_lot_kind": (
            str(raw["camera_lot_kind"]) if raw.get("camera_lot_kind") else None
        ),
        "social_prompt_active": bool(raw.get("social_prompt_active", False)),
        "social_prompt_kind": str(raw.get("social_prompt_kind") or "invite_over"),
        "social_prompt_text": str(raw.get("social_prompt_text") or ""),
        "social_invitee_name": (
            str(raw["social_invitee_name"]) if raw.get("social_invitee_name") else None
        ),
        "sim_library": tuple(sim_library),
        "social_lookup_ran": bool(raw.get("social_lookup_ran", False)),
        "invitee_occult_status": (
            str(raw["invitee_occult_status"]) if raw.get("invitee_occult_status") else None
        ),
        "life_stage": (str(life_stage) if life_stage else None),
        "emotion": (str(raw["emotion"]) if raw.get("emotion") else None),
        "moodlets": [str(x) for x in (raw.get("moodlets") or ())],
        "traits": [str(x) for x in traits],
        "whims": [str(x) for x in (raw.get("whims") or ())],
        "cursor_client_x": cursor_x if isinstance(cursor_x, int) else None,
        "cursor_client_y": cursor_y if isinstance(cursor_y, int) else None,
        "client_width": client_w if isinstance(client_w, int) else None,
        "client_height": client_h if isinstance(client_h, int) else None,
        "edge_band_px": (
            int(raw["edge_band_px"])
            if isinstance(raw.get("edge_band_px"), int) and not isinstance(raw.get("edge_band_px"), bool)
            else None
        ),
        "camera_scan_needed": bool(raw.get("camera_scan_needed", False)),
        "camera_pan_directions": [str(x) for x in pan_dirs],
        "world_target": dict(world_target) if world_target is not None else None,
    }


def tick(
    session_id: str,
    observation: Mapping,
    *,
    presence_probe: PresenceProbe | None = None,
    idle_ms: int = DEFAULT_IDLE_MS,
    learning_model: Mapping | None = None,
    learning_query: Mapping | None = None,
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
    # New mode sensing is opt-in so pre-existing listener receipts remain valid.
    # Keyboard shortcuts and the old combined boolean are never scene proof.
    mode_context = None
    if any(k in observation for k in (
        "mode_observations", "panel_observations", "shortcut_hint"
    )):
        try:
            mode_context = evaluate_mode(
                game_version=observation.get("game_version"),
                mode_observations=observation.get("mode_observations", []),
                panel_observations=observation.get("panel_observations"),
                shortcut_hint=observation.get("shortcut_hint"),
            )
        except UIModeError as exc:
            raise HostListenerError("MODE_CONTEXT_INVALID:" + str(exc)) from exc
        observed_mode = mode_context["mode"]
        # A contradictory legacy flag is a real sensor conflict, not a vote.
        if (
            "build_or_buy_mode" in observation
            and bool(observation["build_or_buy_mode"]) != (observed_mode in {"BUY", "BUILD"})
            and observed_mode != "UNKNOWN"
        ):
            mode_context = {
                **mode_context, "state": "MODE_UNVERIFIED", "mode": "UNKNOWN",
                "mode_autonomy_allowed": False, "reason": "LEGACY_MODE_CONFLICT",
            }
        else:
            obs["build_or_buy_mode"] = observed_mode in {"BUY", "BUILD"}
    if (learning_model is None) != (learning_query is None):
        raise HostListenerError("LEARNING_MODEL_AND_QUERY_REQUIRED_TOGETHER")
    # Presence gate: if operator is on-canvas / playing, yield before eval side-plans.
    if presence_probe is None:
        presence_probe = PresenceProbe(
            foreground_is_sims=False,
            cursor_in_client=False,
            operator_declared_playing=bool(observation.get("operator_declared_playing", False)),
            player_directed_queue=bool(obs["player_directed"]),
            probe_ok=False,  # No OS probe is not proof of idle.
        )
    if obs["player_directed"] or observation.get("operator_declared_playing"):
        presence_probe = replace(
            presence_probe,
            player_directed_queue=presence_probe.player_directed_queue or obs["player_directed"],
            operator_declared_playing=presence_probe.operator_declared_playing or bool(observation.get("operator_declared_playing")),
        )
    try:
        handoff = decide(presence_probe, session_active=True, idle_ms=idle_ms)
    except HandoffError as exc:
        raise HostListenerError(str(exc)) from exc
    presence = as_presence(handoff)
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
            "handoff": handoff,
            "listener_action": "YIELD_TO_PLAYER",
            "ui_mode": mode_context,
            "execute_clicks": False,
            "proof_ceiling": cfg.get("proof_ceiling"),
            "next": "Player playing or unknown presence — host stands down this tick.",
        }
        _write_json(meta_path, meta)
        tick_path = path / f"tick-{ticks:04d}.json"
        _write_json(tick_path, receipt)
        receipt["receipt"] = str(tick_path.relative_to(ROOT))
        return receipt

    # Non-Live and ambiguous scenes still provide bounded interface context,
    # never a simulated Live queue/needs plan. The Build census is advisory.
    if mode_context is not None and not mode_context["mode_autonomy_allowed"]:
        try:
            floor_activity = evaluate_floor_activity(
                build_or_buy_mode=mode_context["mode"] in {"BUY", "BUILD"},
                active_story=obs.get("active_story"),
                stories_touched=obs.get("stories_touched") or (),
                floor_items=obs.get("floor_items") or (),
                player_directed=obs["player_directed"],
                lot_model=obs.get("lot_model"),
            )
        except BuildFloorActivityError as exc:
            raise HostListenerError(str(exc)) from exc
        ticks += 1
        listener_action = (
            "MODE_CONTEXT_ONLY" if mode_context["mode"] in {"BUY", "BUILD"}
            else "MODE_UNVERIFIED"
        )
        receipt = {
            "schema": "betterinstincts.host-listener.tick/v1",
            "session_id": session_id, "tick": ticks,
            "presence": presence, "handoff": handoff,
            "ui_mode": mode_context,
            "build_floor_activity": floor_activity,
            "listener_action": listener_action,
            "execute_clicks": False,
            "proof_ceiling": cfg.get("proof_ceiling"),
            "next": "Observe the game mode again; do not dispatch Live actions.",
        }
        meta["ticks"] = ticks
        meta["last_tick_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        meta["last_disposition"] = listener_action
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
            school_day_active=obs["school_day_active"],
            school_goals_incomplete=obs["school_goals_incomplete"],
            school_phase=obs["school_phase"],
            pinned_whims=obs["pinned_whims"],
            homework_pending=obs["homework_pending"],
            inventory_has_homework=obs["inventory_has_homework"],
            homework_on_lot=obs["homework_on_lot"],
            sim_at_school=obs["sim_at_school"],
            camera_lot_kind=obs["camera_lot_kind"],
            social_prompt_active=obs["social_prompt_active"],
            social_prompt_kind=obs["social_prompt_kind"],
            social_prompt_text=obs["social_prompt_text"],
            social_invitee_name=obs["social_invitee_name"],
            sim_library=obs["sim_library"],
            social_lookup_ran=obs["social_lookup_ran"],
            invitee_occult_status=obs["invitee_occult_status"],
            life_stage=obs["life_stage"],
            scenario_active=obs["scenario_active"],
            scenario_goals_incomplete=obs["scenario_goals_incomplete"],
            scenario_profile=obs["scenario_profile"],
            allow_career=obs["allow_career"],
            needs_game_certified=obs["needs_game_certified"],
            income_game_observed=obs["income_game_observed"],
            navigating_needs_active=obs["navigating_needs_active"],
            navigating_needs_incomplete=obs["navigating_needs_incomplete"],
            navigating_needs_profile=obs["navigating_needs_profile"],
            build_or_buy_mode=obs["build_or_buy_mode"],
            cursor_client_x=obs["cursor_client_x"],
            cursor_client_y=obs["cursor_client_y"],
            client_width=obs["client_width"],
            client_height=obs["client_height"],
            edge_band_px=obs["edge_band_px"],
            camera_scan_needed=obs["camera_scan_needed"],
            camera_pan_directions=obs["camera_pan_directions"],
            world_target=obs["world_target"],
            emotion=obs["emotion"],
            moodlets=obs["moodlets"],
            traits=obs["traits"],
            whims=obs["whims"] or obs["pinned_whims"],
            gardening=obs["gardening"],
            prior_career_state=obs.get("prior_career_state"),
            aspiration_prompt_active=obs.get("aspiration_prompt_active", False),
            aspiration_prompt_id=obs.get("aspiration_prompt_id"),
            aspiration_prompt_text=obs.get("aspiration_prompt_text") or "",
            aspiration_completion_enabled=obs.get(
                "aspiration_completion_enabled", False
            ),
            occult_needs_engine_ready=obs.get("occult_needs_engine_ready", False),
            operator_prefers_aspiration_ok=obs.get("operator_prefers_aspiration_ok"),
            prior_aspiration_state=obs.get("prior_aspiration_state"),
            balance_level=obs.get("balance_level"),
            ailment=obs.get("ailment"),
            inventory_has_holistic_cure=obs.get("inventory_has_holistic_cure"),
            apothecary_stall_available=obs.get("apothecary_stall_available", False),
            apothecary_skill_level=obs.get("apothecary_skill_level"),
            natural_living_meditate_available=obs.get(
                "natural_living_meditate_available", False
            ),
            houseplants_available=obs.get("houseplants_available", False),
            prior_balance_state=obs.get("prior_balance_state"),
        )
        force = plan_force(
            location_kind=obs["location_kind"],
            objects_on_current_lot=obs["objects_on_current_lot"],
            disposition=behavior["clarity"]["disposition"],
        )
        floor_activity = evaluate_floor_activity(
            build_or_buy_mode=obs["build_or_buy_mode"],
            active_story=obs.get("active_story"),
            stories_touched=obs.get("stories_touched") or (),
            floor_items=obs.get("floor_items") or (),
            player_directed=obs["player_directed"],
            lot_model=obs.get("lot_model"),
        )
    except (
        BehaviorEvalError,
        InstinctsHostError,
        HostStackError,
        NeedsForceError,
        BuildFloorActivityError,
    ) as exc:
        raise HostListenerError(str(exc)) from exc

    disposition = behavior["clarity"]["disposition"]
    receipt = {
        "schema": "betterinstincts.host-listener.tick/v1",
        "session_id": session_id,
        "tick": ticks + 1,
        "presence": presence,
        "handoff": handoff,
        "behavior": behavior,
        "instincts": instincts,
        "host_stack": stack,
        "needs_force_plan": force,
        "build_floor_activity": floor_activity,
        "ui_mode": mode_context,
        "learning_hint": None,
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
    # Learning has no input hooks and never changes host plans. Explicit
    # model/query are required; a player-directed or unknown scene must abstain.
    if learning_model is not None:
        safe_query = dict(learning_query)
        safe_query["player_directed"] = bool(obs["player_directed"])
        safe_query["player_active"] = False  # Already yielded on active/unknown presence.
        safe_query["scene_verified"] = bool(
            safe_query.get("scene_verified")
            and isinstance(obs.get("viewport"), dict)
            and obs["viewport"].get("state") == "VIEWPORT_OK"
        )
        try:
            receipt["learning_hint"] = recommend_judgment(learning_model, safe_query)
        except JudgmentLearningError as exc:
            raise HostListenerError("LEARNING_HINT_INVALID:" + str(exc)) from exc
        # Recommendations NEVER execute: preserve existing behavior/needs owner.
        receipt["learning_hint"]["execute_clicks"] = False
    meta["ticks"] = ticks + 1
    meta["last_tick_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    meta["last_disposition"] = disposition
    _write_json(meta_path, meta)
    tick_path = path / f"tick-{ticks + 1:04d}.json"
    _write_json(tick_path, receipt)
    receipt["receipt"] = str(tick_path.relative_to(ROOT))
    return receipt
