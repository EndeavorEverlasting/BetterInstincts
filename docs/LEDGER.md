# Canonical project ledger

**Repository:** EndeavorEverlasting/BetterInstincts
**Owner objective (2026-10-20):** A creative, freely distributed contribution to The Sims 4 modding community that makes Sims autonomously meet needs responsibly, generate income, improve career outcomes, and pursue more fulfilling lives. Start with an observable small win while retaining the entire multi-month vision here. Prefer community-standard languages/tooling and patterns; avoid inventing new systems unnecessarily.

## Non-negotiable product behavior
1. Player agency outranks all autonomy suggestions.
2. Needs and safety outrank money/career efficiency; leisure and character remain meaningful.
3. Different Sims should not converge on one robotic optimization loop.
4. Behavior must be configurable, individually defeatable, reversible, and performant.
5. No save alteration, arbitrary user directories, telemetry, hidden background tasks, or mass changes.

## State and evidence ledger
| Item | State | Evidence / proof ceiling |
| --- | --- | --- |
| Repository | VERIFIED | New public GitHub repo with initial README, MIT and Python gitignore; `main` initial commit f6d129ef84f7a31beb5ec3f2610e1e39bd9aa749. |
| Tool ecosystem | RESEARCHED | See docs/PRIOR_ART.md; Python + XML tuning prevalent, but exact local game build not inspected. |
| Doctrine | MERGED TO MAIN | PR #1 merged as 308778a18c4349523fa99942c2e0e2818a27fd66; root AGENTS.md, validator, CI present on main. |
| Decision policy | OFFLINE PROTOTYPE + CI PASS | Pure Python scorer + synthetic tests only; NOT a game mod. PR #1 final head b15abd76317dd5e7a131a807b641736bfecf9297 passed 19 tests, doctrine check, tracked-asset scan and whitespace gate; [CI run](https://github.com/EndeavorEverlasting/BetterInstincts/actions/runs/39371028568). |
| Game integration | UNPROVEN | No tested `.package` or `.ts4script`, no game observation. |
| Live performance/compatibility | UNPROVEN | Requires local game and disposable saves. |
| Multiple-version resolver | IMPLEMENTED OFFLINE; NO CERTIFIED BUILDS | Exact patch+platform+module lookup with no latest fallback and byte-immutable older certified evidence guard in CI. Catalog empty by design. |
| Local game progress/evaluator | IMPLEMENTED OFFLINE; GAME PROOF UNPROVEN | Bounded CLI trial recorder; five vanilla/five modified + rollback gate and reviewer-only numerical verdict. Not a Sims API hook. |
| Public release | NOT AUTHORIZED | Requires docs/VALIDATION.md release gates. |

## Durable decisions (revise with evidence)
- First investigation: one observable base-game needs behavior (hunger) and its tuning/priority mechanism, not whole-game AI replacement.
- Alternative prioritization algorithms are hypotheses until live game comparison.
- Keep MIT for original code; third-party dependency license audits before any reuse.
- Honor community patterns: Sims 4 Studio for extraction/packaging research; consider XML Injector, Lot51 Core, S4CL only for justified integrations, not default dependencies.
- Use a single repo-local output root; require an explicitly provided, previewed install path for any future installer.

## Permanent operator correction (P00/P04/P97 — 2026-10-20)
**Serve several versions of The Sims 4.** When a new game build arrives, preserve code/configuration proven on older builds; do not reinterpret them or silently migrate to latest. Compare each build's tuning and certify the new profile independently. The **local game-capable agent owns completing BI-002's hunger experiment**, its actual package, gameplay trials, rollback, evaluation and proof; planning/handoff/CI-only work is explicitly insufficient. Agent progress must be machine-observable from repo-provided live-cert hooks. This decision persists in AGENTS.md, docs/DOCTRINE.md, docs/COMPATIBILITY.md, docs/LIVE_CERT.md and plans/active/BI-002.execution.v1.json.

## Project fact discipline
Mark CURRENT FACT, OBSERVED IMPLEMENTED, DOCUMENTED UNVERIFIED, INFERRED, EVIDENCE GAP. A third-party README doesn't prove a game runtime behavior. Document exact Sims patch + pack list for game tests. Preserve rejected choices here rather than reopening settled questions without new evidence.

