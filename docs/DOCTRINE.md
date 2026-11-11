# BetterInstincts doctrine — v1

## Product contract
BetterInstincts should make autonomy more **competent and believable**, not maximize task throughput at any cost. A Sim may rest, socialize, pursue a hobby, or behave imperfectly. Explicit player direction always outranks mod suggestions. Pursuit of work/career must consider time, energy, relationships, traits, mood, and user settings after those capabilities are observed in the game.


**Proof invariants:** An offline policy prototype is not a playable mod. First win: do not close BI-002 until hunger is live certified from the actual game, independently of CI.

## Product identity and capability freedom
BetterInstincts improves the game's natural mechanics through safe, coordinated autonomy: six needs and financial sustainability are the core challenge; boot/save/scene/host infrastructure enables it rather than replacing it. Evaluate all relevant domains concurrently, respect real time/object/attention constraints, preserve ongoing goals when interrupted, and revalidate before resumption. Prefer native mechanics without prohibiting demonstrated, reversible extensions, new domains, economy experiments, or alternative engineering techniques. None of those extensions is a prerequisite to BI-002 without a proved dependency. The versioned semantic owner is `contracts/ontology.v1.json`; its consultation gate is not a game execution permit.

## Engineering authority
- Root **AGENTS.md** is the mandatory agent entrypoint.
- **docs/LEDGER.md** owns product intent, facts, decisions, and proof state.
- **docs/ROADMAP.md**, **docs/HORIZON.md**, and **plans/horizon.v1.json** own accepted future capability slices and enforceable dependencies.
- **plans/active/BI-003.execution.v1.json** owns follow-on work for bladder, energy, hygiene, fun and social once hunger is live-proven.
- **docs/PRIOR_ART.md** owns external evidence and adoption/rejection decisions.
- **plans/active/BI-001.md** is closed; **plans/active/BI-002.md** owns the non-optional hunger gameplay gate.
- **docs/COMPATIBILITY.md** and **docs/LIVE_CERT.md** own version retention and bounded evaluation contracts.
- **plans/active/BI-002.execution.v1.json** owns the local game execution gate graph.
- **docs/VALIDATION.md** owns definitions of evidence quality.
- **docs/PROMPT_INVOCATIONS.md** pins TokenCorridor P-number invocation identity and provenance.
- TokenCorridor owns the exact P-number registry; this repository must not fork or rename prompt meanings.
- Authority order: platform/security/owner instruction > root agent governance > canonical ledger/sprint > local implementation notes. Repository docs cannot override user safety.

## Project architecture rule
Observe the game's native tuning and compare with community implementations **before** adding a generalized decision framework. Prefer localized XML tuning and proven shared extension points if appropriate. Introduce Python game scripts only if the chosen behavior cannot be implemented safely through tuning. Offline Python prototypes are simulations, not game hooks. Do not use Rust/TypeScript/C# in the game runtime without evidence of a concrete need; build tooling may be different from runtime language.

## Long-lived patch support (P00)
Support multiple independently verified game builds. Do not equate newest with only-supported. Certified profile and proof bytes are immutable across future updates; patch updates add new profiles and compare tuning against prior local evidence. Do not silently reinterpret a certified older game's configuration. Match exact full game version, OS/platform and feature module; unknown patches fail closed. Mod version and game patch are different concepts. No real game build has yet been certified.

## Offline install (P00/P01 — 2026-11-09)
The Sims 4 host must **never** press EA **Connect** or otherwise force the installed game online. Play as installed offline. On `CONNECTION IS REQUIRED`, choose **Stay Offline** only. Prefer on-lot spawn / local computer Order over phone paths that surface an online gate. See `contracts/upgrade-parts-force.v1.json` `offline_install`.

BI-002 game-capable agent must actually perform the hunger A/B and rollback, attach evidence, and pass maintainer review before sprint closure. Without game access it remains BLOCKED and ACTIVE, not completed via handoff.

## Long-horizon continuity (P141/P82/P07/P04)
The governing trajectory is **all six adult needs -> cross-need balance -> steady observed income while maintaining needs -> observed skill growth while maintaining income and needs -> career advancement**. Never optimize away playfulness or player override. Maintain compatibility throughout all phases. Current priority remains BI-002 hunger; no downstream live completion without its full game proof. Offline six-need `horizon.py` is a separate experimental candidate; original four-need `priority.py` remains a baseline. The declarative threshold values are provisional, not actual game tuning. CI rejects missing needs, reordered income/skills dependencies, and absent parent governance. One game host agent must actually build and certify BI-002.

