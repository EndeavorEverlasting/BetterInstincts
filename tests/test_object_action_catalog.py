"""P82 characterization: object menu learning is portable but never game authority."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from betterinstincts.object_action_catalog import (
    EVENT_SCHEMA, ObjectActionCatalogError, empty_catalog, ingest, load_catalog,
    record_event, recommend,
)
from betterinstincts import host_listener

PATCH = "1.121.361.1020"
SESSION = "catalog_test_session"
OBJ = "object:bed_123"
CLASS = "object_class:bed"
ACTION = "action:sleep"


def event(kind, seq, capture, **fields):
    return {"schema": EVENT_SCHEMA, "kind": kind, "seq": seq,
            "at_ms": 100000 + seq * 100,
            "capture_ref": capture, "source": "PLAYER", **fields}


def menu(seq, capture, *, obj=OBJ, klass=CLASS, version=PATCH):
    return event("menu", seq, capture, object_ref=obj, class_ref=klass,
                 game_version=version, actions=[ACTION, "action:nap"])


def selection(seq, capture, *, obj=OBJ, klass=CLASS, version=PATCH):
    return event("selection", seq, capture, object_ref=obj, class_ref=klass,
                 game_version=version, action_ref=ACTION,
                 interaction_ref="interaction:" + str(seq))


def outcome(seq, interaction, *, reviewed=True, result="helpful",
            domain="energy", new_capture=None):
    return event("outcome", seq, new_capture or "capture:result_" + str(seq),
                 interaction_ref=interaction, operator_reviewed=reviewed,
                 effects=[{"domain": domain, "result": result,
                           "evidence_ref": "evidence:observed_" + str(seq)}])


def cycle(state, i, *, reviewed=True, result="helpful", domain="energy"):
    start = i * 3 + 1
    capture = "capture:menu_" + str(i)
    for e in (menu(start, capture), selection(start + 1, capture),
              outcome(start + 2, "interaction:" + str(start + 1),
                      reviewed=reviewed, result=result, domain=domain)):
        state, receipt = ingest(state, e, session_id=SESSION)
        assert receipt["execute_allowed"] is False
    return state


def query(state, **changes):
    fields = {"session_id": SESSION, "game_version": PATCH,
              "object_ref": OBJ, "class_ref": CLASS,
              "capture_ref": "capture:menu_2", "now_ms": 101000,
              "available_actions": [ACTION, "action:nap"],
              "desired_domains": ["energy", "career"],
              "player_active": False, "player_queue_present": False}
    fields.update(changes)
    return recommend(state, **fields)


class ObjectActionLearningTests(unittest.TestCase):
    def test_three_reviewed_outcomes_promote_portable_advisory_only(self):
        state = empty_catalog()
        for i in range(3):
            state = cycle(state, i)
        recommendation = query(state)
        self.assertEqual(recommendation["state"], "ADVISORY_ONLY")
        self.assertEqual(recommendation["candidate"]["action_ref"], ACTION)
        self.assertEqual(recommendation["candidate"]["goal_domain"], "energy")
        self.assertEqual(recommendation["candidate"]["reviewed_helpful"], 3)
        self.assertFalse(recommendation["execute_allowed"])
        self.assertFalse(recommendation["cancel_allowed"])
        self.assertIsNone(recommendation["control_permit"])
        self.assertEqual(len(state["classes"]), 2)
        # The class evidence is portable; a new object's current menu is required.
        other = "object:another_bed"
        state, _ = ingest(state, menu(1, "capture:other_menu", obj=other),
                          session_id="other_session")
        other_query = query(state, session_id="other_session", object_ref=other,
                            capture_ref="capture:other_menu", now_ms=100200)
        self.assertEqual(other_query["state"], "ADVISORY_ONLY")

    def test_unknown_or_unreviewed_outcome_does_not_train(self):
        for reviewed, result in ((False, "helpful"), (True, "unknown")):
            state = empty_catalog()
            for i in range(3):
                state = cycle(state, i, reviewed=reviewed, result=result)
            self.assertEqual(query(state)["state"], "INSUFFICIENT_REVIEWED_UTILITY")

    def test_harmful_feedback_reduces_recommendation(self):
        state = empty_catalog()
        for i in range(5):
            state = cycle(state, i, result="harmful" if i >= 3 else "helpful")
        self.assertEqual(
            query(state, capture_ref="capture:menu_4", now_ms=101500)["state"],
            "INSUFFICIENT_REVIEWED_UTILITY",
        )

    def test_stale_or_incompatible_menu_abstains(self):
        state = empty_catalog()
        for i in range(3):
            state = cycle(state, i)
        for fields in (
            {"game_version": "1.121.999.1020"},
            {"capture_ref": "capture:elsewhere"},
            {"object_ref": "object:other"},
            {"class_ref": "object_class:fridge"},
            {"available_actions": [ACTION]},
            {"now_ms": 500000},
        ):
            self.assertEqual(query(state, **fields)["state"],
                             "REOBSERVE_CURRENT_OBJECT_MENU")

    def test_player_input_and_player_owned_queue_win(self):
        state = empty_catalog()
        for i in range(3):
            state = cycle(state, i)
        self.assertEqual(query(state, player_active=True)["state"], "PLAYER_FIRST")
        self.assertEqual(query(state, player_queue_present=True)["state"], "PLAYER_FIRST")

    def test_action_selection_requires_exact_fresh_menu(self):
        state, _ = ingest(empty_catalog(), menu(1, "capture:first"),
                          session_id=SESSION)
        for candidate in (
            selection(2, "capture:wrong"),
            selection(2, "capture:first", klass="object_class:fridge"),
            selection(2, "capture:first", version="1.122.1.1020"),
            {**selection(2, "capture:first"), "action_ref": "action:unknown"},
            {**selection(2, "capture:first"), "at_ms": 900000},
        ):
            with self.assertRaisesRegex(ObjectActionCatalogError,
                                        "SELECTION_NOT_IN_FRESH_MENU"):
                ingest(state, candidate, session_id=SESSION)

    def test_post_action_proof_must_be_distinct_and_matched(self):
        state, _ = ingest(empty_catalog(), menu(1, "capture:menu"),
                          session_id=SESSION)
        state, _ = ingest(state, selection(2, "capture:menu"),
                          session_id=SESSION)
        with self.assertRaisesRegex(ObjectActionCatalogError,
                                    "OUTCOME_UNMATCHED_OR_NOT_POST_ACTION"):
            ingest(state, outcome(3, "interaction:2", new_capture="capture:menu"),
                   session_id=SESSION)
        with self.assertRaisesRegex(ObjectActionCatalogError,
                                    "OUTCOME_UNMATCHED_OR_NOT_POST_ACTION"):
            ingest(state, outcome(3, "interaction:not_selected"),
                   session_id=SESSION)
        with self.assertRaisesRegex(ObjectActionCatalogError,
                                    "OUTCOME_UNMATCHED_OR_NOT_POST_ACTION"):
            ingest(state, {**outcome(3, "interaction:2"), "at_ms": 999999999},
                   session_id=SESSION)

    def test_replay_is_idempotent_and_gap_is_rejected(self):
        state, _ = ingest(empty_catalog(), menu(1, "capture:menu"),
                          session_id=SESSION)
        again, receipt = ingest(state, menu(1, "capture:menu"),
                                session_id=SESSION)
        self.assertEqual(state, again)
        self.assertFalse(receipt["recorded"])
        with self.assertRaisesRegex(ObjectActionCatalogError, "EVENT_SEQUENCE_GAP"):
            ingest(state, menu(3, "capture:skip"), session_id=SESSION)

    def test_bad_fields_and_untrusted_text_denied(self):
        original = menu(1, "capture:menu")
        for bad in (
            {**original, "sim_name": "Private User"},
            {**original, "game_version": "UNKNOWN"},
            {**original, "actions": [ACTION, ACTION]},
            {**original, "source": "OS_KEYLOGGER"},
            {**original, "seq": True},
        ):
            with self.assertRaises(ObjectActionCatalogError):
                ingest(empty_catalog(), bad, session_id=SESSION)

    def test_atomic_local_persistence_and_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "object-action.json"
            receipt = record_event(path, menu(1, "capture:menu"),
                                   session_id=SESSION)
            self.assertTrue(receipt["recorded"])
            self.assertEqual(load_catalog(path)["revision"], 1)
            self.assertFalse(record_event(path, menu(1, "capture:menu"),
                                          session_id=SESSION)["recorded"])
            self.assertEqual(load_catalog(path)["revision"], 1)

    def test_active_host_session_port_requires_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "session.json").write_text(json.dumps({"state": "ACTIVE"}))
            with patch.object(host_listener, "_session_dir", return_value=root), \
                    patch.object(host_listener, "OUTPUT", root):
                with self.assertRaisesRegex(
                    host_listener.HostListenerError, "EXPLICIT_OBJECT"
                ):
                    host_listener.observe_object_action(SESSION, menu(1, "capture:menu"))
                result = host_listener.observe_object_action(
                    SESSION, menu(1, "capture:menu"), explicit_opt_in=True)
                self.assertTrue(result["catalog"]["recorded"])
                self.assertFalse(result["execute_clicks"])
                state = host_listener.suggest_object_action(
                    SESSION, {k: v for k, v in {
                        "game_version": PATCH, "object_ref": OBJ,
                        "class_ref": CLASS, "capture_ref": "capture:menu",
                        "now_ms": 100200,
                        "available_actions": [ACTION, "action:nap"],
                        "desired_domains": ["energy"],
                        "player_active": False,
                        "player_queue_present": False,
                    }.items()})
                self.assertEqual(state["state"], "INSUFFICIENT_REVIEWED_UTILITY")
                (root / "session.json").write_text(json.dumps({"state": "INACTIVE"}))
                with self.assertRaisesRegex(
                    host_listener.HostListenerError, "OBJECT_SESSION_NOT_ACTIVE"
                ):
                    host_listener.observe_object_action(
                        SESSION, menu(2, "capture:later"), explicit_opt_in=True)


if __name__ == "__main__":
    unittest.main()
