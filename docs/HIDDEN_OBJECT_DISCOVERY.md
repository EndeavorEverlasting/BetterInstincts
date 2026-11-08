# Hidden Object Discovery — general-purpose host capability

**Owner:** `contracts/hidden-object-discovery.v1.json` and `betterinstincts/hidden_object_discovery.py`. **Build:** offline, opt-in, no game input. **Preserves:** [Curious Catalog](CURIOUS_CATALOG.md) (rare seeds/alien fruit), [Scene Intelligence](SCENE_INTELLIGENCE.md), [Ontology](ONTOLOGY.md), existing BI-002 hunger proof.

## Player outcome

Help the operator **find** hidden, environmental and potentially free Build/Buy objects in The Sims 4: toothbrushes, dishes, collectibles, crystals, ponds, invisible lights, trees, streetlights and decorative cars. This is **catalog discovery**, not a promise that every named item exists or is free, placeable, usable, or installed on the current patch/packs. Do not blend it with `bb.ignoregameplayunlocksentitlement` (career unlocks), `bb.moveobjects` (placement), or a new money cheat. Those are separate, non-default capabilities.

This builds on the existing `curious_catalog` seam rather than replacing its gardening opportunity queue. General discovery is an operator-requested host service: no autorun on boot, no whim-triggered keystrokes, no game-speed changes, no consumption of the player queue. Return to the original Sim needs / income / skill goals when the user finishes.

## P04 compulsory recipe retrieval and local host evidence

A bare text handoff is insufficient. Every BetterInstincts P04 invocation must **discover** this workstream from `AGENTS.md` and fetch the exact active recipe through `python -m scripts.hidden_object_discovery guide` (works without game access). That command exposes all five numbered `operator_playbook.ordered_steps` in the sole typed contract: `OPEN_CHEAT_CONSOLE` → `ENABLE_CHEATS` → `REVEAL_HIDDEN_OBJECTS` → `ENTER_BUILD_BUY` → `SELECT_DEBUG_RESULTS`.

These preserve the operator's precise directions: `Ctrl+Shift+C` on PC/Mac (four triggers on consoles), top-left cheat box, `testingcheats true` + Enter, `bb.showhiddenobjects` + Enter, optionally `bb.showliveeditobjects` + Enter, console close, hammer-and-wrench or patch-verified `F2`, bottom-left search `debug`, click an **observed** `DEBUG` suggestion. Look for toothbrushes, dirty dishes, crystals, ponds, invisible lights and world props. Observe—not assume—confirmation toast, item availability, installed packs, usable state and each price.

After genuine host observations, the P04 lane must use `python -m scripts.hidden_object_discovery audit --observation dist/game-host/hidden-object-p04-receipt.json`. The audit requires exactly five ordered step receipts, a real `observation_ref` and independently gated `control_permit_ref` for each, the named UI gate, local player/save/scene facts and at least one reviewed catalog result. Missing/altered evidence returns `P04_EVIDENCE_INCOMPLETE`; structurally complete receipts return `P04_EVIDENCE_SHAPE_COMPLETE_PENDING_INDEPENDENT_REVIEW`, **never gameplay certification**. This is an evidence-shape audit only: real camera frames and human claims still require independent verification. The local game agent remains responsible for getting and inspecting those observations, not creating placeholder proof.

The repository CI checks `python -m scripts.check_hidden_object_p04` so removing this recipe, the P04 entrypoint or the machine dispatch breaks tests. The local host must not use the recipe to auto-enable cheats, touch speed, purchase, place or mutate protected saves. This lane is relevant when the user's parent objective involves hidden item discovery; otherwise it is inventoried and deferred, **not** an unrelated blocker.

## Sustained discovery — reusable four-hour agent goal

[Hidden Catalog Scout](HIDDEN_OBJECT_SCOUT.md) is the bounded local-agent work loop built *on top of this exact P04 setup*. It runs as explicit `start → next → record → status` checkpointed batches under `dist/`, not as a daemon or OpenAI scheduled task. Default timebox: 240 minutes; target: 40 **candidate** objects, reviewed §0 prices counted separately. After initial guide and receipt, each iteration requires fresh game/build/save/lease evidence, then rotates through five object classes. It never repeatedly types the initial cheat sequence or autonomously purchases/places objects. `python -m scripts.hidden_object_scout goal` exposes the typed mission.

## Deterministic path

The operator supplied this **requested workflow order** for the manual host:

1. Already loaded on the desired lot, with a specific authorized disposable lab save: console chord for the actual platform (Windows `Ctrl+Shift+C`; PlayStation four shoulder buttons; Xbox four shoulder buttons).
2. One line at a time: `testingcheats true`, Enter; `bb.showhiddenobjects`, Enter.
3. When **explicitly requested**, `bb.showliveeditobjects`, Enter; not default.
4. Close console; enter/confirm Build/Buy using observed, patch-appropriate chrome (do not blindly inject F1, F2 or F3).
5. Search `debug`; select a **visible** `DEBUG` suggestion, never assume a particular result.
6. Browse the bounded hints for clutter, collectibles, landscaping, world decor or lighting, optionally seek a named target. Reobserve catalog after switching filters and search.
7. Read actual price, pack availability, item name and placement affordances before reporting findings. Each placement is a separate user-authorized act, not part of discovery.

