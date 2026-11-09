"""Cooperative, keyboard-first Sims camera intentions (P95/P124).

Policy and injected ports only. This module never sends a key, moves a cursor,
installs a keyhook, loads a game mod, selects a Sim, or touches saves. Native
Enter centers; an opt-in in-game camera API is necessary for *following*.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from betterinstincts.scenes import load_catalog
from betterinstincts.ui_chrome import hotkeys_for_mode, resolve_app_hotkey
from betterinstincts.workflow_interop import CooperativeScreenQueue, QueuedStep

CENTER_SIM = "CENTER_ACTIVE_SIM"
CENTER_LOT = "CENTER_CURRENT_LOT"
FOLLOW_SIM = "FOLLOW_ACTIVE_SIM"
COMMANDS = frozenset((CENTER_SIM, CENTER_LOT, FOLLOW_SIM))
PROOF = "OFFLINE_CAMERA_INTENT_AND_INJECTED_PORT_NOT_LIVE_GAME_CERTIFIED"


class SimCameraError(ValueError):
    """Input was not a safe, registered camera intent."""


def _chord(hotkey_id: str) -> list[str]:
    for row in hotkeys_for_mode("LIVE"):
        if row.get("id") == hotkey_id:
            return list(row["chord"])
    raise SimCameraError("NATIVE_CAMERA_KEY_NOT_REGISTERED")


def command_from_app_hotkey(event: Mapping[str, Any]) -> str:
    """Resolve the opt-in app shortcut through the existing UI-chrome owner."""
    return resolve_app_hotkey(event)


def plan_sim_camera(
    command: str,
    *,
    capture_ref: str,
    observation: Mapping[str, Any] | None,
) -> dict:
    """Decide one camera action from a current trusted host observation.

    A READY plan is never an input permit: the cooperative queue plus the
    independent game-host screen/session/save gate remain mandatory.
    """
    if command not in COMMANDS:
        raise SimCameraError("UNKNOWN_SIM_CAMERA_COMMAND")
    if not isinstance(capture_ref, str) or not 1 <= len(capture_ref) <= 128:
        raise SimCameraError("SIM_CAMERA_CAPTURE_REF_REQUIRED")
    base = {
        "command": command, "capture_ref": capture_ref,
        "execute_allowed": False, "proof_ceiling": PROOF,
    }

    def hold(reason: str) -> dict:
        return {**base, "state": "SIM_CAMERA_NOT_READY",
                "gate": "REOBSERVE_OR_YIELD", "reason": reason, "effect": None}

    if not isinstance(observation, Mapping):
        return hold("HOST_CAMERA_OBSERVATION_MISSING")
    if len(str(dict(observation))) > 8192:
        raise SimCameraError("SIM_CAMERA_OBSERVATION_TOO_LARGE")
    version = load_catalog()["game_version"]
    expected = {
        "source": "HOST_CAPTURE",
        "capture_ref": capture_ref,
        "scene_id": "live_mode",
        "mode": "LIVE",
        "game_version": version,
        "capture_quality": "CONTENT_PRESENT",
        "viewport_state": "NORMAL",
        "save_authorized": True,
        "player_queue_owned": False,
        "text_entry_active": False,
        "modal_open": False,
        "player_camera_owned": False,
    }
    for key, value in expected.items():
        if type(observation.get(key)) is not type(value) or observation.get(key) != value:
            return hold("LIVE_SCENE_FOCUS_OR_PLAYER_GATE_INVALID:" + key)
    cues = observation.get("independent_cues")
    if (
        not isinstance(cues, list) or len(cues) != 2
        or not all(isinstance(c, Mapping) and isinstance(c.get("token"), str)
                   and 1 <= len(c["token"]) <= 80 for c in cues)
        or {c.get("source") for c in cues} != {"visual", "operator"}
    ):
        return hold("INDEPENDENT_SCENE_CUES_REQUIRED")
    revision = observation.get("camera_revision")
    if not isinstance(revision, str) or not 1 <= len(revision) <= 80:
        return hold("CAMERA_REVISION_MISSING")
    sim_id = observation.get("active_sim_id")
    if command != CENTER_LOT and (type(sim_id) is not int or not 0 < sim_id <= 2**63 - 1):
        return hold("ACTIVE_SIM_ID_UNVERIFIED")
    if command == FOLLOW_SIM and observation.get("active_sim_instanced") is not True:
        return hold("ACTIVE_SIM_NOT_INSTANCED")
    if command in (FOLLOW_SIM, CENTER_SIM) and observation.get("camera_follow_sim_id") == sim_id:
        # Preserve an existing follow lock instead of issuing a redundant
        # center or refocus that could alter the player's chosen view.
        return {**base, "state": "ALREADY_FOLLOWING_SIM", "gate": "NO_EFFECT",
                "sim_id": sim_id, "camera_revision": revision, "effect": None}
    if command == FOLLOW_SIM:
        effect = {"kind": "GAME_CAMERA_API", "api": "focus_on_sim", "follow": True,
                  "sim_id": sim_id, "cursor_movement": False}
    else:
        effect = {"kind": "SEND_KEY_CHORD", "chord": _chord(command),
                  "cursor_movement": False}
    return {**base, "state": "SIM_CAMERA_READY_FOR_ADMISSION",
            "gate": "COOPERATIVE_SCREEN_QUEUE_AND_LIVE_HOST",
            "sim_id": sim_id if command != CENTER_LOT else None,
            "camera_revision": revision, "effect": effect}


def enqueue_sim_camera(
    queue: CooperativeScreenQueue, *, work_id: str, command: str,
    capture_ref: str,
    observe: Callable[[], Awaitable[Mapping[str, Any]]],
    send_chord: Callable[[list[str]], Awaitable[bool]] | None = None,
    focus_follow: Callable[[int], Awaitable[bool]] | None = None,
) -> dict:
    """One deferred key or in-game API effect; never Mouse/SendInput directly."""
    if not isinstance(queue, CooperativeScreenQueue) or not callable(observe):
        raise SimCameraError("COOPERATIVE_QUEUE_AND_SENSOR_REQUIRED")
    if command not in COMMANDS:
        raise SimCameraError("UNKNOWN_SIM_CAMERA_COMMAND")
    if (command == FOLLOW_SIM and not callable(focus_follow)) or (
        command != FOLLOW_SIM and not callable(send_chord)
    ):
        raise SimCameraError("CAMERA_EFFECT_PORT_UNAVAILABLE")
    receipt = {"state": "NOT_DISPATCHED", "command": command, "proof_ceiling": PROOF}
    anchor: dict = {}

    async def validate() -> bool:
        latest = plan_sim_camera(command, capture_ref=capture_ref, observation=await observe())
        if latest["state"] != "SIM_CAMERA_READY_FOR_ADMISSION":
            return False
        if anchor:
            # Even if a Sim/scene still looks valid, never reuse pre-change
            # camera coordinates or selection after an intervening camera move.
            return (
                latest["camera_revision"] == anchor["camera_revision"]
                and latest["sim_id"] == anchor["sim_id"]
                and latest["effect"] == anchor["effect"]
            )
        anchor.update(latest)
        return True

    async def action(checkpoint) -> None:
        await checkpoint()
        if not await validate():
            raise SimCameraError("SIM_CAMERA_TARGET_STALE_AT_EFFECT")
        effect = anchor["effect"]
        if effect["kind"] == "SEND_KEY_CHORD":
            dispatched = await send_chord(list(effect["chord"]))
        else:
            dispatched = await focus_follow(int(effect["sim_id"]))
        if dispatched is not True:
            raise SimCameraError("SIM_CAMERA_EFFECT_NOT_ACKNOWLEDGED")
        # A port ACK is NOT a camera screenshot or a verified follow lock.
        receipt["state"] = "EFFECT_DISPATCHED_UNVERIFIED"
        receipt["effect_kind"] = effect["kind"]
        receipt["target_sim_id"] = anchor["sim_id"]

    queue.enqueue(QueuedStep(work_id=work_id, validate=validate, action=action))
    return {"state": "QUEUED_CAMERA_INTENT", "work_id": work_id,
            "command": command, "execute_allowed": False,
            "receipt": receipt, "proof_ceiling": PROOF}
