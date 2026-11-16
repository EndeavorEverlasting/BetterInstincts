"""Screenshot-grounded disclosures with synthetic native identities and effects."""
import unittest

from betterinstincts.career_response_port import CareerResponsePort, SCOPE
from tests.test_career_decisions import event, plan


def endorsement(**changes):
    card = event(
        career_id="career:civil-designer", shift_ref="shift:ended",
        disclosed_card={"title": "Celebrity Endorsement", "subject": "Smog Vacuum",
                        "career": "Civil Designer", "pack": "Get Famous",
                        "card_source_ref": "ea:card", "fame_allowed": True},
        response_ids=[71, 119],
        options=[
            {"response_id": 119, "option_ref": "ea:offer:endorse",
             "effect_basis_ref": "ea:reward:endorse", "label": "Get Endorsement",
             "disclosed_positive_effects": ["fame", "performance", "simoleons"],
             "job_lost": False, "irreversible": False},
            {"response_id": 71, "option_ref": "ea:offer:promote",
             "effect_basis_ref": "ea:reward:promote", "label": "Self Promote",
             "disclosed_positive_effects": ["fame"], "job_lost": False, "irreversible": False},
        ],
    )
    card.update(changes)
    return card


class Adapter:
    def __init__(self):
        self.frame = {"event": endorsement(), "build_verified": True,
                      "scene_verified": True, "save_authorized": True,
                      "session_ref": "session:one", "process_instance_ref": "process:one",
                      "save_ref": "slot:lab", "paused": True, "player_active": False}
        self.requests = []
        self.behavior = "SUBMITTED"
        self.on_submit = None

    def read_career_event(self):
        return self.frame

    def submit_if_current(self, request):
        self.requests.append(request)
        if self.on_submit is not None:
            self.on_submit()
        if self.behavior == "lost":
            raise OSError("native return lost")
        return {"state": self.behavior, "attempt_ref": request["attempt_ref"],
                "dispatch_ref": "dispatch:1"}


def observed(request):
    scoped = {key: request[key] for key in SCOPE}
    base = {**scoped, "event_ref": request["event_ref"],
            "recipient_sim_id": request["recipient_sim_id"], "source": "EA_NATIVE"}
    response = {**base, "event_revision": request["event_revision"],
                "response_id": request["response_id"], "accepted": True,
                "attempt_ref": request["attempt_ref"], "dispatch_ref": "dispatch:1",
                "capture_ref": "capture:native-ack", "captured_at_epoch_ms": 100200}
    effect = {**base, "response_id": request["response_id"], "effect_basis_ref": "ea:reward:endorse",
              "applied": True, "event_rewards_attributed": True, "dispatch_ref": "dispatch:1",
              "observed_deltas": {"fame": 5, "performance": 4, "simoleons": 100},
              "capture_ref": "capture:rewards", "captured_at_epoch_ms": 100300}
    continuation = {**base, "resumed": True, "event_closed": True, "dispatch_ref": "dispatch:1",
                    "shift_ref": request["shift_ref"], "continuation_kind": "POST_SHIFT_LIVE_MODE",
                    "activity_ref": "live:home", "capture_ref": "capture:home", "captured_at_epoch_ms": 100400}
    return response, effect, continuation


