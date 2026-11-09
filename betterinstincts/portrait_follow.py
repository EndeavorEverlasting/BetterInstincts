"""Verified active-Sim portrait follow, independent of one-shot Enter centering.

Right-click the currently selected portrait ONLY after exact screenshot/geometry
attestation, player-idle admission and a fresh before-effect recheck.
"""
from __future__ import annotations

import re
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from betterinstincts.sim_camera import FOLLOW_SIM, plan_sim_camera
from betterinstincts.workflow_interop import CooperativeScreenQueue, QueuedStep
from betterinstincts.screen_atlas import _native_owner
from betterinstincts.camera_traverse import safe_rest_point

TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")
PROOF = "OFFLINE_PORTRAIT_FOLLOW_NOT_LIVE_GAME_OBSERVED"
PORTRAIT_CUES = {
    "visual": "active_sim_portrait_selection",
    "operator": "active_sim_identity_confirmed",
}


class PortraitFollowError(ValueError):
    pass


def plan_portrait_follow(*, capture_ref: str, observation: Mapping[str, Any] | None) -> dict:
    """Read-only policy: a right-click is preferred, never a guessed point."""
    base = {"execute_allowed": False, "proof_ceiling": PROOF, "control": "RIGHT_CLICK_ACTIVE_SIM_PORTRAIT"}
    def hold(reason: str) -> dict:
        return {**base, "state": "PORTRAIT_FOLLOW_NOT_READY", "gate": "PORTRAIT_REOBSERVE_REQUIRED",
                "reason": reason, "effect": None}
    try:
        camera = plan_sim_camera(FOLLOW_SIM, capture_ref=capture_ref, observation=observation)
    except (ValueError, TypeError):
        return hold("CAMERA_SCENE_UNVERIFIED")
    if camera["state"] == "SIM_CAMERA_NOT_READY":
        return hold(camera["reason"])
    sim_id = camera["sim_id"]
    if camera["state"] == "ALREADY_FOLLOWING_SIM":
        return {**base, "state": "PORTRAIT_FOLLOW_ALREADY_OBSERVED",
                "gate": "CAMERA_ACTIVE_SIM_LOCKED", "sim_id": sim_id, "effect": None}
    if not isinstance(observation, Mapping):
        return hold("PORTRAIT_OBSERVATION_MISSING")
    portrait = observation.get("active_sim_portrait")
    if not isinstance(portrait, Mapping):
        return hold("ACTIVE_SIM_PORTRAIT_NOT_ATTESTED")
    if (portrait.get("source") != "HOST_CAPTURE"
            or portrait.get("capture_ref") != capture_ref
            or type(portrait.get("sim_id")) is not int or portrait["sim_id"] != sim_id
            or type(portrait.get("selected_sim_id")) is not int
            or portrait["selected_sim_id"] != sim_id
            or portrait.get("lane") != "BOTTOM_LEFT_HOUSEHOLD_PORTRAITS"
            or portrait.get("visible") is not True
            or portrait.get("occluded") is not False
            or portrait.get("enabled") is not True):
        return hold("ACTIVE_SIM_PORTRAIT_UNVERIFIED_OR_OBSCURED")
    for key in ("portrait_revision", "ui_layout_revision", "selected_sim_revision"):
        value = portrait.get(key)
        if not isinstance(value, str) or not TOKEN.fullmatch(value):
            return hold("PORTRAIT_REVISION_UNVERIFIED:" + key)
    cues = portrait.get("cues")
    if (not isinstance(cues, list) or len(cues) != 2
            or any(not isinstance(c, Mapping) or set(c) != {"source", "token"} for c in cues)
            or {c.get("source"): c.get("token") for c in cues} != PORTRAIT_CUES):
        return hold("PORTRAIT_INDEPENDENT_CUES_REQUIRED")
    w, h, rect = portrait.get("client_width"), portrait.get("client_height"), portrait.get("hitbox")
    if (type(w) is not int or type(h) is not int or w < 640 or h < 480
            or not isinstance(rect, list) or len(rect) != 4
            or any(type(v) is not int for v in rect)):
        return hold("EXACT_PORTRAIT_GEOMETRY_REQUIRED")
    left, top, right, bottom = rect
    if (not 0 <= left < right < w//2 or not h//2 <= top < bottom < h
            or min(right-left, bottom-top) < 8):
        return hold("PORTRAIT_OUTSIDE_BOTTOM_LEFT_OR_TOO_SMALL")
    point = [(left + right)//2, (top+bottom)//2]
    return {
        **base, "state": "PORTRAIT_FOLLOW_READY_FOR_ADMISSION",
        "gate": "COOPERATIVE_SCREEN_QUEUE_AND_NATIVE_HOST",
        "sim_id": sim_id, "capture_ref": capture_ref,
        "camera_revision": camera["camera_revision"],
        "portrait_revision": portrait["portrait_revision"],
        "ui_layout_revision": portrait["ui_layout_revision"],
        "selected_sim_revision": portrait["selected_sim_revision"],
        "client_width": w, "client_height": h,
        "hitbox": list(rect),
        "effect": {"kind": "RIGHT_CLICK_PORTRAIT", "button": "RIGHT",
                   "client": point, "follow": True, "not_equivalent": ["ENTER", "SHIFT_ENTER"]},
    }


def enqueue_native_portrait_follow(
    queue: CooperativeScreenQueue, *, work_id: str,
    capture_ref: str, observe: Callable[[], Awaitable[Mapping[str, Any]]],
    process_id: int, session_id: str,
    right_click_screen: Callable[[int, int], Awaitable[None]],
    move_screen: Callable[[int, int], Awaitable[None]],
) -> dict:
    """Injected native owner; queue preserves human idle + cross-agent lock.

    The real local adapter supplies the existing Win32 native mouse port.
    A right-click acknowledgment is not proof that Sims actually followed.
    """
    if (not isinstance(queue, CooperativeScreenQueue) or not callable(observe)
            or not callable(right_click_screen) or not callable(move_screen)
            or type(process_id) is not int or process_id <= 0
            or not isinstance(session_id, str) or not TOKEN.fullmatch(session_id)):
        raise PortraitFollowError("PORTRAIT_NATIVE_PORT_REQUIRED")
    anchor: dict = {}
    async def verify() -> tuple[dict, Mapping[str, Any]] | None:
        obs = await observe()
        if not _native_owner(obs, process_id, session_id):
            return None
        plan = plan_portrait_follow(capture_ref=capture_ref, observation=obs)
        if plan["state"] != "PORTRAIT_FOLLOW_READY_FOR_ADMISSION":
            return None
        signature = tuple((key, str(plan[key])) for key in (
            "sim_id", "capture_ref", "camera_revision", "portrait_revision",
            "ui_layout_revision", "selected_sim_revision", "hitbox", "client_width", "client_height",
        ))
        if anchor and anchor["signature"] != signature:
            return None
        if not anchor:
            anchor.update(signature=signature)
        return plan, obs

    async def validate() -> bool:
        return await verify() is not None

    async def action(checkpoint) -> None:
        await checkpoint()
        latest = await verify()
        if latest is None:
            raise PortraitFollowError("PORTRAIT_TARGET_STALE_AT_EFFECT")
        plan, obs = latest
        origin = (obs["client_origin_x"], obs["client_origin_y"])
        x, y = plan["effect"]["client"]
        try:
            await right_click_screen(origin[0]+x, origin[1]+y)
        finally:
            await checkpoint()
            after = await observe()
            if (not _native_owner(after, process_id, session_id)
                    or (after["client_origin_x"], after["client_origin_y"]) != origin):
                raise PortraitFollowError("PORTRAIT_REST_INTERRUPTED")
            rest = safe_rest_point(client_width=plan["client_width"],
                                   client_height=plan["client_height"],
                                   origin_x=origin[0], origin_y=origin[1])
            await move_screen(*rest["screen"])

    queue.enqueue(QueuedStep(work_id=work_id, validate=validate, action=action))
    return {"state": "QUEUED_PORTRAIT_RIGHT_CLICK",
            "work_id": work_id, "execute_allowed": False, "proof_ceiling": PROOF,
            "next": "ADMITTED_RIGHT_CLICK_THEN_FRESH_FOLLOW_OBSERVATION"}
