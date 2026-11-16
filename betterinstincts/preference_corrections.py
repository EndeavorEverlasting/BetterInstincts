"""Policy and semantic navigation for changing an existing Sims preference."""
from __future__ import annotations

import json
from collections.abc import Mapping
from math import sqrt
from pathlib import Path
from statistics import mean, stdev

from betterinstincts.fixed_ui_click_map import resolve_target_xy
from betterinstincts.preference_prompts import _safe_id, load_catalog
from betterinstincts.ui_microsystems import plan_open_bottom_right_panel

CONTRACT = Path(__file__).resolve().parents[1] / "contracts/preference-corrections.v1.json"
IDENTITY = ("session_id", "process_id", "game_build", "save_ref", "sim_id")
TEXT_IDENTITY = tuple(key for key in IDENTITY if key != "process_id")
TARGET = ("family", "category", "topic_id")
MAX_CAPTURE_AGE_MS = 5_000


def _same_fields(left, right, fields):
    return all(type(left.get(key)) is type(right.get(key)) and left.get(key) == right.get(key)
               for key in fields)


def _activity_score(request, current, desired, config):
    """Compare attributed outcomes from independent matched activity exposures."""
    pairs = request.get("paired_outcomes")
    if not isinstance(pairs, list) or not config["min_independent_pairs"] <= len(pairs) <= config["max_pairs"]:
        return None
    weights = config["activity_weights"]
    captures, windows, differences = set(), set(), []
    for pair in pairs:
        if (not isinstance(pair, Mapping)
                or not _same_fields(pair, request, ("game_build", "save_ref", "sim_id", *TARGET))
                or pair.get("attributed_to_preference") is not True
                or pair.get("matched_conditions") is not True
                or pair.get("availability_unchanged") is not True
                or pair.get("current_value") != current
                or pair.get("candidate_value") != desired):
            return None
        pair_captures = (pair.get("current_receipt"), pair.get("candidate_receipt"))
        window = pair.get("window_ref")
        if (not all(_safe_id(ref) for ref in (*pair_captures, window))
                or pair_captures[0] == pair_captures[1]
                or captures.intersection(pair_captures) or window in windows):
            return None
        captures.update(pair_captures)
        windows.add(window)
        before, after = pair.get("current_outcome"), pair.get("candidate_outcome")
        for outcome in (before, after):
            if (not isinstance(outcome, Mapping) or outcome.keys() != weights.keys()
                    or any(type(score) not in (int, float) or not -1 <= score <= 1
                           for score in outcome.values())):
                return None
        # A productive preference cannot trade away protected needs.
        if after["needs"] < before["needs"]:
            return None
        differences.append(sum(weight * (after[key] - before[key])
                               for key, weight in weights.items()))
    count = len(differences)
    observed = mean(differences)
    uncertainty = stdev(differences) / sqrt(count)
    return {
        "pairs": count,
        "mean_gain": observed,
        "standard_error": uncertainty,
        "conservative_gain": (observed - uncertainty) * count / (count + config["prior_sample_count"]),
        "minimum_gain": config["min_conservative_gain"],
    }


def _change_reason(request, config, family, current, desired):
    if request.get("reason") == "mistake":
        mistake = request.get("mistake")
        if (not isinstance(mistake, Mapping)
                or not _same_fields(mistake, request, (*IDENTITY, *TARGET, "pref_revision"))
                or not _safe_id(mistake.get("receipt_ref"))
                or mistake.get("mistaken_value") != current
                or mistake.get("restore_value") != desired):
            return "MISTAKE_RECEIPT_REQUIRED", None
        if (mistake.get("source") == "operator_correction"
                or (mistake.get("source") == "automation_receipt"
                    and request.get("preference_owner") == "automation")):
            return None, None
        return "PLAYER_INTENT_PROTECTED", None
    if request.get("reason") != "repeated_behavior":
        return "CORRECTION_REASON_REQUIRED", None
    if request.get("preference_owner") != "automation":
        return "PLAYER_INTENT_PROTECTED", None
    if family != "likes_dislikes" or request.get("category") != "activity":
        return "ACTIVITY_POLICY_UNAVAILABLE", None
    try:
        activities = load_catalog()["preferences"]
    except (OSError, ValueError):
        return "ACTIVITY_CATALOG_UNAVAILABLE", None
    if request.get("topic_id") not in activities:
        return "ACTIVITY_POLICY_UNAVAILABLE", None
    score = _activity_score(request, current, desired, config)
    if score is None:
        return "ATTRIBUTED_COMPARISON_REQUIRED", None
    if score["conservative_gain"] < score["minimum_gain"]:
        return "PRODUCTIVITY_GAIN_INSUFFICIENT", score
    return None, score


