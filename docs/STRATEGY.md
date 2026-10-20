# P141 — strategic opportunity scout (2026-10-20)

## Current facts
Repo initially had no product implementation beyond three initialization files. Community prior art shows an existing ecosystem of targeted XML tuning, modular packages, and Python-based library hooks; see docs/PRIOR_ART.md. Current actual game patch, vanilla tuning and gameplay measurements are absent.

## Competing theses, falsification, and dispositions
| Thesis | Pull / leverage | Cheapest disproof | Result |
| --- | --- | --- | --- |
| A. Start with narrow urgent-need improvement and reproducible vanilla comparison | Direct value, low conceptual scope, immediate compatibility learning | Vanilla already reliably handles chosen urgency or game tuning cannot alter it safely | **SURVIVES**; preferred next investigation |
| B. Start with career/income decision automation | Matches multi-month vision, potentially differentiating | Requires events, UI/work hours, pack behaviors, durable intent interpretation not yet learned | **DEFERRED** until baseline hook understood |
| C. Replace autonomy AI with a full scheduling/utility framework now | Largest potential future scope | External tuning/needs mods already solve many slices with less collision | **REJECTED** as premature architecture |
| D. Build only a telemetry/testing harness before touching behavior | Great regression leverage | Would postpone observable player improvement; synthetic test suite alone misses actual Sims behavior | **WEAKENED**; pair light evidence harness with A instead |

## Strategic choice
**A: reversible, observable hunger tuning experiment, with lightweight measurement.** Confidence MEDIUM: external precedent strong but unproven against the operator's live game build. Counterfactual: if first vanilla baseline meets needs or tuning is insufficient, select another user-visible need or script adapter using recorded falsification, not broad architecture by default.

## Cheapest discriminating investigation
On a disposable save, record a precise baseline in a controlled household. Extract vanilla hunger-related tuning using Sims 4 Studio and identify one real score/modifier seam. Implement a standalone reversible package (no bundled game content); test with and without it under the same conditions. Metrics: hunger recovery before critical state, player-order interruption count (target zero), unrelated action spam (target zero), household playability, log errors, relative frame/simulation responsiveness. Compare with base-game and optionally high-signal conflicting mods in separate runs.

**Route:** P97 prior-art inspection is recorded; the next game-bound action is a P07-sized bounded implementation with human/local-game proof. This scout does not assert a built mod or promote its own recommendation to observed success.
