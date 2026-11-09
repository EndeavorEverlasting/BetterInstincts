"""Reviewed contextual queue/whim valence: bounded, opt-in online model.

Observe != predict != authorize. Model-only predictions never cancel actions,
pin whims, mutate game settings, or assert that an outcome was observed.
"""
from __future__ import annotations

import math
import re
import time
from collections import defaultdict
from collections.abc import Mapping

from betterinstincts.autonomy_moderation import (
    AutonomyModerationError, evaluate_autonomy_moderation,
)

MODEL_SCHEMA = "betterinstincts.behavior-valence-model/v1"
REVIEW_SCHEMA = "betterinstincts.behavior-valence-review/v1"
REPORT_SCHEMA = "betterinstincts.behavior-valence-report/v1"
KINDS = frozenset({"QUEUE", "WHIM"})
CONTEXTS = frozenset({"survival", "work", "social", "leisure", "other"})
OUTCOMES = frozenset({"POSITIVE", "NEGATIVE"})
PATCH = re.compile(r"^[0-9]+(?:[.][0-9]+){3}$")
TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")
MAX_REVIEWS = 256
MAX_CELLS = 192
MAX_TOTAL = 512
MAX_MODEL_BYTES = 48000
MIN_SUPPORT = 3
HIGH = 0.75
LOW = 0.25


class BehaviorValenceError(ValueError):
    pass


def _token(value: object) -> bool:
    return isinstance(value, str) and bool(TOKEN.fullmatch(value))


def _profile(version: object, platform: object) -> tuple[str, str]:
    if not isinstance(version, str) or not PATCH.fullmatch(version):
        raise BehaviorValenceError("EXACT_PATCH_REQUIRED")
    if platform not in {"windows", "linux", "macos"}:
        raise BehaviorValenceError("PLATFORM_REQUIRED")
    return version, platform


def empty_model(*, game_version: str, platform: str) -> dict:
    v, p = _profile(game_version, platform)
    return {
        "schema": MODEL_SCHEMA, "game_version": v, "platform": p,
        "counts": [], "seen_review_refs": [],
        "model_type": "CONTEXTUAL_BETA_BINOMIAL_COUNTS",
        "proof_ceiling": "OFFLINE_REVIEWED_BEHAVIOR_EXAMPLES_ONLY",
    }


def validate_model(model: Mapping) -> dict:
    if not isinstance(model, Mapping) or model.get("schema") != MODEL_SCHEMA:
        raise BehaviorValenceError("MODEL_SCHEMA_INVALID")
    _profile(model.get("game_version"), model.get("platform"))
    counts, seen = model.get("counts"), model.get("seen_review_refs")
    if (not isinstance(counts, list) or len(counts) > MAX_CELLS
            or not isinstance(seen, list) or len(seen) > MAX_REVIEWS
            or not all(_token(x) for x in seen)):
        raise BehaviorValenceError("MODEL_BOUNDS_OR_REPLAY_INVALID")
    if len(set(seen)) != len(seen):
        raise BehaviorValenceError("MODEL_REVIEW_REPLAY_INVALID")
    keys = set()
    total = 0
    for row in counts:
        if not isinstance(row, Mapping) or set(row) != {
                "kind", "context", "action_id", "positive", "negative"}:
            raise BehaviorValenceError("MODEL_CELL_INVALID")
        if (not isinstance(row["kind"], str) or row["kind"] not in KINDS
                or not isinstance(row["context"], str) or row["context"] not in CONTEXTS
                or not _token(row["action_id"])
                or any(type(row[k]) is not int or not 0 <= row[k] <= MAX_TOTAL
                       for k in ("positive", "negative"))):
            raise BehaviorValenceError("MODEL_CELL_INVALID")
        key = (row["kind"], row["context"], row["action_id"])
        if key in keys:
            raise BehaviorValenceError("MODEL_DUPLICATE_CELL")
        keys.add(key)
        total += row["positive"] + row["negative"]
    if total > MAX_TOTAL or len(str(dict(model)).encode("utf-8")) > MAX_MODEL_BYTES:
        raise BehaviorValenceError("MODEL_TOTAL_BOUNDS")
    if model.get("model_type") != "CONTEXTUAL_BETA_BINOMIAL_COUNTS":
        raise BehaviorValenceError("MODEL_TYPE_INVALID")
    return dict(model)


