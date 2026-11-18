# Semantic save selection

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
