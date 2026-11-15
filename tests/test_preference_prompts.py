"""P141→P95→P82: source-only offer recipient and shared continuation falsifiers.

Fixtures are invented test states, never actual gameplay or EA save values.
"""
import copy
import unittest

from betterinstincts.preference_prompts import (
    PreferencePromptError, evaluate_offer, load_catalog, plan_stage,
)
from betterinstincts.preference_recipient import (
    RecipientEvidenceError, compare_recipient_continuations,
)
from tests.test_decision_horizon import snapshot as horizon_snapshot, step


def offer(kind="like", topic="video_gaming", **updates):
    return {
        "dialog_class": "sim_preference_offer", "dialog_stage": "offer",
        "scene": "live", "sim_ref": "sim:selected-other",
        "topic_id": topic, "offer_kind": kind, "capture_ref": "offer-capture-1",
        "visible_buttons": ["YES", "NO"], "captured_at_epoch_ms": 2000,
        **updates,
    }


def recipient_offer(*, yes_fun=12, no_fun=0, with_native=True,
                    selected="sim:selected-other", **offer_updates):
    """Entirely synthetic live-shaped evidence; no invented real Sim values."""
    row = offer(sim_ref=selected)
    sid, household = "1024001", "5501"
    native = {
        "schema": "betterinstincts.preference-recipient-snapshot/v1",
        "source": "EA_NATIVE", "read_origin": "RUNNING_GAME_MEMORY",
        "live_read_verified": True, "motives_complete": True,
        "game_build": "1.121.361.1020",
        "native_hook_ref": "hook-synthetic-1",
        "state_revision": "state-1",
        "sim_id": sid, "household_id": household,
        "capture_ref": row["capture_ref"], "captured_at_epoch_ms": 1500,
        "age": "ADULT", "primary_aspiration": "NERD_BRAIN",
        "extended_species": "HUMAN",
        "traits": ["GEEK"], "current_activity": "SLEEP",
        "needs": {"energy": 75, "hunger": 85, "fun": 55},
        "skills": {"video_gaming": 2},
        "career": {"minutes_until_work": 30, "source_ref": "career-now-1"},
    }
    snap = horizon_snapshot(
        capture_ref=row["capture_ref"], sim_ref=sid,
        selected_sim_ref=selected, household_ref=household,
        source_revision=native["state_revision"],
        forecast_scope="RECIPIENT_COUNTERFACTUAL",
        traits=list(native["traits"]),
        needs=dict(native["needs"]),
        need_rates={"energy": -0.1, "hunger": -0.1, "fun": -0.1},
        need_floors={"energy": 20, "hunger": 30, "fun": 20},
        skills=dict(native["skills"]), minutes_until_work=30,
        minutes_until_need_floor=30,
        teleport_unlocked=False, queue_owner="AUTONOMY",
        player_directed=False, player_active=False,
        queue_verified=True, scene_verified=True,
    )
    row["recipient_sim_id"] = sid
    if with_native:
        row["recipient_snapshot"] = native
    row["continuation_model"] = {
        "snapshot": snap,
        "activities": {"existing-goal": {"weight": 31, "max_minutes": 100}},
        "continuation_steps": [
            step("play-video-game", duration=5, value=5),
        ],
        "routes": [],
        "branch_effects": {
            "YES": {
                "basis_ref": "synthetic-yes-forecast",
                "per_step": {"play-video-game": {"need_delta": {"fun": yes_fun}}},
            },
            "NO": {
                "basis_ref": "synthetic-no-forecast",
                "per_step": {"play-video-game": {"need_delta": {"fun": no_fun}}},
            },
        },
    }
    row.update(offer_updates)
    return row


