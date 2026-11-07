# BetterInstincts ontology — v1, revision 2 semantic candidate

**Status:** candidate for semantic review; not a runtime authorization layer or proof of Sims gameplay. Machine graph: `contracts/ontology.v1.json`. Base inspection: `502f66efc0ee` on `main`, November 7, 2026.

## Why this exists
BetterInstincts already has canonical domain contracts and a glossary. This **integrates their meaning without replacing their owners**. It captures what exists in the game, what was actually observed, what is merely inferred, what the player wants, what an agent proposes, and what an independently gated action could do. A model recommendation never grants control.

## Product identity: natural instincts, open capabilities
**BetterInstincts makes The Sims 4 better at being The Sims.** Its near-term challenge remains all six needs, then self-sustaining income and bills, then skills and careers while preserving leisure, relationships, personality and player choices. Bootstrapping, save conventions, screen understanding and the host are *enablers* so the original needs challenge can be developed and certified reliably. They must not become a new prerequisite for speculative economic simulations.

**Game-native first, not exclusively.** Prefer tested native mechanics and community-compatible tuning. Creative economies, novel integration methods, richer worlds, alternate domain policies, and new programming methods are not forbidden by an ontology. Admit them only through the appropriate evidence, risk, authority and dependency gates; don't make them mandatory for hunger/needs certification. No Sim, household, world, goal or process is the exclusive center of the system.

**Concurrent evaluation is not parallel in-game action.** Existing `domain_cascade` polls needs, budget, career, skills and relationships, and existing `need_load_balance` independently handles needs-service health, detach and assumption windows. The semantic advisor consumes their bounded receipts and proposes which continuing goal deserves attention, without replacing either subsystem or granting SendInput authority. Shared time, object, queues, funds and player attention remain real constraints.

**Continuity of intent.** A burglary-like contingency may alter what deserves immediate attention, but the goal it interrupts must survive, together with the reason, observation, and condition for re-evaluation. The reported claim that calling police can outperform confrontation is a *patch/mod-specific hypothesis* until observed in the local game. No synthetic case becomes a universal Sims mechanic.

### P141 strategic discrimination
| Thesis | Repository evidence | Strongest counterargument | Decision |
| --- | --- | --- | --- |
| Replace the existing domain cascade with a universal simulator | Cross-domain ambitions are growing | Existing cascade and need-service balancer already own distinct, tested responsibilities; rewrite risks regression | **REJECT** |
| Add a lightweight, open-domain semantic and continuity seam on existing receipts | Ontology v1 lacked time, resource sharing, interruption and resumption; user repeatedly requests parallelism without losing intent | Offline coordination is not yet game evidence; keep it advisory and narrow | **SELECT** for a deterministic, bounded offline prototype |
| Orchestrate a new game economy as the next parent sprint | The product could eventually extend world-level systems | BI-002 hunger remains unproven and an economy adds no proven prerequisite for it | **DEFER**, keep extension path open |

P141 routed the selected seam to **P95**; P124 preserves clear ownership; P78 keeps vocabulary in `contracts/glossary.v1.json` and the ontology, not duplicate runtime specifications.

### P95 representative program seams
**Success, evaluate-only:** supplied observation → existing `domain_cascade.poll_cascade` receipts → `semantic_advisory.compose_semantic_turn` → rank multiple goal threads with resource contention and evidence-qualified urgent contingencies → issue one *advisory* selection and continuity receipt. A later, independent `screen_admit` step must decide whether any particular host action is authorized. The prototype stops before execution.

**Failure:** uncertain event evidence or expired window → no forced preemption; resource contention → defer but keep all goals; player presence or player-owned queue → yield; interrupted goal → retain resumption condition and re-observe before selecting; unknown game build or save provenance → no game action. The prototype must never certify gameplay.

**Architecture alternatives:** a monolithic new scheduler duplicates `domain_cascade`; a hardcoded Sims-domain enum blocks useful extensions; the selected read-only adapter is replaceable and can support Sim, household or world scopes without forcing future agents into a particular algorithm.


## Six semantic planes
1. **World:** build/version, saves, households, Sims, needs, locations, objects.
2. **Perception/knowledge:** UI scene, viewport, observations, observations' provenance, claims with uncertainties and falsifiers.
3. **Agency:** goals, player direction, opportunities, affordances, queued actions, agent proposals and per-step control permits.
4. **Learning:** observed outcomes and explicitly human-reviewed judgments support opt-in, advisory-only learning.
5. **Governance:** sessions, incidents, receipts and evidence ceilings link intentions to independently demonstrated outcomes.
6. **Orchestration:** situation, open-domain capabilities, continuing goal threads, activities, resource claims, time windows, contingencies, interruptions, resumption and game-native/extension paths.

