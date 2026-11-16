## 2026-11-14 — Closers follow-up: malformed hover data and partially held stock

Post-merge CodeAnt review of #242 revealed two additional source-only defects. `fertilizer_hover_recognition` now validates external JSON `source` as a **string** before set membership, returning `FertilizerHoverError` for a list/dictionary instead of escaping with raw `TypeError`; the existing backyard planner also validates identity source, item kind, spatial-map category/pose source, and pending transfer status before any set membership. Negative tests cover malformed JSON-like values.

If the selected Sim has **one or more independently observed pocket units** and a separate fertilizer pickup is still queued, the planner now protects that pending pickup from duplication **while permitting one enabled `FERTILIZE` action** on a ready plant. It refuses to invent sufficient stock for `FERTILIZE_ALL`. If there are **zero** pocket units and transfer is pending, the action remains `WAIT_FOR_EXACT_ITEM_INVENTORY_READBACK_NO_REPEAT`. `gardening_service` remains the owner of player/busy/needs admission; existing-source policy never executes an interaction.

Tests: `tests/test_fertilizer_hover_recognition.py` and `tests/test_fertilizer_workflow.py`. This does not change the current installed Sims native gameplay/host P08 gate, still issue #171.

## 2026-11-14 — MoonWake /the-closers: actual screenshot of Growfruit Super Fertilizer

**New primary operator evidence:** A paused Sims 4 garden screenshot visibly shows a highlighted, individually identifiable ground item, with tooltip heading **SUPER FERTILIZER**, explanation **“Special fertilizer received from Jasmine as part of the Growfruit Challenge.”**, and displayed **§80**. The visible tooltip pointer is associated with the highlighted small grey object on the backyard ground. These facts rule out a generic bag-shaped classifier as the only valid route. The image does **not** show the installed game build, unique EA object ID, precise world geometry, available inventory drag affordance, active Sim's stock change or a successful fertilization.

**Machine-readable privacy-safe fixture:** `contracts/fixtures/BI-SUPER-FERTILIZER-HOVER-20261114.v1.json` records only the visible item tooltip, approximate non-calibrated screen boxes and unknowns. The original screenshot, user HUD, household, balance, portraits and saves are **not published**. Synthetic fixture object IDs are not EA target references.

**Recognition-to-advice call stack:**

```text
explicit live-host/calibrated CV hover observation
  -> tooltip text + pointer-to-highlighted target + same capture
  -> fertilizer_hover_recognition.recognize_super_fertilizer_hover
       exact English SUPER FERTILIZER, description "special fertilizer"
       source=USER_SCREENSHOT: candidate identity only; demand host reobservation
       source=HOST_VERIFIED_HOVER: still identity only, never game authority
  -> fertilizer_workflow._backyard_transfer_candidate
       require actual actor/lot/build/ownership/eligibility/route/menu evidence
       match source item and current observed enabled transfer affordance
       propose ONE transfer; do not buy, sell, execute mouse or claim outcome
  -> new independent selected-Sim personal inventory capture
  -> current exact plant menu with real stock => FERTILIZE one plant
  -> verified plant effect => completion, not earlier click or cooldown
```

A true `SUPER_FERTILIZER` candidate is admitted through `identity_source=HOVER_TOOLTIP` with a structured `hover_observation` of schema `betterinstincts.fertilizer-hover/v1`, `title`, `description`, `source`, `capture_ref`, `pointer_target_ref`, `highlighted_target_ref`, and `tooltip_attached_to_target=true`; all refs must represent one actual highlighted object in the same current capture. The live host must independently attest the proper household, exact Sim, lot, patch, scene, item ownership, personal-inventory destination, route, protected/reserved status, fertilizer eligibility, current usable transfer interaction and any pending transfer. A screenshot/class label alone never grants any item effect. The optional semantic spatial map accepts source-proven `FERTILIZER_BAG` and `SUPER_FERTILIZER` identity; it does **not** manufacture 3D world poses from the screenshot.

**Post-merge PR #239 correction:** An optional backyard scan must not veto a genuinely usable pocket. If verified personal inventory already contains sufficient fertilizer, bypass the scan even when its data are malformed or a pickup is still reported pending. With partial pocket stock and no usable bag transfer, propose one separately observed `FERTILIZE` action rather than deadlocking; `FERTILIZE_ALL` still requires enough stock for all eligible plants. Explicitly prove any post-transfer inventory gain with a **different, later capture**; do not reuse the transfer's original capture in a readback regression fixture.

