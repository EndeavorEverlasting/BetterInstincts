"""P95 tooltip/event-time learning: behavioral associations, not cursor telemetry."""
import unittest
import uuid

from betterinstincts.hover_learning import (
    EVENT_SCHEMA, HoverLearningError, empty_state, evaluate, observe,
)
from betterinstincts.host_listener import HostListenerError, activate, deactivate, observe_hover


T = 1_800_000_000_000


def event(kind, n, at_ms, **fields):
    return {"schema": EVENT_SCHEMA, "id": f"ev_{n:04d}",
            "at_ms": at_ms, "kind": kind,
            "source": "sensor_supplied", **fields}


def seen(state, kind, n, at_ms, **fields):
    return observe(state, event(kind, n, at_ms, **fields))[0]


class HoverLearningTests(unittest.TestCase):
    def test_tooltip_polls_are_edge_deduplicated(self):
        st = seen(empty_state(), "tooltip_visible", 1, T,
                  target_ref="object:plant", tooltip_ref="tip:watering")
        same, result = observe(st, event(
            "tooltip_visible", 2, T + 1000,
            target_ref="object:plant", tooltip_ref="tip:watering"))
        self.assertEqual(result["state"], "UNCHANGED_TOOLTIP")
        self.assertEqual(same, st)
        self.assertEqual(evaluate(st, now_ms=T + 1000)["windows"]["180"]["tooltip_appearances"], 1)
        st = seen(st, "tooltip_hidden", 3, T + 2000, target_ref="object:plant")
        st = seen(st, "tooltip_visible", 4, T + 3000,
                  target_ref="object:plant", tooltip_ref="tip:watering")
        self.assertEqual(evaluate(st, now_ms=T + 3000)["windows"]["180"]["tooltip_appearances"], 2)

    def test_reviewed_association_requires_matched_action_and_evidence(self):
        st = seen(empty_state(), "tooltip_visible", 1, T,
                  target_ref="object:plant", tooltip_ref="tip:watering")
        for n in range(3):
            st = seen(st, "action", 10 + n * 2, T + n * 10000 + 1000,
                      target_ref="object:plant", action_ref="action:water",
                      interaction_ref=f"interaction:watering{n}")
            st = seen(st, "outcome", 11 + n * 2, T + n * 10000 + 2000,
                      interaction_ref=f"interaction:watering{n}",
                      outcome="helpful", evidence_ref=f"capture:proof{n}",
                      operator_reviewed=True)
        receipt = evaluate(st, now_ms=T + 30000)
        pattern = receipt["windows"]["180"]["patterns"][0]
        self.assertEqual(pattern["attempts"], 3)
        self.assertEqual(pattern["reviewed_helpful"], 3)
        self.assertEqual(pattern["reviewed_success_rate"], 1)
        self.assertTrue(pattern["learning_eligible"])
        self.assertFalse(receipt["automatically_trained"])
        self.assertFalse(receipt["execute_clicks"])
        self.assertIsNone(receipt["control_permit"])
        with self.assertRaisesRegex(HoverLearningError, "DUPLICATE_INTERACTION_OUTCOME"):
            seen(st, "outcome", 99, T + 31000,
                 interaction_ref="interaction:watering0", outcome="helpful",
                 evidence_ref="capture:replay", operator_reviewed=True)

    def test_unreviewed_outcome_does_not_claim_success(self):
        st = seen(empty_state(), "tooltip_visible", 1, T,
                  target_ref="object:tv", tooltip_ref="tip:watch")
        st = seen(st, "action", 2, T + 1, target_ref="object:tv",
                  interaction_ref="interaction:watch", action_ref="action:watch")
        st = seen(st, "outcome", 3, T + 2,
                  interaction_ref="interaction:watch", outcome="helpful",
                  evidence_ref="capture:observed", operator_reviewed=False)
        p = evaluate(st, now_ms=T + 3)["windows"]["180"]["patterns"][0]
        self.assertEqual(p["pending_review_or_outcome"], 1)
        self.assertEqual(p["reviewed_helpful"], 0)
        self.assertIsNone(p["reviewed_success_rate"])
        self.assertFalse(p["learning_eligible"])

    def test_target_and_outcome_provenance_fail_closed(self):
        st = seen(empty_state(), "tooltip_visible", 1, T,
                  target_ref="object:tv", tooltip_ref="tip:watch")
        with self.assertRaisesRegex(HoverLearningError, "ACTION_WITHOUT_MATCHED_TOOLTIP"):
            seen(st, "action", 2, T + 10, target_ref="object:fridge",
                 interaction_ref="interaction:food", action_ref="action:eat")
        with self.assertRaisesRegex(HoverLearningError, "OUTCOME_WITHOUT_MATCHED_ACTION"):
            seen(st, "outcome", 3, T + 10, interaction_ref="interaction:unknown",
                 outcome="helpful", evidence_ref="capture:whatever",
                 operator_reviewed=True)
        with self.assertRaisesRegex(HoverLearningError, "UNEXPECTED_HOVER_EVENT_FIELDS"):
            observe(st, {**event("hover", 4, T + 15, target_ref="object:tv"),
                         "raw_tooltip_text": "Private person name"})
        with self.assertRaisesRegex(HoverLearningError, "INVALID_TARGET_REF"):
            seen(st, "hover", 5, T + 16, target_ref="Raw visible label")

    def test_all_five_windows_respect_event_time_not_lifetime(self):
        st = empty_state()
        st = seen(st, "tooltip_visible", 1, T, target_ref="object:tv",
                  tooltip_ref="tip:watch")
        st = seen(st, "tooltip_hidden", 2, T + 1000, target_ref="object:tv")
        st = seen(st, "tooltip_visible", 3, T + 240000, target_ref="object:tv",
                  tooltip_ref="tip:watch")
        counts = evaluate(st, now_ms=T + 240000)["windows"]
        self.assertEqual([counts[str(x)]["tooltip_appearances"]
                          for x in (180, 300, 600, 1800, 3600)], [1, 2, 2, 2, 2])
        # Hour retention allows a long explicit session without unbounded history.
        st = seen(st, "hover", 4, T + 3840001, target_ref="object:tv")
        self.assertEqual(len(st["events"]), 1)

    def test_time_regression_and_duplicate_id_refused(self):
        st = seen(empty_state(), "hover", 1, T, target_ref="object:tv")
        with self.assertRaisesRegex(HoverLearningError, "HOVER_TIME_REGRESSION"):
            seen(st, "hover", 2, T - 1, target_ref="object:tv")
        with self.assertRaisesRegex(HoverLearningError, "DUPLICATE_HOVER_EVENT_ID"):
            seen(st, "hover", 1, T + 100, target_ref="object:tv")

    def test_event_budget_fails_closed(self):
        st = empty_state()
        for n in range(256):
            st = seen(st, "hover", n, T + n, target_ref="object:tv")
        with self.assertRaisesRegex(HoverLearningError, "HOVER_EVENT_BUDGET_EXCEEDED"):
            seen(st, "hover", 256, T + 256, target_ref="object:tv")


