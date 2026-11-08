# Aspiration service — async microsystem (P95)

**Prompt:** TokenCorridor P95 — Program Design & Call-Stack Prototype Architect
**Provenance:** `spec-architecture-prompts.v1.json` blob `5926a198a14567de55110ed19e922fc444b4dec7`
**Machine owner:** [`contracts/aspiration-service.v1.json`](../contracts/aspiration-service.v1.json)
**Evaluator:** `betterinstincts.aspiration_service` / `python -m scripts.aspiration_service`

## Design brief

- **Subject:** Aspiration and life-state dialogs as a peer microsystem beside need and career services — starting with the Mother Nature / Fairy timed-charm initiation.
- **Audience:** local host agents that would otherwise OK occult transformations while the base six-need engine is unfinished.
- **Job:** Keep a sticky `ASPIRATION_PROMPT` alive across survival/needs turns; judge OK/Cancel with an explicit `aspiration_completion_enabled` toggle; refuse life-state mutations that rewrite need trees until occult readiness is separately proven.
- **Architecture:** Thin continuity/judgment seam over `decision-prompts` — not a second needs planner, not a daemon, not fairy certification.
- **Upstreams:** `impeccable`, `UP-A85AD9DC3`, `UP-40FE662CF`.
- **Not:** BI-002 hunger cert; occult need-tree microsystems; auto-OK on random prompts; save mutation.

## Why this exists

Need and career microsystems already load-balance in tandem. Aspiration and occult initiation dialogs arrive asynchronously (chance cards, ritual confirmations) and can permanently change life state — which changes needs. Agents and developers must be able to **disable aspiration completion** while building the regular Sims needs floor, then enable it when ready. End users will typically leave it enabled.

## Toggle

| Mode | `aspiration_completion_enabled` | Behavior |
| --- | --- | --- |
| Product / end-user | `true` (contract product default) | Ordinary aspiration milestones may recommend OK; life-state mutations still require occult-needs readiness |
| Lab / developer | `false` (host default) | All completion and life-state prompts fail closed to **Cancel** |

Host stack defaults to **lab fail-closed** (`false`) so BI-002 needs work is not derailed by fairy/vampire/etc. transformations. Operators set `aspiration_completion_enabled=true` when they intentionally want aspiration progress.

## Microsystem states

| State | Meaning |
| --- | --- |
| `IDLE` | No aspiration dialog attached |
| `TRACKING` | Dialog/prompt held; peers still busy |
| `DISABLED_REFUSE` | Toggle off — Cancel authorized |
| `JUDGING` | Toggle on — scoring in progress |
| `READY_CANCEL` | Judgment selected Cancel |
| `READY_OK` | Judgment selected OK (never for unready occult rewrite) |
| `YIELDED` | Player-first / busy |
| `COMPLETE` | Dialog dismissed / cleared |

## Success call stack (evaluate-only)

```
observation (+ optional prior aspiration_service state)
  -> aspiration_service.evaluate_aspiration_service
       matches catalogued prompt (narrative tokens / prompt_id)
       carries sticky prompt from prior_state while still active
  -> if aspiration_completion_enabled=false -> READY_CANCEL / PRESS_CANCEL
  -> if life_state_mutation and occult_needs_engine_ready=false -> Cancel
  -> else judge OK/Cancel from prompt class + operator preference
  -> host_stack surfaces aspiration_service even when next_gate is survival/needs
  -> host_tandem emits ASPIRATION_PROMPT_HELD; dialog Cancel/OK outranks gardening
```

## Failure call stacks

| Failure | Host response |
| --- | --- |
| Toggle disabled | `DISABLED_REFUSE` + dialog Cancel |
| Occult needs unready | `READY_CANCEL` + Cancel (fairy/vampire/etc.) |
| Player directed / busy | `YIELDED`; do not click dialog |
| Unknown life-state prompt | Cancel / fail closed |
| Dialog cleared | `COMPLETE` / `IDLE` |

## Module map

| Module | Responsibility | Side effects |
| --- | --- | --- |
| `aspiration_service` | Sticky prompt, toggle, OK/Cancel judgment | none |
| `decision-prompts` | Catalog narrative tokens / options | none |
| `host_stack` | Surface aspiration_service; dialog gates outrank needs | none |
| `domain_cascade` | Aspirations domain poll | none |
| `host_tandem` | Async observe events + aspiration dialog handoff | none |

## P82 admission

- **Hypothesis:** Sticky aspiration prompts evaluated every tandem tick let the host Cancel occult initiation while needs work continues, without forgetting the dialog or auto-OKing life-state changes.
- **Baseline:** decision_eval alone scores chance cards when `prompt_id` wins `next_gate`; life-state dialogs can be ignored or accidentally OK'd while needs dominate.
- **Falsifier:** OK recommended while `aspiration_completion_enabled=false`; OK for Mother Nature while occult needs unready; dropping sticky prompt while dialog still active.
- **Measure:** `tests/test_aspiration_service.py` + host_tandem aspiration continuity cases.

## Proof ceiling

`HOST_ASPIRATION_MICROSYSTEM_TANDEM_NOT_DAEMON_NOT_LIFE_STATE_MUTATION`. Live Cancel on Mother Nature remains OPEN (P08). Does not close BI-002. Does not authorize fairy need-tree work.
