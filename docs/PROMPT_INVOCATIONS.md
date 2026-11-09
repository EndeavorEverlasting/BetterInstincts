# Canonical TokenCorridor prompt invocations — 2026-10-20

Do not treat this as a local Prompt Kit or substitute repository. Source of truth: private **EndeavorEverlasting/TokenCorridor**, file `harness/exports/prompt-invocation-catalog.v1.json`, fetched at blob SHA `8c281379ba7ccc871947391233b1db72f4a108ef`. TokenCorridor canonical invocation resolver: `scripts/prompt_invocation_resolver.py`; IDs were selected using exact catalog matches, not inferred from titles.

| ID | Verified title | Canonical prompt definition owner | Source blob SHA | Invoked in BI-001 as |
| --- | --- | --- | --- | --- |
| P07 | Repo Sprint Executor | `src/tokencorridor/interface/promptkit/registry/base/prompts.json` | `848728632c1243ebba023fa0012292a2ad33cada` | Implement, validate, commit, PR, integrate scoped horizon code |
| P82 | Prototype-Measure-Refine Delivery Loop | `src/tokencorridor/interface/promptkit/registry/prompts/spec-architecture-prompts.v1.json` | `5926a198a14567de55110ed19e922fc444b4dec7` | Six-needs policy hypothesis, measurable offline prototype; `docs/HORIZON_DECISIONS.md` |
| P01 | Harness Infrastructure Builder | `src/tokencorridor/interface/promptkit/registry/base/prompts.json` | `848728632c1243ebba023fa0012292a2ad33cada` | 2026-11-07 ontology preflight and CI operational infrastructure — `scripts/semantic_preflight.py`, `scripts/check_ontology.py` |
| P00 | Governance Doctrine Installer | `src/tokencorridor/interface/promptkit/registry/base/prompts.json` | `848728632c1243ebba023fa0012292a2ad33cada` | AGENTS.md, docs/DOCTRINE.md, validator and CI: multiversion preservation |
| P97 | Open-Source Prior-Art & Gap Analyst | `src/tokencorridor/interface/promptkit/registry/prompts/spec-architecture-prompts.v1.json` | `5926a198a14567de55110ed19e922fc444b4dec7` | docs/PRIOR_ART.md: reference implementation, gap map and adoption decisions |
| P141 | Repository Strategic Opportunity Scout | `src/tokencorridor/interface/promptkit/registry/prompts/spec-architecture-prompts.v1.json` | `5926a198a14567de55110ed19e922fc444b4dec7` | docs/STRATEGY.md: compare/falsify competing theses, select next investigation |
| P04 | [PARALLEL] Repo-Aware Sprint + Harness Factoring Distributor | `src/tokencorridor/interface/promptkit/registry/base/prompts.json` | `848728632c1243ebba023fa0012292a2ad33cada` | plans/active/BI-001.md: runtime partition, safe owner lanes, proof/gates |
| P95 | Program Design & Call-Stack Prototype Architect | `src/tokencorridor/interface/promptkit/registry/prompts/spec-architecture-prompts.v1.json` | `5926a198a14567de55110ed19e922fc444b4dec7` | 2026-11-08 countertop mechanics + Env-max island hierarchy (`docs/BUILD_OPTIMIZE.md`) + build-yield category pools + balance/imbalance + aspiration + career + camera-safe traverse + library-save-before-room-mutate + build spatial/integrity/house-state |
| P83 | Agent Work Verifier & Iterative Advancer | `src/tokencorridor/interface/promptkit/registry/prompts/repository-work-ledger-prompts.v1.json` | `e1d571b5490a68292c1953dd7b1ecf6ee28fe96c` | 2026-11-08 Build verification; 2026-11-09 cross-worktree input locking and reversible-uninstall independent review (`docs/ASYNC_INTEROP.md`) |
| P78 | Repository Glossary & Documentation Diet | `src/tokencorridor/interface/promptkit/registry/prompts/spec-architecture-prompts.v1.json` | `5926a198a14567de55110ed19e922fc444b4dec7` | 2026-11-07 preserve existing `contracts/glossary.v1.json` as vocabulary owner and `contracts/ontology.v1.json` as graph owner |

