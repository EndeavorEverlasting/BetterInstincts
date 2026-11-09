# P04 — A-OK-Bloomer Vertical Garden → Household Inventory (local-game execution)

**Mission / observable result:** On an explicitly authorized disposable Sims 4 lab save, locate the **A-OK-Bloomer Vertical Garden** from Build/Buy using **`AOK`**, acquire it **without placing it on the lot**, use **Backspace** while the object is held to deposit it in **Household Inventory**, reopen that inventory, and independently verify the exact item is present. This task is not complete when the planner emits JSON, a keypress is acknowledged, a PR is merged, or an inventory tab is merely opened.

## LAUNCH ORDER — one local agent, no operator relay of repository context

1. **REPO-0 (CURRENT_CHAT_RUNTIME / GitHub provider): COMPLETED at 2026-11-09 reconciliation floor.** PR [#83](https://github.com/EndeavorEverlasting/BetterInstincts/pull/83) integrated the AOK catalog recipe, [#90](https://github.com/EndeavorEverlasting/BetterInstincts/pull/90) integrated the screen atlas, and [#91](https://github.com/EndeavorEverlasting/BetterInstincts/pull/91) integrated the 15-second shared-screen lock and safe Git uninstall at `fd5fa3536029cae7a9020fa543d0c321d709c23d`. Refresh current `origin/main` rather than reset to that historical floor. Do not re-cherry-pick their source branches.
2. **GAME-0 (LOCAL_AGENT_RUNTIME, GATE):** identify the actual Windows Sims process, exact full patch, foreground/window bounds and UI scale; confirm Eco Lifestyle content and an operator-authorized disposable **LAB** save; inspect Build/Buy scene via two independent cues. Verify no active player task/queue and valid opt-in host session. Missing any signal: stop effects, preserve goal.
3. **MAP-1 (LOCAL_AGENT_RUNTIME, GATE):** obtain the existing evaluated AOK plan; compare named screen targets against **fresh, real, exact-patch** game captures; calibrate each target. Do not execute `CANDIDATE_UNVERIFIED` normalized positions as though they were verified. Select the native Win32 adapter for the native Sims game, not an imaginary Playwright DOM.
4. **ITEM-1 (LOCAL_AGENT_RUNTIME):** with the 15-second global human-idle check, shared desktop lock, scene/target revalidation, and one step per admission, search `AOK`; confirm the result's **actual displayed title** matches the vertical garden; acquire it into the held-object state; press **Backspace**; open Household Inventory. Never place it on the lot and never send an unverified spawn/cheat ID.
5. **PROOF-1 (LOCAL_AGENT_RUNTIME):** record before/after Household Inventory contents and a visually inspected item identity, catalog/held-object/Backspace/inventory receipts and transaction/funds state when available. Capture bounded screenshots in ignored `dist/` and independently review the outcome. If item is absent or uncertain, classify as **NOT_PROVEN** and recover without a blind second purchase.
6. **CONVERGENCE:** update the tracked canonical ledger with sanitized result only after observed proof; keep issue [#35](https://github.com/EndeavorEverlasting/BetterInstincts/issues/35) and BI-002 active until their **separate** live-certification requirements are met. Report **CHANGED | PROVED | NEXT**, exact patch, current SHA, user-save protection and one next executable command.

## Read first and available source owners

`AGENTS.md` → `docs/ONTOLOGY.md` + `docs/DOCTRINE.md` + `docs/LEDGER.md` → `docs/UI_CHROME.md` + `contracts/ui-chrome.v1.json` + `betterinstincts/ui_chrome.py` → `docs/SCREEN_ATLAS.md` + `docs/ASYNC_INTEROP.md` → `docs/SCENE_INTELLIGENCE.md` + `docs/HOUSE_STATE.md` + `docs/LIVE_CERT.md` + `plans/active/BI-002.execution.v1.json`.

**P03** provided current repository/PR/branch evidence and the first safe integration sprint; **P141** selected preservation plus real-game proof over wholesale old-branch cherry-picks or a new screen controller; **P124** keeps `ui_chrome`, `screen_atlas`, `ui_mode` and `control_handoff` as separate established owners. Moonwake is the source of exact P-number meanings; this handoff does not redefine them. There is no new background agent, camera watcher, UI-map fork, or player input bypass.

## First local commands (in a safe current checkout)

```powershell
git status --short
git branch --show-current
git fetch origin
git log --oneline -5
python -m scripts.semantic_preflight
python -m unittest tests.test_ui_chrome tests.test_screen_atlas tests.test_control_handoff tests.test_workflow_interop -v
python -m scripts.ui_chrome plan --item-id a_ok_bloomer --mode BUILD --client 1920 1080
python -m scripts.screen_atlas inventory
python -m scripts.screen_atlas target --mode BUILD --id catalog.search_field
```

The `1920 1080` argument above inspects the existing **candidate** map only. Substitute measured actual client size and do not click on that map before exact-build calibration and independent player-safe admission. If the checkout is dirty or the branch has active agent work, preserve it and use an isolated safe worktree; never force-reset or overwrite work.

## Exact transaction protocol (one input at a time)

**Precondition:** `LAB_SAVE_ATTESTED` + `ECO_LIFESTYLE_AVAILABLE` + `WINDOW_AND_PATCH_MATCH` + `BUILD_OR_BUY_CONFIRMED_BY_TWO_CUES` + `PLAYER_IDLE_AT_LEAST_15000_MS` + `SCREEN_LOCK_HELD` + `CATALOG_TARGET_VERIFIED`. An F2/F3 hotkey alone does **not** prove mode. Search field, first-result and cardboard-box inventory tab are **CANDIDATE_UNVERIFIED** at the historical 1920×1080 profile.

| Step | Admitted action | Required observation before next step |
| --- | --- | --- |
| 0 | Inspect Household Inventory and funds | Record whether exact A-OK-Bloomer is **already present**; if yes, stop as `ALREADY_PRESENT`, not a new-purchase success |
| 1 | Enter confirmed Build/Buy | Two independent mode/scene cues, live exact patch, authorized lab save |
| 2 | Focus verified catalog search, type `AOK`, press Enter | Search results refreshed, no stale target/overlay |
| 3 | Inspect matching result and select **A-OK-Bloomer Vertical Garden** | Exact title/pack match, available price/funds, explicit held-object ghost/cancel affordance; never assume first result is correct |
| 4 | Press **Backspace** with that object still held | Held ghost disappears or UI indicates deposit; **not** lot placement |
| 5 | Open verified **Household Inventory** tab | Exact object is present in correct household inventory, and purchase/funds effects are reconciled |
| 6 | Capture item identity and receipt, park pointer at interior only if uninterrupted and independently admitted | Independent before/after evidence; no duplicate spending or camera traversal |

**Success gate:** `AOK_IN_HOUSEHOLD_INVENTORY_OBSERVED` requires an actual in-game Household Inventory listing of the named item on the authorized save, with an independently corroborated held-object/deposit transition and a reviewer-accepted screenshot/receipt. No claim that a Sim is personally carrying a large planter. The repository's `§365` price is an unverified catalog expectation, **not** a substitute for real price/funds observations.

**Interruption and recovery:** Human input in any app, stale input age, unknown game patch, active player queue, lost foreground PID, misidentified search result, black/unknown scene, lost screen lease, target drift, or changed resolution → **PAUSED / NO NEW EFFECT**. Preserve pending intent. After a possible partial purchase, reconcile both inventory and funds before retrying; never replay a clicked/Backspace step blindly. If the item is already in Household Inventory, record `ALREADY_PRESENT` and avoid buying another. If a held ghost is still visible, do not place it: ask the host to reacquire safely, reobserve, and cancel only if justified. No saving over a protected game slot.

## Receipt and truth dimensions

Write private/nonsecret bounded runtime evidence only under ignored `dist/game-host/aok-bloomer/`. The local agent owns a structured receipt with fields: `run_id`, `repository_head`, `game_version_full`, `platform`, `process_id`, `save_classification` (not personal save path), `eco_lifestyle_observed`, `mode_cues`, `viewport_and_ui_scale`, `calibration_review_ref`, `player_idle_probe_refs`, `screen_lease_ref`, `item_title_seen`, `inventory_before`, `inventory_after`, `held_object_seen`, `deposit_event_seen`, `funds_before_after`, `screenshot_refs`, `review_status`, `outcome`, `next_action`. Use `NOT_OBSERVED` explicitly rather than manufacturing values.

Distinguish **plan generated**, **host admitted**, **input issued**, **item held**, **inventory observed**, **reviewed success**, **git committed**, **PR merged**, and **BI-002 live-certified** independently. Only the fifth plus independent review can close this specific AOK task. The existing broader BI-002 hunger trials and issue #35 cross-agent interrupt cert remain independently open.

## Repository reconciliation (GitHub provider audit, 2026-11-09)

At audit time there were **38 non-default branches**: **12 strictly behind `main` (zero ahead)** and **26 diverged**. GitHub reported **zero open PRs** after merging #91; issue **#35** was the only open issue and remains valid. Branch references were **not deleted**: the available provider actions do not expose delete-branch and divergent history is not automatic evidence of a missing feature.

The strictly-behind, potential archive candidates are: `codex/garden-and-catalog`, `codex/gardening-behavior`, `codex/p04-windows-preflight`, `codex/tandem-needs-gardening`, `docs/bi-semantic-ontology-p04-20261107`, `feat/bi-camera-safe-traverse-20261108`, `feat/bi-curious-catalog-20261107`, `feat/bi-hidden-object-host-p04-20261107`, `feat/bi-hidden-object-scout-sustained-goal-20261107`, `feat/bi-ontology-foundation-20261107`, `feat/bi-p04-debug-playbook-enforcement-20261107`, `fix/p83-ontology-preflight-and-resume-20261107`. **Before any branch deletion:** recheck remote HEAD, open PR references, unpushed local worktrees and whether branch deletion is user-authorized. The 26 diverged branches require a patch/tree-equivalence audit, not just `ahead_by`; old PR #84 is explicitly superseded by merged #86, and the source heads of merged #83/#90/#91 need not be replayed merely because squash history diverges. Preserve unique work.

**Next command for the game-capable agent:** `python -m scripts.ui_chrome plan --item-id a_ok_bloomer --mode BUILD --client 1920 1080`, then acquire *real local game* exact-build calibration and the first safe admitted interaction. Do not stop at producing another plan.
