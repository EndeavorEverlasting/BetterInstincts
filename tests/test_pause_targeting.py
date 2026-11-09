"""P82 pause-first world targeting: time frozen, camera independently validated."""
from __future__ import annotations

import unittest
from contextlib import contextmanager
from unittest.mock import patch

from betterinstincts.camera_traverse import (
    CameraTraverseError, assess_drift_recovery, assess_game_pause, load_contract,
)
from betterinstincts.scenes import load_catalog
from betterinstincts.ui_chrome import load_contract as ui_contract
from scripts.camera_traverse import pause_game_on_admitted_host


VERSION = load_catalog()["game_version"]
CAPTURE = "capture:pause-1"


def frame(
    *,
    state="PLAYING", capture=CAPTURE, revision="camera:1",
    clock_revision="clock:10", speed_override=None, **changes,
):
    clock = {
        "source": "HOST_GAME_CLOCK", "capture_ref": capture,
        "camera_revision": revision, "game_version": VERSION,
        "clock_revision": clock_revision, "speed_state": state,
        "pause_indicator_active": state == "PAUSED",
        "clock_still_during_sample": state == "PAUSED",
        "pause_origin": "PLAYER",
    }
    if speed_override:
        clock.update(speed_override)
    row = {
        "source": "HOST_CAPTURE", "capture_ref": capture,
        "camera_revision": revision, "game_version": VERSION,
        "mode": "LIVE", "scene_id": "live_mode",
        "capture_quality": "CONTENT_PRESENT", "viewport_state": "NORMAL",
        "player_camera_owned": False, "player_queue_owned": False,
        "modal_open": False, "text_entry_active": False,
        "save_authorized": True, "camera_displaced": False,
        "camera_reanchor_attempts": 0, "cursor_client": [960, 540],
        "independent_cues": [
            {"source": "visual", "token": "live_ui"},
            {"source": "operator", "token": "exact_live_confirm"},
        ],
        "game_clock": clock,
    }
    row.update(changes)
    return row


def pause(candidate):
    return assess_game_pause(capture_ref=candidate.get("capture_ref", CAPTURE), observation=candidate)


class LiveClockPolicyTests(unittest.TestCase):
    def test_contract_registers_documented_toggle_with_non_idempotent_gate(self):
        cfg = load_contract()["drift_recovery"]["gameplay_pause"]
        self.assertEqual(cfg["toggle_key"], ["P"])
        self.assertTrue(cfg["pause_before_live_pixel_targeting"])
        self.assertFalse(cfg["auto_resume"])
        row = [h for h in ui_contract()["modes"]["LIVE"]["hotkeys"]
               if h["id"] == "PAUSE_GAME_TOGGLE"]
        self.assertEqual(len(row), 1)
        self.assertTrue(row[0]["not_idempotent"])
        self.assertEqual(row[0]["requires_clock_precondition"], "PLAYING_CORROBORATED")

    def test_running_game_requests_one_pause_no_mouse_click(self):
        result = pause(frame())
        self.assertEqual(result["gate"], "GAME_PAUSE_REQUIRED")
        self.assertEqual(result["key"], ["P"])
        self.assertFalse(result["paused_verified"])
        self.assertFalse(result["auto_resume_allowed"])
        self.assertFalse(result["execute_allowed"])

    def test_already_paused_preserves_player_speed_no_toggle(self):
        result = pause(frame(state="PAUSED"))
        self.assertEqual(result["gate"], "GAME_PAUSED_FOR_TARGETING")
        self.assertTrue(result["paused_verified"])
        self.assertIsNone(result["key"])
        self.assertEqual(result["pause_origin"], "PLAYER")
        self.assertEqual(result["clock_revision"], "clock:10")

    def test_missing_stale_or_conflicting_clock_never_toggles(self):
        candidates = [
            frame(game_clock=None),
            frame(speed_override={"source": "INFERRED_SCREENSHOT"}),
            frame(speed_override={"camera_revision": "camera:old"}),
            frame(speed_override={"capture_ref": "capture:stale"}),
            frame(speed_override={"game_version": "unknown"}),
            frame(speed_override={"clock_revision": ""}),
            frame(state="UNKNOWN"),
            frame(state="PLAYING", speed_override={"pause_indicator_active": True}),
            frame(state="PAUSED", speed_override={"clock_still_during_sample": False}),
            frame(state="PAUSED", speed_override={"pause_indicator_active": False}),
            frame(capture_quality="BLACK"),
            frame(mode="BUY"),
        ]
        for candidate in candidates:
            with self.subTest(candidate=candidate):
                p = pause(candidate)
                self.assertEqual(p["gate"], "GAME_PAUSE_REOBSERVE")
                self.assertFalse(p["paused_verified"])
                self.assertNotEqual(p.get("key"), ["P"])

    def test_player_control_text_and_modal_stop_pause(self):
        for change in (
            {"player_camera_owned": True}, {"player_queue_owned": True},
            {"text_entry_active": True}, {"modal_open": True},
            {"save_authorized": False}, {"independent_cues": []},
            {"scene_id": "main_menu"}, {"game_version": "unknown"},
        ):
            with self.subTest(change=change):
                self.assertEqual(pause(frame(**change))["gate"], "GAME_PAUSE_REOBSERVE")

    def test_scene_pause_before_reframe_or_target_when_cursor_safe(self):
        result = assess_drift_recovery(
            target_kind="SIM", capture_ref=CAPTURE,
            observation=frame(camera_displaced=True),
            client_width=1920, client_height=1080,
        )
        self.assertEqual(result["gate"], "GAME_PAUSE_REQUIRED")
        self.assertEqual(result["recovery_step"]["kind"], "PAUSE_GAME_IF_PLAYING")
        self.assertFalse(result["world_click_ready"])
        self.assertTrue(result["invalidate_prior_pixels"])

    def test_even_when_paused_requiring_new_target_and_camera_scene(self):
        result = assess_drift_recovery(
            target_kind="WORLD_OBJECT", target_id="A-OK Bloomer",
            capture_ref=CAPTURE, observation=frame(state="PAUSED"),
            client_width=1920, client_height=1080,
        )
        self.assertEqual(result["gate"], "CAMERA_RECOVERY_REOBSERVE")
        self.assertEqual(result["reason"], "WORLD_TARGET_CAPTURE_MISSING")
        self.assertFalse(result["world_click_ready"])

    def test_safe_rest_outranks_pause_if_camera_edge_panning(self):
        result = assess_drift_recovery(
            target_kind="LOT", capture_ref=CAPTURE,
            observation=frame(cursor_client=[1, 550]),
            client_width=1920, client_height=1080,
        )
        self.assertEqual(result["gate"], "CAMERA_SAFE_REST")
        self.assertEqual(result["recovery_step"]["kind"], "SAFE_REST")

    def test_unrecognized_pause_policy_fails_closed(self):
        cfg = load_contract()
        cfg["drift_recovery"]["gameplay_pause"]["auto_resume"] = True
        with self.assertRaisesRegex(CameraTraverseError, "GAME_PAUSE_POLICY_UNSAFE"):
            assess_game_pause(capture_ref=CAPTURE, observation=frame(), cfg=cfg)


