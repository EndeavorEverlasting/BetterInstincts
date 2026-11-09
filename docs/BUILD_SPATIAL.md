# Build spatial axes — P95 program design

**Prompt:** TokenCorridor P95 — Program Design & Call-Stack Prototype Architect
**Machine owner:** [`contracts/build-spatial.v1.json`](../contracts/build-spatial.v1.json)
**Library / CLI:** `betterinstincts.build_spatial` / `python -m scripts.build_spatial`
**Depends on:** [`HOUSE_STATE.md`](HOUSE_STATE.md), [`BUILD_INTEGRITY.md`](BUILD_INTEGRITY.md)

## Axes

| Axis | Values | Meaning |
| --- | --- | --- |
| **Enclosure** | `INSIDE` / `OUTSIDE` / `UNKNOWN_ENCLOSURE` | Interior vs lot grass/patio/street. Lot grid ≠ inside. |
| **Story** | `FLOOR_1` / `FLOOR_2` / `UNKNOWN_STORY` | First floor vs second floor. Aliases: `1`/`GROUND`, `2`/`UPPER`. |

## Selected architecture: `ENCLOSURE_AND_STORY_AXES`

Host must classify before placing. Build order:

1. `FLOOR_1` structure (indoor floor tiles)
2. `FLOOR_1` indoor furniture / walls / kitchen / dining / sleep
3. `FLOOR_2` structure (only if F1 indoor floor exists)
4. `FLOOR_2` indoor furniture
5. `OUTSIDE` floater cleanup (never as indoor)

## Fail closed

- Outside-as-inside
- F2 before F1
- Indoor place with unknown enclosure or story
- Ignoring story when an entity attests `FLOOR_2`

## Host wiring

`host_stack.evaluate_turn(..., build_or_buy_mode=True, lot_model=...)` attaches `build_spatial.inventory` + `build_spatial.order` and elevates gate `BUILD_ORDER_FLOOR1_BEFORE_FLOOR2` when gaps remain.

Listener floor-activity (which story is active, single vs multi-floor, theme from attested items) lives in [`BUILD_FLOOR_ACTIVITY.md`](BUILD_FLOOR_ACTIVITY.md) — peer to this axis owner, not a competing spatial daemon.

## Proof ceiling

`OFFLINE_BUILD_SPATIAL_AXES_NOT_LIVE_LOT_RESTORE`
