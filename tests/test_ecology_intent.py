"""PS-0241: adversarial ecology planning, interruption and forecast tests."""
from __future__ import annotations

import copy
import json
import unittest

from betterinstincts.ecology_intent import (
    EcologyIntentError, new_ecology_intent, reconcile_ecology_intent,
    reconcile_household_ecology, acknowledge_native_ecology_dispatch, NEEDS, OBSERVATION,
)
from betterinstincts.ecology_forecast import (
    EcologyForecastError, compare_duration_models,
)

NOW = 1_700_000_000.0
BUILD = "1.121.361.1020"


def intent(sim="sim:servo"):
    return new_ecology_intent(
        game_build=BUILD, household_ref="household:1", sim_ref=sim,
        lot_ref="lot:1", plant_ref="plant:trap", item_ref="object:superfert",
        goal_ref="goal:eco:1",
    )


def observed(sim="sim:servo", seq=1, **changes):
    row = {
        "schema": OBSERVATION, "game_build": BUILD,
        "household_ref": "household:1", "sim_ref": sim,
        "lot_ref": "lot:1", "plant_ref": "plant:trap",
        "item_ref": "object:superfert", "sequence": seq,
        "capture_ref": f"capture:{sim.replace(':', '-')}-{seq}",
        "observed_at_unix": NOW, "scene": "LIVE",
        "mode_verified": True, "paused": True, "player_active": False,
        "queue_verified": True, "queue": [],
        "needs_proof_ref": "proof:needs:1",
        "needs": {
            name: {"value": 0.85, "decay_per_sim_minute": 0.005}
            for name in NEEDS
        },
        "work_proof_ref": "proof:work:1",
        "minutes_until_work": 120,
        "inventory_verified": True, "inventory_proof_ref": "proof:inventory:1",
        "inventory_count": 0,
        "ground_stock_verified": True,
        "ground_stock_proof_ref": "proof:ground:1", "ground_stock_count": 1,
        "plant_verified": True, "plant_proof_ref": "proof:plant:1",
        "plant_state": "DEPLETED",
        "pickup_upper_sim_minutes": 5.0, "fertilize_upper_sim_minutes": 6.0,
        "timing_proof_ref": "proof:duration:1",
    }
    row.update(changes)
    return row


def queue_row(obs, action="PICKUP", target="object:superfert", origin="HOST"):
    return {
        "sim_ref": obs["sim_ref"], "capture_ref": obs["capture_ref"],
        "action_id": action, "target_ref": target, "origin": origin,
        "origin_proof_ref": "proof:queue:1" if origin != "UNKNOWN" else None,
        "state": "PENDING",
    }


def outcome(before, after, step, before_count, after_count, **extra):
    return {
        "step": step, "status": "SUCCEEDED", "sim_ref": before["sim_ref"],
        "target_ref": "object:superfert" if step == "PICKUP" else "plant:trap",
        "before_capture_ref": before["capture_ref"],
        "after_capture_ref": after["capture_ref"],
        "before_item_count": before_count, "after_item_count": after_count,
        "native_action_ref": "ea:action:123", "native_queue_ref": "ea:queue:1",
        "proof_ref": "proof:outcome:1",
        **extra,
    }



def ack(state, before, status="QUEUED", **changes):
    receipt = {
        "game_build": BUILD, "household_ref": state["household_ref"],
        "sim_ref": state["sim_ref"], "lot_ref": state["lot_ref"],
        "step": state["awaiting"],
        "target_ref": state["item_ref"] if state["awaiting"] == "PICKUP" else state["plant_ref"],
        "proposal_capture_ref": before["capture_ref"],
        "queue_capture_ref": before["capture_ref"] + ":native",
        "queue_verified": True,
        "queue_proof_ref": "proof:nativequeue:1",
        "native_observation_ref": "ea:queue:event:1",
        "player_active": False,
        "status": status,
        "queue_origin": "HOST",
        "origin_proof_ref": "proof:nativeorigin:1",
        "native_queue_ref": "ea:queue:1",
        "effect_absent_verified": status == "NOT_ENQUEUED",
        "absence_proof_ref": "proof:noeffect:1",
    }
    receipt.update(changes)
    return acknowledge_native_ecology_dispatch(state, receipt)



