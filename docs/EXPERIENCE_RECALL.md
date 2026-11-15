# Experience recall: remember once, reuse thereafter

**Canonical owner:** \`betterinstincts/experience_recall.py\`; contract \`contracts/experience-recall.v1.json\`. **CLI:** \`python -m scripts.experience_recall\`. This is a tiny historical-receipt index, not a new game planner, preference chooser, chance-card solver, EA observer or background service.

## Operator correction — November 14, 2026

**Do not restart Sims 4 simply because an agent has recognized a previously tested experience.** The game has already been exercised in vanilla and with BetterInstincts installed. The preference Yes and No trials on exact build \`1.121.361.1020\` and the restored rollback constitute earlier evidence; their provenance does not disappear when the game is restarted or when an agent session changes. Reuse the already captured facts and any local receipts before attempting a new trial.

For the pictured **“IT BEGINS...”** Video Gaming preference offer, the prior evidence is:

- EA tuning \`265965\` and localization \`0x0A349797\` already mapped. **Yes = response 0**, Actor trait **Likes Video Gaming \`258767\`**; **No = response 1**, Actor marker **Video Gaming No Opinion \`266814\`**. No is stateful, not a no-op.
- Yes added buff \`263631\` to **3/3 active household members** in the reported trial; the No trial's household-buff readback is still missing.
- After Yes, the UI showed social activity; the originating computer interaction's completion was not instrumented.
- The local agent reported successful no-save exit, hash-verified save rollback, observer removal, settings and Ecology restoration, and game relaunch.
- PR #263's readback validator remains separate and unmerged. Historical outcome evidence is **not** authorization to click this currently open dialog.

## Demand-load operation (NO startup or retest)

1. Identify the **current observed offer** from the visible HUD/EA data, and resolve its exact game build and the **actual installation profile** (prefer an existing mod/pack manifest digest; never invent a profile). This is a lightweight read-only check, not a requirement to relaunch.
2. Ask \`recall\` **before** research, experiment, or observer setup. A hit means \`PAST_EXPERIENCE_RECALLED\` with \`historical_research_needed=false\`; the earlier lesson is ready to inform the current independent preference policy. A miss means inspect **existing local rollback/trial receipts** first—not automatically restart the game.
3. When an **actual previously unseen semantic outcome** has been independently observed or is supported by an attributable operator report, use \`remember\` **once**, with sanitized provenance. Reencounters with the same build, profile, mechanic, choice and result return \`ALREADY_KNOWN\` and **do not rewrite** the on-disk index, increment training counts, or repeat the gameplay trial.
4. Contradictory result for the same identity returns \`CONFLICT_REVIEW_REQUIRED\` and keeps the older lesson unchanged. Changes in game build or installation profile are distinct experiences and are never silently treated as proven by the older record.
5. Resume the current active Sims session if one already exists. A memory hit **does not close the current dialog**, supply a native ACK, prove a present outcome, grant a game input permit or override the player. Preserve one-screen-owner/fresh-scene/player-interruption gates for any separately authorized action.

Example, with actual values from the already completed local evidence (substitute only the known installation profile, evidence reference and observation timestamp; do **not** invent those from this document):

\`\`\`powershell
python -m scripts.experience_recall recall --domain preference_offer --game-build 1.121.361.1020 --installation-profile ACTUAL_PROFILE --mechanic-id ea_265965 --choice-id yes_0
python -m scripts.experience_recall recall --domain preference_offer --game-build 1.121.361.1020 --installation-profile ACTUAL_PROFILE --mechanic-id ea_265965 --choice-id no_1
\`\`\`

Once a genuine local source is identified for a not-yet-indexed prior experience, record it without replaying:

\`\`\`powershell
python -m scripts.experience_recall remember --domain preference_offer --game-build 1.121.361.1020 --installation-profile ACTUAL_PROFILE --mechanic-id ea_265965 --choice-id yes_0 --result actor_trait_258767_buff_263631 --evidence-level OPERATOR_REPORTED_LIVE --evidence-ref ACTUAL_SANITIZED_RECEIPT --observed-at-ms ACTUAL_EPOCH_MILLISECONDS
\`\`\`

Use \`LOCAL_ARTIFACT_VERIFIED\` only after actually reading local receipts and \`NATIVE_RECEIPT\` only for a verified native observer receipt. A user report alone can be stored as \`OPERATOR_REPORTED_LIVE\`. The index itself does not authenticate caller provenance. The same behavior generalizes to career decisions, needs, ecology tasks and object interactions; the index stores previously learned **outcome pointers**, while each existing domain owner retains actual decision semantics.

**Storage:** \`dist/experience-recall/experiences.json\` in the explicit project checkout, ignored by Git. The index is created **only when the first new experience is committed**; duplicates and conflicts create no directory, temp file, write or modified timestamp. It contains bounded context, a sanitized outcome token, provenance level/reference and observation timestamp. No Sim names, household IDs, personal paths, raw screenshots, gameplay telemetry, profile crawling, or save changes. Retention is by exact scope rather than an automatic 30-day forgetting timer; there are 128 bounded records, with no silent eviction.

This seam **complements** existing \`chance_event_research.remember\`, \`judgment_learning\` and \`object_action_catalog\`; it does not replace their trained policies, reviewed decisions or native-game receipt gates. The independent **BI-002 hunger five vanilla/five modified/rollback** certification is not closed by remembered preference facts.

## Multi-agent write safety (MoonWake Closers, 2026-11-14)

The previous first-version store used an atomic file replacement but did not serialize the read-modify-write transaction. Two agents could both read the same index, independently append distinct new facts, and the later replace could discard the earlier experience. P83/P03 found this before treating cross-agent continuity as closed.

The same canonical memory owner now performs a **read-only first lookup**: familiar facts and conflicts do not create storage, a writer lock, or a new training example. A genuinely new experience obtains an exclusive, bounded local writer lock, **re-reads** the latest index, and only then writes its combined contents by atomic replacement. A second agent that races with an active writer receives `EXPERIENCE_WRITER_BUSY` without altering either record; it may retry the explicit command after the writer finishes. An existing crash/foreign lock is never automatically stolen or destroyed.

This is **not** background automation or a native mod hook. Existing operator-provided and artifact-proved preference outcomes are eligible historical records; a screenshot of the presently open dialog is not evidence that the current instance has been answered. The caller must still load the memory from the intended canonical checkout. Separate worktrees have distinct ignored `dist/` directories and are **not** silently synchronized by this feature. An agent switching worktrees must deliberately use the same canonical checkout/store or explicitly reconcile records; do not pretend memory was seeded just because the source module exists on `main`.

The follow-on agent should first consult `recall` and existing `dist/live-cert/bi002-20261114` trial/rollback receipts on the Windows host. Only absent, newly observed distinct experiences deserve `remember`. Do not launch a new game or repeat a completed vanilla/mod trial to make an already-known experience readable.

## Proof and verification

\`\`\`sh
python -m unittest tests.test_experience_recall -v
python -m scripts.semantic_preflight --consultation contracts/consultations/BI-EXPERIENCE-RECALL-20261114.v1.json --operation repo_mutation --file betterinstincts/experience_recall.py
python -m scripts.check_native_gameplay_authority --base-ref <ACTUAL_PR_BASE_SHA>
python -m scripts.check_human_sovereignty --json
python -m scripts.check_peripheral_boundary
\`\`\`

A test or merged change proves an offline memory mechanism exists. Automatic local-host recall, remembered-record seeding, native observer availability, a currently open dialog response and Sims gameplay certification each require their own observed receipts; none are inferred from this code.
