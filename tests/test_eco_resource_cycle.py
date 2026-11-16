"""Adversarial, fully offline eco-material cycle regression tests."""
from __future__ import annotations

import copy
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from betterinstincts import house_state
from betterinstincts.host_listener import activate, tick
from betterinstincts.career_service import evaluate_green_technician_daily_task
from betterinstincts.eco_resource_cycle import (
    EcoResourceCycleError, plan_eco_fabrication, plan_fertilizer_sources,
)
from betterinstincts.fertilizer_workflow import evaluate_fertilizer_workflow
from betterinstincts.host_stack import evaluate_turn
from tests.test_lot_mutation_preservation import observed_two_story_lot
from tests.test_ui_mode import VERSION, idle, observation

NOW = 1_000_000.0
REF = "capture:eco1"
NEEDS = dict(hunger=.95, energy=.95, fun=.95, social=.95, bladder=.95, hygiene=.95)


def base(schema):
    return {
        "schema": schema, "capture_ref": REF, "observed_at_unix": NOW,
        "sim_ref": "sim:main", "scene_verified": True,
        "queue_verified": True, "player_directed": False, "needs_safe": True,
    }


def source(ref="source:surplus", kind="HARVESTED_PRODUCE", **changes):
    row = {
        "source_ref": ref, "kind": kind, "quantity": 3,
        "reserve_quantity": 0, "unit_opportunity_cost": 0,
        "unit_cash_cost": 0, "available": True, "player_reserved": False,
        "action_id": "COLLECT_FERTILIZER", "target_ref": "plant:surplus",
        "capture_ref": REF,
    }
    row.update(changes)
    return row


def fert(**changes):
    row = dict(base("betterinstincts.fertilizer-sourcing/v1"),
               deficit_units=2, cash=100, cash_reserve=50, sources=[source()])
    row.update(changes)
    return row


def recipe(**changes):
    row = {
        "recipe_id": "FABRICATED_ECO_UPGRADE_PART", "bits_required": 15,
        "pieces_required": 10, "min_skill": 1, "unlocked": True,
        "available": True, "station_ref": "fabricator:community",
        "capture_ref": REF,
    }
    row.update(changes)
    return row


def recyclable(ref="item:trash", klass="TRASH", **changes):
    row = {
        "item_ref": ref, "source_class": klass, "quantity": 1,
        "reserve_quantity": 0, "unit_opportunity_cost": 0,
        "capture_ref": REF, "available": True, "recycle_eligible": True,
        "protected": False, "player_reserved": False,
        "required_elsewhere": False, "unique": False,
    }
    row.update(changes)
    return row


def outcome(ref, klass, bits, pieces, value=0, **changes):
    row = {
        "outcome_ref": ref, "source_class": klass, "bits_gained": bits,
        "pieces_gained": pieces, "consumed_value": value,
        "player_interrupted": False, "game_build": "build:observed",
        "sim_ref": "sim:main", "before_ref": ref + ":before",
        "after_ref": ref + ":after",
    }
    row.update(changes)
    return row


def eco(**changes):
    row = dict(base("betterinstincts.eco-fabrication/v1"),
               career_track="GREEN_TECHNICIAN",
               daily_task="FABRICATE_ECO_UPGRADE_PART",
               daily_task_status="PENDING",
               game_build="build:observed", fabrication_skill=1,
               bits=0, pieces=0, recipes=[recipe()],
               recycler_available=True, fabricator_available=True,
               recyclable_items=[recyclable()], recycle_outcomes=[])
    row.update(changes)
    return row


