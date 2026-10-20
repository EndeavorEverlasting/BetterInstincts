# BetterInstincts — canonical agent entrypoint

Read **docs/DOCTRINE.md**, **docs/LEDGER.md**, and **docs/PROMPT_INVOCATIONS.md** before designing or editing. Their tracked paths are authority for this project. **plans/active/BI-001.md** owns the current sprint and proof gates. This file is intentionally short; do not silently bypass it or create alternate project ledgers.

## Parent objective
Create a free, community-native Sims 4 autonomy mod that helps Sims meet needs, earn income, progress in careers, and enjoy their lives without overriding manual player control or personality. Do not confuse an offline policy prototype with a playable mod.

## Mandatory preflight
Refresh repo, branch, HEAD, status, PRs and current game/version evidence before mutation. Declare actual HOST, providers, owned/forbidden paths, collisions, dependencies, checks, proof ceiling, and parent gate. Resolve P-numbers only from TokenCorridor's canonical resolver/catalog; no guessed prompt interpretations.

## Invariants
- **Player first:** no interruption of explicit player commands; no uncontrolled repeated autonomy loops.
- **Save-safe:** do not edit, migrate, delete, or overwrite user saves or game files. Use disposable saves for live tests only.
- **Storage:** never write to arbitrary user-profile directories, auto-discover installs, or bulk-copy game assets. No background daemons, scheduled scans, network telemetry, or unbounded logs.
- **Community-native:** inspect credible mod precedent and licensing before introducing frameworks; favor tuning before script hooks if it really fits.
- **Performance:** bounded event work; no per-frame global scans or busy-waits. No runtime hooks until measured in a disposable game.
- **Evidence:** tests, built artifacts, commit, PR, merged status, and live game behavior are separate proof levels; never inflate them.
- **Continuity:** preserve and update docs/LEDGER.md, docs/ROADMAP.md, and the owning sprint with accepted corrections; no chat-only critical decisions.

## Completion contract
Report CHANGED | PROVED | NEXT, including exact checks run/skipped, commit SHA, push/PR/merge, game patch and live-test status. A plan is not implementation; a green CI check is not playable-mod proof. Do not publish pre-alpha as a release.
