"""Catalogued, opt-in Sims preference prompt judgment; no side effects.

Only a fresh verified dialog observation can lead to a proposed Yes/No
action. A follow-up OK requires a separately observed confirmation dialog.
Screen admission, visual target verification and actual input are separate.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from betterinstincts.preference_recipient import (
    RecipientEvidenceError, compare_recipient_continuations,
)

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "contracts" / "preference-prompts.v1.json"
MAX_BYTES = 32_768
CHASED_BY_DEATH = "chased_by_death"
TRAIT_OFFER = "sim_trait_offer"
ALLOWED_POLICY = frozenset({"POSITIVE", "NEGATIVE", "GOAL_ONLY"})


class PreferencePromptError(ValueError):
    pass


def load_catalog(path: Path = CATALOG) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise PreferencePromptError("PREFERENCE_CATALOG_UNSAFE")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != "betterinstincts.preference-prompts/v1":
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


def is_trait_offer(offer: Mapping) -> bool:
    return (offer.get("dialog_class") == TRAIT_OFFER
            or offer.get("topic_id") == CHASED_BY_DEATH
            or any(isinstance(offer.get(key), str)
                   and offer[key].strip().casefold() == "chased by death"
                   for key in ("title", "trait_label")))


def _chased_by_death(offer, result, rule, *, player_directed, build_known, opted_in):
    if (not isinstance(rule, Mapping) or rule.get("label") != "Chased by Death"
            or rule.get("button_labels") != {"YES": "Yes", "NO": "No thanks!"}):
        return {**result, "reason": "TRAIT_DECLINE_RULE_INVALID"}
    if (
        offer.get("topic_id"), offer.get("offer_kind"), offer.get("dialog_class"),
        offer.get("dialog_stage"), offer.get("scene"),
    ) != (CHASED_BY_DEATH, "add_trait", TRAIT_OFFER, "offer", "live"):
        return {**result, "reason": "UNVERIFIED_TRAIT_OFFER"}
    if any(not isinstance(offer.get(key), str) or offer[key].strip().casefold() != rule["label"].casefold()
           for key in ("title", "trait_label")):
        return {**result, "reason": "TRAIT_IDENTITY_MISMATCH"}
    labels = offer.get("button_labels")
    buttons = offer.get("visible_buttons")
    if (not isinstance(labels, Mapping) or dict(labels) != rule["button_labels"]
            or not isinstance(buttons, (list, tuple)) or len(buttons) != 2
            or any(type(button) is not str for button in buttons)
            or set(buttons) != labels.keys()):
        return {**result, "reason": "TRAIT_BUTTON_LABELS_UNVERIFIED"}
    if player_directed or offer.get("player_directed") is not False:
        return {**result, "reason": "PLAYER_DIRECTED"}
    if build_known is not True:
        return {**result, "reason": "GAME_BUILD_UNVERIFIED"}
    if opted_in is not True:
        return {**result, "reason": "AUTOMATION_NOT_OPTED_IN"}
    return {
        **result, "decision": "DECLINE", "reason": "OPERATOR_CHASED_BY_DEATH_DECLINE",
        "steps": ["NO"], "target_label": rule["button_labels"]["NO"],
        "response_route": "NATIVE_ONLY", "topic_id": CHASED_BY_DEATH,
        "offer_kind": "add_trait", "sim_ref": offer["sim_ref"],
        "capture_ref": offer["capture_ref"], "requires_independent_stage_reobservation": False,
    }


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
    if is_trait_offer(offer):
        return _chased_by_death(
            offer, result, config.get("trait_declines", {}).get(CHASED_BY_DEATH),
            player_directed=player_directed, build_known=known_game_build, opted_in=automation_opt_in,
        )
    if (offer.get("dialog_class") != "sim_preference_offer"
            or offer.get("dialog_stage") != "offer"
            or offer.get("scene") != "live"):
        return {**result, "reason": "WRONG_SCENE_OR_DIALOG_CLASS"}
    buttons = offer.get("visible_buttons")
    if not isinstance(buttons, (list, tuple)) or any(type(b) is not str for b in buttons):
        return {**result, "reason": "BUTTONS_UNVERIFIED"}
    if len(buttons) != 2 or set(buttons) != {"YES", "NO"}:
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
    continuation = None
    if offer["topic_id"] == "video_gaming":
        # This native prompt is scored for its recipient, which may differ
        # from the Sim currently selected in the HUD.
        if (not _safe_id(offer.get("recipient_sim_id"))
                or "recipient_snapshot" not in offer
                or "continuation_model" not in offer):
            return {**result, "reason": "LIVE_RECIPIENT_SNAPSHOT_REQUIRED"}
        try:
            continuation = compare_recipient_continuations(
                offer, offer["continuation_model"]
            )
        except RecipientEvidenceError as exc:
            return {**result, "reason": str(exc)}
        except (ValueError, KeyError, TypeError):
            return {**result, "reason": "RECIPIENT_CONTINUATION_INVALID"}
        scores = continuation["scores"]
        advantage = scores["YES"] - scores["NO"]
        # Avoid an unobserved/indifferent answer and false certainty from rounding.
        if abs(advantage) <= 0.000001:
            return {**result, "reason": "PREFERENCE_EFFECT_INDIFFERENT"}
        positive = advantage > 0
        reason = "RECIPIENT_YES_ADVANTAGE" if positive else "RECIPIENT_NO_ADVANTAGE"
    else:
        policy = topic[kind]
        if policy == "GOAL_ONLY":
            positive_goals = set(topic.get(kind + "_goals", ()))
            if not positive_goals.intersection(goals):
                return {**result, "reason": "NO_MATCHING_SIM_GOAL"}
            positive = True
        else:
            positive = policy == "POSITIVE"
        reason = "CATALOGUED_GOAL_ALIGNED" if policy == "GOAL_ONLY" else "CATALOGUED_HEURISTIC"
    decision = "ACCEPT" if positive else "DECLINE"
    return {
        **result,
        "decision": decision,
        "reason": reason,
        "steps": ["YES", "OK"] if positive else ["NO"],
        "topic_id": offer["topic_id"],
        "offer_kind": kind,
        "sim_ref": offer["sim_ref"],
        "capture_ref": offer["capture_ref"],
        "requires_independent_stage_reobservation": bool(positive),
        **({
            "recipient_sim_id": continuation["recipient_sim_id"],
            "recipient_state_revision": continuation["state_revision"],
            "continuation": continuation,
        } if continuation is not None else {}),
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
        if is_trait_offer(offer) or (isinstance(previous_receipt, Mapping)
                                    and is_trait_offer(previous_receipt)):
            raise PreferencePromptError("TRAIT_OFFER_HAS_NO_CONFIRMATION_STEP")
        prior = previous_receipt
        if not isinstance(prior, Mapping) or prior.get("step") != "YES" or prior.get("state") != "INPUT_DISPATCHED":
            raise PreferencePromptError("OK_REQUIRES_PRIOR_YES_RECEIPT")
        if (offer.get("dialog_class") != "sim_preference_confirmation"
                or offer.get("dialog_stage") != "confirmation"
                or offer.get("scene") != "live"
                or offer.get("visible_buttons") != ["OK"]):
            raise PreferencePromptError("OK_DIALOG_NOT_REOBSERVED")
        if any(offer.get(key) != prior.get(key) for key in
               ("sim_ref", "recipient_sim_id", "topic_id", "offer_kind")):
            raise PreferencePromptError("OK_PROMPT_IDENTITY_CHANGED")
        if offer.get("topic_id") == "video_gaming" and not _safe_id(offer.get("recipient_sim_id")):
            raise PreferencePromptError("OK_PROMPT_IDENTITY_CHANGED")
        if not _safe_id(offer.get("capture_ref")) or offer["capture_ref"] == prior.get("capture_ref"):
            raise PreferencePromptError("OK_REQUIRES_NEW_CAPTURE")
        if type(offer.get("captured_at_epoch_ms")) is not int or offer["captured_at_epoch_ms"] <= prior.get("captured_at_epoch_ms", 0):
            raise PreferencePromptError("OK_CAPTURE_NOT_NEWER")
        # The prior YES was only possible after a positive assessment.
        return {"state": "STAGE_READY", "step": "OK", "target_role": "OK",
                "sim_ref": offer["sim_ref"],
                **({"recipient_sim_id": offer["recipient_sim_id"]} if "recipient_sim_id" in offer else {}),
                "topic_id": offer["topic_id"],
                "offer_kind": offer["offer_kind"], "capture_ref": offer["capture_ref"],
                "control_permit": None, "proof_ceiling": "PLAN_ONLY_NOT_INPUT"}
    result = evaluate_offer(offer, automation_opt_in=automation_opt_in,
                            player_directed=player_directed,
                            known_game_build=known_game_build, catalog=catalog)
    if stage not in result["steps"] or stage == "OK":
        raise PreferencePromptError("STAGE_NOT_AUTHORIZED_BY_POLICY")
    return {"state": "STAGE_READY", "step": stage, "target_role": stage,
            **({"response_route": result["response_route"], "target_label": result["target_label"]}
               if result.get("response_route") == "NATIVE_ONLY" else {}),
            "sim_ref": offer["sim_ref"],
            **({"recipient_sim_id": result["recipient_sim_id"]} if "recipient_sim_id" in result else {}),
            "topic_id": offer["topic_id"],
            "offer_kind": offer["offer_kind"], "capture_ref": offer["capture_ref"],
            "control_permit": None, "proof_ceiling": "PLAN_ONLY_NOT_INPUT"}
