# Host UI chrome map — regions, hotkeys, catalog deposit

**Owner:** `contracts/ui-chrome.v1.json` and `betterinstincts/ui_chrome.py`.
**CLI:** `python -m scripts.ui_chrome`.
**Peers:** `docs/UI_MODE.md` (mode classification), `docs/HOUSEHOLD_OBJECT_FORCE.md` (useful-item catalog), `docs/HOUSE_STATE.md` (`BACKSPACE_TO_INVENTORY`).
**Proof ceiling:** normalized maps + hotkey glossary offline only — not live click or key certification, not BI-002 closure.

## Why this exists

Agentic screenshot clicking keeps missing Build/Buy chrome (search field vs lot-name banner, inventory tab vs category icons). Operators need **named targets by definition**, a **hotkey glossary per mode**, and **recipes** (AOK Bloomer → Household Inventory) that host logic can execute after independent admission — not vision guesswork.

## Input preference (interop)

**HOTKEY_FIRST_WHEN_EQUIVALENT:** prefer catalogued hotkeys / `KEY` chords over `CLICK_TARGET` whenever an equivalent exists. Keyboard effects still require the cooperative 15s idle gate, but they do not relocate the cursor into chrome/lot fights with the operator. Mouse remains `MOUSE_FALLBACK` only when no catalogued hotkey exists (search focus, first result, inventory tab today). Hotkeys never prove mode or grant `execute_allowed`.

## P95 call stack

`ui_mode.evaluate_mode` → require BUY/BUILD → `ui_chrome.plan_catalog_to_inventory` (hotkey-first rewrite) / `resolve_target` → adapter prefers `send_key_chord` then mouse fallback → (future) admitted SendInput. Live phone / needs / career / skills panels are **declared stubs** so the map can extend without a second daemon.

## Coordinate space

Normalized client fractions `[0,1]×[0,1]`, origin top-left, keyed by resolution profile (`1920x1080` candidate from Bargain Bend Build host). Absolute pixels are derived only when the caller supplies live client width/height.

Search field candidate (1920×1080) is client **(140, 864)** (`nx=0.0729`, `ny=0.8000`). After every chrome click, score with `python -m scripts.click_error_eval against-chrome …`; **NEAR_MISS/MISS → Escape-cancel** (do not continue the recipe into the lot). Cursor computer-use canvas coords are not client pixels — convert before scoring.

## Fixed-UI click map (learn coordinates over time)

**Owner:** `contracts/fixed-ui-click-map.v1.json`, `betterinstincts/fixed_ui_click_map.py`, CLI `python -m scripts.fixed_ui_click_map`.
**Rule:** every agent click on **fixed HUD** must be recorded with `target_id` + `client_xy` + classification (`HIT` / `NEAR_MISS` / `MISS` / `WRONG_CONTROL`). Wrong-control misses (e.g. intended household portrait → opened calendar at ~`(300,1045)`) must not rewrite the intended target’s attested coords. **Moving** world/Sim bodies are out of scope — separate system.

**Miss causes (learn over time):** geometry alone is not enough — also label `miss_cause` via `python -m scripts.click_miss_cause classify|ingest-parts-buy|summarize` (`contracts/click-miss-cause.v1.json`). Priority: `PEER_HUD_COLLISION` → `OVERLAY_CLEAR_WIPE` → `STALE_SURFACE` → `WRONG_CONTROL` → `ZOOM_INSUFFICIENT` → `LOT_PUNCH_THROUGH` → `HITBOX_DRIFT`. Feature vectors are pinned for future ML; RULE_V1 is not a trained model. Peer Skills vs phone fights must not be “learned” as hitbox drift.
**Handoff:** `ARM_LIVE_HOTKEYS` (left-click world focus, right-click cancel options) → `CHEAT_CONSOLE` (`Ctrl+Shift+C`) → white-strip confirm before `type_text`. Plan: `python -m scripts.fixed_ui_click_map handoff`.

## Escape / U host-forensics boundary (2026-11-10)

**Do not equate ESC with game-time pause.** EA lists **Esc = Cancel** and **P / 0 / \` = Pause**. Esc may dismiss a held object or active modal, and may open Options when nothing consumes it. The historical id `PAUSE_MENU` is retained for callers, but it is context-sensitive, never a certified direct time-control action or evidence that a physical key is remapped. Never send repeated Esc presses to "force" a pause menu, and never unpause to retry.

**U** maps to the **Clubs panel** only when the Get Together entitlement, Live scene, game focus, and hotkey-arm conditions are independently met. An absent panel is not proof that Windows has disabled U. The catalog neither registers nor remaps any physical keyboard shortcut.

For a non-mutating operator-host test, see `docs/PERIPHERAL_INCIDENT.md#escapeu-selective-game-input-forensic-matrix`. Offline tests validate semantic and synthetic key-up safety, not local game behavior or Cursor-session responsibility.

