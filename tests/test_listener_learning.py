"""Existing listener remains player-first when a reviewed learner is attached."""
import unittest
import uuid

from betterinstincts.host_listener import HostListenerError, activate, deactivate, tick
from betterinstincts.player_presence import PresenceProbe
from betterinstincts.judgment_learning import EXAMPLE_SCHEMA, QUERY_SCHEMA, learn

VERSION = "1.121.361.1020"
CONTEXT = {
    "scenario": "event_social", "need_state": "stable",
    "scene": "event", "previous_action": "socialize", "style": "social",
}
NEEDS = {k: 0.8 for k in ("hunger","bladder","energy","hygiene","fun","social")}
OBS = {
    "schema": "betterinstincts.host-listener.observation/v1",
    "needs": NEEDS, "queue": ["read"], "location_kind": "home",
    "objects_on_current_lot": True, "capture_ref": "capture:listener_safe",
    "viewport": {"state": "VIEWPORT_OK"},
}
QUERY = {
    "schema": QUERY_SCHEMA, "game_version": VERSION, "platform": "windows",
    "context": CONTEXT, "available_actions": ["sit_and_chat_here","socialize"],
    "player_directed": False, "player_active": False, "scene_verified": True,
}


def _model():
    return learn([{
        "schema": EXAMPLE_SCHEMA, "game_version": VERSION,
        "platform": "windows", "context": CONTEXT,
        "action": "sit_and_chat_here", "outcome": "helpful",
        "operator_reviewed": True, "opt_in": True,
        "observation_ref": "capture:example_" + str(i),
    } for i in range(3)], game_version=VERSION, platform="windows")


class ListenerLearningTests(unittest.TestCase):
    def setUp(self):
        self.sid = "test_learn_" + uuid.uuid4().hex[:16]
        activate(self.sid)
        self.model = _model()

    def tearDown(self):
        deactivate(self.sid)

    def test_opt_in_advisory_on_safe_observation(self):
        receipt = tick(self.sid, OBS,
                       presence_probe=PresenceProbe(False, False, last_input_age_ms=19000),
                       learning_model=self.model, learning_query=QUERY)
        self.assertEqual(receipt["learning_hint"]["state"], "ADVISORY_ONLY")
        self.assertEqual(receipt["learning_hint"]["suggested_action"], "sit_and_chat_here")
        self.assertFalse(receipt["learning_hint"]["execute_clicks"])
        self.assertFalse(receipt["execute_clicks"])

    def test_active_player_takes_precedence_before_learning(self):
        receipt = tick(self.sid, OBS,
                       presence_probe=PresenceProbe(True, True, last_input_age_ms=0),
                       learning_model=self.model, learning_query=QUERY)
        self.assertEqual(receipt["listener_action"], "YIELD_TO_PLAYER")
        self.assertNotIn("learning_hint", receipt)
        self.assertFalse(receipt["execute_clicks"])

    def test_unverified_viewport_abstains_even_if_query_claims_safe(self):
        receipt = tick(self.sid, {**OBS, "viewport": {"state": "VIEWPORT_BLACK"}},
                       presence_probe=PresenceProbe(False, False, last_input_age_ms=19000),
                       learning_model=self.model, learning_query=QUERY)
        self.assertEqual(receipt["learning_hint"]["state"], "ABSTAIN")
        self.assertEqual(receipt["learning_hint"]["reason"], "SCENE_UNVERIFIED")

    def test_partial_explicit_learning_input_is_rejected(self):
        with self.assertRaisesRegex(HostListenerError, "LEARNING_MODEL_AND_QUERY_REQUIRED"):
            tick(self.sid, OBS,
                 presence_probe=PresenceProbe(False, False, last_input_age_ms=19000),
                 learning_model=self.model)


if __name__ == "__main__":
    unittest.main()
