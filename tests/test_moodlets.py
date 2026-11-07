import unittest

from betterinstincts.host_stack import evaluate_turn
from betterinstincts.moodlets import MoodletError, evaluate_moodlets, load_contract

LIVE = {
    "hunger": 0.55,
    "bladder": 0.35,
    "energy": 0.12,
    "hygiene": 0.4,
    "fun": 0.28,
    "social": 0.85,
}


class MoodletTests(unittest.TestCase):
    def test_contract_has_observed_labels(self):
        cfg = load_contract()
        self.assertIn("angry", cfg["moodlets"])
        self.assertIn("scared", cfg["moodlets"])
        self.assertIn("VERY_ANGRY", cfg["emotions"])

    def test_sensor_absent(self):
        report = evaluate_moodlets()
        self.assertEqual(report["state"], "SENSOR_NOT_SUPPLIED")
        self.assertIn("MOODLETS_NOT_OBSERVED", report["findings"])

    def test_live_party_strip(self):
        report = evaluate_moodlets(
            emotion="VERY ANGRY",
            moodlets=["scared", "angry", "uncomfortable"],
            needs=LIVE,
            event_active=True,
            outdoor_social_prefix=True,
            indoor_capacity_observed=True,
        )
        self.assertEqual(report["state"], "MOODLETS_EVALUATED")
        self.assertEqual(report["emotion"], "VERY_ANGRY")
        self.assertIn("scared", report["moodlets"])
        self.assertIn("TENSE_MOOD_OUTDOOR_SOCIAL", report["findings"])
        self.assertEqual(report["gate"], "MOODLET_AWARE_ROUTING")
        self.assertIn("SIT_AND_CHAT_HERE_INDOOR", report["relief"])
        self.assertIn("CANCEL_OUTDOOR_WALK_SIT_AND_CHAT_HERE", report["relief"])

    def test_host_stack_carries_moodlets(self):
        result = evaluate_turn(
            LIVE,
            event_active=True,
            outdoor_social_prefix=True,
            indoor_capacity_observed=True,
            emotion="VERY_ANGRY",
            moodlets=["scared", "angry", "uncomfortable"],
            viewport={"state": "VIEWPORT_OK"},
        )
        self.assertEqual(result["moodlets"]["emotion"], "VERY_ANGRY")
        self.assertIn("TENSE_MOOD_OUTDOOR_SOCIAL", result["moodlets"]["findings"])
        self.assertIn("MOODLET_REINFORCES_INDOOR_ROUTING", result["event_balance"]["findings"])
        # Energy critical still outranks event indoor routing.
        self.assertEqual(result["next_gate"], "SURVIVAL_NEEDS_BEFORE_EVENT")

    def test_alias_resolution(self):
        report = evaluate_moodlets(moodlets=["spooked", "furious"])
        self.assertIn("scared", report["moodlets"])
        self.assertIn("angry", report["moodlets"])

    def test_invalid_needs(self):
        with self.assertRaises(MoodletError):
            evaluate_moodlets(moodlets=["angry"], needs={"hunger": 1.0})


if __name__ == "__main__":
    unittest.main()