class ListenerHoverPortTests(unittest.TestCase):
    def setUp(self):
        self.sid = "hover_test_" + uuid.uuid4().hex[:16]
        activate(self.sid)

    def tearDown(self):
        deactivate(self.sid)

    def test_active_opt_in_session_persists_and_reports_without_control(self):
        e = event("tooltip_visible", 1, T, target_ref="object:plant",
                  tooltip_ref="tip:watering")
        with self.assertRaisesRegex(HostListenerError, "EXPLICIT_HOVER_OPT_IN_REQUIRED"):
            observe_hover(self.sid, e)
        first = observe_hover(self.sid, e, explicit_opt_in=True)
        self.assertEqual(first["transition"]["state"], "RECORDED_OBSERVATION")
        self.assertEqual(first["evaluation"]["event_count"], 1)
        self.assertFalse(first["execute_clicks"])
        again = observe_hover(self.sid, event(
            "tooltip_visible", 2, T + 1, target_ref="object:plant",
            tooltip_ref="tip:watering"), explicit_opt_in=True)
        self.assertEqual(again["transition"]["state"], "UNCHANGED_TOOLTIP")
        self.assertEqual(again["evaluation"]["event_count"], 1)
        self.assertIn("dist/host-listener/", first["state_path"])

    def test_deactivated_session_refuses_later_events(self):
        deactivate(self.sid)
        with self.assertRaisesRegex(HostListenerError, "HOVER_SESSION_NOT_ACTIVE"):
            observe_hover(self.sid, event("hover", 1, T, target_ref="object:tv"),
                          explicit_opt_in=True)


if __name__ == "__main__":
    unittest.main()
