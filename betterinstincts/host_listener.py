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
from betterinstincts.affordance_memory import (
    AffordanceMemoryError, empty_index, load_index, record_event,
)
from betterinstincts.opportunity_survey import (
    OpportunitySurveyError, evaluate_opportunity_survey,
)
from betterinstincts.build_floor_activity import (
    BuildFloorActivityError,
    evaluate_floor_activity,
)
from betterinstincts.host_stack import HostStackError, evaluate_turn
from betterinstincts.chance_event_research import (
    ChanceEventError, assess as assess_chance_event, load_memo as load_chance_memo,
)
from betterinstincts.sim_camera import command_from_app_hotkey
from betterinstincts.instincts_host import InstinctsHostError, NeedSnapshot, plan, plan_to_dict
from betterinstincts.needs_force import NeedsForceError, plan_force
from betterinstincts.judgment_learning import JudgmentLearningError, recommend as recommend_judgment
from betterinstincts.behavior_valence import (
    BehaviorValenceError, MAX_MODEL_BYTES,
    learn_reviewed, validate_model,
)
from betterinstincts.player_presence import PresenceProbe
from betterinstincts.ui_mode import UIModeError, evaluate_mode
from betterinstincts.control_handoff import (
    DEFAULT_IDLE_MS,
    HandoffError,
    as_presence,
    decide,
)
from betterinstincts.scenes import load_catalog, stamp_host_capture_branch

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
    session_id: str, supplied_event: Mapping, *, explicit_opt_in: bool = False,
    game_version: str | None = None, lot_id: str | None = None,
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
        # The session event ledger stays canonical; the bounded cross-session
        # index is a projection, not a second hover event parser or policy owner.
        memory = {"state": "UNCHANGED_TOOLTIP", "recorded": False}
        if transition["recorded"]:
            try:
                memory = record_event(
                    OUTPUT / "affordance-memory.v1.json", supplied_event,
                    session_id=session_id, game_version=game_version,
                    lot_id=lot_id, hover_state=updated,
                )
            except AffordanceMemoryError as exc:
                # The session observation is already saved; return a recoverable
                # index warning rather than lying about a durable discovery.
                memory = {"state": "AFFORDANCE_INDEX_REPAIR_REQUIRED",
                          "recorded": False, "reason": str(exc)}
        return {
            "schema": "betterinstincts.hover-observation-receipt/v1",
            "session_id": session_id, "transition": transition,
            "evaluation": evaluation, "state_path": str(state_path.relative_to(ROOT)),
            "affordance_memory": memory,
            "execute_clicks": False, "control_permit": None,
        }
    finally:
        lock_path.unlink(missing_ok=True)


def observe_object_action(
    session_id: str, supplied_event: Mapping, *, explicit_opt_in: bool = False,
) -> dict:
    """Accept sanitized game-object events under an active listener session.

    PLAYER/HOST are event provenance, not a license to intercept the desktop.
    Sensors must explicitly invoke this port for each observed menu/selection/
    outcome. The listener does not start a global hook or issue game input.
    """
    from betterinstincts.object_action_catalog import (
        ObjectActionCatalogError, record_event as record_object_event,
    )

    if explicit_opt_in is not True:
        raise HostListenerError("EXPLICIT_OBJECT_OBSERVATION_OPT_IN_REQUIRED")
    path = _session_dir(session_id)
    metadata = path / "session.json"
    if metadata.is_symlink() or not metadata.is_file():
        raise HostListenerError("OBJECT_SESSION_NOT_ACTIVE")
    session = json.loads(metadata.read_text(encoding="utf-8"))
    if session.get("state") != "ACTIVE":
        raise HostListenerError("OBJECT_SESSION_NOT_ACTIVE")
    try:
        receipt = record_object_event(
            OUTPUT / "object-action-catalog.v1.json",
            supplied_event, session_id=session_id,
        )
    except ObjectActionCatalogError as exc:
        raise HostListenerError("OBJECT_EVENT_INVALID:" + str(exc)) from exc
    return {"schema": "betterinstincts.object-action-observation-receipt/v1",
            "session_id": session_id, "catalog": receipt,
            "execute_clicks": False, "control_permit": None}


