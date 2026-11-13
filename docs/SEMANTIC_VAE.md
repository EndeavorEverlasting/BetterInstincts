## 2026-11-13 — The Closers: installation-profile isolation and CLI readback

**P83 verified gap in original #221:** one user could have several local BetterInstincts installation profiles with separate opt-in settings, but the original on-disk filename keyed only game/save/lot/build/graph. On the same world, one named profile could read, continue training, or delete another profile's checkpoint despite distinct consent. This has now been repaired in the existing owner; not a new service, sensor or learning framework.

**Rule:** All CLI operations (`enable`, `disable`, `status`, `train`, `purge`) resolve the **active** installation profile unless explicitly passed `--profile EXISTING_PROFILE`. Unknown profile IDs are rejected before any mutation. `record_if_enabled` passes its selected consent profile to the local training write. Low-level read/write/purge APIs also accept `profile_id` (default: `"default"`) and use the exact same storage selector.

**Migration/retention:** Existing `default` profile data stays at the **unchanged original context-hash filename**; there is no implicit migration, overwrite or deletion. Named profiles now use an opaque hash of `profile_id + world context`, with no fallback into the default model or other named models. `purge` deletes only the selected profile and provided verified world context; `disable` preserves that data.

```sh
python -m scripts.semantic_vae status
python -m scripts.semantic_vae status --profile family
python -m scripts.semantic_vae enable --profile family --ack-local-data
python -m scripts.semantic_vae train --profile family --snapshot S.json --event E.json --patch P.json
python -m scripts.semantic_vae disable --profile family
python -m scripts.semantic_vae purge --profile family --snapshot S.json --ack-delete-local-data
python -m unittest tests.test_semantic_vae tests.test_semantic_vae_cli -v
```

The named profile must **already exist** through the canonical installation-profiles owner. The CLI cannot create it on an arbitrary supplied name. A profile is an installation-local preferences boundary for the same computer user, not an OS security account. Other OS users should have distinct OS-level user profiles. A direct call to `record_local_sample(..., explicit_opt_in=True, profile_id="family")` is an explicit lab/test data operation, not a silent host collector; applications should call the preference-checked `record_if_enabled` instead.

**Evaluation limitation:** The prequential reconstruction metric is measured on synthetic/offline examples so far. It does not show the decoder improves route choices, camera tracking, object detection, real SLAM, or Sims gameplay. Existing graph/camera/VOI gates remain authoritative; no local P08 or actual MoonWake group-walk/agent-dispatch proof is implied. Next local owner: an operator-authorized exact-patch, active-session, source-calibrated observation adapter and independent real labeled holdout/CPU measurements; BI-002 hunger remains separate and ACTIVE.

# Local semantic VAE learning — MoonWake Sixth Gear (2026-11-13)

**Purpose.** Every opted-in BetterInstincts installation can learn from *its own* independently observed, admissible The Sims 4 navigation examples. The user's computer is a **local training workstation**, not an automatically exposed internet server. No central service, upload, background daemon or global telemetry is installed. **State:** genuine trainable Python prototype + local storage; not yet a running Sims mod, calibrated screenshot recognizer, real VIO/SLAM, or certified game integration.

## Canonical owners and Sixth Gear decision

`contracts/semantic-vae.v1.json` owns training semantics; `betterinstincts/semantic_vae.py` owns a small variational encoder/decoder and local checkpoint. `spatial_convolution.py#_sample` remains the *single existing authority* for calibrated semantic 5×5×3 input and independent traversed/blocked outcomes. `traversal_cost_learning.context_hash` keeps a model bound to exact world/save/household/lot/build/graph without storing private names. `camera_traverse.py` remains the separate camera owner; `household_navigation.py` owns verified walkable routes. `screen_admit`, player presence, scene/save/lot and game-build gates still own every effect. Do not replace or bypass any of these.

P141 considered four hypotheses:
1. Shared/federated automatic gameplay server — **REJECTED** (no user consent, network/storage/security architecture, or need to accomplish local learning).
2. Video/raw-screenshot VAE — **DEFERRED** (no proven camera sensor or privacy-preserving training capture; the raw images are unnecessary for the first experiment).
3. A reconstructed dense SLAM map used directly to create routes — **REJECTED** (the decoded scene may hallucinate walls or connections; the physical graph must remain source verified).
4. **SELECTED:** a tiny local semantic VAE on existing, independently reviewed grid patches, with replay protection, a bounded corpus, deterministic holdout and the current native-gameplay authority intact. Evidence: `docs/SPATIAL_CONVOLUTION.md` and `tests/test_spatial_convolution.py` already expose a verified intake.

