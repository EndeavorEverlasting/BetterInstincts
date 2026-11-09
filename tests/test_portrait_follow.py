"""Portrait-follow regression: exact active Sim, no blind world right click."""
from __future__ import annotations
import unittest
import tempfile
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch

from betterinstincts.portrait_follow import (
    plan_portrait_follow, enqueue_native_portrait_follow,
)
from betterinstincts.player_presence import PresenceProbe
from betterinstincts.workflow_interop import CooperativeScreenQueue
from betterinstincts.scenes import load_catalog
from scripts.sim_camera import follow_active_portrait_on_admitted_host

CAP="capture:portrait-1"

def scene(**updates):
    d={
        "source":"HOST_CAPTURE","capture_ref":CAP,"scene_id":"live_mode",
        "mode":"LIVE","game_version":load_catalog()["game_version"],
        "capture_quality":"CONTENT_PRESENT","viewport_state":"NORMAL",
        "save_authorized":True,"player_queue_owned":False,
        "text_entry_active":False,"modal_open":False,"player_camera_owned":False,
        "camera_revision":"camera:51","active_sim_id":492,
        "active_sim_instanced":True,"camera_follow_sim_id":None,
        "independent_cues":[{"source":"visual","token":"live_hud"},
                            {"source":"operator","token":"live_confirmed"}],
        "process_id":303,"focused_process_id":303,"session_id":"demo",
        "host_admitted":True,"client_origin_x":0,"client_origin_y":0,
        "active_sim_portrait":{
            "source":"HOST_CAPTURE","capture_ref":CAP,"sim_id":492,
            "selected_sim_id":492,"lane":"BOTTOM_LEFT_HOUSEHOLD_PORTRAITS",
            "visible":True,"occluded":False,"enabled":True,
            "portrait_revision":"portrait:51","ui_layout_revision":"hud:51",
            "selected_sim_revision":"selection:51","client_width":1920,
            "client_height":1080,"hitbox":[250,750,350,850],
            "cues":[{"source":"visual","token":"active_sim_portrait_selection"},
                    {"source":"operator","token":"active_sim_identity_confirmed"}],
        },
    }
    d.update(updates)
    return d

def plan(s=None):
    return plan_portrait_follow(capture_ref=CAP,observation=s or scene())

class PortraitPolicyTests(unittest.TestCase):
    def test_right_click_is_preferred_follow_not_enter(self):
        p=plan()
        self.assertEqual(p["gate"],"COOPERATIVE_SCREEN_QUEUE_AND_NATIVE_HOST")
        self.assertEqual(p["effect"]["button"],"RIGHT")
        self.assertTrue(p["effect"]["follow"])
        self.assertEqual(p["effect"]["client"],[300,800])
        self.assertFalse(p["execute_allowed"])

    def test_already_following_is_no_second_right_click(self):
        p=plan(scene(camera_follow_sim_id=492))
        self.assertEqual(p["state"],"PORTRAIT_FOLLOW_ALREADY_OBSERVED")
        self.assertIsNone(p["effect"])

    def test_wrong_portrait_or_stale_layout_never_clicks(self):
        original=scene()
        for mutation in (
            {"sim_id":493},{"selected_sim_id":493},{"hitbox":[1700,700,1800,830]},
            {"visible":False},{"occluded":True},{"ui_layout_revision":None},
            {"cues":[{"source":"visual","token":"guessed"}]},
        ):
            with self.subTest(mutation=mutation):
                o=scene(active_sim_portrait={**original["active_sim_portrait"],**mutation})
                self.assertEqual(plan(o)["gate"],"PORTRAIT_REOBSERVE_REQUIRED")
        self.assertEqual(plan(scene(modal_open=True))["gate"],"PORTRAIT_REOBSERVE_REQUIRED")
        self.assertEqual(plan(scene(player_camera_owned=True))["gate"],"PORTRAIT_REOBSERVE_REQUIRED")

    def test_native_adapter_dispatches_right_click_not_enter(self):
        effects=[]
        current=scene()
        @contextmanager
        def lease(*a,**k):
            def ready(): effects.append("ready")
            yield ready
        def sensor(): return current
        with patch("betterinstincts.screen_admit.admitted_screen_lease",lease),\
             patch("scripts.win32_input.send_right_click",lambda x,y,**kw: effects.append(("right",x,y))),\
             patch("scripts.win32_input.park_safe_cursor_rest",lambda **kw:effects.append("rest")):
            out=follow_active_portrait_on_admitted_host(
                process_id=303,session_id="demo",observe=sensor)
        self.assertIn(("right",300,800),effects)
        self.assertNotIn("ENTER",effects)
        self.assertFalse(out["camera_follow_observed"])
        self.assertEqual(out["state"],"PORTRAIT_RIGHT_CLICK_DISPATCHED_UNVERIFIED")

    def test_native_adapter_rechecks_wrong_selected_sim(self):
        observed=[scene(),scene(active_sim_portrait={
            **scene()["active_sim_portrait"],"selected_sim_id":493
        })]
        @contextmanager
        def lease(*a,**k):yield lambda: None
        def sensor():return observed.pop(0)
        with patch("betterinstincts.screen_admit.admitted_screen_lease",lease),\
             patch("scripts.win32_input.send_right_click") as click:
            with self.assertRaisesRegex(ValueError,"PORTRAIT_CHANGED_BEFORE_RIGHT_CLICK"):
                follow_active_portrait_on_admitted_host(
                    process_id=303,session_id="demo",observe=sensor)
            click.assert_not_called()


class PortraitQueueTests(unittest.IsolatedAsyncioTestCase):
    async def test_queue_waits_for_human_then_right_clicks(self):
        with tempfile.TemporaryDirectory() as temp:
            last=[1000]
            effects=[]
            async def no_delay(_):pass
            async def observe():return scene()
            async def right(x,y):effects.append(("right",x,y))
            async def move(x,y):effects.append(("rest",x,y))
            queue=CooperativeScreenQueue(
                lambda:PresenceProbe(False,False,last_input_age_ms=last[0]),
                lambda:True,lock_root=Path(temp),sleep=no_delay)
            enqueue_native_portrait_follow(
                queue,work_id="portrait-1",capture_ref=CAP,observe=observe,
                process_id=303,session_id="demo",
                right_click_screen=right,move_screen=move)
            self.assertEqual((await queue.run_once())["state"],"WAITING_FOR_USER")
            self.assertEqual(effects,[])
            last[0]=16000
            self.assertEqual((await queue.run_once())["state"],"COMPLETED")
            self.assertEqual(effects[0],("right",300,800))
            self.assertEqual(effects[1][0],"rest")

if __name__=="__main__":
    unittest.main()
