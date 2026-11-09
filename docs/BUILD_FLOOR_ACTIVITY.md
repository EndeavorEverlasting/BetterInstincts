# Build floor activity — listener peer (P95)

**Owner:** `contracts/build-floor-activity.v1.json` / `betterinstincts/build_floor_activity.py`
**CLI:** `python -m scripts.build_floor_activity`
**Wired into:** opt-in `host_listener` ticks when `build_or_buy_mode` is true
**Proof ceiling:** offline census only — not a live story sensor cert, not Env/bill meter cert

## Operator ask

While building, the listener should notice **which floor** is active, whether work spans **one floor or several**, and infer a **floor theme** from the kinds of items present — so host logic can later suggest Build/Buy optimizations.

## Selected architecture: `FLOOR_ACTIVITY_CENSUS`

1. Normalize `active_story` with existing `build_spatial` aliases (`1`/`GROUND` → `FLOOR_1`, `2`/`UPPER` → `FLOOR_2`).
2. Union `stories_touched` + item stories → `SINGLE_FLOOR` or `MULTI_FLOOR`.
3. Per-story category histogram → theme (`kitchen`, `bedroom`, `outdoor_garden`, …).
4. Map theme → advisory `build_optimize` category hints (no auto-place).

Rejected: pixel-only height as story proof; inventing catalog rows from screenshots; a second spatial daemon.

## Observation fields (attested)

```json
{
  "build_or_buy_mode": true,
  "active_story": "FLOOR_1",
  "stories_touched": ["FLOOR_1", "FLOOR_2"],
  "floor_items": [
    {"id": "hydro-1", "category": "planter", "story": "FLOOR_1", "label": "Hydroponic Planter"}
  ]
}
```

Items and stories must be operator/sensor attested. Until a certified Build HUD story sensor exists, supply them explicitly on the listener tick observation.

## CLI

```sh
python -m scripts.build_floor_activity themes
python -m scripts.build_floor_activity evaluate --observation dist/game-host/build-floor-obs.json
```

## Evolution path

Theme → optimize hints is the seed for host suggestions (e.g. kitchen → appliance/counter pools). Live placement and meter confirmation remain separate P08 gates. Does not close BI-002.

## Room census peer

Optional `lot_model` Build/Buy observations attach a compact read-only census. See [ROOM_CENSUS.md](ROOM_CENSUS.md) for the full-inventory CLI and [room-census contract](../contracts/room-census.v1.json) for authoritative labels and output.
