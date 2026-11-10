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

**Canonical cheat list:** `skill_catalog` owns every `skill_id` → `skill_stat` → `stats.set_skill_level …` spelling. Print with `python -m scripts.diy_skill_force commands` (optional `--bundle remote_income|full_unlock`). Never invent stats — e.g. `stats.set_skill_level Major_MediaProduction 10` (with **i**); `Major_MediaProducton` is a no-op typo.

**Force gaps (codified Live path):** prefer `python -m scripts.diy_skill_force force-gaps` over one-shot agent scripts. A live invocation must supply the *observed* portrait key and location, exact `--members N` / ordered `--roster-key` list, existing `--profile-id` (or active profile), observed `--save-key` / `--household-key`, `--session-id`, PID, console proof and screen admission. **Always L-inventory first** on the intended Sim (J name proof). Type **only** non-yellow / absent rows — never re-type gold max rows; Photography and Pet Training max at 5. Never confuse Servo Olga (`OLGA_P2`) with human Charlee (`CHARLEE_P3`). Inherited `--all-listed-max` ledger rows are **not** fresh panel proof.

**Scroll the full Skills list (operator 2026-11-10):** after burger-expand, wheel-scroll the list (`plan_skills_panel_inventory` / `skills-inventory-plan`) so every row is seen. Gold/yellow checkmark rows are maxed; **non-yellow** rows are gap targets. Do not trust the first viewport alone. Resolve gaps with `gap_targets_from_observed_levels` or `commands --gaps-from levels.json`.

**Per-skill ceilings:** Photography and Pet Training **max at Level 5** (common sense / operator 2026-11-10). Catalog `max_level: 5` — gold at 5 is `PANEL_OBSERVED_MAX`; never force them to 10.

**Expand the Skills list (operator correction 2026-11-09; endpoints measured same day):** the default Skills flyout shows only ~2 rows. Do **not** treat the tiny scrollbar alone as enough. Open Skills with **L**, then grab the **burger bar** (two short horizontal lines) centered on the thin grey strip **directly above** the green `SKILL MASTERY PERKS` header and **click-drag upward** to resize. PrintWindow-measured 1920×1080 endpoints (`fixed-ui-click-map.skills_burger_bar_1920x1080`):

| State | Target | `client_xy` | Green header ~y |
| --- | --- | --- | --- |
| **MIN** (default) | `live.skills_burger_grip_min` | `(1722, 810)` | ~818 |
| **MAX** (expanded) | `live.skills_burger_grip_max` | `(1722, 225)` | ~234 |

Expand drag: stepped LMB `(1722,810) → (1722,225)` via `scripts.win32_input.left_drag` / plan `plan_skills_burger_expand`. Fast sidecar drags miss — prefer focused window + many `SetCursorPos` steps on the grip. Remeasure if the green band drifts. Collapse the perks chevron only as a secondary space-saver after the burger expand.

**PASS ceiling:** only a Skills-panel `LOCAL_OBSERVED` read after play-brief may support a live skill-force PASS. Console text, reward/trait dialogs, and mid-cascade `LEVEL UP` / `MAXED SKILL` toasts are **not** PASS. Open the console with `send_key_chord(['CTRL','SHIFT','C'])` (not a bare `send_vk`/`tap` sequence that can drop SHIFT and screenshot). Each cheat line: re-click the console strip → `type_text(cmd + "\n")`.

**Console focus before typing (operator correction 2026-11-09 / 2026-11-10):** never `type_text` cheat lines unless the white cheat strip is visually confirmed open and focused. Unfocused typing is Live hotkeys — **`V` starts video recording**. Open console with **Ctrl+Shift+C** via `keybd_event` after Sims `SetForegroundWindow` (SendInput chords often miss while physical keys work — same class as panel letter J). After open, the cheat field stays focused — type the batch without per-line strip re-clicks. Mood color is **not** selection.

**Servo identity (operator correction 2026-11-10):** white portrait boundaries only show that *a* chip is selected. Identical Servos cannot be told apart by bounds alone. Identity = panel text that embeds the Sim name. Prefer **J** (work/career). Aspiration **G** also works but is not the default for skill-force. Then **L** (skills) so progress is in sight.

