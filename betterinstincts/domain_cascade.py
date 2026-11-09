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
from betterinstincts.sim_profile import SimProfileError, SkillInput, evaluate_sim_profile
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
        "balance",
        "budget",
        "career",
        "aspirations",
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
    lot_model: Optional[Mapping] = None,
    multitasking: Optional[bool] = None,
    sim_room_id: Optional[str] = None,
    sim_seated: Optional[bool] = None,
    sim_seat_id: Optional[str] = None,
    lot_traits: Sequence[str] = (),
    prior_career_state: Optional[Mapping[str, object]] = None,
    aspiration_prompt_active: bool = False,
    aspiration_prompt_id: Optional[str] = None,
    aspiration_prompt_text: str = "",
    aspiration_completion_enabled: bool = False,
    occult_needs_engine_ready: bool = False,
    operator_prefers_aspiration_ok: Optional[bool] = None,
    prior_aspiration_state: Optional[Mapping[str, object]] = None,
    balance_level: Optional[str] = None,
    ailment: Optional[str] = None,
    inventory_has_holistic_cure: Optional[bool] = None,
    apothecary_stall_available: bool = False,
    apothecary_skill_level: Optional[int] = None,
    natural_living_meditate_available: bool = False,
    houseplants_available: bool = False,
    prior_balance_state: Optional[Mapping[str, object]] = None,
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

    # --- balance / imbalance (Enchanted by Nature wellness) ---
    try:
        if should_attach_balance_service(
            balance_level=balance_level,
            ailment=ailment,
            prior_state=prior_balance_state,
        ):
            balance = evaluate_balance_service(
                snap,
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
            bal_findings = [
                f
                for f in (balance.get("findings") or [])
                if f.startswith("BALANCE_")
                or f.startswith("AILMENT_")
                or f.startswith("HOLISTIC_")
                or f.startswith("NATURE_")
                or f.startswith("NEGATIVE_")
                or f.startswith("POSITIVE_")
                or f.startswith("SURVIVAL_")
                or f.startswith("VERY_")
                or f.startswith("MOODLETS_")
            ]
            if balance.get("condition_held"):
                bal_findings.append("BALANCE_CONDITION_HELD")
            receipts.append(
                _receipt(
                    "balance",
                    gate=str(balance.get("gate") or "BALANCE_IDLE"),
                    action=str(balance.get("action") or "NO_BALANCE_CONDITION"),
                    payload={
                        "balance_service": compact_balance_service(balance),
                        "prior_gates": [r["gate"] for r in receipts],
                    },
                    findings=bal_findings,
                )
            )
        else:
            receipts.append(
                _receipt(
                    "balance",
                    gate="BALANCE_IDLE",
                    action="NO_BALANCE_CONDITION",
                    payload={"prior_gates": [r["gate"] for r in receipts]},
                )
            )
    except BalanceServiceError as exc:
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

    # --- career / school / scenario (via career microsystem) ---
    career_payload: dict = {}
    try:
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
        ) or school_day_active or school_goals_incomplete or homework_pending or (
            inventory_has_homework is not None or homework_on_lot is not None
        ) or scenario_active or scenario_goals_incomplete:
            career = evaluate_career_service(
                snap,
                location_kind=location_kind,
                school_day_active=school_day_active,
                school_goals_incomplete=school_goals_incomplete,
                school_phase=school_phase,
                homework_pending=homework_pending,
                inventory_has_homework=inventory_has_homework,
                homework_on_lot=homework_on_lot,
                available_objects=tuple(available_objects or ()),
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
                pinned_whims=pinned_whims or whims,
                whims=whims,
                prior_state=prior_career_state,
                capture_ref=capture_ref,
            )
            career_payload["career_service"] = compact_career_service(career)
            for key, row in (career.get("lanes") or {}).items():
                if isinstance(row, dict):
                    career_payload[key] = {
                        "gate": row.get("gate"),
                        "action": row.get("action"),
                    }
            hw = career_payload.get("teen_homework") or {}
            if hw.get("gate") not in {None, "LEISURE_OR_IDLE"}:
                gate = str(hw["gate"])
                action = str(hw.get("action") or "CAREER_PLAN")
            else:
                gate = str(career.get("gate") or "CAREER_IDLE")
                action = str(career.get("action") or "NO_CAREER_DOMAIN_SIGNAL")
            if career.get("obligation_held"):
                findings.append("CAREER_OBLIGATION_HELD")
        else:
            gate = "CAREER_IDLE"
            action = "NO_CAREER_DOMAIN_SIGNAL"
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
                findings=[f for f in findings if f.startswith("CAREER_")],
            )
        )
    except CareerServiceError as exc:
        raise DomainCascadeError(str(exc)) from exc

    # --- aspirations / life-state dialogs ---
    try:
        if should_attach_aspiration_service(
            aspiration_prompt_active=aspiration_prompt_active,
            prompt_id=aspiration_prompt_id,
            prompt_text=aspiration_prompt_text,
            prior_state=prior_aspiration_state,
        ):
            aspiration = evaluate_aspiration_service(
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
            asp_findings = [f for f in (aspiration.get("findings") or []) if f.startswith("ASPIRATION_") or f.startswith("OCCULT_")]
            if aspiration.get("prompt_held"):
                asp_findings.append("ASPIRATION_PROMPT_HELD")
            receipts.append(
                _receipt(
                    "aspirations",
                    gate=str(aspiration.get("gate") or "ASPIRATION_IDLE"),
                    action=str(aspiration.get("action") or "NO_ASPIRATION_PROMPT"),
                    payload={
                        "aspiration_service": compact_aspiration_service(aspiration),
                        "dialog_choice": aspiration.get("dialog_choice"),
                        "prior_gates": [r["gate"] for r in receipts],
                    },
                    findings=asp_findings,
                )
            )
        else:
            receipts.append(
                _receipt(
                    "aspirations",
                    gate="ASPIRATION_IDLE",
                    action="NO_ASPIRATION_PROMPT",
                    payload={"prior_gates": [r["gate"] for r in receipts]},
                )
            )
    except AspirationServiceError as exc:
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
