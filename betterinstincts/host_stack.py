"""Thin host call stack: viewport gate + needs plan + chance-card decision eval.

P95 seam: PrintWindow viewport → decision prompt → instincts plan → (live click /
Save As / restart gates remain outside this pure module). Never executes Sims UI.
"""
from __future__ import annotations

from typing import Mapping, Optional, Sequence

from betterinstincts.behavior_eval import BehaviorEvalError, evaluate_queue
from betterinstincts.queue_capacity import QueueCapacityError, evaluate_queue_capacity
from betterinstincts.traversal_voi import evaluate_traversal_voi
from betterinstincts.decision_eval import (
    DecisionEvalError,
    measure_need_deltas,
    recommend,
    recommendation_to_dict,
)
from betterinstincts.event_balance import EventBalanceError, evaluate_event_turn
from betterinstincts.fun_service import (
    FunServiceError,
    evaluate_fun_service,
    should_attach_fun_service,
)
from betterinstincts.gardening_service import GardeningServiceError, evaluate_gardening_turn
from betterinstincts.household_economy import (
    HouseholdEconomyError, evaluate_household_economy,
)
from betterinstincts.household_upkeep import (
    HouseholdUpkeepError, evaluate_household_upkeep,
)
from betterinstincts.need_service_base import threshold_pair
from betterinstincts.need_services import (
    NeedServicesError,
    compact_need_services,
    evaluate_need_services,
    should_attach_need_services,
)
from betterinstincts.instincts_host import (
    InstinctsHostError,
    NeedSnapshot,
    plan,
    plan_to_dict,
)
from betterinstincts.build_integrity import BuildIntegrityError, structure_restore_plan
from betterinstincts.build_library_checkpoint import (
    BuildLibraryCheckpointError,
    plan_library_save_if_required,
)
from betterinstincts.build_optimize import BuildOptimizeError, evaluate_build_optimize
from betterinstincts.build_spatial import BuildSpatialError, build_order_plan, inventory_spatial
from betterinstincts.moodlets import MoodletError, evaluate_moodlets
from betterinstincts.navigating_needs import (
    NavigatingNeedsError,
    evaluate_navigating_needs_turn,
)
from betterinstincts.scenario_goals import evaluate_scenario_turn
from betterinstincts.discovery_hud import DiscoveryHudError, evaluate_discovery_hud
from betterinstincts.autonomy_moderation import AutonomyModerationError, evaluate_autonomy_moderation
from betterinstincts.behavior_valence import BehaviorValenceError, evaluate_behavior_valence
from betterinstincts.opportunistic_actions import (
    OpportunisticActionError,
    plan_school_homework_window,
    plan_targeted_chat_whim,
)
from betterinstincts.school_day import (
    SchoolDayError,
    evaluate_school_day_turn,
    resolve_sim_premises,
)
from betterinstincts.sim_profile import SkillInput, SimProfileError, evaluate_sim_profile
from betterinstincts.social_opportunity import (
    SocialOpportunityError,
    evaluate_social_opportunity,
    should_attach_social_opportunity,
)
from betterinstincts.career_service import (
    CareerServiceError,
    compact_career_service,
    evaluate_career_service,
    should_attach_career_service,
)
from betterinstincts.preference_prompts import evaluate_offer as evaluate_preference_offer
from betterinstincts.aspiration_service import (
    AspirationServiceError,
    compact_aspiration_service,
    evaluate_aspiration_service,
    should_attach_aspiration_service,
)
from betterinstincts.balance_service import (
    BalanceServiceError,
    compact_balance_service,
    evaluate_balance_service,
    should_attach_balance_service,
)
from betterinstincts.teen_homework import (
    TeenHomeworkError,
    evaluate_teen_homework_turn,
    should_attach_teen_homework,
)
from betterinstincts.camera_traverse import (
    CameraTraverseError,
    assess_drift_recovery,
    assess_edge_creek_regression,
    assess_world_target,
    evaluate_cursor_risk,
)
from betterinstincts.viewport import ViewportError, predict_risk
from betterinstincts.sim_camera import SimCameraError, plan_sim_camera
from betterinstincts.active_sim_camera_lock import evaluate_active_sim_camera_lock
from betterinstincts.lot_focus import (
    LotFocusError,
    assess_lot_focus,
    assess_off_intent_view,
    should_assess_lot_focus,
)
from betterinstincts.live_host_ops import (
    LiveHostOpsError,
    assess_edge_creek_flag,
    assess_unpause_admission,
    assess_world_xy_policy,
    load_contract as load_live_host_ops,
    priority_order as live_host_priority_order,
)
from betterinstincts.lot_boundary import (
    LotBoundaryError,
    admit_world_click_in_footprint,
    assess_lot_boundary,
)
from betterinstincts.scenes import stamp_host_capture_game_version
from betterinstincts.scene_ui_semantics import assess_live_hud, SceneUISemanticsError
from betterinstincts.scenery_memory import record_scenery, SceneryMemoryError


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
    multitasking: Optional[bool] = None,
    sim_room_id: Optional[str] = None,
    sim_seated: Optional[bool] = None,
    sim_seat_id: Optional[str] = None,
    lot_traits: Sequence[str] = (),
    event_active: bool = False,
    event_goals_incomplete: Sequence[str] = (),
    event_profile: str = "lounge_party",
    outdoor_social_prefix: bool = False,
    indoor_capacity_observed: bool = False,
    homework_pending: bool = False,
    inventory_has_homework: Optional[bool] = None,
    homework_on_lot: Optional[bool] = None,
    school_homework_window: Optional[Mapping[str, object]] = None,
    school_day_active: bool = False,
    school_goals_incomplete: Sequence[str] = (),
    school_phase: Optional[str] = None,
    school_profile: str = "high_school_years",
    sim_at_school: Optional[bool] = None,
    camera_lot_kind: Optional[str] = None,
    social_prompt_active: bool = False,
    social_prompt_kind: str = "invite_over",
    social_prompt_text: str = "",
    social_invitee_name: Optional[str] = None,
    sim_library: Sequence[Mapping[str, object]] = (),
    social_lookup_ran: bool = False,
    invitee_occult_status: Optional[str] = None,
    queued_social_targets: Sequence[Mapping[str, object]] = (),
    pinned_whims: Sequence[str] = (),
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
    lot_floor_profile_id: Optional[str] = None,
    lot_floor_key: Optional[str] = None,
    lot_model: Optional[Mapping[str, object]] = None,
    scenario_active: bool = False,
    scenario_goals_incomplete: Sequence[str] = (),
    scenario_profile: str = "scoring_simoleons",
    allow_career: bool = False,
    needs_game_certified: bool = False,
    income_game_observed: bool = False,
    guests_present: bool = False,
    occupied_objects: Sequence[str] = (),
    sibling_fun_lane_claims: Sequence[str] = (),
    need_failure_signals: Optional[Mapping[str, Sequence[str]]] = None,
    navigating_needs_active: bool = False,
    navigating_needs_incomplete: Sequence[str] = (),
    navigating_needs_profile: str = "navigating_needs",
    gardening: Optional[Mapping[str, object]] = None,
    household_upkeep: Optional[Mapping[str, object]] = None,
    household_economy: Optional[Mapping[str, object]] = None,
    discovery_hud: Optional[Mapping[str, object]] = None,
    autonomy_observation: Optional[Mapping[str, object]] = None,
    behavior_model: Optional[Mapping[str, object]] = None,
    cursor_client_x: Optional[int] = None,
    cursor_client_y: Optional[int] = None,
    client_width: Optional[int] = None,
    client_height: Optional[int] = None,
    edge_band_px: Optional[int] = None,
    camera_pointer_context: Optional[Mapping[str, object]] = None,
    camera_scan_needed: bool = False,
    camera_pan_directions: Sequence[str] = (),
    world_target: Optional[Mapping[str, object]] = None,
    camera_recovery: Optional[Mapping[str, object]] = None,
    sim_camera_command: Optional[str] = None,
    sim_camera_observation: Optional[Mapping[str, object]] = None,
    camera_map_goal: Optional[Mapping[str, object]] = None,
    traversal_voi_observation: Optional[Mapping[str, object]] = None,
    camera_zoom_intent: Optional[str] = None,
    camera_planning_goal: Optional[Mapping[str, object]] = None,
    camera_travel_goal: Optional[Mapping[str, object]] = None,
    camera_clock_ms: Optional[int] = None,
    live_hud_observation: Optional[Mapping[str, object]] = None,
    requested_hud_panel: Optional[str] = None,
    requested_hud_target: Optional[str] = None,
    scenery_observation: Optional[Mapping[str, object]] = None,
    scenery_registry: Optional[Mapping[str, object]] = None,
    prior_career_state: Optional[Mapping[str, object]] = None,
    aspiration_prompt_active: bool = False,
    aspiration_prompt_id: Optional[str] = None,
    aspiration_prompt_text: str = "",
    aspiration_completion_enabled: bool = False,
    occult_needs_engine_ready: bool = False,
    operator_prefers_aspiration_ok: Optional[bool] = None,
    prior_aspiration_state: Optional[Mapping[str, object]] = None,
    preference_offer: Optional[Mapping[str, object]] = None,
    preference_automation_opt_in: bool = False,
    preference_game_build_confirmed: bool = False,
    balance_level: Optional[str] = None,
    ailment: Optional[str] = None,
    inventory_has_holistic_cure: Optional[bool] = None,
    apothecary_stall_available: bool = False,
    apothecary_skill_level: Optional[int] = None,
    natural_living_meditate_available: bool = False,
    houseplants_available: bool = False,
    prior_balance_state: Optional[Mapping[str, object]] = None,
) -> dict:
    """Compose viewport, moodlets, event-balance, instincts, and dialog gates.

    Viewport anomalies outrank needs actions: do not click world objects while
    PrintWindow is black. See contracts/viewport-black.v1.json.

    When critical needs are off-lot, next_gate becomes MAP_TRAVEL_HOME_FIRST —
    never IN_FRAME_WALK_THRASH (glossary). Moodlets are supplied observations
    (portrait strip); absence is SENSOR_NOT_SUPPLIED — never vision-invented.

    Optional Simology/skills/preferences/whims attach a read-only sim_profile
    (docs/SIM_PROFILE.md); never authorizes practice_skill or BI-005 closure.

    Fun is owned by fun_service (docs/FUN_SERVICE.md); all six motives compose via
    need_services (docs/NEED_SERVICES.md) using shared need_service_base (P124).

    Optional school_day_active / school_goals_incomplete attach High School Years
    top-left goal planning (docs/SCHOOL_DAY.md); homework on premises fails closed.

    Optional homework_pending + teen life_stage / inventory_has_homework attach teen
    career-panel homework budgeting (docs/TEEN_HOMEWORK.md); not BI-006 certification.

    Optional scenario_active / scenario_goals_incomplete attach scenario scoring HUD
    planning (docs/SCENARIO_GOALS.md); career stays horizon-deferred without proof.

    Optional navigating_needs_active / navigating_needs_incomplete attach Discovery
    Quest Navigating Needs tandem (docs/NAVIGATING_NEEDS.md); panel-aligned need
    remedies outrank scenario scoring; uncovered urgent motives fall through to instincts.

    Optional build_objective runs evaluate-only Build/Buy catalog ranking
    (docs/BUILD_OPTIMIZE.md); never paints walls from this pure module.

    Optional lot_model (RECURSIVE_LOT_MODEL) in Build/Buy attaches library-save-before-
    room-mutate, build_spatial enclosure/story classification (inside/outside,
    FLOOR_1/FLOOR_2), and structure-first build_integrity
    (docs/BUILD_LIBRARY_CHECKPOINT.md, docs/BUILD_SPATIAL.md, docs/BUILD_INTEGRITY.md).

    Optional social_prompt_active runs Sims-library occult lookup before invite OK
    (docs/SOCIAL_OPPORTUNITY.md / docs/TEEN_DAY_JOURNEY.md).

    Optional sim_at_school / camera_lot_kind resolve Sim premises vs camera lot.

    Optional cursor_client_* / camera_scan_needed attach camera-safe traverse
    (docs/CAMERA_TRAVERSE.md): edge-park outranks needs clicks; capture-first
    plans replace continuous edge scrolling.
    """
    premises = resolve_sim_premises(
        location_kind=location_kind,
        camera_lot_kind=camera_lot_kind,
        sim_at_school=sim_at_school,
        school_day_active=school_day_active,
    )
    effective_location = premises["effective_location_kind"]
    # P141/P01: physical walking and camera navigation are separate. This
    # advisor is only considered when the caller supplies verified queue and
    # movement-checkpoint observations, never from a camera-panning hint.
    traversal_voi_advice = None
    if traversal_voi_observation is not None:
        if not isinstance(traversal_voi_observation, Mapping):
            raise HostStackError("VOI_OBSERVATION_INVALID")
        voi_snapshot = dict(traversal_voi_observation)
        if voi_snapshot.get("capture_ref") != capture_ref:
            voi_snapshot["queue_verified"] = False
        if player_directed or already_busy:
            voi_snapshot["human_present"] = True
        traversal_voi_advice = evaluate_traversal_voi(
            voi_snapshot, goal=voi_snapshot.get("goal"),
            route=voi_snapshot.get("route"),
        )
    social_opportunity = None
    school_homework_plan = None
    targeted_chat_plan = None
    school_day = None
    navigating_needs = None
    teen_homework = None
    career_service = None
    aspiration_service = None
    # Independent, read-only likes/dislikes judgment; does not take the
    # aspiration life-state lane or authorize host screen control.
    preference_prompt = (
        evaluate_preference_offer(
            preference_offer,
            automation_opt_in=preference_automation_opt_in,
            known_game_build=preference_game_build_confirmed,
            player_directed=player_directed or already_busy,
        )
        if preference_offer is not None else None
    )
    balance_service = None
    scenario = None
    fun_service = None
    need_services = None
    gardening_report = None
    household_upkeep_report = None
    household_economy_report = None
    discovery_report = None
    autonomy_report = None
    valence_report = None
    try:
        if autonomy_observation is not None:
            # This peer is read-only for every domain, not just gardening.
            # Caller-reported "idle" cannot override actual player activity
            # or the active actor's absence.
            auto_input = dict(autonomy_observation)
            if player_directed:
                auto_input["player_active"] = True
            if sim_absent or sim_at_school is True:
                auto_input["selected_sim_ref"] = None
            autonomy_report = evaluate_autonomy_moderation(
                auto_input, capture_ref=capture_ref,
            )
            # A passive observation is never a reviewed training example.
            # Evidence labels and ML predictions occupy different fields.
            auto_input.setdefault("activity_context", "other")
            valence_report = evaluate_behavior_valence(
                auto_input, capture_ref=capture_ref, model=behavior_model,
            )
        if discovery_hud is not None:
            # A verified top-left quest is a typed advisor, not a new UI/input
            # owner. Do not let a stale Build/Buy flag silently become Live.
            supplied = dict(discovery_hud)
            if build_or_buy_mode:
                supplied["mode"] = "BUILD"
            if player_directed:
                supplied["player_active"] = True
            discovery_report = evaluate_discovery_hud(
                supplied, needs=needs, capture_ref=capture_ref,
            )
            if not already_busy and not player_directed:
                state = discovery_report["state"]
                observed_goals = tuple(supplied.get("incomplete_goals") or ())
                if state == "ROUTE_EXISTING_NAVIGATING_NEEDS":
                    if (scenario_active or scenario_goals_incomplete
                            or (navigating_needs_active and
                                tuple(navigating_needs_incomplete) != observed_goals)):
                        raise HostStackError("DISCOVERY_LEGACY_GOAL_CONFLICT")
                    navigating_needs_active = True
                    navigating_needs_incomplete = observed_goals
                elif state == "ROUTE_EXISTING_SCORING_SIMOLEONS":
                    if (navigating_needs_active or navigating_needs_incomplete
                            or (scenario_active and
                                tuple(scenario_goals_incomplete) != observed_goals)):
                        raise HostStackError("DISCOVERY_LEGACY_GOAL_CONFLICT")
                    scenario_active = True
                    scenario_goals_incomplete = observed_goals
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
        whim_labels = list(whims) + [w for w in pinned_whims if w not in whims]
        sim_profile = evaluate_sim_profile(
            sim_name=sim_name,
            life_stage=life_stage,
            traits=traits,
            aspiration=aspiration,
            aspiration_track=aspiration_track,
            skills=skills,
            likes=likes,
            dislikes=dislikes,
            whims=whim_labels,
            emotion=emotion,
            moodlets=moodlets,
            needs=needs,
            capture_ref=capture_ref,
        )
        queue_capacity = evaluate_queue_capacity(
            tuple(queue or ()), multitasking=multitasking, player_directed=player_directed
        )
        if (traversal_voi_advice is not None
                and traversal_voi_observation.get("requested_action_kind") == "WALK"):
            # This restricts only a specifically requested agent Walk. It does
            # not cancel player actions or block the separate domain follow-up.
            queue_capacity = dict(queue_capacity)
            if player_directed or already_busy:
                queue_capacity.update(
                    gate="PLAYER_QUEUE_YIELD" if player_directed else "HOST_BUSY_YIELD",
                    max_new_actions=0, enqueue_allowed=False,
                )
            elif not traversal_voi_advice["sim"]["walk_candidate"]:
                queue_capacity.update(
                    gate="VOI_WALK_DENIED", max_new_actions=0,
                    enqueue_allowed=False,
                )
            else:
                queue_capacity["max_new_actions"] = min(
                    queue_capacity["max_new_actions"], 1
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
        # Observed class-transition homework and target-specific chat wishes are
        # optional read-only ports; existing school/queue and invite owners remain.
        if school_homework_window is not None:
            school_homework_plan = plan_school_homework_window(
                school_homework_window, capture_ref=capture_ref,
                school_phase=school_phase or "morning_free_time",
                school_day_active=school_day_active,
                location_kind=effective_location,
                homework_pending=homework_pending,
                inventory_has_homework=inventory_has_homework,
                queue=tuple(queue or ()), player_directed=player_directed,
                already_busy=already_busy, multitasking=multitasking,
                survival_critical=tuple(n for n in ("hunger", "bladder", "energy")
                                        if needs[n] < 0.35),
            )
        if whim_labels:
            targeted_chat_plan = plan_targeted_chat_whim(
                tuple(whim_labels), tuple(sim_library),
                capture_ref=capture_ref, queue=tuple(queue or ()),
                queued_social_targets=tuple(queued_social_targets),
                player_directed=player_directed, already_busy=already_busy,
                survival_critical=tuple(n for n in ("hunger", "bladder", "energy")
                                        if needs[n] < 0.35),
                multitasking=multitasking,
            )
        if should_attach_social_opportunity(
            social_prompt_active=social_prompt_active,
            prompt_kind=social_prompt_kind,
        ):
            social_opportunity = evaluate_social_opportunity(
                social_prompt_active=social_prompt_active,
                prompt_kind=social_prompt_kind,
                prompt_text=social_prompt_text,
                invitee_name=social_invitee_name,
                sim_library=sim_library,
                lookup_ran=social_lookup_ran,
                occult_status=invitee_occult_status,
                player_directed=player_directed,
                already_busy=already_busy,
                capture_ref=capture_ref,
            )
        if should_attach_career_service(
            homework_pending=homework_pending,
            inventory_has_homework=inventory_has_homework,
            homework_on_lot=homework_on_lot,
            school_day_active=school_day_active,
            school_goals_incomplete=school_goals_incomplete,
            scenario_active=scenario_active,
            scenario_goals_incomplete=scenario_goals_incomplete,
            life_stage=life_stage,
            prior_state=prior_career_state,
        ):
            career_service = evaluate_career_service(
                needs,
                location_kind=effective_location,
                school_day_active=school_day_active,
                school_goals_incomplete=school_goals_incomplete,
                school_phase=school_phase,
                homework_pending=homework_pending,
                inventory_has_homework=inventory_has_homework,
                homework_on_lot=homework_on_lot,
                available_objects=tuple(available_objects or ()),
                sim_at_school=sim_at_school,
                queue=tuple(queue or ()),
                player_directed=player_directed,
                already_busy=already_busy,
                life_stage=life_stage or "teen",
                lot_model=lot_model,
                multitasking=multitasking,
                sim_room_id=sim_room_id,
                sim_seated=sim_seated,
                sim_seat_id=sim_seat_id,
                emotion=emotion,
                lot_traits=lot_traits,
                scenario_active=scenario_active,
                scenario_goals_incomplete=scenario_goals_incomplete,
                pinned_whims=pinned_whims,
                whims=whims,
                prior_state=prior_career_state,
                capture_ref=capture_ref,
            )
        if should_attach_aspiration_service(
            aspiration_prompt_active=aspiration_prompt_active,
            prompt_id=aspiration_prompt_id,
            prompt_text=aspiration_prompt_text,
            prior_state=prior_aspiration_state,
        ):
            aspiration_service = evaluate_aspiration_service(
                aspiration_prompt_active=aspiration_prompt_active,
                prompt_id=aspiration_prompt_id,
                prompt_text=aspiration_prompt_text,
                aspiration_completion_enabled=aspiration_completion_enabled,
                occult_needs_engine_ready=occult_needs_engine_ready,
                player_directed=player_directed,
                already_busy=already_busy,
                operator_prefers_ok=operator_prefers_aspiration_ok,
                prior_state=prior_aspiration_state,
                capture_ref=capture_ref,
            )
        if should_attach_balance_service(
            balance_level=balance_level,
            ailment=ailment,
            prior_state=prior_balance_state,
        ):
            balance_service = evaluate_balance_service(
                needs,
                balance_level=balance_level,
                ailment=ailment,
                emotion=emotion,
                moodlets=moodlets,
                inventory_has_holistic_cure=inventory_has_holistic_cure,
                apothecary_stall_available=apothecary_stall_available,
                apothecary_skill_level=apothecary_skill_level,
                natural_living_meditate_available=natural_living_meditate_available,
                houseplants_available=houseplants_available,
                available_objects=tuple(available_objects or ()),
                player_directed=player_directed,
                already_busy=already_busy,
                prior_state=prior_balance_state,
                capture_ref=capture_ref,
            )
        if should_attach_teen_homework(
            homework_pending=homework_pending,
            inventory_has_homework=inventory_has_homework,
            life_stage=life_stage,
        ):
            teen_homework = evaluate_teen_homework_turn(
                needs,
                location_kind=effective_location,
                school_day_active=school_day_active,
                homework_pending=homework_pending,
                inventory_has_homework=inventory_has_homework,
                homework_on_lot=homework_on_lot,
                available_objects=tuple(available_objects or ()),
                sim_at_school=sim_at_school,
                queue=tuple(queue or ()),
                player_directed=player_directed,
                already_busy=already_busy,
                life_stage=life_stage or "teen",
                lot_model=lot_model,
                multitasking=multitasking,
                sim_room_id=sim_room_id,
                sim_seated=sim_seated,
                sim_seat_id=sim_seat_id,
                emotion=emotion,
                lot_traits=lot_traits,
                capture_ref=capture_ref,
            )
        if school_day_active or school_goals_incomplete or (
            homework_pending and effective_location == "school"
        ) or (
            homework_pending
            and effective_location == "home"
            and not (teen_homework and teen_homework.get("owns_home_homework"))
        ) or sim_at_school is True:
            school_day = evaluate_school_day_turn(
                needs,
                school_day_active=school_day_active or bool(school_goals_incomplete),
                school_goals_incomplete=school_goals_incomplete,
                school_phase=school_phase or "morning_free_time",
                location_kind=location_kind,
                camera_lot_kind=camera_lot_kind,
                sim_at_school=sim_at_school,
                homework_pending=homework_pending,
                pinned_whims=pinned_whims or whim_labels,
                queue=tuple(queue or ()),
                player_directed=player_directed,
                already_busy=already_busy,
                school_profile=school_profile,
                capture_ref=capture_ref,
            )
        if scenario_active or scenario_goals_incomplete:
            scenario = evaluate_scenario_turn(
                needs,
                scenario_active=scenario_active or bool(scenario_goals_incomplete),
                scenario_goals_incomplete=scenario_goals_incomplete,
                scenario_profile=scenario_profile,
                school_day_active=school_day_active or bool(school_goals_incomplete),
                allow_career=allow_career,
                needs_game_certified=needs_game_certified,
                income_game_observed=income_game_observed,
                queue=tuple(queue or ()),
                player_directed=player_directed,
                already_busy=already_busy,
                capture_ref=capture_ref,
            )
        if navigating_needs_active or navigating_needs_incomplete:
            navigating_needs = evaluate_navigating_needs_turn(
                needs,
                navigating_needs_active=navigating_needs_active
                or bool(navigating_needs_incomplete),
                navigating_needs_incomplete=navigating_needs_incomplete,
                quest_profile=navigating_needs_profile,
                school_day_active=school_day_active or bool(school_goals_incomplete),
                build_or_buy_mode=build_or_buy_mode,
                queue=tuple(queue or ()),
                player_directed=player_directed,
                already_busy=already_busy,
                capture_ref=capture_ref,
            )
        if event_active or outdoor_social_prefix or (
            homework_pending
            and not (school_day_active or effective_location == "school" or sim_at_school is True)
        ):
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
        event_fun_via = bool(
            event_balance is not None and event_balance.get("gate") == "EVENT_FUN_VIA_GOALS"
        )
        if gardening is not None or should_attach_need_services(needs, guests_present=guests_present):
            need_services = evaluate_need_services(
                needs,
                available_objects=tuple(available_objects or ()),
                occupied_objects=tuple(occupied_objects or ()),
                guests_present=guests_present,
                emotion=emotion,
                moodlets=moodlets,
                life_stage=life_stage or "young_adult",
                traits=traits,
                queue=tuple(queue or ()),
                player_directed=player_directed,
                already_busy=already_busy,
                event_active=event_active,
                event_fun_via_goals=event_fun_via,
                sibling_lane_claims={"fun": tuple(sibling_fun_lane_claims or ())},
                failure_signals=need_failure_signals,
                capture_ref=capture_ref,
            )
            fun_service = (need_services.get("services") or {}).get("fun")
        elif should_attach_fun_service(needs, guests_present=guests_present):
            fun_service = evaluate_fun_service(
                needs,
                available_objects=tuple(available_objects or ()),
                occupied_objects=tuple(occupied_objects or ()),
                guests_present=guests_present,
                emotion=emotion,
                moodlets=moodlets,
                life_stage=life_stage or "young_adult",
                traits=traits,
                queue=tuple(queue or ()),
                player_directed=player_directed,
                already_busy=already_busy,
                event_active=event_active,
                event_fun_via_goals=event_fun_via,
                sibling_lane_claims=tuple(sibling_fun_lane_claims or ()),
                capture_ref=capture_ref,
            )
        if gardening is not None:
            gardening_report = evaluate_gardening_turn(
                needs, need_services, gardening, capture_ref=capture_ref,
                player_directed=player_directed, already_busy=already_busy,
                sim_absent=sim_absent or sim_at_school is True,
                build_or_buy_mode=build_or_buy_mode,
                school_day_active=school_day_active,
                homework_pending=homework_pending,
            )
        if household_economy is not None:
            # Independent verified household roster/tasks, no new game authority.
            # Existing needs, upkeep and career planners retain their owners.
            if ("selected_member_key" in household_economy
                    and household_economy.get("capture_ref") != capture_ref):
                raise HouseholdEconomyError("HOUSEHOLD_HANDOFF_CAPTURE_MISMATCH")
            household_economy_report = evaluate_household_economy(household_economy)
        if household_upkeep is not None:
            _, needs_floor = threshold_pair()
            household_upkeep_report = evaluate_household_upkeep(
                household_upkeep, capture_ref=capture_ref,
                player_directed=player_directed,
                already_busy=already_busy or sim_absent or sim_at_school is True,
                build_or_buy_mode=build_or_buy_mode,
                human_survival_hold=any(v < needs_floor for v in needs.values()),
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
        TeenHomeworkError,
        QueueCapacityError,
        CareerServiceError,
        AspirationServiceError,
        BalanceServiceError,
        SchoolDayError,
        SocialOpportunityError,
        OpportunisticActionError,
        FunServiceError,
        NeedServicesError,
        NavigatingNeedsError,
        GardeningServiceError,
        HouseholdUpkeepError,
        HouseholdEconomyError,
        DiscoveryHudError,
        AutonomyModerationError,
        BehaviorValenceError,
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
                include_pools=True,
                capture_ref=capture_ref,
            )
        except BuildOptimizeError as exc:
            raise HostStackError(str(exc)) from exc

    build_integrity = None
    build_spatial = None
    build_library = None
    if build_or_buy_mode and lot_model is not None:
        try:
            build_library = plan_library_save_if_required(lot_model)
            build_spatial = {
                "inventory": inventory_spatial(lot_model),
                "order": build_order_plan(lot_model),
            }
            build_integrity = structure_restore_plan(lot_model)
        except (BuildIntegrityError, BuildSpatialError, BuildLibraryCheckpointError) as exc:
            raise HostStackError(str(exc)) from exc

    lot_floor_map = None
    if build_or_buy_mode and lot_floor_profile_id and lot_floor_key:
        try:
            from betterinstincts.installation_profiles import InstallationProfileError
            from betterinstincts.lot_floor_map import LotFloorMapError, on_build_mode_entered

            lot_floor_map = on_build_mode_entered(
                profile_id=str(lot_floor_profile_id),
                lot_key=str(lot_floor_key),
            )
        except (LotFloorMapError, InstallationProfileError, OSError, ValueError) as exc:
            lot_floor_map = {
                "state": "FLOOR_MAP_TRIGGER_FAILED",
                "error": str(exc),
                "execute_allowed": False,
                "proof_ceiling": "PROFILE_FLOOR_MAP_OFFLINE_AND_LOCAL_STORE_NOT_LIVE_OBJECT_HIT_CERT",
            }

    drift_recovery = None
    if camera_recovery is not None:
        if not isinstance(camera_recovery, Mapping):
            raise HostStackError("CAMERA_RECOVERY_REQUEST_INVALID")
        try:
            drift_recovery = assess_drift_recovery(
                target_kind=camera_recovery.get("target_kind"),
                capture_ref=capture_ref,
                observation=camera_recovery.get("observation"),
                client_width=client_width,
                client_height=client_height,
                target_id=camera_recovery.get("target_id"),
                world_target_observation=camera_recovery.get("world_target_observation"),
                reframe_directions=camera_recovery.get("reframe_directions", ()),
                sim_camera_observation=sim_camera_observation,
                continuous_follow=camera_recovery.get("continuous_follow", False),
            )
        except (CameraTraverseError, TypeError) as exc:
            raise HostStackError(str(exc)) from exc

    sim_camera_intent = None
    if sim_camera_command is not None:
        try:
            sim_camera_intent = plan_sim_camera(
                sim_camera_command,
                capture_ref=capture_ref,
                observation=sim_camera_observation,
            )
        except (SimCameraError, TypeError) as exc:
            raise HostStackError(str(exc)) from exc

    target_framing = None
    needs_floor_map = None
    if world_target is not None:
        if not isinstance(world_target, Mapping):
            raise HostStackError("WORLD_TARGET_REQUEST_INVALID")
        try:
            target_framing = assess_world_target(
                target_id=world_target.get("target_id"),
                capture_ref=capture_ref,
                observation=world_target.get("observation"),
                client_width=client_width,
                client_height=client_height,
                reframe_directions=world_target.get("reframe_directions", ()),
            )
        except (CameraTraverseError, TypeError) as exc:
            raise HostStackError(str(exc)) from exc
        # New, optional evidence-only continuity gate. Unlike fixed UI hitboxes,
        # world-object highlights are camera- and capture-revision-bound. An
        # absent/changed highlight must revoke an otherwise valid pixel target.
        # This never grants click authority; legacy callers without frames
        # retain their existing independent camera/lot/player protections.
        if "highlight_frames" in world_target:
            from betterinstincts.world_traversal_learning import (
                WorldTraversalLearningError, assess_highlight_continuity,
            )
            target_observation = world_target.get("observation")
            expected_revision = (
                target_observation.get("camera_revision")
                if isinstance(target_observation, Mapping) else None
            )
            try:
                highlight = assess_highlight_continuity(
                    target_id=world_target.get("target_id"),
                    frames=world_target["highlight_frames"],
                    capture_ref=capture_ref, camera_revision=expected_revision,
                )
            except (WorldTraversalLearningError, TypeError) as exc:
                raise HostStackError("WORLD_HIGHLIGHT_EVIDENCE_INVALID:" + str(exc)) from exc
            target_framing["highlight_tracking"] = highlight
            if not highlight["highlight_locked"]:
                target_framing["click_ready"] = False
                target_framing["click_candidate"] = None
                # A stronger camera framing block remains stronger; when the
                # object was already framed, revoke its admission candidate.
                if target_framing["gate"] == "WORLD_TARGET_AWAIT_HOST_ADMISSION":
                    target_framing["state"] = "WORLD_TARGET_NOT_CLICK_READY"
                    target_framing["gate"] = "WORLD_HIGHLIGHT_REACQUIRE_REQUIRED"
                    target_framing["reason"] = highlight["state"]
        # Opportunistic floor map while investigating a needs/world object —
        # preferred continuous path vs Build T sampling sprints.
        if lot_floor_profile_id and lot_floor_key and world_target.get("target_id"):
            try:
                from betterinstincts.installation_profiles import InstallationProfileError
                from betterinstincts.lot_floor_map import (
                    LotFloorMapError,
                    opportunistic_needs_map,
                )

                obs = world_target.get("observation")
                if isinstance(obs, Mapping) and not obs.get("capture_ref"):
                    obs = dict(obs)
                    obs["capture_ref"] = capture_ref
                needs_floor_map = opportunistic_needs_map(
                    profile_id=str(lot_floor_profile_id),
                    lot_key=str(lot_floor_key),
                    target_id=str(world_target.get("target_id")),
                    observation=obs if isinstance(obs, Mapping) else None,
                    need_id=(
                        str(world_target["need_id"])
                        if world_target.get("need_id") is not None
                        else None
                    ),
                    kind=(
                        str(world_target["object_kind"])
                        if world_target.get("object_kind") is not None
                        else None
                    ),
                    expected_interactions=world_target.get("expected_interactions"),
                    observed_interactions=world_target.get("observed_interactions"),
                )
            except (LotFloorMapError, InstallationProfileError, OSError, ValueError, TypeError) as exc:
                needs_floor_map = {
                    "state": "NEEDS_MAP_TRIGGER_FAILED",
                    "error": str(exc),
                    "execute_allowed": False,
                    "proof_ceiling": "PROFILE_FLOOR_MAP_OFFLINE_AND_LOCAL_STORE_NOT_LIVE_OBJECT_HIT_CERT",
                }

    # The overlay/panel microsystem shares capture and selected-Sim revisions.
    # A resolved event is not a permit to resume an unverified queued action.
    live_hud = None
    if live_hud_observation is not None:
        try:
            live_hud = assess_live_hud(
                capture_ref=capture_ref, observation=live_hud_observation,
                requested_panel=requested_hud_panel,
                requested_target=requested_hud_target,
                needs=needs,
                chance_event_observation=live_hud_observation.get("chance_event_observation"),
                chance_event_memo=live_hud_observation.get("chance_event_memo"),
            )
        except (SceneUISemanticsError, TypeError) as exc:
            raise HostStackError(str(exc)) from exc

    scenery_receipt = None
    if scenery_observation is not None:
        try:
            scenery_receipt = record_scenery(
                scenery_registry or {
                    "schema": "betterinstincts.scenery-discoveries/v1",
                    "records": [],
                },
                capture_ref=capture_ref, observation=scenery_observation,
            )
        except (SceneryMemoryError, TypeError) as exc:
            raise HostStackError(str(exc)) from exc

    # Bind all agent camera movements to active-Sim ownership. A generic
    # camera scan is NOT an exception without a named, fresh goal lease.
    camera_lock = None
    camera_navigation_requested = bool(
        camera_scan_needed or camera_pan_directions or
        (world_target is not None and world_target.get("reframe_directions"))
    )
    if camera_navigation_requested or (
        sim_camera_observation is not None and sim_camera_command is None
    ):
        camera_directions = camera_pan_directions or (
            world_target.get("reframe_directions", ()) if world_target else ()
        )
        try:
            camera_lock = evaluate_active_sim_camera_lock(
                capture_ref=capture_ref, observation=sim_camera_observation,
                map_requested=camera_navigation_requested,
                map_goal=camera_map_goal, directions=camera_directions,
                zoom_intent=camera_zoom_intent,
                planning_goal=camera_planning_goal,
                travel_goal=camera_travel_goal,
                now_ms=camera_clock_ms,
            )
        except (SimCameraError, CameraTraverseError, TypeError) as exc:
            raise HostStackError(str(exc)) from exc

    lot_focus = None
    lot_focus_observation = sim_camera_observation
    if lot_focus_observation is None and isinstance(camera_recovery, Mapping):
        rec_obs = camera_recovery.get("observation")
        if isinstance(rec_obs, Mapping):
            lot_focus_observation = rec_obs
    if isinstance(lot_focus_observation, Mapping):
        lot_focus_observation = stamp_host_capture_game_version(lot_focus_observation)
    if should_assess_lot_focus(
        observation=lot_focus_observation if isinstance(lot_focus_observation, Mapping) else None,
        camera_recovery=camera_recovery if isinstance(camera_recovery, Mapping) else None,
    ):
        try:
            lot_focus = assess_lot_focus(
                capture_ref=capture_ref,
                observation=lot_focus_observation,
                travel_goal=camera_travel_goal,
            )
        except (LotFocusError, SimCameraError, TypeError) as exc:
            raise HostStackError(str(exc)) from exc

    off_intent_view = None
    if isinstance(lot_focus_observation, Mapping) and (
        lot_focus_observation.get("intended_world_object_click") is True
        or lot_focus_observation.get("click_intent")
        or lot_focus_observation.get("assess_off_intent_view") is True
    ):
        off_intent_view = assess_off_intent_view(observation=lot_focus_observation)
        if off_intent_view.get("triggered") and isinstance(lot_focus, dict):
            lot_focus = {
                **lot_focus,
                "off_intent_view": off_intent_view,
                "gate": off_intent_view.get("gate") or lot_focus.get("gate"),
            }

    # Pointer context is an optional observed phase, never a control permit.
    # Player-directed work always owns the cursor even if an agent supplied
    # a contradictory context flag.
    pointer_context = camera_pointer_context or {}
    if camera_pointer_context is not None:
        if not isinstance(camera_pointer_context, Mapping) or len(str(dict(camera_pointer_context))) > 2048:
            raise HostStackError("CAMERA_POINTER_CONTEXT_INVALID")
        if cursor_client_x is None or cursor_client_y is None:
            raise HostStackError("CAMERA_POINTER_CONTEXT_REQUIRES_CURSOR")
        if set(camera_pointer_context) - {"phase", "target_kind", "target_verified", "player_owned"}:
            raise HostStackError("CAMERA_POINTER_CONTEXT_UNKNOWN_FIELD")
    camera_traverse = None
    try:
        camera_traverse = evaluate_cursor_risk(
            cursor_client_x=cursor_client_x,
            cursor_client_y=cursor_client_y,
            client_width=client_width,
            client_height=client_height,
            edge_band_px=edge_band_px,
            interaction_phase=pointer_context.get("phase", "REST"),
            target_kind=pointer_context.get("target_kind"),
            target_verified=pointer_context.get("target_verified", False),
            player_owned=player_directed or pointer_context.get("player_owned", False),
            camera_scan_needed=camera_scan_needed,
            directions=camera_pan_directions,
        )
    except CameraTraverseError as exc:
        raise HostStackError(str(exc)) from exc

    # P00/P01 live-host-ops: chat corrections are incomplete until this contract fires.
    live_host_ops = None
    edge_creek = None
    try:
        lho_cfg = load_live_host_ops()
        obs = lot_focus_observation if isinstance(lot_focus_observation, Mapping) else {}
        scenery_tokens: list[str] = []
        raw_tokens = obs.get("scenery_tokens") if isinstance(obs, Mapping) else None
        if isinstance(raw_tokens, (list, tuple)):
            scenery_tokens = [str(t) for t in raw_tokens]
        elif isinstance(lot_focus, Mapping):
            state = str(lot_focus.get("state") or "")
            if "WATER" in state or "CANAL" in state:
                scenery_tokens.append("CANAL")
            if "STREET" in state:
                scenery_tokens.append("STREET")
            if state.startswith("OFF_LOT"):
                scenery_tokens.append("OFF_LOT")
        cursor_edge = bool(
            isinstance(camera_traverse, Mapping)
            and camera_traverse.get("gate") == "CAMERA_SAFE_REST"
        )
        buy_after = bool(
            isinstance(obs, Mapping)
            and (
                obs.get("buy_catalog_open") is True
                or obs.get("build_buy_open") is True
            )
        )
        edge_creek = assess_edge_creek_regression(
            cursor_in_edge_band=cursor_edge,
            scenery_tokens=scenery_tokens,
            buy_catalog_open_after_world_click=buy_after,
        )
        # Keep live_host_ops assess_edge_creek_flag aligned for policy consumers.
        edge_flag = assess_edge_creek_flag(
            cursor_in_edge_band=cursor_edge,
            scenery_tokens=scenery_tokens,
            cfg=lho_cfg,
        )
        parts_open = bool(isinstance(obs, Mapping) and obs.get("parts_gate_open") is True)
        queue_incomplete = bool(
            isinstance(obs, Mapping) and obs.get("household_queue_incomplete") is True
        )
        paused_verified = bool(
            not isinstance(obs, Mapping) or obs.get("paused_verified", True) is not False
        )
        unpause = assess_unpause_admission(
            parts_gate_open=parts_open,
            household_queue_incomplete=queue_incomplete,
            paused_verified=paused_verified,
            cfg=lho_cfg,
        )
        world_xy = None
        if isinstance(obs, Mapping) and obs.get("world_target_kind"):
            world_xy = assess_world_xy_policy(
                target_kind=str(obs.get("world_target_kind")),
                using_hardcoded_field_xy=bool(obs.get("using_hardcoded_field_xy")),
                target_visible_in_fresh_capture=bool(
                    obs.get("target_visible_in_fresh_capture")
                ),
                cfg=lho_cfg,
            )
        live_host_ops = {
            "architecture": lho_cfg["architecture"]["selected"],
            "priority_order": live_host_priority_order(lho_cfg),
            "unpause_admission": unpause,
            "edge_creek_regression": edge_creek,
            "edge_creek_flag": edge_flag,
            "world_xy_policy": world_xy,
            "owners": lho_cfg.get("owners"),
            "proof_ceiling": lho_cfg.get("proof_ceiling"),
        }
    except LiveHostOpsError as exc:
        live_host_ops = {
            "error": str(exc),
            "proof_ceiling": "LIVE_HOST_OPS_CONTRACT_LOAD_FAILED",
        }

    # Lot FOOTPRINT / BOUNDARY: street/asphalt/neighbor are not the house.
    lot_boundary = None
    world_click_footprint = None
    try:
        lot_boundary = assess_lot_boundary(
            observation=lot_focus_observation if isinstance(lot_focus_observation, Mapping) else None,
            lot_focus=lot_focus if isinstance(lot_focus, Mapping) else None,
        )
        if isinstance(lot_focus_observation, Mapping) and lot_focus_observation.get(
            "proposed_world_click_xy"
        ):
            xy = lot_focus_observation.get("proposed_world_click_xy")
            world_click_footprint = admit_world_click_in_footprint(
                client_xy=xy if isinstance(xy, (list, tuple)) else (0, 0),
                observation=lot_focus_observation,
                lot_focus=lot_focus if isinstance(lot_focus, Mapping) else None,
                click_zone=str(lot_focus_observation.get("proposed_click_zone") or "UNKNOWN"),
            )
    except LotBoundaryError as exc:
        lot_boundary = {
            "error": str(exc),
            "admit_world_clicks": False,
            "proof_ceiling": "LOT_BOUNDARY_CONTRACT_LOAD_FAILED",
        }

    # Priority: viewport > camera edge-park > player > survival/event > map travel > decision > needs.
    next_gate = "EXECUTE_INSTINCTS_PLAN"
    fallback = None
    if (
        isinstance(world_click_footprint, Mapping)
        and world_click_footprint.get("admit") is False
        and isinstance(lot_focus_observation, Mapping)
        and lot_focus_observation.get("proposed_world_click_xy") is not None
    ):
        next_gate = str(world_click_footprint.get("gate") or "LOT_BOUNDARY_OUTSIDE_FOOTPRINT")
        fallback = {
            "mechanism": "LOT_BOUNDARY_FOOTPRINT_DENY",
            "owner": "betterinstincts/lot_boundary.py",
            "contract": "contracts/lot-boundary.v1.json",
            "lot_boundary": lot_boundary,
            "world_click_footprint": world_click_footprint,
            "execute_allowed": False,
            "forbidden": list(world_click_footprint.get("forbidden") or []),
            "recovery": list(world_click_footprint.get("recovery") or []),
            "next": world_click_footprint.get("next"),
            "note": "Street/asphalt/neighbor/outside AABB are not house contents — restore ON_LOT before world clicks.",
        }
    elif (
        isinstance(lot_boundary, Mapping)
        and lot_boundary.get("admit_world_clicks") is False
        and isinstance(lot_focus_observation, Mapping)
        and lot_focus_observation.get("require_world_click_admit") is True
    ):
        next_gate = str(lot_boundary.get("gate") or "LOT_BOUNDARY_OUTSIDE_FOOTPRINT")
        fallback = {
            "mechanism": "LOT_BOUNDARY_FOOTPRINT_DENY",
            "owner": "betterinstincts/lot_boundary.py",
            "contract": "contracts/lot-boundary.v1.json",
            "lot_boundary": lot_boundary,
            "execute_allowed": False,
            "forbidden": list(lot_boundary.get("forbidden") or []),
            "recovery": list(lot_boundary.get("recovery") or []),
            "next": lot_boundary.get("next"),
        }
    elif (
        isinstance(live_host_ops, Mapping)
        and isinstance(live_host_ops.get("unpause_admission"), Mapping)
        and live_host_ops["unpause_admission"].get("admit") is False
        and isinstance(lot_focus_observation, Mapping)
        and lot_focus_observation.get("request_unpause") is True
    ):
        next_gate = "PAUSED_PRODUCTIVITY_REQUIRED"
        fallback = {
            "mechanism": "PAUSED_PRODUCTIVITY_BEFORE_TIME_RISK",
            "owner": "betterinstincts/live_host_ops.py",
            "contract": "contracts/live-host-ops.v1.json",
            "unpause_admission": live_host_ops["unpause_admission"],
            "priority_order": live_host_ops.get("priority_order"),
            "execute_allowed": False,
            "forbidden": list(live_host_ops["unpause_admission"].get("forbid") or []),
            "next": live_host_ops["unpause_admission"].get("next"),
        }
    elif viewport is not None and viewport.get("state") != "VIEWPORT_OK":
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
    elif camera_traverse is not None and camera_traverse.get("gate") == "CAMERA_SAFE_REST":
        next_gate = "CAMERA_SAFE_REST"
        fallback = {
            "mechanism": "SAFE_CURSOR_REST",
            "owner": "scripts/camera_traverse.py",
            "contract": "contracts/camera-traverse.v1.json",
            "command": "python -m scripts.camera_traverse rest --session-id SID --process-id PID --execute",
            "safe_rest": camera_traverse.get("safe_rest"),
            "cursor": camera_traverse.get("cursor"),
            "forbidden": [
                "LEAVE_CURSOR_IN_EDGE_BAND",
                "CONTINUOUS_EDGE_HOLD",
                "EDGE_MOUSE_PARK",
                "NEEDS_OBJECT_CLICK",
                "RESUME",
            ],
        }
        if isinstance(edge_creek, Mapping) and edge_creek.get("triggered"):
            next_gate = "EDGE_CREEK_REGRESSION"
            fallback = {
                **fallback,
                "mechanism": "EDGE_MOUSE_PARK_TO_CREEK",
                "edge_creek_regression": edge_creek,
                "recovery_chord": edge_creek.get("recovery_chord"),
                "next": edge_creek.get("next"),
                "forbidden": list(
                    dict.fromkeys(
                        list(fallback.get("forbidden") or [])
                        + list(edge_creek.get("forbidden") or [])
                    )
                ),
                "note": "Oldest regression: edge dwell pans to creek — SAFE_CURSOR_REST then Shift+Enter.",
            }
    elif camera_traverse is not None and camera_traverse.get("gate") == "YIELD_TO_PLAYER":
        next_gate = "RESPECT_PLAYER_OR_BUSY_STATE"
        fallback = None
    elif camera_traverse is not None and camera_traverse.get("gate") in {
        "EDGE_UI_CLICK_HOST_ADMISSION",
        "EDGE_TARGET_REOBSERVE_OR_REFRAME",
        "TRANSIT_MUST_END_AT_SAFE_REST",
    }:
        next_gate = (
            "RESPECT_PLAYER_OR_BUSY_STATE" if (player_directed or already_busy)
            else camera_traverse["gate"]
        )
        fallback = {
            "mechanism": "CAMERA_EDGE_INTERACTION",
            "owner": "betterinstincts/camera_traverse.py",
            "edge_interaction": camera_traverse,
            "execute_allowed": False,
        }
    elif (
        not player_directed
        and not build_or_buy_mode
        and household_economy_report is not None
        and isinstance(household_economy_report.get("work_tone"), Mapping)
        and household_economy_report["work_tone"]["gate"]
            == "WORK_HARD_ADMISSION_REQUIRED"
        and (live_hud is None or live_hud["gate"] == "HUD_CONTEXT_READY")
        and drift_recovery is None
    ):
        # Work tone must be independently admitted and observed before an
        # at-work Sim releases attention. Busy status is normal at work.
        next_gate = "CAREER_WORK_HARD_ADMISSION_REQUIRED"
        fallback = {
            "owner": "betterinstincts/career_service.py",
            "gate": next_gate,
            "work_tone": household_economy_report["work_tone"],
            "next": "REOBSERVE_WORK_TONE_BEFORE_AWAKE_PORTRAIT_HANDOFF",
            "execute_allowed": False,
        }
    elif (
        not player_directed
        and not build_or_buy_mode
        and household_economy_report is not None
        and household_economy_report["portrait_handoff"] is not None
        and (live_hud is None or live_hud["gate"] == "HUD_CONTEXT_READY")
        and drift_recovery is None
    ):
        # The current actor's recovery can set already_busy. The portrait
        # proposal preserves that queue and requires fresh target readback.
        next_gate = "AWAKE_HOUSEHOLD_HANDOFF_READY"
        fallback = {
            "owner": "betterinstincts/household_economy.py",
            "gate": next_gate,
            "portrait_handoff": household_economy_report["portrait_handoff"],
            "execute_allowed": False,
        }
    elif player_directed or already_busy:
        next_gate = "RESPECT_PLAYER_OR_BUSY_STATE"
        if drift_recovery is not None:
            fallback = {
                "mechanism": "CAMERA_DRIFT_RECOVERY",
                "owner": "betterinstincts/camera_traverse.py",
                "recovery": drift_recovery,
                "execute_allowed": False,
            }
    elif live_hud is not None and live_hud["gate"] != "HUD_CONTEXT_READY":
        next_gate = live_hud["gate"]
        fallback = {
            "mechanism": "LIVE_HUD_OVERLAY_AND_PANEL",
            "owner": "betterinstincts/scene_ui_semantics.py",
            "hud": live_hud,
            "execute_allowed": False,
            "forbidden": ["BLIND_EVENT_CLOSE", "CANCEL_PLAYER_ACTION_QUEUE",
                          "REUSE_PRE_OVERLAY_PANEL_HITBOX"],
        }
    elif (scenery_receipt is not None
          and scenery_receipt["record"]["reason"] == "OFF_TARGET"):
        next_gate = "OFF_TARGET_SCENERY_REANCHOR_REQUIRED"
        fallback = {
            "mechanism": "SCENERY_DISCOVERY_AND_REANCHOR",
            "owner": "betterinstincts/scenery_memory.py",
            "scene": scenery_receipt,
            "execute_allowed": False,
            "next": "REOBSERVE_SELECTED_SIM_PORTRAIT_THEN_REVALIDATE_TARGET",
        }
    elif isinstance(off_intent_view, Mapping) and off_intent_view.get("triggered"):
        next_gate = str(off_intent_view.get("gate") or "OFF_INTENT_VIEW_ARM_REQUIRED")
        fallback = {
            "mechanism": "OFF_INTENT_VIEW_ARM",
            "owner": "betterinstincts/lot_focus.py",
            "api": "assess_off_intent_view",
            "off_intent_view": off_intent_view,
            "recovery": off_intent_view.get("recovery"),
            "execute_allowed": False,
            "next": off_intent_view.get("next"),
            "forbidden": list(off_intent_view.get("forbidden") or []),
            "note": "Buy/street after world-object click = MISS_OFF_LOT; Esc(+F1)+Shift+Enter — do not explore Buy.",
        }
    elif lot_focus is not None and lot_focus.get("state") in {
        "OFF_LOT_STREET",
        "OFF_LOT_WATER",
        "TRAVELING_WITH_BANNER",
        "MANAGE_WORLDS_MAP",
        "VIEWPORT_BLACK_OR_WHITE",
    }:
        scenery = lot_focus.get("scenery_focus")
        if scenery == "TRAVELING_WITH_BANNER":
            mechanism = "TRAVEL_PARTY_CANCEL"
        elif scenery == "MANAGE_WORLDS_MAP":
            mechanism = "MANAGE_WORLDS_FOCUS_RESTORE"
        elif scenery == "VIEWPORT_BLACK_OR_WHITE":
            mechanism = "VIEWPORT_RECOVERY_DISTINCT"
        else:
            mechanism = "LOT_OFF_FOCUS_RESTORE"
        next_gate = str(lot_focus.get("gate") or "LOT_OFF_FOCUS_RESTORE_REQUIRED")
        fallback = {
            "mechanism": mechanism,
            "owner": "betterinstincts/lot_focus.py",
            "contract": "contracts/camera-traverse.v1.json#lot_focus",
            "lot_focus": lot_focus,
            "scenery_focus": scenery,
            "recovery": lot_focus.get("recovery"),
            "execute_allowed": False,
            "next": lot_focus.get("next"),
            "forbidden": list(lot_focus.get("forbidden") or [])
            + ["STREET_ROAM", "UNBOUNDED_CAMERA_PAN", "CLICK_VOID", "CROWN", "FOOTPRINT", "SELL"],
        }
    elif drift_recovery is not None:
        # Recovery outranks generic scan/target clicks. Physical actions still
        # pass exact-session + human-idle screen_admit at the native boundary.
        next_gate = "RESPECT_PLAYER_OR_BUSY_STATE" if (player_directed or already_busy) else drift_recovery["gate"]
        fallback = {
            "mechanism": "CAMERA_DRIFT_RECOVERY",
            "owner": "betterinstincts/camera_traverse.py",
            "contract": "contracts/camera-traverse.v1.json",
            "recovery": drift_recovery,
            "execute_allowed": False,
            "next": drift_recovery.get("next_step"),
            "forbidden": [
                "BLIND_WORLD_CLICK", "REUSE_PRE_PAN_TARGET_COORDINATES",
                "UNCALIBRATED_PORTRAIT_RIGHT_CLICK", "AUTO_RECLICK",
            ],
        }
    elif player_directed or already_busy:
        next_gate = "RESPECT_PLAYER_OR_BUSY_STATE"
    elif camera_lock is not None and camera_lock["gate"] != "CAMERA_ACTIVE_SIM_LOCKED":
        # No discretionary camera placement. Restoring the active Sim outranks
        # exploration and ordinary game actions; the only map exception is a
        # fresh named-goal lease with a mandatory admitted return to Enter.
        next_gate = camera_lock["gate"]
        fallback = {
            "mechanism": "ACTIVE_SIM_CAMERA_LOCK",
            "owner": "betterinstincts/active_sim_camera_lock.py",
            "contract": "contracts/camera-traverse.v1.json",
            "camera_lock": camera_lock,
            "execute_allowed": False,
            "forbidden": ["UNBOUNDED_CAMERA_PAN", "AGENT_CHOOSES_CAMERA_VIEW",
                          "MAP_TRAVERSE_WITHOUT_GOAL", "LEAVE_CAMERA_ON_STREET"],
        }
    elif camera_traverse is not None and camera_traverse.get("gate") in {
        "CAMERA_SAFE_TRAVERSE",
        "CAPTURE_BEFORE_EDGE_SCAN",
    }:
        next_gate = str(camera_traverse["gate"])
        traverse_plan = camera_traverse.get("plan") or {}
        fallback = {
            "mechanism": "CAMERA_SAFE_TRAVERSE",
            "owner": "scripts/camera_traverse.py",
            "contract": "contracts/camera-traverse.v1.json",
            "command": traverse_plan.get("command")
            or "python -m scripts.camera_traverse plan --capture-only",
            "steps": traverse_plan.get("steps") or [],
            "forbidden": list(traverse_plan.get("forbidden") or [])
            + ["EDGE_MOUSE_PARK", "CONTINUOUS_EDGE_HOLD", "RESUME"],
        }
    elif player_directed or already_busy:
        next_gate = "RESPECT_PLAYER_OR_BUSY_STATE"
    elif target_framing is not None:
        # A named world target must be framed *before* any host click route.
        # Ready means only that fresh, independent screen admission may begin.
        next_gate = target_framing["gate"]
        fallback = {
            "mechanism": "CAMERA_FIRST_WORLD_TARGET",
            "owner": "betterinstincts/camera_traverse.py",
            "contract": "contracts/camera-traverse.v1.json",
            "target_framing": target_framing,
            "execute_allowed": False,
            "forbidden": ["BLIND_WORLD_CLICK", "AUTO_RECLICK", "REUSE_PRE_PAN_TARGET_COORDINATES"],
        }
    elif sim_camera_intent is not None:
        next_gate = sim_camera_intent["gate"]
        fallback = {
            "mechanism": "SIM_CAMERA_FOCUS_OR_FOLLOW",
            "owner": "betterinstincts/sim_camera.py",
            "input_owner": "contracts/ui-chrome.v1.json",
            "sim_camera": sim_camera_intent,
            "execute_allowed": False,
            "forbidden": ["MOUSE_PORTRAIT_FALLBACK", "REPEAT_CAMERA_FOCUS_LOOP", "FOLLOW_WITH_ENTER"],
        }
    elif social_opportunity is not None and social_opportunity["gate"] == "SOCIAL_LOOKUP_REQUIRED":
        next_gate = "SOCIAL_LOOKUP_REQUIRED"
        fallback = {
            "mechanism": social_opportunity["action"],
            "owner": "betterinstincts/social_opportunity.py",
            "contract": "contracts/social-opportunity.v1.json",
            "invitee_name": social_opportunity.get("invitee_name"),
            "dialog_choice": social_opportunity.get("dialog_choice"),
            "press_ok_allowed": False,
            "next_actions": social_opportunity.get("next_actions") or [],
            "forbidden": [
                "PRESS_OK_BEFORE_SIM_LIBRARY_LOOKUP",
                "VISION_INVENT_OCCULT_STATUS",
                "RESUME",
            ],
        }
    elif social_opportunity is not None and social_opportunity["gate"] in {
        "SOCIAL_LOOKUP_AMBIGUOUS_OR_MISSING",
        "SOCIAL_OCCULT_UNKNOWN",
        "SOCIAL_OCCULT_UNSAFE_HOME_INVITE",
    }:
        next_gate = social_opportunity["gate"]
        fallback = {
            "mechanism": social_opportunity["action"],
            "owner": "betterinstincts/social_opportunity.py",
            "contract": "contracts/social-opportunity.v1.json",
            "invitee_name": social_opportunity.get("invitee_name"),
            "occult_status": social_opportunity.get("occult_status"),
            "lookup": social_opportunity.get("lookup"),
            "dialog_choice": "CANCEL",
            "press_ok_allowed": False,
            "forbidden": [
                "PRESS_OK_WHEN_OCCULT_UNKNOWN",
                "PRESS_OK_WHEN_NAME_AMBIGUOUS",
                "AUTO_ACCEPT_CLASSMATE_INVITE",
                "RESUME",
            ],
        }
    elif social_opportunity is not None and social_opportunity["gate"] == "SOCIAL_OPPORTUNITY_OK_ALLOWED":
        next_gate = "SOCIAL_OPPORTUNITY_OK_ALLOWED"
        fallback = {
            "mechanism": social_opportunity["action"],
            "owner": "betterinstincts/social_opportunity.py",
            "contract": "contracts/social-opportunity.v1.json",
            "invitee_name": social_opportunity.get("invitee_name"),
            "occult_status": social_opportunity.get("occult_status"),
            "lookup": social_opportunity.get("lookup"),
            "dialog_choice": "OK",
            "press_ok_allowed": True,
            "forbidden": ["VISION_INVENT_OCCULT_STATUS", "RESUME"],
        }
    elif aspiration_service is not None and aspiration_service["gate"] in {
        "ASPIRATION_COMPLETION_DISABLED",
        "OCCULT_NEEDS_NOT_READY",
        "ASPIRATION_JUDGE_CANCEL",
        "ASPIRATION_JUDGE_OK",
    }:
        next_gate = str(aspiration_service["gate"])
        fallback = {
            "mechanism": aspiration_service["action"],
            "owner": "betterinstincts/aspiration_service.py",
            "contract": "contracts/aspiration-service.v1.json",
            "prompt": aspiration_service.get("prompt"),
            "dialog_choice": aspiration_service.get("dialog_choice"),
            "press_ok_allowed": bool(aspiration_service.get("press_ok_allowed")),
            "aspiration_completion_enabled": aspiration_service.get(
                "aspiration_completion_enabled"
            ),
            "next_actions": aspiration_service.get("next_actions") or [],
            "forbidden": [
                "AUTO_OK_LIFE_STATE_MUTATION",
                "IGNORE_ASPIRATION_COMPLETION_TOGGLE",
                "REWRITE_NEEDS_VIA_OCCULT_WHILE_BASE_UNREADY",
                "RESUME",
            ],
        }
    elif (
        build_library is not None
        and build_or_buy_mode
        and not player_directed
    ):
        next_gate = str(build_library.get("gate") or "LIBRARY_CHECKPOINT_REQUIRED")
        fallback = {
            "mechanism": "BUILD_LIBRARY_CHECKPOINT",
            "owner": "betterinstincts/build_library_checkpoint.py",
            "contract": "contracts/build-library-checkpoint.v1.json",
            "action": build_library.get("action") or "SCAN_ALL_FLOORS_AND_ROOMS",
            "building_id": build_library.get("building_id"),
            "targets": build_library.get("targets") or [],
            "execute_allowed": False,
            "forbidden": [
                "MUTATE_ROOM_WITHOUT_LIBRARY_SAVE",
                "SLEDGE_WALLS_WITHOUT_LIBRARY_SAVE",
                "TREAT_SAVE_AS_AS_LIBRARY_CHECKPOINT",
                "RESUME",
            ],
            "detail": build_library.get("reason"),
        }
    elif (
        build_spatial is not None
        and (build_spatial.get("order") or {}).get("steps")
        and build_or_buy_mode
        and not player_directed
    ):
        order = build_spatial["order"]
        primary = order.get("primary") or {}
        next_gate = str(order.get("gate") or "BUILD_ORDER_FLOOR1_BEFORE_FLOOR2")
        fallback = {
            "mechanism": "BUILD_SPATIAL_ORDER",
            "owner": "betterinstincts/build_spatial.py",
            "contract": "contracts/build-spatial.v1.json",
            "primary": primary,
            "steps": order.get("steps") or [],
            "inventory": build_spatial.get("inventory"),
            "execute_allowed": False,
            "forbidden": [
                "TREAT_OUTSIDE_AS_INSIDE",
                "BUILD_F2_BEFORE_F1",
                "PLACE_WITH_UNKNOWN_AXES",
                "NEST_OBJECTS",
                "STRIP_KITCHEN_AESTHETIC",
                "RESUME",
            ],
        }
    elif (
        build_integrity is not None
        and build_integrity.get("state") == "STRUCTURE_RESTORE_REQUIRED"
        and build_or_buy_mode
        and not player_directed
    ):
        primary = build_integrity.get("primary") or {}
        next_gate = str(build_integrity.get("gate") or "RESTORE_FLOOR_BEFORE_FURNITURE")
        fallback = {
            "mechanism": "BUILD_INTEGRITY_STRUCTURE_RESTORE",
            "owner": "betterinstincts/build_integrity.py",
            "contract": "contracts/build-integrity.v1.json",
            "primary": primary,
            "steps": build_integrity.get("steps") or [],
            "execute_allowed": False,
            "forbidden": [
                "TREAT_OUTDOOR_AS_INDOOR",
                "PLACE_INDOOR_ON_GRASS",
                "NEST_OBJECTS",
                "STRIP_KITCHEN_AESTHETIC",
                "BULK_SWEEP_STRUCTURE",
                "RESUME",
            ],
        }
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
                "TREAT_OUTDOOR_AS_INDOOR",
                "NEST_OBJECTS",
            ],
        }
    elif sim_absent:
        next_gate = "SIM_ABSENT_HOST_PREP_ONLY"
    elif school_day is not None and school_day["gate"] == "SURVIVAL_NEEDS_CRITICAL":
        next_gate = "SURVIVAL_NEEDS_BEFORE_SCHOOL"
        fallback = {
            "mechanism": "SURVIVAL_NEEDS_CRITICAL",
            "owner": "betterinstincts/school_day.py",
            "contract": "contracts/school-day.v1.json",
            "action": school_day["action"],
            "survival_critical": school_day["survival_critical"],
            "forbidden": ["SCHOOL_GOAL_SPAM_WHILE_STARVING", "RESUME"],
        }
    elif (school_homework_plan is not None
          and school_homework_plan["gate"] in {
              "HOMEWORK_WINDOW_READY", "HOMEWORK_WINDOW_CONTINUE",
          }):
        # Explicit same-capture homework affordance takes precedence over the
        # older school-premises *heuristic*, never over survival/player/class.
        next_gate = school_homework_plan["gate"]
        fallback = {
            "mechanism": school_homework_plan["action"],
            "owner": "betterinstincts/opportunistic_actions.py",
            "contract": "contracts/opportunistic-actions.v1.json",
            "next_actions": school_homework_plan["next_actions"],
            "execute_allowed": False,
            "forbidden": ["CANCEL_GO_TO_CLASS", "BLIND_HOMEWORK_SPAM",
                          "OVERRIDE_PLAYER_QUEUE", "CLAIM_COMPLETION"],
        }
    elif school_day is not None and school_day["gate"] == "SCHOOL_DAY_GOAL_PROGRESS":
        next_gate = "SCHOOL_DAY_GOAL_PROGRESS"
        goal_plan = school_day.get("goal_plan") or {}
        fallback = {
            "mechanism": school_day["action"],
            "owner": "betterinstincts/school_day.py",
            "contract": "contracts/school-day.v1.json",
            "goals_incomplete": school_day.get("goals_incomplete") or [],
            "next_goal": goal_plan.get("next_goal"),
            "next_actions": goal_plan.get("next_actions") or [],
            "primary_route": school_day.get("primary_route") or goal_plan.get("primary_route"),
            "preferred_routes": school_day.get("preferred_routes")
            or goal_plan.get("preferred_routes")
            or [],
            "phase": school_day.get("school_phase"),
            "pinned_whims_matched": (goal_plan.get("pinned_whims_matched") if goal_plan else None) or [],
            "forbidden": [
                "HOMEWORK_DURING_SCHOOL_DAY",
                "HOMEWORK_ON_SCHOOL_PREMISES",
                "ATHLETIC_THRASH_WHILE_NOT_STUMBLE_PINNED",
                "LEAVE_SCHOOL_WHILE_STUDY_GOAL_OPEN",
                "RESUME",
            ],
        }
    elif school_day is not None and school_day["gate"] == "HOMEWORK_PREMISES_BLOCKED":
        next_gate = "HOMEWORK_PREMISES_BLOCKED"
        fallback = {
            "mechanism": school_day["action"],
            "owner": "betterinstincts/school_day.py",
            "contract": "contracts/school-day.v1.json",
            "forbidden": ["HOMEWORK_ON_SCHOOL_PREMISES", "RESUME"],
            "resume_when": ["after_school_at_home", "school_day_ended"],
        }
    elif teen_homework is not None and teen_homework["gate"] == "SURVIVAL_BEFORE_HOMEWORK":
        next_gate = "SURVIVAL_BEFORE_HOMEWORK"
        fallback = {
            "mechanism": teen_homework["action"],
            "owner": "betterinstincts/teen_homework.py",
            "contract": "contracts/teen-homework.v1.json",
            "survival_critical": teen_homework["survival_critical"],
            "forbidden": [
                "SKIP_SURVIVAL_FOR_HOMEWORK",
                "QUEUE_HOMEWORK_WHILE_STARVING",
                "RESUME",
            ],
        }
    elif teen_homework is not None and teen_homework["gate"] == "HOMEWORK_PREMISES_BLOCKED":
        next_gate = "HOMEWORK_PREMISES_BLOCKED"
        fallback = {
            "mechanism": teen_homework["action"],
            "owner": "betterinstincts/teen_homework.py",
            "contract": "contracts/teen-homework.v1.json",
            "forbidden": ["HOMEWORK_ON_SCHOOL_PREMISES", "RESUME"],
            "resume_when": ["after_school_at_home", "school_day_ended"],
        }
    elif teen_homework is not None and teen_homework["gate"] == "HOMEWORK_AFTER_NEEDS_QUEUE":
        next_gate = "HOMEWORK_AFTER_NEEDS_QUEUE"
        fallback = {
            "mechanism": teen_homework["action"],
            "owner": "betterinstincts/teen_homework.py",
            "contract": "contracts/teen-homework.v1.json",
            "forbidden": ["SKIP_NEEDS_QUEUE_FOR_HOMEWORK", "RESUME"],
        }
    elif teen_homework is not None and teen_homework["gate"] == "HOMEWORK_INVENTORY_MISSING":
        next_gate = "HOMEWORK_INVENTORY_MISSING"
        fallback = {
            "mechanism": teen_homework["action"],
            "owner": "betterinstincts/teen_homework.py",
            "contract": "contracts/teen-homework.v1.json",
            "next_actions": teen_homework.get("next_actions") or [],
            "primary_route": teen_homework.get("primary_route"),
            "preferred_routes": teen_homework.get("preferred_routes") or [],
            "forbidden": [
                "VISION_INVENT_INVENTORY",
                "SKIP_TEEN_HOMEWORK_TASK",
                "MOTHERLODE",
                "RESUME",
            ],
        }
    elif teen_homework is not None and teen_homework["gate"] in {
        "HOMEWORK_ALREADY_QUEUED", "HOMEWORK_STUDY_SCAN_REQUIRED",
        "HOMEWORK_QUEUE_CAPACITY_HOLD", "PREPARE_STUDY_LOCATION",
    }:
        next_gate = teen_homework["gate"]
        fallback = {
            "mechanism": teen_homework["action"],
            "owner": "betterinstincts/teen_homework.py",
            "contract": "contracts/teen-homework.v1.json",
            "next_actions": teen_homework.get("next_actions") or [],
            "primary_route": teen_homework.get("primary_route"),
            "study_space": teen_homework.get("study_space"),
            "queue_budget": teen_homework.get("queue_budget"),
            "execute_allowed": False,
            "forbidden": [
                "BLIND_FILL_QUEUE", "QUEUE_HOMEWORK_ON_SIDEWALK",
                "QUEUE_HOMEWORK_WITHOUT_SEAT_PROOF", "RESUME",
            ],
        }
    elif teen_homework is not None and teen_homework["gate"] == "QUEUE_TEEN_HOMEWORK":
        next_gate = "QUEUE_TEEN_HOMEWORK"
        fallback = {
            "mechanism": teen_homework["action"],
            "owner": "betterinstincts/teen_homework.py",
            "contract": "contracts/teen-homework.v1.json",
            "next_actions": teen_homework.get("next_actions") or [],
            "primary_route": teen_homework.get("primary_route"),
            "preferred_routes": teen_homework.get("preferred_routes") or [],
            "forbidden": ["CLAIM_BI006_CLOSURE", "RESUME"],
        }
    elif (targeted_chat_plan is not None and targeted_chat_plan["gate"] in {
        "CHAT_WHIM_ON_LOT_READY", "CHAT_WHIM_RELATIONSHIP_READY",
        "CHAT_WHIM_INVITE_REVIEW", "CHAT_WHIM_TARGET_LOOKUP_REQUIRED",
        "CHAT_WHIM_TARGET_REOBSERVE", "CHAT_WHIM_QUEUE_REOBSERVE",
        "CHAT_WHIM_AFFORDANCE_UNKNOWN", "CHAT_WHIM_MULTIPLE_TARGETS_REVIEW",
    }):
        next_gate = targeted_chat_plan["gate"]
        fallback = {
            "mechanism": targeted_chat_plan["action"],
            "owner": "betterinstincts/opportunistic_actions.py",
            "contract": "contracts/opportunistic-actions.v1.json",
            "target_name": targeted_chat_plan.get("target_name"),
            "target_sim_id": targeted_chat_plan.get("target_sim_id"),
            "next_actions": targeted_chat_plan["next_actions"],
            "execute_allowed": False,
            "forbidden": ["BLIND_RELATIONSHIP_CLICK", "INVITE_UNKNOWN_OCCULT",
                          "CANCEL_PLAYER_QUEUE", "CHAT_UNVERIFIED_TARGET"],
        }
    elif navigating_needs is not None and navigating_needs["gate"] == "BUILD_OR_BUY_YIELD":
        next_gate = "BUILD_OR_BUY_YIELD"
        fallback = {
            "mechanism": navigating_needs["action"],
            "owner": "betterinstincts/navigating_needs.py",
            "contract": "contracts/navigating-needs.v1.json",
            "forbidden": ["FORCE_F1", "NEEDS_OBJECT_CLICK", "RESUME"],
        }
    elif navigating_needs is not None and navigating_needs["gate"] == "NAVIGATING_NEEDS_TANDEM":
        next_gate = "NAVIGATING_NEEDS_TANDEM"
        goal_plan = navigating_needs.get("goal_plan") or {}
        fallback = {
            "mechanism": navigating_needs["action"],
            "owner": "betterinstincts/navigating_needs.py",
            "contract": "contracts/navigating-needs.v1.json",
            "goals_incomplete": navigating_needs.get("goals_incomplete") or [],
            "next_goal": goal_plan.get("next_goal"),
            "next_need": goal_plan.get("next_need"),
            "next_actions": goal_plan.get("next_actions") or [],
            "primary_route": navigating_needs.get("primary_route")
            or goal_plan.get("primary_route"),
            "preferred_routes": navigating_needs.get("preferred_routes")
            or goal_plan.get("preferred_routes")
            or [],
            "forbidden": [
                "INVENT_PANEL_GOALS",
                "IGNORE_PANEL_FOR_UNRELATED_FLUFF",
                "RESUME",
            ],
        }
    elif scenario is not None and scenario["gate"] == "SCENARIO_GOAL_PROGRESS":
        next_gate = "SCENARIO_GOAL_PROGRESS"
        goal_plan = scenario.get("goal_plan") or {}
        fallback = {
            "mechanism": scenario["action"],
            "owner": "betterinstincts/scenario_goals.py",
            "contract": "contracts/scenario-goals.v1.json",
            "goals_incomplete": scenario.get("goals_incomplete") or [],
            "next_goal": goal_plan.get("next_goal"),
            "next_actions": goal_plan.get("next_actions") or [],
            "primary_route": scenario.get("primary_route") or goal_plan.get("primary_route"),
            "preferred_routes": scenario.get("preferred_routes")
            or goal_plan.get("preferred_routes")
            or [],
            "forbidden": [
                "MOTHERLODE_FOR_SCENARIO",
                "REORDER_HORIZON_TO_CAREER_FIRST",
                "RESUME",
            ],
        }
    elif scenario is not None and scenario["gate"] == "SCENARIO_CAREER_DEFERRED":
        next_gate = "SCENARIO_CAREER_DEFERRED"
        fallback = {
            "mechanism": scenario["action"],
            "owner": "betterinstincts/scenario_goals.py",
            "contract": "contracts/scenario-goals.v1.json",
            "career_horizon_blocked": (scenario.get("goal_plan") or {}).get("career_horizon_blocked"),
            "forbidden": [
                "MOTHERLODE_FOR_SCENARIO",
                "FORCE_CAREER_BEFORE_EARN_CRAFT",
                "RESUME",
            ],
            "resume_when": [
                "allow_career",
                "needs_game_certified",
                "income_game_observed",
            ],
        }
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
        # Off-lot critical needs outrank local need-service object plans.
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
        # Active chance-card / decision prompt outranks local need-service plans.
        next_gate = "RESOLVE_DECISION_PROMPT"
    elif gardening_report is None and need_services is not None and need_services["gate"] in {
        "NEED_SERVICES_TANDEM",
        "NEED_SERVICES_LOAD_BALANCE",
    }:
        next_gate = need_services["gate"]
        primary = need_services.get("primary_need")
        fallback = {
            "mechanism": need_services["action"],
            "owner": "betterinstincts/need_services.py",
            "contract": "contracts/need-services.v1.json",
            "lb_contract": "contracts/need-load-balance.v1.json",
            "primary_need": primary,
            "primary_route": need_services.get("primary_route"),
            "preferred_routes": need_services.get("preferred_routes") or [],
            "next_actions": need_services.get("next_actions") or [],
            "parallel_ready_needs": need_services.get("parallel_ready_needs") or [],
            "detached_needs": need_services.get("detached_needs") or [],
            "assumption_windows": need_services.get("assumption_windows") or [],
            "health": need_services.get("health") or {},
            "architecture": need_services.get("architecture"),
            "p95_ground": (need_services.get("load_balance") or {}).get("p95_ground"),
            "forbidden": [
                "REINVENT_NEED_PARSER_PER_AGENT",
                "MONOLITH_SINGLE_QUEUE_FOR_ALL_NEEDS",
                "BACKGROUND_NEED_DAEMON",
                "STICK_TO_DEAD_CALL_STACK",
                "SELECT_UNHEALTHY_AS_PRIMARY",
                "RESUME",
            ],
        }
    elif gardening_report is None and fun_service is not None and fun_service["gate"] in {
        "FUN_SERVICE_PLAN",
        "FUN_SERVICE_BLOCKED",
    }:
        next_gate = fun_service["gate"]
        fallback = {
            "mechanism": fun_service["action"],
            "owner": "betterinstincts/fun_service.py",
            "contract": "contracts/fun-service.v1.json",
            "primary_route": fun_service.get("primary_route"),
            "preferred_routes": fun_service.get("preferred_routes") or [],
            "next_actions": fun_service.get("next_actions") or [],
            "parallel_ready": fun_service.get("parallel_ready") or [],
            "lanes": fun_service.get("lanes") or [],
            "architecture": fun_service.get("architecture"),
            "forbidden": [
                "MONOLITH_SINGLE_FUN_QUEUE_FOR_ALL_SIMS",
                "PILE_ONTO_CONTENDED_TV_OR_COMPUTER",
                "IGNORE_PORTABLE_FUN_WHEN_GUESTS_PRESENT",
                "PLAYFUL_EXCLUSIVE_WITHOUT_PLAYFUL_EMOTION",
                "RESUME",
            ],
        }
    elif risk.get("risk_level") in {"ELEVATED", "HIGH"} and risk.get("required_before_clicks"):
        next_gate = "PRINTWINDOW_ANALYZE_BEFORE_CLICKS"
    elif balance_service is not None and balance_service["gate"] in {
        "READY_HOLISTIC_CURE",
        "READY_NATUROPATH",
        "RECOVERING_NATURE",
    }:
        # After survival/homework/need gates; outranks optional gardening.
        next_gate = str(balance_service["gate"])
        fallback = {
            "mechanism": balance_service["action"],
            "owner": "betterinstincts/balance_service.py",
            "contract": "contracts/balance-service.v1.json",
            "balance_level": balance_service.get("balance_level"),
            "ailment": balance_service.get("ailment"),
            "primary_route": balance_service.get("primary_route"),
            "preferred_routes": balance_service.get("preferred_routes") or [],
            "next_actions": balance_service.get("next_actions") or [],
            "condition": balance_service.get("condition"),
            "forbidden": [
                "INVENT_BALANCE_METER_OR_AILMENT",
                "BALANCE_ACTION_WHILE_SURVIVAL_CRITICAL",
                "CLAIM_PACK_CERT_FROM_OFFLINE_MICROSYSTEM",
                "RESUME",
            ],
        }
    elif (
        household_upkeep_report is not None
        and household_upkeep_report["gate"] == "UPKEEP_ACTION_READY"
        and (
            gardening_report is None
            or gardening_report["gate"] != "GARDEN_ACTION_READY"
            or household_upkeep_report["next_actions"][0]["priority"] <= 3
        )
    ):
        # Preserve cross-domain priorities: live/player/need/career/aspiration
        # gates above; emergency household upkeep before optional garden work.
        next_gate = "UPKEEP_ACTION_READY"
        fallback = {
            "owner": "betterinstincts/household_upkeep.py",
            **household_upkeep_report,
        }
    elif (household_economy_report is not None
          and household_economy_report["gate"] in {
              "COOPERATIVE_ALLOCATION_READY", "SOLO_RESPONSIBILITY_READY",
          }):
        # A voluntary, observed cross-member coordination suggestion only;
        # priority below active player, survival, school, career and upkeep.
        next_gate = household_economy_report["gate"]
        fallback = {
            "owner": "betterinstincts/household_economy.py",
            "contract": "contracts/household-economy.v1.json",
            **household_economy_report,
            "execute_allowed": False,
            "forbidden": ["CANCEL_PLAYER_QUEUE", "EXHAUST_SINGLE_SIM",
                          "UNOBSERVED_INCOME_EFFECT", "AUTO_ASSIGN_UNKNOWN_SIM"],
        }
    elif gardening_report is not None:
        next_gate = gardening_report["gate"]
        fallback = {"owner": "betterinstincts/gardening_service.py", **gardening_report}
    elif discovery_report is not None and discovery_report.get("state") in {
        "PHONE_GOAL_AFFORDANCE_CANDIDATE", "INSPECT_PHONE_AFFORDANCES",
    }:
        # Only after school, needs, manual commands, and existing goals.
        # This is a read-only recommendation, not permission to send/call.
        next_gate = "DISCOVERY_PHONE_REVIEW_ONLY"
        fallback = {
            "owner": "betterinstincts/discovery_hud.py",
            "mechanism": "INSPECT_CURRENT_PHONE_QUEST",
            "quest": discovery_report.get("quest"),
            "next_action": discovery_report.get("next_action"),
            "execute_allowed": False,
            "forbidden": ["SEND_TEXT", "PLACE_CALL", "AUTO_TRAVEL",
                          "BLIND_PHONE_CLICK", "RESUME"],
        }
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
        "queue_capacity": queue_capacity,
        "traversal_voi": traversal_voi_advice,
        "moodlets": moodlet_eval,
        "sim_profile": sim_profile,
        "school_day": school_day,
        "teen_homework": teen_homework,
        "school_homework_window": school_homework_plan,
        "targeted_chat_whim": targeted_chat_plan,
        "career_service": (
            compact_career_service(career_service) if career_service is not None else None
        ),
        "preference_prompt": preference_prompt,
        "aspiration_service": (
            compact_aspiration_service(aspiration_service)
            if aspiration_service is not None
            else None
        ),
        "balance_service": (
            compact_balance_service(balance_service) if balance_service is not None else None
        ),
        "social_opportunity": social_opportunity,
        "sim_premises": premises,
        "scenario": scenario,
        "navigating_needs": navigating_needs,
        "event_balance": event_balance,
        "fun_service": fun_service,
        "need_services": (
            compact_need_services(need_services) if need_services is not None else None
        ),
        "build_optimize": build_optimize,
        "gardening": gardening_report,
        "household_upkeep": household_upkeep_report,
        "household_economy": household_economy_report,
        "discovery_hud": discovery_report,
        "autonomy_moderation": autonomy_report,
        "behavior_valence": valence_report,
        "build_integrity": build_integrity,
        "build_spatial": build_spatial,
        "build_library": build_library,
        "lot_floor_map": lot_floor_map,
        "needs_floor_map": needs_floor_map,
        "camera_traverse": camera_traverse,
        "live_hud_semantics": live_hud,
        "scenery_discovery": scenery_receipt,
        "active_sim_camera_lock": camera_lock,
        "lot_focus": lot_focus,
        "off_intent_view": off_intent_view,
        "live_host_ops": live_host_ops,
        "lot_boundary": lot_boundary,
        "world_click_footprint": world_click_footprint,
        "camera_recovery": drift_recovery,
        "world_target_framing": target_framing,
        "sim_camera": sim_camera_intent,
        "instincts": instincts,
        "decision": decision,
        "influence": influence,
        "viewport": dict(viewport) if viewport else None,
        "viewport_risk": risk,
        "proof_ceiling": "HOST_STACK_OFFLINE_COMPOSITION_NOT_LIVE_PROOF",
    }

