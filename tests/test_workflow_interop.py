"""Deterministic 15-second async desktop waiter + cross-agent lock regressions."""
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from betterinstincts.control_handoff import (
    HandoffError, exclusive_desktop_owner, exclusive_screen_owner,
)
from betterinstincts.player_presence import PresenceProbe
from betterinstincts.workflow_interop import (
    CooperativeScreenQueue, QueuedStep, MAX_QUEUE,
)


class WaiterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.age = 0
        self.active = True
        self.events = []
        self.sleeps = []

        async def fake_sleep(seconds):
            self.sleeps.append(seconds)

        self.queue = CooperativeScreenQueue(
            lambda: PresenceProbe(False, False, last_input_age_ms=self.age),
            lambda: self.active, lock_root=Path(self.tmp.name), sleep=fake_sleep,
        )

    def step(self, work_id="one", valid=True):
        async def validate():
            self.events.append("validate")
            return valid

        async def action(checkpoint):
            await checkpoint()
            self.events.append("effect")

        return QueuedStep(work_id, validate, action)

    async def test_human_activity_waits_without_dropping_work(self):
        self.queue.enqueue(self.step())
        first = await self.queue.drain(max_checks=3)
        self.assertEqual(first["state"], "WAIT_BUDGET_REACHED")
        self.assertEqual([x.work_id for x in self.queue.pending], ["one"])
        self.assertNotIn("effect", self.events)
        self.age = 14999
        self.assertEqual((await self.queue.run_once())["state"], "WAITING_FOR_USER")
        self.age = 15000
        self.assertEqual((await self.queue.run_once())["state"], "COMPLETED")
        self.assertEqual(self.queue.completed, ["one"])
        self.assertEqual(self.events, ["validate", "effect"])

    async def test_idle_without_active_session_still_waits(self):
        self.age = 16000
        self.active = False
        self.queue.enqueue(self.step())
        self.assertEqual((await self.queue.run_once())["state"], "WAITING_FOR_USER")
        self.assertEqual(len(self.queue.pending), 1)

    async def test_missing_or_failed_probe_never_grants(self):
        self.queue.probe = lambda: PresenceProbe(False, False, last_input_age_ms=None)
        self.queue.enqueue(self.step())
        self.assertEqual((await self.queue.run_once())["state"], "WAITING_FOR_USER")
        self.queue.probe = lambda: (_ for _ in ()).throw(RuntimeError("sensor"))
        self.assertEqual((await self.queue.run_once())["state"], "WAITING_FOR_USER")

    async def test_input_during_second_probe_waits_then_resumes(self):
        ages = iter([16000, 0])
        self.queue.probe = lambda: PresenceProbe(False, False, last_input_age_ms=next(ages))
        self.queue.enqueue(self.step())
        self.assertEqual((await self.queue.run_once())["state"], "WAITING_FOR_USER")
        self.assertEqual(len(self.queue.pending), 1)
        self.assertEqual(self.events, [])
        self.queue.probe = lambda: PresenceProbe(False, False, last_input_age_ms=16000)
        self.assertEqual((await self.queue.run_once())["state"], "COMPLETED")

    async def test_interrupted_partial_effect_never_replays(self):
        # Preflight(2), acquired-lock(2), validate-followup(2),
        # effect1(2), effect2 interrupted: 8 approved probes then input.
        ages = iter([16000] * 8 + [0])
        self.queue.probe = lambda: PresenceProbe(False, False, last_input_age_ms=next(ages))

        async def validate():
            return True

        async def action(checkpoint):
            await checkpoint()
            self.events.append("effect1")
            await checkpoint()
            self.events.append("effect2")

        self.queue.enqueue(QueuedStep("partial", validate, action))
        result = await self.queue.run_once()
        self.assertEqual(result["state"], "NEEDS_RECONCILIATION")
        self.assertEqual(self.events, ["effect1"])
        self.assertIn("partial", self.queue.needs_review)
        self.assertEqual(len(self.queue.pending), 0)

    async def test_changed_scene_never_dispatches(self):
        self.age = 16000
        self.queue.enqueue(self.step(valid=False))
        self.assertEqual((await self.queue.run_once())["state"], "NEEDS_REVALIDATION")
        self.assertEqual(self.events, ["validate"])
        self.assertIn("one", self.queue.needs_review)

    async def test_desktop_lock_contention_keeps_queue(self):
        self.age = 16000
        self.queue.enqueue(self.step())
        with exclusive_desktop_owner(lock_root=Path(self.tmp.name)):
            self.assertEqual((await self.queue.run_once())["state"], "WAITING_FOR_AGENT")
        self.assertEqual((await self.queue.run_once())["state"], "COMPLETED")

    async def test_queue_is_bounded_and_deduplicated(self):
        self.queue.enqueue(self.step("a"))
        with self.assertRaisesRegex(ValueError, "ALREADY_REGISTERED"):
            self.queue.enqueue(self.step("a"))
        for i in range(1, MAX_QUEUE):
            self.queue.enqueue(self.step(f"step{i}"))
        with self.assertRaisesRegex(ValueError, "QUEUE_FULL"):
            self.queue.enqueue(self.step("overflow"))

    async def test_legacy_game_executor_obeys_desktop_lease(self):
        with exclusive_desktop_owner(lock_root=Path(self.tmp.name)):
            with self.assertRaisesRegex(HandoffError, "SCREEN_OWNER_BUSY"):
                with exclusive_screen_owner(1234, lock_root=Path(self.tmp.name)):
                    self.fail("must not grab other agent's desktop")
        with exclusive_screen_owner(1234, lock_root=Path(self.tmp.name)):
            with self.assertRaisesRegex(HandoffError, "SCREEN_OWNER_BUSY"):
                with exclusive_desktop_owner(lock_root=Path(self.tmp.name)):
                    self.fail("must not grab game's desktop")



class CanonicalScreenLockTests(unittest.TestCase):
    def test_default_lock_location_is_shared_outside_repository_checkouts(self):
        import bootstrap
        from betterinstincts.control_handoff import canonical_lock_root
        root = canonical_lock_root()
        expected = bootstrap.paths()["locks"]
        self.assertEqual(root, expected)
        self.assertEqual(root.parent.name, "runtime")
        self.assertNotIn("dist/host-listener", str(root).replace("\\\\", "/"))

    def test_presence_policy_stays_pure_when_profile_is_unavailable(self):
        from bootstrap import BootstrapError
        from betterinstincts.control_handoff import decide
        with patch(
            "betterinstincts.control_handoff.workstation_paths",
            side_effect=BootstrapError("no profile"),
        ):
            verdict = decide(
                PresenceProbe(False, False, last_input_age_ms=20000),
                session_active=True,
            )
            self.assertTrue(verdict["screen_control_allowed"])
            with self.assertRaisesRegex(HandoffError, "SCREEN_LOCK_PROFILE_UNRESOLVED"):
                with exclusive_desktop_owner():
                    self.fail("no input without canonical profile")

    def test_15_seconds_is_non_negotiable_even_for_explicit_override(self):
        with self.assertRaisesRegex(ValueError, "IDLE_THRESHOLD_OUT_OF_RANGE"):
            CooperativeScreenQueue(
                lambda: PresenceProbe(False, False, last_input_age_ms=100000),
                lambda: True, idle_ms=14999,
            )


if __name__ == "__main__":
    unittest.main()
