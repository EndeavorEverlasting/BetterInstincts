## Certification-first existing-game handoff

If Sims is already open for certification, use `Continue-BetterInstincts-Certification.cmd` to start the scoped local agent in the existing evidence checkout. See [the current-session task](LIVE_CERTIFICATION_HANDOFF.md).

The launcher receipt now includes `lab_save_route` from the single ignored `dist/game-host/active-certification.v1.json` memo (when provisioned). **Finish the already-open Video Gaming "IT BEGINS..." certification first**: an already-running game must be inspected and preserved, not restarted or displaced by the oldest disposable save. Historical vanilla/modded and Yes/No trials are not erased or silently replayed. Without a running game, only the exact previously authorized pinned lab save may be advised; never pick an old personal/unknown save by date. After the *current* certification has genuinely reviewed outcome/effect/rollback receipts, ordinary standardized trials may use `scripts.save_candidate_priority`'s oldest eligible lab-disposable advisory. Nothing auto-selects or resumes. Exact CLI, private memo schema and proof boundaries: [LAUNCH_CERTIFICATION_PRIORITY.md](LAUNCH_CERTIFICATION_PRIORITY.md).

# BetterInstincts: download, bootstrap and play

Status: pre-alpha offline toolkit, not a certified playable Sims 4 mod. The one-click Windows entrypoint is Start-BetterInstincts.cmd. Windows and actual game proof must be independently observed; source and CI are not that proof.

## Play The Sims 4

Double-click [Start-BetterInstincts.cmd](../Start-BetterInstincts.cmd) on your
Windows Sims PC. It uses Git and Python 3.11+, gets the current `main` into
`%USERPROFILE%/dev/BetterInstincts`, and opens a uniquely identified install.
It preserves existing games and local changes. If a prerequisite, checkout
or game selection needs attention, the launcher prints the next step.

From an existing checkout on the Sims PC, use the container-backed CLI
with Docker in Linux-container mode. The container verifies source and
the Windows host owns the game lifecycle.

```powershell
py -3 -m scripts.play --json
py -3 -m scripts.play --game-exe "C:\path\to\The Sims 4\Game\Bin\TS4_x64.exe" --json
```

For development with a calibrated private context, use either entry point.

```powershell
.\Start-BetterInstincts.cmd --dev "C:\path\to\private-dev-context.json"
py -3 -m scripts.play --mode dev --save-context "C:\path\to\private-dev-context.json" --json
```

| Mode | Save target | What the current launcher can do |
| --- | --- | --- |
| Production | Most recently played save | Open Sims and identify the current process. Rank a complete supplied same-instance list with game-reported last-played times. Use the in-game Load Game list for the actual load while the production observer and loader are pending. |
| Dev | Oldest authorized disposable save for the selected household and run | Reuse the existing calibrated lab navigator when the observed executable build, registry, exact candidate and active player-first listener agree. A pending certification takes precedence. Independent save and household readback remains required. |

The dev context uses schema `betterinstincts.startup-save-context/v1` and
`startup_mode: dev`. Supply `run_id`, `game_version`,
`available_households`, `registry`, `navigation_profile` and
`session_id`. The registry and calibrated chosen-save profile are JSON
files next to the context. The profile must use the selected slot and
same registry. Use the existing household preference when more than one
household is in scope. Keep these files and template images private.
A production context uses the same schema with `startup_mode: production`
and provides the observed `process` from the launch receipt, source
`IN_GAME_LAST_PLAYED`, `inventory_complete: true`, `capture_ref`,
and `candidates` containing `save_id` and UTC `last_played_utc`.

The launcher treats a dispatch PID and a game PID independently. A
replacement or reused PID invalidates the in-flight action. The receipt
records the current process identity separately from any save result.
Exit 0 for play means it preserved an existing game. Exit 2 names the
remaining gate, including any manual save or readback step on a new
launch. Check `launch_state` to see whether dispatch already happened.
Use `python -m scripts.play --plan --json` for the Docker check without
launching Sims.

## Record any intervention

The launch output includes the receipt path under
`%LOCALAPPDATA%/BetterInstincts/runtime/play-receipts`. When a person or
agent has to complete a startup step, record it against the launch before
continuing. Use one row per completed step with distinct local evidence
references. Required but pending steps appear in `automation_gaps`.

```powershell
py -3 -m scripts.launch_receipt --receipt "C:\path\to\launch.json" --actor agent --stage production_save --step "Opened the observed latest save" --owner scripts/launch_save_route.py --before capture:before-picker --during capture:slot-selection --after capture:loaded-household
```

Each assistance entry is stored beside `launch.json` for the same run and
keeps the missing repository owner visible. Keep gameplay evidence and
operator-directed play separate from repository startup automation.

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
