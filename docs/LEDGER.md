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
