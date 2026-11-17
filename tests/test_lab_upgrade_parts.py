"""Exercise the real launch route and restock controller against a native-port fixture."""
from copy import deepcopy
from contextlib import nullcontext
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from betterinstincts.computer_upgrade_parts import menu_catalog
from betterinstincts import host_listener
from scripts import game_host, lab_upgrade_parts, launch_receipt, launch_save_route, play, smart_start
from tests.test_launch_save_route import PATCH, RUN, lab, register
from tests.test_process_bound_play import DISPATCHED, GAME

PARTS = menu_catalog()["part_ids"]
ACTORS = ("sim:work", "sim:bea", "sim:cam")
BOUND = {"household_id": "household:lab", "household_binding_confirmed": True}
ROUTE = {"state": "DEV_OLDEST_DISPOSABLE_CANDIDATE", "candidate_save_id": "slot:lab-001",
         "successor_run_id": RUN, "household_id": BOUND["household_id"]}


class FixtureBridge:
    def __init__(self):
        self.scope = {"save_id": ROUTE["candidate_save_id"], "household_id": BOUND["household_id"]}
        self.spend_cap = 2000
        self.sequence = 0
        self.effects = []
        self.bad_outcome = False
        self.frame = {
            "scene": "NEIGHBORHOOD_MAP", "save_id": self.scope["save_id"],
            "active_households": [{"household_id": BOUND["household_id"], "lot_id": "lot:one"}],
            "player_idle_verified": True, "input_generation": 2,
            "household_id": BOUND["household_id"], "lot_id": "lot:one", "paused": False,
            "selected": ACTORS[0], "computer_id": "computer:one", "computer_available_to_selected": True,
            "funds": 1_010_000, "portraits": [
                {"actor": ACTORS[0], "status": "AT_WORK"},
                {"actor": ACTORS[1], "status": "AVAILABLE", "pocket_counts": dict.fromkeys(PARTS, 0)},
                {"actor": ACTORS[2], "status": "AVAILABLE", "pocket_counts": dict.fromkeys(PARTS, 98)},
            ],
        }

    def exchange(self, operation, **data):
        if operation == "observe":
            self.sequence += 1
            frame = {**self.frame, "capture": f"capture:frame-{self.sequence}"}
            frame = deepcopy(frame)
            for row in frame["portraits"]:
                if row["status"] == "AVAILABLE":
                    row["restock_timing"] = {
                        "capture": frame["capture"], "queue_verified": True,
                        "player_directed": False, "needs_safe": True,
                        "minutes_until_work": 120, "minutes_until_need_floor": 90,
                        "reserve_minutes": 5, "switch_upper_minutes": 1,
                        "picker_upper_minutes": 3, "buy_upper_minutes": 2,
                        **row.get("timing_override", {}),
                    }
            return {"frame": frame, "observation_id": data["observation_id"]}
        self.effects.append((operation, data))
        self.frame["applied_command_id"] = data["command_id"]
        if operation == "open_active_lot":
            self.frame.update(scene="LOT_DETAILS", selected_lot_id=data["lot_id"])
        if operation == "play_active_lot":
            self.frame["scene"] = "LIVE"
        if operation == "pause_live":
            self.frame["paused"] = True
        if operation == "select_portrait":
            self.frame["selected"] = data["actor"]
        if operation == "open_upgrade_parts":
            self.frame["picker"] = {
                "actor": data["actor"], "computer_id": data["computer_id"],
                "revision": "picker:one", "cart_empty": True, "unit_prices": dict.fromkeys(PARTS, 2),
            }
        if operation == "buy_upgrade_parts":
            selected = next(row for row in self.frame["portraits"] if row["actor"] == data["actor"])
            for part, count in data["quantities"].items():
                selected["pocket_counts"][part] += count
            self.frame["funds"] -= data["total_cost"]
            self.frame["picker"] = None
            if self.bad_outcome:
                self.frame["funds"] += 1
        return {"command_id": data["command_id"], "status": "APPLIED"}