class FertilizerSourcingTests(unittest.TestCase):
    def test_surplus_first_and_no_hidden_effect(self):
        row = fert(sources=[source("source:purchase", "GARDEN_STALL",
                                   unit_cash_cost=4, purchase_reviewed=True),
                            source("source:surplus")])
        saved = copy.deepcopy(row)
        out = plan_fertilizer_sources(row, capture_ref=REF, now=NOW)
        self.assertEqual(out["gate"], "FERTILIZER_SOURCE_READY")
        self.assertEqual(out["next_actions"][0]["source_ref"], "source:surplus")
        self.assertEqual(out["next_actions"][0]["quantity"], 2)
        self.assertFalse(out["dispatch_authorized"])
        self.assertEqual(row, saved)

    def test_unreviewed_purchase_and_reserves_never_consumed(self):
        for src in (source(unit_cash_cost=10),
                    source(unit_cash_cost=70, purchase_reviewed=True),
                    source(quantity=1, reserve_quantity=1),
                    source(player_reserved=True),
                    source(available=False),
                    source(capture_ref="capture:old")):
            with self.subTest(source=src):
                out = plan_fertilizer_sources(fert(sources=[src]),
                                              capture_ref=REF, now=NOW)
                self.assertEqual(out["gate"], "FERTILIZER_SOURCE_UNKNOWN_OR_UNAFFORDABLE")
                self.assertFalse(out["next_actions"])

    def test_partial_affordable_purchase_and_reserve_preservation(self):
        # Three units cost 24, but the reserved household money leaves only 20.
        row = fert(deficit_units=3, cash=80, cash_reserve=60,
                   sources=[source("source:stall", "GARDEN_STALL",
                                   unit_cash_cost=8, purchase_reviewed=True)])
        out = plan_fertilizer_sources(row, capture_ref=REF, now=NOW)
        self.assertEqual(out["gate"], "FERTILIZER_SOURCE_READY")
        self.assertEqual(out["next_actions"][0]["quantity"], 2)
        self.assertLessEqual(8 * out["units_planned"], row["cash"] - row["cash_reserve"])
        self.assertFalse(out["dispatch_authorized"])

    def test_extreme_money_and_timestamp_fail_as_typed_validation(self):
        enormous = 10**10000
        for row in (fert(cash=enormous), fert(cash_reserve=enormous),
                    fert(sources=[source(unit_cash_cost=enormous)]),
                    fert(observed_at_unix=enormous)):
            with self.subTest(field=str(list(row.keys())[-1])):
                try:
                    out = plan_fertilizer_sources(row, capture_ref=REF, now=NOW)
                except EcoResourceCycleError:
                    continue
                self.assertEqual(out["gate"], "FERTILIZER_REOBSERVE")
        out = plan_fertilizer_sources(fert(), capture_ref=REF, now=enormous)
        self.assertEqual(out["gate"], "FERTILIZER_REOBSERVE")
        self.assertFalse(out["next_actions"])

    def test_sourcing_rejects_a_different_sim_or_false_parent_deficit(self):
        workflow = {
            "schema": "betterinstincts.fertilizer-workflow/v1",
            "capture_ref": REF, "observed_at_unix": NOW,
            "sim_ref": "sim:main", "actor_verified": True, "inventory_verified": True,
            "transfer_authorized": False,
            "plants": [{"target_ref": "plant:a", "state": "PENDING",
                        "fertilize_ready": True}], "supplies": [],
        }
        workflow["sourcing"] = fert(deficit_units=1, sim_ref="sim:other")
        with self.assertRaisesRegex(Exception, "FERTILIZER_SOURCE_ACTOR_MISMATCH"):
            evaluate_fertilizer_workflow(workflow, [], capture_ref=REF, now=NOW)
        workflow["sourcing"] = fert(deficit_units=9)
        with self.assertRaisesRegex(Exception, "FERTILIZER_SOURCE_DEFICIT_MISMATCH"):
            evaluate_fertilizer_workflow(workflow, [], capture_ref=REF, now=NOW)

    def test_stale_player_unknown_needs_and_done(self):
        for change, gate in (
            ({"observed_at_unix": NOW - 181}, "FERTILIZER_REOBSERVE"),
            ({"player_directed": True}, "FERTILIZER_PLAYER_FIRST"),
            ({"needs_safe": None}, "FERTILIZER_NEEDS_FIRST"),
        ):
            with self.subTest(change=change):
                out = plan_fertilizer_sources(fert(**change), capture_ref=REF, now=NOW)
                self.assertEqual(out["gate"], gate)
                self.assertFalse(out["next_actions"])
        self.assertEqual(
            plan_fertilizer_sources(fert(deficit_units=0),
                                    capture_ref=REF, now=NOW)["gate"],
            "FERTILIZER_SUPPLY_READY",
        )

    def test_existing_gardening_pocket_deficit_integrates_without_change_to_legacy(self):
        workflow = {
            "schema": "betterinstincts.fertilizer-workflow/v1",
            "capture_ref": REF, "observed_at_unix": NOW,
            "sim_ref": "sim:main", "actor_verified": True, "inventory_verified": True,
            "transfer_authorized": False,
            "plants": [{"target_ref": "plant:a", "state": "PENDING",
                        "fertilize_ready": True}],
            "supplies": [],
        }
        self.assertEqual(
            evaluate_fertilizer_workflow(workflow, [], capture_ref=REF, now=NOW)["gate"],
            "FERTILIZER_SUPPLY_REQUIRED",
        )
        workflow["sourcing"] = fert(deficit_units=1)
        out = evaluate_fertilizer_workflow(workflow, [], capture_ref=REF, now=NOW)
        self.assertEqual(out["gate"], "FERTILIZER_SOURCE_ACTION_READY")
        self.assertEqual(out["next_actions"][0]["quantity"], 1)
        self.assertFalse(out["dispatch_authorized"])

    def test_duplicate_source_or_bad_amount_denied(self):
        for sources in ([source(), source()], [source(quantity=True)],
                        [source(reserve_quantity=8)]):
            with self.subTest(sources=sources), self.assertRaises(EcoResourceCycleError):
                plan_fertilizer_sources(fert(sources=sources), capture_ref=REF, now=NOW)


