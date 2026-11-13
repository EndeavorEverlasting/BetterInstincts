"""P82 falsifiers for cursor-free NanoCan autonomy and revenue attribution."""
from __future__ import annotations

import copy
import unittest

from betterinstincts.nanocan_recycling import (
    NanoCanRecyclingError, evaluate_nanocan_recycling, reconcile_nanocan_outcome,
)
from betterinstincts.autonomy_moderation import (
    AutonomyModerationError, evaluate_native_household_autonomy,
)

NOW = 2000.0
CAP = "capture:nano"
BUILD = "1.121.361.1020"
HH = "household:test"


def sim(ref="sim:one", **changes):
    row = dict(
        sim_ref=ref, capture_ref=CAP, queue_verified=True,
        player_command_present=False, player_owned=False,
        urgent_need=False, imminent_obligation=False, policy_opt_in=True,
        queue=[], available_actions=[],
    )
    row.update(changes)
    return row


def dish(ref="dish:a", **changes):
    row = dict(
        dish_ref=ref, capture_ref=CAP, state="DIRTY_EMPTY",
        stack_size=1, attempt="NONE", verified=True,
        player_reserved=False, disposal_allowed=True,
    )
    row.update(changes)
    return row


def can(ref="can:nano", **changes):
    row = dict(
        can_ref=ref, capture_ref=CAP, kind="NANOCAN_TOUCHLESS",
        verified=True, usable=True, cooldown_ready=True,
        broken=False, player_reserved=False,
    )
    row.update(changes)
    return row


def route(mode="NATIVE_DRAG_EQUIVALENT", dish_ref="dish:a",
          can_ref="can:nano", **changes):
    row = dict(
        mode=mode, dish_ref=dish_ref, can_ref=can_ref,
        capture_ref=CAP, game_build=BUILD,
        ea_source_ref="ea:nanocan:export:verified",
        source_kind="EA_SCRIPT", mechanism_verified=True,
        native_affordance_ref="ea:interaction:disposal",
        available=True, native_route_verified=True,
        reward_equivalence_verified=True,
        reward_proof_ref="proof:drag-equivalent",
    )
    if mode == "NATIVE_SIM_DISPOSE":
        row["actor_ref"] = "sim:one"
    row.update(changes)
    return row


def visit(**changes):
    row = dict(
        schema="betterinstincts.nanocan-recycling/v1",
        household_ref=HH, game_build=BUILD, capture_ref=CAP,
        observed_at_unix=NOW, scene="LIVE", lot_scope="HOME",
        household_verified=True, lot_verified=True, queue_verified=True,
        policy_opt_in=True, household_member_count=4,
        household_member_count_verified=True,
        dishes=[dish()], cans=[can()], native_routes=[route()],
    )
    row.update(changes)
    return row


def evaluate(obs=None, *, sims=None, player_active=False):
    return evaluate_nanocan_recycling(
        obs if obs is not None else visit(), household_ref=HH,
        game_build=BUILD, capture_ref=CAP, player_active=player_active,
        sims=[sim()] if sims is None else sims, now=NOW,
    )


def outcome(**changes):
    row = dict(
        schema="betterinstincts.nanocan-outcome/v1",
        proposal_key="capture:nano:dish:a:can:nano:NATIVE_DRAG_EQUIVALENT",
        dish_ref="dish:a", can_ref="can:nano",
        before_capture_ref="capture:before",
        after_capture_ref="capture:after",
        attempt_ref="attempt:nano", attempt_state="DISPATCHED",
        funds_before=500, funds_after=540,
        dish_removed_verified=True, disposal_proof_ref="proof:removed",
        causal_reward_verified=True, causal_reward_proof_ref="proof:causal",
    )
    row.update(changes)
    return row


