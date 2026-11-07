"""Semantic coordinator P95 success/failure stacks; no Sims or filesystem access."""
import copy
import unittest

from betterinstincts.domain_cascade import poll_cascade
from betterinstincts.semantic_advisory import SemanticAdvisoryError, compose_semantic_turn


class SemanticAdvisoryTests(unittest.TestCase):
    def setUp(self):
        self.cascade = {
            "schema": "betterinstincts.domain-cascade-result/v1",
            "state": "DOMAIN_CASCADE_POLLED",
            "capture_ref": "synthetic:semantic-test",
        }
        self.goals = [
            {"id": "earn-rent", "domain": "economy.experimental", "priority": 8,
             "resource_claims": ["sim:A:attention"], "mechanic_path": "native"},
            {"id": "eat", "domain": "needs", "priority": 12,
             "resource_claims": ["sim:A:attention", "object:fridge"], "mechanic_path": "native"},
            {"id": "call-police", "domain": "contingency.custom", "priority": 1,
             "resource_claims": ["sim:A:attention"], "mechanic_path": "native"},
        ]

    def test_offline_call_stack_consumes_existing_cascade(self):
        actual = poll_cascade({
            "bladder": .8, "hunger": .2, "energy": .7,
            "hygiene": .8, "fun": .8, "social": .8,
        }, capture_ref="synthetic:actual-domain-cascade")
        before = copy.deepcopy(actual)
        result = compose_semantic_turn(actual, self.goals)
        self.assertEqual(actual, before)
        self.assertEqual(result["selected_goal_id"], "eat")
        self.assertIn("economy.experimental", result["evaluated_domains"])
        self.assertIn("earn-rent", result["resource_conflicts"])
        self.assertIsNone(result["control_permit"])

    def test_observed_urgent_contingency_preempts_and_keeps_prior_intent(self):
        event = {
            "goal_id": "call-police", "urgency": 90,
            "deadline_ticks": 2, "observation_ref": "synthetic:verified-cue",
            "evidence_state": "LOCAL_OBSERVED",
        }
        result = compose_semantic_turn(
            self.cascade, self.goals, contingencies=[event],
            previous={"selected_goal_id": "earn-rent"},
        )
        self.assertEqual(result["selected_goal_id"], "call-police")
        self.assertTrue(result["contingency_preemption"])
        self.assertEqual(result["suspended"][0]["goal_id"], "earn-rent")
        self.assertTrue(result["suspended"][0]["revalidation_required"])

    def test_unverified_or_expired_event_cannot_force_preemption(self):
        for event in [
            {"goal_id": "call-police", "urgency": 999,
             "observation_ref": "synthetic:x", "evidence_state": "HYPOTHESIS"},
            {"goal_id": "call-police", "urgency": 999,
             "observation_ref": "synthetic:x", "evidence_state": "LOCAL_OBSERVED",
             "deadline_ticks": 0},
            {"goal_id": "call-police", "urgency": 999,
             "observation_ref": "", "evidence_state": "LOCAL_OBSERVED"},
        ]:
            result = compose_semantic_turn(
                self.cascade, self.goals, contingencies=[event],
                previous={"selected_goal_id": "eat"},
            )
            self.assertEqual(result["selected_goal_id"], "eat")
            self.assertFalse(result["contingency_preemption"])

    def test_player_override_is_a_yield_not_a_better_rank(self):
        result = compose_semantic_turn(
            self.cascade, self.goals, player_directed=True,
            previous={"selected_goal_id": "earn-rent"},
            contingencies=[{"goal_id": "call-police", "urgency": 1000,
                           "observation_ref": "synthetic:cue",
                           "evidence_state": "LOCAL_OBSERVED"}],
        )
        self.assertEqual(result["state"], "YIELD_TO_PLAYER")
        self.assertIsNone(result["selected_goal_id"])
        self.assertIsNone(result["control_permit"])
        self.assertEqual(result["suspended"][0]["goal_id"], "earn-rent")
        self.assertEqual(result["suspended"][0]["reason"], "PLAYER_ACTIVITY_YIELD")
        yielded = dict(self.cascade, state="DOMAIN_CASCADE_YIELDED")
        self.assertEqual(compose_semantic_turn(yielded, self.goals)["state"], "YIELD_TO_PLAYER")

    def test_contingency_does_not_override_stronger_observed_priority(self):
        goals = [dict(self.goals[1], priority=100), self.goals[2]]
        event = {"goal_id": "call-police", "urgency": 90,
                 "observation_ref": "synthetic:event", "evidence_state": "LOCAL_OBSERVED"}
        result = compose_semantic_turn(self.cascade, goals, contingencies=[event],
                                       previous={"selected_goal_id": "eat"})
        self.assertEqual(result["selected_goal_id"], "eat")
        self.assertFalse(result["contingency_preemption"])

    def test_intent_survives_no_ready_goals(self):
        result = compose_semantic_turn(self.cascade, [], previous={"selected_goal_id": "earn-rent"})
        self.assertEqual(result["state"], "NO_READY_GOALS")
        self.assertEqual(result["suspended"][0]["goal_id"], "earn-rent")

    def test_future_domains_and_extensions_do_not_require_ontology_rewrite(self):
        extra = {"id": "community-market", "domain": "world.economy.v3", "priority": 50,
                 "resource_claims": [], "mechanic_path": "extension"}
        result = compose_semantic_turn(self.cascade, [extra])
        self.assertEqual(result["selected_domain"], "world.economy.v3")
        self.assertEqual(result["selected_mechanic_path"], "extension")
        self.assertEqual(result["state"], "ADVISORY_ONLY")

    def test_resumption_candidates_revalidate_without_replaying_actions(self):
        prior = {"selected_goal_id": "call-police", "suspended": [
            {"goal_id": "earn-rent", "reason": "OBSERVED_CONTINGENCY_PREEMPTION"}]}
        result = compose_semantic_turn(self.cascade, self.goals, previous=prior)
        self.assertIn("earn-rent", result["resume_candidates"])
        self.assertTrue(result["suspended"][0]["revalidation_required"])

    def test_bad_evidence_and_duplicate_thread_fail(self):
        with self.assertRaisesRegex(SemanticAdvisoryError, "CASCADE_RECEIPT_REQUIRED"):
            compose_semantic_turn({}, self.goals)
        with self.assertRaisesRegex(SemanticAdvisoryError, "DUPLICATE_GOAL_THREAD"):
            compose_semantic_turn(self.cascade, self.goals + [self.goals[0]])
        with self.assertRaisesRegex(SemanticAdvisoryError, "GOAL_PRIORITY_INVALID"):
            compose_semantic_turn(self.cascade, [{"id": "bad", "domain": "any", "priority": float("nan")}])

    def test_no_ready_goals_is_not_authority(self):
        result = compose_semantic_turn(self.cascade, [dict(self.goals[0], status="SUSPENDED")])
        self.assertEqual(result["state"], "NO_READY_GOALS")
        self.assertIsNone(result["control_permit"])


if __name__ == "__main__":
    unittest.main()
