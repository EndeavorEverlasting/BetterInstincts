# BetterInstincts: download, bootstrap and play

Status: pre-alpha offline toolkit, not a certified playable Sims 4 mod. The one-click Windows entrypoint is Start-BetterInstincts.cmd. Windows and actual game proof must be independently observed; source and CI are not that proof.

## Player workflow

1. Save the plain-text launcher from the download page and double-click it. It checks for Git and Python 3.11+. It does not elevate, modify the registry, services, drivers, keyboard, OS or game files, or install system prerequisites silently.
2. Reuse the canonical user checkout at %USERPROFILE%/dev/BetterInstincts. Missing: clone the official repository. Existing: require exact official origin, main branch, clean worktree, then fetch and fast-forward only. Never delete, reset or clobber unrelated/dirty work.
3. Reuse the existing bootstrap.py install lifecycle and ownership manifest. The toolkit remains separate from game files, personal saves and mods.
4. The first-run scanner checks bounded known EA/Steam/Epic paths and Steam libraryfolders metadata, with no drive crawl, save enumeration, Documents reads, telemetry, or input watchers. A deliberate double-click now attempts to launch the **single** detected game automatically, without a second Continue button. It first checks Windows tasklist read-only and avoids launching a second Sims process. If zero or multiple distinct Game/Bin installation roots appear, the original local chooser opens; `TS4.exe` and `TS4_x64.exe` inside the **same** verified Game/Bin root count as one installation (64-bit preferred). A malformed or ambiguous process inventory blocks new launch rather than assuming no game is running. Observed PIDs are process-name evidence only, not authenticated full-path identities. A failed post-launch inventory never causes an automatic second launch. A concurrent double-click launch race is not yet independently proven safe on Windows.
5. The explicit double-click (or `python -m scripts.first_run auto`) requests only a game launch. The manual chooser buttons also remain supported. A subprocess dispatch PID may be the launcher rather than TS4; a separate read-only tasklist snapshot may observe a game PID, but neither is evidence that the game reached its menu or loaded a save.
6. Existing: choose Load Game, verify the save and select Play. **No latest-save auto-load is shipped yet**: current policy protects all unknown/user saves, and newest file timestamps are not reliable proof of last played game or the correct on-screen tile. Unknown Resume targets are never automatically clicked. New: choose New Game, design your Sim and place them; optional traits/aspirations by playstyle are guidance, not automatic CAS mutations.

EA/Steam authentication, if requested, remains the game platform's own player process. BetterInstincts never installs The Sims 4 for the player, bypasses authentication, or requires changing Windows security protections.

## Existing owners and CLI

From the repository checkout:

    python -m scripts.first_run auto
    python -m scripts.first_run auto --fallback-gui
    python -m scripts.first_run discover
    python -m scripts.first_run plan --mode new --goal career
    python -m scripts.first_run gui
    python -m scripts.first_run launch --game-exe "C:\Program Files\EA Games\The Sims 4\Game\Bin\TS4_x64.exe" --mode existing --confirm-launch

Existing bootstrap.py owns install, doctor, uninstall and the added Play The Sims 4 GUI handoff. betterinstincts/first_run.py owns read-only discovery and explicit launch policy. scripts/first_run.py owns both the chooser and the explicit auto CLI; scripts/smart_start.py owns read-only Windows process inventory, single-install/single-process admission and process dispatch evidence. contracts/launch-journey.v1.json records the state contract. scripts/game_host.py remains the calibrated local game-host owner requiring actual scene captures, screen permission and save safety, not silently invoked by this launcher.

## Skill-aware first-session plan (new Sims)

The existing GUI and CLI now produce deterministic, goal-aware skill priorities and an ordered first-session plan, in addition to the existing aspiration/trait suggestions. This is a player-owned, advisory-only route, not automatic Create-a-Sim editing or a way to grant skill levels during CAS.

The planner begins with player CAS decisions, evaluates all six needs, prioritizes urgent survival over optional training, checks funds before equipment costs when income is pressured, and reassesses career demands, needs, free time and leisure. Players can select a preferred starting skill, which outranks generic goal weights. Suggestions use base-game, adult-oriented examples; age, packs, budget and actual outcomes must be verified in-game.

