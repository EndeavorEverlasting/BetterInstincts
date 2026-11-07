# BetterInstincts — canonical agent entrypoint

Before edits/samples/experiments, read `docs/ONTOLOGY.md` + owners; commit `contracts/consultations/` first; run `scripts/semantic_preflight.py`. Read **docs/DOCTRINE.md**, **docs/LEDGER.md**, **docs/PROMPT_INVOCATIONS.md**. **plans/active/BI-001.md** merged; **plans/active/BI-002.md** owns game-lab gate.

## Parent objective
Build a community-native Sims 4 autonomy mod for needs, income, careers and personality. Never override the player; an offline policy prototype is not a playable mod.

## Mandatory preflight
Refresh HEAD/branch, PRs, status, game/version; declare host, scopes, collisions, tests, proof and parent gate. Resolve P-numbers via Moonwake catalog.

## P04 hidden-object discovery
For any BetterInstincts P04, inventory `plans/active/BI-HIDDEN-OBJECTS.P04.md` and run `python -m scripts.hidden_object_discovery guide`. On hidden-item scope, follow its dispatch/scene/save/consent gates; otherwise defer without blocking the parent. Audit real local evidence using `python -m scripts.hidden_object_discovery audit --observation dist/game-host/hidden-object-p04-receipt.json`. This cannot certify gameplay.

## Invariants
- **Player first:** no interruption of explicit player commands; no uncontrolled repeated autonomy loops.
- **Save-safe:** never edit, delete, migrate or overwrite user saves/game files. Unknown/user saves protected; names never prove disposability.
- **Storage:** no arbitrary user-profile writes, auto-discovery, asset copying, daemons, scheduled scans, telemetry or unbounded logs.
- **Community-native:** review prior art/licensing; favor tuning before script hooks where justified.
- **Performance:** bounded work; no global per-frame scans, busy-waits or unmeasured runtime hooks.
- **Evidence:** separate tests, build, PR, merge and gameplay. Scenes need two independent cues; unknown -> no action. See docs/SCENE_INTELLIGENCE.md.
- **Continuity:** keep docs/LEDGER.md, docs/ROADMAP.md and sprint current; no chat-only decisions.

## Multiversion + real-game closure
Read `docs/COMPATIBILITY.md`, `docs/LIVE_CERT.md`, `plans/active/BI-002.execution.v1.json`. Pin exact version/platform/module; UNKNOWN_VERSION fails closed. Never auto-select patch, alter older certified profiles, or claim synthetic game proof. CI protects prior certified bytes.

The **local agent** owns hunger: inspect installed game/tuning, build reversible package, run 5 vanilla + 5 modified trials, verify rollback/queue and reviewed proof. Offline handoffs/CI do not close BI-002. Without host: BLOCKED_LOCAL_GAME_ACCESS, keep ACTIVE. `python -m scripts.live_cert status --run-id ID`.

## Horizon continuity
Read `docs/HORIZON.md`, `plans/horizon.v1.json`, `plans/active/BI-003.execution.v1.json`. Order: all six needs, balance, income, skills, careers; preserve prior systems/patches. Offline != game proof; BI-002 stays open. `python -m scripts.check_horizon`.

## Completion contract
Report CHANGED | PROVED | NEXT, including exact checks run/skipped, commit SHA, push/PR/merge, game patch and live-test status. A plan is not implementation; a green CI check is not playable-mod proof. Do not publish pre-alpha as a release.

P04: `docs/handoff/BI-JUDGMENT-LEARNING-P04-2026-11-07.md`; ontology: `docs/handoff/BI-SEMANTIC-ONTOLOGY-P04-2026-11-07.md`; hidden objects: `plans/active/BI-HIDDEN-OBJECTS.P04.md` (BI-002 active).
