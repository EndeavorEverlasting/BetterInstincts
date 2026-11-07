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

SAFE_TAGS = frozenset({"ethical", "safe", "preserve_performance", "stable_mood", "host_prep", "rabbit_hole", "keep_home_lot"})
RISK_TAGS = frozenset({"theft", "risk_reputation", "risk_school", "risk_mood", "leave_home_lot", "blocks_home_build", "travel_with_sim"})


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


def score_option(option: dict, *, needs_critical: bool, prefer_home_control: bool) -> ScoredOption:
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
        if any(t in {"theft", "risk_school", "risk_reputation", "leave_home_lot"} for t in tags):
            score -= 4.0
            rationale.append("penalize_risky_under_critical_needs")
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


def recommend(
    prompt_id: str,
    needs: Mapping[str, float],
    *,
    catalog: dict | None = None,
    prefer_home_control: bool = False,
    urgent_threshold: float = 0.35,
) -> DecisionRecommendation:
    prompt = get_prompt(prompt_id, catalog)
    critical = _needs_critical(needs, urgent_threshold)
    ranked = tuple(sorted(
        (score_option(opt, needs_critical=critical, prefer_home_control=prefer_home_control)
         for opt in prompt["options"]),
        key=lambda s: (-s.score, s.option_id),
    ))
    best = ranked[0]
    # Tie or all negative under unknown: fall back to catalog default when present.
    default = prompt.get("default_when_unknown_needs")
    if default and ranked[0].score == ranked[1].score:
        for item in ranked:
            if item.option_id == default:
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
