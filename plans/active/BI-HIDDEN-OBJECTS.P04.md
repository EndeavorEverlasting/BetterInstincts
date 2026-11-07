# P04 — Hidden object discovery, BetterInstincts

## LAUNCH ORDER

1. **GATE-0 — CI_OR_REMOTE_RUNNER.** Refresh `main`, branch, open PRs, checks, and repo status. Verify the pre-implementation consultation `contracts/consultations/BI-HIDDEN-OBJECTS-20261107.v1.json`. Run `python -m scripts.check_ontology --base-ref origin/main`, `python -m unittest tests.test_hidden_object_discovery -v`, full `unittest discover`, and doctrine/scene/horizon validators. Repair any failures in the scoped feature branch; do not overwrite unrelated work.
2. **HOST-0 — LOCAL_AGENT_RUNTIME (independent physical gate).** Read actual Windows game process, exact full patch, packs, current UI and save provenance. Collect separate visual and operator scene cues, verify `CONTENT_PRESENT` and the player's explicit disposable-lab consent. Do not reuse historical patch `1.121.361.1020` as fresh evidence.
3. **DISCOVER-1 — LOCAL_AGENT_RUNTIME.** FIRST run `python -m scripts.hidden_object_discovery guide` and read back all five operator steps; then run `python -m scripts.hidden_object_discovery categories`; produce a real `dist/game-host/hidden-object-observation.json` then run `... plan --observation ... --category all`. The result is proposal-only. For actual UI input, separately admit each step with existing `screen_admit`/save policy/player-presence lease; use one console line per Enter, and stop on uncertainty/interrupt.
4. **CATALOG-1 — LOCAL_AGENT_RUNTIME.** Follow the exact ordered recipe below. Search `debug`, select only an observed DEBUG result, capture bounded actual item labels/price/pack/placement affordances; `review-entry` converts **one reviewed entry** into a price-classified receipt, not a global all-free claim. Respect pack availability. Never place multiple items blindly.
5. **RECEIPT-1 — LOCAL_AGENT_RUNTIME.** Collect separate evidence for each required operator step and reviewed catalog listing, then run `python -m scripts.hidden_object_discovery audit --observation dist/game-host/hidden-object-p04-receipt.json`; no live or free-item claim follows from structural success alone. **BI002-1** remains an independent local-host parent lane. Continue the existing hunger real-game 5+5 trials and rollback as already required. Debug item discovery neither closes nor blocks hunger.
6. **CONVERGENCE — repo owner.** Preserve sanitized receipts, correct actual regressions and update existing `docs/LEDGER.md` and owning contract/host adapter after independent review. Keep private images/saves outside Git. Report CHANGED | PROVED | NEXT with the exact patch, PR/check state, number of uniquely observed objects, verified zero/nonzero/unknown prices, and separately evidenced placement.


## P04 MUST-READ: exact operator playbook and evidence checklist

**Mandatory on any BetterInstincts `invoke P04`:** Run `python -m scripts.hidden_object_discovery guide`, which returns the complete, machine-owned instructions and platform chords from `contracts/hidden-object-discovery.v1.json`. Treat this as an ingest/read gate, not a game-action permit. Check that all five IDs are present and ordered. If the P04 parent objective is unrelated to hidden items, retain this as a deferred lane, do not divert UI work.

1. **`OPEN_CHEAT_CONSOLE` — while loaded onto a Sim's lot.** PC/Mac: press `Ctrl+Shift+C` together; PlayStation: `L1+R1+L2+R2`; Xbox: `LB+RB+LT+RT`. Observe the thin white cheat text bar near the **upper-left** of the game screen, allowing for patch/layout differences. Capture `OBSERVE_CONSOLE_VISIBLE` evidence.
2. **`ENABLE_CHEATS` — one command.** Focus the cheat console, type exactly `testingcheats true`, press **Enter**. Look for a confirmation such as **“Cheats are enabled”**, but do not fabricate one if the UI differs. Capture the actual response as `REVIEW_TESTINGCHEATS_RESPONSE`.
3. **`REVEAL_HIDDEN_OBJECTS` — one command per Enter.** Focus console, type `bb.showhiddenobjects`, press **Enter**. Only with a separate explicit opt-in, optionally type `bb.showliveeditobjects` and press **Enter** (environmental cars, big trees, streetlights, etc.). Close the console using the same platform chord. Capture actual command responses/console closure under `REVIEW_HIDDEN_AND_OPTIONAL_LIVE_EDIT_RESPONSE`. Never type `buydebug` or slash-join commands.
4. **`ENTER_BUILD_BUY` — observed scene transition.** Use the visible **hammer-and-wrench icon near the top-right**, or the keyboard `F2` Build/Buy shortcut if calibrated on the current game build. Verify genuine Build/Buy chrome and catalog (`OBSERVE_BUILD_BUY_MODE`); never infer it from a black viewport or a mode-change keystroke alone.
5. **`SELECT_DEBUG_RESULTS` — discover and inspect.** In Build/Buy, use the **bottom-left search bar above the house illustration** when present; type `debug`. Look for one or more visually confirmed **DEBUG** suggestions, select one that is actually visible, and verify the resulting catalog (`OBSERVE_DEBUG_SUGGESTIONS_AND_CATALOG`). Browse clutter (toothbrushes, dirty dishes), crystals/collectibles, ponds/landscape objects, invisible lighting, and optional live-edit world decor (cars/trees/streetlights). Observe each listing's actual name, installed-pack context, price and usable/placement affordance.