| P67 | Repository Eval Framework Builder | `src/tokencorridor/interface/promptkit/registry/prompts/ai-engineering-level-up-prompts.v1.json` | `5350ce61085e748ab219fa482e25d70517b10e0f` | 2026-11-07 progression/CI honesty eval pyramid — see docs/PROGRESSION_EVAL.md |
| P62 | Skill Correctness and Efficiency Eval Implementer | `src/tokencorridor/interface/promptkit/registry/prompts/skill-development-prompts.v1.json` | `7ef8e6991f558db191989c495d9255a282f88ba9` | 2026-11-07 vision/scaffolding/product rates + forbidden promotion cases — see `betterinstincts/progression_eval.py` |
| P124 | Repository Code Readability & Structural Refactorer | `src/tokencorridor/interface/promptkit/registry/prompts/spec-architecture-prompts.v1.json` | `5926a198a14567de55110ed19e922fc444b4dec7` | 2026-11-08 build_optimize single-owner pools + countertop mechanics (no second catalog daemon); balance_service reuses survival_critical; need_service_base + domain_cascade; prior moodlets/event_balance |

## 2026-11-09 skill-force trait OK + keybd typing (P95 + Trifecta)

**P95/P124** keep one `diy_skill_force` owner: v3 adds `ACCEPT_OFFERED_REWARD_TRAIT`
and `type_text` keybd_event typing. Consultation
`BI-SKILL-FORCE-TRAIT-ACCEPT-20261109.v1.json`. **P82** offline tests in
`tests/test_diy_skill_force.py`; **P07** integrate; **P08** live OK on offered
traits + multi-Sim full_unlock remains open beside concurrent live-cert.

## 2026-11-09 full skill unlock ladder (extend diy_skill_force)

**P95/P124** expand the existing skill-force owner with `full_unlock` (adult
Major_* at level 10) so Sims are not blocked from activities/unlockables.
Preserves `diy_maker`. Consultation:
`contracts/consultations/BI-SKILL-FORCE-FULL-UNLOCK-20261109.v1.json`.

## 2026-11-09 DIY skill-force for Servos / Handiness / Robotics (P95 + P124 + Trifecta)

Resolved **P95 — Program Design & Call-Stack Prototype Architect** and
**P124 — Repository Code Readability & Structural Refactorer** (Moonwake /
TokenCorridor `spec-architecture-prompts.v1.json`, blob
`5926a198a14567de55110ed19e922fc444b4dec7`). **P95** selects
`DIY_SKILL_FORCE` (maker skill cheat planner; active-Sim selection; bundles
`diy_maker` / `servo_core`). **P124** peers beside `funds_inject` without
rewriting `sim_profile`. Trifecta: **P82** offline falsifiers in
`tests/test_diy_skill_force.py`; **P07** source integration; **P08** live
Skills-panel confirmation remains independently gated. Consultation:
`contracts/consultations/BI-DIY-SKILL-FORCE-20261109.v1.json`.

## 2026-11-09 click-error eval + Escape-cancel on chrome miss trifecta

**P95** designed `POST_CLICK_VERIFY_ESCAPE_CANCEL`: score intended ui_chrome
targets vs observed client pixels (HIT/NEAR_MISS/MISS, ABOVE_TARGET,
LOT_PUNCH_THROUGH_RISK); non-HIT → Escape-cancel via CANCEL_HOLD. Remapped
`catalog.search_field` 1920×1080 to client ≈(140,864). **P124** peer
`click_error_eval` beside `ui_chrome` / `screen_atlas` (evaluate + recovery plan
only; no SendInput). **P82** measured above-search lot punch-through →
ESCAPE_CANCEL in `tests/test_click_error_eval.py`. **P08** live click attest
remains OPEN. Consultation:
`contracts/consultations/BI-CLICK-ERROR-EVAL-20261109.v1.json`.

## 2026-11-09 host UI chrome map + AOK inventory recipe trifecta

**P95** designed `UI_CHROME_PEER_MAP`: normalized Build/Buy chrome targets,
per-mode hotkey glossary, Live panel stubs (needs/career/skills/phone), and
`catalog_to_household_inventory` with preferred search **AOK**. **P124** peer
`ui_chrome` beside `ui_mode` / `household_object_force` (no vision clicker
daemon). **P82** measured AOK term, Buy/Build-only deposit, profile fail-closed,
and Backspace hotkey glossary in `tests/test_ui_chrome.py`. **P08** live click
calibration remains OPEN. Consultation:
`contracts/consultations/BI-UI-CHROME-MAP-20261109.v1.json`.

