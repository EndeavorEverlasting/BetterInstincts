import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from scripts import game_host as host


class FakeGui:
    FAILSAFE = False
    PAUSE = 0

    def __init__(self, count=1):
        self.count = count
        self.clicked = []

    def locateAllOnScreen(self, template, grayscale=False):
        return [object() for _ in range(self.count)]

    def center(self, box):
        return (15, 25)

    def click(self, point):
        self.clicked.append(point)


class GameHostTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.original_output = host.OUTPUT
        host.OUTPUT = self.root / "dist" / "game-host"
        self.addCleanup(setattr, host, "OUTPUT", self.original_output)
        exe = self.root / "TS4_x64.exe"
        exe.write_bytes(b"synthetic fixture; never executed")
        self.exe = exe

    def make_profile(self, mode="chosen", alias="BI_TEST_01"):
        templates = (["new_game"] if mode == "new"
                     else ["load_game", "save_tile", "play"])
        for name in templates:
            (self.root / (name + ".png")).write_bytes(b"test fixture")
        cfg = {"schema": host.SCHEMA, "platform": "windows",
               "game_executable": str(self.exe), "game_version": None if mode == "new" else "1.121.1.1030",
               "save_mode": mode, "save_alias": alias,
               "templates": {n: n + ".png" for n in templates}}
        if mode == "chosen":
            # Synthetic operator approval only: no actual Sims save is opened.
            from betterinstincts.save_policy import MANIFEST_SCHEMA
            cfg.update({"save_alias": "BI_TMP_HOST_TEST_01" if alias == "BI_TEST_01" else alias,
                        "save_registry": "synthetic-save-registry.json",
                        "selected_save_id": "slot:synthetic-lab-01",
                        "selected_save_capture_ref": "capture:synthetic-tile-01"})
            register = {"schema": MANIFEST_SCHEMA, "entries": [{
                "save_id": "slot:synthetic-lab-01", "alias": cfg["save_alias"],
                "classification": "LAB_DISPOSABLE", "origin": "LAB_CREATED",
                "lab_origin_confirmed": True, "creation_run_id": "original-lab-run",
                "authorized_run_id": "bi002-game-host",
                "capture_ref": "capture:synthetic-tile-01",
                "game_version": "1.121.1.1030", "operator_confirmed": True
            }]}
            (self.root / "synthetic-save-registry.json").write_text(json.dumps(register), encoding="utf-8")
        path = self.root / "host-profile.json"
        path.write_text(json.dumps(cfg), encoding="utf-8")
        obj, digest = host.profile(path)
        obj["_profile_path"] = str(path)
        return obj, digest

    def launch_fake(self, mode="chosen", run_id="bi002-game-host"):
        cfg, digest = self.make_profile(mode)
        with patch.object(host.sys, "platform", "win32"), patch.object(
            host.subprocess, "Popen", return_value=SimpleNamespace(pid=987)
        ) as spawn:
            receipt = host.launch(run_id, cfg, digest, True)
        self.assertEqual(receipt["state"], "LAUNCH_DISPATCHED")
        spawn.assert_called_once()
        return cfg, digest

    def test_plan_read_only_and_no_game_claim(self):
        cfg, digest = self.make_profile()
        result = host.plan(cfg, digest)
        self.assertEqual(result["ui_steps"], ["load_game", "save_tile", "play"])
        self.assertIn("NO_GAME_LAUNCHED", result["proof_ceiling"])
        self.assertFalse(host.OUTPUT.exists())

    def test_run_id_and_save_intent_restrictions(self):
        for value in ("../saves", "a", "C:foo", "go/away"):
            with self.assertRaises(host.GateError):
                host.run_root(value)
        with self.assertRaisesRegex(host.GateError, "DISPOSABLE_SAVE_ALIAS_REQUIRED"):
            self.make_profile(alias="../real-personal-save")
        self.assertEqual(self.make_profile("new")[0]["save_mode"], "new")

    def test_launch_fails_closed_without_windows_or_explicit_execute(self):
        cfg, digest = self.make_profile()
        with self.assertRaisesRegex(host.GateError, "EXPLICIT_EXECUTE"):
            host.launch("bi002-no", cfg, digest, False)
        with patch.object(host.sys, "platform", "linux"):
            with self.assertRaisesRegex(host.GateError, "WINDOWS"):
                host.launch("bi002-no", cfg, digest, True)
        self.assertFalse(host.OUTPUT.exists())

    def test_chosen_save_click_path_and_evidence_ceiling(self):
        cfg, digest = self.launch_fake()
        with self.assertRaisesRegex(host.GateError, "DISPOSABLE"):
            host.navigate("bi002-game-host", cfg, digest, True, False, gui=FakeGui())
        gui = FakeGui()
        receipt = host.navigate("bi002-game-host", cfg, digest, True, True, gui=gui)
        self.assertEqual(receipt["state"], "CHOSEN_SAVE_PLAY_REQUESTED")
        self.assertEqual(len(gui.clicked), 3)
        self.assertEqual(host.status("bi002-game-host")["game_certification"],
                         "NOT_GRANTED_BY_HOST_ADAPTER")
        with self.assertRaisesRegex(host.GateError, "EXACT_GAME_VERSION_REQUIRED"):
            host.confirm("bi002-game-host", "capture:chosen-test", "", True)
        host.confirm("bi002-game-host", "capture:chosen-test", "1.121.1.1030", True)
        self.assertEqual(host.status("bi002-game-host")["state"],
                         "LIVE_REPORTED_UNREVIEWED")
        self.assertEqual(host.status("bi002-game-host")["game_version"],
                         "1.121.1.1030")

    def test_new_game_only_requests_cas_not_live_game(self):
        cfg, digest = self.launch_fake("new")
        receipt = host.navigate("bi002-game-host", cfg, digest, True, True, gui=FakeGui())
        self.assertEqual(receipt["state"], "NEW_GAME_CAS_REQUESTED")

    def test_ambiguous_gui_never_clicks(self):
        cfg, digest = self.launch_fake()
        gui = FakeGui(2)
        with self.assertRaisesRegex(host.GateError, "AMBIGUOUS_UI_TARGET"):
            host.navigate("bi002-game-host", cfg, digest, True, True, gui=gui)
        self.assertFalse(gui.clicked)

    def test_partial_ui_click_is_checkpointed_and_never_replayed(self):
        cfg, digest = self.launch_fake()

        class PartialGui(FakeGui):
            def locateAllOnScreen(self, template, grayscale=False):
                self.count += 1
                return [object()] if self.count == 1 else [object(), object()]

        gui = PartialGui(0)
        with self.assertRaisesRegex(host.GateError, "AMBIGUOUS_UI_TARGET"):
            host.navigate("bi002-game-host", cfg, digest, True, True, gui=gui)
        self.assertEqual(len(gui.clicked), 1)
        self.assertEqual(host.status("bi002-game-host")["state"], "UI_CLICK_DISPATCHED")
        with self.assertRaisesRegex(host.GateError, "LAUNCH_DISPATCH_REQUIRED"):
            host.navigate("bi002-game-host", cfg, digest, True, True, gui=FakeGui())

    def test_profile_mutation_blocked_after_launch(self):
        cfg, digest = self.launch_fake()
        with self.assertRaisesRegex(host.GateError, "PROFILE_CHANGED"):
            host.navigate("bi002-game-host", cfg, "f"*64, True, True, gui=FakeGui())

    def test_sample_ingest_is_bounded_and_unverified(self):
        cfg, digest = self.launch_fake()
        host.navigate("bi002-game-host", cfg, digest, True, True, gui=FakeGui())
        host.confirm("bi002-game-host", "capture:chosen-test", "1.121.1.1030", True)
        sample = self.root / "snapshot.jsonl"
        good = {"schema": "betterinstincts.object-sample/v1",
                "object_key": "sim-test-01", "metric": "hunger", "value": 0.52,
                "captured_at": "2026-11-06T23:00:00Z"}
        sample.write_text(json.dumps(good) + "\n", encoding="utf-8")
        receipt = host.poll("bi002-game-host", sample)
        self.assertEqual(receipt["samples"], 1)
        self.assertEqual(receipt["state"], "SAMPLE_INGESTED_UNVERIFIED")
        good["sim_name"] = "forbidden"
        sample.write_text(json.dumps(good) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(host.GateError, "SAMPLE_FIELDS_NOT_ALLOWLISTED"):
            host.poll("bi002-game-host", sample)

    def test_duplicate_session_rejected(self):
        cfg, digest = self.launch_fake()
        with patch.object(host.sys, "platform", "win32"):
            with self.assertRaises(FileExistsError):
                host.launch("bi002-game-host", cfg, digest, True)


if __name__ == "__main__":
    unittest.main()
