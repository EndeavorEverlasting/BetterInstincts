# P04 — ontology-first BetterInstincts local-game certification handoff

## LAUNCH ORDER — current repo proof → exact local game proof → convergence

1. **GATE-0 — PROVED, CI_OR_REMOTE_RUNNER:** ontology PR #57 merged on `main` at `091fa6d2ae49de54fd3536b8f7aa6913006df49d`; post-merge CI green. Do not rerun remote work as though it were missing.
2. **LOCAL-0 — LOCAL_AGENT_RUNTIME:** refresh a **safe existing** checkout, inspect the ontology and its canonical owners *before starting experiments, sampling, bootstrapping, or source mutations*. Confirm the supplied deterministic baseline.
3. **BUILD-1 — LOCAL_AGENT_RUNTIME:** observe exact full game build and consented disposable save, check two independent scene cues, create a build-exact consultation *before the first live sample or gameplay-affecting mutation*, and independently confirm host/game admission.
4. **SEM-1 — LOCAL_AGENT_RUNTIME (read-only):** test open-domain goal coordination, resource contention, contingency evidence, player yield, and resumption under deterministic/synthetic input. This may run alongside GAME-1 **only if** separate workers can safely operate without shared writes or game input.
5. **GAME-1 — LOCAL_AGENT_RUNTIME (exclusive game input):** the existing BI-002 hunger parent gate: five genuine baseline vanilla trials.
6. **GAME-2 — LOCAL_AGENT_RUNTIME (exclusive game input):** create a reversible patch-specific package after actual tuning inspection, five genuine modified trials, then rollback and player-queue safety checks.
7. **P08-1 — LOCAL_AGENT_RUNTIME:** observe semantic advisory and, when organically available, contingencies/intent resumption against real game events. Do not manufacture a robbery or universalize any patch-specific anecdote.
8. **REVIEW-1 — OPERATOR_OR_PHYSICAL_RUNTIME:** independently review actual package hashes, selected-save provenance, recorded measurements, rollback and human-control safety before certification.
9. **CONVERGE — LOCAL_AGENT_RUNTIME:** reconcile independently validated outcomes into the owning contracts/ledger by reviewed commits. Never certify BI-002 from an offline PASS or from this handoff.

**Machine-readable lanes:** [BI-SEMANTIC-ONTOLOGY-P04.execution.v1.json](../../plans/active/BI-SEMANTIC-ONTOLOGY-P04.execution.v1.json). This is the canonical **new** ontology handoff. It does not replace the [judgment-learning P04 handoff](BI-JUDGMENT-LEARNING-P04-2026-11-07.md) or `plans/active/BI-002.execution.v1.json`. Parent remains **BI-002 hunger live certification**.

## Pinned, independently proved starting state