**CI repair — preserve observed availability:** The gardening service's existing action sanitizer had been discarding `available=true` after verifying it, so a stricter downstream fertilizer planner treated an actually enabled transfer as unknown. `gardening_service._observed_actions` now retains the verified `available: true` bit (never admits `available=false`); end-to-end positive and negative regressions cover the handoff. No new action authority was created.

**Real game P08 path:** As the screenshot shows a paused game and grounded fertilizing item, first investigate the **native drag of the existing ground item to the active Sim's inventory** using the exact installed version and permitted disposable test save, before inventing a pathfinding command or another purchase. Community reports suggest the Super Fertilizer from hidden Build/Buy can be manually dragged from ground to personal inventory, but no such gesture has been witnessed or certified in the user's installed game. Use only a foreground, player-first, explicitly authorized one-effect test; pause on operator activity, never overwrite the ordinary save, and compare inventory and selected planter outcomes before/after. Native in-game instrumentation and rollback remain issue #171, independent of BI-002 hunger.

Historical EA evidence for Jasmine's super fertilizer: https://forums.ea.com/discussions/the-sims-franchise-discussion-en/march-22-2016-patch-notes/1385720
Evidence of possible player-controlled ground-to-inventory drag (not an EA API): https://www.reddit.com/r/ModTheSims4/comments/1sss18x/mod_making_super_fertilizer_more_accessible/

## 2026-11-14 — Sixth Gear: use already-purchased backyard fertilizer bags first

**Operator-observed parent fact:** Fertilizer bags have already been purchased and placed around the playable household backyard. BetterInstincts must detect those objects and transfer a usable bag into the **active Sim's personal inventory** before attempting the chosen planter. Do **not** infer missing fertilizer means buy more fertilizer.

**Deterministic existing-owner route**

```text
host_stack.evaluate_turn(gardening=current observed context)
  -> gardening_service (player/needs/school/queue/selected-Sim admission)
  -> fertilizer_workflow (exact plant readiness, pocket stock, continuity)
    -> optional backyard_scan (EA-native or calibrated multi-view bag identity)
       - require same Sim, lot, installed game build and fresh capture
       - require real fertilizer eligibility, household ownership, no reservation
       - require verified reachable on-lot path and enabled exact bag transfer
       - prefer shortest observed route; propose ONE bag-to-pocket interaction
       - queued / awaiting readback -> never repeat or claim acquisition
    -> REOBSERVE selected Sim personal inventory
    -> only real pocket fertilizer stock and enabled plant menu permit
       one FERTILIZE / FERTILIZE_ALL candidate
    -> only verified per-plant outcome counts as finished
```

**Opt-in source schema:** `gardening.fertilizer_workflow.backyard_scan` is `betterinstincts.backyard-fertilizer-scan/v1` with `sim_ref`, `lot_ref`, `game_build`, `capture_ref`, `observed_at_unix`, `scene_verified`, `active_sim_verified`, `inventory_destination_verified` and `bags` (maximum 32 objects). Each bag observation must include exact `item_ref`, `item_kind=FERTILIZER_BAG`, `identity_source=EA_READ_ONLY` with one grounded object evidence ref or `CALIBRATED_MULTIVIEW` with two distinct evidence refs; `fertilizer_eligible=true` with `eligibility_evidence_ref`, `quantity`, `location=GROUND`, `zone=BACKYARD`, matching `lot_ref`, `lot_status=VERIFIED_ON_LOT`, `household_owned=true`, `player_reserved=false`, `protected=false`, `route_reachable=true`, `route_evidence_ref`, `route_steps` 0–64 and `transferable=true`. Even a correct bag requires a current observed `TRANSFER_FERTILIZER_TO_SIM_INVENTORY` interaction to the exact `item_ref`. A bag **label** alone never qualifies. A pending transfer includes `status=QUEUED` or `AWAITING_INVENTORY_READBACK`, bag/Sim/lot/action refs and prevents immediate replay.

**Canonical spatial recognition:** When `backyard_scan.spatial_map` is available, the detector also cross-checks `betterinstincts.semantic-spatial-map-doc/v1`: same lot and installed build, non-executing current map, object ID present and classified `FERTILIZER_BAG`, `floor_id=OUTSIDE`, and an independent EA-read-only or calibrated multiview world pose. Mismatched maps or unknown/indoor/unlocated objects do not produce transfers. The spatial map is not itself a live native object sensor or authority to touch game state.

