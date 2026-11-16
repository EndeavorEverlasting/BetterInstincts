"""Native observation and policy for Get Famous drones and perk decisions."""
from __future__ import annotations

import re
from typing import Mapping

from betterinstincts.player_learning import TOKEN

PACK = "Get Famous"
NATIVE = "EA_RUNTIME"
DRONE_MODELS = ("UP_AND_ADAM", "GOTTA_STREAM_EM_ALL")
LOCATIONS = ("INVENTORY", "HOME_LOT", "PUBLIC_GROUND", "OTHER_LOT", "UNLOADED")
MODES = ("STREAMING", "RECORDING", "STOPPED")
STOP_CAUSES = ("BATTERY_DEPLETED", "DEPARTURE", "MANUAL", "INTERRUPTED")
OUTCOMES = ("GAIN", "NO_GAIN", "DOWNSIDE")

# The current EA affordance still owns the content ID, price and eligibility.
PERK_PATHS = {
    "CAREER": ("NOTICEABLE", "CELEBUSERUM", "ESTABLISHED_NAME", "CAREER_HOPPER", "EASY_STREET"),
    "CREATOR": ("CORPORATE_PARTNERSHIP", "INFLUENCER", "ALL_NIGHTER", "TRAILBLAZER", "LIFESTYLE_BRAND"),
    "SOCIAL": ("NETWORKING", "PR_AGENCY", "FAN_FAVORITE", "INSTANT_BESTIES", "SQUAD"),
    "GOOD_REPUTATION": ("GIVING_BACK", "RALLY", "STAR_TREATMENT"),
    "BAD_REPUTATION": ("WHOS_BAD", "PLAY_THE_VILLAIN", "FEUD_BRINGER"),
}
UPGRADES = (
    ("LITHIUM_BATTERY", 3, 1, 2),
    ("RELIABLE_COMPONENTS", 5, 2, 3),
    ("HD_CAMERA", 7, 2, 4),
)
TRAINING = {
    "CAREER": ("FAME_SKILL_OR_CAREER", "BEGIN_STREAM", "PUBLISH_MEDIA", "FAME_SOCIAL"),
    "CREATOR": ("PUBLISH_MEDIA", "BEGIN_STREAM", "FAME_SKILL_OR_CAREER", "FAME_SOCIAL"),
    "SOCIAL": ("FAME_SOCIAL", "BEGIN_STREAM", "FAME_SKILL_OR_CAREER", "PUBLISH_MEDIA"),
    "GOOD_REPUTATION": ("FAME_GOOD_REPUTATION", "FAME_SOCIAL", "BEGIN_STREAM"),
    "BAD_REPUTATION": ("FAME_BAD_REPUTATION", "FAME_SOCIAL", "BEGIN_STREAM"),
}


def _token(value):
    return isinstance(value, str) and TOKEN.fullmatch(value) is not None


def _object(value):
    return isinstance(value, str) and re.fullmatch(r"object:[A-Za-z0-9_-]{3,64}", value) is not None


def _count(value, maximum):
    return type(value) is int and 0 <= value <= maximum


def current_observation(frame, observation):
    return (isinstance(observation, Mapping) and observation.get("source") == NATIVE
            and observation.get("scope") == frame.scope() and observation.get("capture") == frame.capture
            and observation.get("pack") == PACK)


def _current_drone(frame, observation):
    if not current_observation(frame, observation):
        return None
    drone = observation.get("drone")
    if (not isinstance(drone, Mapping) or drone.get("source") != NATIVE
            or drone.get("capture") != frame.capture or drone.get("owner_household") != frame.household
            or drone.get("assigned_actor") != frame.actor or drone.get("model") not in DRONE_MODELS
            or not _object(drone.get("id")) or drone.get("location") not in LOCATIONS
            or drone["location"] == "UNLOADED" or not _token(drone.get("zone"))
            or drone.get("mode") not in MODES
            or (drone["location"] == "INVENTORY" and drone["mode"] != "STOPPED")):
        return None
    return drone


_DRONE_STATE_FIELDS = ("id", "model", "zone", "location", "mode", "battery", "lot", "follows_actor")


def _tracked_observation(frame, observation, track):
    drone = _current_drone(frame, observation)
    if (drone is not None and track is not None and track["scope"] == frame.scope()
            and track["capture"] == frame.capture and track["observed_at"] == frame.observed_at
            and all(drone.get(field) == track.get(field) for field in _DRONE_STATE_FIELDS)):
        return drone
    return None