CLI examples:
- python -m scripts.first_run plan --mode new --goal balanced
- python -m scripts.first_run plan --mode new --goal creative --preferred-skill painting --income-pressure
- python -m scripts.first_run plan --mode new --goal career --critical-needs

The first-run GUI offers preferred skill and early-earnings choices, then displays the top three skills and first-session gates. No save reads, OS input changes, clicks, automatic job enrollment, skill cheats, telemetry or game modifications occur. The automatic launcher still dispatches the game only; CAS and menus remain player-owned. Exact-patch local Windows/CAS certification and any future effect controller remain open under issue #201 and the existing BI-002 game gate.



## MoonWake Closers — verified manual-launch admission (2026-11-13)

The manual first-run chooser and the explicit `python -m scripts.first_run launch` CLI now reuse the **same read-only Windows tasklist admission** as automatic one-click startup. Before any manual dispatch they require a validated installed Game/Bin executable and explicit launch request, then perform bounded process snapshots; a running Sims instance is reused without launching another, while multiple games, ambiguous or untrusted inventories, or a concurrent start block the launch safely. An already-running process is evidence only of a process-name/PID snapshot, not of the selected executable path, correct save, scene or Live Mode.

The GUI now resolves two executables within a **single** detected Game/Bin root to the 64-bit executable instead of incorrectly asking the player to choose between two identical installations. Multiple distinct game roots still need explicit selection.

CLI remains explicit:

```sh
python -m scripts.first_run launch --game-exe "C:\\Program Files\\EA Games\\The Sims 4\\Game\\Bin\\TS4_x64.exe" --mode new --goal career --confirm-launch
```

The new-Sim goal/skill plan is validated before dispatch. No game menu, CAS traits or skills, latest-save identity or player queue is modified. Duplicate-launch checks are source/CI tested; simultaneous Windows launchers, actual PID identity, new CAS creation and gameplay remain local P08 gates. The first-run default `auto` entrypoint still launches without choosing New Game for the player. This closer intentionally fixes consistency rather than inventing a CAS-effect controller.


## Moonwake Fifth Gear acceptance

P95: download -> clone/fast-forward -> install -> discover -> player mode choice -> game launch -> game-owned save or CAS handoff.

P82: negative tests for wrong branch/dirty work, missing dependencies, missing/multiple games, untrusted paths, symlinks, unauthorized launch and non-Windows runtime.

P08: on a real Windows host, prove the downloaded file opens, game executable is identified, chosen EA/Steam launcher authentication is preserved, the game title/menu becomes visible, disposable existing save loads OR new CAS/place occurs, player takeover works and rollback does not touch protected saves. Remote source or CI alone cannot pass P08.

P07: implement and test the source, open PR, independently check CI and integrate only on valid results. P124: keep installer, game discovery, presentation and in-game host actions in separate owners.

Proof levels: source authored / push / CI / merge / actual download page hosted / Windows clicked / executable dispatched / visible game / save loaded / CAS finished / Live Mode observed must always be distinct. BI-002 hunger certification remains independently active.

The static page source is docs/download/index.html and can be served from /docs GitHub Pages or the operator-approved site. A tracked HTML source file does not establish a live website. No Pages account setting is changed as part of this feature.

## Unattended resume acceptance gate (NOT YET RELEASED)

Do not infer the last played household from slot filenames, timestamps, game-running PIDs, arbitrary screenshots or a guessed Resume control. A future automatic latest-save route must first establish a separately authorized save-identity metadata source without reading or modifying protected saves, bind it to a freshly observed exact game build and actual menu tile, verify two independent scene cues and user-idle/foreground state before each one-effect navigation, and stop on ambiguous/stale evidence or player interruption. Preserve this gate on every platform; no silent system settings or install-time daemons. Current implemented behavior is zero-extra-click **game dispatch** only; game loading, menu discovery and Live Mode remain unobserved until the real Windows EA/Steam/Epic P08 trial.
