# BetterInstincts: download, bootstrap and play

Status: pre-alpha offline toolkit, not a certified playable Sims 4 mod. The one-click Windows entrypoint is Start-BetterInstincts.cmd. Windows and actual game proof must be independently observed; source and CI are not that proof.

## Player workflow

1. Save the plain-text launcher from the download page and double-click it. It checks for Git and Python 3.11+. It does not elevate, modify the registry, services, drivers, keyboard, OS or game files, or install system prerequisites silently.
2. Reuse the canonical user checkout at %USERPROFILE%/dev/BetterInstincts. Missing: clone the official repository. Existing: require exact official origin, main branch, clean worktree, then fetch and fast-forward only. Never delete, reset or clobber unrelated/dirty work.
3. Reuse the existing bootstrap.py install lifecycle and ownership manifest. The toolkit remains separate from game files, personal saves and mods.
4. The first-run scanner checks bounded known EA/Steam/Epic paths and Steam libraryfolders metadata, with no drive crawl, save enumeration, Documents reads, telemetry, or input watchers. A deliberate double-click now attempts to launch the **single** detected game automatically, without a second Continue button. It first checks Windows tasklist read-only and avoids launching a second Sims process. If zero or multiple installs appear, the original local chooser opens; a failed/ambiguous process inventory blocks launch. The observed PIDs are process-name evidence only.
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

## Moonwake Fifth Gear acceptance

P95: download -> clone/fast-forward -> install -> discover -> player mode choice -> game launch -> game-owned save or CAS handoff.

P82: negative tests for wrong branch/dirty work, missing dependencies, missing/multiple games, untrusted paths, symlinks, unauthorized launch and non-Windows runtime.

P08: on a real Windows host, prove the downloaded file opens, game executable is identified, chosen EA/Steam launcher authentication is preserved, the game title/menu becomes visible, disposable existing save loads OR new CAS/place occurs, player takeover works and rollback does not touch protected saves. Remote source or CI alone cannot pass P08.

P07: implement and test the source, open PR, independently check CI and integrate only on valid results. P124: keep installer, game discovery, presentation and in-game host actions in separate owners.

Proof levels: source authored / push / CI / merge / actual download page hosted / Windows clicked / executable dispatched / visible game / save loaded / CAS finished / Live Mode observed must always be distinct. BI-002 hunger certification remains independently active.

The static page source is docs/download/index.html and can be served from /docs GitHub Pages or the operator-approved site. A tracked HTML source file does not establish a live website. No Pages account setting is changed as part of this feature.

## Unattended resume acceptance gate (NOT YET RELEASED)

Do not infer the last played household from slot filenames, timestamps, game-running PIDs, arbitrary screenshots or a guessed Resume control. A future automatic latest-save route must first establish a separately authorized save-identity metadata source without reading or modifying protected saves, bind it to a freshly observed exact game build and actual menu tile, verify two independent scene cues and user-idle/foreground state before each one-effect navigation, and stop on ambiguous/stale evidence or player interruption. Preserve this gate on every platform; no silent system settings or install-time daemons. Current implemented behavior is zero-extra-click **game dispatch** only; game loading, menu discovery and Live Mode remain unobserved until the real Windows EA/Steam/Epic P08 trial.
