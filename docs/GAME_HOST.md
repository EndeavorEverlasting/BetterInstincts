# BetterInstincts game-host runbook

## What is implemented

scripts/game_host.py provides a **local Windows** adapter for explicit Sims 4 executable launch, screen-template-based New Game or Load Game selection, bounded session receipts, operator-confirmed Live Mode, and one-shot ingestion of sanitized object-state snapshots. This is **not** a Sims 4 game script, a fully automatic character-creation flow, or an installed telemetry bridge. It does not overwrite, migrate, inspect, or delete any saved game.

Evidence levels stay separate: launch dispatched; GUI click dispatched; chosen save Play requested or New Game CAS requested; operator reported Live Mode with exact game patch and capture reference; external state file ingested but unverified. None grants mod certification. BI-002 still requires hunger A/B trials, rollback and maintainer review under docs/LIVE_CERT.md.

EA's documented existing-save path is Main Menu -> Load Game -> chosen slot -> Play. New Game requires Create-a-Sim and placement before Live Mode. The host adapter **never uses Resume**, which can target an unexpected autosave.

## First local setup

1. Reuse the game-capable Windows checkout and check Git status before pulling. Do not overwrite dirty local files. Use the actual personally selected game installation. The remote agent has not inspected any local game path.
2. Create an untracked dist/game-host/local-profile.json and uniquely matching cropped PNG screenshots in the same folder. The entire dist folder is ignored by Git. Only the local game-host agent may capture screenshots; never commit private screenshots, game assets, or a save manifest.
3. Keep a disposable, non-personal test save. For the chosen-save path, its screenshot tile must uniquely identify that disposable slot. For New Game, the one-click entry goes to CAS and still needs the local agent/operator to finish character/household setup.
4. In a local development Python environment, install pyautogui (and its screenshot dependencies) for the optional GUI navigation. This is **not** an in-game dependency. PyAutoGUI's fail-safe remains enabled. The game menu must be visible on the **same display** the adapter screenshots, and the templates must be calibrated for that host.
5. Read the exact full game version from the actual main menu before Live Mode confirmation. Null version is acceptable for first boot only, never for game certification.
6. Host focus caveats observed on first real boot: a minimized Sims window reports the classic `-32000` placement and will not accept template clicks until restored to the capture display; multi-monitor setups need the game on the primary capture screen. Cursor computer-control overlays can steal focus after a successful New Game click—Create-a-Sim / lot placement / Live Mode may require a short operator handoff even when `NEW_GAME_CAS_REQUESTED` is already receipted. A click receipt is still only `CLICK_DISPATCH_ONLY` until Live Mode is independently confirmed. Prefer `python -m scripts.game_host focus` (optional `--process-id`) which posts `SC_RESTORE` instead of relying on `ShowWindow` alone; the proof ceiling is still **window focus only**, not Live Mode or scene recognition. Do not drive CAS clicks through a computer-control overlay.

Example profile (illustrative path only; not a real detected installation):

~~~json
{
  "schema": "betterinstincts.game-host/v1",
  "platform": "windows",
  "game_executable": "C:\\EXPLICIT-GAME-PATH\\Game\\Bin\\TS4_x64.exe",
  "game_version": null,
  "save_mode": "chosen",
  "save_alias": "BI_LAB_DISPOSABLE_01",
  "templates": {
    "load_game": "load_game.png",
    "save_tile": "chosen_disposable_tile.png",
    "play": "play.png"
  }
}
~~~

For a new game, change save_mode to new and templates to {"new_game": "new_game.png"}. An alias is an opaque lab name, not the user's actual save title.

## Runnable commands

From the BetterInstincts repo root on the Windows game host:

~~~powershell
python -m scripts.game_host plan --profile dist/game-host/local-profile.json
python -m scripts.game_host launch --profile dist/game-host/local-profile.json --run-id bi002-first-boot --execute
# After the main menu visibly appears:
python -m scripts.game_host navigate --profile dist/game-host/local-profile.json --run-id bi002-first-boot --execute --disposable-confirmed
python -m scripts.game_host status --run-id bi002-first-boot
# Only after the actual intended disposable Sim is in Live Mode:
python -m scripts.game_host confirm --run-id bi002-first-boot --disposable-confirmed --game-version ACTUAL.FULL.PATCH.VERSION --capture-ref capture:live-mode-001
# New: initialize or safely reuse an empty baseline recorder, without Sims 4 Studio:
python -m scripts.game_baseline --run-id bi002-first-boot
python -m scripts.live_cert status --run-id bi002-first-boot
~~~

When New Game / CAS / lot placement was driven with PrintWindow + SendInput (or operator handoff) instead of template `navigate`, do **not** replay `navigate` against Live Mode. Record the CAS completion gate, then confirm:

