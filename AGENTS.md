# BetterInstincts — canonical agent entrypoint

Before edits/samples/experiments, read `docs/ONTOLOGY.md` + owners; commit `contracts/consultations/` first; run `scripts/semantic_preflight.py`. Read **docs/DOCTRINE.md**, **docs/LEDGER.md**, **docs/PROMPT_INVOCATIONS.md**. **plans/active/BI-001.md** merged; **plans/active/BI-002.md** owns game-lab gate.

## Parent objective
Create a free, community-native Sims 4 autonomy mod that helps Sims meet needs, earn income, progress in careers, and enjoy their lives without overriding manual player control or personality. Do not confuse an offline policy prototype with a playable mod.

## Mandatory preflight
Refresh repo HEAD/branch, PRs, status and game/version. Declare HOST, providers, scopes, collisions, tests, proof and parent gate. Resolve P-numbers using Moonwake's exact catalog.

## Invariants
- **Player first:** no interruption of explicit player commands; no uncontrolled repeated autonomy loops.
- **Save-safe:** never edit, migrate, delete or overwrite user saves or game files. Unknown/user saves stay protected; a lab-like name never proves disposability.
- **Storage:** never write to arbitrary user-profile directories, auto-discover installs, or bulk-copy game assets. No background daemons, scheduled scans, network telemetry, or unbounded logs.
- **Community-native:** inspect credible mod precedent and licensing before introducing frameworks; favor tuning before script hooks if it really fits.
- **Performance:** bounded event work; no per-frame global scans or busy-waits. No runtime hooks until measured in a disposable game.
- **Evidence:** separate tests, builds, PR, merge and live behavior. Scenes need two independent cues; unknown means no action. See docs/SCENE_INTELLIGENCE.md.
- **Continuity:** preserve and update docs/LEDGER.md, docs/ROADMAP.md, and the owning sprint with accepted corrections; no chat-only critical decisions.

## Multiversion + real-game closure
Read `docs/COMPATIBILITY.md`, `docs/LIVE_CERT.md`, and `plans/active/BI-002.execution.v1.json`. Never select a newer game patch automatically, silently change an older certified configuration, or certify synthetic tests as game observations. Require an exact full game version, platform and module; UNKNOWN_VERSION must fail closed. CI compares previously certified profile bytes and evidence to the Git base.

The **local game-capable agent** owns the hunger experiment to completion: inspect the installed game and tuning, produce a reversible package, record at least five vanilla and five modified trials, verify rollback and player queue safety, and provide reviewed gameplay evidence. Plans, handoffs and offline CI **do not close BI-002**. Without game access report BLOCKED_LOCAL_GAME_ACCESS and leave the sprint ACTIVE while continuing safe independent work. Progress: `python -m scripts.live_cert status --run-id ID`.

## Horizon continuity
Read `docs/HORIZON.md`, `plans/horizon.v1.json` and `plans/active/BI-003.execution.v1.json`. Order: all six needs, balance, income, skills, careers; maintain earlier systems and patch profiles throughout. Never mistake offline simulation for game proof, close BI-002 prematurely or invent an alternative trajectory. Run `python -m scripts.check_horizon`.

## Completion contract
Report CHANGED | PROVED | NEXT, including exact checks run/skipped, commit SHA, push/PR/merge, game patch and live-test status. A plan is not implementation; a green CI check is not playable-mod proof. Do not publish pre-alpha as a release.

P04: `docs/handoff/BI-JUDGMENT-LEARNING-P04-2026-11-07.md` (BI-002 active).
