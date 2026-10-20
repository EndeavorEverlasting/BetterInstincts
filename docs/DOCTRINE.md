# BetterInstincts doctrine — v1

## Product contract
BetterInstincts should make autonomy more **competent and believable**, not maximize task throughput at any cost. A Sim may rest, socialize, pursue a hobby, or behave imperfectly. Explicit player direction always outranks mod suggestions. Pursuit of work/career must consider time, energy, relationships, traits, mood, and user settings after those capabilities are observed in the game.

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

BI-002 game-capable agent must actually perform the hunger A/B and rollback, attach evidence, and pass maintainer review before sprint closure. Without game access it remains BLOCKED and ACTIVE, not completed via handoff.

## Long-horizon continuity (P141/P82/P07/P04)
The governing trajectory is **all six adult needs -> cross-need balance -> steady observed income while maintaining needs -> observed skill growth while maintaining income and needs -> career advancement**. Never optimize away playfulness or player override. Maintain compatibility throughout all phases. Current priority remains BI-002 hunger; no downstream live completion without its full game proof. Offline six-need `horizon.py` is a separate experimental candidate; original four-need `priority.py` remains a baseline. The declarative threshold values are provisional, not actual game tuning. CI rejects missing needs, reordered income/skills dependencies, and absent parent governance. One game host agent must actually build and certify BI-002.

## Filesystem and storage policy
Authoritative source: this Git repository. Tracked documentation and fixtures belong to their corresponding tracked directories. Generated builds belong under a single repo-local `dist/` (git-ignored); transient tests under OS-provided temporary directories, not home/Downloads/Desktop. Any future installation tool must require an **explicit, user-selected Mods root**; must preview intended changed files, allow uninstall, avoid writes outside its dedicated `BetterInstincts/` subfolder, and fail closed on unclear locations. Never traverse, rewrite, or copy `saves/`, EA game assets, Mods belonging to others, or configuration without explicit user consent. Never create persistent runtime caches/logs until a size, rotation, and retention policy is validated. No autorun/background scanners.

## Correctness & release safety
No playable-mod claim until a real package/script is built, installed on a **disposable** Sims save, verified with the correct current game patch, and tested for player queue safety, target behavior, conflicting mods, load errors, performance, and safe removal. Game update = compatibility unverified until repeated. Record known DLC dependencies; default to base-game targeting. No redistribution of EA content or other mods/libraries without permission; note required third-party libraries rather than bundling them.

## Agent accountability
Preflight repo/branch/PR, protected paths, status, read-first ledger, and latest provider evidence. Execute safe ready work, run the focused validators and regression tests, produce durable tracked artifacts, and report proof ceiling. Do not mark work done because a plan exists or because an agent acknowledges a request. Human-only game testing may be routed to a named operator gate; continue independent work meanwhile.
