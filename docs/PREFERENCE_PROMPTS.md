## 2026-11-14 — Exact Video Gaming preference tuning found; native observer remains the one next action

**LOCAL EA SOURCE FINDING (operator/local agent, not independently re-opened through GitHub):** Windows Sims 4 `1.121.361.1020`, localization key `0x0A349797` maps to `adventureMoment_SimPreference_Activities_VideoGaming_Like` tuning `265965`. `YES` response ID `0`, loot `266649`, adds `Likes Video Gaming` trait `258767` to resolver `Actor`. `NO` response ID `1`, loot `266780`, adds `Video Gaming No Opinion` marker `266814` to resolver `Actor`. **Both responses also apply buff `263631` to `ActiveHousehold`.** NO is not a state-neutral button, and a buff targeted at ActiveHousehold must not be attributed to only the recipient Actor. The originating interaction supplies the resolver; its Actor must match the moment Sim, never infer the recipient from the HUD-selected portrait or generic dialog owner.

**Machine owners:** `contracts/preference-native-response-map.v1.json` is the single reported static map; `betterinstincts/preference_native_map.py` cross-checks normalized one-shot offer observations and independently linked response, Actor loot/trait, ActiveHousehold buff and activity-resumption receipts. `tests/test_preference_native_map.py` covers wrong build/tuning/locale/actor, inverted Yes/No IDs, NO-as-no-op, wrong buff target, stale/replayed captures and dispatch-without-effect. These are synthetic **offline schema** tests only; a caller labelling an object `EA_NATIVE` is not itself trusted proof. The existing `preference_recipient.py` still owns fresh recipient motive/character/career Bellman/KKT comparison, and `scripts/preference_prompts.py` retains the one-effect input gate.

**Do not re-investigate generic `dialog_show`/`dialog_respond`:** the local agent has already verified their exact-build signatures and identified the specific response map. It reported a scoped MoonWake Sixth Gear local run and a native Python 3.7-parseable, one-shot **read-only observer** under ignored `dist/live-cert/bi002-20261114/bi_preference_observer.py`, and a local-only consultation commit `91492ae`. The GitHub provider could not open those bytes or access the running Windows process; this separate branch does not duplicate/replace that observer or overwrite active draft #261/#262.

**Immediate local P08 execution, not another research sprint:** preserve the mod-disabled paused screenshot as baseline; in a fresh *authorized disposable* game launch, enable and install ONLY the scoped one-shot observer (after reviewing its exact local code and packaging), recreate the Video Gaming offer, capture `moment Sim ID == resolver Actor Sim ID`, actual `response_id` and a fresh `preference-recipient-snapshot/v1` of motives, traits, skills, career deadline and current activity. An agent can then, under the existing player-first one-effect admission, run one explicitly permitted response and capture its native acceptance, target-specific trait/marker and household buff, any confirmation and independently observed activity resumption. To compare the other branch, reset disposable state and repeat; the original paused mod-disabled process need not be spoofed as instrumented. Confirm hash-based uninstall and rollback. No source claim, synthetic receipt, screenshot, static IDs or `INPUT_DISPATCHED` alone is a native cert. BI-002 5+5 hunger remains separate.

## 2026-11-14 — Sixth Gear: recipient-bound Yes/No continuation (stacked over draft #261)

**Changed source:** `betterinstincts/preference_recipient.py` owns native-recipient evidence validation and bounded branch comparison. `betterinstincts/preference_prompts.py` still owns modal stage policy, and `scripts/preference_prompts.py` still owns one independently gated click. A Video Gaming or other catalog heuristic is *no longer sufficient* for a Yes/No recommendation: missing native offer-recipient snapshot, model or proven predicted branch effects yields HOLD. Player direction, unknown prompt, absent opt-in and stale dialog also HOLD.

