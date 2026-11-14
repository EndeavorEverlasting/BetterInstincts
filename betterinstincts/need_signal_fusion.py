"""Fuse independently observed Sims motive trends with provenance-bound sensor health.

This is a deterministic policy port. Native EA and calibrated HUD CV sensors are
external, version-specific producers NOT implemented or launched by this module.
Never reads game files, screen, saves, hosts, or queues; never grants an effect.
"""
from __future__ import annotations

import math
import re
import time
from collections.abc import Mapping
from typing import Any

from betterinstincts.moodlets import evaluate_moodlets
from betterinstincts.occult_needs import load_catalog

SCHEMA = "betterinstincts.need-signal-fusion/v1"
RESULT = "betterinstincts.need-signal-fusion-result/v1"
PROOF = "OFFLINE_FUSED_OBSERVATION_NOT_LIVE_NATIVE_OR_CV_SENSOR"
SOURCE_ORDER = ("EA_NATIVE", "HUD_CV")
DIRECTIONS = frozenset({"UP", "DOWN", "FLAT", "UNKNOWN"})
REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{1,119}$")
MAX_AGE_SECONDS = 60
MAX_CROSS_SOURCE_SKEW = 12
MAX_SAMPLES_PER_CALL = 2
MAX_RATE = 1.0


class NeedSignalError(ValueError):
    pass


def _ref(value: Any) -> bool:
    return isinstance(value, str) and bool(REF.fullmatch(value))


