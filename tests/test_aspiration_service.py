import unittest

from betterinstincts.aspiration_service import (
    AspirationServiceError,
    compact_aspiration_service,
    evaluate_aspiration_service,
    load_contract,
    match_prompt,
    should_attach_aspiration_service,
)

MOTHER_NATURE = (
    "Charlee is about to summon Mother Nature. She will bestow a temporary "
    "charm that allows Charlee to complete her Fairy transformation. "
    "Should Charlee proceed?"
)


class AspirationServiceTests(unittest.TestCase):
    def test_contract_loads(self):
        cfg = load_contract()
        self.assertEqual(cfg["schema"], "betterinstincts.aspiration-service/v1")
        self.assertIn("occult.fairy.mother_nature_summon", cfg["catalogued_prompts"])

    def test_match_mother_nature_requires_two_cues(self):
        matched = match_prompt(prompt_text=MOTHER_NATURE)
        self.assertIsNotNone(matched)
        self.assertEqual(matched["prompt_id"], "occult.fairy.mother_nature_summon")
        self.assertIsNone(match_prompt(prompt_text="Fairy"))

    def test_disabled_toggle_cancels_fairy_summon(self):
        report = evaluate_aspiration_service(
            aspiration_prompt_active=True,
            prompt_text=MOTHER_NATURE,
            aspiration_completion_enabled=False,
        )
        self.assertTrue(report["prompt_held"])
        self.assertEqual(report["microsystem_state"], "DISABLED_REFUSE")
        self.assertEqual(report["dialog_choice"], "CANCEL")
        self.assertFalse(report["press_ok_allowed"])
        self.assertEqual(report["gate"], "ASPIRATION_COMPLETION_DISABLED")
        self.assertIn("ASPIRATION_COMPLETION_DISABLED_CANCEL", report["findings"])

    def test_enabled_but_occult_unready_still_cancels_life_state(self):
        report = evaluate_aspiration_service(
            aspiration_prompt_active=True,
            prompt_id="occult.fairy.mother_nature_summon",
            aspiration_completion_enabled=True,
            occult_needs_engine_ready=False,
            operator_prefers_ok=True,
        )
        self.assertEqual(report["dialog_choice"], "CANCEL")
        self.assertFalse(report["press_ok_allowed"])
        self.assertEqual(report["gate"], "OCCULT_NEEDS_NOT_READY")
        self.assertIn("OCCULT_NEEDS_ENGINE_NOT_READY_CANCEL", report["findings"])

    def test_enabled_occult_ready_and_operator_ok(self):
        report = evaluate_aspiration_service(
            aspiration_prompt_active=True,
            prompt_id="occult.fairy.mother_nature_summon",
            aspiration_completion_enabled=True,
            occult_needs_engine_ready=True,
            operator_prefers_ok=True,
        )
        self.assertEqual(report["dialog_choice"], "OK")
        self.assertTrue(report["press_ok_allowed"])
        self.assertEqual(report["microsystem_state"], "READY_OK")

    def test_sticky_prior_survives_needs_turn_then_cancels_when_disabled(self):
        first = evaluate_aspiration_service(
            aspiration_prompt_active=True,
            prompt_text=MOTHER_NATURE,
            aspiration_completion_enabled=False,
            capture_ref="capture:prior",
        )
        self.assertTrue(should_attach_aspiration_service(prior_state=first))
        carried = evaluate_aspiration_service(
            aspiration_prompt_active=True,
            prior_state=first,
            aspiration_completion_enabled=False,
            capture_ref="capture:tandem",
        )
        self.assertTrue(carried["prompt_held"])
        self.assertEqual(carried["dialog_choice"], "CANCEL")
        self.assertIn("ASPIRATION_PROMPT_CARRIED_FROM_PRIOR", carried["findings"])

    def test_explicit_clear_when_dialog_gone(self):
        prior = evaluate_aspiration_service(
            aspiration_prompt_active=True,
            prompt_text=MOTHER_NATURE,
            aspiration_completion_enabled=False,
        )
        done = evaluate_aspiration_service(
            aspiration_prompt_active=False,
            prior_state=prior,
            aspiration_completion_enabled=False,
        )
        self.assertFalse(done["prompt_held"])
        self.assertEqual(done["microsystem_state"], "COMPLETE")

    def test_player_yield_preserves_tracking(self):
        report = evaluate_aspiration_service(
            aspiration_prompt_active=True,
            prompt_text=MOTHER_NATURE,
            aspiration_completion_enabled=False,
            player_directed=True,
        )
        self.assertEqual(report["microsystem_state"], "YIELDED")
        self.assertTrue(report["prompt_held"])
        self.assertIsNone(report["dialog_choice"])

    def test_unknown_active_dialog_fail_closed_cancel(self):
        report = evaluate_aspiration_service(
            aspiration_prompt_active=True,
            prompt_text="Something mysterious is happening to your Sim.",
            aspiration_completion_enabled=True,
            occult_needs_engine_ready=True,
            operator_prefers_ok=True,
        )
        self.assertEqual(report["dialog_choice"], "CANCEL")
        self.assertIn("ASPIRATION_PROMPT_UNKNOWN_FAIL_CLOSED", report["findings"])

    def test_compact_strips_bulk(self):
        report = evaluate_aspiration_service(
            aspiration_prompt_active=True,
            prompt_text=MOTHER_NATURE,
            aspiration_completion_enabled=False,
        )
        compact = compact_aspiration_service(report)
        self.assertTrue(compact["compacted"])
        self.assertEqual(compact["dialog_choice"], "CANCEL")

    def test_idle_without_prompt(self):
        report = evaluate_aspiration_service(aspiration_completion_enabled=False)
        self.assertEqual(report["microsystem_state"], "IDLE")
        self.assertFalse(report["prompt_held"])

    def test_bad_contract_path_fails_closed(self):
        with self.assertRaises(AspirationServiceError):
            load_contract(path=__file__)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
