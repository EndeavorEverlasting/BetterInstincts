"""The actual computer-use lane must pause, journal and feed codification."""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from betterinstincts import host_listener
from betterinstincts.agent_control_runner import AgentControlRunner, AgentControlRunnerError
from betterinstincts.control_discovery import (
    SCHEMA, EVENT_SCHEMA, ControlDiscoveryError, compact_handoff,
    coverage, codification_work_items, ingest, new_session,
)
from betterinstincts.player_presence import PresenceProbe
from betterinstincts.workflow_interop import CooperativeScreenQueue


def base():
    return new_session(
        session_id="bi-control-01", household_ref="household:opaque",
        goal_id="goal:fertilizer", game_patch="1.121.361.1020",
        fallback_reason="EXISTING_RULE_FAILED",
        listener_active=True, explicit_opt_in=True,
    )


def event(ledger, kind, work="work:plant2", **kwargs):
    return ingest(ledger, {
        "schema": EVENT_SCHEMA, "seq": ledger["next_seq"],
        "kind": kind, "work_id": work, **kwargs,
    })


def prepared(ledger, work="work:plant2"):
    return event(
        ledger, "PREPARE", work,
        action_ref="fertilize:select",
        object_class_ref="object_class:planter",
        before_capture_ref="capture:before",
        authority_ref="admission:checked",
    )


