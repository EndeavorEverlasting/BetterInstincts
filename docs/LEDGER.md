# Canonical project ledger

## 2026-11-09 — Explicit-click desktop bootstrap UI (P92)

Repository main page `bootstrap.py` now defaults to an opt-in local Tkinter window with Inspect paths, Install and Uninstall buttons; the uninstall action requires explicit confirmation and reuses the same manifest/checkout safety gates as the CLI. Opening the window or denying confirmation changes nothing. This is a local Python GUI (not a GitHub web execution privilege), with CLI fallback if Tkinter is unavailable. New consultation `BI-BOOTSTRAP-GUI-P92-20261109.v1.json`; offline unit tests cover command routing and cancel. Live workstation click/install proof remains open.


## 2026-11-09 — Operator-first asynchronous control and canonical install lifecycle

**Parent:** user and agents must share the computer without agents cancelling queued work or stealing focus. P00/P01 preserve canonical governance/harness; P95 prototypes an opt-in `CooperativeScreenQueue` at 15 seconds OS-wide trusted inactivity; P124 reuses existing `control_handoff` as the admission owner, with one `desktop-shared.lock` for participating Playwright/host executors and a bounded queue. A Playwright adapter reuses an existing page; no new browser is launched. Human input on any app yields; unknown input or stale scene fails closed; possible partial effects require reconciliation rather than blind replay. This does not automatically retrofit every external agent/legacy `host_tandem` callback.

**P92:** `bootstrap.py` is the canonical Windows/Linux profile path owner, cloning into the development rule if absent; creates only a user-scoped offline launcher and SHA-bound manifest. Uninstall removes only proven owned paths; preexisting/dirty clones, saves and mods survive. No PATH/registry/cron/task/service mutation or playable mod claimed.

**Trifecta:** P82 deterministic failure/interruption/installer tests; P07 actual GitHub implementation/CI; P08 real Windows host, Linux trusted probe and Sims/Playwright tests are OPEN. Remote merge, local checkout, install/use path and real entrypoint are independent proofs. Consultation `BI-ASYNC-INTEROP-P92-20261109.v1.json` precedes code changes. `docs/ASYNC_INTEROP.md` is the operator/agent runbook. BI-002 hunger certification remains active.


## 2026-11-09 — Host UI chrome map + hotkey glossary + AOK inventory recipe (P95 + P124 + Trifecta)

**Operator:** Agentic Build clicks keep missing chrome; need durable per-mode element maps, hotkey glossary (Build/Live/Buy), extensible Live phone/bottom-right panels, and host logic that finds **AOK** Bloomer, buys it, and deposits to Household Inventory — not vision thrash. **P95** selects `UI_CHROME_PEER_MAP` (normalized client fractions + recipes; stubs for Live needs/career/skills/phone). **P124** peer `ui_chrome` beside `ui_mode` / `household_object_force` — no second screen daemon. Consultation `BI-UI-CHROME-MAP-20261109.v1.json`. CLI: `python -m scripts.ui_chrome glossary|resolve|plan`. Preferred search **AOK**; Meat Wall career note corrected (Grow unlock on Bloomer, not auto inventory drop). P08 live click calibration OPEN. Does not close BI-002.

## 2026-11-09 — F1/F2/F3 game mode context shared across asynchronous microsystems (P95 + P124 + Trifecta)

**Operator objective:** Determine Live (F1), Buy (F2), or Build (F3), and contextualize menus without mixing Live needs/queue automation into Build/Buy. **P95** designs scene-cue → mode → panel → listener → tandem (or Build floor census). **P124** reuses canonical `scenes` as authority and existing opt-in listener/tandem instead of duplicating a poller. Added `buy_mode` and `build_mode` to the scene catalog while preserving the ambiguous legacy `build_buy`. Candidate cue pairs and panel IDs live in `contracts/ui-mode.v1.json`; evaluator in `betterinstincts/ui_mode.py`; listener emits context-only receipts outside Live, and asynchronous `host_tandem` ends without new dispatch on non-Live/unknown mode. Legacy observations without explicit cue fields still work but do not constitute mode proof. Consultation `BI-UI-MODE-CONTEXT-20261109.v1.json` predates behavior mutations. **Trifecta:** offline P82 falsifiers in `tests/test_ui_mode.py`, P07 source/CI integration, P08 genuine game capture and focus/overlay calibration still OPEN on the local host. Source and documentation are not game-sensor certification; BI-002 remains ACTIVE.


## 2026-11-09 — Build floor activity for host listener (P95 + trifecta)

**Operator:** While still in Build Mode, extend the listener so it can see activity differences across floors — one floor vs several, which floor is active, and floor theme from item types/specifics — evolving toward optimize suggestions. **P95** selects `FLOOR_ACTIVITY_CENSUS` (reuse `build_spatial` story aliases; attested `floor_items` only; no pixel invent). **P124** peer `build_floor_activity` wired into `host_listener` ticks when `build_or_buy_mode`. Consultation `BI-BUILD-FLOOR-ACTIVITY-20261109.v1.json`. CLI: `python -m scripts.build_floor_activity evaluate`. Live story chrome sensor P08 OPEN. Does not close BI-002.

## 2026-11-08 — Household useful-item force catalog (P95 + P124 + trifecta)

**Operator:** Durable reusable catalog for forcing named useful objects into any Sims household on command — must not stay chat-trapped. List: Out of This World Desktop, Cruelty-Free Meat Wall, UFO Bed, Captain Sigma, Eco-Matic Smog Vacuum, Hydroponic Planter, optional Positronic Pro. **Strong correction:** `bb.showhiddenobjects` is **elementary** for unlocking hidden/catalog rows on that list; Better BuildBuy is optional UX only and never a substitute; never hallucinate `gsi_create_obj` hex IDs. Large objects → Household Inventory or lot, never pocket. **P95** call stack: elementary unlock → career.promote deposits → catalog search. **P124** factors as sibling to `funds_inject` / `curious_catalog` / `hidden_object_discovery` — one `household_object_force` owner. Consultation `BI-HOUSEHOLD-OBJECT-FORCE-20261108.v1.json`. CLI: `python -m scripts.household_object_force catalog|elementary-unlock|plan`. Proof ceiling offline plan only; live P08 OPEN. Does not close BI-002.

## 2026-11-08 — Countertop mechanics + Env-max island hierarchy (P95 + P124 + trifecta)

**Operator:** Live Build Mode learning — island vs standard counters, Auto-Counters
gear shapes/corners, barstools snap only to island overhangs, dining chairs never
snap, counter Env cap **2**, Corporate Chic Env-2 locked behind Culinary 2 (cheat
`bb.ignoregameplayunlocksentitlement`), default Env-2 islands Harbinger / Real Flat /
Immemorial. **P95** adds `placement_mechanics.countertops` + `counter` /
`counter_island` / `barstool` categories inside `build-optimize` v3. **P124** keeps
the single `build_optimize` owner (`seating_snap_verdict`, `category_hierarchy`,
`evaluate_countertop_plan`) — no second catalog daemon. Consultation
`BI-COUNTERTOP-MECHANICS-20261108.v1.json`. CLI:
`python -m scripts.build_optimize --countertops` /
`--hierarchy --category counter_island`. Proof ceiling
`OFFLINE_COUNTERTOP_MECHANICS_AND_YIELD_POOLS_NOT_LIVE_PLACE_NOT_BILL_METER_CERT`.
Live place/snap/pathing P08 OPEN. Does not close BI-002.

## 2026-11-08 — Build yield microsystem: per-category best pools (P95 + P124 + trifecta)
Operator ask: complete the microsystem that maximizes best values in **each Build/Buy category** so the host has a pool for environment, neighborhood, bills, etc. Ontology consultation `BI-BUILD-YIELD-MICROSYSTEM-20261108` precedes mutation. **P95** expands `build-optimize` v2 with value axes + category trays; **P124** keeps a single evaluate-only owner (`best_pools` / `evaluate_category_pools`) instead of a second daemon. Dual Env+Green 2/2 walls remain yield floor; bill pools skip null axes. CLI: `python -m scripts.build_optimize --pools`. Live paint/meters OPEN; BI-002 ACTIVE.

## 2026-11-08 — Balance/Imbalance microsystem (P95 + P124 + trifecta)

**Operator:** Enchanted by Nature Balance meter — prolonged negative mood →
Imbalance (needs drain 25% faster, skills 15% slower) → Very Imbalanced always
contracts a physical ailment (example: Burning Passion). Cure via Naturopath,
Holistic Cure, nature engagement, and positive moods. **P95** adds peer
microsystem `balance_service` (`contracts/balance-service.v1.json`,
`docs/BALANCE_SERVICE.md`) with sticky `BALANCE_CONDITION_HELD`, nature-first
recovery for Imbalanced, Naturopath/Holistic Cure escalation for Very Imbalanced
+ supplied ailment. **P124** reuses `survival_critical`, moodlets emotion family,
and gardening plant-care peers — no second scorer or daemon. Wired through
`host_stack`, `domain_cascade` (order: needs → **balance** → budget → …), and
`host_tandem` (`BALANCE_READY_HANDOFF_REQUIRED`). Consultation
`BI-BALANCE-MICROSYSTEM-20261108.v1.json`. Proof ceiling
`HOST_BALANCE_MICROSYSTEM_TANDEM_NOT_DAEMON_NOT_PACK_CERT`. Live Naturopath/cure
P08 OPEN. Does not close BI-002; does not invent meter readings.

## 2026-11-08 — Aspiration microsystem (P95 + trifecta)

**Operator:** Mother Nature / Fairy summon dialog on Charlee would permanently
rewrite life state and needs while the base six-need engine is unfinished.
**P95** adds peer microsystem `aspiration_service`
(`contracts/aspiration-service.v1.json`, `docs/ASPIRATION_SERVICE.md`) with sticky
`ASPIRATION_PROMPT_HELD`, explicit `aspiration_completion_enabled` toggle (lab host
default **false** → Cancel; product default true), and occult-needs readiness gate
before any life-state OK. Wired through `host_stack`, `domain_cascade`, and
`host_tandem` (`ASPIRATION_DIALOG_HANDOFF_REQUIRED`). Consultation
`BI-ASPIRATION-MICROSYSTEM-20261108.v1.json`. Proof ceiling
`HOST_ASPIRATION_MICROSYSTEM_TANDEM_NOT_DAEMON_NOT_LIFE_STATE_MUTATION`. Live Cancel
P08 OPEN. Does not close BI-002; does not authorize fairy need-tree work.

## 2026-11-08 — Career microsystem (P95 + trifecta)

