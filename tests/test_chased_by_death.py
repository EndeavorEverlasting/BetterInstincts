"""A negative trait response must bind to the same live dialog and recipient."""
import unittest
from unittest.mock import Mock, patch

from betterinstincts.preference_native_map import EFFECT_SCHEMA, RESPONSE_SCHEMA, TRAIT_MAP_SCHEMA
from betterinstincts.preference_prompts import PreferencePromptError, evaluate_offer, plan_stage
from scripts.preference_prompts import PreferenceStepError, execute_step
from scripts.preference_response_port import PreferenceResponsePort
from tests.test_preference_native_map import offer as video_fixture
from tests.test_preference_prompts import recipient_offer


class ChasedByDeathTests(unittest.TestCase):
    def setUp(self):
        self.policy = {
            "dialog_class": "sim_trait_offer", "dialog_stage": "offer", "scene": "live",
            "topic_id": "chased_by_death", "offer_kind": "add_trait",
            "title": "CHASED BY DEATH", "trait_label": "Chased by Death",
            "button_labels": {"YES": "Yes", "NO": "No thanks!"},
            "visible_buttons": ["YES", "NO"], "player_directed": False,
            "sim_ref": "sim:offer-recipient", "captured_at_epoch_ms": 100,
        }
        # Fixture IDs are arbitrary. Unlike Video Gaming, the negative response
        # is zero here. No fixture ID is an EA mapping.
        self.local_map = {
            "schema": TRAIT_MAP_SCHEMA, "topic_id": "chased_by_death",
            "game_build": "1.121.361.1020", "dialog_tuning_id": 444, "trait_id": 555,
            "localization_key": "0xA0", "installed_tuning_ref": "local:fixture",
            "response_ids": {"YES": 1, "NO": 0},
        }
        self.native = video_fixture()
        self.native.update(dialog_kind="sim_trait_offer", dialog_tuning_id=444,
                           offered_trait_id=555, localization_key="0xA0",
                           recipient_trait_present=False, captured_at_epoch_ms=100,
                           response_ids={"YES": 1, "NO": 0}, button_labels=dict(self.policy["button_labels"]))
        # The active HUD portrait may differ from the interaction's Actor.
        self.native["selected_sim_id"] = "98765"
        self.policy.update(recipient_sim_id=self.native["resolver_actor_sim_id"],
                           capture_ref=self.native["capture_ref"])
        self.frame = {
            "native_offer": self.native, "policy_offer": self.policy,
            "player_active": False, "player_directed": False, "paused": True,
            "save_authorized": True, "scene_verified": True,
            "native_idle_admitted": True, "input_generation": 3,
        }
        self.adapter = Mock()
        self.adapter.read_offer.return_value = self.frame
        self.adapter.submit_if_current.return_value = {"state": "SUBMITTED", "dispatch_ref": "native:declined"}
        self.port = PreferenceResponsePort(self.adapter, trait_binding=self.local_map, now_ms=lambda: 100)

    def respond(self):
        return self.port.respond(enabled=True)

    def test_only_decline_even_when_visible_order_changes(self):
        self.policy["visible_buttons"].reverse()
        decision = evaluate_offer(self.policy, automation_opt_in=True)
        self.assertEqual((decision["steps"], decision["target_label"]), (["NO"], "No thanks!"))
        self.assertEqual(plan_stage(self.policy, "NO", automation_opt_in=True)["response_route"],
                         "NATIVE_ONLY")
        for stage in ("YES", "OK"):
            with self.assertRaises(PreferencePromptError):
                plan_stage(self.policy, stage, automation_opt_in=True)
        self.assertEqual(self.respond()["choice"], "NO")
        request = self.adapter.submit_if_current.call_args.args[0]
        self.assertEqual(request["response_id"], 0)
        self.assertEqual(request["expected_label"], "No thanks!")
        self.assertEqual(request["expected_role"], "NO")
        self.assertEqual(request["recipient_sim_id"], self.native["resolver_actor_sim_id"])
        self.assertTrue(request["expected_paused"])
        self.assertEqual(request["expected_input_generation"], 3)
        self.assertEqual(self.respond()["state"], "RECONCILE_EXISTING_ATTEMPT")
        self.adapter.submit_if_current.assert_called_once()

    def test_host_cannot_click_even_with_a_self_reported_no_bounding_box(self):
        self.policy["target_boxes"] = {"NO": [1, 1, 99, 99]}
        for stage in ("YES", "NO", "OK"):
            with self.assertRaisesRegex(PreferenceStepError, "TRAIT_OFFER_REQUIRES_NATIVE_RESPONSE"):
                execute_step(self.policy, stage=stage, session_id="demo", process_id=1,
                             idle_ms=15000, receipt_path=None)

    def test_recognition_requires_exact_trait_and_labels_and_opt_in(self):
        for bad in ({"trait_label": "Another trait"}, {"topic_id": "painting"},
                    {"button_labels": {"YES": "No thanks!", "NO": "Yes"}},
                    {"player_directed": None}, {"offer_kind": "dislike"}):
            with self.subTest(bad=bad):
                self.assertEqual(evaluate_offer({**self.policy, **bad}, automation_opt_in=True)["decision"], "HOLD")
        self.assertEqual(evaluate_offer(self.policy)["decision"], "HOLD")

    def test_missing_map_or_untrusted_binding_holds(self):
        self.assertEqual(PreferenceResponsePort(self.adapter).respond(enabled=True)["reason"],
                         "LOCAL_TRAIT_RESPONSE_MAP_REQUIRED")
        for bad in ({"response_ids": {"YES": 0, "NO": 1}},
                    {"button_labels": {"YES": "No thanks!", "NO": "Yes"}},
                    {"offered_trait_id": 556}, {"game_build": "1.0.0.0"},
                    {"recipient_trait_present": True}, {"moment_sim_id": "123"}):
            with self.subTest(bad=bad), patch.dict(self.native, bad):
                self.assertEqual(self.respond()["state"], "REOBSERVE")
        self.adapter.submit_if_current.assert_not_called()

    def test_rechecks_player_ownership_and_capture_age(self):
        self.frame["player_active"] = True
        self.assertEqual(self.respond()["state"], "YIELD_TO_PLAYER")
        self.frame["player_active"] = False
        self.frame["native_idle_admitted"] = False
        self.assertEqual(self.respond()["state"], "YIELD_TO_PLAYER")
        self.frame["native_idle_admitted"] = True
        stale = PreferenceResponsePort(self.adapter, trait_binding=self.local_map, now_ms=lambda: 1101)
        self.assertEqual(stale.respond(enabled=True)["reason"], "NATIVE_TRAIT_CAPTURE_STALE")
        self.adapter.submit_if_current.assert_not_called()

    def test_only_correlated_no_ack_and_independent_trait_absence_resolve(self):
        self.adapter.submit_if_current.side_effect = OSError("lost reply")
        self.assertEqual(self.respond()["state"], "DISPATCH_OUTCOME_UNKNOWN")
        sent = self.adapter.submit_if_current.call_args.args[0]
        dialog = sent["dialog_ref"]
        response = {
            "schema": RESPONSE_SCHEMA, "source": "EA_NATIVE", "dialog_ref": dialog,
            "recipient_sim_id": sent["recipient_sim_id"], "accepted_by_native_dialog": True,
            "event_ref": "native:ack", "captured_at_epoch_ms": 101,
            "response_id": 0, "dispatch_ref": "native:retained", "attempt_ref": sent["attempt_ref"],
        }
        effect = {
            "schema": EFFECT_SCHEMA, "source": "EA_NATIVE", "dialog_ref": dialog,
            "recipient_sim_id": sent["recipient_sim_id"], "response_event_ref": "native:ack",
            "capture_ref": "capture:independent", "captured_at_epoch_ms": 102,
            "offered_trait_id": 555, "recipient_trait_present": False, "dialog_closed": True,
        }
        for wrong in (dict(response, response_id=1), dict(response, attempt_ref="other:attempt")):
            self.assertEqual(self.port.reconcile(dialog, wrong, effect)["state"],
                             "BETTERINSTINCTS_RESPONSE_UNATTRIBUTED")
        for wrong in (dict(effect, recipient_trait_present=True),
                      dict(effect, capture_ref=self.policy["capture_ref"]), dict(effect, dialog_closed=False)):
            self.assertEqual(self.port.reconcile(dialog, response, wrong)["state"], "HOLD")
        result = self.port.reconcile(dialog, response, effect)
        self.assertEqual(result["state"], "OUTCOME_RECEIPTS_SCHEMA_MATCH")
        self.assertFalse(result["trait_added"])
        self.assertEqual(self.respond()["state"], "RECONCILE_EXISTING_ATTEMPT")
        self.adapter.submit_if_current.assert_called_once()

    def test_native_trait_cannot_be_routed_as_a_video_gaming_accept(self):
        video = recipient_offer()
        legacy = video_fixture()
        legacy.update(dialog_kind="sim_trait_offer", capture_ref=video["capture_ref"],
                      captured_at_epoch_ms=video["captured_at_epoch_ms"],
                      native_hook_ref=video["recipient_snapshot"]["native_hook_ref"],
                      state_revision=video["recipient_snapshot"]["state_revision"],
                      household_id=video["recipient_snapshot"]["household_id"])
        self.frame.update(native_offer=legacy, policy_offer=video)
        self.assertEqual(self.respond()["state"], "REOBSERVE")
        self.adapter.submit_if_current.assert_not_called()

    def test_native_refusal_yields_without_trying_the_other_button(self):
        self.adapter.submit_if_current.return_value = {"state": "REFUSED"}
        self.assertEqual(self.respond()["reason"], "ATOMIC_NATIVE_CHECK_REFUSED")
        self.adapter.submit_if_current.assert_called_once()
        self.assertEqual(self.adapter.submit_if_current.call_args.args[0]["response_id"], 0)