def suggest_object_action(session_id: str, query: Mapping) -> dict:
    """Read-only queue candidate for an independently fresh object/menu snapshot."""
    from betterinstincts.object_action_catalog import (
        ObjectActionCatalogError, load_catalog as load_object_catalog, recommend,
    )
    path = _session_dir(session_id)
    metadata = path / "session.json"
    if metadata.is_symlink() or not metadata.is_file():
        raise HostListenerError("OBJECT_SESSION_NOT_ACTIVE")
    session = json.loads(metadata.read_text(encoding="utf-8"))
    if session.get("state") != "ACTIVE":
        raise HostListenerError("OBJECT_SESSION_NOT_ACTIVE")
    required = {"game_version", "object_ref", "class_ref", "capture_ref",
                "now_ms", "available_actions", "desired_domains",
                "player_active", "player_queue_present"}
    if not isinstance(query, dict) or set(query) != required:
        raise HostListenerError("OBJECT_QUERY_FIELDS_INVALID")
    try:
        return recommend(
            load_object_catalog(OUTPUT / "object-action-catalog.v1.json"),
            session_id=session_id, **query,
        )
    except (ObjectActionCatalogError, TypeError) as exc:
        raise HostListenerError("OBJECT_QUERY_INVALID:" + str(exc)) from exc


def observe_behavior_review(
    session_id: str, reviews: list[Mapping], *,
    game_version: str, platform: str,
    explicit_opt_in: bool = False, prior_model: Mapping | None = None,
) -> dict:
    """Explicit supervised-learning write, bounded to one active session.

    This is NOT invoked by tick. Reviewed evidence, not passive observations,
    must drive every update. Persist only aggregates and replay refs.
    """
    import os
    import tempfile
    if explicit_opt_in is not True:
        raise HostListenerError("EXPLICIT_BEHAVIOR_REVIEW_OPT_IN_REQUIRED")
    path = _session_dir(session_id)
    meta_path = path / "session.json"
    if meta_path.is_symlink() or not meta_path.is_file():
        raise HostListenerError("BEHAVIOR_SESSION_NOT_ACTIVE")
    lock_path = path / ".behavior-model-writer.lock"
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise HostListenerError("BEHAVIOR_REVIEW_WRITER_BUSY") from exc
    try:
        os.close(fd)
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("state") != "ACTIVE":
            raise HostListenerError("BEHAVIOR_SESSION_NOT_ACTIVE")
        state_path = path / "behavior-valence.json"
        if state_path.is_symlink():
            raise HostListenerError("BEHAVIOR_MODEL_SYMLINK_FORBIDDEN")
        if state_path.exists():
            if prior_model is not None:
                raise HostListenerError("BEHAVIOR_PRIOR_ALREADY_INITIALIZED")
            if not state_path.is_file() or state_path.stat().st_size > MAX_MODEL_BYTES:
                raise HostListenerError("BEHAVIOR_MODEL_FILE_UNSAFE")
            prior = json.loads(state_path.read_text(encoding="utf-8"))
        else:
            prior = prior_model
        try:
            model = learn_reviewed(
                reviews,game_version=game_version,platform=platform,prior=prior)
        except BehaviorValenceError as exc:
            raise HostListenerError("BEHAVIOR_REVIEW_INVALID:" + str(exc)) from exc
        raw = json.dumps(model,sort_keys=True,indent=2) + "\n"
        if len(raw.encode("utf-8")) > MAX_MODEL_BYTES:
            raise HostListenerError("BEHAVIOR_MODEL_TOO_LARGE")
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",encoding="utf-8",dir=path,
                prefix=".behavior-",suffix=".tmp",delete=False,
            ) as handle:
                temporary = Path(handle.name)
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary,state_path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return {
            "schema":"betterinstincts.behavior-review-receipt/v1",
            "session_id":session_id,"state":"REVIEWED_MODEL_UPDATED",
            "model_cells":len(model["counts"]),
            "reviewed_examples_total":len(model["seen_review_refs"]),
            "state_path":str(state_path.relative_to(ROOT)),
            "execute_clicks":False,"control_permit":None,
        }
    finally:
        lock_path.unlink(missing_ok=True)