**Lean panel sequence:** LEFT_CLICK portrait → **arm → J** name proof → **arm → L** skills sight → **arm → Ctrl+Shift+C** → type one skill probe → close console → **play a few seconds** (levels only refresh after play) → pause → measure → extrapolate → confirm → next skill. Owners: `plan_lean_observed_sim_skill_beat`, `plan_arm_then_panel_letter`. **Fresh world LMB→RMB arm immediately before every panel letter** — if J/L “does not register,” arm was skipped. **Forbidden:** portrait RMB, camera ladder, white-bounds-alone identity, G-as-default identity, `PANEL_LETTER_WITHOUT_FRESH_ARM`. Do not re-arm between cheat *lines* while the console field stays focused.

**Skill progress extrapolator (operator correction 2026-11-09):** for each gap skill, apply one iteration, play-brief, measure Skills-panel level delta, memoize, then `remaining = ceil((target - after) / delta)`. Confirm panel LOCAL_OBSERVED before the next skill. Delta ≤ 0 → falsify (do not guess retries). Owner: `extrapolate_skill_iterations`.

**Live hotkey arm (operator correction 2026-11-10):** **Right-click exposed world/terrain** to arm Live hotkeys — the left-click is not required (prior LMB→RMB also worked). Point must be terrain in the remaining viewport — **never** a `fixed-ui-click-map` seed. Assessor: `assess_arm_world_point`. Skill: `.cursor/skills/live-hotkey-arm`. Terrain RMB is not `RIGHT_CLICK_VIEW`.

**Lean skill-force beat (operator correction 2026-11-09):** happy path is cancel → arm once (world LMB+RMB) → **LEFT_CLICK** target portrait once → **Ctrl+Shift+C** → type the batch. **Forbidden:** portrait RMB, `RIGHT_CLICK_VIEW`, wheel zoom, camera ladder, portrait probe loops, re-arm between lines. Camera policy remains a separate admitted beat — never improvise it mid-skill-typing.

**Arm → cheat-console handoff:** after arm, hand off to the existing `CHEAT_CONSOLE` microsystem (`Ctrl+Shift+C` via `_toggle_cheat_console`), refocus `live.cheat_console_strip`, require white-strip proof before any `type_text`. Plan: `plan_arm_to_console_handoff` / `python -m scripts.fixed_ui_click_map handoff`.

**Fixed-UI click tracking:** record every HUD click (`python -m scripts.fixed_ui_click_map record --target-id … --client-xy X,Y --classification …`). Portrait vs calendar adjacency is a known WRONG_CONTROL — do not click ~`(300,1045)` when selecting Sims.

**Target-Sim algorithm (codified 2026-11-09):** one portrait at a time —

1. **EVALUATE** ledger/panel gaps (`evaluate_member_skill_levels`)
2. If gaps: **SELECT** via LEFT_CLICK portrait (not Space-as-primary)
3. **PROVE_IDENTITY** from Skills/Dynasty header
4. **CAMERA** center + `RIGHT_CLICK_VIEW` (15% pullback)
5. **CONSOLE** Ctrl+Shift+C + white-strip confirm
6. **DISPATCH** gap `stats.set_skill_level` lines
7. **PLAY_BRIEF** → **PANEL_RECORD**

CLI (evaluate-only until gates attested):

```sh
python -m scripts.diy_skill_force target-sim \
  --session-id example-local-session --members 4 \
  --save-key example-save --household-key example-household \
  --roster-key sim-001 --roster-key sim-002 --roster-key sim-003 --roster-key sim-004 \
  --member-key sim-003 --display-name "Sim Gamma" --roster-index 2 \
  --bundle full_unlock
```

Pass `--observed-panel-header "Sim Gamma hasn't…"` and `--console-strip-observed` only after live proof; `live_dispatch_ready` stays false otherwise. Owner: `plan_target_sim_skill_algorithm` / contract `target_sim_algorithm`.

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

**Skills-panel roster ledger (no more screenshot loops):** after you read a Skills panel once, record it:

```sh
python -m scripts.diy_skill_force panel-record --session-id example-local-session --members 4 \
  --save-key example-save --household-key example-household \
  --roster-key sim-001 --roster-key sim-002 --roster-key sim-003 --roster-key sim-004 \
  --display-name "Sim Alpha" --display-name "Sim Beta" --display-name "Sim Gamma" --display-name Sim Delta \
  --member-key sim-002 --member-display-name "Sim Beta" --all-listed-max --skill-level cooking=10
python -m scripts.diy_skill_force roster-status --session-id example-local-session
```

`PANEL_OBSERVED_MAX` skips maximize cells; `PANEL_OBSERVED` stores gaps below 10. `household_roster.members` is exact Live portrait count — **N** must be observed for each user's current household; example N=4 is synthetic. Never invent any portrait. Scoped ledger path: local user configuration under `households/<profile-id>/<scope-id>.json` (never a tracked repository fixture).

