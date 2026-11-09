"""P82: whim-pin is mouse-only and never bypasses the native screen queue."""
import tempfile
import unittest
from pathlib import Path

from betterinstincts.player_presence import PresenceProbe
from betterinstincts.whim_pinning import (
    WhimPinError, plan_whim_pin, enqueue_whim_pin,
)
from betterinstincts.workflow_interop import CooperativeScreenQueue

PATCH="1.121.361.1020"
CAP="capture:pin"


def candidate(**kw):
    r=dict(sim_ref="sim:tim",whim_ref="whim:garden",action_id="GARDEN",
           capture_ref=CAP,positive_proof_ref="proof:benefit",
           evidence_kind="OBSERVED_POSITIVE",pin_policy_opt_in=True)
    r.update(kw)
    return r


def calibration(**kw):
    r=dict(target_id="whims.pin_whim",panel_id="whims",mode="LIVE",
           profile="1920x1080",game_version=PATCH,
           client_width=1920,client_height=1080,
           x=500,y=300,hitbox=[496,296,504,304],
           ui_layout_revision="layout:one",
           selected_sim_revision="selection:one",
           status="OPERATOR_VERIFIED_EXACT_BUILD",
           evidence_ref="proof:pin-hitbox",
           whim_ref="whim:garden",sim_ref="sim:tim",capture_ref=CAP)
    r.update(kw)
    return r


def observed(**kw):
    r=dict(target_id="whims.pin_whim",panel_id="whims",mode="LIVE",
           scene_id="live_mode",profile="1920x1080",game_version=PATCH,
           client_width=1920,client_height=1080,
           capture_quality="CONTENT_PRESENT",viewport_state="NORMAL",
           target_visible=True,save_authorized=True,player_queue_owned=False,
           independent_cues=[
               dict(source="visual",token="live-game-verified"),
               dict(source="operator",token="operator-confirmed-live")],
           panel_cues=[
               dict(source="visual",token="panel:live_whims"),
               dict(source="operator",token="whims_visible")],
           panel_visible=True,panel_hitbox=[496,296,504,304],
           ui_layout_revision="layout:one",selected_sim_revision="selection:one",
           panel_obscured=False,panel_animation_stable=True,target_enabled=True,
           sim_ref="sim:tim",selected_sim_ref="sim:tim",capture_ref=CAP,
           whim_ref="whim:garden",whim_visible=True,whim_pinned=False,
           scene_verified=True,player_active=False,
           process_id=1234,focused_process_id=1234,session_id="test-accept",
           host_admitted=True,client_origin_x=100,client_origin_y=50)
    r.update(kw)
    return r


class PinPlanTests(unittest.TestCase):
    def plan(self,c=None,cal=None,**kw):
        return plan_whim_pin(c or candidate(),cal or calibration(),
                             capture_ref=CAP,selected_sim_ref="sim:tim",
                             scene_verified=True,**kw)

    def test_valid_plan_is_not_pin_proof(self):
        r=self.plan()
        self.assertFalse(r["execute_allowed"])
        self.assertIsNone(r["control_permit"])
        self.assertEqual(r["target_id"],"whims.pin_whim")

    def test_mismatched_wish_sim_no_consent_or_mode_fails(self):
        for c,cal in [
            (candidate(whim_ref="whim:other"),calibration()),
            (candidate(pin_policy_opt_in=False),calibration()),
            (candidate(evidence_kind="MODEL_POSITIVE"),calibration()),
            (candidate(),calibration(sim_ref="sim:alex")),
            (candidate(),calibration(panel_id="career")),
            (candidate(),calibration(target_id="whims.inspect_whim")),
            (candidate(),calibration(mode="BUILD")),
        ]:
            with self.subTest(c=c,cal=cal),self.assertRaises(WhimPinError):
                self.plan(c,cal)
        with self.assertRaises(WhimPinError):
            self.plan(player_active=True)


class NativePinTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.age=16000
        self.effects=[]
        self.current=observed()
        async def no_delay(_): pass
        self.queue=CooperativeScreenQueue(
            lambda:PresenceProbe(False,False,last_input_age_ms=self.age),
            lambda:True,lock_root=Path(self.tmp.name),sleep=no_delay)

    async def sense(self):
        return self.current

    async def click(self,x,y):
        self.effects.append(("click",x,y))
        self.current=dict(self.current,whim_pinned=True)

    async def move(self,x,y):
        self.effects.append(("rest",x,y))

    def enqueue(self,**kw):
        return enqueue_whim_pin(
            self.queue,work_id="pin-once",candidate=candidate(),
            calibration=calibration(),observe=self.sense,
            process_id=1234,session_id="test-accept",
            click_screen=self.click,move_screen=self.move,
            capture_ref=CAP,selected_sim_ref="sim:tim",scene_verified=True,**kw)

    async def test_single_mouse_click_and_safe_rest(self):
        r=self.enqueue()
        self.assertFalse(r["execute_allowed"])
        self.assertFalse(r["pin_verified"])
        self.assertEqual((await self.queue.run_once())["state"],"COMPLETED")
        self.assertEqual(self.effects[0],("click",600,350))
        self.assertEqual(self.effects[1],("rest",1060,590))
        self.assertTrue(self.current["whim_pinned"])
        self.assertFalse(r["pin_verified"])
        self.assertEqual((await self.queue.run_once())["state"],"EMPTY")

    async def test_wrong_current_wish_actor_hitbox_or_focus_never_click(self):
        for bad in [
            dict(whim_ref="whim:other"),dict(selected_sim_ref="sim:alex"),
            dict(whim_pinned=True),dict(whim_visible=False),
            dict(player_active=True),dict(panel_obscured=True),
            dict(target_enabled=False),dict(focused_process_id=999),
            dict(ui_layout_revision="layout:changed")]:
            with self.subTest(bad=bad):
                self.queue.pending.clear()
                self.queue.needs_review.clear()
                self.current=observed(**bad)
                self.effects=[]
                self.enqueue()
                self.assertEqual((await self.queue.run_once())["state"],
                                 "NEEDS_REVALIDATION")
                self.assertEqual(self.effects,[])

    async def test_player_interrupt_after_click_quarantines_without_reclick(self):
        async def interrupted(x,y):
            self.effects.append(("click",x,y))
            self.current=dict(self.current,whim_pinned=True)
            self.age=0
        self.current=observed()
        self.enqueue()
        # Replace the injected click via enqueuing afresh, with same identity.
        self.queue.pending.clear()
        self.queue.needs_review.clear()
        enqueue_whim_pin(self.queue,work_id="pin-interrupt",
            candidate=candidate(),calibration=calibration(),observe=self.sense,
            process_id=1234,session_id="test-accept",
            click_screen=interrupted,move_screen=self.move,
            capture_ref=CAP,selected_sim_ref="sim:tim",scene_verified=True)
        self.assertEqual((await self.queue.run_once())["state"],
                         "NEEDS_RECONCILIATION")
        self.assertEqual(self.effects,[("click",600,350)])
        self.assertEqual(len(self.queue.pending),0)

    async def test_no_verified_calibration_or_no_player_idle_never_clicks(self):
        for cal in [calibration(status="CANDIDATE_UNVERIFIED"),
                    calibration(game_version="1.0.0.0"),
                    calibration(x=503)]:
            with self.subTest(cal=cal):
                self.queue.pending.clear()
                self.queue.needs_review.clear()
                with self.assertRaises(WhimPinError):
                    enqueue_whim_pin(self.queue,work_id="fail",
                        candidate=candidate(),calibration=cal,observe=self.sense,
                        process_id=1234,session_id="test-accept",
                        click_screen=self.click,move_screen=self.move,
                        capture_ref=CAP,selected_sim_ref="sim:tim",scene_verified=True)
        self.current=observed()
        self.age=0
        self.enqueue()
        self.assertEqual((await self.queue.run_once())["state"],"WAITING_FOR_USER")
        self.assertEqual(self.effects,[])


if __name__=="__main__": unittest.main()
