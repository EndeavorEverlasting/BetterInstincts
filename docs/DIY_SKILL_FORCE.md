# Skill-force — P95 host unlock ladder

**Prompt:** TokenCorridor P95 — Program Design & Call-Stack Prototype Architect
**P124:** sibling owner beside `funds_inject` / `household_object_force`; distinct from read-only `sim_profile`
**Machine owner:** [`contracts/diy-skill-force.v1.json`](../contracts/diy-skill-force.v1.json) (v10)
**Evaluator / planner:** `betterinstincts.diy_skill_force`
**Execute adapter:** `python -m scripts.diy_skill_force`
**Typing owner:** `scripts.win32_input.type_text` (keybd_event — UNICODE-only is a silent miss on some TS4 hosts)

## Design brief

- **Subject:** Adult `Major_*` skills on **every** household Sim/Servo (count N → skill-round-robin Space-traverse → dispatch).
- **Audience:** operators who need activities and unlockables ungated (DIY and beyond), especially after a save reload undoes progression.
- **Job:** Mode-agnostic cheat planner. Default **`full_unlock`** maxes the adult catalog at level **10** using **skill-round-robin**: one skill for every portrait, then the next skill, until all are 10. Re-applies required residuals **Cooking / Fitness / Natural Living** at the end (unless already recorded complete), confirms offered mastery/reward-trait **OK** dialogs, skips already-complete skill×member cells, and supports **foreground-only `household --members N --execute --roster-key ... --first-portrait-attested`** / **`python bootstrap.py household-skills -- …`** with an exact, fixed portrait roster. Never autorun from install.
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
  -> Ctrl+Shift+C close (never Esc)
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
python -m scripts.diy_skill_force household --members 3 --bundle full_unlock --execute --roster-key SIM_A --roster-key SIM_B --roster-key SERVO_C --first-portrait-attested --process-id PID --session-id ID
python bootstrap.py household-skills
python bootstrap.py household-skills -- --members 3 --bundle full_unlock --execute --roster-key SIM_A --roster-key SIM_B --roster-key SERVO_C --first-portrait-attested --process-id PID --session-id ID
```

**Household (skill-round-robin):** observe Live portrait count → `--members N` where **N is whatever that household is** (not an invented 8/10 ceiling). Dispatch order is **one skill × every portrait, then the next skill** (not all skills on one Sim before Space). Between cells, `_execute_plan(close_console=True)` has **already closed** the console with Ctrl+Shift+C; **never toggle it again** before **Space** (`SELECT_NEXT_HOUSEHOLD_SIM`; wraps after last portrait). The Space action requires a fresh `admitted_screen_lease`; another agent owning the screen must cause deferral, not blind selection. Already-complete skill×member cells in the durable completion ledger (`dist/game-host/diy-skill-force-completion.json`) are **skipped** while Space still advances so selection stays aligned. Each typed cheat line is recorded `DISPATCHED` immediately (resume/skip evidence only; **not** Skills-panel PASS). `--redo` ignores the ledger for that run. Bootstrap entry `python bootstrap.py household-skills` prints the recipe; with `-- --members N …` it forwards into the verified checkout — never on install/gui open. `--detach` is **rejected before launching any subprocess**. The foreground executor waits for trustworthy OS input idle ≥15000ms and rechecks admission. Only one screen-input owner should work on the skill job. `--roster-key` values must be the exact, stable, ordered portrait identities, not invented names; `--first-portrait-attested` is a local host/operator assertion that the initial selected portrait is the first. These arguments are not themselves visual evidence: any roster change or uncertain selection requires stopping and reobserving, never adding a household member. Residual ids: `Major_HomestyleCooking`, `Skill_Fitness`, `Skill_NLS`. Missing packs may no-op individual lines.

## P83 installation and ledger-proof correction (2026-11-09)

When **all requested skill×portrait cells have a DISPATCHED ledger entry**, the
planner now returns `HOUSEHOLD_SKILL_FORCE_NO_PENDING_DISPATCH_UNVERIFIED`,
not "all members already maxed." This avoids promoting a typed cheat into
Skills-panel confirmation. Executing that all-skipped plan does **not** open
the console, press Space, or move the pointer. Repeated runs after a save
reload need fresh panel observation before relying on skip status; `--redo`
is available in an explicitly authorized disposable lab.

The bootstrap "Household skills" recipe is **plan-only** and never a shortcut
to bulk `--execute`. The on-disk CLI still exposes live execution, but
`--roster-key` and `--first-portrait-attested` are local agent assertions,
not independent pixel/sensor evidence. The current executor also spans
multiple cheat-console UI effects under one admission, so P08 local agents
must validate per-effect human-input precedence and real per-cell Sim
identity before using unattended bulk runs.

For exact local installation and live certification gates, read
[the P04 handoff](handoff/BI-HOUSEHOLD-SKILL-LOCAL-P04-2026-11-09.md)
and its [machine dispatch](../plans/active/BI-HOUSEHOLD-SKILL-LOCAL-P04.dispatch.v1.json).
The safe first local command is a *read-only* git/status preflight, not a
cheat command. Install via `bootstrap.py install` only after resolving and
safely updating the canonical checkout.

## Proof ceiling

`HOST_SENDINPUT_DIY_SKILL_CHEAT_DISPATCH_NOT_BI005_SKILL_GROWTH_CERT`

Does not close BI-002 or BI-005. `sim_profile` remains read-only inspection.

## Fifth Gear judgment boundary (2026-11-09)

The original task is **skill across a fixed household**, not `create a Sim`, `create a Servo`, CAS/household merge, Build/Buy, Gallery, Store, EA Connect or any online feature. A separate new objective and independent authorization would be needed to add characters. `contracts/household-judgment.v1.json` + `betterinstincts/household_judgment.py` provide the reusable fail-closed advisory before permitted skill inputs; `betterinstincts/menu_blockers.py` forbids online navigation globally. Existing screen-admission and player-precedence checks are independent and still mandatory.

**Important evidence limit:** the GitHub-hosted planner cannot read real-time Sims portrait IDs. The CLI receives operator/local-agent `--roster-key` attestations and does not itself recapture IDs after each Space. Local Cursor/Win32 adapters must observe the selection and roster for P08 validation. Invariant `fixed N` is guaranteed for planned target slots, **not proven against on-screen changes** until actual runtime observation. A typed cheat and completion ledger `DISPATCHED` are weaker than Skills-panel `LOCAL_OBSERVED` and never certify level 10 by themselves. No other autonomy microservice or player-directed activity is disabled by this task-specific foreground restriction.

**Individual-cell clarification:** `plan_skill_force` now returns `SKILL_FORCE_MEMBER_NO_PENDING_DISPATCH_UNVERIFIED` (not `ALREADY_MAXED`) when its requested skills are merely recorded in the ledger. Its execute skip path is input-free, including no cursor park. These names are proof states, not assurances that the Sims game kept level 10 after reload.
