"""Exercise player-owned observations through the existing listener entrypoint."""
import asyncio
import sqlite3
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from betterinstincts.host_listener import activate, deactivate, tick
from betterinstincts.host_tandem import run_opportunity_survey_session
from betterinstincts.player_presence import PresenceProbe
from tests.test_ui_mode import observation


PLAYING = PresenceProbe(True, True, last_input_age_ms=0, foreground_process_id=101)
IDLE = PresenceProbe(True, True, last_input_age_ms=60_000, foreground_process_id=101)
CONTEXT = {"scenario": "event_social", "previous_action": "socialize", "style": "social",
           "available_actions": ["sit_and_chat_here", "socialize"]}


class PassivePlayerLearningTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        for name, value in (("ROOT", root), ("OUTPUT", root / "dist" / "host-listener")):
            patcher = patch("betterinstincts.host_listener." + name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.store = root / "dist" / "judgment-learning" / "player-observed"
        self.session = "player-lessons"
        self.sequence = 0
        activate(self.session, player_learning_profile="local-player")

    def snapshot(self, kind, detail, **changed):
        self.sequence += 1
        raw = observation("LIVE")
        raw.update(capture_ref=f"capture:lesson-{self.sequence}", **changed)
        raw["player_learning"] = {
            "kind": kind, "run": "game-instance-a", "household": "household-a",
            "platform": "windows", "sequence": self.sequence, **detail,
        }
        return raw

    def choice(self, interaction, **changed):
        return self.snapshot("choice", {
            **CONTEXT, "interaction": interaction, "action": "sit_and_chat_here",
            "owner": "PLAYER",
        }, **changed)

    def outcome(self, interaction, goal_delta=0.20, **changed):
        return self.snapshot("outcome", {
            "interaction": interaction, "effect_capture": f"capture:effect-{self.sequence}",
            "completed": True, "goal_delta": goal_delta,
        }, **changed)

    def run_tick(self, raw, probe=PLAYING):
        receipt = tick(self.session, raw, presence_probe=probe)
        self.assertFalse(receipt["execute_clicks"])
        self.assertFalse(receipt["player_learning"]["execute_clicks"])
        self.assertIsNone(receipt["player_learning"]["control_permit"])
        return receipt

    def learn(self, identity, **outcome):
        self.assertEqual(self.run_tick(self.choice(identity))["listener_action"], "YIELD_TO_PLAYER")
        return self.run_tick(self.outcome(identity, **outcome))["player_learning"]["state"]

    def hint(self, **extra):
        return self.run_tick(self.snapshot("query", CONTEXT, **extra), IDLE)["player_learning"]

    def test_learns_only_after_outcome_and_reuses_the_same_profile(self):
        self.assertEqual(self.hint()["reason"], "NO_PLAYER_DEMONSTRATIONS")
        for i in range(2):
            self.assertEqual(self.learn(f"interaction-{i}"), "PLAYER_OUTCOME_HELPFUL")
            self.assertEqual(self.hint()["state"], "ABSTAIN")
        self.assertEqual(self.learn("interaction-2"), "PLAYER_OUTCOME_HELPFUL")
        deactivate(self.session)
        self.session = "returning-session"
        activate(self.session, player_learning_profile="local-player")
        hint = self.hint()
        self.assertEqual(hint["state"], "ADVISORY_ONLY")
        self.assertEqual(hint["suggested_action"], "sit_and_chat_here")
        self.assertEqual(hint["support"], 3)
        # A different profile cannot see the demonstrations.
        self.session = "other-session"
        activate(self.session, player_learning_profile="other-player")
        self.assertEqual(self.hint()["reason"], "NO_PLAYER_DEMONSTRATIONS")

    def test_wrong_actor_or_unverified_live_capture_cannot_complete_episode(self):
        self.run_tick(self.choice("player-choice"))
        mismatch = self.outcome("player-choice", actor_ref="sim:another")
        self.assertEqual(self.run_tick(mismatch)["player_learning"]["reason"], "NO_MATCHING_PLAYER_CHOICE")
        self.run_tick(self.choice("player-choice"))
        non_sims = PresenceProbe(False, False, last_input_age_ms=0, foreground_process_id=456)
        self.assertEqual(self.run_tick(self.outcome("player-choice"), non_sims)["player_learning"]["reason"],
                         "FRESH_FOREGROUND_LIVE_GAME_REQUIRED")
        self.assertFalse(self.store.exists())

    def test_distinct_effect_capture_required(self):
        choice = self.choice("player-choice")
        self.run_tick(choice)
        outcome = self.outcome("player-choice")
        outcome["player_learning"]["effect_capture"] = choice["capture_ref"]
        self.assertEqual(self.run_tick(outcome)["player_learning"]["reason"], "OUTCOME_EVIDENCE_NOT_INDEPENDENT")
        self.assertFalse(self.store.exists())

    def test_harmful_precedent_vetoes_advice(self):
        for i in range(3):
            self.learn(f"interaction-{i}")
        before = self.choice("urgent-loss")
        self.run_tick(before)
        outcome = self.outcome("urgent-loss")
        outcome["needs"]["hunger"] = 0.20
        self.assertEqual(self.run_tick(outcome)["player_learning"]["state"], "PLAYER_OUTCOME_HARMFUL")
        self.assertEqual(self.hint()["state"], "ABSTAIN")

    def test_ordinary_session_never_opens_player_learning_store(self):
        self.session = "ordinary"
        activate(self.session)
        result = self.run_tick(self.choice("player-choice"))
        self.assertEqual(result["listener_action"], "YIELD_TO_PLAYER")
        self.assertEqual(result["player_learning"]["reason"], "PLAYER_LEARNING_NOT_OPTED_IN")
        self.assertFalse(self.store.exists())

    def test_replay_cannot_count_and_shared_store_survives_writer_contention(self):
        choice = self.choice("player-choice")
        outcome = self.outcome("player-choice")
        self.run_tick(choice)
        self.assertEqual(self.run_tick(outcome)["player_learning"]["state"], "PLAYER_OUTCOME_HELPFUL")
        deactivate(self.session)
        self.session = "another-listener"
        activate(self.session, player_learning_profile="local-player")
        self.run_tick(choice)
        self.assertEqual(self.run_tick(outcome)["player_learning"]["state"], "OUTCOME_ALREADY_RECORDED")
        self.assertEqual(self.hint()["state"], "ABSTAIN")

        choice = self.choice("new-player-choice")
        outcome = self.outcome("new-player-choice")
        self.run_tick(choice)
        db = sqlite3.connect(next(self.store.glob("*.sqlite3")))
        self.addCleanup(db.close)
        db.execute("BEGIN IMMEDIATE")
        try:
            self.assertEqual(self.run_tick(outcome)["player_learning"]["reason"],
                             "PLAYER_LEARNING_STORE_UNAVAILABLE")
        finally:
            db.rollback()
        self.assertEqual(self.run_tick(outcome)["player_learning"]["state"], "PLAYER_OUTCOME_HELPFUL")
        self.assertEqual(db.execute("SELECT COUNT(*) FROM episodes").fetchone()[0], 2)

    def test_query_cannot_override_current_player_or_emergency(self):
        for i in range(3):
            self.learn(f"interaction-{i}")
        raw = self.snapshot("query", CONTEXT)
        active = self.run_tick(raw)
        self.assertEqual(active["listener_action"], "YIELD_TO_PLAYER")
        self.assertEqual(active["player_learning"]["reason"], "PLAYER_OR_QUEUE_FIRST")
        raw = self.snapshot("query", CONTEXT, queue=["play chess"])
        self.assertEqual(self.run_tick(raw, IDLE)["player_learning"]["reason"], "PLAYER_OR_QUEUE_FIRST")
        raw = self.snapshot("query", CONTEXT)
        raw["needs"]["hunger"] = 0.25
        self.assertEqual(self.run_tick(raw, IDLE)["player_learning"]["reason"], "URGENT_NEEDS_FIRST")

    def test_instance_change_or_unattributed_intervening_action_breaks_episode(self):
        self.run_tick(self.choice("player-choice"))
        restarted = PresenceProbe(True, True, last_input_age_ms=0, foreground_process_id=102)
        self.assertEqual(self.run_tick(self.outcome("player-choice"), restarted)["player_learning"]["reason"],
                         "NO_MATCHING_PLAYER_CHOICE")
        self.run_tick(self.choice("another-player-choice"))
        agent = self.choice("agent-choice")
        agent["player_learning"]["owner"] = "HOST"
        self.assertEqual(self.run_tick(agent)["player_learning"]["reason"], "PLAYER_CHOICE_UNPROVEN")
        self.assertEqual(self.run_tick(self.outcome("another-player-choice"))["player_learning"]["reason"],
                         "NO_MATCHING_PLAYER_CHOICE")

    def test_contextual_replay_differs_from_one_global_choice(self):
        # Train on two contrasting contexts. The held-out frame is evaluated
        # without recording its result. Equal frequencies make the global
        # baseline unable to answer both contexts correctly.
        alternate = {**CONTEXT, "scenario": "leisure", "previous_action": "none",
                     "available_actions": ["play_hobby", "sit_and_chat_here"]}
        for i in range(3):
            self.learn(f"social-{i}")
            choice = self.snapshot("choice", {
                **alternate, "action": "play_hobby", "owner": "PLAYER", "interaction": f"hobby-{i}",
            })
            self.run_tick(choice)
            self.run_tick(self.outcome(f"hobby-{i}"))
        self.assertEqual(self.hint()["suggested_action"], "sit_and_chat_here")
        other = self.run_tick(self.snapshot("query", alternate), IDLE)["player_learning"]
        self.assertEqual(other["suggested_action"], "play_hobby")

    def test_existing_async_survey_keeps_observing_after_screen_yield(self):
        observe = AsyncMock(side_effect=[self.choice("player-choice"), self.outcome("player-choice")])
        on_receipt = AsyncMock()
        with patch("betterinstincts.host_tandem.asyncio.sleep", new=AsyncMock()):
            result = asyncio.run(run_opportunity_survey_session(
                self.session, "sim:test", observe=observe, probe=lambda _: PLAYING,
                max_turns=2, on_receipt=on_receipt,
            ))
        self.assertEqual(result["survey_receipts"], 2)
        self.assertTrue(all(event["player_yield"] for event in result["events"]))
        final = on_receipt.await_args.args[0]
        self.assertEqual(final["player_learning"]["state"], "PLAYER_OUTCOME_HELPFUL")
        self.assertFalse(final["execute_clicks"])