## Hotkeys (intent / glossary)

| Mode | Chord | Effect | Notes |
| --- | --- | --- | --- |
| LIVE | F1 | Request Live | Never proves mode |
| BUY | F2 | Request Buy | Never proves mode |
| BUILD | F3 | Request Build | Never proves mode |
| BUY/BUILD | Backspace | Deposit held object to Household Inventory | Requires hold; do not place |
| BUY/BUILD | Esc | Cancel hold | May open MENU if nothing held |
| Any | Ctrl+Shift+C | Cheat console | One command per line |
| BUY/BUILD | Ctrl+Z | Undo | |
| LIVE | M | Phone (candidate) | Unverified / locale-sensitive |
| LIVE | **Z** | **CAMERA_ZOOM_IN** | KEY preferred; scroll wheel also zooms in. **Not** right-click. |
| LIVE | **X** | **CAMERA_ZOOM_OUT** | KEY preferred; scroll wheel also zooms out. |
| LIVE | Enter | Center active Sim once | Not zoom |
| LIVE | Shift+Enter | Center lot once | Not zoom |

**ZOOM_MODE ≠ ZOOM_CONTROL (operator 2026-11-10):** `RIGHT_CLICK_VIEW` is a zoom-*ladder mode* (0.85 of max close) plus portrait-follow posture. Reaching that distance uses **Z** / wheel — never RMB as the zoom actuator. World-object pick: traverse → zoom in → screenshot → identify (`OBJECT_PICK_IDENTIFY` in `docs/CAMERA_TRAVERSE.md`).

## AOK Bloomer recipe

Preferred catalog search term is **`A-OK`** (hyphenated; bare `AOK` returns no results). Operator phrases **`wall shelf`**, **`vertical garden`**, and **`bloomer`** are synonyms of `a_ok_bloomer` — never a separate wall-shelf product.

```sh
python -m scripts.ui_chrome resolve-item --query "wall shelf"
python -m scripts.ui_chrome plan --item-id "wall shelf" --mode BUILD --client 1920 1080
python -m scripts.ui_chrome plan --item-id a_ok_bloomer --mode BUILD --client 1920 1080
python -m scripts.ui_chrome resolve --mode BUILD --target catalog.search_field --client 1920 1080
python -m scripts.ui_chrome glossary
```

Plan steps: focus search → type `AOK` (live host may need `a-ok` + Outdoor Activities autocomplete when bare `AOK` returns empty) → select A-OK-Bloomer Vertical Garden → observe hold → Backspace → open Household Inventory → observe item. `execute_allowed` stays false until P08-calibrated host admission. Forbids lot placement and pocket inventory.

Civil Designer L5 unlocks **Grow Cruelty-Free Meat** on this planter; the planter itself is an ordinary Eco Lifestyle catalog purchase (~§365).

## Selected-Sim whim pin / unpin slots

Far-left selected-Sim bubbles — left of household portraits, above the notebook/phone tray. Usually **2 or 3** scalloped thought-clouds; rare **4th** is a **jagged starburst** by the Sim’s left shoulder (viewer-right of the avatar). Mouse-only.

Three nested geometries (do not conflate):

1. **Bubble outline** — thought-cloud or jagged starburst (container)
2. **Content thumbnail** — circular art *inside* the bubble (whim subject) — **not** the pin
3. **Pin thumbtack** — small circular badge on the **lower-right rim** of the outline; offset **(+30, +6)** from bubble center; green when pinned

| Slot | Bubble `client_xy` | Pin thumbtack `client_xy` | Status |
| --- | --- | --- | --- |
| 0 left | **(145, 833)** | **(170, 847)** | Measured cloud + green pin |
| 1 mid | **(203, 827)** | **(233, 833)** | Cloud measured; pin via (+30,+6) |
| 2 third | **(255, 830)** | **(285, 836)** | Estimated when three present |
| 3 jagged 4th | **(278, 900)** | **(308, 906)** | Rare jagged PrintWindow-measured (paused) |

Slot seeds do not authorize a live pin — `whim_pinning` still requires per-whim attestation + native queue.