**User's requested sequence is preserved.** EA notes that `testingcheats true` is not inherently required for the Build-mode hidden-object cheat; on PlayStation/Xbox, enabling testing cheats can disable achievements/trophies for the current save. Confirm this risk before running that command. A screen toast may vary, and not every hidden item is available, functional, placeable or free. **“Vast majority cost §0” is a hypothesis, not an accepted measured count.** Only record `free: true` when the individual's observed catalog price is exactly §0. Source: [EA's official Sims 4 cheat FAQ](https://www.ea.com/games/the-sims/the-sims-4/faq/cheats).

**Machine check:** the local agent must report the exact 5 `step_id` values in order, each with a distinct `observation_ref`, matching `observed_gate`, `control_permit_ref`, and `outcome: OBSERVED`. The receipt also needs actual exact build, player opt-in/idle, disposable lab-save attestation, independent visual/operator scene cue references, exclusive host lease, paused state, normal viewport and unchanged speed/queue. Optional live-edit requires its own outcome receipt. At least one individual catalog result must include a visible label, capture reference, and operator review; price may remain unknown.

Record sanitized receipts under `dist/game-host/hidden-object-p04-receipt.json`; then run:

```sh
python -m scripts.hidden_object_discovery guide
python -m scripts.hidden_object_discovery plan --observation dist/game-host/hidden-object-observation.json --category all
python -m scripts.hidden_object_discovery audit --observation dist/game-host/hidden-object-p04-receipt.json
python -m scripts.check_hidden_object_p04
```

The `audit` result `P04_EVIDENCE_INCOMPLETE` is a hard incomplete gate. Even `P04_EVIDENCE_SHAPE_COMPLETE_PENDING_INDEPENDENT_REVIEW` is **not independent proof that an input occurred** or proof of live game certification. If no live game is attached, retrieve the guide and report `AWAITING_LOCAL_GAME_HOST` without inventing a completed receipt.

## Repo, authority and source

- Repository: `EndeavorEverlasting/BetterInstincts`, feature branch `feat/bi-hidden-object-host-p04-20261107`. Remote main must be refreshed; never reset another agent's work.
- Parent: player-first Sims autonomy and **BI-002** live needs game certification remain active.
- P04 exact owner: Moonwake `harness/exports/prompt-invocation-catalog.v1.json`, **[PARALLEL] Repo-Aware Sprint + Harness Factoring Distributor**; read current `AGENTS.md`, `docs/ONTOLOGY.md`, `docs/SCENE_INTELLIGENCE.md`, `docs/CURIOUS_CATALOG.md`, `docs/HIDDEN_OBJECT_DISCOVERY.md`.
- Typed owner: `contracts/hidden-object-discovery.v1.json`. Existing garden-specific Curious Catalog is preserved, not overwritten.
- Mandatory gate: semantic consultation predated implementation commit. A previous offline consultation is *not* a game-sampling permission. New live work needs an exact-build consultation + `scripts/semantic_preflight.py --operation game_sampling --exact-game-build ACTUAL_VERSION` and separate screen/lease/save admission.

## Dependency graph and lane ownership

```text
Consulted ontology (committed)
          |
Source/contract + offline tests
          |
  +-------+-------------------+
  |                           |
CI tests + chronology     Host evidence + exact patch
  |                           |
  |                       Player consent + scene lease
  |                           |
  |                       Guided debug / live-edit discovery
  |                           |
  |                       Reviewed individual prices
  +-------------+-------------+
                |
           Reviewed convergence

BI-002 hunger live certification — parallel independent parent lane
```

**Collision contract:** CI owns no game UI; the Windows host owns no canonical prompt registry, provider Git writes or unrelated source; one Git writer per branch/worktree; operator alone attests save/cheat consent; both GUI discovery and BI-002 hunger trials require exclusive UI ownership and therefore **may not operate concurrently on the same game process**. Different host/CI lanes may run independently.

**Factoring:** Existing game scene/save guards own scene admission; existing Curious Catalog owns gardening prompts and session state; the new discovery module owns generic read-only classification and command proposals; future screenshot control adapter belongs to the Windows local host. Do not create a second scene classifier, save authority, or HUD controller.

**Machine dispatch:** [BI-HIDDEN-OBJECTS.dispatch.v1.json](BI-HIDDEN-OBJECTS.dispatch.v1.json). The typed plan is **not** a Moonwake `prompt_parallel_dispatch.py` receipt or launched sub-agent. If the Moonwake validator/adapter is unavailable to the checkout, record `AUTONOMY_GAP` and continue safe repo/provider work; do not call serial commits parallel dispatch.

## Acceptance and failure route

Offline gate: contract consistent, all negative tests pass, chronology shows consultation precedes behavior writes, no accidental gameplay/PID/SendInput. Remote CI should be read back after PR. Live gate: actual version/packs, genuine two-source current scene, operator lab consent, stable Build/Buy, each cheat/search step observed, zero queue interference, no unsanctioned speed/change/purchase, item-by-item price proof and safe exit. If screen black/unknown or player interacting: `ABSTAIN`, preserve current player intention, do no input.

**Proof ceiling:** current ChatGPT/provider work can reach Git commits + CI; it cannot claim live Windows input, discovered item counts, free-item evidence, installed game version, or BI-002 closure. Keep original validated behavior intact. No operator copy/paste is required to build the software; the local runner consumes this machine dispatch when available.
