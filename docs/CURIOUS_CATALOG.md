# Curious Catalog — rare / money gardening shelves (P95 + trifecta)

Machine owner: [`contracts/curious-catalog.v1.json`](../contracts/curious-catalog.v1.json).
CLI: `python -m scripts.curious_catalog`.

## Outcome

On-whim access to hidden Buy shelves for **alien fruit, rare seeds, hydroponics**, and other high-value grow gear — without autorun, without slash-joined console paste, and **without touching game speed**.

## Activation (going forward)

```sh
python -m scripts.curious_catalog activate --session-id lab-curious
python -m scripts.curious_catalog shop-list          # money-tier shopping list
python -m scripts.curious_catalog plan               # console lines only
python -m scripts.curious_catalog deactivate --session-id lab-curious
```

### In-game (paused Buy Mode)

1. Keep the game **Paused** (never press 1/2/3 or `` ` ``).
2. Buy Mode (F3 / hammer).
3. `Ctrl+Shift+C`
4. Line 1: `testingcheats enabled true` → Enter
5. Line 2: `bb.showhiddenobjects` → Enter
   - **Never** type `buydebug` or `bb.showhiddenobjects / buydebug`
6. Search bar: `debug` then `seed` / `Quill` / `Hydroponic` / `Dragon` / `Growfruit` / `Money Tree`

## Money shop list (S-tier first)

| Item | Why | Search |
| --- | --- | --- |
| Rare Plants seed packet | Magic Beans, Cowplant, Dragon Fruit, Death Flower, Orchid, Growfruit | `Rare` / `seed` |
| Quill Fruit | Sixam alien — high value | `Quill` |
| Dragon Fruit | Top sell among rares | `Dragon` |
| Money Tree | Direct Simoleons (Seasons) | `Money Tree` |
| Growfruit / Orchid / Cowplant Berry | High-value staples | name |
| Fang Flower / Orb Plant | Sixam aliens | `Fang` / `Orb` |
| Hydroponic Planter | Futuristic auto-water host | `Hydroponic` |

## Proof ceiling

`HOST_CURIOUS_CATALOG_OPT_IN_CHEAT_DISPATCH_NOT_MOD_UI_NOT_BI002_CERT`.
Live placement remains operator Buy Mode; host must never advance sim speed.

## General hidden objects (separate host service)

The gardening/rare-seed Curious Catalog above is **not** a complete debug-object browser. The generic opt-in discovery service at [HIDDEN_OBJECT_DISCOVERY.md](HIDDEN_OBJECT_DISCOVERY.md) handles toothbrushes, dishes, crystals, ponds, invisible lights, world cars, streetlights and trees. Its contract is `contracts/hidden-object-discovery.v1.json`, planner is `betterinstincts/hidden_object_discovery.py`, and CLI is `python -m scripts.hidden_object_discovery`. It uses the player's requested `testingcheats true` → `bb.showhiddenobjects` sequence, with optional `bb.showliveeditobjects`, and inspects actual item prices rather than assuming all are free. It neither autoruns nor replaces this money-garden path. Existing `curious_catalog` code/receipts remain authoritative for the gardening shelf.
