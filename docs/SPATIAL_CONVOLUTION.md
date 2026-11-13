# Spatial convolution learning: bounded model, preserved gameplay authority

**Status:** implementation is an offline/opt-in trainable model; not an installed Sims 4 image detector, game mod, or live gameplay certification. Owner: `betterinstincts/spatial_convolution.py`; machine policy: `contracts/spatial-convolution.v1.json`. Existing `traversal_cost_learning` owns verified per-edge latency updates; `household_navigation` owns graph topology and final route. Issue #171 owns actual EA-native integration, and BI-002 hunger remains an independent live gate.

## Measured hypothesis and call stack

A tiny convolution can learn spatial blockage patterns from independent observed outcomes when a fixed map graph alone cannot. It is **not** a magical general-purpose intelligence engine. An operator/verified EA source supplies a 5×5 local floor patch with three binary channels (`WALKABLE, BLOCKED, TARGET`), with at least 20 classified cells and exactly one reachable target cell. Each patch must also bind its scope, lot, exact game build, graph revision and geometry source to the currently verified world; an apparently valid grid from another save/lot/build is rejected. Two trainable 3×3×3 filters slide over the 5×5 patch; ReLU and 3×3 spatial average pooling feed a trainable logistic probability of BLOCKED. Online one-step SGD updates **both filters and output head**. No third-party ML package is required.

```
verified floor patch + known graph edge + current scope
 -> verify geometry source, lot/floor, player and scene
 -> 3x3 convolutions / ReLU / mean pool / sigmoid
 -> independently observed traversal outcome
 -> replay fingerprint + 1-in-5 deterministic holdout
 -> bounded SGD (train only) OR prequential Brier validation (holdout only)
 -> context-scoped model (explicit opt-in local atomic write)
 -> optional household_navigation.spatial_convolution
 -> non-actuating spatial_learning_advisory receipt
 -> existing verified route and player/native effect gate remain unchanged
```

The holdout is selected from the *pre-action* capture reference hash, not from labels or model predictions. Predictions are **withheld** until at least 24 training samples (6 each class), 8 disjoint holdouts and prequential Brier loss beats a smoothed constant-rate comparator by 0.02 per holdout. This is intentionally conservative; synthetic tests do not establish real-world calibration.

## Data authority and consent

An outcome needs two distinct capture references, exact scope/patch/graph revision, source attestation (`GAME_ROUTE_PROBE` with verified sensor OR `OPERATOR_VERIFIED_TRAVERSAL` with human review), and observed target or blocked original region. Model fingerprints use SHA-256 of patch-build and pre-action capture identity; no raw Sim/save names are persisted. A stale scene, unknown or active player direction, player takeover, cross-world patch, unknown floor, unverified passage, malformed tensor, cross-save model, exhausted event budget or conflicting writer is denied. Only one bounded sample is processed per explicitly invoked call; no periodic sampling, OS hooks or telemetry are installed.

Call `learn(snapshot, event, patch, prior=model, explicit_opt_in=True)` for pure in-memory training, or `record_local_sample(snapshot, event, patch, explicit_opt_in=True)` for an atomic opt-in profile update. `load_local_model(snapshot)` does not scan other profiles. A future local adapter must independently establish sensor provenance and opt-in before invoking these; there is no automatic learning claimed in the packaged game.

`plan_household_navigation(snapshot)` accepts an optional `spatial_convolution` mapping with `model`, `patch`, `from_region` and `to_region` for the proposed *first* passage. It only attaches `spatial_learning_advisory` after existing route, scene, player, and graph checks; it never reranks the path. Existing callers without this mapping have unchanged output and control authority. Do not confuse camera motion with Sim travel, or use an uncalibrated model to create blocked passages or clicks.

## P141 → /fifth-gear scoped disposition

P141 considered dense host CNN/sensor takeover (**deferred**, PR #159 independent), generic action reinforcement learner (**rejected**, reward/control authority unproved), fixed edge-detection kernels (**weakened**, do not learn), and source-attested trainable convolution (**selected**). P95 builds the small verified input→conv→outcome seam, P82 measures training, holdout/replay/provenance and baseline, P08 real Sims session remains **NOT_RUN** in GitHub-only runtime, P07 implements integrated tests/CI, and P124 keeps the model isolated and the verified navigation planner unchanged. No host slash-skill activation or five spawned agents are implied by repository work.

## Validation and forward gates

Run `python -m unittest tests.test_spatial_convolution -v`, `python -m scripts.check_ontology --base-ref BASE_SHA`, `python -m scripts.check_native_gameplay_authority --base-ref BASE_SHA`, then full CI. Calibration on real game observations must be independently evaluated per patch, including latency and CPU memory; only after reproducible gains may an effect-owner consider using this advisory to prioritize already verified routes. To deliver playable native gameplay, obtain exact-patch EA tuning/hook evidence and local disposable save A/B plus rollback. Preserve all BI-002 hunger gates.
