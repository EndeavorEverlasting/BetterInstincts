# BetterInstincts glossary

Canonical vocabulary for host listeners, evaluators, and autonomy.
**Machine authority:** [`contracts/glossary.v1.json`](../contracts/glossary.v1.json)
**Program design (P95):** [HOST_AUTONOMY.md](HOST_AUTONOMY.md)

Do not invent synonyms in contracts or agent chat. Add terms to the JSON contract first, then document here.

| Term | Meaning |
| --- | --- |
| **PLAYER_FIRST** | Explicit player direction outranks autonomy and host optimization. |
| **PLAYER_PRESENT_ON_CANVAS** | Foreground Sims window and cursor inside the client rect. |
| **PLAYER_PLAYING** | On-canvas, recent input grace, declared playing, or player-directed queue → host yields. |
| **HOST_MAY_AUTOMATE** | Opt-in session active and not `PLAYER_PLAYING`; evaluate / optional execute. |
| **YIELD_TO_PLAYER** | Refuse SendInput; do not rewrite the queue. |
| **HOST_LISTENER** | Opt-in bounded session that ticks observations into evaluators (not a daemon). |
| **HOST_AUTOMATE** | Presence-gated orchestrator over behavior + needs-force plans. |
| **HOST_EVALUATOR** | Read-only scorer (`host_eval`, `behavior_eval`, etc.). |
| **GOOD_BEHAVIOR** / **BAD_BEHAVIOR** | Matrix verdicts over queue × critical needs. |
| **EMULATE** | Keep the same intent class as a good queue. |
| **OPTIMIZE** | Replace bad/suboptimal queue; never override player direction. |
| **EMULATE_THEN_OPTIMIZE** | Keep good intent; improve routing (e.g. map travel). |
| **MAP_TRAVEL** | Manage Worlds / phone travel to the lot with required objects. |
| **IN_FRAME_WALK_THRASH** | Forbidden: making the Sim pathfind across the current frame instead of traveling. |
| **CRITICAL_NEED** | Motive below `needs.v1.json` urgency threshold. |
| **PROOF_CEILING** / **LOCAL_OBSERVED** / **GAME_CERTIFIED** | Evidence claim limits — see VALIDATION / LIVE_CERT. |

Related matrices: `contracts/behavior-matrix.v1.json`, `contracts/player-presence.v1.json`, `contracts/needs-force.v1.json`, `contracts/host-listener.v1.json`.
