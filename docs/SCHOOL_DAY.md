# School-day goals → Sims actions — P95 host catalog

Machine owner: [`contracts/school-day.v1.json`](../contracts/school-day.v1.json).
Evaluator: `python -m scripts.school_day` / `betterinstincts.school_day`.
Integrated by: `host_stack` when `SCHOOL_DAY_GOAL_PROGRESS` / `HOMEWORK_PREMISES_BLOCKED`.

## Design brief

- **Subject:** High School Years top-left school goals and premises-blocked homework.
- **Audience:** local host agent + operator on the school lot (morning free time).
- **Job:** Fully encompass goal→action mapping so the host queues Study for Exams and related goals instead of athletic fluff when Not Stumble is pinned; defer homework when the career panel forbids on-premises work.
- **Upstreams:** `impeccable`, `UP-A85AD9DC3`, `UP-0F2FB5920`, `UP-40FE662CF`.
- **Not:** EA career/school API certification, vision OCR of the goal panel, or BI-005 skill practice.

## LOCAL_OBSERVED gap (2026-11-07)

LabLab High School Years morning free time: school goals in the top-left were difficult to advance while homework could not be done on school premises; Clumsy **Not Stumble** favored sedentary study. Capture: `operator:school-day-goals-20261107`.

**Premises rule:** `location_kind` / `sim_at_school` is the **active Sim's premises**, not the camera lot. A home viewport while the portrait shows the school icon must not trigger home homework lot-scan. See `resolve_sim_premises` and journey spine `docs/TEEN_DAY_JOURNEY.md`.

## P82 hypothesis

- **Hypothesis:** A versioned school-day goal catalog plus phase-aware homework blocking routes the host to sedentary `Study for Exams` steps before premises-blocked homework and before generic lot fluff, when survival needs are green.
- **Falsifier:** Host queues homework on school lot during `morning_free_time`, ignores incomplete school goals with green survival, or invents goal labels without operator supply.
- **Measure:** Contract load + plan/turn evaluators + `host_stack` gate attachment + doctrine paths + unit tests in `tests/test_school_day.py`.

## High School Years priority

1. `study_for_exams` — High School pie → Study for Exams (desk/sedentary)
2. `attend_class` — class schedule / classroom
3. `participate` — in-class participation
4. `socialize_at_school` — indoor classmate social

Athletic queue items and on-premises homework are **non-satisfying** during blocked phases.

## Call-stack role

```
supplied school goals + phase + location + whims
  -> school_day.evaluate_school_day_turn
  -> host_stack.next_gate (SCHOOL_DAY_GOAL_PROGRESS | HOMEWORK_PREMISES_BLOCKED)
```

## Proof ceiling

`HOST_SCHOOL_DAY_GOAL_CATALOG_NOT_EA_TUNING_API_NOT_CAREER_CERT`. Live HUD goal ticks remain OPEN until operator confirmation. Does not certify BI-002 or school career progression.
