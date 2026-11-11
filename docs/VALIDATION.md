# Validation and release gates

## Offline (safe in any host)
From repo root:
```sh
python -m unittest discover -s tests -v
python scripts/validate_doctrine.py
python scripts/check_tracked_assets.py
python -m scripts.check_horizon
python -m scripts.check_horizon_continuity
python -m scripts.eval_horizon
python -m scripts.horizon_status
python -m scripts.host_eval --out dist/host-eval/local.json
python -m scripts.progression_eval --out dist/progression-eval/local.json
python -m scripts.progression_eval --repo-only
python -m scripts.check_backward_compat --base-ref <git-base-sha>
python -m betterinstincts.priority
```
No network, EA installation, privileged permissions, or external Python packages needed. CI proves only these offline checks, never game compatibility. Progression rates separate scaffolding from `product_progression_rate` (see [PROGRESSION_EVAL.md](PROGRESSION_EVAL.md)).

## Local cert progress and compatibility (game evidence UNPROVEN)
Follow [the live-cert CLI instructions](LIVE_CERT.md) and [BI-002's executable gates](../plans/active/BI-002.execution.v1.json). Agents record observed trials, query status after every trial and deliver gameplay capture references. `MEASUREMENTS_PASS_REVIEW_REQUIRED` is **not a certificate**. CI protects older certified patch profiles; it cannot observe Sims or validate the package's in-game functionality. UNKNOWN_VERSION and UNVERIFIED must never be promoted silently.

## Horizon offline-vs-gameplay proof
The six-need policy (`betterinstincts/horizon.py`) and stage dependency graph (`plans/horizon.v1.json`) are **offline architecture**, not Sims integrations. Unit tests, a 12-needs-level plus income/skill scenario probe, and status CLI prove only policy invariants and current outstanding gate. `scripts.check_horizon` fails if any of the five successor needs, joint balance, income-before-skills order, or dependency topology disappears. Individual needs must later be certified per game patch, then jointly balanced; income needs observed in-game funds changes before skills, which need measured in-game skill increments.

## Gameplay gate (UNPROVEN)
Record date, OS, base-game patch, installed DLC, Mods manifest, Sims 4 Studio build, tested package hash, explicit install destination (chosen by user), and a disposable test save. Never touch original/production saves. Perform repeatable baseline+modified sessions on the same reset state; avoid stale script caches when game instructions require clearing them. Keep reproducible notes/sanitized error logs. Stop and roll back if action loops, frozen queues, unexpected forced interactions, cross-household effects, performance regression or lost gameplay.

Minimum manual acceptance for BI-002:
- One narrow urgent-hunger autonomy behavior materially improves over vanilla under comparable conditions.
- Player-directed action is not cancelled, reordered, or interrupted by our module.
- With feature disabled/removed, behavior returns to baseline; save loads.
- No unexplained exception, recurring spam, or significant slowdown.
- Identify collisions with Smarter Self-Care, MCCC, Better Sleep Autonomy and applicable overrides; test separate mod combinations rather than assert blanket compatibility.
- Package installs/uninstalls in a documented, explicit directory; no unexpected disk writes.

## Publication gate
Release only if a playable build actually passed the gameplay gate on a named patch, has install/uninstall instructions, known limitations, license/dependency disclosures, changelog and rollback instructions. Label untested patches **unknown**. New EA patches require rerunning compatibility proof. Report built != locally tested != merged != live-proven.

## Opt-in human ↔ host screen handoff (P95 → Trifecta)

```sh
python -m unittest tests.test_control_handoff tests.test_host_autonomy -v
python -m unittest discover -s tests -v
python -m scripts.check_horizon
python -m scripts.progression_eval --repo-only
```

The control policy is offline-testable and fails closed on active/unknown human input. One-shot local inspection is `python -m scripts.control_handoff --session-id ID --process-id PID --idle-ms 8000 --confirm`; the named listener session must be explicitly activated. The execution adapter `scripts.needs_force run --execute` requires the session ID, exact PID and **one** `--step-id` plus scene and queue verification by the local game agent. No unattended watcher, no implicit focus takeover, no multi-click lease.

The full live P08 proof still requires game-host observations of **player input interrupting host control**, idle passage allowing one verified control step, zero player queue interruptions and scene-safe recovery; tests/mocks alone do not demonstrate that. Other direct UI executors must adopt the same gate before claiming general interoperability. BI-002 hunger certification remains independent.

## Reviewed human judgment learner — P97/P95/Trifecta

```sh
python -m unittest tests.test_judgment_learning tests.test_listener_learning -v
python -m unittest discover -s tests -v
python -m scripts.check_horizon
python -m scripts.progression_eval --repo-only
```

These establish deterministic **offline** train/predict/prequential, active-player and unknown-scene abstention, patch isolation, explicit consent, bounded input/paths, and advisory-only listener integration. `python -m scripts.judgment_learning --help` documents explicit local training/recommendation commands; raw reviewed examples and aggregate models stay in ignored repo `dist/judgment-learning`, never committed. CI green and high historical precision do **not** demonstrate real gameplay, causal improvement, valid real-world sensors, package compatibility or BI-002 certification. Real game proof and control collision checks belong to the local P08 + BI-002 path.

## P00/P01 human sovereignty harness — separate gates

`python -m scripts.check_human_sovereignty --json` validates revision-5
ontology and glossary coverage, canonical governance owners, typed authority
taxonomy, machine source/adoption inventory, safe background classification,
known raw-input exceptions, and CI wiring. Unit fixtures:
`tests.test_human_sovereignty_governance` and
`tests.test_human_first_harness`. These checks must fail on an
unregistered raw Win32/desktop input script, false-gated screen effect,
or invented background input permission. Run existing peripheral and
operator-hook tests as independent checks.

Pass means only **registered static source and offline fixtures**:
`REPO_COMMITTED`, `CI_TESTS_PASSED`, `DEFAULT_BRANCH_MERGED`,
`CANONICAL_DEV_CHECKOUT_CURRENT`, `LOCAL_USE_APP_CURRENT`,
`LOCAL_CURSOR_HOOK_ACTIVE`, `WINDOWS_HUMAN_INTERRUPT_OBSERVED`,
and `GAMEPLAY_CERTIFIED` are separate evidence dimensions.
Unadopted legacy CAS and raw adapters are inventory debts, not safe
runtime execution permits. See `docs/HUMAN_FIRST_HARNESS.md`.

## Native EA gameplay architecture gate — P00/P01

Run `python -m scripts.check_native_gameplay_authority` and
`python -m unittest tests.test_native_gameplay_authority -v`.
PR CI also runs the checker with `--base-ref` using the actual
GitHub PR base commit SHA. This enforces the machine
`contracts/native-gameplay-authority.v1.json` route taxonomy,
mandatory new/updated per-product-file route declarations in
`contracts/native-gameplay-decisions/`, static denial of known desktop
input mechanisms inside the current core gameplay-policy modules,
ontology/agent rule/Cursor rule ownership and proof-ceiling separation.
A host diagnostic can remain a host diagnostic, but a host-lab or
offline-policy route cannot claim shipped native gameplay.

This is a **static preventative architecture guard**, not a
runtime sandbox: declarations can misdescribe code, unlisted
dynamic imports need review, external agents need separate
activation/proof and real Sims queue effect still requires
patch-specific EA inspection, disposable 5+5 or equivalent named
A/B, live player override, rollback and maintainer review.
Native mod delivery remains issue #171 and BI-002 remains separate.

