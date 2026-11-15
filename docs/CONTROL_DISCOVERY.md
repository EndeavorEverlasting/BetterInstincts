## Native responder recovery (PS-0251)

Start with the [repository skill](../.agents/skills/native-responder-recovery/SKILL.md). Use the existing control-discovery journal and the evidence checkout that produced it. Author source in the canonical development checkout or an isolated worktree. The game effect runs in the installed Sims build under the user-selected Mods root. A GitHub merge, a file installed under Mods, and a game-native effect are distinct.

The Video Gaming callback `AdventureMoment._on_dialog_response` was seen after a historical player-side response. The repeat-offer Yes was agent-assisted, and its current native acknowledgement and trait/buff readback were unavailable. Reuse both sets of evidence with their original attribution. PR #275 owns the provisional host response port. The open game-side work is to bind and verify the real EA submit primitive and auto-activation in the installed game, then capture the first BetterInstincts-owned outcome on a future naturally occurring offer. BI-002 and the same-household LabLab successor preflight continue independently of this native proof.

## 2026-11-14 — Passive-listener identity and every-discovery source backlog

**Operator correction, implemented in this isolated follow-on:** human activity pauses **behavior**, not the active computer-use session or its reviewed passive listener. `AgentControlRunner.observe_while_paused` attaches an already-approved no-focus/no-input observation callback only after a real `WAITING_FOR_USER` pause. Every `CooperativeScreenQueue` passive result now carries `effect_class=PASSIVE_OBSERVATION` and its **own work_id**, whether it succeeded, waited, failed validation or required reconciliation. `AgentControlRunner.pulse` reports `LISTENER_OBSERVATION_*` independently; the pending gameplay action remains queued and cannot be marked COMPLETE, produce a post-action result, or bypass the revalidated 15-second idle gate because the listener returned success. `wait_and_pulse` keeps observing the active session while awaiting the actual action, within its explicit bounded poll count.

**Collect without context overload:** whenever an adopted calibrated agent/sensor discovers a menu, object action, queue event, sensor recovery, interruption or negative result during controlled use, call `runner.record_semantic_discovery(work_id, discovery_kind, fact_ref, source_ref, evidence_ref)`. This writes strict tokenized `DISCOVERY` evidence to the same opt-in listener journal; no raw mouse/keyboard screenshots, audio or external-app data. At most six distinct discoveries attach to one prepared action. `control_discovery.codification_work_items(ledger, offset, limit)` exposes up to eight small source-and-test obligations per page, each carrying the action, before/after provenance, all observed semantic discoveries, interruption, outcome and next gate. `compact_handoff` includes only the first four work items, with a cursor for the next page. The full bounded journal remains authoritative.

**No false codification completion:** a `CODIFICATION_RECEIPT` reports source files, tests, commit and review **as submitted claims**. `coverage.source_verification_pending_total` remains nonzero until independently checked on GitHub/main. Neither a recorded click, a passive observation, a receipt, an open PR, nor local unit tests proves live Sims behavior. The current test cases explicitly distinguish passive observation success/failure from the pending agent action and preserve unverified source obligations. Actual installed-game input and native integration remain separate, operator-authorized P08 work; BI-002 stays active.

# Agent control → listener → codify every discovery

**Parent correction:** BetterInstincts agents **may take control of the Sims screen** when native/repository logic cannot finish the task. That is a legitimate **last resort**, not a prohibited capability. Computer use is the discovery bridge; the repository must progressively absorb its repeated decisions, affordances, failures and verified effects.

