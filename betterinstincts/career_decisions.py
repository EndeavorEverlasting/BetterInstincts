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


DISCLOSED_EFFECT_BOUNDS = {**EFFECT_BOUNDS, "fame": 1_000_000.0}


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
    return type(x) in (int, float) and abs(x) <= maximum and math.isfinite(x)


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
    card = data.get("disclosed_card")
    if (not isinstance(card, Mapping) or not _ref(card.get("id"))
            or not isinstance(card.get("identity"), Mapping)
            or set(card["identity"]) != {"title", "subject", "career", "pack"}
            or not all(isinstance(value, str) and value for value in card["identity"].values())
            or not isinstance(card.get("options"), Mapping)
            or len(card["options"]) != 2
            or not isinstance(card.get("preferred_option"), str)
            or card["preferred_option"] not in card["options"]
            or not _ref(card.get("continuation"))
            or any(not isinstance(effects, list) or not effects
                   or any(type(key) is not str or key not in DISCLOSED_EFFECT_BOUNDS for key in effects)
                   or len(set(effects)) != len(effects)
                   for effects in card["options"].values())):
        raise CareerDecisionError("DISCLOSED_CAREER_CARD_CONTRACT_INVALID")
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


def _choose_disclosed_card(event, options, config):
    """Use the reviewed exact-card choice and observed IDs, with no invented utility."""
    card = config["disclosed_card"]
    evidence = event["disclosed_card"]
    if (not isinstance(evidence, Mapping)
            or any(evidence.get(key) != value for key, value in card["identity"].items())
            or not _ref(evidence.get("card_source_ref"))):
        return _hold("DISCLOSED_CARD_IDENTITY_UNVERIFIED", event=event)
    if evidence.get("fame_allowed") is not True:
        return _hold("DISCLOSED_CARD_FAME_NOT_ALLOWED", event=event)
    if len(options) != len(card["options"]):
        return _hold("DISCLOSED_CARD_OPTIONS_UNVERIFIED", event=event)

    by_label = {}
    for option in options:
        label = option.get("label")
        effects = option.get("disclosed_positive_effects")
        expected = card["options"].get(label) if isinstance(label, str) else None
        if (expected is None or label in by_label
                or not isinstance(effects, list) or any(type(key) is not str for key in effects)
                or sorted(effects) != sorted(expected)
                or option.get("job_lost") is not False or option.get("irreversible") is not False):
            return _hold("DISCLOSED_CARD_OPTIONS_UNVERIFIED", event=event)
        # If the adapter also has numerical tuning, reject conflicts with the
        # disclosed outcome instead of silently ignoring the extra evidence.
        if "outcomes" in option and not _matches_disclosed_outcomes(option["outcomes"], expected, config):
            return _hold("DISCLOSED_CARD_OUTCOMES_CONFLICT", event=event)
        by_label[label] = option
    label = card["preferred_option"]
    chosen = by_label[label]
    return {
        **_recommend(event, chosen, reason="REVIEWED_DISCLOSED_CAREER_REWARDS"),
        "card_id": card["id"],
        "option_label": label,
        "required_positive_effects": list(card["options"][label]),
        "continuation_kind": card["continuation"],
        "card_source_ref": evidence["card_source_ref"],
        "score_margin": None,
        "excluded_risky_response_ids": [],
        "all_scores": [],
    }


def _matches_disclosed_outcomes(branches, expected, config):
    if not isinstance(branches, list) or len(branches) != 1 or not isinstance(branches[0], Mapping):
        return False
    branch = branches[0]
    effects = branch.get("effects")
    return (_int(branch.get("probability_bps"), config["probability_scale"], config["probability_scale"])
            and branch.get("job_lost") is False and branch.get("irreversible") is False
            and _ref(branch.get("effect_source_ref"))
            and isinstance(effects, Mapping) and set(effects) == set(expected)
            and all(_number(value, DISCLOSED_EFFECT_BOUNDS[key]) and value > 0
                    for key, value in effects.items()))


