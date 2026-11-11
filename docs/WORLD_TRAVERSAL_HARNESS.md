# World traversal — P00/P01 canonical ontology, doctrine and harness

**Parent objective:** Make Sims 4 in-world object recognition robust across highlight loss, occlusion, camera movement and off-lot drift; learn accurately from *observed* click results without competing with player input or a separate cursor agent. This is an enabling service for the original six-needs → balance → income → skills → careers product trajectory; **BI-002 hunger remains ACTIVE, not replaced or blocked by the vision lane**.

**Status:** Tracked P00/P01 source governance and P01 operational harness only. Local Cursor skill activation, screenshot sensor calibration, actual Sims clicks, game-mod installation and 5+5 BI-002 certification are **not** proved by this document or CI.

## Single machine authority and semantic glossary

- **Agent law:** `AGENTS.md` routes to mandatory `docs/AGENT_OPERATING_RULES.md`, `docs/DOCTRINE.md`, `docs/ONTOLOGY.md`.
- **Machine ontology:** `contracts/ontology.v1.json` revision 5, `BI-ONT-028..030`. `HIGHLIGHT_OBSERVATION` = two independent present/absent cues from a host capture; `WORLD_TARGET_TRACK` = capture/camera/target/bounds continuity; `WORLD_INTERACTION_ATTEMPT` = actual independently observed, player-uninterrupted before/after result. `GAME_OBJECT`, `VIEW_SCENE`, `OBSERVATION`, `OUTCOME`, `CONTROL_PERMIT` remain their existing owners.
- **World learning contract and pure implementation:** `contracts/world-traversal-learning.v1.json`, `betterinstincts/world_traversal_learning.py`. Two ordered distinct frames, two independent cues each, matching target+camera/capture and stable boxes. Two ABSENT cues may have `highlight_target_id=null`; two full absent frames yield `HIGHLIGHT_LOST`. PRESENT without identity, conflict, occlusion, one-frame flicker or moved camera cannot lock. Even LOCKED grants no host input. No duplicate clicks.
- **Post-click learner:** only real `GAME_EVENT` or operator-reviewed success/failure with `player_interrupted: false`, distinct before/after refs and observed result. Deduplicate by game-version + before-capture fingerprint across batches and holdout. Bound persistence to 2,048 accepted evidence IDs (existing config), reject counted legacy models lacking provenance; abstain on exhausted or unknown. Do not use household names or screenshot pixels in the model. Synthetic Brier scores are not actual precision or recall.
- **Input ownership:** `betterinstincts/host_stack.py` may revoke an unsafe world-click *candidate*; independent `screen_admit`, `lot_boundary`, `player_presence`, save/scene/exact-build and single-effect leases own execution. No local agent may change OS peripheral services/preferences/Print Screen, remap keys, press an unadmitted click or save a user's game.
- **P08 supporting priority:** `plans/horizon.v1.json#next_supporting_priority`, existing `plans/active/BI-HORIZON.dispatch.v1.json`, `plans/active/BI-WORLD-TRAVERSAL-CLOSERS-P04-20261110.md`, canonical Horizon execution-wide owner. PR #159's spatial-perception work is a separate active writer; do not overwrite it.

The *only* machine registry for this harness is `contracts/world-traversal-harness.v1.json`. This page, skill and ledger explain it rather than introducing alternate data owners.

## P01 codebase map

| Surface | Canonical owner | Responsibility |
| --- | --- | --- |
| Governance / ontology | `AGENTS.md`, `docs/AGENT_OPERATING_RULES.md`, `contracts/ontology.v1.json` | Enforce vocabulary, precedence, player first and proof classes |
| Recognition and learning | `contracts/world-traversal-learning.v1.json`, `betterinstincts/world_traversal_learning.py` | Pure classifier and bounded replay-safe advisory learning |
| Existing host composition | `betterinstincts/host_stack.py` | Opt-in `world_target.highlight_frames`, clear stale click candidate |
| Actual game input and protection | `betterinstincts/screen_admit.py`, `betterinstincts/lot_boundary.py`, `contracts/player-presence.v1.json`, `contracts/save-policy.v1.json` | Independent permission, off-lot, save, player, scene guards |
| Stage and dispatch | `plans/horizon.v1.json`, `plans/active/BI-HORIZON.dispatch.v1.json`, `scripts/horizon_status.py` | Supporting P08 priority, NOT BI-002 stage promotion |
| Validation | `scripts/check_world_traversal_harness.py`, `tests/test_world_traversal_harness.py`, `tests/test_world_traversal_learning.py`, `.github/workflows/ci.yml` | Presence, cross-owner invariants, negative semantic/routing and offline test proof |
| Path/install owners | `contracts/workstation-paths.v1.json`, `bootstrap.py` | Canonical dev checkout, separate managed use path, worktrees and runtime entrypoint |
| Agent skill | `.cursor/skills/world-traversal-p08/SKILL.md` | Scoped triggered workflow, not runtime click/adapter or auto-activation |

## P01 workflow / operator launch order

Use an **existing canonical checkout**, not a new guessed folder. Local agent starts read-only:

```sh
python -m scripts.horizon_status
python -m scripts.check_world_traversal_harness
python -m scripts.check_horizon
python -m unittest tests.test_world_traversal_harness tests.test_world_traversal_learning -v
python -m scripts.world_traversal_eval
```

