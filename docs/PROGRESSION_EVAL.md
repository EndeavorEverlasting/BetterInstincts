# Progression & CI honesty evaluator — P67 + P62 (+ P95 design)

Executable repository eval framework for **how far BetterInstincts has actually progressed** toward the parent objective, and whether CI/CD evidence is being over-claimed.

## What it measures

| Rate | Meaning | Current intent |
| --- | --- | --- |
| `vision_marker_rate` | North star, owner objective, product contract, five non-negotiables, horizon order, first-win hunger, proof-ceiling honesty markers still present in governance docs | Must stay 1.0 |
| `scaffolding_rate` | Required contracts, evaluators, live-cert tools, and CI substrings present | May be high before any game cert |
| `product_progression_rate` | Fraction of primary trajectory stages (`BI-002`…`BI-006`) with **GAME_CERTIFIED** evidence | Honest product rate; **0.0** until catalog profiles exist |
| `hunger_trial_rate` | Vanilla 5 + modified 5 + rollback progress toward BI-002 | Separate from packaging CI |
| `ci_game_gap` | `scaffolding_rate - product_progression_rate` | Large early gap is expected; promoting CI green as playable is **BLOCKED** |

## Fail-closed promotions

- Claiming `GAME_CERTIFIED` or `PLAYABLE_MOD` with an empty compatibility catalog
- Closing BI-002 without ≥5 baseline, ≥5 modified, and rollback
- Income before needs balance; skills before income; career before skills
- Missing vision markers or required CI/scaffolding paths

## Run

```sh
python -m scripts.progression_eval --out dist/progression-eval/current.json
python -m scripts.progression_eval --repo-only
python -m unittest tests.test_progression_eval -v
```

Receipts must stay under ignored `dist/progression-eval/`. Suite fixtures: `tests/fixtures/progression-eval.v1.json`.

## Proof ceiling

Offline / synthetic only. A green progression suite or high scaffolding rate is **not** Sims live certification, not a hunger package, and not a release. Live BI-002 trials remain `LOCAL_OBSERVED` or unproven until maintainer-accepted profiles exist.

## Call stack (P95)

`contracts/progression-eval.v1.json` → `betterinstincts/progression_eval.py` → `scripts/progression_eval.py` → CI (`scripts.progression_eval`) + `tests/test_progression_eval.py`. Complements `host_eval` (journey) and `eval_horizon` (policy scenarios); does not replace `live_cert`.
