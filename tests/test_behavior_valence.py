"""P82: reviewed posterior learning never becomes game-action authority."""
import time
import unittest

from betterinstincts.behavior_valence import (
    BehaviorValenceError, MODEL_SCHEMA, REVIEW_SCHEMA, empty_model,
    learn_reviewed, evaluate_behavior_valence, validate_model,
    prequential_evaluate,
)
from betterinstincts.host_stack import evaluate_turn

PATCH = "1.121.361.1020"
CAP = "capture:valence"
NOW = time.time()
NEEDS = {k:.9 for k in ("hunger","bladder","energy","hygiene","fun","social")}


def review(n,*,kind="QUEUE",action_id="INSULT",context="social",
           outcome="NEGATIVE",**changes):
    row=dict(schema=REVIEW_SCHEMA,game_version=PATCH,platform="windows",
             kind=kind,action_id=action_id,context=context,outcome=outcome,
             operator_reviewed=True,opt_in=True,
             review_ref=f"review:{n}",evidence_ref=f"proof:outcome{n}")
    row.update(changes)
    return row


def sample(**changes):
    row=dict(schema="betterinstincts.autonomy-moderation/v1",
             sim_ref="sim:tim",selected_sim_ref="sim:tim",
             goal_ref="goal:garden",capture_ref=CAP,observed_at_unix=NOW,
             selection_verified=True,selection_proof_ref="proof:selected",
             queue_verified=True,player_active=False,urgent_need=False,
             imminent_obligation=False,autonomy_setting="FULL",
             disable_selected_sim_autonomy=False,goal_pending=False,
             pin_policy_opt_in=True,activity_context="social",
             game_version=PATCH,platform="windows",queue=[],whims=[])
    row.update(changes)
    return row


def action(slot="slot:1",**kw):
    row=dict(action_id="INSULT",queue_slot_ref=slot,sim_ref="sim:tim",
             capture_ref=CAP,origin="SIM_AUTONOMY",origin_proof_ref="proof:auto",
             effect="RELATIONSHIP_HARM",effect_proof_ref="proof:harm")
    row.update(kw)
    return row


def whim(identifier="whim:one",**kw):
    row=dict(whim_ref=identifier,action_id="GARDEN",
             capture_ref=CAP,sim_ref="sim:tim",
             benefit="BENEFICIAL",benefit_proof_ref="proof:benefit",
             pinned=False,available=True)
    row.update(kw)
    return row


