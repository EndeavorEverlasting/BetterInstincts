# Navigating Needs → host tandem — P95 call stack

Machine owner: [`contracts/navigating-needs.v1.json`](../contracts/navigating-needs.v1.json).
Evaluator: `python -m scripts.navigating_needs` / `betterinstincts.navigating_needs`.
Integrated by: `host_stack` when `NAVIGATING_NEEDS_TANDEM` (and build-mode yield).

## Design brief

- **Subject:** EA Discovery Quest **Navigating Needs** top-left Live panel (suggests need actions).
- **Audience:** local host agent + operator when the quest is active.
- **Job:** Work **in tandem** with the panel — prefer remedies that tick both the linked motive and the incomplete quest goal, ordered by motive urgency among the (up to three) visible goals.
- **Upstreams:** `impeccable`, `UP-A85AD9DC3`, `UP-0F2FB5920`, `UP-40FE662CF`.
- **Not:** A second Needs UI, vision OCR of the panel, EA API certification, or BI-002 hunger closure.

## Why tandem (not replace)

The panel already teaches the same six-need remedies BetterInstincts cares about (toilet, shower/bath, nap, cook/quick meal, read/TV, socialize). Host logic should **amplify** that surface: when hunger is critical and “Cook a Meal or Have a Quick Meal” is incomplete, queue fridge quick-meal/cook rather than inventing a parallel path that ignores the quest. Fall through to **need_services** (then instincts) when the **worst** urgent motive is not among the currently visible panel goals (e.g. bladder critical while only Fun/Social tips show). If the panel covers the worst urgent, stay in tandem even if other motives are also urgent.

Sibling Discovery Quest **Scoring Simoleons** stays under `docs/SCENARIO_GOALS.md` (income/craft/career). Do not merge those catalogs.

## LOCAL_OBSERVED gap (2026-11-07)

Operator called out the Navigating Needs top-left suggestions as the intuitive tandem surface for BetterInstincts. Same-day PrintWindow/desktop pass observed Bargain Bend **Build Mode** (panel not shown — Live Mode only). Goal list anchored to public Discovery Quest walkthrough + operator intent. Capture: `operator:navigating-needs-tandem-20261107`. Live HUD tick confirmation remains OPEN.

## P82 hypothesis

- **Hypothesis:** Panel-aligned urgency ordering + catalog interactions beat ignoring the panel or queuing unrelated Fun/Social fluff while Navigating Needs goals remain incomplete.
- **Falsifier:** Host invents goal labels, blocks uncovered urgent motives for non-visible goals, or clicks needs objects while Build/Buy is active.
- **Measure:** Contract load + plan/turn evaluators + `host_stack` gate + listener fields + `tests/test_navigating_needs.py`.

## Goal → linked need

| Panel goal | Linked need | Primary route |
| --- | --- | --- |
| Use a toilet | bladder | `USE_TOILET` |
| Cook a Meal or Have a Quick Meal | hunger | `QUICK_MEAL_OR_COOK` |
| Take a nap | energy | `TAKE_NAP` |
| Take a shower or bath | hygiene | `SHOWER_OR_BATH` |
| Read a book or watch TV | fun | `READ_OR_WATCH_TV` |
| Socialize with another Sim | social | `CHAT_WITH_SIM` |

## Call-stack role

```
supplied Navigating Needs goals + motives + build/school flags
  -> navigating_needs.evaluate_navigating_needs_turn
  -> host_stack.next_gate (NAVIGATING_NEEDS_TANDEM | BUILD_OR_BUY_YIELD)
  -> uncovered urgent -> need_services tandem / instincts / MAP_TRAVEL
```

School day and Build/Buy outrank tandem. Tandem outranks scenario scoring when both would otherwise compete.

## Proof ceiling

`HOST_NAVIGATING_NEEDS_TANDEM_CATALOG_NOT_EA_API_NOT_BI002_CERT`. Live panel ticks and BI-002 5+5 hunger certification remain OPEN.
