# Host UI chrome map — regions, hotkeys, catalog deposit

**Owner:** `contracts/ui-chrome.v1.json` and `betterinstincts/ui_chrome.py`.
**CLI:** `python -m scripts.ui_chrome`.
**Peers:** `docs/UI_MODE.md` (mode classification), `docs/HOUSEHOLD_OBJECT_FORCE.md` (useful-item catalog), `docs/HOUSE_STATE.md` (`BACKSPACE_TO_INVENTORY`).
**Proof ceiling:** normalized maps + hotkey glossary offline only — not live click certification, not BI-002 closure.

## Why this exists

Agentic screenshot clicking keeps missing Build/Buy chrome (search field vs lot-name banner, inventory tab vs category icons). Operators need **named targets by definition**, a **hotkey glossary per mode**, and **recipes** (AOK Bloomer → Household Inventory) that host logic can execute after independent admission — not vision guesswork.

## P95 call stack

`ui_mode.evaluate_mode` → require BUY/BUILD → `ui_chrome.resolve_target` / `plan_catalog_to_inventory` → adapter maps normalized fractions to client pixels → (future) admitted SendInput. Live phone / needs / career / skills panels are **declared stubs** so the map can extend without a second daemon.

## Coordinate space

Normalized client fractions `[0,1]×[0,1]`, origin top-left, keyed by resolution profile (`1920x1080` candidate from Bargain Bend Build host). Absolute pixels are derived only when the caller supplies live client width/height.

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

Preferred catalog search term is **`AOK`** (not `a-ok` / `bloomer` as primary).

```sh
python -m scripts.ui_chrome plan --item-id a_ok_bloomer --mode BUILD --client 1920 1080
python -m scripts.ui_chrome resolve --mode BUILD --target catalog.search_field --client 1920 1080
python -m scripts.ui_chrome glossary
```

Plan steps: focus search → type `AOK` → Enter → click first result → observe hold → Backspace → open Household Inventory → observe item. `execute_allowed` stays false until P08-calibrated host admission. Forbids lot placement and pocket inventory.

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