**Exact identity:** the offered-to Sim is `recipient_sim_id` (canonical unsigned 64-bit *decimal string*, without lossy numeric conversion). It can differ from `sim_ref`, which names the currently selected/observed HUD actor. Each staged response includes recipient ID; a later OK requires a new capture and an identity-matching prior YES receipt. The native live producer must supply `betterinstincts.preference-recipient-snapshot/v1` with `source=EA_NATIVE`, `read_origin=RUNNING_GAME_MEMORY`, same capture, native hook/state revision, current motives, traits, skill levels, age/aspiration/species, current activity, career time budget and actual recipient/household IDs. Its timestamp must precede the offer by no more than 2 seconds. The host verifies this provenance; **no actual recipient snapshot has yet been observed**.

**The same continuation plan:** `continuation_model.continuation_steps` is one shared evidence-bound activity list with optional shared routes. Both branches use the *same* recipient needs/skills/work deadlines and the same planner; `branch_effects.YES/NO` can modify only bounded need, skill, mood or money deltas on the same step IDs, each with its own basis reference. A different chain, a different chosen forecast path, incomplete feasibility, an unobserved skill or a tied score is HOLD. Bellman continuation and KKT time price are reused; branch comparison emits no input permit. A counterfactual planner-local copy binds the recipient as the forecast actor and reports the *actual* selected Sim separately; this is not a claim that the in-game selection changed or that action execution is authorized.

**Schema vs live values:** The local operator's `EA recipient field map` reported `SaveGameData.sims/SimData.sim_id, household_id, attributes`, character and trackers, `commodity_tracker` need/value/change timestamp, and `sim_careers` work/assignment constraints from installed `1.121.361.1020` `generated.zip`. The map is local under ignored `dist/` and was not directly read through this GitHub session; no field numbers or current values are invented in Git. An unauthorised disk save is not a live source. The native producer must inspect exact hook signatures and provide a fresh recipient snapshot from the running game before any automatic preference response is considered.

**Actual game proof still open:** the prior native `SimTravel` observation does not establish `InteractionComplete`, a preference choice, or queue/activity resumption. The source comparator can be tested offline, but the live P08 must observe offer → correct recipient → motive/character/career native read → accepted/declined input under player/queue authority → observed confirmation → revalidated continuation → activity resumed. Maintain protected save, exact patch, opt-in, offline game and rollback gates. Keep PR #261 draft and the local agent's head intact; this work is a separately scoped stacked branch.

**Checks from local checkout:**

```sh
python -m unittest tests.test_preference_prompts tests.test_preference_host_adapter -v
python -m scripts.check_native_gameplay_authority --base-ref <PR_BASE_SHA>
python -m scripts.semantic_preflight --consultation contracts/consultations/BI-PREFERENCE-RECIPIENT-SIXTH-GEAR-20261114.v1.json --operation repo_mutation --file betterinstincts/preference_prompts.py --file betterinstincts/preference_recipient.py
python -m scripts.check_human_sovereignty --json
```

# Skill-triggered likes and dislikes — human-first decision microsystem

**Owner:** `betterinstincts/preference_prompts.py` / `contracts/preference-prompts.v1.json`. **Host caller:** `betterinstincts/host_stack.py` (from `host_listener.py`). **Observed single-step input:** `scripts/preference_prompts.py`. **Screen ownership:** `betterinstincts/screen_admit.py`, never this catalog.

## What the user gets

When a Sim earns skill levels or a preference prompt appears, an agent can evaluate the proposed **like** or **dislike** without automatically clicking the first answer. The versioned catalog starts with practical preferences (Cooking, Gardening, Handiness, Programming, Robotics, Fabrication, Fitness, Painting, Writing, Charisma), while Mischief/Music require a matching Sim goal. A positive like is ordinarily useful; a dislike of a useful skill is ordinarily rejected. A dislike can be beneficial when it supports that Sim's declared goals (e.g., avoid Mischief). The catalog is a *heuristic*, not hardwired Sim personality truth. Player direction always wins.

