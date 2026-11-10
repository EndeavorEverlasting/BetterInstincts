"""Cross-domain operator sovereignty: no free OS or screen authority."""
import unittest

from betterinstincts.effect_authority import EffectClass, assess_effect
from betterinstincts.player_presence import PresenceProbe


class EffectAuthorityTests(unittest.TestCase):
    def test_human_active_only_pauses_contending_effects(self):
        busy = PresenceProbe(False, False, last_input_age_ms=0, operator_busy=True)
        for kind in ("SCREEN_EFFECT", "GAME_MUTATION"):
            with self.subTest(kind=kind):
                decision = assess_effect(kind, session_active=True, probe=busy)
                self.assertFalse(decision["execute_allowed"])
                self.assertTrue(decision["needs_screen"])
        for kind in ("PASSIVE_OBSERVATION", "BACKGROUND_REASONING"):
            with self.subTest(kind=kind):
                decision = assess_effect(kind, session_active=True, probe=busy)
                self.assertTrue(decision["execute_allowed"])
                self.assertFalse(decision["needs_screen"])

    def test_idle_is_candidate_not_transferable_execution_permission(self):
        idle = PresenceProbe(False, False, last_input_age_ms=30000)
        result = assess_effect(EffectClass.SCREEN_EFFECT, session_active=True, probe=idle)
        self.assertEqual(result["state"], "SCREEN_CANDIDATE")
        self.assertIn("double-check", result["note"])
        self.assertFalse(assess_effect("GAME_MUTATION", session_active=True)["execute_allowed"])

    def test_unknown_or_host_mutation_never_admitted(self):
        for kind in ("NOT_REVIEWED", "", None, "OS_CONFIGURATION"):
            with self.subTest(kind=kind):
                self.assertEqual(assess_effect(kind, session_active=True)["state"], "DENIED")

    def test_session_shutdown_stops_background_and_ui(self):
        for kind in EffectClass:
            result = assess_effect(kind, session_active=False)
            self.assertFalse(result["execute_allowed"])


if __name__ == "__main__":
    unittest.main()
