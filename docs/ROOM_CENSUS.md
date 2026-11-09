# Whole-house room census — multi-label, read-only

**Owner:** `betterinstincts/room_census.py` and `contracts/room-census.v1.json`. Projection of the existing revisioned `house_state` model, not a second world model or an always-on scanner.

## What the app can classify

For **every story actually represented in supplied observations** (including `FLOOR_3` and `BASEMENT_1`), it groups known `ROOM_ZONE` entities and object claims by `story + zone`. Each group returns an indoor/outdoor/unknown enclosure, inventory with evidence, multiple **functional labels** (kitchen, dining, living, office, garden, etc.), and multiple independent **style labels** (rustic, modern, industrial, bohemian, etc.). No single winning label erases other supported roles. Each label has an item-evidence count, not a fabricated probability.

A `ROOM_ZONE` observation creates `STRUCTURE_ATTESTED` evidence; grouping items with the same attested zone but no verified room boundary creates only `ZONE_CANDIDATE`. If the source disagrees on enclosure, the output is `UNKNOWN_ENCLOSURE` with a conflict flag. Without attested story or zone, items remain in `unassigned_items`. These are important distinctions: object co-location is not wall-boundary detection, and a viewport image alone is not a room scan.

Styles are derived **only** from explicit per-object `style_tags` in the lot model, never from a product name or category. `function_tags` can supplement canonical kind/category mappings. Both are plural by design and never authorize actions. Indoor/outdoor, object occupancy and building integrity remain governed by the existing `build_spatial` / `build_integrity` components.

## Observation call stack

```
opt-in local host with observed room/floor/object data
  -> house_state.observe (revisioned, merge-not-replace)
  -> room_census.scan_lot_model (pure, bounded read-only projection)
  -> build_floor_activity.evaluate_floor_activity (optional Build/Buy attachment)
  -> host_listener.tick (optional advisory receipt; no SendInput)
```

Input is an existing `house_state` model with `ROOM_ZONE` and object entities using `story`, `zone`, `enclosure`/`domain`, `kind`, optional `category`, and optional `style_tags`/`function_tags`. Story aliases for the first two floors use `build_spatial`; attested higher floors/basements are accepted, not auto-discovered. The scan never claims that all actual game floors were visited until independently proven by a host coverage sensor.

```bash
python -m scripts.room_census taxonomy
python -m scripts.room_census evaluate --model dist/house-state/<run_id>/<lot>.model.json
```

The local game host still needs **P08 exact-game-build certification** for observing story changes, room boundaries, inside/outside geometry, floor enumeration, and object/style metadata. In the interim these are operator/sensor-attested inputs, not autonomously captured Sims 4 state. This offline feature does not close BI-002.

**Moonwake routing:** P95 designs the seam; P124 factors it into existing house-state/floor-listener owners; Trifecta P82/P07 covers deterministic tests and integration, P08 remains game-only. **P178 was absent from the current P00–P143 exported catalog** and is not assigned a guessed definition.