**Household (skill-round-robin):** observe Live portrait count → `--members N` where **N is whatever that household is** (not an invented 8/10 ceiling). Dispatch order is **one skill × every portrait, then the next skill** (not all skills on one Sim before Space). Between cells, `_execute_plan(close_console=True)` has **already closed** the console with Ctrl+Shift+C; **never toggle it again** before **Space** (`SELECT_NEXT_HOUSEHOLD_SIM`; wraps after last portrait). The Space action requires a fresh `admitted_screen_lease`; another agent owning the screen must cause deferral, not blind selection. Already-complete skill×member cells in the durable completion ledger (`households/<profile-id>/<scope-id>.json`) are **skipped** while Space still advances so selection stays aligned. Each typed cheat line is recorded `DISPATCHED` immediately (resume/skip evidence only; **not** Skills-panel PASS). `--redo` ignores the ledger for that run. Bootstrap entry `python bootstrap.py household-skills` prints the recipe; with `-- --members N …` it forwards into the verified checkout — never on install/gui open. `--detach` is **rejected before launching any subprocess**. The foreground executor waits for trustworthy OS input idle ≥15000ms and rechecks admission. Only one screen-input owner should work on the skill job. `--roster-key` values must be the exact, stable, ordered portrait identities, not invented names; `--first-portrait-attested` is a local host/operator assertion that the initial selected portrait is the first. These arguments are not themselves visual evidence: any roster change or uncertain selection requires stopping and reobserving, never adding a household member. Residual ids: `Major_HomestyleCooking`, `Skill_Fitness`, `Skill_NLS`. Missing packs may no-op individual lines.

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

## Trait safety, Escape forbids and trait repair (2026-11-09 Servo Evil incident)

A prior agent activated a NEW male Servo (CAS gender Continue) when the operator wanted Escape-cancel; the Servo became Evil and caused laundry fires. Same owner, no second trait daemon (contract v10):

- **Reward dialogs never blind-OK Evil/harmful traits.** `decide_reward_dialog` / `classify_reward_trait`: Evil (id `trait_Evil`, aliases `evil`, `trait_evil`, `Evil`, or "evil" in the observed dialog text) -> `ESCAPE_CANCEL_DIALOG` (Escape on that one observed dialog; never Enter, never an OK click); unclassified -> `HOLD`. `ACCEPT_OFFERED_REWARD_TRAIT` plan steps carry `refuse_blind_ok`, `forbidden_reward_traits` and `harmful_trait_action`; the executor still dispatches no reward-dialog input. Benign mastery traits keep `never_press_cancel`.
- **`trait_repair` plan (selected Sim):** `python -m scripts.diy_skill_force trait-repair` -> `testingcheats enabled true` -> `traits.remove_trait trait_Evil` -> Ctrl+Shift+C close -> `OBSERVE_TRAIT_REMOVED`. Default removes Evil only; `traits.equip_trait trait_Good` is emitted only with `--equip-good --operator-requested-good`. Other trait ids fail closed (`TRAIT_NOT_REPAIRABLE`). Evaluate-only (`execute_allowed=false`); the console id is community-documented and needs LOCAL_OBSERVED on the installed build.
- **`ui_forbids` / `evaluate_ui_action` (`ui-check` CLI):** Escape is never the household-traverse / console close (use **Ctrl+Shift+C**) and is never spammed (opens the Travel map / pause MENU); creating or activating a new Servo needs explicit operator consent; CAS gender **Continue** is forbidden once Escape-cancel was requested; `trait_Good` needs an operator request. Decision catalog: `cas.servo.create_continue_vs_escape_cancel` (Escape-cancel unless `new_servo_consent`); `school.attend.join_or_send_alone` forces **Send Alone** under host work (`host_work_active`).
- **Fire risk:** see `docs/HOUSEHOLD_UPKEEP.md` (repair/tune before laundry autonomy; Lint-Less / clean lint / clothesline).

```text
python -m scripts.diy_skill_force trait-repair
python -m scripts.diy_skill_force reward-check --trait trait_Evil
python -m scripts.diy_skill_force ui-check --action ESCAPE --context household_traverse
```

**Live gates still open (LOCAL_OBSERVED required, no PASS claimed):** trait removal on the selected Sim; household skill force with Skills-panel read after PLAY_BRIEF_OBSERVE_REPAUSE; Send Alone dialog. Proof ceiling `OFFLINE_REGRESSION_GUARDS_NOT_LIVE_TRAIT_REMOVE_OR_SKILLS_PANEL_PASS`.