class EcologyIntentTests(unittest.TestCase):

    def test_proposal_cannot_promote_to_game_outcome_without_native_queue_ack(self):
        first = observed(paused=False)
        proposed = reconcile_ecology_intent(intent(), first, now=NOW)
        second = observed(seq=2, paused=False, inventory_count=1)
        second["outcome"] = outcome(first, second, "PICKUP", 0, 1)
        unacked = reconcile_ecology_intent(proposed["intent"], second, now=NOW)
        self.assertEqual(unacked["gate"], "ECOLOGY_AWAIT_NATIVE_DISPATCH_ACK")
        self.assertEqual(unacked["intent"]["step"], "PICKUP")
        self.assertEqual(unacked["intent"]["dispatch_status"], "PROPOSED")
        self.assertFalse(unacked["execute_allowed"])

    def test_native_ack_rejects_wrong_queue_provenance_and_duplicates(self):
        first = observed(paused=False)
        proposed = reconcile_ecology_intent(intent(), first, now=NOW)
        state = proposed["intent"]
        for attrs in (
            {"sim_ref": "sim:other"},
            {"queue_origin": "PLAYER"},
            {"queue_origin": "UNKNOWN"},
            {"player_active": True},
            {"queue_capture_ref": first["capture_ref"]},
            {"native_queue_ref": ""},
            {"proposal_capture_ref": "capture:stale"},
        ):
            with self.subTest(attrs=attrs):
                out = ack(state, first, **attrs)
                self.assertNotEqual(out["gate"], "ECOLOGY_NATIVE_QUEUE_ATTESTED")
                self.assertEqual(out["intent"], state)
        accepted = ack(state, first)
        self.assertEqual(accepted["intent"]["dispatch_status"], "QUEUED")
        duplicate = ack(accepted["intent"], first)
        self.assertEqual(duplicate["gate"], "ECOLOGY_ACK_NO_PENDING_PROPOSAL")
        self.assertEqual(duplicate["intent"], accepted["intent"])

    def test_rejected_enqueue_requires_proven_no_effect_then_fresh_replan(self):
        first = observed(paused=False)
        proposed = reconcile_ecology_intent(intent(), first, now=NOW)
        ambiguous = ack(
            proposed["intent"], first, status="NOT_ENQUEUED",
            effect_absent_verified=False,
        )
        self.assertEqual(ambiguous["gate"], "ECOLOGY_ACK_REOBSERVE")
        self.assertEqual(ambiguous["intent"]["dispatch_status"], "PROPOSED")
        denied = ack(proposed["intent"], first, status="NOT_ENQUEUED")
        self.assertEqual(denied["gate"], "ECOLOGY_NATIVE_NONENQUEUE_CONFIRMED")
        self.assertIsNone(denied["intent"]["awaiting"])
        self.assertEqual(denied["intent"]["step"], "PICKUP")
        second = observed(seq=2, paused=False)
        retried = reconcile_ecology_intent(denied["intent"], second, now=NOW)
        self.assertEqual(retried["gate"], "ECOLOGY_PLAY_STEP_PROPOSED")
        self.assertEqual(retried["proposal"]["step"], "PICKUP")

    def test_queue_identity_mismatch_does_not_complete_or_requeue(self):
        first = observed(paused=False)
        proposal = reconcile_ecology_intent(intent(), first, now=NOW)
        accepted = ack(proposal["intent"], first)
        second = observed(seq=2, paused=False, inventory_count=1)
        second["outcome"] = outcome(
            first, second, "PICKUP", 0, 1, native_queue_ref="ea:unrelated",
        )
        res = reconcile_ecology_intent(accepted["intent"], second, now=NOW)
        self.assertEqual(res["gate"], "ECOLOGY_AWAIT_INDEPENDENT_OUTCOME")
        self.assertEqual(res["intent"]["verified_steps"], [])
        self.assertEqual(res["intent"]["dispatch_status"], "QUEUED")

    def test_paused_plan_survives_and_no_game_effect(self):
        state = intent()
        before = copy.deepcopy(state)
        result = reconcile_ecology_intent(state, observed(), now=NOW)
        self.assertEqual(state, before)
        self.assertEqual(result["gate"], "ECOLOGY_PLANNED_WHILE_PAUSED")
        self.assertEqual(result["mode"], "PLANNING")
        self.assertEqual([s["step"] for s in result["remaining_steps"]], ["PICKUP", "FERTILIZE"])
        self.assertEqual(result["proposal"]["step"], "PICKUP")
        self.assertIsNone(result["intent"]["awaiting"])
        self.assertFalse(result["execute_allowed"])
        self.assertFalse(result["cancel_allowed"])
        json.dumps(result)

    def test_play_proposal_then_independently_verified_pickup_and_use(self):
        first = observed(paused=False)
        play = reconcile_ecology_intent(intent(), first, now=NOW)
        self.assertEqual(play["gate"], "ECOLOGY_PLAY_STEP_PROPOSED")
        self.assertEqual(play["intent"]["awaiting"], "PICKUP")
        self.assertEqual(play["intent"]["dispatch_status"], "PROPOSED")
        pickup_ack = ack(play["intent"], first)
        self.assertEqual(pickup_ack["gate"], "ECOLOGY_NATIVE_QUEUE_ATTESTED")
        second = observed(seq=2, paused=False, inventory_count=1)
        second["outcome"] = outcome(first, second, "PICKUP", 0, 1)
        fert = reconcile_ecology_intent(pickup_ack["intent"], second, now=NOW)
        self.assertEqual(fert["gate"], "ECOLOGY_PLAY_STEP_PROPOSED")
        self.assertEqual(fert["proposal"]["step"], "FERTILIZE")
        self.assertEqual(fert["intent"]["verified_steps"], ["PICKUP"])
        fert_ack = ack(fert["intent"], second)
        third = observed(seq=3, paused=False, inventory_count=0, plant_state="GOOD")
        third["outcome"] = outcome(
            second, third, "FERTILIZE", 1, 0,
            before_plant_state="DEPLETED", after_plant_state="GOOD",
        )
        end = reconcile_ecology_intent(fert_ack["intent"], third, now=NOW)
        self.assertEqual(end["gate"], "ECOLOGY_VERIFIED_COMPLETE")
        self.assertEqual(end["intent"]["verified_steps"], ["PICKUP", "FERTILIZE"])
        self.assertEqual(end["remaining_steps"], [])
        self.assertFalse(end["execute_allowed"])

    def test_unverified_inventory_gain_does_not_advance(self):
        first = observed(paused=False)
        play = reconcile_ecology_intent(intent(), first, now=NOW)
        second = observed(seq=2, paused=False, inventory_count=1)
        out = reconcile_ecology_intent(ack(play["intent"], first)["intent"], second, now=NOW)
        self.assertEqual(out["gate"], "ECOLOGY_AWAIT_INDEPENDENT_OUTCOME")
        self.assertEqual(out["intent"]["step"], "PICKUP")
        self.assertEqual(out["intent"]["awaiting"], "PICKUP")

    def test_wrong_capture_and_unconsumed_stock_cannot_complete(self):
        first = observed(paused=False, inventory_count=1)
        play = reconcile_ecology_intent(intent(), first, now=NOW)
        self.assertEqual(play["proposal"]["step"], "FERTILIZE")
        second = observed(seq=2, paused=False, inventory_count=1, plant_state="GOOD")
        second["outcome"] = outcome(
            first, second, "FERTILIZE", 1, 1,
            before_plant_state="DEPLETED", after_plant_state="GOOD",
        )
        out = reconcile_ecology_intent(play["intent"], second, now=NOW)
        self.assertNotEqual(out["gate"], "ECOLOGY_VERIFIED_COMPLETE")
        self.assertEqual(out["intent"]["step"], "FERTILIZE")

    def test_autonomy_cancellation_requires_independent_receipt_to_reoffer(self):
        first = observed(paused=False)
        play = reconcile_ecology_intent(intent(), first, now=NOW)
        second = observed(seq=2, paused=False)
        waiting = reconcile_ecology_intent(ack(play["intent"], first)["intent"], second, now=NOW)
        self.assertEqual(waiting["gate"], "ECOLOGY_AWAIT_INDEPENDENT_OUTCOME")
        third = observed(seq=3, paused=False)
        third["interruption"] = {
            "step": "PICKUP", "status": "NATIVE_INTERRUPTED",
            "cause": "SIM_AUTONOMY",
            "before_capture_ref": first["capture_ref"],
            "after_capture_ref": third["capture_ref"],
            "proof_ref": "proof:interruption:3",
            "native_queue_ref": "ea:queue:1",
        }
        restored = reconcile_ecology_intent(waiting["intent"], third, now=NOW)
        self.assertEqual(restored["gate"], "ECOLOGY_PLAY_STEP_PROPOSED")
        self.assertEqual(restored["proposal"]["step"], "PICKUP")
        self.assertEqual(restored["intent"]["verified_steps"], [])

    def test_intermediate_telemetry_preserves_native_outcome_origin(self):
        initial = observed(paused=False)
        proposed = reconcile_ecology_intent(intent(), initial, now=NOW)
        intermediate = observed(seq=2, paused=False)
        pending = reconcile_ecology_intent(ack(proposed["intent"], initial)["intent"], intermediate, now=NOW)
        self.assertEqual(pending["gate"], "ECOLOGY_AWAIT_INDEPENDENT_OUTCOME")
        self.assertEqual(pending["intent"]["awaiting_capture_ref"], initial["capture_ref"])
        self.assertEqual(pending["intent"]["awaiting_item_count"], 0)
        completed = observed(seq=3, paused=False, inventory_count=1)
        completed["outcome"] = outcome(initial, completed, "PICKUP", 0, 1)
        next_result = reconcile_ecology_intent(pending["intent"], completed, now=NOW)
        self.assertEqual(next_result["proposal"]["step"], "FERTILIZE")
        self.assertEqual(next_result["intent"]["verified_steps"], ["PICKUP"])

    def test_shared_proactive_need_threshold_blocks_low_nonemergency_need(self):
        o = observed()
        o["needs"]["social"]["value"] = 0.50
        self.assertEqual(
            reconcile_ecology_intent(intent(), o, now=NOW)["gate"],
            "ECOLOGY_NEED_OR_WORK_FIRST",
        )

    def test_player_and_unknown_queue_win(self):
        for paused in (True, False):
            with self.subTest(paused=paused):
                o = observed(paused=paused, player_active=True)
                self.assertEqual(
                    reconcile_ecology_intent(intent(), o, now=NOW)["gate"],
                    "ECOLOGY_PLAYER_FIRST",
                )
        o = observed()
        o["queue"] = [queue_row(o, origin="UNKNOWN")]
        self.assertEqual(
            reconcile_ecology_intent(intent(), o, now=NOW)["gate"],
            "QUEUE_ORIGIN_UNVERIFIED",
        )
        o["queue"] = [queue_row(o, origin="PLAYER")]
        self.assertEqual(
            reconcile_ecology_intent(intent(), o, now=NOW)["gate"],
            "PLAYER_QUEUE_FIRST",
        )

    def test_existing_task_not_enqueued_twice(self):
        o = observed(paused=False)
        o["queue"] = [queue_row(o)]
        result = reconcile_ecology_intent(intent(), o, now=NOW)
        self.assertEqual(result["gate"], "TASK_ALREADY_QUEUED")
        self.assertIsNone(result["intent"]["awaiting"])

    def test_autonomy_diversion_preserves_intent(self):
        o = observed(paused=False)
        o["queue"] = [queue_row(o, action="CHAT", target="sim:neighbor", origin="SIM_AUTONOMY")]
        result = reconcile_ecology_intent(intent(), o, now=NOW)
        self.assertEqual(result["gate"], "AUTONOMY_INTERRUPTED_RECONCILE")
        self.assertEqual(result["remaining_steps"][0]["step"], "PICKUP")
        self.assertFalse(result["cancel_allowed"])

    def test_critical_need_and_work_window_defer(self):
        urgent = observed()
        urgent["needs"]["social"]["value"] = 0.2
        self.assertEqual(
            reconcile_ecology_intent(intent(), urgent, now=NOW)["gate"],
            "ECOLOGY_NEED_OR_WORK_FIRST",
        )
        tight = observed(minutes_until_work=35)
        self.assertEqual(
            reconcile_ecology_intent(intent(), tight, now=NOW)["gate"],
            "ECOLOGY_DEFER_FOR_NEEDS_OR_WORK",
        )
        unknown = observed(minutes_until_work=None)
        self.assertEqual(
            reconcile_ecology_intent(intent(), unknown, now=NOW)["gate"],
            "WORK_DEADLINE_UNVERIFIED",
        )

    def test_stale_version_and_replay_fail_closed(self):
        o = observed(game_build="1.000.000.000")
        self.assertEqual(
            reconcile_ecology_intent(intent(), o, now=NOW)["gate"], "ECOLOGY_SCOPE_MISMATCH"
        )
        old = observed(observed_at_unix=NOW-61)
        self.assertEqual(
            reconcile_ecology_intent(intent(), old, now=NOW)["gate"], "ECOLOGY_STALE_OR_REPLAY"
        )
        one = reconcile_ecology_intent(intent(), observed(), now=NOW)
        again = reconcile_ecology_intent(one["intent"], observed(), now=NOW)
        self.assertEqual(again["gate"], "ECOLOGY_STALE_OR_REPLAY")

    def test_forged_queue_identity_and_missing_plant_proof(self):
        o = observed()
        q = queue_row(o)
        q["capture_ref"] = "capture:old"
        o["queue"] = [q]
        self.assertEqual(
            reconcile_ecology_intent(intent(), o, now=NOW)["gate"], "QUEUE_UNVERIFIED"
        )
        o = observed(inventory_count=1, plant_verified=False)
        self.assertEqual(
            reconcile_ecology_intent(intent(), o, now=NOW)["gate"],
            "ECOLOGY_PLANT_ELIGIBILITY_UNVERIFIED",
        )

    def test_malformed_ground_stock_fails_closed_without_crash(self):
        o = observed(ground_stock_count="not-an-integer")
        self.assertEqual(
            reconcile_ecology_intent(intent(), o, now=NOW)["gate"],
            "ECOLOGY_SUPPLY_UNVERIFIED",
        )

    def test_household_portrait_switch_does_not_mix_sim_intents(self):
        s1, s2 = intent("sim:servo"), intent("sim:neighbor")
        a = reconcile_household_ecology(
            {"sim:servo": s1, "sim:neighbor": s2},
            {"sim:servo": observed("sim:servo"),
             "sim:neighbor": observed("sim:neighbor", inventory_count=1)},
            now=NOW,
        )
        self.assertEqual(a["sim:servo"]["proposal"]["step"], "PICKUP")
        self.assertEqual(a["sim:neighbor"]["proposal"]["step"], "FERTILIZE")
        with self.assertRaises(EcologyIntentError):
            reconcile_household_ecology(
                {"sim:servo": s1},
                {"sim:servo": observed("sim:neighbor")},
                now=NOW,
            )

    def test_optional_duration_training_cannot_create_authority(self):
        samples = [
            {
                "game_build": BUILD, "action_id": "PICKUP",
                "capture_ref": f"sample:{i}", "proof_ref": f"proof:sample:{i}",
                "context": float(i % 2),
                "duration_sim_minutes": 3.0 if i % 2 == 0 else 8.0,
            }
            for i in range(12)
        ]
        o = observed(
            duration_context=0.0,
            duration_training={"PICKUP": samples, "FERTILIZE": []},
        )
        out = reconcile_ecology_intent(intent(), o, now=NOW)
        self.assertIn(out["forecast_models"]["PICKUP"]["model"],
                      {"DETERMINISTIC", "GAUSSIAN_PROCESS_MATERN32"})
        self.assertFalse(out["execute_allowed"])


