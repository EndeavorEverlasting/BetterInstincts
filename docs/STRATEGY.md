# P141 — strategic opportunity scout (refreshed 2026-11-06)

## Current facts
- Parent product gate remains **BI-002 hunger** (`plans/horizon.v1.json` `current_gate`); certified profiles **0**; live trials **0/5** vanilla and modified.
- Offline Mod Lab + bounded DBPF TGI index are on `main` (PR #7/#8/#9). Proof ceiling stays file metadata / index keys — not gameplay.
- Local Documents `GameVersion.txt` observed as `1.121.361.1020` (LOCAL_OBSERVED only). No Studio/install under common Program Files paths on this host → **BLOCKED_LOCAL_GAME_ACCESS** for BI-002.
- **Identity collision:** horizon/roadmap **BI-004 = recurring income**, while `plans/active/BI-004*` previously named the Mod Lab tooling sprint. `scripts/horizon_status.py` still emits `"income_gate":"BI-004"`. Agents conflating these IDs can mis-close gates.
- Prior 2026-10-20 scout selected hunger tuning; that product choice is unchanged. This refresh asks what deserves the **next offline investigation** while the game host is blocked.

## Design brief (tooling identity, not a UI)
- **Subject:** BetterInstincts lane labeling (horizon vs Mod Lab).
- **Audience:** local agents and maintainers reading plans/status JSON.
- **Job:** make income gate and Mod Lab impossible to conflate at a glance.
- **Upstreams (bounded):** `impeccable` — purpose clarity; `UP-A85AD9DC3` Diagram Design — lane storytelling; `UP-40FE662CF` no-mistakes — validate before push. No product chrome; IA/contracts only.

## Competing theses, falsification, and dispositions
| Thesis | Evidence | Leverage / timing | Cheapest disproof | Result |
| --- | --- | --- | --- | --- |
| A. Unblock BI-002 hunger on a real game host | Horizon `current_gate`, LIVE_CERT, zero trials | Highest product value | Game/Studio still absent | **SURVIVES as parent gate**; **BLOCKED** here — not the offline next mutation |
| B. Disambiguate Mod Lab sprint ID from horizon BI-004 income | Collision across ROADMAP, HORIZON, plans/active, handoff, status CLI | Stops wrong-gate closure; cheap; timing is now post-Mod Lab merge | If every consumer already names paths not IDs — falsified by `income_gate` + `plans/active/BI-004*` sharing the token | **SURVIVES; preferred next offline investigation** |
| C. Add cross-package TGI overlap candidates next | DBPF index now emits per-package keys | Natural Mod Lab depth | Without selected real Mods root / Studio compare, value is synthetic-only; overlaps are not conflicts | **DEFERRED** until B lands and an explicit Mods root is selected |
| D. Ship a Mod Lab GUI / dashboard | /design attached; CLI JSON exists | Visible product surface | Violates current “no cards/dashboard by default,” adds surface before game proof; AI-default risk | **REJECTED** as premature product chrome |
| E. Broad autonomy/scheduler rewrite offline | Horizon still unproven in game | Large future scope | Same rejection as 2026-10-20; external mods already target slices | **REJECTED** |

## Strategic choice
**B: rename the Mod Lab tooling lane to `BI-MODLAB` and keep horizon `BI-004` as income-only.** Confidence **HIGH** for the offline contract fix; does not claim game progress. Counterfactual: if a future tooling sprint needs a numeric ID, allocate outside BI-002…BI-008 (for example BI-009+) rather than reuse an income/skills/career gate.

Parent product recommendation remains **A** whenever a game-capable host and disposable save exist.

## Cheapest discriminating investigation
1. Move Mod Lab plans/dispatch/handoff to `BI-MODLAB*` and update references.
2. Add a regression that forbids an active Mod Lab dispatch sprint id equal to a horizon stage id.
3. Prove `python -m scripts.horizon_status` still reports `income_gate=BI-004` and `current_gate=BI-002`.
4. Leave BI-002 gameplay proof untouched.

**Route:** **P07** (bounded contract/docs/tests; strategic uncertainty resolved). Parallel **P124** on `betterinstincts/dbpf.py` readability only if behavior-preserving. Cross-package TGI overlap → later **P82** after explicit Mods root. Hunger → local game **P07/P08** when unblocked. This scout does not implement those successors beyond the selected B slice when a combined trifecta invocation authorizes immediate P07.

---

## 2026-11-07 — P141 scout: live-certification evidence seam, after PR #30

**Authority and operating lane.** Owner: BetterInstincts, based on the operator's 2026-11-07 parent brief. Host: GitHub repository research/writeback only; actual Sims process and certified trials belong to the Windows game-capable local agent. Base: `main` `9f238fb` (PR #30 merged). This is a **strategic scout and routed investigation**, not mod/package authorship, a new sensor implementation, or game certification. Preserve the 2026-11-06 Mod Lab lane-ID decision above as historical context; do not reopen its bounded sprint. Prompt identity: Moonwake `harness/exports/prompt-invocation-catalog.v1.json` → **P141 Repository Strategic Opportunity Scout**, definition owner `spec-architecture-prompts.v1.json`, source blob `5926a198a14567de55110ed19e922fc444b4dec7`.

### Parent objective retained in remote source

- **North star:** a free, community-native Sims 4 autonomy mod helping Sims meet needs, earn income, progress careers and enjoy their lives, without overriding manual control or personality.
- **Product quality:** believable competence, not robotic throughput. Leisure, rest, socializing, hobbies, traits and imperfect choices remain valuable; player direction always outranks automation.
- **Non-negotiables:** needs/safety outrank income; individual variation; configurable, individually defeatable and reversible behaviors; bounded performance; no save alterations, arbitrary user directories, telemetry, hidden background processes or mass changes.
- **Horizon dependency:** all six adult needs → six-need balance → observed steady income while maintaining needs → observed skill growth while preserving income/needs → career advancement. Keep patch-specific certification immutable. **Needs → income → skills → career** is the operator's priority, not a suggested optimization.
- **First product win:** BI-002 hunger on an exact game patch with reversible authored package, ≥5 vanilla and ≥5 modified genuine observations, rollback, player-queue safety, and maintainer review. A green CI check, high evaluator score, or offline policy never establishes a playable mod.

Canonical machine owners: `plans/horizon.v1.json`, `plans/active/BI-002.execution.v1.json`, `docs/HORIZON.md`, `docs/LIVE_CERT.md`; this dated scout is a decision receipt, **not** a second product roadmap.

### Repository situation and opportunity signals

**CURRENT FACT — verified from remote `main` at scout time:** PR #30 integrated progression evaluation and its CI gate. `docs/PROGRESSION_EVAL.md` separates `vision_marker_rate`, `scaffolding_rate`, `product_progression_rate`, `hunger_trial_rate`, `ci_game_gap`; current recorded floor is vision 1.0, scaffolding 1.0, product 0.0, hunger trials 0.0. `docs/HOST_EVAL.md` contains a deterministic boot → chosen LAB save → map/Live journey evaluator, scene/viewport checks and queue-safety regressions, but explicitly says its fixtures are offline. `docs/GAME_HOST.md` and `docs/LEDGER.md` report **local-agent-observed** Live Mode on patch `1.121.361.1020`; that is a historical local receipt, **not an observation by this GitHub-only scout**. No qualifying 5+5 hunger gameplay study or reviewed, game-certified profile exists. `scripts/live_cert.py` has a bounded manual record/attest/evaluate workflow; a numeric pass still requires maintainer review.

**DERIVED PATTERN:** host navigation/scene recovery, player-presence checks, offline evaluator scoring and manual live-cert recording are separately present, but their **evidence handoff into one actual BI-002 hunger trial is unproven**. The most valuable missing seam is trustworthy, player-safe real-game measurement, not another generalized simulated policy. `FULL_CLIENT_BLACK` and Build/Buy stuck regressions show why observing the correct scene and retaining a rollback path precede any hunger action.

### Five competing theses and attempted falsification

| Thesis | Evidence; leverage; timing | Cheapest falsifier or alternative explanation | Cost / complexity; unlock | Disposition |
| --- | --- | --- | --- | --- |
| **A. Qualify one actual hunger observation through existing host → live-cert workflow** | Game host reached Live on the reported patch; host/scene evaluator and live-cert CLI already exist; product progress remains zero. Immediate BI-002 leverage. | A safe, explicit disposable-save session cannot reliably identify Live, hunger change, baseline time and player queue; or the existing CLI already has complete qualifying gameplay evidence. No such complete evidence is recorded. | Low-to-medium local game effort; makes 5+5 and package/rollback comparison practical without new general engine. | **SURVIVES — SELECT** |
| **B. Expand synthetic evaluators across income, skills and career now** | Strong P67/P62 scaffolding creates easy places for fixtures and scorecards. | New fixtures do not increase `product_progression_rate` or prove Sims actions; existing coverage is already high. | Low-medium code cost but high opportunity cost; product uncertainty unchanged. | **WEAKENED** |
| **C. Build a continuous generalized listener/agent autopilot** | `HOST_AUTONOMY.md` defines opt-in player-presence, EMULATE/OPTIMIZE and MAP_TRAVEL. | No verified game-safe need-actuation or player override proof; a continuous loop could conflict with agency/performance. Bounded manual actions may suffice. | High complexity and gameplay risk; could unlock later opt-in behavior. | **DEFERRED** |
| **D. Start autonomous earnings/skills/careers before hunger cert** | High owner value downstream. | Explicit horizon prerequisites and no needs-balancing/game income proof; a funds cheat receipt is not earned income. | High causality/confound risk; unlock only after needs measured. | **REJECTED for current gate** |
| **E. Replace host/evaluators with one unified engine** | Several host, progression and live-cert interfaces now exist. | Distinct proof ceilings are deliberate; unification may silently convert offline signals into false live claims. A thin evidence mapping may solve the seam. | High regression risk; architectural cleanup could matter later. | **WEAKENED / defer redesign** |

### Strategic comparison and one selected investigation

| Surviving direction | Evidence strength | Parent leverage | Reversibility / dependency | Measurability | Decision |
| --- | --- | --- | --- | --- | --- |
| **A: first qualified live hunger observation** | High on existing tools; direct live hunger evidence absent | **Directly unlocks BI-002** | Disposable save, no save writes, only explicit local consent; requires real game + precise version | Baseline trace, hunger/timing/queue/capture refs | **SELECT — HIGH confidence on priority; game outcome UNKNOWN** |
| B: more evaluator fixtures | High that offline evaluator exists, low on product impact | Indirect | Easily reversible, no game required | Test counts but not gameplay | Not selected |
| E: unified engine | Medium existence, low need for rewrite | Indirect | Larger risk and interface churn | Must first show evidence-loss defect | Not selected |

**Recommended thesis:** close the **real-game observation-to-certification seam** using existing scene/host evaluators and `live_cert` before writing another generic engine or attempting downstream autonomy. This is not a new certification standard; follow `docs/LIVE_CERT.md`.

**Cheapest discriminating investigation (next owning contract: P07 / BI-002 GAME-1, local game-capable agent):**
1. Read `AGENTS.md`, `docs/GAME_HOST.md`, `docs/HOST_EVAL.md`, `docs/LIVE_CERT.md`, `docs/SCENE_INTELLIGENCE.md`, `plans/active/BI-002.execution.v1.json`; establish **fresh** Sims PID and exact full patch (historical PID 66096 and version are not current-process proof).
2. On an **explicitly operator-authorized disposable LAB save only**, reach Live with two independent cues and a nonblack content capture. If scene unknown, black, Build/Buy, or active player input, **abstain/recover safely**, not a hunger click. Never Resume or inspect/modify a user save.
3. Observe **one genuine vanilla hunger case** with before/after evidence: timed beginning of eating, minimum hunger, queue interruption, lag/loops/exceptions, capture reference, patch/platform and selected-Sim state. Do not fabricate motive measurements from screenshots, use cheat subsidy as income, or treat host click-dispatch as changed game behavior. Use manual observation when no trusted sensor exists.
4. Initialize/record it via `python -m scripts.live_cert` **only after actually observed**, then run `status`; audit what evidence can be independently reviewed. If sensing is insufficient, preserve an explicit `SENSOR_NOT_SUPPLIED` / `INCONCLUSIVE` finding and route one narrow P95 interface decision; do not add generalized AI.
5. **Discriminating decision:** **PROMOTE** A to the remaining BI-002 5+5/reversible package path if one baseline observation is reproducible, attributable, and player-safe; **WEAKEN** if only manual timing is credible and needs narrowly scoped capture; **REJECT** any unsafe actuation, save ambiguity or player-queue collision; **INCONCLUSIVE** if local game/runtime cannot be reached. None certifies BI-002 until full gameplay and maintainer review.

**Route:** **P07** for the bounded existing BI-002 local game investigation. P82 is **NOT admitted** now: no valid same-patch live baseline/comparator or falsifiable mod-effect dataset yet, and building an offline substitute would not change the product decision. Re-enter P82 for a *single measured hunger tuning hypothesis* once baseline and actual source/resource are observed. Use P95 only on a demonstrated narrow host/observation interface ambiguity; P97 only for exact external tuning prior art needed by that implementation. The scout itself stops here.

**Not now:** broader listener daemon; unbounded Sims AI rewrite; income/skills/career; feature-rich dashboards; unified-evaluator rewrite; adding another planner instead of a hunger observation.

**Proof ceiling:** P141 strategic comparison **recorded in Git**, not live-executed; source files, PR #30 merged status, repository test descriptions and Cursor-provided counts do not prove a playable package. No game process, exact *currently running* patch, personal save, first hunger observation or maintainer review was accessed from this environment. First parent gate remains `BI-002` / `HUNGER_LIVE_CERTIFIED`.

---

## 2026-11-07 — P141 scout: post handoff + Sit-and-Chat floor (interrupt-safe)

**Authority.** Operator invoked **P124 then P141** after PR #34 handoff merged and issue [#35](https://github.com/EndeavorEverlasting/BetterInstincts/issues/35) opened; floor also absorbed PR #38 Sit-and-Chat indoor grounding (`main` `5d30fe1` at scout start). Prompt identity: TokenCorridor `spec-architecture-prompts.v1.json` blob `5926a198a14567de55110ed19e922fc444b4dec7` → **P141**. This scout does **not** implement the selected initiative. Prior scouts above remain historical; this refresh answers what deserves the next bounded investigation **while the operator is actively building** (interruptability required; no host screen contention).

### Situation model

**CURRENT FACT:** `control_handoff` + exclusive per-PID lock gate `needs_force` SendInput and listener/planner paths; offline Trifecta tests and post-merge CI for PR #34 passed. Direct adapters `game_host` / `host_menu` / `funds_inject` / `viewport_recover` / `menu_blockers` (and CAS helpers) still issue SendInput outside that barrier ([HOST_AUTONOMY.md](HOST_AUTONOMY.md) boundary; issue #35). Sit-and-Chat is host-guidance only; live pie-menu dispatch remains OPEN. BI-002 certified profiles and hunger trials remain **0**. Live Sims process observed locally during scout (PID example 66096) with operator actively using the UI — host must yield.

**DERIVED PATTERN:** The product bottleneck is no longer “missing arbitration design”; it is **uneven adoption + unproven live interruption/resume**, under a moving feature floor. Offline structural clarity of SendInput primitives (P124) reduces the cost of the next gate wrap without claiming P08 or hunger proof.

### Competing theses

| Thesis | Evidence; leverage; timing | Cheapest falsifier | Disposition |
| --- | --- | --- | --- |
| **A. Run issue #35 P08 live handoff sequence now** | Mandatory acceptance; only path that proves human↔host transfer | Operator is mid-build / recent input; running confirm/focus would fight for the screen | **SURVIVES as mandatory gate**; **BLOCKED_OPERATOR_BUSY** until explicit idle + disposable-save consent |
| **B. Wrap remaining shared-control SendInput adapters under the same opt-in session + PID lock + idle recheck** | Issue #35 adapter lane; HOST_AUTONOMY boundary; duplicated click code was the P124 hotspot | If every execute path already imports `control_handoff` — falsified by inventory | **SURVIVES — SELECT** as next offline-safe investigation |
| **C. First BI-002 vanilla hunger observation** | Still parent product gate; prior scout selected this | Same interrupt/busy and missing 5+5 package readiness; handoff incompleteness confounds hunger UI steps | **SURVIVES as parent**; **DEFER** as *next* mutation while adapters remain ungated and operator builds |
| **D. Live Sit-and-Chat pie-menu SendInput** | PR #38 guidance landed; outdoor-social pain is real | Competes with handoff coverage; still not hunger cert | **DEFER** until B’s barrier exists for that click path |
| **E. Broad autonomy / unified host engine rewrite** | Multiple host modules exist | Explicit prior rejection; risk of false live claims | **REJECTED** |

### Decision matrix (no fake scores)

| Direction | Parent leverage | Interrupt-safe now? | Reversibility | Select? |
| --- | --- | --- | --- | --- |
| A P08 live handoff | Direct UX proof for #35 | **No** while building | High if disposable save | Wait for operator idle |
| **B adapter barrier adoption** | Makes A and hunger UI steps trustworthy | **Yes** (code/tests only) | High; per-adapter | **YES** |
| C hunger observation | Closes BI-002 | No while building / ungated clicks | Medium | Later |
| D Sit-and-Chat live | Event quality | No | Medium | Later under B |
| E rewrite | Indirect | n/a | Low | No |

**Selected thesis (HIGH confidence on priority):** finish **shared handoff protection on remaining direct-screen adapters** (issue #35 adapter coverage), using the P124 `scripts/win32_input` owner as the single mouse primitive seam — **without** claiming universal handoff or BI-002 closure. Live P08 (thesis A) remains mandatory and is the first action when the operator is idle on an authorized disposable lab save.

**Cheapest discriminating investigation → route P07** (strategic uncertainty for the adapter lane is resolved; design already in HOST_AUTONOMY / control_handoff):
1. Inventory every `--execute` SendInput caller; mark covered vs pending.
2. Port `host_menu`, `menu_blockers`, `funds_inject`, `viewport_recover` (and other applicable shared-control paths) through session ACTIVE + `exclusive_screen_owner` + pre/post-focus `confirm`, preserving Build/Buy/CAS fail-closed behavior and never forcing Live while the operator builds.
3. Focused offline regressions per adapter + one protected control that dry-run still plans without clicking.
4. Stop before live focus/click unless the operator explicitly frees the screen for issue #35 P08.

**Not now:** income/skills/career; listener daemons; CAS absolute-input maze migration beyond the shared left-click owner; treating P124 dedupe as live proof.

**Proof ceiling:** scout + P124 readability refactor only. No P08 live sequence was executed against the building session. Parent gate remains BI-002 hunger certification.

---

## 2026-11-07 — P141 scout: post need-services mainline + branch hygiene (P03)

**Authority.** Operator invoked **P03 → P141 → P124 → /trifecta** after observing unclean branch integration. Prompt identities: TokenCorridor `base/prompts.json` blob `848728632c1243ebba023fa0012292a2ad33cada` → **P03 Repository Evidence + First Sprint Executor**; `spec-architecture-prompts.v1.json` blob `5926a198a14567de55110ed19e922fc444b4dec7` → **P141** / **P124**. Floor: `main` after PR #52 (six-need tandem + LB) and PR #53 (LB glossary).

### FACTS (P03 harvest, abbreviated)
- Center of gravity: tandem need services + load-balance health on `main`; domain-cascade peer owner staged/committed on `feat/bi-domain-cascade-20261107`.
- Fully merged remotes deleted: `feat/bi-need-services-tandem-20261107`, `feat/bi-need-lb-glossary-20261107`, `feat/bi-host-evaluator-20261107`, `feat/bi-game-host-launch-receipts-20261106`, `docs/bi-game-host-p04-canonical-handoff-20261106`, superseded `feat/bi-need-load-balance-health-20261107`, glossary-duplicate `feat/bi-adapter-handoff-barrier-20261107`.
- Remaining diverged remotes still hold unique/unmerged history (p95 handoff, p97 listener, scene-map, modlab, live-baseline, etc.) — do not mass-delete without per-branch salvage review.
- Stash/WIP still carries `screen_admit.py` and adapter script touches for issue #35; curious-catalog worktree at pre-#52 tip.

### Competing theses
| Thesis | Evidence | Offline-safe? | Result |
| --- | --- | --- | --- |
| A. BI-002 hunger live cert | Parent gate; 0/5 trials | No without operator Live | **SURVIVES as parent**; not this mutation |
| B. Land domain-cascade peer owner on main | Committed local; joins LB without second needs queue | Yes | **SURVIVES — execute now via trifecta** |
| C. Finish issue #35 `screen_admit` + adapter wraps | Prior P141 selection; untracked `screen_admit.py` | Yes offline | **SURVIVES — next after B** |
| D. Bulk-delete remaining remote branches | Many still diverge with unique commits | Risky salvage | **REJECT mass delete**; salvage case-by-case |
| E. Curious catalog product surface | Separate worktree; not on main | Yes later | **DEFER** behind C |

**Selected thesis:** **B then C** — integrate domain cascade (P124 already factors it as peer owner; reuse `need_service_base` for need parsing), then resume adapter screen-admit. Parent A unchanged.

**Route:** trifecta P08/P82/P07 on domain cascade → then P07 on `screen_admit` adapters. P08 live remains OPEN / operator-gated.
