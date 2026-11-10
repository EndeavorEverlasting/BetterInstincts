# Individual profiles and household identity (public portability)

BetterInstincts is a reusable program, **not a snapshot of any one player's Sims**. Public contracts, source and regression fixtures describe Sims by generic roles, stable game/observer identities and capabilities, never by an owner's Sim names or household composition.

## The identity boundaries

| Owner | What it knows | What it must never assume |
| --- | --- | --- |
| Product code and contracts | Need/skill/career semantics, action and safety policies | A player's characters, lot, saves, portrait count or preferences |
| Local installation profile | Optional user-chosen preference toggles; existing `default`/named settings | A profile maps to one Sim or can authorize game input |
| Local save | An opaque observed save identity, only on that user's machine | Another user's save has the same Sims or IDs |
| Local household | Opaque observed household identity in that save; current portrait roster | Names, fixed N or portrait order remain constant |
| Local Sim/portrait | Stable locally observed identity bound to the current household; observed traits, needs, skills | Display name is unique, stable or safe as an identity key |
| Live execution | Foreground player-first screen admission and independently re-observed target | A typed CLI roster, dispatched cheat or unit test equals live proof |

The canonical `betterinstincts.household-scope/v1` binder takes `profile_id`, `save_key`, `household_key` and an ordered set of locally attested stable `roster_keys`. It creates deterministic opaque scope/member keys and a separate roster fingerprint; this is **not itself an observer**. No screenshot capture or game scanning is enabled by calling it. If the roster changes or its observed identity cannot be proven, the live worker must stop and reconcile rather than map a previous member's progress onto the new Sim.

The profile owner is `betterinstincts/installation_profiles.py`; the scope policy owner is `betterinstincts/household_judgment.py`; the skill-progress owner remains `betterinstincts/diy_skill_force.py`. The `scripts/diy_skill_force.py` entrypoint composes them, without introducing a second competing profile store.

## Local-only storage and opt-in workflow

The scoped completion ledger lives under the existing user configuration parent:

- Windows: `%LOCALAPPDATA%/BetterInstincts/households/<profile-id>/<opaque-scope-id>.json`
- Linux: `$XDG_CONFIG_HOME/betterinstincts/households/<profile-id>/<opaque-scope-id>.json` (or `~/.config/betterinstincts/...`)

Per-Sim skills list export (same private root; each installer/profile has different data):

- Windows: `%LOCALAPPDATA%/BetterInstincts/households/<profile-id>/exports/<scope-id>-skills-<stamp>.json`
- Linux: `$XDG_CONFIG_HOME/betterinstincts/households/<profile-id>/exports/<scope-id>-skills-<stamp>.json`
- Floor maps (per lot): `%LOCALAPPDATA%/BetterInstincts/households/<profile-id>/floors/<lot-key>.json` (Linux under the same `households/<profile-id>/floors/` root). Auto-ensure on Build when `learning.lot_floor_map_auto` is true; agents map computers/workstations/paths over time (`scripts.lot_floor_map`).

```sh
python -m scripts.diy_skill_force skills-export \
  --profile-id default \
  --save-key observed-save --household-key observed-household \
  --members N --roster-key portrait-001 [--roster-key portrait-002 ...]
```

Owner: `export_household_skills_list` / `household_skills_export_path`. Export is ledger-backed (`PANEL_OBSERVED*` vs `DISPATCHED`); it is not live Skills-panel proof and must not be committed to git.

Existing installation preference settings are not relocated or reset. Scoping is opt-in when planning; **a live household execute now requires explicit profile/save/household/portrait evidence**. It rejects populated legacy ledgers and foreign scopes rather than importing their completed-cell claims. Existing unscoped offline plans remain compatible, but their progress cannot silently become scoped live authority.

Example planning (synthetic IDs only):

```sh
python -m scripts.diy_skill_force household --members 2 --skill handiness --roster-key portrait-001 --roster-key portrait-002 --save-key save-a --household-key household-a
```

These IDs are placeholders; the local observer must obtain real stable values and independently verify target/roster and game state before any input. Do **not** run `--execute` based on this example. Respect the existing save, Build/Buy checkpoint, UI ownership and player-idle gates. The current remote test suite does not prove that a local Windows game adapter has captured these identifiers, that a cheat raised a skill, or that a playable mod has been released.

## Publishing rule and regression cases

1. Commit generic, synthetic fixtures only; never actual Sims/household names, screenshots, save IDs, installed paths, roster receipts, personal preferences, completed-skill data or personally identifying logs.
2. Classify a behavior or lesson by stable **game mechanics** and version/pack capabilities, not a particular household member. Store local observations and individual judgments in their owner-specific local profile/household state.
3. Exercise one-member, multi-member and large rosters; compare two profiles, two saves, two households, portrait permutations, missing or duplicate IDs, and incompatible ledgers.
4. `DISPATCHED` means text was issued, not that the local Skills panel proved mastery. Unknown or stale local observations stay unproven, not promoted into the public repository.
5. Existing private ledgers are not deleted, migrated or rewritten automatically. Operators may explicitly start a new scoped ledger after local roster reconciliation.

See `tests/test_household_scope.py` for executable checks. Live P08 proof remains an independent local Windows/disposable-save task; do not merge claims of local gameplay certification with offline CI.