## 2026-11-09 build floor activity listener trifecta

**P95** designed `FLOOR_ACTIVITY_CENSUS`: active story, SINGLE vs MULTI floor
span, per-floor themes from attested item categories, advisory
`build_optimize` hints. **P124** peer module `build_floor_activity` consumed by
`host_listener` (no second spatial daemon). **P82** measured kitchen/single,
bedroom+living/multi, skip-when-not-build, and listener tick attachment in
`tests/test_build_floor_activity.py`. **P08** live wall-up / story chrome sensor
remains OPEN. Consultation:
`contracts/consultations/BI-BUILD-FLOOR-ACTIVITY-20261109.v1.json`.

## 2026-11-08 household useful-item force catalog trifecta

**P95** designed the reusable household object-force call stack: elementary
`bb.showhiddenobjects` unlock for catalog/hidden list items, `careers.promote`
Household Inventory deposits for career rewards, optional BBB UX only (never a
substitute), forbidden hallucinated `gsi_create_obj` hex. **P124** factored as a
sibling to `funds_inject` / `curious_catalog` / `hidden_object_discovery` rather
than a second spawn daemon. **P82** measured elementary-unlock refusal, BBB
substitution refusal, career-only skip, and full-catalog plan commands in
`tests/test_household_object_force.py`. **P08** live promote/search deposit
remains OPEN. Consultation:
`contracts/consultations/BI-HOUSEHOLD-OBJECT-FORCE-20261108.v1.json`.

## 2026-11-08 countertop mechanics + Env-max island hierarchy trifecta

**P95** designed machine-readable countertop placement (standard vs island, gear
shapes/corners, barstool-only snap, Env cap 2) and seeded the attested island
hierarchy inside the existing Build/Buy yield owner. **P124** expanded
`build_optimize` in place rather than spawning a surfaces daemon. **P82** measured
ALLOW/DENY seating snap, career-lock exclusion, and default Env-2 island heads in
`tests/test_build_optimize.py`. **P08** live place/snap/Sim pathing remains OPEN.
Consultation: `contracts/consultations/BI-COUNTERTOP-MECHANICS-20261108.v1.json`.

## 2026-11-08 build-yield category pools trifecta

**P95** designed per-category best-value pools across environment, neighborhood, and
bill axes inside the existing Build/Buy yield owner. **P124** expanded
`build_optimize` in place rather than spawning a parallel catalog service.
**P82** measured dual 2/2 wall heads, efficient appliance/light bill heads, and
null-axis skip falsifiers in `tests/test_build_optimize.py`. **P08** live paint /
bill meters remain OPEN. Consultation:
`contracts/consultations/BI-BUILD-YIELD-MICROSYSTEM-20261108.v1.json`.

**Resolution is not execution.** Artifacts prove these workflows were applied to this initial sprint; no TokenCorridor CLI execution, full compliant remote parallel-worker receipt, or installed `/trifecta` skill is claimed. In BI-001 the branch-writer is one GitHub provider lane. Do not copy proprietary/private Prompt Kit contents into this public repository; this file contains only invocation identities and evidence pointers. Refresh exact provenance from TokenCorridor on subsequent work instead of trusting this snapshot indefinitely.

## 2026-11-08 balance/imbalance microsystem trifecta

**P95** designed sticky `BALANCE_SERVICES_TANDEM` beside need/career/aspiration/
gardening for Enchanted by Nature Balance meter + ailments. **P124** factored
into existing `survival_critical`, moodlets, and gardening owners rather than a
second wellness daemon. **P82** measured nature-first Imbalanced, Naturopath
Very Imbalanced + Burning Passion, survival suspend, and sticky continuity
falsifiers in `tests/test_balance_service.py`. **P08** live Naturopath/Holistic
Cure remains OPEN on the local game host. **P07** owns implementation/integration
of `balance_service` + host wiring. Consultation predates mutation:
`contracts/consultations/BI-BALANCE-MICROSYSTEM-20261108.v1.json`.

## 2026-11-08 aspiration microsystem trifecta