## High-value disambiguations
- **Scene vs viewport:** a dark Copperdale Build/Buy catalog and a black Live viewport are not the same thing; classify chrome, HUD, mode and capture quality separately.
- **Opportunity vs feasible action:** an attractive Sim goal is not an available interaction until the correct lot, object, modal, game patch and player-ownership gates are observed.
- **Proposal vs authority:** successful offline scoring or learned action confidence cannot turn into SendInput permission.
- **Observation vs certification:** a semantic cue, operator statement, local screenshot and repeated live A/B test have different proof ceilings.
- **Lab save vs protected save:** a `BI_TMP_` name is only a hint, not a grant; the source-of-origin, bound run and explicit operator assent decide.
- **Judgment vs model:** operator-reviewed decisions can train a model; the model's output is advisory and can never change an allow/deny safety rule.

## Grounded authority
Keep original owning files authoritative. The glossary is `contracts/glossary.v1.json`; scenes and saves are `contracts/game-scenes.v1.json` and `contracts/save-policy.v1.json`; listener and presence are `contracts/host-listener.v1.json` and `contracts/player-presence.v1.json`; game incident is `contracts/viewport-black.v1.json`; learning is `contracts/judgment-learning.v1.json`. For product direction and proof, use `AGENTS.md`, `docs/DOCTRINE.md`, `docs/LEDGER.md` and `docs/VALIDATION.md`. This draft must not overwrite historical certified build data.

## Mandatory consultation *before* behavior prototypes
A behavior mutation starts with an **ontology consultation receipt**, before the first change to live-host calls or an offline policy prototype. Its fields are defined in `mutation_consultation.required`. For every proposed feature, the agent:

1. Resolves affected concept IDs and follows each `canonical_owner` source; names any semantic gap rather than creating an unreviewed synonym.
2. Evaluates implicated invariant IDs, particularly player direction, save provenance, scene evidence, patch exactness and learner non-authority.
3. Records game-build and evidence ceiling, negative tests, rollback path, and whether the proposal is merely offline or seeks guarded lab execution.
4. Emits one of `ADMIT_FOR_OFFLINE_PROTOTYPE`, `REQUIRE_ONTOLOGY_AMENDMENT`, `BLOCK_UNSAFE`, or `DEFER_FOR_GAME_EVIDENCE` with source references.
5. Repeats consultation on changed scope at review/merge. Old receipts do not cover different patch builds, actions or UI states.

Repository CI runs the Git-history consultation gate and `scripts/semantic_preflight.py` provides a local agent preflight. Neither Git history nor a CLI PASS proves human reading, host authorization, required GitHub status checks, or live Sims gameplay.

## Example: hunger recovery without deleting a player's intention
`SIM → NEED/NEED_STATE → OBSERVATION → CLAIM → GOAL → OPPORTUNITY → AFFORDANCE → ACTION_PROPOSAL` is the *reasoning* path. Before an actual guarded input, the host also needs `HOST_SESSION + GAME_BUILD + GAME_SCENE + SAVE_SLOT + PLAYER_PRESENCE → CONTROL_PERMIT`. After attempted input, a separate `OUTCOME` and `PROOF_RECEIPT` record what actually happened. Missing any execution gate means **abstain from execution**; it does not prevent read-only analysis.

## Next harness acceptance cases
- A feature proposal with missing affected-concept mapping fails *before* prototype mutation.
- A black screenshot with visible Build/Buy catalog does not classify as Live; absent independent cues means abstain.
- A save labeled `BI_TMP_` but missing provenance is protected.
- A learned high-confidence suggestion cannot produce a click permit.
- An offline evaluator PASS cannot change `GAME_CERTIFIED` or close BI-002.
- A change confined to documentation can evolve ontology without claiming gameplay proof; a behavior change without consultation cannot pass review.

**Acceptance posture:** semantic review first; then wire the consultation manifest, deterministic validator, negative regression tests, CI status check, and repository protection to enforce it. No main merge or live gameplay change is implied by this candidate.

## Local agent preflight before mutation, sampling or experiment
Before changing a behavioral file, run `python -m scripts.semantic_preflight --consultation contracts/consultations/BI-SEMANTIC-ORCHESTRATION-20261107.v1.json --operation repo_mutation --file betterinstincts/semantic_advisory.py` with the **actual** proposed paths and a consultation that predates their first mutation. For read-only offline experiments use `--operation offline_experiment`. For real game sampling or experimentation use `--operation game_sampling` or `game_experiment` and a *new* consultation scoped to `EXACT_GAME_BUILD:<version>` and `--exact-game-build <version>`; the current offline receipt must fail these operations. Independently observe player/presence/save/scene/control admission before any real UI input. P04 passes these requirements into the local game-capable agent rather than manufacturing live proof here.
