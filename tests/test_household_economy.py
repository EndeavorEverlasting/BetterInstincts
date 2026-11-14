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
    def _work_household(self, count=3):
        row = snapshot(count)
        row["selected_member_key"] = row["members"][0]["member_key"]
        for index, member in enumerate(row["members"]):
            member["activity"] = "AT_WORK" if index == 0 else "AWAKE"
        row["work_shift"] = {
            "schema": "betterinstincts.work-shift.observation/v1",
            "member_key": row["selected_member_key"],
            "capture_ref": CAP,
            "shift_ref": "shift:career001",
            "state": "AT_WORK",
            "work_mode": "RABBIT_HOLE",
            "promotion_requirements": "MET",
            "daily_task": "COMPLETE",
            "performance": "BELOW_TARGET",
            "current_tone": "NORMAL",
            "tone_owner": "GAME",
            "work_hard_available": True,
        }
        return row

    def test_work_tone_precedes_handoff_with_no_chores(self):
        row = self._work_household()
        row["members"][0]["busy"] = True
        result = evaluate_household_economy(row)
        self.assertEqual(result["work_tone"]["gate"], "WORK_HARD_ADMISSION_REQUIRED")
        self.assertIsNone(result["portrait_handoff"])
        self.assertFalse(result["work_tone"]["execute_allowed"])
        plan = evaluate_turn(
            NEEDS, location_kind="home", available_objects=[], queue=[],
            capture_ref=CAP, household_economy=row, already_busy=True,
        )
        self.assertEqual(plan["next_gate"], "CAREER_WORK_HARD_ADMISSION_REQUIRED")
        self.assertFalse(plan["fallback"]["execute_allowed"])

    def test_observed_work_hard_then_immediate_next_awake_and_needs(self):
        row = self._work_household()
        # A new independent game capture must attest the changed tone.
        fresh = "capture:work-tone-confirmed002"
        row["capture_ref"] = fresh
        row["work_shift"]["capture_ref"] = fresh
        row["work_shift"]["current_tone"] = "WORK_HARD"
        for member in row["members"]:
            member["capture_ref"] = fresh
        row["members"][1]["needs"]["hunger"] = 0.08
        result = evaluate_household_economy(row)
        self.assertEqual(result["work_tone"]["gate"], "WORK_HARD_OBSERVED_HANDOFF_READY")
        handoff = result["portrait_handoff"]
        self.assertEqual(handoff["to_member_key"], row["members"][1]["member_key"])
        self.assertEqual(handoff["reason"], "SELECTED_MEMBER_AT_RABBIT_HOLE_WORK")
        self.assertTrue(handoff["new_capture_required"])
        self.assertIn("hunger", handoff["need_keys"])
        self.assertIsNone(handoff["task_ref"])
        plan = evaluate_turn(
            NEEDS, location_kind="home", available_objects=[], queue=[],
            capture_ref=fresh, household_economy=row, already_busy=True,
        )
        self.assertEqual(plan["next_gate"], "AWAKE_HOUSEHOLD_HANDOFF_READY")

    def test_unmet_promotion_releases_attention_without_overworking(self):
        row = self._work_household()
        row["work_shift"]["daily_task"] = "INCOMPLETE"
        result = evaluate_household_economy(row)
        self.assertEqual(result["work_tone"]["gate"], "PROMOTION_OPPORTUNITY_NOT_PROVEN")
        self.assertEqual(result["portrait_handoff"]["to_member_key"],
                         row["members"][1]["member_key"])
        row["members"][0]["needs"]["energy"] = 0.1
        result = evaluate_household_economy(row)
        self.assertEqual(result["work_tone"]["gate"], "WELLBEING_FIRST_SKIP_WORK_HARD")
        self.assertIsNotNone(result["portrait_handoff"])

    def test_active_career_never_auto_abandons_sim(self):
        row = self._work_household()
        row["work_shift"]["work_mode"] = "ACTIVE_CAREER"
        result = evaluate_household_economy(row)
        self.assertEqual(result["work_tone"]["gate"], "ACTIVE_OR_UNKNOWN_CAREER_HOLD")
        self.assertIsNone(result["portrait_handoff"])

    def test_working_member_is_not_an_available_home_chore_worker(self):
        row = self._work_household()
        row["work_shift"]["daily_task"] = "INCOMPLETE"
        row["members"][0]["skills"]["gardening"] = {"verified": True, "level": 10}
        row["members"][1]["activity"] = "ASLEEP"
        row["members"][2]["activity"] = "AWAY"
        row["tasks"].append(task(row, "garden-working", "gardening"))
        result = evaluate_household_economy(row)
        self.assertEqual(result["assigned_count"], 0)
        self.assertIsNone(result["portrait_handoff"])

    def test_work_shift_identity_and_player_presence_fail_closed(self):
        for broken in (
            {"member_key": "sim:somebody-else"},
            {"capture_ref": "capture:old"},
        ):
            row = self._work_household()
            row["work_shift"].update(broken)
            with self.subTest(broken=broken), self.assertRaisesRegex(
                HouseholdEconomyError, "WORK_SHIFT_EVIDENCE_INVALID"
            ):
                evaluate_household_economy(row)
        row = self._work_household()
        row["members"][0]["activity"] = "AWAKE"
        with self.assertRaisesRegex(HouseholdEconomyError, "WORK_SHIFT_SELECTED_ACTOR"):
            evaluate_household_economy(row)
        row = self._work_household()
        row["members"][0]["player_reserved"] = True
        result = evaluate_household_economy(row)
        self.assertEqual(result["work_tone"]["gate"], "PLAYER_RESERVED_WORK_SHIFT")
        self.assertIsNone(result["portrait_handoff"])
        row["player_active"] = True
        with self.assertRaisesRegex(HouseholdEconomyError, "PLAYER_PRESENCE"):
            evaluate_household_economy(row)

    def test_sleep_handoff_requires_no_chore_or_existing_task(self):
        s = snapshot(3)
        s["selected_member_key"] = s["members"][0]["member_key"]
        s["members"][0]["activity"] = "ASLEEP"
        s["members"][1]["activity"] = "AWAKE"
        s["members"][2]["activity"] = "AWAKE"
        self.assertEqual(s["tasks"], [])
        result = evaluate_household_economy(s)
        handoff = result["portrait_handoff"]
        self.assertEqual(handoff["to_member_key"], s["members"][1]["member_key"])
        self.assertIsNone(handoff["task_ref"])
        self.assertEqual(handoff["reason"], "SELECTED_MEMBER_RECOVERING_OR_AWAY")
        self.assertTrue(handoff["new_capture_required"])
        self.assertEqual(set(handoff["need_keys"]), set(NEEDS))
        self.assertFalse(handoff["execute_allowed"])
        host = evaluate_turn(NEEDS, location_kind="home", available_objects=[],
                             queue=[], capture_ref=CAP, household_economy=s,
                             already_busy=True)
        self.assertEqual(host["next_gate"], "AWAKE_HOUSEHOLD_HANDOFF_READY")

    def test_critical_needs_target_is_selected_even_when_work_ineligible(self):
        s = snapshot(3)
        s["selected_member_key"] = s["members"][0]["member_key"]
        s["members"][0]["activity"] = "ASLEEP"
        s["members"][1]["activity"] = "AWAKE"
        s["members"][1]["needs"]["hunger"] = 0.04
        s["members"][2]["activity"] = "AWAKE"
        s["tasks"].append(task(s, "garden13", "gardening"))
        result = evaluate_household_economy(s)
        self.assertEqual(result["portrait_handoff"]["to_member_key"],
                         s["members"][1]["member_key"])
        # Allocation has a distinct wellbeing floor; portrait selection does
        # not strand a hungry actor just because they cannot garden.
        self.assertNotIn(s["members"][1]["member_key"], result["workload_claims"])

    def test_portrait_order_wraps_once_and_skips_unverified_or_reserved(self):
        s = snapshot(4)
        s["selected_member_key"] = s["members"][3]["member_key"]
        s["members"][3]["activity"] = "ASLEEP"
        s["members"][0]["activity"] = "AWAY"
        s["members"][1]["activity"] = "UNKNOWN"
        s["members"][2]["activity"] = "AWAKE"
        self.assertEqual(evaluate_household_economy(s)["portrait_handoff"]["to_member_key"],
                         s["members"][2]["member_key"])
        s["members"][2]["player_reserved"] = True
        self.assertIsNone(evaluate_household_economy(s)["portrait_handoff"])
        s["members"][2]["player_reserved"] = False
        s["members"][2]["queue_verified"] = False
        self.assertIsNone(evaluate_household_economy(s)["portrait_handoff"])

    def test_one_member_all_sleeping_and_missing_identity_do_not_loop(self):
        s = snapshot(1)
        s["selected_member_key"] = s["members"][0]["member_key"]
        s["members"][0]["activity"] = "ASLEEP"
        self.assertIsNone(evaluate_household_economy(s)["portrait_handoff"])
        s = snapshot(3)
        s["selected_member_key"] = s["members"][1]["member_key"]
        for member in s["members"]:
            member["activity"] = "RECHARGING"
        self.assertIsNone(evaluate_household_economy(s)["portrait_handoff"])
        s.pop("selected_member_key")
        self.assertIsNone(evaluate_household_economy(s)["portrait_handoff"])

    def test_completed_verified_need_review_rotates_then_waits_for_fresh_capture(self):
        s = snapshot(3)
        s["selected_member_key"] = s["members"][0]["member_key"]
        for member in s["members"]:
            member["activity"] = "AWAKE"
        self.assertIsNone(evaluate_household_economy(s)["portrait_handoff"])
        s["attention_review"] = {
            "member_key": s["members"][0]["member_key"],
            "capture_ref": CAP,
            "proof_ref": "capture:current-needs-review-ok",
            "state": "VERIFIED_COMPLETE",
        }
        result = evaluate_household_economy(s)
        self.assertEqual(result["portrait_handoff"]["to_member_key"],
                         s["members"][1]["member_key"])
        self.assertEqual(result["portrait_handoff"]["reason"],
                         "SELECTED_MEMBER_NEEDS_REVIEW_VERIFIED_COMPLETE")
        # The next observed selected member must get a *new* capture; the old
        # completion does not spin over remaining portraits in one frame.
        s["selected_member_key"] = s["members"][1]["member_key"]
        s.pop("attention_review")
        self.assertIsNone(evaluate_household_economy(s)["portrait_handoff"])

    def test_replayed_stale_or_unbound_attention_review_denied(self):
        s = snapshot(2)
        s["selected_member_key"] = s["members"][0]["member_key"]
        s["members"][0]["activity"] = "AWAKE"
        s["members"][1]["activity"] = "AWAKE"
        s["attention_review"] = {
            "member_key": s["members"][0]["member_key"],
            "capture_ref": CAP,
            "proof_ref": "capture:review-1",
            "state": "VERIFIED_COMPLETE",
        }
        for field, value in (("member_key", s["members"][1]["member_key"]),
                             ("capture_ref", "capture:old"),
                             ("proof_ref", ""),
                             ("state", "CLAIMED_COMPLETE")):
            broken = copy.deepcopy(s)
            broken["attention_review"][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                    HouseholdEconomyError, "ATTENTION_REVIEW_PROOF_INVALID"):
                evaluate_household_economy(broken)
        s["player_active"] = True
        with self.assertRaisesRegex(HouseholdEconomyError, "PLAYER_PRESENCE"):
            evaluate_household_economy(s)
        s["player_active"] = False
        s["members"][0]["activity"] = "ASLEEP"
        with self.assertRaisesRegex(HouseholdEconomyError,
                                    "ATTENTION_REVIEW_ACTOR_NOT_VERIFIED_AVAILABLE"):
            evaluate_household_economy(s)
        s["members"][0]["activity"] = "AWAKE"
        s["members"][0]["player_reserved"] = True
        with self.assertRaisesRegex(HouseholdEconomyError,
                                    "ATTENTION_REVIEW_ACTOR_NOT_VERIFIED_AVAILABLE"):
            evaluate_household_economy(s)

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
