"""Lot-off-focus recognition (offline policy)."""
from __future__ import annotations

import unittest

from betterinstincts.host_stack import evaluate_turn
from betterinstincts.lot_focus import assess_lot_focus, should_assess_lot_focus
from betterinstincts.scenes import load_catalog


CAPTURE = "capture:lot-focus-1"


def obs(**overrides):
    data = {
        "source": "HOST_CAPTURE",
        "capture_ref": CAPTURE,
        "scene_id": "live_mode",
        "mode": "LIVE",
        "game_version": load_catalog()["game_version"],
        "capture_quality": "CONTENT_PRESENT",
        "viewport_state": "NORMAL",
        "save_authorized": True,
        "player_queue_owned": False,
        "text_entry_active": False,
        "modal_open": False,
        "player_camera_owned": False,
        "camera_revision": "camera:lot-1",
        "active_sim_id": 492,
        "active_sim_instanced": True,
        "camera_follow_sim_id": 492,
        "camera_displaced": False,
        "client_width": 1920,
        "client_height": 1080,
        "camera_on_active_household_lot": True,
        "camera_lot_kind": "home",
        "independent_cues": [
            {"source": "visual", "token": "live_hud"},
            {"source": "operator", "token": "live_confirmed"},
        ],
    }
    data.update(overrides)
    return data


SIX = {
    "hunger": 0.8,
    "bladder": 0.8,
    "energy": 0.8,
    "fun": 0.8,
    "hygiene": 0.8,
    "social": 0.8,
}


class LotFocusTests(unittest.TestCase):
    def test_on_lot_when_household_lot_attested(self):
        out = assess_lot_focus(capture_ref=CAPTURE, observation=obs())
        self.assertEqual(out["state"], "ON_LOT")
        self.assertFalse(out["execute_allowed"])
        self.assertIsNone(out.get("restore"))
        self.assertEqual(out["proof_ceiling"], "OFFLINE_LOT_FOCUS_POLICY_NOT_LIVE_CAMERA_CERTIFIED")

    def test_off_lot_street_when_travel_afar_without_goal(self):
        out = assess_lot_focus(
            capture_ref=CAPTURE,
            observation=obs(
                zoom_mode_observed="TRAVEL_AFAR",
                camera_on_active_household_lot=False,
                camera_lot_kind="street",
                live_hud_present=False,
            ),
        )
        self.assertEqual(out["state"], "OFF_LOT_STREET")
        self.assertEqual(out["gate"], "LOT_OFF_FOCUS_RESTORE_REQUIRED")
        self.assertEqual(out["restore_plan"]["command"], "CENTER_ACTIVE_SIM")
        self.assertEqual(out["restore_plan"]["chord"], ["ENTER"])
        self.assertIn("SHIFT_ENTER", out["restore_plan"]["forbid_default"])
        self.assertFalse(out["execute_allowed"])

    def test_unknown_when_cues_insufficient(self):
        out = assess_lot_focus(
            capture_ref=CAPTURE,
            observation={
                "source": "HOST_CAPTURE",
                "capture_ref": CAPTURE,
                "game_version": load_catalog()["game_version"],
            },
        )
        self.assertEqual(out["state"], "UNKNOWN")
        self.assertEqual(out["gate"], "LOT_FOCUS_UNKNOWN")
        self.assertIsNone(out.get("restore"))

    def test_off_lot_from_compound_scenery_tokens_with_live_hud(self):
        """Neighborhood PrintWindow: canal/street labels + low lot fraction.

        Live HUD can still be visible while scenery is clearly off immersion —
        compound tokens like CANAL_LEFT must still force OFF_LOT + Enter restore.
        """
        out = assess_lot_focus(
            capture_ref=CAPTURE,
            observation=obs(
                camera_on_active_household_lot=False,
                camera_lot_kind="neighborhood",
                live_hud_present=True,
                camera_altitude="NEIGHBORHOOD_HIGH",
                lot_fraction_of_frame=0.35,
                scenery_tokens=[
                    "CANAL_LEFT",
                    "STREET_RIGHT",
                    "NEIGHBOR_HOUSES",
                    "STREETLIGHTS",
                    "ACTIVE_LOT_LIT_CENTER",
                ],
            ),
        )
        self.assertEqual(out["state"], "OFF_LOT_STREET")
        self.assertEqual(out["gate"], "LOT_OFF_FOCUS_RESTORE_REQUIRED")
        self.assertEqual(out["restore_plan"]["chord"], ["ENTER"])
        self.assertFalse(out["execute_allowed"])

    def test_should_assess_on_travel_afar_cue(self):
        self.assertTrue(
            should_assess_lot_focus(observation=obs(zoom_mode_observed="TRAVEL_AFAR"))
        )

    def test_host_stack_emits_lot_focus_off_street(self):
        turn = evaluate_turn(
            SIX,
            capture_ref=CAPTURE,
            sim_camera_observation=obs(
                zoom_mode_observed="TRAVEL_AFAR",
                camera_on_active_household_lot=False,
                camera_lot_kind="neighborhood",
                live_hud_present=False,
            ),
        )
        self.assertIsNotNone(turn.get("lot_focus"))
        self.assertEqual(turn["lot_focus"]["state"], "OFF_LOT_STREET")
        self.assertEqual(turn["next_gate"], "LOT_OFF_FOCUS_RESTORE_REQUIRED")
        self.assertEqual(turn["fallback"]["mechanism"], "LOT_OFF_FOCUS_RESTORE")


if __name__ == "__main__":
    unittest.main()
