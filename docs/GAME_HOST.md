# BetterInstincts game-host runbook

## What is implemented

scripts/game_host.py provides a **local Windows** adapter for explicit Sims 4 executable launch, screen-template-based New Game or Load Game selection, bounded session receipts, operator-confirmed Live Mode, and one-shot ingestion of sanitized object-state snapshots. This is **not** a Sims 4 game script, a fully automatic character-creation flow, or an installed telemetry bridge. It does not overwrite, migrate, inspect, or delete any saved game.

Evidence levels stay separate: launch dispatched; GUI click dispatched; chosen save Play requested or New Game CAS requested; operator reported Live Mode with exact game patch and capture reference; external state file ingested but unverified. None grants mod certification. BI-002 still requires hunger A/B trials, rollback and maintainer review under docs/LIVE_CERT.md.

EA's documented existing-save path is Main Menu -> Load Game -> chosen slot -> Play. New Game requires Create-a-Sim and placement before Live Mode. The host adapter **never uses Resume**, which can target an unexpected autosave.

## First local setup

1. Reuse the game-capable Windows checkout and check Git status before pulling. Do not overwrite dirty local files. Use the actual personally selected game installation. The remote agent has not inspected any local game path.
2. Create an untracked dist/game-host/local-profile.json and uniquely matching cropped PNG screenshots in the same folder. The entire dist folder is ignored by Git. Only the local game-host agent may capture screenshots; never commit private screenshots, game assets, or a save manifest.
3. Keep a disposable, non-personal test save. For the chosen-save path, its screenshot tile must uniquely identify that disposable slot. For New Game, the one-click entry goes to CAS and still needs the local agent/operator to finish character/household setup.
4. In a local development Python environment, install pyautogui (and its screenshot dependencies) for the optional GUI navigation. This is **not** an in-game dependency. PyAutoGUI's fail-safe remains enabled. The game menu must be visible on screen and the templates must be calibrated for that host.
5. Read the exact full game version from the actual main menu before Live Mode confirmation. Null version is acceptable for first boot only, never for game certification.

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
~~~

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
