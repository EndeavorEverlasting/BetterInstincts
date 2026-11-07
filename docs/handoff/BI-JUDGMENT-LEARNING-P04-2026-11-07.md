# P04 — BetterInstincts judgment-learning live certification handoff

## LAUNCH ORDER

1. **GATE-0 (CI_OR_REMOTE_RUNNER):** confirm `main` contains reviewed learner PR #41 and **post-merge CI**; run focused + full tests on local checkout without overwriting dirty files.
2. **GAME-1 (LOCAL_AGENT_RUNTIME):** attach to verified actual Sims 4 process, exact full version, explicitly authorized disposable lab save, two independent scene cues, and existing player/agent/host screen-control lease.
3. **LEARN-1 (LOCAL_AGENT_RUNTIME + operator review):** record *real, reviewed* helpful and harmful situation/action/outcome examples; replay the opt-in learner and compare against context-free baseline. No fabricated labels.
4. **P08-1 (LOCAL_AGENT_RUNTIME):** test the real screen handoff + listener advisory on active/idle player states, verify zero queue mutation and fail-closed abstention. Preserve captured proof only in ignored `dist/`.
5. **BI002-1 (LOCAL_AGENT_RUNTIME):** in parallel with the learning evidence lane where safe, finish the existing hunger actual reversible package, ≥5 vanilla and ≥5 modified trials, rollback, queue safety and independent maintainer review. Do not confuse learning evidence with hunger certification.
6. **CONVERGENCE:** reconcile validated outcome into repo `docs/LEDGER.md`, owning scripts/tests and exact patch evidence without exposing private observations. Report **CHANGED | PROVED | NEXT**.

**This P04 is a durable, machine-readable handoff**, not evidence that a ChatGPT connection started the user's Windows Sims session. Typed lane owner and dependencies: [BI-JUDGMENT-LEARNING-P04.execution.v1.json](../../plans/active/BI-JUDGMENT-LEARNING-P04.execution.v1.json).

## Pinned evidence and authority

