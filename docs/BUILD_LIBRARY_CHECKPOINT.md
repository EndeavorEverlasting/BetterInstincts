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

## 2026-11-09 correction — whole home and purchase coverage

A prior agent reportedly removed the entire second floor. The earlier guard protected only structural/room edits and exempted `BACKSPACE_TO_INVENTORY`; it did not prove the full household layout was saved before purchases or object placement. This is a safety-critical gap.

**Required order (no optional skips):** inventory and observe the entire lot across every story and room, including outdoor areas; classify room structure, enclosure, functional and style labels; collect per-floor and per-room captures and explicitly attest the full floor roster; save the *pre-change* whole building in Sims **My Library** and observe the resulting item; bind an attestation with a `lot_manifest`; persist and read back the exact revisioned `house_state` model; only then evaluate one purchase/mutation through `admit_mutation` with a matching current revision. Catalog, placement, inventory and structural actions all go through the same gate. After any subsequent observation or mutation outcome, the previous checkpoint is stale, and a fresh one is required. Unknown coverage, missing classification, stale metadata and a capture reference without actual Library verification deny the action.

The `lot_manifest` shape: `operator_confirmed: true`, `all_stories_inspected: true`, exact `lot_id` and `model_revision`; `floors` keyed by all stories, each containing its exact `rooms` and a model-tracked `capture_ref`; `rooms` keyed by the same IDs produced by `room_census`, each with model-tracked `capture_ref`, valid nonempty `function_labels` and `style_labels`. No extra, omitted, unknown or unverified room claims are permitted. This is an operator-attested completeness claim, not a synthetic claim that computer vision independently discovered unseen rooms. The gate also requires a successful repository-local metadata checkpoint readback; that metadata is **not** a game save.

**Scope and proof:** The offline decision system cannot recover the deleted floor or intercept third-party mouse input on its own. Real host writers (including Cursor/Playwright) must be wired to require a *fresh runtime-verified* lot lease before Build/Buy input; a library attestation is not a live game-input permit. No game saves were touched by these code changes. Recovery must first inspect existing saves/Library and preserve the last known good state, never save over wreckage.