- **Repository:** `EndeavorEverlasting/BetterInstincts` (public; protect private saves, media and paths).
- **Integration:** [PR #57](https://github.com/EndeavorEverlasting/BetterInstincts/pull/57) merged into **main** at `091fa6d2ae49de54fd3536b8f7aa6913006df49d`.
- **Pre-merge full CI:** [run 42423095521](https://github.com/EndeavorEverlasting/BetterInstincts/actions/runs/42423095521): **433 offline tests**, **1 skipped**; `ONTOLOGY_GATE_PASS changed=9 early_consultations=2`; local semantic-preflight canary passed.
- **Post-merge main CI:** [run 42423191457](https://github.com/EndeavorEverlasting/BetterInstincts/actions/runs/42423191457): **SUCCESS** at exact merged main commit.
- **Ontology:** `contracts/ontology.v1.json` revision 2; 40 concepts, 45 typed edges, 18 invariants, Git blob `eda1b4664714ca21a3caa659e40cbd6061ac36c8`. Earlier consultation receipts remain pinned to the original historical blob.
- **Code and harness:** `betterinstincts/semantic_advisory.py`, `scripts/semantic_preflight.py`, `scripts/check_ontology.py`, `tests/test_semantic_advisory.py`, `tests/test_ontology_gate.py`. The semantic module cannot perform UI input or grant a `CONTROL_PERMIT`.
- **Proof ceiling:** merged **offline engineering** only. **No game host, actual Sims package, local live sampling, operator save consent or game-playable release is established by those facts.**

## Foundational semantics — preserve, don't reinterpret

**Mission:** better natural Sims 4 instincts: maintain six needs, make enough income to meet bills, progressively balance careers, skills, relationships, rest, personality and unexpected events through bounded cross-domain decisions. Boot/menu/save/scene recovery supports this mission, but does not replace the needs-engine parent. Existing `domain_cascade` owns cross-domain polling; existing `need_load_balance` owns six-need service detach/assumption windows. Do not invent a second scheduler to re-prove those two owners.

**No arbitrary capability ceiling:** a future world economy, household coordinator, new algorithm, custom gameplay mechanic or community extension may be proposed and evaluated. Prefer tested native game mechanics by default; justify extensions individually and do **not** make them prerequisites for BI-002 without actual dependency evidence. An ontology describes semantics and admissibility, not an exhaustive approved-domain enum or a mandatory Python/architecture choice.

**Continuity of intent:** a time-sensitive event can preempt an activity when observed evidence supports the change. Persist the earlier `GOAL_THREAD`, interruption cause, resource ownership, and `RESUME_CONDITION`; re-evaluate before resuming, never replay stale clicks blindly. Parallel evaluators **do not** imply parallel physical actions or an override of explicit player commands.

**Burglar story:** calling police instead of confronting a burglar is the operator's observed strategic insight, **not an assumed universal Sims mechanic**. Exact installed game version/packs/mods, observed UI affordances, actual police/action outcome, and the interrupt/resume path must be independently demonstrated before converting it to a rule.

**Proof taxonomy:** `ONTOLOGY_CONSULTED` ≠ `REPO_OFFLINE_PASS` ≠ `MAIN_MERGED` ≠ `LOCAL_GAME_OBSERVED` ≠ `BI002_REVIEW_CERTIFIED`. The last two remain unproven in this handoff.

## Mandatory local preflight — ontology before experiments

After reading `AGENTS.md`, `docs/ONTOLOGY.md`, `contracts/ontology.v1.json`, and **affected concept owners**, run in the existing repo checkout:

```sh
python -m scripts.check_ontology
python -m unittest tests.test_ontology_gate tests.test_semantic_advisory -v
python -m scripts.semantic_preflight --consultation contracts/consultations/BI-SEMANTIC-ORCHESTRATION-20261107.v1.json --operation offline_experiment
```

A successful **offline** consultation explicitly **does not** admit real-game sampling. For EACH *new* local gameplay experiment or change, the local agent must:

1. Recover the actual local game/patch/platform/pack combination **without assuming a historical version is still installed**. Inspect real player presence, allowed save provenance, actual Sims UI scenes (two independent cues) and agent/host control ownership.
2. Review affected `GOAL_THREAD`, `CONTINGENCY`, `CONTROL_PERMIT`, `GAME_BUILD`, `SAVE_SLOT`, `PLAYER_INTENT`, `OUTCOME` concepts and their current owner files; explicitly record missing concepts, claims, alternative diagnoses, expected effects and negative tests.
3. Create a **new** `contracts/consultations/<scoped-id>.v1.json` receipt using the actual ontology Git blob SHA and `betterinstincts.ontology-consultation/v1` fields. Include actual `EXACT_GAME_BUILD:<full-version>`, all universal safety invariants, owner paths, specific candidate mutation files, evidence ceiling, operator/save/control impact, rollback, uncertainties and admitted decision. **Commit it before any behavior code mutation**. Do not push private game evidence or absolute personal paths to public GitHub.
4. Run the gate **before** a live sampling or gameplay experiment:

```sh
python -m scripts.semantic_preflight --consultation contracts/consultations/NEW_SCOPED_GAME_CONSULTATION.v1.json --operation game_sampling --exact-game-build ACTUAL_FULL_VERSION
```

5. Treat `ONTOLOGY_PREFLIGHT_PASS_NOT_GAME_AUTHORITY` as **semantic readiness only**. Next independently verify `game_host`/scene/build/save/player/explicit opt-in controls; any unknown prevents input. A pass never grants a UI click, save operation, proof of training benefit, or release certification.

Before *other* new behavior changes, create/commit the analogous consultation and check `--operation repo_mutation --file <actual-repo-file>`; PR CI checks the historical commit chronology for **each changed behavior path**, not just one blanket receipt at the end.

## Real-game validation: the single product parent

The local agent's job is to complete **BI-002**, not to produce more offline scaffolding while game proof is available. Start from [BI-002 execution gates](../../plans/active/BI-002.execution.v1.json) and [live certification instructions](../LIVE_CERT.md). On an actually authorized and disposable save, collect **at least five distinct vanilla trials** then five modified trials with one reversible package, real pre/post metrics, original package/tuning hashes, queue/player-safety observations and rollback. `python -m scripts.live_cert status --run-id ACTUAL_LOCAL_RUN_ID` after each. Only independent maintainer review can certify a new build profile; no blanket promotion of other patches.

The semantic P08 lane then explores actual context from the player-allowed game: whether multiple domain goals stay live, whether an observed urgency should preempt, whether an earlier intention survives and resumes, whether resources are double-booked, and whether player direction always yields. Record a *failure or inconclusive outcome* where evidence is absent rather than claiming success. Any game-coupled correction must itself start with ontology consultation and a separate scoped owned PR.

## Runtime partition and autonomous execution

| Work | Actual host | Status |
| --- | --- | --- |
| Ontology/semantic implementation, full 433-test CI, merge/readback | CURRENT_CHAT_RUNTIME via GitHub provider + CI_OR_REMOTE_RUNNER | **PROVED** |
| Read-only local ontology preflight, exact patch discovery | LOCAL_AGENT_RUNTIME | **NOT LAUNCHED HERE** |
| Five vanilla, five modified, reversible package and rollback | LOCAL_AGENT_RUNTIME, one game-controller writer | **WAITING_REAL_GAME** |
| Player authority and final game certification | OPERATOR_OR_PHYSICAL_RUNTIME | **NOT OBSERVED** |

The graph has a possible safe read-only `SEM-1` lane separate from `GAME-1`. This handoff **does not claim it was dispatched in parallel**. Probe actual local child agents, repository runners and available CI adapters on the host, then dispatch only independent lanes where available. Game input remains a single-controller lane. The Moonwake `harness/contracts/prompt-parallel-dispatch.v1.json` and `scripts/prompt_parallel_dispatch.py` paths were not retrievable at its inspected `main`; do not assert a generic P04 manifest was CLI-validated or executed. The repo-native typed plan above is the authoritative transport until a verified adapter owns actual dispatch.

## Verification and convergence receipt

Capture: exact current source SHA; worktree/branch status; actual full game patch and packs; selected-save provenance and consent; separate `baseline_count/5` and `modified_count/5`; package/tuning hashes and rollback; per-goal continuity/preemption proof; object/queue safety; outcome capture refs; independent review status; which P08/BI-002 gate has **actually** passed; exact next host command.

The source repo keeps evidence bounded and non-sensitive under ignored `dist/`; only sanitized receipts and reviewed code are committed. Existing horizon/version evidence remains immutable.

**CHANGED | PROVED | NEXT:** preserve this handoff and the prior learning handoff as separate domains. On local host, first run `python -m unittest tests.test_ontology_gate tests.test_semantic_advisory -v`, then confirm actual game access and continue the first unproven BI-002 gate. Do not stop at P04's text if an authorized, safe local experiment is executable.
