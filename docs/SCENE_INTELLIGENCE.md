# BetterInstincts Scene Intelligence — canonical design and safety contract

**BI-SCENE-MAP | First catalog revision | No game UI shipped.** Primary audience: the Windows Sims 4 game-host agent and lab operator. Outcome: recognize and safely traverse the real game with an upgradeable, evidence-qualified scene model; never infer ownership from a save's name.

## Authority, provenance and proof

Source and machine authority: `contracts/game-scenes.v1.json` (35 candidate scene IDs), `contracts/save-policy.v1.json`, `betterinstincts/scenes.py`, `betterinstincts/save_policy.py`. Entry points: `scripts/scene_map.py`, `scripts/save_guard.py`; existing `scripts/game_host.py` uses `selected_save_guard` **before** any Load Game selection click. `scripts/check_scene_contract.py` and CI prevent removing the safety boundary. Root AGENTS.md and doctrine remain higher authority. No parallel policy owners.

**Evidence ceiling:** First live game startup and CAS were observed on patch `1.121.361.1020` (PR #13); subsequent Live Mode and hunger trials have not been observed. The catalog's visual cues are semantic placeholders, **not screenshot templates or a trained vision model**. Merely supplying expected cues does not independently verify a screen. `CANDIDATE_UNVERIFIED` is never a game observation or permission to click. Unknown patch, ambiguous scene or missing independent evidence returns abstention. New game patches must add new exact-build evidence/catalog revisions without silently rewriting older certified profiles.

## Scene families / UI shape

- **Launch and loading:** launcher tile, splash, startup loading, main menu, new-game entry, save picker/detail, world loading, lot loading, travel loading, errors.
- **CAS and household:** story quiz, editor, household placement, household management/detail.
- **Maps:** world selection, neighborhood map, lot details, Manage Worlds confirmation.
- **Live and Build:** Live Mode, Build/Buy, paused view, travel selection.
- **Libraries and overlays:** Gallery browse/details, My Library browse/details, options/settings, save/save-as/exit dialogs, Marketplace, unknown overlay.

Every scene record supplies `id`, `family`, two source-distinct required cues, `ux_regions`, explicit `assumptions`, `evidence_state`, and typed outgoing `transitions` with `gate` and `execution: MANUAL_ONLY`. A transition is a candidate decision tree, not a fully validated in-game route. Overlay returns may depend on source context; absent that context, ask for operator verification instead of defaulting to a potentially wrong screen. Unknown state is terminal in the decision model.

**Scene observation flow (P95 thin call stack):**
`operator/capture adapter -> sanitized explicit cues -> scene_map CLI -> scenes.load_catalog -> validate exact patch + 2 cue sources -> classify -> propose_transition -> JSON proposal or BLOCKED`. There is **no** click or filesystem write in this call stack. Failure: missing cue, conflicting two-scene matches or unknown patch -> unknown/BLOCKED, no fallback to latest. The next local build seam is a bounded, game-version-calibrated screenshot-recognition adapter that emits authentic cues and capture refs; it must be independently tested against real screenshots before any guarded click.

**Save-selection call stack:** `game_host.navigate(chosen) -> session/profile floor -> save_policy.selected_save_guard -> same-directory private manifest -> decide exact save ID, alias, original lab provenance, current run, exact patch, current capture, operator approval -> permitted lab SELECT_FOR_PLAY only -> existing unique screenshot template click -> click-only receipt`. Failure: absent/mismatched/duplicate/protected record -> `SAVE_SELECTION_PROTECTED` before `gui.locateAllOnScreen` or `gui.click`. `new` mode does not select an existing save. **Resume is never used.**

## Save taxonomy and naming conventions

| Class | Suggested name | Who owns it | Host authorization |
| --- | --- | --- | --- |
| `LAB_DISPOSABLE` | `BI_TMP_EXPERIMENT_01` | Explicitly lab-created, operator-attested | Only selected lab slot, exact run/version/capture |
| `LAB_CONTINUATION` | `BI_CONT_EXPERIMENT_01` | Lab-created and retained across sessions | Explicit current-session selection; never auto-delete |
| `USER_PROTECTED` | Any user-defined name, *including BI-like names* | User | No automated selection or modification |
| `UNKNOWN_PROTECTED` | Anything unregistered, missing, ambiguous or unverified | Assume user/protected | No automated selection or modification |

**A name is NEVER a disposal grant.** `BI_TMP_` and `BI_CONT_` are hints only. The policy requires a unique, explicitly bound local registry entry with `origin=LAB_CREATED`, `lab_origin_confirmed=true`, `operator_confirmed=true`, `creation_run_id`, `authorized_run_id`, `game_version`, `save_id`, `capture_ref`, and matching alias. That is **operator attestation, not independent save-file forensics**. The game host also requires an exact, user-calibrated screenshot tile template. Personal saves are protected regardless of how their names look. Conflicting aliases and identities fail closed. DELETE, OVERWRITE, MIGRATE and RESUME remain unconditionally denied even for lab saves. No scanner enumerates or edits the game's actual saves directory.

## Private local manifest example (illustrative, NOT an observed save)

Keep a manifest only alongside an explicitly selected local `dist/game-host/local-profile.json`, never in tracked Git. The local agent must use real operator-observed values, not the following fixture strings.

```json
{
  "schema": "betterinstincts.save-register/v1",
  "entries": [{
    "save_id": "slot:observed-lab-identity",
    "alias": "BI_TMP_EXPERIMENT_01",
    "classification": "LAB_DISPOSABLE",
    "origin": "LAB_CREATED",
    "lab_origin_confirmed": true,
    "creation_run_id": "bi002-first-boot",
    "authorized_run_id": "bi002-chosen-session",
    "game_version": "1.121.361.1020",
    "capture_ref": "capture:unique-disposable-tile",
    "operator_confirmed": true
  }]
}
```

For `save_mode=chosen`, the private profile needs `save_registry="local-save-register.json"` (the manifest's filename in the same folder), `selected_save_id` and `selected_save_capture_ref` matching the observed registration. A legacy `chosen` profile without this binding may launch a process but MUST NOT navigate the save picker. This deliberately fails closed for older automatic selection paths. Use `save_mode=new` for the new disposable CAS route without an existing-save registry; still require the local operator to confirm the created save's ownership before any continuation.

## Local commands (synthetic cues first, no game changes)

```powershell
python -m scripts.check_scene_contract
python -m scripts.scene_map --game-version 1.121.361.1020 --observations dist/game-host/cues.json --target cas_editor
python -m scripts.save_guard --registry dist/game-host/local-save-register.json --save-id slot:OBSERVED --run-id RUN_ID --alias BI_TMP_EXPERIMENT_01 --game-version 1.121.361.1020 --capture-ref capture:OBSERVED
python -m unittest discover -s tests -v
```

The `cues.json` file is an explicitly provided JSON array such as `[{"source":"visual","token":"cas:story_quiz"},{"source":"operator","token":"quiz_choices_visible"}]`. Do not create a synthetic screenshot and claim real CAS recognition. Outputs are read-only JSON to stdout. Any sensitive screenshot/capture and local manifest must stay in ignored repo-local `dist/`; never upload private save lists or EA game assets.

## Design choice and alternatives (P95 / P82)

Compared: (A) coordinate/script-specific screen automation, (B) flat screenshot filename→click map, (C) typed scene graph plus independent save policy. A fails on focus theft and patch/layout changes, already observed in CAS; B cannot encode transitions, ambiguity and ownership. Chosen C separates **recognition**, **permission**, and **side effect**, makes ambiguity and unknown patch explicit, and keeps automation manual pending genuine evidence. Offline tests execute success and failure stacks with fake cues, fake saves and a fake GUI; the same interfaces will serve future local capture adapters.

## Live certification / upgrade process

1. Local operator re-enters actual game `bi002-first-boot`; finish disposable CAS → lot → Live Mode. Review real screenshots and screen cues per scene, store bounded private refs with exact game patch, focus state, window mode, display, optional DLC, localization and resolution.
2. For each distinct variant, record observed cues and transitions, label *observed* vs *hypothesized*, test known negatives/overlays and screenshot ambiguity. Do not auto-accept a transition because its target exists in JSON. Calibrate one build at a time; preserve prior proofs.
3. Bind a lab save only after origin, identity and current-run authorization are actually reviewed. Otherwise treat as USER/UNKNOWN_PROTECTED; NEVER touch personal saves.
4. Once disposable Live Mode is independently verified, run `python -m scripts.game_host confirm --run-id bi002-first-boot --disposable-confirmed --game-version 1.121.361.1020 --capture-ref capture:live-mode-001` **only if that capture exists**, then `python -m scripts.game_baseline --run-id bi002-first-boot`; collect five actual vanilla hunger trials, five modified trials, rollback and maintainer review. Sims 4 Studio remains pending for modified-package tuning.
5. Any game patch, new world, new UI overlay, accessibility layout or DLC is an additive discovery/variant and regression task. Unknown/unreviewed patches fail closed, no automatic latest fallback; validate in CI and verify behavior live before enabling future host automation.

**No new user-facing UI has been shipped.** Design reference IDs carried as pointers only: `impeccable`, `UP-60B0939CC`, `UP-60FBA76B5`, `UP-F8DA7EE77`; no upstream code or artwork copied.
