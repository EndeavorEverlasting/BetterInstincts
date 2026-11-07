import unittest

from betterinstincts.host_stack import evaluate_turn
from betterinstincts.sim_profile import SimProfileError, evaluate_sim_profile, load_contract

LIVE = {
    "hunger": 0.7,
    "bladder": 0.6,
    "energy": 0.55,
    "hygiene": 0.5,
    "fun": 0.4,
    "social": 0.45,
}


class SimProfileTests(unittest.TestCase):
    def test_contract_discovery_and_gardening(self):
        cfg = load_contract()
        self.assertEqual(cfg["schema"], "betterinstincts.sim-profile/v1")
        self.assertIn("gardening", cfg["desire_catalog"])
        surfaces = {row["surface_id"] for row in cfg["player_discovery_map"]}
        self.assertIn("simology_panel", surfaces)
        self.assertIn("skills_panel", surfaces)
        self.assertIn("preferences_panel", surfaces)
        self.assertIn("practice_skill", cfg["forbidden_actions"])

    def test_sensor_absent(self):
        report = evaluate_sim_profile()
        self.assertEqual(report["state"], "SENSOR_NOT_SUPPLIED")
        self.assertIn("SIM_PROFILE_NOT_OBSERVED", report["findings"])
        self.assertTrue(report["player_discovery_map"])
        self.assertIsNone(report["gate"])

    def test_gardening_desire_from_whim_like_and_skill(self):
        report = evaluate_sim_profile(
            sim_name="Charlee LabLab",
            traits=["loves_outdoors"],
            aspiration="Freelance Botanist",
            skills=[{"name": "Gardening", "level": 2}],
            likes=["gardening", "nature"],
            whims=["Tend garden"],
            moodlets=["gardening"],
            needs=LIVE,
        )
        self.assertEqual(report["state"], "SIM_PROFILE_EVALUATED")
        self.assertEqual(report["gate"], "SIM_PROFILE_INSPECT")
        self.assertIn("DESIRE_CONTEXT_MATCHED", report["findings"])
        self.assertIn("SKILL_LEVELS_READ_ONLY", report["findings"])
        desire_ids = {row["desire_id"] for row in report["desires"]}
        self.assertIn("gardening", desire_ids)
        garden = next(row for row in report["desires"] if row["desire_id"] == "gardening")
        joined = " ".join(garden["evidence"])
        self.assertIn("whims:", joined)
        self.assertIn("likes:", joined)
        self.assertIn("skills:", joined)
        self.assertIn("practice_skill", report["forbidden_actions"])
        self.assertEqual(report["skills"][0]["proof"], "READ_LEVELS_ONLY")
        self.assertNotEqual(report["proof_ceiling"], "GAME_CERTIFIED")

    def test_dislike_conflict_flag(self):
        report = evaluate_sim_profile(
            likes=["cooking"],
            dislikes=["gardening"],
            whims=["garden"],
        )
        self.assertIn("DESIRE_CONFLICTS_DISLIKE", report["findings"])

    def test_host_stack_attachment_read_only(self):
        result = evaluate_turn(
            LIVE,
            sim_name="Charlee LabLab",
            traits=["cheerful"],
            skills=["gardening:3"],
            likes=["gardening"],
            whims=["gardening"],
            moodlets=["playful"],
            emotion="HAPPY",
            viewport={"state": "VIEWPORT_OK"},
        )
        profile = result["sim_profile"]
        self.assertEqual(profile["state"], "SIM_PROFILE_EVALUATED")
        self.assertEqual(profile["gate"], "SIM_PROFILE_INSPECT")
        # Advisory only — must not steal next_gate from needs/instincts when needs are fine-ish.
        self.assertNotEqual(result["next_gate"], "SIM_PROFILE_INSPECT")
        self.assertIn("practice_skill", profile["forbidden_actions"])
        self.assertIn("gardening", {d["desire_id"] for d in profile["desires"]})

    def test_invalid_skill_level(self):
        with self.assertRaises(SimProfileError):
            evaluate_sim_profile(skills=[{"name": "gardening", "level": 99}])


if __name__ == "__main__":
    unittest.main()
