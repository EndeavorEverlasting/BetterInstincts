Warning: truncated output (original token count: 81833)
Total output lines: 2203

## 2026-11-15 — Container-backed BetterInstincts Play

`scripts.play` adds one foreground command for players and a JSON receipt for agents. The container checks startup source identity before the existing Windows installer and game-process admission run. Exact-byte launcher verification resolves the reproduced Windows install-retry failure. The first-run path preserves the active game and the certification-first save handoff. The Docker smoke and offline suite cover the shipped source. Actual Windows process, game-menu and Live Mode evidence remain separate. See [First run](FIRST_RUN.md#play-from-the-command-line).

## 2026-11-14 — Sixth Gear: certification-first save handoff before oldest-first trials

**Parent:** Finish the existing live Video Gaming preference prompt certification on its established game/session/save before routing later standardized trial certifications to the oldest operator-authorized lab disposable save. Preserve historical vanilla/modded Yes/No and rollback evidence; **do not restart to relearn it**. An existing running session takes priority; otherwise require an exact current-run pinned lab save, never a filename/age guess. `P141 → P95 → P82 → P08 → P07 → P124` sourced from MoonWake current skill/manifest/catalog. P141 rejected newest auto-load, prematurely oldest-first, replayed baseline trials and a competing desktop actuator. P95/P82 define a pure guarded two-stage route; P08 Windows/Sims current prompt unobserved here; P07/P124 wire a local ignored memo into existing first-run receipts and the canonical oldest-first ranker without game or save side effects. Source: `contracts/launch-certification-priority.v1.json`, `scripts/launch_save_route.py`, `tests/test_launch_save_route.py`, `docs/LAUNCH_CERTIFICATION_PRIORITY.md`. The separate active preference PR #263 and BI-002 hunger gate are not claimed closed. Main/CI/live states are independent provider truths.

## 2026-11-14 — MoonWake Closers: all-microsystem mathematical factoring and superior fallback

**Operator objective:** no isolated, unscalable equations; Bellman, Lagrange/KKT and Gaussian reasoning must be available to all microsystems, while allowing newly developed superior planners and relegating existing modules to fallback. **P83** independently recovered merged career #264 and already source-owned PS0245 `decision_horizon.py` (Bellman/KKT) plus PS0241 `ecology_forecast.py` (chronological holdout GP). **P03** consultation-first new common `microsystem_math.py`, 21-service registry, automated seven-domain cascade route, data-complete mathematical packets and player-first fallback. **P141** compared monolith rewrite, duplicated solver families, docs-only and compositional adapter; selected reuse with protected domain owners. **P124** preserves all existing `domain_cascade` receipts and original career/needs/aspiration services, no new game clicker or background worker; Gaussian remains deterministic until enough independent samples. **P04** future mathematical alternatives can compete on independent holdout and same hard feasibility; actual installed game-native integration remains separate P08/issue #171, not a fictitious provider-dispatched Windows agent. Regressions in `tests/test_microsystem_math.py`; machine contract `contracts/microsystem-math.v1.json` and [docs/MICROSYSTEM_MATH.md](MICROSYSTEM_MATH.md) own further expansion. PR/CI/merged states require provider verification; source-only math never grants `CONTROL_PERMIT`.

## 2026-11-14 — MoonWake Closers: reusable Sims experience durability and no-restart continuity

**Parent (operator):** The game has already been tested in vanilla and BetterInstincts-mod modes; Yes/No Video Gaming preference and rollback evidence already exist. On a fresh agent encounter, historical lessons should be recalled, not re-created through a new save/game restart. The currently open "IT BEGINS..." modal remains its own event. **MoonWake Closers canonical order:** P83 → P03 → P141 → P124 → P04 (exact definitions sourced from the private MoonWake prompt catalog and group manifest; this remote GitHub connector does not execute the host's local `prompt_group_walk.py`).

**P83 claim reconciliation:** PR #266's experience store was independently found merged on `main` at `18c5c4b5ad66e2736e02e7cbf071f8187d4e1d0c`; both historical GitHub jobs were SUCCESS. The code preserves deduplication/patch-profile keys/recall-without-current-dialog-completion, but its original `record_new` read and `os.replace` were not synchronized across independent agents. Two different new experiences could be lost when writers reused the same stale snapshot. This is a material recurrence/continuity defect, not a reason to repeat gameplay.

**P03 bounded first sprint:** Consultation-first isolated branch `fix/bi-experience-memory-writer-20261114` repairs the existing `betterinstincts/experience_recall.py` store. No new memory owner, new game automation, implicit startup, save change or unrelated MoonWake instructions mutation. Known/conflicting cases return without lock or file write; new facts use an exclusive local writer lock, latest-index recheck, and atomic replacement. A competing writer receives explicit bounded `EXPERIENCE_WRITER_BUSY` instead of erasing another agent's evidence. Tests include interleaved distinct facts, no-write on duplicates, contested writer, and lock-preserving behavior.

**P141 strategic discrimination:** (1) Rerun vanilla/mod trials to reconstruct knowledge — REJECT: existing evidence already meets historical recall use; (2) create another global asynchronous game-memory daemon — REJECT: duplicates existing local owners and violates consent/host boundaries; (3) accept previous write race — REJECT: may silently lose new experience; (4) serialise only truly new same-store inserts and re-read latest under lock — SELECT, narrow and no game effect. Separate worktrees retain separate ignored `dist` stores unless deliberately reconciled; there is no false assertion of automatic cross-worktree synchronization.

**P124/P04 ownership:** Keep `contracts/experience-recall.v1.json`, `docs/EXPERIENCE_RECALL.md`, `tests/test_experience_recall.py` and existing preference/host autonomy policy owners aligned. P04's next real host lane is local adoption of merged source, reusing existing `dist/live-cert/bi002-20261114` Yes/No/rollback evidence, seeding only absent experiences, and showing a repeated `recall` without Sims restart. Native response instrumentation remains PR #263; independent BI-002 hunger certification remains open. A GitHub handoff is not proof MoonWake agents or Windows gameplay were launched.

**Proof ceiling:** GitHub source/CI/merge must be checked at the exact final head; the previous reported P08 game run is inherited/local operator evidence and not re-run. No claim of live native callback registration or authenticated local trial-file readback from this provider.

## 2026-11-14 — Corrected oldest-first save trial governance (MoonWake P00 → P01)

**Operator correction:** The most recent Sims 4 save is **not** the most disposable; older saves are preferred for experimentation because recent saves may contain decisions users discover they need to undo much later. The revised rule applies only after the pre-existing `LAB_DISPOSABLE` origin/run/capture/game-version guard admits a record. Personal/unknown saves and lab continuations remain excluded, and age never grants rights to read, load automatically, overwrite, modify or delete any save.

**P00:** updated root AGENTS.md, detailed governance and canonical `save-policy.v1.json` with oldest-attested-lab-creation-first and no-selection defaults. **P01:** added a bounded advisory CLI, completeness checker and hostile-case tests, normal CI gate, original-owner docs, and a consultation record committed *before* behavior mutation. Missing/tied creation chronology or bad origin/running evidence abstains. Source and provider CI are separate from a real game; no Windows launch or MoonWake local stage-walker dispatch is claimed. The new method does **not** require restarting completed vanilla/modded experiments. See `docs/SAVE_CANDIDATE_PRIORITY.md` and `contracts/consultations/BI-SAVE-OLDEST-FIRST-P00-P01-20261114.v1.json`.

## 2026-11-14 — Prior experiences: memoize new, retrieve familiar, no Sims restart

**Operator correction:** Already-performed vanilla and modded Sims 4 trials, including Video Gaming Yes/No and rollback, are historical facts and should not trigger another game restart or generic investigation simply because the agent crosses a new conversation/session. The screenshot shows the Video Gaming offer currently open; recognizing an identical earlier mechanic is not proof the *current* instance was answered.

**Execution:** Added consultation-first, bounded, exact-build and installation-profile `betterinstincts/experience_recall.py` with `scripts/experience_recall.py` and tests. First new semantic outcome is stored under the explicit ignored repo `dist/experience-recall` owner; identical later experience returns `ALREADY_KNOWN` without another write or game trial, and `recall` returns `PAST_EXPERIENCE_RECALLED` without granting game input or treating today's dialog as completed. Conflicts HOLD without overwriting. Canonical contract: `contracts/experience-recall.v1.json`; local operator steps: `docs/EXPERIENCE_RECALL.md`. Existing chance-event memo, reviewed judgment learner and native preference map remain their original policy/evidence owners.

**Evidence integrity:** The reported earlier Yes response `0` added trait `258767` and buff `263631` to 3/3 active Sims; earlier No response `1` added marker `266814`. No-branch buff recipients and originating computer-task completion remain unknown. The new index starts empty on each unseeded local checkout; local receipt import is the first host step, NOT restarting Sims. Branch source/CI and game-native behavior are separate proof dimensions; independent BI-002 hunger certification remains active.

## 2026-11-14 — MoonWake Closers: Servo need telemetry after Sixth Gear #234

**P83 independent reconciliation:** [#234](https://github.com/EndeavorEverlasting/BetterInstincts/pull/234) was merged, but the code retained a source-continuity gap: a different Servo, game patch or swapped EA hook/HUD calibration could inherit HEALTHY/RECOVERING from earlier sensor health; changed sample IDs with nonmonotonic timestamps could also be promoted. A green, high Social level with proven steep native decline remained routine instead of triggering anticipatory diagnosis. Moodlet input was only capture-bound, not necessarily bound to the **same selected Sim, build and time**, risking inappropriate “happy” prioritization after portrait switches. Existing direct Servo four-motive and six-need human call stacks are preserved.

**P03/P141 action:** On consultation-first isolated branch, improve existing `betterinstincts/need_signal_fusion.py` owner, not a new standalone daemon or duplicate moodlet service. P141 compared UI-only panic (no numerical 3x inference), uninspected native runtime replacement (P08 blocked), redundant source-state engine (reject), and narrow continuity/forecast correction (selected). P124 maintains bounded schema with exact context, source monotonicity, conditional source-measured time-to-policy threshold and actor-bound fresh moodlet labels; P04 retains live independent EA-native/HUD-CV producers and authorized sensor-only recovery in [issue #235](https://github.com/EndeavorEverlasting/BetterInstincts/issues/235). This is advisory-only and does not cancel dancing, alter queues, operate screen or certify game effects. Native forecast horizon 30 Sim minutes and 0.55 normalized level are **offline policy settings**, not game-calibrated decay or proof chevrons equal 3×. P04 local walker/agent dispatch is not claimed when unavailable. BI-002 hunger and open PR #159 unchanged.

## 2026-11-14 — Sixth Gear: Career/Work panel and chance-card autonomous decision policy

**Parent objective:** routine autonomous career/work decisions **inside the installed game without human or desktop agent clicks**, with progressive-disclosure discoverability to prevent repeated manual teaching. Operator said a Work-panel screenshot will follow; source currently confirms `contracts/ui-microsystems.v1.json#panels.career` Live/J, existing `career_service` Work Hard, teen homework, and Green Technician daily task. No exact installed EA career event hook or response catalog is present in GitHub. **P141:** rejected Win32 clicker, unconditionally Work Hard, fixed Yes/No, and guessed EA hooks. **P95:** selected bounded risk-adjusted career chance-card policy behind existing `career_service` facade; exact observed recipient Sim, career, shift, event tuning/revision and complete source-backed response probabilities/effects. **P82:** synthetic risk, stale identity, player override, duplicate response, career variance and distinct response/effect/resumption tests. **P08:** installed Sims career-event hook/effects, game-native mod activation and actual event outcome/rollback unavailable to this connected GitHub runtime; this remains the real next game gate, independent of preference and BI-002 hunger live trials. **P07/P124:** machine contract, native route receipt, career facade, focused regression tests, four glossary terms and concise progressive router avoid parallel controllers and prompt bloat; record actual PR/CI/merge independently. This source work does not run MoonWake local `prompt_group_walk.py`, a real crew of subprocess agents, Windows Sims or the native gameplay effect. Parent remains OPEN for native automatic response certification. See `docs/CAREER_DECISIONS.md` and `contracts/career-decisions.v1.json`.

## 2026-11-14 — MoonWake Closers: purchase-dialog post-merge review repair

**Parent:** eliminate repetitive purchasing across any currently selected Sims household portrait, including scrollable ingredient/seed/medicine menus, without duplicating computer control or falsely claiming a native gameplay mod. Original purchase-dialog work: PR #250 merged at `085758e618d681ca52b287b80bcd0b1885c1e443`, both CI checks successful. Current MoonWake Closers source resolves **P83 → P03 → P141 → P124 → P04**. **P83:** reviewed source and actual PR comments after merge, finding three substantive defects: deferred mutable action injection, cart selection lost during reduced-spend-cap hold, and exact viewport matching rejecting legitimate intermediate scrolling. **P03:** consultation-first targeted policy, tests, native authority receipt. **P141:** selected repair inside existing `purchase_dialog.py` + `CooperativeScreenQueue`, not an independent clicker, rewriting the catalog, or buying all contents by default. **P124:** moved scroll placement to continuous known contiguous item-order spans while keeping observation signatures for discovery; deep-copy queued effects; retain reconciliation before holds. **P04:** parallel proof surface is independent CI test and peripheral/authority jobs; native in-game effect and local agent launch cannot be claimed through GitHub remote provider. `contracts/purchase-dialog.v1.json`, `docs/PURCHASE_DIALOG.md`, and focused tests own recurrence guards. **Proof ceiling:** source and CI/mainline as observed independently; game build native adapter and transaction remain separate under #171; BI-002 hunger remains independent. Source changes are not installed Sims gameplay.

## 2026-11-14 — MoonWake Sixth Gear: bottom-right HUD state intelligence (offline)

**Parent objective:** move repeated bottom-right panel visual interpretation from the agent into reusable BetterInstincts host logic, standardizing COLLAPSED / CONDENSED (continuous height) / EXPANDED (maximum), without conflating module selection, internal scrolling, selected Sim or player ownership.
**P141:** rejected per-frame agent explanations, blind coordinate clicking and a duplicate screen controller; selected existing `ui_microsystems`, `ui_chrome`, `screen_atlas` and `workflow_interop` owners plus one host perception seam. **P95/P82:** added two-cue personal-inventory color-band classification on the operator's eight 1919×1079 paused Live screenshots (local offline trial: eight classifications matched), normalized 0–1 height and a deterministic non-effect posture proposal; additional synthetic/negative tests cover cue disagreement, unsupported patch/geometry, operator control, stale scene/Sim, and HUD module conflict. **P08:** native event travel probe remains separately proved by local agent; no in-game panel open/resize/close, interaction completion, automatic garden dispatch, or rollback proof here. **P07/P124:** `betterinstincts/hud_panel_state.py`, `scripts/hud_panel_state.py`, `contracts/bottom-right-panel-states.v1.json`, tests, consultation, native route and `docs/HUD_PANEL_STATE.md` are source-scoped and reuse established interaction owners. No local MoonWake walker/Windows host or independent agents were run in this GitHub provider session. Provider PR/CI/merge status must be verified separately. Native follow-on issue #171 and BI-002 remain active.

## 2026-11-14 — MoonWake Closers: PS-0241 native dispatch acknowledgement after PR #253/#254/#255

**Operator parent:** an installed Sims mod must wake on native events and advance planned garden pickup to independently verified fertilization without desktop agents. Paused planning, live play, six-need and work deadlines, player priority and per-Sim continuity remain essential. **P83:** independently verified PR #253 merged at \`355392fab2bac8f7d4d104c96b3ae1450282ffa1\`, PR #254 and #255 already merged into newer main \`2e79e0ac1d1e3e8b2e032bb7d4540a91a499ac56\` at preflight, while PR #252 remains separate draft. **P03:** found false-positive native-effect assumption: \`PLAY\` proposal previously moved directly into awaiting state, without native queue acceptance, permitting ambiguous outcomes and stalls. **P141:** considered standalone desktop clicker (reject), all-DAG replacement of the ecology reducer (defer—would duplicate existing owner), and one source-proven queue-admission protocol (select). **P124:** kept per-Sim reducer cohesive and reused existing DAG/Bellman/GP policy owners rather than building another planner. **P04:** route real EA import/event registration, queue API identity and native package build/rollback to issue #171 and proven host; GitHub has no Windows Sims session. Implemented receipt-bound \`PROPOSED -> QUEUED -> VERIFIED\` and \`NOT_ENQUEUED\` non-effect recovery, plus tests. **Proof ceiling:** offline CI and merged source (verify independently); native installed/game effect/roll back still UNPROVEN.

## 2026-11-14 — PS-0241 generalized cross-domain activity DAG and GP timing

Source original: Prompt Scratch → Idea Inbox A11 (PS-0241). Separate branch introduces evidence-bound DAG planning for purchase → personal inventory → observed walking/unlocked teleport → career artifact → verification, with work/needs deadlines, budget and resilient per-Sim queue reconciliation. The existing domain cascade/semantic/task/queue/purchase/traversal owners remain authoritative; garden Planning/Play PR #252 remains untouched. Cross-capture completed steps require fresh revalidation before being excluded from plans. Bounded RBF/Matérn/periodic GP forecasts remain advisory and cohort-isolated. Source-only Python focused tests passed locally; no installed mod, native effect dispatch, local MoonWake walker or Sims live certification was observed. Native successor #171; independent BI-002 hunger certification remains open. Details: docs/ACTIVITY_CHAIN.md.

## 2026-11-14 — PS-0241 native-first ecology planning/play continuity and installer floor

**Parent:** The user requires an installed BetterInstincts native mod, automatically operating whenever time before work and six-need floors permits; no desktop agent should be needed during normal play. Local-agent proof: manual Super Fertilizer ground-to-Servo inventory transfer followed by Sixam Mosquito Trap Depleted→Good on build `1.121.361.1020`. That was not mod automation; Mods contained only `Resource.cfg`. Open native parent #171 and concurrent draft planning/time-window PR #252 remain distinct.

**P141 → P95 → P82 → P08 → P07 → P124:** P141 rejected desktop daemon, guessed patch hooks and uncalibrated GP; P95 selected existing gardening/continuity policy owners plus one capture-bound per-Sim intent reducer. P82 implemented finite deadlines, paused plan/play transition, native-outcome-bound pickup/fertilization, safe autonomy interruption recovery, and bounded 10–24 sample Matérn GP holdout-vs-deterministic fallback. P08 remains **BLOCKED_LOCAL_GAME_ACCESS_AND_EA_HOOK_PROOF**; provider actions cannot inspect host EA Python or game. P07/P124 source: `betterinstincts/ecology_intent.py`, `ecology_forecast.py`, `scripts/native_ecology_bundle.py`, tests, a consultation, native route decision and `docs/ECOLOGY_INTENT.md`. The packager is gated by source-bound verified native hook evidence and produces 3.7 bytecode only; its owned install/uninstall preserves other Mods. It is not an implemented EA hook or native gameplay certificate. PR/main, CI, installation and live evidence must each be independently verified. Preserve the existing host/needs queue owners and scope of PR #252.

## 2026-11-14 — Universal Sims purchase dialogs: scroll discovery, goal demand and anti-arthritis cart

**Parent operator objective:** Make all Sims purchase picker variants usable through a reusable, extensible repository engine across any selected portrait and household. Seven original screenshots show advanced apothecary's below-the-fold Lightning Root Leaf/Lump of Moss/Sage/Small Critter Bone, five-row seed/ingredient pickers and one-row Medicine with owned stock. **P141 → P95 → P82 → P08 → P07 → P124** resolved from current MoonWake Sixth Gear source; local `prompt_group_walk.py` and game host not run through GitHub. P141 rejects static page-length assumptions, blanket buy-all and competing desktop clickers. P95 separates source-scoped observed catalog scan from evidence-based material shortages and per-item spending decisions. P82 exercises adversarial snapshot/scroll/transaction receipts. P08 actual game-runtime/native hook remains **BLOCKED_LOCAL_GAME_ACCESS**. P07/P124 source changes: `betterinstincts/purchase_dialog.py`, `contracts/purchase-dialog.v1.json`, screenshot-fixture tests, native authority decision and `docs/PURCHASE_DIALOG.md`. No code claim of game effects or purchased resources; existing five-part picker and cooperative queue retain authority. Real live follow-on #171 and independent BI-002 hunger remain active. Track PR/merge/test proof separately from this source-design record.

## 2026-11-14 — MoonWake Closers: reconcile stopped-agent and household/career parent

**Operator parent:** agents must keep completing BetterInstincts goals rather than terminate after brief gameplay reports; sleep and promotion-aware Work Hard handoffs become deterministic source and ultimately native actions; every controlled discovery must be captured and converted into tested repository logic. **P83 source verification:** main had already merged #232 (sleep-to-awake roster), #233 (Work Hard advisory → next Sim), #240 (agent context + controlled semantic discovery) and #243 (human-pause active listener, disjoint observation/effect outcomes, full codification work-item pages). No live Sims Work Hard/portrait action is observed by GitHub. The older conflicting PR #231 adds a second liveness module; its code is source-only and not a live Codex stop hook. **P03 first safe repair:** implement a read-only parent-turn gate in existing `agent_context`, expose it through actual `AgentControlRunner`, add negative tests. **P141 options:** reject duplicate session controller/merging #231 as-is, screenshot-driven completion, unnecessary mouse automation; select owner-reuse and independent acceptance checks. **P124:** no new runner/daemon, preserve player-presence and passive-listener distinctions, no native/game effect claim. **P04:** connected GitHub provider supports bounded source/CI/PR proof; local MoonWake walker, P08 Windows game effects and local Codex stop enforcement require separate exact runtime proof. Promote action discoveries through existing `control_discovery.codification_work_items`; unknown source verification remains OPEN. **Next:** local issue #171 exact-patch EA work tone/portrait effect and game canaries, BI-002 hunger 5+5 trials/rollback remain ACTIVE.

## 2026-11-14 — Scalable contributor-training integration from PR #226

**Parent:** opt-in community evidence and trusted contributor pathway; reuse the already drafted VAE candidate review instead of parallelizing an independent trainer. **P141:** chose explicit semantic reviewed-case bundles alongside inert VAE weights over automatic federation/raw gameplay uploads. **P95/P82:** schema/digest/privacy/replay design with positive and adversarial tests. **P08:** GitHub checks can validate offline code only, not actual Sims gameplay, cross-host generalization or local MoonWake walker operation. **P07/P124:** recover the conflicted historical #226 onto a fresh main baseline, keep all changes in an isolated PR, and integrate an audit of manual community submissions with the current judgment-learning owner. No automatic telemetry, promotion, privilege escalation or effect authority. Main/CI status must be established from provider after review.

## 2026-11-14 — Post-merge Super Fertilizer closer edge guards

**P83 independent review of #242:** Two CodeAnt issues remained after green merge: unhashable external hover source in `fertilizer_hover_recognition` can cause uncaught `TypeError`, and pending pickup can freeze a valid single-plant action despite positive personal pocket fertilizer. Other CodeAnt/Codex findings about dropped `available` were corrected before #242 merged and proven by CI. **P03:** two-owner source repair with falsifiers for JSON-shaped input and pending-stock parallel state; **P141:** reject global input catcher or new queue controller, preserve one existing action owner; **P124:** type checks at source boundaries and explicit pending transfer semantics; **P04:** no local agents/EA game tested from GitHub provider, native issue #171 still owns test with user-authorized disposable save and rollback. BI-002 independent. No source-only checks equal game outcome. See `docs/ECO_RESOURCE_CYCLE.md`.

## 2026-11-14 — Control-use correction: paused listener identity and complete semantic evidence backlog

**Parent:** Allow last-resort agent control after native/repository options are exhausted; capture **every** adopted atomic action and discovery, yield effects without exiting computer use when the user becomes active, then resume from the existing trusted idle listener with fresh scene/target/queue evidence. **Observed repo defect:** `CooperativeScreenQueue` could return `COMPLETED` for a passive observation; `AgentControlRunner.pulse` could misattribute it to a still-pending gameplay effect. **Correction:** source-tag every passive result and isolate listener state from gameplay QUEUE_STATUS and OUTCOME, expose approved passive observation during a user pause, add tokenized `DISCOVERY` events, bounded per-action journal evidence and paged code/test work items. **P141:** preserve native-first/control-handoff/host-listener owners, reject new daemon/recorder. **P95/P82:** program the source identity and negative regression fixtures. **P08:** local installed game not available in this provider context. **P07/P124:** small isolated feature branch and change classification; CI/main/live states verified independently before claiming. Repo completion claims remain weaker than actual provider/mainline readback; `source_verification_pending_total` makes this explicit. See `docs/CONTROL_DISCOVERY.md`.

## 2026-11-14 — MoonWake Closers: actual Super Fertilizer hover screenshot closes identity hypothesis

**Operator evidence (new):** Screenshot of paused backyard shows an actual highlighted ground object identified by its tooltip: **Super Fertilizer**, special fertilizer from Jasmine/Growfruit Challenge, displayed §80. Prior #239 assumed `FERTILIZER_BAG` must be the literal category and failed to encode highlighted-tooltip associations. This image proves the on-screen name/class candidate, not an installed-patch game object ID, route, inventory effect, item eligibility or a live sensor pipeline. Raw screenshot not committed publicly; sanitized facts only in `contracts/fixtures/BI-SUPER-FERTILIZER-HOVER-20261114.v1.json`. **P83:** independently audited merged #239 and subsequent review comments: one Codex partial-stock deadlock plus two CodeAnt blockers (optional scan taking precedence over sufficient pocket, pending transfer hiding valid plant action) and a false same-capture readback test. **P03:** source and regression repairs in canonical fertilizer workflow; added a bounded semantic tooltip recognition owner, no global OCR/desktop daemon. **P141:** prefer item-specific anchored hover evidence + current-game independent eligibility/transfer proof; reject another buying loop, screenshot-only world pose or automatic clicker. **P124:** recognition owner separate from existing stock/transfer/plants owner; legacy FERTILIZER_BAG and EA/multiview still supported, player/needs unchanged. **P04:** route native exact-patch object/drag and disposable A/B proof to existing issue #171; no verified autonomous agent dispatch or local MoonWake walker here. `P08` cannot be certified by GitHub CI. BI-002 remains separate. See `docs/ECO_RESOURCE_CYCLE.md`.

## 2026-11-14 — Operator correction: agent control is a last-resort discovery path, not forbidden

Operator explicitly wants agents to take control when existing deterministic/native logic is inadequate. Preserve the active computer-use session during player activity but **pause behavior** at the next cooperative checkpoint; keep the already-activated read-only host listener and pending work intact. Resume after verified trusted idle with independent scene/save/queue/target checks. **Every admitted atomic agent action** creates a compact semantic journal PREPARE → QUEUE_STATUS → independently observed OUTCOME → reviewed repository module/test CODIFICATION_RECEIPT. Do not call a click an implemented native mechanic; verify commits, CI, default branch and live Sims separately. Added source owners `betterinstincts/control_discovery.py`, `betterinstincts/agent_control_runner.py` and opt-in `host_listener` journal port. See `docs/CONTROL_DISCOVERY.md` and `contracts/control-discovery.v1.json`. Browser/Win32 raw capture, OS repair, player queue override, uncontrolled daemons and silent replay remain prohibited. Existing idle listener and CooperativeScreenQueue are reused, not replaced. BI-002 is still active.

## 2026-11-14 — Sixth Gear: bounded agent context, cross-chat handoffs and retrieval fault layers

**Parent:** Agents should behave cohesively across chat/model context windows by recovering the same authoritative operator objective, corrections, rejected paths, household goal and next gate, not by relying on chat text or expanding prompt size. **P141 discrimination:** reject universal memory/prompt bloat, new all-controlling game brain, and mandatory graph search; select a source-owned, evidence-ranked context envelope and conditional read-only retrieval routing. **P95:** separate data integrity, retrieval choice and final judgment; pin source revisions and scope, deny conflicting/expired records and carry revisions/corrections across handoffs. **P82:** replay, bounded context, conflicting links, missing data, skipped retrieval and player-first no-effect tests. **P08:** installed exact-build Sims and native runtime are not available through GitHub; game certification remains **BLOCKED_LOCAL_GAME_ACCESS**. **P07/P124:** optional `agent_context` sidecar in existing `host_stack` with tests, contract and source governance, no rival scheduler or permission escalation. GitHub commit/CI/PR/merge states require independent checks; a source packet is not agent installation, persistent model memory, tool execution or playable mod proof. BI-002 remains active. See `docs/AGENT_CONTEXT.md` and `contracts/agent-context.v1.json`.

## 2026-11-14 — Sixth Gear: purchased fertilizer bags already scattered around backyard

**Actual parent:** Operator already purchased the fertilizer and placed bags around the backyard. Existing `fertilizer_workflow.py` knew how to propose transfer of a `GROUND` supply when a matching action was externally supplied, but could not identify which purchased bags were actually eligible, owned/on-lot/reachable and unreserved, nor prevent duplicate pending pickup across a readback gap. **P141** compared repurchase loop (rejected: contradicts known stock), global vision/click worker (rejected: redundant unsafe host), blind bag-label assumption (rejected: pack/mod-dependent semantics), and opt-in provenance-gated bag survey integrated with existing gardening transfer owner (selected). **P95:** current object survey → exact Sim/lot/route → one observed transfer → readback → existing planter menu → independent outcome. **P82:** direct positive and falsifiers for multiple bags, route choice, wrong lot/Sim, stale capture, duplicate/pending transfer, no menu, protected stock, selected planter, player and needs. **P08:** GitHub provider cannot access installed Windows Sims 4 patch, native item transfer API, live UI/sensors or user's current save; game installation / effect remains BLOCKED_LOCAL_GAME_ACCESS, not a source pass. **P07/P124:** additive `backyard_scan` path extends existing `fertilizer_workflow.py` without replacing legacy GROUND supply or source planner, with contract, tests and clear native successor issue #171. No `prompt_group_walk.py` local execution or agent dispatch claimed. Check CI and provider main merge independently. BI-002 hunger remains active. See `docs/ECO_RESOURCE_CYCLE.md`.

## 2026-11-14 — MoonWake /the-closers: PR #237 ecology evidence repair

**Original parent:** fertilizer supply and planter actions, source-ranked recycling of safe objects, and exact Green Technician Eco-Upgrade Part fabrication without repeated human micromanagement. **P83 independent readback:** #237 merged to main at `def2b5e3a2cae88d59b72a4fac64e227daf9fccf`; later CodeAnt review identified five real gaps despite green CI. Codex review failure indicated usage limit, **not** an independently observed code defect; CodeRabbit did not provide completed review findings after close. **P03 first-sprint:** repair in `eco_resource_cycle.py`, `fertilizer_workflow.py` with focused adversarial regression fixtures. **P141:** reject replacing owners/clicker and extra parallel engines; select validation, identity and idempotence repairs on existing source-level seam. **P124:** keep source and actor ownership within two current modules, no generic new manager; preserve garden/teen homework/Work Hard and player-first priorities. **P04:** native EA gameplay and real resource/career outcome require actual Windows Sims host, exact build, local sources and disposable A/B under issue #171; cannot claim agent dispatch or live gameplay from GitHub. Closer proof remains CI/provider merge vs local game independently. See `docs/ECO_RESOURCE_CYCLE.md`.

## 2026-11-14 — MoonWake Sixth Gear: recycler, fertilizer sourcing and Green Technician fabrication

**Parent correction:** Operator still manually sources fertilizer and eco inputs, chooses recycle objects, acquires Fabricator, chooses Eco-Upgrade Part recipe and follows career progress. Earlier one-step gardening/fertilization, teen homework, Work Hard, NanoCan and mechanics registry source code did not form a complete observed resource-to-craft chain. **P141:** reject new UI click daemon, universal game scheduler or static craft advice; select narrow optional material-cycle policy through existing gardening, career and host owners. **P95:** observed ingredient deficit → safe source choice → recycled Bits/Pieces → exact unlocked career recipe → crafting, with bounded receipts, protected inventory and immutable goal. **P82:** adversarial source cost, player control, task and item ownership, verified yield/replay, recipe unlock, host integration tests. **P08:** local game/EA-native interaction and real outcome proof not available in GitHub provider; issue #171 remains the real local game gate. **P07/P124:** feature branch adds policy modules/tests, opt-in gardening and career/host composition, contracts, 42-item mechanics source coverage and documentation. Source and provider CI/PR/merge are separate truth; never claim playable automation. BI-002 hunger remains active. See `docs/ECO_RESOURCE_CYCLE.md`.

## 2026-11-14 — Sixth Gear: Servo social triple-down and dual-sensor rate diagnosis

**Parent evidence:** operator's paused Sims 4 screenshot shows a Servo, Fine, with green Fun, green Social but THREE red downward chevrons, green Durability and yellow Charge. This is an observed ordinal drop indicator, **not** a measured numeric 3× loss or active decay while paused. Existing `occult_needs` already owns the four Servo motives; existing `moodlets` already routes supplied emotion labels but no rate monitoring was wired. P141 rejected six-human-need delta-only, pure uncalibrated CV, unavailable native runtime-only, and background daemon; selected bounded independent EA_NATIVE + HUD_CV semantic fusion. P95 implemented profile-specific extraction, signed native rate only with provenance, categorical HUD decay, exact-Sim/build/capture/probe health, healthy fallback, two-distinct-post-reset re-admission, source conflicts, and existing moodlet decision evaluation. P82 tests paused high decline despite Fine/Happy, source outages/conflicts/replay, profiles, human control and no game effects. An optional human-six host_stack sidecar preserves ordinary call stacks; Servo four must use `evaluate_need_signals` directly pending real native adapter. Local P08 installed game, EA callback and calibrated CV actor are **NOT_RUN**; GitHub policy/CI is not gameplay certification. BI-002 hunger stays active, PR #159 independent. See `docs/NEED_SIGNAL_FUSION.md`.

## 2026-11-14 — MoonWake Sixth Gear: promotion-aware Work Hard followed by household handoff

**Parent:** Convert obvious recurring Sims host judgments into deterministic, reusable BetterInstincts logic. When a Sim enters a verified rabbit-hole job, determine whether Work Hard meaningfully advances independently observed promotion readiness, protect wellbeing and player-set tones, obtain separate in-game native effect proof, then move attention to the next awake household Sim and reobserve their six needs. **Recovered floor:** merged main @c944a5a0b3058f1884b323affbc96f396b8f973f already has sleep/recharge/away portrait rotation and 38 mechanics; existing career_service focuses on teen homework and must remain intact. **P141:** Reject universal Work Hard (overwork/player conflict), repeating desktop clicks (native-first violation), and a rival job scheduler (ownership drift); select thin policy port inside career_service + household_economy + host_stack. **P95:** Require same-capture selected shift and no guessed promotion thresholds; only MET requirements, COMPLETE/NOT_REQUIRED daily task, BELOW_TARGET performance, observed option, neutral unowned tone and existing wellbeing reserve propose Work Hard. **P82:** Falsify with unmet/unknown promotion, other tone, critical needs, stale shift, active career, unsupported option, player priority, and test real next-awake handoff with no chores. **P08:** Real current Windows Sims and EA-native work tone/portrait action unverified in GitHub provider; explicit BLOCKED_LOCAL_GAME_ACCESS with issue #171 and BI-002 active. **P07/P124:** Source-only policy, host gate, registry, native route, contracts, regression tests, independent provider CI and authorized mainline integration are separate statuses. Neither an offline result nor merge proves a playable mod. See docs/CAREER_PERFORMANCE.md, docs/HOUSEHOLD_ECONOMY.md and contracts/career-service.v1.json#work_shift_tone.

## 2026-11-13 — MoonWake Sixth Gear: mechanics coverage and sustainable multi-Sim work

**Parent objective:** track missing Sims mechanics holistically so plans actually evolve; never turn one Sim into an exhausted laborer. One Sim prioritizes six needs, fun, relationships and temperament even above discretionary income; an observed multi-Sim household may distribute care, chores, skill-aligned production and finances to improve overall yield without sacrificing personal welfare. **Recovery:** existing need_load_balance/domain_cascade/household_upkeep/gardening/career, single-actor queue protections, stable opaque household scope. Their coverage was dispersed with no canonical gap ledger. **P141 alternatives:** reject static list alone, universal scheduler and unconditional profit-first policy; select source-verified mechanics registry + opt-in cooperative allocator. **P95 design:** source state, explicit uncovered gaps, cycle-free dependencies and outcome-driven replan; per-member emotional and needs floor, queue/skill/preference/resource/fairness constraints. **P82:** separate source-only solo versus cooperative/roster/collision/failed-task tests, never invent game-effect metrics. **P08:** actual Sims, EA tuning/hook, multi-character productivity, mood and yield remain BLOCKED_LOCAL_GAME_ACCESS through GitHub. **P07/P124:** add source-owned registry/allocator and optional ports to existing host_stack/host_listener, contracts/tests/CLI and ledger/roadmap; require actual PR CI/readback for source proof. **Independence:** full MoonWake local walker/agents not launched via GitHub. No native effect, account, Windows, save or gameplay mutation; BI-002 hunger still ACTIVE. See docs/HOUSEHOLD_ECONOMY.md.

## 2026-11-13 — Sixth Gear: school homework seam + named chat whims

**Operator parent:** embrace the observed ability to finish homework immediately before/during the class transition when the actual game permits it, without sacrificing class; convert a targeted Chat with [Sim] whim into an actual on-lot or R Relationships route rather than leaving the wish absent from the action queue. **Repo floor:** school and teen homework were blanket premises-blocked, social_opportunity was only invite-modal, whim_pinning only pins; no native game effect proven. **P141:** compare blanket denial, unconditional timed cheat, blind UI clicker and verified affordance + existing owner integration; choose verified observation with exact target, no new input authority. **P95/P82:** bounded evidence-qualified policy, queue budget/dedup and negative tests. **P08:** no local Windows Sims 4 game captured by GitHub provider; requires exact-build actual homework and R chat evidence, no invented certification. **P07/P124:** implement through existing host_stack/listener and legacy school/teen/social owners, add read-only local CLI, machine contract and tests; check CI/PR/merge independently. Preserves player queue, attendance, save safety, native-gameplay sovereignty and BI-002 hunger ACTIVE. See `docs/OPPORTUNISTIC_ACTIONS.md` and `contracts/opportunistic-actions.v1.json`.

## 2026-11-13 — MoonWake Sixth Gear: need-aware action queue supervision and activity timing

**Parent:** Prevent oversized, duplicate and contradictory Sims Live Mode autonomous queues; account for actual activity duration and proven moodlet/temperament/balance/trait effects; interrupt autonomous tasks when observed or forecast critical needs warrant, without oscillation or overriding the player. MoonWake current canonical Sixth Gear order: **P141 → P95 → P82 → P08 → P07 → P124**. Selected P141 thesis is an evidence-qualified one-Sim-at-a-time advisor in the existing all-household native policy: fixed global caps, blind timeout cancellations and mouse-based clickers are rejected. Source consultation `contracts/consultations/BI-QUEUE-SUPERVISION-SIXTH-GEAR-20261113.v1.json` was committed before code. P95/P82: source-bound semantic identity and mutually exclusive outcomes, four bounded duration multipliers and independently attested same-build completion samples, existing conservative capacity bands, six-needs active-clock forecast, verified switch-history cooldown and one proposed cancel at a time. P08 actual EA hook/Windows/Live Mode is **BLOCKED_LOCAL_GAME_ACCESS**, not simulated or passed by CI. P07/P124: optional bounded queue-supervision port under `betterinstincts/autonomy_moderation.py`, one owner of cancellation candidates and `betterinstincts/queue_capacity.py` reused. Original queue behavior preserved without the optional snapshot; no daemon, save effect, peripheral change or autoplay. Real EA-native input, empirical causality and actual cancellation remain issue #171; BI-002 hunger is independently ACTIVE. `docs/QUEUE_SUPERVISION.md` is the exact seam and test reference. Full `prompt_group_walk.py` and separate host agent dispatch are NOT_RUN from the connected GitHub provider; do not infer them from contract/source text. Commit/PR/CI/merge/live evidence must be independently verified.

## 2026-11-13 — MoonWake Closers: NanoCan queue provenance and player-target safety

P83 independently verified #216 merged but found three connected offline policy holes: unresolved player/unknown queue target not reserved, native cleanup queue matching did not compare patch/source/destination/phase/revision, and bare legacy sink hints could look like suppression candidates. P03 implemented source-only fail-closed guard after version-pinned ontology consultation. P141 rejected broad SLAM or general native-autonomy rewrites as the wrong ownership and declined an unproven installed EA script. P124 retains one `nanocan_recycling` policy owner, treats `sink_suppression_candidate` as a strict alias of a complete native source/lot/queue-qualified redirect, and adds focused negative/positive tests. P04 keeps exact-build native event/queue integration under issue #171 (local Windows Sims, player-consented disposable save) rather than replacing the P08 owner or fabricating a dispatch. **No live-game queue cancellation, no local MoonWake walker/agent launch, no in-game income proof.** BI-002 remains active.

## 2026-11-13 — MoonWake /the-closers: VAE profile-isolation correction

P83 independently read merged PR #221 and confirmed source/mainline/CI, then discovered **cross-installation-profile learned-model aliasing**: VAE filenames used the Sims world hash while profile opt-in could differ. P03 corrected named-profile storage and CLI selection using the current `semantic_vae` and `installation_profiles` owners; old `default` checkpoint paths remain unchanged. P141 compared overlapping alternatives and selected explicit profile-keyed checkpoints over a separate data store, auto-migration, or new sensor. P124 kept one storage/consent authority with focused tests rather than a parallel framework. P04 distinguishes remote merged source from unavailable native Sims/Windows runner and does not claim actual local agent dispatch. Real-gamedata model quality, P08, and BI-002 remain unproven. See `docs/SEMANTIC_VAE.md` and `contracts/consultations/BI-LOCAL-SEMANTIC-VAE-CLOSERS-20261113.v1.json`.

## 2026-11-13 — MoonWake /sixth-gear local semantic VAE

**Parent objective:** Let each opted-in BetterInstincts installation improve locally from its own user gameplay, including probabilistic spatial representation using a variational encoder/decoder; do not confuse physical Sim traversal with camera movement or make hallucinated geometry authoritative. **P141 choice:** local semantic-patch VAE using the existing verified convolution intake; reject central telemetry and inferred-route actuation, defer raw-video VAE until real game sensor calibration. **P95 → P82 → P08 → P07 → P124:** one encoder/decoder call stack, a bounded and replay-safe evidence store, opt-in/disable/status/purge CLI and regression tests; P08 local real-game testing is unavailable through GitHub. No claimed launched MoonWake walker/independent agent pool, no live trained Sims model, no telemetry or server. The canonical design, proof ceiling and P82 falsifiers are in `docs/SEMANTIC_VAE.md`; native gameplay route is `contracts/native-gameplay-decisions/BI-LOCAL-SEMANTIC-VAE-20261113.v1.json`. Reconcile PR/CI/merge and true local runtime separately. BI-002 remains ACTIVE.

## 2026-11-13 — MoonWake Closers follow-up: manual first-run launch reliability

P83 independently verified #218 source/CI/main but found two practical omissions: the GUI and explicit CLI bypassed `scripts/smart_start.auto_start` duplicate-process validation, and the GUI treated the 32/64-bit executables in one Game/Bin as ambiguous. P03 implemented a bounded source repair after consultation `BI-FIRST-RUN-MANUAL-CLOSERS-20261113`: a shared verified selector, manual launch through existing process admission, tests for already-running, invalid selection, consent and save preservation. P141 compared direct native CAS automation (DEFER local EA evidence), a new launcher (REJECT unnecessary duplicate), and reuse of existing first-run owners (SELECT). P124 preserves one admission and one installation-selection owner with a simple test seam. P04 still requires actual local Windows P08 and game-native character creation; no independent host agent/walker dispatch is claimed by GitHub provider work. The original BI-002 hunger gate and issue #201 latest-save objective remain separate.

## 2026-11-12 — P141 / Fifth Gear: new-Sim skill-aware first session

P141 strategic comparison: a bounded, player-first skill and productivity advisor survives; blind CAS click automation is deferred to local Windows/scene certification; automatic maximum-skill manipulation is rejected as unauthorized game behavior. Existing first_run owners are reused. The bounded implementation adds goal/skill-context planning, six-needs and funds gates, explicit preference precedence and negative tests. Moonwake ordered composition is P95 → P82 → P08 → P07 → P124, but real local P08 and the Moonwake walker remain NOT_RUN through the GitHub connector. No offline work certifies CAS, a running mod, BI-002 hunger or user save manipulation. Branch, CI, PR and main are independent proof dimensions.

## 2026-11-12 — P141 → Fifth Gear: NanoCan sink/dishwasher/trash/vanilla queue redirection

**Parent outcome:** Across all household Sims, prefer a verified in-lot NanoCan for dirty empty dishes and genuinely disposable waste; selectively replace competing autonomously generated sink, dishwasher or conventional-bin actions, without deleting player commands, swallowing whims, fabricating money or stealing desktop focus. P141 selected bounded source- and spatial-proven native queue redirection rather than blanket cancellation, speculative dense SLAM or an unverified package. Consultation was committed before product code (`BI-NANOCAN-QUEUE-REDIRECTION-20261112`). P95/P82 extend `nanocan_recycling`, keep `autonomy_moderation` as all-Sims port, and falsify unsafe queue slot/origin/target/path cases. P08 cannot be certified from the GitHub provider; exact installed EA tuning, native action IDs, reward and runtime A/B require authorized local disposable Sims. P07/P124 source/contracts/tests/CI integration must be verified against the current branch and actual main SHA before asserting landing. Live game queue cancellation, native mod installation and measured payouts are **not observed**. BI-002 hunger remains the independent active parent## 2026-11-12 — P141 → Fifth Gear: trainable spatial convolution advisory

P141 selected a bounded, real 3×3 convolutional spatial learner over verified floor patches instead of broad RL, fixed hand-coded edge detectors, or takeover of independent visual sensor PR #159. The consultation `contracts/consultations/BI-SPATIAL-CONVOLUTION-P141-FIFTH-GEAR-20261112.v1.json` was committed before product changes on the isolated branch. P95/P82: source-checked 5×5×3 patches, two trainable convolution filters, ReLU/mean pooling and logistic head; replay-safe one-step SGD with 1/5 disjoint prequential holdout and a better-than-constant Brier threshold. P07/P124: optional non-actuating receipt in existing navigation; existing Dijkstra, camera, human, save and graph gates retain authority. P08 Windows Sims game/sensor certification is NOT_RUN in GitHub connector; offline CI and main merge are separately checked. BI-002 hunger is not closed. See `docs/SPATIAL_CONVOLUTION.md`.

## 2026-11-12 — MoonWake Closers: single-click launcher structural verification

**Verified floor:** #200 merged on `main` at `17aaffb05763cf40e7cd8cb6ef7a1682dc06dde5` with successful GitHub offline CI. No Windows Sims launch, real save, game patch or menu capture was independently verified. P83 found two reproducible defects: dual recognized exes in the same Game/Bin erroneously produced MULTIPLE installs; a malformed tasklist result or untrusted later process snapshot could appear empty and admit new launch or overclaim a game PID.

**P03/P141:** A bounded closer consultation (P141 rejects speculative automatic Resume and timestamps, selects same-root dedup + process evidence hardening) was committed first. **P124:** reuse `scripts/smart_start.py`, with tests in `tests/test_smart_start.py` and source contract `contracts/launch-journey.v1.json`; keep known chooser, user save policy, native game mechanics and BI-002 untouched. **P04:** Issue #201 owns real Windows Sims menu/last-played identity + Live Mode local certification; no autonomously launched local agent is claimed. Exact branch CI/merge evidence is a separate gate before claiming integration.

**Remaining true boundaries:** Unattended save selection and native gameplay are not implemented. An existing process name is not a verified executable path. Near-simultaneous independent double-click starts need a local Windows concurrency test/atomic single-instance design before a broad safety claim.

## 2026-11-12 — P141 → Fifth Gear: one-click Sims 4 launch reliability

**Parent:** First-time BetterInstincts user double-clicks a Windows launcher and wants the game and latest session without extra interaction. Current implemented portion: unique Sims installation dispatched with read-only process/PID evidence. Unknown/user saves are never silently selected; exact most-recent game save identity and calibrated menu controls remain unproven. Git and Python 3.11+ remain prerequisites; clean-main fast-forward and uninstall protections remain unchanged.

**P141:** Reject blind Resume and lab-only coordinate reuse; defer guessing newest save by file timestamp; select bounded single-install/single-process game dispatch. The machine consultation `contracts/consultations/BI-BOOT-RELIABILITY-P141-FIFTH-GEAR-20261112.v1.json` predates branch behavior mutations.

**P95/P82:** `scripts/smart_start.py` uses bounded read-only Windows process inventory, blocks duplicate/concurrent game launch, reuses `first_run` installation resolution, and distinguishes dispatch PID from independently observed Sims process name/PID. Synthetic tests exercise missing/ambiguous installations, inventory failures, active processes, Linux refusal, concurrency, and proof ceilings. No save or game files are read/edited.

**P08:** NOT_RUN: GitHub connector cannot observe local Windows Sims 4/EA/Steam/Epic executable, menus, Live Mode or player takeover. **P07/P124:** isolated source/contract/README/first-run/Windows entrypoint and tests, preserve manual chooser fallback, player authority, BI-002 and native EA mechanics. CI/main verification independent.

**Follow-on:** Actual Windows double-click + process/title/menu observation, then separate verified user-authorized last-played save identity and calibrated per-effect host gate. Do not market latest-save load as shipped.

## 2026-11-12 — MoonWake Closers: Semantic SLAM external active-world proof

P83 independently verified merged PR #197 at main `ece07ccfe21c4bd0322af71821cf04aaf312c2ab`, including prior green offline/peripheral CI. Actual defect: a stale stored map and old camera could agree but differ from the game lot or exact build. P03 selected and executed bounded provenance guard, committing ontology consultation before code; P141 rejected broad dense SLAM as premature and deferred independently owned PR #159; P124 reused the existing semantic map+room traversal owners, strengthened offline tests and prohibited class-unknown frame candidates; P04 separated cloud CI from local single-screen P08 certification and did not claim worker dispatch. No local game certification, scans, EA-file input or mouse automation. BI-002 hunger remains active. Closeout proof ceiling: source+CI+merge only; read back PR and main before declaring integrated.

## 2026-11-12 — BetterInstincts Semantic SLAM (P141 → P95 → P82 → P08 → P07 → P124)

**P141 selected:** A sparse, evidence-qualified 3D object/floor/elevation + local camera relocalization layer. Dense physical SLAM/VIO rejected without inertial/depth/host camera evidence; camera-bound 2D-only pick maps insufficient for stacked/wall-mounted/contained objects. Ontology consultation committed before code as `BI-SEMANTIC-SLAM-20261112`.

**Owned implementation:** `contracts/semantic-spatial-map.v1.json`, pure `betterinstincts/semantic_spatial_map.py`, read-only bridge in `room_map_traverse.py`, native-effect routing, tests and `docs/SEMANTIC_SPATIAL_MAP.md`. Camera pose solved from fresh noncoplanar landmarks using a residual-bounded local affine approximation; Y is actual world elevation, not screen vertical. No input, save edits, automatic capture, private image storage, or trained classifier claimed. PR #159 spatial perception/sensor remains independently owned/unmerged; no colliding edits.

**Proof and release distinction:** Offline synthetic evaluation is testable in GitHub CI; P08 *real game* calibration and object-class accuracy still need operator-authorized local Sims host. BI-002 hunger and the game-native authority guards are not altered. Never promote projected pixels to a control permit. PR CI, branch, merge state and main SHA must be verified independently before declaring repository landing.

## 2026-11-12 — Moonwake /the-closers: PR #194 household-funds review corrections

**Parent retained:** Generalized active household funds alteration across a known Windows Sims 4 runtime, independent of EA app / Steam / Epic install directory, with verified fallback routes, player-first authority and no unsupported platform promises. PR #194 was merged at `b6ce1719c98119fee2e9d877a1a05c42c3e5f1db` after green offline CI, but its closed-PR review threads still exposed material execution gaps. Consultation `contracts/consultations/BI-HOUSEHOLD-FUNDS-CLOSERS-20261112.v1.json` was committed before closer source modifications.

**P83 review dispositions:** (1) Unsafe recovery Ctrl+Shift+C toggle: fixed by requiring `operator-ready --console-ready` for recovery, with no focus borrow and no automatic chord. (2) JSON key-order dependent additive choice: fixed by numeric maximum of fitting deltas, tested in reversed order. (3) Fabricated `dispatch:*` predecessor: actual local original `--execute` receipt with exact command, target, funds, PID, session and mode required before fallback input. (4) PID/process-name test that only grepped code: replaced with behavioral mocked host denials that dispatch zero keys. (5) Receipt write errors could conceal prior input: exclusive receipt reserved before effects; postwrite failure returns observed dispatch/unknown status and does not claim clean blocking. (6) Predecessor replay: atomic one-use claim before first recovery keystroke; uncertain results cannot replay. The obsolete consultation schema defect on #194 was already fixed before its merge, as its final CI run confirms.

**P03/P141/P124:** Existing `betterinstincts/funds_inject.py`, `scripts/funds_inject.py` and `contracts/host-funds.v1.json` remain sole code/contract owners. Contract advances to v5, no additional UI controller, daemon, game scans, Windows settings, save writes, protected slot reads, or invented native EA hooks. Runtime game compatibility is keyed by observed running PID and exact build rather than by launcher directory. Evidence strings alone do not imply gameplay effect.

**P04 bounded lanes:** Repo-only code/contract/tests/CI are the current ChatGPT+GitHub lane; operator-owned Windows Sims P08 disposable-save trial is a separate physical-runtime lane that cannot be certified remotely. No parallel launch is authorized to steal desktop focus or bypass player idle/scene gates. The parent BI-002 hunger native gameplay trial and BI-004 earned-income distinction remain unchanged.

**Proof ceiling and next gate:** Branch implementation and synthetic regression tests must pass fresh PR CI; only then is repository integration eligible. There is **no** live game/console-focus/HUD-delta or cross-storefront P08 proof here. Local runbook and acceptance: `docs/HOUSEHOLD_FUNDS_RECOVERY.md`. If the durable recovery claim exists but the effect is uncertain, do not delete or retry it; operator must observe the actual balance and start a new explicitly authorized transaction.


## 2026-11-12 — Fifth Gear: active-household funds verified fallback / storefront-neutral host

**Parent objective:** Make a generalized active Sims 4 household funds boost reliable when one cheat-console command fails, across Windows EA app, Steam, Epic and custom installation directories. Do not mistake a different launcher for a separate cheat engine or claim version-independent game certification. Consultation committed first: `contracts/consultations/BI-HOUSEHOLD-FUNDS-FALLBACK-20261112.v1.json`; code decision: `contracts/native-gameplay-decisions/BI-HOUSEHOLD-FUNDS-FALLBACK-20261112.v1.json`.

**P95:** Retain the canonical exact-funds planner and existing screen lease. **P82:** An observed no-op plus a unique prior dispatch reference and distinct HUD reference admits at most one EA-documented, non-overshooting additive command; deny pending effect, changed balances and less-than-§1,000 gaps. **P08:** Physical Windows/Sims HUD, input-focus and cross-storefront/patch trials remain OPEN, without a claim of local proof. **P07:** Existing CLI now supports explicit `recover` and an operator-armed console route; exact executable basename/PID and foreground are checked without hardcoded install paths. **P124:** No duplicate input controller, hidden scanner, uncontrolled motherlode loop or save manipulation.

**Proof:** Offline regressions own the route/evidence/overshoot/identity checks; remote CI cannot certify actual funds changed. A partial additive increase is not exact-target attainment or BI-004 earned income. Operator/local runbook: `docs/HOUSEHOLD_FUNDS_RECOVERY.md`. The parent BI-002 hunger gameplay gate and immutable version profiles remain unchanged.


## 2026-11-12 — The Closers: BI-002 capture-ID provenance validation

**P83 verification:** Merged PR #191 (`11e21e4533e49c4481e23db64d3db44fe9c9ad4f`) and successful workflow #43133524922 establish the exact-text replay guard on main, but source review found `validate_trial` still admitted `"   "`, padded and hidden-control `observation_ref` values. Different spellings could inflate independent evidence counts. **P03 execution:** an isolated consultation-first branch hardens the existing `live_eval.validate_trial`, adds pre-append and persisted-read regressions, and documents the scope; no second evaluator or Sims input controller. **P141:** selected this proven recurrence gap over speculative native EA calls or an autonomy rewrite. **P124:** preserve the one evidence owner and repair the previously displaced 2026-11-10 funds heading without changing its content. **P04:** current ChatGPT GitHub provider can validate and integrate offline; real local game P08 remains with the authorized Windows host, including 5 vanilla + 5 modified trials and rollback. This change does not grant gameplay certification.

## 2026-11-11 — P141 → Fifth Gear: BI-002 trial observation replay guard

**Parent:** BI-002 hunger native-gameplay first win remains ACTIVE; prior offline receipts cannot certify Sims gameplay. P141 tested four strategic theses and selected the narrow evidence-integrity gap rather than a new orchestration engine, competing spatial branch or guessed native EA hooks. Pre-mutation consultation: `contracts/consultations/BI-002-OBSERVATION-REPLAY-P141-FIFTH-GEAR-20261111.v1.json`.

**P95:** retain `betterinstincts/live_eval.py` as deterministic trial evidence owner and `scripts/live_cert.py` as local run intake; both reuse one uniqueness rule, with no Sims-side effect. **P82:** characterize duplicated observation references across different stages/trials, a failed pre-append case and persisted receipt tampering; preserve unique 5 baseline/5 modified/1 rollback fixtures. **P08:** local game proof is separately blocked in the GitHub provider runtime; never promote record validation to gameplay. **P07:** scoped source/tests/doc changes on an isolated branch with native `NON_GAMEPLAY` decision. **P124:** one canonical helper, no duplicate pipeline or broadened runtime dependencies.

**Correction:** a reused capture ID now fails with `DUPLICATE_OBSERVATION_REF` before the CLI writes and when already stored evidence is read/evaluated. Reference-identity validation cannot establish the underlying media is genuine or independent; actual game patch, mod hash, 5+5 measured trials, rollback, player queue and maintainer review remain open. Track tests/PR/merge from provider receipts; no local Sims or desktop input operations occurred.

## 2026-11-10 — Fifth Gear exact active-household funds injection (P95 → P82 → P08 → P07 → P124)

**Parent:** Replace disorganized agents clicking around for money cheats with one generalized Sims 4 active-household operation independent of portrait, Sim identity, save labels or lot. Reuse the established host-funds and human-first screen lease; do not create a second UI controller. **Authoritative EA source:** https://www.ea.com/games/the-sims/the-sims-4/faq/cheats (Ctrl+Shift+C, testingcheats true, money N sets exact household total). **Consultation:** `contracts/consultations/BI-HOUSEHOLD-FUNDS-EXACT-20261110.v1.json`, committed before behavior changes.

**P95 call stack:** operator target balance + observed current HUD balance → reject unknown or already-at/above target → retain Live/Build/Buy scene and screen ownership → Ctrl+Shift+C → testingcheats true → money N once → observe HUD → evidence-attested evaluation. The command is a target TOTAL, not an additive delta. Do not force F1 or select a Sim portrait.

**P82 falsifiers:** negative/unknown/NaN/out-of-range balances; richer households never lose wealth; single exact command; no unverified automatic motherlode/loop; human override; tampered command queue; local HUD proof required; no fixed console-coordinate click, duplicate testingcheats command or unbalanced modifier chord. `tests/test_funds_inject.py` owns these offline tests.

**P08 boundary:** GitHub/CI has no physical Windows/Sims host. Local operator P08 must verify console activation and text focus, current Sims build, observed household balance, exact post-command HUD amount, player-takeover behavior, and rollback on a disposable save under `admitted_screen_lease`. Input dispatch and externally supplied HUD attestation are not independent game proof. Do not automatically repeat commands on unproven effects.

**P07/P124 convergence:** Keep `betterinstincts/funds_inject.py` as the pure contract owner, `scripts/funds_inject.py` as the explicit opt-in host adapter and `contracts/host-funds.v1.json` as the machine-readable policy. The separate BI-004 earned-income horizon and BI-002 hunger live gate remain distinct. Execute focused tests, semantic preflight, PR CI and main integration before claiming merge. No Windows settings, peripherals, protected saves or EA files touched.

**NEXT:** local P08 disposable-game verification of console focus and exact HUD balance with a receipt; only then consider a calibrated in-game/HUD sensor and opt-in retry logic. Manual HUD recheck, not blind motherlode, is the failure path.

## 2026-11-10 — Moonwake P04 canonical Escape/U physical-input forensics workload

**Parent:** The Sims 4 Esc still cancels actions but not the expected Options menu, and U remains insufficiently observed. **Verified source floor:** PR #183 merged at `03b8cc488fc856daf35cd6babadf12cd36fe93ad` with offline CI; physical input repair and Cursor-session attribution remain UNPROVEN. **P04 resolution:** Moonwake catalog `8c281379ba7ccc871947391233b1db72f4a108ef` — `[PARALLEL] Repo-Aware Sprint + Harness Factoring Distributor`, base source `848728632c1243ebba023fa0012292a2ad33cada`. Runtime partition: GitHub source proof CURRENT_CHAT_RUNTIME, offline CI CI_OR_REMOTE_RUNNER, operator physical keyboard OPERATOR_OR_PHYSICAL_RUNTIME, local read-only Cursor evidence LOCAL_AGENT_RUNTIME. Machine workload added to *existing* Horizon and dispatch owners; two independent evidence lanes then a serial convergence lane. No local worker adapter dispatched from provider GitHub; no second cursor owner. **Mandatory invariants:** keep BI-002 hunger ACTIVE_GAME_UNPROVEN, world sensor as current next-supporting priority, human input sovereign and Windows key/device preferences untouched. **Next:** `python -m scripts.horizon_status` in canonical checkout, then physical/manual Esc/Options/P/U differential plus local approved read-only Cursor hook/process evidence, followed by causal reconciliation and acceptance.

## 2026-11-10 — Escape/U selective-game-input forensic correction (host proof open)

**Observed operator symptom:** physical Escape functions outside Sims and cancels some in-game operations but does not open the expected Options/pause menu; U also reported affected. **Provider audit:** main PRs #97/#98/#104/#110/#147/#160/#161/#162/#175/#177/#180; no Cursor tool/session provenance establishing an OS remap. EA documents P/0/backtick direct pause separately from Escape cancellation. The inherited `PAUSE_MENU` label was misleading and existing `send_key_chord` lacked exception-safe release of synthetic pressed keys. This branch retains the historical hotkey id but makes its semantics explicit, protects pack-gated U/Clubs, adds fail-closed contract tests, balances keyboard injection on interrupted calls and records a host-only manual differential matrix in `docs/PERIPHERAL_INCIDENT.md`.

**Proof:** GitHub source commits/readback and CI only; NOT Windows host activation, an installed Cursor hook, physical Escape/U repair, confirmed mod fault or live Sims certification. **Next:** observe manual Esc-cancel vs Esc-Options vs P/0 pause vs three-dots Options in foreground Live with a known overlay state, compare U only when Clubs entitlement is present, correlate sanitized Cursor process/action timeline, and resolve only the proven cause. No host settings, protected saves or Windows services changed.

## 2026-11-10 — Moonwake Closers object-action review integrity (P83 → P03 → P141 → P124 → P04)

**Parent:** Independently verify the previously merged PR #179 at current main and close replay/evidence holes before promoting object-menu utility knowledge. Initial verified mainline at audit: `a1ef40c4a7b4993fa077be12603feebc90525795` (household-navigation PR #181 already merged). PR #180 legacy-input enforcement merged concurrently; #159 spatial-perception and #149 home-queue remain separately owned.

**P83/P03:** The first implementation's repeated reviewed outcome `evidence_ref` was counted multiple times across interactions/sessions, old or contradictory event-sequence replays were treated as successes, and beneficial domain judgments ignored other-domain harmful reviews. Static confidence could therefore be inflated despite green CI. There was also literal escaped backtick markup in four added documentation sections. No Windows/Sims live host was attached to this provider execution.

**P141:** Selected the narrowly testable review-integrity repair over invasive global click monitoring or a competing queue scheduler; existing human-first and listener/affordance owners remain canonical.

**P124:** One catalog reducer retains event validation, replay-unique evidence aggregation, legacy read compatibility and conservative queue advisory; no new screen-input owner. A bounded record cap explicitly abstains rather than forgetting or overclaiming reviews. The existing listener still owns explicit activation and passive opportunity survey.

**P04:** Machine-readable dependency handoff: `plans/active/BI-OBJECT-ACTION-CLOSERS-P04-20261110.v1.json`. The game-calibrated semantic menu sensor and P08 disposable live queue certification require the local operator game runtime. The current parent BI-002 hunger A/B/rollback remains active; do not reframe local sensor work as BI-002 completion.

**Proof ledger:** GitHub provider PR checks/merge and mainline readback will be reported separately from actual Sims event capture or input authority. This note is not a CI pass or merge claim by itself.

## 2026-11-10 — Moonwake closers P83 → P03 → P141 → P124 → P04: live-input coverage repair

**Parent:** gamer/operator computer control is sovereign during active use,
including mouse, keyboard, dictation and other applications; no autonomous
Bluetooth/driver/Print Screen/Escape/U remapping or save mutation. Previous
validated baseline: merged PRs #175, #176, #177; ontology revision 6; main
`dc062e008c60de9f8898228e0c1a92168214b0f3`.

**P83 factual discrepancy:** the P01 harness classified six CAS, school
and host-menu raw inputs as `UNADOPTED_LEGACY_NO_LIVE_AUTHORITY`, but
`scripts/host_menu.py#run_journey` and
`scripts/school_attend_click.py#run_plan` could still reach direct clicks
through executable paths. A manifest entry was not a runtime denial.

**P03 bounded remedy:** `betterinstincts/legacy_screen_boundary.py`
denies all six listed unadopted executors before any first screen effect.
Read-only planners stay available. P01's harness now checks the denial
entrypoint using source AST rather than trusting an advisory string;
its discovery scans both application and scripts roots. Negative regression
tests simulate direct CLI/library invocation with no Win32 effects.
`--operator-screen-released` alone never admits input.

**P141 discriminating opportunity:** the next high-leverage *investigation*
is one exact-build legacy input flow under `admitted_screen_lease`
with real scene and player-takeover evidence; global OS input hooks are
unjustified and forbidden. P124 kept the safety owner single and separated
static classification, pure runtime deny and CLI planning (no refactor
of functioning desktop/game code unrelated to this defect). P04 owns
the bounded successor tasks and distinct local/remote proof ceilings
in `docs/handoff/BI-HUMAN-FIRST-CLOSERS-P04-2026-11-10.md`.

**Proof ceiling:** repository tests and GitHub CI, not local installed
Windows game, actual physical input preemption, Cursor activation,
independent external-agent interception or playable Sims-mod proof.
BI-002 hunger remains ACTIVE / `BLOCKED_LOCAL_GAME_ACCESS`.

## 2026-11-10 — fifth-gear object-action catalog (P95 → P82 → P08 → P07 → P124)

**Parent objective:** Portable machine-readable discovery of Sims object
menus, selected actions and their reviewed needs/money/skills/career effects,
so the host's opportunity survey can rank actions while preserving human
control in any household/save. Scoped consultation:
`contracts/consultations/BI-OBJECT-ACTION-CATALOG-20261110.v1.json`.
Provider baseline `dc062e008c60de9f8898228e0c1a92168214b0f3`;
existing PR #159 spatial perception and #149 home queue deliberately untouched.

**Implementation:** `betterinstincts/object_action_catalog.py`,
`contracts/object-action-catalog.v1.json`,
`host_listener.observe_object_action` and
`host_listener.suggest_object_action`, existing listener tick survey
`object_action_hint`, scoped CLI and deterministic negative replay/portability
tests. Reviewed usefulness requires at least three helpful outcome examples and
at least 75% helpful reviews in exact patch/class/action/domain; menu
appearance and selection alone are insufficient. Local catalog is atomic
and bounded, with no OS hooks, game input, save mutation or daemon.

**Evidence ceiling:** GitHub connector writes and CI/offline tests are not
local Sims game proof. P08 needs a calibrated game sensor, true player/host
events, independent scene/actor/capture gates and disposable live A/B before
real queue actuation could be certified. BI-002 hunger A/B + rollback stays
the parent product gate. See `docs/OBJECT_ACTION_CATALOG.md`.

## 2026-11-10 — P00/P01 holistic human-first doctrine, ontology and harness

**Parent objective:** consolidate the user control and background independence
work from merged PR #175 and #176 into one P00 authority model and a P01
machine-checked harness. P00 recasts effect admission and operator-owned OS
input capabilities in ontology revision 5, glossary, compact AGENTS and
doctrine without replacing original rules. P01 adds an explicit source/adoption
inventory, source-discovery test, CI validator, scoped skill, codebase map,
path registry link and proof-dimensional reporting.

**Critical limits:** raw Win32 helpers and legacy CAS/host-menu entrypoints
remain explicitly inventoried as unadopted or mixed until independently gated.
A static registry does not intercept independent agents, forbid an OS-admin
shell outside this repository, or certify a physical user takeover. No
Windows or Sims game mutation occurred in this provider-scoped work. Existing
CI/P08 and BI-002 hunger live game proof remain separate.

**Source provenance:** Moonwake current P00/P01 canonical base registry at
`src/tokencorridor/interface/promptkit/registry/base/prompts.json`;
pre-mutation consultation:
`contracts/consultations/BI-P00-P01-HUMAN-SOVEREIGNTY-GOVERNANCE-HARNESS-20261110.v1.json`.

## 2026-11-10 — P00/P01 governance and operational harness for world-object highlight learning

**Parent objective:** After PR #168/#169 implementation/Closers and PR #174 canonical supporting P08 Horizon routing, invoke Moonwake P00 then P01 to make world-target highlight-loss and replay-safe click learning **first-class, enforceable** BetterInstincts ontology, doctrine and harness behavior. No new clicker or fake local-agent launch. Current provider main at consultation: `db11b22c59a61777adf4dc2e553da3feac1a52c4`; overlapping open PR #159 spatial-perception and #149 needs/homework were left untouched. Moonwake P00 = Governance Doctrine Installer; P01 = Harness Infrastructure Builder, confirmed from current `AGENTS.md` / deterministic resolver / exported prompt catalog and owning registry blob `848728632c1243ebba023fa0012292a2ad33cada`. Private instruction index and engineering/context-system routes read on 2026-11-10; no private custom-instruction text was copied to this public repository.

**P00 landed on branch after historical ontology consultation:** machine `contracts/ontology.v1.json` revision 5 adds `HIGHLIGHT_OBSERVATION` (measured independent glow cues), `WORLD_TARGET_TRACK` (target/camera/revision continuity), `WORLD_INTERACTION_ATTEMPT` (post-action, replay-unique, explicitly non-interrupted evidence) and invariants `BI-ONT-028..030`. The canonical root `AGENTS.md` routes to detailed agent rules, while `docs/DOCTRINE.md` and `docs/ONTOLOGY.md` preserve all prior safety/identity and explain no model, glow or fixture grants `CONTROL_PERMIT`. BI-002 hunger stays active; real P08 sensor is nonpromoting support. No OS peripheral/Print Screen/Bluetooth/keymap change, game save action or foreground access was performed.

**P01 implemented (not just proposed):** `contracts/world-traversal-harness.v1.json` owns the canonical codebase map, staged `OFFLINE_PREFLIGHT → WORLD_SENSOR → WORLD_OUTCOME → WORLD_INTEGRATE` workflow, four artifact/privacy classes, all existing input/safety owner links, runtime partition, explicit validator/skill activation and the *existing* workstation path registry. `docs/WORLD_TRAVERSAL_HARNESS.md` records the full reproducible agent workflow; `.cursor/skills/world-traversal-p08/SKILL.md` triggers only for world-object sensor work. No new scheduled tasks, watchers, game hooks, local user settings or competing cursor path. `scripts/check_world_traversal_harness.py`, 15 negative `tests/test_world_traversal_harness.py` cases and CI enforce presence/identity/proof/privacy, no phantom local activation, single screen ownership, P08 serialization, BI-002 retention and exact machine path owners. Existing `scripts/horizon_status.py` remains the operator-facing report, not a second status service.

**Proof boundary:** Green repository CI proves governance and typed routing; independent local Cursor skill activation, real world screenshot accuracy/feature learning, P08 permitted click and BI-002 5+5/rollback/maintainer review are still **unobserved** without an authorized local game host. NEXT: run `python -m scripts.horizon_status` and `python -m scripts.check_world_traversal_harness` from the existing canonical local checkout, then use an operator-approved disposable Sims Live session for sensor-only P08. Record PR/merge/postmerge checks in this ledger only after provider readback.


## 2026-11-10 — Double-confirm focus-borrow admission following human-first mainline

**Parent:** merged #175 establishes typed human-sovereignty effect classes and
independent bounded passive observation. A second contract slice closes a
specific race in `screen_admit`: previously one idle snapshot preceded focus
stealing, and a remembered focus claim could survive a human foreground change.
Two fresh input probes must now precede any focus borrow; two more follow
the borrow, with exact Sims foreground required before one game effect.
`needs_force` composes the canonical gate. This is offline code/fixture
work; physical operator takeover, foreground restore and live gameplay remain
independently uncertified. Consultation:
`contracts/consultations/BI-HUMAN-FOCUS-BORROW-ADMISSION-20261110.v1.json`.

## 2026-11-10 — Human-first effect lanes and host input sovereignty

**Parent objective:** make every BetterInstincts subsystem yield to physical
operator use of any application, keeping read-only observation/reasoning useful
while preventing screen/game effects and forbidden Windows control. The reported
Bluetooth, Print Screen, Escape and U interference is classified as
UNAUTHORIZED_OPERATOR_HOST_CAPABILITY_INTERFERENCE; attribution/root cause
remain unproved from GitHub-only access.

**P95/P82/P08/P07/P124:** Reuse existing cooperative screen-owner and idle
admission instead of inventing a second daemon. Added typed policy,
bounded independent passive observation, direct regression fixtures and expanded
host-setting static deny lists. P08 Windows/Sims runtime proof remains required,
not asserted by offline CI. Consultation:
`contracts/consultations/BI-HUMAN-SOVEREIGNTY-EFFECT-LANES-20261110.v1.json`.
Keep BI-002 hunger live certification ACTIVE and do not overwrite parallel PR
#159 spatial-perception work.

## 2026-11-10 — P04 canonical next supporting contract horizon priority

**Operator direction:** After the exact P83→P03→P141→P124→P04 Closers repair (#169), invoke Moonwake P04 again so that the **next priority exists in the canonical BetterInstincts contract horizon** for durable local-agent execution. The existing runbook alone was not enough: `plans/horizon.v1.json`, `plans/active/BI-HORIZON.dispatch.v1.json`, repo-wide owner `plans/active/BI-HORIZON-EXECUTION-WIDE-20261110.v1.json`, and `scripts/horizon_status.py` did not agree on a discoverable supporting P08 sensor priority.

**Canonical source recovery:** Current Moonwake `AGENTS.md`, resolver, prompt-invocation catalog and the owning `src/tokencorridor/interface/promptkit/registry/base/prompts.json` at blob `848728632c1243ebba023fa0012292a2ad33cada` confirmed P04 is the repo-aware sprint/harness factoring distributor. BetterInstincts existing canonical product stage `BI-002` remains ACTIVE_GAME_UNPROVEN. The latest mainline inspected before this change was `57eb5edd0639615f38152d7ba8e27b2c820c4516`; PR #159 (spatial perception) and PR #149 (needs/homework) are open, separately owned. Repo-only ChatGPT+GitHub is `CURRENT_CHAT_RUNTIME`, not the local Windows game host. No local agent dispatch or game input is observed from this provider connection.

**P04 placement / factoring:** Reuse the existing native `BI-HORIZON.dispatch.v1.json` rather than create a second planner. The next supporting priority is `BI-WORLD-TRAVERSAL-P08-SENSOR` with a strict `WORLD_SENSOR → WORLD_OUTCOME → WORLD_INTEGRATE` sequence. Actual camera, object, highlight and private game evidence belongs to `LOCAL_AGENT_RUNTIME`; GitHub source/review belongs to `CURRENT_CHAT_RUNTIME`; CI static proof belongs to `CI_OR_REMOTE_RUNNER`; physical save/user permission is operator-gated. Live sensor and observed click phases share one cursor with BI-002 hunger, so **serial execution** is required. Only source/CI work already completed here counts as provider-executed; do not invent launched autonomous workers or use an unverified Moonwake runner command. The runbook remains `plans/active/BI-WORLD-TRAVERSAL-CLOSERS-P04-20261110.md`.

**Governance and regression:** Ontology consultation `contracts/consultations/BI-P04-WORLD-TRAVERSAL-HORIZON-ROUTING-20261110.v1.json` committed before changing Horizon. `scripts.check_horizon.validate_dispatch` and `scripts.horizon_status.status` join both canonical files and enforce BI-002 retention, genuine local host, local-only receipts, sensor-before-click, PR #159 ownership, explicit nonparallel cursor and Windows-peripheral safety. Focused tests reject missing cross-reference, wrong host, orphan/out-of-order dependencies and game-screen races. No new background agent, save migration, Sims mod release, external desktop setting, or user-private game data was created.

**Actual validation and integration state:** Record specific GitHub PR, test results and postmerge SHA only after CI verification. **NEXT:** local host agent reads `python -m scripts.horizon_status`, executes the source-only preflight, then obtains exact-patch and approved disposable-state proof before passive sensor measurements. BI-002 5+5 hunger/rollback/review remains open and independent.

## 2026-11-10 — Moonwake Closers: verify, repair and reconcile world highlight learning

**Operator request:** Invoke the established Closers composition P83 → P03 → P141 → P124 → P04 on the full world-traversal/learning conversation, not just re-describe PR #168. Current Moonwake AGENTS, deterministic resolver and five canonical prompt bodies were read; the group alias itself was not found registered on Moonwake main. Current BetterInstincts main at review was `6a399ea` (merged PR #168), with full `test` and independent peripheral-safety checks successful. Open PR #159 owns spatial-perception work; avoid overlapping its `host_listener`.

**P83 material findings:** While a target remains visible under the pointer, a real sensor may show `highlight_target_id: null` once the highlight disappears. The original evaluator threw before recognizing `HIGHLIGHT_LOST`; the host could not receive its reason-specific safe stop. Also, a copied `GAME_EVENT`/operator row with an existing before-capture ref could repeatedly increase model confidence; training/holdout overlap could generate self-validating Brier scores. Missing player-interruption attestation was not rejected. These were source-verified logic gaps, not observed Windows runtime incidents.

**P03/P124 repair scope:** `BI-CLOSERS-WORLD-HIGHLIGHT-EVIDENCE-20261110` ontology consultation precedes source mutation. `world_traversal_learning.py` now recognizes absent highlighted identity on negative cues; positive cues without identity fail closed. A single shared bounded pre-capture fingerprint owner deduplicates accepted supervised labels and excludes replayed training/holdout cases. Only explicitly false interruption is accepted. Nonempty legacy models lacking replay provenance are rejected rather than silently upgraded, and the global fingerprint capacity is 2,048 with no eviction. `host_stack` retains its existing independent world-click admission and was not modified.

**P141 outcome:** Compared actual host sensor proof, larger ML architectures, an immediate unilateral merge of PR #159, and broader cursor autonomy. Selected **first local P08 screenshot/outcome sensor proof** as the next investigation. Others are either premature or independently owned. **P04:** persisted runnable owner/evidence/guard manifest in `plans/active/BI-WORLD-TRAVERSAL-CLOSERS-P04-20261110.md`. The game process, captures, local validation and BI-002 vanilla/modified trials remain independently unobserved from provider-only GitHub access.

**Validation/integration:** Report actual GitHub PR, exact head SHA, required checks, merge SHA and postmerge readback only *after* provider confirmation. Proof ceiling is **OFFLINE_REPOSITORY_AND_FIXTURE_VALIDATION**, not screenshot detector accuracy, live mouse safety, installed mod or BI-002 closure.


## 2026-11-10 — Moonwa…36833 tokens truncated… offline ranking only — live Shift+apply paint and neighborhood meter observation remain OPEN. Does not close BI-002.

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

## 2026-11-09 — P83 verification, correction and advance

Independently verified P78/Trifecta PR #87 was integrated (merge `4730c4f9ba0f8fcdef4ede6354105806e6abaec8`; offline CI run `42575619927` passed). P83 found that the earlier classifier did not enforce the `ATTESTED_OBSERVATIONS_ONLY` rule against permitted `HYPOTHESIS` house-state entities: those could fabricate floor presence, items, styles and apparent enclosure conflict. The revised `room_census` excludes such claims and tracks `unverified_claim_count`. The Build/Buy floor-activity peer now reuses the same multistory/basement normalizer, avoiding its earlier F1/F2-only inconsistency. Room glossary pointers target executable owners; regression tests cover hypothetical room/objects and high/basement floor activity. Real-game collection and BI-002 P08 remain separate, unproven local-host gates.

## 2026-11-09 — Screen atlas and safe pointer rest (P95/P124/Trifecta)

The repeated missed-click and camera-pan operator report is now represented by the inspectable `screen_atlas` inventory and explicitly gated Playwright-hosted game click prototype (PR #90). The existing UI chrome owns normalized names/hotkeys, game scenes own patch/scene identity, hidden-object discovery owns curated console commands, camera traverse owns safe rest geometry, and the cooperative workflow queue owns 15-second player-first admission. No uncontrolled Playwright launcher or independent screen daemon was added. The atlas prohibits promoting candidate targets to click authority without exact-build calibration plus fresh two-source, save/player-safe host observation. Post-click rest uses its own fresh presence checkpoint; interruption quarantines rather than fighting the player. The atlas now emits an explicit per-scene coverage map and exposes an injected, exact-PID native input port. This remains an **offline adapter prototype**, not a wired native Win32 executor, P08 in-game camera proof, or BI-002 certification. Run `python -m unittest tests.test_screen_atlas tests.test_ui_chrome tests.test_camera_traverse tests.test_playwright_interop -v`.

## 2026-11-09 — P95 hover-tooltip observational learning

The operator wants BetterInstincts to learn which user behaviors actually help, starting with hover-triggered tooltips and 3/5/10/30/60-minute windows. Added an explicit ACTIVE-session, per-call opt-in semantic-event port, the bounded pure hover reducer, and reviewed-outcome association evaluations. Tooltip sightings are deduplicated; actions link through interaction_ref to independently evidenced outcomes. Unreviewed associations are pending and recommendations cannot grant input. See [HOVER_LEARNING.md](HOVER_LEARNING.md), contracts/hover-learning.v1.json and tests/test_hover_learning.py. Real tooltip sensor calibration, passive scene capture, actual user-game observations and learned benefit remain unverified; no hook/daemon installed. P95 offline proof only; BI-002 remains ACTIVE.

## 2026-11-09 — P95 + Trifecta input-channel behavior learning

Extended the existing bounded hover learner so catalog-qualified hotkeys and
cheat invocations enter the same opt-in action/outcome ledger and the same
3/5/10/30/60-minute projections. Identity resolution reads the existing
`ui-chrome`, hidden-object, household-object-force and host-funds contracts
rather than copying command strings or logging raw user input. The session
remains read-only/advisory. P95 owns the program seam; P82 tests mixed-channel
deduplication and evidence; P07 owns GitHub CI/merge. P08 cannot certify actual
Sims input events or command effects without a local game host. See
`docs/HOVER_LEARNING.md`, `betterinstincts/behavior_input_catalog.py`,
`tests/test_behavior_input_channels.py`. BI-002 remains ACTIVE.


### 2026-11-09 — Active-Sim camera focus/follow (pre-alpha host lane)

P95/P124 camera-intent seam added: native Enter centers active Sim; Shift+Enter centers lot; real follow requires opt-in in-game camera API, with an app-scoped shortcut mapping that is not installed as an OS/Sims keybinding. Owners: betterinstincts/sim_camera.py, betterinstincts/ui_chrome.py, scripts/sim_camera.py; tests: tests/test_sim_camera.py. Offline/injected-port effects do not establish in-game tracking or BI-002 gameplay certification. The local agent still needs an installed mod, exact active Sim/Live mode, player consent and 15-second idle gating before live proof; the parent hunger/autonomy objective remains unchanged.


### 2026-11-09 — Repair recurring camera drift before pixel targets

A host intent previously planned edge-safe rest and target framing separately, but native world pixels were not checked against the current camera revision at the final action boundary. Camera drift during an agent's screenshot/pixel target analysis can therefore invalidate its measurements. Added a canonical recovery decision, host/listener routing and separate camera-revision-bound native world-click adapter that refuses stale pixels. Stable operator-calibrated HUD buttons remain unaffected. Stop-click when user resumes play, avoid blind portrait right-click, use one-shot native center controls and opt-in in-game follow only with independent admission. Exact-build live game certification remains P08; BI-002 hunger/needs status unchanged.


### 2026-11-09 — Pause-first target stabilization

Extended camera recovery to gate Live pixel sampling on independently verified PAUSED state, using a single guarded EA P toggle only if PLAYING. Already paused/unknown speed yields without input; player pause is preserved. Recheck pause HUD, game clock and clock_revision across new capture, camera reanchor and final native world-target effect. Pausing sim time is not evidence that camera stopped moving or stale skills HUD refreshed. Existing player-idle admission and separate skills panel 5–10s play/observe/re-pause remain intact. No automatic resume. P08 game sensor and physical effect unverified.

### 2026-11-09 — Scene-specific semantic click microsystems (P95 + P124 + Trifecta)

P95 prototype: distinct Sims UI panel/action namespaces (aspirations, career, skills, simology, Live inventory, needs, Build/Buy household inventory, pack-gated small business); composite skills/needs and literal unresolved `skit` do not invent clicks. P124 reuses canonical `screen_atlas`, `ui_chrome`, and `workflow_interop` instead of starting a competing Playwright/Win32 clicker. Runtime admission now checks exact-patch attested target rectangle, safe center, panel-specific visual/operator cues, current layout and selected-Sim revisions, target visibility/enabled/stability/occlusion, then the one-action 15-second idle desktop owner and interior rest. P82 focused regressions in `tests/test_ui_microsystems.py`; P07 GitHub CI/merge ownership. A glossary entry or offline mocked click is not native game proof: P08 exact-build screenshots, real local game click receipts and no-drift/target outcome remain OPEN; BI-002 hunger remains ACTIVE. See `docs/UI_MICROSYSTEMS.md` and consultation `BI-SEMANTIC-CLICK-MICROSYSTEMS-20261109`.

## 2026-11-09 — Queued fertilization vs autonomous whims (P95 + P124 + Trifecta)

**Operator:** Tim abandons queued plant fertilization to chat or follow unrelated Sims 4 autonomy. The user-requested task must survive distraction without fighting explicit player control. **P95:** a per-Sim, multi-target queue-continuity evaluator; **P124:** pure reusable peer, opt-in through existing gardening service and host listener, no second daemon. **P82:** deterministic target/provenance/queue falsifiers; **P07:** bounded source/contract/host tests and mainline convergence; **P08:** native exact-build game-input and fertilization outcome certification remains a local-game-only gate. Source: `docs/TASK_CONTINUITY.md`, `contracts/task-continuity.v1.json`; consultation: `contracts/consultations/BI-AUTONOMY-QUEUE-CONTINUITY-20261109.v1.json`. Proposals cannot click/cancel or mark success without independent evidence. BI-002 hunger remains ACTIVE.

## 2026-11-09 — P95 / P124 / Trifecta human interoperability and preference judgment

Added a guarded, machine-readable preference prompt microsystem to the existing host listener/stack. The separate catalog `contracts/preference-prompts.v1.json` classifies positive likes, harmful dislikes and goal-dependent preferences, while preserving unknown/occult/reward-trait dialogs as HOLD. `betterinstincts/preference_prompts.py` is pure policy; `scripts/preference_prompts.py` permits only one opt-in, fresh-observed, Win32 PID-bound, session/scene/save/queue-guarded input step. A YES dispatch does not imply success and OK requires a separately verified newer confirmation observation and same session/PID receipt. Documentation: `docs/PREFERENCE_PROMPTS.md`. P82 adversarial tests include unknown prompts, stale targets, missing authority, and human activity; P07 CI/PR proof is separate from actual Sims 4 P08 certification. P124 reuses canonical `player_presence`, `control_handoff`, `host_listener`, `host_stack`, `screen_admit` and `workflow_interop`; no competing daemon or screen writer. Removed legacy unsafe stationary-cursor idle and blind trait-OK clicks from `scripts/diy_skill_force.py` (pending real dialog classification). Consultation: `contracts/consultations/BI-HUMAN-PRESENCE-PREFERENCES-20261109.v1.json`. Parent BI-002 remains ACTIVE; actual game/packs/PID proof still requires a local host.

## 2026-11-09 — Household Sim selection, whims, autonomy action moderation, Discovery Quest HUD

**Operator:** protect queued work when switching household Sims, evaluate useful whims without mistaking them for harmful queued actions, and build first-class top-left discovery panels for Scoring Simoleons, Navigating Needs and You and Your Phone. **Design:** `selected_sim_continuity` suspends non-selected Sim work until fresh portrait+queue proof; `autonomy_moderation` yields one evidence-qualified, explicitly opt-in cancellation *proposal* (not a click) for independently harmful autonomous queue actions, and one nonpreemptive verified positive-whim candidate; `discovery_hud` routes verified top-left quest labels through existing scoring/needs owners, plus exact observed phone affordances. No global settings changes, no new daemon, no blind cancel or unverified live action. Consultation `BI-AUTONOMY-HUD-OFFSCREEN-20261109`; source docs `docs/AUTONOMY_AND_DISCOVERY_HUD.md`. Trifecta P82 offline regression tests, P07 integration, P08 local exact-build gameplay proof still OPEN; BI-002 unchanged.

## 2026-11-09 — Top-left Discovery Quest listener → host integration

Second-pass cohesion after `BI-AUTONOMY-HUD-OFFSCREEN-20261109`: `BI-DISCOVERY-HUD-HOST-COMPOSITION-20261109` consults ontology before shared host changes. `host_listener` transports a bounded optional `discovery_hud` snapshot, `host_stack` reuses existing scoring and Navigating Needs evaluators, refuses conflicting legacy goal feeds, and exposes a phone review gate **only** after higher-priority safety/needs/obligation work. No new daemon, game setting mutation, screen-input permission, or live quest completion claim; legacy path absent observation unchanged. Dedicated integration negatives in `tests/test_discovery_hud.py`; P08 game-host truth still pending.

## 2026-11-09 — Global autonomy moderation host bridge (separate preconsultation)

`BI-GLOBAL-AUTONOMY-HOST-20261109` records a second semantic preflight before enhancing the same optional listener path: global `autonomy_observation` now provides the existing per-Sim, proven-origin harm/benefit moderation receipt independently of gardening. Host presence/absent-Sim guards are stronger than supplied policy assertions. No input authority, cancellation effect, settings mutation, new daemon or live-game proof. Regression tests cover generic host, listener tick, manual override and offscreen guard. Source contract `contracts/autonomy-moderation.v1.json` remains the single policy owner.

## 2026-11-09 — Action and whim valence training, mouse-only pin intent

P95/P124/Trifecta extends the same opt-in host listener, not a new scheduler. `behavior_valence` classifies every observed queue action and whim into positive/negative/neutral/unknown plus separate Beta-Binomial reviewed-sample advice; model predictions do not prove negative effects, suppress player choice or authorize queue cancellation. Exact-patch, opt-in operator-reviewed examples update bounded model counts; an optional active-session sidecar can persist an aggregate without storing names/raw media. `whim_pinning` declares a per-whim mouse-only pin route using existing cooperative `screen_atlas` native port and exact attested hitbox, rejecting stale actor/whim/layout or player control; live pin proof remains P08 OPEN. The three top-left Discovery Quest modules remain owned by existing `discovery_hud` and their established domain services. Consultation `BI-QUEUE-WHIM-LEARNING-PIN-20261109` committed first.

## 2026-11-09 — Critical second-floor loss: full-lot pre-mutation protection

**Operator report:** An agent destroyed the entire second floor while building, with no trusted pre-change save. Treat the current game state as a recovery incident; do not save over an intact prior version or claim a backup exists without independent evidence.

**P00** hardens `AGENTS.md` and doctrine; **P01** requires every host Build/Buy caller to route through the same fail-closed lease; **P95** extends the existing `build_library_checkpoint` + `house_state` call stack to a complete multi-story room census with pre-change My Library save and persisted model readback; **P124** keeps `house_state` the sole model owner and `room_census` the projection, rejecting a competing home-snapshot daemon. **Trifecta P82/P07/P08:** falsification in `tests/test_lot_mutation_preservation.py`, repository integration/CI, and separately required Windows live host interception+recovery proof. Offline source commits, tests and merges must never be reported as game-file recovery or live input enforcement. The old inventory/purchase loophole is rejected; no agent mutations or purchases when any floor/room coverage is unknown.

**Incident recovery:** preserve running game and any last-known-good saves from overwrite; verify available in-game Load Game and My Library building versions with human-approved read-only navigation. Only after checking known-good artifacts should an explicitly authorized local agent restore a disposable copy. The second floor is not claimed restored. Consultation: `contracts/consultations/BI-WHOLE-HOME-LATEST-MAIN-20261109.v1.json`.


## 2026-11-09 — Async lot opportunity intelligence and persistent hover affordances

**Parent objective:** while Sims queue actions and the player operates the desktop, keep a bounded, read-only lot survey active; when the player is independently idle and the mode is verified, plan one scoped exploration target through the existing desktop cooperative admission. Memoize observed tooltip/action relationships across host sessions and reuse current patch/lot knowledge to avoid rediscovery. User-selected goals and six needs remain authoritative; no blind queue fill, map panning, raw tooltips or unreviewed clicks.

**P95:** reuse `house_state` → `room_census`, `queue_capacity`, `hover_learning` and `semantic_advisory` semantics; add `opportunity_survey` as a pure ranking peer. Its output is included on player-yield ticks. **P124:** single owners for geometry, queue admission, event validation, index, and screen interop; no parallel daemon or duplicate model. **Trifecta:** P82 regression cases and CI; P07 bounded feature PR and integration; P08 live Windows game proof still open independently of BI-002.

**Contracts:** `contracts/consultations/BI-ASYNC-OPPORTUNITY-SURVEY-20261109.v1.json`, `contracts/opportunity-survey.v1.json`, `contracts/hover-learning.v1.json`, `contracts/host-listener.v1.json`, canonical `contracts/glossary.v1.json`. **Source:** `betterinstincts/opportunity_survey.py`, `betterinstincts/affordance_memory.py`, existing `host_listener` and `host_tandem`. **Provenance:** local token index is runtime memory, not automatically synced to Git; newly recognized semantic terms require evidence-backed source review before canonical promotion. **Validation target:** `python -m unittest tests.test_opportunity_survey tests.test_affordance_memory tests.test_hover_learning tests.test_host_tandem tests.test_queue_study -v`. No unobserved real-game input/queue/speed outcome is claimed.

## 2026-11-09 — fixed-roster household judgment and foreground serial skill progression (Fifth Gear)

Operator-observed Cursor defect: the skill-first N-portrait assignment was expanded by adding a Sim/Servo, online features were entered despite offline gameplay, and the detached UI worker competed with local agents. **Existing canonical owner already implements skill-major round robin.** A concrete execution defect was found: `_execute_plan(close_console=True)` closed the console, but `_execute_household` toggled it again before Space. Fix removes the redundant toggle and requires a fresh screen lease for Space; `--detach` is blocked before spawn, and ordered original roster IDs/first-portrait attestations become required for opt-in execute. Scope policy denies creation/household expansion/online actions; `menu_blockers` rejects online navigation globally. Owners: `contracts/consultations/BI-HOUSEHOLD-JUDGMENT-SERIAL-OFFLINE-20261109.v1.json`, `contracts/household-judgment.v1.json`, `betterinstincts/household_judgment.py`, `scripts/diy_skill_force.py`, `contracts/diy-skill-force.v1.json`, `docs/HOUSEHOLD_JUDGMENT.md`, tests. P95 design, P82 falsifiers, P124 one owner, P07 CI/integration, P08 actual Windows-game observation outstanding. **Evidence ceiling:** GitHub remote repo change and offline CI only. CLI roster input does not prove actual on-screen state; protected player-first/saves and BI-002 remain separate. No live account or active Cursor settings changed.

## 2026-11-09 — P83 verification → Fifth Gear correction → P04 Windows installation handoff

**Parent:** safely install merged BetterInstincts offline toolkit locally, then local agent performs real P08 skill-first household certification. Starting provider floor: PR #146 main squash `5ebe8f74f6869556d947c964aa1392e92fa10259`; no live machine/Sim was available to GitHub API. P83 re-read the actual skill/installer code and identified two material omissions: DISPATCHED-only ledger skips were mislabeled 'already maxed', and the current CLI `--roster-key` compares a supplied list to itself (no live portrait sensor). Also `_execute_plan` spans multiple UI events under one screen lease, so per-effect player-interruption proof remains open. **P95/P124** preserved one existing skill owner; **P07/P82** repair the misleading ledger state, avoid unnecessary Space/console/cursor input on all-skipped plans, and make bootstrap recipe read-only with targeted tests. **P08** local Windows proof remains a hard gate, not simulated in CI. **P04** machine-readable local dispatch at `plans/active/BI-HOUSEHOLD-SKILL-LOCAL-P04.dispatch.v1.json`; complete first-action handoff at `docs/handoff/BI-HOUSEHOLD-SKILL-LOCAL-P04-2026-11-09.md`. No user saves, Mods, machine settings, live Cursor rules or online features changed. Runtime host must inspect canonical checkout and installer manifest before modifying anything.

**P83 second pass:** individual `SKILL_FORCE_MEMBER_ALREADY_MAXED` from a `DISPATCHED`-only ledger was still a false-positive proof phrase, and its skip path parked the cursor. Replaced it with `SKILL_FORCE_MEMBER_NO_PENDING_DISPATCH_UNVERIFIED`, zero-input skip behavior and a focused regression test. Whole-household and per-member states now both distinguish dispatch receipts from panel truth.

## 2026-11-09 — Servo Evil / Escape / laundry-fire regression guards (P95 + P124 + P62 + P83)

**Incident:** a prior agent activated a NEW male Servo (CAS gender "Male" + Continue; the operator's "mail" was the male homophone) when the operator wanted Escape-cancel. That Servo took Evil and, with low Durability plus laundry, caused fires.

**P95 / P124:** extend the existing `diy_skill_force` owner (no second trait daemon) with `trait_safety`, `trait_repair` and `ui_forbids` (contract v10); extend `household_upkeep` with a `servo_fire_risk` laundry gate; extend `decision_eval` / `decision-prompts` with the CAS Continue-vs-Escape-cancel prompt and mandatory Send Alone for host work. **P62:** offline falsifiers in `tests/test_diy_skill_force.py`, `tests/test_household_upkeep.py`, `tests/test_decision_eval.py` (Evil reward never accepted; trait_repair emits `traits.remove_trait trait_Evil` only by default; Escape forbidden as household-traverse close and as spam; new-Servo activate/CAS Continue forbidden without consent; durability-critical blocks laundry; clothesline preferred when unsupervised). **P83 gap review:** live trait removal, household skill levels and the Send Alone dialog remain unobserved; nothing here is a live PASS.

**Consultation:** `contracts/consultations/BI-SERVO-EVIL-ESCAPE-LAUNDRY-P62-20261109.v1.json` (committed before mutations). **Proof ceiling:** `OFFLINE_REGRESSION_GUARDS_NOT_LIVE_TRAIT_REMOVE_OR_SKILLS_PANEL_PASS`. BI-002 and BI-005 stay open.

## 2026-11-09 Send Alone -> JOIN misclick regression (P95 + P124 + P62 + P94)

**RCA:** an agent intended Send Alone on the School Join/Send Alone dialog but clicked the calibrated point `(960,600)`, which actually hit **JOIN**; Charlee traveled to school. Computer-use overlay clicks also do not reach the Sims UI (documented in `scripts/cas_quiz_okay.py`). **P95 / P124:** single owner `betterinstincts/school_attend_click.py` (`plan_send_alone_click` evaluate-only, `score_option_hit` on `click_error_eval` thresholds, `verify_post_click`) with the hit-target contract under `contracts/decision-prompts.v1.json` -> `school.attend.join_or_send_alone.hit_targets` (Join ABOVE Send Alone, relative `send_alone_y = join_y + gap_px`, legacy `(960,600)` **SUPERSEDED / FORBIDDEN**, post-click proof contract, detached-SendInput executor policy). CLI `python -m scripts.school_attend_click plan|verify` (execute optional, gated, default false; reuses `scripts/cas_quiz_okay.click_okay`). **P62:** `tests/test_school_attend_click.py` falsifiers: (960,600) scores as JOIN hit / Send Alone miss; school lot or "School Day ends" => `JOIN_MISCLICK_CONFIRMED`; home lot + dialog gone + school HUD absent + fresh PrintWindow/operator source => `SEND_ALONE_VERIFIED`; computer-use overlay executor forbidden. **P94:** `docs/GAME_HOST.md` strikes the stale coordinates and forbids claiming Send Alone from intent alone.

**Consultation:** `contracts/consultations/BI-SEND-ALONE-CLICK-VERIFY-20261109.v1.json` (committed before mutation). **Proof ceiling:** `OFFLINE_CLICK_VERIFY_POLICY_NOT_LIVE_SEND_ALONE_PASS`. The layout stays `PROVISIONAL_UNCALIBRATED` until a PrintWindow/operator-measured `join_y` is recorded. **Open live gate (operator-owned):** return the Sim to the home lot while the operator controls the screen; a measured Join/Send Alone calibration and a LOCAL_OBSERVED detached-SendInput trial remain with the game-capable local agent. BI-002 and BI-005 stay open.

## 2026-11-10 — cross-repo desktop peripheral ownership reinforcement

- Owner: BetterInstincts, atop PR #160. Consulted ontology rev 4 before behavior guard edits at `contracts/consultations/BI-PERIPHERAL-BOUNDARY-20261110-RCA.v1.json`.
- Guard: `contracts/peripheral-authority.v1.json`, `scripts/check_peripheral_boundary.py` and `tests/test_peripheral_boundary.py`. Agent entrypoints and ontology documentation link this owner; SysAdminSuite owns Windows repair and approved technician rollout.
- Evidence: operator reports both Bluetooth mice successfully connected after service repair. Exact service-only RCA remains unisolated from earlier adapter transition. Game foreground-stealing defect is separate.
- Proof ceiling: repo static/fixture regression until new source checker, ontology chronology and CI are run; no new Windows, Bluetooth or Sims live certification is implied.


## 2026-11-10 — Computer Purchase Upgrade Parts: human-first menu command

**Operator observation:** A computer's deep interactions expose **Purchase Upgrade Parts** and five purchase items (Common, Electronic, Kitchen, Plumbing, Robot Salvage Upgrade Parts). The intermediate menu names and depth are **not** yet certified; do not infer a fixed Order path or coordinates.

**Ownership / Fifth Gear:** P95 maps menu/command/queue/observation/funds/inventory seams; P82 adds falsifiable offline probes and regression tests; P08 live screen and inventory proof remains **UNVERIFIED** without a consented local Sims 4 host; P07 implements the scoped feature; P124 retains the existing DIY planner and `CooperativeScreenQueue` owners. The pre-mutation ontology consultation is `contracts/consultations/BI-COMPUTER-UPGRADE-PARTS-HUMAN-FIRST-20261110.v1.json`.

**Implemented feature scope:** `contracts/upgrade-parts-force.v1.json` v3 exact five-menu catalog, dynamic menu lookup, user intent/spend/price/inventory preconditions, no-bypass OS/peripheral prohibitions. `betterinstincts/computer_upgrade_parts.py` proposes one observed game-native action at a time; `enqueue_computer_menu_step` delegates exclusively to the existing cooperative queue with revalidation and per-effect idle probes. `scripts/upgrade_parts_force.py computer-menu|computer-intent` are on-demand **passive commands**. Preserve the seven-item DIY budget, spawn alternatives, offline install, and earlier per-Sim pocket-stock receipts.

**Safety:** User activity or unknown presence yields. Unknown menu, repeated page, invalid context or unsafe funds state waits. No service, Bluetooth, adapter, driver, keyboard, UAC, EA Connect, unpause, save or Build/Buy mutations authorized. One observed purchase receipt is not automatic inventory success; each purchase must increase the selected Sim's observed pocket count before another is considered.

**Proof separation:** Code tests/PR checks are offline only. A live P08 acceptance requires disposable authorized Live Mode, observed menu discovery, explicit single-unit purchase within spend cap, inventory delta, human-reclaim interruption, and protected Bluetooth/peripheral controls unaffected. Do not claim local install, gameplay certification, or BI-002 closure from a repository merge.

## 2026-11-10 — Native household autonomy goal-yield policy (Fifth Gear)

**Operator intent:** Suppress low-value Sim-autonomy derailments of quantifiably
productive ongoing tasks across all household members, without using
desktop mouse actions or overriding human choices. The source is native
EA interaction/autonomy tuning and script interfaces, not GUI queue clicks.

**P95:** Existing \`autonomy_moderation\` remains canonical. Added
\`evaluate_native_household_autonomy\` to score each supplied Sim, protect
player-command/unknown queues, preserve legitimate needs, leisure, social,
career, income, skill and aspiration yields, and recommend exactly one
evidence-qualified suppression/replacement per Sim. Selection is by
stable Sim identity, not the active portrait or a named household roster.

**P82:** Paired tests cover multiple Sims, active player ownership,
unknown/stale evidence, non-interrupting beneficial leisure, zero-yield
with a verified native alternative, lower-yield goal interruptions and
nonexecution authority. Consulted before mutation:
\`contracts/consultations/BI-NATIVE-AUTONOMY-GOAL-YIELD-20261110.v1.json\`.

**P08:** Exact-game-build EA file and hook reconnaissance, installed
native adapter, live per-Sim queue transitions, interruption recovery and
rollback are NOT OBSERVED. A standalone policy cannot cancel an in-game
action. Do not promote this offline feature to a shipped playable mod.
**P07/P124:** Extend current owners; do not start a duplicate host daemon,
fixed-pixel queue canceller or mutate EA files/saves. Preserve BI-002
hunger certification as a separate active game-host gate.

## 2026-11-10 — Moonwake Closers / native household autonomy Horizon reconciliation

**Parent:** native EA autonomy must protect quantitative, meaningful ongoing Sim goals for
*every* household member without a selected-portrait dependency or desktop cursor
cancellation; player commands and legitimate social, fun, needs and personality remain
higher authority. **Closers sequence:** P83 → P03 → P141 → P124 → P04, resolved
from current Moonwake prompt catalog.

**P83 verified prior result:** PR #170 merged on `main` at
`57eb5edd0639615f38152d7ba8e27b2c820c4516` with offline CI tests,
ontology chronology, and independent desktop-peripheral safety check passing.
The new pure `evaluate_native_household_autonomy` remains a candidate evaluator,
not an EA API interception, installed `.ts4script`, UI click or live queue effect.
Issue #171 remains OPEN for exact-game-build native adapter, multi-Sim queue
observations, override tests and reversible rollback. Nothing in this session
read local EA files, ran Sims, touched saves, changed peripherals or established
the existing local game session is still current.

**P03 / first safe sprint:** add `native_goal_continuity` to the machine
Horizon cross-cutting capability registry; extend `scripts/check_horizon.py`
with anti-promotion guard and negative regressions. Preserve original 12 stage
IDs/edges and BI-002 `ACTIVE_GAME_UNPROVEN`. Consultation preceding mutation:
`contracts/consultations/BI-CLOSERS-NATIVE-AUTONOMY-HORIZON-20261110.v1.json`.

**P141 selection:** cross-stage native autonomy seam (SELECT) vs an extra
blocking milestone (REJECT: would delay needs and violate dependencies) vs a
new desktop clicker/duplicate decision engine (REJECT: player sovereignty).
Not an unrequested broad autonomy rewrite.

**P124 integration:** one policy owner
`betterinstincts/autonomy_moderation.py`, one Horizon validator
`scripts/check_horizon.py`, one active execution owner
`plans/active/BI-HORIZON-EXECUTION-WIDE-20261110.v1.json`; do not rewrite
historical runtime attestations or duplicate closeout state.

**P04 execution boundary:** current GitHub/CI runtime can test the tracked
Horizon policy/validation and merge green work; P08 game-native adoption is
local-game work under issue #171 and BI-002 remains the independent 5 vanilla
+ 5 modified + rollback + maintainer-review gate. A version-correct, read-only
EA source inspection is the next native-autonomy task; gameplay effects remain
`NOT_OBSERVED` until installed and tested.

## 2026-11-10 — household navigation no-oscillation P00/P01 + Fifth Gear

Parent: prevent agents from moving back/forth in the same region without progress. Consultation created in separate earlier commit; ontology revision 7 defines NAVIGATION_SCOPE/REGION/PASSAGE/FRONTIER/INTENT/PROGRESS/STALL/RECOVERY and invariants BI-ONT-036..041. P95: independent route graph versus camera/visual graph. P82: stable weighted navigation with synthetic no-progress A-B-A-B falsifiers. P08: no actual live game host or approved disposable session in this chat, live proof remains UNPROVEN. P07: pure planner + room-map integration. P124: machine contract, validation, CI, governance and ledger. Read-only offline advisory, no autonomous mouse/controller, save, OS configuration or new server. BI-002 needs gate remains active; open spatial perception PR #159 not overwritten.

## 2026-11-10 — P00/P01 native EA programming first, host lab is not game runtime

**Owner clarification:** the user's BetterInstincts vision is game-native Sim behavior,
not a general-purpose computer-use robot that keeps the in-game queue on track
by selecting portraits, pressing Escape or clicking the action queue. Core motives,
autonomy, career, income, skills and goal continuity should be implemented through
verified EA XML tuning and, where needed, patch-specific Sims-embedded Python
hooks. Human choices, legitimate fun/social, mood and personality must still win.

**P00 governance (ontology revision 8):** `GAMEPLAY_IMPLEMENTATION_ROUTE`,
`NATIVE_MECHANIC_EVIDENCE`, `HOST_LAB_BOUNDARY`; invariants
`BI-ONT-042..045`. `AGENTS.md`, mandatory detailed governance,
`docs/DOCTRINE.md`, and `docs/ONTOLOGY.md` now make EA-native programming
the required gameplay architecture. This **does not** ban explicitly approved
desktop/camera/UI tests; those are bounded lab diagnostics and bootstrapping,
not the shipped behavior.

**P01 harness:** machine contract
`contracts/native-gameplay-authority.v1.json`, source/PR validator
`scripts/check_native_gameplay_authority.py`, negative regression tests,
an always-applied `.cursor/rules/native-gameplay.mdc`, and the independent
native-first CI gate. New or changed `betterinstincts/*.py` and native mod
sources require a same-PR `contracts/native-gameplay-decisions/*.json`
file stating whether the change is EA tuning, game script, policy-only,
host-lab-only, or unrelated. Core gameplay policy modules refuse GUI
dependencies and HOST_LAB_ONLY. Offline policy/native route metadata cannot
self-certify game effects.

**Consultation predates mutation:**
`contracts/consultations/BI-NATIVE-MECHANICS-FIRST-P00-P01-20261110.v1.json`.
No game files, protected saves, Sims host, local Cursor installation,
driver, Bluetooth, input keys or user settings were changed in this
provider-side sprint. Static CI is not a runtime enforcement sandbox.
Issue #171 remains the native EA adapter/proof owner; BI-002 hunger
5+5 trials remain the independent Horizon stage. The first game-side
gate is a local, explicitly approved read-only inspection of exact-patch
EA tuning/hooks, not another mouse-driven gameplay loop.

## 2026-11-11 — Fifth Gear first-run download and Sims handoff

**Parent:** One inspectable Windows file safely clones/updates the official canonical BetterInstincts checkout, installs the existing offline toolkit, finds an already-installed Sims 4 executable and requests explicit player consent for launch. On existing games, the user chooses Load Game and the exact save; on new games, Create-a-Sim/placement remains player-controlled and goal-based traits/aspirations are advisory. Never read/edit/delete saves, alter game files, install system tools or change Windows peripherals.

**P95 → P82 → P08 → P07 → P124:** Prior consultation in contracts/consultations/BI-FIRST-RUN-BOOTSTRAP-20261111.v1.json; canonical state machine contracts/launch-journey.v1.json. Source owners: Start-BetterInstincts.cmd; existing bootstrap.py; betterinstincts/first_run.py; scripts/first_run.py; docs/download/index.html; docs/FIRST_RUN.md. CI negatives are offline only. Real player-host Windows launch, save selection, CAS, gameplay and hosted Pages publication remain separately unproven. BI-002 hunger certification stays ACTIVE and is not silently reprioritized.


## 2026-11-11 — P97/P00/P01 Fifth Gear: operator peripheral sovereignty

**Parent objective:** prohibit BetterInstincts agents, host-game helpers, launchers and harness paths from disabling or reconfiguring operator Bluetooth/HID, Print Screen, Escape/U, Windows services/registry, pairing or physical input just to recover gameplay/capture. Investigate causal attribution without assuming AI or driver blame.

**P97:** existing repo mechanisms plus Cline command approval, PyAutoGUI fail-safe, Open Interpreter sandbox/admission and hook timeout behavior inspected; bounded adoption/gap report: `docs/PRIOR_ART.md`. No third-party code copied.

**P00:** consultation `contracts/consultations/BI-PERIPHERAL-SOVEREIGNTY-P97-P00-P01-20261111.v1.json` committed before source mutation; ontology revision 9 adds `PERIPHERAL_IDENTITY_EVIDENCE`, `AGENT_EFFECT_PERIMETER` and invariants BI-ONT-046..048. Detailed governance, doctrine and ontology documentation extended append-only; original `AGENTS.md` retains its size-budgeted routing.

**P01 and Fifth Gear:** existing `contracts/peripheral-authority.v1.json`, `scripts/check_peripheral_boundary.py` and `tests/test_peripheral_boundary.py` strengthened. Scan includes root launchers, all future executable directories, Cursor hooks and workflow YAML; PairAsync/UnpairAsync, Bluetooth service/driver/pairing, input hooks/preferences/registry and disabled PyAutoGUI failsafe are regression negatives. P95 selected reuse, P82 designed hostile fixtures, P08 physical host proof remains independent, P07 CI/PR integrates, P124 keeps one owner.

**Evidence distinction:** working ProtoArc EM11 NL and appearance 962/early generic `Mouse` are supported by operator's SysAdminSuite report; actual generic-label transition, unchanged endpoint identity, M343, guarded failure-event delivery, causal root cause and AI actor attribution remain unobserved here. The game is not authorized to attempt Windows pairing or repairs. GitHub CI/merge proof and physical host hook activation require distinct verified receipts. Existing BI-002 game hunger milestone remains active and is not displaced.

**Safe rollback:** revert isolated branch's commits; no Windows settings, drivers, user saves, game build, or local agent installation altered.

## 2026-11-11 — Closers of the P97/P00/P01 peripheral-sovereignty sprint

Parent #188 remains merged at `a44a7c67dd44e8dd36fecbd4435695b674b9ebc5`; prior GitHub safety and offline CI were green. P83 checked source and independent review. Two valid CodeAnt review findings remained after merge: `.psm1` executable PowerShell modules were missing from the static scanner; PyAutoGUI's `gui` alias could disable FAILSAFE without matching the original regex. A third agent-effect boundary gap allowed Cursor's fixed Python unittest/checker shell commands even though the same agent could change the imported repository files. This is a demonstrable command policy issue, **not proven historical agent causation**.

Consultation `contracts/consultations/BI-PERIPHERAL-CLOSERS-P83-P03-P141-P124-P04-20261111.v1.json` committed before behavior changes. The existing checker now covers additional Windows source suffixes and aliased failsafe disable forms. The existing Cursor pre-effect hook now denies mutable local interpreter commands while allowing read-only Git probes, and protects safety policy/test/checker paths from ordinary agent writes. Machine contracts and adversarial tests are updated in place; no new desktop actuator, daemon, or OS repair mechanism.

**P141 strategic disposition:** selected real local Cursor hook activation proof after the source is integrated; rejected privileged Sims-side hardware repair; deferred a new general sandbox until justified. **P04 factoring:** safe provider-side patch/CI/merge first; independently local Cursor allow/deny proof and SysAdminSuite recurrence/M343 are separate owner/host gates; BI-002 hunger stays open. Durable plan `plans/active/BI-PERIPHERAL-CLOSERS-20261111.md`. No direct local Windows behavior is observed in this GitHub-provider session.

## 2026-11-12 — P141 → Fifth Gear natural semantic survey

Portability and nonjerky observation strengthening: single pure planner `betterinstincts/observation_sweep.py`, explicit read-only DBPF evidence `betterinstincts/ea_geometry_intake.py`, and read-only room-map call seam. Evidence-first zero-movement reuse, stationary capture, revision/floor/novelty and previous-view guards, one smooth monotone candidate path and strict no-actuation status. Original room-map, native autonomy, save and P08 admission remain unchanged. Consultation committed before source mutation (`185b6b70563aa8335360fbc9d124a7cfc9adc559`), decision and regression tests added. Live Sims host certification and actual EA building resource decode remain open; no game-side proof claimed. See `docs/NATURAL_SEMANTIC_SURVEY.md`.

## 2026-11-12 — P97 → P141 → Fifth Gear: semantic camera feedback hardening

Prior-art source inspected ROS Nav2 smoother and active-perception/jerk trajectory research; selected existing observation_sweep as owner. Consultation committed before source. New policy defaults to no motion proposal without explicit opt-in, blocks pending outcomes, avoids last-eight view cycles, demands distinct evidence-source classes and uses quintic minimum-jerk waypoints. Pure functions only; no stealth sensing or Windows/game input, and no local P08 runtime certification. Test/CI/merge proof tracked at PR; BI-002 active. See docs/NATURAL_SEMANTIC_SURVEY.md and docs/PRIOR_ART.md.

## 2026-11-12 — Six-needs and occult profile-specific action learning

**Parent continuity:** BI-002 hunger real-game A/B 5+5, rollback and reviewed
no-player-interruption remain ACTIVE. **Bounded offline extension:** versioned
`contracts/occult-needs.v1.json` maps six adult motives to existing need-lanes
and Fun action IDs; separate typed overlays handle Fairy Emotional Force,
Servo Charge/Durability, Vampire Thirst/Energy and Mermaid Hydration. Other
profiles either retain explicit six motives (alien, spellcaster, werewolf) or
abstain for local verification. Action choices are exact-patch/profile/pack,
observed-menu and player-gated; no actions are executed. Opt-in reviewed
per-motive learning uses bounded opaque unique evidence, measured outcomes,
smoothed ranking with minimum support, harmful-action suppression, and no
automatic disk writes. No Sims API, resident daemon, game input, save edits,
CV inference or auto-mod installation. Consultation committed before any
behavior change; native route POLICY_ONLY. Guide: docs/OCCULT_NEEDS.md.
**Proof ceiling:** provider source/CI only until exact Windows local Sims
observations and native follow-on. MoonWake P08 real-game certification not
observed; local `prompt_group_walk.py` process not invoked in this provider.


## 2026-11-12 — P141 → MoonWake Fifth Gear: local adaptive navigation costs

**Parent:** BetterInstincts learns on the individual's computer how to favor shorter/reliable *verified* Sims routes over time, without inventing SLAM accuracy or spamming Walk. Current main baseline used: `54ca0c5cc342beade013b4e00fd7bf16e8370370`. P141 selected evidence-gated local edge timing and failure estimates over a separate RL locomotion controller or another raw SLAM sensor (PR #159 separately owns the latter). The P141 ontology consultation committed **before** policy edits: `contracts/consultations/BI-TRAVERSAL-ADAPTIVE-COST-P141-FIFTH-GEAR-20261112.v1.json`.

MoonWake order: P141 → P95 → P82 → P08 → P07 → P124. P95 designed current verified graph → opt-in observer → replay-resistant scoped model → deterministic weighted existing Dijkstra; P82 provided slow-path, failure, stale context, replay, player-control and storage falsifiers. P08 requires an actual Windows/Linux compatible Sims installation, exact patch, explicit operator-approved disposable session, real before/after route samples, model rollback, player takeover and a separately observed native goal action; **NOT RUN from the GitHub connector**. P07 implemented source, model, tests, local host listener port; P124 preserves existing navigation, camera, VOI, actual effect and host session owners, and separates policy-only from host-lab code.

Pure route weights update using verified expected-versus-observed time plus failure EWMA, support shrinkage and fixed-point deterministic Dijkstra (`docs/TRAVERSAL_COST_LEARNING.md`). Zero samples/corruption/stale patch or graph => baseline; no input authority or save modification. The new listener port is explicitly activated and opt-in; *no background sensor, daemon, native EA hook, real game passage timing, or local installation activation is claimed*. CI/test/merge evidence must be read back independently; BI-002 hunger remains ACTIVE. This is a supporting movement optimization, not a replacement parent goal.

## 2026-11-12 — Second occult-needs iteration: durable on-device learner

After the typed catalog and offline policy landed on main via PR #205, the
remaining parent gap was that reviewed learning ranked only canonical actions
and lived in memory. This bounded successor introduces replay-safe
`learn_candidate` for novel actually observed menu actions: explicit review,
opt-in, before/after measured motive changes, exact patch, profile and
current-availability gates, and 3+ independently reviewed helpful outcomes
at >=75% helpful ratio for promotion. It also adds explicit user-selected,
approved local JSON model save/load with deterministic profile filenames,
SHA-256 compare-and-replace, symlink/cap guards, locking and readback. No
automatic profile scan/creation, no gameplay input and no privileged I/O.
Changed code is independently classified POLICY_ONLY / NON_GAMEPLAY;
consultation predates mutation. Source guide: `docs/OCCULT_NEEDS.md`.
**Proof ceiling:** offline CI and local file fixtures only, not actual EA
motive/effect calibration. BI-002 hunger game gate stays ACTIVE.

## 2026-11-12 — Servo-to-Servo and Gardener-Bot cooperative maintenance

**Parent objective:** Sim/Servo mutual care, Gardener-Bot repair,
proactive safe battery and Durability maintenance in one existing
household system. Before this work, `household_upkeep` already
supported basic Servo peer tune-up with Robotics verification and
self-charge candidates, but selected humans first and did not
model Utili-Bots. Expanded existing policy to typed Utili-Bot repair,
tune-up and charge targets, helper Servo Charge/Durability reserves,
verified Fix-O-Matic repair qualification, peer Social,
enhanced self-tune and Servo-first maintenance with human fallback.
Separate candidate/queue/attempt/outcome, prevent excessive
tune-up loops, keep wet robots and unknown observations safe.
Consultation was committed before policy mutation; native review
route remains POLICY_ONLY. See `docs/HOUSEHOLD_UPKEEP.md`.
**Proof ceiling:** offline repository CI; no game-side effect,
disposable save tests, EA source IDs or Sims 4 runtime certification.
BI-002 remains the active native hunger gate.


## 2026-11-12 — P141 → MoonWake /fifth-gear computer picker batch

**Operator objective:** Eliminate repeated manual computer upgrade-part
purchases while preserving native Sims play, player sovereignty, per-Sim
pocket stock and approved household spending.

**P141:** Compared existing-owner observed-cart batch, speculative unverified
native EA hook, independent rapid-click service and cheats-only bulk Spawn.
Selected the observed-cart batch as the cheapest defensible policy slice;
rejected a second desktop clicker and silent-cheat default; deferred EA
native execution pending exact game-build evidence.

**P95/P82:** Extend betterinstincts/computer_upgrade_parts.py with five-row
cart quantities, price/funds/total budget checks, one click per new picker
revision, one final Buy and exact funds/pocket inventory reconciliation.
Tests cover five items, overspend, unobserved/stale rows, player takeover,
incorrect totals, extra selections and partial outcomes. Existing single-
item route preserved. Read-only batch and restock CLI, consultation,
native gameplay decision and machine contract retain the design.

**P08 proof ceiling:** No Windows The Sims 4 game process, actual EA-native
purchase hook or independently observed live inventory delta accessible from
the GitHub connector. Offline tests/CI and main merge are separate gates.
BI-002 hunger live certification remains open.

**P07/P124:** One existing purchase owner; no second clicker, no auto-run,
EA Connect, save edits or OS settings. Verify GitHub CI and main merge
independently. Next true gate: exact game build, source-verified EA-native
integration, disposable Live Mode before/after purchase and player reclaim.

## 2026-11-13 — Cursor-free NanoCan dish recycling

**Operator objective:** Have household Sims (including suitable occult
and Servo household members) convert dirty empty dishes into NanoCan
money without a desktop mouse/cursor, rather than wash them at a sink.
Critical prior-art finding: player drag/drop into NanoCan has a reported
§10-per-household-member reward, while ordinary Sim garbage disposal is
often only §10 total. Treat them as different native effect classes,
not interchangeable and never fabricate game currency.

**Implemented policy seam:** `betterinstincts/nanocan_recycling.py`
read-only one-dish/one-can proposal with exact installed build/source,
full fresh item and can proof, cooldown, queue, player, and lot safety.
Attach it optionally under `betterinstincts/autonomy_moderation.py`
native household evaluator. Report planning payout only as
community-reported/uncertified; `reconcile_nanocan_outcome` requires
actual attributed before/after funds + dish removal and does not
mutate money. Consultation-before-mutation in
`BI-NANOCAN-CURSOR-FREE-DISH-RECYCLING-20261113`; native review
POLICY_ONLY. **Actual native Sims mod and P08 gameplay remain unproved.**
The established BI-002 hunger parent remains active. Design + operator
harness entry: `docs/NANOCAN_RECYCLING.md`.


## 2026-11-12 — /the-closers: computer upgrade-parts cart integrity

**Parent remains:** automatic game-native computer purchasing for all five
upgrade-part kinds without player arrow-by-arrow input. Previous PR #210
was independently confirmed merged, and its offline CI passed. This audit
does not upgrade policy code to an installed/verified Sims 4 mod.

**P83 → P03:** Verified code and found missing pocket baseline before the
first arrow and too-weak policy-to-queue batch receipt validation. Introduced
the consultation first, kept the native route POLICY_ONLY and hardened the
existing computer_upgrade_parts.py owner; added focused adversarial tests
before submitting to full CI. No desktop input or save mutation.

**P141:** Compared single-owner transaction hardening, direct EA-native hook
with unknown patch, a second desktop click service and cheat-only supply
spawn. Selected the existing owner; other routes rejected/deferred with
exact game evidence needed for adoption.

**P124:** Existing two-stage proposal/queue API and CLI preserved.
Code debt classification: KEEP existing owner, STRENGTHEN batch queue
boundary, DEFER native behavior to issue #213. No new commerce agent.

**P04:** One serial GitHub source/CI integration lane; native game runtime
cannot be dispatched from this provider. The existing open issue #213
retains the exact-build EA-source/Live Mode/disposable-save obligation.
No claim of local MoonWake walker or five external agents launched.
Merge and CI are separate checkable states; inspect final PR and main
before promoting this source receipt to provider-verified closure.

## 2026-11-13 — Awake household handoff

Manual play recovered Charlee's six needs, verified peer Servo Tune Up, and started Olga's archaeology book. The host now proposes the first eligible awake actor when the selected member is asleep, recharging or away. See plans/active/BI-SIXTH-GEAR-AWAKE-HANDOFF-20261113.md. Native enqueue remains open under issue #171. BI-002 remains active.

## 2026-11-14 — Deterministic sleep-to-next-portrait and household needs continuation
**Parent:** each verified sleep/recharge/absence transition immediately yields to the next verified awake portrait in household order; no task or machine-learning discovery prerequisite. **P141:** extend PR #229 existing owner, reject a new desktop clicker/scheduler, reject requiring chores for attention. **P95/P82:** independent roster rotation, zero-task, critical-needs, optional completed-review receipt and negative proofs. **P08:** no exact EA native-game portrait effect available through GitHub; blocked for actual gameplay, not an offline code pass. **P07/P124:** policy, regression fixtures, mechanics coverage and host-stack advisory integration; no installed native effect asserted.** The returned handoff requires a fresh selected Sim identity, needs, queue and game effect authority; BI-002 remains ACTIVE. See `docs/HOUSEHOLD_ECONOMY.md`, mechanic `household-portrait-attention-rotation`, issue #171.


## 2026-11-14 — PS-0245 mathematical planning / MoonWake Sixth Gear
Recovered MoonWake canonical `/sixth-gear` **P141 → P95 → P82 → P08 → P07 → P124**, BetterInstincts source `1923ecf2`, and PS-0241 activity graph owner. P141 compared duplicate global solver, blanket GP, desktop input agent, and bounded optimized overlay; selected the last. Ontology consultation `BI-PS0245-DECISION-HORIZON-20261114` committed before behavioral code. P95/P82 formalized pure stochastic semi-Markov expected utility, hard feasibility, survival-weighted loss, KKT time relaxation and adversarial cases including a synthetic deadline-greedy counterexample. P08 **NOT RUN**: no access to local exact-build EA runtime/disposable-game instrumentation from the GitHub provider; no machine or live input permit. P07/P124 owned one distinct policy and test suite, keeping the existing PS-0241 route, queue, household and learner owners. Feature PR #255: https://github.com/EndeavorEverlasting/BetterInstincts/pull/255. Early CI run 43627114847 failed one test-fixture route ambiguity among 2034 tests; repaired with a legitimate fresh home-to-garden route. Next CI run 43627406861 passed main offline tests and peripheral safety gate at source head `09fff4c`. This receipt does not imply a local MoonWake walker launch, native package, observed game effect, or merged `main` before independent provider verification. BI-002 and native integration issue #171 remain active.


## 2026-11-14 — PS-0245 /the-closers (P83 → P03 → P141 → P124 → P04)

**P83:** Independently read GitHub PR #255 (merged), source `betterinstincts/decision_horizon.py`, main SHA `2e79e0ac1d1e3e8b2e032bb7d4540a91a499ac56`, and passing final offline CI `43627569877` (2,034 tests with one skip; independent peripheral-safety job success). Live Sims 4 activation, actual game effects, true local MoonWake walker and GP gains remain unproved.

**P03:** Executed the first bounded safe repair after discovering: checking hard motive floors only after action benefits could conceal a mid-action violation; a zero-utility tie could still stage a no-op; a truncated search could leave `next_step` non-null. Ontology consultation `BI-PS0245-CLOSERS-FEASIBILITY-20261114` committed first. Updated source, adversarial regression tests, native-gameplay policy classification and this change history.

**P141:** Compared replacing optimizer (REJECT: duplicative), deploying guessed EA native APIs (DEFER: exact patch not inspected), blanket GP (DEFER: insufficient calibrated evidence) and the bounded existing-owner safety repair (SELECT). Continue product goal through native issue #171, not another advisory-only engine.

**P124:** Preserve `activity_chain`, `decision_horizon`, the existing household/need-rate/queue owners and exact runtime authority; one cohesive code owner with documented conservative need trajectory and denial-on-cap behavior. No broad refactor or behavior-for-appearance churn.

**P04:** Independent source validations belong to CI_OR_REMOTE_RUNNER; source-proven EA game/runtime and protected disposable save are LOCAL_AGENT_RUNTIME, serial with shared game screen and native effect author. The local MoonWake walker and actual agent dispatch were not launched from GitHub/this chat. Durable local handoff: `docs/handoff/BI-PS0245-CLOSERS-LOCAL-NATIVE-GATE-20261114.md`. Preserve proof dimensions for source, tests, PR, mainline, installed mod and live game; verify exact updated branch/CI before treating this closer as merged. BI-002 remains ACTIVE.

## 2026-11-14 — Exact-build BI-002 host preflight

P08 observed the operator-authorized disposable session paused in Live Mode on Windows `1.121.361.1020`. The active profile had script mods enabled and contained the BetterInstincts Ecology script. The session was therefore ineligible for vanilla timing. Local recorder `bi002-20261114` evaluated `INCOMPLETE` with 0 vanilla, 0 modified and 0 rollback observations. An older recorder includes a partial attempt whose evidence label says eating did not begin. Its rows were preserved and excluded from the new run.

BI-002 remains active. Establish a repeatable mod-disabled scenario with measured time to first bite, normalized hunger, simulation lag, queue behavior and exceptions. The modified phase still needs a verified Sims 4 Studio build and exact vanilla tuning export, then an authored reversible package, matched trials, rollback and independent review. No package was built or installed. The consultation is `BI-HUNGER-LIVE-CERT-20261114`.

After the operator restarted, the running executable reported Windows `1.121.361.1020`, the options showed `modsdisabled = 1` and `scriptmodsenabled = 0`, and a fresh window observation showed the disposable household paused in Live Mode with the selected Sim asleep. This clears the mod-isolation prerequisite for a vanilla session. The paused scene gives no trial timing, calibrated numeric hunger or simulation-lag sample. The recorder still contains zero gameplay rows.

## 2026-11-15 — Continue the active Windows certification

Added `Continue-BetterInstincts-Certification.cmd` and `scripts.continue_certification` to dispatch the current-session task through the installed Codex CLI. The task starts with the running Video Gaming offer, reuses historical Yes/No receipts, uses the existing Bellman and receipt sources from #262/#263, and routes a reviewed, synced result to the next BI-002 trial on the oldest authorized disposable save. `--checkout` retains the original evidence worktree when source was updated elsewhere. P08 Windows gameplay and actual provider sync remain to be observed on the host.

## Certification handoff and household continuity

PR #271's handoff preloads Video Gaming Yes/No memory from the original evidence
checkout. It preserves the open session and carries the remaining current-offer
gate. The installer profile stores household choice and the successor route
ranks current-run disposable slots within the reviewed household. Current
Windows offer, observed effects, and authorized load remain local proof.

## Repeat preference continuity

Repeat Video Gaming offers reuse reviewed mechanic and rollback evidence across restarts while keeping current visible resolution distinct. The handoff recalls each exact-build response across the original observer profiles.


## 2026-11-15 — PS-0251 native responder recovery

Main floor for this sprint was PR #276 (dd3e709). PR #275 owns the separate native response adapter stack. The before/during/after trace now projects the admitted dispatch boundary and independent outcome to a paged source-and-regression obligation. Bernice's assisted repeat Yes is a sanitized regression case with unknown current EA acknowledgement and effect. The first genuinely mod-owned response still needs initial native import and response observation on the exact build. BI-002 hunger is active and separate.

## 2026-11-15 — Laundry Day washer availability

The reported floor pile showed “No available Washing Machine” with two washers
and two dryers present, consistent with the verified EA Forums symptom. The
exact cause on the lot is unobserved. The existing household upkeep policy
now ranks current, usable alternatives, distinguishes route/occupancy evidence
from corroborated stale registration, and emits one advisory next step with
player, queue and Servo safety checks. Regression fixtures include the four
present appliances and a disabled tooltip with no diagnosed cause. Exact-build
EA observation, native submit, effect verification and rollback remain open in
[#279](https://github.com/EndeavorEverlasting/BetterInstincts/issues/279).

## 2026-11-15 — Laundry fallback and household reserve

MoonWake Sixth Gear scoped the existing upkeep and budget owners to an
operator-selected §1,000,000 household floor. Verified surplus can fund one
last-resort washer after owned routes are exhausted and the whole-lot backup
is verified. When earning is unavailable, propose a single exact subsidy to
minimum plus verified cost. Income growth remains earned. Source-only P08 is
blocked on the exact Windows game and independent effect/rollback readback in
[#279](https://github.com/EndeavorEverlasting/BetterInstincts/issues/279).

## 2026-11-15 — Cross-microsystem fallback recovery

The existing control-discovery journal routes each attributed assisted effect through the mechanics registry and keeps its own fallback reason and before, dispatch, and outcome evidence. Source owners and existing tests are surfaced in the paged handoff. Reviewed legacy classification adds an event without replay. The offline suite exercises mixed microsystems, unknown ownership, and player protection. Windows evidence remains a separate gate under [#171](https://github.com/EndeavorEverlasting/BetterInstincts/issues/171).

## 2026-11-15 — Household wealth-aware activity forecasts

The existing PS-0245 planner accepts balances above §1 million, enforces the
canonical reserve before debit and after modeled effects, and penalizes losses
more heavily near that reserve. Forecasting applies expected-value weighting
to success and sunk-cost failure and clips gains at the game cap. The normal
microsystem math consumer inherits the policy. Native outcome calibration
remains part of [#171](https://github.com/EndeavorEverlasting/BetterInstincts/issues/171).

## Process-bound Windows play

The download entry verifies the clean canonical main checkout it is about to
run. The host launcher uses current Windows process identity independently of
the dispatch PID. Dev uses the oldest already authorized disposable save in
the selected household and run, through its calibrated local adapter. Production
resolves the latest-played target from current in-game evidence when supplied.
The default production workflow still needs an installed-build save observer and
loader. Launch receipts retain required assistance and any partial dispatch.
Actual Windows save-load/readback and gameplay remain separate proof gates.
