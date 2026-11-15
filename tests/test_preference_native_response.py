"""Exercise the product response path with an injected native adapter."""
import unittest
from unittest.mock import Mock

from betterinstincts.preference_native_map import assess_native_offer_binding
from scripts.preference_response_port import PreferenceResponsePort
from tests.test_preference_native_map import offer as native_offer, receipts
from tests.test_preference_prompts import recipient_offer


class PreferenceResponseTests(unittest.TestCase):
    def setUp(self):
        self.adapter = Mock()
        self.policy = recipient_offer()
        self.native = native_offer()
        self.native.update(
            capture_ref=self.policy["capture_ref"],
            captured_at_epoch_ms=self.policy["captured_at_epoch_ms"],
            native_hook_ref=self.policy["recipient_snapshot"]["native_hook_ref"],
            state_revision=self.policy["recipient_snapshot"]["state_revision"],
            household_id=self.policy["recipient_snapshot"]["household_id"],
        )
        self.frame = {
            "native_offer": self.native, "policy_offer": self.policy,
            "player_active": False, "player_directed": False, "paused": True,
            "save_authorized": True, "scene_verified": True,
        }
        self.adapter.read_offer.return_value = self.frame
        self.adapter.submit_if_current.return_value = {
            "state": "SUBMITTED", "dispatch_ref": "native:bi-submitted",
        }
        self.port = PreferenceResponsePort(self.adapter)

    def test_product_chooses_native_yes_once_without_a_caller_selected_button(self):
        result = self.port.respond(enabled=True)
        self.assertEqual(result["state"], "BETTERINSTINCTS_RESPONSE_SUBMITTED")
        self.assertFalse(result["outcome_observed"])
        request = self.adapter.submit_if_current.call_args.args[0]
        self.assertEqual(request["response_id"], 0)
        self.assertEqual(request["recipient_sim_id"], "1024001")
        self.assertTrue(request["expected_paused"])
        self.assertEqual(self.port.respond(enabled=True)["state"], "RECONCILE_EXISTING_ATTEMPT")
        self.adapter.submit_if_current.assert_called_once()

    def test_product_can_choose_no_when_recipient_scores_favor_it(self):
        self.frame["policy_offer"] = recipient_offer(yes_fun=-3, no_fun=10)
        self.assertEqual(self.port.respond(enabled=True)["choice"], "NO")
        self.assertEqual(self.adapter.submit_if_current.call_args.args[0]["response_id"], 1)

    def test_missing_opt_in_or_player_preemption_never_submits(self):
        self.assertEqual(self.port.respond()["state"], "PLAYER_RETAINS_CHOICE")
        self.adapter.read_offer.assert_not_called()
        self.frame["player_active"] = True
        self.assertEqual(self.port.respond(enabled=True)["state"], "YIELD_TO_PLAYER")
        self.adapter.submit_if_current.assert_not_called()

    def test_stale_actor_or_missing_recipient_model_reports_recovery(self):
        self.native["state_revision"] = "other-revision"
        self.assertEqual(self.port.respond(enabled=True)["reason"], "DECISION_STATE_BINDING_MISMATCH")
        self.native["state_revision"] = self.policy["recipient_snapshot"]["state_revision"]
        self.policy.pop("continuation_model")
        self.assertEqual(self.port.respond(enabled=True)["reason"], "LIVE_RECIPIENT_SNAPSHOT_REQUIRED")
        self.adapter.submit_if_current.assert_not_called()

    def test_unknown_sender_result_keeps_attempt_reserved(self):
        self.adapter.submit_if_current.side_effect = OSError("adapter disconnected")
        self.assertEqual(self.port.respond(enabled=True)["state"], "DISPATCH_OUTCOME_UNKNOWN")
        self.assertEqual(self.port.respond(enabled=True)["state"], "RECONCILE_EXISTING_ATTEMPT")
        self.adapter.submit_if_current.assert_called_once()

    def test_lost_submit_result_reconciles_only_with_the_reserved_attempt(self):
        self.adapter.submit_if_current.side_effect = OSError("reply lost")
        self.assertEqual(self.port.respond(enabled=True)["state"], "DISPATCH_OUTCOME_UNKNOWN")
        request = self.adapter.submit_if_current.call_args.args[0]
        binding = assess_native_offer_binding(self.native)
        response, effect, resumed = receipts("YES", binding)
        dialog = binding["dialog_ref"]
        resumed["activity_ref"] = self.native["originating_interaction_ref"]
        response["dispatch_ref"] = "native:readback"
        for wrong in (None, "bi-attempt:another-offer"):
            response["attempt_ref"] = wrong
            self.assertEqual(self.port.reconcile(dialog, response, effect, resumed)["state"],
                             "BETTERINSTINCTS_RESPONSE_UNATTRIBUTED")
        response["attempt_ref"] = request["attempt_ref"]
        stale = dict(response, captured_at_epoch_ms=binding["captured_at_epoch_ms"])
        self.assertEqual(self.port.reconcile(dialog, stale, effect, resumed)["reason"],
                         "MATCHED_NATIVE_RESPONSE_ACK_REQUIRED")
        self.assertEqual(self.port.reconcile(dialog, response, effect, resumed)["state"],
                         "OUTCOME_RECEIPTS_SCHEMA_MATCH")
        response["dispatch_ref"] = "native:unrelated"
        self.assertEqual(self.port.reconcile(dialog, response, effect, resumed)["state"],
                         "BETTERINSTINCTS_RESPONSE_UNATTRIBUTED")
        self.assertEqual(self.port.respond(enabled=True)["state"], "RECONCILE_EXISTING_ATTEMPT")
        self.adapter.submit_if_current.assert_called_once()

    def test_missing_or_refusing_native_adapter_has_an_explicit_recovery(self):
        self.assertEqual(PreferenceResponsePort().respond(enabled=True)["state"], "NATIVE_ADAPTER_REQUIRED")
        self.adapter.submit_if_current.return_value = {"state": "REFUSED"}
        self.assertEqual(self.port.respond(enabled=True)["reason"], "ATOMIC_NATIVE_CHECK_REFUSED")

    def test_assisted_click_or_unrelated_activity_cannot_certify_product_dispatch(self):
        binding = assess_native_offer_binding(self.native)
        response, effect, resumed = receipts("YES", binding)
        dialog = binding["dialog_ref"]
        self.assertEqual(self.port.reconcile(dialog, response, effect, resumed)["state"],
                         "BETTERINSTINCTS_RESPONSE_UNATTRIBUTED")
        self.port.respond(enabled=True)
        self.assertEqual(self.port.reconcile(dialog, response, effect, resumed)["state"],
                         "BETTERINSTINCTS_RESPONSE_UNATTRIBUTED")
        response["dispatch_ref"] = "native:bi-submitted"
        self.assertEqual(self.port.reconcile(dialog, response, effect, resumed)["state"],
                         "ORIGINAL_ACTIVITY_READBACK_REQUIRED")
        resumed["activity_ref"] = self.native["originating_interaction_ref"]
        self.assertEqual(self.port.reconcile(dialog, response, effect, resumed)["state"],
                         "OUTCOME_RECEIPTS_SCHEMA_MATCH")
