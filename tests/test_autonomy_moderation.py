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

    def test_harm_already_occurred_has_distinct_repair_proposal(self):
        outcome = dict(effect="RELATIONSHIP_HARM",origin="SIM_AUTONOMY",
                       outcome_ref="outcome:insult",target_ref="sim:alex",
                       effect_proof_ref="proof:relationship",origin_proof_ref="proof:auto",
                       sim_ref="sim:tim",capture_ref=CAP)
        repair = dict(effect="RELATIONSHIP_HARM",action_id="APOLOGIZE",
                      target_ref="sim:alex",menu_observation_ref="menu:apology",
                      sim_ref="sim:tim",capture_ref=CAP,available=True)
        r = self.call(sample(observed_harm_outcomes=[outcome],
                             observed_repair_actions=[repair],repair_policy_opt_in=True))
        self.assertEqual(r["state"], "NEGATIVE_EFFECT_REPAIR_CANDIDATE")
        self.assertEqual(r["repair_candidate"]["action_id"], "APOLOGIZE")
        self.assertTrue(r["repair_candidate"]["outcome_not_reversed_by_proposal"])
        self.assertFalse(r["execute_allowed"])
        self.assertFalse(r["cancel_allowed"])
        self.assertIsNone(r["cancel_candidate"])
        r = self.call(sample(observed_harm_outcomes=[outcome],
                             observed_repair_actions=[repair],repair_policy_opt_in=False))
        self.assertEqual(r["state"], "HARM_REPAIR_REVIEW_OPT_IN_REQUIRED")
        for change in [dict(effect_proof_ref=None), dict(origin="PLAYER"),
                       dict(target_ref="sim:someone-else")]:
            with self.subTest(change=change):
                self.assertIsNone(self.call(sample(
                    observed_harm_outcomes=[{**outcome,**change}],
                    observed_repair_actions=[repair],
                    repair_policy_opt_in=True))["repair_candidate"])

    def test_wrong_sim_old_capture_and_bad_input(self):
        r=self.call(sample(queue=[action(sim_ref="sim:alex")]))
        self.assertEqual(r["state"],"REOBSERVE_QUEUE")
        r=self.call(sample(whims=[whim(capture_ref="old")]))
        self.assertEqual(r["state"],"REOBSERVE_WHIMS")
        for obs in [sample(queue="bad"),sample(autonomy_setting="AUTO"),
                    sample(queue=[action(effect="INVENTED")])]:
            with self.subTest(obs=obs),self.assertRaises(AutonomyModerationError):
                self.call(obs)


class AutonomyHostIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.needs = dict(hunger=.9,bladder=.9,energy=.9,hygiene=.9,fun=.9,social=.9)

    def test_general_host_exposes_harmful_action_candidate_without_cancel(self):
        from betterinstincts.host_stack import evaluate_turn
        r = evaluate_turn(self.needs,autonomy_observation=sample(queue=[action()]),
                          capture_ref=CAP,location_kind="home",queue=[],
                          viewport={"state":"VIEWPORT_OK"})
        self.assertEqual(r["autonomy_moderation"]["state"],
                         "HARMFUL_AUTONOMOUS_ACTION_CANDIDATE")
        self.assertFalse(r["autonomy_moderation"]["cancel_allowed"])
        self.assertFalse(r["autonomy_moderation"]["execute_allowed"])
        p = evaluate_turn(self.needs,autonomy_observation=sample(queue=[action()]),
                          capture_ref=CAP,location_kind="home",queue=[],
                          player_directed=True,viewport={"state":"VIEWPORT_OK"})
        self.assertEqual(p["autonomy_moderation"]["state"],"PLAYER_FIRST")
        self.assertEqual(p["next_gate"],"RESPECT_PLAYER_OR_BUSY_STATE")
        off = evaluate_turn(self.needs,autonomy_observation=sample(queue=[action()]),
                           capture_ref=CAP,location_kind="home",queue=[],
                           sim_absent=True,viewport={"state":"VIEWPORT_OK"})
        self.assertEqual(off["autonomy_moderation"]["state"],"SIM_NOT_VERIFIED_SELECTED")
        self.assertIsNone(evaluate_turn(self.needs)["autonomy_moderation"])

    def test_one_existing_listener_ticks_global_policy_without_game_effect(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from betterinstincts.host_listener import activate,tick,HostListenerError
        from betterinstincts.player_presence import PresenceProbe
        with tempfile.TemporaryDirectory() as temp, patch(
            "betterinstincts.host_listener.ROOT",Path(temp).resolve()
        ),patch("betterinstincts.host_listener.OUTPUT",
                 Path(temp).resolve()/"dist/host-listener"):
            activate("autonomy-policy-test")
            obs=dict(schema="betterinstincts.host-listener.observation/v1",
                     needs=self.needs,queue=[],location_kind="home",
                     capture_ref=CAP,viewport={"state":"VIEWPORT_OK"},
                     autonomy_observation=sample(queue=[action()]))
            r=tick("autonomy-policy-test",obs,presence_probe=PresenceProbe(
                False,False,last_input_age_ms=20000,probe_ok=True))
            self.assertEqual(r["host_stack"]["autonomy_moderation"]["state"],
                             "HARMFUL_AUTONOMOUS_ACTION_CANDIDATE")
            self.assertFalse(r["execute_clicks"])
            with self.assertRaisesRegex(HostListenerError,"OBSERVATION_AUTONOMY_POLICY_INVALID"):
                tick("autonomy-policy-test",{**obs,"autonomy_observation":[]})


class NativeHouseholdAutonomyTests(unittest.TestCase):
    """P82 falsifiers for EA-native policy; no UI or installed-game effects."""

    def household(self, sims=None, **overrides):
        data = {
            "schema": "betterinstincts.native-household-autonomy/v1",
            "household_ref": "house:random", "game_build": "1.118.0",
            "capture_ref": CAP, "observed_at_unix": NOW,
            "player_active": False,
            "sims": sims if sims is not None else [self.sim("sim:1")],
        }
        data.update(overrides)
        return data

    def yield_row(self, **overrides):
        row = {"action_id": "work", "yield_proof_ref": "proof:measured",
               "yield_by_domain": {"career": .9}}
        row.update(overrides)
        return row

    def sim(self, sim_id, **overrides):
        row = {
            "sim_ref": sim_id, "capture_ref": CAP,
            "queue_verified": True, "player_owned": False,
            "player_command_present": False, "policy_opt_in": True,
            "active_goal": self.yield_row(active=True),
            "queue": [{
                "action_id": "idle", "queue_slot_ref": "slot:1",
                "origin": "SIM_AUTONOMY", "origin_proof_ref": "proof:autonomy",
                "effect_proof_ref": "proof:effect", "yield_proof_ref": "proof:zero",
                "yield_by_domain": {"fun": 0},
                "interrupts_goal": True,
            }],
            "available_actions": [],
        }
        row.update(overrides)
        return row

    def evaluate(self, obs):
        from betterinstincts.autonomy_moderation import evaluate_native_household_autonomy
        return evaluate_native_household_autonomy(obs, now=NOW)

    def test_all_household_sims_independent_of_active_portrait(self):
        obs = self.household(sims=[self.sim("sim:one"), self.sim("sim:two"),
                                   self.sim("sim:three", player_command_present=True)])
        obs["selected_sim_ref"] = "sim:three"
        decisions = self.evaluate(obs)["decisions"]
        self.assertEqual([x["sim_ref"] for x in decisions],
                         ["sim:one", "sim:two", "sim:three"])
        self.assertEqual([x["state"] for x in decisions], [
            "NATIVE_SUPPRESSION_CANDIDATE", "NATIVE_SUPPRESSION_CANDIDATE",
            "PLAYER_OR_UNKNOWN_OWNER_PROTECTED"])
        self.assertEqual(decisions[0]["replacement_candidate"]["kind"],
                         "RESUME_ATTESTED_GOAL")
        self.assertFalse(self.evaluate(obs)["cancel_allowed"])
        self.assertFalse(self.evaluate(obs)["desktop_input_allowed"])

    def test_social_and_fun_yield_stays_when_no_goal_derailment(self):
        leisure = self.sim("sim:one", active_goal=None)
        leisure["queue"][0]["yield_by_domain"] = {"fun": .2, "social": .3}
        r = self.evaluate(self.household(sims=[leisure]))
        self.assertIsNone(r["decisions"][0]["suppress_candidate"])
        self.assertEqual(r["decisions"][0]["state"], "PRESERVE_QUEUE_OR_YIELD")

    def test_unproductive_autonomy_can_prefer_verified_native_affordance(self):
        idle = self.sim("sim:one", active_goal=None, available_actions=[
            self.yield_row(action_id="eat", yield_by_domain={"hunger": .7},
                           native_affordance_verified=True, available=True)])
        decision = self.evaluate(self.household(sims=[idle]))["decisions"][0]
        self.assertEqual(decision["state"], "NATIVE_SUPPRESSION_CANDIDATE")
        self.assertEqual(decision["replacement_candidate"]["action_id"], "eat")
        self.assertEqual(decision["replacement_candidate"]["kind"],
                         "NATIVE_AFFORDANCE_CANDIDATE")

    def test_bad_provenance_missing_optin_and_stale_queue_fail_closed(self):
        cases = [
            (self.sim("sim:1", player_owned=None), "PLAYER_OR_UNKNOWN_OWNER_PROTECTED"),
            (self.sim("sim:1", player_command_present=True), "PLAYER_OR_UNKNOWN_OWNER_PROTECTED"),
            (self.sim("sim:1", policy_opt_in=False), "OPT_IN_REQUIRED"),
            (self.sim("sim:1", queue_verified=False), "QUEUE_NOT_VERIFIED"),
            (self.sim("sim:1", active_goal={"action_id": "work", "active": True}),
             "GOAL_EVIDENCE_UNKNOWN"),
        ]
        for sim, state in cases:
            with self.subTest(state=state):
                self.assertEqual(self.evaluate(self.household(sims=[sim]))["decisions"][0]["state"], state)
        stale = self.evaluate(self.household(observed_at_unix=NOW-181))
        self.assertEqual(stale["decisions"][0]["state"], "REOBSERVE_SIM")
        self.assertTrue(all(not stale[x] for x in ("cancel_allowed", "enqueue_allowed")))

    def test_player_queue_blocks_other_autonomous_entry(self):
        sim = self.sim("sim:1")
        sim["queue"].insert(0, dict(sim["queue"][0], origin="PLAYER",
                                    queue_slot_ref="slot:player"))
        r = self.evaluate(self.household(sims=[sim]))
        self.assertEqual(r["decisions"][0]["state"], "PLAYER_QUEUE_PROTECTED")
        self.assertIsNone(r["decisions"][0]["suppress_candidate"])


    def test_unknown_or_host_queue_blocks_autonomy_mutation(self):
        for origin in ("UNKNOWN", "HOST", "PLAYER"):
            sim = self.sim("sim:1")
            sim["queue"].insert(0, dict(sim["queue"][0], origin=origin,
                                        queue_slot_ref="slot:other"))
            with self.subTest(origin=origin):
                decision = self.evaluate(self.household(sims=[sim]))["decisions"][0]
                self.assertEqual(decision["state"], "PLAYER_QUEUE_PROTECTED")
                self.assertIsNone(decision["suppress_candidate"])

    def test_urgent_needs_and_obligation_do_not_get_trampled(self):
        for field in ("urgent_need", "imminent_obligation"):
            sim = self.sim("sim:1", **{field: True})
            decision = self.evaluate(self.household(sims=[sim]))["decisions"][0]
            self.assertEqual(decision["state"], "URGENT_NEED_OR_OBLIGATION_PROTECTED")
        with self.assertRaisesRegex(AutonomyModerationError, "NATIVE_AUTONOMY_IDENTITY_INVALID"):
            self.evaluate(self.household(game_build="UNKNOWN"))

    def test_unverified_autonomous_yield_and_duplicate_id_rejected(self):
        sim = self.sim("sim:1")
        sim["queue"][0]["yield_proof_ref"] = None
        self.assertEqual(self.evaluate(self.household(sims=[sim]))["decisions"][0]["state"],
                         "ACTION_YIELD_UNKNOWN")
        with self.assertRaisesRegex(AutonomyModerationError, "NATIVE_DUPLICATE_SIM"):
            self.evaluate(self.household(sims=[sim, sim]))

    def test_positive_leisure_can_still_be_less_than_proven_protected_goal(self):
        sim = self.sim("sim:1")
        sim["queue"][0]["yield_by_domain"] = {"fun": .1}
        d = self.evaluate(self.household(sims=[sim]))["decisions"][0]
        self.assertEqual(d["state"], "NATIVE_SUPPRESSION_CANDIDATE")
        # But never for a non-interrupting interaction.
        sim["queue"][0]["interrupts_goal"] = False
        self.assertEqual(self.evaluate(self.household(sims=[sim]))["decisions"][0]["state"],
                         "PRESERVE_QUEUE_OR_YIELD")


if __name__=="__main__": unittest.main()
