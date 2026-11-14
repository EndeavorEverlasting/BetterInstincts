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
