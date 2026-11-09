# House / lot environment model — P95 program design

**Prompt:** TokenCorridor P95 — Program Design & Call-Stack Prototype Architect
**Provenance:** `spec-architecture-prompts.v1.json` (see `docs/PROMPT_INVOCATIONS.md`)
**Machine owner:** [`contracts/house-state.v1.json`](../contracts/house-state.v1.json)
**Library / CLI:** `betterinstincts.house_state` / `python -m scripts.house_state`

## Design brief

- **Subject:** Build/Buy work on a disposable lab lot (e.g. Bargain Bend).
- **Job:** Maintain one durable, revisioned **lot environment model** that accumulates what we know as we look and move. Plan the next action from that model. Persist checkpoints as **continuity of the same understanding**, plus optional Save As for recovery.
- **Not:** Wipe knowledge after each action, extract a checkpoint from scratch, and reassess the lot as if it were unknown. That blank-slate loop destroyed usable layout while chasing floaters.

## Selected architecture: `RECURSIVE_LOT_MODEL`

| Candidate | Verdict |
| --- | --- |
| Blank-slate checkpoint loop (act → discard → recapture → reassess) | **Rejected** — thrash + layout destruction |
| Checkpoint photos only, no structured model | **Rejected** — recovery crumbs without compounding agency |
| Invent full object graph from pixels | **Rejected** — false precision |
| Recursive lot model + targeted mutations + optional Save As | **Selected** |

## Success call stack

```
load_or_create(run_id, lot_id)          # same durable model
  -> observe(claims)                    # merge; bump revision; never wipe entities
  -> plan_next(model)                   # one action grounded in entities/goals
  -> admit_mutation(revision, action, targets)
  -> (live adapter optional; execute_allowed stays false offline)
  -> observe(outcome_delta)             # recursive update of SAME model
  -> persist_checkpoint(model)          # continuity receipt, not a new blank world
```

Forbidden loop: `act → discard_model → capture_from_scratch → reassess_as_if_unknown → repeat`.

## Mutation rules

- Non-mutating camera/UI/catalog browse: allowed without a lease.
- Mutating actions need a model revision > 0 with entities and explicit targets where applicable.
- **`build_spatial` classifies INSIDE/OUTSIDE and FLOOR_1/FLOOR_2** — see [`BUILD_SPATIAL.md`](BUILD_SPATIAL.md). Host plans F1 before F2.
- **`build_library_checkpoint` must `LIBRARY_ADMIT` before room/structure leases** — see [`BUILD_LIBRARY_CHECKPOINT.md`](BUILD_LIBRARY_CHECKPOINT.md). Save the building to My Library before sledge/walls/room tools; game Save As is not a substitute.
- **`build_integrity` must `INTEGRITY_ADMIT` before any lease** — see [`BUILD_INTEGRITY.md`](BUILD_INTEGRITY.md). Outdoor grass is never indoor floor; nesting denied; floor/walls/kitchen protected.
- `BULK_INVENTORY_SWEEP` is always denied — clear floaters only as named `FLOATER` entities via `BACKSPACE_TO_INVENTORY`.
- Destructive bulk rearrange / sledge / move-house require operator-attested lab `Save As` (`BI_TMP_` / `BI_CONT_`) on the model.
- Plan order is **structure-first** (floor → walls → kitchen → dining → sleep pod) before furniture or floater cleanup.
- After any admitted mutation, the next required step is **observe outcome into the same model**, not a fresh reassessment.

## Operator recovery (Bargain Bend wreckage)

1. If a known-good save exists: **Load** it. Do **not** Save the wrecked session over that slot.
2. If you want a forensic copy of wreckage: **Save As** under a distinct `BI_TMP_…` name, then load the good save (or restart the lab lot).
3. After load: seed a **new** model revision from the restored lot — the wreckage model is not authoritative.

```bash
python -m scripts.house_state recovery --has-known-good-save
python -m scripts.house_state init --run-id bi-bargain-1 --lot-id "Bargain Bend"
python -m scripts.house_state observe --run-id bi-bargain-1 --lot-id "Bargain Bend" \
  --entities-json '{"table.1":{"kind":"DINING_TABLE","confidence":"LOCAL_OBSERVED"},"chair.slot6":{"kind":"DINING_CHAIR","confidence":"LOCAL_OBSERVED","status":"MISSING"}}' \
  --goal SEAT_SIXTH_CHAIR --capture lot_wide3
python -m scripts.house_state plan --run-id bi-bargain-1 --lot-id "Bargain Bend"
python -m scripts.house_state admit --run-id bi-bargain-1 --lot-id "Bargain Bend" \
  --action PLACE_FROM_CATALOG --target chair.slot6
python -m scripts.house_state checkpoint --run-id bi-bargain-1 --lot-id "Bargain Bend" --label pre-place
```

## Proof ceiling

`OFFLINE_RECURSIVE_LOT_MODEL_NOT_EA_SAVE_API_NOT_LOT_RESTORE_PROOF`

This does **not** close BI-002, restore Bargain Bend by itself, or prove live Save As / Load.
