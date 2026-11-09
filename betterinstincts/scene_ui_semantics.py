"""Live HUD semantic state: overlay resolution, bottom-right active panel, queue continuity.

No side effects. Every overlay action is a proposal requiring independently
admitted native action; a random event is NOT equivalent to a generic close.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from betterinstincts.decision_eval import score_option, SAFE_TAGS, RISK_TAGS
from betterinstincts.ui_microsystems import (
    load_contract as load_ui_contract, resolve_action, panel_observation_matches,
    UIMicrosystemError,
)

TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")
BOTTOM_RIGHT = frozenset({
    "aspirations", "career", "skills", "relationships", "simology",
    "personal_inventory", "needs",
})
OVERLAY_TYPES = frozenset({"CAREER_EVENT", "RANDOM_EVENT", "OPPORTUNITY", "SIM_NOTIFICATION", "DECISION_MODAL"})
PROOF = "OFFLINE_HUD_CONTEXT_NOT_LIVE_GAME_CERTIFIED"


class SceneUISemanticsError(ValueError):
    pass


def _token(value: object) -> bool:
    return isinstance(value, str) and bool(TOKEN.fullmatch(value))


def _cues(value: object, expected: Mapping[str, str]) -> bool:
    return (
        isinstance(value, list) and len(value) == 2
        and all(isinstance(x, Mapping) and set(x) == {"source", "token"} for x in value)
        and {x.get("source"): x.get("token") for x in value} == dict(expected)
    )


def _score_observed_overlay_choices(
    overlay: Mapping[str, Any], *, capture_ref: str,
    needs: Mapping[str, float] | None, layout_revision: str,
    selected_sim_revision: str, client_width: Any, client_height: Any,
) -> dict:
    """Conservative existing decision-score microservice over observed choices.

    A model-generated label or unverified option is never an actual choice.
    A unique top score is a *recommendation* requiring an admitted mouse port.
    """
    base = {"state": "OVERLAY_OPTIONS_NOT_ATTESTED", "execute_allowed": False}
    if (
        overlay.get("choices_capture_ref") != capture_ref
        or overlay.get("choices_ui_layout_revision") != layout_revision
        or overlay.get("choices_selected_sim_revision") != selected_sim_revision
        or not _cues(overlay.get("choice_cues"), {
            "visual": "overlay_options_visible",
            "operator": "overlay_options_confirmed",
        })
    ):
        return base
    choices = overlay.get("choices")
    if (not isinstance(choices, list) or not 2 <= len(choices) <= 6
            or type(client_width) is not int or type(client_height) is not int
            or client_width < 640 or client_height < 480
            or not isinstance(needs, Mapping)
            or set(needs) != {"hunger","bladder","energy","hygiene","fun","social"}
            or any(type(n) not in {float,int} or not 0 <= n <= 1 for n in needs.values())):
        return base
    seen = set()
    scores = []
    for choice in choices:
        if not isinstance(choice, Mapping):
            return base
        identifier, tags, rect = choice.get("option_id"), choice.get("tags"), choice.get("hitbox")
        if (not _token(identifier) or identifier in seen
                or choice.get("source") != "HOST_CAPTURE"
                or not isinstance(tags, list) or len(tags) > 12
                or any(not isinstance(t, str) or t not in SAFE_TAGS | RISK_TAGS for t in tags)
                or not isinstance(rect, list) or len(rect) != 4
                or any(type(n) is not int for n in rect)):
            return base
        left, top, right, bottom = rect
        if (not 0 <= left < right < client_width
                or not 0 <= top < bottom < client_height
                or min(right-left,bottom-top) < 8):
            return base
        seen.add(identifier)
        scores.append(score_option(
            {"option_id": identifier, "label": identifier, "tags": tags},
            needs_critical=min(needs.values()) < 0.35,
            prefer_home_control=False,
        ))
    ranks = sorted(scores, key=lambda x: (-x.score, x.option_id))
    if ranks[0].score <= 0 or ranks[0].score == ranks[1].score:
        return {**base, "state": "OVERLAY_CHOICE_TIE_OR_UNSAFE_REVIEW",
                "ranked_ids": [x.option_id for x in ranks]}
    best = ranks[0]
    return {**base, "state": "OVERLAY_CHOICE_RECOMMENDED",
            "recommended_option_id": best.option_id,
            "score": best.score,
            "rationale": list(best.rationale),
            "option_hitbox": list(next(x["hitbox"] for x in choices if x["option_id"] == best.option_id)),
            "ranked_ids": [x.option_id for x in ranks],
            "next": "EXACT_HOST_AND_PLAYER_ADMISSION_REQUIRED_NO_AUTO_ACCEPT"}


def assess_live_hud(
    *, capture_ref: str, observation: Mapping[str, Any] | None,
    requested_panel: str | None = None, requested_target: str | None = None,
    needs: Mapping[str, float] | None = None,
) -> dict:
    """Evaluate overlay before panel actions, preserve pending goal/queue refs."""
    base = {"execute_allowed": False, "proof_ceiling": PROOF, "capture_ref": capture_ref,
            "panel": None, "overlay": None, "continuation": None}
    def hold(gate: str, reason: str) -> dict:
        return {**base, "state": "LIVE_HUD_REOBSERVE_REQUIRED", "gate": gate, "reason": reason}
    if not _token(capture_ref) or not isinstance(observation, Mapping):
        return hold("LIVE_HUD_REOBSERVE", "FRESH_OBSERVATION_REQUIRED")
    if (observation.get("source") != "HOST_CAPTURE" or observation.get("capture_ref") != capture_ref
            or observation.get("mode") != "LIVE" or observation.get("scene_id") != "live_mode"
            or not _token(observation.get("ui_layout_revision"))
            or not _token(observation.get("selected_sim_revision"))
            or type(observation.get("active_sim_id")) is not int or observation["active_sim_id"] <= 0):
        return hold("LIVE_HUD_REOBSERVE", "LIVE_UI_IDENTITY_OR_REVISION_UNVERIFIED")
    goal = observation.get("active_goal_id")
    if goal is not None and not _token(goal):
        return hold("LIVE_HUD_REOBSERVE", "GOAL_ID_UNVERIFIED")
    queue = observation.get("pending_action_queue_refs", [])
    if (not isinstance(queue, list) or len(queue) > 32 or
            any(not _token(ref) for ref in queue) or len(set(queue)) != len(queue)):
        return hold("LIVE_HUD_REOBSERVE", "QUEUE_REFS_INVALID")
    continuation = {
        "active_goal_id": goal, "queue_refs": list(queue),
        "selected_sim_id": observation["active_sim_id"],
        "selected_sim_revision": observation["selected_sim_revision"],
        "resume_condition": "FRESH_REVALIDATION_AFTER_OVERLAY",
        "resume_without_replaying_unverified_actions": True,
    }
    base["continuation"] = continuation
    overlay = observation.get("overlay")
    if overlay is not None:
        if (not isinstance(overlay, Mapping) or not _token(overlay.get("overlay_id"))
                or overlay.get("kind") not in OVERLAY_TYPES
                or overlay.get("capture_ref") != capture_ref
                or overlay.get("ui_layout_revision") != observation["ui_layout_revision"]
                or overlay.get("visible") is not True or not _cues(
                    overlay.get("cues"),
                    {"visual": "visible_overlay_identity", "operator": "overlay_identity_confirmed"},
                )):
            return hold("OVERLAY_REOBSERVE", "OVERLAY_IDENTITY_UNVERIFIED")
        overlay_id = overlay["overlay_id"]
        if overlay.get("decision_state") != "RESOLVED":
            advice = _score_observed_overlay_choices(
                overlay, capture_ref=capture_ref, needs=needs,
                layout_revision=observation["ui_layout_revision"],
                selected_sim_revision=observation["selected_sim_revision"],
                client_width=observation.get("client_width"),
                client_height=observation.get("client_height"),
            )
            return {**base, "state": "OVERLAY_DECISION_PENDING", "gate": "OVERLAY_DECISION_REQUIRED",
                    "overlay": {"overlay_id": overlay_id, "kind": overlay["kind"],
                                "decision_owner": "EXISTING_EVENT_OR_CAREER_MICROSYSTEM",
                                "choice_advisory": advice, "dismiss_action": None},
                    "next": "EVALUATE_DECISION_THEN_REOBSERVE;DO_NOT_CANCEL_PLAYER_QUEUE"}
        if overlay.get("decision_accepted") is not True:
            return {**base, "state": "OVERLAY_RESOLUTION_UNVERIFIED", "gate": "OVERLAY_REOBSERVE",
                    "overlay": {"overlay_id": overlay_id, "kind": overlay["kind"]}}
        close = overlay.get("dismiss_target")
        if (not isinstance(close, Mapping)
                or close.get("kind") not in {"ACKNOWLEDGE_RESOLVED", "CLOSE_RESOLVED"}
                or close.get("overlay_id") != overlay_id
                or close.get("capture_ref") != capture_ref
                or close.get("ui_layout_revision") != observation["ui_layout_revision"]
                or close.get("visible") is not True or close.get("obscured") is not False
                or close.get("enabled") is not True
                or not _cues(close.get("cues"), {
                    "visual": "resolved_overlay_dismiss_button",
                    "operator": "dismiss_button_confirmed",
                })):
            return {**base, "state": "OVERLAY_DISMISS_UNVERIFIED", "gate": "OVERLAY_REOBSERVE",
                    "overlay": {"overlay_id": overlay_id, "kind": overlay["kind"]}}
        rect = close.get("hitbox")
        w, h = observation.get("client_width"), observation.get("client_height")
        if (type(w) is not int or type(h) is not int or w < 640 or h < 480
                or not isinstance(rect, list) or len(rect) != 4
                or any(type(v) is not int for v in rect)):
            return hold("OVERLAY_REOBSERVE", "DISMISS_HITBOX_UNVERIFIED")
        left, top, right, bottom = rect
        if not (0 <= left < right < w and 0 <= top < bottom < h
                and min(right-left, bottom-top) >= 8):
            return hold("OVERLAY_REOBSERVE", "DISMISS_HITBOX_OUT_OF_BOUNDS")
        return {**base, "state": "OVERLAY_DISMISS_AWAIT_NATIVE_ADMISSION",
                "gate": "OVERLAY_DISMISS_READY",
                "overlay": {"overlay_id": overlay_id, "kind": overlay["kind"],
                            "button": "LEFT", "client": [(left+right)//2, (top+bottom)//2],
                            "hitbox": list(rect), "client_width": w, "client_height": h,
                            "ui_layout_revision": observation["ui_layout_revision"],
                            "resume_only_after_overlay_absent": True}}
    panel_id = observation.get("active_right_panel_id")
    if panel_id is None:
        return {**base, "state": "HUD_NO_RIGHT_PANEL", "gate": "HUD_CONTEXT_READY",
                "active_panel_id": None}
    cfg = load_ui_contract()
    if panel_id not in BOTTOM_RIGHT or panel_id not in cfg["panels"]:
        return hold("RIGHT_PANEL_REOBSERVE", "ACTIVE_PANEL_ID_UNVERIFIED")
    panel = cfg["panels"][panel_id]
    if (observation.get("right_panel_visible") is not True or
            observation.get("right_panel_obscured") is not False or
            not _cues(observation.get("right_panel_cues"), panel["cues"])):
        return hold("RIGHT_PANEL_REOBSERVE", "ACTIVE_PANEL_CUES_INVALID")
    resolved = {
        "panel_id": panel_id, "family": panel["family"],
        "ui_layout_revision": observation["ui_layout_revision"],
        "selected_sim_revision": observation["selected_sim_revision"],
        "cues": panel["cues"], "status": "OBSERVED_PANEL_CONTEXT",
    }
    if requested_panel is not None:
        if requested_panel != panel_id:
            return {**base, "state": "RIGHT_PANEL_SWITCH_REQUIRED", "gate": "RIGHT_PANEL_SWITCH_OR_REOBSERVE",
                    "panel": resolved, "requested_panel": requested_panel}
        if not _token(requested_target):
            return hold("RIGHT_PANEL_REOBSERVE", "TARGET_ID_REQUIRED")
        try:
            action = resolve_action(panel_id, requested_target, mode="LIVE", cfg=cfg)
        except (UIMicrosystemError, ValueError) as exc:
            return hold("RIGHT_PANEL_REOBSERVE", str(exc))
        # Fresh exact hitbox attestation is owned by ui_microsystems; no
        # model-selected point or slot is given merely because panel is active.
        resolved["action"] = action
        resolved["hitbox_attestation_required"] = True
    return {**base, "state": "RIGHT_PANEL_OBSERVED", "gate": "HUD_CONTEXT_READY",
            "active_panel_id": panel_id, "panel": resolved}


def enqueue_resolved_overlay_dismiss(
    queue, *, work_id: str, capture_ref: str, observe,
    process_id: int, session_id: str, click_screen, move_screen,
) -> dict:
    """One admitted click of a *resolved* event overlay's attested close.

    Queue/host validate again immediately before side effect. An unresolved
    career or random decision has NO generic escape/cancel shortcut.
    """
    from betterinstincts.workflow_interop import CooperativeScreenQueue, QueuedStep
    from betterinstincts.screen_atlas import _native_owner
    from betterinstincts.camera_traverse import safe_rest_point

    if (not isinstance(queue, CooperativeScreenQueue) or not _token(work_id)
            or not _token(capture_ref) or type(process_id) is not int or process_id <= 0
            or not _token(session_id) or not all(callable(x) for x in (
                observe, click_screen, move_screen,
            ))):
        raise SceneUISemanticsError("OVERLAY_NATIVE_PORT_REQUIRED")
    anchor = {}
    receipt = {"state": "NOT_DISPATCHED", "overlay_cleared_observed": False,
               "resume_queued_game_actions": False}
    async def verified():
        scene = await observe()
        if not _native_owner(scene, process_id, session_id):
            return None
        plan = assess_live_hud(capture_ref=capture_ref, observation=scene)
        if plan["gate"] != "OVERLAY_DISMISS_READY":
            return None
        o = plan["overlay"]
        fingerprint = (
            o["overlay_id"], o["kind"], tuple(o["hitbox"]),
            o["ui_layout_revision"], tuple(o["client"]),
            plan["continuation"]["selected_sim_revision"],
            plan["continuation"]["active_goal_id"],
        )
        if anchor and anchor["fingerprint"] != fingerprint:
            return None
        if not anchor:
            anchor["fingerprint"] = fingerprint
        return plan, scene

    async def validate() -> bool:
        return await verified() is not None

    async def action(checkpoint) -> None:
        await checkpoint()
        proof = await verified()
        if proof is None:
            raise SceneUISemanticsError("RESOLVED_OVERLAY_STALE_AT_EFFECT")
        plan, obs = proof
        o = plan["overlay"]
        origin = (obs["client_origin_x"], obs["client_origin_y"])
        try:
            await click_screen(origin[0]+o["client"][0], origin[1]+o["client"][1])
            receipt["state"] = "OVERLAY_DISMISS_DISPATCHED_UNVERIFIED"
        finally:
            await checkpoint()
            after = await observe()
            if (not _native_owner(after, process_id, session_id)
                    or (after["client_origin_x"], after["client_origin_y"]) != origin):
                raise SceneUISemanticsError("OVERLAY_CURSOR_REST_INTERRUPTED")
            rest = safe_rest_point(
                client_width=o["client_width"], client_height=o["client_height"],
                origin_x=origin[0], origin_y=origin[1],
            )
            await move_screen(*rest["screen"])
            # Fresh overlay absence is a necessary, not sufficient, condition
            # for resuming old actions; every queued action revalidates itself.
            receipt["overlay_cleared_observed"] = (
                after.get("source") == "HOST_CAPTURE"
                and after.get("overlay") is None
                and after.get("active_sim_id") == plan["continuation"]["selected_sim_id"]
                and after.get("selected_sim_revision") == plan["continuation"]["selected_sim_revision"]
            )
            if receipt["overlay_cleared_observed"]:
                receipt["state"] = "OVERLAY_CLEARED_QUEUE_REVALIDATION_REQUIRED"
    queue.enqueue(QueuedStep(work_id=work_id, validate=validate, action=action))
    return {"state": "QUEUED_RESOLVED_OVERLAY_DISMISS",
            "work_id": work_id, "receipt": receipt, "execute_allowed": False,
            "proof_ceiling": PROOF}


def enqueue_native_overlay_choice(
    queue, *, work_id: str, capture_ref: str, observe,
    process_id: int, session_id: str, click_screen, move_screen,
) -> dict:
    """One recommended, freshly corroborated choice; never guess a popup option.

    The local host must explicitly permit choice automation for this event.
    Revalidates selected Sim, event, layout, options and ranking immediately
    before a single native click; no repeated or negative-score selection.
    """
    from betterinstincts.workflow_interop import CooperativeScreenQueue, QueuedStep
    from betterinstincts.screen_atlas import _native_owner
    from betterinstincts.camera_traverse import safe_rest_point

    if (not isinstance(queue, CooperativeScreenQueue)
            or not _token(work_id) or not _token(capture_ref)
            or type(process_id) is not int or process_id <= 0
            or not _token(session_id)
            or not all(callable(x) for x in (observe, click_screen, move_screen))):
        raise SceneUISemanticsError("OVERLAY_CHOICE_NATIVE_PORT_REQUIRED")
    anchor = {}
    receipt = {"state": "NOT_DISPATCHED", "choice_acknowledged": False,
               "resume_queued_game_actions": False}
    async def verified():
        obs = await observe()
        if not _native_owner(obs, process_id, session_id):
            return None
        ui = assess_live_hud(
            capture_ref=capture_ref, observation=obs, needs=obs.get("needs"),
        )
        if ui["gate"] != "OVERLAY_DECISION_REQUIRED":
            return None
        overlay = obs.get("overlay")
        if not isinstance(overlay, Mapping) or overlay.get("auto_choice_authorized") is not True:
            return None
        advice = ui["overlay"]["choice_advisory"]
        if advice["state"] != "OVERLAY_CHOICE_RECOMMENDED":
            return None
        fingerprint = (
            overlay["overlay_id"], advice["recommended_option_id"],
            tuple(advice["option_hitbox"]), obs["ui_layout_revision"],
            obs["selected_sim_revision"], obs["active_sim_id"],
            ui["continuation"]["active_goal_id"],
        )
        if anchor and anchor["fingerprint"] != fingerprint:
            return None
        if not anchor:
            anchor["fingerprint"] = fingerprint
        return ui, obs

    async def validate():
        return await verified() is not None

    async def action(checkpoint):
        await checkpoint()
        ready = await verified()
        if ready is None:
            raise SceneUISemanticsError("OVERLAY_CHOICE_CHANGED_AT_EFFECT")
        plan, obs = ready
        advice = plan["overlay"]["choice_advisory"]
        l, t, r, b = advice["option_hitbox"]
        origin = (obs["client_origin_x"], obs["client_origin_y"])
        try:
            await click_screen(origin[0]+(l+r)//2, origin[1]+(t+b)//2)
            receipt["state"] = "OVERLAY_CHOICE_DISPATCHED_UNVERIFIED"
        finally:
            await checkpoint()
            after = await observe()
            if (not _native_owner(after, process_id, session_id)
                    or (after["client_origin_x"], after["client_origin_y"]) != origin):
                raise SceneUISemanticsError("OVERLAY_CHOICE_REST_INTERRUPTED")
            rest = safe_rest_point(
                client_width=obs["client_width"], client_height=obs["client_height"],
                origin_x=origin[0], origin_y=origin[1],
            )
            await move_screen(*rest["screen"])
            next_overlay = after.get("overlay")
            receipt["choice_acknowledged"] = (
                after.get("source") == "HOST_CAPTURE"
                and after.get("active_sim_id") == obs["active_sim_id"]
                and (
                    next_overlay is None
                    or (
                        isinstance(next_overlay, Mapping)
                        and next_overlay.get("overlay_id") == obs["overlay"]["overlay_id"]
                        and next_overlay.get("decision_state") == "RESOLVED"
                    )
                )
            )
            if receipt["choice_acknowledged"]:
                receipt["state"] = "CHOICE_ACKNOWLEDGED_NEXT_OVERLAY_REOBSERVE_REQUIRED"

    queue.enqueue(QueuedStep(work_id=work_id, validate=validate, action=action))
    return {"state": "QUEUED_VERIFIED_OVERLAY_CHOICE",
            "work_id": work_id, "execute_allowed": False,
            "receipt": receipt, "proof_ceiling": PROOF}