## Center console (time / speed / environment)

Bottom-center pill (`fixed-ui-click-map.center_console_1920x1080`). **Prefer speed hotkeys** P/0, 1, 2, 3.

| Control | `client_xy` | Prefer |
| --- | --- | --- |
| Pause | **(889, 1033)** | P / 0 |
| Play 1x | **(920, 1033)** | 1 |
| Fast 2x | **(952, 1033)** | 2 |
| Ultra 3x | **(984, 1033)** | 3 |
| Camera shutter | **(1040, 1033)** | — |
| Day/night | **(860, 1065)** | — |
| Clock / calendar text | **(930, 1065)** | ≠ BL Show Calendar `(305,1055)` |
| Weather | **(1010, 1065)** | — |
| Thermometer | **(1045, 1065)** | — |
| Eco footprint | **(1075, 1065)** | — |

## Skills panel burger bar (expand / collapse)

Open Skills with **L**. The resize grip is the two short horizontal lines on the thin grey strip **directly above** green `SKILL MASTERY PERKS`. Scrollbar alone is not a full list read. PrintWindow endpoints (`fixed-ui-click-map.skills_burger_bar_1920x1080`, 1920×1080):

| State | target_id | client_xy |
| --- | --- | --- |
| MIN (default flyout) | `live.skills_burger_grip_min` | **(1722, 810)** |
| MAX (expanded) | `live.skills_burger_grip_max` | **(1722, 225)** |

Expand: stepped LMB drag min→max (`plan_skills_burger_expand` / `win32_input.left_drag`). Collapse: max→min. Remeasure if the green header Y drifts.

## Top-right Live HUD chrome

PrintWindow-measured 1920×1080 (`fixed-ui-click-map.top_right_hud_1920x1080`). **Cheat console white strip overlays this band** when open — prefer hotkeys and precise strip refocus before typing.

| Control | target_id | client_xy | Prefer |
| --- | --- | --- | --- |
| Build/Buy | `live.top_build_buy` | **(1504, 22)** | F3 |
| Manage Worlds | `live.top_manage_worlds` | **(1562, 22)** | — |
| Gallery | `live.top_gallery` | **(1609, 22)** | F4 |
| EA Store | `live.top_ea_store` | **(1650, 22)** | — |
| Floor story | `live.top_floor_story` | **(1707, 22)** | — |
| Walls view | `live.top_walls_view` | **(1740, 22)** | — |
| Camera/house | `live.top_camera_lot_house` | **(1768, 22)** | — |
| Lessons/help | `live.top_lessons_help` | **(1801, 22)** | — |
| Video capture | `live.top_video_capture` | **(1838, 22)** | — |
| Notifications | `live.top_notification_inbox` | **(1859, 22)** | — |
| Options … | `live.top_options` | **(1898, 22)** | Esc (careful) |
| Live people (Build exit) | `live.top_live_people` | **(1585, 35)** | F1 |

## Escape menu Save / Save As (1920×1080)

Owner: `fixed-ui-click-map.escape_menu_1920x1080`, loader `load_escape_menu_coords` / `plan_escape_menu_save`. Live-measured 2026-11-10 (`dist/game-host/horizon-exec-20261110/`).

| Row | target_id | client_xy | Hazard |
| --- | --- | --- | --- |
| Options gear | `live.top_options` | **(1898, 22)** | Opens MENU chrome |
| Save | `live.escape_menu_save` | **(960, 420)** | In-place save — not for new lab slots |
| Save As | `live.escape_menu_save_as` | **(960, 422)** | **Only 2px below Save** — inside default hit radius; never confuse intents |

**SAVE GAME dialog:** click **ADD NEW SAVE** (top green+ row) only. **Never** click existing save rows, **Delete**, or **Overwrite**. `live.save_game_add_new_save` coords remain **UNMEASURED** until next capture.

## Top-left Discovery Quest tabs

Gift-box tab pill, top-left. PrintWindow-measured on 1920×1080; also `discovery-hud.tab_slots_1920x1080` and `fixed-ui-click-map`.

| Tab | target_id | client_xy | Status |
| --- | --- | --- | --- |
| Lifelong Aspirations | `live.discovery_tab_lifelong_aspirations` | **(26, 34)** | Present |
| Navigating Needs | `live.discovery_tab_navigating_needs` | **(60, 34)** | Present |
| You and Your Phone | `live.discovery_tab_you_and_your_phone` | **(99, 34)** | Present |
| Work/School/Party event | `live.discovery_tab_event_context` | **(135, 34)** | Estimated — appears for events; remeasure Live |