**Distinct dialog domains remain distinct:** aspiration completion and occult/life-state transformations stay in `aspiration_service`; skill-reward traits must be classified as reward traits, not inferred from a level-up toast; likes/dislikes own only `sim_preference_offer`. Unknown or uncatalogued dialogs **HOLD** and need review. Game build, installed packs and actual phrase/button positions are **not certified by this repository's offline tests**.

## Machine-readable call stack

```text
Fresh game capture (exact PID, Sim, build, scene, candidate dialog, two cues)
  -> existing host_listener.tick / host_stack.evaluate_turn
  -> preference_prompts.evaluate_offer
      HOLD             -> no action
      DECLINE          -> propose single NO
      ACCEPT           -> propose YES, then independently observed OK
  -> explicit opt-in + ACTIVE listener session + trusted desktop-wide 30/60/120s idle
  -> one shared desktop input lock / repeated session and user-owner checks
  -> revalidate fresh capture (<5s), selected Sim, cleared player queue,
     authorized save, same Sims foreground PID and visible client button rectangle
  -> exactly ONE button click via scripts.preference_prompts
  -> receipt says INPUT_DISPATCHED (not accepted/verified)
  -> if YES: recapture the resulting confirmation; same Sim, topic, kind,
     session and process, distinct/newer capture -> separate OK operation
  -> observe actual in-game outcome before recording learned success
```

The listener receives optional structured observation values `preference_offer`, `preference_automation_opt_in`, `preference_game_build_confirmed`. The evaluation result lives at `host_stack.preference_prompt`; it is intentionally **not** a SendInput permit. Observations need `dialog_class: sim_preference_offer`, `dialog_stage: offer`, `scene: live`, `sim_ref`, `capture_ref`, `topic_id`, `offer_kind` (like/dislike), and exactly `visible_buttons: ["YES", "NO"]`; `goal_tags` are optional. Live --execute additionally needs `observed_process_id`, `captured_at_epoch_ms`, `sim_selected`, `player_queue_clear`, `save_authorized`, `game_build_confirmed`, and exact pixel `target_boxes` from the current client viewport (e.g. `YES: [x1,y1,x2,y2]`); don't invent boxes. Independently confirm game scene, window identity and visual target in the producing adapter; this component does not perform image recognition.

```powershell
# Planning only — no game control
python -m scripts.preference_prompts --observation dist/game-host/preference-offer.json --opt-in
python -m scripts.preference_prompts --observation dist/game-host/preference-offer.json --opt-in --stage YES

# A deliberate single click; ACTIVE session/PID and a new receipt required
python -m scripts.preference_prompts --observation dist/game-host/preference-offer.json --stage YES --opt-in --execute --session-id SESSION --process-id PID --idle-ms 30000 --receipt dist/game-host/preference-yes-receipt.json

# Reobserve confirmation with a NEW capture, then one OK; do not replay old capture
python -m scripts.preference_prompts --observation dist/game-host/preference-confirmation.json --stage OK --opt-in --execute --session-id SESSION --process-id PID --idle-ms 30000 --previous-receipt dist/game-host/preference-yes-receipt.json --receipt dist/game-host/preference-ok-receipt.json
```

`--execute` does **not** steal focus from another application. It fails if Sims isn't already foreground; when a person works elsewhere, compatible agents retain pending intentions through `workflow_interop.CooperativeScreenQueue` and retry only after fresh permission. It won't attempt to simulate the game, auto-close every overlay, scan other apps, or alter Sims saves.

## Skill-force regression guard

Prior `scripts/diy_skill_force.py` used stable cursor time as a surrogate for OS idle and dispatched repeated Enter plus guessed reward-OK coordinates after skill upgrades. This could override dictation or accept an unwanted dislike. That logic is intentionally disabled: cursor stability remains diagnostic only; `GetLastInputInfo` must prove trustworthy idle, and reward prompts now report `NEEDS_DIALOG_IDENTIFICATION` instead of being clicked blindly. The catalogued preference path offers a safe next step; *actual reward traits* require their own independently verified prompt adapter. Until then they stay pending, not implicitly accepted.

