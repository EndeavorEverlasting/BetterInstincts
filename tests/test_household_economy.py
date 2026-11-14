"""Solo happiness and cooperative household economics: adversarial source-only tests."""
from __future__ import annotations

import copy
import unittest

from betterinstincts.household_judgment import bind_household_scope
from betterinstincts.household_economy import (
    HouseholdEconomyError, evaluate_household_economy,
)
from betterinstincts.host_stack import HostStackError, evaluate_turn
from betterinstincts.host_listener import _load_observation, HostListenerError

CAP = "capture:household-economy-test001"
NEEDS = {k: 0.91 for k in ("hunger", "bladder", "energy", "hygiene", "fun", "social")}


def snapshot(n=1):
    scope = bind_household_scope(
        profile_id="default", save_key="local_test_save", household_key="test-household",
        roster_keys=["sim_"+str(i) for i in range(n)],
    )
    members = []
    for i, member_key in enumerate(scope["member_keys"]):
        members.append({
            "member_key": member_key, "capture_ref": CAP,
            "mood": "HAPPY", "temperament": "BALANCED", "needs": dict(NEEDS),
            "player_reserved": False, "busy": False, "available": True,
            "queue_verified": True, "queue": [], "multitasking": False,
            "recent_workload": i,
            "skills": {"gardening":{"level":2+i,"verified":True}},
            "likes": ["gardening"] if i == n - 1 else [],
            "dislikes": [],
        })
    return {
        "schema": "betterinstincts.household-economy.observation/v1",
        "capture_ref": CAP,
        "scope": scope,
        "observed_roster_fingerprint": scope["roster_fingerprint"],
        "roster_verified": True, "player_active": False, "members": members,
        "tasks": [], "reserved_resources": [], "failed_tasks": [],
    }


def task(s, ident, mech, kind="YIELD", priority=3, resource=None,
         skill=None, level=0):
    return {
        "task_ref": ident, "mechanic_id": mech, "kind": kind,
        "priority": priority, "resource_ref": resource,
        "required_skill": skill, "min_skill_level": level,
        "eligible_member_keys": list(s["scope"]["member_keys"]),
        "observed_available": True, "player_owned": False,
        "capture_ref": CAP,
    }


