"""Cross-chat context, evidence and no-effect regression fixtures."""
import copy
import json
import unittest

from betterinstincts.agent_context import (
    SCHEMA, AgentContextError, compile_agent_context, continue_handoff,
    diagnose_context_failure, route_context,
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
