# Build library checkpoint — P95 program design

**Prompt:** TokenCorridor P95 — Program Design & Call-Stack Prototype Architect
**Provenance:** `spec-architecture-prompts.v1.json` (see `docs/PROMPT_INVOCATIONS.md`)
**Machine owner:** [`contracts/build-library-checkpoint.v1.json`](../contracts/build-library-checkpoint.v1.json)
**Library / CLI:** `betterinstincts.build_library_checkpoint` / `python -m scripts.build_library_checkpoint`
**Upstream model:** [`HOUSE_STATE.md`](HOUSE_STATE.md)

## Motivating failure

An agent deleted the walls of the house in Build/Buy without first saving the
building into **My Library**. There was no revertible building blueprint — only
human judgment intervening after the damage. Chat reminders do not bind the host.

## Selected architecture: `LIBRARY_SAVE_BEFORE_ROOM_MUTATE`

| Candidate | Verdict |
| --- | --- |
| Game Save As only | **Rejected** — session recovery ≠ building blueprint; does not satisfy this gate |
| Agent courtesy prompt | **Rejected** — not enforceable across callers |
| Save to Library after mutation | **Rejected** — preserves wreckage, not judgment |
| Library save before room/structure mutate | **Selected** |

## Rules (fail closed)

1. Before `SLEDGE`, `WALL_ROOM_TOOL`, `MOVE_HOUSE_OR_ROOM`, `MULTI_OBJECT_REARRANGE`, or any mutation targeting wall/floor/room structure: require a fresh `library_checkpoint` on the lot model.
2. Fresh means `library_checkpoint.model_revision ==` current model revision, matching `building_id`.
3. `SAVE_TO_LIBRARY` is the only mutation that creates the checkpoint; it does not require a prior one.
4. Game Save As (`BI_TMP_` / `BI_CONT_`) remains a separate destructive gate and **never** counts as a library checkpoint.
5. Outdoor floater inventory alone is not a room mutation.

## Call stack

```
lot model observe
  -> plan_next / host_stack: if restore pending without library -> SAVE_TO_LIBRARY
  -> attest_library_save(building_id, library_item_name, capture_ref)
  -> admit_mutation: LIBRARY_ADMIT then Save As / spatial / integrity
  -> optional live adapter
  -> observe outcome (invalidates library checkpoint until re-saved)
```

## Proof ceiling

`OFFLINE_LIBRARY_SAVE_ADMISSION_NOT_LIVE_GALLERY_WRITE`

Does not write EA Documents or Gallery from offline code. Live Save-to-My-Library
UI remains a separate adapter under screen admission.
