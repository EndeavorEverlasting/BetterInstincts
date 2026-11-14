"""Career-event choice policy under the existing career_service owner.

Pure deterministic planning: no Sims imports, game hooks, OS clicks, agents,
save reads, or claims that an observed-source dict is authenticated EA data.
The installed native adapter (after exact-build P08 certification) owns events
and effects; this module decides from fully evidenced offered outcomes only.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
import math
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "career-decisions.v1.json"
SCHEMA = "betterinstincts.career-event.observation/v1"
RESULT = "betterinstincts.career-event-decision/v1"
ACK = "betterinstincts.career-event-outcome/v1"
PROOF = "OFFLINE_CAREER_CHOICE_ONLY_NOT_NATIVE_RESPONSE_OR_RESUMPTION"
MAX_OPTIONS = 8
MAX_OUTCOMES = 8
MAX_AGE_MS = 5000
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
EFFECT_BOUNDS = {
    "performance": 100.0, "simoleons": 100000.0, "skill": 10.0,
    "mood": 100.0, "fun": 100.0, "social": 100.0,
    "reputation": 100.0, "relationship": 100.0,
}


class CareerDecisionError(ValueError):
    pass


def _ref(x: object) -> bool:
    return type(x) is str and ID.fullmatch(x) is not None


def _sim(x: object) -> bool:
    return (type(x) is str and 1 <= len(x) <= 20 and x.isascii()
            and x.isdecimal() and x[0] != "0"
            and 0 < int(x) < (1 << 64))


def _int(x: object, low: int, high: int) -> bool:
    return type(x) is int and low <= x <= high


def _number(x: object, maximum: float) -> bool:
    return type(x) in (int, float) and math.isfinite(x) and abs(x) <= maximum


def _hold(reason: str, *, event: Mapping | None = None) -> dict:
    return {
        "schema": RESULT, "state": "HOLD", "reason": reason,
        "event_ref": event.get("event_ref") if isinstance(event, Mapping) else None,
        "recipient_sim_id": (event.get("recipient_sim_id")
                             if isinstance(event, Mapping) else None),
        "recommended_response_id": None, "execute_allowed": False,
        "control_permit": None, "proof_ceiling": PROOF,
    }


def load_contract() -> dict:
    if (CONTRACT.is_symlink() or not CONTRACT.is_file()
            or CONTRACT.stat().st_size > 32000):
        raise CareerDecisionError("CAREER_DECISION_CONTRACT_UNSAFE")
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.career-decisions/v1":
        raise CareerDecisionError("CAREER_DECISION_CONTRACT_INVALID")
    score = data.get("scoring")
    if (not isinstance(score, Mapping) or
            set(score.get("weights", {})) != set(EFFECT_BOUNDS) or
            any(not _number(v, 100) or v < 0 for v in score["weights"].values()) or
            not _number(score.get("risk_aversion"), 1) or
            score.get("risk_aversion") < 0 or
            not _number(score.get("min_score_margin"), 100) or
            score.get("min_score_margin") <= 0 or
            score.get("max_termination_probability_bps") != 0 or
            score.get("allow_irreversible_outcome") is not False):
        raise CareerDecisionError("CAREER_DECISION_RISK_CONFIG_INVALID")
    return data


def _outcomes(option: Mapping[str, Any], config: dict) -> tuple[float, str | None]:
    branches = option.get("outcomes")
    if not isinstance(branches, list) or not 1 <= len(branches) <= MAX_OUTCOMES:
        return 0.0, "CAREER_OPTION_OUTCOMES_MISSING"
    weights = config["scoring"]["weights"]
    total = 0
    score = 0.0
    worst = float("inf")
    for outcome in branches:
        if not isinstance(outcome, Mapping):
            return 0.0, "CAREER_OUTCOME_INVALID"
        probability = outcome.get("probability_bps")
        if (not _int(probability, 1, 10000) or
                not _ref(outcome.get("effect_source_ref")) or
                type(outcome.get("job_lost")) is not bool or
                type(outcome.get("irreversible")) is not bool):
            return 0.0, "CAREER_OUTCOME_SOURCE_OR_RISK_UNKNOWN"
        effects = outcome.get("effects")
        if (not isinstance(effects, Mapping) or
                not set(effects).issubset(EFFECT_BOUNDS) or
                any(not _number(value, EFFECT_BOUNDS[key])
                    for key, value in effects.items())):
            return 0.0, "CAREER_EFFECT_VECTOR_UNKNOWN"
        # Never reward a purported career gain that risks a nonconsensual
        # irreversible change to employment, household or game state.
        if outcome["job_lost"] or outcome["irreversible"]:
            return 0.0, "CAREER_IRREVERSIBLE_RISK_HOLD"
        branch_score = sum(float(value) * weights[key]
                           for key, value in effects.items())
        score += branch_score * probability / config["probability_scale"]
        worst = min(worst, branch_score)
        total += probability
    if total != config["probability_scale"]:
        return 0.0, "CAREER_OUTCOME_PROBABILITIES_INCOMPLETE"
    return score - config["scoring"]["risk_aversion"] * (score - worst), None


def evaluate_career_event(
    event: Mapping[str, Any] | None, *, now_epoch_ms: int,
    autonomy_enabled: bool, player_active: bool,
    previously_responded: Mapping[str, Any] | None = None,
    contract: dict | None = None,
) -> dict:
    """Select one bounded, non-ambiguous choice without clicking any button.

    A genuine installed EA native observer is the future source of these
    fields; this pure function cannot authenticate caller-provided provenance.
    """
    if not isinstance(event, Mapping):
        return _hold("CAREER_EVENT_REQUIRED")
    if (type(autonomy_enabled) is not bool or type(player_active) is not bool
            or type(event.get("player_directed")) is not bool
            or type(event.get("player_queue_reserved")) is not bool):
        return _hold("CAREER_PLAYER_AUTHORITY_UNKNOWN", event=event)
    if player_active or event["player_directed"] or event["player_queue_reserved"]:
        return _hold("PLAYER_OWNS_CAREER_DECISION", event=event)
    if not autonomy_enabled:
        return _hold("CAREER_AUTONOMY_NOT_ENABLED", event=event)
    if (event.get("schema") != SCHEMA or event.get("source") != "EA_NATIVE"
            or event.get("read_origin") != "RUNNING_GAME_MEMORY"
            or event.get("stage") != "CHOICE"
            or event.get("event_kind") != "CAREER_CHANCE_CARD"
            or event.get("options_complete") is not True):
        return _hold("COMPLETE_NATIVE_CAREER_CHOICE_REQUIRED", event=event)
    if (not _ref(event.get("game_build")) or
            not _int(event.get("dialog_tuning_id"), 1, 2**63 - 1) or
            any(not _ref(event.get(k)) for k in (
                "event_ref", "event_revision", "native_hook_ref",
                "capture_ref", "career_id", "shift_ref")) or
            not _sim(event.get("recipient_sim_id")) or
            not _sim(event.get("household_id")) or
            not _int(event.get("career_level"), 1, 99)):
        return _hold("CAREER_EVENT_IDENTITY_OR_SOURCE_INVALID", event=event)
    selected = event.get("selected_sim_id")
    if selected is not None and not _sim(selected):
        return _hold("CAREER_SELECTED_PORTRAIT_INVALID", event=event)
    config = load_contract() if contract is None else contract
    if event.get("career_mode") not in config["supported_career_modes"]:
        return _hold("CAREER_MODE_NOT_SOURCE_VERIFIED", event=event)
    capture = event.get("captured_at_epoch_ms")
    if (not _int(now_epoch_ms, 1, 2**63 - 1)
            or not _int(capture, 1, 2**63 - 1)
            or not 0 <= now_epoch_ms - capture <= MAX_AGE_MS):
        return _hold("CAREER_CHOICE_CAPTURE_STALE", event=event)
    if previously_responded is not None:
        if not isinstance(previously_responded, Mapping):
            return _hold("CAREER_RESPONSE_RECEIPT_UNRECONCILED", event=event)
        if (previously_responded.get("event_ref") == event["event_ref"]
                and previously_responded.get("event_revision") == event["event_revision"]):
            return _hold("CAREER_EVENT_ALREADY_ACTED_OR_UNCERTAIN", event=event)
    offered = event.get("response_ids")
    options = event.get("options")
    if (not isinstance(offered, list) or not isinstance(options, list)
            or not 2 <= len(offered) <= MAX_OPTIONS or len(offered) != len(options)
            or any(not _int(x, 0, 2**31 - 1) for x in offered)
            or len(set(offered)) != len(offered)):
        return _hold("COMPLETE_CAREER_RESPONSE_IDS_REQUIRED", event=event)
    scored = []
    for option in options:
        if (not isinstance(option, Mapping) or
                not _int(option.get("response_id"), 0, 2**31 - 1) or
                not _ref(option.get("option_ref")) or
                not _ref(option.get("effect_basis_ref"))):
            return _hold("CAREER_OPTION_SOURCE_UNVERIFIED", event=event)
        score, reason = _outcomes(option, config)
        if reason:
            return _hold(reason, event=event)
        scored.append((option["response_id"], score))
    if set(offered) != {key for key, _ in scored}:
        return _hold("CAREER_RESPONSE_OPTION_SET_MISMATCH", event=event)
    if len({key for key, _ in scored}) != len(scored):
        return _hold("CAREER_DUPLICATE_RESPONSE_OPTION", event=event)
    rank = sorted(scored, key=lambda x: (-x[1], x[0]))
    if rank[0][1] - rank[1][1] < config["scoring"]["min_score_margin"]:
        return _hold("CAREER_CHOICE_UTILITY_TIE_OR_WEAK_MARGIN", event=event)
    return {
        "schema": RESULT, "state": "RECOMMENDED_NATIVE_CHOICE",
        "reason": "BEST_EVIDENCED_CAREER_OUTCOME",
        "event_ref": event["event_ref"],
        "event_revision": event["event_revision"],
        "capture_ref": event["capture_ref"],
        "recipient_sim_id": event["recipient_sim_id"],
        "selected_sim_id": selected,
        "career_id": event["career_id"],
        "dialog_tuning_id": event["dialog_tuning_id"],
        "recommended_response_id": rank[0][0],
        "score_margin": round(rank[0][1] - rank[1][1], 6),
        "all_scores": [{"response_id": k, "risk_adjusted_score": round(v, 6)}
                       for k, v in rank],
        "next": "NATIVE_ONE_RESPONSE_THEN_REOBSERVE_CAREER_AND_ACTIVITY",
        "execute_allowed": False, "control_permit": None,
        "proof_ceiling": PROOF,
    }


def reconcile_career_event(
    decision: Mapping[str, Any] | None,
    response: Mapping[str, Any] | None,
    *,
    activity: Mapping[str, Any] | None,
) -> dict:
    """Only report a matched, distinct response and resumed activity shape."""
    if (not isinstance(decision, Mapping)
            or decision.get("state") != "RECOMMENDED_NATIVE_CHOICE"):
        return {"schema": ACK, "state": "UNVERIFIED",
                "reason": "CAREER_DECISION_NOT_ADMITTED", "proof_ceiling": PROOF}
    if (not isinstance(response, Mapping)
            or response.get("source") != "EA_NATIVE"
            or response.get("event_ref") != decision["event_ref"]
            or response.get("event_revision") != decision["event_revision"]
            or response.get("recipient_sim_id") != decision["recipient_sim_id"]
            or response.get("response_id") != decision["recommended_response_id"]
            or response.get("accepted") is not True
            or not _ref(response.get("capture_ref"))
            or response["capture_ref"] == decision["capture_ref"]):
        return {"schema": ACK, "state": "UNVERIFIED",
                "reason": "CAREER_NATIVE_RESPONSE_ACK_MISSING", "proof_ceiling": PROOF}
    if (not isinstance(activity, Mapping)
            or activity.get("source") != "EA_NATIVE"
            or activity.get("event_ref") != decision["event_ref"]
            or activity.get("recipient_sim_id") != decision["recipient_sim_id"]
            or activity.get("resumed") is not True
            or not _ref(activity.get("capture_ref"))
            or activity["capture_ref"] in (decision["capture_ref"], response["capture_ref"])
            or not _ref(activity.get("activity_ref"))):
        return {"schema": ACK, "state": "UNVERIFIED",
                "reason": "CAREER_ACTIVITY_RESUMPTION_UNOBSERVED", "proof_ceiling": PROOF}
    return {
        "schema": ACK, "state": "RESPONSE_AND_RESUMPTION_SHAPE_MATCH",
        "event_ref": decision["event_ref"], "recipient_sim_id": decision["recipient_sim_id"],
        "response_id": decision["recommended_response_id"],
        "activity_ref": activity["activity_ref"],
        "execute_allowed": False, "proof_ceiling": PROOF,
    }