**Cheat distinction:** EA explicitly lists `bb.showhiddenobjects` as a Build cheat and states that Build-mode cheats generally do not require `testingcheats true`. The requested ritual includes `testingcheats true`; on PlayStation/Xbox, requiring it may disable trophies or achievements for that save. The planner therefore **requires specific console-risk acknowledgement** before even emitting a ready plan. Do not assert a success toast is mandatory for `bb.` commands. See [EA's cheat FAQ](https://www.ea.com/games/the-sims/the-sims-4/faq/cheats).

## CLI use by the Windows local agent

Start with the **current** `AGENTS.md`, `docs/ONTOLOGY.md`, the prior-to-mutation consultation, `docs/DOCTRINE.md`, `docs/LEDGER.md`, `docs/COMPATIBILITY.md`, `docs/SCENE_INTELLIGENCE.md`, `docs/LIVE_CERT.md`. Before any new local code mutation or sampling, run `scripts/semantic_preflight.py` using a new consultation specific to the operation; this sprint's receipt is **offline only**.

```sh
python -m unittest tests.test_hidden_object_discovery -v
python -m scripts.hidden_object_discovery categories
python -m scripts.hidden_object_discovery plan --observation dist/game-host/hidden-object-observation.json --category clutter --target toothbrush
python -m scripts.hidden_object_discovery plan --observation dist/game-host/hidden-object-observation.json --category world --target streetlight --live-edit
python -m scripts.hidden_object_discovery review-entry --observation dist/game-host/reviewed-object.json
```

The game-host adapter owns creating `dist/game-host/hidden-object-observation.json` **from real current host evidence**, not synthetic test fixtures:

```json
{
  "exact_game_build": "ACTUAL.FULL.VERSION.HERE",
  "platform": "windows",
  "scene_id": "build_buy",
  "visual_cue_ref": "capture:REVIEWED_ACTUAL_FRAME",
  "operator_cue_ref": "operator:SEPARATE_CURRENT_SCENE_CONFIRMATION",
  "capture_quality": "CONTENT_PRESENT",
  "viewport": "NORMAL",
  "save_attestation": "OPERATOR_ATTESTED_DISPOSABLE_LAB",
  "player_explicit_opt_in": true,
  "player_idle": true,
  "host_control_lease": "HOST_EXCLUSIVE",
  "game_paused": true
}
```

The version above is a **placeholder**, intentionally not a valid patch value; replace it only with live host evidence. For console support, also set `acknowledge_testingcheats_trophy_risk: true` after the operator acknowledges the consequences. Valid plans still contain `dispatch_authorized:false` and `manual_only:true` on every step. **Never** treat a plan as a control permit.

A reviewed per-item observation can be passed to `review-entry`:

```json
{
  "operator_reviewed": true,
  "result_visible": true,
  "capture_ref": "capture:ONE_CURRENT_ITEM",
  "item_label": "Actual catalog label",
  "price_simoleons": 0
}
```

That example demonstrates the **data shape**, not a claim that an item was observed. A zero price is certified only for the particular user-reviewed catalog listing on that version; if omitted, the result is `OBSERVED_PRICE_UNKNOWN`. Do not assert an exhaustive inventory or blanket "all items cost 0."

## Fail-closed host integration

`plan_discovery` returns `ABSTAIN` and no steps for unknown full patch, ambiguous/missing two-source scene, non-normal viewport, non-lab save, missing opt-in, active player, missing host exclusive lease, unpaused game, or console achievement warning not acknowledged. It does **not** identify the real game process or type a cheat. The next host adapter must:

- Verify game PID and exact build; check `game-scenes.v1.json` and the existing scene router; independently observe the real Build/Buy chrome **after** mode transition.
- Use existing protected-save guard and player-presence/control-permit system before *each* actual command, transition, search or click; halt on uncertainty, UI mismatch or interruption.
- Feed genuine bounded capture references and optional reviewed price results; write only sanitized receipts under ignored `dist/`.
- Avoid toggling cheats blindly when previous state is unknown. If a cheat already appears enabled, inspect and obtain operator direction before reissuing a potentially toggling command.
- Confirm no player queue edits, no speed change, no financial mutation and no save overwrite; verify rollback/cancel flow. The operator may place individual items only after explicit consent.

## Proof and ownership

**CURRENT_CHAT_RUNTIME / GitHub provider:** write bounded offline source/contracts/tests/P04 receipts. **CI_OR_REMOTE_RUNNER:** run focused/full tests and ontology chronology check against PR base. **LOCAL_AGENT_RUNTIME / Windows host:** current game screen and item findings, one-step-permit implementation and actual price/placement observations. **OPERATOR_OR_PHYSICAL_RUNTIME:** save/cheat/placement consent. **BI-002:** hunger gameplay certification remains separate and active.

The host-facing dispatch is [`BI-HIDDEN-OBJECTS.dispatch.v1.json`](../plans/active/BI-HIDDEN-OBJECTS.dispatch.v1.json); canonical local handoff is [`BI-HIDDEN-OBJECTS.P04.md`](../plans/active/BI-HIDDEN-OBJECTS.P04.md). No simulated evidence or offline test closes BI-002.
