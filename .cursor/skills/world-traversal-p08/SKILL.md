---
name: world-traversal-p08
description: >-
  Read-only first, operator-gated Sims 4 in-world object highlight perception
  and observed-outcome learning. Use for lost highlight, world target tracking,
  camera reacquisition, P08 sensor validation and world-click confidence.
---

# World target highlight / P08 — canonical local skill (P00/P01)

**This is workflow guidance, not a running tool or a game-input grant.**
Resolve `AGENTS.md` → `docs/AGENT_OPERATING_RULES.md` → `docs/DOCTRINE.md` → `docs/ONTOLOGY.md`; P00/P01 source of truth is `contracts/world-traversal-harness.v1.json`. The actual learning algorithm lives in `betterinstincts/world_traversal_learning.py`; this skill must not recreate it as cursor/Playwright logic.

## Trigger

Activate when an agent is assigned in-world object/highlight recognition, object occlusion, camera changes, world target tracking, a click that unexpectedly misses, before/after click-result learning, or `BI-WORLD-TRAVERSAL-P08-SENSOR`. **Do not** use for ordinary fixed UI chrome or as a global screen clicker. Local Cursor rule installation/activation requires separate host proof.

## Launch order — first runnable command

From the verified canonical BetterInstincts development checkout (not the managed-use app path or an arbitrary new clone):

```sh
python -m scripts.horizon_status
python -m scripts.check_world_traversal_harness
python -m scripts.check_horizon
python -m unittest tests.test_world_traversal_learning -v
python -m scripts.world_traversal_eval
```

Before editing behavior code, create a fresh `contracts/consultations/` record and invoke `python -m scripts.semantic_preflight --consultation <record> --operation repo_mutation --file <actual-path>`; tests and CI never authorize a Sims session. Refresh main/PRs; open PR #159 owns its own spatial-perception files and cannot be overwritten.

## WORLD_SENSOR — local-only, passive, explicit opt-in

The game-capable local agent checks exact Sims 4 build, approved disposable lab save, observed mode/lot, player presence and selected capture adapter. **No automatic scan or host focus borrow for passive capture.** Without those gates, write a `BLOCKED_LOCAL_GAME_ACCESS` fact; continue only source-level safe work.

Observe two ordered distinct `HOST_CAPTURE` frames of the same in-world object and camera revision, with two independent qualified highlight cues per frame. Measure bounds/hover and visible/occluded status. When a visible object's highlight disappears, `highlight_target_id: null` with two `ABSENT` cues must yield `HIGHLIGHT_LOST` and revoke the host click candidate. PRESENT without ID must abstain; single flicker, camera change, off-lot view and ambiguous cues cannot grant a reclick. Measure safe player takeover. Retain raw captures **local only**, not in Git, Drive, or tracked docs.

## WORLD_OUTCOME — later, separately admitted, serial

Only after `WORLD_SENSOR` local proof and a **new explicit operator-approved** one-effect permit, use the existing screen/lot/save/presence/exact-build guards. One reversible click at a time; verify the actual game menu/queue or target state afterward. Train only from reviewed or game-event post-action evidence with `player_interrupted: false`, distinct before and after capture refs and replay-unique before capture. Duplicates and holdout overlap abstain. A strategy ranking, test Brier score or `LOCKED` is not an input permit.

## WORLD_INTEGRATE — only after proof / owner reconciliation

Compose separately accepted sensor cues into `host_stack.world_target.highlight_frames` without creating another cursor controller or changing the open spatial-perception PR #159's owner. P08 evidence can support BI-002 object finding but **cannot close the BI-002 Hunger 5+5 A/B, rollback and maintainer review**.

## Safety, artifacts, readback

Single desktop game screen owner; run serial with BI-002 gameplay and WORLD_OUTCOME. Yield to any human interaction, in Sims or another app. Never manipulate Bluetooth/driver/Print Screen/OS input mappings, lock out Escape/U, mutate Sims user saves, Build/Buy structure, use outside-lot coordinates, auto-reclick, or start a background scanner. All paths resolve through `contracts/workstation-paths.v1.json`, not local-agent preference.

- Offline explicit model snapshots: ignored `dist/world-traversal-eval/`
- Local, consented P08 receipts: ignored `dist/game-host/<approved-run-id>/`
- Sanitize receipts and use source/commit refs only in `docs/LEDGER.md`

Final handoff: **CHANGED | PROVED | NEXT**, exact game version or `BLOCKED_LOCAL_GAME_ACCESS`, source SHA and CI status, any independent actual local sensor/click proof, observed operator takeover, and one next executable gate. See `docs/WORLD_TRAVERSAL_HARNESS.md`.
