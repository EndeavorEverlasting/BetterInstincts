"""Thin host call stack: viewport gate + needs plan + chance-card decision eval.

P95 seam: PrintWindow viewport → decision prompt → instincts plan → (live click /
Save As / restart gates remain outside this pure module). Never executes Sims UI.
"""
from __future__ import annotations

from typing import Mapping, Optional, Sequence

from betterinstincts.decision_eval import (
    DecisionEvalError,
    measure_need_deltas,
    recommend,
    recommendation_to_dict,
)
from betterinstincts.instincts_host import (
    InstinctsHostError,
    NeedSnapshot,
    plan,
    plan_to_dict,
)
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
) -> dict:
    """Compose viewport safety + instincts + optional dialog for one host turn.

    Viewport anomalies outrank needs actions: do not click world objects while
    PrintWindow is black. See contracts/viewport-black.v1.json.
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
    except (InstinctsHostError, DecisionEvalError, ViewportError) as exc:
        raise HostStackError(str(exc)) from exc

    # Priority: unreadable viewport > open decision modal > needs plan > save.
    next_gate = "EXECUTE_INSTINCTS_PLAN"
    if viewport and viewport.get("state") == "VIEWPORT_ANOMALY":
        next_gate = str(viewport.get("next_gate") or "RECOVER_OR_AUTHORIZED_RESTART")
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
        "instincts": instincts,
        "decision": decision,
        "influence": influence,
        "viewport": dict(viewport) if viewport else None,
        "viewport_risk": risk,
        "proof_ceiling": "HOST_STACK_OFFLINE_COMPOSITION_NOT_LIVE_PROOF",
    }

