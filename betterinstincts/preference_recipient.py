"""Strict native offer-recipient identity and shared-continuation comparator.

Offline policy only: consumes a caller-produced, fresh EA_NATIVE event snapshot,
never opens disk saves/generated.zip, injects game input or resumes the queue.
The same evidence-bound activity graph is evaluated for YES and NO; ONLY
bounded, separately evidenced preference effects can differ.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import math
import re

from betterinstincts.decision_horizon import (
    DecisionHorizonError, allocate_continuous_time, optimize_activity_plan,
)

BUILD = "1.121.361.1020"
SCHEMA = "betterinstincts.preference-recipient-snapshot/v1"
PROOF = "OFFLINE_RECIPIENT_COUNTERFACTUAL_NOT_NATIVE_RESPONSE_OR_RESUMPTION"
REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")
MAX_SKEW_MS = 2000
MAX_EFFECTS = 24
ALLOWED_DELTAS = frozenset(("need_delta", "skill_delta", "mood_delta", "money_delta"))


class RecipientEvidenceError(ValueError):
    pass


def _ref(value: object) -> bool:
    return isinstance(value, str) and REF.fullmatch(value) is not None


def _sim_id(value: object) -> bool:
    """Use exact uint64 decimal *text*: never coerce via lossy JS float."""
    return (type(value) is str and value.isascii() and value.isdecimal()
            and value[0] != "0" and len(value) <= 20
            and 0 < int(value) <= (1 << 64) - 1)


def _num(value: object, low: float, high: float) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


def _observed_map(value: object, low: float, high: float, limit: int) -> bool:
    return (isinstance(value, Mapping) and 1 <= len(value) <= limit
            and all(_ref(k) and _num(v, low, high) for k, v in value.items()))


def _traits(value: object) -> bool:
    return (isinstance(value, list) and len(value) <= 48
            and all(_ref(t) for t in value) and len(set(value)) == len(value))


def _live_recipient(offer: Mapping, model: Mapping) -> tuple[str, Mapping, dict]:
    sid = offer.get("recipient_sim_id")
    if not _sim_id(sid):
        raise RecipientEvidenceError("RECIPIENT_SIM_ID_REQUIRED")
    live = offer.get("recipient_snapshot")
    if (not isinstance(live, Mapping) or live.get("schema") != SCHEMA
            or live.get("source") != "EA_NATIVE"
            or live.get("live_read_verified") is not True
            or live.get("motives_complete") is not True
            or live.get("game_build") != BUILD
            or live.get("sim_id") != sid
            or not _sim_id(live.get("household_id"))
            or not _ref(live.get("native_hook_ref"))
            or not _ref(live.get("state_revision"))
            or live.get("capture_ref") != offer.get("capture_ref")
            or live.get("read_origin") != "RUNNING_GAME_MEMORY"):
        raise RecipientEvidenceError("LIVE_RECIPIENT_SNAPSHOT_REQUIRED")
    at, at_offer = live.get("captured_at_epoch_ms"), offer.get("captured_at_epoch_ms")
    if (type(at) is not int or type(at_offer) is not int or at <= 0
            or at_offer <= 0 or not 0 <= at_offer - at <= MAX_SKEW_MS):
        raise RecipientEvidenceError("RECIPIENT_CAPTURE_STALE_OR_FUTURE")
    if (not _observed_map(live.get("needs"), 0, 100, 16)
            or not _observed_map(live.get("skills"), 0, 10, 24)
            or not _traits(live.get("traits"))
            or not _ref(live.get("age"))
            or not _ref(live.get("extended_species"))
            or not _ref(live.get("primary_aspiration"))
            or not _ref(live.get("current_activity"))
            or not isinstance(live.get("career"), Mapping)
            or not _num(live["career"].get("minutes_until_work"), 0, 10000)
            or not _ref(live["career"].get("source_ref"))):
        raise RecipientEvidenceError("RECIPIENT_NEEDS_CHARACTER_OR_CAREER_MISSING")
    snap = model.get("snapshot")
    if not isinstance(snap, Mapping):
        raise RecipientEvidenceError("RECIPIENT_PLAN_SNAPSHOT_MISSING")
    if (snap.get("capture_ref") != offer.get("capture_ref")
            or snap.get("sim_ref") != sid
            or snap.get("household_ref") != live["household_id"]
            or snap.get("needs") != live["needs"]
            or snap.get("skills") != live["skills"]
            or snap.get("traits") != live["traits"]
            or snap.get("minutes_until_work") != live["career"]["minutes_until_work"]
            or snap.get("source_revision") != live["state_revision"]
            or snap.get("forecast_scope") != "RECIPIENT_COUNTERFACTUAL"
            or snap.get("scene_verified") is not True
            or snap.get("queue_verified") is not True
            or snap.get("player_active") is not False
            or snap.get("player_directed") is not False):
        raise RecipientEvidenceError("RECIPIENT_PLANNING_STATE_MISMATCH")
    # Do not claim that UI selection changed. The Bellman planner's selected
    # actor equality is adapted in a PRIVATE no-effect counterfactual copy.
    # Return the actual selected actor separately in the receipt.
    simulated = dict(snap)
    simulated["selected_sim_ref"] = sid
    return sid, live, simulated


def _branch_steps(steps: object, branch: object) -> list[dict]:
    if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_EFFECTS:
        raise RecipientEvidenceError("SHARED_CONTINUATION_REQUIRED")
    if (not isinstance(branch, Mapping) or set(branch) != {"basis_ref", "per_step"}
            or not _ref(branch.get("basis_ref"))
            or not isinstance(branch.get("per_step"), Mapping)
            or len(branch["per_step"]) > MAX_EFFECTS):
        raise RecipientEvidenceError("PREFERENCE_EFFECT_PROVENANCE_REQUIRED")
    known = {step.get("id") for step in steps if isinstance(step, Mapping)}
    if (len(known) != len(steps) or None in known
            or any(not _ref(k) for k in known)
            or not set(branch["per_step"]).issubset(known)):
        raise RecipientEvidenceError("PREFERENCE_EFFECT_ACTION_MISMATCH")
    derived = deepcopy(steps)
    for item in derived:
        change = branch["per_step"].get(item["id"], {})
        if (not isinstance(change, Mapping)
                or not set(change).issubset(ALLOWED_DELTAS)):
            raise RecipientEvidenceError("PREFERENCE_EFFECT_SHAPE_INVALID")
        current = item.get("effects", {})
        if not isinstance(current, dict):
            raise RecipientEvidenceError("PREFERENCE_EFFECT_BASE_INVALID")
        current = dict(current)
        for key, delta in change.items():
            if key in ("mood_delta", "money_delta"):
                maximum = 100 if key == "mood_delta" else 10000
                if not _num(delta, -maximum, maximum):
                    raise RecipientEvidenceError("PREFERENCE_EFFECT_NUMBER_INVALID")
                old = current.get(key, 0)
                if not _num(old, -maximum, maximum) or not _num(old + delta, -maximum, maximum):
                    raise RecipientEvidenceError("PREFERENCE_EFFECT_OUT_OF_RANGE")
                current[key] = old + delta
            else:
                if (not isinstance(delta, Mapping) or len(delta) > 16
                        or any(not _ref(k) or not _num(v, -100, 100)
                               for k, v in delta.items())):
                    raise RecipientEvidenceError("PREFERENCE_EFFECT_MAP_INVALID")
                merged = dict(current.get(key, {}))
                if not isinstance(current.get(key, {}), Mapping):
                    raise RecipientEvidenceError("PREFERENCE_EFFECT_BASE_INVALID")
                for k, v in delta.items():
                    upper = 100 if key == "need_delta" else 10
                    if (not _num(merged.get(k, 0), -upper, upper)
                            or not _num(merged.get(k, 0) + v, -upper, upper)):
                        raise RecipientEvidenceError("PREFERENCE_EFFECT_OUT_OF_RANGE")
                    merged[k] = merged.get(k, 0) + v
                current[key] = merged
        item["effects"] = current
    return derived


def compare_recipient_continuations(offer: Mapping, model: Mapping) -> dict:
    """Use ONE graph, recipient/clock/needs/career, two predicted effects.

    The game recipient may differ from UI selection. Selection in the
    private counterfactual is not screen control or a native gameplay claim.
    No unequal selected paths or unknown native trackers can choose a button.
    """
    if (not isinstance(model, Mapping) or
            set(model) != {"snapshot", "continuation_steps", "routes",
                           "branch_effects", "activities"}):
        raise RecipientEvidenceError("CONTINUATION_MODEL_INVALID")
    sid, live, snapshot = _live_recipient(offer, model)
    branches = model.get("branch_effects")
    if not isinstance(branches, Mapping) or set(branches) != {"YES", "NO"}:
        raise RecipientEvidenceError("SAME_PLAN_BRANCH_EFFECTS_REQUIRED")
    steps = model.get("continuation_steps")
    routes = model.get("routes", [])
    if not isinstance(routes, list):
        raise RecipientEvidenceError("CONTINUATION_ROUTES_INVALID")
    plans = {
        choice: optimize_activity_plan(
            snapshot, _branch_steps(steps, branches[choice]), routes,
            capture_ref=offer["capture_ref"],
        )
        for choice in ("YES", "NO")
    }
    if any(p["gate"] != "FORECAST_STAGED_NOT_DISPATCHABLE" for p in plans.values()):
        raise RecipientEvidenceError("CONTINUATION_NOT_FEASIBLE_OR_COMPLETE")
    if (plans["YES"]["available_minutes"] != plans["NO"]["available_minutes"]
            or [(s["step_id"], s["travel"]) for s in plans["YES"]["forecast_steps"]]
            != [(s["step_id"], s["travel"]) for s in plans["NO"]["forecast_steps"]]):
        raise RecipientEvidenceError("CONTINUATION_PATH_DIVERGED")
    allocation = allocate_continuous_time(plans["NO"]["available_minutes"], model.get("activities"))
    shadow_price = allocation["shadow_price_lambda"]
    scores = {
        k: round(v["expected_net_utility"] - shadow_price * v["projected_minutes"], 6)
        for k, v in plans.items()
    }
    return {
        "recipient_sim_id": sid, "recipient_household_id": live["household_id"],
        "state_revision": live["state_revision"], "capture_ref": offer["capture_ref"],
        "actual_selected_sim_ref": offer["sim_ref"],
        "native_hook_ref": live["native_hook_ref"],
        "continuation_step_ids": [s["step_id"] for s in plans["YES"]["forecast_steps"]],
        "scores": scores, "time_shadow_price": shadow_price,
        "effect_basis_refs": {k: branches[k]["basis_ref"] for k in ("YES", "NO")},
        "resume_gate": "REOBSERVE_RECIPIENT_AND_ACTIVITY_AFTER_DIALOG",
        "control_permit": None, "execute_allowed": False, "proof_ceiling": PROOF,
    }
