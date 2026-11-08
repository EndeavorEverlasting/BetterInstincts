# Build/Buy integrity — P95 program design

**Prompt:** TokenCorridor P95 — Program Design & Call-Stack Prototype Architect
**Provenance:** `spec-architecture-prompts.v1.json` (see `docs/PROMPT_INVOCATIONS.md`)
**Machine owner:** [`contracts/build-integrity.v1.json`](../contracts/build-integrity.v1.json)
**Library:** `betterinstincts.build_integrity`
**Upstream model:** [`HOUSE_STATE.md`](HOUSE_STATE.md) (`RECURSIVE_LOT_MODEL`)

## Motivating failure

Bargain Bend Build/Buy thrash treated **lot grass as indoor floor**, nested objects inside each other, and deleted **floor, walls, kitchen aesthetic, dining table, and futuristic sleep pod**. Cleanup-by-sweep is not building.

## Selected architecture: `STRUCTURE_FIRST_SPATIAL_ADMISSION`

| Candidate | Verdict |
| --- | --- |
| Coordinate click thrash | **Rejected** |
| Lot-grid == indoor | **Rejected** |
| Inventory sweep as cleanup | **Rejected** |
| Aesthetic optional | **Rejected** |
| Structure-first spatial admission over recursive lot model | **Selected** |

## Rules (fail closed)

1. **Indoor ≠ outdoor.** `INDOOR_FLOOR_REQUIRED` objects cannot place on `OUTDOOR_LOT` / grass.
2. **Floor before furniture.** No bed, sleep pod, dining set, or appliances until an attested `FLOOR_TILE` with `domain=INDOOR_FLOOR` and `status=PRESENT|PARTIAL` exists in the model.
3. **No nesting.** `nest_risk=true` → deny.
4. **Protected zones.** Kitchen / bedroom / dining / bath furniture cannot be sledge/inventoried without a `RESTORE_*` goal (+ Save As for structure).
5. **Restore order.** Floor → walls → kitchen → dining → sleep pod.

## Call stack

```
lot model observe(domains, zones, entities)
  -> build_library_checkpoint (My Library save before room/structure mutate)
  -> build_integrity.evaluate_integrity(...)
  -> house_state.admit_mutation (denied unless LIBRARY_ADMIT + INTEGRITY_ADMIT)
  -> optional live adapter
  -> observe outcome into SAME model
```

See also [`BUILD_LIBRARY_CHECKPOINT.md`](BUILD_LIBRARY_CHECKPOINT.md).

## Proof ceiling

`OFFLINE_BUILD_INTEGRITY_ADMISSION_NOT_LIVE_LOT_RESTORE`

Does not by itself rebuild Bargain Bend in Live/Build Mode. It blocks the mechanisms that wrecked it.
