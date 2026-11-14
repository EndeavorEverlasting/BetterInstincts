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
