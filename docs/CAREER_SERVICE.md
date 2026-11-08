# Career service — async microsystem (P95)

**Prompt:** TokenCorridor P95 — Program Design & Call-Stack Prototype Architect  
**Provenance:** `spec-architecture-prompts.v1.json` blob `5926a198a14567de55110ed19e922fc444b4dec7`  
**Machine owner:** [`contracts/career-service.v1.json`](../contracts/career-service.v1.json)  
**Evaluator:** `betterinstincts.career_service` / `python -m scripts.career_service`  
**Lane note:** [`CAREER_PERFORMANCE.md`](CAREER_PERFORMANCE.md) (BI-006-adjacent scaffolding, not certification)

## Design brief

- **Subject:** Career-panel duties as a peer microsystem beside need services — starting with teen **High School Student** daily **homework**.
- **Audience:** local host agents that otherwise stay stuck in needs and forget schoolwork.
- **Job:** Keep a sticky `CAREER_OBLIGATION` alive across survival suspensions; evaluate every observation in tandem with `need_services`; resume homework policy only when survival is green and premises allow.
- **Architecture:** Thin continuity/orchestration seam over existing `teen_homework` / `school_day` / `scenario_goals` owners — not a second homework planner, not a daemon, not adult promotion proof.
- **Upstreams:** `impeccable`, `UP-A85AD9DC3`, `UP-40FE662CF`.
- **Not:** BI-006 GAME_CERTIFIED career advancement; inventing inventory; background scanners; overriding player queues.

## Why this exists

Need microsystems already load-balance in tandem. Career was only a cascade poll / one-shot host gate, so agents recovered hunger/energy and dropped the teen's daily homework. Ontology already requires `GOAL_THREAD` continuity across interruptions; this microsystem is that continuity for career-panel work.

## Microsystem states

| State | Meaning |
| --- | --- |
| `IDLE` | No career obligation attached |
| `TRACKING` | Obligation held; not yet actionable (queue/needs peers still busy) |
| `SUSPENDED_FOR_SURVIVAL` | Hunger/bladder/energy critical — hold obligation, do not queue homework |
| `PREMISES_BLOCKED` | At school / school day — hold obligation |
| `READY` | Survival green at home — resume teen_homework policy lanes |
| `YIELDED` | Player-first / busy — preserve tracking if already obligated |
| `COMPLETE` | Explicit `homework_pending=false` (book presence alone never reopens) |

## Success call stack (evaluate-only)

```
observation (+ optional prior career_service state)
  -> career_service.evaluate_career_service
       attaches high_school_student when teen homework/school signals present
       carries sticky obligation from prior_state when still pending
  -> delegates READY lanes to teen_homework (and school_day when active)
  -> host_stack surfaces career_service even when next_gate is survival/needs
  -> domain_cascade career receipt cites career_service
  -> host_tandem emits CAREER_OBLIGATION_HELD while needs/garden run;
       after survival recovers, CAREER_READY_HANDOFF before gardening resume
```

## Failure call stacks

| Failure | Host response |
| --- | --- |
| Survival critical | `SUSPENDED_FOR_SURVIVAL` + `obligation_held=true` |
| Premises / school day | `PREMISES_BLOCKED` + hold |
| Player directed / busy | `YIELDED`; do not authorize career clicks |
| homework_pending=false | `COMPLETE` / clear — never reopen from book metadata |
| Missing prior + no signals | `IDLE` |

## Module map

| Module | Responsibility | Side effects |
| --- | --- | --- |
| `career_service` | Sticky obligation, tandem state, compact receipt | none |
| `teen_homework` | Homework recovery / queue policy | none |
| `school_day` | In-school goal catalog | none |
| `host_stack` | Always expose attached career_service beside need_services | none |
| `domain_cascade` | Career domain polls via career_service | none |
| `host_tandem` | Async observe events + career handoff after needs | none |

## P82 admission

- **Hypothesis:** Sticky career obligation evaluated every tandem tick prevents agents from forgetting teen homework after survival preemption, without letting career outrank critical needs.
- **Baseline:** host_stack/domain_cascade call teen_homework only when that gate wins `next_gate`; suspended turns lose career visibility.
- **Falsifier:** Dropping `obligation_held` while `homework_pending=true`; queuing homework under survival-critical needs; reopening completed homework from book tokens alone.
- **Measure:** `tests/test_career_service.py` + host_tandem career continuity cases.

## Proof ceiling

`HOST_CAREER_MICROSYSTEM_TANDEM_NOT_DAEMON_NOT_BI006_CERT`. Live homework completion remains OPEN (P08). Does not close BI-002 or BI-006.