**1. OFFLINE_PREFLIGHT** (`CURRENT_CHAT_RUNTIME` or `LOCAL_AGENT_RUNTIME`): fresh repository/main/PR/worktree inventory, ontology consultation before behavioral changes, codebase-map verification, existing synthetic fixture tests; use `python -m scripts.semantic_preflight` with the exact consultation and owned paths for code modification. A pass proves source/gates only.

**2. WORLD_SENSOR** (`LOCAL_AGENT_RUNTIME` game-capable host, explicit permission): exact game build, selected **operator-approved disposable** save, correct mode/lot, single screen lease and player idle/proof. Bounded *passive* source-qualified captures only (no focus borrowing), sufficient independent image/game cues, camera/viewpoint identity, visible object vs lost glow, occlusions, walls/gates, hydroponic-plant intersections and off-lot rejection. Confirm `HIGHLIGHT_LOST` leads to null click candidate after two ABSENT frames, no auto-reclick, and instant yield to human activity. Unknown/unavailable host → `BLOCKED_LOCAL_GAME_ACCESS`, not fabricated successful sensor readings.

**3. WORLD_OUTCOME** (same game screen, **serial after** sensor, new consent and permit): one reversible action only after the existing independent save, scene, target, lot, player and exact-build gates. Independently observe actual action queue/menu/object result; record failure and wrong-object cases, not just successful clicks. Test reacquisition after camera move and user takeover. Do not promote model confidence or synthetic holdout metrics into input authority.

**4. WORLD_INTEGRATE** (GitHub repo writer, after accepted private sanitized receipt and resolution of independent spatial perception PR #159): add the smallest tested sensor-to-`highlight_frames` adapter in an isolated PR, preserve single controller and old game patch profiles. Postmerge CI and local-game follow-up remain different proof dimensions.

The local Sims host is shared by BI-002 Hunger trials: there are **zero authorized concurrent mouse workers**, even if repository evaluation jobs can run in parallel. The P01 harness itself launches **no game agent** and creates no scheduler or watcher.

## Artifact inventory and privacy

| Artifact | Ownership / location | Evidence ceiling |
| --- | --- | --- |
| World traversal offline model, eval receipts | `dist/world-traversal-eval/*.json` ignored; only explicit CLI writes | Synthetic supplied frame/outcome labels |
| Sensor P08 receipt | `dist/game-host/<approved-run-id>/world-highlight-sensor-receipt.json` local/private, ignored | Actual measured visual cues, no click certification |
| Click outcome P08 receipt | `dist/game-host/<approved-run-id>/world-click-outcome-receipt.json` local/private, ignored | One independently verified permitted effect, not BI-002 |
| Public review / continuous truth | `docs/LEDGER.md`, source tests and PR/merge/CI identities only | Sanitized code proof, never raw user captures |
| Compatibility profiles / use paths | `contracts/workstation-paths.v1.json`, `docs/INSTALLATION_PROFILES.md` | Paths are rules; current Windows installation/use entrypoint NOT live-verified |

Never track screenshots, household/Sim names, user save payloads or local absolute profile paths; never overwrite model input snapshots or auto-scan user folders. Extra opted-in local metadata may be captured only with bounded retention and manual review.

## Harness triggers, hooks, failure handling, reports

**Trigger:** world-object highlight loss, camera target drift, object occlusion/selection, missed world clicks, postclick strategy learning, or P08. `SKILL.md` is locally discoverable by compatible Cursor harnesses after checkout but its activation in a particular installed local agent has not been observed. It is not a new input adapter. The **existing** `.cursor/hooks.json` / `.cursor/hooks/operator_boundary.py` guard remains a local-activation-dependent defense; never weaken/remove it, and never claim it controls unadopted external tools. P00/P01 does **not** install a new global hook, scheduled process or skill into a user profile.

On failure, classify **contract drift**, **untrusted/no cues**, **replay/holdout contamination**, **player takeover**, **off-lot/stale camera**, **game host unavailable**, or **shared-owner conflict**. Abstain before action, preserve target/intent for a fresh re-observation. If source-level regression: focused tests and consultation, isolate branch, PR and CI; if local P08 blocked: record exact missing gate and continue safe repo work. Never treat retries as extra independent successful evidence.

**Operator status:** `python -m scripts.horizon_status` reports current product gate, next supporting sensor priority, stage order and `BLOCKED_LOCAL_GAME_ACCESS_UNTIL_AUTHORIZED`. Complete report uses **CHANGED | PROVED | NEXT**, main SHA/PR vs checked branch, actual provider results, local game version and permission if witnessed. `scripts.check_world_traversal_harness` checks presence, source ownership, ontology semantics, safe runtime partition, artifact privacy and P01 map/skill routing; it does not run the game.

## P01 canonical paths and completeness gate

The **existing** `contracts/workstation-paths.v1.json` is authoritative: Windows and Linux each have one development checkout, a distinct installed *use* path, bounded worktree parent and explicit entrypoint. `bootstrap.py` owns install/uninstall; no alternative paths, silent second clone or global PATH/registry modification. Local runtime readback of these paths and skill activation remains **NOT_VERIFIED**.

Run `python -m scripts.check_world_traversal_harness`, and then `python -m unittest tests.test_world_traversal_harness -v`. CI also enforces the entire suite, Horizon validator, original ontology chronology/semantic consultation, camera/scene and independent peripheral safety gates. Passing these checks proves **repository harness installation**, not configured Cursor local activation, a working screenshot detector, actual Sims clicks, or BI-002 hunger certification.
