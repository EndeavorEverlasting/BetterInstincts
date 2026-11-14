"""Offline regressions for the locally reported EA Video Gaming response map.

Every native-shaped receipt below is SYNTHETIC. No Sims game was launched,
no dialog was answered, and no instrumented activity resumption is claimed.
"""
import copy
import unittest

from betterinstincts.preference_native_map import (
    load_response_map, assess_native_offer_binding, assess_native_preference_outcome,
    OFFER_SCHEMA, RESPONSE_SCHEMA, EFFECT_SCHEMA, RESUME_SCHEMA,
)


def offer():
    return {
        "schema": OFFER_SCHEMA, "source": "EA_NATIVE",
        "read_origin": "RUNNING_GAME_MEMORY",
        "game_build": "1.121.361.1020",
        "dialog_tuning_id": 265965, "localization_key": "0x0A349797",
        "resolver_source": "originating_interaction",
        "resolver_role": "Actor", "resolver_actor_sim_id": "1024001",
        "moment_sim_id": "1024001", "selected_sim_id": "1024002",
        "household_id": "55001", "dialog_ref": "native:pref-offer-1",
        "capture_ref": "native:before-1", "native_hook_ref": "hook:reported",
        "state_revision": "state:original", "originating_interaction_ref": "ia:265965",
        "captured_at_epoch_ms": 100000,
        "response_ids": {"YES": 0, "NO": 1},
    }


def receipts(choice, binding):
    m = load_response_map()
    v = m["responses"][choice]
    trait_id = (v["effect"]["trait_id"] if choice == "YES"
                else v["effect"]["marker_id"])
    response = {
        "schema": RESPONSE_SCHEMA, "source": "EA_NATIVE",
        "dialog_ref": binding["dialog_ref"],
        "recipient_sim_id": binding["recipient_sim_id"],
        "response_id": v["response_id"], "event_ref": "native:response-1",
        "captured_at_epoch_ms": 100100, "accepted_by_native_dialog": True,
    }
    effect = {
        "schema": EFFECT_SCHEMA, "source": "EA_NATIVE",
        "dialog_ref": binding["dialog_ref"],
        "recipient_sim_id": binding["recipient_sim_id"],
        "response_event_ref": response["event_ref"],
        "capture_ref": "native:effect-1", "captured_at_epoch_ms": 100200,
        "actor_effect": {
            "subject": "Actor", "loot_id": v["loot_id"],
            "trait_or_marker_id": trait_id, "applied": True,
        },
        "common_effect": {
            "subject": "ActiveHousehold",
            "buff_id": 263631, "applied": True,
        },
    }
    resumed = {
        "schema": RESUME_SCHEMA, "source": "EA_NATIVE",
        "dialog_ref": binding["dialog_ref"],
        "recipient_sim_id": binding["recipient_sim_id"],
        "capture_ref": "native:resumed-1",
        "captured_at_epoch_ms": 100300,
        "resumed": True, "activity_ref": "queue:previous-action",
    }
    return response, effect, resumed


