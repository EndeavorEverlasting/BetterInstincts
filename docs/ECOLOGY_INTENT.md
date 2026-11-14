# PS-0241 — Ecology planning/play and per-Sim intent continuity

**Status:** source implementation and offline test candidate. **Not an installed Sims 4
mod; native auto-activation and in-game certification are still open in
[issue #171](https://github.com/EndeavorEverlasting/BetterInstincts/issues/171).**
The local agent reported game patch \`1.121.361.1020\`, an empty Mods folder
except \`Resource.cfg\`, and a separate operator-observed manual Super Fertilizer
pickup and Sixam Mosquito Trap effect. Neither this source branch nor that
manual trial proves automatic in-game execution.

## Parent acceptance and division of responsibility

The eventual installed \`.ts4script\` or \`.package\` must be the live engine.
Once a user installs the supported mod and enables scripts in the game, the
**game itself** must drive the ecology workflow without a desktop agent,
background daemon or separate click launcher. Preserve player control,
personality, priorities, emergency needs, work, household autonomy settings,
and user saves.

The first reusable policy seam is
\`betterinstincts/ecology_intent.py\`. Existing
\`gardening_service.py\`, \`fertilizer_workflow.py\`,
\`task_continuity.py\` and \`queue_supervision.py\` retain their owners.
This reducer is not a second game actuator. The source-only adapter
contract is:

\`\`\`text
version-pinned native EA event observation
  -> verified per-Sim/household/lot/capture state
  -> in-memory per-Sim intent reducer (PLANNING if paused, PLAY otherwise)
  -> one exact target proposal, never a desktop input permission
  -> separately reviewed native hook admits one game queue action
  -> independent game queue / inventory / plant outcome observation
  -> reconcile same persistent intent and advance only with proof
\`\`\`

## Invariants implemented in source

- **No active portrait assumption.** Intents are keyed by exact Sim identity,
  not HUD position or active portrait. The bounded batch handles up to 32
  distinct identities and has no UI rotation or game effect.
- **Paused is PLANNING.** A serializable \`PICKUP -> FERTILIZE\` plan survives
  pause/Play transitions, later observations and portrait switching.
  Planning emits no native queue write.
- **Play is proposal, not permission.** At most one step per new capture is
  proposed. Awaited steps are not blindly reissued; matching queued steps
  prevent duplicates. Unknown-origin, autonomous, or player-owned queue
  entries are never cancelled.
- **Reconcile interruptions.** A native, provenance-bound independent
  \`NATIVE_INTERRUPTED\` receipt can release an interrupted step for a later
  re-proposal. Silence or a missing queue row cannot. Player activity
  suppresses any new proposal without destroying the intent.
- **Independent pickup proof.** A queue acknowledgement is not a stock
  increase. FERTILIZE is allowed in the policy only after previously
  held inventory or a fresh, independently witnessed positive change in the
  selected Sim's personal stock. Verified native action outcome and plant
  \`DEPLETED -> GOOD\` with consumed stock are required to call this
  two-step trial complete.
- **Safety budget:** \`available = min(earliest measured six-need floor,
  work deadline - 30 simulated minutes)\`. Both estimated action upper
  durations are required, multiplied by 1.25; unknowns or insufficient
  margins defer the garden without discarding the goal. The 30-minute
  reserve and 1.25 multiplier are **conservative policy defaults**, not
  calibrated Sims facts.
- **Asynchronous telemetry:** future native events can trigger bounded
  observation/reconciliation without parallel game mutations or global
  frame-by-frame polling. The current implementation does not start a
  background listener or scrape game files.

## Mathematics: deterministic baseline versus bounded GP

\`betterinstincts/ecology_forecast.py\` contains a pure,
standard-library Matérn-3/2 Gaussian-process duration comparator.
It operates only on 10–24 same-patch, same-action,
proof-qualified, uniquely captured completion samples.
It uses chronological held-out observations, tests absolute
prediction error against the median-duration baseline and requires
two-standard-deviation upper-bound coverage. Uncertain/poor/discontinuous
series fall back to the declared deterministic upper time. A successful GP
must improve held-out MAE by at least 10%, cover every held-out duration,
and yield a useful shorter upper bound, never below 80% of the previously
attested deterministic upper. No numerical fit grants any EA queue authority.

Cholesky computation is \`O(n^3)\` and bounded to \`n <= 24\`.
There is **no telemetry storage, learning daemon, task thread or GPU
dependency**. Native source must prove an activity-context feature
before GP results are entrusted with planning a live time window.

## Mandatory native installation and certification gate

1. In a user-authorized disposable save, inspect the **installed**
   \`1.121.361.1020\` EA queue, needs, clock, inventory, household and
   interaction/event interfaces **read-only**. Record actual source file,
   game patch, embedded Python version, callable signatures, native
   hook identifiers and correlation between queue origin and player intent.
   This must be local source evidence, not inferred API names.
2. Evaluate whether narrow XML tuning suffices. If not, implement a
   version-correct EA-script bridge that imports/runs the reducer logic
   using syntax and dependencies compatible with Sims' embedded interpreter,
   **not** the workstation's Python 3.11+ automatically.
3. Build a reversible, source-owned \`.ts4script\` archive with
   game-compatible bytecode (community references report Python 3.7
   \`.pyc\`; confirm against the installed EA runtime before building).
   Install only in the explicitly verified Mods path, with script mods
   enabled; preserve existing \`Resource.cfg\`, other Mods and saves.
   Never edit EA original archives. Emit file hash and owned rollback
   manifest. Merely placing an unverified zip in Mods is not an activation
   or auto-event-hook proof.
4. Compare game-native vanilla versus modified in a disposable reset
   state: paused planning, unpause and pickup, inventory gain, exact
   fertilization and plant-state result, autonomous queue interruption,
   player preemption, urgent need, imminent work, second household Sim,
   no-duplicate/replay cases and another unaffected behavior control.
5. Record script-load/registration evidence, live callback/event,
   queue before/after, needs/work deadline, independent inventory/plant
   changes and performance. Uninstall the owned package and verify
   unchanged saves and restored vanilla behavior. New patch requires a
   fresh compatible build and trial.

Public cross-check references:
[TS4 script mod format](https://thesims4moddersreference.org/reference/file-types/),
[Python 3.7 bytecode build example](https://github.com/ExtReMLapin/ts4-unofficial-fixes),
[modern loader troubleshooting](https://github.com/dnavaria/sims4ai/blob/master/docs/TROUBLESHOOTING.md).

## Current proof states

- **Source:** implementation committed on feature branch; CI status separately verified.
- **Native package:** not built / not installed.
- **Automatically triggered game events:** not observed.
- **Earlier manual garden transfer and plant effect:** operator/local-agent reported
  only, not the mod doing it.
- **End-to-end / rollback:** not run against the game from GitHub.

The first exact native successor remains issue #171. The draft
[PR #252](https://github.com/EndeavorEverlasting/BetterInstincts/pull/252)
adds separate garden-specific capture-bound time gating and must be
reconciled after its writer completes; this source feature does not
overwrite its branch or claim its unmerged changes are on \`main\`.


## Reversible package builder (available in source)

\`scripts/native_ecology_bundle.py\` has three commands. It intentionally
refuses to build until the local agent has produced a verified
\`BetterInstincts_Ecology.py\` game-native entrypoint and source-bound
\`betterinstincts.native-ecology-hook-proof/v1\` JSON receipt.
The receipt must identify the exact game build, installed EA source,
event and queue signatures, auto-import signature, player-preemption
evidence, source SHA-256 and Python 3.7 compatibility.

\`\`\`text
python -m scripts.native_ecology_bundle build --python37 "VERIFIED_PYTHON37" --source "VERIFIED_BetterInstincts_Ecology.py" --hook-proof "LOCAL_HOOK_PROOF.json" --output-dir "NEW_STAGING_DIR" --game-build "1.121.361.1020"

python -m scripts.native_ecology_bundle install --mods-dir "VERIFIED_SIMS_MODS_DIR" --package "STAGING/BetterInstincts_Ecology.ts4script" --manifest "STAGING/BetterInstincts_Ecology.ownership.json" --confirm-game-closed

python -m scripts.native_ecology_bundle uninstall --mods-dir "VERIFIED_SIMS_MODS_DIR" --confirm-game-closed
\`\`\`

The game must actually be closed before installation and removal;
\`--confirm-game-closed\` records an assertion, not independent
process-state proof. The install checks \`Resource.cfg\`, installs only
its namespaced archive and ownership manifest, verifies its hash, and
refuses to overwrite other Mods or delete modified files. No save, OS
setting, activation preference, game file or EA asset is altered.

**Remaining blocker:** a locally inspected and tested
\`BetterInstincts_Ecology.py\` that automatically attaches to the game's
native event system and bridges native outcomes to the reducer. The
workstation Python 3.11+ policy is not itself a Python 3.7
game-loadable module. The local adapter must port compatible logic,
compile, install and independently observe game import/events before
claiming activation.
