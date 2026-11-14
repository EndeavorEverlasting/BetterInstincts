# Universal purchase dialogs — bounded, extensible anti-arthritis policy

**Owner:** `contracts/purchase-dialog.v1.json`, `betterinstincts/purchase_dialog.py`. Existing source owners remain `betterinstincts/upgrade_parts_force.py` (observed menu navigation), `betterinstincts/computer_upgrade_parts.py` (verified five-part computer picker), and `betterinstincts/workflow_interop.py` (human-first cooperative effect queue). This is a **policy-only offline capability**, not an installed mod or a background mouse-clicker. The game-native successor is issue #171. BI-002 hunger remains independent.

## Why one dialog engine instead of hand-coded menus?

On 2026-11-14, seven operator screenshots exposed (a) the nectar machine's Purchase Basic Ingredients catalog, (b) Craft Nectar / Purchase Basic Ingredients surface, (c) computer Order domain choices including Purchase Seeds / Oversized Crop Seeds / Medicine, (d) the five oversized seed rows, (e) Medicine priced at §50 and marked 10 owned for that screenshot, and (f/g) two positions in **Purchase Advanced Apothecary Ingredients**, including Lemon above Lightning Root Leaf, Lump of Moss, Sage and Small Critter Bone. Visible named items and prices are fixtures, **not** a claim that the screenshots cover the whole current game or every installed DLC.

The same structured observation schema handles an arbitrary `menu_id` + `source` + `actor_id` across households, portrait slots, game objects, recipes and installed packs. It does not guess hidden rows or click a fixed pixel coordinate. Add future menus through new observed dialog identities, demand evidence and native adapters. Never fork another standalone OS clicker.

## Canonical workflow

1. An **observed need** triggers a desired stock quantity. Valid trigger families include career material, garden seed or ingredient gaps, Handiness upgrade components, Servo/Fixer-Bot repair material, apothecary/nectar/crafting recipes, household restock and explicit player requests. Each requires a current actor, menu, item, observed required quantity, observed owned quantity and evidence reference. The planner purchases only the **positive gap**. Scanning a shop never grants spending permission.
2. Existing observed menu-route logic locates the correct object and visible menu/domain, including `More Choices`. The game operator/host must identify the selected portrait and open that specific actual picker under existing live host policies. A screenshot from a prior session is a test fixture, **not** a current scene permit.
3. The picker reader discovers the entire catalog: if opening mid-list, propose one verified scroll **up** toward the top and re-observe; at top, accumulate uniquely identified rows, then scroll **down** one viewport at a time until an independently observed bottom. This handles overlapping rows (Lemon appears in both screenshots) without duplicate purchases. Repeated pages, missing scroll endpoints, stale revisions, item price/identity changes, missing packs and page bounds stop safely rather than spinning.
4. With a complete observed catalog, `derive_demand` computes the request. The cart state machine checks fresh selected-Sim inventory baseline, observed funds, price/quantity totals, explicit spend cap, player command/authorization, selected portrait, paused Live mode, known scene and verified channel/explicit fallback authorization. It proposes **one increment at a time**, only for a currently observed row and verified increment control. An offscreen requested item triggers a bounded direction-aware scroll and a fresh viewport readback. Every increment requires fresh selected row and global count/cost reconciliation. Final Buy is proposed exactly once.
5. **After** Buy, `verify_dialog_purchase` compares selected-Sim inventory deltas with the exact requested quantities and the household funds debit with the exact expected cost. Uncertain outcomes need reconciliation, never re-buy. Per-portrait/current-household identity must be refreshed before future transactions.
6. A real host adapter, **when independently admitted**, can enqueue a typed proposed atomic effect through `CooperativeScreenQueue.enqueue_effect`, which owns operator-presence/idle, fresh scene and effect checkpoints. If the gamer begins interacting, suspend the effect while preserving intent, and do not replay uncertain effects on resumption. No host adapter is added or activated by this offline policy.

### Literal example from the two advanced apothecary screenshots

The initial viewport can be halfway down the 9 currently pictured unique items. It first seeks the top; then two overlapping observed pages expose Acorn, Aura Petal, Basil, Daisy, Lemon, Lightning Root Leaf, Lump of Moss, Sage and Small Critter Bone, with the screenshot's respective unit prices §35, §7, §11, §12, §30, §70, §9, §15 and §55. If an observed recipe needs 2 Lemons and that Sim has 1 available, the plan requests **1 Lemon**, not 999 of every item. If two offscreen resources are truly required, the engine scrolls toward their cataloged pages and reconciles one cart modification at a time before the single Buy.

## P141 → P95 → P82 → P08 → P07 → P124 evidence boundary

- **P141:** Existing fixed five-row computer-parts picker and cooperative queue are the preferred owners; reject universal clickers, hardcoded coordinates and unapproved blanket purchase.
- **P95:** Catalog scan, evidence-qualified natural trigger, cart/readback, and an existing queue adapter are separate responsibilities.
- **P82:** `tests/test_purchase_dialog.py` exercises multi-page discovery, overlaps, mid-list startup, cost drift, wrong portrait, human presence, stock gap, currency/quantity validation, spending cap, repeated revisions, unread scroll, cart outcome and no blind retries.
- **P08:** **BLOCKED_LOCAL_GAME_ACCESS** in a GitHub-only provider context. Actual exact-patch observed Sims 4 interaction, EA-native source provenance, disposable-save A/B and rollback remain necessary for a live claim.
- **P07:** Repository-owned pure policy and regression suite; branch/PR/checks/merge must be confirmed independently. Do not claim the local MoonWake `prompt_group_walk.py` or Codex launcher ran simply because the source composition was applied.
- **P124:** Canonical contract, native gameplay route decision, product ledger and this guide keep future menus extensible and protect the existing five-part picker. Source-only work must not be described as installed/in-game autonomy.

### Regression commands

```sh
python -m unittest tests.test_purchase_dialog -v
python -m unittest tests.test_computer_upgrade_parts tests.test_computer_upgrade_batch tests.test_acquisition_integration -v
python -m scripts.check_native_gameplay_authority
python -m scripts.check_human_sovereignty --json
python -m scripts.check_peripheral_boundary
python scripts/semantic_preflight.py
```

Before a real release, inspect exact installed game build, available item purchases and EA tuning/hook provenance; then obtain authorized disposable-game evidence. Existing Build/Buy floor and My Library checkpoint remains mandatory for purchases/mutations in that mode. Never silently apply those Build/Buy gates as proof that a paused Live-mode computer order already occurred. The player always retains control.
