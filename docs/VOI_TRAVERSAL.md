# Purposeful traversal and value of information (VOI) — P141 → P01 → /fifth-gear

**Canonical owner:** `contracts/voi-traversal-harness.v1.json`. **Status:** offline policy and host-plan evaluation; not a Sims runtime walker, trained model, or live input permit. BI-002 hunger remains active.

## Parent outcome and P141 selection

A Sim must not be sent through a string of Walk/Go Here commands merely to discover a scene. Movement is **transit to a named domain action** (needs, career, skills, whims), not user value. P141 compared (1) expanding SLAM/EA geometry for every reroute (**deferred**: the spatial owner already exists and still cannot bind queue actions), (2) reducing general queue capacity (**rejected**: capacity is not purpose), and (3) adding a durable one-walk-to-goal guard over existing graph and host stack (**selected**: small, reversible, testable). Avoid a second route engine.

## Separation of mechanisms

| Mechanism | Owner | Physical Sim position | Admitted purpose |
| --- | --- | --- | --- |
| Passive viewport/EA read-only observation | scene/geometry existing owners | Unchanged | Cheap information first |
| Camera pan, zoom, active-Sim follow | `camera_traverse.py` + active Sim camera lock | **Unchanged** | Inspect named target under admitted lease; restore view |
| Sim walk | `household_navigation.py` route + `traversal_voi.py` queue guard | Changes only if EA actually executes it | Transit to a verified target action, never wandering to obtain pixels |
| Sims native object interaction | native EA object affordance via existing admitted host route | EA pathfinds as needed | Preferred final action; an extra Walk is usually redundant |

VOI chooses which **evidence** to gather with the least disturbance: passive observation first, camera reframe second only under its separate named lease, physical Walk last and only for a verified domain objective. Cost/benefit estimates remain *advice*; they never grant input, overwrite game physics, or count movement as meaningful progress. Any future ML must use reviewed, source-qualified outcomes and holdout, not synthetic success as live accuracy.

## One-walk invariant

For one actor and goal: **at most one outstanding host-origin WALK** and **at most one walk since the last independently observed domain action**. An emitted walk must point to a current, verified region and a concrete downstream action `{goal_id,domain,action_id,target_id}`; the same target and goal must carry through the route and queue evidence. Once the Walk appears in the queue or the checkpoint reports one already attempted, no additional Walk may be proposed. Arrival alone never resets the checkpoint; only a new, verified domain-action outcome can. The player’s queue, unknown origins, cross-save state, off-lot destinations, stale captures and absent checkpoint evidence yield/abstain, not cancel or repair by further walking. No individual camera movement consumes a Sim walk slot.

A reviewer must reject the following counterexample: `Walk(A), Walk(B), Walk(C), Eat(fridge)` despite ample queue capacity. A candidate `Interact(fridge)` with a verified object affordance is preferable to `Walk(fridge), Eat(fridge)`; Sims can pathfind natively. If deliberate transit is truly necessary, one bounded Walk followed by `Eat(fridge)` is the maximum until an observed outcome. These are **planning** constraints; a live game's UI cannot be inferred from synthetic records.

## P01 harness workflow

Entry: read `AGENTS.md`, `docs/AGENT_OPERATING_RULES.md`, `docs/ONTOLOGY.md`, `docs/DOCTRINE.md`, `docs/LEDGER.md`, this page and the machine contract. Use `contracts/consultations/BI-VOI-PURPOSEFUL-TRAVERSAL-20261112.v1.json` for semantic preflight. Path contract stays `contracts/workstation-paths.v1.json` / `bootstrap.py`; no new clones or host directories.

1. Inspect the actor/goal/capture/queue/checkpoint and direct object affordance. Do not convert an action label into an agent-origin claim.
2. Use existing `plan_household_navigation` only for verified on-lot Sim passages. Its full route is not permission to enqueue every hop.
3. Call the pure VOI evaluator. It returns a proposed **next action** and a separate camera recommendation, no effect permission. Existing presence/scene/save/target/host-effect leases remain independent.
4. After one host Walk, **reobserve the actual queue and goal outcome**. Never issue a second Walk to fix a missing outcome; reconcile the remaining intent. If the target affordance is unknown, use capture-first and named camera planning.
5. Validate offline with `python -m scripts.check_voi_traversal_harness`, `python -m unittest tests.test_traversal_voi -v`, `python -m scripts.check_ontology`, and `python -m scripts.check_native_gameplay_authority --json`. The main CI test discovery also exercises `tests/test_traversal_voi.py`.
6. For P08, only an operator-authorized local Sims host on an exact version and disposable save can certify camera recovery, queue observation, native interaction and the no-walk-spam effect. Record genuine queue before/after captures, player takeover, one Walk-to-domain action and zero second Walk attempts. CI/local synthetic tests are not game certification.

**Artifacts:** ontology consultation, policy contract, native-route decision, pure evaluator, host composition, offline tests, this procedure, GitHub PR/CI receipts. **Failure:** return a named denied gate; never invent control permits or claim Live Mode certification. **Handoff:** record CHANGED | PROVED | NEXT separately for test, PR, merge, game and workstation state.

## Extension seam

A future trained VOI estimator may emit `expected_information_gain`, `risk` and `evidence_version` for passive, camera and physical movement; the deterministic invariant remains the immutable admission floor. Retain one owner for motion state and deduplicated goal outcomes; never learn from unreviewed camera motion or reward walking without completing the career/skill/need/whim action.