class CareerFabricationTests(unittest.TestCase):
    def test_exact_green_technician_recipe_not_arbitrary_product(self):
        row = eco(bits=15, pieces=10, recipes=[
            recipe(recipe_id="CHAIR", bits_required=1, pieces_required=1),
            recipe()])
        out = evaluate_green_technician_daily_task(row, capture_ref=REF, now=NOW)
        self.assertEqual(out["gate"], "ECO_FABRICATE_READY")
        self.assertEqual(out["next_actions"][0]["recipe_id"], "FABRICATED_ECO_UPGRADE_PART")
        self.assertFalse(out["dispatch_authorized"])

    def test_recipe_not_observed_locked_or_station_absent(self):
        for delta in (
            {"recipes": []},
            {"recipes": [recipe(unlocked=False)]},
            {"fabrication_skill": 0},
            {"fabricator_available": False},
            {"recipes": [recipe(available=False)]},
        ):
            with self.subTest(delta=delta):
                out = plan_eco_fabrication(eco(bits=15, pieces=10, **delta),
                                           capture_ref=REF, now=NOW)
                self.assertFalse(out["next_actions"])
                self.assertNotEqual(out["gate"], "ECO_FABRICATE_READY")

    def test_safe_recycling_cold_start_never_invents_yield(self):
        out = plan_eco_fabrication(eco(), capture_ref=REF, now=NOW)
        self.assertEqual(out["shortfall"], {"bits": 15, "pieces": 10})
        self.assertEqual(out["gate"], "ECO_RECYCLE_CANDIDATE")
        self.assertTrue(out["next_actions"][0]["measurement_trial"])
        self.assertFalse(out["dispatch_authorized"])

    def test_empirical_yields_prefer_measured_efficient_class(self):
        out = plan_eco_fabrication(eco(recyclable_items=[
            recyclable(), recyclable("item:metal", "SCRAP", unit_opportunity_cost=1),
        ], recycle_outcomes=[
            outcome("proof:a", "SCRAP", 10, 10),
            outcome("proof:b", "SCRAP", 10, 10),
        ]), capture_ref=REF, now=NOW)
        self.assertEqual(out["gate"], "ECO_RECYCLE_CANDIDATE")
        self.assertEqual(out["next_actions"][0]["item_ref"], "item:metal")
        self.assertFalse(out["next_actions"][0]["measurement_trial"])
        self.assertTrue(out["ranking"][0]["decision_grade"])

    def test_no_protected_unique_player_reserved_or_unmeasured_valuable_recycling(self):
        for change in ({"protected": True}, {"player_reserved": True},
                       {"unique": True}, {"required_elsewhere": True},
                       {"reserve_quantity": 1}, {"recycle_eligible": False},
                       {"source_class": "UNMEASURED", "unit_opportunity_cost": 30}):
            with self.subTest(change=change):
                row = eco(recyclable_items=[recyclable(**change)])
                out = plan_eco_fabrication(row, capture_ref=REF, now=NOW)
                self.assertEqual(out["gate"], "ECO_SAFE_RECYCLABLE_SOURCE_REQUIRED")
                self.assertFalse(out["next_actions"])

    def test_source_failure_never_fabricates_or_recycles(self):
        for change in ({"player_directed": True}, {"needs_safe": False},
                       {"observed_at_unix": NOW - 181},
                       {"capture_ref": "capture:stale"}):
            with self.subTest(change=change):
                out = plan_eco_fabrication(eco(**change), capture_ref=REF, now=NOW)
                self.assertFalse(out["next_actions"])
                self.assertFalse(out["dispatch_authorized"])

    def test_same_evidence_pair_cannot_be_counted_twice(self):
        first = outcome("proof:a", "SCRAP", 10, 10)
        second = outcome("proof:b", "SCRAP", 10, 10,
                         before_ref=first["before_ref"],
                         after_ref=first["after_ref"])
        with self.assertRaisesRegex(EcoResourceCycleError, "CAPTURE_REPLAY"):
            plan_eco_fabrication(eco(recycle_outcomes=[first, second]),
                                 capture_ref=REF, now=NOW)

    def test_missing_patch_cannot_create_recycling_training_grade(self):
        first = outcome("proof:a", "SCRAP", 10, 10, game_build=None)
        second = outcome("proof:b", "SCRAP", 10, 10, game_build=None)
        out = plan_eco_fabrication(eco(game_build=None, recycle_outcomes=[first, second]),
                                   capture_ref=REF, now=NOW)
        self.assertEqual(out["gate"], "ECO_BUILD_UNVERIFIED")
        self.assertEqual(out["ranking"], [])
        self.assertFalse(out["next_actions"])

    def test_career_completion_or_unknown_status_does_not_refabricate(self):
        for status, gate in (("COMPLETE", "ECO_CAREER_TASK_COMPLETE"),
                             (None, "ECO_CAREER_TASK_STATUS_UNKNOWN"),
                             ("UNKNOWN", "ECO_CAREER_TASK_STATUS_UNKNOWN")):
            with self.subTest(status=status):
                out = plan_eco_fabrication(
                    eco(bits=15, pieces=10, daily_task_status=status),
                    capture_ref=REF, now=NOW
                )
                self.assertEqual(out["gate"], gate)
                self.assertEqual(out["next_actions"], [])

    def test_outcome_replay_and_invalid_yields_denied(self):
        a = outcome("proof:a", "TRASH", 10, 10)
        for rows in ([a, a], [outcome("proof:a", "TRASH", True, 1)]):
            with self.subTest(rows=rows), self.assertRaises(EcoResourceCycleError):
                plan_eco_fabrication(eco(recycle_outcomes=rows),
                                     capture_ref=REF, now=NOW)

    def test_host_stack_career_seam_and_player_override(self):
        row = eco(bits=15, pieces=10)
        # A real current host call is allowed to calculate a recommendation,
        # not to execute a native effect or click a UI.
        for player in (False, True):
            out = evaluate_turn(NEEDS, eco_fabrication={
                **row, "observed_at_unix": __import__("time").time(),
            }, capture_ref=REF, viewport={"state": "VIEWPORT_OK"},
                player_directed=player, location_kind="home")
            advice = out["eco_fabrication"]
            self.assertIsNotNone(advice)
            self.assertFalse(advice["dispatch_authorized"])
            self.assertEqual(advice["gate"],
                             "ECO_PLAYER_FIRST" if player else "ECO_FABRICATE_READY")


