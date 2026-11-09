"""Event-overlay and bottom-right panel semantic attention regressions."""
from __future__ import annotations
import tempfile, unittest
from pathlib import Path
from betterinstincts.scenes import load_catalog
from betterinstincts.ui_microsystems import load_contract
from betterinstincts.scene_ui_semantics import (
    assess_live_hud, enqueue_resolved_overlay_dismiss,
)
from betterinstincts.player_presence import PresenceProbe
from betterinstincts.workflow_interop import CooperativeScreenQueue
from betterinstincts.host_stack import evaluate_turn

CAP="capture:hud-1"
SIX=dict.fromkeys(("hunger","bladder","energy","hygiene","fun","social"),0.8)

def frame(**changes):
    f={"source":"HOST_CAPTURE","capture_ref":CAP,"mode":"LIVE",
       "scene_id":"live_mode","game_version":load_catalog()["game_version"],
       "active_sim_id":492,"selected_sim_revision":"sel:1",
       "ui_layout_revision":"hud:1","client_width":1920,"client_height":1080,
       "active_goal_id":"goal:career","pending_action_queue_refs":["act:skill","act:garden"],
       "active_right_panel_id":"career","right_panel_visible":True,
       "right_panel_obscured":False,
       "right_panel_cues":[{"source":"visual","token":"panel:live_career"},
                            {"source":"operator","token":"career_visible"}],
       "process_id":303,"focused_process_id":303,"session_id":"demo",
       "host_admitted":True,"client_origin_x":0,"client_origin_y":0}
    f.update(changes);return f

def overlay(*,resolved=False,**changes):
    o={"overlay_id":"evt:promotion","kind":"CAREER_EVENT",
       "capture_ref":CAP,"ui_layout_revision":"hud:1","visible":True,
       "decision_state":"RESOLVED" if resolved else "PENDING",
       "decision_accepted":resolved,
       "cues":[{"source":"visual","token":"visible_overlay_identity"},
               {"source":"operator","token":"overlay_identity_confirmed"}],
       "dismiss_target":{
           "kind":"ACKNOWLEDGE_RESOLVED","overlay_id":"evt:promotion",
           "capture_ref":CAP,"ui_layout_revision":"hud:1",
           "visible":True,"obscured":False,"enabled":True,
           "hitbox":[950,650,1050,700],
           "cues":[{"source":"visual","token":"resolved_overlay_dismiss_button"},
                   {"source":"operator","token":"dismiss_button_confirmed"}],
       },
    }
    o.update(changes);return o

def assess(obs=None,**kwargs):
    return assess_live_hud(capture_ref=CAP,observation=obs or frame(),**kwargs)

class LiveHudTests(unittest.TestCase):
    def test_all_bottom_right_panels_are_trackable(self):
        cfg=load_contract()
        for id in ("aspirations","career","skills","relationships",
                   "simology","personal_inventory","needs"):
            self.assertIn(id,cfg["panels"])
            cues=cfg["panels"][id]["cues"]
            p=assess(frame(active_right_panel_id=id,
                right_panel_cues=[{"source":k,"token":v} for k,v in cues.items()]))
            self.assertEqual(p["active_panel_id"],id)
            self.assertEqual(p["gate"],"HUD_CONTEXT_READY")

    def test_panel_switch_without_stale_click(self):
        p=assess(frame(),requested_panel="skills",requested_target="skills.inspect_skill")
        self.assertEqual(p["gate"],"RIGHT_PANEL_SWITCH_OR_REOBSERVE")
        self.assertFalse(p["execute_allowed"])
        p=assess(frame(),requested_panel="career",requested_target="career.inspect_job")
        self.assertTrue(p["panel"]["hitbox_attestation_required"])
        self.assertIsNone(p["panel"].get("click"))
        bad=assess(frame(right_panel_cues=[
            {"source":"visual","token":"panel:live_skills"},
            {"source":"operator","token":"career_visible"}]))
        self.assertEqual(bad["gate"],"RIGHT_PANEL_REOBSERVE")

    def test_career_popup_stops_queue_and_requires_choice(self):
        p=assess(frame(overlay=overlay()))
        self.assertEqual(p["gate"],"OVERLAY_DECISION_REQUIRED")
        self.assertEqual(p["continuation"]["active_goal_id"],"goal:career")
        self.assertEqual(p["continuation"]["queue_refs"],["act:skill","act:garden"])
        self.assertIsNone(p["overlay"]["dismiss_action"])
        h=evaluate_turn(SIX,capture_ref=CAP,live_hud_observation=frame(overlay=overlay()))
        self.assertEqual(h["next_gate"],"OVERLAY_DECISION_REQUIRED")
        self.assertFalse(h["fallback"]["execute_allowed"])
        self.assertEqual(h["live_hud_semantics"]["continuation"]["queue_refs"],
                         ["act:skill","act:garden"])

    def test_random_popup_not_closed_on_guess_or_unaccepted_decision(self):
        p=assess(frame(overlay=overlay(kind="RANDOM_EVENT",
                                       decision_state="PENDING")))
        self.assertEqual(p["gate"],"OVERLAY_DECISION_REQUIRED")
        p=assess(frame(overlay=overlay(resolved=True,decision_accepted=False)))
        self.assertEqual(p["gate"],"OVERLAY_REOBSERVE")
        p=assess(frame(overlay=overlay(resolved=True,dismiss_target=None)))
        self.assertEqual(p["gate"],"OVERLAY_REOBSERVE")

    def test_resolved_popup_requires_attested_close_and_revalidation(self):
        p=assess(frame(overlay=overlay(resolved=True)))
        self.assertEqual(p["gate"],"OVERLAY_DISMISS_READY")
        self.assertEqual(p["overlay"]["client"],[1000,675])
        self.assertFalse(p["execute_allowed"])
        self.assertTrue(p["overlay"]["resume_only_after_overlay_absent"])


class OverlayQueueTests(unittest.IsolatedAsyncioTestCase):
    async def test_clears_only_resolved_overlay_and_retains_action_refs(self):
        with tempfile.TemporaryDirectory() as root:
            current=[frame(overlay=overlay(resolved=True))]
            events=[]
            async def observe():return current[0]
            async def click(x,y):
                events.append(("click",x,y))
                current[0]=frame(overlay=None)
            async def move(x,y):events.append(("rest",x,y))
            async def sleep(_):pass
            queue=CooperativeScreenQueue(
                lambda:PresenceProbe(False,False,last_input_age_ms=17000),
                lambda:True,lock_root=Path(root),sleep=sleep)
            queued=enqueue_resolved_overlay_dismiss(
                queue,work_id="dismiss-1",capture_ref=CAP,observe=observe,
                process_id=303,session_id="demo",click_screen=click,move_screen=move)
            self.assertEqual((await queue.run_once())["state"],"COMPLETED")
            self.assertEqual(events[0],("click",1000,675))
            self.assertEqual(queued["receipt"]["state"],"OVERLAY_CLEARED_QUEUE_REVALIDATION_REQUIRED")
            self.assertTrue(queued["receipt"]["overlay_cleared_observed"])
            self.assertFalse(queued["receipt"]["resume_queued_game_actions"])

if __name__=="__main__":unittest.main()