class AdmittedPausePortTests(unittest.TestCase):
    def make_lease(self, effects):
        @contextmanager
        def fake_lease(process_id, session_id):
            self.assertEqual((process_id, session_id), (4321, "lab-session"))
            def checkpoint():
                effects.append("checkpoint")
            yield checkpoint
        return fake_lease

    def test_one_toggle_only_when_playing_then_verifies_paused(self):
        effects = []
        observations = iter([
            frame(), frame(),
            frame(state="PAUSED", capture="capture:pause-2", revision="camera:2",
                  clock_revision="clock:11", speed_override={"pause_origin": "AGENT"}),
        ])
        with patch("betterinstincts.screen_admit.admitted_screen_lease", self.make_lease(effects)), \
                patch("scripts.win32_input.send_key_chord",
                      lambda chord: effects.append(tuple(chord))):
            out = pause_game_on_admitted_host(
                process_id=4321, session_id="lab-session",
                observe=lambda: next(observations),
            )
        self.assertEqual(out["state"], "PAUSE_VERIFIED")
        self.assertEqual(effects, ["checkpoint", "checkpoint", ("P",)])
        self.assertTrue(out["new_capture_required_for_target"])
        self.assertFalse(out["auto_resume"])

    def test_already_paused_is_noop_without_input(self):
        effects = []
        with patch("betterinstincts.screen_admit.admitted_screen_lease", self.make_lease(effects)), \
                patch("scripts.win32_input.send_key_chord",
                      lambda chord: effects.append(tuple(chord))):
            out = pause_game_on_admitted_host(
                process_id=4321, session_id="lab-session",
                observe=lambda: frame(state="PAUSED"),
            )
        self.assertEqual(out["state"], "GAME_ALREADY_PAUSED_NO_INPUT")
        self.assertEqual(effects, ["checkpoint"])
        self.assertFalse(out["key_dispatched"])

    def test_speed_changed_between_probes_forbids_toggle(self):
        effects = []
        observations = iter([frame(), frame(state="PAUSED")])
        with patch("betterinstincts.screen_admit.admitted_screen_lease", self.make_lease(effects)), \
                patch("scripts.win32_input.send_key_chord",
                      lambda chord: effects.append(tuple(chord))):
            with self.assertRaisesRegex(CameraTraverseError, "PAUSE_SOURCE_CHANGED_BEFORE_KEY"):
                pause_game_on_admitted_host(
                    process_id=4321, session_id="lab-session",
                    observe=lambda: next(observations),
                )
        self.assertEqual(effects, ["checkpoint", "checkpoint"])

    def test_unverified_post_toggle_does_not_retry_or_resume(self):
        effects = []
        observations = iter([frame(), frame(), frame(state="PLAYING")])
        with patch("betterinstincts.screen_admit.admitted_screen_lease", self.make_lease(effects)), \
                patch("scripts.win32_input.send_key_chord",
                      lambda chord: effects.append(tuple(chord))):
            out = pause_game_on_admitted_host(
                process_id=4321, session_id="lab-session",
                observe=lambda: next(observations),
            )
        self.assertEqual(out["state"], "PAUSE_KEY_DISPATCHED_UNVERIFIED")
        self.assertFalse(out["pause_verified"])
        self.assertEqual(effects.count(("P",)), 1)
        self.assertFalse(out["auto_resume"])

    def test_unknown_or_missing_sensor_never_sends_key(self):
        effects = []
        with patch("betterinstincts.screen_admit.admitted_screen_lease", self.make_lease(effects)), \
                patch("scripts.win32_input.send_key_chord",
                      lambda chord: effects.append(tuple(chord))):
            with self.assertRaisesRegex(CameraTraverseError, "GAME_PAUSE_STATE_NOT_VERIFIED"):
                pause_game_on_admitted_host(
                    process_id=4321, session_id="lab-session",
                    observe=lambda: frame(game_clock=None),
                )
        self.assertEqual(effects, ["checkpoint"])


if __name__ == "__main__":
    unittest.main()
