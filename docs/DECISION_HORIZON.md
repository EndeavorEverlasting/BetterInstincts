## 2026-11-14 — Reusable Bellman/KKT/GP umbrella (Closers)

This is the canonical **Bellman + Lagrange/KKT** numerical owner, not a one-off ecological solver. The shared registry-backed adapter `betterinstincts/microsystem_math.py` and [MICROSYSTEM_MATH.md](MICROSYSTEM_MATH.md) now call these exact methods across registered microsystems, together with the existing `ecology_forecast.compare_duration_models` Gaussian process. No duplicate math engine is introduced. Every active `domain_cascade` receipt receives a source-only mathematical advisory *or explicit original-owner fallback*, and 14 additional microsystems are registered for optional scoped calls. This mathematical forecast does not override actor, player, inventory, deadline, hard need-floor or queued-effect gates. Independent alternative planners are welcome through the same holdout/feasibility comparison and may supersede the PS0245 candidate while keeping this method as fallback. Native-game execution remains unproven.

# PS-0245 — Bellman and KKT planning slice

**Source owner:** \`betterinstincts/decision_horizon.py\`. **Status:** offline policy prototype; **not a native Sims mod**, queue actuator, installed script, or observed gameplay change.

The existing PS-0241 \`activity_chain.py\` is the source of evidence, dependency validation, fresh game-state checks and conservative travel durations. This module **consumes** those same recorded observations. It never invents an affordance, unlock, action outcome, route, queue permit or patch-specific EA function.

## P141 → P95 → P82 → P08 → P07 → P124

P141 considered: (1) replacing \`domain_cascade\` with a generalized solver — rejected because it duplicates the current owner; (2) using a GP to predict all actions — deferred because the existing \`ecology_forecast.py\` already holds optional, holdout-gated estimation; (3) desktop automation — rejected because native gameplay and player sovereignty cannot be replaced by repeated clicks; (4) a bounded optimized successor over the observed PS-0241 action DAG — selected as a reversible testable policy slice. P95 formalized the call stack; P82 must compare fixed synthetic workload against the existing earliest-deadline greedy chain; P08 remains **blocked until exact local Sims runtime and disposable-game evidence**; P07/P124 own source implementation and repository integration, not assumed local execution of the MoonWake walker.

## Typed mathematical model

Each input snapshot has an actor and household identifier, selected Sim, current observation capture, planning/play mode, scene and queue proofs, a queue owner and depth, player activity, Sim inventory, funds, needs levels and **observed rates** (including negative values), need floors, skills, time until work and need floor, a time reserve, a world location, a prior completed-step ledger and optional checkpoint. Per-step records inherit PS-0241 IDs, domains, observed location, prerequisites, conservative duration, deadline, purchase cost and evidence reference. Extensions include \`success_probability\` and \`effects: {requires_inventory, inventory_delta, need_delta, skill_delta, money_delta, mood_delta}\`. Need and skill types are **open named sets**, not a six-needs-only assumption; no unseen occult motive is inferred. Observed \`teleport_unlocked\`, its evidence and same-capture proof enable a distinct teleport route; walking remains a separate alternative.

The immutable \`PlanningState\` contains time, position, funds, needs, skills, inventory and completed action identities. \`ActionModel\` preserves prerequisites, probabilities, conservative time, resources, outcomes and safety metadata.

For observed feasible action \(a\), the bounded semi-Markov recurrence is

\[
V(s)=\max\{0,\ \max_{a\in A_{\mathrm{feasible}}(s)}
[p_a(r(s,a)+V(s'_a))-(1-p_a)\lambda_{\mathrm{failure}}]\}.
\]

Failure is an absorbing *reobserve and reconcile* terminal event rather than a guessed retry. Need rates accumulate during walking/teleporting/using an object **before** end-of-action effects are credited. Duration, risk and funds all influence expected utility. Hard feasibility can never be bought off by a high utility weight. Current implementation searches success branches to bounded depth and computes expected survival-weighted total utility for each resulting path; it does not assert policy iteration/convergence in an unbounded world. \`max_expansions\` and \`max_depth\` cap CPU work deterministically. Each step may occur at most once, which also suppresses no-op and walk/teleport cycles. The first proposed step is returned separately from the longer **forecast**, always with \`execute_allowed: false\`.

Source evidence from PS-0241 must be revalidated after a player interruption, camera or portrait switch, scene change, stale completion, or unknown in-flight outcome; otherwise the result is an abstaining receipt. Actual per-portrait intent checkpoints and native automation remain with existing continuity and native game owners. A sleeping/working Sim must be handed off via the existing household continuity evaluator, not by this optimizer clicking another portrait.

## Lagrange / KKT versus discrete choices

\`shadow_prices\` are nonnegative relative coefficients for the *tradeable* marginal cost of time, currency, need changes, skill, mood, failure risk and explicit action value. They are **not permission to violate** queue, money, deadline, player, irreversible-action or inventory constraints. The discrete action problem uses explicit feasibility filtering and bounded enumeration; applying KKT stationarity to an integer inventory menu would be incorrect.

\`allocate_continuous_time\` separately solves the differentiable, concave allocation problem \(\max\sum_i w_i\log(1+x_i)\) subject to \(0\le x_i\le u_i\), \(\sum x_i\le B\). The algorithm uses the exact clipped water-filling formula \(x_i=\operatorname{clip}(w_i/\lambda-1,0,u_i)\) with bisection on the budget shadow price. Its output includes allocation, dual price, binding budget and interior KKT residual. It remains advisory, not a substitute for discrete action feasibility.

## Consumer boundary and evaluation

Read-only call stack: observed PS-0241 snapshot + affordance/route records → \`optimize_activity_plan\` → **one next-step recommendation** + retained forecast/checkpoint gate → existing authority/continuity/native owner rechecks and, only when independently implemented and proven, native queue integration.

Run \`python -m unittest tests.test_decision_horizon -v\` plus existing \`tests.test_activity_chain\`, semantic preflight, native authority checker, human/peripheral/queue guards, and repo CI. Synthetic comparison fixtures deliberately show counterexamples to greedy earliest-deadline ordering, but **do not establish** actual real-game completion-time, income, need, career, queue-churn, CPU or player-interruption improvements. These dimensions require paired disposable vanilla/modified real-game measurements and observed CPU costs. No GP uplift is claimed.

**Current limit:** This is a useful interoperable mathematical policy slice, not full agent-independent native activation. Issue #171 owns source-verified exact-build integration. The unrelated BI-002 hunger baseline remains active. No local save, EA code, workstation, game Mods folder or host settings were changed.

## 2026-11-14 Closers: transient-floor, zero-utility and search-budget hardening

Verified PR #255 on `main` at `2e79e0ac1d1e3e8b2e032bb7d4540a91a499ac56`; final source CI run `43627569877` passed the offline suite. The independent closer pass identified three concrete read-only policy hazards: a benefit credited at the **end** of an action could conceal a need-floor violation **during** that action, a user-provided zero utility weight vector could turn a no-value action into a tiebreak selection, and exhausted search expansions could still expose an actionable-looking `next_step`. Regression repairs now check the initial and pre-benefit linear-trajectory endpoints, prohibit zero-positive-utility tiebreak actions and clear `next_step` when the search is truncated, leaving a visibly provisional forecast.

These constraints do not authorize native execution and cannot establish that any game feature, skill, actual moodlet, patch hook or probabilistic estimate works in The Sims 4. Respect `docs/handoff/BI-PS0245-CLOSERS-LOCAL-NATIVE-GATE-20261114.md` for the first host gate and issue #171 for native EA integration. `BI-002` remains an independent live hunger certification parent.

## Household wealth guard

The canonical budget supplies the reserve. `available_funds` is the current
household balance, through the existing Sims funds cap. A forecast may spend
only verified surplus. If already below the reserve, a step can increase
funds or leave them unchanged. Check the initial debit and the modeled
completion separately. Expected proceeds cannot cover the initial debit.

For either modeled outcome, let `loss = max(0, before - after)` and
`surplus = max(0, after - reserve)`. The additional utility penalty is
`0.05 * loss * (1 + max(0, 1 - surplus / (0.1 * reserve)))`. The extra
penalty tapers to its baseline over the first 10% of reserve in surplus.
These coefficients are initial policy values. Each step reports its
probability-weighted loss penalty and projected funds after debit and
success. Success earns the regular monetary weight on the realizable funds
change. Failure absorbs the upfront cost and stops the forecast pending
reobservation. The soft score cannot override feasibility, player intent,
needs, or queue constraints. Subsidies remain outside this forecast.
