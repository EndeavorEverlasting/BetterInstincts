# Scenario goals → Sims actions — P95 host catalog

Machine owner: [`contracts/scenario-goals.v1.json`](../contracts/scenario-goals.v1.json).
Evaluator: `python -m scripts.scenario_goals` / `betterinstincts.scenario_goals`.
Integrated by: `host_stack` when `SCENARIO_GOAL_PROGRESS` / `SCENARIO_CAREER_DEFERRED`.

## Design brief

- **Subject:** Scenario scoring HUD goals (Earn §250, Craft an Object, Get a career).
- **Audience:** local host agent + operator during scenario scoring runs.
- **Job:** Queue legitimate earn/craft interactions; defer career until horizon income proof; never motherlode for scenario scoring.
- **Upstreams:** `impeccable`, `UP-A85AD9DC3`, `UP-0F2FB5920`, `UP-40FE662CF`.
- **Not:** EA career/income API certification, BI-004 income closure, or cheat funding.

## LOCAL_OBSERVED gap (2026-11-07)

LabLab scenario scoring: HUD prioritized earn and craft before career; motherlode is not a scoring strategy. Capture: `operator:scoring-simoleons-20261107`.

## Horizon alignment

`needs recovery` → `earn_simoleons` → `craft_object` → `get_career` (`horizon_deferred` on career until `allow_career` + `needs_game_certified` + `income_game_observed`).

## Scoring profile priority

1. `earn_simoleons` — paint/sell, freelance gigs
2. `craft_object` — crafting station interactions
3. `get_career` — phone/PC find job (deferred by default)

Forbidden: `motherlode_for_scenario`, `reorder_horizon_to_career_first`.

## Call-stack role

```
supplied scenario goals + school_day flag + cert flags
  -> scenario_goals.evaluate_scenario_turn
  -> host_stack.next_gate (SCENARIO_GOAL_PROGRESS | SCENARIO_CAREER_DEFERRED)
```

School day active yields `SCHOOL_DAY_OUTRANKS_SCENARIO` in the scenario evaluator; `host_stack` still ranks school gates first.

## Proof ceiling

`HOST_SCENARIO_GOAL_CATALOG_NOT_EA_API_NOT_INCOME_OR_CAREER_CERT`. Live HUD goal ticks remain OPEN until operator confirmation.
