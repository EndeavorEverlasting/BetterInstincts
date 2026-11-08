"""Career microsystem — sticky teen homework obligation beside need services.

Evaluate-only peer to need_services. Delegates READY policy to teen_homework /
school_day / scenario_goals. Never invents inventory, never daemons, never
claims BI-006 certification.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional, Sequence

from betterinstincts.scenario_goals import ScenarioGoalsError, evaluate_scenario_turn
from betterinstincts.school_day import SchoolDayError, evaluate_school_day_turn
from betterinstincts.teen_homework import (
    TeenHomeworkError,
    evaluate_teen_homework_turn,
    should_attach_teen_homework,
    survival_critical,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "career-service.v1.json"
TRACK_HIGH_SCHOOL = "high_school_student"
ACTIVE_STATES = frozenset(
    {
        "TRACKING",
        "SUSPENDED_FOR_SURVIVAL",
        "PREMISES_BLOCKED",
        "READY",
        "YIELDED",
    }
)


class CareerServiceError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 128000:
        raise CareerServiceError("UNSAFE_CAREER_SERVICE_CONTRACT")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CareerServiceError("INVALID_CAREER_SERVICE_JSON") from exc
    if data.get("schema") != "betterinstincts.career-service/v1":
        raise CareerServiceError("INVALID_CAREER_SERVICE_SCHEMA")
    if TRACK_HIGH_SCHOOL not in (data.get("career_tracks") or {}):
        raise CareerServiceError("CAREER_TRACK_HIGH_SCHOOL_MISSING")
    return data


def should_attach_career_service(
    *,
    homework_pending: bool = False,
    inventory_has_homework: Optional[bool] = None,
    homework_on_lot: Optional[bool] = None,
    school_day_active: bool = False,
    school_goals_incomplete: Sequence[str] = (),
    scenario_active: bool = False,
    scenario_goals_incomplete: Sequence[str] = (),
    life_stage: Optional[str] = None,
    prior_state: Optional[Mapping[str, object]] = None,
    force: bool = False,
) -> bool:
    if force:
        return True
    prior = prior_state or {}
    if prior.get("obligation_held") and prior.get("microsystem_state") in ACTIVE_STATES:
        return True
    # Career-panel daily homework is itself enough to attach — do not require
    # life_stage="teen" sensor (agents often omit it and then forget homework).
    if homework_pending:
        return True
    if should_attach_teen_homework(
        homework_pending=homework_pending,
        inventory_has_homework=inventory_has_homework,
        life_stage=life_stage,
    ):
        return True
    if homework_on_lot is not None and homework_pending:
        return True
    if school_day_active or school_goals_incomplete:
        return True
    if scenario_active or scenario_goals_incomplete:
        return True
    return False


def _prior_obligation(prior_state: Optional[Mapping[str, object]]) -> Optional[dict]:
    if not isinstance(prior_state, Mapping):
        return None
    obligation = prior_state.get("obligation")
    if not isinstance(obligation, Mapping):
        return None
    if not prior_state.get("obligation_held"):
        return None
    return {
        "track": str(obligation.get("track") or TRACK_HIGH_SCHOOL),
        "daily_task": str(obligation.get("daily_task") or "homework"),
        "source": str(obligation.get("source") or "prior_career_service"),
        "resume_condition": str(
            obligation.get("resume_condition")
            or "FRESH_SURVIVAL_GREEN_HOME_REVALIDATION"
        ),
    }


def compact_career_service(report: dict, *, max_actions: int = 4) -> dict:
    """Listener/tandem-safe summary."""
    lanes = report.get("lanes") or {}
    compact_lanes = {}
    for key, row in lanes.items():
        if not isinstance(row, dict):
            continue
        compact_lanes[key] = {
            "gate": row.get("gate"),
            "action": row.get("action"),
            "primary_route": row.get("primary_route"),
        }
    return {
        "schema": report.get("schema"),
        "state": report.get("state"),
        "capture_ref": report.get("capture_ref"),
        "gate": report.get("gate"),
        "action": report.get("action"),
        "microsystem_state": report.get("microsystem_state"),
        "obligation_held": report.get("obligation_held"),
        "obligation": report.get("obligation"),
        "career_track": report.get("career_track"),
        "primary_route": report.get("primary_route"),
        "preferred_routes": list(report.get("preferred_routes") or [])[:8],
        "next_actions": list(report.get("next_actions") or [])[:max_actions],
        "findings": list(report.get("findings") or []),
        "lanes": compact_lanes,
        "architecture": report.get("architecture"),
        "proof_ceiling": report.get("proof_ceiling"),
        "compacted": True,
    }


def evaluate_career_service(
    needs: Mapping[str, float],
    *,
    location_kind: str = "unknown",
    school_day_active: bool = False,
    school_goals_incomplete: Sequence[str] = (),
    school_phase: Optional[str] = None,
    homework_pending: bool = False,
    inventory_has_homework: Optional[bool] = None,
    homework_on_lot: Optional[bool] = None,
    available_objects: Sequence[str] = (),
    sim_at_school: Optional[bool] = None,
    queue: Sequence[str] = (),
    player_directed: bool = False,
    already_busy: bool = False,
    life_stage: Optional[str] = None,
    scenario_active: bool = False,
    scenario_goals_incomplete: Sequence[str] = (),
    pinned_whims: Sequence[str] = (),
    whims: Sequence[str] = (),
    prior_state: Optional[Mapping[str, object]] = None,
    capture_ref: str = "capture:career-service",
) -> dict:
    """Evaluate career microsystem for one observation; preserve sticky obligation."""
    cfg = load_contract()
    findings: list[str] = []
    prior_obligation = _prior_obligation(prior_state)
    stage = life_stage or "teen"

    # Explicit completion wins over book metadata / stale prior.
    # homework_pending=False clears even when a book token remains visible.
    if (
        not homework_pending
        and not school_day_active
        and not school_goals_incomplete
        and not scenario_active
        and not scenario_goals_incomplete
    ):
        if prior_obligation and prior_state and prior_state.get("obligation_held"):
            findings.append("CAREER_OBLIGATION_CLEARED_EXPLICIT_COMPLETE")
        return {
            "schema": "betterinstincts.career-service-result/v1",
            "state": "CAREER_SERVICE_EVALUATED",
            "capture_ref": capture_ref,
            "gate": "CAREER_COMPLETE" if prior_obligation else "CAREER_IDLE",
            "action": (
                cfg["call_stack"]["gates"]["CAREER_COMPLETE"]["action"]
                if prior_obligation
                else cfg["call_stack"]["gates"]["CAREER_IDLE"]["action"]
            ),
            "microsystem_state": "COMPLETE" if prior_obligation else "IDLE",
            "obligation_held": False,
            "obligation": None,
            "career_track": None,
            "primary_route": None,
            "preferred_routes": [],
            "next_actions": [],
            "findings": sorted(set(findings)),
            "lanes": {},
            "architecture": "CAREER_MICROSYSTEM_TANDEM_BESIDE_NEEDS",
            "proof_ceiling": cfg["proof_ceiling"],
            "resume_condition": None,
        }

    homework_signal = bool(
        homework_pending
        or inventory_has_homework is False
        or (prior_obligation and prior_obligation.get("daily_task") == "homework")
    )
    track = TRACK_HIGH_SCHOOL if (
        stage == "teen" or homework_signal or school_day_active or school_goals_incomplete
    ) else None
    obligation = None
    if homework_signal or prior_obligation:
        obligation = prior_obligation or {
            "track": TRACK_HIGH_SCHOOL,
            "daily_task": "homework",
            "source": "career_panel_daily_task",
            "resume_condition": "FRESH_SURVIVAL_GREEN_HOME_REVALIDATION",
        }
        findings.append("CAREER_OBLIGATION_HELD")

    lanes: dict[str, dict] = {}
    try:
        if school_day_active or school_goals_incomplete:
            school = evaluate_school_day_turn(
                needs,
                school_day_active=school_day_active or bool(school_goals_incomplete),
                school_goals_incomplete=school_goals_incomplete,
                school_phase=school_phase or "morning_free_time",
                location_kind=location_kind,
                homework_pending=homework_pending,
                pinned_whims=pinned_whims or whims,
                queue=queue,
                capture_ref=capture_ref,
            )
            lanes["school_day"] = {
                "gate": school.get("gate"),
                "action": school.get("action"),
                "primary_route": (school.get("preferred_routes") or [None])[0],
            }
        if homework_signal:
            homework = evaluate_teen_homework_turn(
                needs,
                location_kind=location_kind,
                school_day_active=school_day_active,
                homework_pending=homework_pending or bool(prior_obligation),
                inventory_has_homework=inventory_has_homework,
                homework_on_lot=homework_on_lot,
                available_objects=tuple(available_objects or ()),
                sim_at_school=sim_at_school,
                queue=tuple(queue or ()),
                player_directed=player_directed,
                already_busy=already_busy,
                life_stage=stage,
                capture_ref=capture_ref,
            )
            lanes["teen_homework"] = {
                "gate": homework.get("gate"),
                "action": homework.get("action"),
                "primary_route": homework.get("primary_route"),
                "preferred_routes": list(homework.get("preferred_routes") or []),
                "next_actions": list(homework.get("next_actions") or []),
                "findings": list(homework.get("findings") or []),
            }
        if scenario_active or scenario_goals_incomplete:
            scenario = evaluate_scenario_turn(
                needs,
                scenario_active=scenario_active or bool(scenario_goals_incomplete),
                scenario_goals_incomplete=scenario_goals_incomplete,
                school_day_active=school_day_active,
                queue=queue,
                capture_ref=capture_ref,
            )
            lanes["scenario"] = {
                "gate": scenario.get("gate"),
                "action": scenario.get("action"),
                "primary_route": ((scenario.get("goal_plan") or {}).get("next_goal")),
            }
    except (SchoolDayError, TeenHomeworkError, ScenarioGoalsError) as exc:
        raise CareerServiceError(str(exc)) from exc

    survival = survival_critical(needs) if homework_signal or lanes else []
    homework_lane = lanes.get("teen_homework") or {}

    if player_directed or already_busy:
        microsystem_state = "YIELDED"
        gate = "PLAYER_FIRST_OR_BUSY"
        action = cfg["call_stack"]["gates"]["PLAYER_FIRST_OR_BUSY"]["action"]
        findings.append("PLAYER_FIRST_PRESERVES_CAREER_TRACKING")
        next_actions: list[dict] = []
        preferred: list[str] = []
        primary = None
    elif survival:
        microsystem_state = "SUSPENDED_FOR_SURVIVAL"
        gate = "SUSPENDED_FOR_SURVIVAL"
        action = cfg["call_stack"]["gates"]["SUSPENDED_FOR_SURVIVAL"]["action"]
        findings.append("SURVIVAL_SUSPENDS_CAREER_ACTION_NOT_OBLIGATION")
        next_actions = []
        preferred = []
        primary = None
    elif homework_lane.get("gate") == "HOMEWORK_PREMISES_BLOCKED" or (
        homework_pending and (school_day_active or location_kind == "school" or sim_at_school is True)
    ):
        microsystem_state = "PREMISES_BLOCKED"
        gate = "PREMISES_BLOCKED"
        action = cfg["call_stack"]["gates"]["PREMISES_BLOCKED"]["action"]
        findings.append("CAREER_HELD_OFF_PREMISES")
        next_actions = []
        preferred = []
        primary = None
    elif homework_lane.get("gate") in {
        "QUEUE_TEEN_HOMEWORK",
        "HOMEWORK_INVENTORY_MISSING",
        "HOMEWORK_AFTER_NEEDS_QUEUE",
    }:
        microsystem_state = "READY"
        if prior_obligation and homework_lane.get("gate") != "HOMEWORK_AFTER_NEEDS_QUEUE":
            gate = "CAREER_READY_AFTER_NEEDS"
            action = cfg["call_stack"]["gates"]["CAREER_READY_AFTER_NEEDS"]["action"]
            findings.append("CAREER_RESUMED_AFTER_SURVIVAL_OR_CONTINUITY")
        else:
            gate = "CAREER_SERVICES_TANDEM"
            action = cfg["call_stack"]["gates"]["CAREER_SERVICES_TANDEM"]["action"]
            findings.append("CAREER_TANDEM_READY")
        next_actions = list(homework_lane.get("next_actions") or [])
        preferred = list(homework_lane.get("preferred_routes") or [])
        primary = homework_lane.get("primary_route")
    elif obligation:
        microsystem_state = "TRACKING"
        gate = "CAREER_SERVICES_TANDEM"
        action = cfg["call_stack"]["gates"]["CAREER_SERVICES_TANDEM"]["action"]
        findings.append("CAREER_TRACKING_BESIDE_NEEDS")
        next_actions = []
        preferred = []
        primary = None
    else:
        microsystem_state = "IDLE"
        gate = "CAREER_IDLE"
        action = cfg["call_stack"]["gates"]["CAREER_IDLE"]["action"]
        next_actions = []
        preferred = []
        primary = None

    obligation_held = bool(obligation) and microsystem_state not in {"IDLE", "COMPLETE"}
    return {
        "schema": "betterinstincts.career-service-result/v1",
        "state": "CAREER_SERVICE_EVALUATED",
        "capture_ref": capture_ref,
        "gate": gate,
        "action": action,
        "microsystem_state": microsystem_state,
        "obligation_held": obligation_held,
        "obligation": obligation if obligation_held else None,
        "career_track": track if obligation_held else None,
        "primary_route": primary,
        "preferred_routes": preferred,
        "next_actions": next_actions,
        "findings": sorted(set(findings)),
        "lanes": lanes,
        "survival_critical": list(survival),
        "architecture": "CAREER_MICROSYSTEM_TANDEM_BESIDE_NEEDS",
        "proof_ceiling": cfg["proof_ceiling"],
        "resume_condition": (
            obligation.get("resume_condition") if obligation_held and obligation else None
        ),
    }
