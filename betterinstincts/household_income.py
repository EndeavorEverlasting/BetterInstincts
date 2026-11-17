"""One shared income goal, with at most one next portrait or queue recommendation."""
from __future__ import annotations

import json
import re
from collections.abc import Mapping
from fractions import Fraction
from pathlib import Path

from betterinstincts.budget_eval import household_reserve
from betterinstincts.funds_inject import MAX_HOUSEHOLD_FUNDS
from betterinstincts.queue_capacity import evaluate_queue_capacity
from betterinstincts.robotics_income import evaluate_robotics_income

CONTRACT = Path(__file__).resolve().parents[1] / "contracts/household-economy.v1.json"
REF = re.compile(r"[A-Za-z0-9:_./-]{3,160}")
BUILD = re.compile(r"[0-9]+(?:\.[0-9]+){3}")
MAX_MINUTES = 10080


def _ref(value: object) -> bool:
    return isinstance(value, str) and bool(REF.fullmatch(value))


def _integer(value: object, maximum: int, minimum: int = 0) -> bool:
    return type(value) is int and minimum <= value <= maximum


def _catalog() -> dict:
    income = json.loads(CONTRACT.read_text(encoding="utf-8"))["income"]
    return {row["id"]: row for row in income["catalog"]}


def _queues(packet: Mapping, members: list[dict]) -> tuple[dict, set, set, int] | None:
    """Cross-check every visible queue row and aggregate committed household costs."""
    observed = packet.get("queues")
    if not isinstance(observed, Mapping) or set(observed) != {m["member_key"] for m in members}:
        return None
    queues, tasks, resources, committed = {}, set(), set(), 0
    for member in members:
        key = member["member_key"]
        rows = observed[key]
        if (not member["queue_verified"] or not isinstance(rows, list)
                or len(rows) != len(member["queue"]) or len(rows) > 16):
            return None
        actions = set()
        for label, row in zip(member["queue"], rows):
            if (not isinstance(row, Mapping) or row.get("label") != label
                    or row.get("origin") not in ("SIM_AUTONOMY", "BETTERINSTINCTS", "PLAYER")
                    or not _ref(row.get("action_id"))
                    or not _integer(row.get("upfront_unpaid"), MAX_HOUSEHOLD_FUNDS)):
                return None
            action = row["action_id"]
            actions.add(action)
            for field, claims in (("task_ref", tasks), ("resource_ref", resources)):
                value = row.get(field)
                if value is not None:
                    if not _ref(value):
                        return None
                    claims.add(value)
            committed += row["upfront_unpaid"]
        queues[key] = (actions, any(row["origin"] == "PLAYER" for row in rows),
                       bool(rows) and all(row.get("lane") == "INCOME" for row in rows))
    return queues, tasks, resources, committed


def _economics(offer: Mapping, activity: Mapping, robotics: Mapping) -> tuple[int, Fraction] | None:
    if activity["mode"] == "ROBOTICS_RECEIPTS":
        result = robotics.get(offer["member_key"], {}).get(offer["action_id"], {})
        if result.get("state") != "POSITIVE_NET_CANDIDATE":
            return None
        return result["upfront_cash"], Fraction(str(result["projected_net_per_sim_hour"]))
    cash = offer.get("upfront_cash")
    net = offer.get("settled_net")
    minutes = offer.get("settled_minutes")
    if (not _ref(offer.get("settlement_proof_ref"))
            or offer.get("settlement_proof_ref") == offer.get("affordance_ref")
            or not _integer(cash, MAX_HOUSEHOLD_FUNDS)
            or not _integer(net, MAX_HOUSEHOLD_FUNDS, 1)
            or not _integer(minutes, MAX_MINUTES, 1)):
        return None
    return cash, Fraction(60 * net, minutes)


