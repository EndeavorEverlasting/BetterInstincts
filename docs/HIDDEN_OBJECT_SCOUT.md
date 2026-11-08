# Hidden Catalog Scout — sustained four-hour local-agent mission

**Canonical contract:** `contracts/hidden-object-scout-goal.v1.json`
**Implementation:** `betterinstincts/hidden_object_scout.py`
**CLI:** `python -m scripts.hidden_object_scout`
**Transport:** `plans/active/BI-HIDDEN-OBJECTS.P04.md` and its typed dispatch.

## Mission

After a real P04 unlock/search and approved local host attachment, spend **up to four hours** gradually finding, inspecting, and categorizing unusual objects in The Sims 4's hidden Build/Buy catalog. This is a repeatable **agent work goal**, not a Sim motive, need, unbounded optimization loop or background process. The user wants to discover toothbrushes, dirty dishes, crystals, invisible lights, ponds, cars, large trees, streetlights and other surprises.

Aim to gather **40 distinct candidate objects** across five rotating shelf families: **clutter → collectibles → landscaping → lighting → world**. Each item's label, pack and capture identifier are tracked. When a player actually reviews a listing, classify price as exactly §0, nonzero or unknown. **40 is a target, not a claim that 40 objects are obtainable.** The mission may continue after reaching the target while safe and inside its timebox, or stop sooner if the catalog is exhausted or the operator takes over.

## Three distinct activities

1. **Initial P04 setup:** One time per independently verified game/lot context. Read `python -m scripts.hidden_object_discovery guide`; follow the exact five ordered steps *with observed UI and valid permits*. Capture `dist/game-host/hidden-object-p04-receipt.json` and audit it using the existing `python -m scripts.hidden_object_discovery audit --observation ...`. That P04 receipt must include `save_ref` as an opaque local lab-save identity. **Never blindly retype a possibly toggling cheat on every batch.** A consented optional live-edit command requires its own observed receipt.
2. **Repeatable local agent catalog batches:** Keep gameplay paused, player idle and the exclusive UI lease valid. Before **every** batch, obtain a fresh current Build/Buy observation with exact patch, independent visual/operator cues, a matching `save_ref`, normal viewport and a capture timestamp at most 180 seconds old. Run `next` and let the existing local game agent carry out the proposed search *only after each new screen-admit permit*. Observe up to 12 results; never blindly click, purchase, place, force scene/speed, or consume a player action queue. Record one bounded report under ignored `dist/`, then `record` checkpoint.
3. **Evidence and review:** Candidates from agent observation may be **pending review** indefinitely; an unreviewed item's price must be absent/unknown. Reviewed per-item listings can become `reviewed_free`, `reviewed_priced`, or `reviewed_price_unknown`. The module stores structured receipts, not screenshots. Do not infer "most objects free" from the catalog class.

## CLI — used by the existing Windows local agent

```sh
# Always inspect scope and initial P04 guide first
python -m scripts.hidden_object_scout goal
python -m scripts.hidden_object_discovery guide

# Create a new four-hour checkpoint, without starting the Sims game or any daemon
python -m scripts.hidden_object_scout start --session-id catalog-lab-01 --minutes 240 --target 40

# Current real host facts must be captured separately under ignored dist/game-host/
python -m scripts.hidden_object_scout next --session-id catalog-lab-01 \
  --observation dist/game-host/current-build-buy.json \
  --p04-receipt dist/game-host/hidden-object-p04-receipt.json

# The existing host agent performs only the individually admitted UI steps,
# then records the just-observed bounded batch in dist/game-host/catalog-batch.json
python -m scripts.hidden_object_scout record --session-id catalog-lab-01 \
  --observation dist/game-host/current-build-buy.json \
  --p04-receipt dist/game-host/hidden-object-p04-receipt.json \
  --report dist/game-host/catalog-batch.json

python -m scripts.hidden_object_scout status --session-id catalog-lab-01
python -m scripts.hidden_object_scout pause --session-id catalog-lab-01
python -m scripts.hidden_object_scout resume --session-id catalog-lab-01
python -m scripts.hidden_object_scout stop --session-id catalog-lab-01
```

`next` is **idempotent** until the matching `record` succeeds. A safe local agent can call it again after interruptions, including after process restarts. It rotates categories and specific search hints with each completed batch. A duplicate batch report with the same digest is a harmless no-op; conflicting retries fail. Checkpoints live at `dist/hidden-object-scout/<session-id>/state.json`, bounded to 512 KB; they are not committed or published.

### Batch receipt schema (shape only, NOT a fabricated live observation)

```json
{
  "batch_id": "catalog-lab-01-B001",
  "category": "clutter",
  "search_term": "debug",
  "search_capture_ref": "capture:real-search-001",
  "result_state": "ITEMS_CAPTURED",
  "items": [
    {
      "item_label": "Actual observed listing name",
      "pack_name": "Actual pack or UNKNOWN",
      "capture_ref": "capture:real-item-001",
      "result_visible": true,
      "operator_reviewed": false
    }
  ]
}
```

If the actual search returns no result, set `result_state: NO_MATCH` with an empty `items` array and an actual search capture. Do not put `price_simoleons` into an unreviewed row. For a genuinely operator-reviewed listing, set `operator_reviewed:true` and optionally `price_simoleons` to a nonnegative integer. The first P04 setup receipt must be independently reviewed as already required; subsequent agent discoveries can accumulate for later operator review. This allows hours of productive candidate collection without representing autonomous image interpretation as human verification.

## Work loop and hard stops

The local Windows agent **owns** the outer repeated work cycle; there is intentionally no fake resident process, OpenAI recurring task, timer-based spam loop, or startup autorun:

```text
START → real P04 setup receipt → fresh Build/Buy + patch/save/lease
       → NEXT (category + search hint; manual-only)
       → independent per-action screen_admit / local UI action
       → capture bounded real results
       → RECORD (atomic checkpoint + metrics)
       → wait for safe next batch / re-observe
       ↻ while timebox ACTIVE and game/host safe
       → stop on timeout (4h default), 96 batches, or 12 consecutive no-new-result batches
```

A minimum 15-second gap between recorded batches prevents a busy-wait. The owner can pause or stop immediately on operator input; a pause freezes the remaining time budget. If game build, save identity, scene, lease, consent, capture freshness or P04 receipt changes, `next` returns `ABSTAIN` and produces no search. Do not silently transition into a new game, load a protected save, repeat cheats or continue after a crash. Review and reacquire the exact authority before resuming.

**Proof dimensions stay separate:** candidate count, reviewed count, genuinely verified free/priced/unknown counts, category coverage, total batches, time remaining and actual local host captures. Offline unit tests/CI validate planning and checkpoint correctness; they do not prove a four-hour game run. BI-002 hunger trials remain the parent game-autonomy milestone and cannot share the same UI lease concurrently. The scout is an independent optional exploratory lane.

## Local run acceptance

A local agent earns **WORK_RUNNING** only with an actual attached Sims process, current exact build, authorized disposable lab save, P04 guide/receipt, live Build/Buy scene cues and current exclusive host lease; timeboxed loops must produce real per-batch receipts. A structural `BATCH_CHECKPOINTED_NOT_GAME_CERTIFIED` reply is not an item discovery without actual capture review. **MISSION_COMPLETED** requires a clear termination reason plus final coverage metrics and genuine observed captures, not merely 240 minutes of process idling.

For repo-only testing:

```sh
python -m unittest tests.test_hidden_object_scout -v
python -m unittest discover -s tests -v
python -m scripts.check_hidden_object_p04
python -m scripts.check_ontology --base-ref origin/main
```
