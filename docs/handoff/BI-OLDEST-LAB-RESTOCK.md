# Oldest lab save, household restock and native responder handoff

The Windows agent runs the workflow using the official checkout and the
repository launcher when the host permits it. For a named save and roster,
use the [semantic dev command](#restock-a-named-dev-save). The default command
below chooses the oldest eligible lab save. On a first run, clone canonical
`main` to the bootstrapper's normal checkout location.

```powershell
$repo = Join-Path $env:USERPROFILE 'dev\BetterInstincts'
if (-not (Test-Path -LiteralPath $repo)) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $repo) -Force -ErrorAction Stop | Out-Null
    git clone --branch main -- https://github.com/EndeavorEverlasting/BetterInstincts.git $repo
    if ($LASTEXITCODE -ne 0) { throw 'Could not clone BetterInstincts main.' }
}
Set-Location -LiteralPath $repo
.\Start-BetterInstincts.cmd --upgrade-parts
```

An existing dirty or divergent development copy uses the isolated checkout
procedure below. The launcher also clones canonical `main` when absent
and fast-forwards a clean canonical checkout before using its code. It launches the installed Sims 4
once and verifies the process ID, creation time, executable path and exact
version. An already-loaded Sims session is preserved.

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

The bridge claims exclusive restock control on the verified map. The
installed native responder waits while this control is held. When all
available portraits are verified at the target and the picker is closed,
the controller orders one native transfer to the registered responder
and resumes Play in the same save and lot. The native responder owns
subsequent decisions. The bootstrapper reads back ownership and waits for
an independently observed decision. The same transfer can follow a
verified no-available-portraits result, which remains a distinct outcome.

## Restock a named dev save

From a verified checkout on the Windows Sims host, use the authorized private
startup context and the trial's exact game-visible names. This example uses
synthetic labels and a placeholder context path.

```powershell
py -3 -m scripts.play --native-start --upgrade-parts `
    --save-context 'C:\Private\startup.json' --save-name 'Example Lab Save' `
    --household 'Example Household' --minimum-household-members 3 `
    --household-member 'Example Sim A' --household-member 'Example Sim B' `
    --household-member 'Example Sim C' --json
```

`--upgrade-parts` implies dev mode. Selection flags require an explicit
`--save-context`. Use `--household-id` if an already chosen household label
is ambiguous. When starting in an isolated worktree, run this command from
that checkout and pass its verified SHA as `--checkout-head`.

Configure the exact-build `native_startup` menu observer and
`native_upgrade_parts` controller binding in the same private context. In
restock mode `native_startup` only needs `capabilities` and
`read_save_catalog`. It can admit an already-running game at the main menu.
A loaded session stays in place. The catalog ties the title and roster to the
current process and slot. The expected title must match the oldest authorized
disposable candidate for the requested household and roster. The calibrated
save-menu path opens that slot. The restock bridge verifies the actual slot
and Live roster against the catalog before switching portraits or purchasing.

Read the first failed `stage` and `reason` from the private launch receipt.
Keep the existing session and reconcile any pending command. If the project
hook denies the agent launch, follow the
[guarded Windows acceptance procedure](../../plans/active/BI-SEMANTIC-SAVE-LAUNCH.md#windows-acceptance).

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
`navigation_profiles` to map each eligible registry `save_id` to its local
calibrated chosen-save profile filename. A single `navigation_profile` is also
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
Also include
`responder_handoff: "betterinstincts.lab-restock-responder-handoff/v1"`
when the binding can enforce exclusive restock control and observe a
decision from the installed responder.

| Operation | Required independent observation or effect |
| --- | --- |
| `observe` | Echo the current `observation_id` and return a new frame. Read back the save, scene and authoritative `behavior_owner`. For a semantic run, include the observed `slot` on each frame. On the map report the active household and lot IDs. In Live Mode report the same scope, pause state, ordered roster, availability, selected Sim, pocket stock, computer and picker evidence. Report a closed picker as `picker: null`. |
| `claim_restock_control` | Acquire the exact process, save, run, household and lot lease on the verified map. Deny active player control or unresolved work from another owner. Read back `behavior_owner: RESTOCK`. The registered adapter sets `Frame.restock_has_control` from the same authority and rechecks ownership atomically before applying a native effect. |
| `open_active_lot`, `play_active_lot`, `pause_live` | Revalidate the current save, scene, active household and named lot before one action. |
| `select_portrait` | Use the shared native selection and readback port for the exact Sim ID. |
| `open_upgrade_parts` | Use the currently observed on-lot computer affordance and return the actor-bound empty picker, current revision, funds and all five observed unit prices. |
| `buy_upgrade_parts` | Immediately before one confirmation, revalidate the actor, computer, picker revision, exact quantities, full price, funds and `expected_pocket_counts`. Revalidate the timing, queue and needs evidence attached to the supplied capture. Read back personal pocket stock and household funds. |
| `handoff_to_responder` | Bind to the last verified paused Live capture and lot. Atomically check the restock lease, input generation, registered exact-build callback, closed picker and settled transactions, then resume Play and give control to the existing native responder. Return correlated acknowledgement only after that transition. |

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

On the first post-transfer frame, report `paused: false`,
`behavior_owner: NATIVE_RESPONDER` and `responder.registered: true` with
`responder.handoff_command_id` matching the transfer. Subsequent
observations keep these bindings. After the registered
`InstalledPlayerRuntime.cycle` evaluates a normal decision, report
`responder.decision_state: DECISION_OBSERVED`, an opaque `decision_ref`
and `decision_capture` matching the fresh observation. A decision may
leave the game alone. A listener registration or transfer acknowledgement
alone leaves decision proof open. The launcher sends no effects after the
transfer and waits for up to four subsequent observations.

## Acceptance and terminal states

The Windows agent owns continuity from bootstrap through receipt. Run the
focused repository fixture in CI or an independently approved sandbox.
Use the checkout recovery above and continue at the first unproved gate.
If the agent shell is denied, use the operator-owned invocation described
in [Windows acceptance](../../plans/active/BI-SEMANTIC-SAVE-LAUNCH.md#windows-acceptance),
with the appropriate restock command above. Use standard semantic dev Play
for a trial that ends at the first responder decision without restocking.
If the binding is absent,
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
verify player takeover and that an unsettled purchase or transfer cannot
replay. In the functional run show the ordered sequence
`RESTOCK_VERIFIED` → `RESPONDER_CONTROL_OBSERVED` →
`NATIVE_RESPONDER_DECISION_OBSERVED`. Capture a native decision and its
independent in-game result when the fixture presents an eligible action.
Check that the same installed responder yields to player input.
Preserve the evidence, demonstrate owned binding rollback, and record
P08 only after the functional run and protected control are observed.
`python -m unittest tests.test_lab_upgrade_parts -v` runs the repository
fixture.

If a replan holds at an empty picker, keep the game at that observed state
and retain the quote in the receipt. The Windows native binding owner can
inspect the current picker and determine its safe dismissal. An uncertain
cart needs independent inventory and funds reconciliation first. The normal
launcher preserves running sessions, so relaunching is not a resume action.
For a semantic restock, recover `restock_binding.scope`, `sha256` and
`catalog_capture` from the existing private receipt. Verify the same process
and bridge hash before a read-only observation. Correlate fresh slot, roster
and effect evidence against `restock.pending` and its command ID before any
retry. Reconcile pocket counts and household funds for a pending purchase.
If the transfer is pending or the first decision is unobserved, continue
with the existing receipt and native binding in the same running session.
An observed transfer with a missing decision calls for read-only callback
inspection using the correlated handoff command ID.

`RESTOCK_VERIFIED` requires a fresh final roster and pocket observation
showing that all available portraits reached at least 99 of every part.
`NO_AVAILABLE_PORTRAITS` records that no purchases occurred because all
observed Sims were unavailable. A launch dispatch or menu opening is an
intermediate checkpoint. An unavailable host, unproved binding or uncertain
effect leaves the workflow incomplete with its exact gate in the receipt.
