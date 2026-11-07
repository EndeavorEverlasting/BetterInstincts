# Teen day journey — P95 host call-stack (2026-11-07 LabLab)

Canonical continuity for the operator journey that produced school-day goals, teen homework career-performance, lot-scan inventory recovery, school-presence awareness, and classmate invite occult safety. Machine owners remain the per-domain contracts below; this document is the **journey spine**, not a competing authority.

## Journey (LOCAL_OBSERVED order)

1. **School-day HUD** — top-left High School Years goals; premises block homework on school lot (`docs/SCHOOL_DAY.md`).
2. **Scenario Scoring Simoleons** — gift-box goals; career deferred (`docs/SCENARIO_GOALS.md`).
3. **Teen homework missing from inventory** — career-panel daily task; book on dining table / lot surface; operator put in inventory after lot scan (`docs/TEEN_HOMEWORK.md`, `docs/CAREER_PERFORMANCE.md`).
4. **Survival first** — hunger/bladder/energy and queued toilet/shower outrank homework.
5. **Camera ≠ Sim premises** — viewport may show home while portrait school icon / schedule says teen is at school; `sim_at_school` / resolved premises drive gates.
6. **After school** — homework now in inventory; performance still improvable.
7. **Social invite** — “Should Charlee invite over classmate Morgan?” OK/Cancel. Occult/vampire status must be resolved by **unique Sims-library lookup** before OK; unknown/ambiguous → Cancel (`docs/SOCIAL_OPPORTUNITY.md`).

## Call-stack (highest first)

```
player_first / busy
  → survival critical (hunger|bladder|energy)
  → social invite prompt (Sims-library occult lookup → OK only if unique + known-safe)
  → school premises / school_day_active (defer homework; school goals)
  → needs queue (toilet/shower/eat) before homework
  → homework inventory missing → lot-scan Put in Inventory → else computer ladder
  → queue teen homework when inventory has book at home
  → scenario goals (earn/craft; career deferred)
  → leisure
```

## Invariants preserved

- Player first; no uncontrolled autonomy loops.
- Never invent inventory, lot contents, or occult status from looks/name vibe.
- Empty inventory ≠ absent from lot (lot-scan first).
- School premises / `sim_at_school` block home-homework recovery and invite-home thrash.
- Unknown occult or non-unique library match → Cancel/Abstain (fail closed).
- Does not close BI-002 or certify BI-006.

## Captures

| Capture | Meaning |
| --- | --- |
| `operator:school-day-goals-20261107` | School goals + premises-blocked homework |
| `operator:scoring-simoleons-20261107` | Scenario gift-box |
| `operator:teen-homework-missing-20261107` | Inventory empty; lot surface book; lot-scan put-in-inventory |
| `operator:invite-morgan-occult-unknown-20261107` | Morgan invite; occult UNKNOWN until library lookup |

## Proof ceiling

Host catalogs + supplied observations. Live OK on Morgan invite remains **UNPROVEN** until unique Sims-library occult evidence is supplied and gate allows OK.