class PreferenceRecipientTests(unittest.TestCase):
    def test_catalog_is_classification_not_automatic_video_game_vote(self):
        catalog = load_catalog()
        self.assertEqual(catalog["preferences"]["video_gaming"]["like"], "POSITIVE")
        no_live = offer()
        for kind in ("like", "dislike"):
            no_live["offer_kind"] = kind
            got = evaluate_offer(no_live, automation_opt_in=True)
            self.assertEqual(got["decision"], "HOLD")
            self.assertEqual(got["reason"], "LIVE_RECIPIENT_SNAPSHOT_REQUIRED")
            self.assertEqual(got["steps"], [])

    def test_shared_continuation_accepts_yes_for_recipient_not_selected_sim(self):
        row = recipient_offer()
        got = evaluate_offer(row, automation_opt_in=True)
        self.assertEqual(got["decision"], "ACCEPT")
        self.assertEqual(got["steps"], ["YES", "OK"])
        self.assertEqual(got["recipient_sim_id"], "1024001")
        comp = got["continuation"]
        self.assertEqual(comp["recipient_sim_id"], "1024001")
        self.assertEqual(comp["actual_selected_sim_ref"], "sim:selected-other")
        self.assertEqual(comp["continuation_step_ids"], ["play-video-game"])
        self.assertGreater(comp["scores"]["YES"], comp["scores"]["NO"])
        self.assertIsNone(comp["control_permit"])
        self.assertFalse(comp["execute_allowed"])
        self.assertEqual(comp["resume_gate"], "REOBSERVE_RECIPIENT_AND_ACTIVITY_AFTER_DIALOG")

    def test_only_preference_effect_changes_negative_branch_outcome(self):
        row = recipient_offer(yes_fun=-3, no_fun=10)
        got = evaluate_offer(row, automation_opt_in=True)
        self.assertEqual(got["decision"], "DECLINE")
        self.assertEqual(got["steps"], ["NO"])
        self.assertEqual(got["continuation"]["continuation_step_ids"], ["play-video-game"])
        self.assertLess(got["continuation"]["scores"]["YES"], got["continuation"]["scores"]["NO"])

    def test_tie_is_hold_not_unjustified_no(self):
        row = recipient_offer(yes_fun=0, no_fun=0)
        self.assertEqual(evaluate_offer(row, automation_opt_in=True)["reason"],
                         "PREFERENCE_EFFECT_INDIFFERENT")

    def test_live_recipient_must_match_game_identity_and_capture(self):
        mutators = [
            lambda r: r.update(recipient_sim_id="99999"),
            lambda r: r.update(recipient_sim_id="01"),
            lambda r: r.update(recipient_sim_id=True),
            lambda r: r["recipient_snapshot"].update(sim_id="123"),
            lambda r: r["recipient_snapshot"].update(source="DISK_SAVE"),
            lambda r: r["recipient_snapshot"].update(read_origin="SAVE_SLOT"),
            lambda r: r["recipient_snapshot"].update(live_read_verified=False),
            lambda r: r["recipient_snapshot"].update(motives_complete=False),
            lambda r: r["recipient_snapshot"].update(game_build="1.120"),
            lambda r: r["recipient_snapshot"].update(captured_at_epoch_ms=0),
            lambda r: r["recipient_snapshot"].update(captured_at_epoch_ms=2001),
            lambda r: r["recipient_snapshot"].update(capture_ref="other"),
            lambda r: r["recipient_snapshot"].update(state_revision=""),
            lambda r: r["recipient_snapshot"].update(needs={"fun": 50}),
            lambda r: r["recipient_snapshot"].update(traits=["OTHER"]),
            lambda r: r["recipient_snapshot"]["career"].update(minutes_until_work=0),
            lambda r: r["continuation_model"]["snapshot"].update(
                sim_ref="different-recipient"),
            lambda r: r["continuation_model"]["snapshot"].update(
                minutes_until_work=999),
            lambda r: r["continuation_model"]["snapshot"].update(
                source_revision="old-state"),
            lambda r: r["continuation_model"]["snapshot"].update(
                forecast_scope="ACTUALLY_SELECTED"),
        ]
        for mutate in mutators:
            row = recipient_offer()
            mutate(row)
            with self.subTest(case=mutate):
                got = evaluate_offer(row, automation_opt_in=True)
                self.assertEqual(got["decision"], "HOLD")
                self.assertFalse(got["steps"])

    def test_no_native_values_and_saved_values_do_not_vote(self):
        row = recipient_offer(with_native=False)
        self.assertEqual(evaluate_offer(row, automation_opt_in=True)["decision"], "HOLD")
        row["recipient_snapshot"] = {
            "source": "DISK_SAVE", "sim_id": row["recipient_sim_id"],
        }
        self.assertEqual(evaluate_offer(row, automation_opt_in=True)["decision"], "HOLD")

    def test_branch_must_only_modify_prediction_effects_not_action_plan(self):
        cases = [
            lambda m: m.pop("continuation_steps"),
            lambda m: m.update(YES=[step("other-path")]),
            lambda m: m["branch_effects"]["YES"].update(
                per_step={"unknown-step": {"need_delta": {"fun": 1}}}),
            lambda m: m["branch_effects"]["YES"].update(
                per_step={"play-video-game": {"upper_minutes": 100}}),
            lambda m: m["branch_effects"]["YES"].update(
                per_step={"play-video-game": {"need_delta": {"fun": float("nan")}}}),
            lambda m: m["branch_effects"].pop("NO"),
        ]
        for mutate in cases:
            row = recipient_offer()
            mutate(row["continuation_model"])
            with self.subTest(case=mutate):
                self.assertEqual(evaluate_offer(row, automation_opt_in=True)["decision"], "HOLD")

    def test_need_emergency_or_work_deadline_blocks_both_branches(self):
        row = recipient_offer()
        row["continuation_model"]["snapshot"]["needs_safe"] = False
        self.assertEqual(evaluate_offer(row, automation_opt_in=True)["decision"], "HOLD")
        row = recipient_offer()
        row["recipient_snapshot"]["career"]["minutes_until_work"] = 2
        row["continuation_model"]["snapshot"]["minutes_until_work"] = 2
        self.assertEqual(evaluate_offer(row, automation_opt_in=True)["decision"], "HOLD")
        row = recipient_offer()
        row["recipient_snapshot"]["needs"]["fun"] = 20
        row["continuation_model"]["snapshot"]["needs"]["fun"] = 20
        row["continuation_model"]["snapshot"]["need_rates"]["fun"] = -1.0
        self.assertEqual(evaluate_offer(row, automation_opt_in=True)["decision"], "HOLD")

    def test_player_dialog_proof_and_source_control_still_block(self):
        row = recipient_offer()
        cases = [
            dict(automation_opt_in=False),
            dict(automation_opt_in=True, player_directed=True),
            dict(automation_opt_in=True, known_game_build=False),
        ]
        for opts in cases:
            self.assertEqual(evaluate_offer(row, **opts)["decision"], "HOLD")
        for change in (
            {"dialog_class": "reward_trait"},
            {"dialog_stage": "confirmation"},
            {"scene": "build"},
            {"visible_buttons": ["YES", "YES"]},
            {"topic_id": "uncatalogued"},
            {"offer_kind": "unknown"},
        ):
            got = evaluate_offer({**row, **change}, automation_opt_in=True)
            self.assertEqual(got["decision"], "HOLD")

    def test_stages_bind_recipient_and_ok_requires_new_observation(self):
        row = recipient_offer()
        yes = plan_stage(row, "YES", automation_opt_in=True)
        self.assertEqual(yes["recipient_sim_id"], "1024001")
        self.assertIsNone(yes["control_permit"])
        prior = {**yes, "state": "INPUT_DISPATCHED", "captured_at_epoch_ms": 2000}
        confirmed = {**row, "dialog_class": "sim_preference_confirmation",
                     "dialog_stage": "confirmation", "visible_buttons": ["OK"],
                     "capture_ref": "capture-confirm", "captured_at_epoch_ms": 3000}
        okay = plan_stage(confirmed, "OK", automation_opt_in=True, previous_receipt=prior)
        self.assertEqual(okay["recipient_sim_id"], "1024001")
        for change in (
            {"recipient_sim_id": "1003"},
            {"capture_ref": row["capture_ref"]},
            {"captured_at_epoch_ms": 1999},
            {"visible_buttons": ["YES", "NO"]},
        ):
            with self.subTest(change=change), self.assertRaises(PreferencePromptError):
                plan_stage({**confirmed, **change}, "OK",
                           automation_opt_in=True, previous_receipt=prior)
        with self.assertRaises(PreferencePromptError):
            plan_stage(row, "NO", automation_opt_in=True)
        with self.assertRaises(PreferencePromptError):
            plan_stage(confirmed, "OK", automation_opt_in=True)


