"""Shared income allocation through the verified household roster."""
import unittest

from betterinstincts.household_economy import evaluate_household_economy
from betterinstincts.host_stack import evaluate_turn
from tests.test_household_economy import CAP, NEEDS, snapshot


def setup():
    row = snapshot(3)
    ids = [m["member_key"] for m in row["members"]]
    for member in row["members"]:
        member["activity"] = "AWAKE"
    row["selected_member_key"] = ids[0]
    row["income"] = {
        "capture_ref": CAP, "scope_id": row["scope"]["scope_id"],
        "save_ref": "save:income-test", "game_build": "1.121.361.1020",
        "household_funds": 1_000_300, "funds_proof_ref": "hud:funds",
        "pending_effect": False, "queues": {key: [] for key in ids},
        "windows": {key: dict(capture_ref=CAP, protected_work=False, safe_minutes=45,
                              queued_minutes=0, reserved_slots=0) for key in ids},
        "offers": [],
    }
    return row, ids


def offer(key, seq, **changes):
    return {"member_key": key, "task_ref": f"task:income-{seq}",
            "activity_id": "art-paint-and-sell", "resource_ref": f"station:{seq}",
            "action_id": f"act:income-{seq}", "capture_ref": CAP, "enabled": True,
            "affordance_ref": f"affordance:{seq}", "settlement_proof_ref": f"outcome:{seq}",
            "upper_minutes": 10, "settled_net": 80, "settled_minutes": 20,
            "upfront_cash": 100, **changes}


def add_queue(row, member_index, *, count=1, origin="BETTERINSTINCTS",
              task_ref=None, action_id=None, resource_ref=None, cash=0):
    member = row["members"][member_index]
    key = member["member_key"]
    for index in range(count):
        label = f"queued-{index}"
        member["queue"].append(label)
        row["income"]["queues"][key].append(
            dict(label=label, origin=origin, action_id=action_id or f"act:queued-{index}",
                 task_ref=task_ref, resource_ref=resource_ref, upfront_unpaid=cash, lane="INCOME"))


def income(row):
    result = evaluate_household_economy(row)["income"]
    assert result["execute_allowed"] is False
    return result


class HouseholdIncomeTests(unittest.TestCase):
    def test_fill_one_then_rotate_at_reserved_limit(self):
        row, ids = setup()
        row["income"]["offers"] = [offer(ids[0], "first"), offer(ids[1], "second"),
                                    offer(ids[2], "third", settled_net=150)]
        initial = income(row)
        self.assertEqual(initial["state"], "HOUSEHOLD_INCOME_ENQUEUE_READY")
        self.assertEqual(initial["next"]["to_member_key"], ids[0])
        self.assertTrue(initial["next"]["new_capture_required"])
        row["members"][0]["multitasking"] = True
        add_queue(row, 0, count=1)
        row["income"]["windows"][ids[0]]["reserved_slots"] = 1
        rotated = income(row)
        self.assertEqual(rotated["state"], "HOUSEHOLD_INCOME_PORTRAIT_READY")
        self.assertEqual(rotated["next"]["to_member_key"], ids[2])
        row["selected_member_key"] = ids[2]
        self.assertEqual(income(row)["next"]["action"], "REVALIDATE_AND_ENQUEUE_ONE_INCOME_ACTION")

    def test_duplicate_resources_pending_effect_and_shared_spend(self):
        row, ids = setup()
        add_queue(row, 0, task_ref="task:already", resource_ref="station:shared", cash=250)
        row["income"]["offers"] = [offer(ids[1], "costly", settled_net=300),
                                    offer(ids[1], "busy", resource_ref="station:shared", upfront_cash=0),
                                    offer(ids[1], "same", task_ref="task:already", upfront_cash=0),
                                    offer(ids[1], "free", upfront_cash=0)]
        self.assertEqual(income(row)["next"]["task_ref"], "task:income-free")
        row["income"]["pending_effect"] = True
        self.assertEqual(income(row)["state"], "INCOME_RECONCILE_PENDING_EFFECT")

    def test_needs_career_queue_owner_and_deadline_are_protected(self):
        row, ids = setup()
        row["income"]["offers"] = [offer(key, str(i)) for i, key in enumerate(ids)]
        row["members"][0]["needs"]["hunger"] = 0.1
        row["members"][1]["activity"] = "AT_WORK"
        row["income"]["windows"][ids[2]]["protected_work"] = True
        self.assertIsNone(income(row)["next"])
        window = row["income"]["windows"][ids[2]]
        window.update(protected_work=False, safe_minutes=15, queued_minutes=10)
        self.assertIsNone(income(row)["next"])
        window["queued_minutes"] = 0
        add_queue(row, 2, origin="PLAYER")
        self.assertIsNone(income(row)["next"])

    def test_business_remains_discovery_and_nonpositive_is_held(self):
        row, ids = setup()
        row["income"]["offers"] = [offer(ids[0], "business", activity_id="small-business"),
                                    offer(ids[1], "loss", settled_net=-1),
                                    offer(ids[2], "robot", activity_id="robotics-craft-and-sell")]
        self.assertIsNone(income(row)["next"])
        row["income"]["offers"] = [offer(ids[0], "free", upfront_cash=0)]
        row["income"]["household_funds"] = 999_000
        self.assertEqual(income(row)["income_goal"], "EARN_TO_RESTORE_RESERVE")
        self.assertEqual(income(row)["next"]["task_ref"], "task:income-free")

    def test_host_turn_uses_income_after_protected_gates(self):
        row, ids = setup()
        row["income"]["offers"] = [offer(ids[0], "active")]
        turn = evaluate_turn(NEEDS, household_economy=row, capture_ref=CAP, location_kind="home",
                             queue=[], viewport={"state": "VIEWPORT_OK"})
        self.assertEqual(turn["next_gate"], "HOUSEHOLD_INCOME_ENQUEUE_READY")
        self.assertFalse(turn["fallback"]["execute_allowed"])
        held = evaluate_turn(NEEDS, household_economy=row, capture_ref=CAP, location_kind="home",
                             queue=[], player_directed=True, viewport={"state": "VIEWPORT_OK"})
        self.assertNotEqual(held["next_gate"], "HOUSEHOLD_INCOME_ENQUEUE_READY")
