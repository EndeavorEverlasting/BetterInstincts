"""Bounded, observation-only Servo health and household bill queue policy.

P95 program seam; P124 composes with host_stack/host_listener, existing
queue_capacity and budget guards. Does NOT poll Windows, click Sims, run a
daemon, move assets or certify in-game outcomes.
"""
from __future__ import annotations

import math
import time
from collections.abc import Mapping

from betterinstincts.queue_capacity import QueueCapacityError, evaluate_queue_capacity

SCHEMA = "betterinstincts.household-upkeep/v1"
MAX_SERVOS = 16
MAX_ACTORS = 16
MAX_ACTIONS = 64
MAX_CAPTURE_AGE_SECONDS = 180
SERVO_NEEDS = frozenset({"durability", "charge", "fun", "social"})
ACTIONS = {"TUNE_UP_SERVO", "REPAIR_SERVO", "RECHARGE_SERVO",
           "SERVO_SELF_TUNE_UP", "PAY_BILLS"}
ATTEMPTS = {"NONE", "QUEUED", "DISPATCHED"}
BILL_STATES = {"UNPAID", "PAID", "NOT_DUE", "UNKNOWN"}


class HouseholdUpkeepError(ValueError):
    pass


def _ref(v: object) -> bool:
    return isinstance(v, str) and 1 <= len(v) <= 120 and all(
        c.isalnum() or c in "_.:-" for c in v
    )


def _num(v: object, *, lower: float = 0, upper: float | None = None) -> bool:
    return (type(v) in (int, float) and math.isfinite(v)
            and v >= lower and (upper is None or v <= upper))


def _bool(v: object) -> bool:
    return type(v) is bool


def _validate(visit: Mapping) -> tuple[list[dict], list[dict], list[dict], Mapping | None]:
    if not isinstance(visit, Mapping) or visit.get("schema") != SCHEMA:
        raise HouseholdUpkeepError("UPKEEP_SCHEMA_INVALID")
    servos, actors, actions = (visit.get(k) for k in ("servos", "actors", "observed_actions"))
    if not isinstance(servos, list) or len(servos) > MAX_SERVOS:
        raise HouseholdUpkeepError("UPKEEP_SERVOS_INVALID")
    if not isinstance(actors, list) or len(actors) > MAX_ACTORS:
        raise HouseholdUpkeepError("UPKEEP_ACTORS_INVALID")
    if not isinstance(actions, list) or len(actions) > MAX_ACTIONS:
        raise HouseholdUpkeepError("UPKEEP_ACTIONS_INVALID")
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
        if not isinstance(needs, Mapping) or set(needs) != SERVO_NEEDS:
            raise HouseholdUpkeepError("UPKEEP_SERVO_NEEDS_INVALID")
        if not all(_num(v, upper=1) for v in needs.values()):
            raise HouseholdUpkeepError("UPKEEP_SERVO_MOTIVE_RANGE_INVALID")
        if not _bool(row.get("needs_verified")) or not _bool(row.get("broken")):
            raise HouseholdUpkeepError("UPKEEP_SERVO_PROOF_INVALID")
        if row.get("water_exposure", "NONE") not in {"NONE", "RISK", "WET"}:
            raise HouseholdUpkeepError("UPKEEP_SERVO_WATER_INVALID")
        if row.get("maintenance_attempt", "NONE") not in ATTEMPTS:
            raise HouseholdUpkeepError("UPKEEP_SERVO_ATTEMPT_INVALID")
        if row.get("charge_attempt", "NONE") not in ATTEMPTS:
            raise HouseholdUpkeepError("UPKEEP_SERVO_CHARGE_ATTEMPT_INVALID")
        cleaned_servos.append(dict(row))
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
    return cleaned_servos, cleaned_actors, cleaned_actions, bill


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
    servos, actors, actions, bill = _validate(observation)
    instant = time.time() if now is None else now
    stamp = observation.get("observed_at_unix")
    fresh = (_num(instant) and _num(stamp) and
             0 <= instant - stamp <= MAX_CAPTURE_AGE_SECONDS and
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
        "bill_health": None,
        "next_actions": [],
        "candidate_count": 0,
        "dispatch_authorized": False,
        "cancel_allowed": False,
        "proof_ceiling": "OFFLINE_SERVO_BILLS_PLAN_NOT_GAME_QUEUE_OR_PAYMENT",
    }
    # Health is always surveyed, even while another domain owns screen input.
    candidates: list[dict] = []
    for servo in servos:
        vals = servo["needs"]
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
            elif vals["durability"] <= .20 or vals["charge"] <= .15:
                health["health"] = "CRITICAL"
            elif vals["durability"] <= .50 or vals["charge"] <= .35:
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
        elif vals["durability"] <= .50:
            if servo.get("maintenance_attempt", "NONE") == "NONE":
                candidates.append(dict(rank=1 if vals["durability"] <= .20 else 5,
                                       action_id="TUNE_UP_SERVO",
                                       target_ref=target, kind="SERVO_TUNE_UP"))
        if vals["charge"] <= .35 and not servo["broken"]:
            if servo.get("charge_attempt", "NONE") == "NONE":
                candidates.append(dict(rank=2 if vals["charge"] <= .15 else 6,
                                       action_id="RECHARGE_SERVO",
                                       target_ref=target, kind="SERVO_RECHARGE"))
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
                and due is not None and due <= 72
                and observation.get("bill_payment_authorized") is True):
            candidates.append(dict(
                rank=0 if due <= -24 else 3 if due <= 0 else 7,
                action_id="PAY_BILLS", target_ref=bill["bill_ref"],
                kind="HOUSEHOLD_BILLS",
                amount=amount,
            ))
    result["candidate_count"] = len(candidates)

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
    for proposal in candidates:
        if any(item["action_id"] == proposal["action_id"]
               and item.get("target_ref") == proposal["target_ref"]
               for actor in actors for item in actor["queue"]):
            continue
        for actor in actors:
            if (not actor["available"] or actor["player_reserved"]
                    or actor["urgent_needs"]):
                continue
            if proposal["action_id"] in {"TUNE_UP_SERVO", "REPAIR_SERVO"} and actor["kind"] != "HUMAN":
                continue
            if proposal["action_id"] == "RECHARGE_SERVO" and (
                actor["kind"] != "SERVO" or actor["sim_ref"] != proposal["target_ref"]
            ):
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
            selected["proposal_key"] = ":".join(
                (capture_ref, actor["sim_ref"], proposal["action_id"], proposal["target_ref"])
            )
            if "amount" in proposal:
                selected["observed_bill_amount"] = proposal["amount"]
            result["next_actions"] = [selected]
            return finish("UPKEEP_ACTION_READY", "QUEUE_ONE_VERIFIED_HOUSEHOLD_ACTION_THEN_REOBSERVE")
    return finish("UPKEEP_NO_SAFE_ACTOR_OR_AFFORDANCE", "INSPECT_HOUSEHOLD_HELPER_QUEUE_OR_MENU")