class HouseholdEconomyTests(unittest.TestCase):
    def test_handoff_uses_awake_servo_and_preserves_recovery(self):
        s = snapshot(3)
        selected, unavailable, servo = s["members"]
        s["selected_member_key"] = selected["member_key"]
        unavailable["activity"] = "RECHARGING"
        servo.update(activity="AWAKE", sim_kind="SERVO",
                     needs=dict.fromkeys(("charge", "durability", "fun", "social"), 0.9))
        s["tasks"].append(task(s, "garden01", "gardening"))
        for state in ("ASLEEP", "RECHARGING", "AWAY"):
            with self.subTest(state=state):
                selected["activity"] = state
                plan = evaluate_household_economy(s)
                self.assertEqual(plan["workload_claims"], [servo["member_key"]])
                self.assertEqual(plan["portrait_handoff"]["to_member_key"], servo["member_key"])
                self.assertFalse(plan["portrait_handoff"]["execute_allowed"])

        servo["activity"] = "UNKNOWN"
        plan = evaluate_household_economy(s)
        self.assertEqual(plan["assigned_count"], 0)
        self.assertIsNone(plan["portrait_handoff"])

    def test_host_exposes_one_handoff_for_current_capture(self):
        s = snapshot(2)
        selected, next_member = s["members"]
        selected["activity"] = "ASLEEP"
        next_member["activity"] = "AWAKE"
        s["selected_member_key"] = selected["member_key"]
        s["tasks"].append(task(s, "garden01", "gardening"))
        args = dict(needs=NEEDS, location_kind="home", available_objects=[], queue=[], household_economy=s)
        plan = evaluate_turn(capture_ref=CAP, already_busy=True, **args)
        self.assertEqual(plan["next_gate"], "AWAKE_HOUSEHOLD_HANDOFF_READY")
        self.assertEqual(plan["fallback"]["portrait_handoff"]["to_member_key"],
                         next_member["member_key"])
        player = evaluate_turn(capture_ref=CAP, player_directed=True, **args)
        self.assertNotEqual(player["next_gate"], "AWAKE_HOUSEHOLD_HANDOFF_READY")
        build = evaluate_turn(capture_ref=CAP, build_or_buy_mode=True, **args)
        self.assertNotEqual(build["next_gate"], "AWAKE_HOUSEHOLD_HANDOFF_READY")
        with self.assertRaisesRegex(HostStackError, "HOUSEHOLD_HANDOFF_CAPTURE_MISMATCH"):
            evaluate_turn(capture_ref="capture:other", **args)

    def test_single_person_fun_and_temperament_outrank_discretionary_income(self):
        s = snapshot()
        s["tasks"].append(task(s, "earn001", "income-earning"))
        s["members"][0]["needs"]["fun"] = 0.6
        report = evaluate_household_economy(s)
        self.assertEqual(report["mode"], "SOLO_WELLBEING_FIRST")
        self.assertEqual(report["assigned_count"], 0)
        self.assertEqual(report["deferred"][0]["reason"],
                         "NO_VERIFIED_WELL_MEMBER_WITH_CAPACITY")
        self.assertEqual(report["personal_wellbeing"][0]["discretionary_yield_gate"],
                         "PERSONAL_NEEDS_OR_LEISURE_FIRST")
        for mood, temperament in (("STRAINED", "BALANCED"), ("HAPPY", "IRRITABLE"),
                                  ("UNKNOWN", "UNKNOWN")):
            s["members"][0]["needs"]["fun"] = 0.91
            s["members"][0]["mood"] = mood
            s["members"][0]["temperament"] = temperament
            with self.subTest(mood=mood, temperament=temperament):
                self.assertEqual(evaluate_household_economy(s)["assigned_count"], 0)

    def test_single_well_person_can_take_one_proven_responsibility(self):
        s = snapshot()
        s["tasks"].extend([task(s,"income01","income-earning"),
                           task(s,"repair01","household-repairs",kind="UPKEEP",priority=1)])
        result = evaluate_household_economy(s)
        self.assertEqual(result["mode"], "SOLO_WELLBEING_FIRST")
        self.assertEqual([a["task_ref"] for a in result["allocations"]], ["repair01"])
        self.assertEqual(len(result["deferred"]), 1)
        self.assertIsNone(result["estimated_income"])
        self.assertFalse(result["execute_allowed"])

    def test_multi_member_work_splits_among_verified_capable_members(self):
        s = snapshot(3)
        s["tasks"].extend([
            task(s, "repairs01", "household-repairs", kind="OBLIGATION", priority=1),
            task(s, "gardening01", "gardening", kind="UPKEEP", priority=2,
                 resource="garden:main", skill="gardening", level=3),
            task(s, "earn01", "income-earning", kind="YIELD", priority=3),
        ])
        r = evaluate_household_economy(s)
        self.assertEqual(r["mode"], "COOPERATIVE_HOUSEHOLD")
        self.assertEqual(r["assigned_count"], 3)
        self.assertEqual(len({a["member_key"] for a in r["allocations"]}), 3)
        self.assertEqual(r["gate"], "COOPERATIVE_ALLOCATION_READY")
        # Gardening only went to a qualified, verified skill holder.
        assignment = next(a for a in r["allocations"] if a["task_ref"] == "gardening01")
        gardener = next(m for m in s["members"] if m["member_key"] == assignment["member_key"])
        self.assertGreaterEqual(gardener["skills"]["gardening"]["level"], 3)
        self.assertTrue(all(a["execute_allowed"] is False for a in r["allocations"]))

    def test_player_reserved_distraught_critical_and_queue_full_never_work(self):
        for condition in ("player", "busy", "hunger", "temperament", "queue"):
            s = snapshot(2)
            s["tasks"].append(task(s,"earn01","income-earning"))
            for member in s["members"]:
                if condition == "player": member["player_reserved"] = True
                if condition == "busy": member["busy"] = True
                if condition == "hunger": member["needs"]["hunger"] = 0.18
                if condition == "temperament": member["temperament"] = "IRRITABLE"
                if condition == "queue": member["queue"] = ["Existing work"] * 6
            with self.subTest(condition=condition):
                r = evaluate_household_economy(s)
                self.assertEqual(r["assigned_count"], 0)

    def test_fair_workloads_and_preferences_are_not_invented_as_income(self):
        s = snapshot(3)
        s["tasks"].append(task(s, "garden01", "gardening", kind="UPKEEP", priority=2))
        r = evaluate_household_economy(s)
        self.assertEqual(r["allocations"][0]["member_key"], s["members"][2]["member_key"])
        self.assertIsNone(r["expected_game_yield"])
        self.assertNotIn("dollars", str(r))

    def test_replay_failure_resource_collision_and_player_task_hold(self):
        s = snapshot(3)
        s["tasks"].extend([
            task(s, "clean1", "household-repairs", kind="UPKEEP", resource="sink:one"),
            task(s, "clean2", "household-repairs", kind="UPKEEP", resource="sink:one"),
            task(s, "clean3", "household-repairs", kind="UPKEEP", resource="sink:two"),
        ])
        s["tasks"][2]["player_owned"] = True
        s["failed_tasks"] = [{
            "task_ref":"clean1", "proof_ref":"capture:clean1failed",
            "capture_ref": CAP, "outcome":"FAILED",
        }]
        r = evaluate_household_economy(s)
        self.assertEqual(r["assigned_count"], 1)
        self.assertIn("FAILED_ACTION_HOLD_REPLAN_WITH_NEW_EVIDENCE",
                      {x["reason"] for x in r["deferred"]})
        self.assertIn("PLAYER_OWNED_TASK_PROTECTED",
                      {x["reason"] for x in r["deferred"]})

    def test_missing_mechanics_always_surface_as_unowned_gap(self):
        s = snapshot(2)
        s["tasks"].append(task(s,"pet001","pet-care",kind="OBLIGATION",priority=1))
        r = evaluate_household_economy(s)
        self.assertEqual(r["assigned_count"], 0)
        self.assertEqual(r["deferred"][0]["reason"], "UNCOVERED_MECHANIC_DISCOVERY_REQUIRED")
        self.assertTrue(r["deferred"][0]["retain_goal"])

    def test_wrong_roster_capture_and_unknown_sim_identity_block(self):
        s = snapshot(2)
        s["tasks"].append(task(s,"household01","household-repairs",kind="UPKEEP"))
        cases = ("fingerprint", "roster", "member-capture", "task-capture", "fake-skill",
                 "player-presence", "duplicate-task")
        for case in cases:
            broken = copy.deepcopy(s)
            if case == "fingerprint": broken["observed_roster_fingerprint"] = "fake"
            if case == "roster": broken["members"].reverse()
            if case == "member-capture": broken["members"][0]["capture_ref"] = "capture:old"
            if case == "task-capture": broken["tasks"][0]["capture_ref"] = "capture:old"
            if case == "fake-skill":
                broken["members"][0]["skills"]["gardening"] = {"level":9,"verified":False}
            if case == "player-presence": broken["player_active"] = True
            if case == "duplicate-task": broken["tasks"].append(copy.deepcopy(broken["tasks"][0]))
            with self.subTest(case=case), self.assertRaises(HouseholdEconomyError):
                evaluate_household_economy(broken)

    def test_host_stack_port_respects_default_and_reports_opt_in_plan(self):
        base = evaluate_turn(NEEDS, location_kind="home", available_objects=[],
                             queue=[], capture_ref=CAP)
        self.assertIsNone(base["household_economy"])
        s = snapshot(2)
        s["tasks"].append(task(s,"garden01","gardening",kind="UPKEEP"))
        result = evaluate_turn(NEEDS, location_kind="home", available_objects=[],
                               queue=[], capture_ref=CAP, household_economy=s)
        self.assertEqual(result["household_economy"]["assigned_count"], 1)
        self.assertFalse(result["household_economy"]["execute_allowed"])

    def test_listener_passes_optional_household_observation_without_telemetry(self):
        s = snapshot(2)
        raw = {"schema":"betterinstincts.host-listener.observation/v1",
               "capture_ref": CAP, "needs": NEEDS, "queue":[],
               "location_kind":"home", "household_economy":s}
        parsed = _load_observation(raw)
        self.assertEqual(parsed["household_economy"], s)
        raw["household_economy"] = "bad"
        with self.assertRaisesRegex(HostListenerError, "HOUSEHOLD_ECONOMY"):
            _load_observation(raw)


if __name__ == "__main__":
    unittest.main()