P95 call stack:
`source-verified game event + current 5×5×3 grid` → `spatial_convolution._sample` (scope, route, independent before/after, player interruption) → `semantic_vae.learn` (replay/deterministic holdout) → `[μ, log σ²]` → `z = μ + exp(log σ²/2)ε` → `sigmoid decoder` → `mean Bernoulli reconstruction loss + 0.02×KL[q(z|x)||N(0,I)]` → clipped deterministic SGD step → atomic, private local checkpoint. A decoder advisory, if calibrated, *cannot* become a validated wall, physical passage, walk, camera pan or click. There is no game effect adapter.

P82 measured hypothesis: on independently reviewed semantic patches the encoder and decoder weights should change after training, duplicate evidence should not increase counts, one-in-five deterministic holdouts must never modify weights, and all missing consent/cross-world/unsafe storage samples must abstain. A heldout reconstruction metric is compared against uniform-Bernoulli baseline (0.693 nats per cell), with a conservative 24 training + 8 holdout + 0.01 improvement floor before research advice. Synthetic tests only prove the algorithm and gates; **real** game calibration needs exact patch and independently sourced examples.

## Local opt-in and storage

Install/clone default is **OFF** (`contracts/installation-profiles.v1.json` → `learning.semantic_vae=false`). If the operator wishes to enroll a local instance, use its canonical checkout, with the existing `bootstrap.py`-resolved use path:

```sh
python -m scripts.semantic_vae status
python -m scripts.semantic_vae enable --ack-local-data
python -m scripts.semantic_vae train --snapshot selected-verified-snapshot.json --event selected-reviewed-event.json --patch selected-source-verified-grid.json
python -m scripts.semantic_vae status --snapshot selected-verified-snapshot.json
python -m scripts.semantic_vae disable
# To erase ONE exact scope's stored training data / learned weights:
python -m scripts.semantic_vae purge --snapshot selected-verified-snapshot.json --ack-delete-local-data
```

The three `train` inputs must originate from an independently verified and currently authorized game/lab adapter. CLI does not generate them, monitor the game, scan files, move the camera or click. `enable` only flips a typed local setting; it does not authorize background collection. Normal consumers can call `record_if_enabled(snapshot,event,patch)` for **one validated observed example at a time**. Direct pure `learn(..., explicit_opt_in=True)` is for bounded offline tests; `record_local_sample(..., explicit_opt_in=True)` is a lower-level explicitly requested training port. No raw screenshot, free-form chat, Sim names, account identities, household names or game saves are stored.

The checkpoint is scoped to the existing user-owned `bootstrap.paths()['use'].parent / runtime / semantic-vae / <opaque-context-hash>.json`. The *same* atomic JSON checkpoint holds bounded trainable weights, a 16 KiB replay Bloom bitmap and the **latest 128** accepted source-qualified semantic vectors, while preserving lifetime counts, model weights and holdout accumulators for up to **10,000** accepted examples. At capacity training refuses further examples; false-positive Bloom matches abstain, never silently re-train a replay. The file is capped at 125 KiB, with a per-context lock, no-follow/symlink checks, owner-only file creation and no network. Different save/lot/build contexts have isolated hashes; 64 context files maximum. Uninstall never silently removes personal data. `disable` stops new training but intentionally retains data; the explicit scope-specific `purge` command erases the selected checkpoint.

There is intentionally no automatic federation or model sharing. A hypothetical future collaborative learning pool would need **separate** opt-in, aggregation/anonymization threat modeling, model-poisoning defenses, clear licensing, rollback, privacy review and independent authorization. The current product does **not** require users to run a public-facing server.

## Safety, performance, and remaining runtime proof

The VAE reads only verified semantic 5×5×3 patches of three channels: `WALKABLE`, `BLOCKED`, `TARGET`. It does not invent objects or bypass current map topology. No new host service/OS hooks, per-frame capture, UI automation, player queue action, EA tuning/script, or auto-training loop is installed. Camera-only movement is not Sim locomotion. Inferred layout is non-authoritative until independently verified. Real `P08` proof remains **BLOCKED_LOCAL_GAME_ACCESS** from GitHub, and the existing BI-002 hunger A/B and rollback are still active and separate.

To validate offline:
```sh
python -m unittest tests.test_semantic_vae tests.test_spatial_convolution -v
python -m scripts.check_semantic_vae
python -m scripts.check_ontology
python -m scripts.check_native_gameplay_authority --json
```

For game-capable certification, obtain an explicitly selected disposable save, exact game build, scope-stamped capture/EA geometry, source-reviewed outcomes, and monitor actual RAM/CPU/sample latency. Compare genuine independent heldout reconstruction and downstream object/route calibration against the existing convolution/graph baselines. Only after these tests should an adapter be authorized. **A decoded map never overrides a real world or game-safety permit.**

P07 scope: offline Python/contract/test/CLI only, no game patch. P124 integration: reuse the existing convolution intake and local bootstrap path, rather than adding a new learner/cursor/scheduler owner. This document is the handoff; GitHub test/merge and local installed runtime must be reported separately.
