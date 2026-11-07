"""Thin host call stack: needs plan + optional chance-card decision eval.

P95 seam: observation → instincts plan → decision recommendation → (live click /
Save As gates remain outside this pure module). Never executes Sims UI.
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
) -> dict:
    """Compose instincts recovery + optional dialog recommendation for one host turn."""
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
    except (InstinctsHostError, DecisionEvalError) as exc:
        raise HostStackError(str(exc)) from exc

    # Decision prompts outrank routine autonomy when a live modal is open.
    next_gate = "EXECUTE_INSTINCTS_PLAN"
    if decision is not None:
        next_gate = "RESOLVE_DECISION_PROMPT"
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
        "proof_ceiling": "HOST_STACK_OFFLINE_COMPOSITION_NOT_LIVE_PROOF",
    }
