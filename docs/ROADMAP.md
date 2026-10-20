# BetterInstincts roadmap — no trajectory rediscovery

**Sequence accepted 2026-10-20:** six adult needs -> balance -> steady income with needs maintained -> skills with income and needs maintained -> career advancement. Throughout, preserve player choice, fun, and older certified game versions. Canonical execution graph: [plans/horizon.v1.json](../plans/horizon.v1.json). Human/readable owner: [HORIZON.md](HORIZON.md).

| Stage | Required result | Local game proof |
| --- | --- | --- |
| BI-001 (MERGED) | Doctrine, version retention, CI and offline hunger prototype | None claimed |
| BI-002 (ACTIVE) | Hunger tuning and disposable-save trials | Authored reversible package, >=5 vanilla + >=5 modified trials, rollback, maintainer review |
| BI-003A | Bladder behavior | Patch-specific autonomy experiment and safety |
| BI-003B | Energy and sleep | Appropriate time, no exhaustion, no forced interruption |
| BI-003C | Hygiene | Need-based behavior without obsessive repetition |
| BI-003D | Fun | Respects personal preferences and balances other obligations |
| BI-003E | Social | Mood/personality-sensitive socializing with no unwanted control |
| BI-003F | Six-needs joint balance | Combined A/B trials; no thrash or neglected need; verified no-command-interruption |
| BI-004 | Recurring income | Observed money delta per valid action, no fake earnings, no work loop |
| BI-005 | Purposeful skill growth | Actual skill progress and time budget; income + needs remain stable |
| BI-006 | Career growth | Attendance, requirements, promotions, work-from-home edge cases |
| BI-007 | Household cooperation, traits, user settings | Multi-Sim fairness, character diversity, opt-outs |
| BI-008 (CONTINUOUS) | Patch compatibility, performance, release quality | Previously proven profiles remain immutable; new patch individually certified |

**Dependency rule:** No downstream *live completion* merely because its offline prototype passes. A local game-capable agent finishes the entire BI-002 hunger experiment. Once BI-002 is certified, BI-003A-E may proceed in parallel only with verified separate tuning/resources and writers. BI-003F gates BI-004; BI-004 gates BI-005; BI-005 gates BI-006. BI-008 accompanies every stage. Machine validator `python -m scripts.check_horizon`.

**Development floor:** `betterinstincts/priority.py` remains a stable four-need comparator. `betterinstincts/horizon.py` is the separate synthetic six-need policy candidate. `contracts/needs.v1.json` uses uncalibrated hypotheses and abstract action IDs; test results do not prove gameplay or compatibility. No globally running agent, camera, watcher, or data collection is authorized.

**Patch/version rule:** Exact version+platform+module, retain immutable certified profiles, no guessed fallback. New build -> new trial and profile, never silently replace old configuration. Parent rationale in [LEDGER.md](LEDGER.md).

If game access is missing, preserve the blocked gate; continue safe conventional repo development and validators without reassigning local physical game proof to ChatGPT provider tools.