def evaluate_household_income(
    packet: object, *, capture_ref: str, scope_id: str, members: list[dict],
    selected: Mapping | None, ready_members: set[str], reserved_resources: set[str],
    failed_tasks: set[str],
) -> dict:
    """Rank current verified offers with one budget and reservations across the roster."""
    report = {"goal_id": "household-earned-income", "state": "INCOME_REOBSERVE",
              "next": None, "execute_allowed": False, "capture_ref": capture_ref}
    if (not isinstance(packet, Mapping) or packet.get("capture_ref") != capture_ref
            or packet.get("scope_id") != scope_id or selected is None
            or not _ref(packet.get("save_ref")) or not _ref(packet.get("funds_proof_ref"))
            or not BUILD.fullmatch(str(packet.get("game_build", "")))
            or not _integer(packet.get("household_funds"), MAX_HOUSEHOLD_FUNDS)):
        return report
    budget = household_reserve(packet["household_funds"])
    report.update(income_goal=budget["income_goal"], scope_id=scope_id)
    if packet.get("pending_effect") is not False:
        return {**report, "state": "INCOME_RECONCILE_PENDING_EFFECT"}
    queues = _queues(packet, members)
    windows = packet.get("windows")
    offers = packet.get("offers")
    if (queues is None or not isinstance(windows, Mapping)
            or not isinstance(offers, list) or len(offers) > 48
            or not all(isinstance(row, Mapping) and _ref(row.get("task_ref")) for row in offers)
            or len({row["task_ref"] for row in offers}) != len(offers)):
        return report
    queue_rows, held_tasks, resources, committed = queues
    # A shared commitment consumes household surplus before any member can use it.
    spendable = max(0, budget["spend_max"] - committed)
    held_resources = resources | reserved_resources
    excluded_tasks = held_tasks | failed_tasks
    catalog = _catalog()
    robotics = {}
    if packet.get("robotics") is not None:
        if (not isinstance(packet["robotics"], Mapping)
                or packet["robotics"].get("available_funds") != packet["household_funds"]):
            return report
        robotics = evaluate_robotics_income(
            packet["robotics"], household_ref=scope_id, game_build=packet["game_build"],
            save_ref=packet["save_ref"], capture_ref=capture_ref,
        )["offers"]
    eligible = []
    for index, actor in enumerate(members):
        key = actor["member_key"]
        window = windows.get(key)
        if (key not in ready_members or queue_rows[key][1]
                or (actor["busy"] and not queue_rows[key][2])
                or not isinstance(window, Mapping) or window.get("protected_work") is not False
                or window.get("capture_ref") != capture_ref
                or not _integer(window.get("safe_minutes"), MAX_MINUTES)
                or not _integer(window.get("queued_minutes"), MAX_MINUTES)
                or not _integer(window.get("reserved_slots"), 7)):
            continue
        quota = evaluate_queue_capacity(actor["queue"], multitasking=actor["multitasking"])["max_new_actions"]
        if quota <= window["reserved_slots"]:
            continue
        remaining = window["safe_minutes"] - window["queued_minutes"]
        for offer in offers:
            activity_id, resource, action_id = (
                offer.get("activity_id"), offer.get("resource_ref"), offer.get("action_id"),
            )
            if (offer.get("member_key") != key or offer.get("capture_ref") != capture_ref
                    or offer.get("enabled") is not True or offer["task_ref"] in excluded_tasks
                    or not _ref(activity_id) or not _ref(resource) or resource in held_resources
                    or not _ref(action_id) or action_id in queue_rows[key][0]
                    or not _ref(offer.get("affordance_ref"))
                    or not _integer(offer.get("upper_minutes"), MAX_MINUTES, 1)
                    or offer["upper_minutes"] > remaining):
                continue
            activity = catalog.get(activity_id)
            if activity is None or activity["mode"] == "DISCOVERY_ONLY":
                continue
            economics = _economics(offer, activity, robotics)
            if economics is None or economics[0] > spendable:
                continue
            cash, rate = economics
            # Keep filling the current portrait while it can take eligible work.
            # When switching, rank alternatives by net return and stable roster order.
            score = (key != selected["member_key"], -rate, index, offer["task_ref"])
            eligible.append((score, key, offer, cash))
    if not eligible:
        return {**report, "state": "NO_SAFE_PROFITABLE_INCOME_ACTION"}
    _, key, offer, cash = min(eligible, key=lambda row: row[0])
    handoff = key != selected["member_key"]
    return {
        **report, "state": "HOUSEHOLD_INCOME_PORTRAIT_READY" if handoff else "HOUSEHOLD_INCOME_ENQUEUE_READY",
        "game_build": packet["game_build"],
        "save_ref": packet["save_ref"],
        "member_keys": [member["member_key"] for member in members],
        "next": {
            "action": "SELECT_PORTRAIT_THEN_REOBSERVE_ACTOR_AND_NEEDS" if handoff
                      else "REVALIDATE_AND_ENQUEUE_ONE_INCOME_ACTION",
            "from_member_key": selected["member_key"], "to_member_key": key,
            "task_ref": offer["task_ref"], "activity_id": offer["activity_id"],
            "action_id": offer["action_id"], "resource_ref": offer["resource_ref"],
            "affordance_ref": offer["affordance_ref"], "upfront_cash": cash,
            "capture_ref": capture_ref, "new_capture_required": True, "execute_allowed": False,
        },
    }
