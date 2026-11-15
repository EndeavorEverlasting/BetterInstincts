# Microsystem mathematics — reusable Bellman / Lagrange–KKT / Gaussian umbrella

**Purpose:** Every registered microsystem has a **common mathematical evaluation seam**, without having to copy the solver or concede ownership to a monolith. A mathematically better design can compete with, augment, or replace a narrower planner **once independently validated**. Existing microsystem behavior remains a legitimate fallback when evidence is incomplete.

**Machine registry:** `contracts/microsystem-math.v1.json` (21 known microsystems, including the seven existing `domain_cascade` poll domains). **Policy adapter:** `betterinstincts/microsystem_math.py`. **Common poll caller:** `betterinstincts/domain_cascade.py#poll_cascade`. Both are `POLICY_ONLY`, no installed game agent, no EA native hooks, no mouse/key input.

## Exact mathematical ownership — reuse, do not reinvent

| Mechanism | Canonical function | Use |
| --- | --- | --- |
| **Bellman / finite-horizon expected utility** | `decision_horizon.optimize_activity_plan` | Observed action DAG, inventory and skill transitions, travel, deadlines, need floors, spending, queue owner, absorbing failure and one proposed next step |
| **Lagrange multipliers / KKT** | `decision_horizon.allocate_continuous_time` | Concave, continuous distribution of a known remaining time budget across activities; never treat a fractional allocation as permission to buy an integer part or violate a hard safety bound |
| **Gaussian process / uncertainty** | `ecology_forecast.compare_duration_models` | Duration estimates from source- and build-matched chronological samples, compared against a deterministic conservative upper bound. A Matérn-3/2 GP only wins if holdout accuracy and safety coverage improve |

This means Gaussian here is **statistical uncertainty prediction**, not Gauss's law of electromagnetism. New Gaussian-family and other planners may be added as independent candidates through the comparator. A mathematical identity, apparent sophistication, or source-only synthetic pass is not measured gameplay superiority.

## P124 composition and progressive disclosure

```text
existing domain_cascade and domain-specific services
  -> all current domain receipts retained unchanged
  -> math_umbrella / registry per active domain
       -> missing/stale/mismatched packet: EXISTING_MICROSYSTEM (fallback)
       -> full fresh packet: PS0245 Bellman and KKT + PS0241 GP comparator
       -> option: independent alternative planner / holdout comparator
       -> choose winning advisory only under shared feasibility
  -> a separate verified native adapter, if developed/certified, may
     consider the advisory after player/scene/queue/save gates
```

`domain_cascade.poll_cascade` automatically checks all seven poll domains, **without requiring a new agent or extra screen controls**. It adds a compact top-level `math_umbrella` receipt. The old `receipts` array, domain order and `gate` continue to come from the original owners; player-directed polling immediately yields. Each domain falls back by default, rather than fabricating probability, history or tuning evidence.

The registry also lists **14 additional microsystems**, including career events, work tones, school, homework, garden, eco fabrication, purchase dialogs, household allocation, upkeep, scenarios, activity chains, traversal and queues. They expose the same direct `evaluate_microsystem_math` API for opt-in composition; they are not incorrectly claimed to be automatically polled by `domain_cascade` if they have no active receipt. A future native or domain-local caller can pass one source-qualified packet and preserve its original owner as fallback. The registry is open to new entries and architectures after source and tests, not a locked enumeration.

## Evidence admission / mathematical fallback

An optional `betterinstincts.microsystem-math-packet/v1` must identify `microsystem_id`, current `capture_ref`, `sim_ref`, `game_build` and provenance; Bellman snapshot/steps/routes, KKT time budget/activity weights and Gaussian duration samples/action/context/baseline. The snapshot's actor and selected Sim must match. Discrete Bellman feasibility, need-floor, time, funds, resources, completed-step and player gates are **not** relaxed by soft shadow prices. KKT is a separate continuous relaxation. The GP can return `DETERMINISTIC` for missing/unqualified samples without making fabricated observations.

