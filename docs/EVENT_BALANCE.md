# Event balance call stack — outdoor-social RCA

Machine owner: [`contracts/event-balance.v1.json`](../contracts/event-balance.v1.json).
Evaluator: `python -m scripts.event_balance` / `betterinstincts.event_balance`.

## Design brief

- **Subject:** Hosted lounge/party balance when Sims keep socializing outdoors.
- **Audience:** local host agent + operator mid-event.
- **Job:** durable RCA + priority call stack for survival needs, indoor routing, event goals, Fun-via-goals, and homework — not chat-only advice.
- **Upstreams:** `impeccable`, `UP-A85AD9DC3`, `UP-40FE662CF`.
- **Not:** a product dashboard or claimed Sims AI rewrite.

## LOCAL_OBSERVED symptom (2026-11-07)

LabLab hosted lounge party in rain: social interactions repeatedly walked Sims onto the outdoor sidewalk under an umbrella while indoor negative space remained free; event goals lagged; Fun/Energy pressed; homework still pending. Capture: `operator:event-outdoor-social-20261107`.

## Leading RCA

`H1_VENUE_OUTDOOR_MEETUP` — venue/event greeting routing prefers outdoor meetup/lot-edge points. Supporting: indoor capacity observed, rain, incomplete goals, still outdoor. Open: venue size / social-object tagging (`VENUE_SIZE_OR_TUNING_PROOF`).

## Call stack (high → low)

1. Player first / busy
2. Viewport OK
3. Survival needs critical (bladder / hunger / energy)
4. **Event indoor routing** — cancel outdoor social prefix when indoor capacity exists
5. Event goal progress (indoor)
6. Fun via event goals (do not leave party for fluff)
7. Homework hold until event ends (unless survival forces home)
8. Noncritical needs
9. Leisure / imperfect social OK

## Host action for outdoor default

`CANCEL_OUTDOOR_WALK_RETARGET_INDOOR` → click indoor Sim, Go Here indoors, or indoor social object. Forbidden: in-frame walk-thrash chasing guests outside.

## Proof ceiling

Host call-stack guidance and RCA only. Does not certify BI-002 hunger, rewrite EA autonomy, or close venue tuning without Studio evidence.
