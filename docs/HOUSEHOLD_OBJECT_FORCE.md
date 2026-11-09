# Household Object Force — durable useful-item catalog

**Owner:** `contracts/household-object-force.v1.json` and `betterinstincts/household_object_force.py`.  
**CLI:** `python -m scripts.household_object_force`.  
**Proof ceiling:** offline library plans only — not live spawn certification, not BI-002 closure.

## Operator correction (binding)

`bb.showhiddenobjects` is **elementary** to unlocking the hidden items on the operator useful-item list. TwistedMexi’s Better BuildBuy (BBB), career promote alone, MCCC, and `objects.gsi_create_obj` with hallucinated hex IDs are **not** substitutes for that unlock.

## Why this exists

Chat recipes for “force these objects into any household” must not stay trapped in a conversation. This is the repository-native, reusable catalog + planner for:

| id | Item | Delivery |
| --- | --- | --- |
| `out_of_this_world_desktop` | Out of This World Desktop | `careers.promote techguru` → L10 eSports |
| `cruelty_free_meat_wall` | Cruelty-Free Meat Wall | `careers.promote careers_Adult_CivilDesigner` → L5 Green Technician |
| `ufo_bed` | UFO Bed (Retro Rocket Bed) | `careers.promote astronaut` → L10 Smuggler |
| `captain_sigma_statue` | Captain Sigma Statue | `careers.promote astronaut` → L8 Space Ranger |
| `positronic_pro` | Positronic Pro (Magnetic Knife Rack) | `careers.promote culinary` → L6 Chef (optional) |
| `eco_matic_smog_vacuum` | Eco-Matic Smog Vacuum | catalog search **after** elementary unlock |
| `hydroponic_planter` | Hydroponic Planter | catalog search **after** elementary unlock |

Career rewards deposit into **Household Inventory** (large objects cannot live in a Sim’s pocket). Fabrication / hidden catalog items require the elementary unlock, then observed Build/Buy search. BBB’s Organized Debug filter is **optional UX** when the vanilla debug catalog is blank — only after `bb.showhiddenobjects`.

## Forbidden

- Hallucinated `objects.gsi_create_obj` hex instance IDs  
- Treating BBB as a replacement for `bb.showhiddenobjects`  
- Skipping elementary unlock for catalog/hidden list items  
- `buydebug` nickname or slash-joined console lines  
- Pocket inventory for large objects  
- Autorun, game-speed thrash, user-save edits  

## CLI

```sh
python -m scripts.household_object_force catalog
python -m scripts.household_object_force catalog --include-optional
python -m scripts.household_object_force elementary-unlock
python -m scripts.household_object_force plan --item-id all
python -m scripts.household_object_force plan --item-id eco_matic_smog_vacuum,hydroponic_planter
python -m scripts.household_object_force plan --item-id ufo_bed,captain_sigma_statue
```

Library plans always set `execute_allowed: false`. Live console input still needs disposable-lab consent, exact-build consultation, scene/presence lease, and per-step `screen_admit` on the Windows host.

## Factoring (P124)

Sibling to `funds_inject` (household inject pattern), `curious_catalog` (gardening shelves), and `hidden_object_discovery` (P04 debug browse). Does **not** rewrite those owners. Extends shared vocabulary `SHOW_HIDDEN_OBJECTS` as the elementary unlock for this catalog’s hidden/fabrication rows.

## Related

- [Curious Catalog](CURIOUS_CATALOG.md) — rare/money gardening shelves  
- [Hidden Object Discovery](HIDDEN_OBJECT_DISCOVERY.md) — general debug browse / P04  
- [Host funds](../contracts/host-funds.v1.json) — household money inject pattern  