def observe_drone(frame, observation, previous=None):
    """Update a bound instance's last-known state, including a confirmed stream edge."""
    drone = _current_drone(frame, observation)
    if drone is None or (previous is not None and (
            previous["scope"] != frame.scope() or previous["id"] != drone["id"]
            or previous["model"] != drone["model"] or previous["capture"] == frame.capture
            or previous["observed_at"] > frame.observed_at)):
        return previous
    mode = drone["mode"]
    stop = previous.get("last_stop") if previous else None
    recovering = previous.get("recovering", False) if previous else False
    # Recovering survives the public-to-home transition for this instance.
    if drone["location"] == "PUBLIC_GROUND" and mode == "STOPPED":
        recovering = True
    elif drone["location"] == "INVENTORY":
        recovering = False
    if previous and previous["mode"] == "STREAMING" and mode != "STREAMING":
        cause = drone.get("stop_cause")
        stop = {"cause": cause if cause in STOP_CAUSES else "UNKNOWN",
                "capture": frame.capture, "location": drone["location"]}
    return {**{field: drone.get(field) for field in _DRONE_STATE_FIELDS},
            "scope": frame.scope(), "capture": frame.capture, "observed_at": frame.observed_at,
            "last_stop": stop, "recovering": recovering,
            "position": drone.get("position") if _token(drone.get("position")) else None}


def _affordance(frame, data, action, target, spent, *, subject=None):
    if (isinstance(data, Mapping) and data.get("capture") == frame.capture
            and data.get("enabled") is True and data.get("action") == action
            and data.get("target") == target and data.get("subject") == subject
            and _token(data.get("opportunity")) and data["opportunity"] not in spent):
        return {"opportunity": data["opportunity"], "action": action, "target": target,
                "subject": subject}
    return None


def _proposal(action, subject, target, frame, offers, spent, **details):
    if not isinstance(offers, Mapping):
        return None
    offer = _affordance(frame, offers.get(subject or action), action, target, spent, subject=subject)
    if offer:
        return {**offer, **details}
    return None


def _drone_action(frame, observation, track, spent):
    """Return a lifecycle decision or fall through to perk/training selection."""
    drone = _tracked_observation(frame, observation, track)
    if drone is None:
        # A remembered instance remains outstanding even after its zone unloads.
        if track is not None:
            return "LOCATE_LAST_KNOWN_DRONE", None
        if (observation.get("drone_search_complete") is True and observation.get("drone") is None
                and observation.get("allow_drone_purchase") is True):
            return "ROUTE_DRONE_ACQUISITION", None
        return "LOCATE_OWNED_DRONE", None

    target, location, mode = track["id"], track["location"], track["mode"]
    offers = drone.get("offers")
    on_site = observation.get("actor_zone") == track["zone"]
    battery = drone.get("battery")
    departure = observation.get("departure_imminent")
    if location in ("OTHER_LOT", "UNLOADED") or (location != "INVENTORY" and not on_site):
        return "LOCATE_LAST_KNOWN_DRONE", None
    if location == "PUBLIC_GROUND":
        route = observation.get("home_route")
        if (departure is not False or not isinstance(route, Mapping)
                or route.get("capture") != frame.capture or route.get("reachable") is not True
                or route.get("origin_zone") != track["zone"] or not _token(route.get("home_lot"))
                or route.get("home_lot") != observation.get("home_lot")
                or not _token(route.get("route_id"))):
            return "PUBLIC_DRONE_ROUTE_UNVERIFIED", None
        details = {"home_lot": route["home_lot"], "route_id": route["route_id"]}
        if (mode == "STREAMING" and track["recovering"] and drone.get("follows_actor") is True
                and battery in ("READY", "FULL")):
            pick = _proposal("RETURN_DRONE_HOME", None, target, frame, offers, spent, **details)
            return "WAIT_FOR_HOME_ROUTE", pick
        if mode == "STOPPED" and battery in ("READY", "FULL"):
            pick = _proposal("BEGIN_RECOVERY_STREAM", None, target, frame, offers, spent, **details)
            return "WAIT_FOR_RESTART_AFFORDANCE", pick
        if mode == "STREAMING" and not track["recovering"]:
            return "DRONE_ALREADY_STREAMING", None
        return "WAIT_FOR_PUBLIC_DRONE_CHARGE_OR_FOLLOW", None
    if location == "HOME_LOT":
        if not _token(drone.get("lot")) or drone.get("lot") != observation.get("home_lot"):
            return "HOME_LOT_ID_UNVERIFIED", None
        if mode == "STOPPED":
            return "WAIT_FOR_STOW_AFFORDANCE", _proposal("STOW_DRONE", None, target, frame, offers, spent)
        if mode == "STREAMING" and (departure is True or battery in ("LOW", "EMPTY")
                                    or track["recovering"]):
            return "WAIT_FOR_END_STREAM_AFFORDANCE", _proposal("END_STREAM", None, target, frame, offers, spent)
        if mode == "RECORDING":
            return "DRONE_RECORDING", None
        # Low-priority perk/training may proceed while the stream is healthy.
        return "DRONE_ALREADY_STREAMING", None
    if departure is not False:
        return "KEEP_DRONE_IN_INVENTORY", None
    if battery not in ("READY", "FULL"):
        return "WAIT_FOR_DRONE_CHARGE", None
    return "DRONE_READY", None