class NanoCanPolicyTests(unittest.TestCase):
    def test_single_player_drag_equivalent_candidate_is_not_a_game_effect(self):
        data = visit()
        original = copy.deepcopy(data)
        result = evaluate(data)
        self.assertEqual(result["state"], "NANOCAN_NATIVE_DISPOSAL_CANDIDATE")
        self.assertEqual(result["proposal"]["mode"], "NATIVE_DRAG_EQUIVALENT")
        self.assertEqual(result["proposal"]["dish_ref"], "dish:a")
        self.assertIsNone(result["proposal"]["actor_ref"])
        self.assertEqual(result["reported_reward_estimate_simoleons"], 40)
        self.assertFalse(result["reported_reward_is_game_proven"])
        self.assertFalse(result["dispatch_authorized"])
        self.assertFalse(result["cancel_allowed"])
        self.assertFalse(result["desktop_input_allowed"])
        self.assertFalse(result["proposal"]["may_post_money"])
        self.assertEqual(data, original)

    def test_ordinary_sim_disposal_is_lesser_reward_and_requires_an_actor(self):
        result = evaluate(visit(native_routes=[
            route("NATIVE_SIM_DISPOSE", reward_equivalence_verified=False)]))
        self.assertEqual(result["proposal"]["mode"], "NATIVE_SIM_DISPOSE")
        self.assertEqual(result["proposal"]["actor_ref"], "sim:one")
        self.assertEqual(result["reported_reward_estimate_simoleons"], 10)

    def test_drag_reward_never_inferred_from_ordinary_sim_route(self):
        result = evaluate(visit(native_routes=[
            route("NATIVE_DRAG_EQUIVALENT",reward_equivalence_verified=False),
            route("NATIVE_SIM_DISPOSE",reward_equivalence_verified=False)]))
        self.assertEqual(result["proposal"]["mode"], "NATIVE_SIM_DISPOSE")
        self.assertEqual(result["reported_reward_estimate_simoleons"], 10)

    def test_direct_route_preferred_over_sim_walking_when_both_proven(self):
        result = evaluate(visit(native_routes=[
            route("NATIVE_SIM_DISPOSE",reward_equivalence_verified=False),
            route("NATIVE_DRAG_EQUIVALENT")]))
        self.assertEqual(result["proposal"]["mode"], "NATIVE_DRAG_EQUIVALENT")

    def test_not_fabricating_cash_without_verified_household_member_count(self):
        for count, verified in ((None,False), (4,False), (0,True), (9,True), ("8",True)):
            with self.subTest(count=count, verified=verified):
                result=evaluate(visit(household_member_count=count,
                                      household_member_count_verified=verified))
                self.assertIsNone(result["reported_reward_estimate_simoleons"])
                self.assertIsNotNone(result["proposal"])

    def test_player_and_lot_guards_deny_disposal(self):
        for mutation in (
            {"policy_opt_in":False},{"scene":"BUILD"},{"lot_scope":"COMMUNITY"},
            {"household_verified":False},{"lot_verified":False},
            {"queue_verified":False},{"observed_at_unix":NOW-181},
        ):
            with self.subTest(mutation=mutation):
                result=evaluate(visit(**mutation))
                self.assertIsNone(result["proposal"])
                self.assertIsNone(result["sink_suppression_candidate"])
        self.assertEqual(evaluate(player_active=True)["state"],"PLAYER_FIRST")
        self.assertEqual(evaluate(player_active=None)["state"],"PLAYER_FIRST")

    def test_only_dirty_empty_single_unreserved_plate_is_eligible(self):
        for mutation in (
            {"state":"EDIBLE_FOOD"}, {"state":"LEFTOVERS"},
            {"state":"CLEAN"}, {"state":"UNKNOWN"},
            {"state":"PLAYER_RESERVED"}, {"stack_size":2},
            {"verified":False},{"player_reserved":True},
            {"disposal_allowed":False},{"capture_ref":"capture:stale"},
            {"attempt":"QUEUED"},{"attempt":"DISPATCHED"},
            {"attempt":"CONFIRMED"},
        ):
            with self.subTest(mutation=mutation):
                result=evaluate(visit(dishes=[dish(**mutation)]))
                self.assertIsNone(result["proposal"])

    def test_cooldown_and_broken_can_holds_all_actions(self):
        for mutation in (
            {"verified":False}, {"usable":False},
            {"cooldown_ready":False},{"broken":True},
            {"player_reserved":True},{"capture_ref":"capture:stale"},
        ):
            with self.subTest(mutation=mutation):
                result=evaluate(visit(cans=[can(**mutation)]))
                self.assertIsNone(result["proposal"])

    def test_no_native_route_never_claims_game_work(self):
        for routes in ([], [route(native_route_verified=False)],
                       [route(available=False)],
                       [route(reward_equivalence_verified=False)],
                       [route(capture_ref="capture:stale")],
                       [route(dish_ref="dish:wrong")]):
            with self.subTest(routes=len(routes)):
                result=evaluate(visit(native_routes=routes))
                self.assertEqual(result["state"],"NATIVE_DISPOSAL_ROUTE_NOT_VERIFIED_OR_BUSY")
                self.assertIsNone(result["proposal"])
                self.assertIsNone(result["sink_suppression_candidate"])

    def test_ordinary_native_sim_route_does_not_override_actor_queue(self):
        r=[route("NATIVE_SIM_DISPOSE",reward_equivalence_verified=False)]
        for bad in (
            {"player_command_present":True}, {"player_owned":True},
            {"urgent_need":True},{"imminent_obligation":True},
            {"policy_opt_in":False},{"queue_verified":False},
            {"capture_ref":"capture:stale"},
            {"queue":[{"origin":"PLAYER","origin_proof_ref":"proof:p"}]},
            {"queue":[{"origin":"UNKNOWN","origin_proof_ref":"proof:x"}]},
        ):
            with self.subTest(bad=bad):
                data=visit(native_routes=r)
                self.assertIsNone(evaluate(data,sims=[sim(**bad)])["proposal"])
        self.assertIsNone(evaluate(visit(native_routes=[
            route("NATIVE_SIM_DISPOSE",actor_ref="sim:wrong")]))["proposal"])

    def test_direct_route_does_not_require_selected_portrait(self):
        result=evaluate(visit(),sims=[sim("sim:one"),sim("sim:two")])
        self.assertIsNone(result["proposal"]["actor_ref"])
        self.assertFalse(result["desktop_input_allowed"])

    def test_native_build_and_source_provenance_are_mandatory(self):
        for mutation in (
            {"game_build":"1.000.000.000"}, {"source_kind":"GUI"},
            {"mechanism_verified":False},
        ):
            with self.subTest(mutation=mutation):
                with self.assertRaisesRegex(NanoCanRecyclingError, "NATIVE_BUILD_OR_SOURCE"):
                    evaluate(visit(native_routes=[route(**mutation)]))
        with self.assertRaisesRegex(NanoCanRecyclingError,"REWARD_PROOF"):
            evaluate(visit(native_routes=[route(reward_proof_ref=None)]))

    def test_sink_suppression_only_for_exact_autonomous_queue_and_safe_can(self):
        sink = dict(action_id="WASH_DISHES",origin="SIM_AUTONOMY",
                    actor_ref="sim:one",dish_ref="dish:a",capture_ref=CAP,
                    queue_slot_ref="queue:sink",origin_proof_ref="proof:autonomy")
        actor=sim(queue=[{"action_id":"WASH_DISHES","queue_slot_ref":"queue:sink",
                          "origin":"SIM_AUTONOMY","origin_proof_ref":"proof:autonomy"}])
        obs=visit(dishes=[dish(pending_sink=sink)])
        result=evaluate(obs,sims=[actor])
        self.assertEqual(result["sink_suppression_candidate"]["queue_slot_ref"],"queue:sink")
        self.assertFalse(result["cancel_allowed"])
        for mutation in ({"origin":"PLAYER"},{"action_id":"WASH_HANDS"},
                         {"queue_slot_ref":"queue:wrong"},
                         {"capture_ref":"capture:old"}):
            with self.subTest(mutation=mutation):
                bad_sink={**sink,**mutation}
                blocked=evaluate(visit(dishes=[dish(pending_sink=bad_sink)]),sims=[actor])
                self.assertIsNone(blocked["sink_suppression_candidate"])
        blocked=evaluate(visit(dishes=[dish(pending_sink=sink)],
                              cans=[can(cooldown_ready=False)]),sims=[actor])
        self.assertIsNone(blocked["sink_suppression_candidate"])

    def test_deterministic_one_proposal_at_a_time_and_unique_ids(self):
        obs=visit(dishes=[dish("dish:z"),dish("dish:a")],
                  native_routes=[
                      route(dish_ref="dish:z"),
                      route(dish_ref="dish:a")])
        result=evaluate(obs)
        self.assertEqual(result["proposal"]["dish_ref"],"dish:a")
        self.assertEqual(result,evaluate(obs))
        with self.assertRaisesRegex(NanoCanRecyclingError,"DISHES_DUPLICATE"):
            evaluate(visit(dishes=[dish(),dish()]))

    def test_schema_and_bounds_malformed_source_evidence_fails_closed(self):
        for obs in (
            visit(dishes=[dish()]*33),
            visit(cans=[can()]*9),
            visit(native_routes=[route()]*65),
            visit(dishes=[dish(stack_size=0)]),
            visit(dishes=[dish(verified="true")]),
            visit(cans=[can(broken="no")]),
            visit(native_routes=[route(mode="DESKTOP_MOUSE")]),
            visit(game_build="unknown"),
        ):
            with self.subTest(keys=tuple(obs)):
                with self.assertRaises(NanoCanRecyclingError):
                    evaluate(obs)

    def test_outcome_requires_independent_causal_observation(self):
        result=reconcile_nanocan_outcome(outcome())
        self.assertEqual(result["state"],"VERIFIED_REWARD")
        self.assertEqual(result["verified_reward_simoleons"],40)
        self.assertFalse(result["modifies_household_funds"])
        for mutation,state in (
            ({"dish_removed_verified":False},"DISH_DISPOSAL_NOT_PROVED"),
            ({"causal_reward_verified":False},"FUNDS_DELTA_NOT_ATTRIBUTED_TO_NANOCAN"),
            ({"causal_reward_proof_ref":None},"FUNDS_DELTA_NOT_ATTRIBUTED_TO_NANOCAN"),
            ({"funds_after":500},"NO_REWARD_OBSERVED"),
            ({"funds_after":490},"AMBIGUOUS_NEGATIVE_FUNDS_CHANGE"),
        ):
            with self.subTest(mutation=mutation):
                result=reconcile_nanocan_outcome(outcome(**mutation))
                self.assertEqual(result["state"],state)
                self.assertNotEqual(result.get("verified_reward_simoleons"),40)

    def test_outcome_prohibits_unobserved_or_replayed_claim(self):
        for mutation in (
            {"attempt_state":"QUEUED"},
            {"before_capture_ref":"capture:after"},
            {"funds_before":float("nan")},
            {"funds_after":-10},
            {"attempt_ref":None},
        ):
            with self.subTest(mutation=mutation):
                with self.assertRaises(NanoCanRecyclingError):
                    reconcile_nanocan_outcome(outcome(**mutation))