Offline test commands:

```bash
python -m unittest tests.test_preference_prompts tests.test_preference_host_adapter tests.test_control_handoff tests.test_diy_skill_force -v
python -m scripts.semantic_preflight --consultation contracts/consultations/BI-HUMAN-PRESENCE-PREFERENCES-20261109.v1.json --operation repo_mutation --file betterinstincts/preference_prompts.py
```

## Proof and gaps

P95: explicit dialog judgment call stack; P124: reuse aspiration/host/listener/screen owners instead of parallel controller; Trifecta: P08 live on the actual Windows Sims PID remains open, P82 synthetic negative/positive cases in offline tests, P07 CI and mainline integration. No local player activity, process names, UI targets, spoken words, or hotkey text are persisted by this feature. A running dictation process **alone** does not indicate a person is speaking: a local operator/agent can explicitly mark `--operator-busy` on the handoff CLI, and independent OS input age catches typing/mouse activity even outside Sims. The dormant-state detector is not a voice-recognition service.

## 2026-11-14 - Benefit-based choice

For a verified catalogued offer, recommend Yes when the offered preference benefits the Sim and No otherwise. Video Gaming likes are beneficial under the fun policy. A goal-dependent preference requires a matching observed goal to recommend Yes. Unrecognized topics or ambiguous evidence remain on hold. The lab observed this offer addressed to another household member while the selected Sim slept. The executor still requires verified recipient selection and a fresh input permit.

### Bellman continuation and Lagrange time price

Any caller of the shared evaluator can attach a continuation_model with a same-capture activity-chain snapshot, YES and NO candidate steps, optional routes, and KKT activities. Each branch passes the existing finite-horizon planner. The evaluator compares expected continuation value after time is priced at the allocator's Lagrange multiplier. A catalogued beneficial offer needs a strict advantage to win against declining. Invalid identity or incomplete planning holds. After the response, the caller needs a fresh observation before resuming the plan. Callers without a model retain catalog behavior. Native capture, response and resumed activity remain unverified.

## Native Video Gaming response and recovery

The observed Yes click in [PR #263](https://github.com/EndeavorEverlasting/BetterInstincts/pull/263#issuecomment-6899683733)
resolved the offer with agent assistance. A native automation check requires
BetterInstincts to choose and submit the response on a fresh suitable offer.
Keep the resolved game paused and reuse its historical evidence.

The in-game integration owns one response port per live session. Feed the
existing native observer and recipient planner into
`scripts.preference_response_port.PreferenceResponsePort`. The host attaches
an independently verified adapter with `read_offer()` and
`submit_if_current(request)`; the port computes the branch and calls the adapter.
Submit on the game thread after an atomic recheck of the current dialog,
recipient, revision, player ownership, save scope and pause state. A refused
operation guarantees no submission. An uncertain operation stays reserved
until readback. Carry the adapter dispatch reference into the native ACK, then
use `reconcile` with the independent effect and originating activity receipts.
Adapt the verified local observer under issue #171. The existing observer and
response IDs alone provide no callable EA submit hook. The host coordinator
does not run inside embedded Python or install a mod.

Keep recovery in the active session. If the adapter is missing, continue the
read-only inspection of the installed, exact-build dialog callback or record
the exact unavailable host capability. If recipient evidence is missing,
recover only that evidence and run the decision again. If dispatch is
uncertain, inspect the outcome. A player-owned decision stays with the player.
When a local agent has to supply the action, keep its visible resolution as
assisted evidence and leave the BetterInstincts response check open. Reuse
the current local agent, original receipts, and current session for this work.

Separately, after a resolved repeat, the local agent can verify LabLab's
household and successor-run authorization from the existing observations and
registry. Carry the old entry as provenance and record the new attestation
only after the match and authorization are established. Then use the existing
certification-first save route on current main. A native automation canary
uses the next suitable offer and does not require replaying the resolved one.