def learn_reviewed(
    reviews: list[Mapping], *, game_version: str, platform: str,
    prior: Mapping | None = None,
) -> dict:
    """Incremental supervised training, only from explicit, reviewed outcomes.

    Caller persists the resulting aggregate; repeated review_refs cannot train
    twice, even across separately submitted batches in the same model lineage.
    """
    version, os_name = _profile(game_version, platform)
    if not isinstance(reviews, list) or not 1 <= len(reviews) <= 64:
        raise BehaviorValenceError("REVIEW_BATCH_INVALID")
    old = (validate_model(prior) if prior is not None else
           empty_model(game_version=version, platform=os_name))
    if (old["game_version"], old["platform"]) != (version, os_name):
        raise BehaviorValenceError("MODEL_PROFILE_MISMATCH")
    seen = list(old["seen_review_refs"])
    keys = {(r["kind"], r["context"], r["action_id"]):
            [r["positive"], r["negative"]] for r in old["counts"]}
    for raw in reviews:
        if not isinstance(raw, Mapping) or set(raw) != {
                "schema", "game_version", "platform", "kind", "context",
                "action_id", "outcome", "review_ref", "evidence_ref",
                "operator_reviewed", "opt_in"}:
            raise BehaviorValenceError("REVIEW_FIELDS_INVALID")
        if (raw["schema"] != REVIEW_SCHEMA
                or raw["game_version"] != version or raw["platform"] != os_name
                or raw["kind"] not in KINDS or raw["context"] not in CONTEXTS
                or raw["outcome"] not in OUTCOMES
                or not _token(raw["action_id"])
                or not _token(raw["review_ref"]) or not _token(raw["evidence_ref"])
                or raw["operator_reviewed"] is not True or raw["opt_in"] is not True):
            raise BehaviorValenceError("REVIEW_PROOF_REQUIRED")
        if raw["review_ref"] in seen:
            raise BehaviorValenceError("REPLAYED_REVIEW_REF")
        seen.append(raw["review_ref"])
        key = (raw["kind"], raw["context"], raw["action_id"])
        values = keys.setdefault(key, [0, 0])
        values[0 if raw["outcome"] == "POSITIVE" else 1] += 1
        if len(seen) > MAX_REVIEWS or len(keys) > MAX_CELLS:
            raise BehaviorValenceError("MODEL_CAP_REACHED")
    counts = [
        dict(kind=k[0], context=k[1], action_id=k[2],
             positive=n[0], negative=n[1])
        for k,n in sorted(keys.items())
    ]
    candidate = {**old, "counts": counts, "seen_review_refs": seen}
    validate_model(candidate)
    return candidate


def _predict(model: Mapping | None, *, kind: str, context: str, action: str,
             version: str | None, platform: str | None) -> dict:
    result = {"valence": "UNKNOWN", "source": "MODEL_ADVISORY_ONLY",
              "support": 0, "probability_positive": None}
    if model is None:
        return result
    approved = validate_model(model)
    if (version, platform) != (approved["game_version"], approved["platform"]):
        return result
    match = next((r for r in approved["counts"]
                  if (r["kind"],r["context"],r["action_id"]) == (
                      kind, context, action)), None)
    if match is None:
        return result
    support = match["positive"] + match["negative"]
    # Beta(1,1) posterior mean; do not turn one anecdote into a rule.
    probability = (match["positive"] + 1) / (support + 2)
    label = ("POSITIVE" if support >= MIN_SUPPORT and probability >= HIGH else
             "NEGATIVE" if support >= MIN_SUPPORT and probability <= LOW else
             "UNKNOWN")
    return {**result, "valence": label, "support": support,
            "probability_positive": round(probability,4)}