def legacy_offer(kind="like", topic="gardening", **kwargs):
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
        result = evaluate_offer(legacy_offer(), automation_opt_in=True)
        self.assertEqual(result["decision"], "ACCEPT")
        self.assertEqual(result["steps"], ["YES", "OK"])
        self.assertIsNone(result["control_permit"])

    def test_dislike_of_useful_skill_rejects_yes(self):
        result = evaluate_offer(legacy_offer(kind="dislike", topic="programming"), automation_opt_in=True)
        self.assertEqual(result["decision"], "DECLINE")
        self.assertEqual(result["steps"], ["NO"])

    def test_mischief_dislike_can_be_positive_with_matching_goal(self):
        row = legacy_offer(kind="dislike", topic="mischief")
        self.assertEqual(evaluate_offer(row, automation_opt_in=True)["decision"], "HOLD")
        row["goal_tags"] = ["avoid_mischief"]
        self.assertEqual(evaluate_offer(row, automation_opt_in=True)["decision"], "ACCEPT")

    def test_all_unsafe_or_untrusted_conditions_hold(self):
        base = legacy_offer()
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
        first = legacy_offer()
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
            plan_stage(legacy_offer(), "NO", automation_opt_in=True)
        with self.assertRaises(PreferencePromptError):
            plan_stage(legacy_offer(topic="unknown"), "YES", automation_opt_in=True)


if __name__ == "__main__":
    unittest.main()
