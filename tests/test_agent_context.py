"""Cross-chat context, evidence and no-effect regression fixtures."""
import copy
import json
import unittest

from betterinstincts.agent_context import (
    SCHEMA, AgentContextError, compile_agent_context, continue_handoff,
    diagnose_context_failure, route_context, assess_agent_turn_boundary,
)

NOW = 1794650000.0
CAPTURE = "capture:household-7"


def handoff(**kwargs):
    base = {
        "schema": SCHEMA,
        "household_ref": "household:opaque-7",
        "game_build": "patch:verified-test",
        "parent_objective": "Keep Sims happy while sustaining the household.",
        "active_goal_id": "goal:fertilize",
        "next_gate": "REOBSERVE_CURRENT_QUEUE",
        "source_revision": "commit:demo",
        "corrections": ["Player-directed tasks outrank convenience."],
        "rejected_paths": ["Never repeat an unverified click."],
        "blockers": ["Live native game verification outstanding."],
    }
    base.update(kwargs)
    return base


def record(fact_id="fact:fertilizer", *, kind="MECHANIC", **kwargs):
    base = {
        "fact_id": fact_id,
        "kind": kind,
        "query_key": "fertilizer",
        "claim": "Fertilizer inventory needs an observed source.",
        "source_owner": "betterinstincts/mechanics_registry.py",
        "source_revision": "commit:demo",
        "evidence_ref": "receipt:one",
        "evidence_state": "REVIEWED_SOURCE",
        "household_ref": "household:opaque-7",
        "game_build": "patch:verified-test",
        "observed_at_unix": NOW - 5,
    }
    if kind in {"GOAL", "OBSERVATION"}:
        base["capture_ref"] = CAPTURE
    base.update(kwargs)
    return base


def build(rows, **kwargs):
    opts = dict(intent="MECHANIC", query_key="fertilizer",
                capture_ref=CAPTURE, now=NOW)
    opts.update(kwargs)
    return compile_agent_context(handoff(), rows, **opts)