**Additional parent guard:** enabling `backyard_scan` also requires `gardening.fertilizer_workflow.lot_ref` and `game_build` to independently match the observed survey. Once the Sim's personal pocket has sufficient independently observed fertilizer, the stale backyard survey is bypassed; the fresh plant menu and per-plant completion owner take precedence. Missing or mismatched lot/build fails closed before a bag transfer candidate can be proposed.

The survey is an **input port**, not an implemented live game sensor. The policy does **not** execute drag/drop, choose a physical screen coordinate, move game objects, install an EA mod, or change saves. Actual object identity, version-specific native pickup-to-inventory semantics, the selected Sim's pocket change and fertilizer menu use require a compatible EA tuning/script source and a disposable-game A/B+rollback under issue #171. A particular purchased bag may be a decorative container or special fertilizer; eligibility must be verified on the installed pack/patch rather than guessed. Protected user saves and autonomy OFF remain authoritative.

Regression: `tests/test_fertilizer_workflow.py::BackyardFertilizerBagTests` plus existing gardening and eco suites. Existing `GROUND` transfer path without a backyard scan remains backward compatible. BI-002 hunger retains independent live certification ownership.

## 2026-11-14 — /the-closers: source validation and career-task idempotence

Post-merge review of PR #237 found five concrete source defects (CodeAnt: two inline findings plus three nitpicks). The bounded closer repair preserves the original source-only, player-first workflow.

- Numeric input limits are checked before float conversion: enormous integer money or clock values cannot escape through `math.isfinite` or timestamp subtraction.
- A reviewed paid fertilizer source may supply **only the affordable integer quantity**, never spend below the cash reserve. Zero affordable units remains blocked; no purchase is executed.
- Nested `fertilizer_workflow.sourcing` must match the parent **selected Sim** and exact currently ready plant deficit (after eligible plant filtering). Mismatched actor or invented deficit is rejected.
- Recycler history cannot promote reused before/after capture pairs even with distinct outcome IDs. A **nonempty exact build reference** is required before any recycling recommendation; unknown-build history has no decision grade.
- For the Green Technician's `FABRICATE_ECO_UPGRADE_PART` obligation, the current career-panel `daily_task_status` must be `PENDING`. `COMPLETE` yields `ECO_CAREER_TASK_COMPLETE` (no duplicate crafting); missing/unknown status yields `ECO_CAREER_TASK_STATUS_UNKNOWN` and a career-panel reobservation.
- All fixes are **policy only**, not native Sims behavior or local game proof. Issue #171 owns exact-patch EA interaction/observer integration, disposable A/B and rollback. BI-002 hunger remains independent.

Regression suite: `tests/test_eco_resource_cycle.py`; governing decision `contracts/native-gameplay-decisions/BI-ECO-CLOSERS-20261114.v1.json`; consultation `contracts/consultations/BI-ECO-CLOSERS-20261114.v1.json`.

# Eco materials, gardening fertilizer, and Green Technician production

## Parent outcome and current proof

BetterInstincts should treat gardening fertilizer, resource sourcing, recycling,
fabrication, and Civil Designer / Green Technician daily work as one dependable
set of **observed supply chains**, not a succession of manual discovery tasks.
The policy runs when the host supplies a fresh verified snapshot and proposes
**one** action; it does not install an EA mod, actuate the screen, buy equipment,
spend Bits/Pieces, alter saves or complete a career requirement.

| Chain | Deterministic decision | Owner |
| --- | --- | --- |
| Planter | Observe plant readiness and pocket inventory → eligible fertilizer action | `fertilizer_workflow.py` via `gardening_service.py` |
| Fertilizer source | If the personally held supply is short, find available verified unreserved produce/manure/fish/ground pickups, or reviewed affordable purchases → one sourcing step → reobserve pocket | `eco_resource_cycle.plan_fertilizer_sources` |
| Recyclable materials | Calculate measured Bits/Pieces shortfall for the selected recipe; reject protected, unique, reserved, unverified or needed objects; prefer measured value/utility, with one safe zero-value trash trial to bootstrap | `eco_resource_cycle.plan_eco_fabrication` |
| Fabrication | Require actual unlocked exact-target recipe, observed Fabricator and stock ≥ observed recipe cost; queue one advisory craft step → verify actual crafted part and daily-task panel separately | `career_service.evaluate_green_technician_daily_task` via `host_stack.evaluate_turn` |
| Coverage evolution | Explicit SOURCE_PRESENT vs GAP, test owners, dependencies and game-effect-certification state | `contracts/mechanics-registry.v1.json` |

## Observed-state call stacks

