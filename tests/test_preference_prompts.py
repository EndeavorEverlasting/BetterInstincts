"""P95 + P124 + Trifecta: preference policy must not grant screen control."""
import unittest

from betterinstincts.preference_prompts import (
    PreferencePromptError, evaluate_offer, load_catalog, plan_stage,
)


def offer(kind="like", topic="gardening", **kwargs):
    return {
        "dialog_class": "sim_preference_offer", "dialog_stage": "offer",
        "scene": "live", "sim_ref": "sim:1", "topic_id": topic,
        "offer_kind": kind, "capture_ref": "capture:first",
        "visible_buttons": ["YES", "NO"], "captured_at_epoch_ms": 1000,
        **kwargs,
    }


class PreferencePromptTests(unittest.TestCase):
    def test_catalog_exposes_useful_and_contextual_policies(self):
        cfg = load_catalog()
        self.assertEqual(cfg["schema"], "betterinstincts.preference-prompts/v1")
        self.assertEqual(cfg["preferences"]["gardening"]["like"], "POSITIVE")
        self.assertEqual(cfg["preferences"]["gardening"]["dislike"], "NEGATIVE")
        self.assertEqual(cfg["preferences"]["mischief"]["dislike"], "GOAL_ONLY")

    def test_positive_like_yes_then_ok_but_not_click_permit(self):
        result = evaluate_offer(offer(), automation_opt_in=True)
        self.assertEqual(result["decision"], "ACCEPT")
        self.assertEqual(result["steps"], ["YES", "OK"])
        self.assertIsNone(result["control_permit"])

    def test_dislike_of_useful_skill_rejects_yes(self):
        result = evaluate_offer(offer(kind="dislike", topic="programming"), automation_opt_in=True)
        self.assertEqual(result["decision"], "DECLINE")
        self.assertEqual(result["steps"], ["NO"])

    def test_mischief_dislike_can_be_positive_with_matching_goal(self):
        row = offer(kind="dislike", topic="mischief")
        self.assertEqual(evaluate_offer(row, automation_opt_in=True)["decision"], "HOLD")
        row["goal_tags"] = ["avoid_mischief"]
        self.assertEqual(evaluate_offer(row, automation_opt_in=True)["decision"], "ACCEPT")

    def test_all_unsafe_or_untrusted_conditions_hold(self):
        base = offer()
        variants = [
            {**base, "topic_id": "new_unknown_pack"},
            {**base, "dialog_class": "occult_life_state"},
            {**base, "dialog_class": "reward_trait"},
            {**base, "scene": "build"},
            {**base, "visible_buttons": ["YES"]},
            {**base, "sim_ref": ""},
            {**base, "offer_kind": "maybe"},
            {**base, "goal_tags": ["\nunsafe"]},
        ]
        for row in variants:
            with self.subTest(row=row):
                self.assertEqual(evaluate_offer(row, automation_opt_in=True)["decision"], "HOLD")
        self.assertEqual(evaluate_offer(base)["reason"], "AUTOMATION_NOT_OPTED_IN")
        self.assertEqual(evaluate_offer(base, automation_opt_in=True, player_directed=True)["reason"], "PLAYER_DIRECTED")
        self.assertEqual(evaluate_offer(base, automation_opt_in=True, known_game_build=False)["reason"], "GAME_BUILD_UNVERIFIED")

    def test_yes_stage_is_one_step_and_ok_needs_new_dialog(self):
        first = offer()
        yes = plan_stage(first, "YES", automation_opt_in=True)
        self.assertEqual(yes["step"], "YES")
        self.assertIsNone(yes["control_permit"])
        receipt = {**yes, "state": "INPUT_DISPATCHED", "captured_at_epoch_ms": 1000}
        second = {**first, "dialog_class": "sim_preference_confirmation",
                  "dialog_stage": "confirmation", "visible_buttons": ["OK"],
                  "capture_ref": "capture:second", "captured_at_epoch_ms": 2000}
        self.assertEqual(plan_stage(second, "OK", automation_opt_in=True,
                                    previous_receipt=receipt)["step"], "OK")
        for bad in (
            {**second, "capture_ref": "capture:first"},
            {**second, "sim_ref": "sim:other"},
            {**second, "captured_at_epoch_ms": 900},
            {**second, "visible_buttons": ["YES", "NO"]},
        ):
            with self.subTest(bad=bad), self.assertRaises(PreferencePromptError):
                plan_stage(bad, "OK", automation_opt_in=True, previous_receipt=receipt)
        with self.assertRaises(PreferencePromptError):
            plan_stage(second, "OK", automation_opt_in=True)

    def test_no_stage_for_accepted_like_and_unknown_prompt(self):
        with self.assertRaises(PreferencePromptError):
            plan_stage(offer(), "NO", automation_opt_in=True)
        with self.assertRaises(PreferencePromptError):
            plan_stage(offer(topic="unknown"), "YES", automation_opt_in=True)


if __name__ == "__main__":
    unittest.main()
