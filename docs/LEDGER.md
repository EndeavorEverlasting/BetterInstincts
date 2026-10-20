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

## Next parent gate
Execute [BI-002](../plans/active/BI-002.md): prove **one** reversible tuning-based, base-game hunger autonomy improvement against a vanilla comparison on a disposable save; if tuning cannot implement this, capture falsifying evidence and route the smallest justified script adapter. CI alone cannot close this gate.
