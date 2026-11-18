"""Route the real Play/save policy through a synthetic Windows binding."""
from contextlib import nullcontext
from dataclasses import asdict
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import time
import unittest
from unittest.mock import Mock, patch

from scripts import game_host, lab_upgrade_parts, launch_receipt, play, save_catalog, smart_start, startup_handoff
from scripts.save_catalog import SCHEMA
from tests.test_lab_upgrade_parts import FixtureBridge, PARTS
from tests.test_launch_save_route import PATCH, RUN, lab, register
from tests.test_process_bound_play import DISPATCHED, GAME, REUSED_PID
from tests.test_semantic_save_launch import HOUSE, OTHER, save


class StartupFixture(startup_handoff.StartupBridge):
    def __init__(self):
        self.scope = {"process": asdict(GAME), "run_id": RUN, "startup_id": "fixture-startup"}
        self.digest = "a" * 64
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
        self.catalog_only = False
        self.session_in_progress = False
        self.catalog_timestamp = None

    def exchange(self, operation, **request):
        self.operations.append(operation)
        if operation == "capabilities":
            return {"state": "NATIVE_BINDING_READY", "operations": (
                ["read_save_catalog"] if self.catalog_only else list(startup_handoff.OPERATIONS))}
        if operation == "read_save_catalog":
            if self.session_in_progress:
                return {"state": "EXISTING_SESSION_IN_PROGRESS", "observation_id": request["observation_id"]}
            return {"state": "MAIN_MENU_OBSERVED", "observation_id": request["observation_id"],
                    "catalog": {"schema": SCHEMA, "process": asdict(self.catalog_process),
                                "inventory_complete": True, "source": "IN_GAME_SAVE_INVENTORY",
                                "scene": "MAIN_MENU", "capture_ref": "capture:menu",
                                "observed_at_unix": self.catalog_timestamp or time(), "saves": [
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
    def run_play(self, bridge, *, mode="dev", fail_receipt_at=None, restock=None, game=DISPATCHED):
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
            write_result = launch_receipt.write_result

            def write_or_fail(path, result):
                if result["stage"] == fail_receipt_at:
                    raise OSError("FIXTURE_RECEIPT_UNAVAILABLE")
                write_result(path, result)

            def record_dispatch(*args, **kwargs):
                bridge.receipt_at_dispatch = json.loads(receipt.read_text())

            with (patch.object(smart_start, "observe_launched_process", return_value=GAME),
                  patch.object(smart_start, "require_same_game_process"),
                  patch.object(game_host, "profile", return_value=(selected, "digest")),
                  patch.object(game_host, "navigate_startup_save", side_effect=record_dispatch) as navigate,
                  patch.object(launch_receipt, "write_result", side_effect=write_or_fail),
                  patch.object(lab_upgrade_parts, "save_navigation_listener", return_value=nullcontext("lease")),
                  patch.object(lab_upgrade_parts, "NativeBridge", return_value=restock),
                  patch.object(startup_handoff, "StartupBridge", return_value=bridge)):
                selection = {"expected_save_name": "Chosen Lab", "required_members": ["Alpha", "Beta", "Gamma"]}
                result = play.complete_play(mode, game, {}, context, receipt, {}, Mock(),
                                            upgrade_parts=restock is not None,
                                            selection=selection if restock is not None else None)
            return result, navigate.call_count, json.loads(receipt.read_text())

    def semantic_restock_fixture(self):
        catalog = StartupFixture()
        catalog.catalog_only = True
        restock = FixtureBridge()
        restock.require_capabilities = Mock()
        restock.digest = "b" * 64
        restock.scope.update(process=asdict(GAME), run_id=RUN, save_id=catalog.save)
        restock.frame.update(save_id=catalog.save, slot=catalog.slot, selected="sim:alpha")
        for row, sim in zip(restock.frame["portraits"], ("sim:alpha", "sim:beta", "sim:gamma"), strict=True):
            row["actor"] = sim
        return catalog, restock

    def test_named_restock_runs_from_catalog_through_one_responder_handoff(self):
        catalog, restock = self.semantic_restock_fixture()
        result, dispatches, receipt = self.run_play(catalog, restock=restock)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(dispatches, 1)
        self.assertEqual(catalog.operations, ["capabilities", "read_save_catalog"])
        self.assertEqual(catalog.receipt_at_dispatch["startup_binding"]["catalog_capture"], "capture:menu")
        self.assertEqual(catalog.receipt_at_dispatch["save_route"]["candidate_slot"], catalog.slot)
        self.assertEqual(catalog.receipt_at_dispatch["save_route"]["candidate_save_name"], "Chosen Lab")
        self.assertEqual(catalog.receipt_at_dispatch["restock_binding"], {
            "scope": restock.scope, "sha256": restock.digest, "catalog_capture": "capture:menu"})
        report = receipt["restock"]
        self.assertEqual(report["state"], "RESTOCK_VERIFIED")
        self.assertEqual(report["skipped"], {"sim:alpha": "AT_WORK"})
        self.assertEqual(report["final_inventory"], dict.fromkeys(("sim:beta", "sim:gamma"), dict.fromkeys(PARTS, 99)))
        self.assertEqual(report["handoff"]["state"], "NATIVE_RESPONDER_DECISION_OBSERVED")
        self.assertEqual(sum(operation == "handoff_to_responder" for operation, _ in restock.effects), 1)

    def test_named_restock_holds_wrong_slot_or_roster_before_portrait_effects(self):
        for reason, changed_slot in (("RESTOCK_SLOT_DOES_NOT_MATCH_CATALOG", True),
                                     ("RESTOCK_ROSTER_DOES_NOT_MATCH_CATALOG", False)):
            with self.subTest(reason=reason):
                catalog, restock = self.semantic_restock_fixture()
                if changed_slot:
                    restock.frame["slot"] = "Slot_00000004"
                else:
                    restock.frame["portraits"][-1]["actor"] = "sim:foreign"
                result, _, _ = self.run_play(catalog, restock=restock)
                self.assertEqual(result["reason"], reason)
                self.assertEqual([op for op, _ in restock.effects], [] if changed_slot else [
                    "claim_restock_control", "open_active_lot", "play_active_lot"])

    def test_named_restock_preserves_existing_loaded_session(self):
        catalog, restock = self.semantic_restock_fixture()
        catalog.session_in_progress = True
        existing_game = {**DISPATCHED, "state": "GAME_ALREADY_RUNNING_NO_DUPLICATE_LAUNCH"}
        result, dispatches, _ = self.run_play(catalog, restock=restock, game=existing_game)
        self.assertEqual(result["reason"], "EXISTING_SESSION_PRESERVED")
        self.assertEqual(catalog.operations, ["capabilities", "read_save_catalog"])
        self.assertEqual(dispatches, 0)
        self.assertEqual(restock.effects, [])

    def test_named_restock_can_use_existing_main_menu(self):
        catalog, restock = self.semantic_restock_fixture()
        existing_game = {**DISPATCHED, "state": "GAME_ALREADY_RUNNING_NO_DUPLICATE_LAUNCH"}
        result, dispatches, _ = self.run_play(catalog, restock=restock, game=existing_game)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(dispatches, 1)

    def test_named_restock_checkpoint_and_foreign_catalog_prevent_dispatch(self):
        for foreign in (False, True):
            with self.subTest(foreign=foreign):
                catalog, restock = self.semantic_restock_fixture()
                if foreign:
                    catalog.catalog_process = REUSED_PID
                result, dispatches, _ = self.run_play(catalog, restock=restock,
                    fail_receipt_at=None if foreign else "dev_save_dispatch")
                self.assertEqual(result["status"], "blocked")
                self.assertEqual(dispatches, 0)
                self.assertEqual(restock.effects, [])

    def test_catalog_expiring_during_restock_capabilities_stops_save_dispatch(self):
        catalog, restock = self.semantic_restock_fixture()
        catalog.catalog_timestamp = time()
        with patch.object(save_catalog, "time", side_effect=[catalog.catalog_timestamp, catalog.catalog_timestamp + 121]):
            result, dispatches, _ = self.run_play(catalog, restock=restock)
        self.assertEqual(result["reason"], "CURRENT_GAME_SAVE_CATALOG_REQUIRED")
        self.assertEqual(dispatches, 0)
        self.assertEqual(restock.effects, [])

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

    def test_lost_play_ack_keeps_same_bridge_scope_before_and_after_dispatch(self):
        bridge = StartupFixture()
        bridge.lose_ack = "play_active_lot"
        result, dispatches, receipt = self.run_play(bridge)
        self.assertEqual(result["reason"], "STARTUP_EFFECT_RECONCILIATION_REQUIRED")
        self.assertEqual(dispatches, 1)
        binding = {"scope": bridge.scope, "sha256": bridge.digest, "catalog_capture": "capture:menu"}
        self.assertEqual(bridge.receipt_at_dispatch["startup_binding"], binding)
        self.assertEqual(receipt["startup_binding"], binding)
        self.assertEqual(receipt["startup_handoff"]["pending"]["command_id"], bridge.command)
        self.assertEqual(bridge.operations.count("play_active_lot"), 1)

    def test_failed_scope_checkpoint_prevents_save_dispatch(self):
        bridge = StartupFixture()
        result, dispatches, receipt = self.run_play(bridge, fail_receipt_at="dev_save_dispatch")
        self.assertEqual(result["reason"], "FIXTURE_RECEIPT_UNAVAILABLE")
        self.assertEqual(dispatches, 0)
        self.assertEqual(receipt["startup_binding"]["scope"], bridge.scope)
        self.assertEqual(bridge.operations, ["capabilities", "read_save_catalog"])

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
