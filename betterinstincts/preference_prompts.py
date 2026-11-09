"""Catalogued, opt-in Sims preference prompt judgment; no side effects.

Only a fresh selected-Sim dialog observation can lead to a proposed Yes/No
action. A follow-up OK requires a separately observed confirmation dialog.
Screen admission, visual target verification and actual input are separate.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "contracts" / "preference-prompts.v1.json"
MAX_BYTES = 32_768
ALLOWED_POLICY = frozenset({"POSITIVE", "NEGATIVE", "GOAL_ONLY"})


class PreferencePromptError(ValueError):
    pass


def load_catalog(path: Path = CATALOG) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise PreferencePromptError("PREFERENCE_CATALOG_UNSAFE")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.preference-prompts/v1":
        raise PreferencePromptError("PREFERENCE_CATALOG_SCHEMA_INVALID")
    topics = data.get("preferences")
    if not isinstance(topics, dict) or not topics:
        raise PreferencePromptError("PREFERENCE_CATALOG_EMPTY")
    for key, row in topics.items():
        if not isinstance(key, str) or not key or not isinstance(row, dict):
            raise PreferencePromptError("PREFERENCE_TOPIC_INVALID")
        if row.get("like") not in ALLOWED_POLICY or row.get("dislike") not in ALLOWED_POLICY:
            raise PreferencePromptError("PREFERENCE_POLICY_INVALID")
    return data


def _safe_id(value: object) -> bool:
    return (type(value) is str and 0 < len(value) <= 128
            and all(ch.isalnum() or ch in "._:-" for ch in value))


def evaluate_offer(
    offer: Mapping[str, object] | None,
    *,
    automation_opt_in: bool = False,
    player_directed: bool = False,
    known_game_build: bool = True,
    catalog: dict | None = None,
) -> dict:
    """Return an advisory decision, never a click permit.

    Missing provenance, unrecognised panel type or conflict with the human
    results in HOLD. No OCR, unverified substring or unknown game trait is
    promoted into an authorized interaction.
    """
    config = catalog if catalog is not None else load_catalog()
    result = {
        "schema": "betterinstincts.preference-prompt-assessment/v1",
        "decision": "HOLD",
        "reason": "OBSERVATION_UNVERIFIED",
        "steps": [],
        "control_permit": None,
        "proof_ceiling": config["proof_ceiling"],
    }
    if not isinstance(offer, Mapping):
        return result
    fields = ("sim_ref", "capture_ref", "topic_id", "offer_kind")
    if any(not _safe_id(offer.get(key)) for key in fields):
        return result
    if (offer.get("dialog_class") != "sim_preference_offer"
            or offer.get("dialog_stage") != "offer"
            or offer.get("scene") != "live"):
        return {**result, "reason": "WRONG_SCENE_OR_DIALOG_CLASS"}
    buttons = offer.get("visible_buttons")
    if not isinstance(buttons, (list, tuple)) or any(type(b) is not str for b in buttons):
        return {**result, "reason": "BUTTONS_UNVERIFIED"}
    if set(buttons) != {"YES", "NO"}:
        return {**result, "reason": "BUTTONS_UNVERIFIED"}
    if player_directed or offer.get("player_directed") is True:
        return {**result, "reason": "PLAYER_DIRECTED"}
    if not known_game_build:
        return {**result, "reason": "GAME_BUILD_UNVERIFIED"}
    if not automation_opt_in:
        return {**result, "reason": "AUTOMATION_NOT_OPTED_IN"}
    kind = offer["offer_kind"]
    if kind not in {"like", "dislike"}:
        return {**result, "reason": "UNKNOWN_OFFER_KIND"}
    topic = config["preferences"].get(offer["topic_id"])
    if not isinstance(topic, dict):
        return {**result, "reason": "UNKNOWN_PREFERENCE"}
    goals = offer.get("goal_tags", [])
    if not isinstance(goals, (list, tuple)) or any(not _safe_id(v) for v in goals):
        return {**result, "reason": "GOALS_UNVERIFIED"}
    policy = topic[kind]
    if policy == "GOAL_ONLY":
        positive_goals = set(topic.get(kind + "_goals", ()))
        if not positive_goals.intersection(goals):
            return {**result, "reason": "NO_MATCHING_SIM_GOAL"}
        positive = True
    else:
        positive = policy == "POSITIVE"
    decision = "ACCEPT" if positive else "DECLINE"
    return {
        **result,
        "decision": decision,
        "reason": "CATALOGUED_GOAL_ALIGNED" if policy == "GOAL_ONLY" else "CATALOGUED_HEURISTIC",
        "steps": ["YES", "OK"] if positive else ["NO"],
        "topic_id": offer["topic_id"],
        "offer_kind": kind,
        "sim_ref": offer["sim_ref"],
        "capture_ref": offer["capture_ref"],
        "requires_independent_stage_reobservation": bool(positive),
    }


def plan_stage(
    offer: Mapping[str, object],
    stage: str,
    *,
    automation_opt_in: bool,
    previous_receipt: Mapping[str, object] | None = None,
    player_directed: bool = False,
    known_game_build: bool = True,
    catalog: dict | None = None,
) -> dict:
    """Plan exactly one button, reusing the original offer's policy metadata.

    An OK-stage observation is intentionally NOT itself treated as a new offer.
    Its prior YES receipt and distinct capture are required to continue.
    """
    if not isinstance(offer, Mapping) or stage not in {"YES", "NO", "OK"}:
        raise PreferencePromptError("PREFERENCE_STAGE_INVALID")
    if stage == "OK":
        prior = previous_receipt
        if not isinstance(prior, Mapping) or prior.get("step") != "YES" or prior.get("state") != "INPUT_DISPATCHED":
            raise PreferencePromptError("OK_REQUIRES_PRIOR_YES_RECEIPT")
        if (offer.get("dialog_class") != "sim_preference_confirmation"
                or offer.get("dialog_stage") != "confirmation"
                or offer.get("scene") != "live"
                or offer.get("visible_buttons") != ["OK"]):
            raise PreferencePromptError("OK_DIALOG_NOT_REOBSERVED")
        if any(offer.get(key) != prior.get(key) for key in ("sim_ref", "topic_id", "offer_kind")):
            raise PreferencePromptError("OK_PROMPT_IDENTITY_CHANGED")
        if not _safe_id(offer.get("capture_ref")) or offer["capture_ref"] == prior.get("capture_ref"):
            raise PreferencePromptError("OK_REQUIRES_NEW_CAPTURE")
        if type(offer.get("captured_at_epoch_ms")) is not int or offer["captured_at_epoch_ms"] <= prior.get("captured_at_epoch_ms", 0):
            raise PreferencePromptError("OK_CAPTURE_NOT_NEWER")
        # The prior YES was only possible after a positive assessment.
        return {"state": "STAGE_READY", "step": "OK", "target_role": "OK",
                "sim_ref": offer["sim_ref"], "topic_id": offer["topic_id"],
                "offer_kind": offer["offer_kind"], "capture_ref": offer["capture_ref"],
                "control_permit": None, "proof_ceiling": "PLAN_ONLY_NOT_INPUT"}
    result = evaluate_offer(offer, automation_opt_in=automation_opt_in,
                            player_directed=player_directed,
                            known_game_build=known_game_build, catalog=catalog)
    if stage not in result["steps"] or stage == "OK":
        raise PreferencePromptError("STAGE_NOT_AUTHORIZED_BY_POLICY")
    return {"state": "STAGE_READY", "step": stage, "target_role": stage,
            "sim_ref": offer["sim_ref"], "topic_id": offer["topic_id"],
            "offer_kind": offer["offer_kind"], "capture_ref": offer["capture_ref"],
            "control_permit": None, "proof_ceiling": "PLAN_ONLY_NOT_INPUT"}
