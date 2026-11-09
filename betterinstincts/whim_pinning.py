"""One guarded, mouse-only positive-whim pin route.

The native Sims host must inject actual screenshot/window observations, an
attested specific pin button hitbox, and admitted click/move ports. No hotkey.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Awaitable, Callable

from betterinstincts.screen_atlas import (
    ScreenAtlasError, enqueue_native_game_click,
)
from betterinstincts.ui_microsystems import UIMicrosystemError, resolve_action
from betterinstincts.workflow_interop import CooperativeScreenQueue


class WhimPinError(ValueError):
    pass


def _ref(value: object) -> bool:
    return (isinstance(value, str) and 1 <= len(value) <= 96
            and all(c.isalnum() or c in "_.:-" for c in value))


def plan_whim_pin(candidate: Mapping, calibration: Mapping, *,
                  capture_ref: str, selected_sim_ref: str,
                  player_active: bool = False, scene_verified: bool = False) -> dict:
    """Validate request; still no effect permission."""
    if not isinstance(candidate, Mapping) or not isinstance(calibration, Mapping):
        raise WhimPinError("WHIM_PIN_INPUT_INVALID")
    if not all(_ref(candidate.get(x)) for x in (
            "sim_ref", "whim_ref", "positive_proof_ref", "capture_ref")):
        raise WhimPinError("WHIM_PIN_PROOF_INVALID")
    if (candidate.get("evidence_kind") != "OBSERVED_POSITIVE"
            or candidate.get("pin_policy_opt_in") is not True):
        raise WhimPinError("PIN_FROM_OBSERVED_OPT_IN_ONLY")
    if (candidate["capture_ref"] != capture_ref
            or candidate["sim_ref"] != selected_sim_ref
            or calibration.get("whim_ref") != candidate["whim_ref"]
            or calibration.get("sim_ref") != selected_sim_ref
            or calibration.get("capture_ref") != capture_ref
            or calibration.get("mode") != "LIVE"
            or calibration.get("panel_id") != "whims"
            or calibration.get("target_id") != "whims.pin_whim"):
        raise WhimPinError("WRONG_WHIM_OR_ACTOR")
    try:
        resolve_action("whims", "whims.pin_whim", mode="LIVE")
    except UIMicrosystemError as exc:
        raise WhimPinError(str(exc)) from exc
    if player_active or not scene_verified:
        raise WhimPinError("PLAYER_OR_SCENE_NOT_ADMITTED")
    return {
        "schema":"betterinstincts.whim-pin-plan/v1",
        "whim_ref":candidate["whim_ref"],
        "sim_ref":selected_sim_ref,
        "capture_ref":capture_ref,
        "status":"AWAIT_NATIVE_HOST_ATTESTATION",
        "target_id":"whims.pin_whim",
        "execute_allowed":False, "control_permit":None,
        "proof_ceiling":"PIN_CLICK_NOT_GAME_PIN_SUCCESS",
    }


def enqueue_whim_pin(
    queue: CooperativeScreenQueue, *, work_id: str,
    candidate: Mapping, calibration: Mapping,
    observe: Callable[[], Awaitable[Mapping[str,Any]]],
    process_id: int, session_id: str,
    click_screen: Callable[[int,int], Awaitable[None]],
    move_screen: Callable[[int,int], Awaitable[None]],
    capture_ref: str, selected_sim_ref: str,
    player_active: bool = False, scene_verified: bool = False,
) -> dict:
    """Reuse the existing native Win32 host queue, never bypass it.

    The wrapped observation checks the *identity of the specific whim*
    before each generic panel target check, including the effect checkpoint.
    """
    plan = plan_whim_pin(candidate,calibration,capture_ref=capture_ref,
                        selected_sim_ref=selected_sim_ref,
                        player_active=player_active,
                        scene_verified=scene_verified)
    if (not isinstance(queue, CooperativeScreenQueue)
            or not callable(observe)):
        raise WhimPinError("CANONICAL_SCREEN_QUEUE_REQUIRED")

    effect_started = False

    async def checked_observe() -> Mapping[str,Any]:
        obs = await observe()
        if not isinstance(obs,Mapping):
            return {}
        valid = (
            obs.get("sim_ref") == selected_sim_ref
            and obs.get("selected_sim_ref") == selected_sim_ref
            and obs.get("capture_ref") == capture_ref
            and obs.get("scene_verified") is True
            and obs.get("player_active") is False
        )
        # After clicking, the button may disappear or show a pinned state.
        # The existing screen_atlas still insists on stable game ownership and
        # window geometry before parking the mouse. Never reclick afterward.
        if not effect_started:
            valid = (valid
                and obs.get("whim_ref") == candidate["whim_ref"]
                and obs.get("whim_visible") is True
                and obs.get("whim_pinned") is False)
        return obs if valid else {}

    async def one_click(x: int, y: int) -> None:
        nonlocal effect_started
        effect_started = True
        await click_screen(x, y)

    try:
        native = enqueue_native_game_click(
            queue,work_id=work_id,calibration=calibration,
            observe=checked_observe,process_id=process_id,session_id=session_id,
            click_screen=one_click,move_screen=move_screen,
        )
    except (ScreenAtlasError, UIMicrosystemError) as exc:
        raise WhimPinError(str(exc)) from exc
    return {**native,"whim_ref":plan["whim_ref"],
            "pin_verified":False,"success_requires":"OBSERVE_PIN_STATE_AFTER_CLICK",
            "proof_ceiling":plan["proof_ceiling"]}