```text
host_stack.evaluate_turn(gardening=observed)
  -> gardening_service.evaluate_gardening_turn
  -> fertilizer_workflow.evaluate_fertilizer_workflow
  -> when personal pocket stock < 1 and fertilizer_workflow.sourcing supplied:
     eco_resource_cycle.plan_fertilizer_sources -> one observed source candidate
  -> separately reobserve sim inventory, plant cooldown, queue and outcome
```

```text
host_stack.evaluate_turn(eco_fabrication=observed)
  -> career_service.evaluate_green_technician_daily_task
  -> eco_resource_cycle.plan_eco_fabrication
  -> exact task and recipe observed?
     NO -> inspect career panel or recipe unlock
     YES -> required Bits/Pieces present?
       NO -> observed recycler available? -> select one safe recyclable
          -> independently observe post-recycle Bits/Pieces delta; repeat
       YES -> observed available Fabricator + enabled recipe?
          NO -> check community station or Build/Buy checkpoint
          YES -> one fabricate candidate; reobserve crafted part, task panel
```

## Machine observation contracts

**Fertilizer source input:** `betterinstincts.fertilizer-sourcing/v1`,
nested at `gardening.fertilizer_workflow.sourcing`. Exact actor and capture,
verified scene/queue, current timestamp ≤180 seconds, known idle player,
safe needs, number of required units, funds and an untouchable cash reserve.
Each source includes stable reference, type, observed quantity, reserved
quantity, opportunity cost, true cash cost, currently available exact
interaction and target. Paid sourcing additionally requires a reviewed
purchase flag; **this is an advisory candidate, not Build/Buy authorization**.
Manure from specific DLC is merely a possible observed source, never assumed.

**Fabrication input:** `betterinstincts.eco-fabrication/v1`, optionally
supplied to `host_stack.evaluate_turn(eco_fabrication=...)`. Required:
selected Sim/capture/time, scene and queue, player/needs evidence,
career track/daily task or explicit goal recipe, Fabrication skill, currently
available recipes, actual cost (Bits/Pieces), unlocked state, currently
available Fabricator/Recycler and safely expendable source inventory.
For a Green Technician daily `FABRICATE_ECO_UPGRADE_PART`, the priority
recipe ID is `FABRICATED_ECO_UPGRADE_PART`. Costs must come from the
**observed currently installed recipe**, not hardcoded or inferred.

**Recycling outcomes:** bounded per-observation measurements with unique
proof ID, matched Sim and game build, separate before/after references, the
source class, actual Bits/Pieces gained, and independently observed consumed
value. An interrupted/player-owned attempt never trains a ranking. At least
two eligible actual outcomes qualify a source class for observed yield
ranking. No background recording, raw game telemetry, server or cross-user
upload is created.

## Fallbacks and permanent behavior boundaries

- Unknown/stale source, player intent or unsafe needs → defer, preserve goal,
  and reobserve; never invent resources or pick random inventory.
- Inventory held in world/household does **not** become personal pocket stock.
  Existing fertilizer transfer/cooldown/continuity owner remains definitive.
- Protect the current player's queue; never clear a command to free a slot.
- Missing Recycler/Fabricator → inspect existing community equipment before
  suggesting acquisition; a purchase requires independent all-floors model,
  My Library backup, readback, and budget approval.
- Never silently recycle gifts, collectibles, needed crafting components,
  unique objects or items assigned to another household obligation.
