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
visit each available Sim. It uses an observed computer's **Order → Purchase
Upgrade Parts** affordance. It tops up the five computer part types to
**99 per Sim's pocket inventory**, buying only the shortfall. The five types
are common, electronic, kitchen, plumbing and robot salvage. Portraits at
work, at school or otherwise unavailable are recorded and skipped. One Sim's
verified inventory and the household funds readback must settle before
moving on. A purchase must fit the approved run cap and the existing
household reserve. The workflow does not issue a save operation.

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

The remaining Windows engineering dependency is the exact-build native
observer and action binding under [issue #171](https://github.com/EndeavorEverlasting/BetterInstincts/issues/171).
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

| Operation | Required independent observation or effect |
| --- | --- |
| `observe` | Echo the current `observation_id` and return a new frame. Read back the save and requested scene from the current game. On the map, report the active household ID and corresponding lot ID. In Live Mode, report that same household and lot, pause state, the ordered roster, availability, selected Sim, pocket stock, and any current computer and picker evidence. |
| `open_active_lot`, `play_active_lot`, `pause_live` | Revalidate the current save, scene, active household and named lot before one action. |
| `select_portrait` | Use the shared native selection and readback port for the exact Sim ID. |
| `open_upgrade_parts` | Use the currently observed on-lot computer affordance and return the actor-bound empty picker, current revision, funds and all five observed unit prices. |
| `buy_upgrade_parts` | Revalidate that actor, computer and picker revision, exact quantities, full price and funds immediately before one native cart confirmation. Read back personal pocket stock and household funds. |

Before each effect, the bridge checks player authority and the supplied
input generation atomically with the requested action. Return its
`command_id` and `APPLIED` only for a correlated native acknowledgement.
The next observation independently includes `applied_command_id` and
fresh state. A changed generation or uncertain response leaves the pending
step in the launch receipt for reconciliation.

## Acceptance and terminal states

Run the same launcher on the exact Windows build with two available Sims
and one away. Preserve the process, save, active household and Live Mode
attestations. Record each selected recipient, actual pocket deltas and
household spend, and the skipped Sim's availability in the existing private
launch receipt. Repeat with player takeover and demonstrate owned binding
rollback. Use `python -m unittest tests.test_lab_upgrade_parts -v` for the
repository fixture before live certification.

`RESTOCK_VERIFIED` requires a fresh final roster and pocket observation
showing that all available portraits reached at least 99 of every part.
`NO_AVAILABLE_PORTRAITS` records that no purchases occurred because all
observed Sims were unavailable. A launch dispatch or menu opening is an
intermediate checkpoint. An unavailable host, unproved binding or uncertain
effect leaves the workflow incomplete with its exact gate in the receipt.
