# World-object highlight tracking and traversal learning

**Status:** opt-in, offline-evaluated host decision layer; **not** an installed screenshot detector, game clicker or Sims 4 live certification. Canonical machine policy: `contracts/world-traversal-learning.v1.json`. Pure engine: `betterinstincts/world_traversal_learning.py`. CLI: `python -m scripts.world_traversal_eval`.

## What changes for world traversal

A fixed HUD button can be calibrated to the same client coordinates until the layout changes. A tree, hydroponic plant, door, wall-mounted object or workstation cannot: camera pan, zoom, rotation, occlusion, Sim movement and player cursor ownership change which pixels represent the target. Existing `camera_traverse.assess_world_target` still owns geometry, margin and bounded replanning. When `world_target.highlight_frames` is supplied to `host_stack.evaluate_turn`, the new **highlight continuity gate** is evaluated *after* camera framing and *before* a framed object reaches independent click admission. Absent evidence is not treated as a successful hit.

Call stack:

1. Preserve target intent (portable semantic object kind and opaque current-session target ID) and existing selected-Sim/camera/lot ownership. Observe scene + capture quality first; prefer attested game-model/EA geometry when available.
2. Capture an in-world target `HOST_CAPTURE` frame with a fresh `capture_ref`, strictly increasing `frame_index`, `camera_revision`, target detection, bounding box and whether the pointer is actually hovering over the intended object.
3. Supply two independent **algorithm/sensor channels** for highlight evidence (for example `VISUAL_MASK` and `EDGE_CONTRAST`, or `GAME_SIGNAL` and one vision channel). This is a *data interface*: those channels are not secretly installed image processing engines, and correlated screenshot algorithms must be calibrated with labeled game examples rather than claimed fully independent.
4. Confirm two consecutive distinct, correctly ordered captures of the **same target, camera revision and overlapping object box**, with two concordant confident highlight cues in each. Only `LOCKED` permits the normal *candidate* to proceed to the independent existing camera, scene, exact-build, save, lot-footprint, operator/player-presence and input ownership admission. A locked highlight is never a permit on its own.
5. On one absent/unknown frame: stop and request fresh observation, **never click through a flicker**. On two fresh confidently absent frames: `HIGHLIGHT_LOST`. On camera revision change, highlighted-target ID mismatch, box-track drift, target gone, occlusion, player cursor leaving hover, or cue disagreement: report the specific state and **clear the click candidate**. Reacquire through existing bounded camera and safe-interior-rest routines, never blindly pan or auto-reclick.
6. After an authorized single effect, accept *only* independently observed `GAME_EVENT` or `OPERATOR_REVIEW` outcomes with separate before/after capture references. A SendInput ACK, coordinate error score, unverified menu, or the model's own prediction is not a success label. When the player takes over, do not train from the interrupted attempt.

`highlight_frames` is optional for compatibility; callers that supply it cannot bypass it. Legacy callers continue through previous camera-first and game/lot/player protections; deploying a sensor adapter should populate this field before relying on highlight-aware world-click evaluation.

### Host input example

```python
world_target = {
    "target_id": "plant-17",
    "observation": {
        "source": "HOST_CAPTURE", "capture_ref": "capture:2",
        "camera_revision": "camera:42", "target_id": "plant-17",
        "target_visible": True, "occluded": False,
        "bbox_client": [620, 360, 720, 490],
        "framing_attempts": 0,
    },
    "highlight_frames": [
        {
            "schema": "betterinstincts.world-traversal.frame/v1",
            "source": "HOST_CAPTURE", "capture_ref": "capture:1",
            "camera_revision": "camera:42", "frame_index": 1,
            "target_id": "plant-17", "highlight_target_id": "plant-17",
            "target_visible": True, "occluded": False,
            "object_confidence": 0.95, "pointer_context": "HOVERING_TARGET",
            "bbox_client": [619, 360, 719, 490],
            "highlight_cues": [
                {"source": "VISUAL_MASK", "state": "PRESENT", "confidence": 0.92},
                {"source": "EDGE_CONTRAST", "state": "PRESENT", "confidence": 0.87},
            ],
        },
        # A second distinct current-camera capture is required.
    ],
}
```

