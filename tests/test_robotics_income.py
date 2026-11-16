import copy
import itertools
import unittest

from betterinstincts.autonomy_moderation import (
    AutonomyModerationError, NATIVE_SCHEMA, evaluate_native_household_autonomy,
)
from betterinstincts.robotics_income import SCHEMA

SCOPE = dict(household_ref="household:lab", game_build="1.121.361.1020", save_ref="save:lab")
CAPTURE = "capture:craft"
NOW = 200
PARTS = {"robot_salvage_part": 5, "mechanism": 1, "computer_chip": 1}


def recipe(action="quadcopter", *, parts=None, owned=False):
    parts = PARTS if parts is None else parts
    prices = {"robot_salvage_part": 10, "mechanism": 40, "computer_chip": 40}
    materials = {}
    for name, n in parts.items():
        materials[name] = (
            {"buy_quantity": 0, "owned_unit_cost": prices[name], "basis_ref": "proof:" + name,
             "stock_ref": "stock:" + name}
            if owned else
            {"buy_quantity": n, "buy_unit_cost": prices[name], "price_ref": "quote:" + name}
        )
    return dict(recipe_ref=action, action_id=action, sale_channel="inventory", sim_ref="sim:roboticist",
                ingredients=parts.copy(), workstation_fee=50, other_costs=0,
                materials=materials, capture_ref=CAPTURE, quote_ref="quote:" + action)


def receipt(number, *, payout=280, offer=None, outcome="SOLD", minutes=60):
    offer = recipe() if offer is None else offer
    names = ("attempt_ref", "native_action_ref", "debit_ref", "terminal_ref", "item_ref", "sale_ref")
    refs = {name: f"{name}:{number}" for name in names}
    costs = {
        name: {"consumed_quantity": n, "consumed_cost": n * offer["materials"][name]["buy_unit_cost"],
               "basis_ref": "ledger:" + name + ":" + str(number)}
        for name, n in offer["ingredients"].items()
    }
    return dict(**SCOPE, **refs, recipe_ref=offer["recipe_ref"], sale_channel=offer["sale_channel"],
                origin="NATIVE_RESPONDER", attributed=True, payout=payout, outcome=outcome,
                workstation_fee=offer["workstation_fee"], other_costs=offer["other_costs"],
                materials=costs, ingredients=offer["ingredients"].copy(), minutes=minutes)


def candidate(action, income=1):
    return dict(action_id=action, income_kind="ROBOTICS_CRAFT_SALE",
                yield_proof_ref="effect:proposal", yield_by_domain={"income": income},
                available=True, native_affordance_verified=True)


def native(*, offers=None, receipts=None, funds=1_001_000, **kwargs):
    offers = [recipe()] if offers is None else offers
    return dict(
        schema=NATIVE_SCHEMA, **SCOPE, capture_ref=CAPTURE,
        observed_at_unix=NOW, player_active=False,
        sims=[dict(sim_ref="sim:roboticist", capture_ref=CAPTURE, queue_verified=True,
                   player_owned=False, player_command_present=False, policy_opt_in=True,
                   queue=[dict(action_id="idle", queue_slot_ref="slot:idle", origin="SIM_AUTONOMY",
                               origin_proof_ref="native:idle", effect_proof_ref="effect:idle",
                               yield_proof_ref="yield:idle", yield_by_domain={"fun": 0})],
                   available_actions=[candidate(p["action_id"]) for p in offers])],
        robotics_income=dict(schema=SCHEMA, **SCOPE, capture_ref=CAPTURE,
                             available_funds=funds, funds_proof_ref="wallet:current",
                             offers=offers, receipts=[] if receipts is None else receipts),
    ) | kwargs


def evaluate(**kwargs):
    result = evaluate_native_household_autonomy(native(**kwargs), now=NOW)
    offers = result["robotics_income"]["offers"]
    return next(iter(offers.values())), result["decisions"][0]


