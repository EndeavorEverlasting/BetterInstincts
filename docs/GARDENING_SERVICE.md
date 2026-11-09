# Gardening behavior service

For observation that continues while an interaction awaits its outcome, use the
bounded [async tandem session](HOST_TANDEM.md). It reuses this peer and the same
needs evaluator; urgent needs can suspend verified host-owned gardening.

Owner: `betterinstincts/gardening_service.py`; policy: `contracts/gardening-service.v1.json`.
Callers: `host_stack.evaluate_turn(..., gardening=...)` and the existing opt-in
`scripts.host_listener tick` observation path. This orchestrates behavior on
existing plants and plantables. Furniture, construction and catalog-scout review
are not prerequisites to the gardening goal.

## Call stack and ownership

```text
current host-listener observation
  -> host_stack
  -> existing need_services / need_load_balance (one evaluation)
  -> gardening_service (same report, same capture)
  -> one observed need remedy, one observed gardening interaction,
     or a concrete state/interaction inspection query
  -> independent screen_admit and local host action
  -> observed outcome and new observation
```

Need parsing and thresholds remain in `need_service_base` / `contracts/needs.v1.json`.
School, homework, dialogs, player intent, absent Sims and viewport protection
remain in the host stack. The peer gardening module owns gardening selection and
continuation; it introduces no replacement needs scorer, scheduler or UI daemon.
The listener retains its existing bounded tick receipts. No new persistence owner
or background hook is introduced.

## Input through the existing listener

Add a `gardening` object to a genuine
`betterinstincts.host-listener.observation/v1` record under ignored `dist/`.
The normal observation still supplies all six needs, queue, location, current
capture, player state and current homework/school flags. In `gardening`, provide:

- `capture_ref`: the same current capture as the parent observation.
- `observed_at_unix`: actual observation time, at most 180 seconds old.
- `scene_verified`, `queue_verified`: true only after genuine current checks.
- `responsibilities_checked`: true only after reading the current daily task and schedule.
- `minutes_until_obligation`: observed Sim-time interval, or
  `no_upcoming_obligation: true` when independently established.
- `observed_actions`: up to 24 actual current available/disabled menu entries.
  Each row has `action_id`, actual `label`, opaque `target_ref`, `capture_ref`
  and boolean `available`. Gardening IDs are `WATER`, `WEED`, `PLANT`, `HARVEST`.
  A need remedy uses the existing need-service action ID (for example `TAKE_NAP`)
  only when that actual interaction was observed on its target.

The Energy lane also supports the locally observed Natural Living `Sleep Here`
interaction as `SLEEP_ON_GROUND`. Supply `observed_sleepable_ground` as an
available capability only after seeing the **enabled** current menu option, then
include that same current action observation. Earlier disabled observations do
not establish eligibility. Pack/skill requirements and recovery outcomes are not
inferred from the presence of outdoor ground.

Use the established command, not a second runner:

```sh
python -m scripts.host_listener tick --session-id ACTIVE_SESSION --process-id ACTUAL_PID --observation dist/game-host/current-gardening.json
```

Placeholders above are locators, not verified observations. The listener and this
service remain plan-only; their result never authorizes a click. The local agent
must still use fresh screen admission immediately before each UI step.

## Outcomes and responsibility protection

The gardening request forces the host's normal needs evaluation even when all
needs are high, then reuses that exact report. Below the existing preemptive floor,
only a matching currently observed remedy may be selected. If the predicted
remedy is unavailable, `GARDEN_INSPECT_NEED_ACTIONS` asks to inspect existing lot
and inventory interactions. It preserves `PLANT_AND_MAINTAIN_GARDEN` as PENDING;
it never turns the failure into a building/placement approval gate.

With needs maintained, pending homework, attendance and imminent obligations
defer gardening. Missing/stale evidence asks for inspection instead of claiming
readiness or asking the player to invent a snapshot. A clear responsibility
window permits one observed action: existing watering/weeding first, then planting
or harvesting. Disabled options and unrelated commands cannot be selected.
There is no Plant All / Tend Garden batch or completion claim from selection.

The 15-Sim-minute activity/recheck window and 30-minute responsibility reserve
are conservative **unmeasured host-policy defaults**, not EA tuning or a proven
interaction duration. The local executor must reobserve and stop adding work
when needs, obligations, player activity or the scene changes. No action is
claimed to finish inside that window based on this advisory result.

## Evidence boundary

Regression tests exercise the actual listener → host-stack → needs → gardening
composition, unavailable-remedy recovery, player/viewport guards, deadline and
homework priority, stale/disabled actions and the one-interaction limit. They do
not prove planting, need restoration or career safety in The Sims. No runtime
hook or playable-mod certificate is introduced; BI-002 remains ACTIVE. Catalog
Scout has its own optional P04 setup gate and must not block this behavior lane.

## Interrupted Fertilize All jobs (P95 / P124 / Trifecta)