If a portfolio-level math packet is out of scope or malformed, the cascade explicitly rejects it but still returns its unmodified legacy domain receipts. If the optional math registry itself is missing/invalid, the registry-independent emergency fallback preserves normal and player-owned domain results without retrying the broken registry. Mathematical evidence is optional, not a new failure dependency for established gameplay. If all three methods have complete valid inputs and Bellman finds a bounded, positive, non-truncated candidate, output `MATH_ADVISORY` with selected first-step ID, KKT allocation and Gaussian model status. Otherwise `FALLBACK_EXISTING` with a reason. **Every mathematical receipt has `execute_allowed=false` and no `control_permit`.** A model cannot authenticate its own source by writing `EA_NATIVE` or `LOCAL_OBSERVED` in an input dictionary.

## Future superior planner — architectural freedom without regressions

A new planner can be named `planner_id` with its own observed candidate step graph and predictions. To become `SUPERIOR_ADVISORY` it must supply independently reviewed, source/build/capture-matched holdout evidence (at least eight distinct captures), at least 10% lower mean absolute prediction error, **no individual holdout error regression**, and a proposed first step that the *existing* Bellman feasibility gate independently admits on the same current actor/scene snapshot. New algorithms aren't restricted to a predetermined family, and may choose different steps. On failed holdout, stale source, unknown effects, unsafe option or inconclusive evidence, the canonical math baseline remains; if *that* is unproven, the older microsystem remains. No challenger is entitled to a game input permit merely because it wins an offline comparator.

This is a **source-level comparison contract**: the caller's "independent reviewer" fields are not proof of a real external reviewer. Actual external review, provenance, speed/quality benchmarking, exact-build safety and installed effect verification must still be independently observed for model promotion in a native mod.

## Domain routing examples

- Work/Chance cards: start `docs/CAREER_DECISIONS.md`, load `career_service`/native event semantics; supply observed event outcomes before using the shared math bridge. The existing Work Hard/welfare checks remain.
- Six needs and balance: `need_services`, `balance_service`; preserve survival floors and emotional recovery, never replace with a high utility candidate below the floor.
- Gardening/purchase/ecology: PS0241 activity DAG/PS0245 time constraints and GP timing; use source-confirmed inventory/cost and observable completion receipts. Never buy every item just because it appears in a scrollable catalog.
- Household/skills/social/traversal: preserve roster/queue/active-Sim ownership, deadlines and scene safety; optional planner improves quality only with complete evidence, not from a global daemon.

**Progressive disclosure:** Start from `docs/DOMAIN_CASCADE.md` (or glossary `DOMAIN_CASCADE`); enter this page when mathematics is actually required; then load only `docs/DECISION_HORIZON.md`, `betterinstincts/ecology_forecast.py`, or the specific microsystem source. No copy of the full math contracts goes into AGENTS.md, custom instructions or always-loaded context.

## Test, certification and closeout

Regression: `tests/test_microsystem_math.py`, `tests/test_domain_cascade.py`, `tests/test_decision_horizon.py`, `tests/test_ecology_forecast.py`, plus full CI. Compare exact legacy receipts before/after enabling a math packet, adverse player-owned and stale samples, validated challenger success, unqualified challenger fallback and no action permit.

**P83/P03:** independently reconciled merged career PR #264 and the already merged PS0245 Bellman/KKT/GP owner. **P141:** selected mathematical composition rather than duplicating three solvers or replacing microsystems. **P124:** one adapter and one registry, maintained original domain owners. **P04:** remaining real native game hook/observed outcome work belongs to issue #171, not an imagined launched remote worker. Connected GitHub can run CI and merge source, not verify Sims native game behavior.

**Proof ceiling:** repository policy and CI only; no imported EA assets or native module installed here, no game event responded to, no player override or rollback measured. Continue separate current career, purchase, preference and BI-002 P08 gameplay trials without restarting already admitted trials.