class RoboticsIncomeTests(unittest.TestCase):
    def test_display_fee_is_only_one_component(self):
        offers, decision = evaluate(receipts=[receipt(1, payout=100)])
        row = offers["quadcopter"]
        self.assertEqual((row["full_unit_cost"], row["realized_net"]), (180, -80))
        self.assertEqual(row["state"], "HOLD_NONPOSITIVE_NET")
        self.assertIsNone(decision["replacement_candidate"])

    def test_owned_material_cost_only_hits_the_profit_side(self):
        offers, _ = evaluate(offers=[recipe(owned=True)], receipts=[receipt(1)], funds=1_000_050)
        row = offers["quadcopter"]
        self.assertEqual((row["full_unit_cost"], row["upfront_cash"]), (180, 50))
        self.assertEqual(row["projected_net_per_sim_hour"], 100)
        self.assertEqual(row["state"], "POSITIVE_NET_CANDIDATE")

    def test_rate_outweighs_gross_payout_in_native_candidate_ranking(self):
        bot = recipe("gardener_bot", parts={"robot_salvage_part": 10, "mechanism": 2})
        offers, decision = evaluate(offers=[bot, recipe()], receipts=[
            receipt(1, payout=400, offer=bot, minutes=180), receipt(2, payout=280)])
        self.assertEqual(offers["gardener_bot"]["realized_net"], 170)
        self.assertEqual(decision["replacement_candidate"]["action_id"], "quadcopter")

    def test_realized_losses_and_failures_learn_without_assistance(self):
        profitable = receipt(1)
        failed = receipt(2, payout=0, outcome="FAILED")
        failed["materials"]["mechanism"].update(consumed_quantity=0, consumed_cost=0)
        before, _ = evaluate(receipts=[profitable])
        after, decision = evaluate(receipts=[profitable, failed])
        self.assertEqual(before["quadcopter"]["state"], "POSITIVE_NET_CANDIDATE")
        self.assertEqual(after["quadcopter"]["realized_net"], -40)
        self.assertEqual(after["quadcopter"]["state"], "HOLD_NONPOSITIVE_NET")
        self.assertIsNone(decision["replacement_candidate"])

    def test_break_even_and_rising_input_cost_fail_income(self):
        offers, _ = evaluate(receipts=[receipt(1, payout=180)])
        self.assertEqual(offers["quadcopter"]["state"], "HOLD_NONPOSITIVE_NET")
        raised = recipe()
        raised["materials"]["mechanism"]["buy_unit_cost"] = 220
        offers, _ = evaluate(offers=[raised], receipts=[receipt(1)])
        self.assertEqual(offers["quadcopter"]["realized_net"], 100)
        self.assertEqual(offers["quadcopter"]["projected_net_per_attempt"], -80)
        self.assertEqual(offers["quadcopter"]["state"], "HOLD_NONPOSITIVE_NET")

    def test_cannot_spend_projected_revenue_or_recovery_reserve(self):
        for funds in (535_466, 1_000_179):
            offers, decision = evaluate(receipts=[receipt(1)], funds=funds)
            self.assertEqual(offers["quadcopter"]["state"], "HOLD_HOUSEHOLD_RESERVE")
            self.assertIsNone(decision["replacement_candidate"])

    def test_incomplete_sources_and_unknown_sales_are_distinct(self):
        offer = recipe()
        del offer["materials"]["computer_chip"]
        offers, _ = evaluate(offers=[offer])
        self.assertEqual(offers["quadcopter"]["state"], "REOBSERVE_FULL_COST")
        offers, _ = evaluate()
        self.assertEqual(offers["quadcopter"]["state"], "OBSERVE_NATIVE_SALE_OR_FAILURE")
        self.assertIsNone(offers["quadcopter"]["projected_net_per_attempt"])

    def test_unrelated_cash_and_cross_scope_events_cannot_teach_margin(self):
        for change in ({"origin": "CHEAT"}, {"origin": "PLAYER"}, {"sale_channel": "retail"},
                       {"game_build": "1.120.0"}, {"household_ref": "household:other"},
                       {"save_ref": "save:other"}):
            with self.subTest(change=change):
                offers, _ = evaluate(receipts=[receipt(1) | change])
                self.assertEqual(offers["quadcopter"]["sample_count"], 0)

    def test_duplicate_and_conflicting_receipts(self):
        source = receipt(1)
        offers, _ = evaluate(receipts=[source, copy.deepcopy(source)])
        self.assertEqual(offers["quadcopter"]["sample_count"], 1)
        overlap = receipt(2) | {"sale_ref": source["sale_ref"]}
        offers, decision = evaluate(receipts=[source, overlap])
        self.assertEqual(offers["quadcopter"]["state"], "RECONCILE_NATIVE_RECEIPTS")
        self.assertIsNone(offers["quadcopter"]["realized_net"])
        self.assertIsNone(decision["replacement_candidate"])

    def test_chained_proof_collisions_are_blocked_in_every_receipt_order(self):
        quotes = [recipe(name) for name in ("quadcopter", "gardener_bot", "party_bot")]
        first, second, third = [receipt(i, offer=offer) for i, offer in enumerate(quotes)]
        second["debit_ref"] = first["debit_ref"]
        third["sale_ref"] = second["sale_ref"]
        for history in itertools.permutations([first, second, third]):
            offers, decision = evaluate(offers=quotes, receipts=list(history))
            self.assertTrue(all(o["state"] == "RECONCILE_NATIVE_RECEIPTS" for o in offers.values()))
            self.assertIsNone(decision["replacement_candidate"])

    def test_incomplete_middle_claim_blocks_every_implicated_recipe(self):
        quotes = [recipe(name) for name in ("quadcopter", "gardener_bot", "party_bot")]
        first, middle, last = [receipt(i, offer=offer) for i, offer in enumerate(quotes)]
        middle.update(attributed=False, debit_ref=first["debit_ref"], sale_ref=last["sale_ref"])
        for history in itertools.permutations([first, middle, last]):
            with self.subTest(attempts=[x["attempt_ref"] for x in history]):
                offers, decision = evaluate(offers=quotes, receipts=list(history))
                self.assertTrue(all(o["state"] == "RECONCILE_NATIVE_RECEIPTS" for o in offers.values()))
                self.assertTrue(all(o["realized_net"] is None for o in offers.values()))
                self.assertIsNone(decision["replacement_candidate"])

    def test_pending_claim_cannot_reuse_other_recipe_item_or_attempt(self):
        bot = recipe("gardener_bot")
        sold = receipt(1)
        for field in ("item_ref", "attempt_ref"):
            pending = {**receipt(2, offer=bot), "outcome": "UNSOLD", field: sold[field]}
            for history in ([sold, pending], [pending, sold]):
                with self.subTest(field=field, first=history[0]["recipe_ref"]):
                    offers, _ = evaluate(offers=[recipe(), bot], receipts=history)
                    self.assertTrue(all(o["state"] == "RECONCILE_NATIVE_RECEIPTS" for o in offers.values()))

    def test_pending_or_ambiguous_outcome_never_becomes_profit(self):
        for change in ({"outcome": "UNSOLD"}, {"attributed": False}, {"sale_ref": None}):
            offers, _ = evaluate(receipts=[receipt(1) | change])
            self.assertEqual(offers["quadcopter"]["state"], "RECONCILE_NATIVE_RECEIPTS")

    def test_pending_receipt_reconciles_only_to_the_same_native_effect(self):
        sold = receipt(1)
        unsold = sold | {"outcome": "UNSOLD"}
        offers, _ = evaluate(receipts=[unsold, sold])
        self.assertEqual(offers["quadcopter"]["state"], "POSITIVE_NET_CANDIDATE")
        self.assertEqual(offers["quadcopter"]["attempt_refs"], [sold["attempt_ref"]])
        offers, _ = evaluate(receipts=[sold, unsold | {"item_ref": "item:other"}])
        self.assertEqual(offers["quadcopter"]["state"], "RECONCILE_NATIVE_RECEIPTS")

    def test_a_cheap_different_bill_of_materials_cannot_train_this_recipe(self):
        cheaper = recipe(parts={"robot_salvage_part": 1})
        offers, _ = evaluate(receipts=[receipt(1, offer=cheaper)])
        self.assertEqual(offers["quadcopter"]["state"], "RECONCILE_NATIVE_RECEIPTS")

    def test_native_player_and_stale_guards_preserve_no_input(self):
        for change in ({"player_active": True}, {"observed_at_unix": -1}):
            result = evaluate_native_household_autonomy(native(receipts=[receipt(1)], **change),
                                                         now=NOW)
            self.assertNotIn("robotics_income", result)
            self.assertFalse(result["enqueue_allowed"])
            self.assertFalse(result["cancel_allowed"])
        obs = native(receipts=[receipt(1)])
        obs["robotics_income"]["capture_ref"] = "capture:old"
        with self.assertRaisesRegex(AutonomyModerationError, "ROBOTICS_SCOPE"):
            evaluate_native_household_autonomy(obs, now=NOW)

    def test_native_action_cannot_claim_unmeasured_robotics_income(self):
        obs = native()
        del obs["robotics_income"]
        self.assertIsNone(evaluate_native_household_autonomy(obs, now=NOW)["decisions"][0]
                          ["replacement_candidate"])

    def test_nonpositive_existing_goal_abstains_without_cancelling(self):
        obs = native(receipts=[receipt(1, payout=100)])
        sim = obs["sims"][0]
        sim["queue"][0]["interrupts_goal"] = True
        sim["active_goal"] = candidate("quadcopter") | {"active": True}
        decision = evaluate_native_household_autonomy(obs, now=NOW)["decisions"][0]
        self.assertIsNone(decision["replacement_candidate"])
        self.assertIsNone(decision["suppress_candidate"])

    def test_other_sim_cannot_use_the_quote_or_claim_owned_stock(self):
        offer = recipe(owned=True)
        offer["sim_ref"] = "sim:other"
        obs = native(offers=[offer], receipts=[receipt(1)])
        del obs["sims"][0]["available_actions"][0]["income_kind"]
        result = evaluate_native_household_autonomy(obs, now=NOW)
        offers = result["robotics_income"]["offers"]["sim:other"]
        self.assertEqual(offers["quadcopter"]["state"], "POSITIVE_NET_CANDIDATE")
        self.assertIsNone(result["decisions"][0]["replacement_candidate"])
        del offer["materials"]["mechanism"]["stock_ref"]
        offers, _ = evaluate(offers=[offer], receipts=[receipt(1)])
        self.assertEqual(offers["quadcopter"]["state"], "REOBSERVE_FULL_COST")

    def test_same_native_action_can_have_distinct_quotes_for_two_sims(self):
        first_offer = recipe(owned=True)
        second_offer = recipe() | {"sim_ref": "sim:other"}
        obs = native(offers=[first_offer, second_offer], receipts=[receipt(1)], funds=1_000_050)
        obs["sims"].append(obs["sims"][0] | {"sim_ref": "sim:other"})
        result = evaluate_native_household_autonomy(obs, now=NOW)
        offers = result["robotics_income"]["offers"]
        self.assertEqual(offers["sim:roboticist"]["quadcopter"]["state"], "POSITIVE_NET_CANDIDATE")
        self.assertEqual(offers["sim:other"]["quadcopter"]["state"], "HOLD_HOUSEHOLD_RESERVE")
        self.assertIsNotNone(result["decisions"][0]["replacement_candidate"])
        self.assertIsNone(result["decisions"][1]["replacement_candidate"])
