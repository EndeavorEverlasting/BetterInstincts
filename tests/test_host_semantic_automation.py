"""Standard automation forwards the semantic camera, overlay and scenery gates."""
from __future__ import annotations
import unittest
from betterinstincts.host_automate import plan_automation
from betterinstincts.player_presence import PresenceProbe
from tests.test_portrait_follow import scene as portrait_scene, CAP as PORTRAIT_CAPTURE
from tests.test_scene_ui_semantics import frame as hud_frame, overlay, CAP as HUD_CAPTURE
from tests.test_scenery_memory import view as street_view, CAP as STREET_CAPTURE

SIX=dict.fromkeys(("hunger","bladder","energy","hygiene","fun","social"),0.8)

def host(capture,**extras):
    return {"needs":SIX,"queue":[],"location_kind":"home",
            "capture_ref":capture,**extras}

def probe(idle=18000):
    return PresenceProbe(False,False,last_input_age_ms=idle)

class SemanticAutomationEntryTests(unittest.TestCase):
    def test_portrait_right_click_is_normal_host_camera_gate(self):
        out=plan_automation(host(PORTRAIT_CAPTURE,
             sim_camera_observation=portrait_scene()),probe(),
             session_active=True)
        self.assertEqual(out["state"],"HOST_AUTOMATION_PLANNED")
        lock=out["host_stack"]["active_sim_camera_lock"]
        self.assertEqual(lock["gate"],"CAMERA_PORTRAIT_FOLLOW_REQUIRED")
        self.assertEqual(lock["portrait_follow"]["effect"]["button"],"RIGHT")
        self.assertFalse(out["execute_clicks"])

    def test_event_interrupts_without_erasing_original_queue(self):
        out=plan_automation(host(HUD_CAPTURE,
            live_hud_observation=hud_frame(overlay=overlay())),
            probe(),session_active=True)
        self.assertEqual(out["host_stack"]["next_gate"],"OVERLAY_DECISION_REQUIRED")
        continuation=out["host_stack"]["live_hud_semantics"]["continuation"]
        self.assertEqual(continuation["queue_refs"],["act:skill","act:garden"])
        self.assertFalse(out["execute_clicks"])

    def test_off_target_street_is_saved_as_scene_receipt_not_travel(self):
        out=plan_automation(host(STREET_CAPTURE,
            scenery_observation=street_view()),
            probe(),session_active=True)
        self.assertEqual(out["host_stack"]["next_gate"],"OFF_TARGET_SCENERY_REANCHOR_REQUIRED")
        self.assertEqual(out["host_stack"]["scenery_discovery"]["record"]["reason"],"OFF_TARGET")
        self.assertFalse(out["host_stack"]["scenery_discovery"]["execute_allowed"])

    def test_human_activity_yields_before_every_new_scene_system(self):
        out=plan_automation(host(PORTRAIT_CAPTURE,
            sim_camera_observation=portrait_scene()),probe(0),
            session_active=True)
        self.assertEqual(out["state"],"YIELD_TO_PLAYER")
        self.assertIsNone(out["host_stack"])

if __name__=="__main__":unittest.main()
