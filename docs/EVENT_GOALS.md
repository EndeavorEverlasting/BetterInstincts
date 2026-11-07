# Event goals → Sims actions — P95 host catalog

Machine owner: [`contracts/event-goals.v1.json`](../contracts/event-goals.v1.json).
Evaluator: `python -m scripts.event_goals` / `betterinstincts.event_goals`.
Integrated by: `event_balance` + `host_stack` when `EVENT_GOAL_PROGRESS` / `EVENT_FUN_VIA_GOALS`.

## Design brief

- **Subject:** Incomplete social-event HUD goals and the pie-menu actions that satisfy them.
- **Audience:** local host agent + operator mid-party.
- **Job:** Fully encompass goal→action mapping so the host queues the right indoor interactions instead of leaving operators to hunt the pie menu.
- **Upstreams:** `impeccable`, `UP-A85AD9DC3`, `UP-40FE662CF`.
- **Not:** an EA tuning dump, vision OCR of the goal panel, or a product dashboard.

## LOCAL_OBSERVED gap (2026-11-07)

LabLab lounge party: goals lagged while outdoor socials burned the timer. Operator report — discovering which interactions actually satisfy event goals was difficult. Capture: `operator:event-outdoor-social-20261107`.

## Lounge-party priority

1. `drink` — bar/cooler Get/Order Drink
2. `be_silly` — Funny/Friendly Be Silly (indoor)
3. `tell_jokes` — Tell a Joke / Funny Story
4. `friendly_socialize` — Sit and Chat Here / Get to Know / indoor Friendly greet
5. `talk_about_food` — Talk about Food

Generic outdoor greet and unscoped Chat are **non-satisfying** for specific goals.

## Host plan shape

For incomplete goals, the evaluator returns:

- normalized goal ids
- next goal by profile priority
- concrete `satisfying_interactions` with steps
- queue match: which queued labels already cover a goal
- findings when the queue does not advance any incomplete goal

## Proof ceiling

`HOST_GOAL_ACTION_CATALOG_NOT_EA_TUNING_API`. Interaction ticks remain OPEN until live HUD confirmation (`GOAL_TICK_LIVE_CONFIRMATION`). Does not certify BI-002.
