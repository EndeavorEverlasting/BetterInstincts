# BetterInstincts ontology — v1, revision 5 (earlier revision history retained)

**Status:** offline semantic contract and CI validators merged in [PR #57](https://github.com/EndeavorEverlasting/BetterInstincts/pull/57); canonical P04 handoff merged in [PR #58](https://github.com/EndeavorEverlasting/BetterInstincts/pull/58). Machine graph: `contracts/ontology.v1.json`. Its machine `state` remains a **candidate for runtime adoption**; it is neither game-input authority nor proof of Sims gameplay. Historical inspection base: `502f66efc0ee`, November 7, 2026.

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

Repository CI runs the Git-history consultation gate, and `scripts/semantic_preflight.py` provides a local agent preflight. A consultation whose decision is `BLOCK_UNSAFE`, `DEFER_FOR_GAME_EVIDENCE`, or `REQUIRE_ONTOLOGY_AMENDMENT` **cannot pass the preflight**, including sampling without changed-file paths. Neither Git history nor a CLI PASS proves human reading, host authorization, configured branch protection, or live Sims gameplay.

## Example: hunger recovery without deleting a player's intention
`SIM → NEED/NEED_STATE → OBSERVATION → CLAIM → GOAL → OPPORTUNITY → AFFORDANCE → ACTION_PROPOSAL` is the *reasoning* path. Before an actual guarded input, the host also needs `HOST_SESSION + GAME_BUILD + GAME_SCENE + SAVE_SLOT + PLAYER_PRESENCE → CONTROL_PERMIT`. After attempted input, a separate `OUTCOME` and `PROOF_RECEIPT` record what actually happened. Missing any execution gate means **abstain from execution**; it does not prevent read-only analysis.

## Next harness acceptance cases
- A feature proposal with missing affected-concept mapping fails *before* prototype mutation.
- A black screenshot with visible Build/Buy catalog does not classify as Live; absent independent cues means abstain.
- A save labeled `BI_TMP_` but missing provenance is protected.
- A learned high-confidence suggestion cannot produce a click permit.
- An offline evaluator PASS cannot change `GAME_CERTIFIED` or close BI-002.
- A change confined to documentation can evolve ontology without claiming gameplay proof; a behavior change without consultation cannot pass review.

**Acceptance posture:** consultation manifests, Git-history validator, negative regression tests, local preflight and PR CI are **implemented and merged**. Repository branch-protection enforcement is **not independently verified**; the local game host is **not certified**. For the P83 correction, a suspended goal must carry explicit revalidation tied to the *current* cascade capture before it can be selected again. A contingency from an older capture cannot preempt a new turn. Neither mechanism authorizes input.

## Local agent preflight before mutation, sampling or experiment
Before changing a behavioral file, run `python -m scripts.semantic_preflight --consultation contracts/consultations/BI-SEMANTIC-ORCHESTRATION-20261107.v1.json --operation repo_mutation --file betterinstincts/semantic_advisory.py` with the **actual** proposed paths and a consultation that predates their first mutation. For read-only offline experiments use `--operation offline_experiment`. For real game sampling or experimentation use `--operation game_sampling` or `game_experiment` and a *new* consultation scoped to `EXACT_GAME_BUILD:<version>` and `--exact-game-build <version>`; the current offline receipt must fail these operations. Independently observe player/presence/save/scene/control admission before any real UI input. P04 passes these requirements into the local game-capable agent rather than manufacturing live proof here.

## 2026-11-10 — revision 5: ZOOM_MODE ≠ ZOOM_CONTROL + OBJECT_PICK_IDENTIFY

Operator: zoom-in is **Z** / scroll (out **X**), never right-click; world-object pick must traverse → zoom in → capture → identify. Semantic viewpoint extension revision 5 appends `zoom_controls` and `object_pick_identify` without replacing the zoom ladder. Owners: `ui-chrome` LIVE hotkeys + `camera-traverse` `#zoom_controls` / `#object_pick_identify`. Consultation `BI-OBJECT-PICK-ZOOM-HOTKEYS-20261110`.

## 2026-11-09 — revision 4: zoom ladder + overlay clear after metadata

Semantic viewpoint extension revision 4 binds the agent zoom ladder on top of revision 3: default `RIGHT_CLICK_VIEW` (0.85 of max close / 15% pullback + portrait follow), `ENVIRONMENT_NAV` at 0.50 for named planning only, `TRAVEL_AFAR` at 0.0 only for verified long-distance travel, and zoomed-in overlay clear after `metadata_tracked` + `accounted_by=BETTER_INSTINCTS`. Canonical owner remains `contracts/camera-traverse.v1.json` with HUD clear via `scene_ui_semantics`. Consultation: `BI-CAMERA-ZOOM-LADDER-OVERLAY-CLEAR-20261109`.

## 2026-11-09 — revision 3: viewpoints, portraits, panels and event continuity

The ontology now distinguishes `GAME_SCENE` (Live/Buy/Build/menu), `VIEW_SCENE` (the camera's observed position/sector around a world and lot), `HUD_PANEL` (active bottom-right module), and `EVENT_OVERLAY` (career/random/decision interruption). An incorrectly encountered top-down street is a meaningful `VIEW_SCENE`, not a new gameplay mode, a target, or permission for further panning. `SCENE_MEMORY` stores bounded deduplicated observations and an explicit operator-review status for later discovery; review does **not** automatically supply route coordinates or a navigation permit.

`SIM_PORTRAIT` is the selected active household Sim's exact attested portrait in the lower-left portrait row. A native right-click on that portrait requests `CAMERA_FOLLOW`; native `Enter` centers once and native `Shift+Enter` centers the lot. `CAMERA_FOLLOW` is a continuing state requiring game observation, **not** merely a sent key or injected mouse click. Goal-scoped map exploration remains a short-lived exception; when it ends, the preferred admitted restoration is right-clicking the active Sim's verified portrait.

`EVENT_OVERLAY` interrupts `ACTION_QUEUE` and `GOAL_THREAD` without erasing them. The HUD decision microsystem first obtains two-source overlay evidence, independently confirmed option identities and hitboxes, and a unique positive recommendation from the existing decision scorer, or yields for review. The player/host session must explicitly authorize any native choice click. A cleared overlay requires fresh re-observation; queued gameplay actions revalidate individually before resumption. Bottom-right tabs include aspirations, career, skills, relationships, personal inventory, needs and Simology; a tab switch changes semantic target context, not permission to reuse old coordinates.

New machine invariants `BI-ONT-019..022` protect active-portrait identity, bounded traversal/restore, overlay queue continuity and evidence/review before viewpoint reuse. Canonical owners: `contracts/portrait-follow.v1.json`, `contracts/ui-microsystems.v1.json`, `contracts/scenery-memory.v1.json`. Historical ontology consultations remain pinned to their original Git blob revisions and must not be silently reinterpreted as revision 3. These are offline executable semantics until local Windows Sims observations establish real camera-follow and UI effects.

## Revision 4: P00/P01 user interaction sovereignty

P00 Governance Doctrine Installer extends PLAYER_FIRST to any user-chosen interaction shape: game, mod UI, mouse, keyboard, voice/assistive work or another application. P01 Harness Infrastructure Builder strengthens the existing control_handoff and workflow_interop owners. BI-ONT-023 preserves human authority and intent; BI-ONT-024 prefers verified native semantic APIs and preserves peripheral preferences.

Unknown presence or activity yields. Two fresh idle probes permit re-evaluation followed by target/scene/save validation. Partial callbacks retain intent and require observed reconciliation plus an explicit remainder, never replay. Native calls respect the same gate; desktop fallback requires opt-in. Already executing native calls and unadopted agents cannot be forcibly intercepted.

## Cross-product peripheral semantics and RCA (November 10, 2026)

Machine concept `OS_PERIPHERAL_AUTHORITY` (`contracts/ontology.v1.json`, invariant `BI-ONT-025`) makes the Windows-repair boundary discoverable to ontology readers. Its `CONTROL_PERMIT → DOES_NOT_GRANT_OS_REPAIR_AUTHORITY` relationship disallows promoting game-side admission to host control. Incident evidence can refer to the OS owner without asserting service-only causality.

The host boundary is `contracts/peripheral-authority.v1.json`, linked to the `PLAYER_INTENT`, `PLAYER_PRESENCE`, `HOST_ACTION`, `CONTROL_PERMIT`, `INCIDENT`, and `PROOF_RECEIPT` concepts. Windows `OS_BLUETOOTH_SERVICE`, `OS_DRIVER_OR_ADAPTER`, and `OS_INPUT_PREFERENCE` effects are **not game affordances**. A game-side control permit cannot be promoted into permission for service, driver, pairing or screenshot-preference changes. Unknown host effects deny until reviewed. SysAdminSuite is the authoritative Windows recovery owner; its existing field path is `docs/field/BLUETOOTH-PERIPHERAL-RECOVERY.md` and its agent routing contract is `harness/api/bluetooth-peripheral-incident-route.v1.json` in that separate repository. The game source regression gate is `scripts/check_peripheral_boundary.py`; it is not a kernel enforcement boundary and cannot stop external unadopted agents. See `docs/PERIPHERAL_INCIDENT.md` for the incident evidence and separated causal claims.

## 2026-11-10 — observed Order menus and source/action semantics

`OBSERVED_MENU_ROUTE`, `ACQUISITION_SOURCE` and `ACTION_EFFECT_CLASS` are graph concepts in `contracts/ontology.v1.json` (BI-ONT-026 / BI-ONT-027); owner is `contracts/upgrade-parts-force.v1.json#acquisition_routing` with application entrypoint `betterinstincts/upgrade_parts_force.py`. Agent semantic routing and read-only CLI are in `docs/ACQUISITION_ROUTING.md`. A previously seen two-step More Choices depth is **not** immutable; menu traversal consumes current visible choices, stops on repeated page signatures and never fabricates a click coordinate. Any portrait in an observed active household is eligible only after a fresh actor, player and screen-lease check. Computer Order is an instant-*candidate*; Fabricator eco parts, regular generator fuel from recycled resources, and insect-farm biofuel are distinct producer/effect classes. Pending game observation cannot be promoted to an inventory/fuel delta, Sims playable mod, or BI-002 certification.


## Revision 5 — P00/P01 world-target highlight and learning semantics

The machine graph `contracts/ontology.v1.json` now distinguishes `HIGHLIGHT_OBSERVATION` (capture-bound two-source positive/negative cue evidence), `WORLD_TARGET_TRACK` (camera- and object-identity-bound continuity) and `WORLD_INTERACTION_ATTEMPT` (observed, replay-unique, non-interrupted outcome). These are **refinements** of `OBSERVATION`, `GAME_OBJECT`, `VIEW_SCENE`, `OUTCOME` and `LEARNING_MODEL`, not rival model/router owners. The target is **world scenery**, not calibrated fixed HUD chrome.

- `BI-ONT-028` guards multi-frame identity, null highlighted identity on actually ABSENT cues, transient/occluded/unknown distinction, and the fact that `LOCKED` is not an input permit.
- `BI-ONT-029` guards independent before/after labels, explicit lack of player interruption, replay exclusion across persisted training and held-out evaluation, fail-closed capacity and advice-only models.
- `BI-ONT-030` preserves BI-002 needs as the active product gate and makes actual local P08 sensor/outcome work one-screen serial, not an invitation to run concurrent desktop clickers or replace the separately owned PR #159.

Source: `contracts/world-traversal-learning.v1.json`; pure implementation `betterinstincts/world_traversal_learning.py`; separate host input admits remain in existing screen, save, lot and player-presence owners. Reusable codebase map/workflow/artifact inventory and CLI verifier: `contracts/world-traversal-harness.v1.json`, `docs/WORLD_TRAVERSAL_HARNESS.md`, `scripts/check_world_traversal_harness.py`. Exact game patch/capture and independent operator review still needed for real screenshots and click-outcome proofs; v5 ontology CI does not install or certify a Sims mod.

## Revision 6 — P00/P01 human-owned control, typed effects, and proof ceilings

Distinct concepts: `EFFECT_ADMISSION_CLASS` (host-side authority, **not**
`ACTION_EFFECT_CLASS` for Sims purchases), `PASSIVE_BACKGROUND_LANE` (trusted
non-interactive in-process work), `HUMAN_CONTROL_RECLAIM` (input anywhere
invalidates stale agent permission), `OS_INPUT_CAPABILITY` (operator-owned
Bluetooth, screenshot/Print Screen, Escape/U and accessibility controls),
and `AGENT_ADOPTION_COVERAGE` (CI/source adoption ≠ physical host enforcement).

`BI-ONT-031..035` require effect classification and deny unknowns;
safe background processing cannot borrow the desktop; human activity blocks
focus/game input; host input configuration is outside game authority; and
registered adapters must preserve separate CI, merge, local-install and live
physical takeover evidence. The machine harness owner is
`contracts/human-first-harness.v1.json`; validator
`scripts/check_human_sovereignty.py`. Existing vision, camera, build,
purchases, aspirations, career, needs, queue and save contracts inherit these
cross-cutting gates without replacing their own more specific risk checks.

## Revision 7 — deterministic household navigation (P00/P01 + Fifth Gear)

`NAVIGATION_SCOPE`, `NAVIGATION_REGION`, `NAVIGATION_PASSAGE`, `NAVIGATION_FRONTIER`, `NAVIGATION_INTENT`, `NAVIGATION_PROGRESS`, `NAVIGATION_STALL` and `NAVIGATION_RECOVERY` are first-class, scope-bound semantics. `BI-ONT-036..041` distinguish player/Sim movement from camera repositioning, verified traversable passages from visual adjacency, and progress evidence from repeated motion. `contracts/household-navigation.v1.json` owns the bounded pure navigation policy; `betterinstincts/household_navigation.py` is the read-only planner. Position loops or failed transitions replan through verified alternatives or abstain. User-supplied save/profile identity is never published or embedded in shared defaults. Region arrival does not certify an object interaction or earn a control permit. Offline results do not certify Sims 4 gameplay. Existing BI-002 and player-first gates remain authoritative.


## Closer gate on BI-ONT-035 — unadopted means runtime denied

`AGENT_ADOPTION_COVERAGE` is not satisfied by an inventoried warning alone.
BI-ONT-035 now has a concrete repository-only negative path: six declared
legacy executors must call `betterinstincts.legacy_screen_boundary`
to deny execution before any focus/SendInput. A Python AST harness check
verifies the declared denial call and offline mocks prove no callback/click
is dispatched. No new ontology node or rival admission policy is needed:
`screen_admit` stays canonical for future adoption. A future status change
must include independent game-scene/target input-safety proof; passing static
checks does not certify physical Windows operator reclamation.

## P00/P01 native-mechanic implementation route

Ontology revision 8 introduces three independent distinctions:
`GAMEPLAY_IMPLEMENTATION_ROUTE` (where game behavior is actually
implemented), `NATIVE_MECHANIC_EVIDENCE` (exact-game-build EA source and
real gameplay outcome), and `HOST_LAB_BOUNDARY` (temporary, opt-in desktop
inspection/testing, **not** autonomous gameplay). Invariants
`BI-ONT-042..045` require EA-native mechanics first, a machine-read
route decision for all changes to product Python, no false promotion of
host/offline policy into installed game proof, and unconditional
player-first protection. This extends, never replaces, existing
`MECHANIC_PATH`, `PLAYER_INTENT`, `CONTROL_PERMIT`,
`EFFECT_ADMISSION_CLASS` and `AGENT_ADOPTION_COVERAGE`.
Canonical implementation routing owner:
`contracts/native-gameplay-authority.v1.json` with
`scripts/check_native_gameplay_authority.py`. Existing host viewport,
mouse, scene and save automation stays available only as an explicitly
bounded lab interface; it is not a new engine or fallback for autonomy.
