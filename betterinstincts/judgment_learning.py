"""Reviewed demonstration -> contextual first-order Markov suggestions.

Offline advisory learner. No Sims hooks, polling, background tasks, SendInput,
user directories, raw captures, network, or automatic learning from clicks.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Mapping, Sequence

SCHEMA = "betterinstincts.judgment-learning/v1"
EXAMPLE_SCHEMA = "betterinstincts.judgment-example/v1"
QUERY_SCHEMA = "betterinstincts.judgment-query/v1"
PATCH_RE = re.compile(r"^[0-9]+(?:\.[0-9]+){3}$")
MAX_EXAMPLES = 256
MAX_CELLS = 512
CONTEXT_FIELDS = ("scenario", "need_state", "scene", "previous_action", "style")
CHOICES = {
    "scenario": {"needs", "event_social", "leisure", "income", "skills", "career"},
    "need_state": {"critical", "low", "stable", "unknown"},
    "scene": {"live", "event", "map", "build_buy", "unknown"},
    "previous_action": {"none", "wait", "eat", "rest", "sleep", "socialize",
                        "sit_and_chat_here", "travel_home", "practice_skill", "other"},
    "style": {"social", "solitary", "balanced", "unknown"},
}
ACTIONS = {
    "eat", "rest", "sleep", "use_toilet", "wash", "socialize",
    "sit_and_chat_here", "travel_home", "practice_skill", "wait",
    "play_hobby", "event_goal", "work", "other",
}
MIN_SUPPORT = 3
MIN_HELPFUL = 3
MIN_HELPFUL_RATE = 0.75


class JudgmentLearningError(ValueError):
    pass


def _patch(value: object) -> str:
    if not isinstance(value, str) or not PATCH_RE.fullmatch(value):
        raise JudgmentLearningError("EXACT_PATCH_REQUIRED")
    return value


def _context(value: object) -> dict:
    if not isinstance(value, dict) or set(value) != set(CONTEXT_FIELDS):
        raise JudgmentLearningError("CONTEXT_FIELDS_REQUIRED")
    for field in CONTEXT_FIELDS:
        if not isinstance(value[field], str) or value[field] not in CHOICES[field]:
            raise JudgmentLearningError("UNRECOGNIZED_CONTEXT:" + field)
    return {field: value[field] for field in CONTEXT_FIELDS}


def _action(value: object) -> str:
    if not isinstance(value, str) or value not in ACTIONS:
        raise JudgmentLearningError("UNRECOGNIZED_ACTION")
    return value


def _example(value: object) -> dict:
    # A reviewed, bounded semantic event, not passive input logging.
    keys = {"schema", "game_version", "platform", "context", "action",
            "outcome", "operator_reviewed", "opt_in", "observation_ref"}
    if not isinstance(value, dict) or set(value) != keys:
        raise JudgmentLearningError("UNREVIEWED_OR_EXTRA_EVENT_FIELDS")
    if value["schema"] != EXAMPLE_SCHEMA:
        raise JudgmentLearningError("INVALID_EXAMPLE_SCHEMA")
    if value["operator_reviewed"] is not True or value["opt_in"] is not True:
        raise JudgmentLearningError("EXPLICIT_REVIEW_AND_OPT_IN_REQUIRED")
    ref = value["observation_ref"]
    if (not isinstance(ref, str)
            or not re.fullmatch(r"capture:[A-Za-z0-9_-]{3,64}", ref)):
        raise JudgmentLearningError("SANITIZED_OBSERVATION_REF_REQUIRED")
    if value["platform"] not in ("windows", "linux", "macos"):
        raise JudgmentLearningError("UNSUPPORTED_PLATFORM")
    if value["outcome"] not in ("helpful", "harmful"):
        raise JudgmentLearningError("REVIEWED_OUTCOME_REQUIRED")
    return {"game_version": _patch(value["game_version"]),
            "platform": value["platform"], "context": _context(value["context"]),
            "action": _action(value["action"]), "outcome": value["outcome"]}


def _profile(value: Mapping) -> tuple[str, str]:
    if not isinstance(value, Mapping):
        raise JudgmentLearningError("INVALID_PROFILE")
    v = _patch(value.get("game_version"))
    platform = value.get("platform")
    if platform not in ("windows", "linux", "macos"):
        raise JudgmentLearningError("UNSUPPORTED_PLATFORM")
    return v, platform


def _key(context: Mapping) -> tuple[str, ...]:
    return tuple(context[field] for field in CONTEXT_FIELDS)


def _validate_model(value: Mapping) -> dict:
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise JudgmentLearningError("INVALID_MODEL_SCHEMA")
    patch, platform = _profile(value)
    counts = value.get("counts")
    if not isinstance(counts, list) or len(counts) > MAX_CELLS:
        raise JudgmentLearningError("MODEL_TOO_LARGE")
    seen = set()
    for row in counts:
        if not isinstance(row, dict) or set(row) != {"context", "action", "helpful", "harmful"}:
            raise JudgmentLearningError("INVALID_MODEL_ROW")
        key = (_key(_context(row["context"])), _action(row["action"]))
        if key in seen:
            raise JudgmentLearningError("DUPLICATE_MODEL_ROW")
        seen.add(key)
        for field in ("helpful", "harmful"):
            if (isinstance(row[field], bool) or not isinstance(row[field], int)
                    or not 0 <= row[field] <= MAX_EXAMPLES):
                raise JudgmentLearningError("INVALID_MODEL_COUNT")
    return {"schema": SCHEMA, "game_version": patch, "platform": platform,
            "counts": counts, "proof_ceiling": "OFFLINE_REVIEWED_DEMONSTRATIONS_ONLY"}


def learn(examples: Sequence[Mapping], *, game_version: str,
          platform: str, prior: Mapping | None = None) -> dict:
    """Update bounded contextual transition counts from reviewed examples only."""
    patch, os_name = _profile({"game_version": game_version, "platform": platform})
    if not isinstance(examples, list) or not 1 <= len(examples) <= MAX_EXAMPLES:
        raise JudgmentLearningError("EXAMPLE_BATCH_LIMIT")
    counts = defaultdict(lambda: [0, 0])
    if prior is not None:
        previous = _validate_model(prior)
        if (previous["game_version"], previous["platform"]) != (patch, os_name):
            raise JudgmentLearningError("PATCH_PROFILE_MISMATCH")
        for row in previous["counts"]:
            counts[(_key(row["context"]), row["action"])] = [row["helpful"], row["harmful"]]
    seen_refs = set()
    for raw in examples:
        event = _example(raw)
        if (event["game_version"], event["platform"]) != (patch, os_name):
            raise JudgmentLearningError("PATCH_PROFILE_MISMATCH")
        ref = raw["observation_ref"]
        if ref in seen_refs:
            raise JudgmentLearningError("DUPLICATE_OBSERVATION_IN_BATCH")
        seen_refs.add(ref)
        cell = counts[(_key(event["context"]), event["action"])]
        cell[0 if event["outcome"] == "helpful" else 1] += 1
        if sum(cell) > MAX_EXAMPLES:
            raise JudgmentLearningError("MODEL_CELL_LIMIT")
        if len(counts) > MAX_CELLS:
            raise JudgmentLearningError("MODEL_TOO_LARGE")
    rows = [
        {"context": dict(zip(CONTEXT_FIELDS, key)), "action": action,
         "helpful": n[0], "harmful": n[1]}
        for (key, action), n in sorted(counts.items())
    ]
    return _validate_model({"schema": SCHEMA, "game_version": patch,
                            "platform": os_name, "counts": rows})


def recommend(model: Mapping, query: Mapping) -> dict:
    """Advisory only: exact context & action availability, otherwise ABSTAIN."""
    baseline = {"state": "ABSTAIN", "suggested_action": None,
                "execute_clicks": False,
                "proof_ceiling": "OFFLINE_REVIEWED_DEMONSTRATIONS_ONLY"}
    approved = _validate_model(model)
    if not isinstance(query, dict) or set(query) != {
        "schema", "game_version", "platform", "context", "available_actions",
        "player_directed", "player_active", "scene_verified",
    } or query["schema"] != QUERY_SCHEMA:
        raise JudgmentLearningError("INVALID_QUERY_SCHEMA")
    if (_patch(query["game_version"]), query["platform"]) != (
            approved["game_version"], approved["platform"]):
        return {**baseline, "reason": "PATCH_PROFILE_MISMATCH"}
    context = _context(query["context"])
    available = query["available_actions"]
    if (not isinstance(available, list) or not 0 <= len(available) <= 16
            or len(set(available)) != len(available)):
        raise JudgmentLearningError("INVALID_AVAILABLE_ACTIONS")
    for action in available:
        _action(action)
    for flag in ("player_directed", "player_active", "scene_verified"):
        if type(query[flag]) is not bool:
            raise JudgmentLearningError("INVALID_QUERY_FLAG")
    if query["player_directed"] or query["player_active"]:
        return {**baseline, "reason": "PLAYER_FIRST"}
    if not query["scene_verified"]:
        return {**baseline, "reason": "SCENE_UNVERIFIED"}
    if not available:
        return {**baseline, "reason": "NO_AVAILABLE_ACTION"}
    eligible = []
    for row in approved["counts"]:
        if row["context"] != context or row["action"] not in available:
            continue
        support = row["helpful"] + row["harmful"]
        rate = row["helpful"] / support if support else 0.0
        if support >= MIN_SUPPORT and row["helpful"] >= MIN_HELPFUL and rate >= MIN_HELPFUL_RATE:
            eligible.append((rate, row["helpful"], row["action"], support))
    if not eligible:
        return {**baseline, "reason": "INSUFFICIENT_REVIEWED_EVIDENCE"}
    eligible.sort(reverse=True)
    # Multiple equally supported actions represent authentic uncertainty;
    # do not optimize away variety using lexical tie-breaking.
    if len(eligible) > 1 and eligible[0][:2] == eligible[1][:2]:
        return {**baseline, "reason": "AMBIGUOUS_PLAYER_PREFERENCE"}
    top = eligible[0]
    return {**baseline, "state": "ADVISORY_ONLY", "suggested_action": top[2],
            "reason": "REVIEWED_CONTEXTUAL_TRANSITION",
            "helpful_rate": round(top[0], 4), "helpful_count": top[1],
            "support": top[3], "model": "FIRST_ORDER_CONTEXTUAL_COUNTS"}


def prequential_evaluate(examples: Sequence[Mapping], *, game_version: str,
                         platform: str) -> dict:
    """Predict on each event BEFORE learning from it; abstention is counted."""
    if not isinstance(examples, list) or not 1 <= len(examples) <= MAX_EXAMPLES:
        raise JudgmentLearningError("EXAMPLE_BATCH_LIMIT")
    model = {"schema": SCHEMA, "game_version": game_version, "platform": platform,
             "counts": []}
    predictions = correct = helpful = 0
    for raw in examples:
        event = _example(raw)
        if (event["game_version"], event["platform"]) != (game_version, platform):
            raise JudgmentLearningError("PATCH_PROFILE_MISMATCH")
        query = {"schema": QUERY_SCHEMA, "game_version": game_version,
                 "platform": platform, "context": event["context"],
                 "available_actions": sorted(ACTIONS),
                 "player_directed": False, "player_active": False,
                 "scene_verified": True}
        predicted = recommend(model, query)
        if event["outcome"] == "helpful":
            helpful += 1
            if predicted["state"] == "ADVISORY_ONLY":
                predictions += 1
                correct += int(predicted["suggested_action"] == event["action"])
        model = learn([raw], game_version=game_version, platform=platform, prior=model)
    return {"schema": "betterinstincts.judgment-evaluation/v1",
            "reviewed_examples": len(examples), "helpful_examples": helpful,
            "suggestions_issued": predictions, "correct_helpful_actions": correct,
            "coverage": round(predictions / helpful, 4) if helpful else 0.0,
            "precision_when_issued": round(correct / predictions, 4) if predictions else None,
            "model": model, "proof_ceiling": "OFFLINE_PREQUENTIAL_NOT_GAME_PROOF"}
