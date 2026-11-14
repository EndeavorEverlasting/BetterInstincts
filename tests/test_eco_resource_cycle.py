"""Adversarial, fully offline eco-material cycle regression tests."""
from __future__ import annotations

import copy
import unittest

from betterinstincts.career_service import evaluate_green_technician_daily_task
from betterinstincts.eco_resource_cycle import (
    EcoResourceCycleError, plan_eco_fabrication, plan_fertilizer_sources,
)
from betterinstincts.fertilizer_workflow import evaluate_fertilizer_workflow
from betterinstincts.host_stack import evaluate_turn

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


if __name__ == "__main__":
    unittest.main()
