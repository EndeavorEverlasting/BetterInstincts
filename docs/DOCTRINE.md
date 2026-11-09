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

**Binding runtime default:** the agent-owned camera stays centered on the active Sim. `Enter` centers the Sim; `Shift+Enter` centers the lot and is not a substitute. Never park on a street, choose arbitrary camera views, or free-pan/zoom based on agent preference. A **named, verified current host-task goal and target** may receive a single bounded map traversal lease (30-second maximum, eight directions); only when the active Sim was already anchored. Traversal must re-center the active Sim under the same admitted host lease in `finally`, then reobserve. Human input, unknown Sim, dialog or focus loss means yield and restoration pending — not forceful override. The machine owner is `betterinstincts/active_sim_camera_lock.py`; see `contracts/camera-traverse.v1.json`, `docs/CAMERA_TRAVERSE.md`, `tests/test_active_sim_camera_lock.py`. Retain player-first and no save writes.

## Portrait-first semantic camera and HUD continuity (2026-11-09)

Camera framing is **not agent preference**. When the host is admitted and no named map-target lease is active, prefer **right-clicking the attested selected active Sim portrait** to follow that Sim. `Enter` is a one-shot center fallback, never continuing follow; `Shift+Enter` centers the lot only. Do not right-click an uncalibrated portrait or reuse stale selection. Before resuming queue work, resolve any independently observed career/random popup through the correct decision microsystem, dismiss only after its decision is accepted and its button verified, then revalidate queued goals. Track the exact active bottom-right panel and its current layout. Misdirected scenery must become reviewed/deduplicated `VIEW_SCENE` evidence, not ignored drift and never blind map-travel authority. Owners: `contracts/portrait-follow.v1.json`, `contracts/scenery-memory.v1.json`, `betterinstincts/scene_ui_semantics.py`. Player control and offline gameplay remain higher priority.

## Complete lot backup / Build-Buy safety (2026-11-09)

Protect the *whole home*, not just one target. Before **any agent** Build/Buy purchase or mutation, the host must attest coverage and classification of all observed stories, rooms and outdoor areas, reconcile the complete operator-attested floor roster with the revisioned model, verify a pre-change My Library building checkpoint and persist/read back the exact model. The old wall-only gate and inventory/purchase exemptions are prohibited. A single room or one screenshot is not proof the second floor was saved. Unknown floor counts are a hard stop; the player retains all native control. A game Save As does not replace My Library. The current pure-Python gate is offline decision machinery, **not** proof of interception of Cursor/Playwright or live Win32 input: independent adapters must consume fresh permits before any game UI mutation. No uncontrolled save edits or online EA path. Detailed policy: `docs/BUILD_LIBRARY_CHECKPOINT.md`.