**Operator:** Agents keep getting stuck in needs and forget teen High School Student
career-panel homework. **P95** adds peer microsystem `career_service`
(`contracts/career-service.v1.json`, `docs/CAREER_SERVICE.md`) with sticky
`CAREER_OBLIGATION_HELD` that evaluates in tandem with need_services, suspends for
survival without dropping the duty, and resumes via `CAREER_READY_AFTER_NEEDS`.
Wired through `host_stack`, `domain_cascade`, `host_listener`, and `host_tandem`
async observe events / `CAREER_READY_HANDOFF_REQUIRED`. Policy lanes still own
`teen_homework` / `school_day`. Consultation
`BI-CAREER-MICROSYSTEM-20261108.v1.json`. Proof ceiling
`HOST_CAREER_MICROSYSTEM_TANDEM_NOT_DAEMON_NOT_BI006_CERT`. Live homework P08 OPEN.
Does not close BI-002 or BI-006.

## 2026-11-08 — Operator correction: resume behavior orchestration

The operator explicitly rejected the furnishing detour and the subsequent failure
to resume repository work. **The prior bed proposal is REJECTED, not pending; no
placement response is required and no furniture/building prerequisite exists.**
Historical entries below describe the earlier mistake and do not authorize or
govern current continuation. The private continuation receipt was corrected too.

The missing program seam is now `gardening_service` → existing `host_stack` and
`host_listener`. It reuses the same six-need service result, preserves the gardening
goal through needs recovery, respects school/homework/player/viewport gates, and
selects at most one current observed Plant/Water/Weed/Harvest interaction. Failed
predictions lead to inspection of existing need interactions, never construction.
P124 keeps existing normalization, needs policy, responsibility and tick-persistence
owners; no second scorer, scheduler or daemon was introduced. Consultation
`BI-GARDENING-BEHAVIOR-20261108.v1.json` predates source changes. Tests, integration
and any actual game observations must be reported separately. BI-002 remains ACTIVE.

**Validation and bounded local outcome:** Windows suite **479 tests run, 3 skipped,
no failures** after adding the optional observed ground-rest lane; the focused
gardening/needs suite passed 25 tests. Normal Living/ground eligibility is not
assumed: the earlier Sleep Here option was disabled while merely tired, whereas
the current exhausted-Sim menu visibly enabled it. On exact build
`1.121.361.1020`, the real `host_stack.evaluate_turn` selected `GARDEN_RECOVER_NEEDS`
with `SLEEP_ON_GROUND` from that current observation. The local agent separately
acquired `screen_admit` and issued one Sleep Here interaction. A subsequent frame
at Saturday 01:37 showed Charlee lying on outdoor ground with sleep Z cues and a
Natural Living needs-care message. **Rest-start is LOCAL_OBSERVED; numerical Energy
recovery, gardening, school safety and gameplay certification remain UNPROVED.**
No furniture purchase, placement, save-file mutation or speed command occurred.
Private captures: original checkout `dist/game-host/gardening-behavior-20261108/`;
actual plan: isolated current-main worktree `dist/game-host/ground-rest-host-plan.json`.
The optional lane requires current enabled `Sleep Here` evidence; ground itself
does not establish skill/pack eligibility. Its consultation predates the lane edit.

## 2026-11-07 — Needs-first gardening and resumable scout continuation

