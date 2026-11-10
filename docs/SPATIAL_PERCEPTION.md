# Spatial perception — host-owned observation and evaluation (P67/P62 + Fifth Gear)

**Status:** repository-only synthetic evaluator + optional host-listener observation seam. **Not** trained Sims 4 object detection or live scene recognition. No game action or save mutation is authorized.

## Why

A fixed client coordinate, a high-confidence object label, or a 2-D bounding box overlap is **not** a map of the Sims world. Agents must separate *what pixels might depict* from *where an object actually sits* and *whether the active lot is still in view*.

The host should own the common data contract and policy. The capture/detection adapter can eventually use native Win32 capture, Pillow, a licensed local object detector, or approved game-model geometry; the host **never depends on Cursor or Codex Playwright**. A detector's labels remain evidence-qualified claims rather than action permits.

## One read-only call stack

```text
authorized Windows host capture / optional reviewed game geometry
    -> bounded detector or human annotation [external adapter]
    -> spatial_perception.assess_frame(frame)
         -> scenes.classify(exact patch, independent visual + operator cues)
         -> camera_revision / capture ID / active lot ID consistency
         -> candidate objects + 2-D overlap projection
         -> independent polygon membership for lot and house footprint
         -> physical relations only with GAME_MODEL or OPERATOR_REVIEW contact
         -> conflicts and UNVERIFIED states
    -> optional host_listener.tick(observation["spatial_frame"])
    -> spatial_perception receipt (NO control permit)
    -> independent lot_boundary + screen_admit + presence and save gates
       [only a separate, authorized game-input executor may ever act]
```

The existing `scenes`, `lot_boundary`, `lot_floor_map`, `build_spatial`, `room_census`, `screen_atlas`, and `control_handoff` modules retain their authority. This module is an **evidence projection**, not a new scheduler, game controller, game-file parser or duplicate floor-map database.

## Spatial semantics

- **World vs screen:** `bbox` is a capture-relative rectangle. A camera pan, rotation, story/zoom change or capture revision invalidates old pixel locations. A viewport's left/right cannot define world north, street side, or creek side.
- **Active lot vs surroundings:** `active_lot_id` and `observed_lot_id` are separate. A mismatch returns `OFF_ACTIVE_LOT`; it cannot become ON_LOT merely because the frame contains a familiar object. Reviewed lot polygons distinguish inside-lot from street/neighbor/canal without inferring a gameplay click permit.
- **House footprint vs yard:** independently sourced, camera-matched `lot` and optional `house` polygons may classify projected object centers as `HOUSE_FOOTPRINT`, `YARD_OR_OPEN_LOT`, or `OUTSIDE_ACTIVE_LOT`. **HOUSE_FOOTPRINT is not proof of room interior**, particularly with missing roof/wall levels. Room enclosure, stories and doors stay in the existing structural models.
- **Wall vs gate vs fence:** they are different semantic classes. A strongly overlapping WALL/GATE contradiction makes both `AMBIGUOUS_STRUCTURE` and blocks their use as physical evidence. A gate-shaped opening is not automatically a wall and a tall wall is not a gate.
- **Relations:** `SCREEN_OVERLAP` only means projection coincidence. `GROWS_IN` (plant/planter), `RESTS_ON` (laptop/desk), `SEATED_AT` (chair/counter), `ATTACHED_TO` (toilet paper/wall), and `ADJACENT_TO` (broom/wall) are *hypotheses* until a same-capture operator-review/game-model contact attests the exact pair. Physical stacking, overlap, and adjacency are not interchangeable.
- **Tiny and novel props:** `WALL_MOUNT`, `DEVICE`, `BROOM`, `TOILET_PAPER`, and `UNKNOWN` are separate; absence of a supported type, confidence, provenance, contact or scene cue remains unknown rather than guessed. Extend the taxonomy with reviewed fixture cases, not a named-Sim/household hardcode.
- **Perception evidence is not authority:** the module always returns `execute_allowed: false` and `control_permit: null`. No build edits, purchases, camera panning, object selection, SendInput or save changes.

## Input contract and integration

A `spatial_frame` is opt-in on an active `host_listener.tick` observation and must share its `capture_ref` and `game_version`. It supplies `schema=betterinstincts.spatial-perception.frame/v1`, `source=HOST_CAPTURE`, `camera_revision`, `active_lot_id`, `observed_lot_id`, `width`, `height`, `scene_id`, two `scene_cues`, `objects` (ID, kind, bbox, source, confidence, evidence_ref, camera_revision), and optional `contacts`, `regions`, and reviewed `view`. See the versioned fixtures for full examples. This feature does not capture screenshots or invent object labels.

The host listener appends `spatial_perception` to receipts in normal, ambiguous-mode and player-yield paths. Even when the player is actively using the mouse, *read-only interpretation* can happen without screen control. A failed scene cue makes classification unverified. Caller-supplied evidence is not an automatically independent truth source.

## P67/P62 evaluator and acceptance

```sh
python -m scripts.spatial_perception_eval --out dist/spatial-perception-eval/ci.json
python -m unittest tests.test_spatial_perception -v
python -m unittest discover -s tests -v
python -m scripts.check_ontology
```

`contracts/evals/spatial-perception-cases.v1.json` owns 16 reproducible synthetic cases. They cover overlapping child/surface pairs, tiny wall attachments, chair adjacency, wall/gate contradiction, lot drift, house-vs-yard-vs-outside, camera-sidedness, unknown patch, stale camera, invented types, forged contact, and scene mismatch. The runner writes per-case PASS/FAIL, weakness class, elapsed milliseconds, counts, and proof ceiling. CI fails on any mismatch; no model tokens or network inference required. This is **a deterministic policy/evidence evaluator**, not an image-detection accuracy benchmark.

## What P08 can and cannot prove yet

The Windows game host still needs **consented, sanitized, capture-bound real Sims screenshots and reviewed ground truth** from multiple lots, camera rotations, zooms, roof/wall views, seasons/lighting, versions and packs. Then implement and benchmark a **host-owned** detector adapter (latency, precision/recall by category, structural confusion matrix and abstention rates) feeding the exact observation schema. A potential initial path is frame-region heuristics/optional local detector with real tests; do not ship claims from fixture-only labels. Revisit true 3-D attachment/slot geometry from authorized read-only game-file mapping where legally and technically justified. P08 must prove actual capture → classification on the real local Windows game, as a separate gate. It cannot be substituted by green CI or this evaluator.

**Persistent safeguards:** player-first interoperability, explicit save scope, no online EA connection, independent click admission, no Build/Buy until every floor/room is classified and the exact house has a verified My Library backup. BI-002 hunger certification remains independently active.
