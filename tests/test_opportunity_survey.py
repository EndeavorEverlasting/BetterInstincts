"""P82: passive survey, queue-safe prediction and idle-only exploration."""
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from betterinstincts.house_state import create_model, observe
from betterinstincts.host_listener import activate, tick
from betterinstincts.host_tandem import (
    queue_idle_exploration, run_opportunity_survey_session,
)
from betterinstincts.opportunity_survey import (
    OpportunitySurveyError, evaluate_opportunity_survey,
)
from betterinstincts.player_presence import PresenceProbe
from betterinstincts.workflow_interop import CooperativeScreenQueue

PATCH = "1.121.361.1020"
NEEDS = dict(hunger=.8, bladder=.9, energy=.15, hygiene=.7, fun=.6, social=.9)
LIVE = [{"source": "visual", "token": "live:sim_portraits_and_needs"},
        {"source": "operator", "token": "live_controls_visible"}]


def lot(*, unverified=False):
    model = create_model("survey_run", "opportunity_lot")
    return observe(model, entities={
        "office-zone": {"kind": "ROOM_ZONE", "story": "FLOOR_2", "zone": "OFFICE",
                        "enclosure": "INSIDE"},
        "desk": {"kind": "DESK", "story": "FLOOR_2", "zone": "OFFICE",
                 "enclosure": "INSIDE",
                 "confidence": "HYPOTHESIS" if unverified else "LOCAL_OBSERVED"},
        "chair": {"kind": "DINING_CHAIR", "story": "FLOOR_2", "zone": "OFFICE",
                  "enclosure": "INSIDE"},
        "bed": {"kind": "BED", "story": "FLOOR_2", "zone": "OFFICE",
                "enclosure": "INSIDE"},
        "fridge": {"kind": "APPLIANCE", "label": "Refrigerator",
                   "story": "FLOOR_2", "zone": "OFFICE", "enclosure": "INSIDE"},
        "yard-zone": {"kind": "ROOM_ZONE", "story": "FLOOR_1", "zone": "GARDEN",
                      "enclosure": "OUTSIDE"},
        "planter": {"kind": "PLANTER", "story": "FLOOR_1", "zone": "GARDEN",
                    "enclosure": "OUTSIDE"},
    })


def survey(**kwargs):
    m = kwargs.pop("lot_model", lot())
    options = dict(
        queue=[], multitasking=False, lot_model=m,
        active_lot_id=m["lot_id"], game_version=PATCH,
        capture_ref="capture:survey-now", verified_live_mode=True,
        host_may_control=True, camera_follow_attested=True,
        actor_ref="sim:teen",
    )
    options.update(kwargs)
    return evaluate_opportunity_survey(NEEDS, **options)


def observation(m, number):
    return {
        "schema": "betterinstincts.host-listener.observation/v1",
        "actor_ref": "sim:teen", "needs": NEEDS, "queue": ["Chat"],
        "multitasking": True, "location_kind": "home",
        "available_objects": ["bed", "fridge"], "capture_ref": f"capture:survey-{number}",
        "lot_model": m, "active_lot_id": m["lot_id"], "game_version": PATCH,
        "mode_observations": LIVE, "camera_follow_attested": True,
        "viewport": {"state": "VIEWPORT_OK"}, "homework_pending": True,
        "inventory_has_homework": True,
    }


def idle(_raw=None):
    return PresenceProbe(True, False, last_input_age_ms=60_000, probe_ok=True)


def playing(_raw=None):
    return PresenceProbe(True, True, last_input_age_ms=0, probe_ok=True)


