# BetterInstincts — canonical agent entrypoint

Before edits/samples/experiments, read `docs/ONTOLOGY.md` + owners; commit `contracts/consultations/` first; run `scripts/semantic_preflight.py`. Read **docs/DOCTRINE.md**, **docs/LEDGER.md**, **docs/PROMPT_INVOCATIONS.md**. **plans/active/BI-001.md** merged; **plans/active/BI-002.md** owns game-lab gate.

## Parent objective
Build a community-native Sims 4 autonomy mod for needs, income, careers and personality. Never override the player; an offline policy prototype is not a playable mod.

## Mandatory preflight
Refresh HEAD/branch, PRs, status, game/version; declare host, scopes, collisions, tests, proof and parent gate. Resolve P-numbers via Moonwake catalog.

## P04 hidden-object discovery
Inventory `plans/active/BI-HIDDEN-OBJECTS.P04.md`; `python -m scripts.hidden_object_discovery guide`. Scope: dispatch/scene/save/consent; else defer. Audit: `python -m scripts.hidden_object_discovery audit --observation dist/game-host/hidden-object-p04-receipt.json`. Scout: `python -m scripts.hidden_object_scout goal` (`docs/HIDDEN_OBJECT_SCOUT.md`). No autorun.

Useful-item force: `python -m scripts.household_object_force`. DIY parts: `python -m scripts.upgrade_parts_force`.

## Invariants
- **Player first:** no interrupt of explicit player commands; no uncontrolled autonomy loops.
- **Save-safe:** never edit/delete/migrate/overwrite user saves/game files. Unknown/user saves protected.
- **Build structure / FLOOR_2:** My Library before structure mutate; `admit_live_structure_effect`; Craftidink=CANCEL_UI. `docs/BUILD_LIBRARY_CHECKPOINT.md`.
- **Offline install:** never EA Connect; Stay Offline only; play as installed.
- **Storage:** no arbitrary profile writes, auto-discovery, asset copy, daemons, telemetry, unbounded logs.
- **Community-native:** review prior art/licensing; favor tuning before script hooks where justified.
- **Performance:** bounded work; no global per-frame scans, busy-waits or unmeasured runtime hooks.
- **Evidence:** separate tests, build, PR, merge and gameplay. See docs/SCENE_INTELLIGENCE.md; two cues; unknown -> no action.
- **Continuity:** keep docs/LEDGER.md, docs/ROADMAP.md and sprint current; no chat-only decisions.

## Multiversion + real-game closure
Read `docs/COMPATIBILITY.md`, `docs/LIVE_CERT.md`, `plans/active/BI-002.execution.v1.json`. Pin exact version/platform/module; UNKNOWN_VERSION fails closed. Never auto-select patch, alter older certified profiles, or claim synthetic game proof. CI protects prior certified bytes.

The **local agent** owns hunger: inspect installed game/tuning, build reversible package, run 5 vanilla + 5 modified trials, verify rollback/queue and reviewed proof. Offline handoffs/CI do not close BI-002. Without host: BLOCKED_LOCAL_GAME_ACCESS, keep ACTIVE. `python -m scripts.live_cert status --run-id ID`.

## Horizon continuity
Read `docs/HORIZON.md`, `plans/horizon.v1.json`, `plans/active/BI-003.execution.v1.json`. Order: all six needs, balance, income, skills, careers; preserve prior systems/patches. Offline != game proof; BI-002 stays open. `python -m scripts.check_horizon`.

## Completion contract
Report CHANGED | PROVED | NEXT with checks, SHA, push/PR/merge, patch, live status. A plan is not implementation; a green CI check is not playable-mod proof.

P04: `docs/handoff/BI-JUDGMENT-LEARNING-P04-2026-11-07.md`; ontology: `docs/handoff/BI-SEMANTIC-ONTOLOGY-P04-2026-11-07.md`; hidden objects: `plans/active/BI-HIDDEN-OBJECTS.P04.md` (BI-002 active).
Interop: `docs/ASYNC_INTEROP.md` (15s idle). Likes: `docs/PREFERENCE_PROMPTS.md`.

## Whole-home preservation before any agent Build/Buy action (2026-11-09)

**Hard stop: no agent may buy, sell, place, move, inventory, sledge, erase, replace, or otherwise mutate a home or lot until a full pre-change backup is verified.** Scan and classify **every** floor, room, and outdoor zone first (including stories not currently visible); maintain the lot's revisioned `house_state` model and use `room_census` for attested room/functional/style classification. Require a complete, operator-confirmed manifest of all floors and rooms with evidence captures, a **pre-mutation Sims My Library building save** separately attested, and successful local metadata checkpoint write/readback against the exact revision. Game Save As does not replace a Library blueprint. Unknown/unobserved floors or rooms, partial classification, stale revisions, missing proof or tool bypass MUST DENY mutation; the safe next action is observation/backup, never improvisation. **Only a positively admitted, current lease may flow to a host input adapter**; an offline `MUTATION_ADMITTED` (`execute_allowed: false`) is not a live input permit. Raw Win32/Playwright clicks in Build/Buy from an unbound agent are prohibited until a consuming host adapter is independently proved to enforce the lease. Player's own UI actions remain under player control. No implicit save-folder access or game mutation is granted. Source: `contracts/build-library-checkpoint.v1.json`, `betterinstincts/build_library_checkpoint.py`, `betterinstincts/house_state.py`, `docs/BUILD_LIBRARY_CHECKPOINT.md`, and `tests/test_lot_mutation_preservation.py`.
