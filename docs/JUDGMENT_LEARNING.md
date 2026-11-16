# BetterInstincts — reviewed judgment learning (P97 → P95 → Trifecta)

## Product outcome and boundary

**Operator hypothesis:** early in development, human players recognize good opportunities that a local agent misses. The opt-in listener should make these judgments reusable so advice becomes more situational over time, without silently learning poor behavior or taking away the player's control. Player direction, character, rest, leisure, privacy and save safety always outrank pattern scores. The Horizon remains **needs → income → skills → career**, with BI-002 hunger the first actual certification.

**Implemented:** a small, explainable, first-order **contextual Markov-count learner** over *operator-reviewed, consented semantic examples*, producing strictly **advisory** action candidates. It is not a machine learning agent hooked into the Sims runtime, not live imitation from keyboard monitoring, and not a finished gameplay mod.

## Passive learning while the player has control

Enable it for one existing host-listener session with an opaque, local profile
token. Reuse that token to recall the same profile in a later session.

```sh
python -m scripts.host_listener activate --session-id SESSION --player-learning-profile LOCAL_PROFILE
python -m scripts.host_listener tick --session-id SESSION --process-id VERIFIED_GAME_PID --observation OBSERVATION_JSON
python -m scripts.host_listener deactivate --session-id SESSION
```

A calibrated adapter supplies the optional `player_learning` object on a
normal listener observation. For a continuous bounded session, pass the same
observations through `host_tandem.run_opportunity_survey_session`. The callback
keeps reading while the existing host action gate yields. Use it without
exploration callbacks for a dedicated observation session.

| Event | Required fields in `player_learning` |
| --- | --- |
| All | `kind`, opaque `run` and `household` tokens, `platform`, monotonic integer `sequence`. The outer frame supplies exact `game_version`, `actor_ref`, `capture_ref`, six normalized `needs`, current Live cues and viewport. |
| Choice | `interaction` token bound to the game interaction, `owner: "PLAYER"`, `scenario`, `style`, `previous_action`, `action`, `available_actions`. The adapter observes menu availability and player attribution. |
| Outcome | Same `interaction`, a third distinct `effect_capture`, boolean `completed`, and `goal_delta` from −1 to +1 in the chosen scenario. The adapter supplies progress attributed to that interaction. |
| Query | `scenario`, `style`, `previous_action`, `available_actions` from a fresh idle frame with an empty queue. The current need condition comes from the frame. |

Use one writer per listener session. A choice is provisional until an outcome
arrives within eight ticks on the same game run, process, exact patch,
household and Sim. A foreground or scope change, an intervening unattributed
action, or an observation gap ends the provisional match. The store keeps at
most 256 deduplicated episodes per local profile. It retains hashed provenance
and semantic context, action and outcome labels under ignored
`dist/judgment-learning/player-observed`. Closing the session ends passive
learning. For a reset, close all sessions using the profile, then remove only
its SQLite file. Transferring source leaves local data in place.

Three independently captured helpful demonstrations in the same context and a
helpful rate of at least 75% can produce a later `player_learning` advisory.
Urgent current needs, player control, a busy queue, tied preferences, and a
harmful precedent suppress the affected advice. This complements the
operator-reviewed workflow below. Both use the same contextual ranker, and
the listener emits no effect permit.

The installed-game producer for player-attributed decisions and independent
outcomes still needs exact-build Windows validation under issue #171. The
first live check is one consented disposable-session action with an
independently observed result, then a held-out idle query plus a protected
player-queue control. The synthetic comparator and local SQLite exercise
establish source behavior and replay handling.

## Installed native lifecycle

The installed ecology package can embed the shared contextual learner and
five-second responder policy. An inspected exact-build EA entry module calls
`start_installed` once for its current game session with the owned
`Mods/BetterInstincts` directory and the local player's learning opt-in. To
build this package, pass `--installed-player-runtime` to
`python -m scripts.native_ecology_bundle build` with the existing hook proof
and the inspected `installed_player_runtime_binding_ref`.