class AgentContextTests(unittest.TestCase):
    def boundary(self, **updates):
        args = {
            "listener_active": True,
            "effect_pending": False,
            "effect_state": None,
            "player_presence": "INACTIVE",
            "game_state": "PAUSED",
            "host_access": "AVAILABLE",
        }
        args.update(updates)
        return assess_agent_turn_boundary(handoff(), **args)

    def test_paused_sims_and_old_agent_report_never_complete_parent(self):
        result = self.boundary()
        self.assertEqual(result["gate"], "GAME_PAUSED_PARENT_OPEN")
        self.assertFalse(result["parent_complete"])
        self.assertFalse(result["terminal_stop_proven"])
        self.assertEqual(result["parent_objective"], handoff()["parent_objective"])
        # Even a receipt-like name alone is insufficient to certify closure.
        claim = self.boundary(claimed_acceptance_refs=["receipt:played-13min"])
        self.assertEqual(claim["gate"], "VERIFY_CLAIMED_PARENT_ACCEPTANCE")
        self.assertFalse(claim["terminal_stop_proven"])

    def test_player_presence_pauses_effects_not_the_listener(self):
        for presence in ("ACTIVE", "UNKNOWN"):
            result = self.boundary(player_presence=presence,
                                   effect_pending=True, effect_state="WAITING_FOR_USER")
            self.assertEqual(result["gate"], "YIELD_EFFECTS_KEEP_LISTENER")
            self.assertTrue(result["turn_quiescence_supported"])
            self.assertTrue(result["listener_remains_active"])
            self.assertTrue(result["effect_pending"])
            result = self.boundary(
                player_presence=presence, effect_pending=True,
                effect_state="WAITING_FOR_USER",
                safe_offline_action="Inspect source-backed career fixtures",
            )
            self.assertEqual(result["gate"], "CONTINUE_OFFLINE_WHILE_PLAYER_ACTIVE")
            self.assertFalse(result["turn_quiescence_supported"])

    def test_pending_and_completed_unobserved_effects_block_agent_end(self):
        for state in ("WAITING_FOR_USER", "WAITING_FOR_AGENT", "BUSY"):
            result = self.boundary(effect_pending=True, effect_state=state)
            self.assertEqual(result["gate"], "PENDING_EFFECT_KEEP_LISTENER")
            self.assertFalse(result["turn_quiescence_supported"])
        for state in ("COMPLETED", "NEEDS_RECONCILIATION"):
            result = self.boundary(effect_pending=True, effect_state=state)
            self.assertEqual(result["gate"], "RECONCILE_PENDING_EFFECT_OUTCOME")
            self.assertFalse(result["terminal_stop_proven"])

    def test_evidenced_host_block_can_quiesce_without_closing_parent(self):
        result = self.boundary(host_access="UNAVAILABLE")
        self.assertEqual(result["gate"], "REOBSERVE_HOST_ACCESS")
        self.assertFalse(result["turn_quiescence_supported"])
        result = self.boundary(
            host_access="UNAVAILABLE", host_unavailable_ref="host:actual-unavailable",
        )
        self.assertEqual(result["gate"], "BLOCKED_EXACT_LOCAL_GAME_ACCESS")
        self.assertTrue(result["turn_quiescence_supported"])
        self.assertFalse(result["parent_complete"])
        result = self.boundary(host_access="UNAVAILABLE",
                               host_unavailable_ref="host:actual-unavailable",
                               safe_offline_action="Review existing queue tests")
        self.assertEqual(result["gate"], "CONTINUE_OFFLINE")

    def test_running_and_missing_listener_need_next_proof(self):
        self.assertEqual(self.boundary(game_state="RUNNING")["gate"],
                         "OBSERVE_ACTIVE_GAME_GOAL")
        self.assertEqual(self.boundary(listener_active=False)["gate"],
                         "RECOVER_EXPLICIT_LISTENER")
        paused = self.boundary(
            listener_active=False, player_presence="ACTIVE",
            effect_pending=True, effect_state="WAITING_FOR_USER",
        )
        self.assertEqual(paused["gate"], "RECOVER_EXPLICIT_LISTENER")
        self.assertFalse(paused["listener_remains_active"])
        self.assertTrue(paused["effect_pending"])
        offline = self.boundary(
            listener_active=False, player_presence="UNKNOWN",
            effect_pending=True, effect_state="WAITING_FOR_USER",
            safe_offline_action="Reconcile pending action evidence",
        )
        self.assertEqual(offline["gate"], "CONTINUE_OFFLINE_NO_ACTIVE_LISTENER")

        self.assertEqual(self.boundary(game_state="NOT_VISIBLE")["gate"],
                         "INVESTIGATE_NEXT_GATE")

    def test_turn_boundary_rejects_untrusted_or_ambiguous_snapshots(self):
        for payload in (
            {"player_presence": "no-one-here"},
            {"game_state": "ASSUME_LIVE"},
            {"listener_active": "yes"},
            {"effect_pending": 0},
            {"effect_state": "UNVERIFIED_COMPLETED"},
            {"effect_state": ["COMPLETED"]},
            {"player_presence": ["ACTIVE"]},
            {"game_state": {"state": "PAUSED"}},
            {"host_access": {"state": "UNAVAILABLE"}},
            {"safe_offline_action": ""},
            {"host_unavailable_ref": "user typed a long claim"},
            {"claimed_acceptance_refs": ["receipt:one", "receipt:one"]},
        ):
            with self.subTest(payload=payload), self.assertRaises(AgentContextError):
                self.boundary(**payload)
        original = handoff()
        assess_agent_turn_boundary(
            original, listener_active=True, effect_pending=False,
            effect_state=None, player_presence="INACTIVE", game_state="PAUSED",
        )
        self.assertEqual(original, handoff())

    def test_bounded_packet_reuses_canonical_source_not_effects(self):
        packet = build([record(), record("fact:goal", kind="GOAL", claim="Fertilize target 2.")])
        self.assertEqual(packet["status"], "EVIDENCE_SELECTED")
        self.assertEqual([r["kind"] for r in packet["records"]], ["GOAL", "MECHANIC"])
        self.assertFalse(packet["execute_allowed"])
        self.assertIsNone(packet["control_permit"])
        self.assertFalse(packet["retrieval"]["invoked"])
        self.assertIn("player", packet["handoff"]["corrections"][0].lower())
        self.assertLessEqual(packet["chars_used"], packet["char_budget"])
        self.assertEqual(packet["chars_used"], len(json.dumps(packet, sort_keys=True, separators=(",", ":"), ensure_ascii=True)))

    def test_deterministic_order_and_duplicate_evidence_dedup(self):
        one = record()
        two = record("fact:other", claim="Compare sources using observed yield.",
                     evidence_ref="receipt:two")
        a = build([one, two, copy.deepcopy(one)])
        b = build([two, one, copy.deepcopy(one)])
        self.assertEqual(a, b)
        self.assertEqual(len(a["records"]), 2)

    def test_stale_candidate_and_unrelated_do_not_promote(self):
        packet = build([
            record("fact:stale", observed_at_unix=NOW - 181,
                   evidence_state="LOCAL_OBSERVED"),
            record("fact:idea", evidence_state="CANDIDATE"),
            record("fact:career", kind="MECHANIC", query_key="career"),
        ])
        self.assertEqual(packet["status"], "RETRIEVAL_REQUIRED")
        self.assertEqual(packet["records"], [])
        self.assertEqual(packet["excluded"]["stale"], 1)
        self.assertEqual(packet["excluded"]["candidate"], 1)
        self.assertEqual(packet["excluded"]["irrelevant"], 1)

    def test_pinned_old_static_sources_survive_chats_but_old_revision_does_not(self):
        old = record(observed_at_unix=NOW - 100000)
        self.assertEqual(build([old])["status"], "EVIDENCE_SELECTED")
        changed = dict(old, source_revision="commit:stale")
        packet = build([changed])
        self.assertEqual(packet["status"], "RETRIEVAL_REQUIRED")
        self.assertEqual(packet["excluded"]["stale"], 1)

    def test_conflicting_sources_fail_closed(self):
        packet = build([
            record(claim="Use rotten produce."),
            record(claim="Do not use rotten produce.", evidence_ref="receipt:conflict"),
        ])
        self.assertEqual(packet["records"], [])
        self.assertEqual(packet["excluded"]["conflict"], 1)
        self.assertEqual(packet["status"], "RETRIEVAL_REQUIRED")

    def test_cannot_smuggle_other_household_patch_or_capture(self):
        for patch in (
            {"household_ref": "household:other"},
            {"game_build": "patch:other"},
            {"evidence_ref": ""},
        ):
            with self.subTest(patch=patch):
                with self.assertRaises(AgentContextError):
                    build([record(**patch)])
        with self.assertRaises(AgentContextError):
            build([record("fact:obs", kind="OBSERVATION", capture_ref="capture:other")],
                  intent="OBSERVATION")

    def test_no_unscoped_or_unbounded_context(self):
        with self.assertRaisesRegex(AgentContextError, "MANDATORY_CONTEXT_EXCEEDS_BUDGET"):
            build([record()], budget_chars=512,
                  )
        with self.assertRaisesRegex(AgentContextError, "CONTEXT_RECORD_COUNT_INVALID"):
            build([record("fact:%s" % i) for i in range(65)])
        with self.assertRaisesRegex(AgentContextError, "CONTEXT_BUDGET_INVALID"):
            build([], budget_chars=True)

    def test_portable_handoff_retains_rejected_and_correction(self):
        first = handoff()
        next_state = continue_handoff(first, {
            "next_gate": "VERIFY_FRESH_AFFORDANCE",
            "evidence_ref": "receipt:verified-transition",
            "corrections": ["Never invent ingredients."],
            "rejected_paths": ["Never repeat an unverified click."],
        })
        self.assertEqual(first["next_gate"], "REOBSERVE_CURRENT_QUEUE")
        self.assertEqual(next_state["next_gate"], "VERIFY_FRESH_AFFORDANCE")
        self.assertEqual(len(next_state["rejected_paths"]), 1)
        self.assertEqual(len(next_state["corrections"]), 2)
        self.assertEqual(next_state["parent_objective"], first["parent_objective"])
        self.assertEqual(json.loads(json.dumps(next_state)), next_state)

    def test_cannot_change_parent_or_gate_without_receipt(self):
        with self.assertRaisesRegex(AgentContextError, "PARENT_OR_SCOPE_MUTATION_DENIED"):
            continue_handoff(handoff(), {"parent_objective": "Maximize money."})
        with self.assertRaisesRegex(AgentContextError, "TRANSITION_EVIDENCE_REQUIRED"):
            continue_handoff(handoff(), {"next_gate": "RUN_ACTION"})

    def test_tool_descriptions_are_explicit_read_only(self):
        self.assertEqual(route_context("RELATION")["tool"], "query_relationships")
        self.assertEqual(route_context("AUTHORITY")["owner"],
                         "contracts/effect-authority.v1.json")
        for intent in ("GOAL", "MECHANIC", "RELATION", "OBSERVATION", "AUTHORITY"):
            self.assertFalse(route_context(intent)["execute_allowed"])
        with self.assertRaises(AgentContextError):
            route_context("issue_refund")

    def test_fault_diagnosis_bottom_up(self):
        def diagnose(available, retrieved, called=True, used=True):
            return diagnose_context_failure(
                required_fact_id="edge:warranty-owner",
                available_fact_ids=available, retrieved_fact_ids=retrieved,
                retrieval_called=called, decision_used_retrieval=used)
        self.assertEqual(diagnose([], [])["layer"], "DATA_LAYER")
        self.assertEqual(diagnose(["edge:warranty-owner"], [], False)["layer"],
                         "DECISION_LAYER")
        self.assertEqual(diagnose(["edge:warranty-owner"], [])["layer"],
                         "RETRIEVAL_LAYER")
        self.assertEqual(diagnose(["edge:warranty-owner"],
                                  ["edge:warranty-owner"], True, False)["layer"],
                         "DECISION_LAYER")
        self.assertEqual(diagnose(["edge:warranty-owner"],
                                  ["edge:warranty-owner"])["layer"], "SUPPORTED")
        self.assertFalse(diagnose(["edge:warranty-owner"],
                                  ["edge:warranty-owner"])["execute_allowed"])

    def test_host_sidecar_does_not_change_gameplay_decision(self):
        from betterinstincts.host_stack import evaluate_turn
        needs = dict(hunger=.85, bladder=.85, energy=.85,
                     hygiene=.85, fun=.85, social=.85)
        base = evaluate_turn(needs, capture_ref=CAPTURE)
        attached = evaluate_turn(
            needs, capture_ref=CAPTURE,
            agent_context_request={
                "handoff": handoff(), "records": [record()],
                "intent": "MECHANIC", "query_key": "fertilizer", "now": NOW,
            })
        self.assertEqual(attached["next_gate"], base["next_gate"])
        self.assertEqual(attached["fallback"], base["fallback"])
        self.assertEqual(attached["agent_context"]["status"], "EVIDENCE_SELECTED")
        self.assertFalse(attached["agent_context"]["execute_allowed"])
        denied = evaluate_turn(needs, capture_ref=CAPTURE,
                               agent_context_request={"invalid": True})
        self.assertEqual(denied["next_gate"], base["next_gate"])
        self.assertEqual(denied["agent_context"]["status"], "CONTEXT_REOBSERVE_REQUIRED")

    def test_insufficient_budget_never_silently_drops_parent(self):
        bloated = handoff(parent_objective="A" * 500,
                          corrections=["B" * 240 for _ in range(10)])
        with self.assertRaisesRegex(AgentContextError, "MANDATORY_CONTEXT_EXCEEDS_BUDGET"):
            compile_agent_context(bloated, [], intent="GOAL", query_key="fertilizer",
                                  capture_ref=CAPTURE, now=NOW, budget_chars=1000)


if __name__ == "__main__":
    unittest.main()
