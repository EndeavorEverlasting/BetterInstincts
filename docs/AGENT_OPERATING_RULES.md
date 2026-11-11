# Mandatory detailed agent operating rules

Read with the compact root AGENTS.md before edits. These existing detailed rules remain binding; the root routes to this owner to meet its enforced size budget.

# BetterInstincts — canonical agent entrypoint

Before edits/samples/experiments, read `docs/ONTOLOGY.md` + owners; commit `contracts/consultations/` first; run `scripts/semantic_preflight.py`. Read **docs/DOCTRINE.md**, **docs/LEDGER.md**, **docs/PROMPT_INVOCATIONS.md**. **plans/active/BI-001.md** merged; **plans/active/BI-002.md** owns game-lab gate.

## Parent objective
Community-native Sims 4 autonomy: needs, income, careers, personality. Player always first; offline prototypes are not playable mods.

## Mandatory preflight
Refresh HEAD/PRs/game; declare host, scope, collisions, tests and proof. Resolve Moonwake P-IDs.

## P04 hidden-object discovery
Read `plans/active/BI-HIDDEN-OBJECTS.P04.md`, `docs/HIDDEN_OBJECT_SCOUT.md`; dispatch/scene/save/consent. `python -m scripts.hidden_object_discovery guide`; `python -m scripts.hidden_object_discovery audit --observation dist/game-host/hidden-object-p04-receipt.json`. Scout: `scripts.hidden_object_scout goal`. No autorun.

Useful-item force: `python -m scripts.household_object_force`. DIY parts: `python -m scripts.upgrade_parts_force`.

## Portable object-action learning (P95 → P82 → P08 → P07 → P124)

Machine owner: `contracts/object-action-catalog.v1.json`; code owner:
`betterinstincts/object_action_catalog.py`; event entrypoint:
`host_listener.observe_object_action`. When a calibrated operator/host
sensor observes a menu, selection or outcome, send sanitized semantics to
this port only inside an **explicit active listener**. Never replace this
with raw Windows mouse/key logging. Query through the existing opportunity
survey with exact current patch, menu, target and capture; results are
advisory-only and never override human action, queue ownership or input
authority. See `docs/OBJECT_ACTION_CATALOG.md`. BI-002 remains active.

Reviewed object usefulness requires distinct post-action evidence; replayed proof, legacy count-only aggregates, stale event sequences and contradictory harmful outcomes must fail closed. See `contracts/object-action-catalog.v1.json` and its tests.

## Invariants
- **Player first:** no interrupt of explicit player commands; no uncontrolled autonomy loops.
- **Save-safe:** never edit/delete/migrate/overwrite user saves/game files. Unknown/user saves protected.
- **Build structure / FLOOR_2 / all purchases:** No agent Build/Buy edits/purchases until ALL floors/rooms are scanned, classified, backed up to My Library pre-edit and model readback verified. Unknowns, stale saves, incomplete FLOOR_2 = DENY. Keep stairs/Craftidink CANCEL_UI and `admit_live_structure_effect`; offline leases are NOT live input permits. `docs/BUILD_LIBRARY_CHECKPOINT.md`.
- **Offline install:** never EA Connect; Stay Offline only; play as installed.
- **Storage:** no arbitrary profile writes, auto-discovery, asset copy, daemons, telemetry, unbounded logs.
- **Community-native:** review prior art/licensing; favor tuning before script hooks where justified.
- **Performance:** bounded work; no global per-frame scans, busy-waits or unmeasured runtime hooks.
- **Evidence:** separate tests, build, PR, merge and gameplay. See docs/SCENE_INTELLIGENCE.md; two cues; unknown -> no action.
- **Continuity:** keep docs/LEDGER.md, docs/ROADMAP.md and sprint current; no chat-only decisions.
- **Live-host ops (P00/P01):** Operator live corrections are incomplete until encoded in `contracts/live-host-ops.v1.json` + `betterinstincts/live_host_ops.py` (+ tests/AGENTS/DOCTRINE/Horizon). Chat memory alone is forbidden. Architecture `PAUSED_PRODUCTIVITY_BEFORE_TIME_RISK`: keep PAUSED; Order/Purchase Upgrade Parts or robotics workstation spawn before Needs/unpause; OFF_INTENT_VIEW → Esc(+F1)+Shift+Enter; EDGE_MOUSE_PARK→creek → SAFE_CURSOR_REST then Shift+Enter; no hardcoded field XY across zoom; yield focus to mouse/Wispr; never Sell / delete Slot_00000007. Fifth Gear with Sims PID live: execute live gates — do **not** emit a new P05 pack.
- **Lot geometry EA-file first:** Prefer authorized READ_ONLY Sims user-data under Documents/Electronic Arts (`contracts/lot-geometry-source.v1.json`) over inventing town maps from PrintWindow. Never open Slot_00000007 without explicit auth. Cardinal/street-creek/camera maps are FALLBACK only.
- **Lot cardinal semantics (FALLBACK):** After EA parse + `lot_floor_map` graph: corner/side relations in `contracts/lot-cardinal-semantics.v1.json` — bathtub SAME_SIDE_AS hydroponics; fridge OPPOSITE near doors; robotics workstation ~90° from FRONT_DOOR. Bargain Bendh has **STREET_SIDE** (asphalt OFF_LOT risk) vs **CREEK_SIDE** (canal/water OFF_LOT risk); `assess_camera_side_drift` → SAFE_CURSOR_REST+Shift+Enter. Workstation is **GRAY** (not blue); Gardener-Bot needs fix; never Activate pending Servo. My Library: `CLEAR_SEARCH_BEFORE_QUERY`.
- **Lot boundary / house footprint:** Before any Live world click, admit via `contracts/lot-boundary.v1.json` + `betterinstincts/lot_boundary.py`. Street/asphalt/neighbor/canal and Buy-without-census are OUTSIDE — DENY. Cardinal hints never justify street/creek clicks. Recover Esc(+F1)+Shift+Enter.