def protects_drone(frame, observation, track, proposal):
    """Admit priority over a normal native proposal only for imminent drone loss."""
    drone = _tracked_observation(frame, observation, track)
    if drone is None or proposal is None:
        return False
    if proposal["action"] in ("BEGIN_RECOVERY_STREAM", "RETURN_DRONE_HOME"):
        return track["recovering"]
    if proposal["action"] in ("END_STREAM", "STOW_DRONE"):
        return (track["recovering"] or observation.get("departure_imminent") is True
                or (proposal["action"] == "END_STREAM" and drone.get("battery") in ("LOW", "EMPTY")))
    return False


def current_stream_stopped(frame, observation, track, target):
    drone = _tracked_observation(frame, observation, track)
    return drone is not None and drone["id"] == target and drone["mode"] == "STOPPED"


def _perk(frame, observation, profile, spent):
    perk = observation.get("perk_panel")
    if not isinstance(perk, Mapping) or perk.get("capture") != frame.capture:
        return None
    rank, points, owned = perk.get("rank"), perk.get("points"), perk.get("owned")
    if not _count(rank, 5) or not _count(points, 100) or not isinstance(owned, (tuple, list)) or len(owned) > 21:
        return None
    if profile in ("GOOD_REPUTATION", "BAD_REPUTATION") and perk.get("verified_reputation_path") != profile:
        return None
    path = PERK_PATHS[profile]
    for tier, name in enumerate(path, start=3 if len(path) == 3 else 1):
        if name in owned:
            continue
        options = perk.get("offers")
        offer = options.get(name) if isinstance(options, Mapping) else None
        if (rank < tier or not isinstance(offer, Mapping) or not _count(offer.get("cost"), points)
                or not offer["cost"] or offer.get("native_prerequisites_met") is not True):
            return None  # Save the points for the selected branch.
        return _proposal("BUY_FAME_PERK", name, frame.actor, frame, options, spent,
                         points_before=points, cost=offer["cost"])
    return None


def _upgrade(frame, observation, track, profile, spent):
    if (track is None or track["capture"] != frame.capture
            or track["location"] not in ("HOME_LOT", "INVENTORY") or track["mode"] != "STOPPED"
            or observation.get("allow_drone_upgrades") is not True):
        return None
    drone = observation["drone"]
    handiness = observation.get("handiness")
    electronic, common = observation.get("electronic_parts"), observation.get("common_parts")
    installed = drone.get("upgrades")
    if (not _count(handiness, 10) or not _count(electronic, 100000) or not _count(common, 100000)
            or not isinstance(installed, (list, tuple)) or len(installed) > len(UPGRADES)):
        return None
    for name, skill, e_parts, c_parts in UPGRADES:
        if name in installed or (name == "HD_CAMERA" and profile != "CREATOR"):
            continue
        if handiness >= skill and electronic >= e_parts and common >= c_parts:
            pick = _proposal("UPGRADE_DRONE", name, track["id"], frame, drone.get("offers"), spent)
            if pick is not None:
                return pick
    return None


def _training(frame, observation, track, profile, spent, history):
    """Use a Dirichlet(3,1,1) predictive mean per action and verified context."""
    if observation.get("departure_imminent") is not False or not _token(observation.get("training_context")):
        return None
    context = observation["training_context"]
    candidates = []
    for priority, action in enumerate(TRAINING[profile]):
        target = frame.actor
        offers = observation.get("training_offers")
        if action == "BEGIN_STREAM":
            if (track is None or track["capture"] != frame.capture or track["location"] != "INVENTORY"
                    or observation["drone"].get("battery") not in ("READY", "FULL")
                    or observation.get("stream_route_safe") is not True):
                continue
            target, offers = track["id"], observation["drone"].get("offers")
        offer = offers.get(action) if isinstance(offers, Mapping) else None
        if not isinstance(offer, Mapping) or offer.get("fits_current_schedule") is not True:
            continue
        minutes = offer.get("active_minutes")
        if not _count(minutes, 1440) or minutes == 0:
            continue
        pick = _proposal(action, None, target, frame, offers, spent, training_context=context)
        if pick:
            gain, neutral, downside = history.get((context, action), (0, 0, 0))
            # Outcome classes are disjoint, and downside has twice the unit cost.
            numerator = 3 + gain - 2 * downside
            if numerator > 0:
                score = numerator / ((5 + gain + neutral + downside) * minutes)
                candidates.append((score, -priority, pick))
    return max(candidates, key=lambda row: row[:2])[2] if candidates else None


