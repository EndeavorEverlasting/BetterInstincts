# Living mechanics registry and household responsibility economy

**Operator outcome:** BetterInstincts must feel like living Sims, not a spreadsheet that forces one Sim to do every chore. Solo life puts happiness, six needs, social time and temperament above discretionary income, while households can specialize, share work, support dependents and increase sustainable collective yield **without sacrificing the individuals**.

**Source status:** offline host policy only. This is not an installed gameplay mod and does not turn a host-language planner into an EA-native gameplay hook. BI-002 hunger's live game certification remains ACTIVE.

## One canonical mechanics map, not forgotten feature descriptions

The machine-readable master is \`contracts/mechanics-registry.v1.json\`, validated by \`betterinstincts/mechanics_registry.py\` and inspected with:

\`\`\`sh
python -m scripts.mechanics_registry status
python -m unittest tests.test_mechanics_registry tests.test_household_economy -v
\`\`\`

The initial registry names **39 mechanics** across needs, emotional health, personal leisure, safety, education, skills, finance, bills, household work, gardening, recycling, robotics, navigation, relationships and life events. **32 entries point to existing source/test owners; seven are intentionally visible gaps**: household yield accounting, family care, pet care, relationship continuity, shared equipment claims, long-horizon replanning, and household fairness learning.

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

## Work shifts reuse the same portrait rotation

The exact selected household member can report `activity: AT_WORK` and an independently verified same-capture `work_shift` observation. **AT_WORK means unavailable for at-home tasks**, like sleep and absence, but unlike those states it first invokes `career_service.evaluate_work_shift_tone`: an eligible rabbit-hole worker may benefit from Work Hard when promotion requirements and daily obligations are met, performance is still below target, the option is observed, and welfare plus player-ownership rules allow it.

While `work_tone.gate == WORK_HARD_ADMISSION_REQUIRED`, **do not** rotate yet or claim that a button was pressed. The existing host `next_gate` is `CAREER_WORK_HARD_ADMISSION_REQUIRED` with `execute_allowed: false`. After the separate native/game-admitted effect produces a fresh observable Work Hard tone, `work_tone.handoff_ready` becomes true; the same fixed-roster next-awake portrait policy supplies `AWAKE_HOUSEHOLD_HANDOFF_READY`, requiring a new target capture and needs/queue assessment. If Work Hard is unwarranted, unavailable or player-protected, the policy preserves the tone and still rotates to the next verified awake member without chores. **Active careers and unknown career modes retain the selected Sim** because their activities cannot be abandoned automatically.

Existing school homework, shared-resources, critical needs, player inputs, queues and protected saves retain their owners. `career-work-hard-tone` is now a distinct source-backed mechanistic coverage row, not an installed playable Sims mod. Exact-game EA-native integration and rollback require a separate P08 gate under issue #171.

## Shared household income

The `income` catalog in [the household economy contract](../contracts/household-economy.v1.json)
owns recognized activities and their stages. Programming includes plugins,
freelance work, apps and games. Art, robotics, and woodworking include selling
and independently observing settlement. Small business is a discovery lane.
Home or venue assignment, business activities, operating hours, staff and
customers, and closeout receipts each need their own observation and action
owners. [EA small-business help](https://help.ea.com/en/articles/the-sims/the-sims-4/how-to-set-up-a-small-business/)

A host observation may supply `household_economy.income`. The packet includes
the current `capture_ref`, roster `scope_id`, `save_ref`, exact `game_build`,
`household_funds`, `funds_proof_ref`, and verified `pending_effect` state.
The queue projection lists each member's existing rows in visible order. Each
row binds the observed label, action ID, origin, unpaid upfront cost and any
task or resource already claimed. The household reserve is shared across all
members. Pending costs are debited from spendable surplus before comparing a
new offer. Forecast receipts cannot create cash or earned-income credit.

Per-member windows bind the current capture, known protected-work state,
safe available Sim minutes, time already committed to the queue, and slots
reserved for needs or commitments. When eligible work fits, the allocator
prefers filling the selected portrait, then proposes switching to the best
remaining eligible portrait. One step is returned per capture. Re-observe
after a portrait change, and reconcile independent queue readback before
proposing another action. Active player work, career and needs priority,
uncertain queues, booked stations, exhausted time and missing evidence all
hold or remove candidates. The queue uses the existing conservative capacity
of two while multitasking and six otherwise.

Each offer binds a member, action, task, activity, shared target, enabled
affordance proof, and conservative time bound. Generic offers need separate
settlement evidence, realized net after sourcing costs, measured duration
and current upfront cash. Robotics offers use the existing receipt evaluator
and its positive net result for the same Sim and native action. A catalog
entry alone supplies neither availability nor price, net yield or permission.

These are host-stack proposals. [Issue #171](https://github.com/EndeavorEverlasting/BetterInstincts/issues/171)
owns exact-build sensor binding, native dispatch, independent outcomes
and rollback.

## Shared native portrait handoff

`betterinstincts.portrait_handoff` chooses one recipient from the observed
active household. `InstalledPlayerRuntime` owns the in-flight switch, uses
the existing player-idle and exact-build gates, and admits it only when
the active domain has released the current portrait. Portrait selection can
run while Live Mode is paused, including between computer purchase batches.
Each workflow keeps its own queue, menu, inventory, needs or skill proof.

| Purpose | When attention moves |
| --- | --- |
| `UPGRADE_PARTS` | Stay with the current Sim until the existing purchase owner has no remaining work for that Sim. Reconcile the purchase against that Sim's inventory and household funds before moving. Advance in observed portrait order to the next eligible Sim. |
| `SKILL` | Choose the first pending Sim in roster order for the current skill. Wait on an earlier unverified Sim. Advance the skill only after its eligible members meet the owner-defined target. |
| `NEEDS` | Keep the current Sim while their actionable needs are unaddressed. When covered by verified care, a matching queued action or sufficient need levels, move to an eligible Sim with uncovered needs. Rank by observed urgency and break ties in circular household order. |
| `TARGET` | Any owner can request a specific eligible member by native Sim ID. Existing income handoffs can use this purpose once their actor IDs are resolved in the same roster. |

The native adapter implements three methods.

1. `read_portrait_handoff(frame)` returns `None` or a current observation.
   Include `capture`, `household`, `selected`, `save`, the ordered `roster`,
   the current work unit's stable `goal`, its `purpose`, `safe_to_leave`,
   and a `members` map keyed by every observed native Sim ID. Use `READY`
   for eligible pending work, `COVERED` for verified complete or already
   addressed work, `UNAVAILABLE` for observed ineligibility this pass, and
   `WAITING` for evidence or progress still pending. Only assert
   `safe_to_leave` when prior effects and actor-specific UI are settled.
   Needs include an `urgency` map for all ready members, from 1 to 3.
   Explicit targets include `target`.
2. `submit_portrait_if_current(attempt, frame)` rechecks the original
   actor, exact target, run, admitted save, ordered roster, player-input
   generation and current domain readiness atomically with one EA selection.
   Use native Sim identity throughout. The runtime requires two independent
   admission frames and records the attempt before invoking the adapter.
3. `read_portrait_outcome(attempt, frame)` reads the native acknowledgement
   and returns `status` (`APPLIED` or `NO_EFFECT`), `request_capture`,
   `capture`, `save`, `roster` and `target`. The callback's independent
   selected-Sim observation must agree. A later frame drives the next
   domain decision. An unresolved attempt holds further dispatch and the
   same goal and recipient cannot be submitted twice in that save and run.

On an authorized Windows lab session, inspect the installed EA selector,
its acknowledgement and the selected-Sim signal for the exact patch.
Build via `py -3 -m scripts.native_ecology_bundle build --help` using the
existing player-runtime option and `--installed-portrait-handoff` with
`installed_portrait_handoff_binding_ref` in the local hook proof. Verify
one paused household purchase handoff with inventory and funds readback,
one serial skill transition with level readback, and one needs handoff
where a covered Sim is skipped and the recipient's need enters their own
queue. Include a player takeover, no duplicate submission and package
rollback. The adapter binding and these game observations belong to
[#171](https://github.com/EndeavorEverlasting/BetterInstincts/issues/171).
