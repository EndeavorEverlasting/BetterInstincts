# BetterInstincts
**Smarter Sims. Better decisions. More interesting lives.**

An experimental, community-oriented autonomy mod project for **The Sims 4**. Make Sims more competent at meeting needs, building income, and progressing in careers while keeping their personalities, free time, autonomy, and the player's direct orders intact.

> **Status: pre-alpha, not a playable mod.** The current Python decision-policy prototype is an offline experiment; it is **not connected to the game**, and no `.package` or `.ts4script` release has been validated.

## Start here
- [Agent instructions](AGENTS.md) — short, mandatory operating entrypoint.
- [Doctrine](docs/DOCTRINE.md) — product and safety boundaries.
- [Project ledger](docs/LEDGER.md) — canonical vision, current evidence, decisions, and gates.
- [External prior art](docs/PRIOR_ART.md) — P97 evidence and adoption choices.
- [Prompt provenance](docs/PROMPT_INVOCATIONS.md) — exact TokenCorridor owners/definitions.
- [Strategic selection](docs/STRATEGY.md) — P141 competing theses and next investigation.
- [Roadmap](docs/ROADMAP.md) — needs, work, career, then broader autonomy.
- [Validation](docs/VALIDATION.md) — offline tests and future game certification.
- [Multiple game-version compatibility](docs/COMPATIBILITY.md) — exact builds, immutable older certified profiles.
- [Live-cert evidence workflow](docs/LIVE_CERT.md) — bounded local observations, progress hooks and numerical evaluator.
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
```
The policy returns a **suggestion** for a fictional Sim snapshot and never touches a real game, save, queue, or Mods directory. The smallest gameplay next step is to inspect the live game's relevant autonomy tuning using Sims 4 Studio, select one specific base-game behavior, and produce/test a reversible package against a recorded patch.

## Community
Original code is MIT licensed. Please open an issue for compatibility observations or behavior proposals, with game version, installed packs, mods, reproducible steps, and sanitized logs. No EA-owned assets or saves, please. This is an independent fan project, **not affiliated with or endorsed by EA/Maxis**. Distribution is intended to be free and consistent with [EA's mod policy](https://help.ea.com/en/articles/the-sims/the-sims-4/mods-policy/).
