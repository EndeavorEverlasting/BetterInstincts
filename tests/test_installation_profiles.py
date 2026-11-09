"""Configuration persistence and profile toggles, isolated from Sims saves/host."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from betterinstincts.installation_profiles import (
    DEFAULTS, InstallationProfileError, choose_profile, create_profile,
    read_document, reset_toggle, set_toggle, settings_path, view,
)
from scripts import instance_settings


class InstallationProfilesTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.path = self.root / "betterinstincts" / "settings.v1.json"

    def test_read_only_defaults_do_not_write_anything(self):
        initial = view(self.path)
        self.assertEqual(initial["profile_id"], "default")
        self.assertEqual(initial["settings"], DEFAULTS)
        self.assertIsNone(initial["game_control_permit"])
        self.assertFalse(self.path.parent.exists())

    def test_named_profiles_isolate_and_persist_toggles(self):
        create_profile("gamer", self.path)
        choose_profile("gamer", self.path)
        out = set_toggle("learning.hover_observations", True, self.path)
        self.assertTrue(out["settings"]["learning.hover_observations"])
        self.assertEqual(out["overrides"], {"learning.hover_observations": True})
        self.assertFalse(view(self.path, profile_id="default")["settings"]["learning.hover_observations"])
        self.assertTrue(view(self.path)["settings"]["learning.hover_observations"])
        reset_toggle("learning.hover_observations", self.path)
        self.assertFalse(view(self.path)["settings"]["learning.hover_observations"])
        self.assertEqual(view(self.path)["overrides"], {})
        self.assertGreater(read_document(self.path)["revision"], 0)

    def test_idempotent_default_does_not_create_file(self):
        set_toggle("learning.hotkey_observations", False, self.path)
        self.assertFalse(self.path.exists())

    def test_unknown_ids_keys_and_bool_coercion_refused(self):
        for item in ("../other", "", "UPPER", "a" * 33):
            with self.assertRaises(InstallationProfileError):
                create_profile(item, self.path)
        with self.assertRaisesRegex(InstallationProfileError, "SETTING_UNKNOWN_OR_TYPE_INVALID"):
            set_toggle("learning.unknown", True, self.path)
        with self.assertRaisesRegex(InstallationProfileError, "SETTING_UNKNOWN_OR_TYPE_INVALID"):
            set_toggle("learning.hover_observations", 1, self.path)
        with self.assertRaisesRegex(InstallationProfileError, "PROFILE_NOT_FOUND"):
            choose_profile("missing", self.path)

    def test_invalid_schema_is_not_overwritten(self):
        self.path.parent.mkdir(parents=True)
        raw = '{"schema":"unexpected","revision":3}'
        self.path.write_text(raw)
        with self.assertRaisesRegex(InstallationProfileError, "SETTINGS_SCHEMA_INVALID"):
            set_toggle("ui.show_evidence_details", False, self.path)
        self.assertEqual(self.path.read_text(), raw)

    def test_unknown_future_key_and_wrong_type_fail_closed(self):
        self.path.parent.mkdir(parents=True)
        data = {"schema": "betterinstincts.installation-profiles/v1",
                "revision": 0, "active_profile": "default",
                "profiles": {"default": {"automations.nonexistent": True}}}
        self.path.write_text(json.dumps(data))
        with self.assertRaisesRegex(InstallationProfileError, "SETTING_UNKNOWN_OR_TYPE_INVALID"):
            read_document(self.path)
        data["profiles"]["default"] = {"ui.show_evidence_details": "false"}
        self.path.write_text(json.dumps(data))
        with self.assertRaisesRegex(InstallationProfileError, "SETTING_UNKNOWN_OR_TYPE_INVALID"):
            read_document(self.path)

    def test_bounded_malformed_and_symlink_data_rejected(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("!" * 33000)
        with self.assertRaisesRegex(InstallationProfileError, "SETTINGS_FILE_UNSAFE"):
            read_document(self.path)
        self.path.write_text("not json")
        with self.assertRaisesRegex(InstallationProfileError, "SETTINGS_CONTENT_INVALID"):
            read_document(self.path)
        self.path.unlink()
        target = self.root / "original.json"
        target.write_text("{}")
        self.path.symlink_to(target)
        with self.assertRaisesRegex(InstallationProfileError, "SYMLINK_SETTINGS_PATH_FORBIDDEN"):
            read_document(self.path)
        self.assertEqual(target.read_text(), "{}")

    def test_atomic_replace_failure_preserves_original(self):
        set_toggle("ui.show_advanced_settings", True, self.path)
        old = self.path.read_bytes()
        with patch("betterinstincts.installation_profiles.os.replace", side_effect=OSError("disk-full")):
            with self.assertRaisesRegex(OSError, "disk-full"):
                set_toggle("ui.show_advanced_settings", False, self.path)
        self.assertEqual(self.path.read_bytes(), old)
        self.assertEqual(list(self.path.parent.glob(".settings-*.tmp")), [])

    def test_busy_writer_refuses_without_modification(self):
        set_toggle("ui.show_advanced_settings", True, self.path)
        locked = self.path.with_suffix(".lock")
        locked.write_text("other writer")
        with self.assertRaisesRegex(InstallationProfileError, "SETTINGS_WRITER_BUSY"):
            choose_profile("default", self.path)
        self.assertTrue(locked.exists())

    def test_paths_distinct_from_install_manifests(self):
        win = settings_path(home=self.root, platform="win32",
                            environment={"LOCALAPPDATA": str(self.root / "Local")})
        lin = settings_path(home=self.root, platform="linux", environment={})
        self.assertEqual(win, self.root / "Local" / "BetterInstincts" / "settings.v1.json")
        self.assertEqual(lin, self.root / ".config" / "betterinstincts" / "settings.v1.json")
        self.assertNotIn("/app/", win.as_posix())
        self.assertNotIn("/dev/", lin.as_posix())

    def test_cli_set_and_show_readback(self):
        from io import StringIO
        from contextlib import redirect_stdout
        with patch.object(instance_settings, "view", side_effect=lambda **kw: view(self.path, **kw)), \
             patch.object(instance_settings, "set_toggle",
                          side_effect=lambda key, enabled, **kw: set_toggle(key, enabled, self.path, **kw)):
            with redirect_stdout(StringIO()) as output:
                self.assertEqual(instance_settings.main(["set", "ui.show_advanced_settings", "true"]), 0)
            self.assertTrue(json.loads(output.getvalue())["settings"]["ui.show_advanced_settings"])
            with redirect_stdout(StringIO()) as output:
                self.assertEqual(instance_settings.main(["show"]), 0)
            self.assertTrue(json.loads(output.getvalue())["settings"]["ui.show_advanced_settings"])



    def test_catalog_is_the_single_default_owner(self):
        catalog = json.loads((Path(__file__).resolve().parents[1] /
                              "contracts" / "installation-profiles.v1.json").read_text())
        self.assertEqual(catalog["defaults"], DEFAULTS)
        self.assertTrue(all(type(value) is bool for value in DEFAULTS.values()))

    def test_hover_cli_profile_opt_in_does_not_bypass_explicit_session_gate(self):
        from io import StringIO
        from contextlib import redirect_stdout
        from scripts import host_listener
        event_path = self.root / "event.json"
        event_path.write_text('{"kind":"hover"}')
        captured = []
        def fake_observe(_sid, _event, *, explicit_opt_in=False):
            captured.append(explicit_opt_in)
            return {"state": "ADVISORY_ONLY", "opt_in": explicit_opt_in}
        with patch.object(host_listener, "observe_hover", side_effect=fake_observe), \
             patch("betterinstincts.installation_profiles.view",
                   return_value={"settings": {"learning.hover_observations": False}}):
            with redirect_stdout(StringIO()):
                self.assertEqual(host_listener.main([
                    "hover", "--session-id", "manual", "--event", str(event_path),
                    "--use-active-profile"]), 0)
        self.assertEqual(captured, [False])
        with patch.object(host_listener, "observe_hover", side_effect=fake_observe), \
             patch("betterinstincts.installation_profiles.view",
                   return_value={"settings": {"learning.hover_observations": True}}):
            with redirect_stdout(StringIO()):
                self.assertEqual(host_listener.main([
                    "hover", "--session-id", "manual", "--event", str(event_path),
                    "--use-active-profile"]), 0)
        self.assertEqual(captured, [False, True])
        # Existing explicitly consenting one-off command is retained unchanged.
        with patch.object(host_listener, "observe_hover", side_effect=fake_observe):
            with redirect_stdout(StringIO()):
                self.assertEqual(host_listener.main([
                    "hover", "--session-id", "manual", "--event", str(event_path),
                    "--explicit-opt-in"]), 0)
        self.assertEqual(captured[-1], True)


    def test_behavior_channel_preferences_separate_and_event_qualified(self):
        from io import StringIO
        from contextlib import redirect_stdout
        from scripts import host_listener
        event_path = self.root / "event.json"
        received = []
        def fake_observe(_sid, _event, *, explicit_opt_in=False):
            received.append(explicit_opt_in)
            return {"state": "ADVISORY_ONLY"}
        for kind, profile, expected in [
            ("hotkey_action", {"learning.hover_observations": True,
                               "learning.hotkey_observations": False,
                               "learning.cheat_observations": True}, False),
            ("hotkey_action", {"learning.hotkey_observations": True}, True),
            ("cheat_action", {"learning.cheat_observations": False,
                              "learning.hotkey_observations": True}, False),
            ("cheat_action", {"learning.cheat_observations": True}, True),
        ]:
            event_path.write_text(json.dumps({"kind": kind}))
            with patch.object(host_listener, "observe_hover", side_effect=fake_observe), \
                 patch("betterinstincts.installation_profiles.view",
                       return_value={"settings": profile}), \
                 redirect_stdout(StringIO()):
                self.assertEqual(host_listener.main([
                    "behavior", "--session-id", "manual", "--event", str(event_path),
                    "--use-active-profile"]), 0)
            self.assertIs(received[-1], expected)

if __name__ == "__main__":
    unittest.main()
