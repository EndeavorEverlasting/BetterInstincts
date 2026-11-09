"""Presence-gated host automation orchestrator (evaluate-first).

Call stack (P95):
  presence.classify -> YIELD or behavior_eval -> host_stack -> needs_force plan
Live SendInput stays in scripts/ and only when HOST_MAY_AUTOMATE + --execute.
"""
from __future__ import annotations

from typing import Mapping, Optional, Sequence
from dataclasses import replace

from betterinstincts.behavior_eval import BehaviorEvalError, evaluate_queue
from betterinstincts.host_listener import HostListenerError, status as listener_status
from betterinstincts.host_stack import HostStackError, evaluate_turn
from betterinstincts.needs_force import NeedsForceError, plan_force
from betterinstincts.player_presence import PresenceProbe
from betterinstincts.control_handoff import DEFAULT_IDLE_MS, HandoffError, as_presence, decide


class HostAutomateError(ValueError):
    pass


def plan_automation(
    observation: Mapping,
    probe: PresenceProbe,
    *,
    session_id: Optional[str] = None,
    session_active: Optional[bool] = None,
    idle_ms: int = DEFAULT_IDLE_MS,
) -> dict:
    """One evaluate-only automation plan gated by player presence."""
    active = session_active
    if active is None and session_id:
        try:
            active = listener_status(session_id).get("state") == "ACTIVE"
        except HostListenerError as exc:
            raise HostAutomateError(str(exc)) from exc
    active = bool(active)

    if observation.get("player_directed") and not probe.player_directed_queue:
        probe = replace(probe, player_directed_queue=True)
    try:
        handoff = decide(probe, session_active=active, idle_ms=idle_ms)
    except HandoffError as exc:
        raise HostAutomateError(str(exc)) from exc
    presence = as_presence(handoff)

    if not handoff["screen_control_allowed"]:
        return {
            "state": "YIELD_TO_PLAYER",
            "presence": presence,
            "handoff": handoff,
            "execute_clicks": False,
            "behavior": None,
            "host_stack": None,
            "needs_force_plan": None,
            "proof_ceiling": presence.get("proof_ceiling"),
            "next": "Host control paused. Resume planning after verified desktop inactivity or explicit operator release.",
        }

    needs = observation.get("needs")
    queue = observation.get("queue") or []
    location = observation.get("location_kind", "unknown")
    if not isinstance(needs, dict) or not isinstance(queue, list):
        raise HostAutomateError("INVALID_OBSERVATION")

    on_lot = bool(observation.get("objects_on_current_lot", location == "home"))
    try:
        behavior = evaluate_queue(
            needs,
            queue,
            player_directed=bool(observation.get("player_directed", False)),
            objects_on_current_lot=on_lot,
            location_kind=str(location),
            capture_ref=str(observation.get("capture_ref") or "capture:automate"),
        )
        stack = evaluate_turn(
            needs,
            available_objects=tuple(observation.get("available_objects") or ()),
            player_directed=bool(observation.get("player_directed", False)),
            already_busy=bool(observation.get("already_busy", False)),
            capture_ref=str(observation.get("capture_ref") or "capture:automate"),
            viewport=observation.get("viewport"),
            location_kind=str(location),
            objects_on_current_lot=on_lot,
            queue=queue,
            # Forward optional independently observed scene/portrait/HUD
            # evidence to the same host-stack gate. Never infer it from
            # high-level intent or mark a click executable here.
            sim_camera_observation=observation.get("sim_camera_observation"),
            live_hud_observation=observation.get("live_hud_observation"),
            requested_hud_panel=observation.get("requested_hud_panel"),
            requested_hud_target=observation.get("requested_hud_target"),
            scenery_observation=observation.get("scenery_observation"),
            scenery_registry=observation.get("scenery_registry"),
            camera_map_goal=observation.get("camera_map_goal"),
            camera_clock_ms=observation.get("camera_clock_ms"),
            camera_scan_needed=bool(observation.get("camera_scan_needed", False)),
            camera_pan_directions=observation.get("camera_pan_directions") or (),
        )
        force = plan_force(
            location_kind=str(location),
            objects_on_current_lot=on_lot,
            disposition=behavior["clarity"]["disposition"],
        )
    except (BehaviorEvalError, HostStackError, NeedsForceError) as exc:
        raise HostAutomateError(str(exc)) from exc

    return {
        "state": "HOST_AUTOMATION_PLANNED",
        "presence": presence,
        "handoff": handoff,
        "behavior": behavior,
        "host_stack": stack,
        "needs_force_plan": force,
        "execute_clicks": False,
        "proof_ceiling": "HOST_AUTOMATE_PLAN_NOT_LIVE_CERT",
        "next": (
            "Separate --execute on scripts.needs_force only while HOST_MAY_AUTOMATE "
            "remains true; one screen step per fresh two-probe handoff gate."
        ),
    }
