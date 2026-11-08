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
| Program | glossary, behavior matrix, host listener, player presence, needs-force, event goals, need services (six-need tandem + fun), navigating needs, host_stack |
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
| `host_stack` | Compose viewport/behavior/event-balance/need-services/instincts gates | none |
| `need_service_base` | P124 shared need/object/lane helpers | none |
| `need_services` | Six-need tandem orchestrator (Fun nested) | none |
| `gardening_service` | Observed plant interactions composed with the same needs report and current responsibilities; no construction recovery | none |
| `need_load_balance` | Health checks, detach, assumption windows, LB pick | none |
| `domain_cascade` | Ordered domain poll receipts (needs/LB → budget → career microsystem → skills → relationships) | none |
| `career_service` | Sticky teen homework / career-panel obligation tandem beside need_services | none |
| `fun_service` | Rich Fun lanes under guest contention | none |
| `navigating_needs` | Discovery Quest panel tandem | none |
| `event_balance` | Outdoor-social RCA + event/needs/homework call stack | none |
| `moodlets` | Supplied emotion/moodlet strip → need pressure + routing bias | none |
| `sim_profile` | Supplied Simology/skills/preferences/whims + moodlets → read-only inspect | none |
| `build_optimize` | Deterministic Build/Buy catalog rank (Env Gain / Eco Footprint) | none |
| `house_state` | Recursive lot environment model + mutation lease; forbids blank-slate reassess | writes `dist/house-state/` receipts |
| `build_integrity` | Structure-first spatial admission (indoor≠outdoor, floor before furniture, no nesting, protect kitchen/bed/dining) | none |
| `build_library_checkpoint` | My Library building save required before room/structure mutate | none |
| `build_spatial` | Enclosure (INSIDE/OUTSIDE) + story (FLOOR_1/FLOOR_2) classification and build order | none |
| `camera_traverse` | Capture-first camera plans; forbids EDGE_MOUSE_PARK; mandatory SAFE_CURSOR_REST | optional SendInput via script |
| `host_listener` | Opt-in session + tick receipts | writes `dist/host-listener/` |
| `host_automate` | Presence-gated plan; optional execute | optional SendInput via script |
| `funds_inject` | Subsidy prompt (funds under 100) + mode-agnostic Money/motherlode inject | optional SendInput via `scripts/funds_inject` |
| `curious_catalog` | Opt-in rare/money garden Buy shelves; plan-only reveal; never game speed | `scripts/curious_catalog` |

## Household subsidy (funds under 100) — P95 mode-agnostic stack
When observed funds are under **100**, host shows a Sims-styled **HOUSEHOLD NOTICE**
("Oops, it looks like decisions were made… Simolean federal bank?"). **Yes** runs:

```
soft-focus Sims (no mode switch)
  -> Ctrl+Shift+C          # cheat console in Live OR Build/Buy
  -> testingcheats enabled true
  -> Money N               # best-effort exact set
  -> motherlode x chunks   # durable +50k (LOCAL_OBSERVED)
```

**Never force F1** while the operator is building — host works in tandem across
Live / Build / Buy. No Esc spam (opens pause MENU). Foreground Sims still required
or SendInput is ignored. Not BI-004 earned income; not a save-file edit.

