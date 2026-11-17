# PS-0241 — Universal mathematical activity chaining

**Source:** Prompt Scratch — CURRENT, Idea Inbox A11, PS-0241 (2026-11-14).
**Owner:** betterinstincts/activity_chain.py and contracts/activity-chain.v1.json.
**Proof:** Offline source policy only, not a playable native mod or live game certificate.

## Reuse the existing owners
The open ecology Planning/Play PR #252 is a consumer of this shared planner, not its owning implementation. Leave its branch and proof untouched. Preserve domain_cascade, semantic_advisory, task_continuity, workflow_interop, purchase_dialog, eco_resource_cycle, career_service and traversal_cost_learning.

A domain adapter supplies observed atomic steps and explicit prerequisite edges. The shared planner compiles a bounded per-Sim directed acyclic graph (DAG). Domain names are open-ended, not a fixed enum. Every step and edge must be backed by a current observation and the owning domain policy.

Example: Verify the career objective → acquire materials from current stock or a known computer purchase route → confirm purchased stock → move relevant material into the selected Sim's personal inventory → verify inventory → choose admitted teleport if currently unlocked and faster, otherwise walk → use the verified station/recipe to make the career-specific artifact → verify the product → observe actual career/task completion. Equivalent graphs can serve gardening, Servo maintenance, homework, chores, needs, friendships, aspirations and future modded activities.

## Optimization
For activity i use conservative source-backed upper work duration U_i and movement bound R_i:
SUM(U_i + R_i) + reserve <= MIN(minutes_until_work, minutes_until_need_floor)
SUM(verified_cost_i) <= verified_available_funds

Respect graph dependencies, resource claims, current locations, step deadlines and player sovereignty. Order ready work by earlier deadline, higher value, stable ID. Defer unknown or over-budget steps rather than invent an action or miss an obligation. This is a bounded deterministic heuristic, not a proof of globally optimal scheduling.

Travel uses current admissible route observations: teleport only when the selected Sim has evidence of its unlock, the target is permitted and its upper time is lower; otherwise use a verified walk or defer. A shortcut never bypasses lot, scene, save or player protections.

## Planning / Play / Recovery
- PLANNING: preserve pause, compile the goal and dependency chain and estimate the schedule without effect dispatch.
- PLAY: recalculate with a fresh capture. The output remains advisory, and the native executor must independently authorize and verify EACH action before continuing.
- In-flight work: RECONCILE_INFLIGHT_BEFORE_REPLAY; do not double-buy or repeat a transfer based on missing queue icons.
- Completion: require source-qualified before/after proof and revalidation when observed in an earlier capture. If stale, request current revalidation rather than skipping the step.
- Per-Sim plans remain independent and scoped to their observed active portrait; shared budgets and item ownership remain with existing household owners. The caller owns durable journal persistence and safe resumption.
- Any player input takes priority immediately; planning can continue read-only when admitted.

## Gaussian process forecasting
A small-data GP supports RBF, Matérn-3/2 and periodic kernels, Cholesky posterior solve and at most 24 unique observations in one homogeneous cohort. It returns mean, uncertainty (sigma) and upper advisory estimate (mean + 2*sigma). Callers must independently verify the cohort's game build, mechanic, Sim context, sample identities and observational provenance. It cannot discover discontinuous game unlocks, establish permission, or relax hard conservative deadlines without validation. Test holdouts, calibration and sparse-data behavior before trusting learned timing. At scale prefer approximations or alternative model families rather than dense cubic GP solves.

## Boundaries and validation
The pure planner owns the DAG, deadlines, and route selection. The installed
player-runtime port consumes it as an optional source of proposals and uses the
existing callback, admission, submission and reconciliation. Run
`python -m unittest tests.test_activity_chain tests.test_installed_player_runtime tests.test_native_ecology_bundle -v`
and the ontology, semantic preflight and native-gameplay authority checks.

Native integration remains issue #171; certify exact installed patch, source-proven native actions, player interrupts, serialization across restarts, current Sim/lot/source inventory, and disposable-save A/B plus rollback. BI-002 hunger remains its own active live certification. Existing PRs #251 and #252 were not modified by this work.

## Installed runtime adapter

An exact-build EA adapter supplies `read_activity_chain(frame)` only when the
package was built with `--installed-player-runtime --installed-activity-chain`
and locally verified `installed_activity_chain_binding_ref` evidence. The
callbacks require a source-observed `Frame.save_ref`. The read port returns
`None` if no goal is eligible or a mapping with:

| Field | Contents |
| --- | --- |
| `game_build`, `run`, `save_ref`, `goal_ref` | Current exact build, native run, admitted save and stable goal occurrence |
| `snapshot` | Planner input with current mode, household, actor, capture, queue, needs and spendable funds |
| `steps`, `routes` | Current domain-owned graph and independently admitted routes |
| `proposals` | Exact binding keys to mappings with `evidence_ref` and stable native `proposal_ref` |

Use `("ACTIVITY", step_id)` for a step and
`("TRAVEL", following_step_id, method, from_location, to_location)` for
its travel edge. Bind the proposal to the exact affordance, recipient,
resource reservation and save. The existing `submit(proposal_ref, frame)`
must atomically recheck the binding and current player/game authority.

Paused callbacks can stage a read-only plan. In Play, existing domain
decisions get their normal turn. If they leave the callback available, the
planner selects the first action and repeats the selection against a second
fresh frame, including the ordinary native priority check. Only one action
can be submitted per callback. The next cycle needs an observation distinct
from both admission frames and settlement bound to the original dispatch,
even if the player has since selected another portrait. The adapter
revalidates prior completions against current state and supplies unresolved
work as in-flight. A lost acknowledgment stays pending. Reissued proposal
tokens and changed locations cannot replay the same logical step. A verified
no-effect outcome ends that attempt. A new attempt needs a separately
qualified goal occurrence. `CHAIN_COMPLETED` means the current observation
validates all steps, including the terminal effect.

The runtime retains attempt identity in memory for the installed session.
Durable save-scoped intent and restart reconciliation still require the
native observation owner. See the
[active runtime sprint](../plans/active/BI-PS0241-ACTIVITY-RUNTIME.md) for the
first Windows gate and protected regression checks.

## MoonWake composition interpretation
The current canonical Sixth Gear order is P141 → P95 → P82 → P08 → P07 → P124. P141 compared a monolithic scheduler, hardcoded domain scripts, GP-only inference and a domain-owner-preserving DAG; the last was selected. P95/P82 authored and tested the offline seam and repaired cross-capture recovery. P08 live runtime is unavailable to this GitHub provider; local MoonWake prompt_group_walk was not executed, and no independent agents were launched. P07/P124 source integration is only as proven by actual commit, checks, PR and mainline evidence.
