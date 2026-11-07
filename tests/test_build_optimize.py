"""P82 measures for build/buy catalog ranking."""
import json
import unittest
from pathlib import Path

from betterinstincts.build_optimize import (
    BuildOptimizeError,
    evaluate_build_optimize,
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

    def test_maximize_env_prefers_gain_2_when_packs_owned(self):
        ranked = rank_items(
            "MAXIMIZE_ENV",
            category="wall_covering",
            owned_packs=["base", "GP02", "EP20"],
            limit=3,
        )
        self.assertTrue(ranked)
        self.assertEqual(ranked[0]["lot_environment_gain"], 2)
        self.assertIn(ranked[0]["id"], {"wall.matchstick_magic", "wall.wildwood_whimsy"})

    def test_maximize_env_base_only_falls_back_to_env1(self):
        ranked = rank_items(
            "MAXIMIZE_ENV",
            category="wall_covering",
            owned_packs=["base"],
            limit=3,
        )
        self.assertTrue(ranked)
        self.assertEqual(ranked[0]["lot_environment_gain"], 1)
        self.assertNotEqual(ranked[0]["id"], "wall.matchstick_magic")

    def test_maximize_green_prefers_log_siding_excludes_industrial(self):
        ranked = rank_items(
            "MAXIMIZE_GREEN",
            category="wall_covering",
            owned_packs=["base", "EP09", "EP19"],
            limit=5,
        )
        self.assertTrue(ranked)
        self.assertEqual(ranked[0]["id"], "wall.log_siding")
        self.assertEqual(ranked[0]["eco_footprint_green"], 2)
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
            "MAXIMIZE_ENV",
            owned_packs=["base", "GP02", "EP20"],
            panels=16,
        )
        self.assertEqual(result["state"], "BUILD_OPTIMIZE_PLAN_READY")
        self.assertEqual(result["best"]["lot_environment_gain"], 2)
        self.assertFalse(result["plan"]["execute_allowed"])
        self.assertEqual(result["projection"]["lot_environment_gain_total"], 32)

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
            build_objective="MAXIMIZE_ENV",
            build_owned_packs=("base", "GP02", "EP20"),
            build_panels=10,
            build_or_buy_mode=True,
        )
        self.assertEqual(out["next_gate"], "BUILD_OPTIMIZE_EVALUATE_ONLY")
        self.assertEqual(out["build_optimize"]["best"]["lot_environment_gain"], 2)
        self.assertFalse(out["fallback"]["execute_allowed"])


if __name__ == "__main__":
    unittest.main()