class EcologyForecastTests(unittest.TestCase):
    def test_bounded_gp_can_beat_deterministic_baseline_on_heldout_context(self):
        rows = [
            {
                "game_build": BUILD, "action_id": "PICKUP",
                "capture_ref": f"sample:{i}", "proof_ref": f"proof:sample:{i}",
                "context": float(i % 2),
                "duration_sim_minutes": 3.0 if i % 2 == 0 else 8.0,
            }
            for i in range(12)
        ]
        result = compare_duration_models(
            rows, game_build=BUILD, action_id="PICKUP",
            context=0.0, baseline_upper_sim_minutes=10.0,
        )
        self.assertEqual(result["training_count"], 9)
        self.assertEqual(result["holdout_count"], 3)
        self.assertLessEqual(result["selected_upper_sim_minutes"], 10.0)
        self.assertIn(result["model"], ("DETERMINISTIC", "GAUSSIAN_PROCESS_MATERN32"))

    def test_gp_absent_or_mismatched_proof_falls_back(self):
        rows = [
            {
                "game_build": BUILD, "action_id": "PICKUP",
                "capture_ref": f"sample:{i}", "proof_ref": f"proof:sample:{i}",
                "context": 0.5, "duration_sim_minutes": 4.0,
            }
            for i in range(12)
        ]
        baseline = compare_duration_models(
            rows[:4], game_build=BUILD, action_id="PICKUP",
            context=0.5, baseline_upper_sim_minutes=10,
        )
        self.assertEqual(baseline["model"], "DETERMINISTIC")
        rows[3]["game_build"] = "wrong"
        rejected = compare_duration_models(
            rows, game_build=BUILD, action_id="PICKUP",
            context=0.5, baseline_upper_sim_minutes=10,
        )
        self.assertEqual(rejected["gate"], "GP_SAMPLE_UNTRUSTWORTHY")
        self.assertEqual(rejected["selected_upper_sim_minutes"], 10)

    def test_gp_bounds_reject_bloat_and_nonfinite_inputs(self):
        with self.assertRaises(EcologyForecastError):
            compare_duration_models(
                [{}] * 25, game_build=BUILD, action_id="PICKUP",
                context=0.1, baseline_upper_sim_minutes=10,
            )
        with self.assertRaises(EcologyForecastError):
            compare_duration_models(
                [], game_build=BUILD, action_id="PICKUP",
                context=float("nan"), baseline_upper_sim_minutes=10,
            )


if __name__ == "__main__":
    unittest.main()