def _preceding_action(request, observed, receipt, target):
    return (isinstance(receipt, Mapping)
            and _same_fields(request, receipt, ("request_ref", *IDENTITY, *TARGET, "desired_value"))
            and receipt.get("target") == target
            and receipt.get("state") == "INPUT_DISPATCHED"
            and _safe_id(receipt.get("capture_ref"))
            and receipt["capture_ref"] != observed["capture_ref"]
            and type(receipt.get("captured_at_ms")) is int
            and 0 <= receipt["captured_at_ms"] < observed["captured_at_ms"])


def _next_target(request, observed, spec):
    family, category, topic = (request[key] for key in TARGET)
    category_target = f"cas.{family}.category.{category}"
    tile = f"cas.{family}.{category}.{topic}"
    current, desired = request["current_value"], request["desired_value"]
    stage = observed.get("stage")
    if stage == "live" and observed.get("simology_panel_open") is False:
        hotkey = plan_open_bottom_right_panel("simology")
        mouse = resolve_target_xy({}, "live.panel_simology")
        return "live.panel_simology", {
            "hotkey": hotkey["chord"],
            "requires_live_hotkey_arm": hotkey["requires_live_hotkey_arm"],
            "mouse_reference": {"viewport": [1920, 1080], "client_xy": mouse["client_xy"]},
        }
    if stage == "simology" or (stage == "live" and observed.get("simology_panel_open") is True):
        # Relationship Preferences has a second button with the same label.
        return "live.simology.preferences.enter_create_a_sim", {
            "label": "Enter Create a Sim",
            "within": ["Preferences", "Likes and Dislikes"],
        }
    if stage == "live":
        return None, {"reason": "SIMOLOGY_PANEL_VISIBILITY_UNVERIFIED"}
    if stage == "cas_existing_household":
        return "cas.preferences", {"label": "Select Preferences"}
    if stage == "cas_preferences":
        return spec["target"], {"label": spec["label"]}
    if stage == "cas_preference_categories":
        if observed.get("family") != family:
            return "cas.preferences.back_to_families", {}
        return category_target, {"labels": spec["categories"][category]}
    if stage == "cas_preference_tiles":
        if not _same_fields(observed, request, ("family", "category")):
            return "cas.preferences.back_to_categories", {}
        if observed.get("topic_id") != topic or observed.get("value") not in spec["values"]:
            return None, {"reason": "TARGET_ROW_NOT_OBSERVED", "search_container": category_target}
        value = observed["value"]
        clear = f"{tile}.clear.{current}"
        select = f"{tile}.select.{desired}"
        last = request.get("previous_action")
        if value == desired:
            if not _preceding_action(request, observed, last, clear if desired == "neutral" else select):
                return None, {"reason": "STAGED_EDIT_READBACK_REQUIRED"}
            if observed.get("other_cas_edits_detected") is not False:
                return None, {"reason": "CAS_EDIT_SCOPE_UNVERIFIED"}
            return "cas.confirm_existing_household_preferences", {}
        if value == current:
            action = select if current == "neutral" else clear
            if isinstance(last, Mapping) and last.get("target") == action:
                return None, {"reason": "PREVIOUS_EDIT_RECONCILIATION_REQUIRED"}
            return action, {}
        if value == "neutral" and _preceding_action(request, observed, last, clear):
            return select, {}
        return None, {"reason": "PREFERENCE_VALUE_CHANGED"}
    return None, {"reason": "UNKNOWN_PREFERENCE_SCENE"}


