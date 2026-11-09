# Skill-force — P95 host unlock ladder

**Prompt:** TokenCorridor P95 — Program Design & Call-Stack Prototype Architect
**P124:** sibling owner beside `funds_inject` / `household_object_force`; distinct from read-only `sim_profile`
**Machine owner:** [`contracts/diy-skill-force.v1.json`](../contracts/diy-skill-force.v1.json) (v5)
**Evaluator / planner:** `betterinstincts.diy_skill_force`
**Execute adapter:** `python -m scripts.diy_skill_force`
**Typing owner:** `scripts.win32_input.type_text` (keybd_event — UNICODE-only is a silent miss on some TS4 hosts)

## Design brief

- **Subject:** Adult `Major_*` skills on **every** household Sim/Servo (count N → Space-traverse → dispatch).
- **Audience:** operators who need activities and unlockables ungated (DIY and beyond).
- **Job:** Mode-agnostic cheat planner. Default **`full_unlock`** maxes the adult catalog at level **10**, re-applies required residuals **Cooking / Fitness / Natural Living** at the end (unless already recorded complete), confirms offered mastery/reward-trait **OK** dialogs, skips skills already in the completion ledger, Spaces past fully-done members to the next Sim that still needs work, and supports **`household --members N --detach`** so agents are not blocked for hours.
- **Not:** BI-005 purposeful skill-growth certification; `practice_skill` queueing; an autorun skill daemon; aspiration life-state completion; invite OK; save edits.

## Bundles

| Bundle | Purpose |
| --- | --- |
| `full_unlock` | **All the way** — adult majors for activities/unlockables (default); residuals re-applied at end |
| `residual_core` | Cooking + Fitness + Natural Living (mandatory miss set) |
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
  -> KEEP_PAUSED during precious-time dispatch / long idle
  -> PLAY_BRIEF_OBSERVE_REPAUSE (5–10s @ 1x → capture Skills panel → pause again)
```

Library plans keep `execute_allowed=false`. Live execute requires an ACTIVE `host_listener` session, exact PID, and `screen_admit`. Yield the screen when another agent owns live certification. Pass `--no-accept-reward-dialogs` to skip trait OK accepts.

**Skills panel proof:** a paused-only Skills screenshot is `UNPROVEN_STALE`. Keep Live paused while time is precious and the main goal is unfinished, but to confirm residual levels run the bounded verify loop (`--verify-skills-panel`): play 5–10 seconds at 1x, read the panel, immediately pause again. Never leave sim speed running; never main-menu Resume.

**PASS ceiling:** only a Skills-panel `LOCAL_OBSERVED` read after play-brief may support a live skill-force PASS. Console text, reward/trait dialogs, and mid-cascade `LEVEL UP` / `MAXED SKILL` toasts are **not** PASS. Open the console with `send_key_chord(['CTRL','SHIFT','C'])` (not a bare `send_vk`/`tap` sequence that can drop SHIFT and screenshot). Each cheat line: re-click the console strip → `type_text(cmd + "\n")`.

## CLI

```text
python -m scripts.diy_skill_force catalog
python -m scripts.diy_skill_force plan --bundle full_unlock
python -m scripts.diy_skill_force level --bundle full_unlock --level 10
python -m scripts.diy_skill_force level --bundle diy_maker
python -m scripts.diy_skill_force level --bundle full_unlock --execute --process-id PID --session-id ID
python -m scripts.diy_skill_force level --bundle full_unlock --execute --process-id PID --session-id ID --verify-skills-panel --verify-play-seconds 7
python -m scripts.diy_skill_force household --members 3 --bundle full_unlock
python -m scripts.diy_skill_force household --members 3 --execute --detach --process-id PID --session-id ID --receipt dist/game-host/household-skill-force-async-receipt.json
```

**Household:** observe Live portrait count → `--members N` where **N is whatever that household is** (not an invented 8/10 ceiling). Member 0 keeps current selection; members 1..N-1 close console with **Ctrl+Shift+C** (never Esc — opens MENU) then **Space** (`SELECT_NEXT_HOUSEHOLD_SIM`). Members whose requested skills are already in the durable completion ledger (`dist/game-host/diy-skill-force-completion.json`, keyed by `session_id` + member index) are **skipped** — no console reopen — and Space continues to the next Sim that still needs work. Each typed cheat line is recorded `DISPATCHED` immediately (resume/skip evidence only; **not** Skills-panel PASS). `--redo` ignores the ledger for that run. Each cheat line: re-click console strip → `type_text(cmd+"\n")`. `computer_type` newlines do **not** submit. `--detach` starts an opt-in worker another agent can poll via receipt — do not reinvent traverse. Before admit, the worker **waits for OS input idle ≥15000ms** (cursor-stable fallback when synthetic input flickers `GetLastInputInfo`); continuous moving cursor fails with `CONTINUOUS_INPUT_BLOCKING_ADMIT`. Residual ids: `Major_HomestyleCooking`, `Skill_Fitness`, `Skill_NLS` (not Major_Cooking / Major_Fitness / Major_NaturalLiving). Missing packs may no-op individual lines.

## Proof ceiling

`HOST_SENDINPUT_DIY_SKILL_CHEAT_DISPATCH_NOT_BI005_SKILL_GROWTH_CERT`

Does not close BI-002 or BI-005. `sim_profile` remains read-only inspection.
