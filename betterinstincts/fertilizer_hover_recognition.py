"""Recognize user/host-supplied *semantic* hover evidence for Sims fertilizer.

This deliberately does not screenshot, OCR, move the cursor, query the game,
or grant any in-game effect. A calibrated sensor may supply the text and the
pointed/highlighted object reference; a user screenshot is identity context
only and cannot stand in for a current verified game-host observation.
"""
from __future__ import annotations

from collections.abc import Mapping

SCHEMA = "betterinstincts.fertilizer-hover/v1"
SOURCES = {"USER_SCREENSHOT", "HOST_VERIFIED_HOVER"}
SUPER_FERTILIZER_TITLE = "SUPER FERTILIZER"


class FertilizerHoverError(ValueError):
    """Malformed or disassociated tooltip-to-ground-item observation."""


def _ref(value: object) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= 120 and all(
        c.isalnum() or c in "_:.-" for c in value
    )


def _text(value: object, limit: int) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= limit:
        raise FertilizerHoverError("FERTILIZER_HOVER_TEXT_INVALID")
    if any(ord(c) < 32 and c not in "\r\n\t" for c in value):
        raise FertilizerHoverError("FERTILIZER_HOVER_TEXT_INVALID")
    return " ".join(value.split())


def recognize_super_fertilizer_hover(
    observation: Mapping, *, capture_ref: str, item_ref: str
) -> dict:
    """Classify an anchored English tooltip; no price, eligibility or actuation.

    A pointed *and* highlighted ground object distinguishes an in-world hover
    from a stray HUD tooltip. HOST_VERIFIED_HOVER is needed for a later policy
    candidate; actual affordance and fertilizer eligibility are separate.
    """
    if not isinstance(observation, Mapping) or observation.get("schema") != SCHEMA:
        raise FertilizerHoverError("FERTILIZER_HOVER_SCHEMA_INVALID")
    if not _ref(capture_ref) or not _ref(item_ref):
        raise FertilizerHoverError("FERTILIZER_HOVER_REF_INVALID")
    if observation.get("capture_ref") != capture_ref:
        raise FertilizerHoverError("FERTILIZER_HOVER_CAPTURE_MISMATCH")
    if observation.get("pointer_target_ref") != item_ref or observation.get(
        "highlighted_target_ref"
    ) != item_ref or observation.get("tooltip_attached_to_target") is not True:
        raise FertilizerHoverError("FERTILIZER_HOVER_TARGET_UNBOUND")
    source = observation.get("source")
    if source not in SOURCES:
        raise FertilizerHoverError("FERTILIZER_HOVER_SOURCE_INVALID")
    title = _text(observation.get("title"), 100)
    description = _text(observation.get("description"), 300)
    displayed_value = observation.get("displayed_value")
    if displayed_value is not None:
        displayed_value = _text(displayed_value, 32)
    recognized = (
        title.casefold() == SUPER_FERTILIZER_TITLE.casefold()
        and "special fertilizer" in description.casefold()
    )
    return {
        "schema": "betterinstincts.fertilizer-hover-result/v1",
        "capture_ref": capture_ref, "target_ref": item_ref,
        "recognized": recognized,
        "item_kind": "SUPER_FERTILIZER" if recognized else None,
        "displayed_value": displayed_value,
        "displayed_value_is_purchase_price": False,
        "identity_candidate_only": True,
        "host_reobservation_required": source != "HOST_VERIFIED_HOVER",
        "dispatch_authorized": False,
        "proof_ceiling": "HOVER_OBJECT_IDENTITY_NOT_ELIGIBILITY_OR_GAME_EFFECT",
    }
