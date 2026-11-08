import asyncio
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from betterinstincts.host_listener import activate
from betterinstincts.host_tandem import HostTandemError, run_tandem_session
from betterinstincts.player_presence import PresenceProbe

GREEN = dict(hunger=.9, bladder=.9, energy=.9, hygiene=.9, fun=.9, social=.9)


def snapshot(number, *, energy=.9, action_ref=None, owner="HOST", homework=False,
             inventory_has_homework=None):
    cap = f"capture:tandem-{number}"
    row = dict(
        schema="betterinstincts.host-listener.observation/v1", actor_ref="sim:charlee",
        needs={**GREEN, "energy": energy}, queue=[], available_objects=["bed", "phone"],
        location_kind="home", capture_ref=cap, viewport={"state": "VIEWPORT_OK"},
        already_busy=bool(action_ref), host_activity_ref=action_ref,
        host_activity_owner=owner, homework_pending=homework,
        gardening=dict(capture_ref=cap, observed_at_unix=time.time(), scene_verified=True,
                       queue_verified=True, responsibilities_checked=True,
                       minutes_until_obligation=120, observed_actions=[
                           dict(action_id=aid, label=label, target_ref=target,
                                capture_ref=cap, available=True)
                           for aid, label, target in (
                               ("WATER", "Water", "plant:one"),
                               ("SLEEP_IN_BED", "Sleep", "bed:existing"))]),
    )
    if inventory_has_homework is not None:
        row["inventory_has_homework"] = inventory_has_homework
    return row


def idle(_):
    return PresenceProbe(False, False, last_input_age_ms=20000, probe_ok=True)


def observed(command):
    return dict(state="OUTCOME_OBSERVED", actor_ref=command["actor_ref"],
                action_ref=command["action_ref"], observation_ref="capture:actual-outcome")


class HostTandemTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name).resolve()
        self.root_patch = patch("betterinstincts.host_listener.ROOT", root)
        self.output_patch = patch("betterinstincts.host_listener.OUTPUT", root / "dist/host-listener")
        self.root_patch.start()
        self.output_patch.start()
        activate("tandem-test")

    def tearDown(self):
        self.output_patch.stop()
        self.root_patch.stop()
        self.temp.cleanup()

    async def test_needs_monitor_preempts_pending_garden_for_sleep_then_revalidates(self):
        state = {"turn": 0, "active": None, "water_count": 0}
        sleep_finished = asyncio.Event()
        never = asyncio.Event()
        dispatched, interruptions = [], []

        async def observe():
            state["turn"] += 1
            if state["turn"] == 3:
                sleep_finished.set()
            await asyncio.sleep(0)  # Actual coroutine boundary, not a mocked evaluator.
            row = snapshot(state["turn"], energy=.1 if state["turn"] in (2, 3) else .9,
                           action_ref=state["active"])
            if state["water_count"] >= 2:
                row["gardening"]["observed_actions"] = []
            return row

        async def execute(command, _):
            dispatched.append(command)
            state["active"] = command["action_ref"]
            if command["phase"] == "GARDENING":
                state["water_count"] += 1
                if state["water_count"] == 1:
                    await never.wait()  # Gardening stays pending while observe continues.
            else:
                await sleep_finished.wait()
            state["active"] = None
            return observed(command)

        async def interrupt(command, row):
            interruptions.append(command)
            return dict(state="HOST_ACTION_INTERRUPTED", actor_ref=command["actor_ref"],
                        action_ref=command["action_ref"], capture_ref=row["capture_ref"])

        out = await run_tandem_session("tandem-test", "sim:charlee", observe=observe,
                                      execute=execute, interrupt_owned=interrupt, probe=idle, max_turns=6)
        self.assertEqual([row["phase"] for row in dispatched], ["GARDENING", "NEEDS", "GARDENING"])
        self.assertEqual(dispatched[1]["action_id"], "SLEEP_IN_BED")
        self.assertNotEqual(dispatched[0]["capture_ref"], dispatched[2]["capture_ref"])
        self.assertEqual(len(interruptions), 1)
        self.assertIn("GARDENING_SUSPENDED_FOR_NEEDS", [row["event"] for row in out["events"]])
        self.assertFalse(out["dispatch_authorized"])

    async def test_player_activity_stops_control_without_cancelling_player_queue(self):
        turns, executed, interrupted = 0, [], []
        async def observe():
            nonlocal turns
            turns += 1
            return snapshot(turns, action_ref=executed[0]["action_ref"] if executed else None)
        async def execute(command, _):
            executed.append(command)
            await asyncio.Event().wait()
        async def interrupt(*args):
            interrupted.append(args)
        def probe(row):
            return idle(row) if turns == 1 else PresenceProbe(True, True, last_input_age_ms=0, probe_ok=True)
        out = await run_tandem_session("tandem-test", "sim:charlee", observe=observe,
                                      execute=execute, interrupt_owned=interrupt, probe=probe, max_turns=3)
        self.assertEqual(out["state"], "PLAYER_OR_UNKNOWN_PRESENCE")
        self.assertEqual(len(executed), 1)
        self.assertEqual(interrupted, [])

    async def test_unknown_ownership_cannot_preempt_pending_activity(self):
        turns, executed, interrupted = 0, [], []
        async def observe():
            nonlocal turns
            turns += 1
            row = snapshot(turns, energy=.1 if turns > 1 else .9)
            row["already_busy"] = False  # Even caller's idle claim is not ownership proof.
            return row
        async def execute(command, _):
            executed.append(command)
            await asyncio.Event().wait()
        async def interrupt(*args):
            interrupted.append(args)
        await run_tandem_session("tandem-test", "sim:charlee", observe=observe,
                                 execute=execute, interrupt_owned=interrupt, probe=idle, max_turns=2)
        self.assertEqual(len(executed), 1)
        self.assertEqual(interrupted, [])

    async def test_ack_is_not_outcome_and_never_replays(self):
        turns, executed = 0, []
        async def observe():
            nonlocal turns
            turns += 1
            return snapshot(turns)
        async def execute(command, _):
            executed.append(command)
            return {"state": "REQUESTED"}
        async def interrupt(*_):
            self.fail("No preemption expected")
        out = await run_tandem_session("tandem-test", "sim:charlee", observe=observe,
                                      execute=execute, interrupt_owned=interrupt, probe=idle, max_turns=3)
        self.assertEqual(out["state"], "OUTCOME_UNPROVEN_REOBSERVE")
        self.assertEqual(len(executed), 1)

    async def test_new_homework_stops_only_owned_garden_and_hands_off(self):
        turns, executed, interrupted = 0, [], []
        async def observe():
            nonlocal turns
            turns += 1
            return snapshot(turns, homework=turns > 1,
                            action_ref=executed[0]["action_ref"] if executed else None)
        async def execute(command, _):
            executed.append(command)
            await asyncio.Event().wait()
        async def interrupt(command, row):
            interrupted.append(command)
            return dict(state="HOST_ACTION_INTERRUPTED", actor_ref=command["actor_ref"],
                        action_ref=command["action_ref"], capture_ref=row["capture_ref"])
        out = await run_tandem_session("tandem-test", "sim:charlee", observe=observe,
                                      execute=execute, interrupt_owned=interrupt, probe=idle, max_turns=3)
        self.assertEqual(out["state"], "RESPONSIBILITY_HANDOFF_REQUIRED")
        self.assertEqual(len(executed), 1)
        self.assertEqual(len(interrupted), 1)
        self.assertIn("CAREER_OBLIGATION_HELD", [row["event"] for row in out["events"]])
        self.assertTrue((out.get("career_obligation") or {}).get("obligation_held"))

    async def test_career_ready_handoff_after_needs_recovery_with_homework(self):
        turns, executed = 0, []
        async def observe():
            nonlocal turns
            turns += 1
            if turns == 1:
                return snapshot(turns, energy=.1)
            return snapshot(turns, energy=.9, homework=True, inventory_has_homework=True)
        async def execute(command, _):
            executed.append(command)
            return observed(command)
        async def interrupt(*_):
            self.fail("No interruption expected")
        out = await run_tandem_session("tandem-test", "sim:charlee", observe=observe,
                                      execute=execute, interrupt_owned=interrupt, probe=idle, max_turns=4)
        self.assertEqual(out["state"], "CAREER_READY_HANDOFF_REQUIRED")
        self.assertIn("CAREER_READY_AFTER_NEEDS", [row["event"] for row in out["events"]])
        self.assertTrue((out.get("career_obligation") or {}).get("obligation_held"))

    async def test_aspiration_dialog_cancels_while_disabled_and_hands_off(self):
        turns, executed = 0, []
        mother = (
            "Charlee is about to summon Mother Nature. She will bestow a temporary "
            "charm that allows Charlee to complete her Fairy transformation."
        )

        async def observe():
            nonlocal turns
            turns += 1
            row = snapshot(turns, energy=.9)
            row["aspiration_prompt_active"] = True
            row["aspiration_prompt_text"] = mother
            row["aspiration_completion_enabled"] = False
            return row

        async def execute(command, _):
            executed.append(command)
            return observed(command)

        async def interrupt(*_):
            self.fail("No interruption expected")

        out = await run_tandem_session(
            "tandem-test",
            "sim:charlee",
            observe=observe,
            execute=execute,
            interrupt_owned=interrupt,
            probe=idle,
            max_turns=3,
        )
        self.assertEqual(out["state"], "ASPIRATION_DIALOG_HANDOFF_REQUIRED")
        self.assertIn("ASPIRATION_PROMPT_HELD", [row["event"] for row in out["events"]])
        self.assertIn("ASPIRATION_DIALOG_READY", [row["event"] for row in out["events"]])
        held = out.get("aspiration_prompt") or {}
        self.assertTrue(held.get("prompt_held"))
        self.assertEqual(held.get("dialog_choice"), "CANCEL")
        self.assertFalse(held.get("press_ok_allowed"))
        self.assertEqual(executed, [])

    async def test_balance_ready_handoff_after_needs_with_burning_passion(self):
        turns, executed = 0, []

        async def observe():
            nonlocal turns
            turns += 1
            if turns == 1:
                row = snapshot(turns, energy=.1)
            else:
                row = snapshot(turns, energy=.9)
            row["balance_level"] = "very_imbalanced"
            row["ailment"] = "Burning Passion"
            return row

        async def execute(command, _):
            executed.append(command)
            return observed(command)

        async def interrupt(*_):
            self.fail("No interruption expected")

        out = await run_tandem_session(
            "tandem-test",
            "sim:charlee",
            observe=observe,
            execute=execute,
            interrupt_owned=interrupt,
            probe=idle,
            max_turns=4,
        )
        self.assertEqual(out["state"], "BALANCE_READY_HANDOFF_REQUIRED")
        self.assertIn("BALANCE_CONDITION_HELD", [row["event"] for row in out["events"]])
        self.assertIn("BALANCE_READY_AFTER_NEEDS", [row["event"] for row in out["events"]])
        held = out.get("balance_condition") or {}
        self.assertTrue(held.get("condition_held"))
        self.assertEqual(held.get("ailment"), "burning_passion")
        self.assertEqual(held.get("gate"), "READY_NATUROPATH")

    async def test_ineffective_completed_rest_is_not_repeated_blindly(self):
        turns, executed = 0, []
        async def observe():
            nonlocal turns
            turns += 1
            return snapshot(turns, energy=.1)
        async def execute(command, _):
            executed.append(command)
            return observed(command)
        async def interrupt(*_):
            self.fail("No interruption expected")
        out = await run_tandem_session("tandem-test", "sim:charlee", observe=observe,
                                      execute=execute, interrupt_owned=interrupt, probe=idle, max_turns=3)
        self.assertEqual(len(executed), 1)
        self.assertIn("NEED_RECOVERY_REVALIDATION_REQUIRED", [row["event"] for row in out["events"]])

    async def test_changed_actor_and_observer_timeout_stop(self):
        async def wrong_actor():
            return {"actor_ref": "sim:someone-else"}
        async def unused(*_):
            self.fail("No execution expected")
        out = await run_tandem_session("tandem-test", "sim:charlee", observe=wrong_actor,
                                      execute=unused, interrupt_owned=unused, probe=idle, max_turns=1)
        self.assertEqual(out["state"], "ACTOR_IDENTITY_CHANGED_OR_UNKNOWN")
        async def stuck():
            await asyncio.Event().wait()
        out = await run_tandem_session("tandem-test", "sim:charlee", observe=stuck,
                                      execute=unused, interrupt_owned=unused, probe=idle, max_turns=1,
                                      observation_timeout_seconds=1)
        self.assertEqual(out["state"], "OBSERVATION_TIMEOUT_REOBSERVE")

    async def test_bounds_and_explicit_activation(self):
        async def unused(*_):
            self.fail("No callback expected")
        kwargs = dict(observe=unused, execute=unused, interrupt_owned=unused, probe=idle)
        for changes in (dict(max_turns=0), dict(interval_seconds=0), dict(action_timeout_seconds=601)):
            with self.subTest(changes=changes), self.assertRaises(HostTandemError):
                await run_tandem_session("tandem-test", "sim:charlee", **kwargs, **changes)
        with self.assertRaisesRegex(HostTandemError, "EXPLICIT_ACTIVE_SESSION_REQUIRED"):
            await run_tandem_session("not-active", "sim:charlee", **kwargs)


if __name__ == "__main__":
    unittest.main()