**P95** designed sticky `ASPIRATION_SERVICES_TANDEM` beside need/career services for
OK/Cancel judgment on aspiration and life-state dialogs (Mother Nature / Fairy).
**P82** measured disabled-Cancel, occult-unready-Cancel, and sticky-prompt falsifiers
in `tests/test_aspiration_service.py`. **P08** live Cancel on the Mother Nature dialog
remains OPEN on the local game host. **P07** owns implementation/integration of
`aspiration_service` + host wiring. Consultation predates mutation:
`contracts/consultations/BI-ASPIRATION-MICROSYSTEM-20261108.v1.json`.

## 2026-11-08 career microsystem trifecta

**P95** designed sticky `CAREER_SERVICES_TANDEM` beside need_services for teen homework
continuity. **P82** measured suspend/resume/complete falsifiers in
`tests/test_career_service.py`. **P08** live homework completion remains OPEN on the
local game host (offline proof only). **P07** owns implementation/integration of
`career_service` + host wiring. Consultation predates mutation:
`contracts/consultations/BI-CAREER-MICROSYSTEM-20261108.v1.json`.

## 2026-11-07 exact invoked order

Current Moonwake catalog read at `harness/exports/prompt-invocation-catalog.v1.json` and current root `AGENTS.md`: **P97 — Open-Source Prior-Art & Gap Analyst** (`spec-architecture-prompts.v1.json`, blob `5926a198a14567de55110ed19e922fc444b4dec7`) → **P95 — Program Design & Call-Stack Prototype Architect** (same owner/blob) → Trifecta sequence **P08 live proof → P82 measured prototype → P07 bounded implementation**, with real Windows runtime proof deferred to local host rather than forged in CI; then **P04 [PARALLEL] Repo-Aware Sprint + Harness Factoring Distributor** (`base/prompts.json`, blob `848728632c1243ebba023fa0012292a2ad33cada`) for local-agent ownership/handoff. The P97/P95/P82/P07 implementable offline work and tests are in `docs/JUDGMENT_LEARNING.md`; P08 remains a separately observable game task. Do not equate canonical prompt identity retrieval with a live launch of a local agent.

## 2026-11-07 ontology-first semantic sprint and final P04

Moonwake current source `AGENTS.md`, deterministic resolver `scripts/prompt_invocation_resolver.py`, and exact exported 144-prompt catalog `harness/exports/prompt-invocation-catalog.v1.json` (blob `8c281379ba7ccc871947391233b1db72f4a108ef`) were read. Actual applied order: **P00 governance** → **P01 harness** → **P141 strategic alternatives** → **P124 ownership/readability** → **P95 thin evaluate-only architecture** → **P78 glossary authority**, with Trifecta's current-runtime P82/P07 verification/integration and real-game P08 deferred to the local host. **Only after source integration** was **P04** created as `docs/handoff/BI-SEMANTIC-ONTOLOGY-P04-2026-11-07.md` and its typed execution plan. PR #57 merged to `main` `091fa6d2ae49de54fd3536b8f7aa6913006df49d`; post-merge CI run `42423191457` passed. The P04 handoff records game trial and maintainer review as unproven. Moonwake's generic parallel-dispatch CLI and schema were not found at the documented paths in current `main`, so its invocation/execution is **not** asserted; the BetterInstincts typed plan is the local agent transport.

## 2026-11-07 P04 — hidden-item operator playbook routing

P04 remains the canonical Moonwake **[PARALLEL] Repo-Aware Sprint + Harness Factoring Distributor**, *not* an invented Sims-specific prompt. BetterInstincts `AGENTS.md` now requires every P04 inventory to inspect `plans/active/BI-HIDDEN-OBJECTS.P04.md` and run `python -m scripts.hidden_object_discovery guide` to retrieve the canonical five-step recipe. The machine dispatch `plans/active/BI-HIDDEN-OBJECTS.dispatch.v1.json` owns local-host work placement; `python -m scripts.hidden_object_discovery audit --observation dist/game-host/hidden-object-p04-receipt.json` enforces receipt shape; CI `scripts/check_hidden_object_p04.py` guards the route and ordered instructions. This applies directly when the parent objective concerns hidden items; otherwise it is inventoried/deferred rather than creating a side quest. These are repository contracts, **not** a verified invocation of Moonwake's own agent dispatcher or a claim that a Windows game session was accessed.


## 2026-11-09 — game mode and menu context microsystem