## Filesystem and storage policy
Authoritative source: this Git repository. Tracked documentation and fixtures belong to their corresponding tracked directories. Generated builds belong under a single repo-local `dist/` (git-ignored); transient tests under OS-provided temporary directories, not home/Downloads/Desktop. Any future installation tool must require an **explicit, user-selected Mods root**; must preview intended changed files, allow uninstall, avoid writes outside its dedicated `BetterInstincts/` subfolder, and fail closed on unclear locations. Never traverse, rewrite, or copy `saves/`, EA game assets, Mods belonging to others, or configuration without explicit user consent. Never create persistent runtime caches/logs until a size, rotation, and retention policy is validated. No autorun/background scanners.

## Correctness & release safety
No playable-mod claim until a real package/script is built, installed on a **disposable** Sims save, verified with the correct current game patch, and tested for player queue safety, target behavior, conflicting mods, load errors, performance, and safe removal. Game update = compatibility unverified until repeated. Record known DLC dependencies; default to base-game targeting. No redistribution of EA content or other mods/libraries without permission; note required third-party libraries rather than bundling them.

## Agent accountability
Preflight repo/branch/PR, protected paths, status, read-first ledger, and latest provider evidence. Execute safe ready work, run the focused validators and regression tests, produce durable tracked artifacts, and report proof ceiling. Do not mark work done because a plan exists or because an agent acknowledges a request. Human-only game testing may be routed to a named operator gate; continue independent work meanwhile.

## Agent-controlled camera authority (2026-11-09)

**Binding runtime default:** the agent-owned camera follows the active Sim via verified portrait right-click at **RIGHT_CLICK_VIEW** — 0.85 of max close (15% pullback from max zoom-in). `Enter` centers once; `Shift+Enter` centers the lot and is not a substitute. Never park on a street / full zoom-out as a default. **ENVIRONMENT_NAV** (halfway / 0.50) is only for named environment planning or nav understanding. **TRAVEL_AFAR** (full zoom-out / street top-down) is only for a verified long-distance travel goal. When zoomed in to RIGHT_CLICK_VIEW or closer, clear tracked HUD overlays (expanded opportunity panel, expanded bottom-right panels, cheat console, expanded phone, extensible) only after BetterInstincts has tracked and accounted for their metadata; unresolved decision overlays never count as clutter. A **named, verified current host-task goal and target** may receive a single bounded map traversal lease (30-second maximum, eight directions); only when the active Sim was already anchored. Traversal must restore RIGHT_CLICK_VIEW under the same admitted host lease in `finally`, then reobserve. Human input, unknown Sim, dialog or focus loss means yield and restoration pending — not forceful override. Owners: `betterinstincts/active_sim_camera_lock.py`, `betterinstincts/camera_traverse.py#assess_agent_zoom_mode`, `betterinstincts/scene_ui_semantics.py#assess_overlay_clear_after_metadata`; see `contracts/camera-traverse.v1.json`, `docs/CAMERA_TRAVERSE.md`, `tests/test_camera_zoom_policy.py`. Retain player-first and no save writes.

## Portrait-first semantic camera and HUD continuity (2026-11-09)

Camera framing is **not agent preference**. When the host is admitted and no named map-target lease is active, prefer **right-clicking the attested selected active Sim portrait** to follow that Sim. `Enter` is a one-shot center fallback, never continuing follow; `Shift+Enter` centers the lot only. Do not right-click an uncalibrated portrait or reuse stale selection. Before resuming queue work, resolve any independently observed career/random popup through the correct decision microsystem, dismiss only after its decision is accepted and its button verified, then revalidate queued goals. Track the exact active bottom-right panel and its current layout. Misdirected scenery must become reviewed/deduplicated `VIEW_SCENE` evidence, not ignored drift and never blind map-travel authority. Owners: `contracts/portrait-follow.v1.json`, `contracts/scenery-memory.v1.json`, `betterinstincts/scene_ui_semantics.py`. Player control and offline gameplay remain higher priority.

## Complete lot backup / Build-Buy safety (2026-11-09)

Protect the *whole home*, not just one target. Before **any agent** Build/Buy purchase or mutation, the host must attest coverage and classification of all observed stories, rooms and outdoor areas, reconcile the complete operator-attested floor roster with the revisioned model, verify a pre-change My Library building checkpoint and persist/read back the exact model. The old wall-only gate and inventory/purchase exemptions are prohibited. A single room or one screenshot is not proof the second floor was saved. Unknown floor counts are a hard stop; the player retains all native control. A game Save As does not replace My Library. The current pure-Python gate is offline decision machinery, **not** proof of interception of Cursor/Playwright or live Win32 input: independent adapters must consume fresh permits before any game UI mutation. No uncontrolled save edits or online EA path. Detailed policy: `docs/BUILD_LIBRARY_CHECKPOINT.md`.

## Household skill judgment / offline action restriction (2026-11-09)

