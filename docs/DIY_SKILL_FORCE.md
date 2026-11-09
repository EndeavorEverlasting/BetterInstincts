# DIY skill-force — P95 host maker skills

**Prompt:** TokenCorridor P95 — Program Design & Call-Stack Prototype Architect  
**P124:** sibling owner beside `funds_inject` / `household_object_force`; distinct from read-only `sim_profile`  
**Machine owner:** [`contracts/diy-skill-force.v1.json`](../contracts/diy-skill-force.v1.json)  
**Evaluator / planner:** `betterinstincts.diy_skill_force`  
**Execute adapter:** `python -m scripts.diy_skill_force`

## Design brief

- **Subject:** Handiness, Robotics, Fabrication, Programming on the **currently selected** Sim or Servo.
- **Audience:** operators who need DIY upgrades, Servo work, and fabricator recipes immediately useful.
- **Job:** Mode-agnostic cheat planner that maxes the DIY maker cluster (default level **10**).
- **Not:** BI-005 purposeful skill-growth certification; `practice_skill` queueing; a second skill daemon; save edits.

## Success call stack

```
CLI plan/level (bundle diy_maker | skill ids)
  -> diy_skill_force.plan_skill_force
  -> REQUIRE_FOREGROUND_SIMS (soft focus)
  -> PRESERVE_OPERATOR_MODE (never force F1)
  -> REQUIRE_ACTIVE_SIM_SELECTION
  -> Ctrl+Shift+C
  -> testingcheats enabled true
  -> stats.set_skill_level Major_Handiness 10
  -> stats.set_skill_level Major_Robotics 10
  -> stats.set_skill_level Major_Fabrication 10
  -> stats.set_skill_level Major_Programming 10
  -> optional Esc
```

Library plans keep `execute_allowed=false`. Live SendInput requires an ACTIVE `host_listener` session, exact PID, and `screen_admit`.

## Bundles

| Bundle | Skills | Use |
| --- | --- | --- |
| `diy_maker` | handiness, robotics, fabrication, programming | Default “super useful” DIY set |
| `servo_core` | handiness, robotics, programming | Lean Servo path without Fabrication pack |

## CLI

```text
python -m scripts.diy_skill_force catalog
python -m scripts.diy_skill_force plan --bundle diy_maker
python -m scripts.diy_skill_force level --bundle diy_maker --level 10
python -m scripts.diy_skill_force level --bundle diy_maker --execute --process-id PID --session-id ID
```

Select each Servo (or human Sim) in Live before `--execute`. Re-run per household member.

## Failure call stacks

| Failure | Host response |
| --- | --- |
| Player directed | `YIELD_TO_PLAYER` |
| Unknown skill / bundle | fail closed |
| Level outside 1..10 | `INVALID_SKILL_LEVEL` |
| Missing foreground / inactive session | block SendInput |
| Missing Discover University / Eco Lifestyle | those cheat lines may no-op; others still apply |

## Proof ceiling

`HOST_SENDINPUT_DIY_SKILL_CHEAT_DISPATCH_NOT_BI005_SKILL_GROWTH_CERT`

Does not close BI-002 or BI-005. `sim_profile` remains read-only inspection.