**Integration and later local findings:** PR [#65](https://github.com/EndeavorEverlasting/BetterInstincts/pull/65) merged as `e7f7977a01f13b9667622dd9b9b8535d04118d58`; PR-head CI `42435179252` and post-merge CI `42435280481` succeeded. After the player became idle, separately admitted UI inspection read the need bars. Values passed to existing `evaluate_need_services` are explicitly **visual HUD fill estimates, not internal game values**. Energy was selected ahead of gardening. The inspected throne offered only Sit / Make Heirloom, falsifying the predicted REST_ON_CHAIR route; the existing load balancer detached that route and opened an assumption window. Ground Sleep Here was disabled and not selected. Current action Wash Hands was inspected without clicking/cancelling its queue icon. No gardening command, placement or purchase issued.

At dismissal the game displayed a school-trouble warning; cause **UNKNOWN**. This contradicts any broad claim that Good performance alone establishes responsibility safety. School attendance was observed, but current after-school homework must be rechecked before gardening (the morning's Complete is time-bound). Inventory showed four items and no visible rest equipment or seed packet. Build/Buy inspection found **Hasty Replacement Palette Bed, §210, Energy 3**; operator placement approval requested, still pending. No bed selected for placement. Private continuation/admissions/captures: original checkout `dist/game-host/garden-scout-20261107/continuation.json`. Scene left in Build/Buy; screen lease released; scout timer remains paused at zero discoveries. Actual needs recovery, gardening and a multi-hour catalog run remain OPEN.

**Operator objective:** use existing needs services to support planting/gardening without sacrificing responsibilities; run the optional Hidden Catalog Scout for up to four hours toward 40 genuine unique candidates. Refreshed `main` floor `b0f58aeea3aef54a1d63bbb568b76b592fb117d7` contains PR #64. Moonwake catalog blob `8c281379ba7ccc871947391233b1db72f4a108ef` and current P95/P124 source bodies were read. Exact Windows executable version freshly observed as `1.121.361.1020`; PID 66096. Existing dirty house-state work remains untouched in the original checkout.

**P08 local observation:** Live Mode, Charlee LabLab, planting beds visible. School panel at Friday 07:19: High School C Student, Homework Complete, Average performance, class in 41 minutes (08:00–15:00). Subsequent capture at Friday 09:45: **At school until 3:00 PM**, Good performance, Homework Complete. This proves observed school attendance, not host-caused gardening or need improvement. Need meters were not read. Two current input-age admissions denied host inspection with `HOST_PAUSED:RECENT_HUMAN_INPUT`; no host game input issued. Lease released. Private evidence: original checkout `dist/game-host/garden-scout-20261107/`.

**P95/P82/P07 scoped repair:** school evidence exposed `domain_cascade` forcing `homework_pending=True` whenever book observations were supplied. A regression first failed for both present and absent books despite completed homework. Passing through the actual flag fixes the defect; pending homework and survival-first controls are retained. Focused cascade/homework/needs suite: **30 passed**; full Windows suite: **464 tests run, 3 skipped**, others passed. This is offline behavior proof, not a live repair claim. P124 keeps the canonical service boundaries and avoids unrelated extraction. Consultations predate protected mutation; see `BI-GARDEN-RESPONSIBILITY-FIX-20261107.v1.json`.

**Scout checkpoint:** `catalog-lab-01` initialized for 240 minutes / target 40 in the isolated current-main worktree, at `dist/hidden-object-scout/catalog-lab-01/state.json`. Zero candidates/batches. Actual `next` returned ABSTAIN for incomplete initial P04 review, Live rather than Build/Buy, missing fresh independent cue/save binding and player/scene admission. Scout timer paused (14358 seconds remaining) to retain its budget; this is not a running four-hour discovery claim or a pause of the parent thread goal. Previous P04 item review and queue proof remain unverified. Do not fabricate them to start the loop. BI-002 remains ACTIVE, game-unproven.

## 2026-11-07 — Local P04 Windows preflight repair

Fresh remote floor `c75f28c55e11d375ac81a699b05518c1a65f7dc7` includes merged PR #61. An isolated worktree preserves unrelated dirty house-state work. On Windows, the full suite exposed ontology consultation identity mismatches: native `str(Path)` produced backslashes while tracked records and Git use forward slashes. `scripts/check_ontology.py` now uses `as_posix()` for identity, consultation exemptions and Git consultation lookup. The original fail-closed decisions and historical ontology validation remain intact. A Windows-path-flavor regression runs on every host. Local suite: **453 tests run, 3 skipped**, all remaining tests passed; focused ontology suite: 18 passed. Provider integration and live discovery outcome must be verified separately. BI-002 stays ACTIVE and game-unproven.

**Integration verified:** PR [#62](https://github.com/EndeavorEverlasting/BetterInstincts/pull/62) merged as `f294f0f4ae77d55551608b7680d4e1bc7c5015cf`. PR-head CI `42433394011` and post-merge CI `42433446110` both succeeded. Focused post-merge local ontology/discovery suite: 33 passed; chronology gate: 2 protected files, 1 prior consultation.

## 2026-11-07 — P04 actual Windows hidden-catalog observation

**LOCAL_OBSERVED, INCOMPLETE REVIEW; NOT GAME_CERTIFIED.** User explicitly confirmed the running session disposable in Live and Build/Buy and authorized the requested inspection. Running executable metadata freshly reported `1.121.361.1020` (Windows); an exact-build consultation preceded sampling. One exclusive existing `screen_admit` lease and double input-idle probes guarded each input; a recent-input denial was respected. Initial occluded capture was rejected. Actual focused screen: Bargain Bend, Build/Buy, normal rendered lot and catalog. Console opened after focus recovery; literal `testingcheats true` was submitted and **Cheats are enabled.** observed; literal `bb.showhiddenobjects` submitted; console closed; existing Build/Buy confirmed; typed `debug`, selected a visible **DEBUG** suggestion and observed hidden catalog. Build/Buy was already active: no new mode transition is claimed. Optional live-edit was not requested or issued.

One individually captured listing: **DEBUG**, white angular cup/bowl depiction, displayed **§0**. Pack identity and usability unknown. Item selected for inspection then cancelled with Escape; no placement or purchase. Funds remained **§945,478**; no speed or queue action issued. Queue contents were not visible and preservation is **not directly proved**. Private captures, actual admission results and truthful receipt remain ignored under `dist/game-host/hidden-object-p04-20261107/` and `dist/game-host/hidden-object-p04-receipt.json` in the original checkout. Audit: **P04_EVIDENCE_INCOMPLETE**, five step records checked, `PLAYER_QUEUE_UNCHANGED_UNPROVEN` and `CATALOG_ENTRY_UNVERIFIED:1` (operator price review pending). Do not replace these gaps with true values to obtain a green audit. No blanket free-item or exhaustive inventory claim. Screen lease released. Both existing hunger recorders still contain zero baseline, modified or rollback trials; BI-002 remains ACTIVE.

**Repository:** EndeavorEverlasting/BetterInstincts
**Owner objective (2026-10-20):** A creative, freely distributed contribution to The Sims 4 modding community that makes Sims autonomously meet needs responsibly, generate income, improve career outcomes, and pursue more fulfilling lives. Start with an observable small win while retaining the entire multi-month vision here. Prefer community-standard languages/tooling and patterns; avoid inventing new systems unnecessarily.

## 2026-11-07 ontology refinement — candidate semantic layer
Operator direction: game-native instincts first, but no arbitrary cap on future engineering or creative mechanisms. Needs plus financially sustainable autonomy remain the core, with existing cross-domain load-balancing retained. Goal threads must survive justified contingency preemption and be re-evaluated before resuming; multiple domains may be assessed together but that never grants simultaneous game input. Scoped ontology consultation must precede experiments, behavioral edits, and game sampling. Authoritative machine graph: `contracts/ontology.v1.json`; offline seam: `betterinstincts/semantic_advisory.py`; local preflight: `scripts/semantic_preflight.py`. Until independently observed, the extension and any burglar-specific strategy remain hypotheses; BI-002 gameplay certification unchanged and ACTIVE. Repository integration and local live-game evidence are separate statuses.

## Non-negotiable product behavior
1. Player agency outranks all autonomy suggestions.
2. Needs and safety outrank money/career efficiency; leisure and character remain meaningful.
3. Different Sims should not converge on one robotic optimization loop.
4. Behavior must be configurable, individually defeatable, reversible, and performant.
5. No save alteration, arbitrary user directories, telemetry, hidden background tasks, or mass changes.

## State and evidence ledger
| Item | State | Evidence / proof ceiling |
| --- | --- | --- |
| Repository | VERIFIED | New public GitHub repo with initial README, MIT and Python gitignore; `main` initial commit f6d129ef84f7a31beb5ec3f2610e1e39bd9aa749. |
| Tool ecosystem | RESEARCHED | See docs/PRIOR_ART.md; Python + XML tuning prevalent, but exact local game build not inspected. |
| Doctrine | MERGED TO MAIN | PR #1 merged as 308778a18c4349523fa99942c2e0e2818a27fd66; root AGENTS.md, validator, CI present on main. |
| Decision policy | OFFLINE PROTOTYPE + CI PASS | Pure Python scorer + synthetic tests only; NOT a game mod. PR #1 final head b15abd76317dd5e7a131a807b641736bfecf9297 passed 19 tests, doctrine check, tracked-asset scan and whitespace gate; [CI run](https://github.com/EndeavorEverlasting/BetterInstincts/actions/runs/39371028568). |
| Game integration | UNPROVEN | No tested `.package` or `.ts4script`, no game observation. |
| Live performance/compatibility | UNPROVEN | Requires local game and disposable saves. |
| Multiple-version resolver | IMPLEMENTED OFFLINE; NO CERTIFIED BUILDS | Exact patch+platform+module lookup with no latest fallback and byte-immutable older certified evidence guard in CI. Catalog empty by design. |
| Local game progress/evaluator | IMPLEMENTED OFFLINE; GAME PROOF UNPROVEN | Bounded CLI trial recorder; five vanilla/five modified + rollback gate and reviewer-only numerical verdict. Not a Sims API hook. |
| Public release | NOT AUTHORIZED | Requires docs/VALIDATION.md release gates. |

## Durable decisions (revise with evidence)
- First investigation: one observable base-game needs behavior (hunger) and its tuning/priority mechanism, not whole-game AI replacement.
- Alternative prioritization algorithms are hypotheses until live game comparison.
- Keep MIT for original code; third-party dependency license audits before any reuse.
- Honor community patterns: Sims 4 Studio for extraction/packaging research; consider XML Injector, Lot51 Core, S4CL only for justified integrations, not default dependencies.
- Use a single repo-local output root; require an explicitly provided, previewed install path for any future installer.

## Permanent operator correction (P00/P04/P97 — 2026-10-20)
**Serve several versions of The Sims 4.** When a new game build arrives, preserve code/configuration proven on older builds; do not reinterpret them or silently migrate to latest. Compare each build's tuning and certify the new profile independently. The **local game-capable agent owns completing BI-002's hunger experiment**, its actual package, gameplay trials, rollback, evaluation and proof; planning/handoff/CI-only work is explicitly insufficient. Agent progress must be machine-observable from repo-provided live-cert hooks. This decision persists in AGENTS.md, docs/DOCTRINE.md, docs/COMPATIBILITY.md, docs/LIVE_CERT.md and plans/active/BI-002.execution.v1.json.

## Project fact discipline
Mark CURRENT FACT, OBSERVED IMPLEMENTED, DOCUMENTED UNVERIFIED, INFERRED, EVIDENCE GAP. A third-party README doesn't prove a game runtime behavior. Document exact Sims patch + pack list for game tests. Preserve rejected choices here rather than reopening settled questions without new evidence.

## PR #3 version compatibility & game-cert harness closeout (2026-10-20)
**State: MERGED, OFFLINE VERIFIED, NOT GAME-CERTIFIED.** PR [#3](https://github.com/EndeavorEverlasting/BetterInstincts/pull/3) merged to `main` at `9550ef66315cfd77c4cbc5044e8c9bae49d8a3be`. [Post-merge CI run 39374046727](https://github.com/EndeavorEverlasting/BetterInstincts/actions/runs/39374046727) passed. Latest feature-branch suite: **46 unit tests**; doctrine, historical-profile preservation, no game-assets tracked, whitespace and source compile all green. Governance and code include exact-patch lookup, frozen older certified profiles/source commits, bounded live-cert recording/progress, read-only tuning auditing, Cursor guidance and code-owner routing. **No** real installed game version, authored hunger `.package`, recorded gameplay trial, human gameplay acceptance, or playable release was verified. Compatibility catalog intentionally contains zero certified builds. Local game experiment BI-002 remains ACTIVE and requires full proof. This proof ceiling is reflected in [machine-readable receipt](../artifacts/proof/BI-002-compat-bootstrap.v1.json).

## Long-horizon operator decision and P141/P82/P07/P04 delivery (2026-10-20)
**Permanent parent sequence:** stabilize **all six adult needs** (Hunger, Bladder, Energy, Hygiene, Fun, Social), then maintain their balance while autonomous work produces **observed recurring income**; only after income is underway develop **observed skills** without neglecting previous systems. Career progress is a successor, not a reason to move skills before income. See [HORIZON.md](HORIZON.md) and `plans/horizon.v1.json`, which owns the dependency ordering. The existing BI-002 hunger experiment remains the first game gate and must not be closed by this new offline work.

**Code added this sprint:** `betterinstincts/horizon.py` and `contracts/needs.v1.json` introduce an uncalibrated six-motive *offline* candidate. Explicit available actions, player command/busy guards, unsupported-life-stage abstention, proactive care and cooldowns prevent income/skill suggestions from preempting needs. Income needs an independently proven needs floor; skills additionally require actual observed income (the in-memory flags are not proof and must later be wired to real compatible runtime evidence). Old `priority.py` is preserved as comparison floor. `scripts/eval_horizon.py`, `scripts/check_horizon.py`, `scripts/horizon_status.py`, tests and CI expose machine-readable progress while preventing missing needs or reordered economic goals. The local execution plan for BI-003A–F lives in `plans/active/BI-003.execution.v1.json`; P04 lane disposition in `plans/active/BI-HORIZON.dispatch.v1.json`.

**Measured proof before integration:** feature branch CI [39456443205](https://github.com/EndeavorEverlasting/BetterInstincts/actions/runs/39456443205) returned SUCCESS with 64 offline tests, 12 checked horizon stages, 16 synthetic scorer cases, and clean doctrine/tracked-asset checks. New commits after that run require their own CI verification. **No actual Sims hunger package, in-game trial, income transaction or skill increment has been observed.** All gameplay phases remain UNPROVEN. The six-need 0.35/0.55 thresholds and abstract actions are experimental design values, not confirmed tuning IDs. P82 hypothesis and falsifiers recorded in [HORIZON_DECISIONS.md](HORIZON_DECISIONS.md).

## PR #5 horizon integration closeout (2026-10-20)
**MERGED TO MAIN:** [PR #5](https://github.com/EndeavorEverlasting/BetterInstincts/pull/5) at `1b5909aaedd31df42573b4a29f0badca1a8fef9a`. [Post-merge CI 39456997645](https://github.com/EndeavorEverlasting/BetterInstincts/actions/runs/39456997645) succeeded; last PR-head CI proved **65 Python tests**, 12 validated horizon stages, 16 deterministic synthetic scenarios, tracked-asset and governance checks. `docs/HORIZON.md` and `plans/horizon.v1.json` are canonical. `betterinstincts/horizon.py` is an **offline policy candidate**, not game-integrated; BI-002 hunger remains ACTIVE GAME UNPROVEN, and **none** of the later needs, income or skills have passed game trials. [Typed proof receipt](../artifacts/proof/BI-HORIZON-20261020.v1.json).

## Next parent gate
Execute [BI-002](../plans/active/BI-002.md): prove **one** reversible tuning-based, base-game hunger autonomy improvement against a vanilla comparison on a disposable save; if tuning cannot implement this, capture falsifying evidence and route the smallest justified script adapter. CI alone cannot close this gate.

## 2026-11-06 — BI-004 custom Mod Lab bootstrap
New additive read-only Mod Lab (docs/MOD_LAB.md; originally plans/active/BI-004.md, later renamed BI-MODLAB) inventories .package header metadata and .ts4script Zip module names under an explicitly selected Mods root. It does not parse package TGI keys, execute scripts, install mods, certify game patches, change files, or prove skill gains. The local-game BI-002 hunger gate and all earlier multiversion/horizon protections remain unchanged. The final PR/merge/CI proof and P04 local handoff must be appended only after provider verification.

## BI-004 provider integration / P04 continuity receipt — 2026-11-06
PR [#7](https://github.com/EndeavorEverlasting/BetterInstincts/pull/7) merged into main at `1686eac7be92c42ccbbabc16144d67248f630da3` after [PR-head CI](https://github.com/EndeavorEverlasting/BetterInstincts/actions/runs/42322823454) SUCCESS. [Post-merge CI](https://github.com/EndeavorEverlasting/BetterInstincts/actions/runs/42322858979) SUCCESS at the merged SHA. The canonical P04 continuation is now [BI-MODLAB.HANDOFF.md](../plans/active/BI-MODLAB.HANDOFF.md), guarded by `BI-MODLAB.dispatch.v1.json` (renamed from BI-004* so horizon income BI-004 stays unambiguous). Offline Mod Lab only; actual installed patch/game and BI-002 hunger trials remain unobserved. No live Sims result is implied.

## BI-004 follow-on — bounded DBPF TGI index (local trifecta) — 2026-11-06
Additive read-only `betterinstincts/dbpf.py` parses package header + resource index keys (Type/Group/Instance) under strict size/count/report budgets; payloads are never decompressed. Wired into Mod Lab inventory as `package_index` with an explicit INDEX_KEYS_ONLY proof ceiling. Synthetic fixtures cover constant-header compression, truncation fail-closed, and report budgets. Local Documents `GameVersion.txt` length-prefixed string observed as `1.121.361.1020` on this host — **LOCAL_OBSERVED only**, not a certified compatibility profile. Sims 4 Studio and a playable game install were not located under common Program Files paths; BI-002 remains ACTIVE / BLOCKED_LOCAL_GAME_ACCESS for gameplay. Real Mods scanning still requires an operator-selected absolute root and must not publish personal manifests.

## P141/P124 — Mod Lab identity + dbpf readability — 2026-11-06
P141 refresh in docs/STRATEGY.md selected **disambiguating Mod Lab from horizon BI-004 income** as the next offline contract (game hunger remains parent product gate but BLOCKED locally). Mod Lab plans/dispatch/handoff now use sprint id **BI-MODLAB**; horizon `BI-004` stays income-only. `horizon_status` emits `tooling_lane=BI-MODLAB` beside `income_gate=BI-004`. Collision regression lives in `tests/test_modlab_handoff.py`. P124 applied a behavior-preserving readability split in `betterinstincts/dbpf.py` without changing index semantics.


## 2026-11-06 — Game-host launch and disposable-save evidence lane (P08/P82/P07 → P04)

**Source integration: MERGED, SYNTHETIC CI VERIFIED.** PR #11 landed on main at c5fd5f16f78568050b3ba5aced9a525f85185c2c; candidate c196b2682cd9a39618d3d1605977878f954f8cea passed GitHub Actions run 42335351712, including game-host synthetic tests, backward compatibility, horizon, doctrine, tracked assets and compilation. The explicit Windows game host (scripts/game_host.py) can prepare a safe profile, dispatch selected Sims executable, request New Game/CAS or choose a screenshot-matched disposable Load Game slot, checkpoint clicks, confirm operator-reported Live Mode and ingest a one-shot sanitized external object-state snapshot. Read docs/GAME_HOST.md. A process request or PyAutoGUI click is not proof that a real save loaded; externally supplied JSONL is not a real in-game observer. Actual The Sims 4 launch, patch, disposable save, active Sim, gameplay change, hunger package, object-state producer and live CI/CD remain unobserved. No personal saves or Mods were touched by this provider runtime.

**Canonical P04 continuation:** plans/active/BI-GAME-HOST.HANDOFF.md with typed work/ownership machine map plans/active/BI-GAME-HOST.dispatch.v1.json. Parallel-ready local lanes GAME-BOOT and TUNING-READONLY need actual separately authorized Windows workers; no parallel local execution was observed. Existing BI-002 gameplay certification remains ACTIVE / BLOCKED_LOCAL_GAME_ACCESS until >=5 actual vanilla and >=5 actual modified trials, rollback and review. BI-MODLAB remains a tooling label; horizon BI-004 is income. Next gate is one verified disposable game session and true hunger baseline followed by a reversible package and comparative gameplay, not another offline prototype or release.

## 2026-11-06 — Local GAME-BOOT first session (trifecta P08/P82/P07)

**LOCAL_OBSERVED, NOT GAME_CERTIFIED.** Fast-forwarded local `main` to `56bc65bf` (merged PR #11 + #12). Offline `python -m unittest discover -s tests -v` → 99 tests OK (2 skipped). Created ignored `dist/game-host/local-profile.json` against an explicitly selected `TS4_x64.exe` under an E: Games install (path kept out of Git). `game_host launch --execute` started live process `TS4_x64` (run `bi002-first-boot`, receipt `LAUNCH_DISPATCHED` / `PROCESS_DISPATCH_ONLY`). Main menu showed **Version 1.121.361.1020 DX11** (matches prior Documents `GameVersion.txt` LOCAL_OBSERVED). Calibrated New Game template; `navigate --execute --disposable-confirmed` reached `NEW_GAME_CAS_REQUESTED` (`UI_CLICK_DISPATCH_ONLY`). Create-a-Sim with story-quiz prompt was visually observed after focus restore. **Live Mode, hunger baselines, reversible package, and object-state producer remain unproven.** Compatibility status for `1.121.361.1020` / windows / hunger is still `UNKNOWN_VERSION` (expected; blocks release claims only). Mid-CAS automation was interrupted by focus steal (minimized `-32000` placement + computer-control overlay); CAS→placement→Live Mode needs a short operator handoff. Sims process left running for that handoff. Parallel TUNING-READONLY still blocked (Sims 4 Studio not located).

## 2026-11-06 — Live Mode-to-baseline bridge (repository implementation, not in-game proof)

From real CAS first boot on `1.121.361.1020`, the blocking physical step remains operator creation/placement of an expendable adult Sim and verified Live Mode. Added `scripts/game_baseline.py` to turn existing `LIVE_REPORTED_UNREVIEWED` host evidence into an **empty, version-bound, repo-local vanilla trial recorder**. Baseline entry does not require Sims 4 Studio; the sentinel `NOT_OBSERVED` cannot be accepted at modified-package attestation, and an actual Studio build must be explicitly recorded later. Retry is non-destructive and version mismatches fail closed. This is code/CI progress only until a local agent records genuine hunger observations. PR/merge/CI receipt: see ensuing GitHub integration; no operator keyboard or gameplay was performed in the chat runtime.

## 2026-11-07 — BI-SCENE-MAP: scene discovery and save safety (design/implementation, not live proof)
Added an extensible exact-build scene graph with 35 candidate scenes, independent cue sources, explicit guarded manual-only transitions and unknown/ambiguous abstention; no screenshot classifier or game UI shipped. Added save ownership policy with `LAB_DISPOSABLE`, `LAB_CONTINUATION`, `USER_PROTECTED`, `UNKNOWN_PROTECTED`. Naming conventions `BI_TMP_` and `BI_CONT_` are NEVER authorization: chosen-save automation now requires a private, bound, uniquely identified, operator-attested lab-origin record; all unknown/user-origin, colliding and stale selections fail before clicks. No automatic delete/overwrite/Resume. P00/P01 governance and CI enforcement added. P95 decision stacks and live-cert next gate documented in docs/SCENE_INTELLIGENCE.md. PR/CI/merge proof recorded by GitHub; previous real CAS observation remains the only verified gameplay milestone; Live Mode/hunger trials 0 observed in this cloud runtime.

## 2026-11-07 — Scene map integration and canonical P04 re-entry
[PR #15](https://github.com/EndeavorEverlasting/BetterInstincts/pull/15) merged the scene/save implementation into `main` as `709646ce11cc1ee1fb80848f66c9130230b3721f`. [PR-head CI](https://github.com/EndeavorEverlasting/BetterInstincts/actions/runs/42373216350) and [post-merge main CI](https://github.com/EndeavorEverlasting/BetterInstincts/actions/runs/42373287837) both SUCCEEDED; PR head ran 139 offline tests. One canonical P04 continuation now lives at `plans/active/BI-SCENE-MAP.HANDOFF.md` with machine dispatcher `plans/active/BI-SCENE-MAP.dispatch.v1.json` and regression protection. The handoff itself is a subsequent tracked change requiring its own PR and CI acceptance. **No** host-side live scene classifier, real disposable-save identity verification, Live Mode or hunger baseline has been observed through this cloud lane. BI-002 stays ACTIVE.

## 2026-11-07 — Local agent re-entry after BI-SCENE-MAP (focus tool, Live Mode still blocked)
Local checkout fast-forwarded to `4cf8cf22`. `python -m scripts.check_scene_contract` PASS (35 scenes); full unittest 141 OK; doctrine/horizon PASS. Overnight `TS4_x64` pid from `bi002-first-boot` remained alive but iconic (`-32000`). `ShowWindow` alone failed; `WM_SYSCOMMAND/SC_RESTORE` restored briefly then reminimized under agent computer-control. Session still `NEW_GAME_CAS_REQUESTED`; no Resume, no personal-save navigation, no Live Mode confirm. Promoted the restore path to `python -m scripts.game_host focus` with an explicit focus-only proof ceiling. **Operator must finish disposable CAS → empty lot → Live Mode without the overlay, then reply `READY_LIVE`.** Hunger baselines remain 0/5.

## 2026-11-07 — Disposable Live Mode via PrintWindow (bi002-quiz-boot)
**CAS→Live disposable lab gate: LOCAL_OBSERVED COMPLETE for host path; NOT GAME_CERTIFIED / hunger still 0/5.** Run `bi002-quiz-boot` (pid 45380, borderless 1920×1080, PrintWindow). Disposable adult **Charlee LabLab** (arbitrary Bodybuilder fill), permanent home **Bargain Bend** empty lot, Live Mode confirmed `LIVE_REPORTED_UNREVIEWED` for patch **1.121.361.1020** with `capture:live-lablab-001` (+ empty-lot proofs `empty-lot-home-live.png` / `empty-lot-home-saved.png` / `goal-audit-live.png`). `game_baseline` recorder ready (`RECORDER_READY`, studio `NOT_OBSERVED`). Lab save **My Saved Game 3 / Slot_00000004** only; Richardson untouched; no Resume. Durable CAS→Live mechanics: `scripts/cas_place_live.py` (empty-lot-first + relocate/Needs/Build coords) and `docs/GAME_HOST.md` relocate/HUD notes — future sessions need not stop at character creation. BI-002 hunger baselines remain a **separate** next gate.

**Empty-lot home (LOCAL_OBSERVED, 2026-11-07):** Permanent Move Household completed for LabLab → Willow Creek **Bargain Bend** (30×20 empty). Manage Worlds green plumbob now on empty lot; Live Mode title shows Bargain Bend / LabLab; funds **§12,708** (Streamlet sale + lot cost). PrintWindow proofs: `dist/game-host/bi002-quiz-boot/empty-lot-home-live.png`, `empty-lot-home-saved.png`. Lab slot **My Saved Game 3 / Slot_00000004** overwritten only; Richardson slots untouched. Durable relocate path: Live HUD Manage Worlds pin `(1558,22)` → Save and Go `y≈556` → lot ellipsis → Move truck `(1692,1000)` → Bargain Bend `(1400,840)` → confirm truck/check. Prefer Sim Story quiz on next CAS boot.

**Instincts / hunger prep (LOCAL_OBSERVED, same run):** Needs panel `(1822,1062)` earlier showed Hunger ~0.40; by late night Hunger was critically red (starving). Placed **Crisponix Budget Dee-Lux (Used)** fridge §215 on Bargain Bend (funds §12,708→§12,493; later §12,263 after accidental sink placements). Build enter `(1505,22)` / exit Live people `(1585,35)`. Proof: `dist/game-host/bi002-quiz-boot/build-fridge-placed.png`, `live-after-build.png`, `empty-lot-fridge-saved.png`. Toilet not reliably placed (bathroom art clicks hit sinks). Timed vanilla `seconds-to-eat` baselines still **0/5**.

**Instincts host planner (2026-11-07, OFFLINE + LOCAL_OBSERVED needs):** Added `betterinstincts/instincts_host.py` + `scripts/instincts_plan.py` — six-need recovery plan from observed motives, object-availability gates, player/busy abstention, and **Save As `BI_CONT_*` only when all six needs are green**. Never DELETE/OVERWRITE/RESUME or touch user-named saves; `BI_TMP_`/`BI_CONT_` remain hints pending registry attestation. School dialog: intended Send Alone; Live observation landed on school lot with Charlee (High School Free Time) — Energy/Hygiene critical, plan next=`wash`. Snapshot `dist/game-host/bi002-quiz-boot/needs-snap-school.json`. Hunger live_cert still 0/5.

**MERGED:** [PR #18](https://github.com/EndeavorEverlasting/BetterInstincts/pull/18) → `main` at `559de8eb03e9bfd60b067baebad2dcf0d1514e4a` (CI test SUCCESS). Live six-need greening + `BI_CONT_` Save As remain OPEN on the disposable LabLab session.

**Decision-prompt eval host stack (2026-11-07, OFFLINE + LOCAL_OBSERVED rock card):** Catalog `contracts/decision-prompts.v1.json` (`school.geology.rock_collection`, `school.attend.join_or_send_alone`) + `betterinstincts/decision_eval.py` + `betterinstincts/host_stack.py` + `scripts/decision_eval.py`. Heuristic scores chance cards against six-need safety and prefer-home-control; `measure_need_deltas` records host influence. Live: ROCK COLLECTION → clicked **No stealing today** (~960,598); receipt `dist/game-host/bi002-quiz-boot/rock-decision-receipt.json`. Scores are not whim/skill API proof.

**MERGED:** [PR #19](https://github.com/EndeavorEverlasting/BetterInstincts/pull/19) → `main` at `eb1ff304fea278b654513ee3c97bf74135870b76` (CI test SUCCESS). Live recovery still OPEN: Charlee reloaded at Copperdale High School (Nap+Toilet queued); Hunger/Fun/Social critical; fridge remains on Bargain Bend; phone travel home unproven this pass. `BI_CONT_` Save As still gated on all-green needs.

**Live viewport black RCA + host ladder (2026-11-07):** LOCAL_OBSERVED PrintWindow `FULL_CLIENT_BLACK` on `bi002-quiz-boot` after MW Just-Go → empty-lot CAS abort → night Bargain Bend. Operator secondary-monitor sneak: void + thin lot-platform wireframe that **tracks the mouse** → engine alive (`VOID_LOT_PLATFORM_WIREFRAME`); not a hang. Sims was on monitor 2 (computer-use primary-only is blind). Leading hypotheses: (H1) camera/world lighting loss after CAS-abort+MW churn; (H4) mouse-tracking platform ⇒ try camera/Build↔Live before reboot; (H2) unlit night empty lot; (H3) desktop-capture/secondary-monitor trap. Codified in `contracts/viewport-black.v1.json`, scene `live_viewport_black`, `betterinstincts/viewport.py`, `scripts/viewport_recover.py` (camera ladder → authorized WM_CLOSE restart; never Resume). Host stack fails closed to viewport recovery before needs clicks. Six-need greening OPEN until viewport OK.

## 2026-11-07 — P95/P67/P62 host journey evaluator (offline)
Implemented version-bound chosen-save boot/map/Live, two scene cues, registered disposable save safety, viewport/restart and critical-needs Join regressions, separate needs/optional whims/skills deltas, CI and a read-only runner. Fixed host_stack control precedence for absent/busy/player-directed Sims. Offline proof only; live black recovery, needs-green and BI-002 hunger 5+5 certification remain unproven. See docs/HOST_EVAL.md.

## 2026-11-07 — Buy-menu stuck RCA + Save and Exit (LOCAL_OBSERVED)
Operator correction on `bi002-quiz-boot` (pid 45380, patch `1.121.361.1020`): the durable stuck surface was **Build/Buy purchase catalog** at Copperdale High School (High School Items tray), not Live Mode void. Camera ladder alone stayed anomalous; WM_CLOSE posted without immediate exit; recovered UI showed Save Game? → **Save and Exit** → SAVING… → `TS4_x64` process count 0. Contract updated: C9, H5 (rank 1), A7. Receipt `dist/game-host/bi002-quiz-boot/save-exit-receipt.json` (Git-ignored). Six needs green, `BI_CONT_` Save As, and BI-002 hunger 5+5 remain **NOT_OBSERVED**.

## 2026-11-07 — Codified black→Buy host fallback (ENTER_BUILD_BUY_UNSTICK)
Durable host logic so future agents do not rediscover the unstick: `contracts/viewport-black.v1.json` `fallback_mechanisms.FB_BUILD_BUY_UNSTICK`, ladder step `ENTER_BUILD_BUY_UNSTICK` (Build hammer only), classifier `BUILD_BUY_CATALOG_RECOVERY`, recoverer stop-state `RECOVERY_BUILD_BUY_UNSTUCK`, and `host_stack.evaluate_turn` `fallback` routing for black viewports. Live exit is a separate step. Patch-like host behavior; not GAME_CERTIFIED.

## 2026-11-07 — Host-menu reboot journey (Memory Boost → Load → LabLab Play)
LOCAL_OBSERVED after true TS4 relaunch (`bi002-lablab-reboot`, pid 66096, patch `1.121.361.1020`): main menu blocked by **MEMORY BOOST IS NOW ON**. Codified durable transitions in `contracts/host-menu.v1.json` + `betterinstincts/host_menu.py` + `scripts/host_menu.py` (+ `menu_blockers`, scene `memory_boost_modal`). Journey forbids Resume/Delete/Richardson. Agents must run `host_menu` rather than rediscovering clicks. Live Mode / six-needs still open after Play dispatch.

## 2026-11-07 — Scene-keyed host-menu resume (domicile + Sim profile)
Codified mid-journey substeps and `--from-scene` resume: map domicile (`select_lablab_domicile`), lot Play, then `select_sim_to_play` → Charlee `(838,392)` → Play `(1840,1005)`. Scene catalog adds LOCAL_OBSERVED `select_sim_to_play`. `game_host navigate` menu-blocker dismiss runs only when `gui is None` on win32 (FakeGui CI skips SendInput). P97 ADAPT: live host proof stays Windows-local; GHA remains offline FakeGui (Automation `entire-local-continuous` Actions-optional pattern; BI does not require Entire). LOCAL_OBSERVED: `--from-scene select_sim_to_play` on pid 66096 reached Live at Copperdale High School (`CONTENT_PRESENT`, capture `after-select-sim-play.png`). Six-needs remediation and BI-002 hunger cert still open.

## 2026-11-07 — P95 host autonomy: glossary, listener, presence, MAP_TRAVEL
Operator corrections: (1) do not in-frame walk-thrash for critical needs — **MAP_TRAVEL** to home fridge/bed; (2) opt-in listener so evaluators can EMULATE good queued behavior and OPTIMIZE bad/suboptimal; (3) respect Play — host yields when cursor/focus is on the Sims canvas or player-directed. P95 program design in `docs/HOST_AUTONOMY.md` + `docs/GLOSSARY.md`. Contracts: `glossary`, `behavior-matrix`, `host-listener`, `player-presence`, `needs-force` v2. Libraries/scripts: `behavior_eval`, `player_presence`, `host_listener`, `host_automate`, `needs_force`. `host_stack` next_gate `MAP_TRAVEL_HOME_FIRST` when critical+off-lot queue. No autorun daemon; evaluate-only until separate `--execute`. Live hunger remediation / BI-002 cert still OPEN.

## 2026-11-07 — Host funds subsidy + durable Money inject
Operator: under **§100**, show a Sims-styled **HOUSEHOLD NOTICE** ("Oops, it looks like decisions were made… Simolean federal bank?") with Yes/No; Yes runs host inject. P95 v2 **mode-agnostic** stack: soft-focus → **Ctrl+Shift+C** → **`testingcheats enabled true`** → try **`Money N`** → **`motherlode` × remaining chunks** — works in **Live / Build / Buy**; **never force F1** while the operator builds. LOCAL_OBSERVED on `1.121.361.1020`: motherlode +§50,000 after testingcheats; Money may no-op; no-foreground SendInput is a silent miss. Contract `contracts/host-funds.v1.json` v2, `betterinstincts/funds_inject.py`, `scripts/funds_inject.py`. School **Join** under crisis remains a host anti-pattern (Send Alone). Proof ceiling: HOST_SENDINPUT_CHEAT_DISPATCH — not BI-004 income, not GAME_CERTIFIED hunger.

## 2026-11-07 — P67/P62 progression + CI honesty evaluators (trifecta)
P95 call-stack for repository-wide progression eval; P67 framework + P62 correctness/efficiency cases. Scores **vision_marker_rate**, **scaffolding_rate**, **product_progression_rate** (BI-002…BI-006 certified fraction), **hunger_trial_rate**, and **ci_game_gap**. Fail-closed on promoting offline CI to GAME_CERTIFIED / playable, closing BI-002 without 5+5+rollback, or reordering needs→income→skills→career. Owners: `contracts/progression-eval.v1.json`, `betterinstincts/progression_eval.py`, `scripts/progression_eval.py`, `docs/PROGRESSION_EVAL.md`, CI step. Current floor expected: `SCAFFOLDING_AHEAD_OF_GAME` with `product_progression_rate=0.0`. Does **not** close BI-002.

## 2026-11-07 — Horizon continuity contract + GAME-1 abstention (player building)
Encoded North Star → Continuity opener in `contracts/horizon-continuity.v1.json` / `docs/HORIZON_CONTINUITY.md` with CI `check_horizon_continuity`. Selected investigation remains **BI-002 GAME-1** per P141 PR #31. Open item `FUNDS_PREFERRED_NON_MOTHERLODE` (exact-funds path TBD; motherlode chunks interim). LOCAL_OBSERVED: TS4 pid 66096, patch `1.121.361.1020`, Bargain Bend LabLab still in **Build Mode** (§968,020) — host **abstained** from F1/hunger clicks (PLAYER_FIRST / BUILD_OR_BUY_MODE_ACTIVE). live-cert run primed when Live is free; hunger trials still 0/5.

## 2026-11-07 — Event balance call stack (outdoor-social RCA)
Operator: lounge party socials always walk outdoors in rain despite indoor negative space; event goals lag; needs + homework collide. /design + trifecta: `contracts/event-balance.v1.json`, `docs/EVENT_BALANCE.md`, `betterinstincts/event_balance.py`, host_stack gates `EVENT_INDOOR_ROUTING` / `SURVIVAL_NEEDS_BEFORE_EVENT` / homework hold. Leading RCA `H1_VENUE_OUTDOOR_MEETUP`. LOCAL_OBSERVED capture `operator:event-outdoor-social-20261107`. Proof ceiling: host call stack, not EA autonomy rewrite; BI-002 hunger still open.

## 2026-11-07 — Moodlet strip sensing (P95 + P124 holism)
Gap: host ignored bottom-left emotion/moodlets (VERY ANGRY + scared/angry/uncomfortable) that steer behavior and pressure needs. Added `contracts/moodlets.v1.json`, `betterinstincts/moodlets.py`, wired through `host_stack` + `event_balance` (`TENSE_MOOD_OUTDOOR_SOCIAL` reinforces indoor retarget). H6 mood RCA promoted PLAUSIBLE. Proof ceiling: supplied labels only (`SENSOR_NOT_SUPPLIED` if absent). Control-handoff tests isolated to temp lock root to clear SCREEN_OWNER_BUSY flake.

## 2026-11-07 — Sit and Chat Here indoor grounding (P95 + trifecta)
Operator: outdoor-social idiocy is avoidable — **Sit and Chat Here** on indoor seating grounds conversation so pathing cannot re-resolve to the sidewalk meetup. P95 updates `EVENT_INDOOR_ROUTING` primary route to `SIT_AND_CHAT_HERE_INDOOR`; action `CANCEL_OUTDOOR_WALK_SIT_AND_CHAT_HERE`; RCA `H9_GREET_WITHOUT_SEAT_GROUNDING` LEADING; glossary terms; host_stack fallback carries `primary_route`. Live pie-menu SendInput still OPEN (`SIT_AND_CHAT_HERE_LIVE_DISPATCH`). Does not close BI-002.

## 2026-11-07 — Event goal → action catalog (P95 + trifecta)
Operator: hard to discover which interactions satisfy social-event HUD goals. Added `contracts/event-goals.v1.json` + `betterinstincts/event_goals.py` mapping lounge-party goals (drink, be_silly, tell_jokes, friendly_socialize, talk_about_food) to concrete indoor pie-menu steps; wired through `event_balance.goal_plan` and host_stack `EVENT_GOAL_PROGRESS` fallback. Queue match flags non-covering greets. Live HUD tick confirmation OPEN (`GOAL_TICK_LIVE_CONFIRMATION`). Does not close BI-002.

## 2026-11-07 — Build/Buy optimize catalog (P95 + /design + trifecta)
Operator Build Mode tooltip on Bargain Bend (**Brick & Plaster**: Lot Environment Gain 1, Eco Footprint Industrial 1). P95 program: deterministic maximize for Environment Gain / Green / Industrial / balanced Env+Green via versioned catalog (Spa Day / Enchanted env+2, Horse Ranch green+2 attested). Owners: `contracts/build-optimize.v1.json`, `docs/BUILD_OPTIMIZE.md`, `betterinstincts/build_optimize.py`, `scripts/build_optimize.py`, host_stack optional gate. Proof ceiling: offline ranking only — live Shift+apply paint and neighborhood meter observation remain OPEN. Does not close BI-002.

## 2026-11-07 — Yield walls: dual Env+Green max 2/2 (P95 + trifecta)
Operator lab: **Veins of Gold Marble Walls** and **Working Bricks** each LOCAL_OBSERVED at Lot Environment Gain **2** and Eco Footprint Green **2** (operator max found); applied interior/exterior for yield over aesthetics. Catalog + `MAXIMIZE_YIELD` default; dual-stat score beats Env-only or Green-only 2s; unknown pack still ranks when operator-attested. Pack IDs TBD. Live apply / meter proof still OPEN; BI-002 hunger still ACTIVE.

## 2026-11-07 — P141 strategic scout after progression evaluator merge

**Owner objective retained:** free, community-native, player-first Sims 4 autonomy: responsible adult needs and cross-need balance before sustainable **observed** income, then skills, then careers, while preserving leisure/personality, reversibility, per-Sim control, patch-specific safety and no save mutation. **This is the product, not an offline scoring engine.** PR #30 (`main` `9f238fb`) brought vision/scaffolding/product rates and CI honesty; recorded product progression and hunger trials remain **0.0**. Repository history includes locally observed game navigation and Live Mode, but no qualifying hunger experiment.

**P141 outcome:** five theses compared and falsified; selected one narrow next investigation — obtain a genuine, attributable, player-safe **vanilla hunger observation** on a confirmed exact patch via existing host/scene/evaluator and `live_cert` workflows. **Route P07 to BI-002 GAME-1 local agent**; if observation interface proves unworkable, only then route a narrowly scoped P95 design. Do **not** prioritize more synthetic evals, income cheats, general listener loops, or a unified engine ahead of gameplay. Full decision, alternatives, falsification and proof ceiling: [2026-11-07 P141 scout](STRATEGY.md#2026-11-07--p141-scout-live-certification-evidence-seam-after-pr-30). **BI-002 ACTIVE / GAME UNPROVEN**; ≥5 vanilla + ≥5 modified + reversible package + rollback + queue safety + maintainer review remain required. No new live-game proof claimed by this documentation-only change.

## 2026-11-07 — Human/agent/host interoperability — P95 then Trifecta

**Operator decision:** BetterInstincts host screen control must defer immediately to real player activity, remain paused during input, and become eligible again after a configurable, trustworthy idle interval; the operator should not need to wrestle for mouse focus. **Pausing the host is not pausing gameplay.** Explicit player direction and personality still win; no hidden input hooks, default daemon, global scans, save mutations, or premature income/skill/career activity. This is a cross-Horizon user-experience invariant, with **BI-002 hunger** remaining the first live product gate.

**Implemented offline candidate:** `control_handoff` is the arbitration state owner (8s default / 1–120s bounded), used by `player_presence`, `host_listener`, `host_automate` and a one-shot control CLI. `needs_force --execute` now requires an ACTIVE named listener session, actual PID and a single selected step, probes before focus, reconfirms after focus, then dispatches no more than one click. The existing Win32 input-age source is used on demand; unknown age and input anywhere on the desktop cause yield. The local agent must re-observe scene/queue and reacquire admission for each next step. P95 call stack and competing design options are in [HOST_AUTONOMY.md](HOST_AUTONOMY.md#2026-11-07--p95-human--agent--host-control-handoff-trifecta).

**Proof ceiling:** synthetic call-stack/regression only until the live P08 interruption-and-resumption test on an authorized disposable lab save; no gameplay package or live hunger trials produced by this change. Other direct click adapters await explicit shared-barrier adoption. The Horizon path stays needs → income → skills → career and BI-002 stays ACTIVE.

**P95/Trifecta second-pass correction:** add exclusive per-game-PID screen ownership across participating agent/host executors, and recheck session ACTIVE just before SendInput. `PAUSED_FOR_AGENT` identifies contention separately from human input. Prevalidate receipt paths so bad output destinations cannot trigger an unreceipted click. Tests cover concurrent-owner rejection and session deactivation. Still not a live-game claim.

## 2026-11-07 — P124 then P141 after PR #34 / #38 (interrupt-safe)

**Floor:** `main` included handoff (`85f0dab` / PR #34) and Sit-and-Chat indoor grounding (PR #38). Operator actively building in a live Sims session; host must not contend for the screen. Issue [#35](https://github.com/EndeavorEverlasting/BetterInstincts/issues/35) remains the P08 live handoff acceptance owner.

**P124:** ranked duplicated Win32 left-click / wheel / right-drag helpers across host UI scripts as the highest-impact editability hotspot for the coming adapter-barrier work. Extracted behavior-preserving owner `scripts/win32_input.py`; `needs_force`, `host_menu`, `menu_blockers`, `funds_inject`, and `viewport_recover` now delegate. CAS absolute-move scripts deferred. Characterization in `tests/test_win32_input.py`. No live SendInput and no handoff-policy change.

**P141:** refreshed [STRATEGY.md](STRATEGY.md#2026-11-07--p141-scout-post-handoff--sit-and-chat-floor-interrupt-safe). Selected next offline investigation: wrap remaining shared-control adapters under the existing `control_handoff` barrier (issue #35 adapter lane) via **P07**. Live P08 interruption/resume stays mandatory but **BLOCKED_OPERATOR_BUSY** while building. BI-002 hunger remains the parent product gate and is not closed by this scout/refactor.

## 2026-11-07 — P97 → P95 → Trifecta reviewed-player judgment learning

**New operator objective:** for now, the human player's contextual judgment often exceeds the host agent's; BetterInstincts should learn recurring patterns from *human-reviewed, helpful or harmful gameplay decisions*, across action sequences, moods/styles and use cases, and eventually become more competent **without replacing player agency or personality**. Prefer demonstrable learning over another broad planner. Preserve **needs → income → skills → career** and keep BI-002 hunger the first real game-certification gate.

**P97** source-level inspection: Lot51 event handlers, River incremental learning/prequential evaluation, hmmlearn hidden Markov modeling; choose simple contextual first-order counts with abstention rather than dependency-heavy unsupervised state inference or silent logging. **P95** introduces one pure model owner `betterinstincts/judgment_learning.py`, an explicit local CLI and opt-in listener-advisory seam. **Trifecta** adds error-path and player/scene/version/consent tests; learner can never execute UI, train from unreviewed clicks or mutate saves. This is an **OFFLINE_REVIEWED_DEMONSTRATIONS_ONLY** implementation, **not** playable-mod proof or evidence that learning improves real Sims gameplay. Full contract: [JUDGMENT_LEARNING.md](JUDGMENT_LEARNING.md). P04 local handoff follows integration; BI-002 remains ACTIVE.

## 2026-11-07 — P04 canonical local runtime learning/cert handoff

PR #41's reviewed-judgment learner was merged to `main` at `13815fe5a6437e1351a95dbcfbd6026cf7317c64` with offline tests, bounded explicit teaching, an aggregate contextual Markov-style model, chronological baseline comparison and opt-in `host_listener` advisory. **P04** now owns a durable local continuation: [handoff](handoff/BI-JUDGMENT-LEARNING-P04-2026-11-07.md) + [typed lanes](../plans/active/BI-JUDGMENT-LEARNING-P04.execution.v1.json). The first local agent must inspect the exact current patch/disposable save and acquire genuine operator-reviewed outcome labels before reporting a learned game benefit. This handoff does not certify the mod or close BI-002, and no local game launch or human review is asserted by provider-side completion.

## 2026-11-07 — Active Sim profile inspection (P95 + /design + trifecta)

Operator gap: gardening desire visible in moodlets without a durable way to check skills, preferences, traits, or whims. **P95** call stack + player discovery map in [`docs/SIM_PROFILE.md`](SIM_PROFILE.md) / `contracts/sim-profile.v1.json`. Host evaluates supplied Simology/skills/likes/dislikes/whims with composed moodlets (`betterinstincts/sim_profile.py`); `host_stack` attaches read-only `sim_profile` under gate `SIM_PROFILE_INSPECT`. Proof ceiling: `SUPPLIED_SIM_PROFILE_OBSERVATIONS_NOT_VISION_API_NOT_BI005` — not skill-growth certification, not vision, not a new game UI. BI-002 hunger remains ACTIVE.

## 2026-11-07 — School-day goals (P95 + /design + trifecta)

**Operator correction:** after multi-day needs recovery, LabLab school performance still suffers; homework is blocked on school **premises** during Morning Free Time; top-left school HUD (`Study for Exams`) is the actionable academic path; pinned Clumsy whim **Not Stumble for 4 Hours** favors sedentary study. **P95** adds `contracts/school-day.v1.json` + `betterinstincts/school_day.py` (goal→High School pie catalog, `HOMEWORK_PREMISES_BLOCKED`, pinned-whim sedentary preference). Wired through `host_stack` + opt-in `host_listener`. **P82** hypothesis: green needs + school-day goal queue beats vanilla / premises-blocked homework chasing. **P08** listener tick against live Copperdale observation is LOCAL_OBSERVED plan-only — HUD goal tick confirmation remains OPEN. Does not close BI-002 or certify careers.

## 2026-11-07 — Scenario scoring goals (P95)

**P95** adds `contracts/scenario-goals.v1.json` + `betterinstincts/scenario_goals.py`: Earn §250 / Craft an Object / Get a career HUD catalog with horizon-deferred career (`SCENARIO_CAREER_DEFERRED`), earn-before-career priority, and forbidden `motherlode_for_scenario`. Gates `SCENARIO_GOAL_PROGRESS` / `SCENARIO_CAREER_DEFERRED` on `host_stack` after school homework premises block; school day outranks scenario. Capture `operator:scoring-simoleons-20261107`. Not income/career GAME_CERTIFIED proof.

## 2026-11-07 — Teen homework career-performance (P95 + P124)

**Operator correction:** teen at home Wed night; career panel High School Student daily task = homework (not scenario Get a career); homework **not** in inventory but **on lot surface** (dining table); operator put book in inventory after lot scan; hunger critical; queue Use Toilet + Take a Shower; computer desk on lot. **P95** adds `contracts/teen-homework.v1.json` + `betterinstincts/teen_homework.py` (recovery ladder headed by `LOT_SCAN_PUT_HOMEWORK_IN_INVENTORY`, `SURVIVAL_BEFORE_HOMEWORK`, inventory-missing path). **P124** small helpers for survival/recovery/lot-scan/gate pick. Wired `host_stack` + `host_listener` (`inventory_has_homework`, `homework_on_lot`, `available_objects`, `life_stage`). Proof ceiling `HOST_TEEN_HOMEWORK_CATALOG_NOT_EA_API_NOT_BI006_CERT`. Capture `operator:teen-homework-missing-20261107`. BI-006-adjacent only — does not close BI-002/BI-006.

## 2026-11-07 — Teen day journey + school presence + Morgan invite (P95 + Trifecta)

**Journey continuity** (`docs/TEEN_DAY_JOURNEY.md`): school-day goals → scenario Scoring Simoleons → homework missing/lot-scan/put-in-inventory → survival-first → camera≠Sim premises while at school → after-school homework in inventory → classmate invite “Morgan” occult UNKNOWN.

**School presence:** `resolve_sim_premises` / `sim_at_school` / `camera_lot_kind` — home camera must not fire lot-scan homework while Sim is at school.

**Social opportunity:** `contracts/social-opportunity.v1.json` — unique Sims-library lookup before OK; ambiguous/missing/unknown/vampire → Cancel; unique HUMAN → OK allowed. App owns the decision. Capture `operator:invite-morgan-occult-unknown-20261107`. Live Cancel observed; live OK after library evidence remains open.

## 2026-11-07 — Curious Catalog gardening secrets (P95 + trifecta)

**Operator:** rare/alien/hydroponic grow gear trapped behind chat shorthand `bb.showhiddenobjects / buydebug` (slash-join fails); host must never advance sim speed. **P95/P82/P07** add `contracts/curious-catalog.v1.json` v3 + `docs/CURIOUS_CATALOG.md` + `betterinstincts/curious_catalog.py` + `scripts/curious_catalog.py`: opt-in session, immersive CURIOUS CATALOG notice (default Not Today), one-command-per-line reveal, ranked `money_garden_shop_list` (Quill/Dragon/Money Tree/Rare seeds/Hydroponic). Capture `operator:curious-catalog-gardening-secrets-20261107`. Does not close BI-002.

## 2026-11-07 — Fun service tandem lanes (P95 + trifecta)

**Operator:** Sims under-serve Fun; guests make them queue behind each other on the same activities. **P95** adds `contracts/fun-service.v1.json` + `betterinstincts/fun_service.py`: independent Fun service with parallel lanes (portable, electronics, creative, social/physical, playful everyday/exclusive, child/toddler). Guest/occupied contention prefers phone/tablet/earbuds; sibling lane claims prevent monolith pile-up; playful-exclusive fail-closed without PLAYFUL. Wired `host_stack` gate `FUN_SERVICE_PLAN`. Architecture: tandem lane services, not one mega-queue daemon. Live dispatch OPEN (`FUN_LANE_LIVE_DISPATCH`). Does not close BI-002.

## 2026-11-07 — Navigating Needs host tandem (P95 + P124 + trifecta)

**Operator:** EA top-left **Navigating Needs** Discovery Quest panel suggests need actions; BetterInstincts should work in tandem rather than invent a parallel Needs chrome. **P95** call stack in [`docs/NAVIGATING_NEEDS.md`](NAVIGATING_NEEDS.md) / `contracts/navigating-needs.v1.json`. **P124** keeps a peer catalog owner (`betterinstincts/navigating_needs.py`) instead of stuffing goals into `scenario_goals`. Urgency-ordered panel goals → `NAVIGATING_NEEDS_TANDEM`; uncovered urgent motives fall through to need_services then instincts; Build/Buy yields. Wired `host_stack` + `host_listener`. LOCAL_OBSERVED: Bargain Bend Build Mode (panel Live-only; HUD tick OPEN). Capture `operator:navigating-needs-tandem-20261107`. Does not close BI-002.

## 2026-11-07 — Six-need tandem services (P95 ×6 + P124 + trifecta)

**Operator:** Independent Fun service is fine; holistically invent peer services for the other needs so they can run in parallel; land on main so agents reuse one durable system; factor with P124. **P124** extracts `betterinstincts/need_service_base.py` (normalize needs, freeness, lane planner). **P95** registry `contracts/need-services.v1.json` + lanes `contracts/need-lanes.v1.json` + orchestrator `betterinstincts/need_services.py`: hunger/bladder/energy/hygiene/social plan via need-lanes; Fun delegates to `fun_service`. Host gate `NEED_SERVICES_TANDEM` picks primary by motive urgency among READY plans. Anti-patterns: reinvent parser per agent, monolith mega-queue, background daemon. Live multi-Sim dispatch OPEN. Does not close BI-002.

## 2026-11-07 — Need-service load balance + assumption windows (P95 + trifecta)

**Operator:** Parallel need microsystems should load-balance with health checks; when one is off, host detaches that call stack, opens a new assumption window (scene/assumptions/options reset), and reweights exploration. Deterministic **P95** program design in [`docs/NEED_LOAD_BALANCE.md`](NEED_LOAD_BALANCE.md) / `contracts/need-load-balance.v1.json` / `betterinstincts/need_load_balance.py`. Wired through `need_services` → host gates `NEED_SERVICES_TANDEM` | `NEED_SERVICES_LOAD_BALANCE`. Decision prompts still outrank need-service plans. Non-urgent guest-blocked siblings stay DEGRADED. Proof ceiling `HOST_NEED_LB_HEALTH_ASSUMPTION_WINDOW_NOT_DAEMON_NOT_EA_API`. Does not close BI-002.

## 2026-11-07 — Domain cascade poll receipts (P124 + trifecta)

**Operator:** Holistic cohesion across needs, Simoleon budget, career/school, skills/whims, and relationships via polling and cascading receipts — joined to the need-service load balancer rather than a second needs queue. **P124** peer owner [`docs/DOMAIN_CASCADE.md`](DOMAIN_CASCADE.md) / `contracts/domain-cascade.v1.json` / `betterinstincts/domain_cascade.py` / `python -m scripts.domain_cascade`. Cascade order: needs (+ navigating_needs + LB) → budget → career → skills_whims → relationships. Player-first halts; LB detach findings propagate. Proof ceiling `HOST_DOMAIN_CASCADE_POLL_RECEIPTS_NOT_DAEMON_NOT_LIVE_CERT`. Live multi-domain ticks OPEN. Does not close BI-002.

## 2026-11-07 — P03 branch hygiene + P141 next gate

**P03:** Merged PR #53 (LB glossary). Deleted remotes fully contained in `main` plus superseded need-service/LB/adapter-docs forks. Left diverged historical remotes untouched pending salvage. **P141:** selected land domain-cascade then issue #35 `screen_admit` adapters; BI-002 remains parent. See [STRATEGY.md](STRATEGY.md#2026-11-07--p141-scout-post-need-services-mainline--branch-hygiene-p03). **P124:** domain_cascade reuses `need_service_base.normalize_needs` instead of a forked six-need parser.

## 2026-11-07 — Issue #35 screen_admit adapters (P141 C + trifecta)

**Offline:** `betterinstincts/screen_admit.py` + `--session-id` gates on `funds_inject`, `menu_blockers`, `viewport_recover`, and `game_host navigate` menu-blocker dismiss. Tests: `tests/test_screen_admit.py`. Proof ceiling `HOST_SCREEN_ADMIT_ADAPTER_BARRIER_NOT_LIVE_CERT`. P08 live handoff interruption/resume remains OPEN / operator-gated on a disposable lab save. `host_menu` / CAS helpers still uncovered. Does not close BI-002.

## 2026-11-07 — General hidden/free-item discovery host seam (P04)

**Operator:** Extend The Sims 4 cheat-console recipe to find all classes of hidden debug and world items (toothbrushes, dishes, crystals, ponds, invisible lights, trees, cars and streetlights), not only the gardening shelves; integrate as host logic and dispatch to the Windows local agent. **Current-runtime implementation:** isolated `feat/bi-hidden-object-host-p04-20261107` branch adds `contracts/hidden-object-discovery.v1.json`, read-only `betterinstincts/hidden_object_discovery.py`, CLI `scripts/hidden_object_discovery.py`, negative tests, prior ontology consultation, [docs/HIDDEN_OBJECT_DISCOVERY.md](HIDDEN_OBJECT_DISCOVERY.md), [P04 handoff](../plans/active/BI-HIDDEN-OBJECTS.P04.md) and [typed dispatch](../plans/active/BI-HIDDEN-OBJECTS.dispatch.v1.json). It reuses rather than rewrites `curious_catalog`, game scene/save guards and player-control leases. Safety: exact current patch + real two-source scene + lab-save attestation + player opt-in/idle/lease + paused state; no SendInput, speed change, unconsented placement, save mutation, or blanket free/available price claim. EA notes Build cheats do not necessarily require `testingcheats true`, which may disable console achievements; the user-requested order is preserved with a console-risk gate. **Pending independent evidence:** CI status, actual Windows game-host proof, item-by-item price evidence, BI-002 original hunger certification. Source-level artifacts do **not** close BI-002.

## 2026-11-07 — P04 hidden-object recipe retrieval and verification guard

**Operator correction:** The local Windows agent needs the actual five-step cheat-console / Build-Buy / `debug` workflow every time P04 inventories BetterInstincts work; an isolated handoff is too easy to overlook. **Ownership retained:** `contracts/hidden-object-discovery.v1.json#operator_playbook`; `AGENTS.md` explicitly registers the P04 handoff, `python -m scripts.hidden_object_discovery guide` retrieves all five ordered steps, and `python -m scripts.hidden_object_discovery audit --observation dist/game-host/hidden-object-p04-receipt.json` rejects missing/misordered step receipts or absent item/price observation evidence. `scripts/check_hidden_object_p04.py` and CI block removal of this route; `plans/active/BI-HIDDEN-OBJECTS.dispatch.v1.json` carries the trigger, ownership, step IDs and proof ceilings. P04 unrelated parent work only inventories/defers this lane; no irrelevant game input.

**Exact requested order:** open console with platform chord while on Sim lot, `testingcheats true` + Enter, `bb.showhiddenobjects` + Enter, optionally `bb.showliveeditobjects` + Enter, close console, enter verified Build/Buy via icon or `F2`, search bottom-left `debug`, select a visible `DEBUG` suggestion and inspect actual catalog/price. A cheat enabled toast and `§0` costs require actual observation, not blanket claims. EA warns testingcheats can affect console achievements. **Safety:** no autonomous keystrokes or purchases, never touch game speed, user saves protected, physical host proof independent; BI-002 hunger remains active. A structurally valid receipt never establishes in-game execution or independently validated screenshots.

## 2026-11-07 — Sustained Hidden Catalog Scout goal (post-P04 extension)

**Operator objective:** give Windows BetterInstincts agents meaningful catalog-discovery work they can repeat for hours, with resumability and actual findings. The scoped branch `feat/bi-hidden-object-scout-sustained-goal-20261107` adds `contracts/hidden-object-scout-goal.v1.json`, bounded `betterinstincts/hidden_object_scout.py`, `scripts/hidden_object_scout.py`, tests, [docs/HIDDEN_OBJECT_SCOUT.md](HIDDEN_OBJECT_SCOUT.md), and P04 handoff/dispatch entries. Default 240-minute mission, 40 unique candidate target, five rotating categories, 96-batch cap, reviewed-price separation, 15-second minimum per recorded batch, atomic ignored-dist checkpoint, idempotent retries and pause/resume/stop. Requires existing exact P04 unlock receipt, a fresh game Build/Buy observation, save identity, patch and player control before each batch; planner itself has zero UI input or autorun authority. **Proof ceiling:** repository/CI only until a local Windows agent supplies real observed item receipts. BI-002 hunger remains separate and active; this goal is no substitute for hunger certification.

## 2026-11-07 — Recursive house/lot environment model (P95)

**Operator corrections:** (1) floater/chair Build/Buy work rearranged Bargain Bend without recoverable pre-state; (2) do not act → extract checkpoint from scratch → reassess — accumulate environment understanding recursively while moving. **P95** selects `RECURSIVE_LOT_MODEL` in [`docs/HOUSE_STATE.md`](HOUSE_STATE.md) / `contracts/house-state.v1.json` / `betterinstincts/house_state.py` / `python -m scripts.house_state`. Model merges observations and mutation outcomes on one revisioned artifact; leases bind actions to entity targets; blank-slate reassess and blind bulk inventory sweeps fail closed; destructive actions require lab Save As attestation. Recovery advice: load known-good save — never overwrite it with wreckage. Proof ceiling `OFFLINE_RECURSIVE_LOT_MODEL_NOT_EA_SAVE_API_NOT_LOT_RESTORE_PROOF`. Does not restore the lot by itself; does not close BI-002.

## 2026-11-08 — Build integrity structure-first (P95 + P83 verify)

**Operator:** prior Build/Buy thrash deleted floor/walls/kitchen aesthetic/dining/futuristic sleep pod; treated outdoor as indoor; nested objects. **P83** verified damage claims against live capture. **P95** adds [`docs/BUILD_INTEGRITY.md`](BUILD_INTEGRITY.md) / `contracts/build-integrity.v1.json` / `betterinstincts/build_integrity.py`: `STRUCTURE_FIRST_SPATIAL_ADMISSION`. `house_state.admit_mutation` now requires `INTEGRITY_ADMIT` (indoor≠outdoor, floor-before-furniture, no nesting, protected zones, restore order). Proof ceiling `OFFLINE_BUILD_INTEGRITY_ADMISSION_NOT_LIVE_LOT_RESTORE`. Lot rebuild remains operator Load known-good or structure-first live restore — mechanisms no longer authorize the failure mode. Does not close BI-002.

## 2026-11-08 — Build spatial enclosure + story axes (P95 + trifecta)

**Operator:** finish the builder; classify **inside vs outside** and **FLOOR_1 vs FLOOR_2**; host must use those differences. **P95** adds [`docs/BUILD_SPATIAL.md`](BUILD_SPATIAL.md) / `contracts/build-spatial.v1.json` / `betterinstincts/build_spatial.py` (`ENCLOSURE_AND_STORY_AXES`). Inventory buckets + build order (F1 structure → F1 indoor → F2 structure → F2 indoor → outdoor floaters). `house_state.plan_next` / `admit_mutation` and `host_stack` Build/Buy turns consume the axes; F2-before-F1 and outside-as-inside fail closed. Proof ceiling `OFFLINE_BUILD_SPATIAL_AXES_NOT_LIVE_LOT_RESTORE`. Does not close BI-002.

## 2026-11-08 — Library save before room mutate (P95 + trifecta)

**Operator:** agents deleted house walls without saving the building to My Library first; host must preserve human judgment with a revertible library item before mutating a room. **P95** selects `LIBRARY_SAVE_BEFORE_ROOM_MUTATE` in [`docs/BUILD_LIBRARY_CHECKPOINT.md`](BUILD_LIBRARY_CHECKPOINT.md) / `contracts/build-library-checkpoint.v1.json` / `betterinstincts/build_library_checkpoint.py`. `house_state.admit_mutation` and `host_stack` fail closed on SLEDGE / WALL_ROOM_TOOL / MOVE_HOUSE_OR_ROOM / structure targets without a fresh `library_checkpoint`; game Save As is explicitly not a substitute. Proof ceiling `OFFLINE_LIBRARY_SAVE_ADMISSION_NOT_LIVE_GALLERY_WRITE`. Does not close BI-002.

## 2026-11-08 — Camera-safe host traversal (P95 + P97 + trifecta)

**Operator:** agents edge-scroll the map/lot for data, then leave the mouse on the screen edge while developing so the camera keeps panning. Want host-owned traversal logic and optional emulation of sibling-app vision features. **P97** inspects Automation visual-intelligence observe≠act and TokenCorridor deterministic-before-VLM; **rejects** cloning OmniParser/Paddle/Qwen into BI; **adopts** existing PrintWindow capture. **P95** selects `CAMERA_SAFE_TRAVERSE` in [`docs/CAMERA_TRAVERSE.md`](CAMERA_TRAVERSE.md) / `contracts/camera-traverse.v1.json` / `betterinstincts/camera_traverse.py` / `python -m scripts.camera_traverse`. Plans are capture-first, use bounded right-drag, and **must** terminate at `SAFE_CURSOR_REST`. `host_stack` gates `CAMERA_SAFE_REST` ahead of needs when the cursor is in the edge band. Proof ceiling `OFFLINE_CAMERA_SAFE_TRAVERSE_NOT_LIVE_CAMERA_PROOF`. P08 live park proof remains OPEN on a disposable lab window. Does not close BI-002.

## 2026-11-08 — Async needs and gardening continuation

The operator requested independent needs management while gardening continues,
including sleep rather than endless gardening. `host_tandem.run_tandem_session`
now observes through the existing listener while one interaction awaits its
outcome. Fresh ownership-bound gardening can suspend for an observed need
remedy; a fresh recovered snapshot can resume gardening. Player input yields
without queue cancellation. See [HOST_TANDEM.md](HOST_TANDEM.md).

Offline coroutine tests prove this sequencing, not live dispatch. The earlier
Natural Living Sleep Here interaction visibly started, but the later paused
scene showed Charlee awake with low Energy; recovery remains unproved. That
pause was preserved. No bed was bought or placed. BI-002 remains ACTIVE.

## 2026-11-09 — Room-census glossary diet (P78 correction)

The operator corrected a voice-transcription error: the intended sequence was **P95, P124, P78, Trifecta**, not P178. The existing read-only room census remains the implemented and merged foundation. P78 keeps room semantics in the code/contract, non-exclusive vocabulary in `contracts/glossary.v1.json`, a small operational `docs/ROOM_CENSUS.md` runbook and compact pointers from floor-activity docs. P82 guards term ownership, glossary table placement, corrected invocation identity and existing room behavior; P07 owns CI/main integration. P08 exact-game-build household/room sensors and live gameplay are still unproven; BI-002 remains ACTIVE.
