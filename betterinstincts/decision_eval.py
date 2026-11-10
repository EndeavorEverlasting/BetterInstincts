"""Score repeatable Sims chance-card / dialog decisions against need safety.

Offline catalog + heuristic evaluator. Never clicks the game, never edits saves,
and never claims live certification from a score alone. Pair with PrintWindow
observation and optional host execution in a separate live lane.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Mapping, Optional, Sequence, Tuple

from betterinstincts.horizon import SIX_NEEDS
from betterinstincts.instincts_host import InstinctsHostError, NeedSnapshot, all_green

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "contracts" / "decision-prompts.v1.json"

SAFE_TAGS = frozenset({
    "ethical", "safe", "preserve_performance", "stable_mood", "host_prep",
    "rabbit_hole", "keep_home_lot", "funds_recovery", "player_choice",
    "escape_cancel",
})
RISK_TAGS = frozenset({
    "theft", "risk_reputation", "risk_school", "risk_mood",
    "leave_home_lot", "blocks_home_build", "travel_with_sim", "host_crisis_anti_pattern",
    "create_new_sim", "unrequested_activation", "risk_new_servo",
})
SCHOOL_PROMPT_ID = "school.attend.join_or_send_alone"


class DecisionEvalError(ValueError):
    """Invalid decision catalog or observation; never a live gameplay success."""


@dataclass(frozen=True)
class ScoredOption:
    option_id: str
    label: str
    score: float
    tags: Tuple[str, ...]
    rationale: Tuple[str, ...]


@dataclass(frozen=True)
class DecisionRecommendation:
    prompt_id: str
    state: str
    recommended_option_id: str
    ranked: Tuple[ScoredOption, ...]
    needs_critical: bool
    proof_ceiling: str


def load_catalog(path: Path = CATALOG) -> dict:
    path = Path(path)
    if path.is_symlink() or path.stat().st_size > 256_000:
        raise DecisionEvalError("DECISION_CATALOG_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.decision-prompts/v1":
        raise DecisionEvalError("BAD_DECISION_SCHEMA")
    prompts = cfg.get("prompts")
    if not isinstance(prompts, list) or not prompts:
        raise DecisionEvalError("DECISION_PROMPTS_REQUIRED")
    ids = []
    for row in prompts:
        if not isinstance(row, dict) or not isinstance(row.get("prompt_id"), str):
            raise DecisionEvalError("INVALID_PROMPT_ROW")
        opts = row.get("options")
        if not isinstance(opts, list) or len(opts) < 2:
            raise DecisionEvalError("PROMPT_NEEDS_TWO_OPTIONS")
        ids.append(row["prompt_id"])
    if len(set(ids)) != len(ids):
        raise DecisionEvalError("DUPLICATE_PROMPT_ID")
    return cfg


def get_prompt(prompt_id: str, catalog: dict | None = None) -> dict:
    cfg = catalog or load_catalog()
    for row in cfg["prompts"]:
        if row["prompt_id"] == prompt_id:
            return row
    raise DecisionEvalError("UNKNOWN_PROMPT_ID")


def _needs_critical(needs: Mapping[str, float], urgent: float = 0.35) -> bool:
    if set(needs) != SIX_NEEDS:
        raise DecisionEvalError("SIX_NEEDS_REQUIRED")
    for value in needs.values():
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value) or not 0 <= value <= 1:
            raise DecisionEvalError("INVALID_NEED_VALUE")
    return any(v < urgent for v in needs.values())


def score_option(
    option: dict,
    *,
    needs_critical: bool,
    prefer_home_control: bool,
    funds_critical: bool = False,
    funds_low: bool = False,
) -> ScoredOption:
    tags = tuple(str(t) for t in option.get("tags", []))
    score = 0.0
    rationale = []
    for tag in tags:
        if tag in SAFE_TAGS:
            score += 2.0
            rationale.append("safe_tag:" + tag)
        if tag in RISK_TAGS:
            score -= 2.0
            rationale.append("risk_tag:" + tag)
    if needs_critical:
        if any(t in SAFE_TAGS for t in tags):
            score += 3.0
            rationale.append("boost_safe_under_critical_needs")
        if any(t in {"theft", "risk_school", "risk_reputation", "leave_home_lot", "host_crisis_anti_pattern"} for t in tags):
            score -= 4.0
            rationale.append("penalize_risky_under_critical_needs")
    # Broke household: never Join / leave home — money + sleep objects live at home.
    if funds_critical or funds_low:
        if "keep_home_lot" in tags or "host_prep" in tags:
            score += 5.0 if funds_critical else 3.0
            rationale.append("boost_home_control_under_money_stress")
        if any(t in {"leave_home_lot", "travel_with_sim", "host_crisis_anti_pattern"} for t in tags):
            score -= 8.0 if funds_critical else 5.0
            rationale.append("forbid_school_join_under_money_stress")
    if prefer_home_control:
        if "keep_home_lot" in tags or "host_prep" in tags:
            score += 3.0
            rationale.append("prefer_home_lot_control")
        if "leave_home_lot" in tags or "travel_with_sim" in tags:
            score -= 3.0
            rationale.append("avoid_leaving_home_lot")
    return ScoredOption(
        option_id=str(option["option_id"]),
        label=str(option.get("label", option["option_id"])),
        score=score,
        tags=tags,
        rationale=tuple(rationale),
    )


def _forced_option(prompt: Mapping, flags: set[str]) -> Optional[str]:
    """Return an option forced by catalog flags, or None.

    ``force_option_when_present``: {flag: option} fires when the flag is set.
    ``force_option_when_absent``: {flag: option} fires when the flag is NOT set
    (consent-style gates: no explicit consent -> safe option).
    """
    present = prompt.get("force_option_when_present") or {}
    if isinstance(present, Mapping):
        for flag, option_id in present.items():
            if flag in flags:
                return str(option_id)
    absent = prompt.get("force_option_when_absent") or {}
    if isinstance(absent, Mapping):
        for flag, option_id in absent.items():
            if flag not in flags:
                return str(option_id)
    return None


def recommend(
    prompt_id: str,
    needs: Mapping[str, float],
    *,
    catalog: dict | None = None,
    prefer_home_control: bool = False,
    urgent_threshold: float = 0.35,
    funds: Optional[float] = None,
    soft_budget_floor: float = 2000.0,
    emergency_reserve: float = 400.0,
    host_work_active: bool = False,
    flags: Sequence[str] = (),
) -> DecisionRecommendation:
    prompt = get_prompt(prompt_id, catalog)
    flag_set = {str(f) for f in flags}
    if host_work_active:
        flag_set.add("host_work_active")
    critical = _needs_critical(needs, urgent_threshold)
    funds_critical = False
    funds_low = False
    if funds is not None:
        if isinstance(funds, bool) or not isinstance(funds, (int, float)) or funds < 0:
            raise DecisionEvalError("INVALID_FUNDS")
        funds_critical = float(funds) < float(emergency_reserve)
        funds_low = float(funds) < float(soft_budget_floor)
    # Crisis auto-forces home control (Send Alone) — operator RCA: Join stranded the lab.
    force_home = (
        prefer_home_control or critical or funds_critical or funds_low
        or "host_work_active" in flag_set
    )
    if force_home and prompt_id == SCHOOL_PROMPT_ID:
        prefer_home_control = True
    ranked = tuple(sorted(
        (score_option(
            opt,
            needs_critical=critical,
            prefer_home_control=prefer_home_control,
            funds_critical=funds_critical,
            funds_low=funds_low,
         )
         for opt in prompt["options"]),
        key=lambda s: (-s.score, s.option_id),
    ))
    best = ranked[0]
    # Hard gate: under crisis never recommend Join for school attendance.
    # Host work (build/repair/skill force) makes Send Alone mandatory too.
    if prompt_id == SCHOOL_PROMPT_ID and (
        critical or funds_critical or funds_low or "host_work_active" in flag_set
    ):
        for item in ranked:
            if item.option_id == "send_alone":
                best = item
                break
    # Tie or all negative under unknown: fall back to catalog default when present.
    default = prompt.get("default_when_unknown_needs")
    if default and ranked[0].score == ranked[1].score:
        for item in ranked:
            if item.option_id == default:
                best = item
                break
    # Catalog-declared hard gates (e.g. CAS: Escape-cancel unless the operator
    # consented to a new Servo, or when Escape-cancel was explicitly requested).
    forced = _forced_option(prompt, flag_set)
    if forced is not None:
        for item in ranked:
            if item.option_id == forced:
                best = item
                break
    return DecisionRecommendation(
        prompt_id=prompt_id,
        state="RECOMMENDATION_READY",
        recommended_option_id=best.option_id,
        ranked=ranked,
        needs_critical=critical,
        proof_ceiling="HEURISTIC_SCORE_NOT_LIVE_OUTCOME_PROOF",
    )


def recommendation_to_dict(result: DecisionRecommendation) -> dict:
    return {
        "prompt_id": result.prompt_id,
        "state": result.state,
        "recommended_option_id": result.recommended_option_id,
        "needs_critical": result.needs_critical,
        "proof_ceiling": result.proof_ceiling,
        "ranked": [
            {
                "option_id": o.option_id,
                "label": o.label,
                "score": o.score,
                "tags": list(o.tags),
                "rationale": list(o.rationale),
            }
            for o in result.ranked
        ],
    }


def option_has_no_risk_tags(tags: Sequence[str]) -> bool:
    """True only when every tag is a known SAFE_TAG and none are RISK_TAGS."""
    if not isinstance(tags, (list, tuple)) or not tags:
        return False
    normalized = [str(t) for t in tags]
    if any(t not in SAFE_TAGS for t in normalized):
        return False
    return not any(t in RISK_TAGS for t in normalized)


def no_risk_host_auto_choice_eligible(
    tags: Sequence[str],
    *,
    implications_row: Mapping | None = None,
    catalog_policy: Mapping | None = None,
    option_id: str | None = None,
) -> bool:
    """Standing host policy gate: safe tags + empty/reversible implications.

    Catalog ``host_no_risk_auto_choice`` may further pin the allowed option_id.
    This never authorizes SendInput by itself.
    """
    if not option_has_no_risk_tags(tags):
        return False
    if isinstance(catalog_policy, Mapping):
        if catalog_policy.get("enabled") is not True:
            return False
        pinned = catalog_policy.get("option_id")
        if pinned is not None and option_id is not None and str(pinned) != str(option_id):
            return False
    if implications_row is None:
        # Tag / catalog pin only. When chance-event research is present, callers
        # must pass the matching implications_row for empty-risk permanence.
        return True
    if not isinstance(implications_row, Mapping):
        return False
    risks = implications_row.get("risks")
    permanence = implications_row.get("permanence")
    if not isinstance(risks, list) or any(not isinstance(x, str) for x in risks):
        return False
    if risks:
        return False
    if permanence not in {"REVERSIBLE"}:
        return False
    if implications_row.get("disputed") is True:
        return False
    return True


def host_no_risk_policy_for_prompt(prompt_id: str, catalog: dict | None = None) -> dict | None:
    """Return catalog host_no_risk_auto_choice block, or None."""
    prompt = get_prompt(prompt_id, catalog)
    policy = prompt.get("host_no_risk_auto_choice")
    return dict(policy) if isinstance(policy, Mapping) else None


def measure_need_deltas(
    before: Mapping[str, float],
    after: Mapping[str, float],
    *,
    host_action: Optional[str] = None,
    material: float = 0.05,
) -> dict:
    """Offline influence metric: before/after six-need deltas after a host action.

    Positive deltas are improvements. This is not a Sims API readback.
    """
    if set(before) != SIX_NEEDS or set(after) != SIX_NEEDS:
        raise DecisionEvalError("SIX_NEEDS_REQUIRED")
    for mapping in (before, after):
        for value in mapping.values():
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value) or not 0 <= value <= 1:
                raise DecisionEvalError("INVALID_NEED_VALUE")
    deltas = {need: float(after[need] - before[need]) for need in sorted(SIX_NEEDS)}
    improved = [n for n, d in deltas.items() if d >= material]
    worsened = [n for n, d in deltas.items() if d <= -material]
    return {
        "state": "DELTAS_COMPUTED",
        "host_action": host_action,
        "deltas": deltas,
        "improved": improved,
        "worsened": worsened,
        "net_sum": sum(deltas.values()),
        "all_green_after": all_green(NeedSnapshot(after)),
        "proof_ceiling": "OPERATOR_OR_SENSOR_SUPPLIED_DELTAS_NOT_GAME_API",
    }
