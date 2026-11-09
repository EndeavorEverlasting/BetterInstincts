# BetterInstincts
**Smarter Sims. Better decisions. More interesting lives.**

An experimental, community-oriented autonomy mod project for **The Sims 4**. Make Sims more competent at meeting needs, building income, and progressing in careers while keeping their personalities, free time, autonomy, and the player's direct orders intact.

> **Status: pre-alpha, not a playable mod.** The current Python decision-policy prototype is an offline experiment; it is **not connected to the game**, and no `.package` or `.ts4script` release has been validated.

## Install / uninstall the offline toolkit (Windows and Linux Mint)

This is **still pre-alpha, not a playable Sims 4 mod**. The repository home page provides [bootstrap.py](bootstrap.py), a user-scoped installer with no third-party dependencies. Download that file to a location **outside** the checkout, inspect it, then run:

```sh
python bootstrap.py doctor
python bootstrap.py install
python bootstrap.py uninstall
```

`install` clones the repository into the [canonical profile-aware development path](contracts/workstation-paths.v1.json) if it is absent, and adds an offline host-listener launcher plus ownership manifest in a separate use path. `uninstall` deletes only verified installer-owned files and a pristine checkout that this bootstrapper itself created; it **preserves existing or modified checkouts and Sims saves**. It does not install a game mod, service, browser, cron job, global package, registry entry or PATH change. Full procedure and platform rules: [Async interoperability and lifecycle](docs/ASYNC_INTEROP.md).

## Cooperative async computer control

The [15-second human-idle waiter](betterinstincts/workflow_interop.py) retains queued agent intent without cancelling it while the operator types or moves the mouse. [Playwright adapters](betterinstincts/playwright_interop.py) reuse an existing browser page rather than launching competing browsers; cooperating Sims executors share a desktop lock. A fresh safety checkpoint is required before each UI effect. Unknown input, stale scene or ambiguous outcomes fail closed. This is **opt-in offline infrastructure**; live browser and Sims behavior are not certified. [Machine-readable interoperability contract](contracts/workflow-interoperability.v1.json) and [full guide](docs/ASYNC_INTEROP.md).

## Start here
- [Agent instructions](AGENTS.md) — short, mandatory operating entrypoint.
- [Doctrine](docs/DOCTRINE.md) — product and safety boundaries.
- [Glossary](docs/GLOSSARY.md) — host/evaluator vocabulary (emulate, optimize, presence).
- [Host autonomy (P95)](docs/HOST_AUTONOMY.md) — opt-in listener, player-presence, map-travel force.
- [Project ledger](docs/LEDGER.md) — canonical vision, current evidence, decisions, and gates.
- [External prior art](docs/PRIOR_ART.md) — P97 evidence and adoption choices.
- [Prompt provenance](docs/PROMPT_INVOCATIONS.md) — exact TokenCorridor owners/definitions.
- [Strategic selection](docs/STRATEGY.md) — P141 competing theses and next investigation.
- [Roadmap](docs/ROADMAP.md) — needs, work, career, then broader autonomy.
- [Validation](docs/VALIDATION.md) — offline tests and future game certification.
- [Progression eval (P67/P62)](docs/PROGRESSION_EVAL.md) — CI honesty vs product progression rate.
- [Full product horizon](docs/HORIZON.md) — all six needs, balanced care, income, skills, then careers.
- [Horizon continuity](docs/HORIZON_CONTINUITY.md) — North Star → Continuity opener + BI-002 GAME-1.
- [Event balance](docs/EVENT_BALANCE.md) — outdoor-social RCA + hosted-event call stack.
- [Event goals](docs/EVENT_GOALS.md) — HUD goal → indoor pie-menu action catalog.
- [Fun service](docs/FUN_SERVICE.md) — parallel Fun lanes under guest/object contention.
- [Curious Catalog](docs/CURIOUS_CATALOG.md) — on-whim rare/alien/hydroponic Buy shelves; never autoruns or speeds sim.
- [Moodlets](docs/MOODLETS.md) — supplied emotion/moodlet strip for host routing.
- [Machine-readable dependency graph](plans/horizon.v1.json) — exact gate ownership and sequencing.
- [P141/P82 selection and experiment](docs/HORIZON_DECISIONS.md) — hypothesis, baseline and falsifiers.
- [Follow-on needs execution](plans/active/BI-003.execution.v1.json) — patch-specific local-agent work.
- [Multiple game-version compatibility](docs/COMPATIBILITY.md) — exact builds, immutable older certified profiles.
- [Live-cert evidence workflow](docs/LIVE_CERT.md) — bounded local observations, progress hooks and numerical evaluator.
- [Maintainer review contract](docs/MAINTAINER_REVIEW.md) — genuine game proof and CODEOWNERS limitations.
- [Executable BI-002 game gate](plans/active/BI-002.execution.v1.json) — local agent cannot close before hunger is actually verified.
- [BI-001 sprint](plans/active/BI-001.md) — merged bootstrap and proof.
- [BI-002 game lab](plans/active/BI-002.md) — first bounded, reversible Sims gameplay test.

