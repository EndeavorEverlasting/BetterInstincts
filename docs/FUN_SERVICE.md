# Fun service — parallel lanes under guest contention

Machine owner: [`contracts/fun-service.v1.json`](../contracts/fun-service.v1.json).
Evaluator: `python -m scripts.fun_service` / `betterinstincts.fun_service`.
Integrated by: `host_stack.evaluate_turn(..., guests_present=, occupied_objects=)`.

## Design brief (P95)

- **Subject:** Fun need recovery when vanilla autonomy under-serves Fun and guests contend for lot activities.
- **Audience:** local host agent mid-Live / mid-party.
- **Job:** Own Fun as an **independent service** with parallel activity lanes so Sims are not forced into one monolith queue that piles everyone onto the same TV/computer.
- **Architecture:** Each lane (`personal_portable`, `electronics_shared`, `creative_hobbies`, …) is its own service plan. Composed under `need_services` (`docs/NEED_SERVICES.md`) with peer hunger/bladder/energy/hygiene/social services via shared `need_service_base` (P124). `host_stack` gate is usually `NEED_SERVICES_TANDEM` with Fun nested — evaluate-only, no background daemon.
- **Upstreams:** `impeccable`, `UP-A85AD9DC3`, `UP-40FE662CF`.
- **Not:** EA tuning dump, vision OCR, or a Fun dashboard.

## LOCAL_OBSERVED gap (2026-11-07)

Sims do not manage Fun well on their own; with guests they queue behind each other and step on the same activities. Capture: `operator:fun-contention-guests-20261107`.

## Lane priority

Default: portable → playful-everyday → shared electronics → creative → social/physical → playful-exclusive → child/toddler.

**When guests / occupied objects:** portable and uncontended creative/playful first; shared TV/console demoted.

## Playful path

Everyday inducers (bubble bath, comedy channel, hilarious videos, comedy book) remain available without Playful. Exclusive actions (Scour for Memes, Play in Bath, Tickle the Ivories, Playful painting) require supplied PLAYFUL emotion/moodlet — fail closed otherwise.

## Proof ceiling

`HOST_FUN_LANE_CATALOG_NOT_EA_TUNING_API`. Live multi-Sim lane dispatch OPEN (`FUN_LANE_LIVE_DISPATCH`). Does not certify BI-002.
