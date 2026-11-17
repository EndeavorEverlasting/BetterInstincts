# Oldest lab save and household upgrade-parts restock

Start the Windows workflow with the repository launcher.

```bat
Start-BetterInstincts.cmd --upgrade-parts
```

The launcher clones canonical `main` when absent and fast-forwards a clean
canonical checkout before using its code. It launches the installed Sims 4
once and verifies the process ID, creation time, executable path and exact
version. An open Sims session is preserved.

The repository ranks the private lab registry by verified creation time and
loads the oldest eligible `LAB_DISPOSABLE` save for the current run. It
independently checks the map's single active household against that save's
bound household ID, selects the active lot, enters Live Mode and pauses.
There is no save or household picker prompt. Ambiguous dates, uncertain
identities, protected saves and a pending certification stop the route.

From the loaded lot, the controller uses the shared portrait chooser to
visit each available Sim. PS-0241 checks that switching, opening the picker,
and settling the purchase fit the Sim's work and needs window. The controller
starts with the earliest feasible deadline and keeps the selected Sim when
deadlines tie. It recalculates after a portrait change and again against
the current picker quote before buying. It uses an observed computer's **Order → Purchase
Upgrade Parts** affordance. It tops up the five computer part types to
**99 per Sim's pocket inventory**, buying only the shortfall. The five types
are common, electronic, kitchen, plumbing and robot salvage. Portraits at
work, at school or otherwise unavailable are recorded and skipped. One Sim's
verified inventory and the household funds readback must settle before
moving on. A purchase must fit the approved run cap and the existing
household reserve. The workflow does not issue a save operation.

## Recover a stale or locally modified checkout

If the original checkout is dirty, ahead of upstream, divergent, or too old
to contain this launcher, create a clean detached worktree and continue the
same run. Preserve the development branch, local commits, staged and unstaged
files, and ignored evidence. A branch cleanup decision is separate from live
certification. The batch launcher targets the canonical development path even
when started elsewhere, so call its Python entrypoint in the detached worktree.

Run this in PowerShell on the Windows Sims host from the original
BetterInstincts checkout. Use the current authorized run and its existing private
startup context. The worktree is for executable source. The original checkout
and runtime receipt directory still own their existing local evidence.

```powershell
$repo = git rev-parse --show-toplevel
if ($LASTEXITCODE -ne 0) { throw 'Open the original BetterInstincts checkout.' }
$origin = git -C $repo remote get-url origin
if ($LASTEXITCODE -ne 0 -or $origin -notin @(
    'https://github.com/EndeavorEverlasting/BetterInstincts.git',
    'git@github.com:EndeavorEverlasting/BetterInstincts.git'
)) { throw 'Verify the official BetterInstincts origin.' }

git -C $repo fetch --no-tags origin 'refs/heads/main:refs/remotes/origin/main'
if ($LASTEXITCODE -ne 0) { throw 'Fetch of BetterInstincts main failed.' }
$head = git -C $repo rev-parse --verify 'refs/remotes/origin/main^{commit}'
if ($LASTEXITCODE -ne 0 -or $head -cnotmatch '^[0-9a-f]{40}$') {
    throw 'Could not resolve the fetched main commit.'
}
$worktreeRoot = Join-Path $env:USERPROFILE 'dev\.worktrees\BetterInstincts'
New-Item -ItemType Directory -Path $worktreeRoot -Force -ErrorAction Stop | Out-Null
$worktree = Join-Path $worktreeRoot ('lab-restock-' + [guid]::NewGuid().ToString('N'))
git -C $repo worktree add --detach $worktree $head
if ($LASTEXITCODE -ne 0) { throw 'Could not create the lab restock worktree.' }
$actualHead = git -C $worktree rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $actualHead -cne $head) { throw 'Worktree commit mismatch.' }
$changes = git -C $worktree --no-optional-locks status --porcelain --untracked-files=all
if ($LASTEXITCODE -ne 0 -or $changes) { throw 'Worktree must start clean.' }

Push-Location -LiteralPath $worktree -ErrorAction Stop
try {
    py -3 -m scripts.play --native-start --upgrade-parts --checkout-head $head --json
    $playExit = $LASTEXITCODE
} finally {
    Pop-Location
}
```

Read the returned JSON, including `stage`, `reason`, `checkout_head`, and
`receipt` when available. Continue at the first unmet gate on the Windows host.
Recover accessible startup, registry, calibration, and bridge evidence before
asking for operator input. Preserve an open game and follow the receipt for an
active certification. If the binding is missing or fails capabilities, continue
with the exact-build binding owner below. Keep any in-flight purchase receipt
for reconciliation before a retry. When the run no longer needs the worktree,
remove only that worktree using `git -C $repo worktree remove $worktree`.

## Local setup and exact-build continuation

The launcher automatically reads
`%LOCALAPPDATA%\BetterInstincts\runtime\lab-upgrade-parts\startup.json`.
Use the existing `betterinstincts.startup-save-context/v1` schema with
`startup_mode: dev`. Keep the existing private registry, current authorized
run ID and exact game version. The launcher opens and closes its own bounded
listener for the existing calibrated save-menu lease. Set
`navigation_profiles` to map each eligible slot ID to its local calibrated
chosen-save profile filename. A single `navigation_profile` is also
supported. Profile and registry identity are checked against the actual
ranked slot; changing the oldest slot never silently reuses an old profile.
Set `approved_spend_cap` to the run's authorized total in simoleons.

