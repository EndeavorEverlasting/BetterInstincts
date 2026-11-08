# Balance service — async microsystem (P95)

**Prompt:** TokenCorridor P95 — Program Design & Call-Stack Prototype Architect
**Provenance:** `spec-architecture-prompts.v1.json` blob `5926a198a14567de55110ed19e922fc444b4dec7`
**Machine owner:** [`contracts/balance-service.v1.json`](../contracts/balance-service.v1.json)
**Evaluator:** `betterinstincts.balance_service` / `python -m scripts.balance_service`
**P124:** Reuses `survival_critical`, moodlets emotion family, and gardening plant-care peers — no second scorer or daemon.

## Design brief

- **Subject:** Enchanted by Nature **Balance / Imbalance** meter and physical ailments as a peer microsystem beside needs, career, aspiration, and gardening.
- **Audience:** local host agents that otherwise ignore prolonged negative-mood imbalance while needs dominate.
- **Job:** Keep a sticky `BALANCE_CONDITION` alive across survival suspensions; evaluate every observation in tandem with `need_services`; prefer nature engagement + positive moods when Imbalanced; escalate Very Imbalanced + ailment to Naturopath / Holistic Cure only after survival is green.
- **Architecture:** Thin continuity/orchestration seam over **supplied** balance-meter and ailment labels — not EA buff rewriting, not a daemon, not pack certification.
- **Upstreams:** `impeccable`, `UP-A85AD9DC3`, `UP-40FE662CF`.
- **Not:** BI-002 hunger cert; inventing meter readings; auto-crafting elixirs; save mutation.

## Why this exists

Need, career, aspiration, and gardening microsystems already load-balance in tandem. Balance is a prolonged mood wellness meter: positive moods push toward Balance; Imbalance drains needs 25% faster and slows skill builds 15%; Very Imbalanced always contracts a physical ailment (operator example: **Burning Passion**). Without a peer owner, agents recover hunger and forget the ailment cure ladder.

## Understanding the system (operator brief)

| Stage | Meaning |
| --- | --- |
| **Balance** | Default. Positive moods push the meter toward Balance. |
| **Imbalance** | Needs drain 25% faster; skills build 15% slower. |
| **Very Imbalanced** | Always contracts a physical ailment (visual/physical changes). |

### How to cure the ailment and restore Balance

1. **Visit a Naturopath** — Phone → Home tab → Visit a Naturopath.
2. **Consume a Holistic Cure** — Apothecary Elixir; buy at Sprucederry Grove stall or craft at Apothecary skill 10.
3. **Engage with Nature** — Water/maintain houseplants; meditate in nature (Natural Living).
4. **Maintain Positive Moods** — Curing the ailment is step one; good mood keeps Balance long-term.

## Microsystem states

| State | Meaning |
| --- | --- |
| `IDLE` | No imbalance / balanced and clear |
| `TRACKING` | Condition held; peers still busy |
| `RECOVERING_NATURE` | Prefer plants / meditate / positive mood |
| `AILMENT_ACTIVE` | Very Imbalanced + supplied ailment |
| `READY_HOLISTIC_CURE` | Inventory cure or obtain/craft path ready |
| `READY_NATUROPATH` | Escalate to phone Naturopath |
| `SUSPENDED_FOR_SURVIVAL` | Hunger/bladder/energy critical — hold condition |
| `YIELDED` | Player-first / busy |
| `RESTORED` / `COMPLETE` | Balanced + no ailment clears sticky tracking |

## Success call stack (evaluate-only)

```
observation (+ optional prior balance_service state)
  -> balance_service.evaluate_balance_service
       requires supplied balance_level and/or ailment (never invent)
       carries sticky condition from prior_state while still imbalanced
  -> survival_critical => SUSPENDED_FOR_SURVIVAL (hold, no cure click)
  -> Very Imbalanced + ailment:
       inventory Holistic Cure -> READY_HOLISTIC_CURE
       else Naturopath / purchase / craft ladder
  -> Imbalanced: RECOVERING_NATURE + SEEK_POSITIVE_MOOD
  -> host_stack surfaces balance_service even when next_gate is survival/needs
  -> domain_cascade balance receipt cites balance_service
  -> host_tandem emits BALANCE_CONDITION_HELD;
       after survival recovers, BALANCE_READY_HANDOFF before gardening resume
```

## Failure call stacks

| Failure | Host response |
| --- | --- |
| Survival critical | `SUSPENDED_FOR_SURVIVAL` + `condition_held=true` |
| Player directed / busy | `YIELDED`; do not authorize cure clicks |
| Balanced + no ailment | `RESTORED` / `IDLE` — clear sticky |
| Meter/ailment not supplied | `IDLE` (fail closed; no invention) |
| Imbalanced only | Nature/mood recovery — not Naturopath first |

## Module map

| Module | Responsibility | Side effects |
| --- | --- | --- |
| `balance_service` | Sticky condition, tandem state, compact receipt | none |
| `moodlets` | Positive/negative emotion family for mood recovery bias | none |
| `gardening_service` | Observed plant care as nature engagement peer | none |
| `teen_homework.survival_critical` | Shared survival suspend (P124 reuse) | none |
| `host_stack` | Always expose attached balance_service beside peers | none |
| `domain_cascade` | Balance domain polls via balance_service | none |
| `host_tandem` | Async observe events + balance handoff after needs | none |

## P82 admission

- **Hypothesis:** Sticky balance condition evaluated every tandem tick prevents agents from forgetting Imbalance / Very Imbalance ailment recovery after survival preemption, without letting cure routes outrank critical needs or inventing HUD readings.
- **Baseline:** moodlets/event_balance sense emotion strip but do not own Balance meter stages or Naturopath/Holistic Cure ladders; gardening may water plants without knowing imbalance context.
- **Falsifier:** Dropping `condition_held` while still Imbalanced/Very Imbalanced; queuing Naturopath under survival-critical needs; inventing Burning Passion without ailment observation; escalating Naturopath when only Imbalanced.
- **Measure:** `tests/test_balance_service.py` + host_tandem balance continuity cases.

## Proof ceiling

`HOST_BALANCE_MICROSYSTEM_TANDEM_NOT_DAEMON_NOT_PACK_CERT`. Live Naturopath / Holistic Cure / nature-balance recovery remains OPEN (P08). Does not close BI-002. Does not certify Enchanted by Nature pack behavior.