- Completing the craft and completing the career daily task are **two
  separately observed outcomes**. Any actual action requires source-pinned
  EA-native hooks/interaction tuning and game-safe admissions (issue #171).
- Do not mark BI-002 hunger as complete or make eco delivery a hunger
  certification prerequisite. Keep career Work Hard and teen homework lanes.
- There is no autonomous mouse clicker or per-frame global scan.

## Exact-game and acceptance gate (P08 — still open)

At an authorized disposable local Sims 4 save: pin the exact installed build,
packs and recipe tuning; inspect read-only EA native interaction IDs/returns,
record available planter fertilizer menu and personal-pocket stock; show
observed source acquisition, transfer, cooldown and target completion.
For Green Technician, capture before/after Bits/Pieces, recycler item identity,
crafted Eco-Upgrade Part, daily-task panel progression, needs/queue ownership,
and rollback A/B. Verify operator manual input interrupts autonomy; no loops,
Save changes, unsupported mod installations or unapproved purchases. Re-run
after source changes. Repository CI covers only source policy.

External mechanic references (not version-pinned EA API evidence):
[EA Fabrication Skill](https://help.ea.com/en/articles/the-sims/the-sims-4/fabrication-skill/),
[EA Civil Designer Career](https://help.ea.com/en/articles/the-sims/the-sims-4/the-sims-4-civil-designer-career/),
[EA Gardening Skill](https://help.ea.com/en/articles/the-sims/the-sims-4/gardening-guide/).

## Repeatable validation

```sh
python -m unittest tests.test_eco_resource_cycle tests.test_fertilizer_workflow tests.test_gardening_service tests.test_mechanics_registry -v
python -m scripts.check_native_gameplay_authority --base-ref <exact-main-base-SHA>
python scripts/semantic_preflight.py
python -m unittest discover -s tests
```

**Independent status dimensions:** source file committed; PR checks observed;
merged main; local checkout current; installed Sims native mod; A/B rollback;
real behavior observed. None implies the next.

## Household Bits and Pieces sourcing

[EA's Fabrication guide](https://help.ea.com/en/articles/the-sims/the-sims-4/fabrication-skill/) documents the household-funds and Recycler hovers, recycling eligible personal inventory, and free equipment at Evergreen Harbor Community Spaces. [EA's Civil Designer guide](https://help.ea.com/en/articles/the-sims/the-sims-4/the-sims-4-civil-designer-career/) confirms one Fabricated Eco-Upgrade Part attempt costs **15 Bits and 10 Pieces**. Read the two labeled resource totals separately from the Simoleon balance. An attempt can fail. Confirm the resulting part and the career panel separately.

The existing `eco_fabrication` carrier accepts optional `sourcing`. The live listener requires the current observed game build, actor, lot, listener session, and independently recognized scene. A caller can also use `career_service.evaluate_green_technician_daily_task` directly for advisory evaluation. Keep receipt IDs opaque and local.

- Match `household_ref`, `game_build`, `lot_ref` and `capture_ref` across the source context and its balance readback. Accepted sources are `HOUSEHOLD_FUNDS_HOVER`, `RECYCLER_HOVER` and `EA_HOUSEHOLD_READBACK`. The source context also carries `session_ref`, `lab_save_verified`, `eco_lifestyle`, and `effect_pending`. Any pending effect calls for readback before proposing another.
- Check already owned eligible items first. Electronics and mechanical salvage, disposable furniture or woodworking output, surplus books/collectibles and organic waste are categories for investigation. Rank items against the remaining Bits and Pieces shortages using two or more matching observed Recycler outcomes and the consumed input value. Each receipt needs its own dispatch and before/after evidence. An explicit zero-value discard candidate may be tested once per observed opportunity. Personal and household items must be visible in this Recycler's picker, and must have current `NOT_ATTEMPTED` status. Protected, unique or reserved items are excluded. Buying goods solely to recycle them has no automatic route because price alone establishes neither yield nor efficiency.
- When a matching Recycler or safe input is unavailable, consider a freshly verified free community Recycler, then an observed currency dive, Rummage or Dive for Deals. These are single opportunities. Measure actual household currency changes and salvage separately. EA confirms the free community option and lists the Guntdach Home Recycler in the regular Build/Buy catalog. A home purchase continues through the existing budget and full-lot Build/Buy review.
- After natural routes are exhausted, a separately enabled debug option may propose the exact current menu. [Community reports](https://sims-online.com/sims-4-eco-lifestyle-cheats-influence-points-footprint/) describe Shift-click **Give Bits and Pieces** on the Fabricator (+50/+50), and Shift-click the selected Sim → **Give Bucks** → **Recycle Bits** or **Recycle Pieces** (+500 of one currency). The suggested action favors the relevant shortage and reduces excess. Use a fresh household balance readback to verify the actual result. Debug does not produce Recycler training evidence.
- A separately observed `STOCK_ECO_UPGRADE_PART` shortage may use the hyphenated **Eco-Upgrade Part** catalog search. The [community-reported §50 listing](https://www.reddit.com/r/thesims/comments/gxjqog/) requires current item, price and funds evidence, explicit purchase opt-in, and an admitted whole-lot checkpoint. There is a separate opt-in for showing the debug reveal sequence. One purchase awaits stock and funds readback. A purchased or found part never satisfies **Fabricate an Eco-Upgrade Part**.

Local verification under [issue #171](https://github.com/EndeavorEverlasting/BetterInstincts/issues/171) needs the exact installed game build, a disposable authorized save, a real balance readback, one source outcome, and a real crafted part plus matching career progress. Also verify player takeover and that previous drafting and fertilizer behavior survive the same game trial.
