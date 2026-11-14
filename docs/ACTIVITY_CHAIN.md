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
Source-only files: betterinstincts/activity_chain.py, contracts/activity-chain.v1.json and tests/test_activity_chain.py. These do not hook, install, unpause or play The Sims 4. Run: python -m unittest tests.test_activity_chain -v, followed by the repository's ontology, semantic preflight, native-gameplay authority and full validation checks.

Native integration remains issue #171; certify exact installed patch, source-proven native actions, player interrupts, serialization across restarts, current Sim/lot/source inventory, and disposable-save A/B plus rollback. BI-002 hunger remains its own active live certification. Existing PRs #251 and #252 were not modified by this work.

## MoonWake composition interpretation
The current canonical Sixth Gear order is P141 → P95 → P82 → P08 → P07 → P124. P141 compared a monolithic scheduler, hardcoded domain scripts, GP-only inference and a domain-owner-preserving DAG; the last was selected. P95/P82 authored and tested the offline seam and repaired cross-capture recovery. P08 live runtime is unavailable to this GitHub provider; local MoonWake prompt_group_walk was not executed, and no independent agents were launched. P07/P124 source integration is only as proven by actual commit, checks, PR and mainline evidence.