**Owners:** \`betterinstincts/agent_control_runner.py\` (adopted computer-use adapter), \`betterinstincts/workflow_interop.py\` (idle/pause/exclusive input), \`betterinstincts/host_listener.py\` (explicitly active journal), \`betterinstincts/control_discovery.py\` (bounded semantic events and codification coverage), \`betterinstincts/object_action_catalog.py\` (existing class-action outcome learning), \`betterinstincts/agent_context.py\` (cross-chat context). Machine authority: \`contracts/control-discovery.v1.json\`; prior owner is not superseded.

## How it behaves

1. **Deterministic first:** Consult current goal, known native mechanics and existing policy. If verified logic already covers the work, reuse it; do not take over just to re-discover a click. Otherwise document why the native route is missing/unproven or this is a deliberately authorized disposable lab diagnostic.
2. **Explicit active listener:** An operator-approved listener session must already be ACTIVE; \`open_control_discovery\` attaches a semantic journal without turning on an unapproved global service. It does not discover the user's game or scan saves.
3. **Agent computer use is allowed:** Before **every atomic** game/UI effect, \`AgentControlRunner.prepare_effect\` records its intent, prior capture and separate authority reference, *then* uses the existing \`CooperativeScreenQueue.enqueue_effect\`. The queue owns the real idle, owner, game/scene/save/queue checks and per-effect checkpoint. The action callback is one bounded effect, not an uncontrolled macro.
4. **Human activity = pause behavior, not kill computer use:** When the user moves, types, plays, speaks through an explicitly surfaced busy signal or uses another app, the action queue returns \`WAITING_FOR_USER\`. Its intent and existing listener session survive. Trusted passive listener observation can continue **only** if reviewed as read-only and non-intrusive. No automatic screenshot/OS telemetry or background daemon is authorized.
5. **Resume from trusted idle:** In the still-active session, \`pulse\` or bounded \`wait_and_pulse\` checks for inactivity. Two fresh idle probes, exact scene/save/target/queue validation and exclusive screen access recur before the **next** effect. A partially completed action is quarantined as \`NEEDS_RECONCILIATION\` and never blindly replayed.
6. **Capture the entire controlled opportunity as semantics:** Every prepared step remains in \`dist/host-listener/<session_id>/control-discovery.json\`, with queue state, independent post-action capture, result and actor-interruption classification. Store concise opaque tokens, not screenshots, names, keyboard logs or entire chat history. Review the existing \`object_action_catalog\` observation route for menu→selection→outcome when available; do not claim an uncalibrated observer captured events automatically.
7. **Turn each step into source and tests:** \`control_discovery.coverage\` surfaces every unaddressed step, including unknown/failed outcomes. The task is not closed merely because computer use worked. Inspect the current code owner, implement a stable deterministic rule or native EA integration when supported, add success/negative/regression tests, then record a linked \`CODIFICATION_RECEIPT\`. This receipt is a *claim of submitted code*, not an independently verified merge or game result. Confirm on GitHub and later in a safe disposable Sims session.

The agent's model context window only receives \`read_control_discovery(session_id)\` / \`compact_handoff\`: counts and the first eight open work items, plus the canonical goal and next action; further records remain available on demand in the bounded local journal. This prevents long computer-use sessions from crowding out the immediate control problem.

## Minimal adapter call stack

\`\`\`python
# Existing ACTIVE listener and explicitly opted-in local disposable session:
from betterinstincts.host_listener import open_control_discovery, read_control_discovery
from betterinstincts.agent_control_runner import AgentControlRunner

open_control_discovery(
    session_id, household_ref=household_ref, goal_id=goal_id,
    game_patch=installed_exact_patch,
    fallback_reason="EXISTING_RULE_FAILED", explicit_opt_in=True,
)
runner = AgentControlRunner(session_id, cooperative_queue)
runner.prepare_effect(
    work_id="work:plant2", action_ref="fertilize:select",
    object_class_ref="object_class:planter",
    before_capture_ref="capture:before",
    authority_ref="admission:fresh", validate=fresh_game_state,
    effect=one_atomic_authorized_game_action,
)
result = await runner.wait_and_pulse(max_checks=120)
# WAITING_FOR_USER means paused, with the same listener and job intact.
# On COMPLETED, obtain a real, independent post-action observation.
runner.record_observed_outcome(
    outcome="HELPFUL", after_capture_ref="capture:after",
    outcome_ref="outcome:verified-plant", player_interrupted=False,
)
open_work = read_control_discovery(session_id)
# Promote each independently verified discovery to source + regression tests.
\`\`\`

Above is an API example for a separately connected authorized local adapter, **not a claim that the host or in-game action ran**. Host observations must be supplied by a calibrated source. Do not infer a generic object action utility from one click; \`object_action_catalog\` requires its own reviewed, replay-unique evidence thresholds.

## Uncompromising closeout accounting

Every attempted screen action is counted even when it fails. \`coverage().unresolved_total\` reports candidates with missing outcome/review/code; \`receipt_submitted\` tracks code-claim receipts still requiring independent source/mainline verification. The continuation question is **what remains unencoded**, not *did the agent manage to click?*

Developer checks: \`python -m unittest tests.test_control_discovery -v\` and \`python -m unittest tests.test_agent_context -v\`; then repository preflight, source classification, CI, and independent provider readback. **Real Sims native behavior, operator idle-sensor integration and local game certification remain host-only proof gates.** No guessed UI coordinates or hidden desktop control.

## 2026-11-14 — Do not end the agent mission at a child checkpoint

Following the control-use correction, `AgentControlRunner.assess_parent_turn_boundary` now reads the active listener and outstanding effect identity before recommending a turn boundary. Player takeover keeps the listener and prepared effect; a passive observation or action QUEUE_STATUS `COMPLETED` does not produce a verified game outcome, a source-backed deterministic rule, or parent completion. Pending real game effects receive a distinct reconciliation gate. An approved source-only task may advance while gameplay input waits. See `docs/AGENT_CONTEXT.md`, `contracts/agent-context.v1.json#parent_turn_boundary` and `tests/test_control_discovery.py`. This is **advisory**, not a deployed Codex stop hook, an EA native gameplay mod or an installed background runner.
