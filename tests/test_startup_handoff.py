"""Route the real Play/save policy through a synthetic Windows binding."""
from contextlib import nullcontext
from dataclasses import asdict
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import time
import unittest
from unittest.mock import Mock, patch

from scripts import game_host, lab_upgrade_parts, play, smart_start, startup_handoff
from scripts.save_catalog import SCHEMA
from tests.test_launch_save_route import PATCH, RUN, lab, register
from tests.test_process_bound_play import DISPATCHED, GAME, REUSED_PID
from tests.test_semantic_save_launch import HOUSE, OTHER, save


class StartupFixture(startup_handoff.StartupBridge):
    def __init__(self):
        self.scope = {"startup_id": "fixture-startup"}
        self.scene = "WORLD_MAP"
        self.household = HOUSE
        self.save = "slot:lab-006"
        self.slot = "Slot_00000006"
        self.generation = 5
        self.catalog_process = GAME
        self.operations = []
        self.command = None
        self.capture_count = 0
        self.frame_changes = {}
        self.lose_ack = None
        self.decision = True

    def exchange(self, operation, **request):
        self.operations.append(operation)
        if operation == "capabilities":
            return {"state": "NATIVE_BINDING_READY", "operations": list(startup_handoff.OPERATIONS)}
        if operation == "read_save_catalog":
            return {"state": "MAIN_MENU_OBSERVED", "observation_id": request["observation_id"],
                    "catalog": {"schema": SCHEMA, "process": asdict(self.catalog_process),
                                "inventory_complete": True, "source": "IN_GAME_SAVE_INVENTORY",
                                "scene": "MAIN_MENU", "capture_ref": "capture:menu",
                                "observed_at_unix": time(), "saves": [
                                    save(4, "Older incomplete", roster=("Alpha",), played="2026-11-14T13:00:00Z"),
                                    save(6, "Chosen Lab", played="2026-11-16T13:00:00Z"),
                                ]}}
        if operation == "observe":
            self.capture_count += 1
            capture = f"capture:frame-{self.capture_count}"
            frame = {"capture": capture, "save_id": self.save, "slot": self.slot, "scene": self.scene,
                     "active_households": [{"household_id": self.household, "lot_id": "lot:fixture"}],
                     "selected_lot_id": "lot:fixture", "household_id": self.household,
                     "lot_id": "lot:fixture", "player_idle_verified": True,
                     "input_generation": self.generation, "applied_command_id": self.command,
                     "roster": ["sim:alpha", "sim:beta", "sim:gamma"], "selected": "sim:alpha",
                     "behavior_owner": "NATIVE_RESPONDER", "playing": True,
                     "responder": {"registered": True, "startup_id": self.scope["startup_id"],
                                   "entry_command_id": self.command,
                                   "decision_state": "DECISION_OBSERVED" if self.decision else "WAITING",
                                   "decision_ref": "decision:fixture", "decision_capture": capture}}
            frame.update(self.frame_changes.get(self.capture_count, {}))
            return {"observation_id": request["observation_id"], "frame": frame}
        assert operation in {"open_active_lot", "play_active_lot"}
        assert request["target"]["lot_id"] == "lot:fixture"
        assert request["input_generation"] == self.generation
        self.scene = "LIVE" if operation == "play_active_lot" else "LOT_DETAILS"
        self.command = request["command_id"]
        return {"command_id": self.command, "status": "UNKNOWN" if self.lose_ack == operation else "APPLIED"}