For household skill goals, preserve the original ordered N portrait roster, traverse one skill across all existing members to level 10 before advancing, and disallow unrelated scope expansion (creating new Sims/Servos, moving Sims, CAS, Build/Buy changes). Reject detached/concurrent skill UI workers; only a single foreground owner may send game input under fresh screen admission. EA Connect, Gallery, Store and online features remain forbidden globally, not just in DIY parts. `contracts/household-judgment.v1.json` and `betterinstincts/household_judgment.py` are the machine policy; `betterinstincts/menu_blockers.py` adds online menu denial. CLI roster flags are host assertions, not fresh screen readback. Skill unlock PASS still requires Skills-panel LOCAL_OBSERVED on an exact game build. See `docs/HOUSEHOLD_JUDGMENT.md`.

## Live-host operating policy / no chat-only rules (2026-11-10)

Operator corrections issued during live Horizon work are **not** execution authority until they land in repository owners: `contracts/live-host-ops.v1.json`, `betterinstincts/live_host_ops.py`, `contracts/camera-traverse.v1.json#edge_creek_regression`, `betterinstincts/lot_focus.py#assess_off_intent_view`, AGENTS/DOCTRINE/LEDGER, and `plans/active/BI-HORIZON-EXECUTION-WIDE-20261110.v1.json#priority_algorithm_20261110`. Selected architecture is `PAUSED_PRODUCTIVITY_BEFORE_TIME_RISK`: any work achievable while PAUSED (Order → Purchase Upgrade Parts, UI mapping, Needs O measure-only, queue all household actions) outranks motive traversals that require the clock. Unpause is denied while parts or household queues remain open. Post-click street/Buy is `OFF_INTENT_VIEW` / `MISS_OFF_LOT` — Esc(+F1)+Shift+Enter, never explore Buy. Mouse in the edge band → creek/canal is `EDGE_CREEK_REGRESSION` — SAFE_CURSOR_REST then Shift+Enter. World object XY are camera-relative; hardcoded field coordinates are not durable across zoom. Borrow Sims focus briefly; yield immediately to mouse move or Wispr. Never Sell; never delete or overwrite `Slot_00000007`. Fifth Gear with a live Sims PID does not mean another P05 pack — execute the live gate. Proof ceiling: contract/harness ≠ live parts HIT ≠ BI-002 close.

## Lot geometry EA-file first / cardinal FALLBACK (2026-11-10)

**Preferred authority** for lot/town identity is authorized READ_ONLY Sims user-data under Documents/Electronic Arts — saves `Slot_*.save` and Tray — owned by `contracts/lot-geometry-source.v1.json`. Do **not** invent external town maps or remap Bargain Bendh from PrintWindow when EA paths can answer. Parser remains RESEARCH_STUB_NO_PARSER; never open `Slot_00000007` without explicit operator auth. Next spike: disposable-copy or authed DBPF index (`next_authorized_spike`).

**FALLBACK** after EA parse + profile `lot_floor_map`: cardinal / street-creek semantics in `contracts/lot-cardinal-semantics.v1.json`. Bargain Bendh has opposite edges **STREET_SIDE** (asphalt OFF_LOT risk) and **CREEK_SIDE** (canal/water OFF_LOT risk); `assess_camera_side_drift` recovers SAFE_CURSOR_REST+Shift+Enter. Also: bathtub SAME_SIDE_AS hydroponics; fridge OPPOSITE near doors; robotics workstation ~90° from FRONT_DOOR; workstation **GRAY** + Gardener-Bot needs fix; never Activate pending Servo; Library `CLEAR_SEARCH_BEFORE_QUERY`.

## Lot boundary / house footprint admission (2026-11-10)

Agents that click street, asphalt, neighbor lots, or canal have lost the house boundary. Durable gate: `contracts/lot-boundary.v1.json` / `betterinstincts/lot_boundary.py`. Algorithm: classify zones INTERIOR|YARD vs STREET|WATER|NEIGHBOR; require `lot_focus` ON_LOT; deny Buy/Build without a Build-census lease; admit a world click only when the client XY is inside a camera-revision-bound footprint AABB **or** the click zone is INTERIOR/YARD. Cardinal semantics apply only after footprint admit. Deny → Esc(+F1)+Shift+Enter lot arm — never thrash asphalt. `host_stack` attaches `lot_boundary` / `world_click_footprint`. Chat memory of “don’t click the street” is incomplete until this contract fires.

## P00/P01: interaction sovereignty and native transport