def _session_behavior_model(path: Path) -> dict | None:
    state_path = path / "behavior-valence.json"
    if state_path.is_symlink():
        raise HostListenerError("BEHAVIOR_MODEL_SYMLINK_FORBIDDEN")
    if not state_path.exists():
        return None
    if not state_path.is_file() or state_path.stat().st_size > MAX_MODEL_BYTES:
        raise HostListenerError("BEHAVIOR_MODEL_FILE_UNSAFE")
    try:
        return validate_model(json.loads(state_path.read_text(encoding="utf-8")))
    except (BehaviorValenceError, ValueError, UnicodeError, TypeError, KeyError) as exc:
        raise HostListenerError("BEHAVIOR_MODEL_INVALID:" + str(exc)) from exc


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
    multitasking = raw.get("multitasking")
    if multitasking is not None and type(multitasking) is not bool:
        raise HostListenerError("OBSERVATION_MULTITASKING_INVALID")
    sim_seated = raw.get("sim_seated")
    if sim_seated is not None and type(sim_seated) is not bool:
        raise HostListenerError("OBSERVATION_SIM_SEATED_INVALID")
    for key in ("sim_room_id", "sim_seat_id"):
        value = raw.get(key)
        if value is not None and (
            not isinstance(value, str) or not value or len(value) > 100
        ):
            raise HostListenerError("OBSERVATION_STUDY_TARGET_INVALID")
    lot_traits = raw.get("lot_traits", [])
    if not isinstance(lot_traits, (list, tuple)) or len(lot_traits) > 16 or any(
        not isinstance(x, str) or not x or len(x) > 80 for x in lot_traits
    ):
        raise HostListenerError("OBSERVATION_LOT_TRAITS_INVALID")
    sim_at_school = raw.get("sim_at_school")
    if sim_at_school is not None and not isinstance(sim_at_school, bool):
        raise HostListenerError("OBSERVATION_SIM_AT_SCHOOL_INVALID")
    sim_library = raw.get("sim_library") or ()
    if not isinstance(sim_library, (list, tuple)):
        raise HostListenerError("OBSERVATION_SIM_LIBRARY_INVALID")
    school_window = raw.get("school_homework_window")
    if school_window is not None and not isinstance(school_window, Mapping):
        raise HostListenerError("OBSERVATION_HOMEWORK_WINDOW_INVALID")
    social_queue = raw.get("queued_social_targets") or ()
    if (not isinstance(social_queue, (list, tuple)) or len(social_queue) > 16
            or any(not isinstance(item, Mapping) for item in social_queue)):
        raise HostListenerError("OBSERVATION_SOCIAL_QUEUE_INVALID")
    life_stage = raw.get("life_stage")
    if life_stage is not None and not isinstance(life_stage, str):
        raise HostListenerError("OBSERVATION_LIFE_STAGE_INVALID")
    gardening = raw.get("gardening")
    if gardening is not None and not isinstance(gardening, Mapping):
        raise HostListenerError("OBSERVATION_GARDENING_INVALID")
    household_upkeep = raw.get("household_upkeep")
    if household_upkeep is not None and (
        not isinstance(household_upkeep, Mapping)
        or len(json.dumps(dict(household_upkeep)).encode("utf-8")) > 8192
    ):
        raise HostListenerError("OBSERVATION_HOUSEHOLD_UPKEEP_INVALID")
    discovery_hud = raw.get("discovery_hud")
    if discovery_hud is not None and (
        not isinstance(discovery_hud, Mapping)
        or len(json.dumps(dict(discovery_hud)).encode("utf-8")) > 8192
    ):
        raise HostListenerError("OBSERVATION_DISCOVERY_HUD_INVALID")
    autonomy_observation = raw.get("autonomy_observation")
    if autonomy_observation is not None and (
        not isinstance(autonomy_observation, Mapping)
        or len(json.dumps(dict(autonomy_observation)).encode("utf-8")) > 8192
    ):
        raise HostListenerError("OBSERVATION_AUTONOMY_POLICY_INVALID")
    camera_pointer_context = raw.get("camera_pointer_context")
    if camera_pointer_context is not None and (
        not isinstance(camera_pointer_context, Mapping)
        or len(json.dumps(dict(camera_pointer_context)).encode("utf-8")) > 2048
    ):
        raise HostListenerError("OBSERVATION_CAMERA_POINTER_CONTEXT_INVALID")
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
    sim_camera_command = raw.get("sim_camera_command")
    if sim_camera_command is not None and not isinstance(sim_camera_command, str):
        raise HostListenerError("SIM_CAMERA_COMMAND_INVALID")
    hotkey_event = raw.get("sim_camera_hotkey_event")
    if hotkey_event is not None:
        if sim_camera_command is not None:
            raise HostListenerError("SIM_CAMERA_DOUBLE_INTENT")
        try:
            sim_camera_command = command_from_app_hotkey(hotkey_event)
        except ValueError as exc:
            raise HostListenerError("SIM_CAMERA_HOTKEY_INVALID") from exc
    sim_camera_observation = raw.get("sim_camera_observation")
    if sim_camera_observation is not None:
        if not isinstance(sim_camera_observation, Mapping) or len(json.dumps(dict(sim_camera_observation))) > 8192:
            raise HostListenerError("SIM_CAMERA_OBSERVATION_INVALID")
        sim_camera_observation = stamp_host_capture_branch(sim_camera_observation)
    camera_recovery = raw.get("camera_recovery")
    if camera_recovery is not None:
        if not isinstance(camera_recovery, Mapping) or len(json.dumps(dict(camera_recovery))) > 8192:
            raise HostListenerError("OBSERVATION_CAMERA_RECOVERY_INVALID")
        camera_recovery = stamp_host_capture_branch(camera_recovery)
    world_target = raw.get("world_target")
    if world_target is not None:
        if not isinstance(world_target, Mapping) or len(json.dumps(dict(world_target))) > 8192:
            raise HostListenerError("OBSERVATION_WORLD_TARGET_INVALID")
        world_target = stamp_host_capture_branch(world_target)
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
    survey_goals = raw.get("survey_goals", [])
    if not isinstance(survey_goals, (list, tuple)) or len(survey_goals) > 16:
        raise HostListenerError("OBSERVATION_SURVEY_GOALS_INVALID")
    actor_ref = raw.get("actor_ref")
    if actor_ref is not None and (
        not isinstance(actor_ref, str) or not actor_ref or len(actor_ref) > 120
    ):
        raise HostListenerError("OBSERVATION_SURVEY_ACTOR_INVALID")
    active_lot_id = raw.get("active_lot_id")
    if active_lot_id is not None and (
        not isinstance(active_lot_id, str) or not active_lot_id or len(active_lot_id) > 80
    ):
        raise HostListenerError("OBSERVATION_ACTIVE_LOT_INVALID")
    camera_follow = raw.get("camera_follow_attested", False)
    if type(camera_follow) is not bool:
        raise HostListenerError("OBSERVATION_CAMERA_FOLLOW_INVALID")
    game_version = raw.get("game_version")
    if game_version is not None and (not isinstance(game_version, str) or len(game_version) > 40):
        raise HostListenerError("OBSERVATION_GAME_VERSION_INVALID")
    if game_version is None and raw.get("capture_ref"):
        game_version = load_catalog()["game_version"]
    survey_occupied = raw.get("occupied_objects", [])
    if not isinstance(survey_occupied, (list, tuple)) or len(survey_occupied) > 128:
        raise HostListenerError("OBSERVATION_OCCUPIED_OBJECTS_INVALID")
    preference_offer = raw.get("preference_offer")
    if preference_offer is not None and (
        not isinstance(preference_offer, Mapping)
        or len(json.dumps(dict(preference_offer)).encode("utf-8")) > 4096
    ):
        raise HostListenerError("OBSERVATION_PREFERENCE_OFFER_INVALID")
    return {
        "preference_offer": dict(preference_offer) if preference_offer is not None else None,
        "preference_automation_opt_in": raw.get("preference_automation_opt_in") is True,
        "preference_game_build_confirmed": raw.get("preference_game_build_confirmed") is True,
        "needs": {k: float(needs[k]) for k in SIX},
        "gardening": dict(gardening) if gardening is not None else None,
        "household_upkeep": (
            dict(household_upkeep) if household_upkeep is not None else None
        ),
        "discovery_hud": dict(discovery_hud) if discovery_hud is not None else None,
        "autonomy_observation": (
            dict(autonomy_observation) if autonomy_observation is not None else None
        ),
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
        "actor_ref": actor_ref,
        "active_lot_id": active_lot_id,
        "camera_follow_attested": camera_follow,
        "game_version": game_version,
        "survey_goals": list(survey_goals),
        "occupied_objects": list(survey_occupied),
        "school_phase": (str(raw["school_phase"]) if raw.get("school_phase") else None),
        "pinned_whims": [str(x) for x in pinned],
        "homework_pending": bool(raw.get("homework_pending", False)),
        "inventory_has_homework": inv if isinstance(inv, bool) else None,
        "homework_on_lot": on_lot_hw if isinstance(on_lot_hw, bool) else None,
        "school_homework_window": dict(school_window) if school_window is not None else None,
        "multitasking": multitasking,
        "sim_room_id": raw.get("sim_room_id"),
        "sim_seated": sim_seated,
        "sim_seat_id": raw.get("sim_seat_id"),
        "lot_traits": list(lot_traits),
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
        "queued_social_targets": tuple(dict(item) for item in social_queue),
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
        "camera_pointer_context": (
            dict(camera_pointer_context) if camera_pointer_context is not None else None
        ),
        "world_target": dict(world_target) if world_target is not None else None,
        "camera_recovery": dict(camera_recovery) if camera_recovery is not None else None,
        "sim_camera_command": sim_camera_command,
        "sim_camera_observation": dict(sim_camera_observation) if sim_camera_observation is not None else None,
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
    # Optional supplied chance card. This is a READ-ONLY sidecar: even when the
    # listener yields to the player the UI may explain an observed popup.
    # No network request, worker launch, button press or session auto-start.
    chance_event_advisory = None
    if "chance_event" in observation:
        event = observation["chance_event"]
        if not isinstance(event, Mapping) or event.get("capture_ref") != obs["capture_ref"]:
            raise HostListenerError("CHANCE_EVENT_CAPTURE_MISMATCH")
        if observation.get("chance_event_external_research_opt_in") not in (None, False, True):
            raise HostListenerError("CHANCE_EVENT_EXTERNAL_OPT_IN_INVALID")
        try:
            memo = load_chance_memo(ROOT / "dist" / "chance-event-research" / "memo.json")
            chance_event_advisory = assess_chance_event(
                event, memo,
                external_research_opt_in=observation.get(
                    "chance_event_external_research_opt_in") is True,
            )
        except ChanceEventError as exc:
            raise HostListenerError("CHANCE_EVENT_INVALID:" + str(exc)) from exc
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
    # Read-only lot assessment continues even while the human owns the mouse.
    # It reads supplied model/queue facts and the persistent token index only;
    # no screen navigation or Sim queue mutation occurs in this path.
    try:
        knowledge = load_index(OUTPUT / "affordance-memory.v1.json")
        memory_state = "INDEX_AVAILABLE"
    except AffordanceMemoryError:
        knowledge = empty_index()
        memory_state = "INDEX_UNAVAILABLE_NEEDS_REPAIR"
    try:
        survey = evaluate_opportunity_survey(
            obs["needs"], queue=obs["queue"], multitasking=obs["multitasking"],
            lot_model=obs.get("lot_model"), active_lot_id=obs["active_lot_id"],
            game_version=obs["game_version"], capture_ref=obs["capture_ref"],
            homework_pending=obs["homework_pending"],
            inventory_has_homework=obs["inventory_has_homework"],
            observed_goals=obs["survey_goals"], aff_index=knowledge,
            player_active=presence["host"] == "YIELD_TO_PLAYER",
            host_may_control=bool(handoff["screen_control_allowed"]),
            verified_live_mode=bool(
                mode_context is not None and mode_context["mode"] == "LIVE"
                and mode_context["mode_autonomy_allowed"]
            ),
            camera_follow_attested=obs["camera_follow_attested"],
            actor_ref=obs["actor_ref"], occupied_objects=obs["occupied_objects"],
        )
    except OpportunitySurveyError as exc:
        raise HostListenerError("SURVEY_OBSERVATION_INVALID:" + str(exc)) from exc
    survey["affordance_index_state"] = memory_state
    # The sensor must supply a fresh menu query in this same tick. This
    # attaches a queue *proposal* to the existing survey, not to game input.
    if "object_catalog_query" in observation:
        candidate = observation["object_catalog_query"]
        if (not isinstance(candidate, Mapping)
                or len(json.dumps(dict(candidate)).encode("utf-8")) > 8192):
            raise HostListenerError("OBJECT_CATALOG_QUERY_INVALID")
        if (candidate.get("capture_ref") != obs["capture_ref"]
                or candidate.get("game_version") != obs["game_version"]):
            raise HostListenerError("OBJECT_CATALOG_QUERY_CAPTURE_MISMATCH")
        if (mode_context is None or mode_context["mode"] != "LIVE"
                or not mode_context["mode_autonomy_allowed"]):
            survey["object_action_hint"] = {
                "state": "SCENE_UNVERIFIED", "candidate": None,
                "execute_allowed": False, "cancel_allowed": False,
            }
        else:
            current = {
                **candidate,
                "player_active": presence["host"] == "YIELD_TO_PLAYER",
                "player_queue_present": bool(obs["player_directed"]),
            }
            survey["object_action_hint"] = suggest_object_action(session_id, current)
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
            "opportunity_survey": survey,
            "ui_mode": mode_context,
            "execute_clicks": False,
            "proof_ceiling": cfg.get("proof_ceiling"),
            "next": "Player playing or unknown presence — host stands down this tick.",
        }
        _write_json(meta_path, meta)
        tick_path = path / f"tick-{ticks:04d}.json"
        if chance_event_advisory is not None:
            receipt["chance_event"] = chance_event_advisory
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
        placement_receipts: list[dict] = []
        if mode_context["mode"] in {"BUY", "BUILD"}:
            from betterinstincts.lot_floor_map import (
                LotFloorMapError,
                record_builder_placement,
            )

            profile_id = obs.get("lot_floor_profile_id") or obs.get("profile_id")
            lot_key = obs.get("lot_floor_key") or obs.get("lot_key")
            placements = obs.get("build_placements") or ()
            if (
                isinstance(profile_id, str)
                and isinstance(lot_key, str)
                and isinstance(placements, (list, tuple))
            ):
                for event in placements:
                    if not isinstance(event, Mapping):
                        continue
                    try:
                        placement_receipts.append(
                            record_builder_placement(
                                profile_id=profile_id,
                                lot_key=lot_key,
                                catalog_name=str(event.get("catalog_name") or ""),
                                bbox_client=event.get("bbox_client") or (),
                                capture_ref=str(
                                    event.get("capture_ref") or obs.get("capture_ref") or ""
                                ),
                                camera_revision=str(
                                    event.get("camera_revision")
                                    or obs.get("camera_revision")
                                    or ""
                                ),
                                object_id=(
                                    str(event["object_id"])
                                    if event.get("object_id") is not None
                                    else None
                                ),
                                kind=str(event.get("kind") or "BUILD_CENSUS_ITEM"),
                                parent_object_id=(
                                    str(event["parent_object_id"])
                                    if event.get("parent_object_id") is not None
                                    else None
                                ),
                                link_relation=str(event.get("link_relation") or "ON_TOP_OF"),
                                linked_object_ids=event.get("linked_object_ids") or (),
                                price=(
                                    str(event["price"])
                                    if event.get("price") is not None
                                    else None
                                ),
                                category=(
                                    str(event["category"])
                                    if event.get("category") is not None
                                    else None
                                ),
                                note=str(event.get("note") or "host_listener_build_placement"),
                            )
                        )
                    except (LotFloorMapError, TypeError, ValueError) as exc:
                        placement_receipts.append(
                            {
                                "state": "BUILD_PLACEMENT_TICK_FAILED",
                                "error": str(exc),
                                "execute_allowed": False,
                            }
                        )
        ticks += 1
        listener_action = (
            "MODE_CONTEXT_ONLY" if mode_context["mode"] in {"BUY", "BUILD"}
            else "MODE_UNVERIFIED"
        )
        if placement_receipts:
            listener_action = "BUILD_PLACEMENT_AUTO_MAP"
        receipt = {
            "schema": "betterinstincts.host-listener.tick/v1",
            "session_id": session_id, "tick": ticks,
            "presence": presence, "handoff": handoff,
            "ui_mode": mode_context,
            "build_floor_activity": floor_activity,
            "build_placements": placement_receipts,
            "opportunity_survey": survey,
            "listener_action": listener_action,
            "execute_clicks": False,
            "proof_ceiling": cfg.get("proof_ceiling"),
            "next": (
                "Builder placements recorded into profile floor graph; no Live dispatch."
                if placement_receipts
                else "Observe the game mode again; do not dispatch Live actions."
            ),
        }
        meta["ticks"] = ticks
        meta["last_tick_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        meta["last_disposition"] = listener_action
        _write_json(meta_path, meta)
        tick_path = path / f"tick-{ticks:04d}.json"
        if chance_event_advisory is not None:
            receipt["chance_event"] = chance_event_advisory
        _write_json(tick_path, receipt)
        receipt["receipt"] = str(tick_path.relative_to(ROOT))
        return receipt

    session_behavior_model = _session_behavior_model(path) if obs.get("autonomy_observation") is not None else None
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
            multitasking=obs["multitasking"],
            sim_room_id=obs["sim_room_id"],
            sim_seated=obs["sim_seated"],
            sim_seat_id=obs["sim_seat_id"],
            lot_traits=obs["lot_traits"],
            lot_model=obs.get("lot_model"),
            school_day_active=obs["school_day_active"],
            school_goals_incomplete=obs["school_goals_incomplete"],
            school_phase=obs["school_phase"],
            pinned_whims=obs["pinned_whims"],
            homework_pending=obs["homework_pending"],
            inventory_has_homework=obs["inventory_has_homework"],
            homework_on_lot=obs["homework_on_lot"],
            school_homework_window=obs["school_homework_window"],
            sim_at_school=obs["sim_at_school"],
            camera_lot_kind=obs["camera_lot_kind"],
            social_prompt_active=obs["social_prompt_active"],
            social_prompt_kind=obs["social_prompt_kind"],
            social_prompt_text=obs["social_prompt_text"],
            social_invitee_name=obs["social_invitee_name"],
            sim_library=obs["sim_library"],
            queued_social_targets=obs["queued_social_targets"],
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
            camera_pointer_context=obs["camera_pointer_context"],
            camera_scan_needed=obs["camera_scan_needed"],
            camera_pan_directions=obs["camera_pan_directions"],
            world_target=obs["world_target"],
            camera_recovery=obs["camera_recovery"],
            sim_camera_command=obs["sim_camera_command"],
            sim_camera_observation=obs["sim_camera_observation"],
            emotion=obs["emotion"],
            moodlets=obs["moodlets"],
            traits=obs["traits"],
            whims=obs["whims"] or obs["pinned_whims"],
            gardening=obs["gardening"],
            household_upkeep=obs["household_upkeep"],
            discovery_hud=obs["discovery_hud"],
            autonomy_observation=obs["autonomy_observation"],
            behavior_model=session_behavior_model,
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
            preference_offer=obs.get("preference_offer"),
            preference_automation_opt_in=obs.get("preference_automation_opt_in", False),
            preference_game_build_confirmed=obs.get("preference_game_build_confirmed", False),
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
        "opportunity_survey": survey,
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
    if chance_event_advisory is not None:
        receipt["chance_event"] = chance_event_advisory
    _write_json(tick_path, receipt)
    receipt["receipt"] = str(tick_path.relative_to(ROOT))
    return receipt


def _require_active_traversal_session(session_id: str, *, explicit_opt_in: bool) -> None:
    """Observe only inside the existing explicitly activated listener lifecycle."""
    if explicit_opt_in is not True:
        raise HostListenerError("EXPLICIT_TRAVERSAL_LEARNING_OPT_IN_REQUIRED")
    path = _session_dir(session_id) / "session.json"
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 64_000:
        raise HostListenerError("TRAVERSAL_LISTENER_NOT_ACTIVE")
    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise HostListenerError("TRAVERSAL_LISTENER_METADATA_INVALID") from exc
    if meta.get("state") != "ACTIVE" or meta.get("session_id") != session_id:
        raise HostListenerError("TRAVERSAL_LISTENER_NOT_ACTIVE")


def observe_traversal_transition(
    session_id: str, snapshot: Mapping, event: Mapping, *,
    explicit_opt_in: bool = False,
) -> dict:
    """Persist one independently observed route outcome, not a mouse event.

    The selected sensor/caller must actually supply a genuine game route probe
    or reviewed observation. This port never creates its own sensor or queue.
    """
    _require_active_traversal_session(session_id, explicit_opt_in=explicit_opt_in)
    from betterinstincts.traversal_cost_learning import (
        TraversalLearningError, record_local_transition,
    )
    try:
        return record_local_transition(snapshot, event, explicit_opt_in=True)
    except TraversalLearningError as exc:
        raise HostListenerError("TRAVERSAL_EVIDENCE_REJECTED:" + str(exc)) from exc


def plan_learned_traversal(
    session_id: str, snapshot: Mapping, *, explicit_opt_in: bool = False,
) -> dict:
    """Apply the private per-profile model to the already-verified pure graph."""
    _require_active_traversal_session(session_id, explicit_opt_in=explicit_opt_in)
    from betterinstincts.household_navigation import plan_household_navigation
    from betterinstincts.traversal_cost_learning import (
        TraversalLearningError, load_local_model,
    )
    if not isinstance(snapshot, Mapping):
        raise HostListenerError("TRAVERSAL_SNAPSHOT_INVALID")
    supplied = dict(snapshot)
    try:
        supplied["traversal_cost_model"] = load_local_model(snapshot)
    except TraversalLearningError:
        # Corruption never promotes a prediction; retain base verified edges.
        supplied["traversal_cost_model"] = None
    return plan_household_navigation(supplied)
