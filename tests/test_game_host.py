import json
from contextlib import contextmanager
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

    def test_focus_restore_is_not_live_mode_proof(self):
        def fake_restore(process_id):
            self.assertEqual(process_id, 15152)
            return {"hwnd": 99, "process_id": 15152, "iconic_before": True,
                    "iconic_after": False, "rect_after": [0, 0, 1920, 1080]}

        with patch.object(host.sys, "platform", "win32"):
            receipt = host.focus(process_id=15152, restore=fake_restore)
        self.assertEqual(receipt["state"], "FOCUS_RESTORE_ATTEMPTED")
        self.assertEqual(receipt["proof_ceiling"],
                         "WINDOW_FOCUS_ONLY_NOT_LIVE_MODE_OR_SCENE_PROOF")
        self.assertIn("READY_LIVE", receipt["next"])
        with patch.object(host.sys, "platform", "linux"):
            with self.assertRaisesRegex(host.GateError, "LOCAL_WINDOWS"):
                host.focus(restore=fake_restore)
        with patch.object(host.sys, "platform", "win32"):
            with self.assertRaisesRegex(host.GateError, "INVALID_PROCESS_ID"):
                host.focus(process_id=0, restore=fake_restore)

    def test_manual_cas_complete_unlocks_confirm_without_template_clicks(self):
        self.launch_fake("new")
        with self.assertRaisesRegex(host.GateError, "DISPOSABLE"):
            host.manual_cas_complete("bi002-game-host", False)
        receipt = host.manual_cas_complete("bi002-game-host", True)
        self.assertEqual(receipt["state"], "NEW_GAME_CAS_REQUESTED")
        self.assertEqual(receipt["drive_method"], "printwindow_sendinput")
        self.assertIn("MANUAL_CAS_DRIVE", receipt["proof_ceiling"])
        host.confirm("bi002-game-host", "capture:live-manual-001", "1.121.361.1020", True)
        self.assertEqual(host.status("bi002-game-host")["state"],
                         "LIVE_REPORTED_UNREVIEWED")
        with self.assertRaisesRegex(host.GateError, "LAUNCH_DISPATCH_REQUIRED"):
            host.manual_cas_complete("bi002-game-host", True)


    def test_windows_navigation_requires_real_handoff_before_screenshot(self):
        cfg, digest = self.launch_fake()
        gui = FakeGui()
        with patch.object(host.sys, "platform", "win32"):
            with self.assertRaisesRegex(host.GateError, "HANDOFF_SESSION_REQUIRED"):
                host.navigate("bi002-game-host", cfg, digest, True, True, gui=gui)
        self.assertEqual(gui.clicked, [])

    def test_windows_navigation_refuses_foreign_foreground_before_screenshot(self):
        cfg, digest = self.launch_fake()
        class TrackedGui(FakeGui):
            scans = 0
            def locateAllOnScreen(self, template, grayscale=False):
                self.scans += 1
                return super().locateAllOnScreen(template, grayscale=grayscale)
        gui = TrackedGui()
        from betterinstincts.player_presence import PresenceProbe

        @contextmanager
        def leased(*args, **kwargs):
            self.assertEqual(args[0], 987)
            yield lambda: None

        unrelated = PresenceProbe(False, False, last_input_age_ms=20000,
                                  foreground_process_id=999, probe_ok=True)
        with (patch.object(host.sys, "platform", "win32"),
              patch("betterinstincts.screen_admit.admitted_screen_lease", leased),
              patch("betterinstincts.player_presence.probe_windows", return_value=unrelated)):
            with self.assertRaisesRegex(host.GateError, "GAME_FOREGROUND_NOT_OWNED"):
                host.navigate("bi002-game-host", cfg, digest, True, True,
                              gui=gui, session_id="host-test-active")
        self.assertEqual(gui.scans, 0)
        self.assertEqual(gui.clicked, [])

    def test_windows_navigation_revalidates_focus_after_template_match(self):
        cfg, digest = self.launch_fake()
        gui = FakeGui()
        from betterinstincts.player_presence import PresenceProbe

        @contextmanager
        def leased(*args, **kwargs):
            yield lambda: None

        owned = PresenceProbe(True, True, last_input_age_ms=20000,
                              foreground_process_id=987, probe_ok=True)
        stolen = PresenceProbe(False, False, last_input_age_ms=20000,
                               foreground_process_id=999, probe_ok=True)
        with (patch.object(host.sys, "platform", "win32"),
              patch("betterinstincts.screen_admit.admitted_screen_lease", leased),
              patch("betterinstincts.player_presence.probe_windows",
                    side_effect=[owned, stolen])):
            with self.assertRaisesRegex(host.GateError, "GAME_FOREGROUND_NOT_OWNED"):
                host.navigate("bi002-game-host", cfg, digest, True, True,
                              gui=gui, session_id="host-test-active")
        self.assertEqual(gui.clicked, [])
        self.assertEqual(host.status("bi002-game-host")["state"], "LAUNCH_DISPATCHED")

    def test_windows_navigation_human_interrupt_aborts_before_observation(self):
        cfg, digest = self.launch_fake()
        gui = FakeGui()
        from betterinstincts.control_handoff import HandoffError

        @contextmanager
        def denied_lease(*args, **kwargs):
            def not_ready():
                raise HandoffError("HOST_PAUSED:RECENT_HUMAN_INPUT")
            yield not_ready

        with (patch.object(host.sys, "platform", "win32"),
              patch("betterinstincts.screen_admit.admitted_screen_lease", denied_lease)):
            with self.assertRaisesRegex(host.GateError, "RECENT_HUMAN_INPUT"):
                host.navigate("bi002-game-host", cfg, digest, True, True,
                              gui=gui, session_id="host-test-active")
        self.assertEqual(gui.clicked, [])


if __name__ == "__main__":
    unittest.main()
