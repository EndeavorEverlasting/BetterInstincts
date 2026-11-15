"""P82/Closers synthetic regression fixtures for shared microsystem math.

No synthetic utility, Gaussian sample or planner win proves a Sims game
event, a native package, or permission to act on the user's desktop.
"""
from __future__ import annotations

import copy
from pathlib import Path
import unittest

from betterinstincts.decision_horizon import optimize_activity_plan
from betterinstincts.domain_cascade import poll_cascade
from betterinstincts.microsystem_math import (
    MicrosystemMathError, evaluate_microsystem_math, evaluate_math_portfolio,
    load_contract,
)

CAPTURE = "cap-math01"
BUILD = "1.121.361.1020"
SIX = {name: 0.9 for name in ("hunger", "bladder", "energy",
                               "hygiene", "fun", "social")}


def snapshot(**changes):
    row = {
        "schema": "betterinstincts.activity-chain/v1",
        "capture_ref": CAPTURE, "mode": "PLANNING",
        "sim_ref": "sim:one", "selected_sim_ref": "sim:one",
        "household_ref": "house:one", "location": "home",
        "scene_verified": True, "queue_verified": True,
        "player_directed": False, "player_active": False,
        "queue_owner": "AUTONOMY", "queue_depth": 0, "queue_capacity": 2,
        "needs_safe": True, "needs": {"energy": 75, "hunger": 85},
        "need_rates": {"energy": -0.1, "hunger": -0.1},
        "need_floors": {"energy": 20, "hunger": 30},
        "skills": {"gardening": 1}, "inventory": {},
        "minutes_until_work": 60, "minutes_until_need_floor": 60,
        "reserve_minutes": 0, "available_funds": 100,
        "blocked_resources": [], "completed": [],
        "teleport_unlocked": False,
    }
    return {**row, **changes}


def step(ident="garden", value=15):
    return {
        "id": ident, "domain": "gardening",
        "kind": "ACTIVITY", "location": "home",
        "evidence_ref": "observed:" + ident,
        "after": [], "resources": [],
        "upper_minutes": 1, "deadline_minutes": 50,
        "value": value, "cost": 0,
        "effects": {"skill_delta": {"gardening": 0.1}},
        "success_probability": 1.0,
    }


def packet(*, domain="career", **changes):
    data = {
        "schema": "betterinstincts.microsystem-math-packet/v1",
        "microsystem_id": domain, "capture_ref": CAPTURE, "sim_ref": "sim:one",
        "game_build": BUILD, "provenance_ref": "native:observed",
        "bellman": {"snapshot": snapshot(), "steps": [step()], "routes": []},
        "kkt": {
            "budget_minutes": 9,
            "activities": {
                "recovery": {"weight": 3, "max_minutes": 8},
                "career": {"weight": 4, "max_minutes": 8},
            },
        },
        "gaussian": {
            "samples": [], "game_build": BUILD, "action_id": "garden",
            "context": 0.5, "baseline_upper_sim_minutes": 5.0,
        },
    }
    return {**data, **changes}


def receipt(name="career", gate="CAREER_IDLE"):
    return {"domain": name, "gate": gate, "action": "KEEP_EXISTING",
            "payload": {"old_owner": "retained"}, "findings": []}


def challenger(**changes):
    samples = [
        {
            "game_build": BUILD, "evidence_state": "LOCAL_OBSERVED",
            "capture_ref": "holdout:" + str(i),
            "proof_ref": "proof:" + str(i),
            "observed_score": 5,
            "baseline_predicted": 12,
            "candidate_predicted": 5.5,
        } for i in range(8)
    ]
    data = {
        "planner_id": "NEW_SAFELY_TESTED_PLANNER",
        "proposed_step_id": "better",
        "reviewer_ref": "independent:reviewer",
        "producer_ref": "source:developer",
        "independent_reviewed": True, "capture_ref": CAPTURE,
        "game_build": BUILD,
        "steps": [step("better", 20)],
        "routes": [], "holdout": samples,
    }
    return {**data, **changes}