def evaluate_correction(request, *, player_directed=False, automation_opt_in=False,
                        known_game_build=False):
    """Recommend one next action or report why fresh evidence is required."""
    result = {"state": "HOLD", "control_permit": None, "proof_ceiling": "POLICY_AND_NAVIGATION_PLAN_ONLY"}

    def hold(reason, **details):
        return {**result, "reason": reason, **details}

    config = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if not isinstance(request, Mapping):
        return hold("CORRECTION_REQUEST_INVALID")
    if player_directed:
        return hold("PLAYER_DIRECTED")
    if not automation_opt_in or not known_game_build:
        return hold("OPT_IN_AND_EXACT_BUILD_REQUIRED")
    if (not all(_safe_id(request.get(key)) for key in ("request_ref", "pref_revision",
                                                      *TARGET, *TEXT_IDENTITY))
            or type(request.get("process_id")) is not int or request["process_id"] <= 0):
        return hold("TARGET_IDENTITY_UNVERIFIED")
    family, category = request["family"], request["category"]
    spec = config["families"].get(family)
    current, desired = request.get("current_value"), request.get("desired_value")
    if (spec is None or category not in spec["categories"]
            or current not in spec["values"] or desired not in spec["values"]):
        return hold("UNKNOWN_PREFERENCE_CATEGORY_OR_VALUE")
    if current == desired:
        return hold("NO_CORRECTION_NEEDED")
    reason, score = _change_reason(request, config, family, current, desired)
    if reason:
        return hold(reason, score=score)
    observed = request.get("observation")
    if not isinstance(observed, Mapping) or not _same_fields(request, observed, IDENTITY):
        return hold("CURRENT_SIM_SAVE_SESSION_REQUIRED")
    now, captured = request.get("now_ms"), observed.get("captured_at_ms")
    if (type(now) is not int or type(captured) is not int
            or not 0 <= now - captured <= MAX_CAPTURE_AGE_MS
            or not _safe_id(observed.get("capture_ref"))):
        return hold("FRESH_CAPTURE_REQUIRED")
    if spec.get("pack") and observed.get("lovestruck_attested") is not True:
        return hold("LOVESTRUCK_AVAILABILITY_REQUIRED")
    if observed.get("stage") == "live_readback":
        confirm = request.get("confirmation")
        if (not isinstance(confirm, Mapping)
                or not _preceding_action(request, observed, confirm, "cas.confirm_existing_household_preferences")
                or not _same_fields(request, observed, TARGET)
                or observed.get("authorized_lab_save") is not True
                or observed.get("stage_verified") is not True
                or observed.get("value") != desired
                or not _safe_id(observed.get("pref_revision"))
                or observed["pref_revision"] == request["pref_revision"]):
            return hold("LIVE_EFFECT_READBACK_REQUIRED", score=score)
        return {**result, "state": "OBSERVED_DESIRED_VALUE", "score": score,
                "capture_ref": observed["capture_ref"], "request_ref": request["request_ref"]}
    if (observed.get("authorized_lab_save") is not True
            or observed.get("paused") is not True
            or observed.get("stage_verified") is not True
            or observed.get("modal_open") is not False
            or observed.get("pref_revision") != request["pref_revision"]):
        return hold("FRESH_PAUSED_LAB_SCENE_REQUIRED", score=score)
    stage = observed.get("stage")
    if (isinstance(stage, str) and stage.startswith("cas_")
            and observed.get("existing_household_verified") is not True):
        return hold("EXISTING_HOUSEHOLD_CAS_REQUIRED", score=score)
    if request.get("confirmation") is not None:
        return hold("LIVE_EFFECT_READBACK_REQUIRED", score=score)
    target, details = _next_target(request, observed, spec)
    if target is None:
        return hold(score=score, **details)
    reference = config["screenshot_reference"]
    anchor = reference["anchors"].get(target)
    if anchor is not None:
        details["mouse_reference"] = {"viewport": reference["viewport"], "client_xy": anchor}
    elif target in ("cas.attraction.category.way_of_life", "cas.attraction.category.fashion"):
        details["reference_location"] = reference["attraction_category_layout"][category]
    return {
        **result,
        "state": "NEXT_TARGET",
        "request_ref": request["request_ref"],
        "capture_ref": observed["capture_ref"],
        "score": score,
        "target": target,
        **details,
        "requires_fresh_target_hitbox": True,
        "requires_fresh_observation_after_input": True,
    }
