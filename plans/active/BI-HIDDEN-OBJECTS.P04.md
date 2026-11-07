# P04 — Hidden object discovery, BetterInstincts

## LAUNCH ORDER

1. **GATE-0 — CI_OR_REMOTE_RUNNER.** Refresh `main`, branch, open PRs, checks, and repo status. Verify the pre-implementation consultation `contracts/consultations/BI-HIDDEN-OBJECTS-20261107.v1.json`. Run `python -m scripts.check_ontology --base-ref origin/main`, `python -m unittest tests.test_hidden_object_discovery -v`, full `unittest discover`, and doctrine/scene/horizon validators. Repair any failures in the scoped feature branch; do not overwrite unrelated work.
2. **HOST-0 — LOCAL_AGENT_RUNTIME (independent physical gate).** Read actual Windows game process, exact full patch, packs, current UI and save provenance. Collect separate visual and operator scene cues, verify `CONTENT_PRESENT` and the player's explicit disposable-lab consent. Do not reuse historical patch `1.121.361.1020` as fresh evidence.
3. **DISCOVER-1 — LOCAL_AGENT_RUNTIME.** First run `python -m scripts.hidden_object_discovery categories`; produce a real `dist/game-host/hidden-object-observation.json` then run `... plan --observation ... --category all`. The result is proposal-only. For actual UI input, separately admit each step with existing `screen_admit`/save policy/player-presence lease; use one console line per Enter, and stop on uncertainty/interrupt.
4. **CATALOG-1 — LOCAL_AGENT_RUNTIME.** Search `debug`, select only an observed DEBUG result, capture bounded actual item labels/price/pack/placement affordances; `review-entry` converts **one reviewed entry** into a price-classified receipt, not a global all-free claim. Respect pack availability. Never place multiple items blindly.
5. **BI002-1 — LOCAL_AGENT_RUNTIME (independent parent lane).** Continue the existing hunger real-game 5+5 trials and rollback as already required. Debug item discovery neither closes nor blocks hunger.
6. **CONVERGENCE — repo owner.** Preserve sanitized receipts, correct actual regressions and update existing `docs/LEDGER.md` and owning contract/host adapter after independent review. Keep private images/saves outside Git. Report CHANGED | PROVED | NEXT with the exact patch, PR/check state, number of uniquely observed objects, verified zero/nonzero/unknown prices, and separately evidenced placement.

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
