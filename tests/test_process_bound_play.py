from dataclasses import asdict
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from betterinstincts.first_run import FirstRunError
from scripts import game_host, launch_receipt, launch_save_route, play, smart_start
from scripts.smart_start import GameProcess
from tests.test_launch_save_route import PATCH, RUN, lab, register

EXE = r"c:\games\the sims 4\game\bin\ts4_x64.exe"
GAME = GameProcess(52, "638987600000000000", EXE, PATCH)
REUSED_PID = GameProcess(52, "638987900000000000", EXE, PATCH)
SUCCESSOR = GameProcess(62, "638987900000000000", EXE, PATCH)
DISPATCHED = {
    "state": "GAME_LAUNCH_DISPATCHED_SAVE_HANDOFF",
    "dispatch_process_id": 17, "game_executable": EXE,
    "observed_game_process": asdict(GAME),
}


class ProcessBoundPlayTests(unittest.TestCase):
    def test_windows_inventory_requires_creation_time_and_full_image(self):
        with patch.object(smart_start.sys, "platform", "win32"):
            runner = Mock(return_value=SimpleNamespace(stdout=json.dumps([asdict(GAME)])))
            self.assertEqual(smart_start.read_game_processes(runner), (GAME,))
            runner.return_value.stdout = json.dumps([{"pid": 52, "executable": EXE}])
            with self.assertRaisesRegex(FirstRunError, "IDENTITY_UNAVAILABLE"):
                smart_start.read_game_processes(runner)
            runner.return_value.stdout = "[]"
            self.assertEqual(smart_start.read_game_processes(runner), ())

    def test_distinct_dispatch_pid_never_controls_observed_game(self):
        with patch.object(smart_start, "read_game_processes", return_value=(GAME,)):
            self.assertEqual(play.observe_launched_process(DISPATCHED), GAME)
        for different in (REUSED_PID, SUCCESSOR):
            with patch.object(smart_start, "read_game_processes", return_value=(different,)):
                with self.assertRaisesRegex(ValueError, "GAME_PROCESS_CHANGED"):
                    play.observe_launched_process(DISPATCHED)
                with self.assertRaisesRegex(FirstRunError, "GAME_PROCESS_CHANGED"):
                    smart_start.require_same_game_process(GAME)

    def test_prod_uses_game_recency_and_rejects_foreign_or_tied_observations(self):
        ctx = {"process": asdict(GAME), "source": "IN_GAME_LAST_PLAYED",
               "inventory_complete": True, "capture_ref": "capture:in-game-inventory",
               "candidates": [
                   {"save_id": "slot:late", "last_played_utc": "2026-11-13T18:00:00Z"},
                   {"save_id": "slot:early", "last_played_utc": "2026-11-11T18:00:00Z"},
               ]}
        self.assertEqual(launch_save_route.production_candidate(GAME, ctx)["candidate_save_id"], "slot:late")
        self.assertIsNone(launch_save_route.production_candidate(REUSED_PID, ctx)["selected_save_id"])
        ctx["candidates"][1]["last_played_utc"] = ctx["candidates"][0]["last_played_utc"]
        self.assertEqual(launch_save_route.production_candidate(GAME, ctx)["reason"],
                         "LATEST_PLAYED_SAVE_AMBIGUOUS")

    def test_dev_excludes_protected_oldest_and_requires_current_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            context = root / "context.json"
            household = {"household_id": "household:a", "household_binding_confirmed": True}
            context.write_text(json.dumps({
                "schema": "betterinstincts.startup-save-context/v1", "startup_mode": "dev",
                "available_households": ["household:a"], "game_version": PATCH, "run_id": RUN,
                "registry": "registry.json",
            }))
            (root / "registry.json").write_text(json.dumps(register(
                {**lab(2, 4), **household},
                {**lab(1, 1, classification="USER_PROTECTED"), **household},
                {**lab(3, 3), **household},
            )))
            cert = root / "no-active-certification.json"
            with patch.object(launch_save_route, "view", return_value={"preferred_household_id": None}):
                self.assertEqual(launch_save_route.route_mode("dev", GAME, context, launch_context=cert)
                                 ["candidate_save_id"], "slot:lab-003")
                self.assertEqual(launch_save_route.route_mode(
                    "dev", GameProcess(52, GAME.creation_ticks, EXE), context, launch_context=cert,
                )["state"], "HOLD_DEV_GAME_BUILD")
                cert.write_text(json.dumps({"status": "PENDING"}))
                self.assertEqual(launch_save_route.route_mode("dev", GAME, context, launch_context=cert)
                                 ["state"], "HOLD_ACTIVE_CERTIFICATION")

    def test_dev_partial_dispatch_keeps_checkpoint_and_records_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt_path, receipt = launch_receipt.begin("dev", root=root)
            context = root / "context.json"
            context.write_text(json.dumps({"navigation_profile": "profile.json", "registry": "registry.json",
                                           "game_version": PATCH, "session_id": "listener"}))
            (root / "profile.json").touch()

            def dispatch(*args, **kwargs):
                kwargs["checkpoint"]("load_game:pending")
                kwargs["checkpoint"]("load_game")
                raise FirstRunError("GAME_PROCESS_CHANGED_REOBSERVE_SCENE_AND_SAVE")

            with (patch.object(play, "observe_launched_process", return_value=GAME),
                  patch.object(launch_save_route, "route_mode", return_value={
                      "state": "DEV_OLDEST_DISPOSABLE_CANDIDATE", "candidate_save_id": "slot:old",
                      "successor_run_id": RUN,
                  }),
                  patch.object(game_host, "profile", return_value=({
                      "selected_save_id": "slot:old", "save_registry": "registry.json",
                      "game_version": PATCH,
                  }, "digest")),
                  patch.object(smart_start, "require_same_game_process"),
                  patch.object(game_host, "navigate_startup_save", side_effect=dispatch) as nav):
                result = play.complete_play("dev", DISPATCHED, {}, context, receipt_path, receipt, Mock())
            nav.assert_called_once()
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["save_state"], "NOT_OBSERVED")
            self.assertEqual(result["automation_gaps"][0]["kind"], "MISSING_REPOSITORY_LOGIC")
            self.assertEqual(json.loads(receipt_path.read_text())["automatic_steps"],
                             ["load_game:pending", "load_game"])

    def test_production_and_assistance_record_missing_logic_with_distinct_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt_path, receipt = launch_receipt.begin("production", root=Path(tmp))
            with patch.object(play, "observe_launched_process", return_value=GAME):
                result = play.complete_play("production", DISPATCHED, {}, None, receipt_path, receipt, Mock())
            self.assertEqual(result["save_state"], "NOT_OBSERVED")
            self.assertEqual(result["automation_gaps"][0]["reason"], "LATEST_SAVE_OBSERVER_AND_LOADER_REQUIRED")
            fields = {"actor": "agent", "stage": "production_save", "step": "Select the latest save",
                      "owner": "scripts/launch_save_route.py", "before": "capture:before",
                      "during": "capture:during", "after": "capture:after"}
            assisted = launch_receipt.record_assistance(receipt_path, **fields)
            self.assertEqual(json.loads(assisted.read_text())["required_actor"], "agent")
            self.assertEqual(json.loads(assisted.read_text())["after_ref"], "capture:after")
            with self.assertRaisesRegex(ValueError, "DISTINCT_BEFORE_DURING_AFTER"):
                launch_receipt.record_assistance(receipt_path, **{**fields, "after": "capture:before"})

    def test_receipts_stop_at_capacity_without_deleting_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fields = {"actor": "human", "stage": "production_save", "step": "Opened the save",
                      "owner": "scripts/launch_save_route.py", "before": "capture:before",
                      "during": "capture:during", "after": "capture:after"}
            with (patch.object(launch_receipt, "MAX_LAUNCHES", 1),
                  patch.object(launch_receipt, "MAX_ASSISTS_PER_LAUNCH", 1)):
                path, _ = launch_receipt.begin("production", root=root)
                row = launch_receipt.record_assistance(path, **fields)
                with self.assertRaisesRegex(ValueError, "PLAY_RECEIPT_STORE_FULL"):
                    launch_receipt.begin("production", root=root)
                with self.assertRaisesRegex(ValueError, "PLAY_ASSISTANCE_STORE_FULL"):
                    launch_receipt.record_assistance(path, **fields)
                self.assertTrue(path.is_file())
                self.assertTrue(row.is_file())