def evaluate_behavior_valence(
    observation: Mapping, *, capture_ref: str,
    model: Mapping | None = None, now: float | None = None,
) -> dict:
    """Classify every current queue action and whim without conflating streams."""
    # Reuse canonical selected-Sim, freshness, origin and review gating.
    try:
        moderation = evaluate_autonomy_moderation(
            observation, capture_ref=capture_ref, now=now)
    except AutonomyModerationError as exc:
        raise BehaviorValenceError(str(exc)) from exc
    result = {
        "schema": REPORT_SCHEMA, "sim_ref": observation["sim_ref"],
        "capture_ref": capture_ref, "gate": "REOBSERVE",
        "queue": {"positive": [], "negative": [], "neutral": [], "unknown": []},
        "whims": {"positive": [], "negative": [], "neutral": [], "unknown": []},
        "model_positive": [], "model_negative": [],
        "pin_candidate": None, "execute_allowed": False, "cancel_allowed": False,
        "proof_ceiling": "OFFLINE_VALENCE_CLASSES_NOT_GAME_EFFECT",
    }
    gate = moderation["state"]
    if gate in {"REOBSERVE_QUEUE", "SIM_NOT_VERIFIED_SELECTED",
                "PLAYER_FIRST", "SURVIVAL_OR_OBLIGATION_FIRST",
                "AUTONOMY_SETTING_QUEUE_CONFLICT"}:
        result["gate"] = gate
        return result
    if not isinstance(observation.get("activity_context"), str) or (
            observation["activity_context"] not in CONTEXTS):
        raise BehaviorValenceError("ACTIVITY_CONTEXT_REQUIRED")
    context = observation["activity_context"]
    version, platform = observation.get("game_version"), observation.get("platform")
    if model is not None:
        validate_model(model)
    used = set()
    for kind, rows, store in (
        ("QUEUE", observation.get("queue", []), result["queue"]),
        ("WHIM", observation.get("whims", []), result["whims"]),
    ):
        for row in rows:
            if not isinstance(row, Mapping):
                raise BehaviorValenceError("VALENCE_ROW_INVALID")
            ident = row.get("queue_slot_ref" if kind == "QUEUE" else "whim_ref")
            action = row.get("action_id")
            if not _token(ident) or (kind,ident) in used:
                raise BehaviorValenceError("VALENCE_IDENTITY_INVALID")
            # Prior whimsical observations could lack an action ID; retain the
            # wish under UNKNOWN rather than breaking legacy listener ticks.
            action_known = _token(action)
            if not action_known and kind == "QUEUE":
                raise BehaviorValenceError("QUEUE_ACTION_REQUIRED")
            if not action_known:
                action = "unknown_whim_action"
            used.add((kind,ident))
            if (row.get("capture_ref") != capture_ref
                    or row.get("sim_ref") != observation["sim_ref"]):
                result["gate"] = "REOBSERVE_ROW"
                return {**result,"queue":{k:[] for k in result["queue"]},
                        "whims":{k:[] for k in result["whims"]},
                        "model_positive":[],"model_negative":[],"pin_candidate":None}
            evidence = None
            observed = "UNKNOWN"
            if kind == "QUEUE":
                effect = row.get("effect")
                if _token(row.get("effect_proof_ref")):
                    if effect == "BENEFICIAL":
                        observed = "POSITIVE"
                    elif effect in {"RELATIONSHIP_HARM","ENVIRONMENT_HARM"}:
                        observed = "NEGATIVE"
                    elif effect == "NEUTRAL":
                        observed = "NEUTRAL"
                    evidence = row["effect_proof_ref"]
            else:
                benefit = row.get("benefit")
                if _token(row.get("benefit_proof_ref")):
                    if benefit == "BENEFICIAL":
                        observed = "POSITIVE"
                    elif benefit == "HARMFUL":
                        observed = "NEGATIVE"
                    elif benefit == "NEUTRAL":
                        observed = "NEUTRAL"
                    evidence = row["benefit_proof_ref"]
            prediction = _predict(
                model if action_known else None,kind=kind,context=context,action=action,
                version=version,platform=platform)
            entry = {
                "kind": kind, "id": ident, "action_id": action,
                "observed_valence": observed, "observed_proof_ref": evidence,
                "learned_advice": prediction,
                "source": "PROVEN_OBSERVATION" if observed != "UNKNOWN" else
                          "UNKNOWN_EFFECT_NOT_A_NEGATIVE_JUDGMENT",
            }
            if kind == "QUEUE":
                entry["origin"] = row.get("origin", "UNKNOWN") if _token(
                    row.get("origin_proof_ref")) else "UNKNOWN"
                entry["player_protected"] = entry["origin"] == "PLAYER"
            else:
                if type(row.get("pinned",False)) is not bool:
                    raise BehaviorValenceError("WHIM_PIN_STATE_INVALID")
                entry["pinned"] = row.get("pinned",False)
            store[observed.lower()].append(entry)
            if observed == "UNKNOWN" and prediction["valence"] == "POSITIVE":
                result["model_positive"].append({"kind":kind,"id":ident,"action_id":action})
            if observed == "UNKNOWN" and prediction["valence"] == "NEGATIVE":
                result["model_negative"].append({"kind":kind,"id":ident,"action_id":action})
            if (kind == "WHIM" and observed == "POSITIVE"
                    and result["pin_candidate"] is None
                    and row.get("pinned",False) is False
                    and row.get("available") is True
                    and observation.get("goal_pending") is False
                    and observation.get("pin_policy_opt_in") is True):
                result["pin_candidate"] = {
                    "sim_ref":observation["sim_ref"], "whim_ref":ident,
                    "action_id":action, "capture_ref":capture_ref,
                    "positive_proof_ref":evidence,
                    "required_target_id":"whims.pin_whim",
                    "evidence_kind":"OBSERVED_POSITIVE",
                    "pin_policy_opt_in":True,
                    "requires":["EXACT_WISH", "PIN_HITBOX", "CURRENT_SELECTED_SIM",
                                "PLAYER_IDLE_LEASE", "NATIVE_SCREEN_ATLAS",
                                "VERIFY_PIN_AFTER_CLICK"],
                }
    result["gate"] = "VALENCE_CLASSIFIED_ADVISORY_ONLY"
    return result


