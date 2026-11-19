# Semantic save selection

The profile shortcut and Settings Play delegate to the existing `scripts.play`
CLI. Run `python -m scripts.play --plan --profile-launch --json` to verify
startup source. Add `--container-engine podman` for a Podman trial. Only the
Windows host reads the local profile and uses the picker and native startup
binding. Record the container plan and the game handoff independently on the
Windows trial host.

## Private startup context

Extend the existing `betterinstincts.startup-save-context/v1` with
`save_catalog`, supplied by the local Windows observation owner. Use a
fresh, complete menu inventory for the exact observed process. The catalog
can model multiple households per slot. The loader can use a catalog
captured after startup while the same process is at the main menu.

- Catalog fields are `schema: betterinstincts.startup-save-catalog/v1`,
  `process` (PID, creation ticks, executable and exact game version),
  `source: IN_GAME_SAVE_INVENTORY`, `scene: MAIN_MENU`,
  `inventory_complete: true`, `capture_ref`, `observed_at_unix` and
  `saves`. Time is UTC Unix seconds, with a two-minute validity window.
- Each save carries `save_id` (the private registry key), `slot`
  (canonical `Slot_XXXXXXXX`), the game-visible `save_name`,
  `last_played_utc` when used in production, and `households`. Use an
  independently verified title-to-slot observation.
- Household rows carry `household_id`, `household_name`, and
  `members` with stable `sim_id` and game-visible `sim_name`.
  Select a household by label or exact ID when labels collide. Roster
  presence is separate from current availability in Live Mode.
- Dev can set `selection.household_name`, `household_id`,
  `expected_save_name`, `minimum_members`, and `required_members`.
  CLI options on `scripts.play` override only the corresponding
  fields. The expected title may help identify a household when its
  observed roster is unambiguous. It must match the oldest authorized
  roster match. A source-qualified named slot that needs current-run
  registration is reported as `observed_target`.
- Keep the existing same-folder `registry`, current authorized
  `run_id`, `game_version`, and `session_id` fields. The calibrated
  `navigation_profile` or `navigation_profiles[save_id]` must bind
  `selected_save_id` and `selected_slot` to the winning slot.
  Title and roster observations provide selection evidence. The existing
  lab register supplies authority. Keep the context and evidence local.

## Route behavior

Dev ranks current-run lab-disposable candidates after applying household
and roster qualification. A valid certification still takes precedence.
Production determines the newest title by independently observed
last-played time. When that slot is a currently authorized lab save,
it can use the calibrated chosen-save adapter. Otherwise the launcher
leaves the newest candidate for the player. The explicitly protected
continuation slot remains unopened. Ties, wrong process, changes of exact
build, age ambiguity and uncertain binding hold the relevant route.

