import unittest

from betterinstincts.balance_service import (
    BalanceServiceError,
    compact_balance_service,
    evaluate_balance_service,
    load_contract,
    resolve_ailment,
    resolve_balance_level,
    should_attach_balance_service,
)

GREEN = {
    "hunger": 0.9,
    "bladder": 0.9,
    "energy": 0.9,
    "hygiene": 0.9,
    "fun": 0.9,
    "social": 0.9,
}
CRITICAL = {
    "hunger": 0.1,
    "bladder": 0.9,
    "energy": 0.9,
    "hygiene": 0.9,
    "fun": 0.9,
    "social": 0.9,
}


class BalanceServiceTests(unittest.TestCase):
    def test_contract_loads(self):
        cfg = load_contract()
        self.assertEqual(cfg["schema"], "betterinstincts.balance-service/v1")
        self.assertIn("very_imbalanced", cfg["balance_levels"])
        self.assertIn("burning_passion", cfg["ailments"])

    def test_resolve_aliases(self):
        self.assertEqual(resolve_balance_level("Very Imbalanced"), "very_imbalanced")
        self.assertEqual(resolve_ailment("Burning Passion"), "burning_passion")
        self.assertIsNone(resolve_ailment("mystery plague"))

    def test_idle_without_supplied_condition(self):
        report = evaluate_balance_service(GREEN)
        self.assertFalse(report["condition_held"])
        self.assertEqual(report["microsystem_state"], "IDLE")
        self.assertFalse(should_attach_balance_service())

    def test_imbalanced_prefers_nature_not_naturopath_first(self):
        report = evaluate_balance_service(
            GREEN,
            balance_level="imbalanced",
            emotion="SAD",
            houseplants_available=True,
        )
        self.assertTrue(report["condition_held"])
        self.assertEqual(report["microsystem_state"], "RECOVERING_NATURE")
        self.assertEqual(report["gate"], "RECOVERING_NATURE")
        self.assertEqual(report["primary_route"], "WATER_OR_MAINTAIN_HOUSEPLANTS")
        self.assertNotEqual(report["primary_route"], "VISIT_NATUROPATH")
        self.assertIn("SEEK_POSITIVE_MOOD", report["preferred_routes"])
        self.assertIn("NEGATIVE_MOOD_PRESSURES_IMBALANCE", report["findings"])

    def test_very_imbalanced_burning_passion_escalates_naturopath(self):
        report = evaluate_balance_service(
            GREEN,
            balance_level="very_imbalanced",
            ailment="Burning Passion",
            emotion="ANGRY",
        )
        self.assertTrue(report["condition_held"])
        self.assertEqual(report["ailment"], "burning_passion")
        self.assertEqual(report["microsystem_state"], "AILMENT_ACTIVE")
        self.assertEqual(report["gate"], "READY_NATUROPATH")
        self.assertEqual(report["primary_route"], "VISIT_NATUROPATH")
        self.assertIn("AILMENT_ACTIVE_ESCALATE_NATUROPATH", report["findings"])

    def test_holistic_cure_inventory_outranks_naturopath(self):
        report = evaluate_balance_service(
            GREEN,
            balance_level="very_imbalanced",
            ailment="burning_passion",
            inventory_has_holistic_cure=True,
        )
        self.assertEqual(report["gate"], "READY_HOLISTIC_CURE")
        self.assertEqual(report["primary_route"], "CONSUME_HOLISTIC_CURE")
        self.assertEqual(report["microsystem_state"], "READY_HOLISTIC_CURE")

    def test_survival_suspends_action_but_holds_condition(self):
        report = evaluate_balance_service(
            CRITICAL,
            balance_level="very_imbalanced",
            ailment="burning_passion",
        )
        self.assertTrue(report["condition_held"])
        self.assertEqual(report["microsystem_state"], "SUSPENDED_FOR_SURVIVAL")
        self.assertIsNone(report["primary_route"])
        self.assertIn("SURVIVAL_SUSPENDS_BALANCE_ACTION_NOT_CONDITION", report["findings"])

    def test_sticky_prior_survives_needs_then_resumes_naturopath(self):
        suspended = evaluate_balance_service(
            CRITICAL,
            balance_level="very_imbalanced",
            ailment="burning_passion",
            capture_ref="capture:prior",
        )
        self.assertTrue(should_attach_balance_service(prior_state=suspended))
        resumed = evaluate_balance_service(
            GREEN,
            prior_state=suspended,
            capture_ref="capture:tandem",
        )
        self.assertTrue(resumed["condition_held"])
        self.assertEqual(resumed["gate"], "READY_NATUROPATH")
        self.assertIn("BALANCE_LEVEL_CARRIED_FROM_PRIOR", resumed["findings"])
        self.assertIn("BALANCE_RESUMED_AFTER_SURVIVAL_OR_CONTINUITY", resumed["findings"])

    def test_balanced_clears_sticky_condition(self):
        prior = evaluate_balance_service(
            GREEN,
            balance_level="imbalanced",
            houseplants_available=True,
        )
        done = evaluate_balance_service(
            GREEN,
            balance_level="balanced",
            prior_state=prior,
        )
        self.assertFalse(done["condition_held"])
        self.assertEqual(done["microsystem_state"], "RESTORED")
        self.assertEqual(done["gate"], "BALANCE_RESTORED")

    def test_does_not_invent_ailment_on_very_imbalanced(self):
        report = evaluate_balance_service(
            GREEN,
            balance_level="very_imbalanced",
            houseplants_available=True,
        )
        self.assertIsNone(report["ailment"])
        self.assertEqual(report["microsystem_state"], "RECOVERING_NATURE")
        self.assertIn("VERY_IMBALANCED_WITHOUT_OBSERVED_AILMENT", report["findings"])
        self.assertEqual(report["primary_route"], "WATER_OR_MAINTAIN_HOUSEPLANTS")

    def test_player_yield_preserves_tracking(self):
        report = evaluate_balance_service(
            GREEN,
            balance_level="imbalanced",
            player_directed=True,
        )
        self.assertTrue(report["condition_held"])
        self.assertEqual(report["microsystem_state"], "YIELDED")
        self.assertEqual(report["next_actions"], [])

    def test_compact_receipt(self):
        report = evaluate_balance_service(
            GREEN,
            balance_level="imbalanced",
            houseplants_available=True,
        )
        compact = compact_balance_service(report)
        self.assertTrue(compact["compacted"])
        self.assertEqual(compact["gate"], report["gate"])
        self.assertTrue(compact["condition_held"])

    def test_ailment_alone_attaches_as_very_imbalanced(self):
        self.assertTrue(should_attach_balance_service(ailment="Burning Passion"))
        report = evaluate_balance_service(GREEN, ailment="burning_passion")
        self.assertEqual(report["balance_level"], "very_imbalanced")
        self.assertEqual(report["gate"], "READY_NATUROPATH")

    def test_needs_must_be_complete(self):
        with self.assertRaises(BalanceServiceError):
            # survival_critical raises via teen_homework on incomplete needs
            evaluate_balance_service({"hunger": 0.5}, balance_level="imbalanced")


if __name__ == "__main__":
    unittest.main()