Current Moonwake catalog verified at `harness/exports/prompt-invocation-catalog.v1.json` blob `8c281379ba7ccc871947391233b1db72f4a108ef`. **P95** selects a thin scene-backed F1/F2/F3 evaluator, reusing `scenes.classify` and honest declared cue status. **P124** factors a separate read-only `ui_mode` projection without a second screen detector, daemon or host listener. Trifecta: **P08** remains a local exact-build screenshot/overlay calibration gate, **P82** implements offline candidate/negative tests, and **P07** owns bounded source integration and CI. Ontology consultation `contracts/consultations/BI-UI-MODE-CONTEXT-20261109.v1.json` was committed before code. Detailed call flow: `docs/UI_MODE.md`. Passing offline tests cannot certify real Live/Buy/Build recognition.

## 2026-11-09 whole-house room census — corrected P95/P124/P78 + Trifecta

Current Moonwake catalog `harness/exports/prompt-invocation-catalog.v1.json` (blob `8c281379ba7ccc871947391233b1db72f4a108ef`) resolves **P78 — Repository Glossary & Documentation Diet**, alongside P95 and P124. The prior `P178` attribution was a voice-transcription error; **P178 was not invoked**. The original pre-prototype consultation remains unmodified as an audit record.

**P95:** read-only room-census architecture over revisioned `house_state`. **P124:** reuse `build_floor_activity` and the existing host listener, not a new daemon. **P78:** consolidate duplicated room documentation, keep glossary terms and executable owners discoverable; preserve only the unique offline runbook and P08 live proof boundary.

**Trifecta:** **P82** measured tests and negative controls in `tests/test_room_census.py`; **P07** committed integration and GitHub CI; **P08** exact-build game room/boundary/object sensor certification remains unproven on this cloud runtime. Full functionality and glossary regression are separately verified by CI, not by an invented gameplay receipt.


## 2026-11-09 screen atlas / camera-safe Playwright-hosted action (PR #90)

**P95** prototyped the existing scene/host-menu inventory → mode/UI chrome → exact calibrated target → fresh independent host observation → cooperative queue checkpoint → one click → checkpoint → safe interior rest call stack; failure paths include active operator, stale scene, wrong patch/profile, unknown save permission and partial click. **P124** keeps the atlas as a composition peer rather than another screen daemon or duplicate console/key catalog. The **Trifecta** applies pre-prototype ontology consultation, focused negative simulation and GitHub PR CI/main integration. **P08 live evidence remains OPEN**: calibrated native Sims input and camera-no-pan proof must not be inferred from browser-mock tests. Owners: `docs/SCREEN_ATLAS.md`, `contracts/screen-atlas.v1.json`, `betterinstincts/screen_atlas.py`, `tests/test_screen_atlas.py`; consultation `BI-SCREEN-ATLAS-SAFE-REST-20261109`.

## 2026-11-09 P95 hover tooltip temporal learning

Resolved P95 exactly from Moonwake current main prompt-invocation catalog: Program Design & Call-Stack Prototype Architect (owner spec-architecture-prompts.v1.json, source blob 5926a198a14567de55110ed19e922fc444b4dec7). The prototyped program seam is an ACTIVE host_listener session -> opt-in semantic tooltip event -> pure hover_learning reducer -> bounded 3/5/10/30/60-minute reviewed association projection. No new mouse hook, daemon, duplicate trainer or SendInput permit. Ontology consultation precedes behavior source commits: contracts/consultations/BI-HOVER-TEMPORAL-20261109.v1.json. Tests: tests/test_hover_learning.py. Remaining game sensor and human-reviewed outcomes require local-host evidence. See docs/HOVER_LEARNING.md.

## 2026-11-09 — P95 + Trifecta hotkey/cheat behavior observations

Current Moonwake catalog resolves **P95 — Program Design & Call-Stack
Prototype Architect**, **P08 — Live Runtime Proof Executor**,
**P82 — Prototype-Measure-Refine Delivery Loop**,
**P07 — Repo Sprint Executor**. P95 chose an opt-in action-channel seam
within the existing `hover_learning` owner and derived action identifiers
from the existing UI/cheat catalog owners; P82 supplied cross-channel,
negative, review and temporal regression cases; P07 owns branch/CI/main
integration. P08 live command/shortcut proof remains an independently
unproved local-host gate. Early ontology receipt:
`contracts/consultations/BI-INPUT-CHANNELS-20261109.v1.json`.

