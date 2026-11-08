"""P82 measures for build/buy catalog ranking."""
import json
import unittest
from pathlib import Path

from betterinstincts.build_optimize import (
    BuildOptimizeError,
    best_pools,
    evaluate_build_optimize,
    evaluate_category_pools,
    load_contract,
    project_stack,
    rank_items,
    resolve_item,
)
from betterinstincts.host_stack import evaluate_turn

ROOT = Path(__file__).resolve().parents[1]


class BuildOptimizeTests(unittest.TestCase):
    def test_contract_loads_and_has_observed_brick(self):
        cfg = load_contract()
        self.assertEqual(cfg["schema"], "betterinstincts.build-optimize/v1")
        brick = resolve_item("Brick & Plaster", cfg["catalog"])
        self.assertIsNotNone(brick)
        self.assertEqual(brick["lot_environment_gain"], 1)
        self.assertEqual(brick["eco_footprint_industrial"], 1)

    def test_maximize_env_prefers_dual_yield_over_env_only(self):
        ranked = rank_items(
            "MAXIMIZE_ENV",
            category="wall_covering",
            owned_packs=["base", "GP02", "EP20"],
            limit=3,
        )
        self.assertTrue(ranked)
        self.assertEqual(ranked[0]["lot_environment_gain"], 2)
        self.assertEqual(ranked[0]["eco_footprint_green"], 2)
        self.assertIn(
            ranked[0]["id"],
            {"wall.veins_of_gold_marble", "wall.working_bricks"},
        )

    def test_maximize_env_attested_unknown_pack_still_ranks(self):
        ranked = rank_items(
            "MAXIMIZE_ENV",
            category="wall_covering",
            owned_packs=["base"],
            limit=3,
        )
        self.assertTrue(ranked)
        self.assertEqual(ranked[0]["lot_environment_gain"], 2)
        self.assertEqual(ranked[0]["eco_footprint_green"], 2)
        self.assertNotEqual(ranked[0]["id"], "wall.matchstick_magic")

    def test_maximize_green_prefers_dual_yield_excludes_industrial(self):
        ranked = rank_items(
            "MAXIMIZE_GREEN",
            category="wall_covering",
            owned_packs=["base", "EP09", "EP19"],
            limit=5,
        )
        self.assertTrue(ranked)
        self.assertEqual(ranked[0]["eco_footprint_green"], 2)
        self.assertEqual(ranked[0]["lot_environment_gain"], 2)
        self.assertIn(
            ranked[0]["id"],
            {"wall.veins_of_gold_marble", "wall.working_bricks"},
        )
        ids = {r["id"] for r in ranked}
        self.assertNotIn("wall.brick_and_plaster", ids)

    def test_maximize_industrial_selects_brick(self):
        ranked = rank_items(
            "MAXIMIZE_INDUSTRIAL",
            category="wall_covering",
            owned_packs=["base"],
            limit=3,
        )
        self.assertEqual(ranked[0]["id"], "wall.brick_and_plaster")
        self.assertGreaterEqual(ranked[0]["eco_footprint_industrial"], 1)

    def test_maximize_yield_picks_dual_max(self):
        ranked = rank_items(
            "MAXIMIZE_YIELD",
            category="wall_covering",
            owned_packs=["base", "EP09", "GP02", "EP19", "EP20"],
            limit=5,
        )
        self.assertTrue(ranked)
        best = ranked[0]
        self.assertEqual(best["lot_environment_gain"], 2)
        self.assertEqual(best["eco_footprint_green"], 2)
        # Dual 2/2 score must beat Env-only 2 (Matchstick) and Green-only 2 (Log Siding).
        matchstick = next(r for r in ranked if r["id"] == "wall.matchstick_magic")
        self.assertGreater(best["objective_score"], matchstick["objective_score"])
        ids = {r["id"] for r in ranked}
        self.assertNotIn("wall.brick_and_plaster", ids)

    def test_balanced_excludes_industrial_brick(self):
        ranked = rank_items(
            "BALANCED_ENV_GREEN",
            category="wall_covering",
            owned_packs=["base", "EP09", "GP02"],
            limit=5,
        )
        ids = {r["id"] for r in ranked}
        self.assertNotIn("wall.brick_and_plaster", ids)
        self.assertTrue(any(r["lot_environment_gain"] >= 1 for r in ranked))
        self.assertIn(
            ranked[0]["id"],
            {"wall.veins_of_gold_marble", "wall.working_bricks"},
        )

    def test_stacking_multiplies_panels(self):
        cfg = load_contract()
        brick = resolve_item("brick_and_plaster", cfg["catalog"])
        proj = project_stack(brick, panels=20, objective="MAXIMIZE_INDUSTRIAL", cfg=cfg)
        self.assertEqual(proj["eco_footprint_industrial_total"], 20)
        self.assertEqual(proj["lot_environment_gain_total"], 20)

    def test_budget_filters_cost(self):
        ranked = rank_items(
            "MAXIMIZE_INDUSTRIAL",
            category="wall_covering",
            owned_packs=["base"],
            budget=5,
            limit=5,
        )
        self.assertEqual(ranked, [])

    def test_player_directed_yields(self):
        result = evaluate_build_optimize(
            "MAXIMIZE_ENV",
            owned_packs=["base", "GP02"],
            player_directed=True,
        )
        self.assertEqual(result["state"], "YIELD_TO_PLAYER")
        self.assertEqual(result["picks"], [])

    def test_evaluate_plan_ready_execute_false(self):
        result = evaluate_build_optimize(
            "MAXIMIZE_YIELD",
            owned_packs=["base", "GP02", "EP20"],
            panels=16,
        )
        self.assertEqual(result["state"], "BUILD_OPTIMIZE_PLAN_READY")
        self.assertEqual(result["best"]["lot_environment_gain"], 2)
        self.assertEqual(result["best"]["eco_footprint_green"], 2)
        self.assertFalse(result["plan"]["execute_allowed"])
        self.assertEqual(result["projection"]["lot_environment_gain_total"], 32)
        self.assertEqual(result["projection"]["eco_footprint_green_total"], 32)

    def test_resolve_veins_and_working_bricks(self):
        cfg = load_contract()
        veins = resolve_item("Veins of Gold Marble Walls", cfg["catalog"])
        bricks = resolve_item("working bricks", cfg["catalog"])
        self.assertIsNotNone(veins)
        self.assertIsNotNone(bricks)
        self.assertEqual(veins["lot_environment_gain"], 2)
        self.assertEqual(veins["eco_footprint_green"], 2)
        self.assertEqual(bricks["lot_environment_gain"], 2)
        self.assertEqual(bricks["eco_footprint_green"], 2)

    def test_unknown_objective_fails_closed(self):
        with self.assertRaises(BuildOptimizeError):
            rank_items("MAXIMIZE_EVERYTHING", owned_packs=["base"])

    def test_buy_category_seed_ranks(self):
        ranked = rank_items(
            "MAXIMIZE_ENV",
            category="buy_object",
            owned_packs=["base"],
            limit=3,
        )
        self.assertEqual(ranked[0]["id"], "buy.placeholder_decor_env1")

    def test_contract_json_roundtrip_size(self):
        raw = (ROOT / "contracts" / "build-optimize.v1.json").read_text(encoding="utf-8")
        data = json.loads(raw)
        self.assertIn("Brick & Plaster", json.dumps(data))

    def test_host_stack_build_optimize_gate(self):
        needs = {
            "hunger": 0.8,
            "bladder": 0.8,
            "energy": 0.8,
            "hygiene": 0.8,
            "fun": 0.8,
            "social": 0.8,
        }
        out = evaluate_turn(
            needs,
            available_objects=("fridge", "toilet", "bed", "shower", "computer", "chair"),
            build_objective="MAXIMIZE_YIELD",
            build_owned_packs=("base", "GP02", "EP20"),
            build_panels=10,
            build_or_buy_mode=True,
        )
        self.assertEqual(out["next_gate"], "BUILD_OPTIMIZE_EVALUATE_ONLY")
        self.assertEqual(out["build_optimize"]["best"]["lot_environment_gain"], 2)
        self.assertEqual(out["build_optimize"]["best"]["eco_footprint_green"], 2)
        self.assertFalse(out["fallback"]["execute_allowed"])
        self.assertIsNotNone(out["build_optimize"].get("pools"))
        self.assertIn("wall_covering", out["build_optimize"]["pools"]["categories"])

    def test_best_pools_cover_categories_and_axes(self):
        pools = best_pools(owned_packs=["base", "EP09", "GP02", "EP19", "EP20"], pool_size=2)
        cats = pools["categories"]
        self.assertIn("wall_covering", cats)
        self.assertIn("appliance", cats)
        self.assertIn("lighting", cats)
        wall_env = cats["wall_covering"]["lot_environment_gain"][0]
        self.assertEqual(wall_env["lot_environment_gain"], 2)
        self.assertEqual(wall_env["eco_footprint_green"], 2)
        wall_yield = cats["wall_covering"]["combined_env_green"][0]
        self.assertIn(
            wall_yield["id"],
            {"wall.veins_of_gold_marble", "wall.working_bricks"},
        )
        fridge = cats["appliance"]["bill_power"][0]
        self.assertEqual(fridge["id"], "appliance.efficient_fridge")
        light = cats["lighting"]["bill_power"][0]
        self.assertEqual(light["id"], "light.efficient_env1")

    def test_null_bill_axis_does_not_win_via_zero(self):
        pools = best_pools(owned_packs=["base"], pool_size=5)
        # Walls declare bill_power=null — wall_covering must omit bill_power pool.
        self.assertNotIn("bill_power", pools["categories"].get("wall_covering", {}))

    def test_bill_savings_prefers_efficient_appliance(self):
        ranked = rank_items(
            "MAXIMIZE_BILL_SAVINGS",
            category="appliance",
            owned_packs=["base"],
            limit=3,
        )
        self.assertEqual(ranked[0]["id"], "appliance.efficient_fridge")
        self.assertLess(ranked[0]["bill_burden"], ranked[1]["bill_burden"])

    def test_evaluate_category_pools_ready(self):
        result = evaluate_category_pools(owned_packs=["base", "EP09"])
        self.assertEqual(result["state"], "BUILD_YIELD_POOLS_READY")
        self.assertFalse(result["plan"]["execute_allowed"])
        self.assertTrue(result["category_summary"])
        self.assertEqual(result["microsystem"], "BUILD_YIELD")

    def test_contract_has_value_axes_and_categories(self):
        cfg = load_contract()
        self.assertEqual(cfg["version"], 2)
        self.assertIn("bill_power", cfg["value_axes"])
        self.assertIn("plumbing", cfg["categories"])
        self.assertEqual(cfg["microsystem"], "BUILD_YIELD")


if __name__ == "__main__":
    unittest.main()