For the [semantic dev restock route](../../docs/handoff/BI-OLDEST-LAB-RESTOCK.md#restock-a-named-dev-save),
use `--upgrade-parts` with an explicit private `--save-context` and the
same title, household and roster inputs. The startup bridge supplies a fresh
process-bound catalog through its read-only operation. The restock bridge
checks the loaded slot and roster, fills each available Sim's inventory to
the target and hands the session to the native responder after settlement.
The standard semantic dev command below ends at the responder's first
observed decision without buying parts.

## Proof and continuation

Sixth Gear selected one semantic admission layer in the existing launcher.
Matching titles without slot identities would be ambiguous. Sorting disk
files would lose game recency and household evidence. A second loader
would duplicate the existing player and template gates. The selected
catalog reuses chronology, lab authorization and the one admitted
navigation path. Source validation exercises both modes and the negative
paths. P08 remains `BLOCKED_LOCAL_GAME_ACCESS`.

On Windows, capture the chosen save title, slot, exact build and all
required Sim identities from a current menu observation before binding
the intended trial. Re-observe the selected household and all required
portraits after the save opens. Confirm that the existing player queue
survives and verify the [microsystem handoff](BI-MICROSYSTEM-HANDOFF.md).
For production, verify the newest title and independently observe the
save that loaded. Record game dispatch, save readback, and portrait
switch effect as separate milestones.

## Native startup binding

`scripts.play` can consume a fresh catalog and continue the same launch into
Live Mode when the exact-build Windows binding is configured. Add
`native_startup` to the private startup context with `bridge` (same-folder
`.exe` filename), its `sha256`, exact `game_version`, and local `binding_ref`.
Retain the current run's lab registry and calibrated chosen-save profile for
the selected slot. The checked-in controller supplies a protocol for the
local binding. Windows and the installed copy of The Sims 4 supply live
evidence for that binding.

The bridge accepts JSON on stdin and returns a bounded JSON response on
stdout. Echo `protocol: betterinstincts.native-startup/v1` and `scope`
on every response. Scope contains the full observed process identity,
`run_id`, and a unique `startup_id`. Use exact-build, source-inspected EA
ports, with local evidence for process attachment, observation and effects.
The startup receipt and captures stay on the Windows host.

| Operation | Native response |
| --- | --- |
| `capabilities` | `state: NATIVE_BINDING_READY` and `read_save_catalog`, `observe`, `open_active_lot`, and `play_active_lot` for standard Play. For semantic restock, only `read_save_catalog` is required. Profile Play can use the two additional optional ports below. |
| `read_save_catalog` | Echo `observation_id`. Wait within the request deadline for the current main-menu inventory. Return `MAIN_MENU_OBSERVED` with the `catalog` described above, or `EXISTING_SESSION_IN_PROGRESS` if the attached process is already in a loaded session. |
| `observe` | Echo `observation_id` and return a fresh `frame` with a distinct `capture`, `save_id`, `slot`, `scene`, `player_idle_verified`, and `input_generation`. Map frames provide `active_households` with household and lot IDs. `LOT_DETAILS` adds `selected_lot_id`. Live frames provide `household_id`, `lot_id`, an ordered `roster` of stable Sim IDs and `selected` Sim. Effect readbacks correlate `applied_command_id`. |
| `open_active_lot` | Verify the exact save, source map, household, lot, current capture and player input generation. Select the active lot once. |
| `play_active_lot` | Check the lot card, exact household and player generation. Enter the lot once and release startup control to the installed native responder. |
| `load_selected_save` | With the fresh main-menu `capture`, bound target, and `minimum_idle_ms`, recheck process, menu position, player-idle threshold and the exact target before issuing one native load. The first map or Live readback must correlate `applied_command_id` to this separate load command. |
| `select_household` | Map observations add `selectable_households` with exact household and lot IDs. Recheck the map, target and input generation before selecting the one requested household. Readback must correlate the command and show that household and lot as active. |

Profile Play refreshes the process-bound catalog after the chooser and
inactivity wait. Production ranks the newest save globally and offers
households in that save. Developer mode uses the oldest authorized disposable
save matching the chosen household and any configured roster constraints. An
exact household ID picked or remembered by the player supersedes an older
household name in the private dev context. Its save-title and roster
constraints still apply. Multiple households without a preference, or a
remembered household missing from the catalog, open the picker. The
existing calibrated load path remains available if the adapter lacks
`load_selected_save`. A missing household-selection port or uncertain
submitted effect leaves a typed hold on the current session.
Profile-driven native effects use the shared input-owner lease and a fresh
idle check with the chosen minimum. The adapter also receives
`minimum_idle_ms` on each profile-driven native effect request. If a native
load enters Live Mode directly, its command ID also anchors the responder's
entry readback. The launch receipt carries the separate `native_save_load`
observation and acknowledgement state.

Before an effect, confirm fresh independent scene and idle evidence and
atomically recheck scope and player priority at dispatch. Acknowledge with
`command_id` and `status: APPLIED` only after an observed native effect.
The launcher writes pending intent before dispatch and checks the matching
transition in a subsequent observation. Keep uncertain intent for read-only
reconciliation. Use `startup_binding.scope` from the existing receipt for
the read-only `observe` request. It contains the bridge's authorized run and
startup ID, which differ from the receipt's own launch ID. Check the current
process and binding against that scope and `startup_binding.sha256`. Compare
the new `applied_command_id`, scene and target to `startup_handoff.pending`.
The receipt already includes `startup_binding.catalog_capture` and the
selected `save_route` before navigation. A separate attempt cannot borrow the
old startup ID or automatically replay a command. The launcher leaves an
existing loaded session in place.

The native responder observation has `behavior_owner: NATIVE_RESPONDER`,
`playing: true`, and a `responder` with `registered: true`, the `startup_id`,
and `entry_command_id` from the lot entry (null for direct Live Mode).
Report `decision_state: DECISION_OBSERVED` only after the registered
`InstalledPlayerRuntime.cycle` actually makes a normal decision in the
startup scope. Supply its `decision_ref` and the current `decision_capture`.
A normal decision can leave the game alone. Play independently records
the selected save, Live household, responder control and a later decision.

### Windows acceptance

Check the existing certification checkout against current official `main`.
For a stale checkout, use the [isolated checkout procedure](../../docs/handoff/BI-OLDEST-LAB-RESTOCK.md#recover-a-stale-or-locally-modified-checkout)
through its clean worktree check. Use the semantic dev command below from
that checkout. Carry forward the already selected title, household and
roster from private run context or the operator's prior instruction. The
live catalog must independently verify which slot and Sims match them.

If the agent receives `OPERATOR_DESKTOP_BOUNDARY`, use its permitted
read-only diagnostics and hand the single blocking Windows launch to the
operator or an independently approved scoped Windows runner. The project
hook stays active. Run offline fixtures in CI or an approved sandbox.
The operator can run the reviewed command in their own PowerShell from
the verified checkout, with the existing private context path:

```powershell
py -3 -m scripts.play --native-start --mode dev --save-context $privateContext --save-name $expectedTitle --minimum-household-members 3 --household-member $firstSim --household-member $secondSim --household-member $thirdSim --json
```

Set the variables from the authorized trial. Add `--household` for an
already chosen household label or `--household-id` if labels collide.
Use the private receipt's first `stage` and `reason` to continue. The
startup bridge can inspect the main menu of an already-running game.
Preserve a loaded session and use its existing receipt. If no catalog
binding exists, a read-only Load Game card can corroborate visible labels.
The exact-build observer still owns title-to-slot and roster binding.
When the target is observed but unregistered, retain `observed_target`
and resolve current-run lab authorization before dispatch. Keep real
labels, identities, capture data and local paths out of Git.

Use the oldest authorized matching save and the intended roster. Confirm the
receipt reaches `NATIVE_RESPONDER_DECISION_OBSERVED` with distinct captures.
Repeat production with an authorized newest lab candidate. Verify both
player takeover during map entry and a production run with a protected
newest candidate. Reconcile a pending command against the current game
before any retry. The offline fixture for the chain is
`python -m unittest tests.test_startup_handoff -v`. The local Windows binding,
actual control transfer, and game callback decision require live validation.