~~~powershell
python -m scripts.cas_place_live
python -m scripts.game_host manual-cas-complete --run-id bi002-quiz-boot --disposable-confirmed
python -m scripts.game_host confirm --run-id bi002-quiz-boot --disposable-confirmed --game-version 1.121.361.1020 --capture-ref capture:live-lablab-001
python -m scripts.game_baseline --run-id bi002-quiz-boot
~~~

`manual-cas-complete` only advances `LAUNCH_DISPATCHED` → `NEW_GAME_CAS_REQUESTED` for `save_mode=new`. Proof ceiling remains manual-drive / not template click / not Live certification. Prefer the **Sim Story quiz** CAS path over manual skill/trait picking when the quiz dialog is available (more reliable disposable fill); arbitrary skills remain fine for host-mechanics boots. On **SELECT A PLACE TO LIVE**, prefer a vacant green-outline empty lot (`cas_place_live` `lot_empty_willow` / `LOT_BARGAIN_BEND`) before a furnished starter; Streamlet-style vacant houses are a fallback only.

### Relocate / HUD click notes (1920×1080 borderless, LOCAL_OBSERVED)

- Top-right HUD icons sit near **y≈22** (not y≈40). Options `…` ≈ `(1898, 22)`. Live HUD **Manage Worlds pin** ≈ `(1558, 22)` (Gallery is ~`(1608, 22)` — do not confuse).
- Options → **Manage Worlds** menu row ≈ `y=713`. Welcome Wagon can grey this out until cleared. **Save and Go to Manage Worlds** blue text ≈ `y=556` (question body is ~`y=492` — miss that).
- Modal buttons (Save and Go / Exit Create A Sim / overwrite / etc.): click the **blue text row**, not the tall white panel body.
- Permanent empty home: Manage Worlds → select home lot → expand lot actions → **Move Household** truck ≈ `(1692, 1000)` → select empty lot (**Bargain Bend** tip hover ≈ `(1400, 840)`, 30×20 §2,000) → BR confirm truck ≈ `(1840, 1017)` → moving modal check ≈ `(1240, 740)`. Travel/visit alone is not permanent home.
- Phone **Household** (blue house + gear) ≈ `(275, 840)`; clicks near y=760 often open Social Bunny instead.
- Manage Worlds bottom-right person button opens **Create-a-Sim** for empty lots—do not treat it as Play LabLab.
- Lab overwrite: Save list → select **LabLab / My Saved Game 3** row → row **Save** pill (~`y=500`, above Delete) → confirm overwrite checkmark. Never confirm Delete; never touch Richardson slots.
- Live **Needs** panel icon ≈ `(1822, 1062)` (red/orange glow when critical). Do not click ~`(1779,1045)` (hits Simology) or higher y into the lot (pie menu). Pause before panel clicks when the sim is selected.
- Build Mode enter via Live HUD hammer ≈ `(1505, 22)`. Exit Build → Live via top-right **people** icon ≈ `(1585, 35)` (do not use Esc — opens Options MENU). Kitchen → fridge illustration → **Crisponix Budget Dee-Lux (Used)** §215; place inland (~`(1100, 250)`), not on sidewalk boundary.
- School Join/Send Alone dialog (High School Years): modal ≈ `(776–1143, 436–622)`; **Send Alone** ≈ `(960, 600)` (bottom pill). Prefer Send Alone when needs are critical so the home lot stays under host control.
- Six-need host planner (offline): `python -m scripts.instincts_plan --needs-json PATH`. Uses `betterinstincts/instincts_host.py` + `horizon.choose`. Recommends **Save As** `BI_CONT_*` only when all six needs are green; never DELETE/OVERWRITE/RESUME or touch user-named saves. `BI_TMP_` / `BI_CONT_` are naming hints only — registry + operator attestation still required (see [SCENE_INTELLIGENCE.md](SCENE_INTELLIGENCE.md)).

Preflight does not launch anything. Launch requires explicit execute and only permits TS4_x64.exe or TS4.exe on Windows. It creates a non-overwriting repo-local dist/game-host/<run-id> manifest and JSONL receipts. GUI navigation requires execute plus disposable confirmation; each successful click leaves an event checkpoint, so a partial flow cannot be blindly repeated. If interrupted, inspect actual game UI and recover safely in a fresh session. Screenshot template matching fails closed if ambiguous or missing; no guessed coordinates or global scanning.

## Bounded one-shot object snapshot seam

The local game hook/sensor still has to be developed against a verified Sims 4 patch and game API. Once an approved local producer exists, it can write a short JSONL snapshot with one sample per line:

~~~json
{"schema":"betterinstincts.object-sample/v1","object_key":"sim-lab-01","metric":"hunger","value":0.52,"captured_at":"2026-11-06T23:00:00Z"}
~~~

After the Live Mode confirmation:

~~~powershell
python -m scripts.game_host poll --run-id bi002-first-boot --sample-file dist/game-host/local-snapshot.jsonl
python -m scripts.game_host status --run-id bi002-first-boot
~~~

