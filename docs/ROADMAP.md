# Roadmap — preserve the whole BetterInstincts vision

A module is not completed merely because a spec exists. Each reaches: designed -> offline-tested -> built -> disposable-save integrated -> patch/compatibility tested -> publicly released. Each game update may invalidate later statuses.

## Milestones
| Milestone | Intended experience | Earliest proof gate | Dependencies |
| --- | --- | --- | --- |
| **BI-001 foundation (merged 2026-10-20)** | Doctrine, ownership, prior-art decisions, offline policy scenario baseline, CI | Validator + offline unit tests, PR review | None |
| **BI-002 needs/hunger** | Sims seek available food before dangerously low hunger without abandoning direct player commands | Vanilla A/B disposable-save trial with one reversible package | Game patch/tooling evidence, BI-001 |
| **BI-003 needs expansion** | Sensible bladder, hygiene, sleep, meal decisions; no wasteful repeated activity | Need-specific package trials and conflict matrix | BI-002 |
| **BI-004 earning income** | Appropriate autonomous income-generating actions when safe and available | Goal-sensitive decisions, payment confirmation, no duplication or endless queues | Relevant in-game actions and schedule rules |
| **BI-005 careers** | Prep, skill building, work attendance, promotion tasks and career progress | Career-specific A/B gameplay incl. no-career and work-from-home cases | BI-004 and pack auditing |
| **BI-006 household cooperation** | Sims distribute chores and care tasks without conflict/starvation | Multi-Sim trials, housemate fairness | Needs modules |
| **BI-007 personalities & settings** | Traits, moods, relationships, leisure, autonomy strength/overrides | Diverse-playstyle fixtures; user-visible settings and disabling | Stable tuning/API integration |
| **BI-008 compatibility & distribution** | Opt-in modules; clean upgrade/removal; reliable updates | Pack/version/mod-conflict matrix and release checklist | Observed gameplay stability |

## All versions retention invariant
Each module must maintain a matrix of exact certified Sims builds/platforms, with the older validated configs frozen. New patch -> new candidate and targeted tuning diff; no blanket migration. BI-002 must produce actual game evidence before its first profile can be certified. Read docs/COMPATIBILITY.md and docs/LIVE_CERT.md; repeated regression checks apply to all subsequent milestones.

## Product settings candidates (NOT IMPLEMENTED)
Global mode: Off / Balanced / Proactive; independent Needs, Income, Career, Chores, Social, and Hobbies toggles; player-order protection mandatory. Design settings for one real mechanism before creating an elaborate UI. Document defaults, migration, pack requirements and per-Sim scope when supported.

## Critical safeguards
Always preserve fun, autonomy boundaries, performance, and save safety. All milestones need baseline comparators and rollback steps. Requirements can be revised by user/community trials, with corrections written to docs/LEDGER.md.