class ValenceTests(unittest.TestCase):
    def call(self,obs,model=None):
        return evaluate_behavior_valence(obs,capture_ref=CAP,model=model,now=NOW)

    def test_all_streams_and_unknown_bucket_separate(self):
        report=self.call(sample(queue=[
            action(),action("slot:2",action_id="COOK",effect="BENEFICIAL"),
            action("slot:3",action_id="WAIT",effect="NEUTRAL"),
            action("slot:4",action_id="CHAT",effect="UNKNOWN",effect_proof_ref=None)],
            whims=[whim(),whim("whim:two",action_id="INSULT",
                              benefit="HARMFUL",benefit_proof_ref="proof:whimrisk"),
                   whim("whim:three",action_id="WAIT",
                        benefit_proof_ref=None)]))
        self.assertEqual([len(report["queue"][x]) for x in
                          ("positive","negative","neutral","unknown")],[1,1,1,1])
        self.assertEqual([len(report["whims"][x]) for x in
                          ("positive","negative","neutral","unknown")],[1,1,0,1])
        self.assertEqual(report["pin_candidate"]["whim_ref"],"whim:one")
        self.assertEqual(report["pin_candidate"]["evidence_kind"],"OBSERVED_POSITIVE")
        self.assertFalse(report["execute_allowed"])
        self.assertFalse(report["cancel_allowed"])
        self.assertNotIn("INSULT",[r["action_id"] for r in report["whims"]["positive"]])

    def test_supervised_learning_is_incremental_conservative_and_patch_qualified(self):
        model=learn_reviewed([review(i) for i in range(3)],
                             game_version=PATCH,platform="windows")
        self.assertEqual(model["schema"],MODEL_SCHEMA)
        self.assertEqual(len(model["seen_review_refs"]),3)
        r=self.call(sample(queue=[action(effect="UNKNOWN",
                                        effect_proof_ref=None)]),model=model)
        self.assertEqual(len(r["queue"]["unknown"]),1)
        self.assertEqual(r["model_negative"][0]["action_id"],"INSULT")
        self.assertIsNone(r["pin_candidate"])
        self.assertEqual(r["queue"]["unknown"][0]["learned_advice"]["valence"],"NEGATIVE")
        self.assertFalse(r["cancel_allowed"])
        r2=self.call(sample(queue=[action(effect="UNKNOWN",
                                        effect_proof_ref=None)],
                            game_version="1.999.999.9999"),model=model)
        self.assertEqual(r2["model_negative"],[])
        with self.assertRaisesRegex(BehaviorValenceError,"REPLAYED"):
            learn_reviewed([review(0)],game_version=PATCH,platform="windows",prior=model)
        plus=learn_reviewed([review(3,kind="WHIM",action_id="GARDEN",
                                    outcome="POSITIVE")],
                            game_version=PATCH,platform="windows",prior=model)
        self.assertEqual(len(plus["seen_review_refs"]),4)

    def test_wish_pinning_requires_proven_positive_and_idle_goal(self):
        for kwargs in [
            dict(goal_pending=True),dict(pin_policy_opt_in=False),
            dict(whims=[whim(pinned=True)]),
            dict(whims=[whim(benefit_proof_ref=None)]),
            dict(whims=[whim(available=False)]),
        ]:
            with self.subTest(kwargs=kwargs):
                obs=sample(whims=[whim()],**{k:v for k,v in kwargs.items()
                                              if k!="whims"})
                if "whims" in kwargs: obs["whims"]=kwargs["whims"]
                self.assertIsNone(self.call(obs)["pin_candidate"])

    def test_player_offscreen_stale_protect_and_no_learn_from_passive_observation(self):
        for obs,gate in [
            (sample(player_active=True,queue=[action()]),"PLAYER_FIRST"),
            (sample(selected_sim_ref="sim:alex",queue=[action()]),"SIM_NOT_VERIFIED_SELECTED"),
            (sample(queue_verified=False,queue=[action()]),"REOBSERVE_QUEUE"),
            (sample(observed_at_unix=NOW-181,queue=[action()]),"REOBSERVE_QUEUE"),
            (sample(urgent_need=True,queue=[action()]),"SURVIVAL_OR_OBLIGATION_FIRST"),
        ]:
            with self.subTest(gate=gate):
                r=self.call(obs)
                self.assertEqual(r["gate"],gate)
                self.assertEqual(r["queue"]["negative"],[])
        r=self.call(sample(whims=[whim(action_id=None)]))
        self.assertEqual(len(r["whims"]["positive"]),1)
        self.assertEqual(r["whims"]["positive"][0]["action_id"],"unknown_whim_action")
        self.assertIsNone(r["whims"]["positive"][0]["learned_advice"]["probability_positive"])

    def test_strict_consent_and_replay_model_validation(self):
        for bad in [
            review(1,operator_reviewed=False),review(2,opt_in=False),
            review(3,evidence_ref=None),review(4,context="otherworldly"),
            review(5,game_version="unknown"),
        ]:
            with self.subTest(bad=bad),self.assertRaises(BehaviorValenceError):
                learn_reviewed([bad],game_version=PATCH,platform="windows")
        with self.assertRaises(BehaviorValenceError):
            learn_reviewed([review(1)]*2,game_version=PATCH,platform="windows")
        with self.assertRaises(BehaviorValenceError):
            learn_reviewed([review(1)],game_version="unknown",platform="windows")
        with self.assertRaises(BehaviorValenceError):
            validate_model({"schema":MODEL_SCHEMA,"game_version":PATCH,
                            "platform":"windows","counts":[],"seen_review_refs":[1]})

    def test_prequential_uses_before_training_and_reports_separate_quality(self):
        examples=[review(i) for i in range(5)]
        r=prequential_evaluate(examples,game_version=PATCH,platform="windows")
        self.assertEqual(r["reviewed_examples"],5)
        self.assertGreaterEqual(r["predictions_issued"],1)
        self.assertEqual(r["prediction_precision"],1.0)
        self.assertEqual(r["negative_precision"],1.0)
        self.assertIsNone(r["positive_precision"])
        empty=prequential_evaluate([review(11)],game_version=PATCH,platform="windows")
        self.assertEqual(empty["predictions_issued"],0)
        self.assertIsNone(empty["prediction_precision"])

    def test_host_uses_read_only_valence_without_preempting_need_or_player(self):
        model=learn_reviewed([review(i) for i in range(3)],
                             game_version=PATCH,platform="windows")
        r=evaluate_turn(NEEDS,autonomy_observation=sample(
            queue=[action()]),behavior_model=model,capture_ref=CAP,
            viewport={"state":"VIEWPORT_OK"},location_kind="home")
        self.assertEqual(len(r["behavior_valence"]["queue"]["negative"]),1)
        self.assertEqual(r["autonomy_moderation"]["sim_ref"],"sim:tim")
        self.assertFalse(r["behavior_valence"]["execute_allowed"])
        manual=evaluate_turn(NEEDS,autonomy_observation=sample(
            queue=[action()]),behavior_model=model,capture_ref=CAP,
            player_directed=True,viewport={"state":"VIEWPORT_OK"},location_kind="home")
        self.assertEqual(manual["behavior_valence"]["gate"],"PLAYER_FIRST")
        self.assertEqual(manual["next_gate"],"RESPECT_PLAYER_OR_BUSY_STATE")


if __name__=="__main__": unittest.main()