class StartupHandoffTests(unittest.TestCase):
    def run_play(self, bridge, *, mode="dev"):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            context = root / "startup.json"
            context.write_text(json.dumps({"schema": "betterinstincts.startup-save-context/v1",
                                           "startup_mode": mode, "game_version": PATCH, "run_id": RUN,
                                           "registry": "registry.json", "native_startup": {},
                                           "navigation_profile": "profile.json",
                                           "selection": {"household_id": HOUSE, "minimum_members": 3}}))
            (root / "profile.json").touch()
            (root / "registry.json").write_text(json.dumps(register(*(
                {**lab(n, day), "household_id": HOUSE, "household_binding_confirmed": True}
                for n, day in ((4, 1), (6, 5))
            ))))
            selected = {"selected_save_id": "slot:lab-006", "selected_slot": "Slot_00000006",
                        "save_registry": "registry.json", "game_version": PATCH}
            receipt = root / "launch.json"
            with (patch.object(smart_start, "observe_launched_process", return_value=GAME),
                  patch.object(smart_start, "require_same_game_process"),
                  patch.object(game_host, "profile", return_value=(selected, "digest")),
                  patch.object(game_host, "navigate_startup_save") as navigate,
                  patch.object(lab_upgrade_parts, "save_navigation_listener", return_value=nullcontext("lease")),
                  patch.object(startup_handoff, "StartupBridge", return_value=bridge)):
                result = play.complete_play(mode, DISPATCHED, {}, context, receipt, {}, Mock())
            return result, navigate.call_count, json.loads(receipt.read_text())

    def test_both_modes_connect_current_catalog_to_native_decision(self):
        for mode in ("dev", "production"):
            with self.subTest(mode=mode):
                bridge = StartupFixture()
                result, dispatches, receipt = self.run_play(bridge, mode=mode)
                self.assertEqual(result["status"], "ok")
                self.assertEqual(dispatches, 1)
                self.assertEqual(result["save_route"]["candidate_save_name"], "Chosen Lab")
                self.assertEqual(bridge.operations, ["capabilities", "read_save_catalog", "observe",
                                 "open_active_lot", "observe", "play_active_lot", "observe", "observe", "observe"])
                handoff = receipt["startup_handoff"]
                self.assertEqual(handoff["state"], "NATIVE_RESPONDER_DECISION_OBSERVED")
                self.assertEqual(len({handoff[key] for key in ("save_readback", "household_readback",
                                 "responder_control_capture", "decision_capture")}), 4)

    def test_reused_process_catalog_never_dispatches(self):
        bridge = StartupFixture()
        bridge.catalog_process = REUSED_PID
        result, dispatches, _ = self.run_play(bridge)
        self.assertEqual(result["reason"], "CURRENT_GAME_SAVE_CATALOG_REQUIRED")
        self.assertEqual(dispatches, 0)

    def test_wrong_save_or_household_never_enters_lot(self):
        for mode, field, value in (("dev", "save", "slot:wrong"), ("dev", "household", OTHER),
                                   ("production", "household", OTHER)):
            with self.subTest(mode=mode, field=field):
                bridge = StartupFixture()
                setattr(bridge, field, value)
                result, dispatches, _ = self.run_play(bridge, mode=mode)
                self.assertEqual(dispatches, 1)
                self.assertEqual(result["status"], "blocked")
                self.assertNotIn("open_active_lot", bridge.operations)

    def test_direct_live_requires_no_map_action(self):
        bridge = StartupFixture()
        bridge.scene = "LIVE"
        result, _, receipt = self.run_play(bridge)
        self.assertEqual(result["status"], "ok")
        self.assertNotIn("open_active_lot", bridge.operations)
        self.assertNotIn("play_active_lot", bridge.operations)
        self.assertIsNone(receipt["startup_handoff"]["entry_command_id"])

    def test_ambiguous_map_and_incomplete_live_roster_hold(self):
        bridge = StartupFixture()
        bridge.frame_changes[1] = {"active_households": []}
        result, _, _ = self.run_play(bridge)
        self.assertEqual(result["reason"], "STARTUP_ACTIVE_MAP_HOUSEHOLD_AMBIGUOUS")
        self.assertNotIn("open_active_lot", bridge.operations)
        bridge = StartupFixture()
        bridge.frame_changes[3] = {"roster": ["sim:alpha", "sim:beta"]}
        result, _, receipt = self.run_play(bridge)
        self.assertEqual(result["reason"], "STARTUP_LIVE_ROSTER_UNVERIFIED")
        self.assertEqual(receipt["startup_handoff"]["pending"]["operation"], "play_active_lot")

    def test_uncertain_effect_and_player_takeover_hold_with_pending_command(self):
        for failure in ("ack", "takeover", "replay"):
            with self.subTest(failure=failure):
                bridge = StartupFixture()
                if failure == "ack":
                    bridge.lose_ack = "open_active_lot"
                elif failure == "takeover":
                    bridge.frame_changes[2] = {"input_generation": 6}
                else:
                    bridge.frame_changes[2] = {"capture": "capture:frame-1"}
                result, _, receipt = self.run_play(bridge)
                self.assertEqual(result["status"], "blocked")
                self.assertEqual(bridge.operations.count("open_active_lot"), 1)
                self.assertNotIn("play_active_lot", bridge.operations)
                self.assertEqual(receipt["startup_handoff"]["pending"]["operation"], "open_active_lot")

    def test_registered_responder_with_no_decision_leaves_startup_incomplete(self):
        bridge = StartupFixture()
        bridge.decision = False
        result, _, receipt = self.run_play(bridge)
        self.assertEqual(result["reason"], "NATIVE_STARTUP_RESPONDER_DECISION_NOT_OBSERVED")
        self.assertEqual(receipt["startup_handoff"]["state"], "RESPONDER_CONTROL_OBSERVED")
        self.assertEqual(bridge.operations.count("play_active_lot"), 1)