class PureSurveyTests(unittest.TestCase):
    def test_busy_queue_still_survey_need_and_career_on_all_known_floors(self):
        m = lot()
        result = survey(queue=["Chat", "Browse"], multitasking=True,
                        homework_pending=True, inventory_has_homework=True,
                        player_active=True, host_may_control=False)
        self.assertEqual(result["state"], "OPPORTUNITIES_EVALUATED")
        self.assertEqual(result["room_count"], 2)
        self.assertEqual(result["queue_budget"]["max_new_actions"], 0)
        self.assertGreater(len(result["candidates"]), 1)
        self.assertEqual(result["candidates"][0]["goal_id"], "need:energy")
        self.assertIn("career:teen_homework", {row["goal_id"] for row in result["candidates"]})
        self.assertIsNone(result["queue_recommendation"])
        self.assertEqual(result["exploration_gate"], "PLAYER_ACTIVE_PASSIVE_ONLY")
        self.assertFalse(result["execute_allowed"])

    def test_idle_has_bounded_revision_scoped_hover_candidates(self):
        result = survey()
        self.assertEqual(result["exploration_gate"], "IDLE_EXPLORATION_CANDIDATE")
        self.assertEqual(result["lot_id"], "opportunity_lot")
        self.assertLessEqual(len(result["exploration_targets"]), 4)
        self.assertTrue(all("lot_revision" in row for row in result["exploration_targets"]))
        self.assertEqual(result["queue_recommendation"]["gate"],
                         "REOBSERVE_AFFORDANCE_AND_QUEUE_BEFORE_INPUT")

    def test_unknown_scene_lot_camera_or_patch_never_sends_input(self):
        self.assertEqual(survey(camera_follow_attested=False)["exploration_gate"],
                         "ACTIVE_SIM_FOLLOW_REQUIRED")
        self.assertEqual(survey(verified_live_mode=False)["exploration_gate"],
                         "LIVE_SCENE_NOT_CERTIFIED")
        m = lot()
        no_lot = evaluate_opportunity_survey(NEEDS, lot_model=m,
                                            active_lot_id="wrong-lot",
                                            game_version=PATCH)
        self.assertEqual(no_lot["state"], "SURVEY_WAITING_FOR_LOT")
        self.assertEqual(no_lot["exploration_gate"], "ACTIVE_LOT_MISMATCH")
        self.assertEqual(evaluate_opportunity_survey(NEEDS)["state"], "SURVEY_WAITING_FOR_LOT")

    def test_unverified_objects_and_capture_mismatched_goals_fail_closed(self):
        result = survey(lot_model=lot(unverified=True),
                        homework_pending=True, inventory_has_homework=True)
        self.assertNotIn("career:teen_homework", {r["goal_id"] for r in result["candidates"]})
        with self.assertRaises(OpportunitySurveyError):
            survey(observed_goals=[{
                "id": "job:painting", "domain": "career", "target_ref": "object:bed",
                "priority": .8, "capture_ref": "capture:OLD"
            }])
        result = survey(observed_goals=[{
            "id": "job:rest", "domain": "career", "target_ref": "object:bed",
            "priority": .8, "capture_ref": "capture:survey-now"
        }])
        self.assertIn("job:rest", {r["goal_id"] for r in result["candidates"]})


class IntegratedSurveyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.p1 = patch("betterinstincts.host_listener.ROOT", root)
        self.p2 = patch("betterinstincts.host_listener.OUTPUT", root / "dist" / "host-listener")
        self.p1.start()
        self.p2.start()
        self.sid = "survey-passive"
        activate(self.sid)

    def tearDown(self):
        self.p2.stop()
        self.p1.stop()
        self.temp.cleanup()

    def test_player_yield_still_emits_lot_knowledge_without_click(self):
        row = observation(lot(), 1)
        result = tick(self.sid, row, presence_probe=playing())
        self.assertEqual(result["listener_action"], "YIELD_TO_PLAYER")
        survey = result["opportunity_survey"]
        self.assertEqual(survey["state"], "OPPORTUNITIES_EVALUATED")
        self.assertTrue(survey["candidates"])
        self.assertEqual(survey["exploration_gate"], "PLAYER_ACTIVE_PASSIVE_ONLY")
        self.assertFalse(result["execute_clicks"])

    def test_same_survey_on_idle_receipt_remains_advisory(self):
        result = tick(self.sid, observation(lot(), 2), presence_probe=idle())
        self.assertEqual(result["opportunity_survey"]["exploration_gate"],
                         "IDLE_EXPLORATION_CANDIDATE")
        self.assertFalse(result["opportunity_survey"]["execute_allowed"])
        self.assertFalse(result["execute_clicks"])


class AsyncSurveyTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.p1 = patch("betterinstincts.host_listener.ROOT", root)
        self.p2 = patch("betterinstincts.host_listener.OUTPUT", root / "dist" / "host-listener")
        self.p1.start()
        self.p2.start()
        activate("async-survey")

    def tearDown(self):
        self.p2.stop()
        self.p1.stop()
        self.temp.cleanup()

    async def test_async_observer_continues_during_player_input(self):
        m = lot()
        count = 0
        receipts = []

        async def observe_async():
            nonlocal count
            count += 1
            await asyncio.sleep(0)
            return observation(m, count)

        async def on_receipt(receipt):
            receipts.append(receipt)

        def presence(raw):
            return playing() if raw["capture_ref"].endswith("-1") else idle()

        result = await run_opportunity_survey_session(
            "async-survey", "sim:teen", observe=observe_async,
            probe=presence, max_turns=2, interval_seconds=1,
            on_receipt=on_receipt,
        )
        self.assertEqual(result["survey_receipts"], 2)
        self.assertEqual(receipts[0]["listener_action"], "YIELD_TO_PLAYER")
        self.assertEqual(receipts[1]["opportunity_survey"]["state"], "OPPORTUNITIES_EVALUATED")
        self.assertEqual(result["pending_exploration"], 0)

    async def test_idle_queue_executes_only_with_fresh_scene_and_probes(self):
        m = lot()
        result = survey(lot_model=m)
        visited = []
        async def instant(_):
            await asyncio.sleep(0)

        async def fresh():
            return observation(m, 99)

        async def visit(target, checkpoint):
            await checkpoint()
            visited.append(target["target_ref"])

        async def scenario(probe):
            with tempfile.TemporaryDirectory() as root:
                screen = CooperativeScreenQueue(
                    probe=lambda: probe(), session_active=lambda: True,
                    sleep=instant, lock_root=Path(root),
                )
                enqueued = queue_idle_exploration(
                    result, actor_ref="sim:teen",
                    screen_queue=screen, observe_fresh=fresh, navigate=visit,
                )
                state = await screen.run_once()
                return enqueued, state, screen

        waiting, w_state, w_screen = await scenario(playing)
        self.assertEqual(waiting["state"], "IDLE_EXPLORATION_QUEUED")
        self.assertEqual(w_state["state"], "WAITING_FOR_USER")
        self.assertEqual(visited, [])
        self.assertEqual(len(w_screen.pending), 1)

        queued, state, _ = await scenario(idle)
        self.assertEqual(queued["state"], "IDLE_EXPLORATION_QUEUED")
        self.assertEqual(state["state"], "COMPLETED")
        self.assertEqual(visited, [result["exploration_targets"][0]["target_ref"]])

    async def test_revision_drift_discards_exploration_without_click(self):
        m = lot()
        result = survey(lot_model=m)
        changed = observe(m, entities={
            "bed": {"kind": "BED", "story": "FLOOR_2", "zone": "OFFICE",
                    "enclosure": "INSIDE", "label": "Updated bed"}
        })
        async def instant(_):
            await asyncio.sleep(0)
        async def fresh():
            return observation(changed, 99)
        fired = []
        async def visit(target, checkpoint):
            fired.append(target)
        with tempfile.TemporaryDirectory() as root:
            screen = CooperativeScreenQueue(
                probe=idle, session_active=lambda: True,
                sleep=instant, lock_root=Path(root),
            )
            queue_idle_exploration(
                result, actor_ref="sim:teen", screen_queue=screen,
                observe_fresh=fresh, navigate=visit,
            )
            state = await screen.run_once()
            self.assertEqual(state["state"], "NEEDS_REVALIDATION")
        self.assertEqual(fired, [])


if __name__ == "__main__":
    unittest.main()