class NativeAutonomyIntegrationTests(unittest.TestCase):
    def test_nested_port_does_not_change_legacy_sim_outputs(self):
        parent={
            "schema":"betterinstincts.native-household-autonomy/v1",
            "household_ref":HH,"game_build":BUILD,"capture_ref":CAP,
            "observed_at_unix":NOW,"player_active":False,"sims":[sim()],
        }
        old=evaluate_native_household_autonomy(parent,now=NOW)
        self.assertNotIn("nanocan_recycling",old)
        updated=evaluate_native_household_autonomy({
            **parent,"nanocan_recycling":visit(),
        },now=NOW)
        self.assertEqual(updated["decisions"],old["decisions"])
        self.assertEqual(updated["nanocan_recycling"]["state"],
                         "NANOCAN_NATIVE_DISPOSAL_CANDIDATE")
        self.assertFalse(updated["enqueue_allowed"])

    def test_parent_player_active_propagates_to_recycling(self):
        parent={
            "schema":"betterinstincts.native-household-autonomy/v1",
            "household_ref":HH,"game_build":BUILD,"capture_ref":CAP,
            "observed_at_unix":NOW,"player_active":True,
            "sims":[sim()],"nanocan_recycling":visit(),
        }
        r=evaluate_native_household_autonomy(parent,now=NOW)
        self.assertEqual(r["nanocan_recycling"]["state"],"PLAYER_FIRST")
        self.assertIsNone(r["nanocan_recycling"]["proposal"])

    def test_parent_context_cannot_be_spoofed_by_nested_recycling(self):
        parent={
            "schema":"betterinstincts.native-household-autonomy/v1",
            "household_ref":HH,"game_build":BUILD,"capture_ref":CAP,
            "observed_at_unix":NOW,"player_active":False,
            "sims":[sim()],"nanocan_recycling":visit(household_ref="household:other"),
        }
        with self.assertRaisesRegex(AutonomyModerationError,"NANOCAN_CONTEXT_MISMATCH"):
            evaluate_native_household_autonomy(parent,now=NOW)