- Repository: `EndeavorEverlasting/BetterInstincts`.
- Accepted feature: [PR #41](https://github.com/EndeavorEverlasting/BetterInstincts/pull/41), merged into `main` at **`13815fe5a6437e1351a95dbcfbd6026cf7317c64`**. Refresh remote HEAD before any work; this hash is a historical integration floor, not a license to reset newer work.
- User objective: BetterInstincts learns to recognize *your* good gameplay opportunities and contextual judgment across scenes and sequences, gradually requiring less human correction. This must not sacrifice manual control, individual Sims, hobbies, fun, socializing or balanced needs.
- Invoked precedence: **P97 prior-art inspection → P95 call-stack design → Trifecta P08/P82/P07 proof/build → P04 handoff**. Prompt identity remains Moonwake-owned, not copied here.
- Read first: `AGENTS.md`, `docs/DOCTRINE.md`, `docs/LEDGER.md`, `docs/PRIOR_ART.md`, `docs/JUDGMENT_LEARNING.md`, `docs/HOST_AUTONOMY.md`, `docs/SCENE_INTELLIGENCE.md`, `docs/LIVE_CERT.md`, `docs/COMPATIBILITY.md`, `plans/active/BI-002.execution.v1.json`.
- No other local file or scratchpad overrides the remote tracked code. One host is `LOCAL_AGENT_RUNTIME`; GitHub is a **provider**, not a running Windows Sims host.

## Ready-to-run local gates

From a current safe checkout (do not overwrite dirty or separately owned work):

```sh
python -m unittest tests.test_judgment_learning tests.test_listener_learning -v
python -m unittest discover -s tests -v
python -m scripts.check_horizon
python -m scripts.progression_eval --repo-only
python -m scripts.judgment_learning --help
python -m scripts.judgment_learning record --help
```

**Session preflight** — use the existing explicit `game_host`, scene map and save-guard scripts. Determine actual **current** game process and exact full main-menu patch; historical process IDs and `1.121.361.1020` observations are **not** current proof. The latest external patch is not an automatic target. Require a disposable, operator-attested LAB save. Observe `CONTENT_PRESENT`, Live Mode and two source-distinct scene cues. Fail closed on black/Build/Buy/unknown screen or active player input.

**Teaching one decision** — only after the operator genuinely reviews *both* chosen action and observed outcome, write `dist/judgment-learning/context.json` with exact supported enum fields (`scenario`, `need_state`, `scene`, `previous_action`, `style`). For example, a reviewed indoor `Sit and Chat Here` interaction that prevented unproductive outdoor walking is a candidate teaching observation, not an assumed success. Then run:

```sh
python -m scripts.judgment_learning record \
  --context dist/judgment-learning/context.json \
  --game-version ACTUAL_FULL_GAME_VERSION --platform windows \
  --action sit_and_chat_here --outcome helpful \
  --observation-ref capture:reviewed_real_001 \
  --examples-out dist/judgment-learning/reviewed.json \
  --operator-reviewed --explicit-opt-in
```

Use distinct observation references for genuine distinct trials. Record harmful/rejected actions as well, without inventing negative evidence. If the operator has not actually reviewed it, **do not** set either opt-in/review flag and do not add it. The CLI only accepts sanctioned semantic labels; no screenshots, private saves, full player names or free-form notes in the model.

**Learn and compare** — after enough independently reviewed examples to justify a pattern, run:

```sh
python -m scripts.judgment_learning train \
  --reviewed-examples dist/judgment-learning/reviewed.json \
  --game-version ACTUAL_FULL_GAME_VERSION --platform windows \
  --explicit-opt-in \
  --model-out dist/judgment-learning/model.json \
  --evaluation-out dist/judgment-learning/evaluation.json

python -m scripts.judgment_learning recommend \
  --model dist/judgment-learning/model.json \
  --query dist/judgment-learning/query.json
```

Report **prequential** contextual coverage + precision **alongside** context-free baseline coverage + precision. One bad or unfamiliar context must **ABSTAIN**, not invent the optimal action. A positive advice rate on synthetic fixtures is not live benefit. Keep each patch/platform profile independent, and personality/style conditional.

**Integrate listener** — after separately starting an opt-in named session and preparing a *real observed* bounded host observation (never synthesize live input):

```sh
python -m scripts.host_listener activate --session-id bi002-p04-learning

python -m scripts.host_listener tick \
  --session-id bi002-p04-learning --process-id ACTUAL_GAME_PID \
  --observation dist/game-host/ACTUAL_OBSERVATION.json \
  --learning-model dist/judgment-learning/model.json \
  --learning-query dist/judgment-learning/query.json

python -m scripts.host_listener deactivate --session-id bi002-p04-learning
```

Confirm the receipt's `learning_hint` is `ADVISORY_ONLY` **only** when the scene is verified and the human idle; the entire listener remains `execute_clicks:false`. When the player interacts with Sims or any desktop app, the listener must yield. Compare the player's queued actions before and after. If the viewport is unknown or the model lacks enough reviewed evidence, the result must be `ABSTAIN`; host planners and screen control must not be influenced by it.

## Acceptance, failure recovery and limits

| Gate | PASS requires | Failure handling |
| --- | --- | --- |
| Local code | same checkout commit, focused/full tests and validators pass | fix smallest actual regression; rerun before game test |
| Player-first handoff | observed player interrupt → host defers → safe idle → handoff, zero interference | stop any UI execution; preserve player queue |
| Teaching | reviewed, explicitly consented semantic labels bound to actual evidence | reject unreviewed or unverifiable events |
| Learning | sufficient consistent reviewed support; contextual vs simple baseline metrics; no leak across game patch/style/scene | abstain; refine evidence, do not override |
| Listener advice | real opt-in tick, safely observed view, advisory receipt, no SendInput | fail closed to player / unknown; inspect owning module |
| BI-002 | actual reversible hunger package, ≥5 vanilla+≥5 modified observed trials, rollback, queue safety, maintainer review | keep BI-002 ACTIVE and report exact missing gate |

**Not authorized:** modifying original/user saves, silent system-wide listeners, training on screenshots without verified interpretation, arbitrary directories, telemetry, hidden network uploads, copying third-party game assets, autonomously opening a new game session without safe local checks, or promoting offline tests to playable mod proof. No installed learning hook or game-certified behavior is claimed by this repository handoff.

**Return contract:** `CHANGED | PROVED | NEXT`, exact main and worktree SHA, OS, Sims patch, disposable save attestation, observation references (sanitized only), reviewed count, approved-vs-harmful labels, learner and baseline denominators, active-player abstention and action outcome, zero queue violations, 5+5 hunger trial counts, rollback status, maintainer review, files/commit/PR/CI/live states. Do not stop at a plan if the local game is safely reachable; run the smallest actual reviewed experiment and preserve a durable receipt.

**First exact command:** `python -m unittest tests.test_judgment_learning tests.test_listener_learning -v`.
