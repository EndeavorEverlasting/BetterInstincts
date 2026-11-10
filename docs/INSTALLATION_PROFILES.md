# Installation-local profiles and settings

**Status:** offline configuration/GUI implementation, not a Sims gameplay or desktop-live certification. Canonical toggles: contracts/installation-profiles.v1.json; implementation: betterinstincts/installation_profiles.py. These profiles are independent of Sims personality (sim_profile.py), game-patch compatibility, save provenance, and installer manifests.

## User workflow

From the repo checkout:

    python -m scripts.instance_settings show
    python -m scripts.instance_settings profiles
    python -m scripts.instance_settings create gardening
    python -m scripts.instance_settings choose gardening
    python -m scripts.instance_settings set learning.hover_observations true
    python -m scripts.instance_settings reset learning.hover_observations
    python -m scripts.instance_settings gui

The installer GUI also has **Preferences**, available from a checkout containing the settings module. Opening the panel does not write anything. Toggling, creating or selecting a profile makes one explicit user-owned local change. All registered boolean settings are displayed in the panel; overrides are isolated by profile.

For an already active host session, enabling learning.hover_observations can opt in to one sanitized hover event through:

    python -m scripts.host_listener hover --session-id SESSION --event sanitized-event.json --use-active-profile

The listener still enforces its active-session and event validation gates. Its existing --explicit-opt-in one-off operator path is unchanged. Simply enabling a preference never starts sensing, captures input, clicks, or grants control.

**Integration truth:** learning.hover_observations is consumed by the opt-in hover CLI. Hotkey/cheat learning and other automation/privacy/UI flags are **stored preferences for future individual adapters**; they are not evidence of running input hooks, actual game capture, runtime host policy switches, or a completed Sim modification. The settings GUI is a functioning profile-management surface.

Windows location: LOCALAPPDATA/BetterInstincts/settings.v1.json.
Linux location: XDG_CONFIG_HOME/betterinstincts/settings.v1.json (default home/.config/betterinstincts/settings.v1.json). Stored independently of the managed installer app directory, git checkout and Sims saves; survives uninstall. No cloud sync, passive telemetry, autostart, scheduled task or background scan.

## Architecture and strategic choices

**P141 alternatives challenged:**
- Universal account/profile service: **REJECT** this slice; disproportionate identity/privacy architecture for local settings.
- Flat booleans inside bootstrap.py: **WEAKENED**; coupling to install/uninstall and no named profile isolation.
- Versioned local profile owner, canonical typed registry and explicit UI: **SELECTED**; reusable without moving gameplay state or weakening safety.
- Cloud synchronization: **DEFERRED** pending operator consent, trust model and demonstrated demand.

**P95 tested call-stack targets:**
1. User CLI/Tk action → validate profile/key/type → acquire local exclusive writer lock → validate preexisting JSON → apply the profile override → atomic replace → readback effective state.
2. Host hover CLI --use-active-profile → resolve effective hover toggle → existing observe_hover active-session admission → sanitized supplied event reducer → bounded evaluation. Existing --explicit-opt-in compatibility path remains.
3. Invalid profile, bad JSON/schema, symlink, oversize file, concurrent writer or replacement failure: fail closed; do not overwrite old preferences.

**P124 ownership:** JSON catalog is the only setting/default registry. Python profile module owns storage and validation; GUI/CLI own presentation; bootstrap links to the panel without owning its data; host listener remains event/consent owner. No daemon, new policy authority or duplicate engine.

**Trifecta:** P82 prototype/refinement and negative tests; P07 implementation/CI/merge; P08 real local GUI and Sims integration proof is still a separate gate. Offline checks cannot certify gameplay, app installation on the operator's workstation or a Sims game patch.

## Privacy and evolution

Preferences are not permissions. Mandatory save, player-presence, scene, version and minimum 15-second idle controls stay independent. Unknown settings/future schema versions are rejected rather than coerced or silently migrated. Local preferences are never included in repository commits, CI fixtures, screenshots or telemetry. New runtime consumers require explicit wiring and regression tests; settings alone never trigger collection.

**Lot floor maps (2026-11-10):** each installation profile owns a private floor object map under `households/<profile-id>/floors/<lot-key>.json` (computers, laptops, robotics workstations, avoid-notes, Order/spawn paths). Toggle `learning.lot_floor_map_auto` defaults **true** — when the host observes Build/Buy with `lot_floor_profile_id` + `lot_floor_key`, `on_build_mode_entered` ensures the skeleton. Agents populate via OBJECT_PICK_IDENTIFY / `python -m scripts.lot_floor_map ingest-parts-buy`. Never Sims saves; never repo/dist as canonical. See `contracts/lot-floor-map.v1.json`.

**Next proof gate:** local Windows/Linux settings GUI launch, persistence/rollback proof, then individually connect additional toggle consumers under their existing authority boundaries.
