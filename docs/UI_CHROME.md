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

## Extension surface

Add Live bottom-right panel cells and phone-app chrome as new targets under `modes.LIVE` once operator-attested screenshots exist. Do not invent click points for `UNCALIBRATED_STUB` panels.

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
