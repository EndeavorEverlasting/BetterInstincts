# Upgrade-parts force — spam-buy Robot Salvage Parts

**Prompt:** TokenCorridor P95 — Program Design & Call-Stack Prototype Architect  
**P124:** sibling owner beside `diy_skill_force` / `funds_inject` / `household_object_force` / `ui_chrome`  
**Machine owner:** [`contracts/upgrade-parts-force.v1.json`](../contracts/upgrade-parts-force.v1.json)  
**Planner:** `betterinstincts.upgrade_parts_force`  
**CLI:** `python -m scripts.upgrade_parts_force`

## Why this exists

Gardener-Bot **Tune Up** fails when the Sim is missing **Robot Salvage Parts** (observed: Charlee needed **4**). The buy path is easy to forget:

**Any computer → Order → Purchase Upgrade Parts → Robot Salvage Parts**

Parts deliver straight into the Sim’s **pocket inventory**. This is not a Build/Buy catalog row and not a Household Inventory deposit.

## Paths

| Path | What it does | Mode | Notes |
| --- | --- | --- | --- |
| `computer` | Spam-buy via Order → Purchase Upgrade Parts × quantity | LIVE | Default. Default quantity **20** (craft-scale); use `--quantity 4` for one Tune Up. |
| `spawn` | `testingcheats enabled true` → Shift+click Dr. F robotics workstation → **Spawn Crafting Supplies** | LIVE | Lab bulk (~50 each). Planning hint only until P08 Shift+click is calibrated. |

Forbidden: hallucinated `gsi_create_obj` hex, Build/Buy search for pocket parts, autorun, save edits, claiming BI-002 from a plan.

## CLI

```text
python -m scripts.upgrade_parts_force catalog
python -m scripts.upgrade_parts_force how-to-buy
python -m scripts.upgrade_parts_force how-to-buy --part robot_salvage_parts
python -m scripts.upgrade_parts_force plan --part robot_salvage_parts --quantity 20
python -m scripts.upgrade_parts_force plan --part "gardener bot parts" --quantity 4 --checklist
python -m scripts.upgrade_parts_force plan --path spawn --part robot_salvage_parts
```

Library plans keep `execute_allowed=false`. Live pie-menu / Shift+click SendInput requires independent `screen_admit` + disposable lab proof (P08 OPEN).

## Synonyms

`gardener bot parts`, `tune up parts`, `robot salvage`, `salvage parts` resolve to `robot_salvage_parts`.

## Proof ceiling

`HOST_UPGRADE_PARTS_PLAN_NOT_LIVE_INVENTORY_CERT` — offline plans and operator checklists only until a live inventory delta is independently observed.