class SemanticDiscoveryTests(unittest.TestCase):
    def test_mixed_microsystem_routes_preserve_per_effect_reason_and_trace(self):
        state = base()
        cases = [
            ("gardening", "NATIVE_ROUTE_MISSING", "betterinstincts/gardening_service.py"),
            ("laundry-availability", "EXISTING_RULE_FAILED", "betterinstincts/household_upkeep.py"),
            ("career-progress", "DISPOSABLE_GAME_DIAGNOSTIC", "betterinstincts/career_service.py"),
            ("preference-offer", "NATIVE_ROUTE_UNPROVEN", "betterinstincts/preference_prompts.py"),
        ]
        for index, (mechanic_id, reason, owner) in enumerate(cases):
            work = f"work:{index}"
            state = event(state, "PREPARE", work, action_ref="action:check",
                          object_class_ref="class:target", before_capture_ref=f"capture:before{index}",
                          authority_ref="authority:admitted", mechanic_id=mechanic_id,
                          fallback_reason=reason)
            state = event(state, "DISPATCH_BOUNDARY", work)
            state = event(state, "QUEUE_STATUS", work, queue_state="COMPLETED")
            state = event(state, "OUTCOME", work, outcome="HARMFUL" if index == 1 else "HELPFUL",
                          after_capture_ref=f"capture:after{index}", outcome_ref=f"outcome:{index}",
                          player_interrupted=False)
            item, = codification_work_items(state, offset=index, limit=1)["items"]
            self.assertEqual(item["source_routing"]["module_ref"], owner)
            self.assertTrue(item["source_routing"]["existing_test_refs"])
            self.assertEqual(item["source_routing"]["mechanic_id"], mechanic_id)
            self.assertEqual(item["fallback_reason"], reason)
            self.assertEqual(item["native_responder_gap"], index != 2)
            trace = item["effect_trace"]
            self.assertEqual(trace["before"]["capture_ref"], f"capture:before{index}")
            self.assertEqual(trace["after"]["capture_ref"], f"capture:after{index}")
            self.assertEqual(trace["during"]["dispatch_boundary_seq"], 4 * index + 2)
            self.assertFalse(trace["native_resolution_proved"])
            self.assertFalse(item["source_verified"])

    def test_legacy_identification_is_evidenced_and_cannot_relabel_work(self):
        state = prepared(base())
        self.assertEqual(codification_work_items(state)["items"][0]["source_routing"]["state"],
                         "MECHANIC_ID_REQUIRED")
        state = event(state, "MECHANIC_IDENTIFIED", mechanic_id="fertilizer-sourcing",
                      classification_ref="review:original-garden-capture")
        route = codification_work_items(state)["items"][0]["source_routing"]
        self.assertEqual(route["classification_ref"], "review:original-garden-capture")
        self.assertEqual(route["module_ref"], "betterinstincts/fertilizer_workflow.py")
        self.assertNotIn("mechanic_id", state["events"][0])
        with self.assertRaisesRegex(ControlDiscoveryError, "IDENTIFICATION_ALREADY_FIXED"):
            event(state, "MECHANIC_IDENTIFIED", mechanic_id="career-progress",
                  classification_ref="review:different")

    def test_gap_unregistered_and_unavailable_registry_keep_work_open(self):
        for mechanic_id, expected in (("pet-care", "MECHANIC_OWNER_GAP"),
                                      ("new-mechanic", "MECHANIC_NOT_REGISTERED")):
            with self.subTest(mechanic_id=mechanic_id):
                state = event(prepared(base()), "MECHANIC_IDENTIFIED", mechanic_id=mechanic_id,
                              classification_ref="review:target")
                state = event(state, "QUEUE_STATUS", queue_state="NEEDS_RECONCILIATION")
                state = event(state, "OUTCOME", outcome="HARMFUL", after_capture_ref="capture:after",
                              outcome_ref="outcome:failed", player_interrupted=False)
                item = codification_work_items(state)["items"][0]
                self.assertEqual(item["source_routing"]["state"], expected)
                self.assertEqual(item["next_gate"], "RESOLVE_MECHANIC_SOURCE_OWNER")
                with self.assertRaisesRegex(ControlDiscoveryError, "MECHANIC_SOURCE_OWNER_REQUIRED"):
                    event(state, "CODIFICATION_RECEIPT", module_ref="betterinstincts/priority.py",
                          test_ref="test:case", commit_ref="commit:pending", review_ref="review:case")
        with patch("betterinstincts.control_discovery.load_registry", side_effect=OSError):
            item = codification_work_items(state)["items"][0]
            self.assertEqual(item["source_routing"]["state"], "MECHANICS_REGISTRY_UNAVAILABLE")
            self.assertEqual(item["observed_outcome"], "HARMFUL")

    def test_codification_claim_must_match_routed_source_owner(self):
        state = event(prepared(base()), "MECHANIC_IDENTIFIED", mechanic_id="gardening",
                      classification_ref="review:garden")
        state = event(state, "QUEUE_STATUS", queue_state="COMPLETED")
        state = event(state, "OUTCOME", outcome="HELPFUL", after_capture_ref="capture:after",
                      outcome_ref="outcome:readback", player_interrupted=False)
        claim = dict(test_ref="test:new-regression", commit_ref="commit:pending", review_ref="review:case")
        with self.assertRaisesRegex(ControlDiscoveryError, "CODIFICATION_MECHANIC_OWNER_MISMATCH"):
            event(state, "CODIFICATION_RECEIPT", module_ref="betterinstincts/career_service.py", **claim)
        state = event(state, "CODIFICATION_RECEIPT", module_ref="betterinstincts/gardening_service.py", **claim)
        item = codification_work_items(state)["items"][0]
        self.assertEqual(item["next_gate"], "VERIFY_COMMIT_TEST_AND_MAIN_READBACK")
        self.assertFalse(item["source_verified"])

    def test_prepare_rejects_paths_and_bad_effect_reasons(self):
        fields = dict(action_ref="action:test", object_class_ref="class:target",
                      before_capture_ref="capture:before", authority_ref="authority:admitted")
        for invalid in ({"mechanic_id": "other/path"}, {"fallback_reason": "UNVERIFIED"},
                        {"fallback_reason": []}):
            with self.subTest(invalid=invalid), self.assertRaises(ControlDiscoveryError):
                event(base(), "PREPARE", **fields, **invalid)

    def test_no_implicit_listener_or_opt_in(self):
        for overrides in (
            {"listener_active": False},
            {"explicit_opt_in": False},
            {"fallback_reason": "NATIVE_ALREADY_WORKING"},
            {"game_patch": "UNKNOWN"},
        ):
            kwargs = dict(
                session_id="bi-control-01", household_ref="household:opaque",
                goal_id="goal:fertilizer", game_patch="1.121.361.1020",
                fallback_reason="EXISTING_RULE_FAILED",
                listener_active=True, explicit_opt_in=True,
            )
            kwargs.update(overrides)
            with self.subTest(overrides=overrides):
                with self.assertRaises(ControlDiscoveryError):
                    new_session(**kwargs)

    def test_every_prepared_action_requires_evidence_and_codification(self):
        state = prepared(base())
        self.assertEqual(coverage(state)["counts"]["prepared"], 1)
        state = event(state, "QUEUE_STATUS", queue_state="COMPLETED")
        self.assertEqual(coverage(state)["counts"]["awaiting_outcome"], 1)
        state = event(state, "OUTCOME", outcome="HELPFUL",
                      after_capture_ref="capture:after",
                      outcome_ref="outcome:plant2-fertilized",
                      player_interrupted=False)
        self.assertEqual(coverage(state)["counts"]["review_ready"], 1)
        self.assertEqual(coverage(state)["unresolved_total"], 1)
        state = event(
            state, "CODIFICATION_RECEIPT",
            module_ref="betterinstincts/gardening_service.py",
            test_ref="tests/test_gardening.py",
            commit_ref="commit:proposed",
            review_ref="review:proposed",
        )
        self.assertEqual(coverage(state)["counts"]["receipt_submitted"], 1)
        self.assertEqual(coverage(state)["unresolved_total"], 0)
        self.assertEqual(coverage(state)["source_verification_pending_total"], 1)
        self.assertEqual(coverage(state)["source_verified_total"], 0)
        self.assertFalse(coverage(state)["all_attempts_source_verified"])
        self.assertEqual(
            codification_work_items(state)["items"][0]["next_gate"],
            "VERIFY_COMMIT_TEST_AND_MAIN_READBACK",
        )
        self.assertEqual(
            state["steps"]["work:plant2"]["codification"]["status"],
            "RECEIPT_SUBMITTED_NOT_MERGE_VERIFIED",
        )
        self.assertFalse(coverage(state)["execute_allowed"])

    def test_invalid_unprepared_result_and_raw_payload_rejected(self):
        with self.assertRaisesRegex(ControlDiscoveryError, "UNPREPARED_EFFECT"):
            event(base(), "QUEUE_STATUS", queue_state="COMPLETED")
        with self.assertRaisesRegex(ControlDiscoveryError, "PREPARE_FIELDS_INVALID"):
            event(base(), "PREPARE", action_ref="some", raw_screenshot="secret")
        state = prepared(base())
        with self.assertRaisesRegex(ControlDiscoveryError, "POST_ACTION_CAPTURE"):
            event(event(state, "QUEUE_STATUS", queue_state="COMPLETED"),
                  "OUTCOME", outcome="HELPFUL",
                  after_capture_ref="capture:before", outcome_ref="outcome:one",
                  player_interrupted=False)

    def test_stale_or_duplicate_sequence_and_false_outcome_block(self):
        state = prepared(base())
        with self.assertRaisesRegex(ControlDiscoveryError, "EVENT_SEQUENCE_INVALID"):
            ingest(state, {
                "schema": EVENT_SCHEMA, "seq": 1,
                "kind": "QUEUE_STATUS", "work_id": "work:plant2",
                "queue_state": "COMPLETED",
            })
        with self.assertRaisesRegex(ControlDiscoveryError, "ACTION_NOT_OBSERVED_AS_ATTEMPTED"):
            event(state, "OUTCOME", outcome="HELPFUL",
                  after_capture_ref="capture:after", outcome_ref="outcome:one",
                  player_interrupted=False)

    def test_interrupted_effect_is_not_silently_codified(self):
        state = prepared(base())
        state = event(state, "QUEUE_STATUS", queue_state="NEEDS_RECONCILIATION")
        state = event(state, "OUTCOME", outcome="UNKNOWN",
                      after_capture_ref="capture:after",
                      outcome_ref="observation:uncertain",
                      player_interrupted=True)
        self.assertEqual(coverage(state)["counts"]["interrupted"], 1)
        self.assertEqual(
            coverage(state)["unresolved"][0]["next_gate"],
            "RECONCILE_HUMAN_INTERRUPTION",
        )
        with self.assertRaisesRegex(ControlDiscoveryError, "REVIEW_OUTCOME_BEFORE_CODIFICATION"):
            event(state, "CODIFICATION_RECEIPT",
                  module_ref="betterinstincts/gardening_service.py",
                  test_ref="tests/test_gardening.py",
                  commit_ref="commit:one", review_ref="review:one")

    def test_passive_semantic_discovery_captured_for_codification(self):
        state = prepared(base())
        state = event(
            state, "DISCOVERY", discovery_kind="OBJECT_AFFORDANCE",
            fact_ref="fact:fertilizer-menu", source_ref="sensor:calibrated",
            evidence_ref="capture:menu-observed",
        )
        self.assertEqual(state["steps"]["work:plant2"]["discoveries"][0]["fact_ref"],
                         "fact:fertilizer-menu")
        work = codification_work_items(state)["items"][0]
        self.assertEqual(len(work["discoveries"]), 1)
        self.assertEqual(work["discoveries"][0]["source_ref"], "sensor:calibrated")
        self.assertEqual(compact_handoff(state)["codification_work"]["items"][0]["discoveries"],
                         work["discoveries"])
        with self.assertRaisesRegex(ControlDiscoveryError, "DUPLICATE_DISCOVERY"):
            event(
                state, "DISCOVERY", discovery_kind="OBJECT_AFFORDANCE",
                fact_ref="fact:fertilizer-menu", source_ref="sensor:calibrated",
                evidence_ref="capture:menu-observed",
            )
        with self.assertRaisesRegex(ControlDiscoveryError, "DISCOVERY_FIELDS_INVALID"):
            event(
                state, "DISCOVERY", discovery_kind="ACTION_MENU",
                fact_ref="fact:menu", source_ref="sensor:calibrated",
                evidence_ref="capture:menu", raw_keystrokes="PRIVATE",
            )

    def test_discoveries_have_finite_budget_and_cannot_arrive_after_claimed_code(self):
        state = prepared(base())
        for i in range(6):
            state = event(
                state, "DISCOVERY", discovery_kind="ACTION_MENU",
                fact_ref="fact:menu%d" % i,
                source_ref="sensor:calibrated",
                evidence_ref="capture:menu%d" % i,
            )
        with self.assertRaisesRegex(ControlDiscoveryError, "DISCOVERY_STEP_BUDGET"):
            event(
                state, "DISCOVERY", discovery_kind="ACTION_MENU",
                fact_ref="fact:extra", source_ref="sensor:calibrated",
                evidence_ref="capture:extra",
            )
        state = event(state, "QUEUE_STATUS", queue_state="COMPLETED")
        state = event(state, "OUTCOME", outcome="HELPFUL",
                      after_capture_ref="capture:after",
                      outcome_ref="outcome:verified", player_interrupted=False)
        state = event(state, "CODIFICATION_RECEIPT",
                      module_ref="betterinstincts/gardening_service.py",
                      test_ref="tests/test_gardening.py",
                      commit_ref="commit:source", review_ref="review:pending")
        with self.assertRaisesRegex(ControlDiscoveryError, "DISCOVERY_AFTER_CODIFICATION"):
            event(
                state, "DISCOVERY", discovery_kind="ACTION_MENU",
                fact_ref="fact:late", source_ref="sensor:calibrated",
                evidence_ref="capture:late",
            )

    def test_every_attempt_has_paged_source_and_regression_work(self):
        state = base()
        for i in range(9):
            state = prepared(state, "work:step%d" % i)
        first = codification_work_items(state, limit=4)
        second = codification_work_items(state, offset=first["next_offset"], limit=4)
        last = codification_work_items(state, offset=second["next_offset"], limit=4)
        ids = [item["work_id"] for page in (first, second, last) for item in page["items"]]
        self.assertEqual(len(ids), 9)
        self.assertEqual(len(set(ids)), 9)
        self.assertIsNone(last["next_offset"])
        self.assertTrue(all(item["required_regression"] for page in (first, second, last)
                            for item in page["items"]))
        self.assertTrue(all(not item["source_verified"] for page in (first, second, last)
                            for item in page["items"]))
        self.assertEqual(compact_handoff(state)["codification_work"]["total_attempted"], 9)
        self.assertNotIn("events", compact_handoff(state))
        with self.assertRaisesRegex(ControlDiscoveryError, "CODIFICATION_PAGE_INVALID"):
            codification_work_items(state, limit=9)

    def test_interrupted_attempt_remains_source_obligation(self):
        state = prepared(base())
        state = event(state, "QUEUE_STATUS", queue_state="NEEDS_RECONCILIATION")
        state = event(state, "OUTCOME", outcome="UNKNOWN",
                      after_capture_ref="capture:after",
                      outcome_ref="observation:uncertain",
                      player_interrupted=True)
        item = codification_work_items(state)["items"][0]
        self.assertEqual(item["next_gate"], "RECONCILE_INTERRUPTED_OUTCOME")
        self.assertEqual(item["observed_outcome"], "UNKNOWN")
        self.assertEqual(coverage(state)["total_attempts"], 1)

    def test_historical_assisted_yes_never_acquires_native_proof(self):
        fixture = Path(__file__).parent / "fixtures/control-discovery/video-gaming-assisted.v1.json"
        historical = json.loads(fixture.read_text(encoding="utf-8"))
        self.assertEqual(historical["during"]["origin"], "AGENT_FALLBACK")
        self.assertTrue(historical["after"]["visible_dialog_dismissed"])
        self.assertIsNone(historical["during"]["instrumented_dispatch_boundary"])
        self.assertIsNone(historical["current_native_ack"])
        self.assertIsNone(historical["current_native_effect"])
        # Reproduce the observed evidence ceiling in an offline journal fixture.
        state = new_session(
            session_id="fixture:repeat-offer", household_ref="fixture:household",
            goal_id="fixture:preference", game_patch=historical["game_patch"],
            fallback_reason=historical["fallback_reason"],
            listener_active=True, explicit_opt_in=True,
        )
        self.assertEqual(historical["before"]["visible_choices"], ["YES", "NO"])
        state = event(
            state, "PREPARE", action_ref="video-gaming:yes",
            object_class_ref="dialog:adventure-moment",
            before_capture_ref="fixture:open-dialog", authority_ref="fixture:historical-assistance",
        )
        state = event(state, "QUEUE_STATUS", queue_state="COMPLETED")
        state = event(
            state, "OUTCOME", outcome="HELPFUL", after_capture_ref="fixture:live-mode",
            outcome_ref="fixture:dialog-dismissal", player_interrupted=False,
        )
        item = codification_work_items(state)["items"][0]
        self.assertEqual("video-gaming:yes", item["action_ref"])
        self.assertTrue(item["native_responder_gap"])
        self.assertEqual("REPLAY_OBSERVED_BEHAVIOR_OR_FAILURE", item["required_regression"][0])
        self.assertFalse(item["effect_trace"]["native_resolution_proved"])
        self.assertIsNone(item["effect_trace"]["during"]["dispatch_boundary_seq"])
        self.assertEqual(item["next_gate"], "IMPLEMENT_SOURCE_RULE_AND_REGRESSION_TEST")

    def test_unknown_effect_stays_open_until_fresh_readback(self):
        state = event(prepared(base()), "DISPATCH_BOUNDARY")
        state = event(state, "QUEUE_STATUS", queue_state="NEEDS_RECONCILIATION")
        state = event(state, "OUTCOME", outcome="UNKNOWN",
                      after_capture_ref="capture:uncertain", outcome_ref="outcome:unavailable",
                      player_interrupted=False)
        self.assertEqual(codification_work_items(state)["items"][0]["next_gate"],
                         "RECONCILE_UNKNOWN_OUTCOME")
        with self.assertRaisesRegex(ControlDiscoveryError, "REVIEW_OUTCOME"):
            event(state, "CODIFICATION_RECEIPT", module_ref="betterinstincts/example.py",
                  test_ref="tests/test_example.py", commit_ref="commit:one", review_ref="review:one")
        with self.assertRaisesRegex(ControlDiscoveryError, "OUTCOME_ALREADY_RECORDED"):
            event(state, "OUTCOME", outcome="NEUTRAL", after_capture_ref="capture:uncertain",
                  outcome_ref="outcome:observed", player_interrupted=False)
        reconciled = event(state, "OUTCOME", outcome="NEUTRAL",
                           after_capture_ref="capture:verified", outcome_ref="outcome:observed",
                           player_interrupted=False)
        self.assertEqual(codification_work_items(reconciled)["items"][0]["next_gate"],
                         "IMPLEMENT_SOURCE_RULE_AND_REGRESSION_TEST")
        self.assertEqual(len(state["events"]) + 1, len(reconciled["events"]))

    def test_dispatch_boundary_needs_preparation_and_is_one_shot(self):
        with self.assertRaisesRegex(ControlDiscoveryError, "UNPREPARED"):
            event(base(), "DISPATCH_BOUNDARY")
        begun = event(prepared(base()), "DISPATCH_BOUNDARY")
        with self.assertRaisesRegex(ControlDiscoveryError, "DISPATCH_ALREADY"):
            event(begun, "DISPATCH_BOUNDARY")
        terminal = event(prepared(base()), "QUEUE_STATUS", queue_state="COMPLETED")
        with self.assertRaisesRegex(ControlDiscoveryError, "DISPATCH_ALREADY"):
            event(terminal, "DISPATCH_BOUNDARY")

    def test_fixture_paging_reuses_canonical_handoff(self):
        state = prepared(prepared(base(), "work:1"), "work:2")
        page = compact_handoff(state, offset=1, limit=1)["codification_work"]
        self.assertEqual(page["items"][0]["work_id"], "work:2")
        self.assertIsNone(page["next_offset"])

    def test_bounded_digest_no_raw_events(self):
        state = base()
        for i in range(12):
            state = prepared(state, f"work:step{i}")
        digest = compact_handoff(state)
        self.assertEqual(digest["events_count"], 12)
        self.assertEqual(digest["codification_coverage"]["unresolved_total"], 12)
        self.assertEqual(len(digest["codification_coverage"]["unresolved"]), 8)
        self.assertEqual(digest["codification_coverage"]["unresolved_truncated"], 4)
        self.assertNotIn("events", digest)
        self.assertTrue(digest["requires_fresh_control_admission"])


class PersistentListenerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root_override = patch.object(host_listener, "ROOT", Path(self.tmp.name))
        self.root_override.start()
        self.addCleanup(self.root_override.stop)
        self.override = patch.object(host_listener, "OUTPUT", Path(self.tmp.name))
        self.override.start()
        self.addCleanup(self.override.stop)
        host_listener.activate("bi-control-01")
        host_listener.open_control_discovery(
            "bi-control-01", household_ref="household:opaque",
            goal_id="goal:fertilizer", game_patch="1.121.361.1020",
            fallback_reason="EXISTING_RULE_FAILED", explicit_opt_in=True,
        )

    def test_journal_requires_opt_in_and_active_session(self):
        with self.assertRaisesRegex(host_listener.HostListenerError, "EXPLICIT"):
            host_listener.record_control_discovery("bi-control-01", {})
        with self.assertRaisesRegex(host_listener.HostListenerError, "ALREADY_EXISTS"):
            host_listener.open_control_discovery(
                "bi-control-01", household_ref="household:opaque",
                goal_id="goal:fertilizer", game_patch="1.121.361.1020",
                fallback_reason="EXISTING_RULE_FAILED", explicit_opt_in=True,
            )
        host_listener.deactivate("bi-control-01")
        with self.assertRaisesRegex(host_listener.HostListenerError, "NOT_ACTIVE"):
            host_listener.record_control_discovery(
                "bi-control-01", {}, explicit_opt_in=True)

    def test_persistent_atomic_event_and_compact_recovery(self):
        state = base()
        item = {
            "schema": EVENT_SCHEMA, "seq": 1, "kind": "PREPARE",
            "work_id": "work:plant2", "action_ref": "fertilize:select",
            "object_class_ref": "object_class:planter",
            "before_capture_ref": "capture:before",
            "authority_ref": "admission:checked",
        }
        receipt = host_listener.record_control_discovery(
            "bi-control-01", item, explicit_opt_in=True)
        self.assertEqual(receipt["event_count"], 1)
        self.assertEqual(receipt["handoff"]["codification_coverage"]["total_attempts"], 1)
        self.assertEqual(host_listener.read_control_discovery("bi-control-01")["events_count"], 1)
        with self.assertRaises(host_listener.HostListenerError):
            host_listener.record_control_discovery(
                "bi-control-01", item, explicit_opt_in=True)


class AgentControlRunTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def parent_handoff():
        return {
            "schema": "betterinstincts.agent-context/v1",
            "household_ref": "household:opaque",
            "game_build": "patch:verified-for-test",
            "parent_objective": "Keep household Sims safe and continue goals.",
            "active_goal_id": "goal:fertilizer",
            "next_gate": "FRESH_OUTCOME_OBSERVATION",
            "source_revision": "commit:tested",
            "corrections": ["Protect human screen control."],
            "rejected_paths": ["Blind repeat."],
            "blockers": [],
        }

    async def test_existing_runner_boundary_preserves_effect_during_human_pause(self):
        self.prepare()
        paused = await self.runner.pulse()
        self.assertEqual(paused["state"], "WAITING_FOR_USER")
        decision = self.runner.assess_parent_turn_boundary(
            self.parent_handoff(), player_presence="ACTIVE",
            game_state="PAUSED",
        )
        self.assertEqual(decision["gate"], "YIELD_EFFECTS_KEEP_LISTENER")
        self.assertTrue(decision["listener_remains_active"])
        self.assertTrue(decision["effect_pending"])
        self.assertFalse(decision["parent_complete"])
        self.assertEqual(len(self.queue.pending), 1)
        decision = self.runner.assess_parent_turn_boundary(
            self.parent_handoff(), player_presence="ACTIVE",
            game_state="PAUSED", safe_offline_action="Read queued work outcomes",
        )
        self.assertEqual(decision["gate"], "CONTINUE_OFFLINE_WHILE_PLAYER_ACTIVE")
        self.assertEqual(len(self.queue.pending), 1)
        self.assertEqual(host_listener.status("bi-control-01")["state"], "ACTIVE")

    async def test_completed_input_not_parent_completion_without_outcome(self):
        self.age = 16000
        self.prepare()
        done = await self.runner.pulse()
        self.assertEqual(done["state"], "COMPLETED")
        result = self.runner.assess_parent_turn_boundary(
            self.parent_handoff(), player_presence="INACTIVE",
            game_state="RUNNING", claimed_acceptance_refs=["receipt:click-done"],
        )
        self.assertEqual(result["gate"], "RECONCILE_PENDING_EFFECT_OUTCOME")
        self.assertFalse(result["terminal_stop_proven"])
        self.assertEqual(self.runner.current_work_id, "work:plant2")
        self.assertEqual(host_listener.status("bi-control-01")["state"], "ACTIVE")

    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root_override = patch.object(host_listener, "ROOT", Path(self.tmp.name))
        self.root_override.start()
        self.addCleanup(self.root_override.stop)
        self.listener_patch = patch.object(host_listener, "OUTPUT", Path(self.tmp.name) / "events")
        self.listener_patch.start()
        self.addCleanup(self.listener_patch.stop)
        host_listener.activate("bi-control-01")
        host_listener.open_control_discovery(
            "bi-control-01", household_ref="household:opaque",
            goal_id="goal:fertilizer", game_patch="1.121.361.1020",
            fallback_reason="EXISTING_RULE_FAILED", explicit_opt_in=True,
        )
        self.age = 0
        self.executed = []

        async def instant(_):  # avoid real 0.2-second sleeps in tests
            await asyncio.sleep(0)

        self.queue = CooperativeScreenQueue(
            lambda: PresenceProbe(False, False, last_input_age_ms=self.age),
            lambda: True, lock_root=Path(self.tmp.name) / "locks",
            sleep=instant,
        )
        self.runner = AgentControlRunner("bi-control-01", self.queue)

    def prepare(self, effect=None, **attribution):
        async def validate():
            return True

        async def default_effect():
            self.executed.append("real-effect")

        return self.runner.prepare_effect(
            work_id="work:plant2", action_ref="fertilize:select",
            object_class_ref="object_class:planter",
            before_capture_ref="capture:before",
            authority_ref="admission:checked", validate=validate,
            effect=effect or default_effect, **attribution,
        )

    async def test_runner_persists_mechanic_before_dispatch_and_reports_its_owner(self):
        self.age = 16000

        async def effect():
            item, = host_listener.read_control_discovery("bi-control-01")["codification_work"]["items"]
            self.assertEqual(item["source_routing"]["mechanic_id"], "gardening")
            self.assertIsNotNone(item["effect_trace"]["during"]["dispatch_boundary_seq"])
            self.executed.append("real-effect")

        self.prepare(effect=effect, mechanic_id="gardening",
                     fallback_reason="NATIVE_ROUTE_UNPROVEN")
        self.assertEqual((await self.runner.pulse())["state"], "COMPLETED")
        receipt = self.runner.record_observed_outcome(
            outcome="HELPFUL", after_capture_ref="capture:after",
            outcome_ref="outcome:verified", player_interrupted=False,
        )
        item, = receipt["handoff"]["codification_work"]["items"]
        self.assertEqual(item["source_routing"]["module_ref"], "betterinstincts/gardening_service.py")
        self.assertEqual(item["fallback_reason"], "NATIVE_ROUTE_UNPROVEN")
        self.assertFalse(item["effect_trace"]["native_resolution_proved"])

    async def test_invalid_mechanic_does_not_prepare_or_enqueue(self):
        with self.assertRaisesRegex(host_listener.HostListenerError, "MECHANIC_ID_INVALID"):
            self.prepare(mechanic_id="private/path")
        self.assertFalse(self.queue.pending)
        self.assertIsNone(self.runner.current_work_id)
        self.assertEqual(host_listener.read_control_discovery("bi-control-01")["events_count"], 0)

    async def test_pause_preserves_control_session_then_idle_resumes(self):
        self.prepare()
        paused = await self.runner.pulse()
        self.assertEqual(paused["state"], "WAITING_FOR_USER")
        self.assertTrue(paused["listener_remains_active"])
        self.assertTrue(paused["behavior_paused_for_player"])
        self.assertEqual(self.executed, [])
        self.assertEqual(len(self.queue.pending), 1)
        self.age = 16000
        resumed = await self.runner.wait_and_pulse(max_checks=3)
        self.assertEqual(resumed["state"], "COMPLETED")
        self.assertEqual(self.executed, ["real-effect"])
        receipt = self.runner.record_observed_outcome(
            outcome="HELPFUL", after_capture_ref="capture:after",
            outcome_ref="outcome:fertilized", player_interrupted=False)
        self.assertEqual(receipt["handoff"]["codification_coverage"]["counts"]["review_ready"], 1)
        self.assertEqual(host_listener.status("bi-control-01")["state"], "ACTIVE")

    async def test_passive_observation_does_not_complete_waiting_screen_effect(self):
        self.prepare()
        first = await self.runner.pulse()
        self.assertEqual(first["state"], "WAITING_FOR_USER")
        observations = []

        async def validate_read_only():
            return True

        async def safe_semantic_read():
            observations.append("semantic:queue-observed")

        queued = self.runner.observe_while_paused(
            work_id="listen:queue", validate=validate_read_only,
            observe=safe_semantic_read,
        )
        self.assertEqual(queued["pending_effect_work_id"], "work:plant2")
        observed = await self.runner.pulse()
        self.assertEqual(observed["state"], "LISTENER_OBSERVATION_COMPLETED")
        self.assertEqual(observed["work_id"], "listen:queue")
        self.assertEqual(observations, ["semantic:queue-observed"])
        self.assertEqual(self.executed, [])
        self.assertEqual(self.runner.last_queue_state, "WAITING_FOR_USER")
        self.assertEqual(len(self.queue.pending), 1)
        with self.assertRaisesRegex(AgentControlRunnerError, "NO_OBSERVED_EFFECT_ATTEMPT"):
            self.runner.record_observed_outcome(
                outcome="HELPFUL", after_capture_ref="capture:after",
                outcome_ref="outcome:not-performed", player_interrupted=False,
            )
        # A human can keep using another application while the read-only
        # listener has completed; only the existing trusted idle gate resumes.
        self.age = 16000
        resumed = await self.runner.wait_and_pulse(max_checks=3)
        self.assertEqual(resumed["state"], "COMPLETED")
        self.assertEqual(self.executed, ["real-effect"])
        self.assertEqual(host_listener.status("bi-control-01")["state"], "ACTIVE")

    async def test_collect_semantic_discovery_while_user_operates(self):
        self.prepare()
        paused = await self.runner.pulse()
        self.assertEqual(paused["state"], "WAITING_FOR_USER")
        receipt = self.runner.record_semantic_discovery(
            work_id="work:plant2", discovery_kind="OBJECT_AFFORDANCE",
            fact_ref="fact:fertilizer", source_ref="sensor:reviewed",
            evidence_ref="capture:menu",
        )
        item = receipt["handoff"]["codification_work"]["items"][0]
        self.assertEqual(item["discoveries"][0]["fact_ref"], "fact:fertilizer")
        self.assertEqual(self.executed, [])
        self.assertEqual(self.runner.last_queue_state, "WAITING_FOR_USER")

    async def test_passive_failure_cannot_be_misattributed_to_gameplay_effect(self):
        self.prepare()
        await self.runner.pulse()

        async def validate_read_only():
            return True

        async def failing_read():
            raise RuntimeError("semantic probe not calibrated")

        self.runner.observe_while_paused(
            work_id="listen:broken", validate=validate_read_only,
            observe=failing_read,
        )
        failed = await self.runner.pulse()
        self.assertEqual(failed["state"], "LISTENER_OBSERVATION_NEEDS_RECONCILIATION")
        self.assertEqual(self.runner.last_queue_state, "WAITING_FOR_USER")
        self.assertIn("listen:broken", self.queue.suspended)
        self.assertEqual(self.executed, [])
        self.age = 16000
        resumed = await self.runner.wait_and_pulse(max_checks=3)
        self.assertEqual(resumed["state"], "COMPLETED")
        self.assertEqual(self.executed, ["real-effect"])

    async def test_cannot_start_passive_observation_without_player_pause(self):
        self.prepare()

        async def valid(): return True
        async def read(): return None

        with self.assertRaisesRegex(AgentControlRunnerError, "PLAYER_PAUSE_REQUIRED"):
            self.runner.observe_while_paused(work_id="listen:early", validate=valid, observe=read)

    async def test_partial_exception_requires_reconciliation_not_replay(self):
        async def incomplete():
            self.executed.append("attempted")
            raise RuntimeError("uncertain game outcome")
        self.age = 16000
        self.prepare(effect=incomplete)
        status = await self.runner.pulse()
        self.assertEqual(status["state"], "NEEDS_RECONCILIATION")
        self.assertEqual(self.executed, ["attempted"])
        self.assertEqual(len(self.queue.pending), 0)
        self.assertIn("work:plant2", self.queue.suspended)
        receipt = self.runner.record_observed_outcome(
            outcome="UNKNOWN", after_capture_ref="capture:after",
            outcome_ref="observation:uncertain", player_interrupted=True)
        self.assertEqual(receipt["handoff"]["codification_coverage"]["counts"]["interrupted"], 1)
        with self.assertRaisesRegex(AgentControlRunnerError, "ONE_EFFECT_IN_FLIGHT"):
            self.prepare()

    async def test_dispatch_boundary_is_persisted_before_callback(self):
        async def observe_boundary():
            work = host_listener.read_control_discovery("bi-control-01")["codification_work"]
            trace = work["items"][0]["effect_trace"]
            self.assertEqual(trace["during"]["dispatch_boundary_seq"], 3)
            self.assertIsNone(trace["after"]["capture_ref"])
            self.executed.append("admitted")

        self.prepare(observe_boundary)
        waiting = await self.runner.pulse()
        self.assertEqual(waiting["state"], "WAITING_FOR_USER")
        item = host_listener.read_control_discovery("bi-control-01")["codification_work"]["items"][0]
        self.assertIsNone(item["effect_trace"]["during"]["dispatch_boundary_seq"])
        self.age = 16000
        self.assertEqual((await self.runner.pulse())["state"], "COMPLETED")
        self.assertEqual(self.executed, ["admitted"])

    async def test_missing_dispatch_journal_write_prevents_effect(self):
        self.age = 16000
        self.prepare()
        original = self.runner._write

        def reject_dispatch(kind, work_id, **fields):
            if kind == "DISPATCH_BOUNDARY":
                raise host_listener.HostListenerError("fixture:writer-busy")
            return original(kind, work_id, **fields)

        with patch.object(self.runner, "_write", side_effect=reject_dispatch):
            result = await self.runner.pulse()
        self.assertEqual(result["state"], "NEEDS_RECONCILIATION")
        self.assertFalse(self.executed)

    async def test_cannot_consume_control_without_prejournal(self):
        host_listener.deactivate("bi-control-01")
        with self.assertRaises(host_listener.HostListenerError):
            self.prepare()
        self.assertEqual(self.executed, [])


if __name__ == "__main__":
    unittest.main()
