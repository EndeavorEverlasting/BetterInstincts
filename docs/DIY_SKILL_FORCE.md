# Skill-force — P95 host unlock ladder

**Prompt:** TokenCorridor P95 — Program Design & Call-Stack Prototype Architect
**P124:** sibling owner beside `funds_inject` / `household_object_force`; distinct from read-only `sim_profile`
**Machine owner:** [`contracts/diy-skill-force.v1.json`](../contracts/diy-skill-force.v1.json) (v3)
**Evaluator / planner:** `betterinstincts.diy_skill_force`
**Execute adapter:** `python -m scripts.diy_skill_force`
**Typing owner:** `scripts.win32_input.type_text` (keybd_event — UNICODE-only is a silent miss on some TS4 hosts)

## Design brief

- **Subject:** Adult `Major_*` skills on the **currently selected** Sim or Servo.
- **Audience:** operators who need activities and unlockables ungated (DIY and beyond).
- **Job:** Mode-agnostic cheat planner. Default **`full_unlock`** maxes the adult catalog at level **10**, then confirms offered mastery/reward-trait **OK** dialogs (e.g. Perfectionist-style) so unlockables are not left modal-blocked.
- **Not:** BI-005 purposeful skill-growth certification; `practice_skill` queueing; a second skill/trait daemon; aspiration life-state completion; invite OK; save edits.

## Bundles

| Bundle | Purpose |
| --- | --- |
| `full_unlock` | **All the way** — adult majors for activities/unlockables (default) |
| `diy_maker` | Handiness + Robotics + Fabrication + Programming |
| `servo_core` | Lean Servo DIY without Fabrication |
| `creative` / `social` / `athletic` | Focused unlock subsets |

## Success call stack

```
CLI plan/level (bundle full_unlock | skill ids)
  -> diy_skill_force.plan_skill_force
  -> REQUIRE_FOREGROUND_SIMS (soft focus)
  -> PRESERVE_OPERATOR_MODE (never force F1)
  -> REQUIRE_ACTIVE_SIM_SELECTION
  -> Ctrl+Shift+C
  -> testingcheats enabled true
  -> stats.set_skill_level <Major_*> 10  (× resolved skills)
  -> ACCEPT_OFFERED_REWARD_TRAIT (Enter + OK hotspot; interleaved + final; never Cancel)
  -> optional Esc
```

Library plans keep `execute_allowed=false`. Live execute requires an ACTIVE `host_listener` session, exact PID, and `screen_admit`. Yield the screen when another agent owns live certification. Pass `--no-accept-reward-dialogs` to skip trait OK accepts.

## CLI

```text
python -m scripts.diy_skill_force catalog
python -m scripts.diy_skill_force plan --bundle full_unlock
python -m scripts.diy_skill_force level --bundle full_unlock --level 10
python -m scripts.diy_skill_force level --bundle diy_maker
python -m scripts.diy_skill_force level --bundle full_unlock --execute --process-id PID --session-id ID
```

Select each household Sim/Servo in Live before `--execute`. Re-run per member. Missing packs may no-op individual lines.

## Proof ceiling

`HOST_SENDINPUT_DIY_SKILL_CHEAT_DISPATCH_NOT_BI005_SKILL_GROWTH_CERT`

Does not close BI-002 or BI-005. `sim_profile` remains read-only inspection.
