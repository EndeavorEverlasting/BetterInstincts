# BetterInstincts — canonical agent entrypoint

Before edits/samples/experiments, read `docs/ONTOLOGY.md` + owners; commit `contracts/consultations/` first; run `scripts/semantic_preflight.py`. Read **docs/DOCTRINE.md**, **docs/LEDGER.md**, **docs/PROMPT_INVOCATIONS.md**. **plans/active/BI-001.md** merged; **plans/active/BI-002.md** owns game-lab gate.

## Parent objective
Community-native Sims 4 autonomy: needs, income, careers, personality. Player always first; offline prototypes are not playable mods.

## Mandatory preflight
Refresh HEAD/PRs/game; declare host, scope, collisions, tests and proof. Resolve Moonwake P-IDs.

## P04 hidden-object discovery
Read `plans/active/BI-HIDDEN-OBJECTS.P04.md`, `docs/HIDDEN_OBJECT_SCOUT.md`; dispatch/scene/save/consent. `python -m scripts.hidden_object_discovery guide`; `python -m scripts.hidden_object_discovery audit --observation dist/game-host/hidden-object-p04-receipt.json`. Scout: `scripts.hidden_object_scout goal`. No autorun.

Useful-item force: `python -m scripts.household_object_force`. DIY parts: `python -m scripts.upgrade_parts_force`.

## Invariants
- **Player first:** no interrupt of explicit player commands; no uncontrolled autonomy loops.
- **Save-safe:** never edit/delete/migrate/overwrite user saves/game files. Unknown/user saves protected.
- **Build structure / FLOOR_2 / all purchases:** No agent Build/Buy edits/purchases until ALL floors/rooms are scanned, classified, backed up to My Library pre-edit and model readback verified. Unknowns, stale saves, incomplete FLOOR_2 = DENY. Keep stairs/Craftidink CANCEL_UI and `admit_live_structure_effect`; offline leases are NOT live input permits. `docs/BUILD_LIBRARY_CHECKPOINT.md`.
- **Offline install:** never EA Connect; Stay Offline only; play as installed.
- **Storage:** no arbitrary profile writes, auto-discovery, asset copy, daemons, telemetry, unbounded logs.
- **Community-native:** review prior art/licensing; favor tuning before script hooks where justified.
- **Performance:** bounded work; no global per-frame scans, busy-waits or unmeasured runtime hooks.
- **Evidence:** separate tests, build, PR, merge and gameplay. See docs/SCENE_INTELLIGENCE.md; two cues; unknown -> no action.
- **Continuity:** keep docs/LEDGER.md, docs/ROADMAP.md and sprint current; no chat-only decisions.
- **Live-host ops (P00/P01):** Operator live corrections are incomplete until encoded in `contracts/live-host-ops.v1.json` + `betterinstincts/live_host_ops.py` (+ tests/AGENTS/DOCTRINE/Horizon). Chat memory alone is forbidden. Architecture `PAUSED_PRODUCTIVITY_BEFORE_TIME_RISK`: keep PAUSED; Order/Purchase Upgrade Parts or robotics workstation spawn before Needs/unpause; OFF_INTENT_VIEW → Esc(+F1)+Shift+Enter; EDGE_MOUSE_PARK→creek → SAFE_CURSOR_REST then Shift+Enter; no hardcoded field XY across zoom; yield focus to mouse/Wispr; never Sell / delete Slot_00000007. Fifth Gear with Sims PID live: execute live gates — do **not** emit a new P05 pack.
- **Lot cardinal semantics (FALLBACK):** Prefer authorized EA save/Tray parse, then profile `lot_floor_map` graph. Cardinal corner/side relations (`contracts/lot-cardinal-semantics.v1.json`) are the next fallback — e.g. bathtub SAME_SIDE_AS hydroponics; fridge OPPOSITE near doors; robotics workstation ~90° from FRONT_DOOR. Workstation is **GRAY** (not blue water generator); Gardener-Bot needs fix; pending Servo must **not** be Activated. My Library/Gallery: `CLEAR_SEARCH_BEFORE_QUERY` (Ctrl+A Delete / clear-X) before every new search term.

## Multiversion + real-game closure
Read `docs/COMPATIBILITY.md`, `docs/LIVE_CERT.md`, `plans/active/BI-002.execution.v1.json`. Pin exact version/platform/module; UNKNOWN_VERSION denies. Never change older certified profiles or call synthetic work game proof.

**Local agent** owns hunger: inspect game/tuning, build reversible package, run 5 vanilla + 5 modified trials, verify rollback, queue and review. CI/handoffs cannot close BI-002; without host: BLOCKED_LOCAL_GAME_ACCESS, ACTIVE. `python -m scripts.live_cert status --run-id ID`.

## Horizon continuity
Read `docs/HORIZON.md`, `plans/horizon.v1.json`, `plans/active/BI-003.execution.v1.json`. Order: all six needs, balance, income, skills, careers; preserve prior patches. BI-002 stays open. `python -m scripts.check_horizon`.

## Completion contract
Report CHANGED | PROVED | NEXT with checks, SHA, push/PR/merge, patch, live status. A plan is not implementation; a green CI check is not playable-mod proof.

P04: `docs/handoff/BI-JUDGMENT-LEARNING-P04-2026-11-07.md`; ontology: `docs/handoff/BI-SEMANTIC-ONTOLOGY-P04-2026-11-07.md`.
Interop: `docs/ASYNC_INTEROP.md` (15s idle). Likes: `docs/PREFERENCE_PROMPTS.md`.
Skills: `docs/HOUSEHOLD_JUDGMENT.md` (fixed roster; serial/offline).