## Success call stack (evaluate-only)
```
operator activates listener/automate session
  -> scripts.host_listener|host_automate
  -> player_presence.classify (FG Sims? cursor in client?)
  -> if PLAYER_PLAYING: YIELD_TO_PLAYER (stop)
  -> behavior_eval.evaluate_queue
  -> moodlets.evaluate_moodlets (supplied HUD strip; else SENSOR_NOT_SUPPLIED)
  -> sim_profile.evaluate_sim_profile (Simology/skills/likes/whims; else SENSOR_NOT_SUPPLIED)
  -> host_stack.evaluate_turn (event_balance + moodlet-aware indoor routing; sim_profile attachment)
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
| Cursor parked in edge pan band | `CAMERA_SAFE_REST` | park interior; withhold needs clicks |
| Lot scan without host camera plan | `CAMERA_SAFE_TRAVERSE` / `CAPTURE_BEFORE_EDGE_SCAN` | capture-first; never CONTINUOUS_EDGE_HOLD |
| Critical + fluff queue off-lot | `OPTIMIZE` + `MAP_TRAVEL` | never in-frame walk thrash |
| Player-directed queue | `EMULATE` only | never optimize away |

## State model
`INACTIVE` → (activate) → `ACTIVE` → tick loop → (deactivate) → `INACTIVE`
Presence per tick: `PLAYER_PLAYING` | `HOST_MAY_AUTOMATE` | `UNKNOWN_PRESENCE` (fail closed: yield).

## Proof ceiling
Offline matrix/listener/presence classification is **not** GAME_CERTIFIED. Live SendInput remains LOCAL_OBSERVED click dispatch until BI-002 hunger gates complete.

## 2026-11-07 — P95 human ↔ agent ↔ host control handoff (Trifecta)

**Terminal user value:** the operator can take the mouse/keyboard and **play immediately** without a host click fighting for the screen; when input has been idle long enough, an explicitly activated host session can *request* screen control again. "Pause" here means **pause BetterInstincts screen actions**, not pause The Sims simulation or cancel the player's queued interactions.

**Selected seam:** `betterinstincts/control_handoff.py` owns the single arbitration policy; `player_presence.classify` is its backwards-compatible projection, not a second source of truth. Existing `host_listener` and `host_automate` use it. `scripts/control_handoff.py` is a one-shot local-agent query, and `scripts/needs_force.py` enforces the gate at a real SendInput boundary. All receipts remain under the existing ignored `dist/` roots. Machine contract: `contracts/control-handoff.v1.json`.

### Competing options and choice

| Model | Why considered | Verdict |
| --- | --- | --- |
| Cursor-on-canvas or foreground-only ownership | Cheapest existing heuristic | **Reject as exclusive gate:** a parked cursor blocks host forever; moving it off-canvas does not establish human inactivity. |
| Global low-level mouse/keyboard hook or background watcher | Can distinguish more events | **Reject now:** violates the no hidden collection/daemon default, expands privacy and concurrency complexity; no gameplay need proven. |
| **Opt-in, global OS input-idle threshold + double fresh probe per one UI action** | Reuses existing Win32 snapshot; bounded and reversible; user always wins on fresh input | **Select:** 8-second default, individually configurable between 1 and 120 seconds, and repeatable by a local explicit-session agent without a background daemon. |

### Control state and call stacks

```text
HUMAN TYPES / MOVES / EXPLICIT PLAYER-DIRECTED QUEUE
  -> fresh desktop input-age / intent probe
  -> control_handoff.decide
  -> PAUSED_FOR_PLAYER (no new host screen action; Sims continues normally)

Explicit ACTIVE host_listener session + trusted desktop idle >= idle_ms
  -> control_handoff.decide (HOST_READY)
  -> local agent observes disposable save + scene + queue
  -> scripts.needs_force run --execute --session-id ID --step-id ONE_STEP --process-id PID
  -> recheck session + pre-focus probe
  -> guarded focus
  -> control_handoff.confirm (two fresh probes 0.2s apart)
  -> dispatch <= one specified host UI step
  -> stop, read new scene / player input before any further step