## P00/P01 world traversal perception, learning and P08 boundary

Read `docs/WORLD_TRAVERSAL_HARNESS.md` and the single manifest `contracts/world-traversal-harness.v1.json` before any work involving **world objects** or their highlights (not fixed HUD chrome), tracking, post-click learning, sensor acquisition, or the supporting Horizon P08 gate. Ontology v1 revision 5 binds `HIGHLIGHT_OBSERVATION`, `WORLD_TARGET_TRACK`, `WORLD_INTERACTION_ATTEMPT` and invariants `BI-ONT-028..030`. Read `contracts/world-traversal-learning.v1.json`, `docs/WORLD_TRAVERSAL_LEARNING.md`, `plans/horizon.v1.json#next_supporting_priority` and `plans/active/BI-HORIZON.dispatch.v1.json`; do not let a prose prompt supplant these owners.

Two independent, fresh, capture/camera/target-bound cues per frame and two frames are required to confirm highlight identity/continuity. A null highlighted-object ID with two ABSENT frames is `HIGHLIGHT_LOST`; PRESENT without ID, occlusion, changed camera or source ambiguity must abstain. Even `LOCKED` means **framing only**; only the existing lot, scene, save, human-presence, exact-build and one-effect host checks can authorize a local click. Never auto-reclick after missing highlight or reuse old coordinates after panning.

A learning row requires a real post-action outcome, explicit `player_interrupted: false`, disjoint before/after capture refs and replay-unique fingerprint (also excluded from holdout); no synthetic score or advice creates a `CONTROL_PERMIT`. The bounded model has 2,048 accepted history identities globally; cap/legacy uncertainty fails closed. No automatic screenshot storage or training daemon, named local Sims, global hotkeys, OS repair, desktop settings changes, or user-save reads. Source-only assessments may run without focus; **actual P08 capture** requires a separately approved disposable Sims session, single host-screen owner and fresh local provenance. WORLD_SENSOR → WORLD_OUTCOME → WORLD_INTEGRATE is serial with BI-002 gameplay, **not** a replacement or prerequisite for the active hunger gate. Do not overwrite the separate PR #159 writer.

Before branching run `python -m scripts.check_world_traversal_harness`, `python -m scripts.horizon_status`; focused evaluator `python -m scripts.world_traversal_eval` is an *offline fixture*, not a screenshot sensor. Local skill `.cursor/skills/world-traversal-p08/SKILL.md` is a tracked opt-in procedure, **not proof it was installed/activated** in a local agent.

## Multiversion + real-game closure
Read `docs/COMPATIBILITY.md`, `docs/LIVE_CERT.md`, `plans/active/BI-002.execution.v1.json`. Pin exact version/platform/module; UNKNOWN_VERSION denies. Never change older certified profiles or call synthetic work game proof.

**Local agent** owns hunger: inspect game/tuning, build reversible package, run 5 vanilla + 5 modified trials, verify rollback, queue and review. CI/handoffs cannot close BI-002; without host: BLOCKED_LOCAL_GAME_ACCESS, ACTIVE. `python -m scripts.live_cert status --run-id ID`.

## Computer Order, Eco materials, and household purchase routing

All agents use `docs/ACQUISITION_ROUTING.md` and `contracts/upgrade-parts-force.v1.json#acquisition_routing` (owner `betterinstincts/upgrade_parts_force.py`). Left-click observed computer → resolve Order by visible choices and bounded More Choices → resolve the desired observed domain → open picker → iterate each visible requested item with inventory/funds proof. Never hardcode two clicks; Order may also be behind More Choices. Select/revalidate each **observed** household portrait, never a fixed named roster or unadmitted Space-only traverse. Order is `INSTANT_UI_CANDIDATE`, not guaranteed; Fabricator eco parts (15 bits/10 pieces), Recycler/generator fuel, and Insect Farm biofuel are distinct queued/time-gated/resource routes. Plans are `execute_allowed=false`; player input, shared screen lease, saved-game safety, patch and pack observation gates remain active. Tests: `tests/test_upgrade_parts_force.py` and `tests/test_acquisition_integration.py`.

## Horizon continuity
Read `docs/HORIZON.md`, `plans/horizon.v1.json`, `plans/active/BI-003.execution.v1.json`. Order: all six needs, balance, income, skills, careers; preserve prior patches. BI-002 stays open. `python -m scripts.check_horizon`.

