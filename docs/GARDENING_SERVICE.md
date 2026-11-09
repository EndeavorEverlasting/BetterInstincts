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
