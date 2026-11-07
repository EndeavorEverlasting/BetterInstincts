# BetterInstincts ontology — v1 candidate

**Status:** candidate for semantic review; not a runtime authorization layer or proof of Sims gameplay. Machine graph: `contracts/ontology.v1.json`. Base inspection: `502f66efc0ee` on `main`, November 7, 2026.

## Why this exists
BetterInstincts already has canonical domain contracts and a glossary. This **integrates their meaning without replacing their owners**. It captures what exists in the game, what was actually observed, what is merely inferred, what the player wants, what an agent proposes, and what an independently gated action could do. A model recommendation never grants control.

## Five semantic planes
1. **World:** build/version, saves, households, Sims, needs, locations, objects.
2. **Perception/knowledge:** UI scene, viewport, observations, observations' provenance, claims with uncertainties and falsifiers.
3. **Agency:** goals, player direction, opportunities, affordances, queued actions, agent proposals and per-step control permits.
4. **Learning:** observed outcomes and explicitly human-reviewed judgments support opt-in, advisory-only learning.
5. **Governance:** sessions, incidents, receipts and evidence ceilings link intentions to independently demonstrated outcomes.

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

This is **the consultation specification**, not a claim that `AGENTS.md`, Cursor rules, CI or GitHub branch protection currently enforces it. That implementation is the next separate gate.

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