## Completion contract
Report CHANGED | PROVED | NEXT with checks, SHA, push/PR/merge, patch, live status. A plan is not implementation; a green CI check is not playable-mod proof.

P04: `docs/handoff/BI-JUDGMENT-LEARNING-P04-2026-11-07.md`; ontology: `docs/handoff/BI-SEMANTIC-ONTOLOGY-P04-2026-11-07.md`.
Interop: `docs/ASYNC_INTEROP.md` (15s idle). Likes: `docs/PREFERENCE_PROMPTS.md`.
Skills: `docs/HOUSEHOLD_JUDGMENT.md` (fixed roster; serial/offline).

## P00/P01 user interaction sovereignty

Ontology revision 4 (`contracts/ontology.v1.json#interaction_policy`) embraces any user-chosen game, mod, voice/assistive or other-app interaction. Adopted autonomous effects yield and resume only after two fresh idle probes plus target validation. Prefer verified native semantic APIs. Desktop fallback requires opt-in. New adapters use CooperativeScreenQueue.enqueue_effect; partial callbacks retain intent for reconcile with observed outcome and a rebuilt remainder. Never alter peripheral preferences or UAC for game automation. External raw callers are not intercepted.

## P00/P01 human-control reclamation and effect admission (revision 6)

Fresh physical user activity in **any app or monitor**, plus explicit voice/assistive
operator-busy, outranks screen/game input at the next cooperative checkpoint.
Classify effects via `contracts/effect-authority.v1.json`. Read-only bounded
observations may continue only when reviewed for no focus, screen, game-state,
save, host-setting or unconsented capture mutation. Any unknown effect denies;
host OS input/peripheral configuration is not within game authority.

Before borrowing Sims foreground, two fresh trusted desktop-wide idle checks
must pass. After any borrowed focus, confirm twice again and verify actual Sims
foreground. Game effects still need scene/save/queue/target and exclusive desktop
ownership. A partially executed effect requires an observed outcome and rebuilt
remainder: do not blind replay, cancel a player's queue or steal their keyboard.
After a human returns, resume only upon new per-effect evidence. Local Windows
installation and Cursor hooks require independent activation and verification.

Use `scripts/check_human_sovereignty.py` for machine coverage (not an OS
sandbox), plus `docs/ASYNC_INTEROP.md` and `docs/VALIDATION.md` for proof gates.

## P00 full governance installation — mandatory for all repository writing agents

**Operating principles:** evidence before action; repository/default-branch floor
before edits; bounded work with declared scope; one independent writer per
branch/worktree and generated surface; reuse canonical owners before replacing;
no completion claim without actual proof. No agent frustration, failed mouse
capture or competing UI activity overrides human autonomy, privacy, or safety.

**Instruction precedence:** platform/security/legal and explicit repo-owner
decisions > this canonical `AGENTS.md` and mandatory detailed governance >
the *current, exact* task-specific Moonwake P-number contract > generic
agent/default behavior. A repo file cannot overrule higher-priority protections.

**Writing sprint declaration:** state real repo and runtime/host (provider
connection is not the user's Windows machine), refreshed branch/PR/main floor,
mission and lane, one-writer ownership, affected and forbidden paths, expected
tracked artifacts, dependencies/collisions, validator commands and evidence
ceiling. In particular, classify whether an effect requires the operator
desktop or is reviewed, read-only background work; never silently expand
P00 governance into unrelated application code or use P01 to rewrite P00.

**Completion:** report CHANGED (real paths), PROVED (commands and outcomes),
NEXT (first executable gate), exact commit SHA, push/PR and actual default
branch status. Independently label local checkout, installed launcher, hook
activation, Windows human-input takeover and Sims Live Mode. No synthetic
fixture, plan, report or draft is gameplay certification.

**Forbidden:** acknowledgment-only execution, plans replacing reachable work,
unsupported completion or merge/deploy assertions, secret publication, OS
Bluetooth/driver/screenshot/input remapping, unsupported game execution,
protected-save changes, stealth mouse/keyboard hooks, and bypassing operator
approval or installed agent protections. If a source adapter is unadopted,
identify the gap instead of running or laundering it through another tool.

## Household navigation anti-oscillation (P00/P01)

For active-household mapping, room traversal, goal routing and camera surveys read `docs/HOUSEHOLD_NAVIGATION.md` and `contracts/household-navigation.v1.json`. Plan with `betterinstincts.household_navigation.plan_household_navigation` via `betterinstincts.room_map_traverse.plan_semantic_region_route`; require opaque actor/lot/household identifiers, verified passages and revision-bound progress. Never infer Sim walkability from `lot_floor_map` `ADJACENT`, `CORNER_OF` or camera pan hints. Preserve distinct discovery, goal and recovery states. A-B-A-B without independent novelty is a stall; no unbounded retries, no blind reclick, no out-of-lot or cross-save state carry. Run `python -m scripts.check_household_navigation` and `python -m unittest tests.test_household_navigation -v`; these are offline only and do not grant an OS/game input permit.
