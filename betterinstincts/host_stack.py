"""Thin host call stack: viewport gate + needs plan + chance-card decision eval.

P95 seam: PrintWindow viewport → decision prompt → instincts plan → (live click /
Save As / restart gates remain outside this pure module). Never executes Sims UI.
"""
from __future__ import annotations

from typing import Mapping, Optional, Sequence

from betterinstincts.behavior_eval import BehaviorEvalError, evaluate_queue
from betterinstincts.decision_eval import (
    DecisionEvalError,
    measure_need_deltas,
    recommend,
    recommendation_to_dict,
)
from betterinstincts.event_balance import EventBalanceError, evaluate_event_turn
from betterinstincts.instincts_host import (
    InstinctsHostError,
    NeedSnapshot,
    plan,
    plan_to_dict,
)
from betterinstincts.build_optimize import BuildOptimizeError, evaluate_build_optimize
from betterinstincts.moodlets import MoodletError, evaluate_moodlets
from betterinstincts.sim_profile import SkillInput, SimProfileError, evaluate_sim_profile
from betterinstincts.viewport import ViewportError, predict_risk


class HostStackError(ValueError):
    pass


def evaluate_turn(
    needs: Mapping[str, float],
    *,
    available_objects: Sequence[str] = (),
    prompt_id: Optional[str] = None,
    prefer_home_control: bool = False,
    player_directed: bool = False,
    already_busy: bool = False,
    sim_absent: bool = False,
    capture_ref: str = "capture:host-turn",
    prior_needs: Optional[Mapping[str, float]] = None,
    host_action: Optional[str] = None,
    viewport: Optional[Mapping[str, object]] = None,
    viewport_context: Optional[Mapping[str, object]] = None,
    location_kind: str = "unknown",
    objects_on_current_lot: Optional[bool] = None,
    queue: Optional[Sequence[str]] = None,
    event_active: bool = False,
    event_goals_incomplete: Sequence[str] = (),
    event_profile: str = "lounge_party",
    outdoor_social_prefix: bool = False,
    indoor_capacity_observed: bool = False,
    homework_pending: bool = False,
    emotion: Optional[str] = None,
    moodlets: Sequence[str] = (),
    sim_name: Optional[str] = None,
    life_stage: Optional[str] = None,
    traits: Sequence[str] = (),
    aspiration: Optional[str] = None,
    aspiration_track: Optional[str] = None,
    skills: Sequence[SkillInput] = (),
    likes: Sequence[str] = (),
    dislikes: Sequence[str] = (),
    whims: Sequence[str] = (),
    build_objective: Optional[str] = None,
    build_owned_packs: Optional[Sequence[str]] = None,
    build_budget: Optional[float] = None,
    build_panels: int = 1,
    build_or_buy_mode: bool = False,
) -> dict:
    """Compose viewport, moodlets, event-balance, instincts, and dialog gates.

    Viewport anomalies outrank needs actions: do not click world objects while
    PrintWindow is black. See contracts/viewport-black.v1.json.

    When critical needs are off-lot, next_gate becomes MAP_TRAVEL_HOME_FIRST —
    never IN_FRAME_WALK_THRASH (glossary). Moodlets are supplied observations
    (portrait strip); absence is SENSOR_NOT_SUPPLIED — never vision-invented.

    Optional Simology/skills/preferences/whims attach a read-only sim_profile
    (docs/SIM_PROFILE.md); never authorizes practice_skill or BI-005 closure.

    Optional build_objective runs evaluate-only Build/Buy catalog ranking
    (docs/BUILD_OPTIMIZE.md); never paints walls from this pure module.
    """
    try:
        snap = NeedSnapshot(
            needs=needs,
            available_objects=tuple(available_objects),
            player_directed=player_directed,
            already_busy=already_busy,
            sim_absent=sim_absent,
            capture_ref=capture_ref,
        )
        instincts = plan_to_dict(plan(snap))
        decision = None
        if prompt_id:
            decision = recommendation_to_dict(
                recommend(prompt_id, needs, prefer_home_control=prefer_home_control)
            )
        influence = None
        if prior_needs is not None:
            influence = measure_need_deltas(prior_needs, needs, host_action=host_action)
        risk = predict_risk(viewport_context or {})
        behavior = None
        event_balance = None
        moodlet_eval = evaluate_moodlets(
            emotion=emotion,
            moodlets=moodlets,
            needs=needs,
            outdoor_social_prefix=outdoor_social_prefix,
            indoor_capacity_observed=indoor_capacity_observed,
            event_active=event_active,
            capture_ref=capture_ref,
        )
        sim_profile = evaluate_sim_profile(
            sim_name=sim_name,
            life_stage=life_stage,
            traits=traits,
            aspiration=aspiration,
            aspiration_track=aspiration_track,
            skills=skills,
            likes=likes,
            dislikes=dislikes,
            whims=whims,
            emotion=emotion,
            moodlets=moodlets,
            needs=needs,
            capture_ref=capture_ref,
        )
        if queue is not None:
            on_lot = (
                bool(objects_on_current_lot)
                if objects_on_current_lot is not None
                else (location_kind == "home")
            )
            behavior = evaluate_queue(
                needs,
                queue,
                player_directed=player_directed,
                objects_on_current_lot=on_lot,
                location_kind=location_kind,
                capture_ref=capture_ref,
            )
        if event_active or outdoor_social_prefix or homework_pending:
            viewport_ok = viewport is None or viewport.get("state") == "VIEWPORT_OK"
            event_balance = evaluate_event_turn(
                needs,
                event_active=event_active,
                event_goals_incomplete=event_goals_incomplete,
                outdoor_social_prefix=outdoor_social_prefix,
                indoor_capacity_observed=indoor_capacity_observed,
                homework_pending=homework_pending,
                player_directed=player_directed,
                already_busy=already_busy,
                viewport_ok=bool(viewport_ok),
                emotion=emotion,
                moodlets=moodlets,
                queue=tuple(queue or ()),
                event_profile=event_profile,
                capture_ref=capture_ref,
            )
    except (
        InstinctsHostError,
        DecisionEvalError,
        ViewportError,
        BehaviorEvalError,
        EventBalanceError,
        MoodletError,
        SimProfileError,
        BuildOptimizeError,
    ) as exc:
        raise HostStackError(str(exc)) from exc

    build_optimize = None
    if build_objective is not None:
        try:
            build_optimize = evaluate_build_optimize(
                build_objective,
                owned_packs=build_owned_packs or ("base",),
                budget=build_budget,
                panels=build_panels,
                player_directed=player_directed,
                build_or_buy_mode=build_or_buy_mode,
                capture_ref=capture_ref,
            )
        except BuildOptimizeError as exc:
            raise HostStackError(str(exc)) from exc

    # Priority: viewport/fallback > player > survival/event stack > behavior map travel > decision > needs.
    next_gate = "EXECUTE_INSTINCTS_PLAN"
    fallback = None
    if viewport is not None and viewport.get("state") != "VIEWPORT_OK":
        classification = str(viewport.get("classification") or "")
        next_gate = str(viewport.get("next_gate") or "VERIFY_VIEWPORT_BEFORE_ACTION")
        if classification in {
            "FULL_CLIENT_BLACK",
            "VOID_LOT_PLATFORM_WIREFRAME",
            "VIEWPORT_NEAR_BLACK",
            "VIEWPORT_BLACK_HUD_ALIVE",
        }:
            fallback = {
                "mechanism": "ENTER_BUILD_BUY_UNSTICK",
                "owner": "scripts/viewport_recover.py",
                "contract": "contracts/viewport-black.v1.json",
                "command": (
                    "python -m scripts.viewport_recover --capture --process-id PID "
                    "--execute --max-steps 5"
                ),
                "success_classification": "BUILD_BUY_CATALOG_RECOVERY",
                "forbidden": ["NEEDS_OBJECT_CLICK", "RESUME", "TerminateProcess"],
            }
            next_gate = "ENTER_BUILD_BUY_UNSTICK"
        elif classification == "BUILD_BUY_CATALOG_RECOVERY" or viewport.get("state") == "VIEWPORT_MODE_BUILD_BUY":
            fallback = {
                "mechanism": "BUILD_BUY_CATALOG_RECOVERY",
                "owner": "scripts/viewport_recover.py",
                "next": "EXIT_BUY_TO_LIVE_OR_OPERATOR_SAVE_EXIT",
                "forbidden": ["NEEDS_OBJECT_CLICK", "RESUME"],
            }
            next_gate = "EXIT_BUY_TO_LIVE_OR_OPERATOR_SAVE_EXIT"
    elif player_directed or already_busy:
        next_gate = "RESPECT_PLAYER_OR_BUSY_STATE"
    elif (
        build_optimize is not None
        and build_optimize.get("state") == "BUILD_OPTIMIZE_PLAN_READY"
        and build_or_buy_mode
        and not player_directed
    ):
        next_gate = "BUILD_OPTIMIZE_EVALUATE_ONLY"
        fallback = {
            "mechanism": "BUILD_OPTIMIZE_PLAN",
            "owner": "betterinstincts/build_optimize.py",
            "contract": "contracts/build-optimize.v1.json",
            "best": build_optimize.get("best"),
            "objective": build_optimize.get("objective"),
            "execute_allowed": False,
            "forbidden": [
                "SENDINPUT_WITHOUT_SESSION",
                "TOUCH_USER_SAVES",
                "RESUME",
                "FORCE_MODE_WHILE_PLAYER_PLAYING",
            ],
        }
    elif sim_absent:
        next_gate = "SIM_ABSENT_HOST_PREP_ONLY"
    elif event_balance is not None and event_balance["gate"] == "SURVIVAL_NEEDS_CRITICAL":
        next_gate = "SURVIVAL_NEEDS_BEFORE_EVENT"
        fallback = {
            "mechanism": "SURVIVAL_NEEDS_CRITICAL",
            "owner": "betterinstincts/event_balance.py",
            "contract": "contracts/event-balance.v1.json",
            "action": event_balance["action"],
            "survival_critical": event_balance["survival_critical"],
            "forbidden": ["EVENT_GOAL_SPAM", "OUTDOOR_SOCIAL_DEFAULT", "RESUME"],
        }
    elif event_balance is not None and event_balance["gate"] == "EVENT_INDOOR_ROUTING":
        next_gate = "EVENT_INDOOR_ROUTING"
        fallback = {
            "mechanism": event_balance["action"],
            "owner": "betterinstincts/event_balance.py",
            "contract": "contracts/event-balance.v1.json",
            "primary_route": event_balance.get("primary_route") or "SIT_AND_CHAT_HERE_INDOOR",
            "preferred_routes": event_balance["preferred_routes"],
            "rca_leading": event_balance["rca_leading"],
            "forbidden": [
                "IN_FRAME_WALK_THRASH_ACROSS_LOT",
                "REPEATED_OUTDOOR_GREET",
                "GREET_WITHOUT_SEAT_GROUNDING",
                "GO_HERE_THAT_RE_ROUTES_OUTDOOR",
                "RESUME",
            ],
        }
    elif event_balance is not None and event_balance["gate"] in {
        "EVENT_GOAL_PROGRESS",
        "EVENT_FUN_VIA_GOALS",
    }:
        next_gate = event_balance["gate"]
        goal_plan = event_balance.get("goal_plan") or {}
        fallback = {
            "mechanism": event_balance["action"],
            "owner": "betterinstincts/event_goals.py",
            "contract": "contracts/event-goals.v1.json",
            "goals_incomplete": event_balance["goals_incomplete"],
            "next_goal": goal_plan.get("next_goal"),
            "next_actions": goal_plan.get("next_actions") or [],
            "primary_route": goal_plan.get("primary_route") or event_balance.get("primary_route"),
            "preferred_routes": event_balance.get("preferred_routes")
            or goal_plan.get("preferred_routes")
            or [],
            "forbidden": [
                "LEAVE_EVENT_FOR_TV_OR_PHONE_FLUFF",
                "HOMEWORK_DURING_TIMER",
                "SPAM_OUTDOOR_GREET_HOPING_GOALS_TICK",
                "GENERIC_CHAT_WHEN_SPECIFIC_GOAL_REQUIRED",
            ],
        }
    elif event_balance is not None and event_balance["gate"] == "HOMEWORK_HOLD_OR_SCHEDULE":
        next_gate = "HOMEWORK_HOLD_OR_SCHEDULE"
        fallback = {
            "mechanism": event_balance["action"],
            "owner": "betterinstincts/event_balance.py",
            "forbidden": ["OUTDOOR_SOCIAL_DEFAULT"],
        }
    elif behavior is not None and behavior["clarity"]["disposition"] in {
        "OPTIMIZE", "EMULATE_THEN_OPTIMIZE"
    } and behavior["clarity"].get("preferred_route") in {
        "MAP_TRAVEL", "MAP_TRAVEL_IF_OBJECTS_OFF_LOT_ELSE_LOCAL_OBJECT"
    } and not (
        objects_on_current_lot if objects_on_current_lot is not None else location_kind == "home"
    ):
        fallback = {
            "mechanism": "MAP_TRAVEL_HOME_FIRST",
            "owner": "scripts/needs_force.py",
            "contract": "contracts/needs-force.v1.json",
            "command": (
                "python -m scripts.needs_force run --location-kind "
                f"{location_kind} --process-id PID --execute"
            ),
            "forbidden": ["IN_FRAME_WALK_THRASH", "RESUME", "DELETE_SAVE"],
            "behavior_row": behavior["clarity"]["matched_row_id"],
        }
        next_gate = "MAP_TRAVEL_HOME_FIRST"
    elif decision is not None:
        next_gate = "RESOLVE_DECISION_PROMPT"
    elif risk.get("risk_level") in {"ELEVATED", "HIGH"} and risk.get("required_before_clicks"):
        next_gate = "PRINTWINDOW_ANALYZE_BEFORE_CLICKS"
    elif instincts.get("all_needs_green"):
        next_gate = "LAB_SAVE_AS_BI_CONT_WHEN_AUTHORIZED"
    elif instincts.get("state") == "BLOCKED_MISSING_OBJECTS":
        next_gate = "PLACE_OR_LOCATE_REQUIRED_OBJECTS"

    return {
        "state": "HOST_TURN_EVALUATED",
        "capture_ref": capture_ref,
        "next_gate": next_gate,
        "fallback": fallback,
        "behavior": behavior,
        "moodlets": moodlet_eval,
        "sim_profile": sim_profile,
        "event_balance": event_balance,
        "build_optimize": build_optimize,
        "instincts": instincts,
        "decision": decision,
        "influence": influence,
        "viewport": dict(viewport) if viewport else None,
        "viewport_risk": risk,
        "proof_ceiling": "HOST_STACK_OFFLINE_COMPOSITION_NOT_LIVE_PROOF",
    }

