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
