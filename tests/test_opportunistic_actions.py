"""Sixth Gear regression proof: verified school-window seam and chat whim targets."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from betterinstincts.host_stack import evaluate_turn
from betterinstincts.host_listener import _load_observation, HostListenerError
from betterinstincts.opportunistic_actions import (
    OpportunisticActionError, plan_school_homework_window, plan_targeted_chat_whim,
)
from scripts.opportunistic_actions import inspect

CAPTURE = "capture:class-chat-lab-001"
NEEDS = {"hunger": .8, "bladder": .8, "energy": .8, "hygiene": .8,
         "fun": .7, "social": .7}
SURVIVAL = []

def window(**changes):
    o = {"capture_ref": CAPTURE, "game_version": "1.121.361.1020",
         "school_phase": "class_time", "homework_available": True,
         "homework_running": False, "class_attendance_preserved": True,
         "observed_actions": ["DO_HOMEWORK"], "source_kind": "GAME_UI_VERIFIED"}
    o.update(changes)
    return o

def homework(**options):
    args = {"capture_ref": CAPTURE, "school_phase": "class_time",
            "school_day_active": True, "location_kind": "school",
            "homework_pending": True, "inventory_has_homework": True,
            "queue": [], "player_directed": False, "already_busy": False,
            "survival_critical": SURVIVAL, "multitasking": False}
    args.update(options)
    return plan_school_homework_window(window(), **args)

def person(**changes):
    o = {"name": "Morgan", "sim_id": "sim:morgan", "on_lot": False,
         "observed_actions": ["RELATIONSHIP_CHAT"], "capture_ref": CAPTURE,
         "occult_status": "HUMAN"}
    o.update(changes)
    return o

def chat(whims=("Chat with Morgan",), sim_library=None, **options):
    args = {"capture_ref": CAPTURE, "queue": [], "queued_social_targets": [],
            "player_directed": False, "already_busy": False,
            "survival_critical": [], "multitasking": False}
    args.update(options)
    return plan_targeted_chat_whim(whims, [person()] if sim_library is None else sim_library, **args)

class OpportunisticActionTests(unittest.TestCase):
    def test_late_homework_underway_window_is_a_real_advisory(self):
        report = homework()
        self.assertEqual(report["gate"], "HOMEWORK_WINDOW_READY")
        self.assertEqual(report["primary_route"], "DO_HOMEWORK_OBSERVED_SCHOOL_WINDOW")
        self.assertFalse(report["execute_allowed"])
        self.assertIn("REOBSERVE_HOMEWORK_AND_CLASS_ATTENDANCE",
                      report["next_actions"][0]["steps"])

    def test_continuing_homework_during_class_does_not_cancel_attendance(self):
        report = plan_school_homework_window(
            window(homework_available=False, homework_running=True,
                   observed_actions=["CONTINUE_HOMEWORK"]),
            capture_ref=CAPTURE, school_phase="class_time",
            school_day_active=True, location_kind="school",
            homework_pending=True, inventory_has_homework=True,
            queue=["Go To Class", "Do Homework"], player_directed=False,
            already_busy=False, survival_critical=[], multitasking=False)
        self.assertEqual(report["gate"], "HOMEWORK_WINDOW_CONTINUE")
        self.assertIn("KEEP_CLASS_ATTENDANCE_QUEUED",
                      report["next_actions"][0]["steps"])

    def test_old_school_block_persists_without_true_affordance(self):
        self.assertIsNone(plan_school_homework_window(
            None, capture_ref=CAPTURE, school_phase="class_time",
            school_day_active=True, location_kind="school",
            homework_pending=True, inventory_has_homework=True,
            queue=[], player_directed=False, already_busy=False,
            survival_critical=[], multitasking=False))
        for patch, expected in [
            ({"class_attendance_preserved": False}, "HOMEWORK_WINDOW_ATTEND_CLASS_FIRST"),
            ({"homework_available": False}, "HOMEWORK_WINDOW_AFFORDANCE_MISSING"),
            ({"capture_ref": "capture:stale"}, "HOMEWORK_WINDOW_REOBSERVE"),
            ({"school_phase": "before_class"}, "HOMEWORK_WINDOW_REOBSERVE"),
            ({"source_kind": "GUESS"}, "HOMEWORK_WINDOW_REOBSERVE"),
        ]:
            with self.subTest(patch=patch):
                report = plan_school_homework_window(
                    window(**patch), capture_ref=CAPTURE, school_phase="class_time",
                    school_day_active=True, location_kind="school",
                    homework_pending=True, inventory_has_homework=True,
                    queue=[], player_directed=False, already_busy=False,
                    survival_critical=[], multitasking=False)
                self.assertEqual(report["gate"], expected)

    def test_school_window_yields_to_survival_player_and_queue(self):
        self.assertEqual(homework(player_directed=True)["gate"], "HOMEWORK_WINDOW_PLAYER_FIRST")
        self.assertEqual(homework(already_busy=True)["gate"], "HOMEWORK_WINDOW_PLAYER_FIRST")
        self.assertEqual(homework(survival_critical=["energy"])["gate"],
                         "HOMEWORK_WINDOW_SURVIVAL_FIRST")
        self.assertEqual(homework(inventory_has_homework=False)["gate"],
                         "HOMEWORK_WINDOW_CONTEXT_NOT_ADMITTED")
        self.assertEqual(homework(queue=["Do Homework"])["gate"],
                         "HOMEWORK_WINDOW_ALREADY_QUEUED")
        self.assertEqual(homework(multitasking=None)["gate"],
                         "HOMEWORK_WINDOW_QUEUE_CAPACITY_HOLD")
        with self.assertRaisesRegex(OpportunisticActionError, "HOMEWORK_AFFORDANCE_INVALID"):
            plan_school_homework_window(
                window(homework_available="yes"), capture_ref=CAPTURE,
                school_phase="class_time", school_day_active=True,
                location_kind="school", homework_pending=True,
                inventory_has_homework=True, queue=[], player_directed=False,
                already_busy=False, survival_critical=[], multitasking=False)

    def test_relationship_hotkey_route_and_on_lot_route(self):
        remote = chat()
        self.assertEqual(remote["gate"], "CHAT_WHIM_RELATIONSHIP_READY")
        self.assertEqual(remote["target_sim_id"], "sim:morgan")
        self.assertEqual(remote["primary_route"], "R_RELATIONSHIPS_EXACT_SIM_CHAT")
        self.assertIn("PRESS_R_AFTER_INDEPENDENT_HOST_ADMISSION",
                      remote["next_actions"][0]["steps"])
        on_lot = chat(sim_library=[person(on_lot=True,
                                         observed_actions=["CHAT_ON_LOT"])])
        self.assertEqual(on_lot["gate"], "CHAT_WHIM_ON_LOT_READY")
        self.assertEqual(on_lot["primary_route"], "CHAT_WITH_OBSERVED_ON_LOT_SIM")
        self.assertFalse(on_lot["execute_allowed"])

    def test_social_target_validation_and_missing_lookups(self):
        self.assertEqual(chat(sim_library=[])["gate"],
                         "CHAT_WHIM_TARGET_LOOKUP_REQUIRED")
        self.assertEqual(chat(sim_library=[person(), person(sim_id="sim:m2")])["gate"],
                         "CHAT_WHIM_TARGET_LOOKUP_REQUIRED")
        self.assertEqual(chat(sim_library=[person(capture_ref="capture:old")])["gate"],
                         "CHAT_WHIM_TARGET_REOBSERVE")
        self.assertEqual(chat(sim_library=[person(sim_id=None)])["gate"],
                         "CHAT_WHIM_TARGET_REOBSERVE")
        self.assertIsNone(chat(whims=["Chat with somebody"]))
        self.assertEqual(chat(whims=["Chat with Morgan","Chat with Taylor"])["gate"],
                         "CHAT_WHIM_MULTIPLE_TARGETS_REVIEW")
        self.assertEqual(chat(queue=["Chat with Morgan"])["gate"],
                         "CHAT_WHIM_QUEUE_REOBSERVE")
        self.assertEqual(chat(queued_social_targets=[
            {"sim_id":"sim:morgan","action_kind":"CHAT","capture_ref":CAPTURE}
        ])["gate"], "CHAT_WHIM_ALREADY_QUEUED")

    def test_off_lot_invitation_requires_known_safe_status(self):
        safe = chat(sim_library=[person(observed_actions=["INVITE_OVER"])])
        self.assertEqual(safe["gate"], "CHAT_WHIM_INVITE_REVIEW")
        self.assertIn("RECHECK_OCCULT_AND_INVITE_PERMISSION",
                      safe["next_actions"][0]["steps"])
        for occult in ("UNKNOWN", "VAMPIRE", "OTHER_OCCULT"):
            with self.subTest(occult=occult):
                blocked = chat(sim_library=[
                    person(observed_actions=["INVITE_OVER"], occult_status=occult)])
                self.assertEqual(blocked["gate"], "CHAT_WHIM_AFFORDANCE_UNKNOWN")

    def test_no_extra_queue_when_player_busy_or_survival_critical(self):
        self.assertEqual(chat(player_directed=True)["gate"], "CHAT_WHIM_PLAYER_FIRST")
        self.assertEqual(chat(already_busy=True)["gate"], "CHAT_WHIM_PLAYER_FIRST")
        self.assertEqual(chat(survival_critical=["hunger"])["gate"],
                         "CHAT_WHIM_SURVIVAL_FIRST")
        self.assertEqual(chat(multitasking=None)["gate"],
                         "CHAT_WHIM_QUEUE_CAPACITY_HOLD")
        with self.assertRaisesRegex(OpportunisticActionError, "CHAT_QUEUE_ENTRY_UNVERIFIED"):
            chat(queued_social_targets=[{"sim_id":"sim:morgan"}])

    def test_host_stack_accepts_school_window_and_keeps_advisory_boundary(self):
        report = evaluate_turn(
            NEEDS, available_objects=[], location_kind="school",
            school_day_active=True, school_phase="class_time",
            homework_pending=True, inventory_has_homework=True,
            school_homework_window=window(), queue=[],
            life_stage="teen", multitasking=False, capture_ref=CAPTURE)
        self.assertIsNotNone(report["school_homework_window"])
        self.assertEqual(report["school_homework_window"]["gate"],
                         "HOMEWORK_WINDOW_READY")
        self.assertEqual(report["next_gate"], "HOMEWORK_WINDOW_READY")
        self.assertFalse(report["fallback"]["execute_allowed"])

    def test_host_stack_routes_targeted_chat_without_new_clicker(self):
        report = evaluate_turn(
            NEEDS, location_kind="home", queue=[],
            whims=["Chat with Morgan"], sim_library=[person()],
            multitasking=False, capture_ref=CAPTURE)
        self.assertEqual(report["targeted_chat_whim"]["gate"],
                         "CHAT_WHIM_RELATIONSHIP_READY")
        self.assertEqual(report["next_gate"], "CHAT_WHIM_RELATIONSHIP_READY")
        self.assertFalse(report["fallback"]["execute_allowed"])

    def test_listener_accepts_bounded_evidence_and_rejects_bad_types(self):
        raw = {"schema":"betterinstincts.host-listener.observation/v1",
               "needs":NEEDS, "queue":[], "location_kind":"school",
               "capture_ref":CAPTURE, "school_day_active":True,
               "school_phase":"class_time", "homework_pending":True,
               "inventory_has_homework":True, "school_homework_window":window(),
               "queued_social_targets":[],"sim_library":[person()]}
        parsed = _load_observation(raw)
        self.assertEqual(parsed["school_homework_window"], window())
        self.assertEqual(parsed["queued_social_targets"], ())
        for key,value in (("school_homework_window","invented"),
                          ("queued_social_targets","untrusted")):
            changed = dict(raw)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(HostListenerError):
                _load_observation(changed)

    def test_bounded_cli_input_is_read_only(self):
        raw = {"needs":NEEDS, "queue":[], "location_kind":"school",
               "capture_ref":CAPTURE, "school_day_active":True,
               "school_phase":"class_time", "homework_pending":True,
               "inventory_has_homework":True, "multitasking":False,
               "school_homework_window":window(), "whims":["Chat with Morgan"],
               "sim_library":[person()]}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "observation.json"
            p.write_text(json.dumps(raw), encoding="utf-8")
            data = inspect(p)
            self.assertEqual(data["school_homework_window"]["gate"],
                             "HOMEWORK_WINDOW_READY")
            self.assertEqual(data["targeted_chat_whim"]["gate"],
                             "CHAT_WHIM_RELATIONSHIP_READY")
            self.assertFalse(data["execute_allowed"])
            self.assertEqual(len(list(Path(tmp).iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