The Windows dependency is an exact-build native observer and action binding.
[Issue #171](https://github.com/EndeavorEverlasting/BetterInstincts/issues/171)
provides the native API discovery context. Its closed issue status carries
no restock observation.
`native_upgrade_parts` in the private context names a same-folder
`bridge` executable, its `sha256`, the exact `game_version` and a local
`binding_ref` from that source review. The launcher checks the binding
and its capabilities before opening the save. This handoff includes the
controller and protocol. The Windows observer/binding still needs to be
implemented and certified against the installed game.

## Native binding protocol

`scripts/lab_upgrade_parts.py` owns the protocol and the terminal result.
The local bridge accepts one `betterinstincts.lab-upgrade-parts-native/v1`
JSON request on standard input and returns one bounded JSON response on
standard output. Every response echoes the protocol and the exact process,
run, save and household scope. At `capabilities`, return
`NATIVE_BINDING_READY` and the supported operation names only for the
currently attached exact build.
Include `restock_planning: "betterinstincts.lab-upgrade-parts-planning/v1"`
in the capabilities reply when capture-bound timing evidence is implemented.

| Operation | Required independent observation or effect |
| --- | --- |
| `observe` | Echo the current `observation_id` and return a new frame. Read back the save and requested scene from the current game. On the map, report the active household ID and corresponding lot ID. In Live Mode, report that same household and lot, pause state, the ordered roster, availability, selected Sim, pocket stock, and any current computer and picker evidence. |
| `open_active_lot`, `play_active_lot`, `pause_live` | Revalidate the current save, scene, active household and named lot before one action. |
| `select_portrait` | Use the shared native selection and readback port for the exact Sim ID. |
| `open_upgrade_parts` | Use the currently observed on-lot computer affordance and return the actor-bound empty picker, current revision, funds and all five observed unit prices. |
| `buy_upgrade_parts` | Immediately before one confirmation, revalidate the actor, computer, picker revision, exact quantities, full price, funds and `expected_pocket_counts`. Revalidate the timing, queue and needs evidence attached to the supplied capture. Read back personal pocket stock and household funds. |

For each available Sim who needs parts, return `restock_timing` in its
portrait row on each qualifying Live frame. Bind `capture` to the enclosing
frame. From the exact build, supply `queue_verified`, `player_directed`,
`needs_safe`, `minutes_until_work`, `minutes_until_need_floor`,
`reserve_minutes`, and the conservative positive simulation-minute bounds
`switch_upper_minutes`, `picker_upper_minutes`, and `buy_upper_minutes`.
Use traceable local timing calibration for the applicable operations and
observe current work and needs state. Pause freezes the current game clock
and is not evidence of an unlimited safe window. Leave an unproved field
unqualified. The controller holds any chain whose full remaining path
cannot fit. If necessary, recover calibration or the native read source
before a live attempt. Keep local EA references and raw data private.

Before each effect, the bridge checks player authority and the supplied
input generation atomically with the requested action. Return its
`command_id` and `APPLIED` only for a correlated native acknowledgement.
The next observation independently includes `applied_command_id` and
fresh state. A changed generation or uncertain response leaves the pending
step in the launch receipt for reconciliation.

## Acceptance and terminal states

The Windows agent owns the run from bootstrap through receipt. Read the
checkout recovery above, run the focused repository fixture, execute the
launcher, and continue at its first unproved gate. If the binding is absent,
inspect the installed exact-build EA source read-only and implement the
needed native ports under the [native gameplay authority](../NATIVE_GAMEPLAY_ARCHITECTURE.md).
Start by proving process attachment and a read-only observation of the
current save and actor. Get that evidence before enabling any effect.
Use the oldest eligible slot and the map's active household directly.
Any manually assisted outcome has a separate assistance receipt.

On the exact Windows build, use at least two available Sims and one away.
Where the lab state permits, have a later portrait with a shorter feasible
window than the selected one. The private launch receipt must show the first
planner comparison, the target different from the selected Sim, the actual
selected-portrait readback, each latest quote, the pocket deltas and actual
household debits. Show final stock for every part for every available Sim,
plus the skipped Sim and reason. Use a fresh matched disposable run to
verify player takeover and that an unsettled purchase cannot replay.
Preserve the evidence, demonstrate owned binding rollback, and record
P08 only after the functional run and protected control are observed.
`python -m unittest tests.test_lab_upgrade_parts -v` runs the repository
fixture.

If a replan holds at an empty picker, keep the game at that observed state
and retain the quote in the receipt. The Windows native binding owner can
inspect the current picker and determine its safe dismissal. An uncertain
cart needs independent inventory and funds reconciliation first. The normal
launcher preserves running sessions, so relaunching is not a resume action.

`RESTOCK_VERIFIED` requires a fresh final roster and pocket observation
showing that all available portraits reached at least 99 of every part.
`NO_AVAILABLE_PORTRAITS` records that no purchases occurred because all
observed Sims were unavailable. A launch dispatch or menu opening is an
intermediate checkpoint. An unavailable host, unproved binding or uncertain
effect leaves the workflow incomplete with its exact gate in the receipt.
