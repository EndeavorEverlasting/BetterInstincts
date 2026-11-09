import time
import unittest
from betterinstincts.autonomy_moderation import (
    AutonomyModerationError, evaluate_autonomy_moderation,
)

NOW=time.time()
CAP="capture:autonomy"


def sample(**kw):
    row=dict(
        schema="betterinstincts.autonomy-moderation/v1",
        sim_ref="sim:tim",goal_ref="goal:garden",capture_ref=CAP,
        observed_at_unix=NOW,queue_verified=True,selected_sim_ref="sim:tim",
        selection_verified=True,selection_proof_ref="proof:portrait",
        autonomy_setting="FULL",disable_selected_sim_autonomy=False,
        player_active=False,urgent_need=False,imminent_obligation=False,
        goal_pending=True,cancel_policy_opt_in=True,queue=[],whims=[])
    row.update(kw)
    return row


def action(**kw):
    row=dict(action_id="INSULT",queue_slot_ref="slot:1",sim_ref="sim:tim",
        capture_ref=CAP,origin="SIM_AUTONOMY",
        origin_proof_ref="proof:auto",effect="RELATIONSHIP_HARM",
        effect_proof_ref="proof:relationship")
    row.update(kw)
    return row


def whim(**kw):
    row=dict(whim_ref="whim:gardening",action_id="GARDEN",
        capture_ref=CAP,sim_ref="sim:tim",benefit="BENEFICIAL",
        benefit_proof_ref="proof:benefit",available=True)
    row.update(kw)
    return row


class AutonomyModerationTests(unittest.TestCase):
    def call(self, obs):
        return evaluate_autonomy_moderation(obs,capture_ref=CAP,now=NOW)

    def test_harmful_autonomy_yields_exact_single_candidate_no_input_permit(self):
        r=self.call(sample(queue=[action(),action(queue_slot_ref="slot:2")]))
        self.assertEqual(r["state"],"HARMFUL_AUTONOMOUS_ACTION_CANDIDATE")
        self.assertEqual(r["cancel_candidate"]["queue_slot_ref"],"slot:1")
        self.assertFalse(r["cancel_allowed"])
        self.assertFalse(r["execute_allowed"])
        self.assertFalse(r["settings_change_allowed"])

    def test_player_queue_and_goal_are_protected(self):
        for obs in [
            sample(queue=[action(origin="PLAYER")]),
            sample(queue=[action(action_id="goal:garden")]),
            sample(queue=[action(protect_goal=True)]),
            sample(queue=[action(origin="UNKNOWN")]),
            sample(queue=[action(effect="NEUTRAL")]),
            sample(queue=[action(effect_proof_ref=None)]),
            sample(queue=[action(origin_proof_ref=None)]),
        ]:
            with self.subTest(obs=obs):
                r=self.call(obs)
                self.assertIsNone(r["cancel_candidate"])

    def test_unselected_active_player_need_off_autonomy_and_optin(self):
        inputs = [
            (sample(selected_sim_ref="sim:alex"),"SIM_NOT_VERIFIED_SELECTED"),
            (sample(player_active=True),"PLAYER_FIRST"),
            (sample(urgent_need=True),"SURVIVAL_OR_OBLIGATION_FIRST"),
            (sample(imminent_obligation=True),"SURVIVAL_OR_OBLIGATION_FIRST"),
            (sample(queue_verified=False),"REOBSERVE_QUEUE"),
            (sample(observed_at_unix=NOW-181),"REOBSERVE_QUEUE"),
            (sample(autonomy_setting="OFF",queue=[action()]),"AUTONOMY_SETTING_QUEUE_CONFLICT"),
            (sample(queue=[action()],cancel_policy_opt_in=False),"HARMFUL_AUTONOMY_REVIEW_OPT_IN_REQUIRED"),
        ]
        for obs,gate in inputs:
            with self.subTest(gate=gate):
                self.assertEqual(self.call(obs)["state"],gate)

    def test_positive_whim_is_nondeceptive_and_nonpreemptive(self):
        self.assertEqual(self.call(sample(
            goal_pending=False,whims=[whim()]))["state"],"POSITIVE_WHIM_QUEUE_CANDIDATE")
        self.assertIsNone(self.call(sample(
            goal_pending=True,whims=[whim()]))["positive_whim_candidate"])
        self.assertIsNone(self.call(sample(
            goal_pending=False,queue=[action(effect="NEUTRAL")],
            whims=[whim()]))["positive_whim_candidate"])
        self.assertIsNone(self.call(sample(
            goal_pending=False,whims=[whim(benefit_proof_ref=None)]))["positive_whim_candidate"])

    def test_wrong_sim_old_capture_and_bad_input(self):
        r=self.call(sample(queue=[action(sim_ref="sim:alex")]))
        self.assertEqual(r["state"],"REOBSERVE_QUEUE")
        r=self.call(sample(whims=[whim(capture_ref="old")]))
        self.assertEqual(r["state"],"REOBSERVE_WHIMS")
        for obs in [sample(queue="bad"),sample(autonomy_setting="AUTO"),
                    sample(queue=[action(effect="INVENTED")])]:
            with self.subTest(obs=obs),self.assertRaises(AutonomyModerationError):
                self.call(obs)


if __name__=="__main__": unittest.main()