def scoped_eco(*, bits=0, pieces=0, mode="LIVE", lot_ref="Eco test lot"):
    row = eco(game_build=VERSION, household_ref="household:eco", sim_ref="sim:test",
              recyclable_items=[])
    context = dict(capture_ref=REF, household_ref=row["household_ref"], game_build=VERSION,
                   lot_ref=lot_ref)
    row["recipes"] = [recipe(**context)]
    row["sourcing"] = {
        **context, "session_ref": "eco-sourcing", "effect_pending": False,
        "lab_save_verified": True, "eco_lifestyle": True, "mode": mode,
        "balances": {**context, "bits": bits, "pieces": pieces, "evidence_ref": "proof:wallet",
                     "source": "HOUSEHOLD_FUNDS_HOVER"},
        "recycler": {**context, "available": True, "target_ref": "recycler:current"},
    }
    return row, context


def opportunity(context, kind, **changes):
    return {**context, "opportunity_ref": f"option:{kind}", "kind": kind,
            "sim_ref": "sim:test", "target_ref": "object:source", "interaction_ref": "menu:source",
            "available": True, "attempt_state": "NOT_ATTEMPTED", **changes}


class HouseholdEcoSourcingTests(unittest.TestCase):
    def evaluate(self, row, **kwargs):
        return plan_eco_fabrication(row, capture_ref=REF, now=NOW, **kwargs)

    def test_actual_balances_and_recipe_cost_control_fabrication(self):
        row, _ = scoped_eco(bits=15, pieces=10)
        self.assertEqual(self.evaluate(row)["gate"], "ECO_FABRICATE_READY")
        balances = row["sourcing"]["balances"]
        for delta in ({"household_ref": "household:other"}, {"capture_ref": "old:cap"},
                      {"lot_ref": "Another lot"}, {"bits": True}, {"source": "HUD_CASH_ONLY"}):
            with self.subTest(delta=delta):
                row["sourcing"]["balances"] = {**balances, **delta}
                self.assertEqual(self.evaluate(row)["gate"], "ECO_OBSERVE_HOUSEHOLD_BALANCE")
        row["sourcing"]["balances"] = balances
        row["recipes"][0]["bits_required"] = 14
        self.assertEqual(self.evaluate(row)["gate"], "ECO_RECIPE_COST_MISMATCH")

    def test_yield_selection_uses_deficit_and_genuine_consumption_receipts(self):
        row, scope = scoped_eco(bits=0, pieces=10)
        def candidate(ref, kind):
            return recyclable(ref, kind, **scope, inventory_scope="HOUSEHOLD",
                              discardable_verified=True, in_current_recycler_picker=True,
                              recycler_ref="recycler:current", attempt_state="NOT_ATTEMPTED")
        def receipt(ref, kind, bits, pieces, **overrides):
            return outcome(ref, kind, bits, pieces, **{**scope, "sim_ref": "sim:test",
                           "method": "RECYCLER", "outcome_verified": True,
                           "dispatch_ref": f"dispatch:{ref}", **overrides})
        row["recyclable_items"] = [
            candidate("item:organic", "ORGANIC_WASTE"),
            candidate("item:circuit", "SALVAGE_ELECTRONICS"),
        ]
        row["recycle_outcomes"] = [
            receipt("proof:a", "ORGANIC_WASTE", 0, 18),
            receipt("proof:b", "ORGANIC_WASTE", 0, 19),
            receipt("proof:c", "SALVAGE_ELECTRONICS", 5, 0),
            receipt("proof:d", "SALVAGE_ELECTRONICS", 7, 0),
            receipt("proof:e", "SALVAGE_ELECTRONICS", 500, 0, method="DEBUG_SIM_BITS"),
            receipt("proof:f", "SALVAGE_ELECTRONICS", 800, 0, household_ref="household:other"),
        ]
        result = self.evaluate(row)
        self.assertEqual(result["shortfall"], {"bits": 15, "pieces": 0})
        self.assertEqual(result["next_actions"][0]["item_ref"], "item:circuit")
        self.assertEqual(result["next_actions"][0]["recycler_ref"], "recycler:current")
        self.assertEqual(result["ranking"][1]["average_bits"], 6)
        row["recyclable_items"][1].update(inventory_scope="PERSONAL", sim_ref="sim:other")
        self.assertEqual(self.evaluate(row)["gate"], "ECO_SAFE_RECYCLABLE_SOURCE_REQUIRED")
        row["recycle_outcomes"][3]["dispatch_ref"] = row["recycle_outcomes"][2]["dispatch_ref"]
        with self.assertRaisesRegex(EcoResourceCycleError, "DISPATCH_REPLAY"):
            self.evaluate(row)

    def test_natural_targets_first_and_opt_in_debug_exact_menus(self):
        row, scope = scoped_eco(bits=0, pieces=10)
        source = row["sourcing"]
        source.update(natural_sources_exhausted=True, debug_opt_in=True,
                      testingcheats_enabled=True, opportunities=[
            opportunity(scope, "RUMMAGE"),
            opportunity(scope, "DIVE_FOR_DEALS"),
            opportunity(scope, "DEBUG_SIM_BITS", target_ref="sim:test",
                        menu_path=["Give Bucks", "Recycle Bits"]),
            opportunity(scope, "DEBUG_FABRICATOR_BOTH", target_kind="HOME_FABRICATOR",
                        menu_path=["Give Bits and Pieces"]),
        ])
        self.assertEqual(self.evaluate(row)["next_actions"][0]["action_id"], "RUMMAGE")
        source["opportunities"][0]["attempt_state"] = "RECONCILED"
        self.assertEqual(self.evaluate(row)["next_actions"][0]["action_id"], "DIVE_FOR_DEALS")
        source["opportunities"][1]["attempt_state"] = "RECONCILED"
        result = self.evaluate(row)
        self.assertEqual(result["gate"], "ECO_DEBUG_RESOURCE_CANDIDATE")
        self.assertEqual(result["next_actions"][0]["community_reported_delta"], {"bits": 50, "pieces": 50})
        self.assertFalse(result["next_actions"][0]["training_eligible"])
        source["opportunities"].pop()
        self.assertEqual(self.evaluate(row)["next_actions"][0]["action_id"], "DEBUG_SIM_BITS")
        source["opportunities"][-1]["menu_path"][-1] = "Recycle Pieces"
        self.assertFalse(self.evaluate(row)["next_actions"])
        source["opportunities"][-1]["menu_path"][-1] = "Recycle Bits"
        source["debug_opt_in"] = False
        self.assertFalse(self.evaluate(row)["next_actions"])
        source["effect_pending"] = True
        self.assertEqual(self.evaluate(row)["gate"], "ECO_RECONCILE_PREVIOUS_EFFECT")

    def test_community_recycler_requires_current_free_use(self):
        row, scope = scoped_eco()
        row["recycler_available"] = False
        route = opportunity(scope, "USE_COMMUNITY_RECYCLER", free_use_verified=True)
        row["sourcing"]["opportunities"] = [route]
        self.assertEqual(self.evaluate(row)["next_actions"][0]["action_id"], "USE_COMMUNITY_RECYCLER")
        route["free_use_verified"] = False
        self.assertEqual(self.evaluate(row)["gate"], "ECO_RECYCLER_ACCESS_REQUIRED")
        row["sourcing"]["natural_sources_exhausted"] = True
        result = self.evaluate(row)
        self.assertEqual(result["catalog_query"], "Guntdach Home Recycler")
        self.assertTrue(result["requires_budget_and_whole_lot_checkpoint"])
        self.assertFalse(result["next_actions"])

    def test_catalog_purchase_only_for_stock_with_price_reserve_and_backup(self):
        model, manifest = observed_two_story_lot()
        row, scope = scoped_eco(mode="BUY", lot_ref=model["lot_id"])
        source = row["sourcing"]
        source.update(objective="STOCK_ECO_UPGRADE_PART", stock_shortfall_verified=True,
                      catalog_purchase_opt_in=True)
        self.assertEqual(self.evaluate(row)["gate"], "ECO_SOURCE_SCOPE_UNVERIFIED")
        row["daily_task"] = None
        self.assertEqual(self.evaluate(row)["catalog_query"], "Eco-Upgrade Part")
        item = source["catalog_part"] = {
            **scope, "definition_id": "ECO_UPGRADE_PART", "label": "Eco-Upgrade Part",
            "available": True, "catalog_ref": "catalog:part", "unit_price": 50, "funds": 1_500_000,
        }
        self.assertEqual(self.evaluate(row, lot_model=model)["action"], "VERIFY_WHOLE_LOT_BUILD_CHECKPOINT")
        with tempfile.TemporaryDirectory() as tmp, patch.object(house_state, "ROOT", Path(tmp)):
            model = house_state.attest_library_save(
                model, building_id=model["lot_id"], library_item_name="Eco checkpoint",
                capture_ref="capture:eco-library", operator_confirmed=True, lot_manifest=manifest,
            )
            result = self.evaluate(row, lot_model=model)
            self.assertEqual(result["gate"], "ECO_PARTS_STOCK_PURCHASE_CANDIDATE")
            self.assertEqual(result["next_actions"][0]["quantity"], 1)
            self.assertFalse(result["dispatch_authorized"])
            for delta in ({"funds": 1_000_000}, {"unit_price": 51}, {"label": "Common Upgrade Part"}):
                source["catalog_part"] = {**item, **delta}
                self.assertFalse(self.evaluate(row, lot_model=model)["next_actions"])

    def test_listener_binds_scope_and_feeds_existing_host_turn(self):
        row, scope = scoped_eco()
        row["observed_at_unix"] = time.time()
        row["sourcing"]["opportunities"] = [opportunity(scope, "RUMMAGE")]
        with tempfile.TemporaryDirectory() as tmp, patch(
            "betterinstincts.host_listener.ROOT", Path(tmp)
        ), patch("betterinstincts.host_listener.OUTPUT", Path(tmp) / "dist" / "host-listener"):
            activate("eco-sourcing")
            raw = {**observation("LIVE"), "capture_ref": REF, "active_lot_id": scope["lot_ref"],
                   "eco_fabrication": row}
            receipt = tick("eco-sourcing", raw, presence_probe=idle())
            self.assertEqual(receipt["host_stack"]["next_gate"], "ECO_NATURAL_SOURCE_CANDIDATE")
            self.assertFalse(receipt["execute_clicks"])
            wrong_sim = tick("eco-sourcing", {**raw, "actor_ref": "sim:other"}, presence_probe=idle())
            self.assertEqual(wrong_sim["host_stack"]["eco_fabrication"]["gate"], "ECO_SOURCE_SCOPE_UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
