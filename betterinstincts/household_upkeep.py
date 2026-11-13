"""Bounded, observation-only Servo health and household bill queue policy.

P95 program seam; P124 composes with host_stack/host_listener, existing
queue_capacity and budget guards. Does NOT poll Windows, click Sims, run a
daemon, move assets or certify in-game outcomes.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from collections.abc import Mapping

from betterinstincts.queue_capacity import QueueCapacityError, evaluate_queue_capacity

SCHEMA = "betterinstincts.household-upkeep/v1"
CONTRACT = Path(__file__).resolve().parents[1] / "contracts/household-upkeep.v1.json"
MAX_SERVOS = 16
MAX_ACTORS = 16
MAX_ACTIONS = 64
MAX_CAPTURE_AGE_SECONDS = 180
SERVO_NEEDS = frozenset({"durability", "charge", "fun", "social"})
ACTIONS = {"TUNE_UP_SERVO", "REPAIR_SERVO", "RECHARGE_SERVO",
           "SERVO_SELF_TUNE_UP", "SOCIALIZE_SERVO", "SERVO_FUN_ACTIVITY", "PAY_BILLS",
           "REPAIR_UTILIBOT", "TUNE_UP_UTILIBOT", "RECHARGE_UTILIBOT"}
SERVO_MAINTENANCE = frozenset({"TUNE_UP_SERVO", "REPAIR_SERVO"})
UTILIBOT_MAINTENANCE = frozenset({"REPAIR_UTILIBOT", "TUNE_UP_UTILIBOT"})
PEER_MAINTENANCE = SERVO_MAINTENANCE | UTILIBOT_MAINTENANCE
ROBOT_CARE = PEER_MAINTENANCE | {"RECHARGE_UTILIBOT"}
HUMAN_ONLY_ACTIONS = frozenset({"PAY_BILLS"})
UTILIBOT_NEEDS = frozenset({"durability", "charge"})
UTILIBOT_KINDS = frozenset({"GARDENER_BOT", "CLEANER_BOT", "FIXER_BOT", "PARTY_BOT"})
ATTEMPTS = {"NONE", "QUEUED", "DISPATCHED"}
BILL_STATES = {"UNPAID", "PAID", "NOT_DUE", "UNKNOWN"}
SKILL_LEVEL_MAX = 10


class HouseholdUpkeepError(ValueError):
    pass


def load_contract() -> dict:
    if CONTRACT.is_symlink() or not CONTRACT.is_file() or CONTRACT.stat().st_size > 32_000:
        raise HouseholdUpkeepError("UPKEEP_CONTRACT_UNSAFE")
    cfg = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.household-upkeep-policy/v1":
        raise HouseholdUpkeepError("UPKEEP_CONTRACT_SCHEMA_INVALID")
    thresholds = cfg.get("servo_thresholds") or {}
    names = ("durability_critical", "durability_watch", "charge_critical",
             "charge_watch", "fun_watch", "social_watch")
    if any(not _num(thresholds.get(k), upper=1) for k in names):
        raise HouseholdUpkeepError("UPKEEP_THRESHOLDS_INVALID")
    if not thresholds["durability_critical"] < thresholds["durability_watch"]:
        raise HouseholdUpkeepError("UPKEEP_DURABILITY_THRESHOLDS_INVALID")
    if not thresholds["charge_critical"] < thresholds["charge_watch"]:
        raise HouseholdUpkeepError("UPKEEP_CHARGE_THRESHOLDS_INVALID")
    fire = cfg.get("servo_fire_risk")
    if not isinstance(fire, Mapping) or fire.get("clothesline_preferred_when_unsupervised") is not True:
        raise HouseholdUpkeepError("UPKEEP_FIRE_RISK_POLICY_REQUIRED")
    dryer = fire.get("dryer_policy") or {}
    if (not isinstance(dryer, Mapping)
            or dryer.get("clean_lint_trap_before_each_dryer_run") is not True
            or dryer.get("unsupervised_dryer") != "FORBIDDEN_UNLESS_LINT_LESS_INSTALLED"):
        raise HouseholdUpkeepError("UPKEEP_FIRE_RISK_DRYER_POLICY_REQUIRED")
    bot = cfg.get("utilibot_policy")
    if (not isinstance(bot, Mapping)
            or set(bot.get("kinds", ())) != UTILIBOT_KINDS
            or set(bot.get("motives", ())) != UTILIBOT_NEEDS):
        raise HouseholdUpkeepError("UPKEEP_UTILIBOT_POLICY_REQUIRED")
    bounds = cfg.get("bounds") or {}
    if type(bounds.get("max_utilibots")) is not int or not 1 <= bounds["max_utilibots"] <= 16:
        raise HouseholdUpkeepError("UPKEEP_UTILIBOT_BOUND_INVALID")
    for key in ("durability_critical", "durability_watch", "charge_critical", "charge_watch"):
        if not _num(bot["thresholds"].get(key), upper=1):
            raise HouseholdUpkeepError("UPKEEP_UTILIBOT_THRESHOLDS_INVALID")
    hp = cfg.get("servo_helper_policy") or {}
    for key in ("min_helper_charge", "min_helper_durability"):
        if not _num(hp.get(key), upper=1):
            raise HouseholdUpkeepError("UPKEEP_SERVO_HELPER_RESERVE_INVALID")
    return cfg


def _ref(v: object) -> bool:
    return isinstance(v, str) and 1 <= len(v) <= 120 and all(
        c.isalnum() or c in "_.:-" for c in v
    )


def _num(v: object, *, lower: float = 0, upper: float | None = None) -> bool:
    return (type(v) in (int, float) and math.isfinite(v)
            and v >= lower and (upper is None or v <= upper))


def _bool(v: object) -> bool:
    return type(v) is bool


def _verified_skill_level(actor: Mapping, skill_id: str) -> float | None:
    """Return verified skill level, or None when missing/unverified."""
    skills = actor.get("skills")
    if not isinstance(skills, Mapping):
        return None
    entry = skills.get(skill_id)
    if not isinstance(entry, Mapping) or entry.get("verified") is not True:
        return None
    level = entry.get("level")
    return float(level) if _num(level, lower=0, upper=SKILL_LEVEL_MAX) else None


def _verified_module(actor: Mapping, name: str) -> bool:
    """A capability is known only when the active host verified its module."""
    modules = actor.get("modules")
    entry = modules.get(name) if isinstance(modules, Mapping) else None
    return isinstance(entry, Mapping) and entry.get("verified") is True and entry.get("enabled") is True


def _servo_helper_ready(actor: Mapping, servos_by_ref: Mapping[str, Mapping],
                        helper_policy: Mapping) -> bool:
    """Do not divert an unobserved, damaged, wet or depleted Servo helper."""
    self_row = servos_by_ref.get(actor["sim_ref"])
    if not self_row or not self_row["needs_verified"]:
        return False
    needs = self_row["needs"]
    return (not self_row["broken"] and self_row.get("water_exposure", "NONE") == "NONE"
            and needs["charge"] >= helper_policy["min_helper_charge"]
            and needs["durability"] >= helper_policy["min_helper_durability"])


def _actor_can_help(actor: Mapping, proposal: Mapping, *, min_robotics: float) -> bool:
    """Qualified helper and exact target action, independent of input authority."""
    action_id, target = proposal["action_id"], proposal["target_ref"]
    kind = actor.get("kind")
    if action_id in HUMAN_ONLY_ACTIONS:
        return kind == "HUMAN"
    if action_id in ROBOT_CARE:
        if actor["sim_ref"] == target:
            return False
        if kind == "HUMAN":
            return True
        if kind == "SERVO":
            level = _verified_skill_level(actor, "robotics")
            return ((level is not None and level >= min_robotics)
                    or (action_id == "REPAIR_UTILIBOT"
                        and _verified_module(actor, "fix_o_matic")))
        return False
    if action_id == "SOCIALIZE_SERVO":
        return actor["sim_ref"] != target and kind in {"HUMAN", "SERVO"}
    if action_id in {"RECHARGE_SERVO", "SERVO_FUN_ACTIVITY", "SERVO_SELF_TUNE_UP"}:
        return kind == "SERVO" and actor["sim_ref"] == target
    return False


def _helper_iter(actors: list[dict], *, prefer_servo: bool) -> list[dict]:
    """Prefer eligible Servo peers for robot care; humans are fallbacks."""
    humans = [a for a in actors if a["kind"] == "HUMAN"]
    servos = [a for a in actors if a["kind"] == "SERVO"]
    return servos + humans if prefer_servo else humans + servos

def _validate(visit: Mapping) -> tuple[list[dict], list[dict], list[dict], list[dict], Mapping | None]:
    if not isinstance(visit, Mapping) or visit.get("schema") != SCHEMA:
        raise HouseholdUpkeepError("UPKEEP_SCHEMA_INVALID")
    servos, actors, actions = (visit.get(k) for k in ("servos", "actors", "observed_actions"))
    if not isinstance(servos, list) or len(servos) > MAX_SERVOS:
        raise HouseholdUpkeepError("UPKEEP_SERVOS_INVALID")
    if not isinstance(actors, list) or len(actors) > MAX_ACTORS:
        raise HouseholdUpkeepError("UPKEEP_ACTORS_INVALID")
    if not isinstance(actions, list) or len(actions) > MAX_ACTIONS:
        raise HouseholdUpkeepError("UPKEEP_ACTIONS_INVALID")
    bots = visit.get("utilibots", [])
    if not isinstance(bots, list) or len(bots) > 16:
        raise HouseholdUpkeepError("UPKEEP_UTILIBOTS_INVALID")
    ids: set[str] = set()
    cleaned_servos: list[dict] = []
    for row in servos:
        if not isinstance(row, Mapping) or not _ref(row.get("sim_ref")):
            raise HouseholdUpkeepError("UPKEEP_SERVO_REF_INVALID")
        ref = row["sim_ref"]
        if ref in ids:
            raise HouseholdUpkeepError("UPKEEP_DUPLICATE_SERVO")
        ids.add(ref)
        needs = row.get("needs")
        if not _bool(row.get("needs_verified")) or not _bool(row.get("broken")):
            raise HouseholdUpkeepError("UPKEEP_SERVO_PROOF_INVALID")
        if row["needs_verified"]:
            if not isinstance(needs, Mapping) or set(needs) != SERVO_NEEDS:
                raise HouseholdUpkeepError("UPKEEP_SERVO_NEEDS_INVALID")
            if not all(_num(v, upper=1) for v in needs.values()):
                raise HouseholdUpkeepError("UPKEEP_SERVO_MOTIVE_RANGE_INVALID")
        elif needs is not None:
            # No pretend four-need readings when a Servo is off-screen.
            raise HouseholdUpkeepError("UPKEEP_UNVERIFIED_SERVO_MOTIVES_MUST_BE_NULL")
        if row.get("water_exposure", "NONE") not in {"NONE", "RISK", "WET"}:
            raise HouseholdUpkeepError("UPKEEP_SERVO_WATER_INVALID")
        if row.get("maintenance_attempt", "NONE") not in ATTEMPTS:
            raise HouseholdUpkeepError("UPKEEP_SERVO_ATTEMPT_INVALID")
        if row.get("charge_attempt", "NONE") not in ATTEMPTS:
            raise HouseholdUpkeepError("UPKEEP_SERVO_CHARGE_ATTEMPT_INVALID")
        if row.get("self_tune_verified", False) not in (True, False) or type(row.get("self_tune_verified", False)) is not bool:
            raise HouseholdUpkeepError("UPKEEP_SELF_TUNE_PROOF_INVALID")
        cleaned_servos.append(dict(row))
    cleaned_bots: list[dict] = []
    for row in bots:
        if (not isinstance(row, Mapping) or not _ref(row.get("bot_ref"))
                or row.get("kind") not in UTILIBOT_KINDS):
            raise HouseholdUpkeepError("UPKEEP_UTILIBOT_IDENTITY_INVALID")
        if row["bot_ref"] in ids:
            raise HouseholdUpkeepError("UPKEEP_DUPLICATE_ROBOT_IDENTITY")
        ids.add(row["bot_ref"])
        if not _bool(row.get("needs_verified")) or not _bool(row.get("broken")):
            raise HouseholdUpkeepError("UPKEEP_UTILIBOT_PROOF_INVALID")
        meter = row.get("needs")
        if row["needs_verified"]:
            if not isinstance(meter, Mapping) or set(meter) != UTILIBOT_NEEDS:
                raise HouseholdUpkeepError("UPKEEP_UTILIBOT_NEEDS_INVALID")
            if not all(_num(v, upper=1) for v in meter.values()):
                raise HouseholdUpkeepError("UPKEEP_UTILIBOT_MOTIVE_RANGE_INVALID")
        elif meter is not None:
            raise HouseholdUpkeepError("UPKEEP_UTILIBOT_UNVERIFIED_MOTIVES_MUST_BE_NULL")
        if row.get("water_exposure", "NONE") not in {"NONE", "RISK", "WET"}:
            raise HouseholdUpkeepError("UPKEEP_UTILIBOT_WATER_INVALID")
        if any(row.get(k, "NONE") not in ATTEMPTS for k in ("maintenance_attempt", "charge_attempt")):
            raise HouseholdUpkeepError("UPKEEP_UTILIBOT_ATTEMPT_INVALID")
        cleaned_bots.append(dict(row))
    aid: set[str] = set()
    cleaned_actors: list[dict] = []
    for row in actors:
        if not isinstance(row, Mapping) or not _ref(row.get("sim_ref")):
            raise HouseholdUpkeepError("UPKEEP_ACTOR_REF_INVALID")
        if row["sim_ref"] in aid or row.get("kind") not in {"HUMAN", "SERVO"}:
            raise HouseholdUpkeepError("UPKEEP_ACTOR_KIND_DUPLICATE")
        aid.add(row["sim_ref"])
        if any(not _bool(row.get(k)) for k in
               ("available", "queue_verified", "player_reserved", "urgent_needs")):
            raise HouseholdUpkeepError("UPKEEP_ACTOR_FLAGS_INVALID")
        if row.get("multitasking") is not None and not _bool(row["multitasking"]):
            raise HouseholdUpkeepError("UPKEEP_MULTITASKING_INVALID")
        queue = row.get("queue")
        if not isinstance(queue, list) or len(queue) > 16:
            raise HouseholdUpkeepError("UPKEEP_ACTOR_QUEUE_INVALID")
        for action in queue:
            if (not isinstance(action, Mapping)
                    or not _ref(action.get("action_id"))
                    or action.get("origin") not in {"PLAYER", "HOST", "SIM_AUTONOMY", "UNKNOWN"}
                    or (action.get("target_ref") is not None and not _ref(action["target_ref"]))):
                raise HouseholdUpkeepError("UPKEEP_QUEUE_ROW_INVALID")
        skills = row.get("skills")
        if skills is not None:
            if not isinstance(skills, Mapping):
                raise HouseholdUpkeepError("UPKEEP_ACTOR_SKILLS_INVALID")
            cleaned_skills: dict = {}
            for skill_id, entry in skills.items():
                if not isinstance(skill_id, str) or not _ref(skill_id):
                    raise HouseholdUpkeepError("UPKEEP_ACTOR_SKILL_ID_INVALID")
                if not isinstance(entry, Mapping) or not _bool(entry.get("verified")):
                    raise HouseholdUpkeepError("UPKEEP_ACTOR_SKILL_PROOF_INVALID")
                level = entry.get("level")
                if entry["verified"]:
                    if not _num(level, lower=0, upper=SKILL_LEVEL_MAX):
                        raise HouseholdUpkeepError("UPKEEP_ACTOR_SKILL_LEVEL_INVALID")
                elif level is not None:
                    raise HouseholdUpkeepError("UPKEEP_UNVERIFIED_SKILL_LEVEL_MUST_BE_NULL")
                cleaned_skills[skill_id] = dict(entry)
            row = dict(row)
            row["skills"] = cleaned_skills
        modules = row.get("modules")
        if modules is not None:
            if not isinstance(modules, Mapping) or len(modules) > 8:
                raise HouseholdUpkeepError("UPKEEP_ACTOR_MODULES_INVALID")
            for module_id, record in modules.items():
                if (not _ref(module_id) or not isinstance(record, Mapping)
                        or not _bool(record.get("verified")) or not _bool(record.get("enabled"))):
                    raise HouseholdUpkeepError("UPKEEP_ACTOR_MODULE_PROOF_INVALID")
        cleaned_actors.append(dict(row))
    cleaned_actions: list[dict] = []
    for row in actions:
        if not isinstance(row, Mapping):
            raise HouseholdUpkeepError("UPKEEP_ACTION_ROW_INVALID")
        if not _ref(row.get("actor_ref")) or not _ref(row.get("target_ref")):
            raise HouseholdUpkeepError("UPKEEP_ACTION_IDENTITY_INVALID")
        if not _ref(row.get("action_id")) or not _bool(row.get("available")):
            raise HouseholdUpkeepError("UPKEEP_ACTION_AFFORDANCE_INVALID")
        cleaned_actions.append(dict(row))
    bill = visit.get("bill")
    if bill is not None:
        if not isinstance(bill, Mapping) or not _ref(bill.get("bill_ref")):
            raise HouseholdUpkeepError("UPKEEP_BILL_REF_INVALID")
        if bill.get("state") not in BILL_STATES or bill.get("attempt", "NONE") not in ATTEMPTS:
            raise HouseholdUpkeepError("UPKEEP_BILL_STATE_INVALID")
        amount, funds = bill.get("amount"), bill.get("household_funds")
        if amount is not None and not _num(amount):
            raise HouseholdUpkeepError("UPKEEP_BILL_AMOUNT_INVALID")
        if funds is not None and not _num(funds):
            raise HouseholdUpkeepError("UPKEEP_BILL_FUNDS_INVALID")
        due = bill.get("due_in_sim_hours")
        if due is not None and not _num(due, lower=-10000, upper=10000):
            raise HouseholdUpkeepError("UPKEEP_BILL_DUE_TIME_INVALID")
        if not _bool(bill.get("bill_verified")):
            raise HouseholdUpkeepError("UPKEEP_BILL_VERIFICATION_INVALID")
    return cleaned_servos, cleaned_bots, cleaned_actors, cleaned_actions, bill


LINT_STATES = {"CLEAN", "DIRTY", "UNKNOWN"}
LINT_LESS_STATES = {"INSTALLED", "NOT_INSTALLED", "UNKNOWN"}


def _validate_laundry(laundry: object) -> dict | None:
    if laundry is None:
        return None
    if not isinstance(laundry, Mapping):
        raise HouseholdUpkeepError("UPKEEP_LAUNDRY_INVALID")
    if "supervised" in laundry and not _bool(laundry["supervised"]):
        raise HouseholdUpkeepError("UPKEEP_LAUNDRY_SUPERVISED_INVALID")
    if "clothesline_available" in laundry and not _bool(laundry["clothesline_available"]):
        raise HouseholdUpkeepError("UPKEEP_LAUNDRY_CLOTHESLINE_INVALID")
    if laundry.get("dryer_lint_state", "UNKNOWN") not in LINT_STATES:
        raise HouseholdUpkeepError("UPKEEP_LAUNDRY_LINT_STATE_INVALID")
    if laundry.get("lint_less", "UNKNOWN") not in LINT_LESS_STATES:
        raise HouseholdUpkeepError("UPKEEP_LAUNDRY_LINT_LESS_INVALID")
    return dict(laundry)


def _laundry_policy(
    servo_health: list[dict],
    laundry: Mapping | None,
    *,
    fresh: bool,
    cfg: Mapping,
    levels: Mapping,
    prerequisite: str | None,
) -> dict:
    """Servo-household laundry/fire gate. Advisory; never an execution authority.

    Durability gates first (repair/tune before laundry autonomy), then the
    clothesline-over-dryer preference when unsupervised, then dryer lint rules.
    """
    fire = cfg["servo_fire_risk"]
    base = {
        "schema": "betterinstincts.household-upkeep-laundry/v1",
        "incident": fire["incident"],
        "preference_order": ["CLOTHESLINE", "DRYER_LINT_LESS", "DRYER_SUPERVISED_CLEAN_LINT"],
        "prerequisite_action": prerequisite,
        "dispatch_authorized": False,
        "proof_ceiling": fire["proof_ceiling"],
    }
    if not servo_health:
        return {**base, "state": "NOT_APPLICABLE_NO_SERVOS", "laundry_autonomy": "NOT_APPLICABLE",
                "action": "NO_SERVO_FIRE_POLICY"}
    unsafe = [h for h in servo_health
              if h["health"] == "BROKEN"
              or (h["needs_verified"] and h["needs"].get("durability", 1) <= levels["durability_critical"])]
    unverified = [h for h in servo_health if not h["needs_verified"]]
    if unsafe:
        return {**base, "state": "BLOCKED_REPAIR_FIRST", "laundry_autonomy": "BLOCKED",
                "action": "REPAIR_OR_TUNE_UP_SERVO_THEN_REOBSERVE_BEFORE_LAUNDRY",
                "blocking_servos": [h["servo_ref"] for h in unsafe]}
    if unverified:
        return {**base, "state": "HOLD_DURABILITY_UNVERIFIED", "laundry_autonomy": "HOLD",
                "action": "OBSERVE_SERVO_DURABILITY_BEFORE_LAUNDRY",
                "blocking_servos": [h["servo_ref"] for h in unverified]}
    if not fresh:
        return {**base, "state": "HOLD_REOBSERVE_STALE", "laundry_autonomy": "HOLD",
                "action": "REOBSERVE_BEFORE_LAUNDRY"}
    obs = laundry or {}
    supervised = obs.get("supervised", fire.get("default_supervised", False)) is True
    lint = obs.get("dryer_lint_state", "UNKNOWN")
    lint_less = obs.get("lint_less", "UNKNOWN")
    line = obs.get("clothesline_available") is True
    allowed = {**base, "laundry_autonomy": "ALLOWED_WITH_FIRE_POLICY"}
    if not supervised and line:
        return {**allowed, "state": "USE_CLOTHESLINE", "action": "PREFER_CLOTHESLINE_OVER_DRYER_UNSUPERVISED"}
    if lint_less == "INSTALLED":
        return {**allowed, "state": "DRYER_ALLOWED_LINT_LESS", "action": "DRYER_OK_LINT_LESS_INSTALLED"}
    if not supervised:
        return {**allowed, "laundry_autonomy": "HOLD", "state": "HOLD_UNSUPERVISED_NO_LINT_LESS",
                "action": "NO_UNSUPERVISED_DRYER_BUILD_CLOTHESLINE_OR_INSTALL_LINT_LESS_HANDINESS_UPGRADE"}
    if lint != "CLEAN":
        return {**allowed, "state": "CLEAN_LINT_THEN_DRYER_SUPERVISED",
                "action": "CLEAN_LINT_TRAP_THEN_REOBSERVE_THEN_SUPERVISED_DRYER"}
    return {**allowed, "state": "DRYER_ALLOWED_SUPERVISED_LINT_CLEAN",
            "action": "SUPERVISED_DRYER_WITH_CLEAN_LINT_TRAP"}


def evaluate_household_upkeep(
    observation: Mapping,
    *,
    capture_ref: str,
    now: float | None = None,
    player_directed: bool = False,
    already_busy: bool = False,
    build_or_buy_mode: bool = False,
    human_survival_hold: bool = False,
) -> dict:
    """Evaluate health on each tick; recommend at most one new queue action.

    A proposed action is NOT an execution authority. After enqueue, the host
    must reobserve the actor's queue and record its attempt state. After a bill
    payment, verify paid state with independent receipt; never double-charge.
    """
    if not _ref(capture_ref) or any(not _bool(v) for v in (
        player_directed, already_busy, build_or_buy_mode, human_survival_hold
    )):
        raise HouseholdUpkeepError("UPKEEP_CALL_INVALID")
    servos, bots, actors, actions, bill = _validate(observation)
    cfg = load_contract()
    levels = cfg["servo_thresholds"]
    instant = time.time() if now is None else now
    stamp = observation.get("observed_at_unix")
    fresh = (_num(instant) and _num(stamp) and
             0 <= instant - stamp <= cfg["bounds"]["max_capture_age_seconds"] and
             observation.get("capture_ref") == capture_ref and
             observation.get("household_verified") is True and
             observation.get("queue_verified") is True and
             observation.get("scene_verified") is True and
             all(a["queue_verified"] for a in actors))
    result = {
        "schema": "betterinstincts.household-upkeep-result/v1",
        "capture_ref": capture_ref,
        "gate": "UPKEEP_INSPECT",
        "action": "REOBSERVE_HOUSEHOLD",
        "servo_health": [],
        "utilibot_health": [],
        "bill_health": None,
        "next_actions": [],
        "candidate_count": 0,
        "next_monitor_seconds": cfg["bounds"]["next_observation_recommendation_seconds"],
        "dispatch_authorized": False,
        "cancel_allowed": False,
        "proof_ceiling": "OFFLINE_SERVO_BILLS_PLAN_NOT_GAME_QUEUE_OR_PAYMENT",
    }
    # Health is always surveyed, even while another domain owns screen input.
    candidates: list[dict] = []
    for servo in servos:
        vals = servo.get("needs") or {}
        health = {
            "servo_ref": servo["sim_ref"],
            "needs": dict(vals),
            "needs_verified": servo["needs_verified"],
            "broken": servo["broken"],
            "water_exposure": servo.get("water_exposure", "NONE"),
            "maintenance_attempt": servo.get("maintenance_attempt", "NONE"),
            "charge_attempt": servo.get("charge_attempt", "NONE"),
            "health": "UNVERIFIED",
        }
        if servo["needs_verified"]:
            if servo["broken"]:
                health["health"] = "BROKEN"
            elif vals["durability"] <= levels["durability_critical"] or vals["charge"] <= levels["charge_critical"]:
                health["health"] = "CRITICAL"
            elif vals["durability"] <= levels["durability_watch"] or vals["charge"] <= levels["charge_watch"] or vals["fun"] <= levels["fun_watch"] or vals["social"] <= levels["social_watch"]:
                health["health"] = "WATCH"
            else:
                health["health"] = "STABLE"
        result["servo_health"].append(health)
        if not servo["needs_verified"] or servo.get("water_exposure") == "WET":
            continue
        target = servo["sim_ref"]
        if servo["broken"]:
            if servo.get("maintenance_attempt", "NONE") == "NONE":
                candidates.append(dict(rank=0, action_id="REPAIR_SERVO",
                                       target_ref=target, kind="SERVO_REPAIR"))
        elif vals["durability"] <= levels["durability_watch"]:
            if servo.get("maintenance_attempt", "NONE") == "NONE":
                candidates.append(dict(rank=1 if vals["durability"] <= levels["durability_critical"] else 5,
                                       action_id="TUNE_UP_SERVO",
                                       target_ref=target, kind="SERVO_TUNE_UP"))
                if (servo.get("self_tune_verified") is True
                        and vals["durability"] > levels["durability_critical"]):
                    candidates.append(dict(rank=8, action_id="SERVO_SELF_TUNE_UP",
                                           target_ref=target, kind="SERVO_SELF_MAINTENANCE"))
        if vals["charge"] <= levels["charge_watch"] and not servo["broken"]:
            if servo.get("charge_attempt", "NONE") == "NONE":
                candidates.append(dict(rank=2 if vals["charge"] <= levels["charge_critical"] else 6,
                                       action_id="RECHARGE_SERVO",
                                       target_ref=target, kind="SERVO_RECHARGE"))
        if vals["social"] <= levels["social_watch"]:
            candidates.append(dict(rank=9, action_id="SOCIALIZE_SERVO",
                                   target_ref=target, kind="SERVO_SOCIAL"))
        if vals["fun"] <= levels["fun_watch"]:
            candidates.append(dict(rank=10, action_id="SERVO_FUN_ACTIVITY",
                                   target_ref=target, kind="SERVO_FUN"))
    # Utili-Bots are game objects, not household Sims: never add human motives.
    # The same observed-menu/actor/queue safety gate applies to all robot care.
    bot_limits = cfg["utilibot_policy"]["thresholds"]
    for bot in bots:
        vals = bot.get("needs") or {}
        status = "UNVERIFIED"
        if bot["needs_verified"]:
            if bot["broken"]:
                status = "BROKEN"
            elif (vals["durability"] <= bot_limits["durability_critical"]
                  or vals["charge"] <= bot_limits["charge_critical"]):
                status = "CRITICAL"
            elif (vals["durability"] <= bot_limits["durability_watch"]
                  or vals["charge"] <= bot_limits["charge_watch"]):
                status = "WATCH"
            else:
                status = "STABLE"
        result["utilibot_health"].append({
            "bot_ref": bot["bot_ref"], "kind": bot["kind"],
            "needs_verified": bot["needs_verified"], "needs": dict(vals),
            "broken": bot["broken"], "health": status,
            "water_exposure": bot.get("water_exposure", "NONE"),
            "maintenance_attempt": bot.get("maintenance_attempt", "NONE"),
            "charge_attempt": bot.get("charge_attempt", "NONE"),
        })
        if not bot["needs_verified"] or bot.get("water_exposure", "NONE") != "NONE":
            continue
        target = bot["bot_ref"]
        if bot["broken"]:
            if bot.get("maintenance_attempt", "NONE") == "NONE":
                candidates.append(dict(rank=0, action_id="REPAIR_UTILIBOT",
                                       target_ref=target, target_kind=bot["kind"],
                                       kind="UTILIBOT_REPAIR"))
        else:
            if (vals["durability"] <= bot_limits["durability_watch"]
                    and bot.get("maintenance_attempt", "NONE") == "NONE"):
                candidates.append(dict(
                    rank=4 if vals["durability"] <= bot_limits["durability_critical"] else 8,
                    action_id="TUNE_UP_UTILIBOT", target_ref=target,
                    target_kind=bot["kind"], kind="UTILIBOT_TUNE_UP"))
            if (vals["charge"] <= bot_limits["charge_watch"]
                    and bot.get("charge_attempt", "NONE") == "NONE"):
                candidates.append(dict(
                    rank=3 if vals["charge"] <= bot_limits["charge_critical"] else 7,
                    action_id="RECHARGE_UTILIBOT", target_ref=target,
                    target_kind=bot["kind"], kind="UTILIBOT_CHARGE"))
    if bill is not None:
        state, attempt = bill["state"], bill.get("attempt", "NONE")
        amount, funds, due = bill.get("amount"), bill.get("household_funds"), bill.get("due_in_sim_hours")
        verified_paid = (state == "PAID" and _ref(bill.get("payment_proof_ref"))
                         and _ref(bill.get("outcome_capture_ref")))
        result["bill_health"] = {
            "bill_ref": bill["bill_ref"], "state": "VERIFIED_PAID" if verified_paid
            else "PAID_UNVERIFIED" if state == "PAID" else state,
            "amount": amount, "household_funds": funds,
            "due_in_sim_hours": due, "attempt": attempt,
            "affordable": _num(amount) and _num(funds) and funds >= amount,
        }
        if (bill["bill_verified"] and state == "UNPAID"
                and attempt == "NONE" and _num(amount) and amount > 0
                and _num(funds) and funds >= amount
                and due is not None and due <= cfg["bill_policy"]["pre_due_window_sim_hours"]
                and observation.get("bill_payment_authorized") is True):
            candidates.append(dict(
                rank=0 if due <= -24 else 3 if due <= 0 else 7,
                action_id="PAY_BILLS", target_ref=bill["bill_ref"],
                kind="HOUSEHOLD_BILLS",
                amount=amount,
            ))
    result["candidate_count"] = len(candidates)
    maint = sorted((c for c in candidates if c["action_id"] in SERVO_MAINTENANCE),
                   key=lambda c: (c["rank"], c["target_ref"], c["action_id"]))
    result["laundry_policy"] = _laundry_policy(
        result["servo_health"], _validate_laundry(observation.get("laundry")),
        fresh=fresh, cfg=cfg, levels=levels,
        prerequisite=maint[0]["action_id"] if maint else None,
    )

    def finish(gate: str, action: str) -> dict:
        result.update(gate=gate, action=action)
        return result

    if not fresh:
        return finish("UPKEEP_REOBSERVE", "INSPECT_FRESH_SERVOS_BILLS_AND_QUEUES")
    if player_directed or already_busy:
        return finish("UPKEEP_PLAYER_FIRST", "PRESERVE_GOALS_NO_INPUT")
    if build_or_buy_mode:
        return finish("UPKEEP_LIVE_REQUIRED", "REOBSERVE_LIVE_MODE")
    if human_survival_hold:
        return finish("UPKEEP_HUMAN_NEEDS_FIRST", "PRESERVE_UPKEEP_PENDING")
    if not candidates:
        return finish("UPKEEP_MONITOR", "RECHECK_ON_NEXT_AUTHORIZED_TICK")

    # Any unread player/unknown queue entry could hide a pending bill or
    # explicit command. Never infer safe queue ownership from UI label alone.
    if any(item["origin"] in {"PLAYER", "UNKNOWN"} for actor in actors for item in actor["queue"]):
        return finish("UPKEEP_QUEUE_ORIGIN_HOLD", "REOBSERVE_PLAYER_QUEUE")

    candidates.sort(key=lambda c: (c["rank"], c["target_ref"], c["action_id"]))
    helper_policy = cfg.get("servo_helper_policy") or {}
    min_robotics = float(helper_policy.get("min_robotics_level", 3))
    if not _num(min_robotics, lower=0, upper=SKILL_LEVEL_MAX):
        raise HouseholdUpkeepError("UPKEEP_HELPER_ROBOTICS_THRESHOLD_INVALID")
    allow_servo_helpers = helper_policy.get("allow_servo_peer_helpers", True) is True
    servo_by_ref = {s["sim_ref"]: s for s in servos}
    skill_gap_seen = False
    helper_motive_gap_seen = False
    for proposal in candidates:
        if any(item["action_id"] == proposal["action_id"]
               and item.get("target_ref") == proposal["target_ref"]
               for actor in actors for item in actor["queue"]):
            continue
        for actor in _helper_iter(
            actors,
            prefer_servo=(proposal["action_id"] in ROBOT_CARE
                          and helper_policy.get("prefer_verified_servo_peers_for_robot_care") is True),
        ):
            if (not actor["available"] or actor["player_reserved"]
                    or actor["urgent_needs"]):
                continue
            if actor["kind"] == "SERVO":
                if proposal["action_id"] in ROBOT_CARE and not allow_servo_helpers:
                    continue
                if proposal["action_id"] == "SERVO_SELF_TUNE_UP":
                    source = servo_by_ref.get(actor["sim_ref"])
                    if (not source or source.get("self_tune_verified") is not True
                            or not source["needs_verified"] or source["broken"]
                            or source.get("water_exposure", "NONE") != "NONE"
                            or source["needs"]["charge"] < helper_policy["min_helper_charge"]):
                        continue
                elif proposal["action_id"] != "RECHARGE_SERVO" and not _servo_helper_ready(
                    actor, servo_by_ref, helper_policy
                ):
                    helper_motive_gap_seen = True
                    continue
                if proposal["action_id"] in ROBOT_CARE and actor["sim_ref"] != proposal["target_ref"]:
                    level = _verified_skill_level(actor, "robotics")
                    module_ok = (proposal["action_id"] == "REPAIR_UTILIBOT"
                                 and _verified_module(actor, "fix_o_matic"))
                    if not module_ok and (level is None or level < min_robotics):
                        skill_gap_seen = True
                        continue
            if not _actor_can_help(actor, proposal, min_robotics=min_robotics):
                continue
            try:
                capacity = evaluate_queue_capacity(
                    [q["action_id"] for q in actor["queue"]],
                    multitasking=actor.get("multitasking"),
                    player_directed=False,
                )
            except QueueCapacityError as exc:
                raise HouseholdUpkeepError(str(exc)) from exc
            if not capacity["enqueue_allowed"]:
                continue
            row = next((r for r in actions if
                        r["action_id"] == proposal["action_id"]
                        and r["actor_ref"] == actor["sim_ref"]
                        and r["target_ref"] == proposal["target_ref"]
                        and r.get("capture_ref") == capture_ref
                        and r["available"]), None)
            if row is None:
                continue
            # A queued proposal must still pass a separate local screen lease.
            selected = {k: row[k] for k in
                        ("action_id", "actor_ref", "target_ref", "capture_ref")}
            selected["proposal_kind"] = proposal["kind"]
            if "target_kind" in proposal:
                selected["target_kind"] = proposal["target_kind"]
            selected["priority"] = proposal["rank"]
            selected["proposal_key"] = ":".join(
                (capture_ref, actor["sim_ref"], proposal["action_id"], proposal["target_ref"])
            )
            if actor["kind"] == "SERVO" and proposal["action_id"] in ROBOT_CARE:
                selected["helper_kind"] = "SERVO_PEER"
                selected["helper_robotics_level"] = _verified_skill_level(actor, "robotics")
                selected["helper_qualification"] = (
                    "FIX_O_MATIC" if proposal["action_id"] == "REPAIR_UTILIBOT"
                    and _verified_module(actor, "fix_o_matic") else "ROBOTICS"
                )
            elif proposal["action_id"] in ROBOT_CARE:
                selected["helper_kind"] = "HUMAN"
            if "amount" in proposal:
                selected["observed_bill_amount"] = proposal["amount"]
            result["next_actions"] = [selected]
            return finish("UPKEEP_ACTION_READY", "QUEUE_ONE_VERIFIED_HOUSEHOLD_ACTION_THEN_REOBSERVE")
    if skill_gap_seen and any(c["action_id"] in ROBOT_CARE for c in candidates):
        result["skill_force_hint"] = {
            "bundle": "servo_core",
            "skills": ["robotics", "handiness"],
            "min_robotics_level": min_robotics,
            "cli": "python -m scripts.diy_skill_force level --bundle servo_core --execute",
            "proof_ceiling": "HOST_SKILL_FORCE_HINT_NOT_PANEL_PASS_NOT_BI005",
        }
        return finish(
            "UPKEEP_HELPER_SKILL_GAP",
            "LEVEL_HELPER_ROBOTICS_VIA_DIY_SKILL_FORCE_THEN_REOBSERVE",
        )
    if helper_motive_gap_seen:
        return finish("UPKEEP_HELPER_NEEDS_UNVERIFIED_OR_LOW",
                      "RECHARGE_OR_VERIFY_SERVO_HELPER_BEFORE_COOPERATION")
    return finish("UPKEEP_NO_SAFE_ACTOR_OR_AFFORDANCE", "INSPECT_HOUSEHOLD_HELPER_QUEUE_OR_MENU")
