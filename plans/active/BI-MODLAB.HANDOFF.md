# P04 canonical handoff — BetterInstincts BI-MODLAB

**Canonical re-entry:** AGENTS.md → docs/DOCTRINE.md / docs/LEDGER.md → docs/MOD_LAB.md → plans/active/BI-MODLAB.md → this handoff. Machine contract: plans/active/BI-MODLAB.dispatch.v1.json. One repository, one writer per branch; do not invent extra local clones or a second authoritative handoff.

**Lane label:** `BI-MODLAB` is tooling only. Horizon stage **BI-004** means recurring income (`plans/horizon.v1.json`, docs/ROADMAP.md). Never close income or hunger because Mod Lab tests passed.

## CHANGED | PROVED | NEXT

**CHANGED:** PR [#7](https://github.com/EndeavorEverlasting/BetterInstincts/pull/7) implemented an explicit-root, read-only Python Mod Lab inventory; PR [#8](https://github.com/EndeavorEverlasting/BetterInstincts/pull/8) published the P04 handoff; PR [#9](https://github.com/EndeavorEverlasting/BetterInstincts/pull/9) added bounded DBPF TGI index reading. Sprint identity was later disambiguated from horizon BI-004 income via the P141 refresh in docs/STRATEGY.md.

**PROVED:** Offline Mod Lab + DBPF synthetic tests and repository CI on the merged heads. Provider receipts for #7/#8/#9 remain historical evidence; this file owns current re-entry paths.

**NEXT parent game gate:** BI-002 remains ACTIVE and BLOCKED_LOCAL_GAME_ACCESS until a game-capable host completes hunger trials. Do not close BI-002 with the Mod Lab scanner or synthetic tests. Six adult needs → balance → observed income (horizon BI-004) → skills → careers remains the protected horizon.

## Launch order for the local agent

1. Re-enter the existing canonical BetterInstincts checkout; run `git fetch --all --prune`, `git status --short`, `git branch --show-current`, `git rev-parse HEAD`. Check live PRs and avoid overwriting local dirty files. The canonical local path and actual game installation **have not been independently observed**; do not guess them.
2. Read root AGENTS.md, docs/LEDGER.md, docs/DOCTRINE.md, docs/COMPATIBILITY.md, docs/LIVE_CERT.md, docs/MOD_LAB.md, docs/STRATEGY.md, plans/active/BI-002.execution.v1.json, plans/active/BI-MODLAB.md, and plans/active/BI-MODLAB.dispatch.v1.json.
3. Run `python -m unittest discover -s tests -v`, `python -m scripts.check_horizon`, `python scripts/validate_doctrine.py`, `python scripts/check_tracked_assets.py`, `python -m scripts.horizon_status`. Keep older certified patch profiles byte-immutable; check full version, platform and feature module.
4. On a disposable synthetic directory named Mods, run `python -m scripts.modlab --mods-root "<EXPLICIT_PATH_TO_Mods>"`; inspect JSON, errors and overlap candidates. Scan a real Mods directory only once explicitly selected by the operator, read-only. Do not upload a raw personal mod manifest to public GitHub.
5. Investigate concrete Sims 4 Studio exported XML for hunger/autonomy and later skill/statistic behavior: `python -m scripts.tuning_audit --xml "<EXPLICIT_EXPORTED_XML>"`. Record exact game patch, packs, observed tuning resource IDs and relevant hypotheses privately; never include EA XML in Git. No script hook or API names are certified by module inventory alone.
6. For gameplay only, execute BI-002 using the game-capable local agent: disposable save; at least five repeatable vanilla and five modified hunger trials; player-order safety, loop/errors/performance, package hash, safe removal and rollback; maintainer review. When no local game exists, mark BLOCKED_LOCAL_GAME_ACCESS and continue independent read-only resource-index research.

## Runtime partition / ownership

| Lane | HOST | Provider / capability | Ownership and proof ceiling |
| --- | --- | --- | --- |
| Mod Lab source + offline tests | CURRENT_CHAT_RUNTIME (initial) / LOCAL_AGENT_RUNTIME (future) | GitHub checkout, Python | Source, metadata inventory, synthetic tests only; one writer |
| Regression suite | CI_OR_REMOTE_RUNNER | GitHub Actions | CI status; no real mod runtime or game observations |
| Real Mods directory and skill-tuning research | LOCAL_AGENT_RUNTIME | Explicit operator-selected root, Sims 4 Studio | Version-specific read-only inventory, tuning IDs only when observed |
| Gameplay validation | LOCAL_AGENT_RUNTIME + OPERATOR_OR_PHYSICAL_RUNTIME | Sims 4, disposable save | BI-002 evidence, package and rollback; must not be forged |

## Known boundaries and rejection reasons

- The manager is not a decompiler or a memory patcher. It reads `.package` DBPF magic plus a bounded TGI index, and `.ts4script` central-directory module names. No active import, tuning override detection, installed API adapter, patch validity, skill-gain hook, or actual Sim decision exists in this lane.
- Never execute a discovered `.ts4script`, extract a foreign archive, move files belonging to other mods, auto-detect user folders, scan saves, or modify existing certified patch data. No telemetry, scheduled processes, background jobs or external downloads.
- Next optional code slice: compare a synthetic-validated TGI listing against the same real package opened in Sims 4 Studio; keep cross-package resource-overlap analysis additive and non-accusatory. Not every shared TGI or module name is an error.
- Lot51 Core, Sims 4 Community Library and XML Injector remain possible future community API seams, not newly installed dependencies. Favor game tuning for the first hunger experiment. Keep the game runtime Python separate from developer Python and record license/version evidence before adapting code.
- Preserve both work lines: **BI-MODLAB** can improve diagnostic tooling without replacing BI-002 as the first playable autonomy proof, and without consuming horizon **BI-004** (income).

## Exact first command

`python -m unittest discover -s tests -v`

Then follow the Mods-root and game-specific gates above. Report CHANGED | PROVED | NEXT with independent source, committed, merged, CI and live-game states.
