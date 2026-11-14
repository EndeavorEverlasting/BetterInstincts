# Living mechanics registry and household responsibility economy

**Operator outcome:** BetterInstincts must feel like living Sims, not a spreadsheet that forces one Sim to do every chore. Solo life puts happiness, six needs, social time and temperament above discretionary income, while households can specialize, share work, support dependents and increase sustainable collective yield **without sacrificing the individuals**.

**Source status:** offline host policy only. This is not an installed gameplay mod and does not turn a host-language planner into an EA-native gameplay hook. BI-002 hunger's live game certification remains ACTIVE.

## One canonical mechanics map, not forgotten feature descriptions

The machine-readable master is \`contracts/mechanics-registry.v1.json\`, validated by \`betterinstincts/mechanics_registry.py\` and inspected with:

\`\`\`sh
python -m scripts.mechanics_registry status
python -m unittest tests.test_mechanics_registry tests.test_household_economy -v
\`\`\`

The initial registry names **38 mechanics** across needs, emotional health, personal leisure, safety, education, skills, finance, bills, household work, gardening, recycling, robotics, navigation, relationships and life events. **31 entries point to existing source/test owners; seven are intentionally visible gaps**: household yield accounting, family care, pet care, relationship continuity, shared equipment claims, long-horizon replanning, and household fairness learning.

\`SOURCE_PRESENT\` means **code and tests exist**, not a playable tested EA effect. \`GAP\` means the owner is **not yet implemented**; it must not be hidden or falsely assigned to a generic service. All source rows have an explicit next proof gate; game certification remains zero until actual local Sims evidence. The registry's graph validates unique IDs, independent domain names, scopes, known predecessors, file-backed owners/test paths and cycle freedom. It cannot become a static closed enum: adding real mechanics through consulted repository changes is expected.

Each mechanic record captures: \`id\`, \`domain\`, \`scope\`, \`owner\`, \`evidence_state\`, \`tests\`, \`dependencies\`, \`next_gate\`, and non-executable proof/privacy flags. Conceptual dependencies do **not** impose new BI-002 prerequisites.

The registry is **not** a second need service, career engine, gardening planner, social-relationship store, or action-queue manager. Existing game-domain owners remain authoritative.

## The solo/household decision change

\`betterinstincts/household_economy.py\` evaluates one independent host-observed snapshot. It reuses the local opaque installation/save/household/roster identity contract in \`household_judgment.bind_household_scope\`, verifies original ordered member IDs/fingerprint and same-capture observations, and consumes **only** tasks already evidenced by existing domain modules.

**Solo well-being-first:** A single Sim has a high welfare reserve. Work is suppressed if fun/social are inadequate, needs are falling, temperament is irritable/unknown, or mood is distressed/unknown. Even when needs are merely passable, optional money-making is delayed until the higher solo welfare floor is satisfied. Essential tasks can be suggested only when safe. Leisure and relationships are meaningful outcomes, not failures to maximize earnings.

**Cooperative household:** With two or more independently verified members, optional observed responsibilities may be assigned one per eligible Sim per planning turn, preserving each member's own six needs and emotional reserve. Selection considers actual verified skill prerequisite, expressed likes/dislikes, prior observed workload (fairness), queue capacity, busy/player-owned state, and already-claimed shared resources. Urgent obligations precede routine maintenance; discretionary yield follows both. The policy does **not** hallucinate cash per hour, salaries, XP or Sim happiness measurements.

A conditional/unknown/strained actor is **not** treated as a free worker. A player-reserved actor is untouched. A task's \`eligible_member_keys\` requires observed availability; an absent Sim/unknown roster/unknown task owner causes deferral. A deferred goal remains in the report. No permanent "mother always cleans" assignment or compulsory fixed 4-Sim roster is built into the source.

An illustrative generic observation contains a \`scope\` from the existing private household binder, \`capture_ref\`, \`observed_roster_fingerprint\`, \`roster_verified\`, \`player_active=false\`, members with six normalized needs/mood/temperament/verified queue/skills/preferences/recent workload, and a list of observed available tasks with \`task_ref\`, \`mechanic_id\`, \`kind\`, \`priority\`, \`resource_ref\`, \`required_skill\`, \`min_skill_level\`, \`eligible_member_keys\`, \`player_owned\`, \`observed_available\` and the same \`capture_ref\`. Every task is a **candidate** rather than a click or EA interaction ID. No personally identifying save names or portraits belong in committed fixtures.

The optional \`household_economy\` host-listener input is passed to \`host_stack.evaluate_turn\` through its existing bounded, opt-in session. Default absence preserves prior behavior. The new report is \`host_stack["household_economy"]\`; positive proposals become late-priority \`COOPERATIVE_ALLOCATION_READY\` or \`SOLO_RESPONSIBILITY_READY\` gates **after** player safety, critical needs, school/career and the existing Servo/bill upkeep owner. Garden or household upkeep responsibilities should be sourced from their own trusted evaluators, not reinvented here.

## Make plans evolve from observed mechanics outcomes

The registry CLI supports read-only outcome reconciliation:

\`\`\`sh
python -m scripts.mechanics_registry reconcile --outcomes REVIEWED_OUTCOMES.json
\`\`\`

The JSON file must contain \`capture_ref\` and \`outcomes\` rows with an existing \`mechanic_id\`, \`outcome\` (SUCCEEDED/FAILED/UNAVAILABLE/UNKNOWN), unique \`proof_ref\`, matching \`capture_ref\`, and \`player_interrupted\` boolean. Failures from source-present mechanics become \`REPLAN_FROM_FAILURE_NOT_BLIND_RETRY\`; failures in GAP entries become \`MISSING_MECHANIC_OWNER\` and route to P95 owner discovery. Player-interrupted outcomes are never treated as evidence that a mechanic failed. Replay, stale capture and invented mechanic IDs are rejected. The output never automatically modifies the registry or Sims.

For household task assignment, source-qualified current \`failed_tasks\` likewise hold failed actions out of the candidate allocation pool until the relevant owner supplies a fresh alternative. Resource claims avoid double booking; deferred tasks retain their identities and reasons. The planning algorithm is **not** a forever loop or a background worker, and historical goals are not silently discarded. The future persistent cross-turn goal/outcome owner remains an explicitly visible mechanics gap, not something represented as implemented.

### Required iterative evolution

1. Observe a missing or failed mechanic with distinct evidence and classify by scope and actual domain.
2. Reconcile with the **existing owner** and the machine registry. If the mechanic is new, add a named GAP row and route the P95 owner discovery; never silently drop it.
3. Add the smallest verified native mechanic/tuning or bounded offline hypothesis under an ontology consultation, with owner, preconditions, test, rollback and game-build scope.
4. Run adversarial and compatibility regression tests. Measure actual success and wellbeing before updating \`evidence_state\` or gameplay proof claims. Real host effects require actual EA Sims runtime/rollback certification.
5. Re-evaluate the **household-level plan** after the new evidence: obligations, resources, voluntary labor, true game time, personal balance, income, skills, social priorities and player choices. Do not simply append a siloed feature and call the experience complete.

## P141 comparison / downstream gates

- **One all-purpose household mega-agent:** rejected; duplicates need load, domain cascade, Servo care and queue owner.
- **Static checklist of Sims mechanics:** rejected alone; gaps and later failures would still vanish without a machine-checkable proof/evolution system.
- **Profit-maximizing household with rigid job titles:** rejected; conflicts with single-Sim happiness and Sims personality.
- **Extensible coverage graph + small scoped cooperative dispatcher:** selected for source-proven, testable integration. It keeps genuine game-native action production for P08/EA.

MoonWake Sixth Gear resolves **P141 → P95 → P82 → P08 → P07 → P124**. Current GitHub work implements source-level P95/P82/P07/P124 evidence. The local MoonWake \`prompt_group_walk.py\` and Sims game host cannot be run through the GitHub connector; no fabricated agent dispatch or P08/game certification. Actual per-member productivity, skill causality, well-being changes, task completion and household yield must be measured in disposable real-game A/B runs. BI-002 hunger remains the primary active game certification gate.

## Immediate sleep-to-next-portrait rotation (deterministic, no model training)

The existing `household_economy` and `host_stack` path owns this source-only rule, registered as `household-portrait-attention-rotation` in the mechanics registry. A selected member independently observed as **ASLEEP**, **RECHARGING** or **AWAY** releases attention on that same verified capture, even when **zero tasks** are available. Find the next **AWAKE** non-player-reserved, queue-verified member in the original fingerprinted portrait roster, wrapping once. Do not choose a missing/unknown/sleeping member, do not self-select, and do not start an input loop when nobody qualifies. Skip the household's task/income allocation wellness floor for portrait **inspection**: low hunger or social needs are why an awake member may need attention.

After a fresh, independently verified selected-Sim needs review is complete, the caller may set `attention_review: {member_key, capture_ref, proof_ref, state: 'VERIFIED_COMPLETE'}` to advance once more. The proof must match the currently selected actor and capture. No review claim, timer or prior handoff receipt may cause repeated cycling. The selected source must be AWAKE and not player-reserved, with a verified queue. A new portrait always requires a **new capture** showing that Sim's identity and needs/queue before another action can be proposed.

The pure `portrait_handoff` result contains `from_member_key`, `to_member_key`, optional `task_ref` (null without eligible work), `reason`, `need_keys`, `new_capture_required: true`, `execute_allowed: false`. A running Sims portrait **click/switch** is **not implemented or game-certified** by this source-only rule; native exact-patch EA integration remains under issue #171. The host must separately prove effect admission and actual selected identity, rather than treating the proposal as completed gameplay. The existing need services, autonomy queues, human authority and save protections are unchanged. Preserve BI-002 as ACTIVE until its exact local 5+5 hunger trials and rollback.

Regression controls in `tests/test_household_economy.py` include empty chores, a critically hungry target, wraparound, actor reservation/unknown states, solo/all-asleep cases, no idle spin, stale/mismatched review and player presence. This is the first codified example of an agent-observed repeated routine becoming a repository-owned, tested, discoverable deterministic mechanic rather than recurring agent deliberation. Further promotions must follow the same source/ontology/native-route/test/proof gates; they are not automatically learned or installed.