This is a single explicit read (max 64 rows / 64 KiB), **not** autonomous process polling or game observation. It accepts only allowlisted metric names and numeric values, emits receipt metadata and the SHA-256 of the input, and does not preserve raw player/Sim data in tracked files. A successful poll returns SAMPLE_INGESTED_UNVERIFIED, not GAME_LIVE_CERTIFIED. A real game sensor and independently reviewed capture remain an unproven next gate.

## Test, review and promotion

Run offline: python -m unittest discover -s tests -v, python -m scripts.check_horizon, python scripts/validate_doctrine.py, and python scripts/check_tracked_assets.py. CI can test synthetic profiles and UI-driver fakes but **cannot** load The Sims 4. Keep existing BI-002 game certification gates: exact patch/platform/module, actual reversible hunger package, five baseline and five modified sessions, rollback, player-queue protection, real runtime observation and maintainer review. Do not claim these were run remotely.

Do not add an unattended scheduled job, cloud telemetry, save manipulation, automatic mod installer or release deployment until the local producer and game experiment are proven. The first useful follow-on is a patch-specific, opt-in in-game observer feeding this bounded snapshot format, alongside actual BI-002 hunger mod testing. Preserve old certified patch evidence and the BI-004 income horizon; BI-MODLAB remains a tooling lane.

Links: docs/LIVE_CERT.md, docs/COMPATIBILITY.md, docs/VALIDATION.md, plans/active/BI-002.execution.v1.json, plans/active/BI-MODLAB.HANDOFF.md.

## Canonical local-agent handoff

The ordered live-game launch, hunger A/B test, snapshot-producer and maintainer lanes are owned by [the P04 game-host handoff](../plans/active/BI-GAME-HOST.HANDOFF.md) and its [typed dispatch contract](../plans/active/BI-GAME-HOST.dispatch.v1.json). No local Sims execution is implied by their existence.

## CAS → Live Mode: the measured next step (2026-11-06)

Real `TS4_x64` reached Create-a-Sim for game version `1.121.361.1020`, run `bi002-first-boot`, in [merged PR #13](https://github.com/EndeavorEverlasting/BetterInstincts/pull/13). The current-host process/PID are historical receipts, not a promise it remains running. After any unattended pause, inspect the window before continuing; NEVER replay the New Game click against an unknown screen.

**Minimal operator step:** bring The Sims 4 to the foreground; prefer **Sim Story** (quiz) over manual skill picking for the disposable Sim fill; create an expendable adult Sim; choose a disposable empty lot and enter **Live Mode**. Do not Resume or load personal saves. Share `READY_LIVE` with the **local game-capable agent**, not as machine proof by itself. No computer-control overlay should be used during focus-sensitive CAS clicks.

**Local agent immediately after Live Mode:** verify the actual game screen and disposable household, capture a private reference, run the `game_host confirm` command above using the observed exact patch, then run `python -m scripts.game_baseline --run-id bi002-first-boot`. This starts a repo-local **zero-trial** `live_cert` recorder with Studio build `NOT_OBSERVED`. It never claims ingestion, an observed hunger delta, or gameplay certification. Retries preserve existing trial rows; a mismatched session version fails closed. The first real hunger baseline still requires a locally measured observation for every numeric field, capture reference, and `python -m scripts.live_cert record --stage baseline --trial 1 ...` with actual measurements only. Record five repeatable vanilla trials, then independently investigate tuning before authoring or attesting a modified package.

**Sims 4 Studio is not a prerequisite for vanilla baseline recording.** Once its real build is observed, the game-host agent records `python -m scripts.live_cert studio --run-id bi002-first-boot --build ACTUAL_STUDIO_BUILD`. The unobserved placeholder is prohibited from package attestation; installing/claiming Studio is never inferred. Full certification still requires actual package hash, verified resource, five modified trials, rollback, player-command and performance checks, independent maintainer review.

CI covers fake host receipts and recorder behavior; it cannot complete Create-a-Sim, operate Live Mode or manufacture measured gameplay observations.

## BI-SCENE-MAP — scene-state and chosen-save safety

Read [docs/SCENE_INTELLIGENCE.md](SCENE_INTELLIGENCE.md) and `contracts/game-scenes.v1.json`. Scene classification is a candidate-only pure offline decision with unknown/ambiguous abstention, NOT a screenshot classifier or click permission. The prior `save_mode=chosen` UI path now refuses to navigate without a same-profile-directory private `save_registry`, `selected_save_id`, `selected_save_capture_ref`, exact game patch, and operator-attested LAB_CREATED identity matching the run. Personal, unknown and unregistered slots must never be selected automatically, even when labelled `BI_TMP_`. An old chosen profile may still plan/launch but selection fails closed until a valid lab origin/capture is reviewed. `save_mode=new` remains the first-boot CAS route and never chooses an existing slot. P04 handoff follows merged implementation.
