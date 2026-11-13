# NanoCan — cursor-free dish recycling and household income

**State:** OFFLINE_POLICY_ONLY. The repository does **not** yet contain a
source-proven, installed EA mod that moves dishes or increases household
funds. This is intentional: fake money from external scripts and screen
ownership violate BetterInstincts player-first, native-gameplay doctrine.

**Parent outcome:** All household Sims should prefer disposing of verified
dirty, empty single plates into an installed NanoCan Touchless Trash Can
rather than pointlessly washing them in sinks, when safe and profitable.
Ideally the game's own mechanics move and recycle the item without mouse
movement, desktop focus or stealing a player's selected Sim.

## Research distinction: disposal is not one reward mechanism

Sources: [Ultimate Sims Guide NanoCan](https://ultimatesimsguides.com/nanocan-touchless-trash-can/),
[EA Forums experience](https://forums.ea.com/discussions/the-sims-4-general-discussion-en/apartment-keys/1399098),
[Mod The Sims NanoCan drag/drop patch history](https://modthesims.info/d/645491/nanocan-drag-and-drop-fix.html),
[Mod The Sims off-grid NanoCan](https://modthesims.info/d/667082/off-grid-nanocan-trash-can.html).

Community reports typically distinguish:

| Mechanism | Community-reported per-item payout | Evidence level |
|---|---|---|
| **Player drag/drop into NanoCan** | §10 × household member count (up to §80) | Reported; exact patch not certified |
| **Ordinary Sim trash disposal** | Often §10 for the whole disposal event | Reported; exact patch not certified |
| **Hypothetical native drag-equivalent call** | *Unknown until EA source inspection and local test* | No verified implementation |

The difference matters. Tuning the Sim's normal autonomous `Throw Away`
may improve cleaning behavior yet **not** reproduce the larger reward of a
manual player drag. Do not invent a native call or inject the difference in
Simoleons. Reward estimates are advice, not game account balances.
Dish stacks can pay differently from single plates; never count a stack as
multiple payout events. The bin can enter a brief cooldown between drops.
The screen image supplied by the operator illustrates an in-lot bin; it
does not provide EA identity, dish interaction proof, or actual funds deltas.

## Program and call stacks (P95)

**Existing owner:** `betterinstincts/autonomy_moderation.py` already
processes *all* Sims in a household independently of the selected portrait,
with a pure `evaluate_native_household_autonomy` function. A nested,
optional `nanocan_recycling` observation now delegates to the small
`betterinstincts/nanocan_recycling.py` policy. Previous callers and
all their results remain unchanged when the optional observation is absent.

```
Future exact-build EA native household/event observer (not installed)
  -> existing evaluate_native_household_autonomy(..., nanocan_recycling={...})
  -> evaluate_nanocan_recycling:
       exact game_build/household/lot/capture and policy opt-in
       player idle and no survival need or manual dish reservation
       bounded dish list (<=32) / installed NanoCans (<=8)
       dirty + EMPTY + SINGLE dish / no queued or dispatched duplicate
       current NanoCan is verified/usable/not broken/not cooling down
       source-proven native routes: drag-equivalent (first), Sim disposal (fallback)
       protected Sim queue/goal and exact actor when fallback needed
       -> ONE `proposal`, never a game action or a money change
       -> optional sink suppression *candidate* only for proven autonomous wash
  -> future game-native adapter (absent; requires read-only EA source inspection)
       -> recheck player authority, queue ownership, exact dish/can, cooldown
       -> one native disposal event, no OS screen input
       -> reobserve item state and actual household funds
  -> reconcile_nanocan_outcome (attributed independent evidence only)
       -> verified payout or precise unresolved reason; never credit funds
```

The Native Drag Equivalent route must show exact game-build EA source,
verified reward equivalence, enabled native affordance, and a fresh dish/can
before it can become even an offline candidate. Ordinary
`NATIVE_SIM_DISPOSE` requires a verified idle household actor and safe
autonomous queue; it is represented with its own *different* payout estimate.
The helper's provenance must come from the installed native EA API, never an
inferred Windows drag or an unproven guess from community web pages.

## Data and state contracts (P82)

See `contracts/nanocan-recycling.v1.json`. Native observations must
contain `schema`, exact `household_ref`, `game_build`, `capture_ref`,
`observed_at_unix`, `scene: LIVE`, `lot_scope: HOME`, verified household,
lot and queue, `policy_opt_in: true`, `dishes`, `cans`, and
`native_routes`. Every *dish* has a stable `dish_ref`, proof/availability,
`state: DIRTY_EMPTY`, `stack_size: 1`, and an
`attempt: NONE|QUEUED|DISPATCHED|CONFIRMED`. Every can has
`kind: NANOCAN_TOUCHLESS`, `can_ref`, verified usable state,
`cooldown_ready`, and current capture. Every route identifies the exact
dish+can, exact build, source kind `EA_TUNING|EA_SCRIPT`, verified
mechanism/source and current native affordance; drag-equivalent additionally
requires `reward_equivalence_verified` plus a distinct proof ref.
The user may opt into normal Sim disposal despite the reduced reward.
There is **no** cursor fallback.

Behavioral safeguards:

- Never destroy edible food, leftovers, a stack, a player-reserved dish or
  an unverified object; don't sell/create/trash unrelated assets.
- A player activity signal, wrong lot/mode, age >180 seconds, unknown
  actor queue, urgent need, reserved object, busy NanoCan, or missing
  native affordance blocks autonomous proposals.
- A Sim-initiated sink wash may only be considered for suppression if its
  exact queued action, slot, actor and independent SIM_AUTONOMY provenance
  are matched and the NanoCan route is safe. No player washing cancellation.
- No automatic purchases, object moves, UI hooks, external coin
  injection, per-frame scans, indefinite retries, or unbounded tracking.
- A decision never proves that a plate vanished or money increased.
  QUEUED/DISPATCHED/CONFIRMED prevents repeated disposal for one plate.
- Reconciliation requires a dispatched attempt, distinct before/after
  captures, independently observed dish disappearance and separately
  attributed causal funds delta. Coincidental balance changes don't count.

**P82 acceptance:** `tests/test_nanocan_recycling.py` tests both payout
classes, cursor exclusion, false reward attribution, manual intent,
route/build provenance, wrong objects, stale menus, cooldown, event bounds,
single item prioritization, duplicate attempts, sink identity, independent
outcome evidence and preservation of existing native household outputs.

## Required native implementation and P08 certification (NOT YET RUN)

1. On the actual Windows Sims installation, identify the exact game build
   and inspect the installed NanoCan, dish cleaning, autonomous sink cleanup,
   player drag/drop and payout tuning **read-only** using Sims 4 Studio
   exports and `scripts/tuning_audit.py`. Capture authentic tuning
   identifiers and callback signatures. Do not copy EA assets to Git.
2. Compare a vanilla Sim's disposal of one plate to a **manual player drag**
   of one plate on the same disposable lot. Observe § balance before and
   after separately, with bin cooldown reset and all other money changes
   excluded. Verify household member count. Repeat to distinguish real
   mechanism effects from a lucky coincident balance update.
3. Prefer a reversible, version-specific XML override if it can route
   autonomous cleanup to NanoCan while preserving manual sink use. If the
   player-drag reward requires a native callback, use only a source-proven,
   installed-build-compatible EA Python script hook. Never guess APIs, patch
   base-game executables, or substitute desktop SendInput.
4. Test native no-cursor dish recycling with multiple Sims, Servo and
   occult members where applicable, sink competitor, queued dishes, paid
   success, cooldown, stacks, manual player interruption, bad/no bin,
   no duplicated reward, and ordinary dish washing as protected control.
   Use disposable saves and independent rollback. No change to physical
   saves or the operator's live game without approval.
5. Keep BI-002 native hunger trials active: this cleaning work cannot
   close that parent game-lab gate.

**Fifth Gear proof ceiling:** current canonical
P95 → P82 → P08 → P07 → P124 was resolved for this sprint. GitHub remote
source and CI can show implementation and offline tests; the local
`prompt_group_walk.py` process and Sims P08 native/game side effect
are **NOT_RUN** in this GitHub provider lane. A passing CI run or merge
must not be reported as working native game automation.
