# Need-service load balance — P95 program design

**Prompt:** TokenCorridor P95 — Program Design & Call-Stack Prototype Architect
**Provenance:** `spec-architecture-prompts.v1.json` blob `5926a198a14567de55110ed19e922fc444b4dec7`
**Machine owner:** [`contracts/need-load-balance.v1.json`](../contracts/need-load-balance.v1.json)
**Evaluator:** `betterinstincts.need_load_balance` / composed by `need_services`
**Parent tandem:** [`NEED_SERVICES.md`](NEED_SERVICES.md)

## Design brief

- **Subject:** Parallel need microsystems (hunger…social) that must load-balance like a balancer with health checks.
- **Audience:** local host agent composing six tandem services without sticking to a dead call stack.
- **Job:** Probe each attached need service; when one is off, **detach** that stack, open a fresh **assumption window** (scene + assumptions + options reset), reweight avenues, and continue on healthy siblings.
- **Architecture:** LB is a thin orchestration seam over `need_services` — not a daemon, not EA autonomy, not a second monolith queue.
- **Upstreams:** `impeccable`, `UP-A85AD9DC3`, `UP-40FE662CF`.
- **Not:** Kubernetes/network LB, background health daemons, save mutation, or BI-002 hunger certification.

## Governance vs harness vs program

| Layer | Owns |
| --- | --- |
| Governance | Player first; no background scanners; no Resume/user-save mutation |
| Harness | unittest + doctrine CI |
| Program | health probe, detach, assumption window, reweight, load-balance pick |
| Live adapters | future SendInput only after evaluate-only plan |

## Domain vocabulary

| Term | Owns |
| --- | --- |
| `NEED_SERVICE_HEALTH` | Per-service probe result: HEALTHY / DEGRADED / UNHEALTHY / YIELDED |
| `NEED_SERVICE_DETACH` | Remove unhealthy service from primary selection pool |
| `ASSUMPTION_WINDOW` | Fresh exploration frame after detach: scene reset, cleared sticky assumptions, reweighted options |
| `NEED_LOAD_BALANCE` | Pick primary among remaining healthy (then degraded) READY services by urgency × weight |
| `MICROSYSTEM` | One need service + its lane catalog (hunger lanes, fun lanes, …) |

## Success call stack (evaluate-only)

```
need_services.evaluate_need_services
  -> plan each microsystem independently (lanes / fun_service)
  -> need_load_balance.health_check_all(services, failure_signals?)
  -> for each UNHEALTHY: DETACH + open_assumption_window(need)
       clears sticky preferred_route / inventory guesses
       rebuilds option_set with BOOST_ALTERNATES_PENALIZE_FAILED weights
  -> load_balance among HEALTHY READY (fallback DEGRADED READY)
  -> gate NEED_SERVICES_LOAD_BALANCE when any detach/window; else NEED_SERVICES_TANDEM
  -> host_stack surfaces primary + windows + health map
```

## Failure call stacks

| Failure | Classification | Host response |
| --- | --- | --- |
| Service BLOCKED / NO_FREE_NEED_LANE | UNHEALTHY | Detach; open assumption window; rebalance |
| CONTENDED only | DEGRADED | Keep attached; demote weight; prefer free sibling lanes |
| Player directed / busy | YIELDED | Never rebalance over PLAYER_FIRST |
| All services unhealthy/idle | IDLE | `NEED_SERVICES_IDLE` / FIND_OR_PLACE — no fake primary |
| Survival urgent + all survival unhealthy | CRITICAL_WINDOW | Assumption window boosts MAP_TRAVEL / place-object options |

## Module map

| Module | Responsibility | Side effects |
| --- | --- | --- |
| `need_load_balance` | Health, detach, windows, reweight, pick | none |
| `need_services` | Compose six plans + invoke LB | none |
| `host_stack` | Gate / fallback exposure | none |
| `need_service_base` | Shared lane primitives (P124) | none |

## P82 admission (measured here)

- **Hypothesis:** Health-check + detach + assumption-window reweight recovers planning when a microsystem is blocked without sticking to its dead preferred route.
- **Baseline:** Urgency-only primary among READY; no health, no detach, no window.
- **Falsifier:** Detaching a HEALTHY urgent survival service; selecting UNHEALTHY as primary; opening a window without clearing sticky assumptions.
- **Measure:** `tests/test_need_load_balance.py` + orchestrator fields on `evaluate_need_services`.

## Proof ceiling

`HOST_NEED_LB_HEALTH_ASSUMPTION_WINDOW_NOT_DAEMON_NOT_EA_API`. Live multi-Sim failover OPEN. Does not close BI-002.
