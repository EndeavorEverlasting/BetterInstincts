"""Opt-in long-lived semantic learning sidecar, no autonomous training."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from betterinstincts.host_listener import (
    activate, tick, observe_behavior_review, HostListenerError,
)
from betterinstincts.player_presence import PresenceProbe
from betterinstincts.behavior_valence import REVIEW_SCHEMA

VERSION="1.121.361.1020"
CAP="capture:listener-review"
NEEDS={k:.9 for k in ("hunger","bladder","energy","hygiene","fun","social")}


def review(n):
    return dict(schema=REVIEW_SCHEMA,game_version=VERSION,platform="windows",
                kind="QUEUE",context="social",action_id="INSULT",
                outcome="NEGATIVE",review_ref=f"review:host{n}",
                evidence_ref=f"proof:host{n}",
                operator_reviewed=True,opt_in=True)


def observation():
    return dict(schema="betterinstincts.host-listener.observation/v1",
                needs=NEEDS,queue=[],location_kind="home",capture_ref=CAP,
                viewport={"state":"VIEWPORT_OK"},
                autonomy_observation=dict(
                    schema="betterinstincts.autonomy-moderation/v1",
                    sim_ref="sim:tim",selected_sim_ref="sim:tim",
                    goal_ref="goal:care",capture_ref=CAP,
                    observed_at_unix=__import__("time").time(),
                    queue_verified=True,selection_verified=True,
                    selection_proof_ref="proof:selected",autonomy_setting="FULL",
                    player_active=False,urgent_need=False,
                    imminent_obligation=False,goal_pending=False,
                    activity_context="social",game_version=VERSION,
                    platform="windows",queue=[
                        dict(action_id="INSULT",queue_slot_ref="slot:one",
                             sim_ref="sim:tim",capture_ref=CAP,
                             origin="SIM_AUTONOMY",origin_proof_ref="proof:auto",
                             effect="UNKNOWN")],whims=[]))


class ListenerValenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name).resolve()
        self.p1=patch("betterinstincts.host_listener.ROOT",root)
        self.p2=patch("betterinstincts.host_listener.OUTPUT",root/"dist"/"host-listener")
        self.p1.start();self.p2.start()
        self.addCleanup(self.p1.stop);self.addCleanup(self.p2.stop)
        self.sid="semantic-session"
        activate(self.sid)
        self.root=root

    def test_no_implicit_learning_and_reviewed_model_survives_ticks(self):
        probe=PresenceProbe(False,False,last_input_age_ms=20000,probe_ok=True)
        first=tick(self.sid,observation(),presence_probe=probe)
        self.assertEqual(first["host_stack"]["behavior_valence"]["model_negative"],[])
        self.assertFalse((self.root/"dist"/"host-listener"/self.sid/
                          "behavior-valence.json").exists())
        with self.assertRaisesRegex(HostListenerError,"EXPLICIT_BEHAVIOR_REVIEW"):
            observe_behavior_review(self.sid,[review(0)],
                game_version=VERSION,platform="windows")
        receipt=observe_behavior_review(self.sid,[review(i) for i in range(3)],
            game_version=VERSION,platform="windows",explicit_opt_in=True)
        self.assertEqual(receipt["reviewed_examples_total"],3)
        second=tick(self.sid,observation(),presence_probe=probe)
        self.assertEqual(second["host_stack"]["behavior_valence"]["model_negative"][0]["action_id"],
                         "INSULT")
        self.assertEqual(second["host_stack"]["behavior_valence"]["queue"]["unknown"][0][
                         "observed_valence"],"UNKNOWN")
        self.assertFalse(second["execute_clicks"])
        self.assertFalse(second["host_stack"]["behavior_valence"]["cancel_allowed"])
        third=tick(self.sid,observation(),presence_probe=probe)
        self.assertEqual(len(third["host_stack"]["behavior_valence"]["model_negative"]),1)
        with self.assertRaisesRegex(HostListenerError,"REPLAYED_REVIEW_REF"):
            observe_behavior_review(self.sid,[review(0)],
                game_version=VERSION,platform="windows",explicit_opt_in=True)
        self.assertEqual(len(json.loads((self.root/"dist"/"host-listener"/self.sid/
                           "behavior-valence.json").read_text())["seen_review_refs"]),3)

    def test_player_and_invalid_input_never_train(self):
        probe=PresenceProbe(False,False,last_input_age_ms=0,probe_ok=True)
        r=tick(self.sid,observation(),presence_probe=probe)
        self.assertEqual(r["listener_action"],"YIELD_TO_PLAYER")
        self.assertNotIn("host_stack",r)
        with self.assertRaises(HostListenerError):
            observe_behavior_review(self.sid,[review(0)|{"operator_reviewed":False}],
                game_version=VERSION,platform="windows",explicit_opt_in=True)
        self.assertFalse((self.root/"dist"/"host-listener"/self.sid/
                          "behavior-valence.json").exists())


if __name__=="__main__": unittest.main()
