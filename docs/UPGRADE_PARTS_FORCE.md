# Household DIY parts budget — pocket stock for every Sim (N)

**Prompt:** TokenCorridor P95 — Program Design & Call-Stack Prototype Architect
**P124:** expand existing `upgrade_parts_force` (peer to `diy_skill_force` household traverse)
**Machine owner:** [`contracts/upgrade-parts-force.v1.json`](../contracts/upgrade-parts-force.v1.json) v3
**Planner:** `betterinstincts.upgrade_parts_force`
**CLI:** `python -m scripts.upgrade_parts_force`

## Goal

Every household Sim (observed portrait count **N**) keeps DIY building parts in **personal pocket inventory** so crafts / Tune Up still work when another member is at work or removed. Shared Household Inventory is the wrong destination for these materials.

## Scalable acquisition (preferred order)

1. **spawn** — `testingcheats` → Shift+click Dr. F robotics workstation → **Spawn Crafting Supplies** (~50 each; one action stocks most DIY materials).
2. **computer** — Computer/laptop → inspect its interactions → discover the nested **Purchase Upgrade Parts** module (offline; intermediate names/depth must be observed, not assumed).
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


## 2026-11-10 — verified menu, command and player sovereignty

The operator located the **Purchase Upgrade Parts** module deep inside the
interactions of a computer. The *purchase-menu catalog* has exactly five
operator-reported options: Common, Electronic, Kitchen, Plumbing, and Robot
Salvage Upgrade Parts. Computer Chips, Mechanisms and optional Eco-Upgrade
Parts are separate DIY/pack materials, **not** asserted menu rows.

Machine contract: `contracts/upgrade-parts-force.v1.json#computer_purchase_menu`.
Host proposal + cooperative queue adapter:
`betterinstincts/computer_upgrade_parts.py`. Existing DIY budget,
spawn alternative, planner and certification remain owned by
`betterinstincts/upgrade_parts_force.py` — no parallel commerce daemon.

```sh
python -m scripts.upgrade_parts_force computer-menu
python -m scripts.upgrade_parts_force computer-intent --part kitchen_upgrade_parts --quantity 2
```

These commands are **passive** and never move the cursor. At an explicitly
activated Live session the host must observe the selected Sim, paused Live
mode, active-lot computer and safe footprint, and choose a verified native
game API or an explicitly opted-in desktop fallback. It may propose clicking
the observed computer. It must then discover the visible nested labels,
accept only observed `Purchase Upgrade Parts`, `Order` or `More Choices...`
where they actually appear, and re-observe after each selection. The
`More Choices` label can recur on distinct pages; repeated page fingerprints
and >16 pages fail closed. An unknown submenu means **wait for evidence**,
not a guessed click or a hardcoded coordinate.

For each unit, verify an actual part row, spending consent, observed price,
funds, approved spend cap and personal-inventory baseline before confirming.
One purchase must show an inventory increase **before** another unit is
considered. Each single action goes through
`CooperativeScreenQueue.enqueue_effect` with fresh scene validation and two
idle probes. Human mouse, keyboard, voice or other-app activity yields;
interrupted or unknown purchases require observed reconciliation, never
blind replay. Boot is passive, and a command does **not** authorize OS
service, Bluetooth, adapter/driver, pairing, UAC or peripheral-preference
changes. Preserve offline installation; never EA Connect.

P95 architecture → P82 offline falsifiers → P08 local runtime proof
(**unavailable without the user's explicitly controlled Sims 4 host**) →
P07 existing-owner implementation → P124 readability/cross-layer
regression guard. Unit tests/CI cannot certify an actual in-game purchase.
