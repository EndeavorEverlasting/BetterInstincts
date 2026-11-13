"""Falsifying offline queue/duration/needs tests; no Sims or saves accessed."""
from __future__ import annotations

import copy
import math
import unittest

from betterinstincts.autonomy_moderation import (
    AutonomyModerationError, evaluate_native_household_autonomy,
)
from betterinstincts.queue_supervision import (
    QueueSupervisionError, evaluate_queue_supervision,
)

CAP, BUILD, HOUSE, NOW = "capture:queue", "build:1.120", "house:1", 1000.0
NEEDS = {name: .8 for name in ("hunger", "bladder", "energy", "hygiene", "fun", "social")}


def action(name="WRITE", slot="slot:1", state="RUNNING", **kw):
    row = {
        "action_id": name, "queue_slot_ref": slot,
        "queue_state": state, "sim_ref": "sim:one", "capture_ref": CAP,
        "origin": "SIM_AUTONOMY", "origin_proof_ref": "proof:origin",
        "protected_goal": False, "goal_proof_ref": "proof:goal",
        "semantic_key": f"semantic:{name.lower()}:target1",
        "semantic_proof_ref": "proof:semantic",
        "serve_proof_ref": "proof:need-effect", "serves_need": None,
        "yield_by_domain": {"skill": .3}, "yield_proof_ref": "proof:yield",
    }
    row.update(kw)
    return row


def activity(*, elapsed=60.0, paused=False):
    return {
        "queue_slot_ref": "slot:1", "action_id": "WRITE", "game_build": BUILD,
        "clock_basis": "ACTIVE_SIM_SECONDS", "base_seconds": 120.0,
        "base_proof_ref": "proof:base", "elapsed_seconds": elapsed,
        "elapsed_proof_ref": "proof:clock", "paused": paused,
        "progress_state": "ADVANCING", "progress_proof_ref": "proof:progress",
        "factors": {
            "moodlet": {"multiplier": 1.5, "proof_ref": "proof:moodlet"},
            "temperament": {"multiplier": 1.0, "proof_ref": "proof:temperament"},
            "balance": {"multiplier": 1.0, "proof_ref": "proof:balance"},
            "trait": {"multiplier": .9, "proof_ref": "proof:trait"},
        },
        "completed_samples": [
            {"sample_ref": "sample:a", "action_id": "WRITE", "game_build": BUILD,
             "active_seconds": 150, "modeled_seconds": 120,
             "outcome_proof_ref": "proof:sample-a"},
            {"sample_ref": "sample:b", "action_id": "WRITE", "game_build": BUILD,
             "active_seconds": 180, "modeled_seconds": 120,
             "outcome_proof_ref": "proof:sample-b"},
        ],
    }


def observation(*, actions=None, needs=None, profile=None):
    native_sim = {
        "sim_ref": "sim:one", "capture_ref": CAP,
        "queue_verified": True, "player_command_present": False,
        "player_owned": False, "policy_opt_in": True,
        "queue": actions if actions is not None else [action()],
        "available_actions": [],
    }
    meta = {
        "sim_ref": "sim:one", "capture_ref": CAP, "queue_verified": True,
        "policy_opt_in": True, "multitasking": False,
        "needs": dict(NEEDS if needs is None else needs),
        "needs_proof_ref": "proof:needs",
        "switch_history_verified": True,
        "active_activity": activity() if profile is None else profile,
    }
    root = {
        "schema": "betterinstincts.native-household-autonomy/v1",
        "household_ref": HOUSE, "game_build": BUILD, "capture_ref": CAP,
        "observed_at_unix": NOW, "player_active": False,
        "sims": [native_sim],
        "queue_supervision": {
            "schema": "betterinstincts.queue-supervision/v1",
            "household_ref": HOUSE, "game_build": BUILD,
            "capture_ref": CAP, "sims": [meta],
        },
    }
    return root


def evaluate(root=None, now=NOW):
    result = evaluate_native_household_autonomy(root or observation(), now=now)
    return result["queue_supervision"]["decisions"][0]