class MicrosystemMathTests(unittest.TestCase):
    def test_registry_covers_cascade_and_all_auxiliary_owner_paths(self):
        cfg = load_contract()
        self.assertEqual(cfg["cascade_domains"],
            ["needs", "balance", "budget", "career", "aspirations",
             "skills_whims", "relationships"])
        self.assertGreaterEqual(len(cfg["microsystems"]), 20)
        root = Path(__file__).resolve().parents[1]
        for name, item in cfg["microsystems"].items():
            with self.subTest(domain=name):
                self.assertTrue((root / item["owner"]).is_file())
                self.assertEqual(item["math_access"], "ON_OBSERVED_EVIDENCE")
                self.assertEqual(item["fallback"], "EXISTING_DOMAIN_OWNER")

    def test_every_cascade_receipt_gets_a_fallback_without_extra_evidence(self):
        result = poll_cascade(SIX, funds=1000)
        math = result["math_umbrella"]
        self.assertEqual(math["state"], "POLLED")
        self.assertFalse(math["execute_allowed"])
        self.assertTrue(math["fallback_receipts_unchanged"])
        self.assertEqual(
            [x["domain"] for x in math["domain_results"]],
            [x["domain"] for x in result["receipts"]])
        self.assertTrue(all(x["state"] == "FALLBACK_EXISTING"
                            for x in math["domain_results"]))
        self.assertEqual(result["receipts"][0]["domain"], "needs")

    def test_one_domain_invokes_all_three_without_mutating_legacy(self):
        existing = receipt()
        before = copy.deepcopy(existing)
        out = evaluate_microsystem_math(
            existing, capture_ref=CAPTURE, packet=packet())
        self.assertEqual(existing, before)
        self.assertEqual(out["state"], "MATH_ADVISORY")
        self.assertEqual(out["selected_planner"], "BELLMAN_KKT_GP")
        self.assertEqual(out["next_step_id"], "garden")
        self.assertEqual(out["bellman"]["gate"], "FORECAST_STAGED_NOT_DISPATCHABLE")
        self.assertEqual(out["lagrange_kkt"]["schema"],
                         "betterinstincts.continuous-time-relaxation/v1")
        self.assertTrue(out["lagrange_kkt"]["budget_binding"])
        self.assertEqual(out["gaussian"]["model"], "DETERMINISTIC")
        self.assertEqual(out["gaussian"]["gate"],
                         "INSUFFICIENT_SOURCE_QUALIFIED_SAMPLES")
        self.assertFalse(out["execute_allowed"])
        self.assertIsNone(out["control_permit"])

    def test_portfolio_routes_only_fresh_targeted_domain_packet(self):
        before = poll_cascade(SIX)
        original = copy.deepcopy(before["receipts"])
        with_math = poll_cascade(SIX, math_packets={"career": packet() },
                                 capture_ref=CAPTURE)
        # The existing domain owners and their receipts remain unchanged.
        ordinary = poll_cascade(SIX, capture_ref=CAPTURE)
        self.assertEqual(with_math["receipts"], ordinary["receipts"])
        rows = {x["domain"]: x for x in with_math["math_umbrella"]["domain_results"]}
        self.assertEqual(rows["career"]["state"], "MATH_ADVISORY")
        self.assertTrue(all(rows[x]["state"] == "FALLBACK_EXISTING"
                            for x in rows if x != "career"))
        self.assertEqual(len(original), len(with_math["receipts"]))

    def test_all_registered_non_cascade_domains_can_opt_in(self):
        cfg = load_contract()
        for name in ("career_event", "work_shift", "teen_homework",
                     "gardening", "purchases", "ecology", "household",
                     "upkeep", "scenarios", "activities", "traversal", "queues"):
            with self.subTest(domain=name):
                out = evaluate_microsystem_math(
                    receipt(name), capture_ref=CAPTURE, packet=packet(domain=name),
                    registry=cfg)
                self.assertEqual(out["state"], "MATH_ADVISORY")

    def test_player_and_stale_actor_packet_fall_back(self):
        self.assertEqual(evaluate_microsystem_math(
            receipt(), capture_ref=CAPTURE, player_active=True,
            packet=packet())["state"], "PLAYER_YIELD")
        for wrong in [
            packet(capture_ref="stale:other"),
            packet(sim_ref="sim:other"),
            packet(game_build="1.122.0.0"),
            packet(bellman={**packet()["bellman"],
                            "snapshot": snapshot(selected_sim_ref="sim:two")}),
            packet(kkt={"budget_minutes": -1, "activities": {}}),
        ]:
            with self.subTest(wrong=wrong):
                out = evaluate_microsystem_math(
                    receipt(), capture_ref=CAPTURE, packet=wrong)
                self.assertEqual(out["state"], "FALLBACK_EXISTING")
                self.assertFalse(out["execute_allowed"])

    def test_bad_optional_packet_cannot_break_career_or_needs_cascade(self):
        baseline = poll_cascade(SIX, funds=900, capture_ref=CAPTURE)
        for malformed in ({"unlisted": packet()}, "not-a-packet", {1: packet()}):
            with self.subTest(malformed=malformed):
                result = poll_cascade(
                    SIX, funds=900, capture_ref=CAPTURE, math_packets=malformed)
                self.assertEqual(result["receipts"], baseline["receipts"])
                self.assertEqual(result["gate"], baseline["gate"])
                self.assertEqual(result["math_umbrella"]["domain_results"][0]["state"],
                                 "FALLBACK_EXISTING")
                self.assertIn("invalid_packet_reason", result["math_umbrella"])

    def test_player_directed_cascade_retains_yield(self):
        result = poll_cascade(SIX, player_directed=True, funds=1000)
        self.assertEqual(result["state"], "DOMAIN_CASCADE_YIELDED")
        self.assertEqual(result["gate"], "PLAYER_FIRST_OR_BUSY")
        self.assertEqual(result["math_umbrella"]["state"], "PLAYER_YIELD")
        self.assertEqual(result["math_umbrella"]["domain_results"][0]["state"],
                         "PLAYER_YIELD")

    def test_malformed_or_truncated_optimization_cannot_displace_fallback(self):
        bad = packet(bellman={
            "snapshot": snapshot(), "steps": [step()], "routes": [],
            "max_expansions": 0,
        })
        self.assertEqual(evaluate_microsystem_math(
            receipt(), capture_ref=CAPTURE, packet=bad)["state"],
            "FALLBACK_EXISTING")
        infeasible = packet(bellman={
            "snapshot": snapshot(available_funds=0),
            "steps": [dict(step(), cost=100)], "routes": [],
        })
        out = evaluate_microsystem_math(
            receipt(), capture_ref=CAPTURE, packet=infeasible)
        self.assertEqual(out["state"], "FALLBACK_EXISTING")
        self.assertEqual(out["reason"], "NO_VERIFIED_POSITIVE_BELLMAN_STEP")

    def test_alternative_planner_promotes_only_after_independent_holdout_and_feasibility(self):
        upgraded = evaluate_microsystem_math(
            receipt(), capture_ref=CAPTURE,
            packet=packet(challenger=challenger()))
        self.assertEqual(upgraded["state"], "SUPERIOR_ADVISORY")
        self.assertEqual(upgraded["next_step_id"], "better")
        self.assertEqual(upgraded["selected_planner"], "NEW_SAFELY_TESTED_PLANNER")
        self.assertEqual(upgraded["challenger"]["holdout_count"], 8)
        self.assertFalse(upgraded["execute_allowed"])
        self.assertIsNone(upgraded["control_permit"])
        self.assertEqual(upgraded["bellman"]["next_step_id"], "garden")

    def test_unqualified_alternative_does_not_replace_math_or_legacy(self):
        for item in [
            challenger(independent_reviewed=False),
            challenger(reviewer_ref="source:developer"),
            challenger(holdout=challenger()["holdout"][:7]),
            challenger(proposed_step_id="unobserved"),
            challenger(steps=[dict(step("better"), irreversible=True)]),
            challenger(game_build="1.999.0.0"),
        ]:
            with self.subTest(item=item):
                out = evaluate_microsystem_math(
                    receipt(), capture_ref=CAPTURE,
                    packet=packet(challenger=item))
                self.assertEqual(out["state"], "MATH_ADVISORY")
                self.assertEqual(out["selected_planner"], "BELLMAN_KKT_GP")
                self.assertNotEqual(out["challenger"]["state"],
                                    "BETTER_OFFLINE_CANDIDATE")
        worse = challenger()
        worse["holdout"][0]["candidate_predicted"] = 20
        out = evaluate_microsystem_math(
            receipt(), capture_ref=CAPTURE,
            packet=packet(challenger=worse))
        self.assertEqual(out["state"], "MATH_ADVISORY")
        self.assertEqual(out["challenger"]["reason"], "CHALLENGER_HOLDOUT_REGRESSION")

    def test_rejects_unknown_or_duplicate_portfolio_domain(self):
        with self.assertRaises(MicrosystemMathError):
            evaluate_math_portfolio([receipt("unlisted")],capture_ref=CAPTURE)
        with self.assertRaises(MicrosystemMathError):
            evaluate_math_portfolio([receipt(), receipt()],capture_ref=CAPTURE)
        with self.assertRaises(MicrosystemMathError):
            evaluate_math_portfolio([receipt()],capture_ref=CAPTURE,
                                    math_packets={"needs": packet()})


if __name__ == "__main__":
    unittest.main()
