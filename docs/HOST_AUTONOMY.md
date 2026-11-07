# Host autonomy program design (P95)

**Prompt:** TokenCorridor P95 — Program Design & Call-Stack Prototype Architect
**Provenance:** `spec-architecture-prompts.v1.json` blob `5926a198a14567de55110ed19e922fc444b4dec7`
**Vocabulary owner:** [GLOSSARY.md](GLOSSARY.md) / `contracts/glossary.v1.json`

## User outcomes
1. Operator can **Play** the disposable lab Sim whenever they want; host never fights the mouse on the Sims canvas.
2. When the operator is **not** playing (cursor/focus off canvas, or explicit yield), an **opt-in** listener/automator continues intelligent need/skill-safe management.
3. Queued behavior is classified with a fixed matrix: **EMULATE** good intent, **OPTIMIZE** bad/suboptimal routing (especially **MAP_TRAVEL** over **IN_FRAME_WALK_THRASH**).
4. No autorun daemon, no GHA-as-listener, no Resume/user-save mutation.

## Governance vs harness vs program
| Layer | Owns |
| --- | --- |
| Governance | AGENTS.md, DOCTRINE (Player first, no background scanners) |
| Harness | unittest, validate_doctrine, CI FakeGui |
| Program | glossary, behavior matrix, host listener, player presence, needs-force, host_stack |
| Live adapters | scripts/* SendInput / PrintWindow — only after evaluate-only plan |

## Domain vocabulary (do not reinvent)
See glossary: `PLAYER_FIRST`, `PLAYER_PLAYING`, `PLAYER_PRESENT_ON_CANVAS`, `HOST_MAY_AUTOMATE`, `YIELD_TO_PLAYER`, `GOOD_BEHAVIOR`, `BAD_BEHAVIOR`, `EMULATE`, `OPTIMIZE`, `EMULATE_THEN_OPTIMIZE`, `MAP_TRAVEL`, `IN_FRAME_WALK_THRASH`, `HOST_LISTENER`.

## Module map
| Module | Responsibility | Side effects |
| --- | --- | --- |
| `glossary` | Canonical term load | none |
| `behavior_eval` | Queue×needs → verdict/disposition | none |
| `player_presence` | Focus+cursor → presence state | none (probe injectable) |
| `needs_force` | MAP_TRAVEL-first recovery plan | none in library |
| `host_stack` | Compose viewport/behavior/instincts gates | none |
| `host_listener` | Opt-in session + tick receipts | writes `dist/host-listener/` |
| `host_automate` | Presence-gated plan; optional execute | optional SendInput via script |

## Success call stack (evaluate-only)
```
operator activates listener/automate session
  -> scripts.host_listener|host_automate
  -> player_presence.classify (FG Sims? cursor in client?)
  -> if PLAYER_PLAYING: YIELD_TO_PLAYER (stop)
  -> behavior_eval.evaluate_queue
  -> host_stack.evaluate_turn
  -> needs_force.plan_force when OPTIMIZE / off-lot critical
  -> receipt under dist/ (ignored)
```

## Success call stack (live automate — separate flag)
```
...evaluate stack...
  -> HOST_MAY_AUTOMATE proven
  -> scripts.needs_force|host_menu --execute (Windows only)
  -> game_capture --analyze (proof ceiling: click dispatch ≠ live cert)
```

## Failure call stacks
| Failure | Classification | Host response |
| --- | --- | --- |
| Session not activated | `SESSION_NOT_ACTIVE` | refuse tick |
| Cursor on Sims canvas / FG Sims with recent input | `PLAYER_PLAYING` | `YIELD_TO_PLAYER` — no SendInput |
| Cursor on other app, FG not Sims | `HOST_MAY_AUTOMATE` | evaluate; execute only if flagged |
| Viewport black | existing viewport fallback | withhold needs/map clicks |
| Critical + fluff queue off-lot | `OPTIMIZE` + `MAP_TRAVEL` | never in-frame walk thrash |
| Player-directed queue | `EMULATE` only | never optimize away |

## State model
`INACTIVE` → (activate) → `ACTIVE` → tick loop → (deactivate) → `INACTIVE`
Presence per tick: `PLAYER_PLAYING` | `HOST_MAY_AUTOMATE` | `UNKNOWN_PRESENCE` (fail closed: yield).

## Proof ceiling
Offline matrix/listener/presence classification is **not** GAME_CERTIFIED. Live SendInput remains LOCAL_OBSERVED click dispatch until BI-002 hunger gates complete.

