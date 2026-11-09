# Household DIY parts budget — pocket stock for every Sim (N)

**Prompt:** TokenCorridor P95 — Program Design & Call-Stack Prototype Architect
**P124:** expand existing `upgrade_parts_force` (peer to `diy_skill_force` household traverse)
**Machine owner:** [`contracts/upgrade-parts-force.v1.json`](../contracts/upgrade-parts-force.v1.json) v2
**Planner:** `betterinstincts.upgrade_parts_force`
**CLI:** `python -m scripts.upgrade_parts_force`

## Goal

Every household Sim (observed portrait count **N**) keeps DIY building parts in **personal pocket inventory** so crafts / Tune Up still work when another member is at work or removed. Shared Household Inventory is the wrong destination for these materials.

## Scalable acquisition (preferred order)

1. **spawn** — `testingcheats` → Shift+click Dr. F robotics workstation → **Spawn Crafting Supplies** (~50 each; one action stocks most DIY materials).
2. **computer** — Computer/laptop → Order → Purchase Upgrade Parts (local, offline).
3. **phone** — Phone → Order → Purchase Upgrade Parts (buyable rows) **only if it stays offline**.

**Offline install (P00/P01):** never press **Connect** on `CONNECTION IS REQUIRED`. Choose **Stay Offline** only. Prefer spawn when phone forces an online gate. The game plays as installed offline.

Buy Mode debug catalog is **not** the preferred stock path.

## DIY builder kit

| Part | Buyable via Order? | Default path |
| --- | --- | --- |
| Common Upgrade Parts | yes | spawn |
| Electronic Upgrade Parts | yes | spawn |
| Plumbing Upgrade Parts | yes | spawn |
| Kitchen Upgrade Parts | yes | phone |
| Robot Salvage Parts | yes | spawn |
| Computer Chip | no (spawn/craft) | spawn |
| Mechanism | no (spawn/craft) | spawn |

Optional pack row: Eco-Upgrade Parts (often missing from Order).

Default budget target: **20** of each kit part per Sim (spawn bulk ~50 satisfies this).

## CLI

```text
python -m scripts.upgrade_parts_force budget
python -m scripts.upgrade_parts_force household --members 4 --path spawn --checklist
python -m scripts.upgrade_parts_force how-to-buy --part robot_salvage_parts
python -m scripts.upgrade_parts_force plan --part electronics --path phone --quantity 20
python -m scripts.upgrade_parts_force record --run-id diy-parts-lab-001 --members 4 --member-slot 0 --part-id robot_salvage_parts --observed-count 50
python -m scripts.upgrade_parts_force status --run-id diy-parts-lab-001
python -m scripts.upgrade_parts_force certify --members 4 --observations obs.json
```

`--members N` must match the Live portrait strip. Host never invents household size.

## Machine-readable live certification

Receipt schema `betterinstincts.diy-parts-budget.cert/v1` under `dist/diy-parts-budget/<run-id>/`.

Per part states: `UNKNOWN` | `SHORT` | `MET`. Aggregate: `UNPROVEN` | `PARTIAL` | `ALL_MEMBERS_MET_REVIEW_REQUIRED`.

Plans alone never certify. `MET` requires independently attested pocket counts ≥ target for every diy_kit part on every member. Even `ALL_MEMBERS_MET_REVIEW_REQUIRED` stays `certified=false` until human/agent review.

## Proof ceiling

`HOST_DIY_PARTS_BUDGET_PLAN_AND_CERT_SCHEMA_NOT_BI002` — offline plans + cert schema; live SendInput / inventory OCR remain P08. Does not close BI-002.
