# P141 -> P82 -> P07/P04: horizon choice and measured experiment

## Current evidence floor (2026-10-20)
BetterInstincts default branch began this sprint at `4e486d69ea81bf64e5f1d1ad75adf5ad48f71ba4`. Its four-need offline policy supports hunger, bladder, energy and hygiene, while BI-002 local Sims hunger experiment remains ACTIVE and game-unproven. Repo already enforces exact patch selection, rollback proof boundaries and immutable older certified configurations. No gameplay package is certified. P141 selects a strategic thesis only; **this independent P07 authorized execution sprint** owns implementation.

## P141 competing opportunities
| Thesis | Evidence and leverage | Falsifier | Disposition |
| --- | --- | --- | --- |
| A. A small common six-need decision contract before income | Existing policy misses standard adult Fun and Social; all successor goals depend on care | If six-need priorities cannot preserve overrides, abstention and fairness, discard approach | SURVIVES; SELECT |
| B. Start income immediately for player excitement | Income is explicitly requested | Unmet needs cause unacceptable interruption or income cannot be measured without game integration | DEFERRED behind six-need cross-balance |
| C. Build a global general-purpose AI/planner now | Might unify future modules | Complexity and runtime intrusion are unnecessary for the first tunings; original game and community tools already handle many behaviors | REJECTED |
| D. Build a broad test platform before needs code | Additional evidence useful | Previous bounded live-cert harness already exists; building more harness without a user-visible next behavior prolongs inaction | WEAKENED; only add focused tests |

**Selected question:** Can a small declarative six-need, eligible-action policy safely arbitrate all core adult motives while preserving leisure, player direction and deferred economic goals? Confidence **medium for offline feasibility; unknown for in-game suitability**. Route P82 for falsifiable offline choice. Actual Sims mechanics route to BI-002 P07 game-host sprint.

## P82 admission record
- **Hypothesis:** with the six-standard-motive catalog, urgent and preemptive remedies will take precedence; the scorer will return no suggestion when player-directed, busy, unsupported, or unable to remedy low needs; income is proposed only after a verified needs floor and skill practice only after observed income.
- **Baseline/comparator:** legacy `betterinstincts/priority.py` for old four needs; known missing Fun and Social mapping.
- **Bounded candidate:** `betterinstincts/horizon.py`, `contracts/needs.v1.json`; no game hooks, no persistence and no installed mods.
- **Measurement:** synthetic six-needs fixtures at urgent and preemptive levels, targeted player override/abstain tests and income/skill stage-gate cases; count failures deterministically with `python -m scripts.eval_horizon`.
- **Decision rule:** PROMOTE offline *research utility* only if all six needs receive correct actions in available-action test cases, no forbidden action is chosen, and all floor gates are respected; WEAKEN/REJECT otherwise. Any observed game thrashing or tuning mismatch can still reject the architecture despite offline PASS.
- **Fidelity/proof ceiling:** candidate can be offline-tested/merged without proving gameplay; no claim of Sims version compatibility or user enjoyment from synthetic output.
- **Implementation owner:** P07 repository sprint; P04 separates read-only strategy, conventional policy, validator/CI and local game lanes. P141 itself does not widen/implement.

## P82 decision and iteration ledger
Iteration 1: preserve working four-need `priority.py`; introduce explicit six-need candidate and test on standard adult motives. Critique: generic actions are *abstract candidates*, not verified Sims tuning IDs, so no production integration warranted. Decide: keep experiment narrowly offline and add explicit environment proof gates. After CI run, append actual exact-head test count and conclusion to `docs/LEDGER.md`; **until then validation is pending**.

## Next actual gate
The local agent completes the real hunger build/test first, then uses the same proven game/version-specific technique to investigate bladder, energy, hygiene, fun and social; cross-module balancing before live income; observed income before live skill automation. No other agent should independently invent that order.
