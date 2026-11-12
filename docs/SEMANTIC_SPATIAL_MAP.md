# Semantic SLAM: world-space objects, floor and elevation (offline candidate)

**Authority:** `contracts/semantic-spatial-map.v1.json` → `betterinstincts/semantic_spatial_map.py` → `betterinstincts.room_map_traverse.plan_semantic_3d_target`. The existing lot-floor graph, world-target highlighting, camera traverse, game scene, native-gameplay, save and player-first input guardians remain unchanged. **No new mouse worker.** `PR #159` is a separate unmerged CV/sensor writer; do not copy its code or claim that it has been integrated.

## Vocabulary and why VIO is not the product here

* **VIO** is visual-inertial odometry; The Sims 4 does not expose a physical IMU feed. Reproducing headset VIO is not justified.
* **SLAM** requires both localization and a persistent environment model. We implement a bounded **semantic map + local camera relocalization seam**, not a dense visual SLAM backend or trained object detector.
* **World XYZ** is an EA lot-relative metric-like coordinate triple, **Y up**. Floors/stories are categorical and independently attested. Viewport `client_xy` is a projected image pixel; a change in camera, zoom, story, viewport or capture revokes that projection.
* **Category** (fridge/shelf/counter/etc.) is not an object instance. A label requires EA catalog or two-view/operator-reviewed classification with threshold; unknown classes must remain unknown.
* **Relations**: `ON_TOP_OF` (supported above), `INSIDE` (contained), `BESIDE` (same-story horizontal adjacency), `WALL_MOUNTED_TO` (wall attachment, potentially vertical adjustment). Geometry and evidence support *each* relation; a 2D overlap is never treated as containment.
* **Occlusion and affordance** are separate: contained items may require opening a cabinet or changing perspective and re-observation; visible shelves may still hide their pickable subparts. A framed target is not permission to interact.

## Pipeline and call stack

1. An **authorized passive sensor** or **read-only EA geometry extractor** supplies explicit object identities, patch, semantic categories, floor IDs, world centers/sizes and independent provenance. The map **rejects invented depth from a single screenshot**. Current sensor PR #159 remains separately owned and unmerged; no automatic scan, screenshot retention or trained weights.
2. `compile_spatial_map` validates identity, spatial evidence, world vertical ranges and parent relationships. It returns an in-memory advisory document. The original `lot_floor_map` remains canonical for profile-local memory; do not create a competing persistent cache.
3. At each view lease, observe **at least five** distinct known 3D landmarks spanning noncoplanar elevation and at least two capture frames. `calibrate_camera` fits a 3D→2D affine camera using a bounded least-squares solve; reject degenerate sets, stale revision, high residual (max 8px, RMS max 5px). This is appropriate only as a *local* orthographic/pseudoperspective approximation. Full perspective/rotation changes require recalibration; it cannot prove global metric accuracy.
4. `plan_semantic_3d_target` routes the map through the current room-traversal planner and returns an advisory `FRAMING_CANDIDATE` only when floor, camera, capture, target identity, current visibility and bbox agree. If not, it returns a **specific next observation** such as change story, open container, recapture or relocalize.
5. Independent `world_traversal_learning.assess_highlight_continuity`, `lot_boundary`, `save_policy`, `player_presence` and `screen_admit` still govern any actual in-game action. Never auto-reclick, repurpose advisory pixels as a click permit, alter Windows input, or touch saves.

## Observable prototype and growth into real CV

Synthetic fixture: wall shelf at Y=2.5, table lamp at Y=2.5, upper-story landmark at Y=6. Under the same synthetic affine camera, equal horizontal XZ does **not** imply equal screen XY when elevation differs. Compare reprojection residual against stored camera-bound pixels; reject conflicting edges, single-frame geometry, degenerate anchors and adversarial outliers.

Future **real** P08 sensor: classify base-game furniture with *operator-consented, labeled, bounded* real screenshots (EA IDs where available), record per-category precision/recall and held-out accuracy, then promote only tested object detections into an adapter. Evaluate floors, ceiling/wall sliders, inside/outside, stacked furniture, occlusion, category confusion, camera pan/zoom/perspective and wrong-object clicks. Minimize data collection; keep raw frames private and ephemeral. First local run needs exact game patch, approved disposable session, independent landmark/capture provenance, host ownership, user-idle/scene/save/lot admission and one-effect consent. No result here is live gameplay proof.

**BI-002 hunger is still active.** This semantic mapping capability supports navigation; it is neither hunger certification nor a prerequisite for the six-needs/income trajectory.

## Validation

```bash
python -m scripts.semantic_preflight --consultation contracts/consultations/BI-SEMANTIC-SLAM-20261112.v1.json --operation repo_mutation --file betterinstincts/semantic_spatial_map.py --file betterinstincts/room_map_traverse.py
python -m unittest tests.test_semantic_spatial_map -v
python -m scripts.check_native_gameplay_authority --base-ref <PR_BASE_SHA>
python -m scripts.check_world_traversal_harness
python -m scripts.check_ontology
```

**Proof ceiling:** Offline geometry, relational and local-camera projection test only. No real screenshot/classifier training, runtime calibration, player-controlled game interaction or merged PR #159 is claimed.


## 2026-11-12 closer correction — external active-world provenance

P83 verified that an **old map and old camera calibration could agree with each other** even when the actual game had moved to a different lot/build. The read-only targeting function now demands independent `active_world` evidence (source, lot_id, game_build, floor_id, camera_revision, capture_ref). Absent or mismatched evidence abstains. An `UNKNOWN_OBJECT` category cannot be promoted into a framing target. The room-map bridge passes this record through; it does not invent it from the stored map. Camera/capture/floor gating and player-first effect admission remain independent and intact. Source labels are not live proof by themselves.