## First working experiment (offline only)
Run from repository root with Python 3.11+ (dev harness version; **not** a claim about the game's embedded Python):
```sh
python -m unittest discover -s tests -v
python scripts/validate_doctrine.py
python scripts/check_tracked_assets.py
python -m betterinstincts.priority
python -m scripts.eval_horizon
python -m scripts.check_horizon
python -m scripts.horizon_status
python -m scripts.progression_eval --repo-only
```
The policy returns a **suggestion** for a fictional Sim snapshot and never touches a real game, save, queue, or Mods directory. The smallest gameplay next step is to inspect the live game's relevant autonomy tuning using Sims 4 Studio, select one specific base-game behavior, and produce/test a reversible package against a recorded patch.

## Community
Original code is MIT licensed. Please open an issue for compatibility observations or behavior proposals, with game version, installed packs, mods, reproducible steps, and sanitized logs. No EA-owned assets or saves, please. This is an independent fan project, **not affiliated with or endorsed by EA/Maxis**. Distribution is intended to be free and consistent with [EA's mod policy](https://help.ea.com/en/articles/the-sims/the-sims-4/mods-policy/).

## Read-only Mod Lab bootstrap
- [Mod Lab and API reconnaissance](docs/MOD_LAB.md) — explicit Mods root, .package TGI index keys and .ts4script module-name inventory; no writes.
- [BI-MODLAB sprint](plans/active/BI-MODLAB.md) — tooling Mod Lab lane (not horizon income BI-004); preserves BI-002 gameplay and the needs/income/skills horizon.
- [P04 Mod Lab machine dispatch](plans/active/BI-MODLAB.dispatch.v1.json) — typed runtime partition, validation commands and game-observation ceiling.
- [P04 Mod Lab canonical handoff](plans/active/BI-MODLAB.HANDOFF.md) — local-agent launch order, verified PR/CI receipts, exact game-only gates and machine dispatch.

## Scene Intelligence & Save Safety (BI-SCENE-MAP)
- [Scene catalog, safe transition architecture and save naming](docs/SCENE_INTELLIGENCE.md) — 35 version-bound candidate scenes and protected-save doctrine.
- [Machine-readable scenes](contracts/game-scenes.v1.json), [save policy](contracts/save-policy.v1.json), [scene sprint](plans/active/BI-SCENE-MAP.md).
- `python -m scripts.check_scene_contract` validates the state graph, chosen-save gate and protected-default policy; no screenshots or game launch performed.

- [P04 Scene Intelligence canonical handoff](plans/active/BI-SCENE-MAP.HANDOFF.md) and [typed dispatch](plans/active/BI-SCENE-MAP.dispatch.v1.json) — current offline evidence, protected-save policy and live Windows host execution order.

## Hidden objects — P04 host discovery
- [General hidden-item discovery](docs/HIDDEN_OBJECT_DISCOVERY.md) — opt-in, read-only game-host planner for `bb.showhiddenobjects` and optional `bb.showliveeditobjects`; deterministic categories, per-item price evidence, no auto-clicks or game-speed changes.
- [Local-agent P04 launch order](plans/active/BI-HIDDEN-OBJECTS.P04.md) and [typed dispatch](plans/active/BI-HIDDEN-OBJECTS.dispatch.v1.json) — exact patch and scene gates remain owned by the Windows game host; BI-002 hunger is still active.