def prequential_evaluate(
    reviews: list[Mapping], *, game_version: str, platform: str
) -> dict:
    """Measure model utility by predicting *before* each reviewed example.

    Report abstention coverage and positive/negative prediction precision
    separately; never count an unknown answer as a confirmed failure/success.
    """
    _profile(game_version,platform)
    if not isinstance(reviews,list) or not 1 <= len(reviews) <= MAX_REVIEWS:
        raise BehaviorValenceError("EVALUATION_BATCH_INVALID")
    model=empty_model(game_version=game_version,platform=platform)
    issued=correct=positive_issued=negative_issued=0
    positive_correct=negative_correct=0
    for row in reviews:
        if not isinstance(row,Mapping):
            raise BehaviorValenceError("EVALUATION_EXAMPLE_INVALID")
        predicted=_predict(model,kind=row.get("kind"),context=row.get("context"),
                           action=row.get("action_id"),version=game_version,
                           platform=platform)
        label=predicted["valence"]
        # Validate and train current event only after its prediction.
        model=learn_reviewed([row],game_version=game_version,platform=platform,
                             prior=model)
        if label in OUTCOMES:
            issued+=1
            correct+=int(label==row["outcome"])
            if label=="POSITIVE":
                positive_issued+=1
                positive_correct+=int(label==row["outcome"])
            else:
                negative_issued+=1
                negative_correct+=int(label==row["outcome"])
    return {
        "schema":"betterinstincts.behavior-valence-evaluation/v1",
        "reviewed_examples":len(reviews),
        "predictions_issued":issued,"predictions_correct":correct,
        "prediction_coverage":round(issued/len(reviews),4),
        "prediction_precision":round(correct/issued,4) if issued else None,
        "positive_precision":round(positive_correct/positive_issued,4)
                             if positive_issued else None,
        "negative_precision":round(negative_correct/negative_issued,4)
                             if negative_issued else None,
        "model_state":model,
        "proof_ceiling":"OFFLINE_PREQUENTIAL_REVIEWED_EXAMPLES_NOT_LIVE_PROOF",
    }