A verified player-authored multi-plant Fertilize command may include an optional `task_continuity` object. The separate pure evaluator at `betterinstincts/task_continuity.py` tracks completed versus still-pending plant references and recognizes independently verified autonomous chat/activity interruptions. The existing gardening service then emits a safe wait, reobserve, duplicate-queue guard, or **one** exact-target observed Fertilize candidate. Existing need, deadline, school, homework, live-mode, player-presence and independent screen-admit gates remain in force. No new queue daemon, live cancellation, or claim of Sims mod certification. See [TASK_CONTINUITY.md](TASK_CONTINUITY.md) and `contracts/task-continuity.v1.json`.

## Selected household Sim and autonomy moderation (offline planning)

When a supplied `gardening` observation includes `task_continuity` plus `selected_sim_observation`, the existing gardening evaluator suspends the goal while another Sim is selected, preserving all unfinished plant references. After reselecting the original Sim it requires fresh portrait and task-queue proof; a switch never proves that the game kept working. An optional `autonomy_observation` supplies a read-only cancellation candidate for independently harmful autonomously queued actions; this is not a SendInput or cancel permit. See [AUTONOMY_AND_DISCOVERY_HUD.md](AUTONOMY_AND_DISCOVERY_HUD.md) for evidence schema and the separate top-left Discovery Quest routing.


## Fertilizer pocket-inventory gate and hydroponic queue (2026-11-09)

Existing owner: betterinstincts/gardening_service.py. Pure supply reducer:
betterinstincts/fertilizer_workflow.py; ontology consultation:
contracts/consultations/BI-FERTILIZER-INVENTORY-QUEUE-20261109.v1.json.
Three glossary owners: PERSONAL_FERTILIZER_INVENTORY,
FERTILIZER_SUPPLY_TRANSFER, FERTILIZER_GOAL_QUEUE.

**Essential Sims mechanic:** Fertilizer lying on the lot or in household
storage is NOT in the gardening Sim's personal inventory. Fertilization
first requires eligible stock in the selected Sim's pocket. The local
agent must identify the correct Sim and source item, move it into that
Sim's actual inventory, and VERIFY the inventory count independently
before retrying the plant menu. No unobserved item guesses or purchases.

**Opt-in capture shape:** Add the following to a fresh gardening context
alongside observed_actions. Example refs and timestamp below are NOT
real captures or dispatch permits:

    "fertilizer_workflow": {
      "schema": "betterinstincts.fertilizer-workflow/v1",
      "capture_ref": "capture:CURRENT",
      "observed_at_unix": 0,
      "sim_ref": "sim:CURRENT",
      "actor_verified": true,
      "inventory_verified": true,
      "transfer_authorized": false,
      "plants": [
        {"target_ref":"plant:1","state":"PENDING","fertilize_ready":true}
      ],
      "supplies": [
        {"item_ref":"fert:1","location":"GROUND","quantity":3,
         "fertilizer_eligible":true,"transferable":true}
      ]
    }

Supported supply locations are SIM_INVENTORY, GROUND and
HOUSEHOLD_INVENTORY. Item quantities must be actually observed, not
estimated from stack icons. Fertilizer eligibility must be observed
for that item (e.g. a suitable harvestable/fish/actual fertilizer);
protected items are excluded. Plant target states are PENDING or
VERIFIED_DONE; VERIFIED_DONE requires both outcome_ref and
outcome_capture_ref. Unknown/cooling-down targets remain pending.

If the user authorizes transfer, set transfer_authorized=true and
include one actually enabled observed_actions row with action_id
TRANSFER_FERTILIZER_TO_SIM_INVENTORY, target_ref equal to the exact
item_ref and the same fresh capture_ref. The plan returns at most one
bounded transfer candidate and quantity. The local executor must
confirm exact drag source, selected Sim's pocket destination, player
idle/input lease, screen admission, and a subsequent pocket-inventory
readback. **The planner never drags, clicks or certifies transfer.**
Without this evidence it asks for inspection and preserves the goal.
Stock already in SIM_INVENTORY is used without a needless transfer.

When personal stock is sufficient, an actually enabled FERTILIZE_ALL
affordance can be selected for a fresh eligible group; otherwise one
observed FERTILIZE action on one exact plant is proposed. Fertilize
requires Gardening level 3; Tend Garden does not replace fertilization
or harvesting. Native Fertilize All exists on some game versions;
never assume it exists from a guide or patch label. After every
selection, reobserve the queue, inventory and plant effects. A
disappearing queued action is NOT proof that a plant was fertilized.
The reducer handles at most 32 plant refs per capture; split larger
lots into independently observed batches with an external remaining
target ledger rather than silently dropping unobserved plants.

For an explicit player-authored multi-plant order, keep using
gardening.task_continuity with action_id=FERTILIZE and per-plant
references. Its TASK_RESUME_CANDIDATE now passes through the SAME
personal-inventory prerequisite. PLAYER_CHANGED_GOAL, already queued
work, selected-Sim switching, needs, homework, careers, modal dialogs,
and autonomy interruptions are still handled by their existing
owners. Side quests never justify deleting uncompleted player goals,
but no agent may cancel or reorder the user's queue autonomously.

Regular repeat behavior is a re-observation/reassessment on the
established opt-in listener, not an invented Sim-day timer or second
daemon. A cooled-down plant is revisited only after new evidence of
eligibility. The service emits offline plans; the live Windows Sims 4
input adapter, true inventory movement, Fertilize All eligibility and
actual gameplay results still require local P08 proof.
