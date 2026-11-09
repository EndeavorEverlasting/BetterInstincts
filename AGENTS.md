# BetterInstincts — canonical agent entrypoint

Before edits/samples/experiments, read `docs/ONTOLOGY.md` + owners; commit `contracts/consultations/` first; run `scripts/semantic_preflight.py`. Read **docs/DOCTRINE.md**, **docs/LEDGER.md**, **docs/PROMPT_INVOCATIONS.md**. **plans/active/BI-001.md** merged; **plans/active/BI-002.md** owns game-lab gate.

## Parent objective
Build a community-native Sims 4 autonomy mod for needs, income, careers and personality. Never override the player; an offline policy prototype is not a playable mod.

## Mandatory preflight
Refresh HEAD/branch, PRs, status, game/version; declare host, scopes, collisions, tests, proof and parent gate. Resolve P-numbers via Moonwake catalog.

## P04 hidden-object discovery
Read `plans/active/BI-HIDDEN-OBJECTS.P04.md` and `docs/HIDDEN_OBJECT_SCOUT.md`. Respect dispatch/scene/save/consent; no autorun. Guide/audit: `scripts.hidden_object_discovery`; scout: `scripts.hidden_object_scout goal`.

Useful-item force: `python -m scripts.household_object_force`. DIY parts: `python -m scripts.upgrade_parts_force`.

## Invariants
- **Player first:** no interrupt of explicit player commands; no uncontrolled autonomy loops.
- **Save-safe:** never edit/delete/migrate/overwrite user saves/game files. Unknown/user saves protected.
- **Build structure / FLOOR_2 / all purchases:** No agent Build/Buy mutation until ALL floors/rooms are observed, classified, and backed up by a pre-edit My Library building save plus persisted model readback. Unknowns, stale saves, incomplete FLOOR_2 = DENY. Keep stairs/Craftidink CANCEL_UI and `admit_live_structure_effect`; offline leases are NOT live input permits. `docs/BUILD_LIBRARY_CHECKPOINT.md`.
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

P04 & ontology handoffs: see `docs/handoff/`; hidden objects: `plans/active/BI-HIDDEN-OBJECTS.P04.md`.
Interop: `docs/ASYNC_INTEROP.md` (15s idle). Likes: `docs/PREFERENCE_PROMPTS.md`.