## PR #3 version compatibility & game-cert harness closeout (2026-10-20)
**State: MERGED, OFFLINE VERIFIED, NOT GAME-CERTIFIED.** PR [#3](https://github.com/EndeavorEverlasting/BetterInstincts/pull/3) merged to `main` at `9550ef66315cfd77c4cbc5044e8c9bae49d8a3be`. [Post-merge CI run 39374046727](https://github.com/EndeavorEverlasting/BetterInstincts/actions/runs/39374046727) passed. Latest feature-branch suite: **46 unit tests**; doctrine, historical-profile preservation, no game-assets tracked, whitespace and source compile all green. Governance and code include exact-patch lookup, frozen older certified profiles/source commits, bounded live-cert recording/progress, read-only tuning auditing, Cursor guidance and code-owner routing. **No** real installed game version, authored hunger `.package`, recorded gameplay trial, human gameplay acceptance, or playable release was verified. Compatibility catalog intentionally contains zero certified builds. Local game experiment BI-002 remains ACTIVE and requires full proof. This proof ceiling is reflected in [machine-readable receipt](../artifacts/proof/BI-002-compat-bootstrap.v1.json).

## Long-horizon operator decision and P141/P82/P07/P04 delivery (2026-10-20)
**Permanent parent sequence:** stabilize **all six adult needs** (Hunger, Bladder, Energy, Hygiene, Fun, Social), then maintain their balance while autonomous work produces **observed recurring income**; only after income is underway develop **observed skills** without neglecting previous systems. Career progress is a successor, not a reason to move skills before income. See [HORIZON.md](HORIZON.md) and `plans/horizon.v1.json`, which owns the dependency ordering. The existing BI-002 hunger experiment remains the first game gate and must not be closed by this new offline work.

**Code added this sprint:** `betterinstincts/horizon.py` and `contracts/needs.v1.json` introduce an uncalibrated six-motive *offline* candidate. Explicit available actions, player command/busy guards, unsupported-life-stage abstention, proactive care and cooldowns prevent income/skill suggestions from preempting needs. Income needs an independently proven needs floor; skills additionally require actual observed income (the in-memory flags are not proof and must later be wired to real compatible runtime evidence). Old `priority.py` is preserved as comparison floor. `scripts/eval_horizon.py`, `scripts/check_horizon.py`, `scripts/horizon_status.py`, tests and CI expose machine-readable progress while preventing missing needs or reordered economic goals. The local execution plan for BI-003A–F lives in `plans/active/BI-003.execution.v1.json`; P04 lane disposition in `plans/active/BI-HORIZON.dispatch.v1.json`.

**Measured proof before integration:** feature branch CI [39456443205](https://github.com/EndeavorEverlasting/BetterInstincts/actions/runs/39456443205) returned SUCCESS with 64 offline tests, 12 checked horizon stages, 16 synthetic scorer cases, and clean doctrine/tracked-asset checks. New commits after that run require their own CI verification. **No actual Sims hunger package, in-game trial, income transaction or skill increment has been observed.** All gameplay phases remain UNPROVEN. The six-need 0.35/0.55 thresholds and abstract actions are experimental design values, not confirmed tuning IDs. P82 hypothesis and falsifiers recorded in [HORIZON_DECISIONS.md](HORIZON_DECISIONS.md).

## PR #5 horizon integration closeout (2026-10-20)
**MERGED TO MAIN:** [PR #5](https://github.com/EndeavorEverlasting/BetterInstincts/pull/5) at `1b5909aaedd31df42573b4a29f0badca1a8fef9a`. [Post-merge CI 39456997645](https://github.com/EndeavorEverlasting/BetterInstincts/actions/runs/39456997645) succeeded; last PR-head CI proved **65 Python tests**, 12 validated horizon stages, 16 deterministic synthetic scenarios, tracked-asset and governance checks. `docs/HORIZON.md` and `plans/horizon.v1.json` are canonical. `betterinstincts/horizon.py` is an **offline policy candidate**, not game-integrated; BI-002 hunger remains ACTIVE GAME UNPROVEN, and **none** of the later needs, income or skills have passed game trials. [Typed proof receipt](../artifacts/proof/BI-HORIZON-20261020.v1.json).

## Next parent gate
Execute [BI-002](../plans/active/BI-002.md): prove **one** reversible tuning-based, base-game hunger autonomy improvement against a vanilla comparison on a disposable save; if tuning cannot implement this, capture falsifying evidence and route the smallest justified script adapter. CI alone cannot close this gate.

## 2026-11-06 — BI-004 custom Mod Lab bootstrap
New additive read-only Mod Lab (docs/MOD_LAB.md; originally plans/active/BI-004.md, later renamed BI-MODLAB) inventories .package header metadata and .ts4script Zip module names under an explicitly selected Mods root. It does not parse package TGI keys, execute scripts, install mods, certify game patches, change files, or prove skill gains. The local-game BI-002 hunger gate and all earlier multiversion/horizon protections remain unchanged. The final PR/merge/CI proof and P04 local handoff must be appended only after provider verification.

## BI-004 provider integration / P04 continuity receipt — 2026-11-06
PR [#7](https://github.com/EndeavorEverlasting/BetterInstincts/pull/7) merged into main at `1686eac7be92c42ccbbabc16144d67248f630da3` after [PR-head CI](https://github.com/EndeavorEverlasting/BetterInstincts/actions/runs/42322823454) SUCCESS. [Post-merge CI](https://github.com/EndeavorEverlasting/BetterInstincts/actions/runs/42322858979) SUCCESS at the merged SHA. The canonical P04 continuation is now [BI-MODLAB.HANDOFF.md](../plans/active/BI-MODLAB.HANDOFF.md), guarded by `BI-MODLAB.dispatch.v1.json` (renamed from BI-004* so horizon income BI-004 stays unambiguous). Offline Mod Lab only; actual installed patch/game and BI-002 hunger trials remain unobserved. No live Sims result is implied.

## BI-004 follow-on — bounded DBPF TGI index (local trifecta) — 2026-11-06
Additive read-only `betterinstincts/dbpf.py` parses package header + resource index keys (Type/Group/Instance) under strict size/count/report budgets; payloads are never decompressed. Wired into Mod Lab inventory as `package_index` with an explicit INDEX_KEYS_ONLY proof ceiling. Synthetic fixtures cover constant-header compression, truncation fail-closed, and report budgets. Local Documents `GameVersion.txt` length-prefixed string observed as `1.121.361.1020` on this host — **LOCAL_OBSERVED only**, not a certified compatibility profile. Sims 4 Studio and a playable game install were not located under common Program Files paths; BI-002 remains ACTIVE / BLOCKED_LOCAL_GAME_ACCESS for gameplay. Real Mods scanning still requires an operator-selected absolute root and must not publish personal manifests.

## P141/P124 — Mod Lab identity + dbpf readability — 2026-11-06
P141 refresh in docs/STRATEGY.md selected **disambiguating Mod Lab from horizon BI-004 income** as the next offline contract (game hunger remains parent product gate but BLOCKED locally). Mod Lab plans/dispatch/handoff now use sprint id **BI-MODLAB**; horizon `BI-004` stays income-only. `horizon_status` emits `tooling_lane=BI-MODLAB` beside `income_gate=BI-004`. Collision regression lives in `tests/test_modlab_handoff.py`. P124 applied a behavior-preserving readability split in `betterinstincts/dbpf.py` without changing index semantics.


## 2026-11-06 — Game-host launch and disposable-save evidence lane (P08/P82/P07 → P04)

**Source integration: MERGED, SYNTHETIC CI VERIFIED.** PR #11 landed on main at c5fd5f16f78568050b3ba5aced9a525f85185c2c; candidate c196b2682cd9a39618d3d1605977878f954f8cea passed GitHub Actions run 42335351712, including game-host synthetic tests, backward compatibility, horizon, doctrine, tracked assets and compilation. The explicit Windows game host (scripts/game_host.py) can prepare a safe profile, dispatch selected Sims executable, request New Game/CAS or choose a screenshot-matched disposable Load Game slot, checkpoint clicks, confirm operator-reported Live Mode and ingest a one-shot sanitized external object-state snapshot. Read docs/GAME_HOST.md. A process request or PyAutoGUI click is not proof that a real save loaded; externally supplied JSONL is not a real in-game observer. Actual The Sims 4 launch, patch, disposable save, active Sim, gameplay change, hunger package, object-state producer and live CI/CD remain unobserved. No personal saves or Mods were touched by this provider runtime.

**Canonical P04 continuation:** plans/active/BI-GAME-HOST.HANDOFF.md with typed work/ownership machine map plans/active/BI-GAME-HOST.dispatch.v1.json. Parallel-ready local lanes GAME-BOOT and TUNING-READONLY need actual separately authorized Windows workers; no parallel local execution was observed. Existing BI-002 gameplay certification remains ACTIVE / BLOCKED_LOCAL_GAME_ACCESS until >=5 actual vanilla and >=5 actual modified trials, rollback and review. BI-MODLAB remains a tooling label; horizon BI-004 is income. Next gate is one verified disposable game session and true hunger baseline followed by a reversible package and comparative gameplay, not another offline prototype or release.
