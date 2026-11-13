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

## 2026-11-10 — universal observed Order domains and eco/fuel source routing

The [acquisition routing guide](ACQUISITION_ROUTING.md) extends this existing module across any attested active household and selected portrait, including interactive Order menus whose **Order** entry or nested domain can require variable **More Choices** paging. Reinspect each page, detect loops, and select only visible labels; a previously observed "two More Choices" is a hint, not a fixed instruction. The upstream five-item computer menu remains owned by `betterinstincts/computer_upgrade_parts.py` and its existing CooperativeScreenQueue dispatch/spend-cap/readback gates; `betterinstincts/upgrade_parts_force.py` adds read-only cross-source planning, not a second clicker.

`Eco-Upgrade Parts` route to the Fabricator (15 bits + 10 pieces per attempt). Generator fuel is a refill via recycled bits/pieces. Biofuel-filled cans route to an insect farm's observed Collect Bio Fuel interaction, which is readiness/time dependent. Neither fuel category is assumed to be sold in the computer purchase picker. The typed contract is `contracts/upgrade-parts-force.v1.json#acquisition_routing`, with ontology `OBSERVED_MENU_ROUTE`, `ACQUISITION_SOURCE`, `ACTION_EFFECT_CLASS` and tests `tests/test_acquisition_integration.py`.

Run `python -m scripts.upgrade_parts_force sources`, `acquisition --portraits ... --requests ...`, `menu-next --options ... --goal ...`, or `order-domain --portraits ... --domain ... --item ...` for **evaluate-only** source plans. An immediate-order candidate is not proof that the Sim received stock; follow the existing fresh scene, spend approval, pocket/funds-delta and player control gates. No protected saves, Build/Buy mutation, online Connect, OS services or Bluetooth changes.


### 2026-11-10 Closers correction — Order-first is mandatory in the live executor

The computer menu has **two independently observed phases**: `menu_scope=ROOT` may select `Order` only after it is visible (using bounded `More Choices` if necessary), then `menu_scope=ORDER` requires `order_menu_observed=true` before selecting the actual `Purchase Upgrade Parts` domain. A direct-looking part-purchase label in the root is **not** permission to skip Order. Re-read menu after every click; no hardcoded “two More Choices.” Every effect still requires the shared `CooperativeScreenQueue` lease, current selected portrait, explicit spend approval, fresh price/funds/cap/inventory baseline, and post-purchase pocket-stock receipt. See `docs/ACQUISITION_ROUTING.md` and `tests/test_computer_upgrade_parts.py`. Both games/live host and Windows Cursor activation remain unobserved in provider CI.


## 2026-11-12 — computer picker: five kinds, one transaction

The operator's screenshot shows one Purchase Upgrade Parts modal with five
rows (Common, Electronic, Kitchen, Plumbing, Robot Salvage), a right arrow on
each row, total count, total cost, available funds, and one bottom confirmation.
The correct model is **one observed shopping cart**, not five separate paid
purchases or an unbounded burst of clicks. The screenshot shows example costs
§10/§120/§90/§30/§5; these are NOT fixed game-price assumptions.

The existing computer_upgrade_parts.py owner now provides
plan_computer_purchase_batch, plan_computer_restock_batch,
propose_computer_batch_step, enqueue_computer_batch_step, and
verify_computer_batch_purchase. This is not another store agent; the older
single-item proposal remains backward-compatible.

The quantity is a **cart selection**. Read all five labeled rows from the
fresh modal, including the current selected count and unit price. Confirm
these reconcile exactly with displayed Total Count and Total Cost. Check
explicit spending authority, observed funds and a total cap sufficient
for the entire requested cart. Propose only one increment of the first
short row, annotated with its expected prior quantity and picker revision.
After every cooperative-queue effect, reobserve the Sim, all rows, total
cost, hitbox and revision. A reused revision, mismatched totals, player
reclaim, missing hitbox, or unexpected selected items must deny.

When the selected quantities exactly match the request, propose exactly
one observed Buy. Afterwards, prove the selected Sim's **personal pocket**
inventory deltas and simoleon debit. Uncertain and partial outcomes require
reconciliation, never blind replay. The cropped screenshot does not furnish
live screen coordinates, a native game API or a valid host input permit.

Read-only commands (no cursor movement, purchase or game launch):

```sh
python -m scripts.upgrade_parts_force computer-batch-intent --requests '{"common_upgrade_parts":2,"robot_salvage_parts":1}'
python -m scripts.upgrade_parts_force computer-restock --targets '{"common_upgrade_parts":20,"robot_salvage_parts":20}' --pocket-counts '{"common_upgrade_parts":18,"robot_salvage_parts":19}'
```

The versioned computer_batch_picker contract is in
contracts/upgrade-parts-force.v1.json. This implementation is **POLICY_ONLY**,
not a functioning installed Sims purchase mod. Native-first gameplay needs
source-inspected exact-build EA tuning/script hooks and a disposable P08
Live Mode observation. A future opt-in restock profile may eliminate further
repeated per-arrow approvals within a preapproved cap; this code never
silently spends or chooses cheats/Spawn Crafting Supplies as a replacement.
No EA Connect or OS/peripheral changes.


## 2026-11-12 — MoonWake Closers: pre-cart proof and immutable dispatch

P83 verified merged #210 but identified two transaction-integrity gaps:
an arrow could be proposed before all five **selected Sim pocket-inventory**
counts were independently observed, and queue admission accepted a stripped
or altered `READY_TO_QUEUE` batch purchase action as long as the picker
callback said yes. These are policy/host-adapter trust-boundary gaps,
**not** evidence that a Sims game purchase was executed.

P03 repaired the existing `betterinstincts/computer_upgrade_parts.py`
owner. The *first arrow* and *Buy* now both require an all-five-part
personal-inventory baseline. Each action receives an observed cart envelope
including unit/total cost, planned quantity, funds, approved spending cap,
fresh picker revision and explicit approval. The cooperative-queue boundary
rejects missing/negative/noninteger limits, cart totals above caps, malformed
increments and Buy when the exact requested cart count/cost has not been met.
The queued action is a frozen **copy** of the admitted receipt: later
mutations to the caller's decision cannot turn an increment into Buy.

The trusted game adapter must **independently** reobserve that receipt's
price/funds, selected Sim, picker revision/rows, scene and current hitbox
immediately before dispatch; callback assertions alone are not proof.
Unknown player activity yields and uncertain purchases reconcile rather
than replay. The route stays POLICY_ONLY under the same
`CooperativeScreenQueue`; no background clicker or EA-native hook was added.

P141 rejected second UI engines and speculative native APIs without the
current exact-patch EA tuning source. P124 kept the one existing code owner,
legacy single-item menu behavior and five-kind calculator. P04's downstream
game-native execution and disposable Live Mode proof remain in
[issue #213](https://github.com/EndeavorEverlasting/BetterInstincts/issues/213);
GitHub provider connectivity does not amount to a local Windows Sims host.
