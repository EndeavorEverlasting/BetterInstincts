# Agent context windows and cross-chat continuity

**Owner:** \`betterinstincts/agent_context.py\`; machine contract: \`contracts/agent-context.v1.json\`. **State:** optional offline policy, not a provider memory connection, Sims runtime hook, or tool runner.

## The architecture

An agent is a bounded decision loop consuming a **portable context packet**, not an owner of its own permanent truth. Different chats, LLMs or local agents receive the same deterministic projection of explicitly supplied inputs. The packet carries a canonical household/goal scope, operator objective and corrections, rejected paths, blockers, current next gate, data provenance, and the read-only retrieval owner best suited to the question. Nothing is written to a user profile by this module.

Canonical data layers remain separate: \`task_continuity\` and \`selected_sim_continuity\` own observed goals and queues; \`mechanics_registry\` and \`object_action_catalog\` own mechanics and reviewed affordances; \`ontology\` / \`semantic_spatial_map\` represent relationships; \`need_signal_fusion\` and \`moodlets\` own capture-bound observations; \`effect_authority\` / \`control_handoff\` remain the sole authority checks. This module never grants a permit; it only points to owners.

## Deterministic call flow

1. **Recover** a caller-supplied, schema-v1 handoff with immutable parent objective, household, active goal, source revision and next gate. Operator corrections and rejected paths are retained, not silently summarized away. A gate transition requires a separate evidence reference.
2. **Route** an intent (GOAL, MECHANIC, RELATION, OBSERVATION or AUTHORITY) to a documented, read-only source owner. This is a *description of the next permitted lookup*, not tool invocation. Agents may choose the appropriate retrieval path instead of reflexively querying a knowledge graph on every turn.
3. **Validate** records against same household and exact game build, explicit source and evidence identity, and observation freshness (180 seconds maximum). Goal and sensor observations require the same capture. Candidates, stale claims and conflicting duplicate facts cannot masquerade as reliable evidence.
4. **Compose** only the relevant fresh records within a declared character budget. Always prioritize authority/goal records; keep mandatory operator decisions. A budget too small to hold the mandatory envelope is an explicit failure, not truncated safety.
5. **Reason** over the packet in existing source-owned evaluators. **Act** only through independent player-first, save/scene/queue/lot, exact-build and per-effect admission. Use \`continue_handoff\` with transition proof to carry state to the next chat or agent.

This is **portable serialization**, not automatic persistence. The caller must deliberately transport a sanitized handoff and any authorized source records; no implicit profile crawling, shared memory daemon, token-count claims, or global game logging.

## Example API

\`\`\`python
from betterinstincts.agent_context import compile_agent_context, route_context

owner = route_context("MECHANIC")  # suggestion only; does not call a tool
packet = compile_agent_context(
    handoff, source_records,
    intent="MECHANIC", query_key="fertilizer",
    capture_ref="capture:current", now=current_unix,
    budget_chars=4096,
)
# packet["execute_allowed"] is always False.
# Missing evidence -> RETRIEVAL_REQUIRED, never an invented answer.
\`\`\`

Host users can optionally supply \`agent_context_request\` to \`host_stack.evaluate_turn\`. This attaches \`agent_context\` to the existing result without changing the earlier next_gate/fallback/gameplay decision. Invalid packets become an explicit denied sidecar report.

## Debug the right layer first

\`diagnose_context_failure\` tests whether the needed relationship/fact was present in canonical data, then whether retrieval obtained it, then whether the decision used it. Missing data calls for data repair; present-but-not-retrieved calls for search/graph-depth repair; retrieved-but-ignored calls for control-loop repair. Adding extra reasoning steps on an incomplete graph cannot fix missing source edges.

## Verification and release

Offline regression: \`python -m unittest tests.test_agent_context -v\`, and existing host integration tests. Required source governance: \`python scripts/semantic_preflight.py\`, \`python -m scripts.check_native_gameplay_authority --base-ref <main_sha>\`, then CI/readback. These are source tests only. Native Sims automation still requires issue #171, actual EA tuning/hook evidence, exact game build, disposable test save, repeated vanilla/modified trials, rollback and player-first acceptance. **BI-002 remains active.**

Sixth Gear scope: P141 rejected universal model memory and a rival decision engine; P95 introduced the context/data/retrieval/decision boundaries; P82 uses replay, conflicts, missing-edge, stale and truncation tests; P08 requires unavailable local game proof; P07/P124 integrate through existing host sidecar and canonical documentation, not an autonomous runner claim.