def _recommend(event, chosen, *, reason):
    return {
        "schema": RESULT, "state": "RECOMMENDED_NATIVE_CHOICE", "reason": reason,
        "event_ref": event["event_ref"], "event_revision": event["event_revision"],
        "capture_ref": event["capture_ref"], "captured_at_epoch_ms": event["captured_at_epoch_ms"],
        "recipient_sim_id": event["recipient_sim_id"],
        "selected_sim_id": event.get("selected_sim_id"),
        "career_id": event["career_id"], "shift_ref": event["shift_ref"],
        "dialog_tuning_id": event["dialog_tuning_id"],
        "recommended_response_id": chosen["response_id"],
        "selected_effect_basis_ref": chosen["effect_basis_ref"],
        "next": "NATIVE_ONE_RESPONSE_THEN_REOBSERVE_CAREER_AND_ACTIVITY",
        "execute_allowed": False, "control_permit": None, "proof_ceiling": PROOF,
    }


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
        # A native event_ref identifies the event across layout/observation
        # revisions. A prior effect attempt or uncertain result must not be
        # replayed merely because the viewport/revision changed.
        if previously_responded.get("event_ref") == event["event_ref"]:
            return _hold("CAREER_EVENT_ALREADY_ACTED_OR_UNCERTAIN", event=event)
    offered = event.get("response_ids")
    options = event.get("options")
    if (not isinstance(offered, list) or not isinstance(options, list)
            or not 2 <= len(offered) <= MAX_OPTIONS or len(offered) != len(options)
            or any(not _int(x, 0, 2**31 - 1) for x in offered)
            or len(set(offered)) != len(offered)):
        return _hold("COMPLETE_CAREER_RESPONSE_IDS_REQUIRED", event=event)
    indexed = {}
    for option in options:
        if (not isinstance(option, Mapping)
                or not _int(option.get("response_id"), 0, 2**31 - 1)
                or not _ref(option.get("option_ref"))
                or not _ref(option.get("effect_basis_ref"))):
            return _hold("CAREER_OPTION_SOURCE_UNVERIFIED", event=event)
        response_id = option["response_id"]
        if response_id in indexed:
            return _hold("CAREER_DUPLICATE_RESPONSE_OPTION", event=event)
        indexed[response_id] = option
    if set(offered) != indexed.keys():
        return _hold("CAREER_RESPONSE_OPTION_SET_MISMATCH", event=event)
    if "disclosed_card" in event:
        return _choose_disclosed_card(event, options, config)

    scored = []
    excluded_risky_response_ids = []
    for response_id, option in indexed.items():
        score, reason = _outcomes(option, config)
        if reason == "CAREER_IRREVERSIBLE_RISK_HOLD":
            excluded_risky_response_ids.append(response_id)
            continue
        if reason:
            return _hold(reason, event=event)
        scored.append((response_id, score))
    if not scored:
        return _hold("NO_SAFE_CAREER_CHOICE_KNOWN", event=event)
    rank = sorted(scored, key=lambda x: (-x[1], x[0]))
    if (len(rank) > 1 and
            rank[0][1] - rank[1][1] < config["scoring"]["min_score_margin"]):
        return _hold("CAREER_CHOICE_UTILITY_TIE_OR_WEAK_MARGIN", event=event)
    return {
        **_recommend(event, indexed[rank[0][0]], reason="BEST_EVIDENCED_CAREER_OUTCOME"),
        "score_margin": (round(rank[0][1] - rank[1][1], 6)
                         if len(rank) > 1 else None),
        "excluded_risky_response_ids": excluded_risky_response_ids,
        "all_scores": [{"response_id": k, "risk_adjusted_score": round(v, 6)}
                       for k, v in rank],
    }