class PreferenceNativeMapTests(unittest.TestCase):
    def test_exact_reported_ids_are_canonical_and_no_is_stateful(self):
        m = load_response_map()
        self.assertEqual(m["dialog"]["tuning_id"], 265965)
        self.assertEqual(m["dialog"]["localization_key"], "0x0A349797")
        self.assertEqual(m["dialog"]["tuning_name"],
                         "adventureMoment_SimPreference_Activities_VideoGaming_Like")
        self.assertEqual(m["responses"]["YES"]["response_id"], 0)
        self.assertEqual(m["responses"]["YES"]["loot_id"], 266649)
        self.assertEqual(m["responses"]["YES"]["effect"]["trait_id"], 258767)
        self.assertEqual(m["responses"]["NO"]["response_id"], 1)
        self.assertEqual(m["responses"]["NO"]["loot_id"], 266780)
        self.assertEqual(m["responses"]["NO"]["effect"]["marker_id"], 266814)
        self.assertEqual(m["common_effects"],
                         [{"operation": "apply_buff", "buff_id": 263631,
                           "subject": "ActiveHousehold"}])
        self.assertTrue(m["model_rules"]["no_is_not_no_op"])
        self.assertFalse(m["evidence"]["actual_dialog_response_observed"])
        self.assertFalse(m["evidence"]["independently_reread_ea_asset_from_remote"])

    def test_actor_recipient_is_not_selected_portrait(self):
        result = assess_native_offer_binding(offer())
        self.assertEqual(result["state"], "OFFER_BINDING_SHAPE_MATCH")
        self.assertEqual(result["recipient_sim_id"], "1024001")
        self.assertEqual(result["selected_sim_id"], "1024002")
        self.assertEqual(result["response_ids"], {"YES": 0, "NO": 1})
        self.assertFalse(result["execute_allowed"])
        self.assertIsNone(result["control_permit"])

    def test_unknown_wrong_actor_and_inverted_ids_hold(self):
        cases = [
            ({"game_build": "1.122.0.0"}, "EXACT_PREFERENCE_TUNING_MISMATCH"),
            ({"dialog_tuning_id": 123}, "EXACT_PREFERENCE_TUNING_MISMATCH"),
            ({"dialog_tuning_id": True}, "EXACT_PREFERENCE_TUNING_MISMATCH"),
            ({"localization_key": "0x00000000"}, "EXACT_PREFERENCE_TUNING_MISMATCH"),
            ({"resolver_role": "SelectedSim"}, "PREFERENCE_RESOLVER_ROLE_UNVERIFIED"),
            ({"resolver_source": "generic_dialog_owner"}, "PREFERENCE_RESOLVER_ROLE_UNVERIFIED"),
            ({"moment_sim_id": "1024002"}, "RESOLVER_ACTOR_NOT_MOMENT_RECIPIENT"),
            ({"resolver_actor_sim_id": "001024001"}, "RESOLVER_ACTOR_NOT_MOMENT_RECIPIENT"),
            ({"response_ids": {"YES": 1, "NO": 0}},
             "RESPONSE_IDS_DIFFER_FROM_INSTALLED_TUNING_MAP"),
            ({"response_ids": {"YES": False, "NO": 1}},
             "RESPONSE_IDS_DIFFER_FROM_INSTALLED_TUNING_MAP"),
            ({"source": "DISK_SAVE"}, "LIVE_NATIVE_OFFER_SOURCE_REQUIRED"),
            ({"native_hook_ref": ""}, "NATIVE_DIALOG_IDENTITY_OR_TIME_REQUIRED"),
        ]
        for changes, reason in cases:
            with self.subTest(changes=changes):
                modified = {**offer(), **changes}
                self.assertEqual(assess_native_offer_binding(modified)["reason"], reason)

    def test_yes_no_have_different_actor_effects_but_same_household_buff(self):
        bound = assess_native_offer_binding(offer())
        outcomes = {}
        for choice in ("YES", "NO"):
            response, effect, resumed = receipts(choice, bound)
            result = assess_native_preference_outcome(bound, response, effect, resumed)
            self.assertEqual(result["state"], "OUTCOME_RECEIPTS_SCHEMA_MATCH")
            self.assertFalse(result["execute_allowed"])
            self.assertEqual(result["response_choice"], choice)
            self.assertEqual(result["household_buff_id"], 263631)
            outcomes[choice] = result
        self.assertEqual(outcomes["YES"]["actor_loot_id"], 266649)
        self.assertEqual(outcomes["YES"]["actor_trait_or_marker_id"], 258767)
        self.assertEqual(outcomes["NO"]["actor_loot_id"], 266780)
        self.assertEqual(outcomes["NO"]["actor_trait_or_marker_id"], 266814)
        self.assertNotEqual(outcomes["YES"]["actor_loot_id"], outcomes["NO"]["actor_loot_id"])

    def test_input_dispatch_only_cannot_claim_native_outcome(self):
        bound = assess_native_offer_binding(offer())
        response, effect, resumed = receipts("YES", bound)
        self.assertEqual(assess_native_preference_outcome(bound, response, None, None)["reason"],
                         "POST_RESPONSE_EFFECT_OBSERVATION_REQUIRED")
        response["accepted_by_native_dialog"] = False
        self.assertEqual(assess_native_preference_outcome(bound, response, effect, resumed)["reason"],
                         "MATCHED_NATIVE_RESPONSE_ACK_REQUIRED")

    def test_wrong_trait_loot_subject_or_missing_buff_hold(self):
        bound = assess_native_offer_binding(offer())
        response, effect, resumed = receipts("NO", bound)
        cases = [
            ("actor_effect", {"trait_or_marker_id": 258767}),
            ("actor_effect", {"loot_id": 266649}),
            ("actor_effect", {"subject": "ActiveHousehold"}),
            ("common_effect", {"subject": "Actor"}),
            ("common_effect", {"buff_id": 123}),
            ("common_effect", {"applied": False}),
        ]
        for field, changes in cases:
            with self.subTest(field=field, changes=changes):
                bad_effect = copy.deepcopy(effect)
                bad_effect[field].update(changes)
                result = assess_native_preference_outcome(bound, response, bad_effect, resumed)
                self.assertEqual(result["reason"],
                                 "ACTOR_AND_HOUSEHOLD_EFFECTS_NOT_SEPARATELY_OBSERVED")

    def test_wrong_dialog_actor_duplicated_capture_and_missing_resume_hold(self):
        bound = assess_native_offer_binding(offer())
        response, effect, resumed = receipts("YES", bound)
        bad_response = {**response, "dialog_ref": "native:other"}
        self.assertEqual(assess_native_preference_outcome(
            bound, bad_response, effect, resumed)["reason"], "MATCHED_NATIVE_RESPONSE_ACK_REQUIRED")
        bad_effect = {**effect, "recipient_sim_id": "1024002"}
        self.assertEqual(assess_native_preference_outcome(
            bound, response, bad_effect, resumed)["reason"], "POST_RESPONSE_EFFECT_OBSERVATION_REQUIRED")
        bad_effect = {**effect, "capture_ref": bound["capture_ref"]}
        self.assertEqual(assess_native_preference_outcome(
            bound, response, bad_effect, resumed)["reason"], "POST_RESPONSE_EFFECT_OBSERVATION_REQUIRED")
        self.assertEqual(assess_native_preference_outcome(
            bound, response, effect, None)["reason"], "POST_DIALOG_ACTIVITY_RESUMPTION_NOT_OBSERVED")
        bad_resumed = {**resumed, "resumed": False}
        self.assertEqual(assess_native_preference_outcome(
            bound, response, effect, bad_resumed)["reason"],
            "POST_DIALOG_ACTIVITY_RESUMPTION_NOT_OBSERVED")
        bad_resumed = {**resumed, "capture_ref": effect["capture_ref"]}
        self.assertEqual(assess_native_preference_outcome(
            bound, response, effect, bad_resumed)["reason"],
            "POST_DIALOG_ACTIVITY_RESUMPTION_NOT_OBSERVED")


if __name__ == "__main__":
    unittest.main()
