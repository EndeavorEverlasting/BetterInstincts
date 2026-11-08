# Domain cascade — poll & cascading receipts (P124 + trifecta)

Machine owner: [`contracts/domain-cascade.v1.json`](../contracts/domain-cascade.v1.json).
Evaluator: `python -m scripts.domain_cascade` / `betterinstincts.domain_cascade`.

## Design brief

- **Subject:** Needs, Simoleon budget, career/school/scenario, skills/whims, and relationships as **peer microsystems**.
- **Job:** On each recurring observation (human, agent, or script), poll domains in horizon-safe order and emit cascading receipts so they can read each other.
- **Join:** Need-service **load balance** (`docs/NEED_LOAD_BALANCE.md`) is the needs-lane balancer; this cascade respects its detach/windows instead of inventing a second needs queue.
- **P124:** Need snapshots come from `need_service_base.normalize_needs` — do not fork six-need parsing in this module.
- **Not:** A background daemon, EA autonomy rewrite, or BI-002 closure.

## Cascade order

```
observation poll
  -> needs (+ navigating_needs advisory; need_services + LB)
  -> budget (simoleons / secure objects)
  -> career (school_day / teen_homework / scenario scoring)
  -> skills_whims (sim_profile)
  -> relationships (social_opportunity)
  -> cascade_receipt (prior receipts visible to later domains)
```

Player-first / busy yields halt the cascade. Critical needs / LB detach outcomes propagate into later domain findings.

## Proof ceiling

## Completed responsibilities and optional gardening

An explicit `homework_pending=False` remains false when inventory or lot observations mention a homework book. Book presence is not evidence of unfinished work. The local school panel on 2026-11-07 displayed Homework Complete; the former `homework_pending or True` adapter incorrectly reopened that task. The cascade now passes the supplied flag unchanged. Pending work still routes to the existing teen-homework owner; critical needs retain precedence.

For the operator's needs-first gardening request, retain this call stack: current observed six-need snapshot → existing `need_services`/load balance → existing domain cascade school/homework receipt → local scene/queue/presence admission → one actual available gardening interaction → observed outcome. Never invent readings or treat a plan as input authority. School attendance and player-directed queues preclude a competing gardening action. The Hidden Catalog Scout owns separate agent exploration, not a Sim need or a replacement for this call stack.

P124 ownership review: **KEEP** `need_service_base` normalization, `need_services` selection and `teen_homework` policy; **REPAIR** only the incorrect argument propagation in `domain_cascade`. No duplicate needs parser, seventh need, new scheduler or unrelated readability extraction is warranted by this defect.

`HOST_DOMAIN_CASCADE_POLL_RECEIPTS_NOT_DAEMON_NOT_LIVE_CERT`. Live multi-domain ticks OPEN.