The entry adapter registers `observe` for player choices and outcomes and
`cycle` for planned response opportunities. A `Frame` carries trusted
real-time activity and a generation that changes on input. It also binds the
capture to the game run, selected Sim, admitted save and household. The
adapter supplies semantic game events only. It neither launches a separate
process nor reads a checkout at runtime. The runtime persists bounded hashed
demonstrations in `Mods/BetterInstincts/player-learning.sqlite3`. Uninstall
preserves that local learning file. Learning and read-only analysis can continue
during takeover.

The adapter's `analyze` returns a mapping from semantic action to a candidate
ID in normal native policy order, a current optional learning query, and needs.
Learning can prioritize an available candidate. At **5.000 real seconds**
of inactivity the controller may consider a proposal on the next native
callback. It rechecks activity generation, player queue, target scope and
capture. The adapter's atomic `submit` performs the last fresh target, queue
and input check, and returns `QUEUED` or a verified `NO_EFFECT`. The adapter
must use new IDs for new opportunities and reconcile an uncertain or queued
submission before another effect. Desktop control retains the existing
15-second rule.

Sims listing a mod file establishes package discovery. Callback registration
and a first qualified Live frame establish listener readiness. Measure the
takeover, the next five-second window, an independently attributed outcome,
and the effect of an eligible queued candidate on the installed game. This
proof and the EA adapter remain open under [native integration #171](https://github.com/EndeavorEverlasting/BetterInstincts/issues/171).

## P97 prior art — source-level evidence, 2026-11-07

| Reference and pinned main | Concrete inspected implementation | Decision |
| --- | --- | --- |
| [Lot51 Core](https://github.com/lot51/core-library/blob/f12c1b1bcfb4d0de37bead0f7235eaa840774ff7/services/events.py), `f12c1b1`, MIT | `CoreEvent`, `EventService.handler`, `process_event` support game lifecycle event handlers with isolated callbacks. **OBSERVED_IMPLEMENTED** API, not certified for user's patch. | **ADAPT LATER:** event-driven integration only when a Sims script hook is empirically necessary. Do not bundle or auto-install Core. |
| [River](https://github.com/online-ml/river/blob/4768de0579f977315e65cd23ee658534c1d62c26/river/compose/pipeline.py), `4768de0`, BSD-3-Clause | `Pipeline.learn_one`, `predict_one` and streaming evaluation in [progressive_validation.py](https://github.com/online-ml/river/blob/4768de0579f977315e65cd23ee658534c1d62c26/river/evaluate/progressive_validation.py). **OBSERVED_IMPLEMENTED** sequential predict-before-learn. | **ADOPT protocol, NOT dependency:** bounded prequential evaluation, clear train/predict boundary; library adds dependencies before gameplay evidence warrants them. |
| [hmmlearn](https://github.com/hmmlearn/hmmlearn/blob/e01a10e99df1042e4c1e6b7c822fd292dd37502f/src/hmmlearn/base.py), `e01a10e`, BSD-3-Clause | probabilistic hidden-state inference and transition models. **OBSERVED_IMPLEMENTED** general HMM inference; no Sims judgment ground truth inspected. | **DEFER:** hidden-state inference is premature for few reviewed examples and makes explanations harder. |
| [XML Injector](https://www.curseforge.com/sims4/mods/xml-injector) | Community-managed interaction snippets as described by distribution page, source not inspected. **DOCUMENTED_UNVERIFIED.** | **UNKNOWN for learner:** useful for specific future game interaction injection, not a teaching or learning engine. |

**Solved internally:** opt-in `host_listener`, player-presence and single-step screen ownership, `behavior_eval`, `event_balance`, scene/viewport gates, Horizon progression scorer. **Available externally:** incremental supervised learning interface and predict-before-learn evaluation; bounded event systems. **Project-specific gap selected:** link reviewed *human chosen action + outcome + situation + preceding action* into conservative explainable recommendations that can appear on an existing listener receipt. **Evidence gap:** approved real game demonstrations, calibration against actual game observations, compatibility of any runtime mod hook on the exact patch, transferability across households. No third-party source code copied.

## P95: call-stack architecture and ownership

| Owner | Input and output | Side effects / proof |
| --- | --- | --- |
| `scripts.judgment_learning` | explicit `train` / `recommend` one-shot commands; local JSON files in `dist/judgment-learning/` only | atomic local model file with **aggregate counts**, never a raw game capture or Sims file |
| `betterinstincts.judgment_learning` | validate reviewed examples → first-order transition counts → context/action recommendation; `prequential_evaluate` | pure in-memory functions, no game IO |
| `contracts/judgment-learning.v1.json` | schema/limits, opt-in, exact version profile, thresholds | tracked contract, no active game permissions |
| `betterinstincts.host_listener.tick` | explicitly supplied `learning_model` + `learning_query` and existing opt-in `PresenceProbe` | optional `learning_hint` in bounded receipt; no learning auto-train, no click |
| `control_handoff` + `host_stack` + `needs_force` | remain sole authority for human control / gameplay action | **never** accept learner output as SendInput authorization |

**Semantics:** state is discrete `scenario`, `need_state`, `scene`, `previous_action`, `style`. The preceding action is the Markov transition input; context and style allow meaningful differences rather than one robotic globally favored action. No names, household IDs, raw notes, event titles, user paths, photos or audio in the model. Training events **must** have opt-in, operator review, helpful/harmful outcome, sanitized reference, exact patch/platform, and enum fields. These are *reviewed claims* until independent game evidence exists.

**Training call stack:**
```text
human plays on explicitly authorized disposable LAB save
  -> local game agent observes a situation (manual, no passive recorder)
  -> human reviews action AND observed outcome
  -> explicit, bounded semantic examples JSON under ignored dist/judgment-learning
  -> scripts.judgment_learning train --explicit-opt-in
  -> validate context, exact patch, permission and size
  -> learn contextual (previous action -> selected action) counts
  -> prequential evaluate: predict BEFORE consuming each example
  -> aggregate model and eval receipts under ignored dist/
```

**Advisory call stack:**
```text
explicit session + host_listener tick with manually supplied validated observation
  -> control_handoff: player first, unknown input age yields
  -> host evaluators and existing queue plan unchanged
  -> optional explicit aggregate model + query
  -> check patch, context, scene, action availability, human presence
  -> if >=3 reviewed helpful and >=75% helpful: advisory choice
  -> else ABSTAIN (ambiguous ties also ABSTAIN)
  -> listener receipt learning_hint / execute_clicks:false
  -> NO game execution from learning channel
```

**Failure call stacks:** absent opt-in/unknown external file → BLOCKED; player input or queue → YIELD_TO_PLAYER; novel patch → ABSTAIN; unverified scene or unknown action → ABSTAIN; high dispute or tied patterns → ABSTAIN; model too large/duplicate reference/unsafe file → BLOCKED; Live black/unknown viewport → no learning hint eligible. Exact input is intentionally short and domain-specific: avoid arbitrary JSON key/value dumping into a learned policy. Do not equate hindsight action success with causal proof.

## P82 experiment decision and safety

Hypothesis: for repeated *reviewed* contexts, a first-order contextual model will return a useful action more consistently than a context-free always-most-frequent-action heuristic, without player override or action availability regressions. **Current evidence:** synthetic tests only. Compare on held-out chronological observations from a real disposable save *after* humans review the outcomes; avoid training/test leakage. The current CLI reports prequential coverage and precision when issued, not inflated accuracy when it abstains. Evaluate unsafe suggestions (target zero), abstention by novel patch/context, action diversity across styles, refusal during player control, latency, and per-context beneficial-outcome proportion.

**Predeclared decision:** **PROMOTE** an advisory candidate for supervised live evaluation only if review demonstrates improved relevant-action selection versus the simple global baseline, zero player-queue overrides, consistent safety and reproducibility on an exact build. **WEAKEN** when coverage is too small, labels noisy or context insufficient; **REJECT** any unsafe suggestion; **INCONCLUSIVE** when no real approved observations exist. None of these outcomes closes BI-002. Do not auto-inject a dependency on River, HMM, LLM or external service.

## One-shot local workflow

All inputs/outputs are inside ignored `dist/judgment-learning/`; never commit private observations, capture references, or model counts.

```sh
python -m scripts.judgment_learning train \
  --reviewed-examples dist/judgment-learning/reviewed.json \
  --game-version ACTUAL.FULL.GAME.VERSION --platform windows \
  --explicit-opt-in \
  --model-out dist/judgment-learning/model.json \
  --evaluation-out dist/judgment-learning/eval.json

python -m scripts.judgment_learning recommend \
  --model dist/judgment-learning/model.json \
  --query dist/judgment-learning/query.json

python -m scripts.host_listener tick --session-id ACTUAL_ACTIVE_SESSION \
  --process-id ACTUAL_GAME_PID \
  --observation dist/game-host/ACTUAL_REVIEWED_OBSERVATION.json \
  --learning-model dist/judgment-learning/model.json \
  --learning-query dist/judgment-learning/query.json
```

The record format is exact and inspectable in `tests/test_judgment_learning.py`; `reviewed.json` is a list of records with `schema=betterinstincts.judgment-example/v1`, `game_version`, `platform`, `context`, `action`, `outcome`, `operator_reviewed=true`, `opt_in=true` and sanitized `observation_ref`. The query must include available actions confirmed for the current game scene. Model `recommend` exits successfully on ABSTAIN because that is a correct safety disposition.

## Proof ceiling and local P04 continuation

**Implemented and CI-testable:** model, CLI, optional listener advisory and safety regressions. **Not observed:** fresh human-approved gameplay examples, Sims compatibility, real-world improvement, game interactions or autonomous mod behavior. **P08 local agent** must first qualify the session/patch/disposable save and observe one real BI-002 vanilla hunger trial; it can separately curate reviewed examples without treating them as a gameplay certificate. Use `docs/LIVE_CERT.md` and `plans/active/BI-002.execution.v1.json`. The next agent should measure a genuinely new *opportunity* in-game (e.g., indoor Sit and Chat Here versus unproductive outdoor walking) and replay this advisory against that evidence, not just report a green test.

## Second-pass interface: one deliberate teaching action

A local agent no longer needs to hand-author a whole JSON training array just to capture one useful operator judgment. The explicit `record` command validates one sanitized context, requires **both** `--operator-reviewed` and `--explicit-opt-in`, and appends it to a bounded list inside ignored `dist/judgment-learning/`. Duplicate observation refs are rejected. No automated screenshot or keyboard recorder is installed; the operator or agent must supply action, observed outcome and sanitized source reference.

```sh
python -m scripts.judgment_learning record \
  --context dist/judgment-learning/context.json \
  --game-version ACTUAL.FULL.GAME.VERSION --platform windows \
  --action sit_and_chat_here --outcome helpful \
  --observation-ref capture:actual_reviewed_001 \
  --examples-out dist/judgment-learning/reviewed.json \
  --operator-reviewed --explicit-opt-in
```

`context.json` is a compact object with exactly `scenario`, `need_state`, `scene`, `previous_action`, `style`; see `tests/test_judgment_learning.py` for accepted semantic labels. Do not claim `operator-reviewed` unless the person really reviewed both action and outcome. A learned action may be suggested repeatedly when supported, but cannot directly queue, cancel, or execute any interaction.

**Measured comparator:** `prequential_evaluate` now reports both the contextual learner's issued-action coverage/precision and a chronological context-free global-most-frequent-helpful-action comparator. The comparator also predicts *before* consuming the current event. Compare both coverage and precision; a higher conditional precision with near-zero coverage is not automatically a better player experience. These numbers are diagnostic until real reviewed game observations exist.
