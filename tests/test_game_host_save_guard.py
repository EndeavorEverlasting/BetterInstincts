"""Chosen-save policy must reject unsafe slots before ANY GUI click."""
import json
import unittest

from test_game_host import FakeGui, GameHostTests
from scripts import game_host as host


class ProtectedChosenSaveTests(unittest.TestCase):
    def setUp(self):
        self.fixture = GameHostTests("test_plan_read_only_and_no_game_claim")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root

    def test_missing_registry_never_clicks_chosen_save(self):
        cfg, digest = self.fixture.launch_fake()
        cfg.pop("save_registry")
        gui = FakeGui()
        with self.assertRaisesRegex(host.GateError, "SAVE_SELECTION_PROTECTED"):
            host.navigate("bi002-game-host", cfg, digest, True, True, gui=gui)
        self.assertEqual(gui.clicked, [])

    def test_user_origin_cannot_be_auto_selected(self):
        cfg, digest = self.fixture.launch_fake()
        registry = self.root / "synthetic-save-registry.json"
        doc = json.loads(registry.read_text())
        doc["entries"][0]["origin"] = "USER_CREATED"
        registry.write_text(json.dumps(doc))
        gui = FakeGui()
        with self.assertRaisesRegex(host.GateError, "LAB_ORIGIN_UNPROVEN"):
            host.navigate("bi002-game-host", cfg, digest, True, True, gui=gui)
        self.assertEqual(gui.clicked, [])

    def test_stale_capture_never_clicks(self):
        cfg, digest = self.fixture.launch_fake()
        cfg["selected_save_capture_ref"] = "capture:another-slot"
        gui = FakeGui()
        with self.assertRaisesRegex(host.GateError, "SAVE_BINDING"):
            host.navigate("bi002-game-host", cfg, digest, True, True, gui=gui)
        self.assertEqual(gui.clicked, [])

    def test_new_game_does_not_require_existing_save_registry(self):
        cfg, digest = self.fixture.launch_fake("new")
        gui = FakeGui()
        self.assertEqual(host.navigate("bi002-game-host", cfg, digest, True, True,
                                       gui=gui)["state"], "NEW_GAME_CAS_REQUESTED")
        self.assertEqual(len(gui.clicked), 1)


if __name__ == "__main__":
    unittest.main()