## 2026-11-09 — Hotkey-first cooperative interop (P95 + P124 + Trifecta)

Resolved **P95 — Program Design & Call-Stack Prototype Architect** and
**P124 — Repository Code Readability & Structural Refactorer** (Moonwake
catalog owner `spec-architecture-prompts.v1.json`, blob
`5926a198a14567de55110ed19e922fc444b4dec7`). P95 selects
`HOTKEY_FIRST_WHEN_EQUIVALENT` for ui-chrome plans and workflow effect
channeling; P124 keeps ownership in `ui_chrome` + shared `win32_input`
keyboard peer (no second input daemon / no global keyhook). Trifecta:
**P82** offline preference/rewrite falsifiers; **P07** bounded integration;
**P08** live F3/F1 vs HUD click remains OPEN. Consultation:
`contracts/consultations/BI-HOTKEY-FIRST-INTEROP-20261109.v1.json`.

## 2026-11-09 — Installation profiles settings (P141 + P124 + P95 + Trifecta)

Resolved against Moonwake main catalog: P141 = Repository Strategic Opportunity Scout; P124 = Repository Code Readability & Structural Refactorer; P95 = Program Design & Call-Stack Prototype Architect. Trifecta here is P82 = Prototype-Measure-Refine Delivery Loop, P07 = Repo Sprint Executor, P08 = Live Runtime Proof Executor. P141 compares and falsifies architectures rather than implementing; the selected scoped profile owner is implemented through P95/P124 and P82/P07. Local workstation/GPU/Sims P08 remains pending. See docs/INSTALLATION_PROFILES.md for path ownership, runtime status and proof boundary.

## 2026-11-09 camera-first target framing (P00 → P01 → P95 → Trifecta)

The current Moonwake `main` catalog at `harness/exports/prompt-invocation-catalog.v1.json` was read with blob `8c281379ba7ccc871947391233b1db72f4a108ef`; current `AGENTS.md` and deterministic resolver were inspected. Exact invocation identities: **P00 Governance Doctrine Installer**, **P01 Harness Infrastructure Builder**, **P95 Program Design & Call-Stack Prototype Architect**. Reused the existing governance, camera/traversal and listener owners rather than installing competing laws/services. Trifecta’s **P82** measured offline assessment/host negative controls, **P07** owns PR/main integration and **P08** remains the exact-build native Sims live-proof boundary. The pre-prototype semantic consultation is `contracts/consultations/BI-CAMERA-FIRST-TARGET-20261109.v1.json`. Product proof is not claimed from API or mocked tests. Full call stack: `docs/CAMERA_TRAVERSE.md`.


## 2026-11-09 active-Sim camera focus/follow — P95 → P124 → Trifecta

Current Moonwake AGENTS.md and prompt catalog were inspected. **P95** designed center-vs-follow semantics and safe code call stacks. **P124** reused ui_chrome as native shortcut owner, camera_traverse for world framing, host_stack for read-only orchestration, existing workflow_interop/screen_admit for cooperative execution, and optional in-game S4CL rather than a second camera controller. **P82** provides offline positive/negative tests; **P07** owns PR/main integration; **P08** native Sims follow behavior and physical custom-hotkey registration are local-host proof gates, not satisfied by mocked tests. Preprototype ontology receipt: contracts/consultations/BI-ACTIVE-SIM-CAMERA-20261109.v1.json. Full call stack: docs/CAMERA_TRAVERSE.md.


## 2026-11-09 recurring camera pixel-target drift — P95 + P124 + Trifecta

Resolved current Moonwake P95 program call-stack architecture, P124 structural refactor, P82 bounded prototype/regression measurement, P07 integration, and P08 live game proof. P95 chose one recovery transaction: cursor SAFE_REST before pixel sampling → fresh frame → Sim/lot focus only when displaced → optional code follow or host-observed map traversal → fresh re-detection → target camera-revision-bound click admission. P124 reused camera_traverse, host_stack/listener, screen_atlas's native click owner and workflow_interop/screen_admit rather than duplicating a mouse controller. P82 adversarial cases live in tests/test_camera_traverse.py and tests/test_screen_atlas.py. P07 owns PR/CI/main convergence. P08 game-side effect and operator interruption remain unproved until observed locally. Pre-mutation ontology consultation: contracts/consultations/BI-CAMERA-DRIFT-RECOVERY-20261109.v1.json.
