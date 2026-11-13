# Adaptive local traversal learning

**Status:** Offline, opt-in, versioned policy and local profile model; **not** Sims 4 in-game sensing, camera SLAM, a gameplay mod, or an effect permit. The independent active Sims host and EA native integration still require local validation. BI-002 hunger remains active.

## Program and owner

The existing source-qualified region graph in `betterinstincts/household_navigation.py` remains the **only** Sim routing owner; `betterinstincts/traversal_voi.py` still enforces at most one Walk followed by a meaningful needs/career/skills/whims action. `betterinstincts/camera_traverse.py` owns view-only camera travel. `betterinstincts/screen_admit.py` and player presence own real inputs. The new `betterinstincts/traversal_cost_learning.py` only calibrates verified passage **costs**. Its output cannot add a passage, prove an affordance, certify a Sim's arrival as task completion, or unlock a game click.

### Mathematical policy

For an already-verified directed passage `e=(u,v)`, the current graph supplies immutable baseline cost `w_e` and source-reviewed expected time `T_e` milliseconds. A consented independent source observes completion `t_i` (not a screenshot guess), with `100 <= t_i <= 300000`.

The clipped latency ratio is:

```text
r_i = clip(t_i / T_e, 0.5, 3.0).
```

Success-only duration and all-outcomes failure EWMA are:

```text
m_n = (1 - alpha_t) m_(n-1) + alpha_t r_i
alpha_t = 1 / min(N_success, 16)
f_n = (1 - alpha_f) f_(n-1) + alpha_f I[failed]
alpha_f = 1 / min(N_observed, 16)
```

A small evidence count should not override baseline engineering. Use a support-shrunk, capped factor:

```text
s_n = min(0.75, N_observed / (N_observed + 6))
q_e = clip(1 + s_n ((m_n - 1 if N_success > 0 else 0) + 1.5 f_n), 0.75, 2.5)
W_e = round(1000 * w_e * q_e)      # deterministic fixed-point integer
```

The existing Dijkstra planner minimizes `sum(W_e)`, with its existing deterministic hop/path tie breaks and step budgets. **No samples means ordinary unmodified route ranking.** A model cannot make an unverified edge walkable. This favors faster and more reliable observed routes, not repeated action spam. These are heuristic, calibrated-cost equations, **not** a claim of an RL-trained neural net or certified world model.

## Explicit learning and lifecycle

1. A user explicitly activates the **existing** host listener and opts in to route learning. The port `host_listener.observe_traversal_transition(session_id, snapshot, event, explicit_opt_in=True)` never creates a sensor or controller.
2. A separately admitted game route probe or a reviewed real traversal reports an opaque event reference, the current exact build/save/household/lot/graph/actor/scene, two distinct capture refs, start/end regions, duration on success (or blocked-at-origin failure), and uninterrupted player absence. Unknown, stale, fake, camera-only, player-interrupted or off-lot evidence is rejected.
3. The model retains only aggregate edge timing ratios, bounded failure statistics and hashed replay identities; raw capture data, human/Sim names, EA assets and Sims save content are not stored. A conservative hashed Bloom history rejects replayed events across sessions and may abstain on collisions.
4. If the opted-in host calls `plan_learned_traversal(session_id, snapshot, explicit_opt_in=True)`, the machine loads its own versioned, scoped JSON model and passes it to the **existing** pure planner. All player/scene/queue/VOI and independent effect gates still apply. No autorun, watcher, background telemetry, or automatic game process modification is installed.

Per-installation files live under the existing user-scoped BetterInstincts runtime home resolved by `bootstrap.paths()`; never under a checkout, game's Mods directory, screenshots, or saves. Single-writer atomic replacement refuses stale concurrent locks. Storage is capped at 64 separate profiles, 20,000 events/profile, 512 edges/profile and 128 KiB/model. Unknown/corrupt models use baseline routing for prediction; training refuses mismatched contexts. The user can stop the host listener and delete their optional model data without modifying the game or replaying events.

## Architecture alternatives and acceptance

P141 evaluated a separate RL locomotion agent (rejected for unsafe, unverified actuator and sparse feedback), another SLAM/vision subsystem (deferred to PR #159), manually weighted static maps (insufficient), and this bounded observed-edge learner (selected). P95 retained existing graph/host/VOI owners rather than cloning a world model. P82's falsifiable synthetic cases: same graph and objective produce lower learned route cost only with real structured evidence, replay is idempotent, failure raises local cost, revision changes invalidate the model, player presence refuses both training and route proposals, and corrupted/cross-profile models never grant action. P08 **requires a local exact-build Sims game**, operator-approved disposable save, instrumented actual passage timing and independent in-game before/after action checks; the GitHub provider cannot perform this trial. P07 and P124 can integrate source, tests and docs without pretending that offline CI certifies P08.

### Offline checks

```sh
python -m scripts.semantic_preflight --consultation contracts/consultations/BI-TRAVERSAL-ADAPTIVE-COST-P141-FIFTH-GEAR-20261112.v1.json --operation repo_mutation --file betterinstincts/traversal_cost_learning.py --file betterinstincts/household_navigation.py --file betterinstincts/host_listener.py
python -m unittest tests.test_traversal_cost_learning tests.test_household_navigation tests.test_traversal_voi -v
python -m scripts.check_household_navigation
python -m scripts.check_native_gameplay_authority --json
python -m scripts.check_ontology
python -m unittest discover -s tests -v
```

**Proof ladder:** reviewed consultation → tested source → CI → merged main → local installed host → consented real game outcomes. These are independently observed statuses, never synonyms.