def _finite(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _health(source: str, *, state: str, reason: str, sample: str | None = None,
            epoch: str | None = None, good: int = 0, stamp: float | None = None) -> dict:
    return {"source": source, "state": state, "reason": reason,
            "last_sample_ref": sample, "reset_ref": epoch,
            "consecutive_good": good, "observed_at_unix": stamp,
            "next_gate": ("NONE" if state == "HEALTHY" else
                          "OBSERVE_DISTINCT_POST_RESET_PROBE" if state == "RECOVERING"
                          else "ISOLATE_SOURCE_RESET_ASSUMPTIONS_AND_HEALTH_CHECK")}


def _read_feed(
    source: str, feed: Mapping[str, Any] | None, *, prior: Mapping[str, Any],
    profile: str, motives: tuple[str, ...], sim_ref: str,
    game_build: str, now: float,
) -> tuple[dict, dict[str, dict]]:
    if feed is None:
        return _health(source, state="DOWN", reason="SOURCE_MISSING"), {}
    if not isinstance(feed, Mapping):
        return _health(source, state="DOWN", reason="SOURCE_INVALID"), {}
    if feed.get("status") != "READY":
        return _health(source, state="DOWN", reason="SOURCE_UNAVAILABLE"), {}
    fields = ("source_ref", "sample_ref", "capture_ref")
    if (feed.get("source") != source
            or any(not _ref(feed.get(k)) for k in fields)
            or feed.get("sim_ref") != sim_ref or feed.get("game_build") != game_build
            or feed.get("profile") != profile
            or feed.get("probe_passed") is not True
            or feed.get("scene_verified") is not True):
        return _health(source, state="QUARANTINED", reason="SOURCE_IDENTITY_OR_PROBE_FAILED"), {}
    stamp = feed.get("observed_at_unix")
    if not _finite(stamp) or not 0 <= now - float(stamp) <= MAX_AGE_SECONDS:
        return _health(source, state="QUARANTINED", reason="SOURCE_STALE_OR_FUTURE"), {}
    if source == "EA_NATIVE":
        if (feed.get("native_read_verified") is not True
                or not _ref(feed.get("native_hook_ref"))):
            return _health(source, state="QUARANTINED", reason="EA_NATIVE_RUNTIME_HOOK_UNPROVEN"), {}
    elif (feed.get("calibration_verified") is not True
          or not _ref(feed.get("calibration_ref"))):
        return _health(source, state="QUARANTINED", reason="HUD_CALIBRATION_UNPROVEN"), {}

    rows = feed.get("needs")
    if (not isinstance(rows, Mapping) or not 1 <= len(rows) <= len(motives)
            or not set(rows).issubset(set(motives))):
        return _health(source, state="QUARANTINED", reason="MOTIVE_PROFILE_MISMATCH"), {}
    parsed: dict[str, dict] = {}
    for motive, raw in rows.items():
        if not isinstance(raw, Mapping):
            return _health(source, state="QUARANTINED", reason="MOTIVE_ROW_INVALID"), {}
        level, direction = raw.get("level"), raw.get("direction", "UNKNOWN")
        if ((level is not None and
             (not _finite(level) or not 0 <= float(level) <= 1))
                or direction not in DIRECTIONS):
            return _health(source, state="QUARANTINED", reason="MOTIVE_LEVEL_OR_DIRECTION_INVALID"), {}
        arrow = raw.get("arrow_count")
        rate = raw.get("rate_per_sim_minute")
        if source == "HUD_CV":
            if (rate is not None or
                (direction in {"UP", "DOWN"} and
                 (type(arrow) is not int or arrow not in (1, 2, 3)
                  or not _ref(raw.get("arrow_proof_ref")))) or
                (direction not in {"UP", "DOWN"} and arrow not in (None, 0))):
                return _health(source, state="QUARANTINED", reason="HUD_TREND_PROOF_INVALID"), {}
        else:
            if arrow is not None or (rate is not None and
                    (not _finite(rate) or abs(float(rate)) > MAX_RATE
                     or not _ref(raw.get("rate_proof_ref"))))):
                return _health(source, state="QUARANTINED", reason="NATIVE_RATE_PROOF_INVALID"), {}
            if rate is not None:
                sign = "UP" if rate > 0 else "DOWN" if rate < 0 else "FLAT"
                if direction not in (sign, "UNKNOWN"):
                    return _health(source, state="QUARANTINED", reason="NATIVE_RATE_DIRECTION_CONTRADICTS_VALUE"), {}
                direction = sign
        parsed[motive] = {
            "level": float(level) if level is not None else None,
            "direction": direction,
            "arrow_count": arrow if source == "HUD_CV" else None,
            "rate_per_sim_minute": float(rate) if rate is not None else None,
            "source": source, "sample_ref": feed["sample_ref"],
            "observed_at_unix": float(stamp),
        }

    previous = prior if isinstance(prior, Mapping) else {}
    older_state = previous.get("state")
    reset = feed.get("reset_ref")
    if older_state in {"DOWN", "QUARANTINED", "RECOVERING"}:
        if not _ref(reset) or feed.get("reset_probe_passed") is not True:
            return _health(source, state="QUARANTINED", reason="RESET_AND_REPROBE_REQUIRED"), {}
        if older_state == "RECOVERING":
            if (reset != previous.get("reset_ref")
                    or feed["sample_ref"] == previous.get("last_sample_ref")
                    or not _finite(previous.get("observed_at_unix"))
                    or float(stamp) <= float(previous["observed_at_unix"])):
                return _health(source, state="QUARANTINED", reason="REPLAYED_OR_NEW_RESET_EPOCH"), {}
            return _health(source, state="HEALTHY", reason="TWO_POST_RESET_PROBES",
                           sample=feed["sample_ref"], epoch=reset, good=2, stamp=float(stamp)), parsed
        if reset == previous.get("reset_ref") or feed["sample_ref"] == previous.get("last_sample_ref"):
            return _health(source, state="QUARANTINED", reason="NEW_RESET_EPOCH_REQUIRED"), {}
        return _health(source, state="RECOVERING", reason="FIRST_POST_RESET_PROBE",
                       sample=feed["sample_ref"], epoch=reset, good=1, stamp=float(stamp)), {}
    if (previous.get("last_sample_ref") == feed["sample_ref"]
            and older_state == "HEALTHY"):
        return _health(source, state="QUARANTINED", reason="SAMPLE_REPLAY"), {}
    return _health(source, state="HEALTHY", reason="FRESH_VERIFIED_PROBE",
                   sample=feed["sample_ref"], epoch=reset if _ref(reset) else None,
                   good=1, stamp=float(stamp)), parsed


