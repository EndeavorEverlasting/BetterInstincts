---
name: live-hotkey-arm
description: >-
  Arms The Sims 4 Live hotkeys by left-clicking in the world then right-clicking
  to cancel options. Use when Space, Ctrl+Shift+C, or other Live hotkeys fail to
  register, when household sim cycling does nothing, or before any Live hotkey
  after focus may have left the game.
---

# Live hotkey arm

## Rule (operator, verbatim)

Left-click ensures that the focus is in the game, and then right-click cancels the options so that the hotkeys work.

You have to left-click in the world and right-click to cancel the options, then the hotkeys work.

## When

- Before `Space` (next household Sim) or any other Live hotkey after focus may have left the game client.
- When Space appears to do nothing (selection does not advance).
- After agent soft-focus / Alt / HUD clicks that leave keyboard focus ambiguous.

## Sequence

1. **LEFT_CLICK** an **empty** world/viewport point (sky/wall/clear floor — not desks, Sims, HUD portraits, or the cheat strip). Left-click on interactables opens pie options (e.g. Clean Lightly) that block hotkeys.
2. **RIGHT_CLICK** the same point to **cancel** the pie/options menu that the left-click opened.
3. Only then send Live hotkeys (`Space`, `Ctrl+Shift+C`, etc.).
4. Prefer PrintWindow over desktop screenshots when the game window sets `WDA_EXCLUDEFROMCAPTURE`.

## Do not

- Treat the cancel right-click as `RIGHT_CLICK_VIEW` portrait follow / camera arm.
- Skip this arm and “Space until lucky.”
- Use this as a substitute for **LEFT_CLICK the target portrait** when selecting a particular Sim for skill force — portrait click + Skills/Dynasty header proof remain required for target-sim.
- `type_text` cheats without a confirmed white console strip (unfocused typing is Live hotkeys; `V` starts video recording).

## Handoff to cheat console

After arm, hand off to the **CHEAT_CONSOLE** microsystem — do not invent a second console opener:

1. `ARM_LIVE_HOTKEYS` (this skill)
2. Optional fixed select (portrait click from `fixed-ui-click-map`, with header proof)
3. `Ctrl+Shift+C` via `scripts.diy_skill_force._toggle_cheat_console`
4. Refocus `live.cheat_console_strip` and confirm white strip before any `type_text`

Plan: `python -m scripts.fixed_ui_click_map handoff` / `plan_arm_to_console_handoff`.

## Fixed-UI click tracking

Record every fixed-HUD click (`python -m scripts.fixed_ui_click_map record …`). Known miss: clicking ~`(300,1045)` opens the household **calendar**, not a Sim portrait.

## Code owners

- Plan step: `betterinstincts.diy_skill_force.plan_live_hotkey_arm` → `ARM_LIVE_HOTKEYS`
- Live helper: `scripts.diy_skill_force._arm_live_hotkeys` (called before Space in household traverse)
- Handoff: `plan_arm_to_console_handoff` / `contracts/fixed-ui-click-map.v1.json`
- Contract: `contracts/diy-skill-force.v1.json` → `live_hotkey_arm` / `household_traverse.arm_before_space`