class QueueSupervisionTests(unittest.TestCase):
    def test_existing_policy_unmodified_if_optional_input_absent(self):
        root = observation()
        del root["queue_supervision"]
        result = evaluate_native_household_autonomy(root, now=NOW)
        self.assertNotIn("queue_supervision", result)
        self.assertFalse(result["cancel_allowed"])

    def test_empirical_duration_has_four_distinct_influences_and_samples(self):
        r = evaluate()
        d = r["duration"]
        self.assertEqual(d["sample_count"], 2)
        self.assertEqual(d["verified_factors"],
                         ["moodlet", "temperament", "balance", "trait"])
        self.assertAlmostEqual(d["learned_ratio"], 1.375)
        self.assertAlmostEqual(d["predicted_seconds"], 222.75)
        self.assertAlmostEqual(d["remaining_seconds"], 162.75)
        self.assertTrue(d["reliable_for_preemption"])
        self.assertEqual(r["gate"], "QUEUE_CAPACITY_AVAILABLE_ADVISORY")
        self.assertFalse(r["enqueue_allowed"])
        self.assertFalse(r["cancel_allowed"])
        self.assertFalse(r["desktop_input_allowed"])
        self.assertEqual(r["queue_budget"]["operator_reported_capacity_band"], [6, 7])

    def test_duplicate_action_only_with_matching_semantics_and_source_proof(self):
        root = observation(actions=[
            action(), action("WRITE", "slot:2", "PENDING"),
        ])
        r = evaluate(root)
        self.assertEqual(r["gate"], "QUEUE_CONFLICT_CANDIDATE")
        self.assertEqual(r["cancel_candidate"]["queue_slot_ref"], "slot:2")
        self.assertEqual(r["cancel_candidate"]["reason"], "DUPLICATE_SEMANTIC_ACTION")
        self.assertFalse(r["cancel_allowed"])
        root["sims"][0]["queue"][1]["semantic_key"] = "semantic:write:target2"
        self.assertIsNone(evaluate(root)["cancel_candidate"])
        root["sims"][0]["queue"][1]["semantic_key"] = "semantic:write:target1"
        root["sims"][0]["queue"][1].pop("semantic_proof_ref")
        self.assertIsNone(evaluate(root)["cancel_candidate"])

    def test_contradiction_requires_same_source_verified_exclusive_group(self):
        root = observation(actions=[
            action("WASH_DISH", "slot:1", "RUNNING",
                   conflict_group="dish:77:exclusive-disposal",
                   conflict_outcome="WASH", conflict_proof_ref="proof:wash"),
            action("NANOCAN", "slot:2", "PENDING",
                   conflict_group="dish:77:exclusive-disposal",
                   conflict_outcome="RECYCLE", conflict_proof_ref="proof:recycle"),
        ], profile=None)
        # The active activity is attached to WRITE, and stale identity must
        # block the cancellation rather than operating on the wrong slot.
        self.assertEqual(evaluate(root)["gate"], "REOBSERVE_ACTIVITY")
        root["queue_supervision"]["sims"][0]["active_activity"] = None
        r = evaluate(root)
        self.assertEqual(r["cancel_candidate"]["reason"], "MUTUALLY_EXCLUSIVE_OUTCOME")
        root["sims"][0]["queue"][1].pop("conflict_proof_ref")
        self.assertIsNone(evaluate(root)["cancel_candidate"])

    def test_urgent_need_preempts_only_current_proven_nonneed_action(self):
        needs = dict(NEEDS, hunger=.24)
        r = evaluate(observation(needs=needs))
        self.assertEqual(r["gate"], "REPLAN_HIGHER_PRIORITY_NEED")
        self.assertEqual(r["priority_need"], "hunger")
        self.assertEqual(r["cancel_candidate"]["queue_slot_ref"], "slot:1")
        self.assertEqual(r["cancel_candidate"]["reason"], "OBSERVED_CRITICAL_NEED")
        self.assertFalse(r["cancel_allowed"])
        root = observation(needs=needs)
        root["sims"][0]["queue"][0]["serves_need"] = "hunger"
        self.assertEqual(evaluate(root)["gate"], "CURRENT_ACTIVITY_SERVES_PRIORITY_NEED")
        root["sims"][0]["queue"][0].pop("serve_proof_ref")
        self.assertEqual(evaluate(root)["gate"], "CURRENT_ACTIVITY_PURPOSE_UNKNOWN")

    def test_forecast_preemption_uses_rates_and_reliable_duration_not_guess(self):
        needs = dict(NEEDS, hunger=.50)
        root = observation(needs=needs)
        meta = root["queue_supervision"]["sims"][0]
        meta.update(
            need_decay_per_active_second={"hunger": .001},
            decay_proof_ref="proof:hunger-rate",
        )
        r = evaluate(root)
        self.assertEqual(r["gate"], "REPLAN_HIGHER_PRIORITY_NEED")
        self.assertEqual(r["cancel_candidate"]["reason"],
                         "FORECAST_CRITICAL_BEFORE_COMPLETION")
        root["queue_supervision"]["sims"][0]["active_activity"]["factors"]["trait"].pop("proof_ref")
        self.assertEqual(evaluate(root)["gate"], "QUEUE_CAPACITY_AVAILABLE_ADVISORY")
        root["queue_supervision"]["sims"][0]["active_activity"] = activity()
        meta.pop("decay_proof_ref")
        self.assertIsNone(evaluate(root)["cancel_candidate"])

    def test_stalled_activity_reobserves_no_blind_timeout_cancel(self):
        root = observation(profile=activity(elapsed=800))
        root["queue_supervision"]["sims"][0]["active_activity"]["progress_state"] = "STALLED"
        r = evaluate(root)
        self.assertTrue(r["duration"]["suspected_stall"])
        self.assertEqual(r["gate"], "STALLED_ACTIVITY_REOBSERVE")
        self.assertIsNone(r["cancel_candidate"])
        root["queue_supervision"]["sims"][0]["active_activity"]["progress_state"] = "ADVANCING"
        self.assertFalse(evaluate(root)["duration"]["suspected_stall"])

    def test_cooldown_halts_oscillating_need_switches(self):
        root = observation(needs=dict(NEEDS, hunger=.25))
        meta = root["queue_supervision"]["sims"][0]
        meta.update(active_clock_second=1000, last_switch_active_second=950)
        self.assertEqual(evaluate(root)["gate"], "SWITCH_COOLDOWN")
        meta["last_switch_active_second"] = 800
        self.assertEqual(evaluate(root)["gate"], "REPLAN_HIGHER_PRIORITY_NEED")
        meta["switch_history_verified"] = False
        self.assertEqual(evaluate(root)["gate"], "SWITCH_HISTORY_UNVERIFIED")

    def test_yields_to_player_unknown_actions_unverified_evidence_pause(self):
        for alter in (
            lambda r: r.update(player_active=True),
            lambda r: r.update(player_active=None),
            lambda r: r["sims"][0].update(player_owned=True),
            lambda r: r["sims"][0].update(player_command_present=True),
            lambda r: r["sims"][0]["queue"][0].update(origin="PLAYER"),
            lambda r: r["sims"][0]["queue"][0].update(origin="UNKNOWN"),
            lambda r: r["sims"][0].update(queue_verified=False),
            lambda r: r["queue_supervision"]["sims"][0].update(policy_opt_in=False),
            lambda r: r["queue_supervision"]["sims"][0]["active_activity"].update(paused=True),
            lambda r: r["queue_supervision"]["sims"][0].update(needs_proof_ref=None),
            lambda r: r.update(observed_at_unix=700),
        ):
            with self.subTest(modifier=alter):
                root = observation(needs=dict(NEEDS, hunger=.2))
                alter(root)
                self.assertIsNone(evaluate(root)["cancel_candidate"])

    def test_protect_player_queue_if_one_pending_player_item(self):
        root = observation(
            actions=[action(), action("EAT", "slot:2", "PENDING",
                                      origin="PLAYER", semantic_key="semantic:eat:meal")],
            needs=dict(NEEDS, hunger=.2),
        )
        self.assertEqual(evaluate(root)["gate"], "PLAYER_OR_UNKNOWN_QUEUE_PROTECTED")
        self.assertIsNone(evaluate(root)["cancel_candidate"])

    def test_rejection_and_capacity_are_heuristics_not_universal_max(self):
        root = observation()
        meta = root["queue_supervision"]["sims"][0]
        meta["rejected_last_enqueue"] = True
        self.assertEqual(evaluate(root)["gate"], "REOBSERVE_AFTER_ENQUEUE_REJECTION")
        meta["rejected_last_enqueue"] = False
        meta["multitasking"] = None
        self.assertEqual(evaluate(root)["gate"], "MULTITASKING_OBSERVATION_REQUIRED")
        root["sims"][0]["queue"] = [
            action("WRITE", f"slot:{i}", "RUNNING" if i == 0 else "PENDING",
                   semantic_key=f"semantic:write:{i}") for i in range(17)
        ]
        self.assertEqual(evaluate(root)["gate"], "QUEUE_OBSERVATION_TOO_LARGE")

    def test_identity_and_sample_replay_breach_fail_closed(self):
        root = observation()
        root["sims"][0]["queue"][0]["capture_ref"] = "capture:wrong"
        with self.assertRaises(AutonomyModerationError):
            evaluate(root)
        root = observation()
        samples = root["queue_supervision"]["sims"][0]["active_activity"]["completed_samples"]
        samples[1]["sample_ref"] = samples[0]["sample_ref"]
        with self.assertRaisesRegex(AutonomyModerationError, "SAMPLE_REPLAY"):
            evaluate(root)
        root = observation()
        root["queue_supervision"]["sims"][0]["active_activity"]["completed_samples"][1]["game_build"] = "build:2"
        with self.assertRaisesRegex(AutonomyModerationError, "SAMPLE_REPLAY_OR_SCOPE"):
            evaluate(root)
        root = observation()
        root["queue_supervision"]["sims"][0]["sim_ref"] = "sim:other"
        with self.assertRaisesRegex(AutonomyModerationError, "SIM_SCOPE_MISMATCH"):
            evaluate(root)

    def test_invalid_nonfinite_needs_and_factors_refused(self):
        root = observation(needs=dict(NEEDS, hunger=float("nan")))
        with self.assertRaises(AutonomyModerationError):
            evaluate(root)
        root = observation()
        root["queue_supervision"]["sims"][0]["active_activity"]["factors"]["trait"]["multiplier"] = math.inf
        with self.assertRaises(AutonomyModerationError):
            evaluate(root)

    def test_native_suppression_has_one_owner_when_queue_replan_wins(self):
        root = observation(needs=dict(NEEDS, hunger=.1))
        root["sims"][0]["queue"][0]["yield_by_domain"] = {"skill": 0}
        root["sims"][0]["available_actions"] = [
            {"action_id": "DO_FUN", "available": True,
             "native_affordance_verified": True,
             "yield_by_domain": {"fun": .9}, "yield_proof_ref": "proof:fun"}
        ]
        native = evaluate_native_household_autonomy(root, now=NOW)
        self.assertIsNone(native["decisions"][0]["suppress_candidate"])
        self.assertEqual(native["decisions"][0]["state"], "QUEUE_SUPERVISION_PRECEDENCE")
        self.assertIsNotNone(native["queue_supervision"]["decisions"][0]["cancel_candidate"])
        self.assertFalse(native["cancel_allowed"])

    def test_household_scope_all_sims_without_selected_portrait(self):
        root = observation()
        second_native = copy.deepcopy(root["sims"][0])
        second_native["sim_ref"] = "sim:two"
        second_native["queue"] = [
            {**action(), "sim_ref": "sim:two", "queue_slot_ref": "slot:two"}
        ]
        second_meta = copy.deepcopy(root["queue_supervision"]["sims"][0])
        second_meta["sim_ref"] = "sim:two"
        second_meta["active_activity"]["queue_slot_ref"] = "slot:two"
        root["sims"].append(second_native)
        root["queue_supervision"]["sims"].append(second_meta)
        results = evaluate_native_household_autonomy(root, now=NOW)
        self.assertEqual(
            {d["sim_ref"] for d in results["queue_supervision"]["decisions"]},
            {"sim:one", "sim:two"},
        )


if __name__ == "__main__":
    unittest.main()