The operator may combine manual game play, mod features, voice/assistive input, IDEs and other apps. Autonomous effects yield at the next cooperative boundary and wait for fresh inactivity evidence before revalidation. Never change screenshot, mouse, Bluetooth or UAC settings for automation. Prefer verified native semantic APIs; never invent an unsupported command. Desktop input is an explicit fallback under existing ownership/presence checks. Passive capture never restores/foregrounds Sims. This applies to adopted adapters, not arbitrary external agents or game-native behavior.

## 2026-11-10 — mandatory CI / live game proof distinction

A green CI check is not playable-mod proof. Never infer a Sims 4 runtime result, real-world object recognition accuracy or BI-002 milestone completion from offline fixtures or unit tests alone. `CHANGED | PROVED | NEXT` reports independently verified repository mutations, measured test outcomes and the remaining Windows-host P08 game-gate separately. Existing documented peripheral, save, player-presence and exact-build protections apply unchanged.

## Human-first effect lanes — 2026-11-10

Human operator activity in **any application or device modality** preempts any
agent screen action, input chord, focus borrow, and game mutation at the next
cooperative checkpoint. No background reasoning may be used to bypass this.
Trustworthy observations, read-only parsing, and bounded planning may continue
independently **without taking the desktop lease** only through a reviewed
passive callback. Unknown activity or stale presence fails closed for input.
Resume requires two fresh trusted idle probes at least 15 seconds old, a new
scene/save/target/user-queue validation and one-effect admission. Never blind
replay partially completed actions.

Host configuration (Bluetooth, drivers, Print Screen settings, Escape/U remapping,
accessibility, global hotkey interception) is outside BetterInstincts authority.
No game prompt, frustrated agent or idle permit grants this authority.
`contracts/effect-authority.v1.json` owns effect classes; source checks do not
control independent unadopted tools or prove live-game behavior.


## P00/P01 — world-object perception and replay-safe learning (ontology revision 5; 2026-11-10)

**Three distinct semantic objects, not interchangeable authority:** `HIGHLIGHT_OBSERVATION` is independent sourced evidence about the *glow* of an in-world object, `WORLD_TARGET_TRACK` is temporal/camera/target continuity, and `WORLD_INTERACTION_ATTEMPT` is a separately attested post-action outcome row. A pixel glow, stable target box or synthetic label **never** means the object was clicked, a useful interaction occurred, or gameplay was certified. Fixed HUD/UI chrome calibration has a separate owner. Pure classifiers in `betterinstincts/world_traversal_learning.py` are opt-in; `host_stack` may revoke framing candidates on lost/ambiguous highlights, but no tracker or model can promote itself into a `CONTROL_PERMIT`.

**World-highlight doctrine:** two ordered, unique host frames; stable camera revision and target identity; two independent accepted cues per frame; stable target bounds; explicit hover context. Two `ABSENT` frames may have `highlight_target_id=null` and yield `HIGHLIGHT_LOST`. A `PRESENT` cue without that identity, one-frame flicker, camera movement, occlusion, stale capture, off-lot observations or source conflict must not authorize input. After any pan, reacquire object/lot/target and let the existing `screen_admit`, `lot_boundary`, `player_presence`, save and one-effect controls decide whether an action is permitted. Human activity—including in other applications, keyboard, mouse and assistive modalities—preempts input; do not disable Bluetooth/Print Screen/OS mapping/security settings to make a capture easier.

**Learning doctrine:** accept only independently observed `GAME_EVENT` or reviewed operator evidence with explicit no-player-interruption attestation, different before/after refs, actual observed target result, and one replay fingerprint for the originating before capture. Train/holdout duplicates abstain; cap history at 2,048 and reject legacy counted snapshots lacking replay provenance rather than manufacturing independence. Never promote offline Brier/fixture performance to true screenshot accuracy or a game action permit. Learn contextual strategies, not household-specific names, personal save content, coordinates or exploitative click loops. Prefer bounded passive sensor work; model snapshots/real captures remain private/local and require explicit operator opt-in.

**Priority and ownership:** `BI-WORLD-TRAVERSAL-P08-SENSOR` in `plans/horizon.v1.json` is *supporting infrastructure*, not a successor to/mandatory dependency of BI-002 hunger. Serial phases `WORLD_SENSOR → WORLD_OUTCOME → WORLD_INTEGRATE` in the existing `BI-HORIZON.dispatch.v1.json` share one Sims screen owner with BI-002; actual world-input permission requires a fresh separately approved disposable-game P08. Open PR #159's spatial-perception owner is independent. Canonical P01 map, workflows, artifact/privacy registry, scoped skill, workstation path and validation instructions: `contracts/world-traversal-harness.v1.json`, `docs/WORLD_TRAVERSAL_HARNESS.md`, `scripts/check_world_traversal_harness.py` and `docs/INSTALLATION_PROFILES.md`. Tracked governance is not local tool activation or gameplay proof.