Tab click ≠ quest completion. Fourth slot is empty until work/school/party (or similar) adds it.

## Bottom-left utility tray (notebook / phone / Show Calendar)

Grey pill immediately left of household portraits on 1920×1080. PrintWindow-measured; also in `contracts/fixed-ui-click-map.v1.json`.

| Control | target_id | client_xy | Notes |
| --- | --- | --- | --- |
| Notebook | `live.notebook` | **(258, 1055)** | Leftmost; spiral notebook |
| Phone | `live.phone` | **(282, 1055)** | Middle; hotkey `M` (unverified) |
| Show Calendar | `live.show_calendar` | **(305, 1055)** | Rightmost; portrait clicks with x&lt;330 often hit this |

Calendar dismiss: `live.calendar_close_x` ≈ **(1445, 255)**. Do not rediscover these by vision thrash.

## Live bottom-right panel letter hotkeys

Catalogued under `modes.LIVE.hotkeys` (`family: BOTTOM_RIGHT_LIVE_PANEL`) and `ui-microsystems.bottom_right_panel_hotkeys`. Prefer letter hotkeys over tray icon clicks. Requires **live-hotkey-arm** (LMB world → RMB cancel) first.

| Panel | Key | hotkey_id |
| --- | --- | --- |
| Aspirations / Satisfaction | G | `PANEL_ASPIRATIONS` |
| Career / work / school | J | `PANEL_CAREER` |
| Skills | L | `PANEL_SKILLS` |
| Relationships | R | `PANEL_RELATIONSHIPS` |
| Personal inventory | I | `PANEL_INVENTORY` |
| Simology | Y | `PANEL_SIMOLOGY` |
| Needs | O | `PANEL_NEEDS` |
| Clubs / groups | U | `PANEL_CLUBS` (pack-gated candidate) |

Aliases: `work`/`school` → career; `inventory` → personal_inventory; `motives` → needs; `groups` → clubs.

```text
python -c "from betterinstincts.ui_microsystems import plan_open_bottom_right_panel; print(plan_open_bottom_right_panel('work'))"
```

Hitboxes remain uncalibrated until Live P08; hotkey open is not proof the panel is visible.

## Extension surface

Phone-app chrome and exact BR hitboxes still need operator-attested screenshots. Do not invent click points for `UNCALIBRATED_STUB` panels when a catalogued hotkey exists.

## Related

- [UI Mode](UI_MODE.md) — F1/F2/F3 scene-backed mode context
- [Household Object Force](HOUSEHOLD_OBJECT_FORCE.md) — career / elementary unlock catalog
- [Curious Catalog](CURIOUS_CATALOG.md) — gardening shelves including vertical garden
- [House State](HOUSE_STATE.md) — `BACKSPACE_TO_INVENTORY` mutating action

## Live local-game execution handoff

The [A-OK Bloomer Household Inventory P04 handoff](handoff/BI-AOK-BLOOMER-INVENTORY-P04-2026-11-09.md) binds this evaluate-only recipe to exact-build calibration, player-safe host admission, one-at-a-time inputs and independent in-game inventory verification. A plan or GitHub merge cannot count as the deposit succeeding. The local agent, not this GitHub provider, performs the live transaction on an explicitly authorized disposable LAB save.


## Live camera keyboard and app-only follow event (P95/P124)

The sole native hotkey registry remains contracts/ui-chrome.v1.json: CENTER_ACTIVE_SIM = Enter (native one-shot); CENTER_CURRENT_LOT = Shift+Enter (native lot); SELECT_NEXT_HOUSEHOLD_SIM = Space (changes Sim selection, never invoked implicitly). The app-scoped BI_FOLLOW_ACTIVE_SIM = Ctrl+Alt+Shift+F is a **proposed local shortcut event** for FOLLOW_ACTIVE_SIM. It is **not** registered in Windows or The Sims 4. betterinstincts.ui_chrome.resolve_app_hotkey accepts only an injected, explicitly opted-in APP_SCOPED_HOST_HOTKEY event; it never monitors, intercepts or registers keys.

betterinstincts.sim_camera owns camera semantics and single-effect queueing; scripts.sim_camera owns injected code ports and optional Sims4CommunityLib compatibility. Existing screen_admit and workflow_interop own player idle/desktop arbitration. No fallback portrait right-click, no global keyhook or automatic camera lock. See CAMERA_TRAVERSE.md, Active-Sim camera section.