The attached `target_framing.highlight_tracking.state` can be `LOCKED`, `HIGHLIGHT_LOST`, `HIGHLIGHT_TRANSIENT`, `TARGET_LOST`, `TARGET_OCCLUDED`, `HIGHLIGHT_AMBIGUOUS`, `TARGET_IDENTITY_CHANGED`, `TARGET_TRACK_DRIFT`, `CAMERA_CHANGED_REACQUIRE`, `HIGHLIGHT_NOT_EXPECTED` or `HIGHLIGHT_UNVERIFIED`. Only `LOCKED` retains the prior camera-framed candidate; no new execution right is created.

## Learning from world outcomes — not cursor XY

The pure `learn_observed_attempts(model, attempts)` implements a bounded, regularized **online Beta–Bernoulli model** per portable context: exact game version, target kind, scene, view kind, zoom band and traversal strategy. A future local host may collect *user-consented, independently verified* examples, but this module performs **no automatic capture, disk write, profile discovery or background inference**. Individual Sim names, lot names, coordinates and raw screenshots never become model keys.

Outcome labels are observed `SUCCESS / TARGET_INTERACTION` with matching target identity, or `FAILURE / NO_RESPONSE|WRONG_OBJECT`; the source must be `GAME_EVENT` or `OPERATOR_REVIEW`, with different before/after capture references. Interrupted, guessed and inconsistent examples abstain. The bounded model holds 64 contexts, 4,096 samples/context and at most 128 examples/update. `rank_strategies` needs **8 independently labeled examples per context**, exposes posterior mean and conservative lower confidence bound, and always returns `execute_allowed=False`. It does *not* train a neural net or change control permits. The model can improve its ranking as evidence accumulates; only new independent holdout samples can measure generalization.

For an explicit offline evaluation, run:

```sh
python -m scripts.world_traversal_eval
python -m scripts.world_traversal_eval --out dist/world-traversal-eval/ci.json
python -m scripts.world_traversal_eval --model-out dist/world-traversal-eval/model-001.json
python -m scripts.world_traversal_eval --model-in dist/world-traversal-eval/model-001.json --model-out dist/world-traversal-eval/model-002.json
python -m unittest tests.test_world_traversal_learning -v
python -m scripts.semantic_preflight --consultation contracts/consultations/BI-WORLD-HIGHLIGHT-TRAVERSAL-LEARNING-20261110.v1.json --operation repo_mutation --file betterinstincts/world_traversal_learning.py --file betterinstincts/host_stack.py
```

Inputs/snapshots are bounded to ignored `dist/world-traversal-eval/` (plus the repo fixture). Model-in and model-out must be different; existing output names are protected. Snapshot migration/merging is **not** implicit. `evaluate_holdout` reports eligible-label coverage and Brier score against an uninformative 0.5 baseline; this is a synthetic algorithm check, not a real-world precision estimate.

## Acceptance and live P08 boundary

Offline P82/P07: tests require (a) two-capture lock, (b) transient flicker abstention, (c) sustained highlight disappearance, (d) camera/identity/occlusion/lot-context revocation, (e) model abstention without evidence, (f) held-out improvement on a declared *synthetic* fixture, (g) existing player authority outranks confidence. Run all repository CI and ontology chronology validators. P124 preserves existing `camera_traverse`, `host_stack`, `click_miss_cause` and `lot_boundary` as owners instead of duplicating them.

**P08 requires a separate, explicitly authorized disposable Sims 4 host session:** capture real frame pairs across zoom/pan/object occlusion/selected-Sim changes; label target highlight and actual menu/queue outcomes; measure false-positive/false-negative rates, calibration error, strategy Brier/coverage, drift recovery boundedness and action revalidation; demonstrate immediate player takeover and no Windows peripheral changes. Sample ordinary furniture, plants-on-planters, overlapping desk objects, walls vs gates, outside-lot terrain and formerly highlighted targets. An unknown patch or unapproved save blocks execution. PR #159 spatial-perception detection is an independent lane; its per-object outputs may **supply** evidence only after explicit, non-conflicting integration and calibration. No claim that that PR or this evaluator itself performs screenshot detection.

**Proof state:** offline repository logic can be tested in CI. Physical real-game labels, neural CV model training, installed sensors, and BI-002 hunger certification remain distinct unproven gates; do not close them from CI alone.
