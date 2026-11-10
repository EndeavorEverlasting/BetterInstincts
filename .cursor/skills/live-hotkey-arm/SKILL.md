---
name: live-hotkey-arm
description: >-
  Arms The Sims 4 Live hotkeys by briefly borrowing the Sims window, right-clicking
  exposed world/terrain, then restoring the operator's foreground app. Use when
  Space, Ctrl+Shift+C, J/L/G, play/pause, or other Live hotkeys fail to register,
  when household sim cycling does nothing, or before any Live hotkey after the
  operator has been in another app (YouTube, browser, IDE, …).
---

# Live hotkey arm (interruptible)

## Rule (operator, 2026-11-10)

1. **Snapshot** the operator's current foreground app (YouTube, browser, IDE — anything).
2. **Borrow** Sims briefly so Live can receive input.
3. **Right-click exposed world/terrain** to arm Live hotkeys.
4. **Restore** the operator's app so they keep control of their computer.

A terrain right-click is enough for the arm itself. Earlier guidance used left-click then right-click; that also worked, but the left-click is **not required**. Focus loss is **not** IDE-specific — users watch YouTube while the game runs.

Composes with ASYNC_INTEROP: 15s trusted idle still gates new screen leases. Borrow/restore does not shorten idle and must never monopolize the desktop.

## When

- **Once** at the start of a skill beat (pinned `[880,480]`), then send `J` / `L` / console / `1` / `0` without more world clicks.
- Re-arm **only** if a hotkey clearly fails to register — repeated terrain RMB moves the map and is forbidden during skill force.
- Before `Space` (next household Sim) when focus may have left the client.

## Sequence

1. SNAPSHOT_OPERATOR_FOREGROUND
2. BORROW_SIMS_FOREGROUND (AttachThreadInput dance; fail closed if Sims cannot borrow)
3. RIGHT_CLICK the **one pinned** terrain point `[880, 480]` — not street-corner roaming
4. Press **Enter** to recenter on the **active Sim** (terrain arm can displace the camera; immersion requires staying on the selected Sim). If selection/camera switches later, Enter again. Never Shift+Enter (lot) and never roam/zoom to refocus.
5. RESTORE_OPERATOR_FOREGROUND when yielding the desktop
6. Then send Live hotkeys (`J`, `L`, `G`, `1`/`0`, `Space`, `Ctrl+Shift+C`, …)
7. Prefer PrintWindow over desktop screenshots when the game window sets `WDA_EXCLUDEFROMCAPTURE`

**Skill-force camera (operator 2026-11-10):** keep focus on the active Sim. Ban lot roam / wheel zoom-out / street top-down as “refocus.” Use native Enter after arm or whenever the view drifts.

Assessor: `assess_arm_world_point` — rejects HUD bands and points within 36px of any mapped seed. Pinned terrain point: `[880, 480]`.

## Play-brief (Skills measure)

1. Borrow → arm → press `1` → restore operator app
2. Wait ≥5s while they keep YouTube/other apps
3. Borrow → arm → press `0` → restore
4. Only then measure Skills panel

Paused-only panel reads are STALE (`plan_arm_then_play_brief`).

## Do not

- Monopolize foreground for the agent session or leave the operator trapped in Sims.
- Arm on mapped fixed-UI coordinates or HUD bands.
- Treat terrain RMB as `RIGHT_CLICK_VIEW` portrait follow / camera arm.
- **Never right-click a household portrait during the lean skill-force beat** (select is LEFT_CLICK only).
- Skip this arm and “Space until lucky.”
- `type_text` cheats without a confirmed white console strip (unfocused typing is Live hotkeys; `V` starts video recording).
- Open console with SendInput chords — use `keybd_event` Ctrl+Shift+C after a Sims borrow (operator 2026-11-10).

## Handoff to cheat console

1. `ARM_LIVE_HOTKEYS` (borrow → terrain RMB → restore, or held borrow for type batch)
2. LEFT_CLICK target portrait (under borrow if needed)
3. Arm → **J** work for name identity (Servos collide on white bounds)
4. Arm → **L** skills for progress sight
5. Held borrow → `Ctrl+Shift+C` → type batch → close → **restore operator**
6. Interruptible play-brief before any Skills measure/extrapolate

Plan: `plan_lean_olga_skill_beat` / `plan_arm_then_panel_letter` / `plan_arm_then_play_brief` / `_with_sims_input_borrow`.

## Code owners

- Plan: `betterinstincts.diy_skill_force.plan_live_hotkey_arm` → `ARM_LIVE_HOTKEYS`
- Live helper: `scripts.diy_skill_force._arm_live_hotkeys` / `_with_sims_input_borrow`
- Interop: `contracts/workflow-interoperability.v1.json` → `game_input_borrow_restore`
- Contract: `contracts/diy-skill-force.v1.json` → `live_hotkey_arm`