def reconcile_career_event(
    decision: Mapping[str, Any] | None,
    response: Mapping[str, Any] | None,
    *,
    effect: Mapping[str, Any] | None,
    activity: Mapping[str, Any] | None,
) -> dict:
    """Require separate native response, recipient effect and activity receipts.

    A caller can forge all of these shapes. Local exact-build game observation
    and genuine provenance review remain independently required for P08.
    """
    if (not isinstance(decision, Mapping)
            or decision.get("state") != "RECOMMENDED_NATIVE_CHOICE"):
        return {"schema": ACK, "state": "UNVERIFIED",
                "reason": "CAREER_DECISION_NOT_ADMITTED", "proof_ceiling": PROOF}
    required_effects = decision.get("required_positive_effects", ())
    effect_bounds = DISCLOSED_EFFECT_BOUNDS if required_effects else EFFECT_BOUNDS
    if (not isinstance(response, Mapping)
            or response.get("source") != "EA_NATIVE"
            or response.get("event_ref") != decision["event_ref"]
            or response.get("event_revision") != decision["event_revision"]
            or response.get("recipient_sim_id") != decision["recipient_sim_id"]
            or type(response.get("response_id")) is not int
            or response.get("response_id") != decision["recommended_response_id"]
            or response.get("accepted") is not True
            or not _ref(response.get("capture_ref"))
            or response["capture_ref"] == decision["capture_ref"]
            or not _int(response.get("captured_at_epoch_ms"), 1, 2**63 - 1)
            or response["captured_at_epoch_ms"] <= decision.get("captured_at_epoch_ms", 0)):
        return {"schema": ACK, "state": "UNVERIFIED",
                "reason": "CAREER_NATIVE_RESPONSE_ACK_MISSING", "proof_ceiling": PROOF}
    if (not isinstance(effect, Mapping)
            or effect.get("source") != "EA_NATIVE"
            or effect.get("event_ref") != decision["event_ref"]
            or effect.get("recipient_sim_id") != decision["recipient_sim_id"]
            or effect.get("response_id") != decision["recommended_response_id"]
            or effect.get("effect_basis_ref") != decision["selected_effect_basis_ref"]
            or effect.get("applied") is not True
            or not _ref(effect.get("capture_ref"))
            or effect["capture_ref"] in (decision["capture_ref"], response["capture_ref"])
            or not _int(effect.get("captured_at_epoch_ms"), 1, 2**63 - 1)
            or effect["captured_at_epoch_ms"] <= response["captured_at_epoch_ms"]
            or not isinstance(effect.get("observed_deltas"), Mapping)
            or not effect["observed_deltas"]
            or not set(effect["observed_deltas"]).issubset(effect_bounds)
            or any(not _number(v, effect_bounds[k])
                   for k, v in effect["observed_deltas"].items())
            or any(effect["observed_deltas"].get(key, 0) <= 0 for key in required_effects)
            or (required_effects and effect.get("event_rewards_attributed") is not True)):
        return {"schema": ACK, "state": "UNVERIFIED",
                "reason": "CAREER_NATIVE_EFFECT_OBSERVATION_MISSING", "proof_ceiling": PROOF}
    if (not isinstance(activity, Mapping)
            or activity.get("source") != "EA_NATIVE"
            or activity.get("event_ref") != decision["event_ref"]
            or activity.get("recipient_sim_id") != decision["recipient_sim_id"]
            or activity.get("resumed") is not True
            or not _ref(activity.get("capture_ref"))
            or activity["capture_ref"] in (
                decision["capture_ref"], response["capture_ref"], effect["capture_ref"])
            or not _ref(activity.get("activity_ref"))
            or not _int(activity.get("captured_at_epoch_ms"), 1, 2**63 - 1)
            or activity["captured_at_epoch_ms"] <= effect["captured_at_epoch_ms"]
            or (required_effects and (
                activity.get("continuation_kind") != decision["continuation_kind"]
                or activity.get("shift_ref") != decision["shift_ref"]
                or activity.get("event_closed") is not True))):
        return {"schema": ACK, "state": "UNVERIFIED",
                "reason": "CAREER_ACTIVITY_RESUMPTION_UNOBSERVED", "proof_ceiling": PROOF}
    return {
        "schema": ACK, "state": "RESPONSE_EFFECT_AND_RESUMPTION_SHAPE_MATCH",
        "event_ref": decision["event_ref"],
        "event_revision": decision["event_revision"],
        "recipient_sim_id": decision["recipient_sim_id"],
        "response_id": decision["recommended_response_id"],
        "response_capture_ref": response["capture_ref"],
        "effect_capture_ref": effect["capture_ref"],
        "activity_capture_ref": activity["capture_ref"],
        "activity_ref": activity["activity_ref"],
        "execute_allowed": False, "proof_ceiling": PROOF,
    }