def plan_fame(frame, observation, track, spent, history):
    if observation is None:
        return "NO_FAME_GOAL", None
    if not current_observation(frame, observation):
        return "REOBSERVE_NATIVE_FAME_SCOPE", None
    goal = observation.get("goal")
    if goal is None:
        return "NO_FAME_GOAL", None
    if not isinstance(goal, str) or goal not in PERK_PATHS:
        return "FAME_GOAL_UNVERIFIED", None
    if (frame.playing is not True or frame.modal_open is not False or observation.get("actor_present") is not True
            or observation.get("needs_safe") is not True):
        return "WAIT_FOR_FAME_ACTOR", None
    # A Sim with a goal can safeguard a drone at home while Fame is disabled.
    drone_state, drone_pick = _drone_action(frame, observation, track, spent)
    if drone_pick and (drone_pick["action"] in ("STOW_DRONE", "END_STREAM")
                       or observation.get("fame_enabled") is True):
        return drone_state, drone_pick
    if observation.get("fame_enabled") is not True:
        return "FAME_PARTICIPATION_REQUIRED", None
    if observation.get("departure_imminent") is not False:
        return drone_state, None
    if track and drone_state not in ("DRONE_READY", "DRONE_ALREADY_STREAMING", "WAIT_FOR_DRONE_CHARGE"):
        return drone_state, None
    perk = _perk(frame, observation, goal, spent)
    if perk and observation.get("allow_perk_spending") is True:
        return "FAME_PERK_READY", perk
    upgrade = _upgrade(frame, observation, track, goal, spent)
    if upgrade:
        return "DRONE_UPGRADE_READY", upgrade
    training = _training(frame, observation, track, goal, spent, history)
    return ("FAME_TRAINING_READY", training) if training else (drone_state, None)


def read_outcome(frame, attempted, outcome):
    """Return the reconciled status and optional categorical training sample."""
    if (not isinstance(outcome, Mapping) or outcome.get("source") != NATIVE
            or outcome.get("scope") != frame.scope() or outcome.get("capture") != frame.capture
            or frame.capture in attempted["captures"] or frame.observed_at < attempted["observed_at"]
            or outcome.get("proposal") != attempted["proposal"] or outcome.get("acknowledged") is not True):
        return "NATIVE_DISPATCH_RECONCILIATION", None
    pick = attempted["proposal"]
    action, target = pick["action"], pick["target"]
    if outcome.get("completed") is False and outcome.get("no_effect_verified") is True:
        return "FAME_NO_EFFECT_OBSERVED", None
    if outcome.get("completed") is not True:
        return "NATIVE_DISPATCH_RECONCILIATION", None
    effect = outcome.get("effect")
    if not isinstance(effect, Mapping) or effect.get("target") != target:
        return "NATIVE_DISPATCH_RECONCILIATION", None
    if action == "BUY_FAME_PERK":
        verified = (effect.get("owned_perk") == pick["subject"] and effect.get("was_owned") is False
                    and _count(effect.get("points_after"), 100)
                    and effect["points_after"] == pick["points_before"] - pick["cost"])
    elif action == "UPGRADE_DRONE":
        verified = effect.get("installed_upgrade") == pick["subject"] and effect.get("was_installed") is False
    elif action == "STOW_DRONE":
        verified = effect.get("inventory_actor") == frame.actor and effect.get("location") == "INVENTORY"
    elif action == "END_STREAM":
        verified = effect.get("mode") == "STOPPED"
    elif action == "BEGIN_RECOVERY_STREAM":
        verified = effect.get("mode") == "STREAMING" and effect.get("follows_actor") is True
    elif action == "RETURN_DRONE_HOME":
        verified = (effect.get("location") == "HOME_LOT" and effect.get("lot") == pick["home_lot"]
                    and effect.get("actor_on_lot") is True)
    elif action == "BEGIN_STREAM" and effect.get("training_finished") is not True:
        # Release admission once the stream is verified so the battery and
        # departure safeguards can still act before the stream finishes.
        return ("FAME_STREAM_OBSERVED", None) if effect.get("mode") == "STREAMING" else (
            "NATIVE_DISPATCH_RECONCILIATION", None)
    else:
        verified = effect.get("training_finished") is True
    if not verified:
        return "NATIVE_DISPATCH_RECONCILIATION", None
    sample = effect.get("training_outcome")
    if "training_context" in pick and effect.get("training_finished") is True and sample in OUTCOMES:
        uninterrupted = (outcome.get("player_interrupted") is False
                         and frame.input_generation == attempted.get("input_generation"))
        return "FAME_EFFECT_OBSERVED", (pick["training_context"], action, sample) if uninterrupted else None
    if "training_context" in pick:
        return "NATIVE_DISPATCH_RECONCILIATION", None
    return "FAME_EFFECT_OBSERVED", None