class LabUpgradePartsTests(unittest.TestCase):
    def test_restocks_two_sims_in_sequence_and_skips_sim_at_work(self):
        bridge = FixtureBridge()
        checkpoints = []
        result = lab_upgrade_parts.run_restock(bridge, lambda report: checkpoints.append(deepcopy(report)))
        self.assertEqual(result["state"], "RESTOCK_VERIFIED")
        self.assertEqual(result["verified_available"], list(ACTORS[1:]))
        self.assertEqual(result["skipped"], {ACTORS[0]: "AT_WORK"})
        self.assertEqual(result["spent"], 1000)
        self.assertEqual([op for op, _ in bridge.effects],
                         ["open_active_lot", "play_active_lot", "pause_live"] +
                         ["select_portrait", "open_upgrade_parts", "buy_upgrade_parts"] * 2)
        buys = [row for op, row in bridge.effects if op == "buy_upgrade_parts"]
        self.assertEqual([row["actor"] for row in buys], list(ACTORS[1:]))
        self.assertEqual([row["quantities"] for row in buys],
                         [dict.fromkeys(PARTS, 99), dict.fromkeys(PARTS, 1)])
        self.assertEqual(sum(c["pending"] is not None for c in checkpoints), len(bridge.effects))
        self.assertIsNone(checkpoints[-1]["pending"])

    def test_map_other_save_and_input_hold_before_any_effect(self):
        for changes, reason in (
            ({"save_id": "slot:other"}, "FRESH_SAVE"),
            ({"active_households": [{"household_id": "household:other", "lot_id": "lot:one"}]},
             "ACTIVE_MAP_HOUSEHOLD"),
            ({"player_idle_verified": False}, "YIELD_TO_PLAYER"),
        ):
            with self.subTest(changes=changes):
                bridge = FixtureBridge()
                bridge.frame.update(changes)
                with self.assertRaisesRegex(lab_upgrade_parts.RestockBlocked, reason):
                    lab_upgrade_parts.run_restock(bridge, Mock())
                self.assertEqual(bridge.effects, [])

    def test_math_selects_a_later_portrait_with_less_safe_slack(self):
        bridge = FixtureBridge()
        bridge.frame["selected"] = ACTORS[1]
        bridge.frame["portraits"][2]["timing_override"] = {"minutes_until_work": 20}
        result = lab_upgrade_parts.run_restock(bridge, Mock())
        self.assertEqual(result["state"], "RESTOCK_VERIFIED")
        self.assertEqual([row["actor"] for op, row in bridge.effects if op == "select_portrait"],
                         [ACTORS[2], ACTORS[1]])
        first = result["planning"]["decisions"][0]
        candidates = result["planning"]["initial_candidates"]
        self.assertLess(candidates[ACTORS[2]]["slack_minutes"], candidates[ACTORS[1]]["slack_minutes"])
        self.assertEqual(first["quote"]["cost"], 10)
        self.assertEqual(result["final_inventory"], dict.fromkeys(ACTORS[1:], dict.fromkeys(PARTS, 99)))

    def test_stale_window_prevents_selection_and_short_quote_window_prevents_purchase(self):
        bridge = FixtureBridge()
        for row in bridge.frame["portraits"][1:]:
            row["timing_override"] = {"capture": "capture:old"}
        checkpoints = []
        def record(report):
            checkpoints.append(deepcopy(report))

        with self.assertRaisesRegex(lab_upgrade_parts.RestockBlocked, "NO_PORTRAIT_RESTOCK_CHAIN"):
            lab_upgrade_parts.run_restock(bridge, record)
        self.assertTrue(all(op not in {"select_portrait", "open_upgrade_parts", "buy_upgrade_parts"}
                            for op, _ in bridge.effects))
        self.assertEqual(checkpoints[-1]["planning"]["hold"][ACTORS[1]]["gate"],
                         "CURRENT_RESTOCK_TIMING_REQUIRED")

        bridge = FixtureBridge()
        exchange = bridge.exchange

        def shrink_after_open(operation, **data):
            result = exchange(operation, **data)
            if operation == "open_upgrade_parts":
                bridge.frame["portraits"][1]["timing_override"] = {"minutes_until_work": 6}
            return result

        bridge.exchange = shrink_after_open
        with self.assertRaisesRegex(lab_upgrade_parts.RestockBlocked, "REOBSERVE_QUOTED"):
            lab_upgrade_parts.run_restock(bridge, record)
        self.assertNotIn("buy_upgrade_parts", [op for op, _ in bridge.effects])
        self.assertEqual(checkpoints[-1]["planning"]["decisions"][-1]["quote"]["gate"],
                         "INSUFFICIENT_EVIDENCE_OR_BUDGET")

    def test_equal_deadline_keeps_selected_and_infeasible_sibling_holds_completion(self):
        bridge = FixtureBridge()
        bridge.frame["selected"] = ACTORS[1]
        result = lab_upgrade_parts.run_restock(bridge, Mock())
        self.assertEqual(result["planning"]["decisions"][0]["target"], ACTORS[1])
        self.assertEqual([data["actor"] for op, data in bridge.effects if op == "select_portrait"],
                         [ACTORS[2]])

        bridge = FixtureBridge()
        bridge.frame["portraits"][2]["timing_override"] = {"minutes_until_work": 6}
        with self.assertRaisesRegex(lab_upgrade_parts.RestockBlocked, "NO_PORTRAIT_RESTOCK_CHAIN"):
            lab_upgrade_parts.run_restock(bridge, Mock())
        self.assertEqual([data["actor"] for op, data in bridge.effects if op == "buy_upgrade_parts"],
                         [ACTORS[1]])

    def test_native_capture_and_household_width_remain_valid_at_planner_boundary(self):
        bridge = FixtureBridge()
        exchange = bridge.exchange
        household = "household:" + "a" * 115
        bridge.scope["household_id"] = household
        bridge.frame["household_id"] = household
        bridge.frame["active_households"][0]["household_id"] = household

        def wide_capture(operation, **data):
            response = exchange(operation, **data)
            if operation == "observe":
                frame = response["frame"]
                frame["capture"] += "-" + "x" * 83
                for row in frame["portraits"]:
                    if "restock_timing" in row:
                        row["restock_timing"]["capture"] = frame["capture"]
            return response

        bridge.exchange = wide_capture
        result = lab_upgrade_parts.run_restock(bridge, Mock())
        self.assertEqual(result["state"], "RESTOCK_VERIFIED")
        self.assertGreater(len(result["final_capture"]), 96)

    def test_maximum_roster_checkpoints_fit_the_launch_receipt(self):
        bridge = FixtureBridge()
        members = [f"sim:{i:02d}" + "a" * 62 for i in range(lab_upgrade_parts.MAX_ROSTER)]
        bridge.frame["selected"] = members[0]
        bridge.frame["portraits"] = [
            {"actor": actor, "status": "AVAILABLE", "pocket_counts": dict.fromkeys(PARTS, 0)}
            for actor in members
        ]
        bridge.spend_cap = 100_000
        bridge.frame["funds"] = 1_100_000
        exchange = bridge.exchange

        def wide_capture(operation, **data):
            response = exchange(operation, **data)
            if operation == "observe":
                frame = response["frame"]
                frame["capture"] += "-" + "x" * 83
                for row in frame["portraits"]:
                    row["restock_timing"]["capture"] = frame["capture"]
            return response

        bridge.exchange = wide_capture
        with TemporaryDirectory() as tmp:
            path, envelope = launch_receipt.begin("dev", root=Path(tmp))
            envelope.update(toolkit={"details": "x" * 2000}, game=DISPATCHED)
            result = lab_upgrade_parts.run_restock(bridge, lambda report:
                     launch_receipt.write_result(path, {**envelope, "restock": report}))
            self.assertEqual(json.loads(path.read_text())["restock"], result)
            self.assertEqual(result["verified_available"], members)

    def test_budget_guard_and_failed_purchase_readback_do_not_advance(self):
        bridge = FixtureBridge()
        bridge.frame["funds"] = 1_000_001
        with self.assertRaisesRegex(lab_upgrade_parts.RestockBlocked, "RESERVE_OR_APPROVED_CAP"):
            lab_upgrade_parts.run_restock(bridge, Mock())
        self.assertNotIn("buy_upgrade_parts", [op for op, _ in bridge.effects])
        bridge = FixtureBridge()
        bridge.bad_outcome = True
        checkpoints = []
        with self.assertRaisesRegex(lab_upgrade_parts.RestockBlocked, "INVENTORY_AND_FUNDS"):
            lab_upgrade_parts.run_restock(bridge, lambda report: checkpoints.append(deepcopy(report)))
        self.assertEqual(checkpoints[-1]["pending"]["action"], "buy_upgrade_parts")
        self.assertEqual(checkpoints[-1]["purchases"], [])
        self.assertEqual([row["actor"] for op, row in bridge.effects if op == "buy_upgrade_parts"],
                         [ACTORS[1]])

    def test_input_takeover_after_buy_keeps_pending_transaction(self):
        bridge = FixtureBridge()
        exchange = bridge.exchange

        def reclaim(operation, **data):
            result = exchange(operation, **data)
            if operation == "buy_upgrade_parts":
                bridge.frame["input_generation"] += 1
            return result

        bridge.exchange = reclaim
        checkpoints = []
        with self.assertRaisesRegex(lab_upgrade_parts.RestockBlocked, "PLAYER_RECLAIMED"):
            lab_upgrade_parts.run_restock(bridge, lambda report: checkpoints.append(deepcopy(report)))
        self.assertEqual(checkpoints[-1]["pending"]["action"], "buy_upgrade_parts")
        self.assertEqual(bridge.frame["selected"], ACTORS[1])

    def test_existing_stock_and_no_available_members_never_open_computer(self):
        for row_status in ("AVAILABLE", "AT_WORK"):
            bridge = FixtureBridge()
            for row in bridge.frame["portraits"]:
                row.update(status=row_status, pocket_counts=dict.fromkeys(PARTS, 101))
            report = lab_upgrade_parts.run_restock(bridge, Mock())
            self.assertEqual(report["state"], "RESTOCK_VERIFIED" if row_status == "AVAILABLE"
                             else "NO_AVAILABLE_PORTRAITS")
            self.assertNotIn("open_upgrade_parts", [op for op, _ in bridge.effects])

    def test_route_ranks_across_bound_households_without_profile_choice(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "startup.json"
            path.write_text(json.dumps({"schema": "betterinstincts.startup-save-context/v1",
                "startup_mode": "dev", "registry": "registry.json", "run_id": RUN, "game_version": PATCH}))
            registry = root / "registry.json"
            older_protected = {**lab(5, 1, classification="USER_PROTECTED"), **BOUND}
            other_run = {**lab(4, 2), **BOUND, "authorized_run_id": "other-run"}
            oldest = {**lab(1, 3), **BOUND}
            younger = {**lab(2, 4), **BOUND, "household_id": "household:other"}
            registry.write_text(json.dumps(register(older_protected, other_run, oldest, younger)))
            with patch.object(launch_save_route, "view", side_effect=AssertionError("No profile prompt")):
                result = launch_save_route.route_mode("dev", GAME, path,
                         active_map_household=True, launch_context=root / "cert.json")
                self.assertEqual(result["candidate_save_id"], "slot:lab-001")
                self.assertEqual(result["household_id"], BOUND["household_id"])
                registry.write_text(json.dumps(register(oldest, {**younger, "lab_created_at_utc":
                                                                  oldest["lab_created_at_utc"]})))
                result = launch_save_route.route_mode("dev", GAME, path,
                         active_map_household=True, launch_context=root / "cert.json")
                self.assertEqual(result["reason"], "ABSTAIN_AMBIGUOUS_CREATION_ORDER")

    def test_launch_uses_calibration_for_chosen_slot_and_calls_restocker(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt_path, receipt = launch_receipt.begin("dev", root=root)
            context = root / "startup.json"
            context.write_text(json.dumps({"registry": "registry.json", "game_version": PATCH,
                "navigation_profile": "obsolete.json", "navigation_profiles": {"slot:lab-001": "old.json"}}))
            (root / "old.json").touch()
            bridge = FixtureBridge()
            with (patch.object(smart_start, "observe_launched_process", return_value=GAME),
                  patch.object(smart_start, "require_same_game_process"),
                  patch.object(launch_save_route, "route_mode", return_value=ROUTE) as route,
                  patch.object(game_host, "profile", return_value=({"selected_save_id": "slot:lab-001",
                      "save_registry": "registry.json", "game_version": PATCH}, "digest")) as profile,
                  patch.object(game_host, "navigate_startup_save") as navigate,
                  patch.object(lab_upgrade_parts, "save_navigation_listener",
                               return_value=nullcontext("launch-listener")),
                  patch.object(lab_upgrade_parts, "NativeBridge", return_value=bridge) as native):
                bridge.require_capabilities = Mock()
                result = play.complete_play("dev", DISPATCHED, {}, context, receipt_path, receipt, Mock(),
                                            upgrade_parts=True)
            route.assert_called_once_with("dev", GAME, context, active_map_household=True)
            profile.assert_called_once_with(root / "old.json")
            navigate.assert_called_once()
            self.assertEqual(navigate.call_args.kwargs["session_id"], "launch-listener")
            native.assert_called_once()
            bridge.require_capabilities.assert_called_once()
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["save_state"], "DEV_SAVE_MAP_OBSERVED")
            self.assertEqual(json.loads(receipt_path.read_text())["restock"]["state"], "RESTOCK_VERIFIED")

    def test_pinned_native_binding_checks_patch_hash_and_capabilities(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            executable = root / "restock.exe"
            executable.write_bytes(b"fixture")
            bind = {"bridge": executable.name, "game_version": PATCH, "binding_ref": "local:binding",
                    "sha256": hashlib.sha256(b"fixture").hexdigest()}
            context = {"native_upgrade_parts": bind, "approved_spend_cap": 2000}
            bridge = lab_upgrade_parts.NativeBridge(root / "startup.json", context, GAME, ROUTE)
            with patch.object(bridge, "exchange", return_value={"state": "NATIVE_BINDING_READY",
                       "operations": list(lab_upgrade_parts.OPERATIONS - {"buy_upgrade_parts"})}):
                with self.assertRaisesRegex(lab_upgrade_parts.RestockBlocked, "CAPABILITIES_INCOMPLETE"):
                    bridge.require_capabilities()
            ready = {"state": "NATIVE_BINDING_READY", "operations": list(lab_upgrade_parts.OPERATIONS)}
            with patch.object(bridge, "exchange", return_value=ready):
                with self.assertRaisesRegex(lab_upgrade_parts.RestockBlocked, "PLANNING_EVIDENCE"):
                    bridge.require_capabilities()
                ready["restock_planning"] = lab_upgrade_parts.PLANNING
                bridge.require_capabilities()
            executable.write_bytes(b"modified")
            with self.assertRaisesRegex(lab_upgrade_parts.RestockBlocked, "BRIDGE_HASH_MISMATCH"):
                bridge._verify()

    def test_open_game_is_preserved_without_calling_save_or_purchase(self):
        with TemporaryDirectory() as tmp:
            receipt_path, receipt = launch_receipt.begin("dev", root=Path(tmp))
            already_open = {**DISPATCHED, "state": "GAME_ALREADY_RUNNING_NO_DUPLICATE_LAUNCH"}
            with (patch.object(smart_start, "observe_launched_process", return_value=GAME),
                  patch.object(game_host, "navigate_startup_save") as navigate):
                result = play.complete_play("dev", already_open, {}, None, receipt_path, receipt,
                                            Mock(), upgrade_parts=True)
            self.assertEqual(result["reason"], "EXISTING_SESSION_PRESERVED")
            self.assertEqual(result["automation_gaps"][0]["required_actor"], "repository")
            navigate.assert_not_called()

    def test_startup_listener_is_owned_and_released_on_failure(self):
        with (patch.object(host_listener, "activate", return_value={"state": "ACTIVATED"}) as activate,
              patch.object(host_listener, "deactivate") as deactivate):
            with self.assertRaisesRegex(RuntimeError, "navigation failed"):
                with lab_upgrade_parts.save_navigation_listener() as session:
                    raise RuntimeError("navigation failed")
            deactivate.assert_called_once_with(session)
            activate.return_value = {"state": "ALREADY_ACTIVE"}
            with self.assertRaisesRegex(lab_upgrade_parts.RestockBlocked, "ALREADY_ACTIVE"):
                with lab_upgrade_parts.save_navigation_listener():
                    self.fail("Existing control session must remain owned by its launcher")
            deactivate.assert_called_once()
