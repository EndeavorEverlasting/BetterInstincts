# BetterInstincts doctrine — v1

## Product contract
BetterInstincts should make autonomy more **competent and believable**, not maximize task throughput at any cost. A Sim may rest, socialize, pursue a hobby, or behave imperfectly. Explicit player direction always outranks mod suggestions. Pursuit of work/career must consider time, energy, relationships, traits, mood, and user settings after those capabilities are observed in the game.

## Engineering authority
- Root **AGENTS.md** is the mandatory agent entrypoint.
- **docs/LEDGER.md** owns product intent, facts, decisions, and proof state.
- **docs/ROADMAP.md** owns accepted future capability slices.
- **docs/PRIOR_ART.md** owns external evidence and adoption/rejection decisions.
- **plans/active/BI-001.md** owns the current execution slice; close it only after its explicit gates.
- **docs/VALIDATION.md** owns definitions of evidence quality.
- TokenCorridor owns the exact P-number registry; this repository must not fork or rename prompt meanings.
- Authority order: platform/security/owner instruction > root agent governance > canonical ledger/sprint > local implementation notes. Repository docs cannot override user safety.

## Project architecture rule
Observe the game's native tuning and compare with community implementations **before** adding a generalized decision framework. Prefer localized XML tuning and proven shared extension points if appropriate. Introduce Python game scripts only if the chosen behavior cannot be implemented safely through tuning. Offline Python prototypes are simulations, not game hooks. Do not use Rust/TypeScript/C# in the game runtime without evidence of a concrete need; build tooling may be different from runtime language.

## Filesystem and storage policy
Authoritative source: this Git repository. Tracked documentation and fixtures belong to their corresponding tracked directories. Generated builds belong under a single repo-local `dist/` (git-ignored); transient tests under OS-provided temporary directories, not home/Downloads/Desktop. Any future installation tool must require an **explicit, user-selected Mods root**; must preview intended changed files, allow uninstall, avoid writes outside its dedicated `BetterInstincts/` subfolder, and fail closed on unclear locations. Never traverse, rewrite, or copy `saves/`, EA game assets, Mods belonging to others, or configuration without explicit user consent. Never create persistent runtime caches/logs until a size, rotation, and retention policy is validated. No autorun/background scanners.

## Correctness & release safety
No playable-mod claim until a real package/script is built, installed on a **disposable** Sims save, verified with the correct current game patch, and tested for player queue safety, target behavior, conflicting mods, load errors, performance, and safe removal. Game update = compatibility unverified until repeated. Record known DLC dependencies; default to base-game targeting. No redistribution of EA content or other mods/libraries without permission; note required third-party libraries rather than bundling them.

## Agent accountability
Preflight repo/branch/PR, protected paths, status, read-first ledger, and latest provider evidence. Execute safe ready work, run the focused validators and regression tests, produce durable tracked artifacts, and report proof ceiling. Do not mark work done because a plan exists or because an agent acknowledges a request. Human-only game testing may be routed to a named operator gate; continue independent work meanwhile.