```

A RESTING cursor within the Sims window is not a permanent player lock when global inactivity is **verified**. Conversely, a player typing in another app is still active: the host must not steal focus. Missing age, ambiguous sensor, inactive session, operator playing, player-directed queue, or new input on the second probe all pause control. No screen-control admission can be carried forward to a batch of clicks; a self-generated host SendInput may reset the desktop idle clock, requiring fresh eligibility before the next step.

**Machine query:**
```sh
python -m scripts.host_listener activate --session-id bi002-control
python -m scripts.control_handoff --session-id bi002-control --process-id ACTUAL_PID --idle-ms 8000 --confirm
python -m scripts.host_listener tick --session-id bi002-control --process-id ACTUAL_PID --observation dist/game-host/OBSERVED.json
# Only after separate live scene, save and player-queue checks:
python -m scripts.needs_force run --location-kind home --process-id ACTUAL_PID --session-id bi002-control --step-id pause_live --idle-ms 8000 --execute
python -m scripts.host_listener deactivate --session-id bi002-control
```

Use a **real observed** disposable session, exact PID, and a valid bounded `host_listener` observation. Example `OBSERVED.json` is a locator placeholder, not a file created by this change. An agent may change idle time per use case but never below the contract minimum. `needs_force` sends **one** selected step per call, not a full scripted sequence; re-observe the scene before the next call. No click, save or package was performed by this GitHub-only change.

**P95 success prototype:** fake Win32 snapshots transition player input → PAUSED, settled idle → HOST_READY; host `--execute` path must have an ACTIVE session + exact PID + one step and reconfirm immediately before dispatch. **Failure prototype:** missing age, inactive session, player-directed queue, second-sample input or failed probe must yield without any click. No fake sensor can certify Live Mode.

**Boundary and next engineering integration:** This prototype gates `needs_force` SendInput and the listener/planner. Shared `--execute` adapters `funds_inject`, `menu_blockers`, `viewport_recover`, and `game_host navigate` (menu-blocker path) now require the same opt-in session + PID via `betterinstincts/screen_admit.py`. `host_menu` and CAS SendInput helpers remain outside this barrier; do not claim universal handoff until those paths are migrated and live-proved. Moving the game window/focus can itself disrupt an active user, hence pre-focus eligibility. Current screen arbitration proof is offline; BI-002 5+5 hunger A/B + rollback + player-queue review remain open.

**Reusable screen admission (issue #35 adapter lane):** `admitted_screen_lease` holds the exclusive per-PID lock and yields `ensure_ready()` for each UI step (session ACTIVE → preflight decide → optional one-shot focus → confirm). Admissions are never transferable across steps. CLI callers pass `--session-id` / `--idle-ms` with `--execute`.

**P124 mouse primitive owner (2026-11-07):** left-click / wheel / right-drag SendInput helpers for the shared host scripts live in `scripts/win32_input.py`. That module is **not** a substitute for `control_handoff` admission; it only removes duplicated Win32 structure so mouse dispatch has one edit site.

**Trifecta interpretation:** P08 live proof cannot run here without an authorized local game window; P82 uses paired synthetic inputs and interruption falsifiers; P07 implements reusable code, tests and repository integration. A full live pass must additionally prove *both* user interruption and subsequent idle resumption on a real disposable Sims game session, with zero host-input collision and an unchanged player queue.

**Agent ↔ host serialization refinement:** a single exclusive file lock per verified Sims PID under the ignored repo `dist/host-listener/` root prevents two cooperating executors from controlling the same game window concurrently. The action script holds it from before focus through the single click and receipt, and releases it normally. A competing `needs_force` execution fails `SCREEN_OWNER_BUSY`; the one-shot status CLI reports `PAUSED_FOR_AGENT` rather than claiming the host is ready. A stale lock **never expires automatically**: agents must establish the old owner is gone before a deliberate local recovery. This is an opt-in single-writer seam, not a system-wide OS mutex for unrelated desktop applications or unmodified legacy UI executors.

## 2026-11-07 — P95 Build/Buy optimize (Environment Gain + Eco Footprint)

**Terminal user value:** disposable-lab host can name and plan the **best** wall covering / Buy item for Lot Environment Gain and Eco Footprint objectives with deterministic catalog logic — not aesthetic guessing.

**Selected seam:** `betterinstincts/build_optimize.py` + `contracts/build-optimize.v1.json`; optional `host_stack` gate `BUILD_OPTIMIZE_EVALUATE_ONLY` when `build_objective` + `build_or_buy_mode` are supplied. CLI: `python -m scripts.build_optimize --objective MAXIMIZE_ENV --owned-packs base,GP02,EP20`. Full design: [BUILD_OPTIMIZE.md](BUILD_OPTIMIZE.md).

**Invariants:** player-directed yields; Green vs Industrial mutually exclusive; stacking per wall panel; `execute_allowed=false` until P08 disposable Build Mode apply proof; catalog rows require evidence_state (LOCAL_OBSERVED Brick & Plaster tooltip on Bargain Bend). Does **not** close BI-002 hunger.

## 2026-11-08 — Camera-safe traverse (P95 + P97 + trifecta)

**Terminal user value:** agents gather lot data without parking the mouse in the Sims edge-pan band so the camera does not keep scrolling while they develop.

**Selected seam:** `betterinstincts/camera_traverse.py` + `contracts/camera-traverse.v1.json`; `host_stack` gates `CAMERA_SAFE_REST` / `CAMERA_SAFE_TRAVERSE` / `CAPTURE_BEFORE_EDGE_SCAN`. CLI: `python -m scripts.camera_traverse`. Full design: [CAMERA_TRAVERSE.md](CAMERA_TRAVERSE.md). P97 adapts Automation/TokenCorridor observe≠act and adopts local PrintWindow rather than cloning CV donors.

**Invariants:** every plan ends at SAFE_CURSOR_REST; EDGE_MOUSE_PARK and CONTINUOUS_EDGE_HOLD are BAD_BEHAVIOR; execute uses existing screen_admit; no background camera daemon. Proof ceiling offline until disposable P08 park proof. Does **not** close BI-002.

## 2026-11-08 — Async needs and gardening session

`betterinstincts/host_tandem.py` owns only the in-flight action lifecycle over
`host_listener.tick`; the listener retains session/tick persistence, the existing
needs modules retain scoring, and the gardening peer retains action selection.
See [HOST_TANDEM.md](HOST_TANDEM.md) for ports, bounded coroutine overlap, exact
host ownership, safe preemption, outcome requirements and current proof ceiling.