class EndorsementTests(unittest.TestCase):
    def test_preferred_option_bound_to_real_response_shape(self):
        case = endorsement()
        decision = plan(case)
        self.assertEqual(decision["recommended_response_id"], 119)
        self.assertEqual(decision["option_label"], "Get Endorsement")
        self.assertEqual(decision["required_positive_effects"], ["fame", "performance", "simoleons"])
        self.assertIsNone(decision["score_margin"])
        self.assertEqual(decision["all_scores"], [])
        case["options"].reverse()
        case["options"][1]["response_id"] = 123
        case["response_ids"] = [123, 71]
        self.assertEqual(plan(case)["recommended_response_id"], 123)

    def test_mismatched_identity_disclosures_and_authority_hold(self):
        for key, value in (("title", "Another Endorsement"), ("subject", "New invention"),
                           ("career", "Scientist"), ("pack", "Other"), ("card_source_ref", "")):
            with self.subTest(key=key):
                case = endorsement()
                case["disclosed_card"][key] = value
                self.assertEqual(plan(case)["reason"], "DISCLOSED_CARD_IDENTITY_UNVERIFIED")
        case = endorsement()
        del case["disclosed_card"]["fame_allowed"]
        self.assertEqual(plan(case)["reason"], "DISCLOSED_CARD_FAME_NOT_ALLOWED")
        self.assertEqual(plan(endorsement(), player_active=True)["reason"], "PLAYER_OWNS_CAREER_DECISION")
        self.assertEqual(plan(endorsement(source="SCREENSHOT"))["reason"], "COMPLETE_NATIVE_CAREER_CHOICE_REQUIRED")

        case = endorsement()
        case["options"][0]["disclosed_positive_effects"].remove("performance")
        self.assertEqual(plan(case)["reason"], "DISCLOSED_CARD_OPTIONS_UNVERIFIED")
        case = endorsement(response_ids=[0, 1])
        self.assertEqual(plan(case)["reason"], "CAREER_RESPONSE_OPTION_SET_MISMATCH")
        case = endorsement()
        case["options"][0]["outcomes"] = [
            {"probability_bps": 10000, "effects": {"simoleons": 100},
             "effect_source_ref": "ea:tuning", "job_lost": False, "irreversible": False},
        ]
        self.assertEqual(plan(case)["reason"], "DISCLOSED_CARD_OUTCOMES_CONFLICT")

    def test_port_submits_once_and_reconciles_post_shift_rewards(self):
        adapter = Adapter()
        port = CareerResponsePort(adapter)
        respond = lambda: port.respond(now_epoch_ms=100100, enabled=True)
        adapter.on_submit = lambda: self.assertEqual(respond()["state"], "RECONCILE_EXISTING_ATTEMPT")
        self.assertEqual(respond()["state"], "BETTERINSTINCTS_RESPONSE_SUBMITTED")
        self.assertEqual(len(adapter.requests), 1)
        request = adapter.requests[0]
        self.assertEqual(request["response_id"], 119)
        self.assertEqual(request["recipient_sim_id"], "1002001")
        self.assertTrue(request["require_fame_allowed"])
        self.assertEqual(request["process_instance_ref"], "process:one")
        response, effect, continuation = observed(request)
        valid = port.reconcile(request["session_ref"], request["event_ref"], response, effect, continuation)
        self.assertEqual(valid["state"], "RESPONSE_EFFECT_AND_RESUMPTION_SHAPE_MATCH")
        adapter.frame["event"]["event_revision"] = "rev:later"
        self.assertEqual(respond()["state"], "RECONCILE_EXISTING_ATTEMPT")
        adapter.frame["process_instance_ref"] = "process:restarted"
        self.assertEqual(respond()["reason"], "NATIVE_CAREER_RUNTIME_CHANGED")
        self.assertEqual(len(adapter.requests), 1)

        for patch, expected in (
            ({"observed_deltas": {"fame": 5, "performance": 4}}, "CAREER_NATIVE_EFFECT_OBSERVATION_MISSING"),
            ({"event_rewards_attributed": False}, "CAREER_NATIVE_EFFECT_OBSERVATION_MISSING"),
            ({"dispatch_ref": "dispatch:other"}, "CAREER_REWARD_DISPATCH_MISMATCH"),
            ({"save_ref": "slot:other"}, "CAREER_READBACK_SCOPE_MISMATCH"),
        ):
            result = port.reconcile(request["session_ref"], request["event_ref"], response,
                                    {**effect, **patch}, continuation)
            self.assertEqual(result["reason"], expected)
        result = port.reconcile(request["session_ref"], request["event_ref"], response,
                                effect, {**continuation, "shift_ref": "shift:other"})
        self.assertEqual(result["reason"], "CAREER_ACTIVITY_RESUMPTION_UNOBSERVED")

    def test_lost_return_cannot_replay_or_adopt_unrelated_ack(self):
        adapter = Adapter()
        adapter.behavior = "lost"
        port = CareerResponsePort(adapter)
        self.assertEqual(port.respond(now_epoch_ms=100100, enabled=True)["state"], "DISPATCH_OUTCOME_UNKNOWN")
        self.assertEqual(port.respond(now_epoch_ms=100100, enabled=True)["state"], "RECONCILE_EXISTING_ATTEMPT")
        request = adapter.requests[0]
        response, effect, continuation = observed(request)
        unrelated = port.reconcile(request["session_ref"], request["event_ref"],
                                   {**response, "attempt_ref": "attempt:other"}, effect, continuation)
        self.assertEqual(unrelated["reason"], "CAREER_ATTEMPT_ACK_MISMATCH")
        proved = port.reconcile(request["session_ref"], request["event_ref"], response, effect, continuation)
        self.assertEqual(proved["state"], "RESPONSE_EFFECT_AND_RESUMPTION_SHAPE_MATCH")
        self.assertEqual(len(adapter.requests), 1)

    def test_refusal_opt_out_and_missing_adapter(self):
        self.assertEqual(CareerResponsePort().respond(now_epoch_ms=100100, enabled=True)["state"],
                         "NATIVE_ADAPTER_REQUIRED")
        adapter = Adapter()
        port = CareerResponsePort(adapter)
        self.assertEqual(port.respond(now_epoch_ms=100100)["state"], "HOLD")
        adapter.frame["save_authorized"] = False
        self.assertEqual(port.respond(now_epoch_ms=100100, enabled=True)["state"], "REOBSERVE")
        self.assertEqual(adapter.requests, [])
        adapter.frame["save_authorized"] = True
        adapter.behavior = "REFUSED_NO_EFFECT"
        self.assertEqual(port.respond(now_epoch_ms=100100, enabled=True)["state"], "REOBSERVE")
        adapter.behavior = "SUBMITTED"
        self.assertEqual(port.respond(now_epoch_ms=100100, enabled=True)["reason"],
                         "FRESH_CAPTURE_AFTER_REFUSAL_REQUIRED")
        adapter.frame["event"].update(capture_ref="capture:new", captured_at_epoch_ms=100050)
        self.assertEqual(port.respond(now_epoch_ms=100100, enabled=True)["state"],
                         "BETTERINSTINCTS_RESPONSE_SUBMITTED")
