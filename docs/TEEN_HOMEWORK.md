# Teen homework — daily High School Student performance — P95 host catalog

Machine owner: [`contracts/teen-homework.v1.json`](../contracts/teen-homework.v1.json).
Evaluator: `python -m scripts.teen_homework` / `betterinstincts.teen_homework`.
Integrated by: `host_stack` when teen homework gates apply at home.

See also: [`docs/CAREER_PERFORMANCE.md`](CAREER_PERFORMANCE.md) for BI-006 lane scope (not certification).

## Design brief

- **Subject:** Teen **High School Student** career-panel daily task = homework (career-performance budgeting).
- **Audience:** local host agent + operator when the teen is home with homework due.
- **Job:** Survival outranks homework; school premises still block homework; missing inventory triggers a recovery ladder without skipping the career task.
- **Upstreams:** `impeccable`, `UP-A85AD9DC3`, `UP-0F2FB5920`, `UP-40FE662CF`.
- **Not:** adult **Get a career** scenario routing, EA API certification, vision-invented inventory, or BI-006 promotion closure.

## LOCAL_OBSERVED (2026-11-07)

Wed night at home: homework **not in inventory** but on the **dining-table lot surface**; operator lot-scanned, **Put in Inventory**, then could queue do-homework; hunger critical; energy low; queue **Use Toilet** + **Take a Shower**; computer desk on lot. Capture: `operator:teen-homework-missing-20261107`.

**Operator correction:** empty inventory ≠ absent from lot. Host must scan lot surfaces and put the book in inventory before computer recovery.

## Recovery ladder (`inventory_has_homework=false`)

1. `LOT_SCAN_PUT_HOMEWORK_IN_INVENTORY` — scan dining table / desk / counters / floor → click homework → **Put in Inventory** (skipped only when `homework_on_lot=false`)
2. `COMPUTER_SCHOOL_DO_HOMEWORK` — Computer → School → Do Homework
3. `COMPUTER_PURCHASE_SCHOOL_BOOKS`
4. `PHONE_SCHOOL_ASK_HOMEWORK`
5. `DESK_WORK_ON_HOMEWORK` (if book present)

Listener observation fields: `inventory_has_homework`, `homework_on_lot`, `available_objects` (tokens like `homework`).

## Call-stack gates

| Gate | When |
| --- | --- |
| `SURVIVAL_BEFORE_HOMEWORK` | hunger / bladder / energy &lt; 0.35 |
| `HOMEWORK_PREMISES_BLOCKED` | school lot or `school_day_active` |
| `HOMEWORK_AFTER_NEEDS_QUEUE` | needs queue active, survival green |
| `HOMEWORK_INVENTORY_MISSING` | home, homework pending, inventory=false |
| `QUEUE_TEEN_HOMEWORK` | home, inventory=true |

## Proof ceiling

`HOST_TEEN_HOMEWORK_CATALOG_NOT_EA_API_NOT_BI006_CERT`. Does not close BI-002 or certify BI-006 career promotions.

## 2026-11-09 — P00 / P01 / P141 / P95 / Trifecta: queue-aware seated study

**Observed failure:** An agent blindly chose `Do Homework` while the Sim was on a sidewalk, and attempted to stack actions without knowing the effective queue limit. The right correction is an admission rule in the existing planner, not another agent daemon.

The player-reported capacity bands are **heuristics**, not certified universal Sims limits: **2–3** items while the Sim is multitasking, **6–7** otherwise. `betterinstincts/queue_capacity.py` admits at most the conservative low end (**2 / 6**) with fresh observed queue length. Unknown multitasking, a full queue or player-directed actions yield **zero new enqueues**. Reobserve after each successful or rejected enqueue; avoid duplicate homework. This is advice, never SendInput authorization.

Before suggesting homework, the host reuses the already-bounded **`house_state` → `room_census`** projection. It ranks attested indoor rooms with a desk/table **and an observed seat**, preferring a desk/office zone to a dining table. Outdoor, unknown, unverified, chairless, or absent lot observations trigger `HOMEWORK_STUDY_SCAN_REQUIRED`. Once a room candidate is found, `PREPARE_STUDY_LOCATION` offers a relocation/seat plan **without queuing homework**. Only a subsequent observation that the Sim is in that exact room **and seated on that exact observed chair**, with a queue slot available and homework not already queued, returns `QUEUE_TEEN_HOMEWORK`.

Focused emotion and Study Spot lot trait are used only as **explicitly observed cues**. A mood aura, faster homework rate, seat availability, travel path, or emotion change is never invented. A proposed seat must be revalidated against the current model revision and live scene before any game input. The existing school-premises, player-direction, and survival gates outrank homework.

Host observation keys: `lot_model` (revisioned model), `multitasking` (boolean or unknown), `sim_room_id`, `sim_seated`, `sim_seat_id`, `lot_traits`, plus existing `emotion`, `queue`, homework and player-status fields. Study/queue reports are read-only and do not grant a control permit.

P141's selected seam was **reuse the room census and teen homework gate**. The rejected approaches were a parallel scheduler and blind desk clicker. P95 prototyped the positive and missing-observation paths. P82 tests the two capacity bands, absent/outdoor/unverified/seatless spaces, duplicate homework, and independent seat attestation. P07 integrates through `host_stack` and opt-in `host_listener`; P08's real Sims game-lab proof is still **OPEN**. BI-002 hunger remains independently ACTIVE until its own live certification.

Consultation before behavior changes: `contracts/consultations/BI-QUEUE-STUDY-P95-20261109.v1.json`. Regression suite: `python -m unittest tests.test_queue_study tests.test_teen_homework -v`.
