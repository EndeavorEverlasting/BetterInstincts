"""Poll domain microsystems and emit cascading receipts (P124).

Works for human, agent, or deterministic-script observations. Evaluate-only.
Respects need_load_balance detach/windows — does not invent a second needs queue.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional, Sequence

from betterinstincts.budget_eval import BudgetEvalError, evaluate as evaluate_budget
from betterinstincts.navigating_needs import (
    NavigatingNeedsError,
    evaluate_navigating_needs_turn,
)
from betterinstincts.need_service_base import NeedServiceBaseError, normalize_needs
from betterinstincts.need_services import (
    NeedServicesError,
    compact_need_services,
    evaluate_need_services,
    should_attach_need_services,
)
from betterinstincts.scenario_goals import ScenarioGoalsError, evaluate_scenario_turn
from betterinstincts.school_day import SchoolDayError, evaluate_school_day_turn
from betterinstincts.sim_profile import SimProfileError, SkillInput, evaluate_sim_profile
from betterinstincts.social_opportunity import (
    SocialOpportunityError,
    evaluate_social_opportunity,
    should_attach_social_opportunity,
)
from betterinstincts.teen_homework import TeenHomeworkError, evaluate_teen_homework_turn

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "domain-cascade.v1.json"
class DomainCascadeError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 128000:
        raise DomainCascadeError("UNSAFE_DOMAIN_CASCADE_CONTRACT")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DomainCascadeError("INVALID_DOMAIN_CASCADE_JSON") from exc
    if data.get("schema") != "betterinstincts.domain-cascade/v1":
        raise DomainCascadeError("INVALID_DOMAIN_CASCADE_SCHEMA")
    if list(data.get("cascade_order") or []) != [
        "needs",
        "budget",
        "career",
        "skills_whims",
        "relationships",
    ]:
        raise DomainCascadeError("DOMAIN_CASCADE_ORDER_DRIFT")
    return data


def _needs(raw: Mapping[str, float]) -> dict[str, float]:
    """Reuse P124 need_service_base — do not fork six-need parsing here."""
    try:
        return normalize_needs(raw)
    except NeedServiceBaseError as exc:
        raise DomainCascadeError(str(exc)) from exc


def _receipt(domain: str, *, gate: str, action: str, payload: Optional[dict] = None, findings: Sequence[str] = ()) -> dict:
    return {
        "domain": domain,
        "gate": gate,
        "action": action,
        "findings": sorted(set(findings)),
        "payload": payload or {},
    }


def poll_cascade(
    needs: Mapping[str, float],
    *,
    available_objects: Sequence[str] = (),
    occupied_objects: Sequence[str] = (),
    guests_present: bool = False,
    player_directed: bool = False,
    already_busy: bool = False,
    funds: Optional[float] = None,
    owned_objects: Optional[Sequence[str]] = None,
    school_day_active: bool = False,
    school_goals_incomplete: Sequence[str] = (),
    school_phase: Optional[str] = None,
    homework_pending: bool = False,
    inventory_has_homework: Optional[bool] = None,
    homework_on_lot: Optional[bool] = None,
    location_kind: str = "home",
    life_stage: Optional[str] = None,
    scenario_active: bool = False,
    scenario_goals_incomplete: Sequence[str] = (),
    navigating_needs_active: bool = False,
    navigating_needs_incomplete: Sequence[str] = (),
    build_or_buy_mode: bool = False,
    emotion: Optional[str] = None,
    moodlets: Sequence[str] = (),
    traits: Sequence[str] = (),
    whims: Sequence[str] = (),
    pinned_whims: Sequence[str] = (),
    skills: Sequence[SkillInput] = (),
    likes: Sequence[str] = (),
    dislikes: Sequence[str] = (),
    social_prompt_active: bool = False,
    social_prompt_kind: str = "invite_over",
    social_prompt_text: str = "",
    social_invitee_name: Optional[str] = None,
    sim_library: Sequence[Mapping[str, object]] = (),
    social_lookup_ran: bool = False,
    invitee_occult_status: Optional[str] = None,
    failure_signals: Optional[Mapping[str, Sequence[str]]] = None,
    queue: Sequence[str] = (),
    capture_ref: str = "capture:domain-cascade",
) -> dict:
    """Poll domains in cascade order; each receipt may cite prior receipts."""
    cfg = load_contract()
    snap = _needs(needs)
    receipts: list[dict] = []
    findings: list[str] = []

    if player_directed or already_busy:
        receipts.append(
            _receipt(
                "needs",
                gate="PLAYER_FIRST_OR_BUSY",
                action="YIELD_OR_EMULATE_ONLY",
                findings=["PLAYER_FIRST_HALTS_CASCADE"],
            )
        )
        return {
            "schema": "betterinstincts.domain-cascade-result/v1",
            "state": "DOMAIN_CASCADE_YIELDED",
            "capture_ref": capture_ref,
            "gate": "PLAYER_FIRST_OR_BUSY",
            "action": "HALT_CASCADE",
            "receipts": receipts,
            "prior_receipts_visible": True,
            "proof_ceiling": cfg["proof_ceiling"],
            "architecture": "DOMAIN_CASCADE_POLL_BUS",
        }

    # --- needs (+ navigating advisory + LB) ---
    needs_payload: dict = {}
    navigating = None
    try:
        if navigating_needs_active or navigating_needs_incomplete:
            navigating = evaluate_navigating_needs_turn(
                snap,
                navigating_needs_active=navigating_needs_active
                or bool(navigating_needs_incomplete),
                navigating_needs_incomplete=navigating_needs_incomplete,
                build_or_buy_mode=build_or_buy_mode,
                school_day_active=school_day_active,
                queue=queue,
                player_directed=False,
                already_busy=False,
                capture_ref=capture_ref,
            )
            needs_payload["navigating_needs"] = {
                "gate": navigating.get("gate"),
                "action": navigating.get("action"),
                "next_goal": (navigating.get("goal_plan") or {}).get("next_goal"),
            }
        if should_attach_need_services(snap, guests_present=guests_present, force=True):
            need_report = evaluate_need_services(
                snap,
                available_objects=available_objects,
                occupied_objects=occupied_objects,
                guests_present=guests_present,
                emotion=emotion,
                moodlets=moodlets,
                life_stage=life_stage or "young_adult",
                traits=traits,
                queue=queue,
                failure_signals=failure_signals,
                capture_ref=capture_ref,
            )
            needs_payload["need_services"] = compact_need_services(need_report)
            receipts.append(
                _receipt(
                    "needs",
                    gate=str(need_report.get("gate")),
                    action=str(need_report.get("action")),
                    payload=needs_payload,
                    findings=(["NEED_LB_DETACH"] if need_report.get("detached_needs") else []),
                )
            )
            if need_report.get("detached_needs"):
                findings.append("NEED_LB_DETACH_PROPAGATES")
    except (NeedServicesError, NavigatingNeedsError) as exc:
        raise DomainCascadeError(str(exc)) from exc

    # --- budget ---
    if funds is not None:
        try:
            budget = evaluate_budget(
                float(funds),
                snap,
                tuple(owned_objects if owned_objects is not None else available_objects),
                moodlets=moodlets,
            )
            receipts.append(
                _receipt(
                    "budget",
                    gate=str(budget.get("next_gate") or budget.get("state") or "BUDGET_EVALUATED"),
                    action=str((budget.get("actions") or ["BUDGET_PLAN"])[0] if isinstance(budget.get("actions"), list) and budget.get("actions") else budget.get("next_gate") or "BUDGET_PLAN"),
                    payload={
                        "money_urgency": budget.get("money_urgency"),
                        "gaps": budget.get("gaps"),
                        "prior_needs_gate": receipts[-1]["gate"] if receipts else None,
                    },
                    findings=list(budget.get("findings") or []),
                )
            )
        except (BudgetEvalError, TypeError, ValueError) as exc:
            receipts.append(
                _receipt(
                    "budget",
                    gate="BUDGET_UNAVAILABLE",
                    action="SKIP_BUDGET",
                    findings=[str(exc)],
                )
            )
    else:
        receipts.append(
            _receipt("budget", gate="BUDGET_NOT_SUPPLIED", action="SKIP_BUDGET")
        )

    # --- career / school / scenario ---
    career_payload: dict = {}
    try:
        if school_day_active or school_goals_incomplete:
            school = evaluate_school_day_turn(
                snap,
                school_day_active=school_day_active or bool(school_goals_incomplete),
                school_goals_incomplete=school_goals_incomplete,
                school_phase=school_phase or "morning_free_time",
                location_kind=location_kind,
                homework_pending=homework_pending,
                pinned_whims=pinned_whims or whims,
                queue=queue,
                capture_ref=capture_ref,
            )
            career_payload["school_day"] = {
                "gate": school.get("gate"),
                "action": school.get("action"),
            }
        if homework_pending or inventory_has_homework is not None or homework_on_lot is not None:
            homework = evaluate_teen_homework_turn(
                snap,
                location_kind=location_kind,
                school_day_active=school_day_active,
                homework_pending=homework_pending,
                inventory_has_homework=inventory_has_homework,
                homework_on_lot=homework_on_lot,
                available_objects=tuple(available_objects or ()),
                queue=tuple(queue or ()),
                life_stage=life_stage or "teen",
                capture_ref=capture_ref,
            )
            career_payload["teen_homework"] = {
                "gate": homework.get("gate"),
                "action": homework.get("action"),
            }
        if scenario_active or scenario_goals_incomplete:
            scenario = evaluate_scenario_turn(
                snap,
                scenario_active=scenario_active or bool(scenario_goals_incomplete),
                scenario_goals_incomplete=scenario_goals_incomplete,
                school_day_active=school_day_active,
                queue=queue,
                capture_ref=capture_ref,
            )
            career_payload["scenario"] = {
                "gate": scenario.get("gate"),
                "action": scenario.get("action"),
                "next_goal": (scenario.get("goal_plan") or {}).get("next_goal"),
            }
        gate = "CAREER_IDLE"
        action = "NO_CAREER_DOMAIN_SIGNAL"
        for key in ("school_day", "teen_homework", "scenario"):
            row = career_payload.get(key)
            if row and row.get("gate") not in {None, "SCENARIO_INACTIVE", "LEISURE_OR_IDLE"}:
                gate = str(row["gate"])
                action = str(row.get("action") or "CAREER_PLAN")
                break
        if any(r["domain"] == "needs" and "DETACH" in "".join(r.get("findings") or []) for r in receipts):
            findings.append("CAREER_SEES_NEED_LB_DETACH")
        receipts.append(
            _receipt(
                "career",
                gate=gate,
                action=action,
                payload={
                    **career_payload,
                    "prior_gates": [r["gate"] for r in receipts],
                },
                findings=findings[-1:],
            )
        )
    except (SchoolDayError, TeenHomeworkError, ScenarioGoalsError) as exc:
        raise DomainCascadeError(str(exc)) from exc

    # --- skills / whims ---
    try:
        profile = evaluate_sim_profile(
            emotion=emotion,
            moodlets=moodlets,
            traits=traits,
            whims=list(whims) + [w for w in pinned_whims if w not in whims],
            skills=skills,
            likes=likes,
            dislikes=dislikes,
            life_stage=life_stage,
            needs=snap,
            capture_ref=capture_ref,
        )
        receipts.append(
            _receipt(
                "skills_whims",
                gate="SIM_PROFILE_INSPECT",
                action="ATTACH_READ_ONLY_PROFILE",
                payload={
                    "desires": profile.get("desires"),
                    "summary": profile.get("summary"),
                    "prior_gates": [r["gate"] for r in receipts],
                },
            )
        )
    except SimProfileError as exc:
        receipts.append(
            _receipt(
                "skills_whims",
                gate="SIM_PROFILE_UNAVAILABLE",
                action="SKIP_PROFILE",
                findings=[str(exc)],
            )
        )

    # --- relationships ---
    if should_attach_social_opportunity(
        social_prompt_active=social_prompt_active,
        prompt_kind=social_prompt_kind,
    ):
        try:
            social = evaluate_social_opportunity(
                social_prompt_active=social_prompt_active,
                prompt_kind=social_prompt_kind,
                prompt_text=social_prompt_text,
                invitee_name=social_invitee_name,
                sim_library=sim_library,
                lookup_ran=social_lookup_ran,
                occult_status=invitee_occult_status,
                capture_ref=capture_ref,
            )
            receipts.append(
                _receipt(
                    "relationships",
                    gate=str(social.get("gate")),
                    action=str(social.get("action")),
                    payload={
                        "invitee_name": social.get("invitee_name"),
                        "occult_status": social.get("occult_status"),
                        "prior_gates": [r["gate"] for r in receipts],
                    },
                    findings=list(social.get("findings") or []),
                )
            )
        except SocialOpportunityError as exc:
            raise DomainCascadeError(str(exc)) from exc
    else:
        receipts.append(
            _receipt(
                "relationships",
                gate="RELATIONSHIPS_IDLE",
                action="NO_SOCIAL_PROMPT",
                payload={"prior_gates": [r["gate"] for r in receipts]},
            )
        )

    primary = next((r for r in receipts if r["domain"] == "needs"), receipts[0])
    return {
        "schema": "betterinstincts.domain-cascade-result/v1",
        "state": "DOMAIN_CASCADE_POLLED",
        "capture_ref": capture_ref,
        "gate": primary["gate"],
        "action": "CASCADE_RECEIPTS_EMITTED",
        "receipts": receipts,
        "cascade_order": list(cfg["cascade_order"]),
        "findings": sorted(set(findings)),
        "prior_receipts_visible": True,
        "proof_ceiling": cfg["proof_ceiling"],
        "architecture": "DOMAIN_CASCADE_POLL_BUS",
        "anti_patterns": list(cfg.get("anti_patterns") or []),
    }