def evaluate_need_signals(observation: Mapping[str, Any], *,
                          now: float | None = None,
                          prior_health: Mapping[str, Mapping] | None = None) -> dict:
    """Advisory fusion; each source can report independently and recover.

    Consumers carry the returned health mapping to a later *distinct* call.
    A health status never restarts any process or permits a Sims game action.
    """
    if not isinstance(observation, Mapping) or observation.get("schema") != SCHEMA:
        raise NeedSignalError("NEED_SIGNAL_SCHEMA_INVALID")
    instant = time.time() if now is None else now
    if not _finite(instant):
        raise NeedSignalError("NEED_SIGNAL_CLOCK_INVALID")
    sim_ref, build, capture = (observation.get(k) for k in
                               ("sim_ref", "game_build", "capture_ref"))
    profile = observation.get("profile")
    if (not all(_ref(v) for v in (sim_ref, build, capture, profile))
            or build.lower() in {"unknown", "latest", "any"}
            or type(observation.get("game_paused")) is not bool
            or type(observation.get("player_active")) is not bool):
        raise NeedSignalError("NEED_SIGNAL_CONTEXT_INVALID")
    catalog = load_catalog()
    p = catalog["profiles"].get(profile)
    if not isinstance(p, Mapping) or p.get("status") != "CATALOG_READY":
        raise NeedSignalError("NEED_SIGNAL_UNSUPPORTED_PROFILE")
    motives = tuple(p["motives"])
    feeds = observation.get("feeds", [])
    if not isinstance(feeds, list) or len(feeds) > MAX_SAMPLES_PER_CALL:
        raise NeedSignalError("NEED_SIGNAL_FEED_BOUNDS")
    by_source: dict[str, Mapping] = {}
    for feed in feeds:
        if not isinstance(feed, Mapping) or feed.get("source") not in SOURCE_ORDER:
            raise NeedSignalError("UNRECOGNIZED_SOURCE")
        if feed["source"] in by_source:
            raise NeedSignalError("DUPLICATE_SOURCE")
        by_source[feed["source"]] = feed
    old = prior_health or {}
    if not isinstance(old, Mapping) or not set(old).issubset(SOURCE_ORDER):
        raise NeedSignalError("INVALID_PRIOR_HEALTH")

    health, normalized = {}, {}
    for source in SOURCE_ORDER:
        health[source], normalized[source] = _read_feed(
            source, by_source.get(source), prior=old.get(source, {}),
            profile=profile, motives=motives, sim_ref=sim_ref,
            game_build=build, now=float(instant))
    healthy = [s for s in SOURCE_ORDER if health[s]["state"] == "HEALTHY"]
    motive_rows = {}
    rapid = []
    conflicts = []
    for motive in motives:
        available = [normalized[s][motive] for s in healthy if motive in normalized[s]]
        aligned = (len(available) < 2 or
                   abs(available[0]["observed_at_unix"] -
                       available[1]["observed_at_unix"]) <= MAX_CROSS_SOURCE_SKEW)
        directions = {r["direction"] for r in available if r["direction"] != "UNKNOWN"}
        discord = aligned and len(directions) > 1
        if discord:
            conflicts.append(motive)
        # Native measured rate/level preferred; fallback to latest good HUD
        # observation independently. Never take numbers from arrows.
        native = next((r for r in available if r["source"] == "EA_NATIVE"), None)
        hud = next((r for r in available if r["source"] == "HUD_CV"), None)
        chosen = native or hud
        if chosen is not None and chosen["direction"] == "UNKNOWN" and hud is not None:
            chosen = hud
        direction = ("CONFLICT" if discord else
                     chosen["direction"] if chosen is not None else "UNKNOWN")
        arrows = hud["arrow_count"] if hud is not None else None
        tier = ("THREE_DOWN_CHEVRONS" if not discord and
                hud is not None and hud["direction"] == "DOWN" and arrows == 3
                else "DIRECTION_OBSERVED" if direction != "UNKNOWN" else "UNKNOWN")
        rate = (native["rate_per_sim_minute"] if native is not None
                and not observation["game_paused"] and not discord else None)
        level = (native["level"] if native is not None and native["level"] is not None
                 else hud["level"] if hud is not None else None)
        if not aligned and chosen is not None:
            tier = "ASYNCHRONOUS_NOT_CORROBORATED"
        critical_decline = (direction == "DOWN" and
                            (tier == "THREE_DOWN_CHEVRONS" or
                             (level is not None and level < 0.35)))
        if critical_decline:
            rapid.append(motive)
        motive_rows[motive] = {
            "level": level, "direction": direction, "hud_arrow_count": arrows,
            "ordinal_rate_tier": tier, "native_rate_per_sim_minute": rate,
            "rate_multiplier_claim": None,
            "active_decay_measured": bool(rate is not None),
            "sources": [r["source"] for r in available],
            "trend_conflict": discord,
            "needs_reobservation": not aligned or discord or chosen is None,
        }

    # Existing moodlets owner performs the interpretation. No new catalog,
    # emotion classifier or inference from an unseen buff icon.
    moods = observation.get("moodlet_observation")
    moodlet_eval = None
    if moods is not None:
        if (not isinstance(moods, Mapping) or not _ref(moods.get("source_ref"))
                or moods.get("capture_ref") != capture
                or not isinstance(moods.get("moodlets", []), list)):
            raise NeedSignalError("MOODLET_EVIDENCE_INVALID")
        moodlet_eval = evaluate_moodlets(
            emotion=moods.get("emotion"),
            moodlets=moods.get("moodlets", ()),
            capture_ref=capture)
    mood_mode = "MOODLET_NOT_OBSERVED"
    if moodlet_eval is not None:
        family = moodlet_eval.get("emotion_family")
        if family in {"anger", "fear", "discomfort"}:
            mood_mode = "REVIEW_NEGATIVE_MOODLET_RELIEF"
        elif family == "positive":
            mood_mode = "PRESERVE_POSITIVE_ACTIVITY_IF_NEEDS_SAFE"
        else:
            mood_mode = "NEUTRAL_OR_UNKNOWN_MOODLET"
    if rapid and mood_mode == "PRESERVE_POSITIVE_ACTIVITY_IF_NEEDS_SAFE":
        mood_mode = "DECLINING_NEED_OUTRANKS_POSITIVE_MOOD"
    if observation["player_active"]:
        priority = "PLAYER_FIRST"
    elif conflicts:
        priority = "SOURCE_CONFLICT_REOBSERVE"
    elif rapid:
        priority = ("PAUSED_RAPID_DECAY_INDICATOR_REVIEW" if observation["game_paused"]
                    else "DIAGNOSE_RAPID_NEED_DECLINE")
    elif any(m["direction"] == "DOWN" for m in motive_rows.values()):
        priority = "MONITOR_DECLINING_NEEDS"
    else:
        priority = "CONTINUE_OR_REOBSERVE"
    state = ("SOURCES_UNAVAILABLE" if not healthy else
             "DUAL_SOURCE_CORROBORATION" if len(healthy) == 2 else
             "SINGLE_SOURCE_FALLBACK")
    return {
        "schema": RESULT, "state": state, "profile": profile,
        "sim_ref": sim_ref, "game_build": build, "capture_ref": capture,
        "motives": motive_rows, "source_health": health, "healthy_sources": healthy,
        "priority": priority, "rapid_declines": rapid,
        "conflicts": conflicts, "moodlet_guidance": mood_mode,
        "moodlets": moodlet_eval, "game_paused": observation["game_paused"],
        "player_active": observation["player_active"],
        "next_actions": (["REQUEST_FRESH_INDEPENDENT_OBSERVATION"] if conflicts
                         else ["REVIEW_SOCIAL_AND_SAFE_NATIVE_AFFORDANCES"]
                         if "social" in rapid else []),
        "execute_allowed": False, "queue_cancel_allowed": False,
        "restart_sensor_allowed": False, "game_input_allowed": False,
        "proof_ceiling": PROOF,
    }
