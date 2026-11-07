# Need services — tandem six-need host factor (P95 + P124)

Registry: [`contracts/need-services.v1.json`](../contracts/need-services.v1.json).
Lanes (non-Fun): [`contracts/need-lanes.v1.json`](../contracts/need-lanes.v1.json).
Fun (rich): [`contracts/fun-service.v1.json`](../contracts/fun-service.v1.json).
Base helpers: `betterinstincts/need_service_base.py`.
Orchestrator: `python -m scripts.need_services` / `betterinstincts.need_services`.

## Design brief

- **Subject:** Independent host services for hunger, bladder, energy, hygiene, fun, social.
- **Job:** Plan need remedies **in tandem** so agents do not invent a monolith queue or reinvent parsers.
- **P124:** Shared `need_service_base` (normalize needs, object freeness, lane planner). New need work extends the registry + lanes — do not fork helpers.
- **Not:** A background daemon, EA tuning API, or BI-002 hunger certification.

## Architecture

```
need_service_base
  ├─ fun_service          (fun-service.v1.json)
  ├─ need_lanes hunger…social (need-lanes.v1.json)
  └─ need_services orchestrator → host_stack NEED_SERVICES_TANDEM
```

Each service returns its own `parallel_ready` lanes. After planning, **P95 load balance** ([`NEED_LOAD_BALANCE.md`](NEED_LOAD_BALANCE.md)) health-checks each microsystem, detaches unhealthy call stacks, opens assumption windows with reweighted options, and picks `primary_need` among healthy READY plans. Sibling lane claims and `occupied_objects` prevent pile-up.

Navigating Needs panel tandem (`docs/NAVIGATING_NEEDS.md`) remains a separate Discovery Quest surface that outranks scenario scoring when active.

## Proof ceiling

`HOST_NEED_SERVICES_REGISTRY_NOT_DAEMON_NOT_EA_API` (+ LB ceiling in NEED_LOAD_BALANCE). Live multi-Sim dispatch OPEN. Does not close BI-002.
