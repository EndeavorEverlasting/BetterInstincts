# Event balance call stack — outdoor-social RCA

Machine owner: [`contracts/event-balance.v1.json`](../contracts/event-balance.v1.json).
Evaluator: `python -m scripts.event_balance` / `betterinstincts.event_balance`.

## Design brief (P95)

- **Subject:** Hosted lounge/party balance when Sims keep socializing outdoors.
- **Audience:** local host agent + operator mid-event.
- **Job:** durable RCA + priority call stack for survival needs, indoor routing, event goals, Fun-via-goals, and homework — not chat-only advice.
- **Primary indoor fix:** **Sit and Chat Here** on an indoor seat grounds the conversation so pathing cannot re-resolve to the outdoor meetup.
- **Upstreams:** `impeccable`, `UP-A85AD9DC3`, `UP-40FE662CF`.
- **Not:** a product dashboard or claimed Sims AI rewrite.

## LOCAL_OBSERVED symptom (2026-11-07)

LabLab hosted lounge party in rain: social interactions repeatedly walked Sims onto the outdoor sidewalk under an umbrella while indoor negative space remained free; event goals lagged; Fun/Energy pressed; homework still pending. Operator: **Sit and Chat Here** was available on indoor seating and would have grounded chat indoors. Capture: `operator:event-outdoor-social-20261107`.

## Leading RCA

1. `H1_VENUE_OUTDOOR_MEETUP` — venue/event greeting routing prefers outdoor meetup/lot-edge points.
2. `H9_GREET_WITHOUT_SEAT_GROUNDING` — greet / Go Here / click-Sim without seat grounding still exits outdoors.

Open: venue size / social-object tagging (`VENUE_SIZE_OR_TUNING_PROOF`); live pie-menu dispatch (`SIT_AND_CHAT_HERE_LIVE_DISPATCH`).

## Call stack (high → low)

1. Player first / busy
2. Viewport OK
3. Survival needs critical (bladder / hunger / energy)
4. **Event indoor routing** — cancel outdoor social; ground with Sit and Chat Here
5. Event goal progress (indoor) — see [`EVENT_GOALS.md`](EVENT_GOALS.md) for drink / be silly / jokes / socialize / food-talk actions
6. Fun via event goals (do not leave party for fluff)
7. Homework hold until event ends (unless survival forces home)
8. Noncritical needs
9. Leisure / imperfect social OK

## Host action for outdoor default

`CANCEL_OUTDOOR_WALK_SIT_AND_CHAT_HERE` → **primary** `SIT_AND_CHAT_HERE_INDOOR` (indoor sofa/chair/bench pie menu). Fallbacks: indoor social object sit-then-chat, already-indoor Sim click, weak Go Here. Forbidden: outdoor greet spam, Go Here that re-routes outdoors, in-frame walk-thrash chasing guests outside.

## Proof ceiling

Host call-stack guidance and RCA only. Does not certify BI-002 hunger, rewrite EA autonomy, or close venue tuning without Studio evidence. Sit-and-Chat SendInput remains OPEN until live pie-menu proof.
